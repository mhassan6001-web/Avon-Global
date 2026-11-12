/**
 * Minimal typed API client.
 *
 * The browser calls same-origin `/api/v1/*`; Next.js proxies to the backend.
 * Errors are normalised to `ApiError` using the backend's error envelope.
 */

export const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly body: unknown;

  constructor(params: {
    status: number;
    code: string;
    message: string;
    requestId: string | null;
    body?: unknown;
  }) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.code = params.code;
    this.requestId = params.requestId;
    this.body = params.body;
  }
}

interface ErrorEnvelope {
  error: { code: string; message: string; request_id?: string | null };
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (!value || typeof value !== "object" || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return (
    !!error &&
    typeof error === "object" &&
    typeof (error as { code?: unknown }).code === "string" &&
    typeof (error as { message?: unknown }).message === "string"
  );
}

export interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
  /** HTTP statuses (besides 2xx) whose JSON body is a valid response, e.g. 503 for readiness. */
  acceptStatuses?: number[];
  fetchImpl?: typeof fetch;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  requestId: string | null;
}

export async function getJson<T>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiResponse<T>> {
  const { timeoutMs = 8000, acceptStatuses = [], fetchImpl = fetch } = options;
  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(new DOMException("Timed out", "TimeoutError")),
    timeoutMs,
  );
  const onAbort = () => controller.abort(options.signal?.reason);
  options.signal?.addEventListener("abort", onAbort, { once: true });

  let response: Response;
  try {
    response = await fetchImpl(`${API_PREFIX}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      credentials: "same-origin",
      signal: controller.signal,
    });
  } catch (cause) {
    const timedOut =
      controller.signal.reason instanceof DOMException &&
      controller.signal.reason.name === "TimeoutError";
    throw new ApiError({
      status: 0,
      code: timedOut ? "timeout" : "network_error",
      message: timedOut
        ? "The server did not respond in time."
        : "The server could not be reached.",
      requestId: null,
      body: cause,
    });
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", onAbort);
  }

  const requestId = response.headers.get("x-request-id");
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (response.ok || acceptStatuses.includes(response.status)) {
    if (body === null) {
      throw new ApiError({
        status: response.status,
        code: "invalid_response",
        message: "The server returned an unreadable response.",
        requestId,
      });
    }
    return { data: body as T, status: response.status, requestId };
  }

  if (isErrorEnvelope(body)) {
    throw new ApiError({
      status: response.status,
      code: body.error.code,
      message: body.error.message,
      requestId: body.error.request_id ?? requestId,
      body,
    });
  }
  throw new ApiError({
    status: response.status,
    code: response.status >= 500 ? "server_error" : "http_error",
    message: `Request failed with status ${response.status}.`,
    requestId,
    body,
  });
}

export const CSRF_COOKIE = "aven_csrf";

/** Read a cookie value (the CSRF token is deliberately readable by the app). */
export function readCookie(name: string, cookieString?: string): string | null {
  const source = cookieString ?? (typeof document === "undefined" ? "" : document.cookie);
  for (const part of source.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

export interface SendOptions extends RequestOptions {
  body?: unknown;
  csrfToken?: string | null;
}

/**
 * JSON request for any method. State-changing requests carry the CSRF token
 * (double-submit) read from the ``aven_csrf`` cookie.
 */
export async function send<T>(
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
  path: string,
  options: SendOptions = {},
): Promise<ApiResponse<T>> {
  const { timeoutMs = 15000, acceptStatuses = [], fetchImpl = fetch } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") {
    const csrf = options.csrfToken !== undefined ? options.csrfToken : readCookie(CSRF_COOKIE);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(new DOMException("Timed out", "TimeoutError")),
    timeoutMs,
  );
  let response: Response;
  try {
    response = await fetchImpl(`${API_PREFIX}${path}`, {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
      credentials: "same-origin",
      signal: options.signal ?? controller.signal,
    });
  } catch (cause) {
    throw new ApiError({
      status: 0,
      code: "network_error",
      message: "The server could not be reached.",
      requestId: null,
      body: cause,
    });
  } finally {
    clearTimeout(timer);
  }
  const requestId = response.headers.get("x-request-id");
  let parsed: unknown = null;
  try {
    parsed = await response.json();
  } catch {
    parsed = null;
  }
  if (response.ok || acceptStatuses.includes(response.status)) {
    return { data: parsed as T, status: response.status, requestId };
  }
  if (isErrorEnvelope(parsed)) {
    throw new ApiError({
      status: response.status,
      code: parsed.error.code,
      message: parsed.error.message,
      requestId: parsed.error.request_id ?? requestId,
      body: parsed,
    });
  }
  throw new ApiError({
    status: response.status,
    code: response.status >= 500 ? "server_error" : "http_error",
    message: `Request failed with status ${response.status}.`,
    requestId,
    body: parsed,
  });
}

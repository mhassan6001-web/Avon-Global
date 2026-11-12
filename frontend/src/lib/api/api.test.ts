import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { ApiError, getJson } from "./client";
import { fetchReadiness, platformState, type ReadinessReport } from "./health";

function fakeFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  const calls: string[] = [];
  const impl = (async (url: string) => {
    calls.push(url);
    return new Response(body === undefined ? "not json" : JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json", ...headers },
    });
  }) as unknown as typeof fetch;
  return { impl, calls };
}

const report: ReadinessReport = {
  status: "ok",
  service: "AVEN GLOBAL",
  version: "0.1.0",
  environment: "test",
  timestamp: "2026-11-12T00:00:00Z",
  checks: [{ name: "database", status: "ok", required: true, latency_ms: 1.2, detail: null }],
};

describe("getJson", () => {
  it("prefixes the versioned API path and returns data with request id", async () => {
    const { impl, calls } = fakeFetch(200, { ok: true }, { "x-request-id": "abc12345" });
    const result = await getJson<{ ok: boolean }>("/health/live", { fetchImpl: impl });
    assert.equal(calls[0], "/api/v1/health/live");
    assert.deepEqual(result.data, { ok: true });
    assert.equal(result.requestId, "abc12345");
  });

  it("maps the backend error envelope to ApiError", async () => {
    const { impl } = fakeFetch(409, {
      error: { code: "already_approved", message: "Already approved.", request_id: "r-1" },
    });
    await assert.rejects(getJson("/x", { fetchImpl: impl }), (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.status, 409);
      assert.equal(error.code, "already_approved");
      assert.equal(error.requestId, "r-1");
      return true;
    });
  });

  it("reports network failures without throwing raw errors", async () => {
    const impl = (async () => {
      throw new TypeError("fetch failed");
    }) as unknown as typeof fetch;
    await assert.rejects(getJson("/x", { fetchImpl: impl }), { code: "network_error", status: 0 });
  });

  it("times out slow responses", async () => {
    const impl = ((_url: string, init?: RequestInit) =>
      new Promise((_, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("aborted", "AbortError")),
        );
      })) as unknown as typeof fetch;
    await assert.rejects(getJson("/x", { fetchImpl: impl, timeoutMs: 20 }), { code: "timeout" });
  });
});

describe("readiness", () => {
  it("treats 503 as a valid not-ready answer", async () => {
    const { impl } = fakeFetch(503, { ...report, status: "failing" });
    const result = await fetchReadiness({ fetchImpl: impl });
    assert.equal(result.status, 503);
    assert.equal(platformState(result.data, null), "degraded");
  });

  it("summarises platform state", () => {
    assert.equal(platformState(report, null), "operational");
    assert.equal(platformState(null, null), "checking");
    assert.equal(platformState(null, new Error("x")), "unreachable");
    const optionalDown: ReadinessReport = {
      ...report,
      checks: [
        ...report.checks,
        {
          name: "redis",
          status: "failing",
          required: false,
          latency_ms: null,
          detail: "unavailable",
        },
      ],
    };
    assert.equal(platformState(optionalDown, null), "degraded");
  });
});

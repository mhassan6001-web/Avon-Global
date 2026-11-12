/** Mirrors backend app/platform/identity/schemas.py. */

export type SessionState = "active" | "mfa_pending" | "mfa_enrolment_required";

export interface UserOut {
  id: string;
  email: string;
  display_name: string;
  role: string;
  role_name: string;
  department: string;
  status: "invited" | "active" | "suspended";
  is_dev_account: boolean;
  mfa_enabled: boolean;
}

export interface MeOut {
  user: UserOut;
  session_state: SessionState;
  permissions: string[];
  mfa_required_by_role: boolean;
  step_up_valid_until: string | null;
}

export interface LoginOut {
  state: SessionState;
  csrf_token: string;
  user: UserOut;
}

/** Where to send someone after sign-in, based on the session state. */
export function routeForState(state: SessionState, next: string | null): string {
  if (state === "mfa_pending")
    return `/sign-in?step=code${next ? `&next=${encodeURIComponent(next)}` : ""}`;
  if (state === "mfa_enrolment_required") return "/two-factor/setup";
  return safeNext(next);
}

/** Only allow same-site relative paths as post-login destinations (no open redirects). */
export function safeNext(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return "/";
  return next;
}

export const PASSWORD_MIN = 12;

export function passwordProblem(password: string, confirm: string): string | null {
  if (password.length < PASSWORD_MIN) return `Use at least ${PASSWORD_MIN} characters.`;
  if (password !== confirm) return "The passwords do not match.";
  return null;
}

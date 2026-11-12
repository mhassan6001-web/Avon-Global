import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { ApiError, readCookie, send } from "../api/client";
import { passwordProblem, routeForState, safeNext } from "./types";

describe("routeForState", () => {
  it("routes by session state", () => {
    assert.equal(routeForState("active", "/system"), "/system");
    assert.equal(routeForState("mfa_pending", null), "/sign-in?step=code");
    assert.equal(routeForState("mfa_enrolment_required", "/x"), "/two-factor/setup");
  });
  it("blocks open redirects", () => {
    for (const bad of ["https://evil.example", "//evil.example", "/\\\\evil", null, ""]) {
      assert.equal(safeNext(bad), "/");
    }
    assert.equal(safeNext("/admin/users"), "/admin/users");
  });
});

describe("passwordProblem", () => {
  it("checks length and confirmation", () => {
    assert.match(passwordProblem("short", "short") ?? "", /12/);
    assert.match(passwordProblem("long-enough-pass", "different-pass") ?? "", /match/);
    assert.equal(passwordProblem("long-enough-pass", "long-enough-pass"), null);
  });
});

describe("send", () => {
  it("adds the CSRF header to state-changing requests only", async () => {
    const seen: Array<Record<string, string>> = [];
    const impl = (async (_url: string, init?: RequestInit) => {
      seen.push(init?.headers as Record<string, string>);
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    }) as unknown as typeof fetch;
    await send("POST", "/auth/logout", { fetchImpl: impl, csrfToken: "tok123" });
    await send("GET", "/auth/me", { fetchImpl: impl, csrfToken: "tok123" });
    assert.equal(seen[0]?.["X-CSRF-Token"], "tok123");
    assert.equal(seen[1]?.["X-CSRF-Token"], undefined);
  });
  it("surfaces the backend error code", async () => {
    const impl = (async () =>
      new Response(
        JSON.stringify({
          error: { code: "step_up_required", message: "Confirm", request_id: "r" },
        }),
        { status: 403 },
      )) as unknown as typeof fetch;
    await assert.rejects(
      send("POST", "/admin/users", { fetchImpl: impl, body: {} }),
      (e: unknown) => {
        assert.ok(e instanceof ApiError);
        assert.equal(e.code, "step_up_required");
        return true;
      },
    );
  });
  it("reads cookies", () => {
    assert.equal(readCookie("aven_csrf", "a=1; aven_csrf=x%3Dy; b=2"), "x=y");
    assert.equal(readCookie("missing", "a=1"), null);
  });
});

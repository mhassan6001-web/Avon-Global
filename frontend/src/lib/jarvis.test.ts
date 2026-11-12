import assert from "node:assert/strict";
import { test } from "node:test";

import { applyStep, toolLabel, type Chain, type GatewayStep } from "./jarvis";

function run(steps: GatewayStep[]): Chain {
  return steps.reduce<Chain>((c, s) => applyStep(c, s), {});
}

test("a read tool lights every node except approval, which is skipped", () => {
  const c = run(["interpreting", "permission_ok", "validated", "audited"]);
  assert.equal(c.audit, "done");
  assert.equal(c.approval, "skipped");
  assert.equal(c.execution, "done");
});

test("a prepared action waits at approval and never shows audit early", () => {
  const c = run(["interpreting", "permission_ok", "validated", "awaiting_approval"]);
  assert.equal(c.approval, "active");
  assert.equal(c.audit, undefined);
  const done = run(["executing", "audited"].map((s) => s as GatewayStep));
  assert.equal(done.approval, "done");
  assert.equal(done.audit, "done");
});

test("a refusal blocks the node where it stopped", () => {
  const c = run(["interpreting", "failed"]);
  assert.equal(c.authentication, "done");
  assert.equal(c.permission, "blocked");
  assert.equal(c.audit, undefined);
});

test("tool labels are readable", () => {
  assert.equal(toolLabel("prepare_task"), "prepare task");
  assert.equal(toolLabel("list_pending_approvals"), "list pending approvals");
});

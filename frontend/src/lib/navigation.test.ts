import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { BUSINESS_MODULES, findModule, isActive, titleForPath } from "./navigation";

describe("navigation", () => {
  it("marks every business module as planned (no fake working modules)", () => {
    assert.ok(BUSINESS_MODULES.length > 0);
    for (const entry of BUSINESS_MODULES) {
      assert.equal(entry.status, "planned", `${entry.slug} must be planned in Stage 1`);
      assert.equal(entry.href, `/modules/${entry.slug}`);
    }
  });

  it("has unique slugs", () => {
    const slugs = BUSINESS_MODULES.map((entry) => entry.slug);
    assert.equal(new Set(slugs).size, slugs.length);
  });

  it("resolves titles and active state", () => {
    assert.equal(titleForPath("/"), "Command Centre");
    assert.equal(titleForPath("/system"), "System Status");
    assert.equal(titleForPath("/modules/finance"), "Finance");
    assert.equal(titleForPath("/unknown"), "AVEN GLOBAL");
    assert.equal(isActive("/system", "/"), false);
    assert.equal(isActive("/", "/"), true);
    assert.equal(isActive("/modules/crm", "/modules/crm"), true);
    assert.equal(findModule("nope"), undefined);
  });
});

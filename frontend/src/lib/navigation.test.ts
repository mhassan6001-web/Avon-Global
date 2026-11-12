import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { BUSINESS_MODULES, findModule, isActive, plannedModules, titleForPath } from "./navigation";

describe("navigation", () => {
  it("planned modules link to their information page; built ones declare a permission", () => {
    assert.ok(BUSINESS_MODULES.length > 0);
    for (const entry of BUSINESS_MODULES) {
      if (entry.status === "planned") assert.equal(entry.href, `/modules/${entry.slug}`);
      else assert.ok(entry.permission, `${entry.slug} needs a permission`);
    }
    assert.deepEqual(
      plannedModules().map((m) => m.slug),
      BUSINESS_MODULES.filter((m) => m.status === "planned").map((m) => m.slug),
    );
    assert.equal(findModule("crm")?.href, "/crm");
  });

  it("has unique slugs", () => {
    const slugs = BUSINESS_MODULES.map((entry) => entry.slug);
    assert.equal(new Set(slugs).size, slugs.length);
  });

  it("resolves titles and active state", () => {
    assert.equal(titleForPath("/"), "Command Centre");
    assert.equal(titleForPath("/system"), "System Status");
    assert.equal(titleForPath("/finance/invoices"), "Finance");
    assert.equal(titleForPath("/modules/hr"), "HR & Payroll");
    assert.equal(titleForPath("/unknown"), "AVEN GLOBAL");
    assert.equal(isActive("/system", "/"), false);
    assert.equal(isActive("/", "/"), true);
    assert.equal(isActive("/crm/customers/1", "/crm"), true);
    assert.equal(titleForPath("/crm/customers/1"), "CRM & Sales");
    assert.equal(findModule("nope"), undefined);
  });
});

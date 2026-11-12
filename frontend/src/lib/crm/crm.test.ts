import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  DIVISION_LABEL,
  DIVISIONS,
  formatMoney,
  isOverdue,
  query,
  STAGE_LABEL,
  STAGES,
} from "./types";

describe("crm helpers", () => {
  it("formats decimal strings exactly", () => {
    assert.equal(formatMoney("1500000.00", "MWK"), "MWK 1,500,000.00");
    assert.equal(formatMoney("12345678901234.5", "USD"), "USD 12,345,678,901,234.50");
    assert.equal(formatMoney("0", "ZAR"), "ZAR 0.00");
    assert.equal(formatMoney(null, "MWK"), "—");
  });
  it("detects overdue follow-ups only while open", () => {
    const now = Date.parse("2026-11-12T12:00:00Z");
    assert.equal(isOverdue({ due_at: "2026-11-11T12:00:00Z", completed_at: null }, now), true);
    assert.equal(
      isOverdue({ due_at: "2026-11-11T12:00:00Z", completed_at: "2026-11-12T00:00:00Z" }, now),
      false,
    );
    assert.equal(isOverdue({ due_at: "2026-11-13T12:00:00Z", completed_at: null }, now), false);
    assert.equal(isOverdue({ due_at: null, completed_at: null }, now), false);
  });
  it("builds query strings without empty values", () => {
    assert.equal(
      query({ q: "pumps", status: "", page: 2, open_only: false, x: null }),
      "?q=pumps&page=2",
    );
    assert.equal(query({}), "");
  });
  it("labels every stage and division", () => {
    for (const s of STAGES) assert.ok(STAGE_LABEL[s]);
    for (const d of DIVISIONS) assert.ok(DIVISION_LABEL[d]);
  });
});

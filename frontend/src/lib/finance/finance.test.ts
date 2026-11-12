import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { daysOverdue, sumMoney } from "./types";

describe("finance helpers", () => {
  it("adds money exactly, including negatives", () => {
    assert.equal(sumMoney(["0.10", "0.20"]), "0.30");
    assert.equal(sumMoney(["12150.00", "-2330.00"]), "9820.00");
    assert.equal(sumMoney(["-11650.00"]), "-11650.00");
    assert.equal(sumMoney(["99999999999999.99", "0.01"]), "100000000000000.00");
    assert.equal(sumMoney([]), "0.00");
  });
  it("counts days past due", () => {
    const today = new Date(2026, 10, 12);
    assert.equal(daysOverdue("2026-11-12", today), 0);
    assert.equal(daysOverdue("2026-11-20", today), 0);
    assert.equal(daysOverdue("2026-10-13", today), 30);
  });
});

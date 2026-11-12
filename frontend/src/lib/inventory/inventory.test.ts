import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { label, qty, remaining } from "./types";

describe("inventory helpers", () => {
  it("computes remaining quantities exactly", () => {
    assert.equal(remaining("8.000", "5.000"), "3.000");
    assert.equal(remaining("2.5", "0.125"), "2.375");
    assert.equal(remaining("1", "2"), "0.000");
  });
  it("formats quantities and labels", () => {
    assert.equal(qty("5.000"), "5");
    assert.equal(qty("2.500"), "2.5");
    assert.equal(qty("10"), "10");
    assert.equal(label("at_customs"), "At customs");
  });
});

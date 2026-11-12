import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { isDecimal, maskAccount } from "./types";

describe("procurement helpers", () => {
  it("validates decimal inputs", () => {
    assert.equal(isDecimal("1500"), true);
    assert.equal(isDecimal("1500.25"), true);
    assert.equal(isDecimal("1500.255"), false);
    assert.equal(isDecimal("1500.2555", 4), true);
    assert.equal(isDecimal("-1"), false);
    assert.equal(isDecimal("abc"), false);
  });
  it("never shows more than the last four digits", () => {
    assert.equal(maskAccount("3004"), "•••• 3004");
  });
});

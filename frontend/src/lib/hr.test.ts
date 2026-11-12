import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { inclusiveDays } from "./hr";

describe("hr helpers", () => {
  it("counts leave days inclusively", () => {
    assert.equal(inclusiveDays("2026-03-02", "2026-03-06"), 5);
    assert.equal(inclusiveDays("2026-03-02", "2026-03-02"), 1);
    assert.equal(inclusiveDays("2026-03-06", "2026-03-02"), 0);
    assert.equal(inclusiveDays("2026-02-27", "2026-03-02"), 4);
  });
});

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { arcs, formatAmount, niceMax, project, smoothPath } from "./scale";

describe("chart geometry", () => {
  it("rounds axis maxima to readable steps", () => {
    assert.equal(niceMax(0), 1);
    assert.equal(niceMax(7), 10);
    assert.equal(niceMax(180), 200);
    assert.equal(niceMax(2300), 2500);
  });
  it("projects values into the box with the highest at the top", () => {
    const pts = project(
      [
        { label: "a", value: 0 },
        { label: "b", value: 10 },
      ],
      100,
      50,
      0,
    );
    assert.deepEqual([pts[0]!.x, pts[0]!.y, pts[1]!.x, pts[1]!.y], [0, 50, 100, 0]);
  });
  it("builds paths and arcs", () => {
    assert.equal(smoothPath([]), "");
    assert.match(
      smoothPath([
        { x: 0, y: 0 },
        { x: 10, y: 5 },
        { x: 20, y: 0 },
      ]),
      /^M0,0 C/,
    );
    assert.deepEqual(arcs([0, 0]), []);
    const a = arcs([1, 3]);
    assert.ok(Math.abs(a[1]!.end - a[0]!.start - Math.PI * 2) < 1e-9);
  });
  it("formats amounts compactly with currency", () => {
    assert.equal(formatAmount(1_250_000, "MWK"), "MWK 1.3M");
    assert.equal(formatAmount(950), "950");
  });
});

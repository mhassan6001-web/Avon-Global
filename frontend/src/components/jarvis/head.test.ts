import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  amplitudeFor,
  headPoints,
  JARVIS_STATES,
  profileRadius,
  rotateY,
  waveSample,
} from "./head";

describe("JARVIS head geometry", () => {
  it("is deterministic and the requested size", () => {
    const a = headPoints(200);
    assert.equal(a.length, 200);
    assert.deepEqual(a, headPoints(200));
  });
  it("keeps every point inside the head profile envelope", () => {
    for (const p of headPoints(500)) {
      assert.ok(p.y >= -1.5 && p.y <= 1);
      assert.ok(Math.hypot(p.x, p.z) <= profileRadius(p.y) * 1.15 + 1e-9);
    }
  });
  it("rotation preserves distance from the axis", () => {
    const p = { x: 0.3, y: 0.2, z: -0.4 };
    const r = rotateY(p, 1.1);
    assert.ok(Math.abs(Math.hypot(r.x, r.z) - Math.hypot(p.x, p.z)) < 1e-12);
  });
  it("waveform is flat when muted or offline and loudest when speaking", () => {
    assert.equal(amplitudeFor("muted"), 0);
    assert.equal(amplitudeFor("offline"), 0);
    const max = Math.max(...JARVIS_STATES.map(amplitudeFor));
    assert.equal(amplitudeFor("speaking"), max);
    assert.equal(Math.abs(waveSample(0.5, 1, 0)), 0);
    assert.equal(Math.abs(waveSample(0, 2, 1)) < 1e-12, true); // pinned at the edges
  });
});

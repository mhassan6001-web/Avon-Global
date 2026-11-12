import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  DEFAULT_PREFERENCES,
  PRE_PAINT_SCRIPT,
  motionScale,
  parsePreferences,
  resolveMotion,
} from "./preferences";

describe("parsePreferences", () => {
  it("returns defaults for missing or corrupt storage", () => {
    assert.deepEqual(parsePreferences(null), DEFAULT_PREFERENCES);
    assert.deepEqual(parsePreferences("{not json"), DEFAULT_PREFERENCES);
    assert.deepEqual(parsePreferences("null"), DEFAULT_PREFERENCES);
  });

  it("keeps valid values and replaces invalid ones field by field", () => {
    assert.deepEqual(parsePreferences('{"motion":"off","contrast":"high"}'), {
      motion: "off",
      contrast: "high",
    });
    assert.deepEqual(parsePreferences('{"motion":"wild","contrast":"high"}'), {
      motion: "system",
      contrast: "high",
    });
  });
});

describe("resolveMotion", () => {
  it("follows the device when set to system", () => {
    assert.equal(resolveMotion("system", false), "full");
    assert.equal(resolveMotion("system", true), "reduced");
  });
  it("lets an explicit choice override the device", () => {
    assert.equal(resolveMotion("full", true), "full");
    assert.equal(resolveMotion("off", false), "off");
  });
  it("scales durations", () => {
    assert.equal(motionScale("full"), 1);
    assert.equal(motionScale("reduced"), 0.4);
    assert.equal(motionScale("off"), 0);
  });
});

describe("PRE_PAINT_SCRIPT", () => {
  it("is syntactically valid JavaScript", () => {
    assert.doesNotThrow(() => new Function(PRE_PAINT_SCRIPT));
  });
});

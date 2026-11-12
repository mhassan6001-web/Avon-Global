import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { SoundEngine } from "./engine";
import { applyPreset, DEFAULT_SOUND, EVENTS, gainFor, parseSound, PRESETS } from "./settings";

/** Minimal fake AudioContext that records node creation. */
function fakeContext() {
  const created: string[] = [];
  const param = () => ({ value: 1, setValueAtTime() {}, exponentialRampToValueAtTime() {} });
  const node = (kind: string) => {
    created.push(kind);
    const n = {
      gain: param(),
      frequency: param(),
      type: "",
      buffer: null,
      connect: (x: unknown) => x,
      start() {},
      stop() {},
    };
    return n;
  };
  const ctx = {
    state: "suspended",
    currentTime: 0,
    sampleRate: 8000,
    destination: {},
    resumed: 0,
    resume() {
      this.resumed++;
      this.state = "running";
      return Promise.resolve();
    },
    createGain: () => node("gain"),
    createOscillator: () => node("osc"),
    createBiquadFilter: () => node("filter"),
    createBufferSource: () => node("source"),
    createBuffer: (_c: number, len: number) => ({ getChannelData: () => new Float32Array(len) }),
  };
  return { ctx, created };
}

describe("sound settings", () => {
  it("defaults to the IMMERSIVE preset", () => {
    assert.equal(DEFAULT_SOUND.preset, "immersive");
    assert.equal(DEFAULT_SOUND.categories.typing, true);
  });
  it("balanced turns typing off; quiet keeps only alerts and JARVIS", () => {
    assert.equal(PRESETS.balanced.categories.typing, false);
    const quiet = applyPreset(DEFAULT_SOUND, "quiet");
    assert.equal(gainFor(quiet, "navigation"), 0);
    assert.equal(gainFor(quiet, "notification"), 0);
    assert.ok(gainFor(quiet, "urgent") > 0);
    assert.ok(gainFor(quiet, "jarvisOn") > 0);
  });
  it("mute and category switches silence only what they control", () => {
    assert.equal(gainFor({ ...DEFAULT_SOUND, muted: true }, "urgent"), 0);
    const noNotes = {
      ...DEFAULT_SOUND,
      categories: { ...DEFAULT_SOUND.categories, notification: false },
    };
    assert.equal(gainFor(noNotes, "message"), 0);
    assert.ok(gainFor(noNotes, "approval") > 0);
    const busOff = { ...DEFAULT_SOUND, volumes: { ...DEFAULT_SOUND.volumes, jarvis: 0 } };
    assert.equal(gainFor(busOff, "jarvisOn"), 0);
    assert.ok(gainFor(busOff, "navigation") > 0);
  });
  it("parses stored settings defensively", () => {
    const parsed = parseSound({
      preset: "bogus",
      master: 7,
      volumes: { interface: -1 },
      categories: { typing: "yes" },
    });
    assert.equal(parsed.preset, "immersive");
    assert.equal(parsed.master, 1);
    assert.equal(parsed.volumes.interface, 0);
    assert.equal(parsed.categories.typing, true);
  });
  it("every event has a recipe category and bus", () => {
    for (const e of Object.values(EVENTS)) assert.ok(e.category && e.bus && e.label);
  });
});

describe("sound engine", () => {
  it("plays nothing before a user gesture unlocks audio", () => {
    const { ctx } = fakeContext();
    const engine = new SoundEngine(DEFAULT_SOUND, () => ctx as unknown as AudioContext);
    assert.equal(engine.play("notification"), false);
    assert.equal(engine.unlock(), true);
    assert.equal(ctx.resumed, 1);
    assert.equal(engine.play("notification"), true);
  });
  it("throttles typing to one tick per 90 ms", () => {
    const { ctx } = fakeContext();
    let t = 1000;
    const engine = new SoundEngine(
      DEFAULT_SOUND,
      () => ctx as unknown as AudioContext,
      () => t,
    );
    engine.unlock();
    assert.equal(engine.play("typing"), true);
    t += 40;
    assert.equal(engine.play("typing"), false);
    t += 60;
    assert.equal(engine.play("typing"), true);
  });
  it("works silently when audio is unsupported", () => {
    const engine = new SoundEngine(DEFAULT_SOUND, () => {
      throw new Error("no audio");
    });
    assert.equal(engine.unlock(), false);
    assert.equal(engine.play("startup"), false);
    assert.equal(new SoundEngine(DEFAULT_SOUND, null).unlock(), false);
  });
  it("respects settings updates immediately", () => {
    const { ctx } = fakeContext();
    const engine = new SoundEngine(DEFAULT_SOUND, () => ctx as unknown as AudioContext);
    engine.unlock();
    engine.update({ ...DEFAULT_SOUND, muted: true });
    assert.equal(engine.play("approval"), false);
  });
});

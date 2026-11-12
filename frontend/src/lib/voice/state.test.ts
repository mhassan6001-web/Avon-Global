import assert from "node:assert/strict";
import { test } from "node:test";

import {
  micOpen,
  nextMic,
  permissionHelp,
  pickMimeType,
  type MicEvent,
  type MicState,
} from "./state";

function run(events: MicEvent[], armed = false, from: MicState = "off"): MicState {
  return events.reduce((s, e) => nextMic(s, e, armed), from);
}

test("push-to-talk: listen, process, then off when replies are not spoken", () => {
  assert.equal(run([{ type: "press" }]), "listening");
  assert.equal(run([{ type: "press" }, { type: "release" }]), "processing");
  assert.equal(
    run([{ type: "press" }, { type: "release" }, { type: "replied", speak: false }]),
    "off",
  );
});

test("spoken replies return to standby when the wake word is armed", () => {
  const s = run(
    [{ type: "arm" }, { type: "wake" }, { type: "timeout" }, { type: "replied", speak: true }],
    true,
  );
  assert.equal(s, "speaking");
  assert.equal(nextMic(s, { type: "spoken" }, true), "standby");
});

test("the wake word only triggers from standby", () => {
  assert.equal(run([{ type: "wake" }]), "off");
});

test("push-to-talk interrupts speech and stop always closes everything", () => {
  assert.equal(nextMic("speaking", { type: "press" }, false), "listening");
  for (const s of ["standby", "listening", "processing", "speaking"] as MicState[]) {
    assert.equal(nextMic(s, { type: "stop" }, true), "off");
  }
});

test("the stop control shows whenever the microphone is open", () => {
  assert.equal(micOpen("standby"), true);
  assert.equal(micOpen("listening"), true);
  assert.equal(micOpen("off"), false);
});

test("mime type and permission help", () => {
  assert.equal(
    pickMimeType((t) => t === "audio/mp4"),
    "audio/mp4",
  );
  assert.equal(
    pickMimeType(() => false),
    null,
  );
  assert.match(permissionHelp("Mozilla/5.0 Chrome/130 Safari/537"), /Chrome/);
  assert.match(permissionHelp("Mozilla/5.0 Version/18 Safari/605"), /Safari/);
});

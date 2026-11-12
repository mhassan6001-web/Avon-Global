import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { addNotice, socketUrl, soundFor, toNotice } from "./events";

describe("realtime events", () => {
  it("builds notices and ignores unknown events", () => {
    const n = toNotice(
      { type: "message.created", conversation_id: "c1", message_id: "m1", requires_ack: true },
      1,
    );
    assert.equal(n?.href, "/messages?c=c1");
    assert.match(n?.text ?? "", /acknowledgement/);
    assert.equal(toNotice({ type: "ready" }), null);
  });
  it("deduplicates and caps notices", () => {
    const a = { id: "a", text: "a", href: "/", at: 1 };
    const b = { id: "b", text: "b", href: "/", at: 2 };
    assert.deepEqual(
      addNotice(addNotice([a], b), a).map((x) => x.id),
      ["a", "b"],
    );
    assert.equal(addNotice([a, b], { ...a, id: "c" }, 2).length, 2);
  });
  it("chooses sounds and socket URLs", () => {
    assert.equal(soundFor({ type: "message.created" }), "message");
    assert.equal(soundFor({ type: "task.updated" }), null);
    assert.equal(
      socketUrl({ protocol: "https:", host: "app.example" }),
      "wss://app.example/api/v1/ws",
    );
    assert.equal(
      socketUrl({ protocol: "http:", host: "localhost:3000" }),
      "ws://localhost:3000/api/v1/ws",
    );
  });
});

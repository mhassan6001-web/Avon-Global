import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { countdown, KIND_LABEL, TENDER_KINDS, TENDER_STATUS_LABEL, TENDER_STATUSES } from "./types";

describe("tender helpers", () => {
  const now = Date.parse("2026-11-12T12:00:00Z");
  it("describes deadlines with urgency", () => {
    assert.deepEqual(countdown("2026-11-22T12:00:00Z", now), {
      text: "10 days left",
      tone: "neutral",
    });
    assert.deepEqual(countdown("2026-11-17T12:00:00Z", now), {
      text: "5 days left",
      tone: "warning",
    });
    assert.deepEqual(countdown("2026-11-13T13:00:00Z", now), {
      text: "1 day left",
      tone: "danger",
    });
    assert.deepEqual(countdown("2026-11-12T17:00:00Z", now), {
      text: "5 hours left",
      tone: "danger",
    });
    assert.deepEqual(countdown("2026-11-12T12:30:00Z", now), {
      text: "Under an hour left",
      tone: "danger",
    });
    assert.deepEqual(countdown("2026-11-10T12:00:00Z", now), {
      text: "Closed 2 days ago",
      tone: "danger",
    });
  });
  it("labels every kind and status", () => {
    for (const k of TENDER_KINDS) assert.ok(KIND_LABEL[k]);
    for (const s of TENDER_STATUSES) assert.ok(TENDER_STATUS_LABEL[s]);
  });
});

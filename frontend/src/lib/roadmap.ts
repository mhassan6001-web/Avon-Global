/**
 * Delivery stages shown on the Command Centre. Mirrors ROADMAP.md, which
 * holds the Director's full stage list. Each stage ends with a test report
 * and stops for Director approval before the next begins.
 */

export type StageState = "approved" | "awaiting_approval" | "queued";

export interface Stage {
  number: number;
  title: string;
  state: StageState;
}

export const STAGES: Stage[] = [
  { number: 1, title: "Core infrastructure & application shell", state: "approved" },
  { number: 2, title: "Identity & security", state: "awaiting_approval" },
  { number: 3, title: "Visual experience & sound engine", state: "queued" },
  { number: 4, title: "Director Command Centre & CRM", state: "queued" },
  { number: 5, title: "Tender management", state: "queued" },
  { number: 6, title: "Procurement", state: "queued" },
];

export const TOTAL_STAGES = 15;

export const STAGE_STATE_LABEL: Record<StageState, string> = {
  approved: "Approved",
  awaiting_approval: "Plan awaiting approval",
  queued: "Queued",
};

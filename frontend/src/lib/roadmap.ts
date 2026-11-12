/**
 * Delivery stages shown on the Command Centre. Mirrors ROADMAP.md.
 * Director instruction (2026-11-12): Stages 3–15 run consecutively, each
 * verified in CI, with questions collected for one final review.
 */

export type StageState = "approved" | "verified" | "in_progress" | "awaiting_approval" | "queued";

export interface Stage {
  number: number;
  title: string;
  state: StageState;
}

export const STAGES: Stage[] = [
  { number: 1, title: "Core infrastructure & application shell", state: "approved" },
  { number: 2, title: "Identity & security", state: "approved" },
  { number: 3, title: "Visual experience & sound engine", state: "verified" },
  { number: 4, title: "Director Command Centre & CRM", state: "verified" },
  { number: 5, title: "Tender management", state: "verified" },
  { number: 6, title: "Procurement & suppliers", state: "in_progress" },
  { number: 7, title: "Finance & accounting", state: "queued" },
  { number: 8, title: "Inventory & logistics", state: "queued" },
  { number: 9, title: "HR & payroll", state: "queued" },
  { number: 10, title: "Staff communications", state: "queued" },
  { number: 11, title: "JARVIS AI core", state: "queued" },
  { number: 12, title: "Voice interface", state: "queued" },
  { number: 13, title: "Documents & integrations", state: "queued" },
  { number: 14, title: "Production readiness", state: "queued" },
  { number: 15, title: "Mobile & installable app", state: "queued" },
];

export const TOTAL_STAGES = 15;

export const STAGE_STATE_LABEL: Record<StageState, string> = {
  approved: "Approved",
  verified: "Verified in CI",
  in_progress: "In progress",
  awaiting_approval: "Awaiting approval",
  queued: "Queued",
};

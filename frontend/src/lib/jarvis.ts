/** JARVIS client model (pure): API shapes and the live control-chain reducer. */

import type { ActionStep, StepStatus } from "@/components/jarvis/TaskFlow";

export interface JarvisStatus {
  can_use: boolean;
  ai_configured: boolean;
  provider: string | null;
  tools: { name: string; category: string; description: string }[];
}

export interface JarvisAction {
  id: string;
  tool: string;
  summary: string;
  status: "proposed" | "executed" | "cancelled" | "failed" | "expired";
  error: string | null;
  result: Record<string, unknown> | null;
  expires_at: string;
  created_at: string;
}

export interface JarvisMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  tools_used: string[];
  actions: JarvisAction[];
  created_at: string;
}

export interface JarvisConversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface BriefingSection {
  key: string;
  title: string;
  lines: string[];
  empty: boolean;
  href: string | null;
}

export interface Briefing {
  generated_at: string;
  local_date: string;
  greeting: string;
  sections: BriefingSection[];
}

/** Backend gateway steps, in the order they can arrive. */
export type GatewayStep =
  | "interpreting"
  | "permission_ok"
  | "validated"
  | "awaiting_approval"
  | "executing"
  | "audited"
  | "failed";

export type Chain = Partial<Record<ActionStep, StepStatus>>;

const ORDER: ActionStep[] = [
  "authentication",
  "permission",
  "validation",
  "rules",
  "approval",
  "execution",
  "audit",
];

function upTo(done: ActionStep[], active?: ActionStep, skipped: ActionStep[] = []): Chain {
  const chain: Chain = {};
  for (const k of done) chain[k] = "done";
  for (const k of skipped) chain[k] = "skipped";
  if (active) chain[active] = "active";
  return chain;
}

/**
 * Advance the control chain for one real backend event. The chain never runs
 * ahead of the event: e.g. "audit" turns done only on "audited".
 */
export function applyStep(chain: Chain, step: GatewayStep): Chain {
  switch (step) {
    case "interpreting":
      return upTo(["authentication"], "permission");
    case "permission_ok":
      return upTo(["authentication", "permission"], "validation");
    case "validated":
      return upTo(["authentication", "permission", "validation"], "rules");
    case "awaiting_approval":
      return upTo(["authentication", "permission", "validation", "rules"], "approval");
    case "executing":
      return upTo(["authentication", "permission", "validation", "rules", "approval"], "execution");
    case "audited": {
      // A read finishes without an approval step; a confirmed action has one.
      const approved = chain.approval === "done" || chain.execution === "active";
      return approved
        ? upTo([...ORDER])
        : upTo(
            ["authentication", "permission", "validation", "rules", "execution", "audit"],
            undefined,
            ["approval"],
          );
    }
    case "failed": {
      const next: Chain = { ...chain };
      const active = ORDER.find((k) => next[k] === "active") ?? "permission";
      next[active] = "blocked";
      return next;
    }
    default:
      return chain;
  }
}

/** Plain-language tool name for the interface. */
export function toolLabel(name: string): string {
  return name.replace(/^prepare_/, "prepare ").replace(/_/g, " ");
}

/** Tender types, labels and deadline helpers (mirror backend schemas). */

import type { Division, Page, UserRef } from "@/lib/crm/types";

export type { Page };

export const TENDER_KINDS = ["rfq", "rfp", "eoi", "itb", "other"] as const;
export type TenderKind = (typeof TENDER_KINDS)[number];
export const METHODS = ["portal", "email", "physical", "other"] as const;
export const TENDER_STATUSES = [
  "identified",
  "reviewing",
  "bidding",
  "awaiting_approval",
  "approved",
  "submitted",
  "won",
  "lost",
  "no_bid",
  "cancelled",
] as const;
export type TenderStatus = (typeof TENDER_STATUSES)[number];
export const ACTIVE_STATUSES: readonly TenderStatus[] = [
  "identified",
  "reviewing",
  "bidding",
  "awaiting_approval",
  "approved",
];
export const REQUIREMENT_KINDS = ["eligibility", "document", "technical", "financial"] as const;
export const REQUIREMENT_STATUSES = ["pending", "met", "not_met", "not_applicable"] as const;
export type RequirementStatus = (typeof REQUIREMENT_STATUSES)[number];

export const KIND_LABEL: Record<TenderKind, string> = {
  rfq: "RFQ",
  rfp: "RFP",
  eoi: "EOI",
  itb: "ITB",
  other: "Other",
};
export const TENDER_STATUS_LABEL: Record<TenderStatus, string> = {
  identified: "Identified",
  reviewing: "Reviewing",
  bidding: "Preparing bid",
  awaiting_approval: "Awaiting approval",
  approved: "Approved to submit",
  submitted: "Submitted",
  won: "Won",
  lost: "Lost",
  no_bid: "No bid",
  cancelled: "Cancelled",
};
export const REQUIREMENT_STATUS_LABEL: Record<RequirementStatus, string> = {
  pending: "Pending",
  met: "Met",
  not_met: "Not met",
  not_applicable: "Not applicable",
};
export const METHOD_LABEL: Record<(typeof METHODS)[number], string> = {
  portal: "Online portal",
  email: "Email",
  physical: "Hand delivery",
  other: "Other",
};

export interface Tender {
  id: string;
  reference: string;
  issuer_reference: string | null;
  title: string;
  issuer_name: string;
  customer_id: string | null;
  kind: TenderKind;
  division: Division | null;
  country_code: string;
  source: string | null;
  published_on: string | null;
  clarification_deadline: string | null;
  submission_deadline: string;
  submission_method: (typeof METHODS)[number];
  bid_security_required: boolean;
  estimated_value: string | null;
  currency: string;
  status: TenderStatus;
  notes: string | null;
  approval_id: string | null;
  submitted_at: string | null;
  submitted_by: UserRef | null;
  award_value: string | null;
  outcome_note: string | null;
  owner: UserRef | null;
  requirements_total: number;
  requirements_open: number;
}

export interface Requirement {
  id: string;
  tender_id: string;
  kind: (typeof REQUIREMENT_KINDS)[number];
  description: string;
  mandatory: boolean;
  status: RequirementStatus;
  file_id: string | null;
  notes: string | null;
}

export interface TenderDetail {
  tender: Tender;
  requirements: Requirement[];
  approval: {
    id: string;
    status: string;
    requested_by: string;
    decided_by: string | null;
    decided_at: string | null;
    decision_note: string | null;
  } | null;
}

export interface TenderSummary {
  has_records: boolean;
  by_status: Partial<Record<TenderStatus, number>>;
  active: number;
  due_within_7_days: number;
  overdue_unsubmitted: number;
  decided: number;
  won: number;
}

/** Human countdown to a deadline: "3 days left", "5 hours left", "Closed 2 days ago". */
export function countdown(
  deadline: string,
  now = Date.now(),
): { text: string; tone: "danger" | "warning" | "neutral" } {
  const ms = new Date(deadline).getTime() - now;
  const abs = Math.abs(ms);
  const hours = Math.floor(abs / 3_600_000);
  const days = Math.floor(hours / 24);
  const span =
    days >= 1
      ? `${days} day${days === 1 ? "" : "s"}`
      : `${Math.max(hours, 0)} hour${hours === 1 ? "" : "s"}`;
  if (ms < 0) return { text: `Closed ${span} ago`, tone: "danger" };
  if (days < 3)
    return {
      text: `${days >= 1 ? span : hours < 1 ? "Under an hour" : span} left`,
      tone: "danger",
    };
  if (days < 7) return { text: `${span} left`, tone: "warning" };
  return { text: `${span} left`, tone: "neutral" };
}

export function formatDateTime(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

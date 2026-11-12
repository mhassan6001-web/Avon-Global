/** CRM types and labels shared by the CRM screens (mirrors backend schemas). */

export interface UserRef {
  id: string;
  display_name: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export const CUSTOMER_STATUSES = ["prospect", "active", "inactive", "archived"] as const;
export type CustomerStatus = (typeof CUSTOMER_STATUSES)[number];
export const CUSTOMER_KINDS = ["organisation", "government", "ngo", "individual"] as const;
export type CustomerKind = (typeof CUSTOMER_KINDS)[number];

export const STAGES = ["lead", "qualified", "proposal", "negotiation", "won", "lost"] as const;
export type Stage = (typeof STAGES)[number];
export const OPEN_STAGES: readonly Stage[] = ["lead", "qualified", "proposal", "negotiation"];

export const DIVISIONS = [
  "general_supplies",
  "technologies",
  "industrial_construction",
  "medical_pharmaceuticals",
  "international_trade",
  "logistics_distribution",
] as const;
export type Division = (typeof DIVISIONS)[number];

export const CURRENCIES = ["MWK", "USD", "ZAR", "ZMW"] as const;
export const ACTIVITY_KINDS = ["meeting", "call", "email", "note", "follow_up"] as const;
export type ActivityKind = (typeof ACTIVITY_KINDS)[number];

export const COUNTRIES: ReadonlyArray<{ value: string; label: string }> = [
  { value: "MW", label: "Malawi" },
  { value: "ZA", label: "South Africa" },
  { value: "ZM", label: "Zambia" },
  { value: "MZ", label: "Mozambique" },
  { value: "TZ", label: "Tanzania" },
  { value: "ZW", label: "Zimbabwe" },
];

export const STATUS_LABEL: Record<CustomerStatus, string> = {
  prospect: "Prospect",
  active: "Active",
  inactive: "Inactive",
  archived: "Archived",
};
export const KIND_LABEL: Record<CustomerKind, string> = {
  organisation: "Company",
  government: "Government",
  ngo: "NGO",
  individual: "Individual",
};
export const STAGE_LABEL: Record<Stage, string> = {
  lead: "Lead",
  qualified: "Qualified",
  proposal: "Proposal",
  negotiation: "Negotiation",
  won: "Won",
  lost: "Lost",
};
export const DIVISION_LABEL: Record<Division, string> = {
  general_supplies: "General Supplies",
  technologies: "Technologies",
  industrial_construction: "Industrial & Construction",
  medical_pharmaceuticals: "Medical & Pharmaceuticals",
  international_trade: "International Trade",
  logistics_distribution: "Logistics & Distribution",
};
export const ACTIVITY_LABEL: Record<ActivityKind, string> = {
  meeting: "Meeting",
  call: "Call",
  email: "Email",
  note: "Note",
  follow_up: "Follow-up",
};

export interface Customer {
  id: string;
  reference: string;
  name: string;
  kind: CustomerKind;
  status: CustomerStatus;
  country_code: string;
  city: string | null;
  industry: string | null;
  email: string | null;
  phone: string | null;
  notes: string | null;
  owner: UserRef | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  open_opportunities: number;
}

export interface Contact {
  id: string;
  customer_id: string;
  name: string;
  job_title: string | null;
  email: string | null;
  phone: string | null;
  is_primary: boolean;
}

export interface Opportunity {
  id: string;
  reference: string;
  customer_id: string;
  customer_name: string;
  title: string;
  division: Division;
  stage: Stage;
  value_amount: string | null;
  currency: string;
  probability: number;
  expected_close: string | null;
  lost_reason: string | null;
  closed_at: string | null;
  owner: UserRef | null;
  is_demo: boolean;
}

export interface Activity {
  id: string;
  customer_id: string;
  customer_name: string;
  opportunity_id: string | null;
  kind: ActivityKind;
  subject: string;
  body: string | null;
  occurred_at: string | null;
  due_at: string | null;
  completed_at: string | null;
  assigned_to: UserRef | null;
  created_by: UserRef | null;
  created_at: string;
}

export interface CustomerDetail {
  customer: Customer;
  contacts: Contact[];
  opportunities: Opportunity[];
  activities: Activity[];
}

export interface CrmSummary {
  has_records: boolean;
  customers_by_status: Partial<Record<CustomerStatus, number>>;
  pipeline: Array<{ stage: Stage; count: number; value_by_currency: Record<string, string> }>;
  follow_ups_overdue: number;
  follow_ups_due_7_days: number;
}

/** Format a decimal string amount without floating-point loss in the integer part. */
export function formatMoney(amount: string | null, currency: string): string {
  if (amount === null) return "—";
  const [whole = "0", fraction = "00"] = amount.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${currency} ${grouped}.${fraction.padEnd(2, "0").slice(0, 2)}`;
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

/** True if a follow-up is open and its due time has passed. */
export function isOverdue(
  activity: Pick<Activity, "due_at" | "completed_at">,
  now = Date.now(),
): boolean {
  return !activity.completed_at && !!activity.due_at && new Date(activity.due_at).getTime() < now;
}

/** Build a query string, skipping empty values. */
export function query(
  params: Record<string, string | number | boolean | null | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "" || value === false) continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

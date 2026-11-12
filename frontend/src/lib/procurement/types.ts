/** Procurement types and pure helpers (mirror backend schemas). */

import type { Page, UserRef } from "@/lib/crm/types";

export type { Page };

export const SUPPLIER_STATUSES = ["unverified", "verified", "suspended"] as const;
export type SupplierStatus = (typeof SUPPLIER_STATUSES)[number];

export interface Supplier {
  id: string;
  reference: string;
  name: string;
  country_code: string;
  city: string | null;
  categories: string | null;
  contact_name: string | null;
  email: string | null;
  phone: string | null;
  registration_number: string | null;
  tax_number: string | null;
  status: SupplierStatus;
  verified_by: UserRef | null;
  verified_at: string | null;
  verification_note: string | null;
  notes: string | null;
  has_active_bank_account: boolean;
  pending_bank_change: boolean;
}

export interface BankAccount {
  id: string;
  bank_name: string;
  account_last4: string;
  currency: string;
  status: "pending" | "active" | "superseded" | "rejected";
  reason: string;
  requested_by: string;
  created_at: string;
  account_name?: string;
  account_number?: string;
  branch?: string | null;
  swift?: string | null;
}

export interface SupplierDetail {
  supplier: Supplier;
  bank_accounts: BankAccount[];
  bank_details_visible: boolean;
}

export interface RequestLine {
  id: string;
  line_no: number;
  description: string;
  quantity: string;
  unit: string;
}

export interface Quote {
  id: string;
  supplier_id: string;
  supplier_name: string;
  supplier_status: SupplierStatus;
  supplier_reference: string | null;
  currency: string;
  valid_until: string | null;
  lead_time_days: number | null;
  delivery_terms: string | null;
  total: string;
  complete: boolean;
  expired: boolean;
  prices: Record<string, string>;
}

export const REQUEST_STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  awaiting_approval: "Awaiting approval",
  approved: "Approved",
  rejected: "Rejected",
  ordered: "Ordered",
  cancelled: "Cancelled",
};

export interface PurchaseRequest {
  id: string;
  reference: string;
  title: string;
  justification: string | null;
  division: string | null;
  needed_by: string | null;
  currency: string;
  status: keyof typeof REQUEST_STATUS_LABEL;
  selected_quote_id: string | null;
  approval_id: string | null;
  requested_by: UserRef | null;
  created_at: string;
  order_id: string | null;
}

export interface PurchaseRequestDetail {
  request: PurchaseRequest;
  lines: RequestLine[];
  quotes: Quote[];
  cheapest_complete_quote_id: string | null;
  comparison_note: string;
}

export interface PurchaseOrder {
  id: string;
  reference: string;
  request_id: string;
  request_reference: string;
  supplier_id: string;
  supplier_name: string;
  currency: string;
  total_amount: string;
  status: string;
  delivery_address: string | null;
  expected_delivery: string | null;
  cancel_reason: string | null;
  issued_by: UserRef | null;
  created_at: string;
  lines: Array<{
    line_no: number;
    description: string;
    quantity: string;
    unit: string;
    unit_price: string;
    line_total: string;
    received_quantity: string;
  }>;
}

export interface LandedCostResult {
  functional_currency: string;
  customs_value: string;
  duty: string;
  excise: string;
  vat: string;
  local_charges: string;
  landed_cost: string;
  unit_cost: string | null;
  vat_included_in_cost: boolean;
  exchange_rate: string;
  exchange_rate_source: string;
  note: string;
}

/** True if a string is a non-negative decimal with at most ``places`` decimals. */
export function isDecimal(value: string, places = 2): boolean {
  return new RegExp(`^\\d{1,16}(\\.\\d{1,${places}})?$`).test(value.trim());
}

/** Mask everything except the last four characters of an account number. */
export function maskAccount(last4: string): string {
  return `•••• ${last4}`;
}

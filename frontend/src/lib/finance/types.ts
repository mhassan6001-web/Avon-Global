/** Finance types and pure helpers (mirror backend schemas). Money stays a decimal string. */

export interface Account {
  id: string;
  code: string;
  name: string;
  type: "asset" | "liability" | "equity" | "income" | "expense";
  subtype: string;
  currency: string | null;
  is_active: boolean;
}

export const SUBTYPES: ReadonlyArray<{ value: string; label: string }> = [
  { value: "bank", label: "Bank or cash" },
  { value: "receivable", label: "Debtors control" },
  { value: "payable", label: "Creditors control" },
  { value: "tax", label: "Tax (VAT etc.)" },
  { value: "inventory", label: "Inventory" },
  { value: "fixed_asset", label: "Fixed asset" },
  { value: "other_asset", label: "Other asset" },
  { value: "other_liability", label: "Other liability" },
  { value: "equity", label: "Equity" },
  { value: "retained_earnings", label: "Retained earnings" },
  { value: "revenue", label: "Revenue" },
  { value: "cost_of_sales", label: "Cost of sales" },
  { value: "expense", label: "Expense" },
  { value: "fx_gain_loss", label: "Exchange gain/loss" },
];

/** Minimal customer or supplier reference for finance pickers. */
export interface Party {
  id: string;
  name: string;
  reference: string;
}

export interface Settings {
  functional_currency: string;
  receivable_account_id: string | null;
  payable_account_id: string | null;
  fx_gain_loss_account_id: string | null;
  accountant_reviewed: boolean;
  ready_for_invoicing: boolean;
  ready_for_bills: boolean;
  missing: string[];
}

export interface DocLine {
  line_no: number;
  description: string;
  quantity: string;
  unit_price: string;
  account_id: string;
  tax_code_id: string | null;
  net: string;
  tax: string;
}

export interface Invoice {
  id: string;
  number: string | null;
  customer_id: string;
  customer_name: string;
  currency: string;
  fx_rate: string | null;
  issue_date: string;
  due_date: string;
  status: "draft" | "issued" | "partially_paid" | "paid" | "credited";
  subtotal: string;
  tax_total: string;
  total: string;
  amount_paid: string;
  amount_credited: string;
  outstanding: string;
  lines: DocLine[];
}

export interface Bill {
  id: string;
  number: string | null;
  supplier_id: string;
  supplier_name: string;
  supplier_invoice_ref: string;
  currency: string;
  bill_date: string;
  due_date: string;
  status: "draft" | "posted" | "partially_paid" | "paid";
  subtotal: string;
  tax_total: string;
  total: string;
  amount_paid: string;
  outstanding: string;
}

export interface Payment {
  id: string;
  number: string | null;
  bill_number: string | null;
  supplier_name: string;
  payee_account_ending: string | null;
  payment_date: string;
  currency: string;
  amount: string;
  method: string;
  status: "awaiting_approval" | "posted" | "rejected";
}

export interface Receipt {
  id: string;
  number: string;
  customer_name: string;
  receipt_date: string;
  currency: string;
  amount: string;
  method: string;
  reference: string | null;
}

export interface TaxCode {
  id: string;
  code: string;
  name: string;
  kind: "output" | "input";
  rate_pct: string;
  account_id: string;
  effective_from: string;
  effective_to: string | null;
}

export interface Period {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: "open" | "closed";
}

export interface Rate {
  id: string;
  currency: string;
  rate_date: string;
  rate: string;
  source: string;
}

export interface JournalLine {
  line_no: number;
  account_code: string;
  account_name: string;
  description: string | null;
  currency: string;
  amount: string;
  debit: string;
  credit: string;
}

export interface Journal {
  id: string;
  number: string | null;
  entry_date: string;
  description: string;
  source_type: string;
  status: string;
  reversed_by_id: string | null;
  lines: JournalLine[];
}

export interface ReportRow {
  account_id: string;
  code: string;
  name: string;
  type: string;
  debit: string;
  credit: string;
  balance: string;
}

export interface Overview {
  has_records: boolean;
  functional_currency: string;
  cash_position: string;
  invoiced_this_month: string;
  collected_this_month: string;
  debtors_outstanding: string;
  creditors_outstanding: string;
  months: Array<{ month: string; invoiced: string; collected: string }>;
  revenue_by_division: Record<string, string>;
}

export const DOC_STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  issued: "Issued",
  posted: "Posted",
  partially_paid: "Part paid",
  paid: "Paid",
  credited: "Credited",
  awaiting_approval: "Awaiting approval",
  rejected: "Rejected",
  reversed: "Reversed",
};

/** Sum decimal strings exactly (as integer cents). */
export function sumMoney(values: string[]): string {
  let cents = 0n;
  for (const v of values) {
    const negative = v.trim().startsWith("-");
    const [whole = "0", fraction = ""] = v.replace("-", "").split(".");
    const c = BigInt(whole || "0") * 100n + BigInt((fraction + "00").slice(0, 2));
    cents += negative ? -c : c;
  }
  const sign = cents < 0n ? "-" : "";
  const abs = cents < 0n ? -cents : cents;
  return `${sign}${abs / 100n}.${String(abs % 100n).padStart(2, "0")}`;
}

/** Days a document is past due on ``today`` (0 if not yet due). */
export function daysOverdue(due: string, today: Date = new Date()): number {
  const d = new Date(`${due}T00:00:00`);
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.max(0, Math.round((t.getTime() - d.getTime()) / 86_400_000));
}

export function isoToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

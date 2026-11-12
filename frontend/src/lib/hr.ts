/** HR types (mirror backend schemas). */

export interface Employee {
  id: string;
  employee_no: string;
  user_id: string | null;
  full_name: string;
  job_title: string;
  department_code: string;
  employment_type: string;
  start_date: string;
  status: string;
  leave_days_per_year: string;
}

export interface Leave {
  id: string;
  employee_id: string;
  employee_name: string;
  kind: string;
  start_date: string;
  end_date: string;
  days: string;
  reason: string | null;
  status: "pending" | "approved" | "rejected" | "cancelled";
  decision_note: string | null;
}

export interface Balance {
  year: number;
  entitlement: string;
  taken: string;
  pending: string;
  remaining: string;
}

export interface Kpi {
  id: string;
  title: string;
  target: string;
  period: string;
  actual: string | null;
  status: string;
  employee_agreed_at: string | null;
}

export interface Review {
  id: string;
  period: string;
  rating: number;
  strengths: string;
  improvements: string;
  employee_comment: string | null;
  acknowledged_at: string | null;
}

export interface Payslip {
  id: string;
  employee_no: string;
  employee_name: string;
  period: string;
  gross: string;
  deductions: string;
  net: string;
  lines: Array<{ code: string; name: string; kind: string; amount: string }>;
}

export interface Run {
  id: string;
  period: string;
  currency: string;
  status: string;
  total_gross: string;
  total_deductions: string;
  total_net: string;
  payslips: Payslip[];
}

export interface MyHr {
  employee: Employee;
  leave: Leave[];
  leave_balance: Balance;
  kpis: Kpi[];
  reviews: Review[];
  payslips: Payslip[];
}

export const LEAVE_KINDS = [
  "annual",
  "sick",
  "maternity",
  "paternity",
  "compassionate",
  "study",
  "unpaid",
] as const;

/** Calendar days from start to end inclusive (dates as YYYY-MM-DD). */
export function inclusiveDays(start: string, end: string): number {
  const a = Date.parse(`${start}T00:00:00Z`);
  const b = Date.parse(`${end}T00:00:00Z`);
  if (Number.isNaN(a) || Number.isNaN(b) || b < a) return 0;
  return Math.round((b - a) / 86_400_000) + 1;
}

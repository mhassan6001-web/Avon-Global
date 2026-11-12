"use client";

import { useState } from "react";

import styles from "@/components/crm/crm.module.css";
import { FinanceNav } from "@/components/finance/FinanceNav";
import {
  Badge,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SegmentedControl,
  TextField,
} from "@/components/ui";
import { useResource } from "@/lib/api/useResource";
import { formatMoney, query } from "@/lib/crm/types";
import { isoToday, type ReportRow } from "@/lib/finance/types";

import page from "@/app/pages.module.css";

const VIEWS = [
  { value: "tb", label: "Trial balance" },
  { value: "pl", label: "Profit & loss" },
  { value: "bs", label: "Balance sheet" },
  { value: "ar", label: "Debtors ageing" },
  { value: "ap", label: "Creditors ageing" },
] as const;
type View = (typeof VIEWS)[number]["value"];

interface TB {
  functional_currency: string;
  rows: ReportRow[];
  total_debit: string;
  total_credit: string;
  balanced: boolean;
}
interface PL {
  functional_currency: string;
  income: ReportRow[];
  expenses: ReportRow[];
  total_income: string;
  total_expenses: string;
  net_profit: string;
  basis: string;
}
interface BS {
  functional_currency: string;
  assets: ReportRow[];
  liabilities: ReportRow[];
  equity: ReportRow[];
  current_earnings: string;
  total_assets: string;
  total_liabilities_and_equity: string;
  balanced: boolean;
}
interface Ageing {
  rows: Array<{
    party_id: string;
    party_name: string;
    currency: string;
    current: string;
    days_1_30: string;
    days_31_60: string;
    days_61_90: string;
    days_over_90: string;
    total: string;
  }>;
}

function Rows({ rows, ccy, title }: { rows: ReportRow[]; ccy: string; title: string }) {
  return (
    <>
      <tr>
        <th colSpan={2} scope="colgroup" className="hud-label">
          {title}
        </th>
      </tr>
      {rows.map((r) => (
        <tr key={r.account_id}>
          <td>
            {r.code} {r.name}
          </td>
          <td className="tabular" style={{ textAlign: "right" }}>
            {formatMoney(r.balance, ccy)}
          </td>
        </tr>
      ))}
    </>
  );
}

export default function ReportsPage() {
  const [view, setView] = useState<View>("tb");
  const year = isoToday().slice(0, 4);
  const [from, setFrom] = useState(`${year}-01-01`);
  const [to, setTo] = useState(isoToday());
  const tb = useResource<TB>(
    view === "tb" ? `/finance/reports/trial-balance${query({ as_of: to })}` : null,
  );
  const pl = useResource<PL>(
    view === "pl"
      ? `/finance/reports/profit-and-loss${query({ date_from: from, date_to: to })}`
      : null,
  );
  const bs = useResource<BS>(
    view === "bs" ? `/finance/reports/balance-sheet${query({ as_of: to })}` : null,
  );
  const ag = useResource<Ageing>(
    view === "ar" || view === "ap"
      ? `/finance/reports/ageing${query({ kind: view === "ar" ? "receivable" : "payable", as_of: to })}`
      : null,
  );
  const error = tb.error ?? pl.error ?? bs.error ?? ag.error;

  return (
    <>
      <PageHeader
        eyebrow="Finance"
        title="Reports"
        description="Computed from posted journals only. Not audited and not reviewed by an accountant unless marked so in Setup."
      />
      <FinanceNav />
      <Panel title="Report">
        <div className={styles.toolbar}>
          <SegmentedControl label="Report" value={view} options={VIEWS} onChange={setView} />
          {view === "pl" && (
            <TextField
              label="From"
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
          )}
          <TextField
            label={view === "pl" ? "To" : "As of"}
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </div>
        <FormError message={error} />
        {view === "tb" &&
          tb.data &&
          (tb.data.rows.length === 0 ? (
            <EmptyState title="Nothing posted yet">
              The trial balance fills as transactions are posted.
            </EmptyState>
          ) : (
            <div className={page.tableWrap}>
              <table className={page.table}>
                <thead>
                  <tr>
                    <th scope="col">Account</th>
                    <th scope="col">Debit</th>
                    <th scope="col">Credit</th>
                  </tr>
                </thead>
                <tbody>
                  {tb.data.rows.map((r) => (
                    <tr key={r.account_id}>
                      <td>
                        {r.code} {r.name}
                      </td>
                      <td className="tabular">{r.debit}</td>
                      <td className="tabular">{r.credit}</td>
                    </tr>
                  ))}
                  <tr>
                    <th scope="row">
                      Totals{" "}
                      <Badge tone={tb.data.balanced ? "success" : "danger"}>
                        {tb.data.balanced ? "Balanced" : "Out of balance"}
                      </Badge>
                    </th>
                    <td className={styles.amount}>{tb.data.total_debit}</td>
                    <td className={styles.amount}>{tb.data.total_credit}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
        {view === "pl" && pl.data && (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <tbody>
                <Rows rows={pl.data.income} ccy={pl.data.functional_currency} title="Income" />
                <tr>
                  <th scope="row">Total income</th>
                  <td className={styles.amount} style={{ textAlign: "right" }}>
                    {formatMoney(pl.data.total_income, pl.data.functional_currency)}
                  </td>
                </tr>
                <Rows rows={pl.data.expenses} ccy={pl.data.functional_currency} title="Expenses" />
                <tr>
                  <th scope="row">Total expenses</th>
                  <td className={styles.amount} style={{ textAlign: "right" }}>
                    {formatMoney(pl.data.total_expenses, pl.data.functional_currency)}
                  </td>
                </tr>
                <tr>
                  <th scope="row">Net profit</th>
                  <td className={styles.amount} style={{ textAlign: "right" }}>
                    {formatMoney(pl.data.net_profit, pl.data.functional_currency)}
                  </td>
                </tr>
              </tbody>
            </table>
            <p className={page.note}>{pl.data.basis}</p>
          </div>
        )}
        {view === "bs" && bs.data && (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <tbody>
                <Rows rows={bs.data.assets} ccy={bs.data.functional_currency} title="Assets" />
                <tr>
                  <th scope="row">Total assets</th>
                  <td className={styles.amount} style={{ textAlign: "right" }}>
                    {formatMoney(bs.data.total_assets, bs.data.functional_currency)}
                  </td>
                </tr>
                <Rows
                  rows={bs.data.liabilities}
                  ccy={bs.data.functional_currency}
                  title="Liabilities"
                />
                <Rows rows={bs.data.equity} ccy={bs.data.functional_currency} title="Equity" />
                <tr>
                  <td>Current earnings (not yet closed to retained earnings)</td>
                  <td className="tabular" style={{ textAlign: "right" }}>
                    {formatMoney(bs.data.current_earnings, bs.data.functional_currency)}
                  </td>
                </tr>
                <tr>
                  <th scope="row">
                    Liabilities and equity{" "}
                    <Badge tone={bs.data.balanced ? "success" : "danger"}>
                      {bs.data.balanced ? "Balanced" : "Out of balance"}
                    </Badge>
                  </th>
                  <td className={styles.amount} style={{ textAlign: "right" }}>
                    {formatMoney(bs.data.total_liabilities_and_equity, bs.data.functional_currency)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
        {(view === "ar" || view === "ap") &&
          ag.data &&
          (ag.data.rows.length === 0 ? (
            <EmptyState title="Nothing outstanding">
              No open {view === "ar" ? "invoices" : "bills"} on this date.
            </EmptyState>
          ) : (
            <div className={page.tableWrap}>
              <table className={page.table}>
                <thead>
                  <tr>
                    <th scope="col">{view === "ar" ? "Customer" : "Supplier"}</th>
                    <th scope="col">Not due</th>
                    <th scope="col">1–30</th>
                    <th scope="col">31–60</th>
                    <th scope="col">61–90</th>
                    <th scope="col">90+</th>
                    <th scope="col">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {ag.data.rows.map((r) => (
                    <tr key={`${r.party_id}-${r.currency}`}>
                      <td>
                        {r.party_name} <span className={styles.ref}>{r.currency}</span>
                      </td>
                      {[r.current, r.days_1_30, r.days_31_60, r.days_61_90, r.days_over_90].map(
                        (v, i) => (
                          <td
                            key={i}
                            className={
                              i >= 3 && v !== "0" && v !== "0.00" ? styles.overdue : "tabular"
                            }
                          >
                            {v}
                          </td>
                        ),
                      )}
                      <td className={styles.amount}>{formatMoney(r.total, r.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </Panel>
    </>
  );
}

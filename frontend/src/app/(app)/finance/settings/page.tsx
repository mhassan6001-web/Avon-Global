"use client";

import { useState } from "react";

import styles from "@/components/crm/crm.module.css";
import { FinanceNav } from "@/components/finance/FinanceNav";
import {
  Badge,
  Button,
  FormError,
  PageHeader,
  Panel,
  SelectField,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useStepUp } from "@/lib/auth/StepUpProvider";
import { CURRENCIES, formatDate } from "@/lib/crm/types";
import {
  isoToday,
  SUBTYPES,
  type Account,
  type Period,
  type Rate,
  type Settings,
  type TaxCode,
} from "@/lib/finance/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

export default function FinanceSetupPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const withStepUp = useStepUp();
  const settings = useResource<Settings>("/finance/settings");
  const accounts = useResource<Account[]>("/finance/accounts?include_inactive=true");
  const periods = useResource<Period[]>("/finance/periods");
  const rates = useResource<Rate[]>("/finance/exchange-rates");
  const taxes = useResource<TaxCode[]>("/finance/tax-codes");
  const [error, setError] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [acc, setAcc] = useState({ code: "", name: "", subtype: "expense", currency: "" });
  const [per, setPer] = useState({ name: "", start_date: "", end_date: "" });
  const [rate, setRate] = useState({
    currency: "USD",
    rate_date: isoToday(),
    rate: "",
    source: "",
  });
  const [tax, setTax] = useState({
    code: "",
    name: "",
    kind: "output",
    rate_pct: "",
    account_id: "",
    effective_from: isoToday(),
  });
  const editable = can("finance.records.edit");
  const all = accounts.data ?? [];
  const pick = (subtype: string) => [
    { value: "", label: "Not set" },
    ...all
      .filter((a) => a.subtype === subtype && a.is_active)
      .map((a) => ({ value: a.id, label: `${a.code} ${a.name}` })),
  ];

  async function act(fn: () => Promise<unknown>, reload: () => Promise<void>) {
    setError(null);
    try {
      await fn();
      play("complete");
      await Promise.all([reload(), settings.reload()]);
    } catch (e) {
      if (e && typeof e === "object" && "code" in e && (e as { code: string }).code === "cancelled")
        return;
      setError(errorMessage(e));
      play("warning");
    }
  }
  const s = settings.data;

  return (
    <>
      <PageHeader
        eyebrow="Finance"
        title="Finance setup"
        description="Chart of accounts, control accounts, periods, exchange rates and tax codes. Nothing is pre-loaded: enter your own, and have a qualified local accountant review them before live use."
        actions={
          s ? (
            <Badge tone={s.accountant_reviewed ? "success" : "warning"}>
              {s.accountant_reviewed ? "Accountant reviewed" : "Awaiting accountant review"}
            </Badge>
          ) : undefined
        }
      />
      <FinanceNav />
      <FormError message={error} />
      <div className={page.grid}>
        <div className={page.span6}>
          <Panel title="Control accounts">
            {s && (
              <form
                className={styles.dialogForm}
                style={{ minWidth: 0 }}
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const body = Object.fromEntries(
                    [...f.entries()].map(([k, v]) => [k, v === "" ? null : v]),
                  );
                  void act(() => send("PUT", "/finance/settings", { body }), accounts.reload);
                }}
              >
                <SelectField
                  name="receivable_account_id"
                  label="Debtors control"
                  defaultValue={s.receivable_account_id ?? ""}
                  options={pick("receivable")}
                  disabled={!editable}
                />
                <SelectField
                  name="payable_account_id"
                  label="Creditors control"
                  defaultValue={s.payable_account_id ?? ""}
                  options={pick("payable")}
                  disabled={!editable}
                />
                <SelectField
                  name="fx_gain_loss_account_id"
                  label="Exchange gain/loss"
                  defaultValue={s.fx_gain_loss_account_id ?? ""}
                  options={pick("fx_gain_loss")}
                  disabled={!editable}
                />
                {editable && (
                  <div className={styles.dialogActions}>
                    <Button type="submit" variant="primary">
                      Save control accounts
                    </Button>
                  </div>
                )}
              </form>
            )}
            {s && s.missing.length > 0 && (
              <p className={page.note}>Still needed: {s.missing.join(", ")}.</p>
            )}
            {can("finance.transaction.approve") && s && (
              <form
                className={styles.formGrid}
                style={{ marginTop: 16, alignItems: "end" }}
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(
                    () =>
                      withStepUp(() =>
                        send("POST", "/finance/settings/accountant-review", {
                          body: { reviewed: !s.accountant_reviewed, note: reviewNote },
                        }),
                      ),
                    settings.reload,
                  ).then(() => setReviewNote(""));
                }}
              >
                <TextField
                  label="Accountant's name and review date"
                  required
                  minLength={3}
                  value={reviewNote}
                  onChange={(e) => setReviewNote(e.target.value)}
                />
                <Button type="submit" size="sm">
                  {s.accountant_reviewed
                    ? "Withdraw accountant review"
                    : "Record accountant review"}
                </Button>
              </form>
            )}
          </Panel>
        </div>
        <div className={page.span6}>
          <Panel title="Financial periods">
            <ul className={styles.timeline}>
              {(periods.data ?? []).map((p) => (
                <li key={p.id} className={styles.timelineItem}>
                  <Badge tone={p.status === "open" ? "success" : "neutral"}>{p.status}</Badge>
                  <div>
                    <strong>{p.name}</strong>
                    <div className={page.muted}>
                      {formatDate(p.start_date)} – {formatDate(p.end_date)}
                    </div>
                  </div>
                  {p.status === "open" && can("finance.transaction.approve") ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        void act(
                          () => withStepUp(() => send("POST", `/finance/periods/${p.id}/close`)),
                          periods.reload,
                        )
                      }
                    >
                      Close
                    </Button>
                  ) : (
                    <span />
                  )}
                </li>
              ))}
            </ul>
            {editable && (
              <form
                className={styles.formGrid}
                style={{ marginTop: 16, alignItems: "end" }}
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(() => send("POST", "/finance/periods", { body: per }), periods.reload);
                }}
              >
                <TextField
                  label="Period name"
                  required
                  minLength={3}
                  placeholder="e.g. FY2027"
                  value={per.name}
                  onChange={(e) => setPer({ ...per, name: e.target.value })}
                />
                <TextField
                  label="Starts"
                  type="date"
                  required
                  value={per.start_date}
                  onChange={(e) => setPer({ ...per, start_date: e.target.value })}
                />
                <TextField
                  label="Ends"
                  type="date"
                  required
                  value={per.end_date}
                  onChange={(e) => setPer({ ...per, end_date: e.target.value })}
                />
                <Button type="submit">Add period</Button>
              </form>
            )}
          </Panel>
        </div>
        <div className={page.span12}>
          <Panel title="Chart of accounts">
            <div className={page.tableWrap}>
              <table className={page.table}>
                <thead>
                  <tr>
                    <th scope="col">Code</th>
                    <th scope="col">Name</th>
                    <th scope="col">Kind</th>
                    <th scope="col">Currency</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {all.map((a) => (
                    <tr key={a.id}>
                      <td className="tabular">{a.code}</td>
                      <td>{a.name}</td>
                      <td>{SUBTYPES.find((x) => x.value === a.subtype)?.label ?? a.subtype}</td>
                      <td>{a.currency ?? "Any"}</td>
                      <td>{a.is_active ? "Active" : "Inactive"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {editable && (
              <form
                className={styles.formGrid}
                style={{ marginTop: 16, alignItems: "end" }}
                onSubmit={(e) => {
                  e.preventDefault();
                  const body = { ...acc, ...(acc.currency ? {} : { currency: undefined }) };
                  void act(async () => {
                    await send("POST", "/finance/accounts", { body });
                    setAcc({ code: "", name: "", subtype: acc.subtype, currency: "" });
                  }, accounts.reload);
                }}
              >
                <TextField
                  label="Account code"
                  required
                  pattern="^[0-9A-Z.\-]{2,20}$"
                  value={acc.code}
                  onChange={(e) => setAcc({ ...acc, code: e.target.value.toUpperCase() })}
                />
                <TextField
                  label="Account name"
                  required
                  minLength={2}
                  value={acc.name}
                  onChange={(e) => setAcc({ ...acc, name: e.target.value })}
                />
                <SelectField
                  label="Kind"
                  value={acc.subtype}
                  onChange={(e) => setAcc({ ...acc, subtype: e.target.value })}
                  options={SUBTYPES}
                />
                <SelectField
                  label="Currency"
                  value={acc.currency}
                  onChange={(e) => setAcc({ ...acc, currency: e.target.value })}
                  options={[
                    { value: "", label: "Any" },
                    ...CURRENCIES.map((c) => ({ value: c, label: c })),
                  ]}
                />
                <Button type="submit">Add account</Button>
              </form>
            )}
          </Panel>
        </div>
        <div className={page.span6}>
          <Panel title="Exchange rates">
            <p className={page.note} style={{ marginTop: 0 }}>
              {s?.functional_currency ?? "MWK"} per 1 unit of the foreign currency. Rates are
              history: add a new one, never edit.
            </p>
            <ul className={styles.timeline}>
              {(rates.data ?? []).slice(0, 10).map((r) => (
                <li key={r.id} className={styles.timelineItem}>
                  <span className="tabular">{r.currency}</span>
                  <div>
                    {r.rate} on {formatDate(r.rate_date)}
                    <div className={page.muted}>{r.source}</div>
                  </div>
                  <span />
                </li>
              ))}
            </ul>
            {editable && (
              <form
                className={styles.formGrid}
                style={{ marginTop: 16, alignItems: "end" }}
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(
                    () => send("POST", "/finance/exchange-rates", { body: rate }),
                    rates.reload,
                  );
                }}
              >
                <SelectField
                  label="Rate currency"
                  value={rate.currency}
                  onChange={(e) => setRate({ ...rate, currency: e.target.value })}
                  options={CURRENCIES.filter((c) => c !== (s?.functional_currency ?? "MWK")).map(
                    (c) => ({ value: c, label: c }),
                  )}
                />
                <TextField
                  label="Rate date"
                  type="date"
                  required
                  value={rate.rate_date}
                  onChange={(e) => setRate({ ...rate, rate_date: e.target.value })}
                />
                <TextField
                  label="Rate"
                  required
                  inputMode="decimal"
                  pattern="^\d{1,12}(\.\d{1,6})?$"
                  value={rate.rate}
                  onChange={(e) => setRate({ ...rate, rate: e.target.value })}
                />
                <TextField
                  label="Source"
                  required
                  minLength={2}
                  placeholder="e.g. Reserve Bank, bank quote"
                  value={rate.source}
                  onChange={(e) => setRate({ ...rate, source: e.target.value })}
                />
                <Button type="submit">Add rate</Button>
              </form>
            )}
          </Panel>
        </div>
        <div className={page.span6}>
          <Panel title="Tax codes">
            <p className={page.note} style={{ marginTop: 0 }}>
              No tax rate is built into the system. Enter current rates and have them confirmed by
              your accountant.
            </p>
            <ul className={styles.timeline}>
              {(taxes.data ?? []).map((t) => (
                <li key={t.id} className={styles.timelineItem}>
                  <span className="tabular">{t.code}</span>
                  <div>
                    {t.name} · {Number(t.rate_pct)}% {t.kind}
                    <div className={page.muted}>
                      from {formatDate(t.effective_from)}
                      {t.effective_to ? ` to ${formatDate(t.effective_to)}` : ""}
                    </div>
                  </div>
                  <span />
                </li>
              ))}
            </ul>
            {editable && (
              <form
                className={styles.formGrid}
                style={{ marginTop: 16, alignItems: "end" }}
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(() => send("POST", "/finance/tax-codes", { body: tax }), taxes.reload);
                }}
              >
                <TextField
                  label="Tax code"
                  required
                  pattern="^[A-Z0-9_\-]{2,20}$"
                  value={tax.code}
                  onChange={(e) => setTax({ ...tax, code: e.target.value.toUpperCase() })}
                />
                <TextField
                  label="Tax name"
                  required
                  minLength={2}
                  value={tax.name}
                  onChange={(e) => setTax({ ...tax, name: e.target.value })}
                />
                <SelectField
                  label="Applies to"
                  value={tax.kind}
                  onChange={(e) => setTax({ ...tax, kind: e.target.value })}
                  options={[
                    { value: "output", label: "Sales (output)" },
                    { value: "input", label: "Purchases (input)" },
                  ]}
                />
                <TextField
                  label="Rate %"
                  required
                  inputMode="decimal"
                  pattern="^\d{1,3}(\.\d{1,3})?$"
                  value={tax.rate_pct}
                  onChange={(e) => setTax({ ...tax, rate_pct: e.target.value })}
                />
                <SelectField
                  label="Tax account"
                  required
                  value={tax.account_id}
                  onChange={(e) => setTax({ ...tax, account_id: e.target.value })}
                  options={pick("tax")}
                />
                <TextField
                  label="Effective from"
                  type="date"
                  required
                  value={tax.effective_from}
                  onChange={(e) => setTax({ ...tax, effective_from: e.target.value })}
                />
                <Button type="submit">Add tax code</Button>
              </form>
            )}
          </Panel>
        </div>
      </div>
    </>
  );
}

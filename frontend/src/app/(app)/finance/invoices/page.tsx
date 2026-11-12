"use client";

import { useMemo, useState } from "react";
import { LuPlus } from "react-icons/lu";

import { DocLinks } from "@/components/documents/DocLinks";
import styles from "@/components/crm/crm.module.css";
import { FinanceNav } from "@/components/finance/FinanceNav";
import { emptyLine, LineEditor, linesBody, type LineDraft } from "@/components/finance/LineEditor";
import {
  Badge,
  Button,
  Dialog,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SelectField,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { CURRENCIES, formatDate, formatMoney } from "@/lib/crm/types";
import {
  DOC_STATUS_LABEL,
  daysOverdue,
  isoToday,
  sumMoney,
  type Account,
  type Invoice,
  type Party,
  type Receipt,
  type TaxCode,
} from "@/lib/finance/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

type DialogKind = "invoice" | "receipt" | "credit" | null;

export default function InvoicesPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const invoices = useResource<Invoice[]>("/finance/invoices?limit=500");
  const receipts = useResource<Receipt[]>("/finance/receipts?limit=100");
  const accounts = useResource<Account[]>("/finance/accounts");
  const taxCodes = useResource<TaxCode[]>("/finance/tax-codes");
  const customers = useResource<Party[]>("/finance/parties?kind=customer");
  const [dialog, setDialog] = useState<DialogKind>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    customer_id: "",
    currency: "MWK",
    issue_date: isoToday(),
    due_date: isoToday(),
  });
  const [lines, setLines] = useState<LineDraft[]>([emptyLine()]);
  const [rc, setRc] = useState({
    customer_id: "",
    bank_account_id: "",
    method: "bank_transfer",
    receipt_date: isoToday(),
    reference: "",
    fx_rate: "",
  });
  const [alloc, setAlloc] = useState<Record<string, string>>({});
  const [cn, setCn] = useState({ invoice_id: "", amount: "", reason: "", credit_date: isoToday() });
  const editable = can("finance.records.edit");

  const revenue = (accounts.data ?? []).filter((a) => a.subtype === "revenue");
  const banks = (accounts.data ?? []).filter((a) => a.subtype === "bank");
  const outputTax = (taxCodes.data ?? []).filter((t) => t.kind === "output");
  const open = useMemo(
    () =>
      (invoices.data ?? []).filter(
        (i) =>
          (i.status === "issued" || i.status === "partially_paid") &&
          (!rc.customer_id || i.customer_id === rc.customer_id),
      ),
    [invoices.data, rc.customer_id],
  );
  const customerOptions = customers.data ?? [];

  async function act(fn: () => Promise<unknown>, cue: "complete" | "approval" = "complete") {
    setError(null);
    try {
      await fn();
      play(cue);
      setDialog(null);
      await Promise.all([invoices.reload(), receipts.reload()]);
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Finance"
        title="Sales invoices and receipts"
        description="Draft, then issue: issuing assigns the next invoice number and posts the journal. Issued invoices are corrected with credit notes, never edited."
        actions={
          editable ? (
            <div className={page.actionsRow} style={{ marginTop: 0 }}>
              <Button
                icon={<LuPlus aria-hidden="true" />}
                variant="primary"
                onClick={() => setDialog("invoice")}
              >
                New invoice
              </Button>
              <Button
                onClick={() => {
                  setAlloc({});
                  setDialog("receipt");
                }}
              >
                Record receipt
              </Button>
              <Button variant="ghost" onClick={() => setDialog("credit")}>
                Request credit note
              </Button>
            </div>
          ) : undefined
        }
      />
      <FinanceNav />
      <FormError message={error ?? invoices.error} />
      <Panel title="Invoices">
        {invoices.data && invoices.data.length === 0 ? (
          <EmptyState title="No invoices yet">
            Invoices are created for real customers from the CRM. Nothing is pre-filled.
          </EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Invoice</th>
                  <th scope="col">Customer</th>
                  <th scope="col">Issued</th>
                  <th scope="col">Due</th>
                  <th scope="col">Total</th>
                  <th scope="col">Outstanding</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {invoices.data?.map((i) => {
                  const late =
                    i.status !== "draft" && i.status !== "paid" && i.status !== "credited"
                      ? daysOverdue(i.due_date)
                      : 0;
                  return (
                    <tr key={i.id}>
                      <td>
                        <strong>{i.number ?? "Draft"}</strong>
                        <DocLinks
                          kind="invoice"
                          id={i.id}
                          label={`Invoice ${i.number ?? "draft"}`}
                        />
                        {i.status === "draft" && editable && (
                          <div>
                            <Button
                              size="sm"
                              variant="primary"
                              onClick={() =>
                                void act(() =>
                                  send("POST", `/finance/invoices/${i.id}/issue`, { body: {} }),
                                )
                              }
                            >
                              Issue
                            </Button>
                          </div>
                        )}
                      </td>
                      <td>{i.customer_name}</td>
                      <td>{formatDate(i.issue_date)}</td>
                      <td className={late ? styles.overdue : undefined}>
                        {formatDate(i.due_date)}
                        {late > 0 && ` · ${late} days late`}
                      </td>
                      <td className={styles.amount}>{formatMoney(i.total, i.currency)}</td>
                      <td className="tabular">{formatMoney(i.outstanding, i.currency)}</td>
                      <td>
                        <Badge
                          tone={
                            i.status === "paid"
                              ? "success"
                              : i.status === "draft"
                                ? "neutral"
                                : "gold"
                          }
                        >
                          {DOC_STATUS_LABEL[i.status]}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <div style={{ height: 20 }} />
      <Panel title="Recent receipts">
        {receipts.data && receipts.data.length === 0 ? (
          <EmptyState title="No receipts yet">
            Receipts are recorded against issued invoices.
          </EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Receipt</th>
                  <th scope="col">Customer</th>
                  <th scope="col">Date</th>
                  <th scope="col">Method</th>
                  <th scope="col">Amount</th>
                </tr>
              </thead>
              <tbody>
                {receipts.data?.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <strong>{r.number}</strong>
                      <DocLinks kind="receipt" id={r.id} label={`Receipt ${r.number}`} />
                      {r.reference && <div className={styles.ref}>{r.reference}</div>}
                    </td>
                    <td>{r.customer_name}</td>
                    <td>{formatDate(r.receipt_date)}</td>
                    <td>{r.method.replace("_", " ")}</td>
                    <td className={styles.amount}>{formatMoney(r.amount, r.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Dialog open={dialog === "invoice"} title="New invoice" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(async () => {
              await send("POST", "/finance/invoices", {
                body: { ...form, lines: linesBody(lines) },
              });
              setLines([emptyLine()]);
            });
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Customer"
              required
              value={form.customer_id}
              onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
              options={[
                { value: "", label: "Choose a customer" },
                ...customerOptions.map((c) => ({ value: c.id, label: c.name })),
              ]}
            />
            <SelectField
              label="Currency"
              value={form.currency}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
              options={CURRENCIES.map((c) => ({ value: c, label: c }))}
            />
            <TextField
              label="Issue date"
              type="date"
              required
              value={form.issue_date}
              onChange={(e) => setForm({ ...form, issue_date: e.target.value })}
            />
            <TextField
              label="Due date"
              type="date"
              required
              value={form.due_date}
              onChange={(e) => setForm({ ...form, due_date: e.target.value })}
            />
          </div>
          <LineEditor
            lines={lines}
            onChange={setLines}
            accounts={revenue}
            taxCodes={outputTax}
            accountLabel="Revenue account"
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save draft
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={dialog === "receipt"} title="Record receipt" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const allocations = Object.entries(alloc)
              .filter(([, v]) => v)
              .map(([invoice_id, amount]) => ({ invoice_id, amount }));
            const first = open.find((i) => i.id === allocations[0]?.invoice_id);
            const total = sumMoney(allocations.map((a) => a.amount));
            const body = {
              customer_id: rc.customer_id,
              receipt_date: rc.receipt_date,
              currency: first?.currency ?? "MWK",
              amount: total,
              bank_account_id: rc.bank_account_id,
              method: rc.method,
              allocations,
              ...(rc.reference ? { reference: rc.reference } : {}),
              ...(rc.fx_rate ? { fx_rate: rc.fx_rate } : {}),
            };
            void act(() => send("POST", "/finance/receipts", { body }));
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Customer"
              required
              value={rc.customer_id}
              onChange={(e) => {
                setRc({ ...rc, customer_id: e.target.value });
                setAlloc({});
              }}
              options={[
                { value: "", label: "Choose a customer" },
                ...customerOptions.map((c) => ({ value: c.id, label: c.name })),
              ]}
            />
            <SelectField
              label="Into bank account"
              required
              value={rc.bank_account_id}
              onChange={(e) => setRc({ ...rc, bank_account_id: e.target.value })}
              options={[
                { value: "", label: "Choose" },
                ...banks.map((a) => ({
                  value: a.id,
                  label: `${a.code} ${a.name}${a.currency ? ` (${a.currency})` : ""}`,
                })),
              ]}
            />
            <TextField
              label="Date received"
              type="date"
              required
              value={rc.receipt_date}
              onChange={(e) => setRc({ ...rc, receipt_date: e.target.value })}
            />
            <SelectField
              label="Method"
              value={rc.method}
              onChange={(e) => setRc({ ...rc, method: e.target.value })}
              options={["bank_transfer", "cash", "cheque", "mobile_money", "card", "other"].map(
                (m) => ({ value: m, label: m.replace("_", " ") }),
              )}
            />
            <TextField
              label="Reference"
              value={rc.reference}
              onChange={(e) => setRc({ ...rc, reference: e.target.value })}
            />
            <TextField
              label="Exchange rate (foreign currency only)"
              inputMode="decimal"
              value={rc.fx_rate}
              onChange={(e) => setRc({ ...rc, fx_rate: e.target.value })}
            />
          </div>
          {rc.customer_id &&
            (open.length === 0 ? (
              <p className={page.muted}>This customer has no open invoices.</p>
            ) : (
              <div className={styles.formGrid}>
                {open.map((i) => (
                  <TextField
                    key={i.id}
                    label={`Pay ${i.number} (owes ${formatMoney(i.outstanding, i.currency)})`}
                    inputMode="decimal"
                    pattern="^\d{1,16}(\.\d{1,2})?$"
                    value={alloc[i.id] ?? ""}
                    onChange={(e) => setAlloc({ ...alloc, [i.id]: e.target.value })}
                  />
                ))}
              </div>
            ))}
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Post receipt
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={dialog === "credit"}
        title="Request credit note"
        onClose={() => setDialog(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(() => send("POST", "/finance/credit-notes", { body: cn }), "approval");
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Invoice"
              required
              value={cn.invoice_id}
              onChange={(e) => setCn({ ...cn, invoice_id: e.target.value })}
              options={[
                { value: "", label: "Choose an invoice" },
                ...(invoices.data ?? [])
                  .filter((i) => i.status === "issued" || i.status === "partially_paid")
                  .map((i) => ({
                    value: i.id,
                    label: `${i.number} · ${i.customer_name} · owes ${formatMoney(i.outstanding, i.currency)}`,
                  })),
              ]}
            />
            <TextField
              label="Credit amount (incl. tax)"
              required
              inputMode="decimal"
              pattern="^\d{1,16}(\.\d{1,2})?$"
              value={cn.amount}
              onChange={(e) => setCn({ ...cn, amount: e.target.value })}
            />
            <TextField
              label="Credit date"
              type="date"
              required
              value={cn.credit_date}
              onChange={(e) => setCn({ ...cn, credit_date: e.target.value })}
            />
          </div>
          <TextField
            label="Reason"
            required
            minLength={5}
            value={cn.reason}
            onChange={(e) => setCn({ ...cn, reason: e.target.value })}
          />
          <p className={page.note}>A credit note is posted only after the Director approves it.</p>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Send for approval
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

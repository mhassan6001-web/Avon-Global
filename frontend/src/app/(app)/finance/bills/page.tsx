"use client";

import { useState } from "react";
import { LuPlus } from "react-icons/lu";

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
  isoToday,
  type Account,
  type Bill,
  type Party,
  type Payment,
  type TaxCode,
} from "@/lib/finance/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

export default function BillsPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const bills = useResource<Bill[]>("/finance/bills?limit=500");
  const payments = useResource<Payment[]>("/finance/payments?limit=100");
  const accounts = useResource<Account[]>("/finance/accounts");
  const taxCodes = useResource<TaxCode[]>("/finance/tax-codes");
  const suppliers = useResource<Party[]>("/finance/parties?kind=supplier");
  const [dialog, setDialog] = useState<"bill" | "pay" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    supplier_id: "",
    supplier_invoice_ref: "",
    currency: "MWK",
    bill_date: isoToday(),
    due_date: isoToday(),
  });
  const [lines, setLines] = useState<LineDraft[]>([emptyLine()]);
  const [pay, setPay] = useState({
    bill_id: "",
    amount: "",
    bank_account_id: "",
    method: "bank_transfer",
    payment_date: isoToday(),
    reference: "",
  });
  const editable = can("finance.records.edit");
  const costAccounts = (accounts.data ?? []).filter((a) =>
    ["expense", "cost_of_sales", "inventory", "fixed_asset"].includes(a.subtype),
  );
  const banks = (accounts.data ?? []).filter((a) => a.subtype === "bank");
  const openBills = (bills.data ?? []).filter(
    (b) => b.status === "posted" || b.status === "partially_paid",
  );

  async function act(fn: () => Promise<unknown>, cue: "complete" | "approval" = "complete") {
    setError(null);
    try {
      await fn();
      play(cue);
      setDialog(null);
      await Promise.all([bills.reload(), payments.reload()]);
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Finance"
        title="Supplier bills and payments"
        description="Every payment is prepared here and approved by the Director before it is recorded. The system never moves money; it records what was authorised."
        actions={
          editable ? (
            <div className={page.actionsRow} style={{ marginTop: 0 }}>
              <Button
                variant="primary"
                icon={<LuPlus aria-hidden="true" />}
                onClick={() => setDialog("bill")}
              >
                Enter bill
              </Button>
              <Button onClick={() => setDialog("pay")}>Prepare payment</Button>
            </div>
          ) : undefined
        }
      />
      <FinanceNav />
      <FormError message={error ?? bills.error} />
      <Panel title="Bills">
        {bills.data && bills.data.length === 0 ? (
          <EmptyState title="No bills yet">Enter supplier invoices as they arrive.</EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Bill</th>
                  <th scope="col">Supplier</th>
                  <th scope="col">Due</th>
                  <th scope="col">Total</th>
                  <th scope="col">Outstanding</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {bills.data?.map((b) => (
                  <tr key={b.id}>
                    <td>
                      <strong>{b.number ?? "Draft"}</strong>
                      <div className={styles.ref}>Supplier ref {b.supplier_invoice_ref}</div>
                      {b.status === "draft" && editable && (
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() =>
                            void act(() =>
                              send("POST", `/finance/bills/${b.id}/post`, { body: {} }),
                            )
                          }
                        >
                          Post
                        </Button>
                      )}
                    </td>
                    <td>{b.supplier_name}</td>
                    <td>{formatDate(b.due_date)}</td>
                    <td className={styles.amount}>{formatMoney(b.total, b.currency)}</td>
                    <td className="tabular">{formatMoney(b.outstanding, b.currency)}</td>
                    <td>
                      <Badge
                        tone={
                          b.status === "paid"
                            ? "success"
                            : b.status === "draft"
                              ? "neutral"
                              : "gold"
                        }
                      >
                        {DOC_STATUS_LABEL[b.status]}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <div style={{ height: 20 }} />
      <Panel title="Payments">
        {payments.data && payments.data.length === 0 ? (
          <EmptyState title="No payments yet">
            Prepared payments wait in the Director&apos;s approval queue.
          </EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Payment</th>
                  <th scope="col">Supplier</th>
                  <th scope="col">Date</th>
                  <th scope="col">Method</th>
                  <th scope="col">Amount</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {payments.data?.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <strong>{p.number ?? "Not yet posted"}</strong>
                      <div className={styles.ref}>for {p.bill_number}</div>
                    </td>
                    <td>
                      {p.supplier_name}
                      {p.payee_account_ending && (
                        <div className={styles.ref}>to account ending {p.payee_account_ending}</div>
                      )}
                    </td>
                    <td>{formatDate(p.payment_date)}</td>
                    <td>{p.method.replace("_", " ")}</td>
                    <td className={styles.amount}>{formatMoney(p.amount, p.currency)}</td>
                    <td>
                      <Badge
                        tone={
                          p.status === "posted"
                            ? "success"
                            : p.status === "rejected"
                              ? "danger"
                              : "gold"
                        }
                      >
                        {DOC_STATUS_LABEL[p.status]}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Dialog open={dialog === "bill"} title="Enter supplier bill" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(async () => {
              await send("POST", "/finance/bills", { body: { ...form, lines: linesBody(lines) } });
              setLines([emptyLine()]);
            });
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Supplier"
              required
              value={form.supplier_id}
              onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
              options={[
                { value: "", label: "Choose a supplier" },
                ...(suppliers.data ?? []).map((s) => ({ value: s.id, label: s.name })),
              ]}
            />
            <TextField
              label="Supplier's invoice number"
              required
              value={form.supplier_invoice_ref}
              onChange={(e) => setForm({ ...form, supplier_invoice_ref: e.target.value })}
            />
            <SelectField
              label="Currency"
              value={form.currency}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
              options={CURRENCIES.map((c) => ({ value: c, label: c }))}
            />
            <TextField
              label="Bill date"
              type="date"
              required
              value={form.bill_date}
              onChange={(e) => setForm({ ...form, bill_date: e.target.value })}
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
            accounts={costAccounts}
            taxCodes={(taxCodes.data ?? []).filter((t) => t.kind === "input")}
            accountLabel="Expense account"
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

      <Dialog open={dialog === "pay"} title="Prepare payment" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const body = Object.fromEntries(Object.entries(pay).filter(([, v]) => v !== ""));
            void act(() => send("POST", "/finance/payments", { body }), "approval");
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Bill"
              required
              value={pay.bill_id}
              onChange={(e) => {
                const b = openBills.find((x) => x.id === e.target.value);
                setPay({ ...pay, bill_id: e.target.value, amount: b?.outstanding ?? "" });
              }}
              options={[
                { value: "", label: "Choose a bill" },
                ...openBills.map((b) => ({
                  value: b.id,
                  label: `${b.number} · ${b.supplier_name} · owes ${formatMoney(b.outstanding, b.currency)}`,
                })),
              ]}
            />
            <TextField
              label="Amount"
              required
              inputMode="decimal"
              pattern="^\d{1,16}(\.\d{1,2})?$"
              value={pay.amount}
              onChange={(e) => setPay({ ...pay, amount: e.target.value })}
            />
            <SelectField
              label="From bank account"
              required
              value={pay.bank_account_id}
              onChange={(e) => setPay({ ...pay, bank_account_id: e.target.value })}
              options={[
                { value: "", label: "Choose" },
                ...banks.map((a) => ({ value: a.id, label: `${a.code} ${a.name}` })),
              ]}
            />
            <SelectField
              label="Method"
              value={pay.method}
              onChange={(e) => setPay({ ...pay, method: e.target.value })}
              options={["bank_transfer", "cheque", "cash", "mobile_money", "other"].map((m) => ({
                value: m,
                label: m.replace("_", " "),
              }))}
            />
            <TextField
              label="Payment date"
              type="date"
              required
              value={pay.payment_date}
              onChange={(e) => setPay({ ...pay, payment_date: e.target.value })}
            />
            <TextField
              label="Reference"
              value={pay.reference}
              onChange={(e) => setPay({ ...pay, reference: e.target.value })}
            />
          </div>
          <p className={page.note}>
            Bank transfers go only to the supplier&apos;s approved account on file. The Director
            approves before anything is recorded as paid.
          </p>
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

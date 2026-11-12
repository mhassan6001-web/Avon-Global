"use client";

import { useState } from "react";
import { LuPlus, LuTrash2 } from "react-icons/lu";

import { CrmNav } from "@/components/crm/CrmNav";
import styles from "@/components/crm/crm.module.css";
import { DocLinks } from "@/components/documents/DocLinks";
import {
  Badge,
  Button,
  Dialog,
  EmptyState,
  FormError,
  IconButton,
  PageHeader,
  Panel,
  SelectField,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { CURRENCIES, formatDate, formatMoney, type Customer, type Page } from "@/lib/crm/types";
import { isoToday, sumMoney } from "@/lib/finance/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

interface Quotation {
  id: string;
  number: string | null;
  customer_name: string;
  title: string;
  currency: string;
  quote_date: string;
  valid_until: string;
  status: "draft" | "awaiting_approval" | "issued" | "accepted" | "declined" | "cancelled";
  expired: boolean;
  total: string;
  created_by: string;
}

interface TaxCode {
  id: string;
  code: string;
  name: string;
  rate_pct: string;
}

interface Line {
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  tax_code_id: string;
}

const emptyLine = (): Line => ({
  description: "",
  quantity: "1",
  unit: "each",
  unit_price: "",
  tax_code_id: "",
});
const inDays = (n: number) => new Date(Date.now() + n * 86_400_000).toISOString().slice(0, 10);

const TONE = {
  draft: "neutral",
  awaiting_approval: "gold",
  issued: "signal",
  accepted: "success",
  declined: "danger",
  cancelled: "neutral",
} as const;

export default function QuotationsPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const editable = can("crm.records.edit");
  const quotations = useResource<Quotation[]>("/crm/quotations");
  const customers = useResource<Page<Customer>>("/crm/customers?size=100");
  const taxCodes = useResource<TaxCode[]>("/crm/quotations/tax-codes");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    customer_id: "",
    title: "",
    currency: "MWK",
    quote_date: isoToday(),
    valid_until: inDays(30),
    terms: "",
  });
  const [lines, setLines] = useState<Line[]>([emptyLine()]);
  const setLine = (i: number, patch: Partial<Line>) =>
    setLines(lines.map((l, k) => (k === i ? { ...l, ...patch } : l)));
  const net = sumMoney(
    lines.map((l) => ((Number(l.quantity) || 0) * (Number(l.unit_price) || 0)).toFixed(2)),
  );

  async function act(fn: () => Promise<unknown>, sound: "complete" | "approval" = "complete") {
    setError(null);
    try {
      await fn();
      play(sound);
      await quotations.reload();
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  const create = () =>
    act(async () => {
      await send("POST", "/crm/quotations", {
        body: {
          ...form,
          terms: form.terms || null,
          lines: lines.map((l) => ({ ...l, tax_code_id: l.tax_code_id || null })),
        },
      });
      setOpen(false);
      setLines([emptyLine()]);
      setForm({ ...form, title: "", terms: "" });
    });

  return (
    <>
      <PageHeader
        eyebrow="CRM"
        title="Quotations"
        description="Priced offers to customers. A quotation gets its number when it is issued and cannot be changed afterwards. Tax comes only from codes that Finance has set up."
        actions={
          editable && (
            <Button
              variant="primary"
              icon={<LuPlus aria-hidden="true" />}
              onClick={() => setOpen(true)}
            >
              New quotation
            </Button>
          )
        }
      />
      <CrmNav />
      <FormError message={error ?? quotations.error} />
      <Panel title="Quotations">
        {quotations.data && quotations.data.length === 0 ? (
          <EmptyState title="No quotations yet">Quotations you prepare appear here.</EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Quotation</th>
                  <th scope="col">Customer</th>
                  <th scope="col">Valid until</th>
                  <th scope="col">Total</th>
                  <th scope="col">Status</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {quotations.data?.map((q) => (
                  <tr key={q.id}>
                    <td>
                      <strong>{q.number ?? "Draft"}</strong>
                      <DocLinks
                        kind="quotation"
                        id={q.id}
                        label={`Quotation ${q.number ?? "draft"}`}
                      />
                      <div className={page.muted}>{q.title}</div>
                    </td>
                    <td>{q.customer_name}</td>
                    <td className={q.expired ? styles.overdue : undefined}>
                      {formatDate(q.valid_until)}
                      {q.expired && " (expired)"}
                    </td>
                    <td className="tabular">{formatMoney(q.total, q.currency)}</td>
                    <td>
                      <Badge tone={TONE[q.status]}>{q.status.replace("_", " ")}</Badge>
                    </td>
                    <td>
                      {editable && q.status === "draft" && (
                        <Button
                          size="sm"
                          onClick={() =>
                            void act(
                              () => send("POST", `/crm/quotations/${q.id}/issue`),
                              "approval",
                            )
                          }
                        >
                          Issue
                        </Button>
                      )}
                      {editable && q.status === "issued" && !q.expired && (
                        <span style={{ display: "flex", gap: 8 }}>
                          <Button
                            size="sm"
                            onClick={() =>
                              void act(() =>
                                send("POST", `/crm/quotations/${q.id}/outcome`, {
                                  body: { status: "accepted" },
                                }),
                              )
                            }
                          >
                            Accepted
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() =>
                              void act(() =>
                                send("POST", `/crm/quotations/${q.id}/outcome`, {
                                  body: { status: "declined" },
                                }),
                              )
                            }
                          >
                            Declined
                          </Button>
                        </span>
                      )}
                      {q.status === "awaiting_approval" && (
                        <span className={page.muted}>Waiting for approval</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Dialog open={open} title="New quotation" onClose={() => setOpen(false)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void create();
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Customer"
              required
              value={form.customer_id}
              onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
              options={[
                { value: "", label: "Choose" },
                ...(customers.data?.items ?? []).map((c) => ({ value: c.id, label: c.name })),
              ]}
            />
            <TextField
              label="Subject"
              required
              minLength={2}
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <SelectField
              label="Currency"
              value={form.currency}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
              options={CURRENCIES.map((c) => ({ value: c, label: c }))}
            />
            <TextField
              label="Quotation date"
              type="date"
              required
              value={form.quote_date}
              onChange={(e) => setForm({ ...form, quote_date: e.target.value })}
            />
            <TextField
              label="Valid until"
              type="date"
              required
              value={form.valid_until}
              onChange={(e) => setForm({ ...form, valid_until: e.target.value })}
            />
          </div>
          <fieldset style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
            <legend className="hud-label">Lines</legend>
            {lines.map((line, i) => (
              <div
                key={i}
                className={styles.formGrid}
                style={{ gridTemplateColumns: "2fr 0.7fr 0.8fr 1fr 1.2fr auto", alignItems: "end" }}
              >
                <TextField
                  label={`Item ${i + 1}`}
                  required
                  minLength={2}
                  value={line.description}
                  onChange={(e) => setLine(i, { description: e.target.value })}
                />
                <TextField
                  label={`Quantity ${i + 1}`}
                  required
                  inputMode="decimal"
                  value={line.quantity}
                  onChange={(e) => setLine(i, { quantity: e.target.value })}
                />
                <TextField
                  label={`Unit ${i + 1}`}
                  required
                  value={line.unit}
                  onChange={(e) => setLine(i, { unit: e.target.value })}
                />
                <TextField
                  label={`Unit price ${i + 1}`}
                  required
                  inputMode="decimal"
                  value={line.unit_price}
                  onChange={(e) => setLine(i, { unit_price: e.target.value })}
                />
                <SelectField
                  label={`Tax code ${i + 1}`}
                  value={line.tax_code_id}
                  onChange={(e) => setLine(i, { tax_code_id: e.target.value })}
                  options={[
                    { value: "", label: "No tax" },
                    ...(taxCodes.data ?? []).map((t) => ({
                      value: t.id,
                      label: `${t.code} (${Number(t.rate_pct)}%)`,
                    })),
                  ]}
                />
                <IconButton
                  label={`Remove line ${i + 1}`}
                  disabled={lines.length === 1}
                  onClick={() => setLines(lines.filter((_, k) => k !== i))}
                >
                  <LuTrash2 />
                </IconButton>
              </div>
            ))}
            <div>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                icon={<LuPlus aria-hidden="true" />}
                onClick={() => setLines([...lines, emptyLine()])}
              >
                Add line
              </Button>
            </div>
          </fieldset>
          <label className={styles.textareaLabel}>
            Terms (printed on the quotation)
            <textarea
              className={styles.textarea}
              rows={3}
              maxLength={5000}
              value={form.terms}
              onChange={(e) => setForm({ ...form, terms: e.target.value })}
            />
          </label>
          <p className={page.muted}>
            Net before tax: {formatMoney(net, form.currency)}. Tax and the final total are
            calculated by the system from the chosen tax codes.
            {taxCodes.data?.length === 0 &&
              " No sales tax code is set up yet, so lines carry no tax."}
          </p>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save draft
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

"use client";

import Link from "next/link";
import { useState } from "react";
import { LuFileDown, LuPlus, LuTrash2 } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
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
import { API_PREFIX, send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { CURRENCIES, formatDate, formatMoney } from "@/lib/crm/types";

import page from "@/app/pages.module.css";

interface Clause {
  heading: string;
  text: string;
}

interface Contract {
  id: string;
  reference: string;
  kind: "supply" | "service";
  party_type: "customer" | "supplier";
  party_name: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  currency: string | null;
  value: string | null;
  status: "draft" | "final";
}

interface Named {
  id: string;
  name: string;
}

// Headings only. The wording of every clause is yours to write.
const HEADINGS = [
  "Parties",
  "Scope",
  "Price and payment",
  "Delivery",
  "Term and ending",
  "Governing law",
];
const PERMS = {
  customer: {
    edit: "crm.records.edit",
    final: "crm.quotation.approve",
    list: "/crm/customers?size=100",
  },
  supplier: {
    edit: "procurement.records.edit",
    final: "procurement.order.approve",
    list: "/procurement/suppliers?size=100",
  },
} as const;

export default function ContractsPage() {
  const { can } = useAuth();
  const contracts = useResource<Contract[]>("/documents/contracts");
  const types = (["customer", "supplier"] as const).filter((t) => can(PERMS[t].edit));
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    kind: "supply",
    party_type: types[0] ?? "customer",
    party_id: "",
    title: "",
    start_date: "",
    end_date: "",
    currency: "",
    value: "",
  });
  const [clauses, setClauses] = useState<Clause[]>(
    HEADINGS.map((heading) => ({ heading, text: "" })),
  );
  const parties = useResource<{ items: Named[] }>(open ? PERMS[form.party_type].list : null);
  const setClause = (i: number, patch: Partial<Clause>) =>
    setClauses(clauses.map((c, k) => (k === i ? { ...c, ...patch } : c)));

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      await contracts.reload();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  const create = () =>
    act(async () => {
      await send("POST", "/documents/contracts", {
        body: {
          kind: form.kind,
          party_type: form.party_type,
          party_id: form.party_id,
          title: form.title,
          start_date: form.start_date || null,
          end_date: form.end_date || null,
          currency: form.value ? form.currency || "MWK" : null,
          value: form.value || null,
          clauses,
        },
      });
      setOpen(false);
    });

  return (
    <>
      <PageHeader
        eyebrow={<Link href="/documents">Documents</Link>}
        title="Contracts and service agreements"
        description="The system gives the layout, numbering and your letterhead. It supplies no legal wording: you write every clause, and a lawyer should review it. Signature lines print blank."
        actions={
          types.length > 0 && (
            <Button
              variant="primary"
              icon={<LuPlus aria-hidden="true" />}
              onClick={() => setOpen(true)}
            >
              New contract
            </Button>
          )
        }
      />
      <FormError message={error ?? contracts.error} />
      <Panel title="Contracts">
        {contracts.data && contracts.data.length === 0 ? (
          <EmptyState title="No contracts yet">Contracts you prepare appear here.</EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Contract</th>
                  <th scope="col">With</th>
                  <th scope="col">Period</th>
                  <th scope="col">Value</th>
                  <th scope="col">Status</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {contracts.data?.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <strong>{c.reference}</strong>
                      <div className={page.muted}>{c.title}</div>
                    </td>
                    <td>
                      {c.party_name}
                      <div className={page.muted}>{c.party_type}</div>
                    </td>
                    <td>
                      {c.start_date ? formatDate(c.start_date) : "—"} to{" "}
                      {c.end_date ? formatDate(c.end_date) : "—"}
                    </td>
                    <td className="tabular">
                      {c.value && c.currency ? formatMoney(c.value, c.currency) : "—"}
                    </td>
                    <td>
                      <Badge tone={c.status === "final" ? "success" : "neutral"}>{c.status}</Badge>
                    </td>
                    <td>
                      <span style={{ display: "flex", gap: 12, alignItems: "center" }}>
                        {(["pdf", "docx"] as const).map((f) => (
                          <a
                            key={f}
                            className={page.inlineLink}
                            href={`${API_PREFIX}/documents/contracts/${c.id}/file?format=${f}`}
                            download
                            aria-label={`Contract ${c.reference} as ${f === "pdf" ? "PDF" : "Word"}`}
                          >
                            <LuFileDown aria-hidden="true" /> {f === "pdf" ? "PDF" : "Word"}
                          </a>
                        ))}
                        {c.status === "draft" && can(PERMS[c.party_type].final) && (
                          <Button
                            size="sm"
                            onClick={() =>
                              void act(() => send("POST", `/documents/contracts/${c.id}/finalise`))
                            }
                          >
                            Mark final
                          </Button>
                        )}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Dialog open={open} title="New contract" onClose={() => setOpen(false)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void create();
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Type"
              value={form.kind}
              onChange={(e) => setForm({ ...form, kind: e.target.value })}
              options={[
                { value: "supply", label: "Supply contract" },
                { value: "service", label: "Service agreement" },
              ]}
            />
            <SelectField
              label="With a"
              value={form.party_type}
              onChange={(e) =>
                setForm({
                  ...form,
                  party_type: e.target.value as "customer" | "supplier",
                  party_id: "",
                })
              }
              options={types.map((t) => ({
                value: t,
                label: t === "customer" ? "Customer" : "Supplier",
              }))}
            />
            <SelectField
              label="Party"
              required
              value={form.party_id}
              onChange={(e) => setForm({ ...form, party_id: e.target.value })}
              options={[
                { value: "", label: "Choose" },
                ...(parties.data?.items ?? []).map((p) => ({ value: p.id, label: p.name })),
              ]}
            />
            <TextField
              label="Subject"
              required
              minLength={2}
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <TextField
              label="Start date"
              type="date"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            />
            <TextField
              label="End date"
              type="date"
              value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            />
            <TextField
              label="Contract value (optional)"
              inputMode="decimal"
              value={form.value}
              onChange={(e) => setForm({ ...form, value: e.target.value })}
            />
            <SelectField
              label="Currency"
              value={form.currency || "MWK"}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
              options={CURRENCIES.map((c) => ({ value: c, label: c }))}
            />
          </div>
          <fieldset style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
            <legend className="hud-label">Clauses (write your own wording)</legend>
            {clauses.map((c, i) => (
              <div key={i} style={{ display: "grid", gap: 6 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "end" }}>
                  <TextField
                    label={`Clause ${i + 1} heading`}
                    required
                    minLength={2}
                    value={c.heading}
                    onChange={(e) => setClause(i, { heading: e.target.value })}
                  />
                  <IconButton
                    label={`Remove clause ${i + 1}`}
                    disabled={clauses.length === 1}
                    onClick={() => setClauses(clauses.filter((_, k) => k !== i))}
                  >
                    <LuTrash2 />
                  </IconButton>
                </div>
                <label className={styles.textareaLabel}>
                  Clause {i + 1} wording
                  <textarea
                    className={styles.textarea}
                    rows={3}
                    required
                    minLength={2}
                    maxLength={1500}
                    value={c.text}
                    onChange={(e) => setClause(i, { text: e.target.value })}
                  />
                </label>
              </div>
            ))}
            <div>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                icon={<LuPlus aria-hidden="true" />}
                onClick={() => setClauses([...clauses, { heading: "", text: "" }])}
              >
                Add clause
              </Button>
            </div>
          </fieldset>
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

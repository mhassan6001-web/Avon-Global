"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LuPlus, LuTrash2 } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
import { ProcurementNav } from "@/components/procurement/ProcurementNav";
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
import { CURRENCIES, formatDate, query } from "@/lib/crm/types";
import {
  REQUEST_STATUS_LABEL,
  type Page,
  type PurchaseRequest,
  type PurchaseRequestDetail,
} from "@/lib/procurement/types";

import page from "@/app/pages.module.css";

interface LineForm {
  description: string;
  quantity: string;
  unit: string;
}

export default function PurchaseRequestsPage() {
  const { can } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState("");
  const { data, error } = useResource<Page<PurchaseRequest>>(
    `/procurement/requests${query({ status, size: 100 })}`,
  );
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    title: "",
    justification: "",
    currency: "MWK",
    needed_by: "",
  });
  const [lines, setLines] = useState<LineForm[]>([
    { description: "", quantity: "1", unit: "each" },
  ]);
  const [formError, setFormError] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Procurement"
        title="Procurement"
        description="Purchase requests, supplier quotations and orders. Every order is approved by the Director before it is issued."
        actions={
          can("procurement.records.edit") ? (
            <Button
              variant="primary"
              icon={<LuPlus aria-hidden="true" />}
              onClick={() => setOpen(true)}
            >
              New purchase request
            </Button>
          ) : undefined
        }
      />
      <ProcurementNav />
      <Panel title="Purchase requests">
        <div className={styles.toolbar}>
          <SelectField
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            options={[
              { value: "", label: "All" },
              ...Object.entries(REQUEST_STATUS_LABEL).map(([value, label]) => ({ value, label })),
            ]}
          />
        </div>
        <FormError message={error} />
        {data && data.items.length === 0 ? (
          <EmptyState title="No purchase requests">
            Raise a request, collect quotations, then send it for approval.
          </EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Request</th>
                  <th scope="col">Needed by</th>
                  <th scope="col">Requested by</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <Link href={`/procurement/requests/${r.id}`} className={styles.rowLink}>
                        {r.title}
                      </Link>
                      <div className={styles.ref}>{r.reference}</div>
                    </td>
                    <td>{formatDate(r.needed_by)}</td>
                    <td>{r.requested_by?.display_name ?? "—"}</td>
                    <td>
                      <Badge
                        tone={
                          r.status === "approved" || r.status === "ordered"
                            ? "success"
                            : r.status === "awaiting_approval"
                              ? "gold"
                              : "neutral"
                        }
                      >
                        {REQUEST_STATUS_LABEL[r.status]}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Dialog open={open} title="New purchase request" onClose={() => setOpen(false)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            setFormError(null);
            const body = {
              title: form.title,
              currency: form.currency,
              ...(form.justification ? { justification: form.justification } : {}),
              ...(form.needed_by ? { needed_by: form.needed_by } : {}),
              lines,
            };
            send<PurchaseRequestDetail>("POST", "/procurement/requests", { body })
              .then(({ data: d }) => router.push(`/procurement/requests/${d.request.id}`))
              .catch((err: unknown) => setFormError(errorMessage(err)));
          }}
        >
          <div className={styles.formGrid}>
            <TextField
              label="What is needed"
              required
              minLength={3}
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
              label="Needed by"
              type="date"
              value={form.needed_by}
              onChange={(e) => setForm({ ...form, needed_by: e.target.value })}
            />
            <TextField
              label="Justification"
              value={form.justification}
              onChange={(e) => setForm({ ...form, justification: e.target.value })}
            />
          </div>
          <fieldset className={styles.timeline} style={{ border: 0, padding: 0 }}>
            <legend className="hud-label">Lines</legend>
            {lines.map((line, i) => (
              <div
                key={i}
                className={styles.formGrid}
                style={{ gridTemplateColumns: "2fr 1fr 1fr auto", alignItems: "end" }}
              >
                <TextField
                  label={`Item ${i + 1}`}
                  required
                  minLength={2}
                  value={line.description}
                  onChange={(e) =>
                    setLines(
                      lines.map((l, k) => (k === i ? { ...l, description: e.target.value } : l)),
                    )
                  }
                />
                <TextField
                  label={`Quantity ${i + 1}`}
                  required
                  inputMode="decimal"
                  pattern="^\d{1,15}(\.\d{1,3})?$"
                  value={line.quantity}
                  onChange={(e) =>
                    setLines(
                      lines.map((l, k) => (k === i ? { ...l, quantity: e.target.value } : l)),
                    )
                  }
                />
                <TextField
                  label={`Unit ${i + 1}`}
                  required
                  value={line.unit}
                  onChange={(e) =>
                    setLines(lines.map((l, k) => (k === i ? { ...l, unit: e.target.value } : l)))
                  }
                />
                <IconButton
                  label={`Remove item ${i + 1}`}
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
                icon={<LuPlus aria-hidden="true" />}
                onClick={() =>
                  setLines([...lines, { description: "", quantity: "1", unit: "each" }])
                }
              >
                Add line
              </Button>
            </div>
          </fieldset>
          <FormError message={formError} />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create request
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

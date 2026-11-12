"use client";

import { useState } from "react";
import { LuPlus, LuTrash2 } from "react-icons/lu";

import { DocLinks } from "@/components/documents/DocLinks";
import styles from "@/components/crm/crm.module.css";
import { OpsNav } from "@/components/inventory/OpsNav";
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
import { send, uploadFile } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDate } from "@/lib/crm/types";
import { label, qty, type DeliveryNote, type Product, type Warehouse } from "@/lib/inventory/types";
import { formatDateTime } from "@/lib/tenders/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

export default function DeliveriesPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const notes = useResource<DeliveryNote[]>("/logistics/delivery-notes");
  const customers = useResource<Array<{ id: string; name: string }>>("/logistics/customers");
  const products = useResource<Product[]>(
    can("inventory.records.view") ? "/inventory/products" : null,
  );
  const warehouses = useResource<Warehouse[]>(
    can("inventory.records.view") ? "/inventory/warehouses" : null,
  );
  const [creating, setCreating] = useState(false);
  const [proofFor, setProofFor] = useState<DeliveryNote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    customer_id: "",
    warehouse_id: "",
    delivery_address: "",
    scheduled_for: "",
  });
  const [lines, setLines] = useState([{ product_id: "", quantity: "" }]);
  const [proof, setProof] = useState<{ received_by_name: string; note: string; file: File | null }>(
    { received_by_name: "", note: "", file: null },
  );
  const editable = can("logistics.records.edit");

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      play("complete");
      setCreating(false);
      setProofFor(null);
      await notes.reload();
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Logistics"
        title="Deliveries"
        description="Delivery notes take stock out when dispatched. Proof of delivery records who actually received the goods; nothing is signed on anyone's behalf."
        actions={
          editable ? (
            <Button
              variant="primary"
              icon={<LuPlus aria-hidden="true" />}
              onClick={() => setCreating(true)}
            >
              New delivery note
            </Button>
          ) : undefined
        }
      />
      <OpsNav section="logistics" />
      <FormError message={error ?? notes.error} />
      <Panel title="Delivery notes">
        {notes.data && notes.data.length === 0 ? (
          <EmptyState title="No deliveries yet">
            Create a delivery note for each outgoing delivery.
          </EmptyState>
        ) : (
          <ul className={styles.timeline}>
            {notes.data?.map((n) => (
              <li key={n.id} className={styles.timelineItem}>
                <Badge
                  tone={
                    n.status === "delivered"
                      ? "success"
                      : n.status === "dispatched"
                        ? "gold"
                        : "neutral"
                  }
                >
                  {label(n.status)}
                </Badge>
                <div>
                  <strong>{n.number}</strong>
                  <DocLinks
                    kind="delivery_note"
                    id={n.id}
                    label={`Delivery note ${n.number}`}
                  /> · {n.customer_name} · from {n.warehouse_code}
                  <div className={page.muted}>
                    {n.lines.map((l) => `${qty(l.quantity)} ${l.unit} ${l.sku}`).join(", ")} ·{" "}
                    {n.delivery_address}
                  </div>
                  {n.status === "delivered" && (
                    <div className={page.muted}>
                      Received by {n.received_by_name} on {formatDateTime(n.delivered_at)}
                      {n.proof_file_id ? " · signed document attached" : ""}
                    </div>
                  )}
                  {n.scheduled_for && n.status === "draft" && (
                    <div className={page.muted}>Scheduled {formatDate(n.scheduled_for)}</div>
                  )}
                </div>
                {editable ? (
                  <span style={{ display: "flex", gap: 8 }}>
                    {n.status === "draft" && (
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() =>
                          void act(() => send("POST", `/logistics/delivery-notes/${n.id}/dispatch`))
                        }
                      >
                        Dispatch
                      </Button>
                    )}
                    {n.status === "draft" && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          void act(() =>
                            send("POST", `/logistics/delivery-notes/${n.id}/cancel`, {
                              body: { reason: "Cancelled before dispatch" },
                            }),
                          )
                        }
                      >
                        Cancel
                      </Button>
                    )}
                    {n.status === "dispatched" && (
                      <Button
                        size="sm"
                        onClick={() => {
                          setProof({ received_by_name: "", note: "", file: null });
                          setProofFor(n);
                        }}
                      >
                        Record proof of delivery
                      </Button>
                    )}
                  </span>
                ) : (
                  <span />
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Dialog open={creating} title="New delivery note" onClose={() => setCreating(false)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const body = {
              ...Object.fromEntries(Object.entries(form).filter(([, v]) => v !== "")),
              lines,
            };
            void act(() => send("POST", "/logistics/delivery-notes", { body }));
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
                ...(customers.data ?? []).map((c) => ({ value: c.id, label: c.name })),
              ]}
            />
            <SelectField
              label="From warehouse"
              required
              value={form.warehouse_id}
              onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}
              options={[
                { value: "", label: "Choose" },
                ...(warehouses.data ?? []).map((w) => ({
                  value: w.id,
                  label: `${w.code} ${w.name}`,
                })),
              ]}
            />
            <TextField
              label="Delivery address"
              required
              minLength={5}
              value={form.delivery_address}
              onChange={(e) => setForm({ ...form, delivery_address: e.target.value })}
            />
            <TextField
              label="Scheduled for"
              type="date"
              value={form.scheduled_for}
              onChange={(e) => setForm({ ...form, scheduled_for: e.target.value })}
            />
          </div>
          {lines.map((l, i) => (
            <div
              key={i}
              className={styles.formGrid}
              style={{ gridTemplateColumns: "2fr 1fr auto", alignItems: "end" }}
            >
              <SelectField
                label={`Product ${i + 1}`}
                required
                value={l.product_id}
                onChange={(e) =>
                  setLines(
                    lines.map((x, k) => (k === i ? { ...x, product_id: e.target.value } : x)),
                  )
                }
                options={[
                  { value: "", label: "Choose" },
                  ...(products.data ?? []).map((p) => ({
                    value: p.id,
                    label: `${p.sku} ${p.name} (${qty(p.on_hand)} on hand)`,
                  })),
                ]}
              />
              <TextField
                label={`Quantity ${i + 1}`}
                required
                inputMode="decimal"
                value={l.quantity}
                onChange={(e) =>
                  setLines(lines.map((x, k) => (k === i ? { ...x, quantity: e.target.value } : x)))
                }
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
              onClick={() => setLines([...lines, { product_id: "", quantity: "" }])}
            >
              Add line
            </Button>
          </div>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create delivery note
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={proofFor !== null} title="Proof of delivery" onClose={() => setProofFor(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (!proofFor) return;
            void act(async () => {
              const file = proof.file
                ? await uploadFile(proof.file, "logistics", "logistics.records.view")
                : null;
              await send("POST", `/logistics/delivery-notes/${proofFor.id}/proof`, {
                body: {
                  received_by_name: proof.received_by_name,
                  ...(proof.note ? { note: proof.note } : {}),
                  ...(file ? { proof_file_id: file.id } : {}),
                },
              });
            });
          }}
        >
          <TextField
            label="Name of the person who received the goods"
            required
            minLength={2}
            value={proof.received_by_name}
            onChange={(e) => setProof({ ...proof, received_by_name: e.target.value })}
          />
          <TextField
            label="Note"
            value={proof.note}
            onChange={(e) => setProof({ ...proof, note: e.target.value })}
          />
          <label className={styles.textareaLabel}>
            Signed delivery note or photo (optional)
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={(e) => setProof({ ...proof, file: e.target.files?.[0] ?? null })}
            />
          </label>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setProofFor(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Mark delivered
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

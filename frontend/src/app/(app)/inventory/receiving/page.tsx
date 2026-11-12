"use client";

import { useState } from "react";

import styles from "@/components/crm/crm.module.css";
import { OpsNav } from "@/components/inventory/OpsNav";
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
import { formatDate } from "@/lib/crm/types";
import { isoToday } from "@/lib/finance/types";
import {
  qty,
  remaining,
  type OpenOrder,
  type Product,
  type Warehouse,
} from "@/lib/inventory/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

interface Grn {
  id: string;
  number: string;
  purchase_order_reference: string;
  received_on: string;
  delivery_note_ref: string | null;
  order_status: string;
}

export default function ReceivingPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const orders = useResource<OpenOrder[]>("/inventory/open-orders");
  const grns = useResource<Grn[]>("/inventory/goods-receipts");
  const products = useResource<Product[]>("/inventory/products");
  const warehouses = useResource<Warehouse[]>("/inventory/warehouses");
  const [order, setOrder] = useState<OpenOrder | null>(null);
  const [head, setHead] = useState({
    warehouse_id: "",
    received_on: isoToday(),
    delivery_note_ref: "",
  });
  const [lines, setLines] = useState<Record<number, { product_id: string; quantity: string }>>({});
  const [error, setError] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Logistics"
        title="Goods received"
        description="Receive deliveries against Director-approved purchase orders. Stock and cost update from the order price."
      />
      <OpsNav section="inventory" />
      <FormError message={error ?? orders.error} />
      <Panel title="Orders waiting for delivery">
        {orders.data && orders.data.length === 0 ? (
          <EmptyState title="Nothing to receive">
            Issued purchase orders appear here until fully received.
          </EmptyState>
        ) : (
          <ul className={styles.timeline}>
            {orders.data?.map((o) => (
              <li key={o.id} className={styles.timelineItem}>
                <span className={styles.ref}>{o.reference}</span>
                <div>
                  <strong>{o.supplier}</strong>
                  <div className={page.muted}>
                    {o.lines
                      .map(
                        (l) =>
                          `${l.description}: ${qty(remaining(l.ordered, l.received))} ${l.unit} to come`,
                      )
                      .join(" · ")}
                  </div>
                </div>
                {can("inventory.records.edit") ? (
                  <Button
                    size="sm"
                    onClick={() => {
                      setLines({});
                      setOrder(o);
                    }}
                  >
                    Receive
                  </Button>
                ) : (
                  <span />
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <div style={{ height: 20 }} />
      <Panel title="Goods-received notes">
        {grns.data && grns.data.length === 0 ? (
          <EmptyState title="No deliveries received yet">
            Each delivery gets its own GRN number.
          </EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">GRN</th>
                  <th scope="col">Order</th>
                  <th scope="col">Received</th>
                  <th scope="col">Supplier note</th>
                  <th scope="col">Order status</th>
                </tr>
              </thead>
              <tbody>
                {grns.data?.map((g) => (
                  <tr key={g.id}>
                    <td>
                      <strong>{g.number}</strong>
                    </td>
                    <td>{g.purchase_order_reference}</td>
                    <td>{formatDate(g.received_on)}</td>
                    <td>{g.delivery_note_ref ?? "—"}</td>
                    <td>
                      <Badge tone={g.order_status === "received" ? "success" : "gold"}>
                        {g.order_status.replace("_", " ")}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Dialog open={order !== null} title="Receive goods" onClose={() => setOrder(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (!order) return;
            const body = {
              purchase_order_id: order.id,
              warehouse_id: head.warehouse_id,
              received_on: head.received_on,
              ...(head.delivery_note_ref ? { delivery_note_ref: head.delivery_note_ref } : {}),
              lines: Object.entries(lines)
                .filter(([, v]) => v.quantity && v.product_id)
                .map(([n, v]) => ({ line_no: Number(n), ...v })),
            };
            setError(null);
            send("POST", "/inventory/goods-receipts", { body })
              .then(async () => {
                play("complete");
                setOrder(null);
                await Promise.all([orders.reload(), grns.reload()]);
              })
              .catch((err: unknown) => {
                setError(errorMessage(err));
                play("warning");
              });
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Into warehouse"
              required
              value={head.warehouse_id}
              onChange={(e) => setHead({ ...head, warehouse_id: e.target.value })}
              options={[
                { value: "", label: "Choose" },
                ...(warehouses.data ?? []).map((w) => ({
                  value: w.id,
                  label: `${w.code} ${w.name}`,
                })),
              ]}
            />
            <TextField
              label="Received on"
              type="date"
              required
              value={head.received_on}
              onChange={(e) => setHead({ ...head, received_on: e.target.value })}
            />
            <TextField
              label="Supplier's delivery note"
              value={head.delivery_note_ref}
              onChange={(e) => setHead({ ...head, delivery_note_ref: e.target.value })}
            />
          </div>
          {order?.lines.map((l) => (
            <div key={l.line_no} className={styles.formGrid} style={{ alignItems: "end" }}>
              <SelectField
                label={`Product for “${l.description}”`}
                value={lines[l.line_no]?.product_id ?? ""}
                onChange={(e) =>
                  setLines({
                    ...lines,
                    [l.line_no]: {
                      quantity: lines[l.line_no]?.quantity ?? "",
                      product_id: e.target.value,
                    },
                  })
                }
                options={[
                  { value: "", label: "Choose" },
                  ...(products.data ?? []).map((p) => ({
                    value: p.id,
                    label: `${p.sku} ${p.name}`,
                  })),
                ]}
              />
              <TextField
                label={`Quantity received (max ${qty(remaining(l.ordered, l.received))})`}
                inputMode="decimal"
                value={lines[l.line_no]?.quantity ?? ""}
                onChange={(e) =>
                  setLines({
                    ...lines,
                    [l.line_no]: {
                      product_id: lines[l.line_no]?.product_id ?? "",
                      quantity: e.target.value,
                    },
                  })
                }
              />
            </div>
          ))}
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setOrder(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Record delivery
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

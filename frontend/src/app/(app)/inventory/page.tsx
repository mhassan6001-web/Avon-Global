"use client";

import { useState } from "react";
import { LuArrowLeftRight, LuPackagePlus, LuScale, LuWarehouse } from "react-icons/lu";

import { KpiCard } from "@/components/charts/Charts";
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
import { formatDate, formatMoney } from "@/lib/crm/types";
import { isoToday } from "@/lib/finance/types";
import {
  label,
  qty,
  type Level,
  type Movement,
  type Product,
  type Warehouse,
} from "@/lib/inventory/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

type DialogKind = "product" | "warehouse" | "adjust" | "transfer" | null;

export default function InventoryPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const products = useResource<Product[]>("/inventory/products");
  const warehouses = useResource<Warehouse[]>("/inventory/warehouses");
  const levels = useResource<Level[]>("/inventory/levels");
  const movements = useResource<Movement[]>("/inventory/movements?limit=50");
  const summary = useResource<{
    has_records: boolean;
    functional_currency: string;
    products: number;
    stock_value: string;
    below_reorder: number;
  }>("/inventory/summary");
  const [dialog, setDialog] = useState<DialogKind>(null);
  const [error, setError] = useState<string | null>(null);
  const [prod, setProd] = useState({
    sku: "",
    name: "",
    unit: "each",
    category: "",
    reorder_level: "0",
  });
  const [wh, setWh] = useState({ code: "", name: "", location: "" });
  const [adj, setAdj] = useState({
    product_id: "",
    warehouse_id: "",
    quantity: "",
    unit_cost: "",
    kind: "adjustment",
    reason: "",
    movement_date: isoToday(),
  });
  const [tr, setTr] = useState({
    product_id: "",
    from_warehouse_id: "",
    to_warehouse_id: "",
    quantity: "",
    movement_date: isoToday(),
    reason: "",
  });
  const editable = can("inventory.records.edit");
  const s = summary.data;
  const ccy = s?.functional_currency ?? "MWK";
  const productOptions = [
    { value: "", label: "Choose a product" },
    ...(products.data ?? []).map((p) => ({ value: p.id, label: `${p.sku} ${p.name}` })),
  ];
  const warehouseOptions = [
    { value: "", label: "Choose a warehouse" },
    ...(warehouses.data ?? []).map((w) => ({ value: w.id, label: `${w.code} ${w.name}` })),
  ];

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      play("complete");
      setDialog(null);
      await Promise.all([
        products.reload(),
        warehouses.reload(),
        levels.reload(),
        movements.reload(),
        summary.reload(),
      ]);
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }
  const clean = (o: Record<string, string>) =>
    Object.fromEntries(Object.entries(o).filter(([, v]) => v !== ""));

  return (
    <>
      <PageHeader
        eyebrow="Logistics"
        title="Inventory"
        description="Stock on hand by warehouse at weighted-average cost. Movements are a permanent ledger: mistakes are corrected with a new adjustment."
        actions={
          editable ? (
            <div className={page.actionsRow} style={{ marginTop: 0 }}>
              <Button
                variant="primary"
                icon={<LuPackagePlus aria-hidden="true" />}
                onClick={() => setDialog("product")}
              >
                New product
              </Button>
              <Button
                icon={<LuWarehouse aria-hidden="true" />}
                onClick={() => setDialog("warehouse")}
              >
                New warehouse
              </Button>
              <Button icon={<LuScale aria-hidden="true" />} onClick={() => setDialog("adjust")}>
                Adjust stock
              </Button>
              <Button
                icon={<LuArrowLeftRight aria-hidden="true" />}
                onClick={() => setDialog("transfer")}
              >
                Transfer
              </Button>
            </div>
          ) : undefined
        }
      />
      <OpsNav section="inventory" />
      <FormError message={error ?? products.error} />
      <div className={page.grid}>
        <div className={page.span4}>
          <KpiCard
            icon={<LuPackagePlus />}
            label="Active products"
            value={s?.has_records ? String(s.products) : null}
          />
        </div>
        <div className={page.span4}>
          <KpiCard
            icon={<LuScale />}
            label={`Stock value (${ccy})`}
            value={s?.has_records ? formatMoney(s.stock_value, ccy) : null}
            note="Weighted-average cost"
          />
        </div>
        <div className={page.span4}>
          <KpiCard
            icon={<LuWarehouse />}
            label="At or below reorder level"
            value={s?.has_records ? String(s.below_reorder) : null}
          />
        </div>
        <div className={page.span12}>
          <Panel title="Products">
            {products.data && products.data.length === 0 ? (
              <EmptyState title="No products yet">
                Add the items you stock. Nothing is pre-filled.
              </EmptyState>
            ) : (
              <div className={page.tableWrap}>
                <table className={page.table}>
                  <thead>
                    <tr>
                      <th scope="col">SKU</th>
                      <th scope="col">Product</th>
                      <th scope="col">On hand</th>
                      <th scope="col">Reorder at</th>
                      <th scope="col">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {products.data?.map((p) => (
                      <tr key={p.id}>
                        <td className={styles.ref}>{p.sku}</td>
                        <td>
                          {p.name}
                          {p.category && <div className={page.muted}>{p.category}</div>}
                        </td>
                        <td className="tabular">
                          {qty(p.on_hand)} {p.unit}{" "}
                          {p.below_reorder && <Badge tone="warning">Reorder</Badge>}
                        </td>
                        <td className="tabular">{qty(p.reorder_level)}</td>
                        <td className={styles.amount}>{formatMoney(p.value, ccy)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
        <div className={page.span6}>
          <Panel title="By warehouse">
            {levels.data && levels.data.length === 0 ? (
              <EmptyState title="No stock held">Receive goods or record opening stock.</EmptyState>
            ) : (
              <ul className={styles.timeline}>
                {levels.data?.map((l) => (
                  <li key={`${l.product_id}-${l.warehouse_id}`} className={styles.timelineItem}>
                    <span className={styles.ref}>{l.warehouse_code}</span>
                    <div>
                      <strong>{l.sku}</strong> {l.product_name}
                      <div className={page.muted}>avg cost {l.average_cost}</div>
                    </div>
                    <span className="tabular">{qty(l.quantity)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
        <div className={page.span6}>
          <Panel title="Recent movements">
            {movements.data && movements.data.length === 0 ? (
              <EmptyState title="No movements yet">
                Every receipt, dispatch, transfer and adjustment is listed here.
              </EmptyState>
            ) : (
              <ul className={styles.timeline}>
                {movements.data?.map((m) => (
                  <li key={m.id} className={styles.timelineItem}>
                    <Badge tone={m.quantity.startsWith("-") ? "warning" : "success"}>
                      {label(m.kind)}
                    </Badge>
                    <div>
                      <strong>{m.sku}</strong> · {m.warehouse_code} · {formatDate(m.movement_date)}
                      <div className={page.muted}>
                        {[m.reference, m.reason].filter(Boolean).join(" · ")}
                      </div>
                    </div>
                    <span className="tabular">{qty(m.quantity)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>

      <Dialog open={dialog === "product"} title="New product" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(() => send("POST", "/inventory/products", { body: clean(prod) }));
          }}
        >
          <div className={styles.formGrid}>
            <TextField
              label="SKU"
              required
              pattern="^[A-Z0-9][A-Z0-9._\-]{1,39}$"
              value={prod.sku}
              onChange={(e) => setProd({ ...prod, sku: e.target.value.toUpperCase() })}
            />
            <TextField
              label="Product name"
              required
              minLength={2}
              value={prod.name}
              onChange={(e) => setProd({ ...prod, name: e.target.value })}
            />
            <TextField
              label="Unit"
              required
              value={prod.unit}
              onChange={(e) => setProd({ ...prod, unit: e.target.value })}
            />
            <TextField
              label="Category"
              value={prod.category}
              onChange={(e) => setProd({ ...prod, category: e.target.value })}
            />
            <TextField
              label="Reorder level"
              inputMode="decimal"
              value={prod.reorder_level}
              onChange={(e) => setProd({ ...prod, reorder_level: e.target.value })}
            />
          </div>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create product
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={dialog === "warehouse"} title="New warehouse" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(() => send("POST", "/inventory/warehouses", { body: clean(wh) }));
          }}
        >
          <div className={styles.formGrid}>
            <TextField
              label="Warehouse code"
              required
              pattern="^[A-Z0-9\-]{2,20}$"
              value={wh.code}
              onChange={(e) => setWh({ ...wh, code: e.target.value.toUpperCase() })}
            />
            <TextField
              label="Warehouse name"
              required
              minLength={2}
              value={wh.name}
              onChange={(e) => setWh({ ...wh, name: e.target.value })}
            />
            <TextField
              label="Location"
              value={wh.location}
              onChange={(e) => setWh({ ...wh, location: e.target.value })}
            />
          </div>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create warehouse
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={dialog === "adjust"} title="Adjust stock" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(() => send("POST", "/inventory/adjustments", { body: clean(adj) }));
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Product"
              required
              value={adj.product_id}
              onChange={(e) => setAdj({ ...adj, product_id: e.target.value })}
              options={productOptions}
            />
            <SelectField
              label="Warehouse"
              required
              value={adj.warehouse_id}
              onChange={(e) => setAdj({ ...adj, warehouse_id: e.target.value })}
              options={warehouseOptions}
            />
            <SelectField
              label="Type"
              value={adj.kind}
              onChange={(e) => setAdj({ ...adj, kind: e.target.value })}
              options={[
                { value: "adjustment", label: "Count adjustment" },
                { value: "opening", label: "Opening stock" },
                { value: "return_in", label: "Customer return (+)" },
                { value: "damage", label: "Damaged stock (−)" },
              ]}
            />
            <TextField
              label="Quantity (+ found, − lost)"
              required
              pattern="^-?\d{1,15}(\.\d{1,3})?$"
              value={adj.quantity}
              onChange={(e) => setAdj({ ...adj, quantity: e.target.value })}
            />
            <TextField
              label="Unit cost (for increases)"
              inputMode="decimal"
              value={adj.unit_cost}
              onChange={(e) => setAdj({ ...adj, unit_cost: e.target.value })}
            />
            <TextField
              label="Date"
              type="date"
              required
              value={adj.movement_date}
              onChange={(e) => setAdj({ ...adj, movement_date: e.target.value })}
            />
          </div>
          <TextField
            label="Reason"
            required
            minLength={3}
            value={adj.reason}
            onChange={(e) => setAdj({ ...adj, reason: e.target.value })}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Record
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={dialog === "transfer"} title="Transfer stock" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(() => send("POST", "/inventory/transfers", { body: clean(tr) }));
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Product"
              required
              value={tr.product_id}
              onChange={(e) => setTr({ ...tr, product_id: e.target.value })}
              options={productOptions}
            />
            <TextField
              label="Quantity"
              required
              inputMode="decimal"
              value={tr.quantity}
              onChange={(e) => setTr({ ...tr, quantity: e.target.value })}
            />
            <SelectField
              label="From"
              required
              value={tr.from_warehouse_id}
              onChange={(e) => setTr({ ...tr, from_warehouse_id: e.target.value })}
              options={warehouseOptions}
            />
            <SelectField
              label="To"
              required
              value={tr.to_warehouse_id}
              onChange={(e) => setTr({ ...tr, to_warehouse_id: e.target.value })}
              options={warehouseOptions}
            />
            <TextField
              label="Date"
              type="date"
              required
              value={tr.movement_date}
              onChange={(e) => setTr({ ...tr, movement_date: e.target.value })}
            />
            <TextField
              label="Note"
              value={tr.reason}
              onChange={(e) => setTr({ ...tr, reason: e.target.value })}
            />
          </div>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Transfer
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

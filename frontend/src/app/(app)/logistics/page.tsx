"use client";

import { useState } from "react";
import { LuAnchor, LuClock, LuPlus, LuTruck, LuUpload } from "react-icons/lu";

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
import { send, uploadFile } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { CURRENCIES, formatDate, formatMoney } from "@/lib/crm/types";
import {
  DOC_TYPES,
  label,
  SHIPMENT_STATUSES,
  type Shipment,
  type ShipmentDetail,
} from "@/lib/inventory/types";
import { formatDateTime } from "@/lib/tenders/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

export default function ShipmentsPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const shipments = useResource<Shipment[]>("/logistics/shipments");
  const summary = useResource<{
    has_records: boolean;
    active_shipments: number;
    late_shipments: number;
    at_customs: number;
  }>("/logistics/summary");
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useResource<ShipmentDetail>(selected ? `/logistics/shipments/${selected}` : null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    direction: "inbound",
    mode: "road",
    carrier: "",
    tracking_number: "",
    origin: "",
    destination: "",
    etd: "",
    eta: "",
    freight_cost: "",
    freight_currency: "",
  });
  const [status, setStatus] = useState({
    status: "in_transit",
    location: "",
    note: "",
    customs_entry_number: "",
  });
  const [docType, setDocType] = useState("commercial_invoice");
  const editable = can("logistics.records.edit");
  const s = summary.data;

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      play("complete");
      await Promise.all([shipments.reload(), summary.reload(), detail.reload()]);
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }
  const clean = (o: Record<string, string>) =>
    Object.fromEntries(Object.entries(o).filter(([, v]) => v !== ""));
  const d = detail.data;
  const closed = d && (d.shipment.status === "delivered" || d.shipment.status === "cancelled");

  return (
    <>
      <PageHeader
        eyebrow="Logistics"
        title="Shipments"
        description="Inbound and outbound freight with a status timeline and customs documents."
        actions={
          editable ? (
            <Button
              variant="primary"
              icon={<LuPlus aria-hidden="true" />}
              onClick={() => setCreating(true)}
            >
              New shipment
            </Button>
          ) : undefined
        }
      />
      <OpsNav section="logistics" />
      <FormError message={error ?? shipments.error} />
      <div className={page.grid}>
        <div className={page.span4}>
          <KpiCard
            icon={<LuTruck />}
            label="Active shipments"
            value={s?.has_records ? String(s.active_shipments) : null}
          />
        </div>
        <div className={page.span4}>
          <KpiCard
            icon={<LuClock />}
            label="Past expected arrival"
            value={s?.has_records ? String(s.late_shipments) : null}
          />
        </div>
        <div className={page.span4}>
          <KpiCard
            icon={<LuAnchor />}
            label="At customs"
            value={s?.has_records ? String(s.at_customs) : null}
          />
        </div>
        <div className={page.span7}>
          <Panel title="Shipments">
            {shipments.data && shipments.data.length === 0 ? (
              <EmptyState title="No shipments yet">
                Record inbound and outbound freight here.
              </EmptyState>
            ) : (
              <ul className={styles.timeline}>
                {shipments.data?.map((sh) => (
                  <li key={sh.id} className={styles.timelineItem}>
                    <Badge
                      tone={sh.late ? "danger" : sh.status === "delivered" ? "success" : "gold"}
                    >
                      {label(sh.status)}
                    </Badge>
                    <div>
                      <button
                        type="button"
                        className={styles.rowLink}
                        style={{
                          background: "none",
                          border: 0,
                          padding: 0,
                          cursor: "pointer",
                          font: "inherit",
                        }}
                        onClick={() => setSelected(sh.id)}
                      >
                        {sh.reference} · {sh.origin} → {sh.destination}
                      </button>
                      <div className={page.muted}>
                        {label(sh.direction)} · {sh.mode}
                        {sh.counterparty ? ` · ${sh.counterparty}` : ""} · ETA {formatDate(sh.eta)}
                        {sh.late ? " · late" : ""}
                      </div>
                    </div>
                    <span className={styles.ref}>{sh.tracking_number ?? ""}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
        <div className={page.span5}>
          <Panel title={d ? `${d.shipment.reference} timeline` : "Shipment details"}>
            {!d ? (
              <p className={page.muted}>Choose a shipment to see its timeline and documents.</p>
            ) : (
              <>
                <dl className={styles.facts}>
                  <dt>Carrier</dt>
                  <dd>{d.shipment.carrier ?? "—"}</dd>
                  <dt>Freight</dt>
                  <dd>
                    {d.shipment.freight_cost && d.shipment.freight_currency
                      ? formatMoney(d.shipment.freight_cost, d.shipment.freight_currency)
                      : "—"}
                  </dd>
                  <dt>Customs entry</dt>
                  <dd>{d.shipment.customs_entry_number ?? "—"}</dd>
                </dl>
                <ol
                  className={styles.timeline}
                  style={{ marginTop: 16 }}
                  aria-label="Shipment events"
                >
                  {d.events.map((ev, i) => (
                    <li key={i} className={styles.timelineItem}>
                      <Badge tone="neutral">{label(ev.status)}</Badge>
                      <div>
                        {formatDateTime(ev.occurred_at)}
                        {ev.location ? ` · ${ev.location}` : ""}
                        <div className={page.muted}>
                          {[ev.note, ev.recorded_by].filter(Boolean).join(" · ")}
                        </div>
                      </div>
                      <span />
                    </li>
                  ))}
                </ol>
                {editable && !closed && (
                  <form
                    className={styles.formGrid}
                    style={{ marginTop: 16, alignItems: "end" }}
                    onSubmit={(e) => {
                      e.preventDefault();
                      void act(() =>
                        send("POST", `/logistics/shipments/${d.shipment.id}/status`, {
                          body: clean(status),
                        }),
                      );
                    }}
                  >
                    <SelectField
                      label="New status"
                      value={status.status}
                      onChange={(e) => setStatus({ ...status, status: e.target.value })}
                      options={SHIPMENT_STATUSES.map((v) => ({ value: v, label: label(v) }))}
                    />
                    <TextField
                      label="Location"
                      value={status.location}
                      onChange={(e) => setStatus({ ...status, location: e.target.value })}
                    />
                    {status.status === "cleared" && (
                      <TextField
                        label="Customs entry number"
                        required
                        value={status.customs_entry_number}
                        onChange={(e) =>
                          setStatus({ ...status, customs_entry_number: e.target.value })
                        }
                      />
                    )}
                    <TextField
                      label="Note"
                      value={status.note}
                      onChange={(e) => setStatus({ ...status, note: e.target.value })}
                    />
                    <Button type="submit">Update status</Button>
                  </form>
                )}
                <h4 className="hud-label" style={{ marginTop: 20 }}>
                  Documents
                </h4>
                {d.documents.length === 0 ? (
                  <p className={page.muted}>No documents attached.</p>
                ) : (
                  <ul className={styles.timeline}>
                    {d.documents.map((doc) => (
                      <li key={doc.id} className={styles.timelineItem}>
                        <span className={styles.ref}>{label(doc.doc_type)}</span>
                        <div>{doc.file_name}</div>
                        <span />
                      </li>
                    ))}
                  </ul>
                )}
                {editable && (
                  <div className={page.actionsRow}>
                    <SelectField
                      label="Document type"
                      value={docType}
                      onChange={(e) => setDocType(e.target.value)}
                      options={DOC_TYPES.map((t) => ({ value: t, label: label(t) }))}
                    />
                    <label className={styles.check}>
                      <LuUpload aria-hidden="true" /> Attach file
                      <input
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file)
                            void act(async () => {
                              const up = await uploadFile(
                                file,
                                "logistics",
                                "logistics.records.view",
                              );
                              await send(
                                "POST",
                                `/logistics/shipments/${d.shipment.id}/documents`,
                                { body: { doc_type: docType, file_id: up.id } },
                              );
                            });
                          e.target.value = "";
                        }}
                      />
                    </label>
                  </div>
                )}
              </>
            )}
          </Panel>
        </div>
      </div>

      <Dialog open={creating} title="New shipment" onClose={() => setCreating(false)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(async () => {
              const { data } = await send<ShipmentDetail>("POST", "/logistics/shipments", {
                body: clean(form),
              });
              setSelected(data.shipment.id);
              setCreating(false);
            });
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Direction"
              value={form.direction}
              onChange={(e) => setForm({ ...form, direction: e.target.value })}
              options={[
                { value: "inbound", label: "Inbound" },
                { value: "outbound", label: "Outbound" },
              ]}
            />
            <SelectField
              label="Mode"
              value={form.mode}
              onChange={(e) => setForm({ ...form, mode: e.target.value })}
              options={["road", "air", "sea", "rail", "courier", "multimodal"].map((m) => ({
                value: m,
                label: label(m),
              }))}
            />
            <TextField
              label="Origin"
              required
              minLength={2}
              value={form.origin}
              onChange={(e) => setForm({ ...form, origin: e.target.value })}
            />
            <TextField
              label="Destination"
              required
              minLength={2}
              value={form.destination}
              onChange={(e) => setForm({ ...form, destination: e.target.value })}
            />
            <TextField
              label="Carrier"
              value={form.carrier}
              onChange={(e) => setForm({ ...form, carrier: e.target.value })}
            />
            <TextField
              label="Tracking number"
              value={form.tracking_number}
              onChange={(e) => setForm({ ...form, tracking_number: e.target.value })}
            />
            <TextField
              label="Departs"
              type="date"
              value={form.etd}
              onChange={(e) => setForm({ ...form, etd: e.target.value })}
            />
            <TextField
              label="Expected arrival"
              type="date"
              value={form.eta}
              onChange={(e) => setForm({ ...form, eta: e.target.value })}
            />
            <TextField
              label="Freight cost"
              inputMode="decimal"
              value={form.freight_cost}
              onChange={(e) => setForm({ ...form, freight_cost: e.target.value })}
            />
            <SelectField
              label="Freight currency"
              value={form.freight_currency}
              onChange={(e) => setForm({ ...form, freight_currency: e.target.value })}
              options={[
                { value: "", label: "—" },
                ...CURRENCIES.map((c) => ({ value: c, label: c })),
              ]}
            />
          </div>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create shipment
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

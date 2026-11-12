"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { LuPlus } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
import { ProcurementNav } from "@/components/procurement/ProcurementNav";
import {
  Badge,
  Button,
  Dialog,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SelectField,
  Spinner,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { CURRENCIES, formatDate, formatMoney } from "@/lib/crm/types";
import {
  REQUEST_STATUS_LABEL,
  type Page,
  type PurchaseOrder,
  type PurchaseRequestDetail,
  type Supplier,
} from "@/lib/procurement/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

export default function PurchaseRequestPage() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAuth();
  const { play } = useSound();
  const { data, error, loading, reload } = useResource<PurchaseRequestDetail>(
    `/procurement/requests/${id}`,
  );
  const suppliers = useResource<Page<Supplier>>(
    can("procurement.records.edit") ? "/procurement/suppliers?size=100" : null,
  );
  const [dialog, setDialog] = useState<"quote" | "submit" | "order" | null>(null);
  const [quote, setQuote] = useState({
    supplier_id: "",
    currency: "MWK",
    valid_until: "",
    supplier_reference: "",
  });
  const [prices, setPrices] = useState<Record<string, string>>({});
  const [choice, setChoice] = useState("");
  const [note, setNote] = useState("");
  const [address, setAddress] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const editable = can("procurement.records.edit");

  async function act(
    fn: () => Promise<unknown>,
    cue: "approval" | "complete" | "navigation" = "navigation",
  ) {
    setActionError(null);
    try {
      await fn();
      play(cue);
      setDialog(null);
      await reload();
    } catch (e) {
      setActionError(errorMessage(e));
      play("warning");
    }
  }

  if (loading && !data) return <Spinner label="Loading purchase request" />;
  if (!data)
    return (
      <EmptyState title="Not available">{error ?? "This request could not be loaded."}</EmptyState>
    );
  const { request: r, lines, quotes } = data;
  const draft = r.status === "draft";

  return (
    <>
      <PageHeader
        eyebrow={r.reference}
        title={r.title}
        description={r.justification ?? undefined}
        actions={
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
        }
      />
      <ProcurementNav />
      <FormError message={actionError} />
      <div className={page.grid}>
        <div className={page.span12}>
          <Panel
            title="Quotation comparison"
            actions={
              editable && draft ? (
                <Button
                  size="sm"
                  icon={<LuPlus aria-hidden="true" />}
                  onClick={() => {
                    setPrices({});
                    setDialog("quote");
                  }}
                >
                  Add quotation
                </Button>
              ) : undefined
            }
          >
            <div className={page.tableWrap}>
              <table className={page.table}>
                <thead>
                  <tr>
                    <th scope="col">Item</th>
                    <th scope="col">Qty</th>
                    {quotes.map((q) => (
                      <th key={q.id} scope="col">
                        {q.supplier_name}
                        <div className={styles.ref}>
                          {q.currency}
                          {q.supplier_status !== "verified" && " · not verified"}
                          {q.expired && " · expired"}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line) => (
                    <tr key={line.id}>
                      <td>{line.description}</td>
                      <td className="tabular">{`${Number(line.quantity)} ${line.unit}`}</td>
                      {quotes.map((q) => (
                        <td key={q.id} className="tabular">
                          {q.prices[line.id] ?? <span className={page.muted}>not priced</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <th scope="row">Total</th>
                    <td />
                    {quotes.map((q) => (
                      <td key={q.id} className={styles.amount}>
                        {formatMoney(q.total, q.currency)}{" "}
                        {q.id === data.cheapest_complete_quote_id && (
                          <Badge tone="success">Lowest valid</Badge>
                        )}
                        {q.id === r.selected_quote_id && <Badge tone="gold">Selected</Badge>}
                        {!q.complete && <Badge tone="warning">Incomplete</Badge>}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
            <p className={page.note}>
              {quotes.length === 0
                ? "No quotations yet. Collect at least one per supplier."
                : data.comparison_note}
            </p>
          </Panel>
        </div>
        <div className={page.span12}>
          <Panel title="Approval and order">
            {editable ? (
              <div className={page.actionsRow}>
                {draft && (
                  <Button
                    size="sm"
                    variant="primary"
                    disabled={!quotes.some((q) => q.complete)}
                    onClick={() => {
                      setChoice(data.cheapest_complete_quote_id ?? "");
                      setNote("");
                      setDialog("submit");
                    }}
                  >
                    Send for Director approval
                  </Button>
                )}
                {r.status === "approved" && (
                  <Button size="sm" variant="primary" onClick={() => setDialog("order")}>
                    Issue purchase order
                  </Button>
                )}
                {r.status === "awaiting_approval" && (
                  <span className={page.muted}>Waiting for the Director.</span>
                )}
                {r.order_id && (
                  <Link href="/procurement/orders" className={page.inlineLink}>
                    View purchase order
                  </Link>
                )}
              </div>
            ) : (
              <p className={page.muted}>View only.</p>
            )}
            <p className={page.note}>
              Needed by {formatDate(r.needed_by)} · requested by{" "}
              {r.requested_by?.display_name ?? "—"}
            </p>
          </Panel>
        </div>
      </div>

      <Dialog
        open={dialog === "quote"}
        title="Add supplier quotation"
        onClose={() => setDialog(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const body = {
              supplier_id: quote.supplier_id,
              currency: quote.currency,
              ...(quote.valid_until ? { valid_until: quote.valid_until } : {}),
              ...(quote.supplier_reference ? { supplier_reference: quote.supplier_reference } : {}),
              lines: Object.entries(prices)
                .filter(([, v]) => v !== "")
                .map(([request_line_id, unit_price]) => ({ request_line_id, unit_price })),
            };
            void act(() => send("POST", `/procurement/requests/${r.id}/quotes`, { body }));
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Supplier"
              required
              value={quote.supplier_id}
              onChange={(e) => setQuote({ ...quote, supplier_id: e.target.value })}
              options={[
                { value: "", label: "Choose a supplier" },
                ...(suppliers.data?.items ?? [])
                  .filter((s) => s.status !== "suspended")
                  .map((s) => ({
                    value: s.id,
                    label: `${s.name}${s.status === "verified" ? "" : " (not verified)"}`,
                  })),
              ]}
            />
            <SelectField
              label="Quote currency"
              value={quote.currency}
              onChange={(e) => setQuote({ ...quote, currency: e.target.value })}
              options={CURRENCIES.map((c) => ({ value: c, label: c }))}
            />
            <TextField
              label="Valid until"
              type="date"
              value={quote.valid_until}
              onChange={(e) => setQuote({ ...quote, valid_until: e.target.value })}
            />
            <TextField
              label="Supplier's quote number"
              value={quote.supplier_reference}
              onChange={(e) => setQuote({ ...quote, supplier_reference: e.target.value })}
            />
            {lines.map((line) => (
              <TextField
                key={line.id}
                label={`Unit price: ${line.description}`}
                inputMode="decimal"
                pattern="^\d{1,14}(\.\d{1,4})?$"
                value={prices[line.id] ?? ""}
                onChange={(e) => setPrices({ ...prices, [line.id]: e.target.value })}
              />
            ))}
          </div>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save quotation
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={dialog === "submit"}
        title="Send for Director approval"
        onClose={() => setDialog(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(
              () =>
                send("POST", `/procurement/requests/${r.id}/submit`, {
                  body: { quote_id: choice, ...(note ? { note } : {}) },
                }),
              "approval",
            );
          }}
        >
          <SelectField
            label="Chosen quotation"
            value={choice}
            onChange={(e) => setChoice(e.target.value)}
            options={quotes
              .filter((q) => q.complete)
              .map((q) => ({
                value: q.id,
                label: `${q.supplier_name} · ${formatMoney(q.total, q.currency)}`,
              }))}
          />
          <TextField
            label="Note for the Director"
            hint={
              choice && choice !== data.cheapest_complete_quote_id
                ? "Required: explain why the lowest valid quotation was not chosen."
                : undefined
            }
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Send
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={dialog === "order"}
        title="Issue purchase order"
        onClose={() => setDialog(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(
              () =>
                send<PurchaseOrder>("POST", `/procurement/requests/${r.id}/order`, {
                  body: address ? { delivery_address: address } : {},
                }),
              "complete",
            );
          }}
        >
          <TextField
            label="Delivery address"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Issue order
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

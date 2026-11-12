"use client";

import { useState } from "react";

import styles from "@/components/crm/crm.module.css";
import { ProcurementNav } from "@/components/procurement/ProcurementNav";
import {
  Badge,
  Button,
  FormError,
  PageHeader,
  Panel,
  SelectField,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/useResource";
import { CURRENCIES, formatMoney } from "@/lib/crm/types";
import type { LandedCostResult } from "@/lib/procurement/types";

import page from "@/app/pages.module.css";

const DECIMAL = "^\\d{1,16}(\\.\\d{1,6})?$";

export default function LandedCostPage() {
  const [form, setForm] = useState({
    goods_value: "",
    supplier_currency: "USD",
    freight: "0",
    insurance: "0",
    exchange_rate: "",
    exchange_rate_source: "",
    duty_rate_pct: "",
    excise_rate_pct: "0",
    vat_rate_pct: "",
    vat_recoverable: true,
    local_charges: "0",
    quantity: "",
  });
  const [result, setResult] = useState<LandedCostResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const field = (key: keyof typeof form, label: string, hint?: string, required = true) => (
    <TextField
      label={label}
      hint={hint}
      required={required}
      inputMode="decimal"
      pattern={DECIMAL}
      value={String(form[key])}
      onChange={(e) => setForm({ ...form, [key]: e.target.value })}
    />
  );

  return (
    <>
      <PageHeader
        eyebrow="Procurement"
        title="Landed-cost estimate"
        description="Customs value, duty, excise, VAT and local charges for an import. You enter every rate: none is built in."
      />
      <ProcurementNav />
      <div className={page.grid}>
        <div className={page.span7}>
          <Panel title="Inputs">
            <form
              className={styles.dialogForm}
              style={{ minWidth: 0 }}
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                const body = Object.fromEntries(
                  Object.entries(form).filter(([k, v]) => !(k === "quantity" && v === "")),
                );
                send<LandedCostResult>("POST", "/procurement/landed-cost", { body })
                  .then(({ data }) => setResult(data))
                  .catch((err: unknown) => setError(errorMessage(err)));
              }}
            >
              <div className={styles.formGrid}>
                {field("goods_value", "Goods value (supplier currency)")}
                <SelectField
                  label="Supplier currency"
                  value={form.supplier_currency}
                  onChange={(e) => setForm({ ...form, supplier_currency: e.target.value })}
                  options={CURRENCIES.map((c) => ({ value: c, label: c }))}
                />
                {field("freight", "Freight (supplier currency)")}
                {field("insurance", "Insurance (supplier currency)")}
                {field(
                  "exchange_rate",
                  "Exchange rate",
                  "Functional currency per 1 unit of supplier currency",
                )}
                <TextField
                  label="Exchange rate source"
                  required
                  minLength={2}
                  placeholder="e.g. bank quote 12 Nov"
                  value={form.exchange_rate_source}
                  onChange={(e) => setForm({ ...form, exchange_rate_source: e.target.value })}
                />
                {field(
                  "duty_rate_pct",
                  "Import duty %",
                  "From the current tariff for this HS code",
                )}
                {field("excise_rate_pct", "Excise %")}
                {field("vat_rate_pct", "VAT %", "Confirm the current rate")}
                {field("local_charges", "Clearing, port and transport (functional currency)")}
                {field("quantity", "Quantity (for unit cost)", undefined, false)}
              </div>
              <label className={styles.check}>
                <input
                  type="checkbox"
                  checked={form.vat_recoverable}
                  onChange={(e) => setForm({ ...form, vat_recoverable: e.target.checked })}
                />
                Import VAT is recoverable (excluded from cost)
              </label>
              <FormError message={error} />
              <div className={styles.dialogActions}>
                <Button type="submit" variant="primary">
                  Calculate estimate
                </Button>
              </div>
            </form>
          </Panel>
        </div>
        <div className={page.span5}>
          <Panel
            title="Estimate"
            actions={result ? <Badge tone="warning">Estimate</Badge> : undefined}
          >
            {result ? (
              <>
                <dl className={styles.facts}>
                  <dt>Customs value (CIF)</dt>
                  <dd className="tabular">
                    {formatMoney(result.customs_value, result.functional_currency)}
                  </dd>
                  <dt>Import duty</dt>
                  <dd className="tabular">
                    {formatMoney(result.duty, result.functional_currency)}
                  </dd>
                  <dt>Excise</dt>
                  <dd className="tabular">
                    {formatMoney(result.excise, result.functional_currency)}
                  </dd>
                  <dt>VAT {result.vat_included_in_cost ? "(in cost)" : "(recoverable)"}</dt>
                  <dd className="tabular">{formatMoney(result.vat, result.functional_currency)}</dd>
                  <dt>Local charges</dt>
                  <dd className="tabular">
                    {formatMoney(result.local_charges, result.functional_currency)}
                  </dd>
                  <dt>
                    <strong>Landed cost</strong>
                  </dt>
                  <dd className={styles.amount} data-testid="landed-cost-total">
                    {formatMoney(result.landed_cost, result.functional_currency)}
                  </dd>
                  {result.unit_cost && (
                    <>
                      <dt>Per unit</dt>
                      <dd className="tabular">
                        {formatMoney(result.unit_cost, result.functional_currency)}
                      </dd>
                    </>
                  )}
                </dl>
                <p className={page.note}>
                  Rate {result.exchange_rate} ({result.exchange_rate_source}). {result.note}
                </p>
              </>
            ) : (
              <p className={page.muted}>Enter the values and rates to see the estimate.</p>
            )}
          </Panel>
        </div>
      </div>
    </>
  );
}

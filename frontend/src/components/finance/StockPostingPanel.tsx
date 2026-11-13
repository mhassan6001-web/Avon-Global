"use client";

import { useEffect, useState } from "react";

import styles from "@/components/crm/crm.module.css";
import { Badge, Button, FormError, Panel, SelectField, TextField } from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useStepUp } from "@/lib/auth/StepUpProvider";
import { formatMoney } from "@/lib/crm/types";
import type { Account } from "@/lib/finance/types";

import page from "@/app/pages.module.css";

interface Config {
  enabled: boolean;
  inventory_account_id: string | null;
  grni_account_id: string | null;
  cogs_account_id: string | null;
  adjustment_account_id: string | null;
  opening_account_id: string | null;
  reviewed_by_name: string | null;
  reviewed_on: string | null;
  valuation_method: string;
}

interface Reconciliation {
  as_of: string;
  posting_enabled: boolean;
  functional_currency: string;
  stock_value: string;
  ledger_balance: string | null;
  difference: string | null;
  movements_not_posted: number;
  reconciled: boolean;
}

const FIELDS = [
  { key: "inventory_account_id", label: "Inventory (asset)" },
  { key: "grni_account_id", label: "Goods received not invoiced" },
  { key: "cogs_account_id", label: "Cost of sales (expense)" },
  { key: "adjustment_account_id", label: "Stock adjustments and damage" },
  { key: "opening_account_id", label: "Opening stock balance" },
] as const;

/** Perpetual inventory accounting: account mapping, switch and reconciliation. */
export function StockPostingPanel({ accounts }: { accounts: Account[] }) {
  const { can } = useAuth();
  const withStepUp = useStepUp();
  const config = useResource<Config>("/finance/stock-posting");
  const rec = useResource<Reconciliation>("/finance/reports/stock-reconciliation");
  const [form, setForm] = useState<Config | null>(null);
  const [error, setError] = useState<string | null>(null);
  const director = can("finance.transaction.approve");
  useEffect(() => {
    if (config.data) setForm(config.data);
  }, [config.data]);
  if (!form) return null;
  const options = [
    { value: "", label: "Not set" },
    ...accounts
      .filter((a) => a.is_active)
      .map((a) => ({ value: a.id, label: `${a.code} ${a.name}` })),
  ];

  async function save() {
    if (!form) return;
    setError(null);
    const body: Record<string, unknown> = { ...form };
    delete body.valuation_method;
    try {
      await withStepUp(() => send("PUT", "/finance/stock-posting", { body }).then(() => undefined));
      await Promise.all([config.reload(), rec.reload()]);
    } catch (e) {
      if (e && typeof e === "object" && "code" in e && (e as { code: string }).code === "cancelled")
        return;
      setError(errorMessage(e));
    }
  }

  return (
    <Panel title="Stock accounting (perpetual inventory)">
      <p className={page.muted}>
        When switched on, every stock movement posts its accounting entry at once, valued at
        weighted-average cost. Keep it off until a qualified accountant has approved the valuation
        method and these accounts.
      </p>
      <FormError message={error ?? config.error} />
      <div className={styles.formGrid}>
        {FIELDS.map((f) => (
          <SelectField
            key={f.key}
            label={f.label}
            value={form[f.key] ?? ""}
            disabled={!director}
            onChange={(e) => setForm({ ...form, [f.key]: e.target.value || null })}
            options={options}
          />
        ))}
        <TextField
          label="Accountant who approved the method"
          value={form.reviewed_by_name ?? ""}
          disabled={!director}
          onChange={(e) => setForm({ ...form, reviewed_by_name: e.target.value || null })}
        />
        <TextField
          label="Approved on"
          type="date"
          value={form.reviewed_on ?? ""}
          disabled={!director}
          onChange={(e) => setForm({ ...form, reviewed_on: e.target.value || null })}
        />
        <label className={styles.check}>
          <input
            type="checkbox"
            checked={form.enabled}
            disabled={!director}
            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
          />
          Post stock movements to the ledger
        </label>
      </div>
      {director ? (
        <Button onClick={() => void save()}>Save stock accounting</Button>
      ) : (
        <p className={page.note}>Only the Director can change these settings.</p>
      )}
      {rec.data && (
        <p className={page.note}>
          <Badge tone={rec.data.reconciled ? "success" : "warning"}>
            {rec.data.reconciled ? "Reconciled" : "Not reconciled"}
          </Badge>{" "}
          Stock value {formatMoney(rec.data.stock_value, rec.data.functional_currency)}
          {rec.data.ledger_balance !== null &&
            `; inventory account ${formatMoney(rec.data.ledger_balance, rec.data.functional_currency)}; difference ${formatMoney(rec.data.difference ?? "0", rec.data.functional_currency)}`}
          . Movements without an accounting entry: {rec.data.movements_not_posted}.
        </p>
      )}
    </Panel>
  );
}

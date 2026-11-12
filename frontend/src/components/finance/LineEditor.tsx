"use client";

import { LuPlus, LuTrash2 } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
import { Button, IconButton, SelectField, TextField } from "@/components/ui";
import type { Account, TaxCode } from "@/lib/finance/types";

export interface LineDraft {
  description: string;
  quantity: string;
  unit_price: string;
  account_id: string;
  tax_code_id: string;
}

export const emptyLine = (): LineDraft => ({
  description: "",
  quantity: "1",
  unit_price: "",
  account_id: "",
  tax_code_id: "",
});

/** Invoice/bill line editor: account and optional tax code per line. */
export function LineEditor({
  lines,
  onChange,
  accounts,
  taxCodes,
  accountLabel,
}: {
  lines: LineDraft[];
  onChange: (lines: LineDraft[]) => void;
  accounts: Account[];
  taxCodes: TaxCode[];
  accountLabel: string;
}) {
  const set = (i: number, patch: Partial<LineDraft>) =>
    onChange(lines.map((l, k) => (k === i ? { ...l, ...patch } : l)));
  return (
    <fieldset style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
      <legend className="hud-label">Lines</legend>
      {lines.map((line, i) => (
        <div
          key={i}
          className={styles.formGrid}
          style={{ gridTemplateColumns: "2fr 0.7fr 1fr 1.4fr 1.2fr auto", alignItems: "end" }}
        >
          <TextField
            label={`Description ${i + 1}`}
            required
            minLength={2}
            value={line.description}
            onChange={(e) => set(i, { description: e.target.value })}
          />
          <TextField
            label={`Qty ${i + 1}`}
            required
            inputMode="decimal"
            pattern="^\d{1,15}(\.\d{1,3})?$"
            value={line.quantity}
            onChange={(e) => set(i, { quantity: e.target.value })}
          />
          <TextField
            label={`Unit price ${i + 1}`}
            required
            inputMode="decimal"
            pattern="^\d{1,14}(\.\d{1,4})?$"
            value={line.unit_price}
            onChange={(e) => set(i, { unit_price: e.target.value })}
          />
          <SelectField
            label={`${accountLabel} ${i + 1}`}
            required
            value={line.account_id}
            onChange={(e) => set(i, { account_id: e.target.value })}
            options={[
              { value: "", label: "Choose" },
              ...accounts.map((a) => ({ value: a.id, label: `${a.code} ${a.name}` })),
            ]}
          />
          <SelectField
            label={`Tax ${i + 1}`}
            value={line.tax_code_id}
            onChange={(e) => set(i, { tax_code_id: e.target.value })}
            options={[
              { value: "", label: "No tax" },
              ...taxCodes.map((t) => ({
                value: t.id,
                label: `${t.code} (${Number(t.rate_pct)}%)`,
              })),
            ]}
          />
          <IconButton
            label={`Remove line ${i + 1}`}
            disabled={lines.length === 1}
            onClick={() => onChange(lines.filter((_, k) => k !== i))}
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
          onClick={() => onChange([...lines, emptyLine()])}
        >
          Add line
        </Button>
      </div>
    </fieldset>
  );
}

/** Strip empty optional fields before sending. */
export function linesBody(lines: LineDraft[]) {
  return lines.map((l) => ({
    description: l.description,
    quantity: l.quantity,
    unit_price: l.unit_price,
    account_id: l.account_id,
    ...(l.tax_code_id ? { tax_code_id: l.tax_code_id } : {}),
  }));
}

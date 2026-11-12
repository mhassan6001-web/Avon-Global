"use client";

import { useState } from "react";

import styles from "@/components/crm/crm.module.css";
import { Button, Dialog, FormError, SelectField, TextField } from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/useResource";
import { COUNTRIES, CURRENCIES, DIVISION_LABEL, DIVISIONS } from "@/lib/crm/types";
import {
  KIND_LABEL,
  METHOD_LABEL,
  METHODS,
  TENDER_KINDS,
  type TenderDetail,
} from "@/lib/tenders/types";

/** Convert a local datetime-local value to an ISO string with the browser's offset. */
function toIso(local: string): string | undefined {
  return local ? new Date(local).toISOString() : undefined;
}

export function TenderDialog({
  open,
  onClose,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: (t: TenderDetail) => void;
}) {
  const [form, setForm] = useState({
    title: "",
    issuer_name: "",
    issuer_reference: "",
    kind: "rfq",
    division: "",
    country_code: "MW",
    source: "",
    clarification_deadline: "",
    submission_deadline: "",
    submission_method: "email",
    estimated_value: "",
    currency: "MWK",
    bid_security_required: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });

  return (
    <Dialog open={open} title="New tender" onClose={onClose}>
      <form
        className={styles.dialogForm}
        onSubmit={(e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          const body = Object.fromEntries(
            Object.entries({
              ...form,
              clarification_deadline: toIso(form.clarification_deadline),
              submission_deadline: toIso(form.submission_deadline),
            }).filter(([, v]) => v !== "" && v !== undefined),
          );
          send<TenderDetail>("POST", "/tenders", { body })
            .then(({ data }) => {
              onSaved(data);
              onClose();
            })
            .catch((err: unknown) => setError(errorMessage(err)))
            .finally(() => setBusy(false));
        }}
      >
        <div className={styles.formGrid}>
          <TextField
            label="Tender title"
            required
            minLength={3}
            maxLength={300}
            value={form.title}
            onChange={set("title")}
          />
          <TextField
            label="Issuer"
            required
            minLength={2}
            maxLength={200}
            value={form.issuer_name}
            onChange={set("issuer_name")}
          />
          <TextField
            label="Issuer's reference"
            maxLength={120}
            value={form.issuer_reference}
            onChange={set("issuer_reference")}
          />
          <SelectField
            label="Type"
            value={form.kind}
            onChange={set("kind")}
            options={TENDER_KINDS.map((k) => ({ value: k, label: KIND_LABEL[k] }))}
          />
          <SelectField
            label="Division"
            value={form.division}
            onChange={set("division")}
            options={[
              { value: "", label: "Not set" },
              ...DIVISIONS.map((d) => ({ value: d, label: DIVISION_LABEL[d] })),
            ]}
          />
          <SelectField
            label="Country"
            value={form.country_code}
            onChange={set("country_code")}
            options={COUNTRIES}
          />
          <TextField
            label="Submission deadline"
            type="datetime-local"
            required
            value={form.submission_deadline}
            onChange={set("submission_deadline")}
          />
          <TextField
            label="Clarification deadline"
            type="datetime-local"
            value={form.clarification_deadline}
            onChange={set("clarification_deadline")}
          />
          <SelectField
            label="Submission method"
            value={form.submission_method}
            onChange={set("submission_method")}
            options={METHODS.map((m) => ({ value: m, label: METHOD_LABEL[m] }))}
          />
          <TextField
            label="Where it was published"
            maxLength={300}
            value={form.source}
            onChange={set("source")}
          />
          <TextField
            label="Estimated value"
            inputMode="decimal"
            pattern="^\d{1,16}(\.\d{1,2})?$"
            value={form.estimated_value}
            onChange={set("estimated_value")}
          />
          <SelectField
            label="Currency"
            value={form.currency}
            onChange={set("currency")}
            options={CURRENCIES.map((c) => ({ value: c, label: c }))}
          />
        </div>
        <label className={styles.check}>
          <input
            type="checkbox"
            checked={form.bid_security_required}
            onChange={(e) => setForm({ ...form, bid_security_required: e.target.checked })}
          />
          Bid security required
        </label>
        <FormError message={error} />
        <div className={styles.dialogActions}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={busy}>
            Add tender
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

"use client";

import { useState, type ReactNode } from "react";

import { Button, Dialog, FormError, SelectField, TextField } from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/useResource";
import {
  ACTIVITY_KINDS,
  ACTIVITY_LABEL,
  COUNTRIES,
  CURRENCIES,
  CUSTOMER_KINDS,
  DIVISION_LABEL,
  DIVISIONS,
  KIND_LABEL,
  type Activity,
  type Contact,
  type Customer,
  type Opportunity,
} from "@/lib/crm/types";

import styles from "./crm.module.css";

/** Remove empty strings so optional fields are sent as absent. */
function compact<T extends Record<string, unknown>>(values: T): Partial<T> {
  return Object.fromEntries(Object.entries(values).filter(([, v]) => v !== "")) as Partial<T>;
}

function FormDialog({
  open,
  title,
  submitLabel,
  onClose,
  onSubmit,
  children,
}: {
  open: boolean;
  title: string;
  submitLabel: string;
  onClose: () => void;
  onSubmit: () => Promise<void>;
  children: ReactNode;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <Dialog open={open} title={title} onClose={onClose}>
      <form
        className={styles.dialogForm}
        onSubmit={(e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          onSubmit()
            .then(onClose)
            .catch((err: unknown) => setError(errorMessage(err)))
            .finally(() => setBusy(false));
        }}
      >
        {children}
        <FormError message={error} />
        <div className={styles.dialogActions}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={busy}>
            {submitLabel}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

export function CustomerDialog({
  open,
  onClose,
  onSaved,
  customer,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: (customer: Customer) => void;
  customer?: Customer;
}) {
  const [form, setForm] = useState({
    name: customer?.name ?? "",
    kind: customer?.kind ?? "organisation",
    status: customer?.status === "archived" ? "inactive" : (customer?.status ?? "prospect"),
    country_code: customer?.country_code ?? "MW",
    city: customer?.city ?? "",
    industry: customer?.industry ?? "",
    email: customer?.email ?? "",
    phone: customer?.phone ?? "",
    notes: customer?.notes ?? "",
  });
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });
  return (
    <FormDialog
      open={open}
      title={customer ? `Edit ${customer.name}` : "New customer"}
      submitLabel={customer ? "Save changes" : "Create customer"}
      onClose={onClose}
      onSubmit={async () => {
        const body = customer
          ? Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v === "" ? null : v]))
          : compact(form);
        const { data } = await send<Customer>(
          customer ? "PATCH" : "POST",
          customer ? `/crm/customers/${customer.id}` : "/crm/customers",
          { body },
        );
        onSaved(data);
      }}
    >
      <div className={styles.formGrid}>
        <TextField
          label="Name"
          required
          minLength={2}
          maxLength={200}
          value={form.name}
          onChange={set("name")}
        />
        <SelectField
          label="Type"
          value={form.kind}
          onChange={set("kind")}
          options={CUSTOMER_KINDS.map((k) => ({ value: k, label: KIND_LABEL[k] }))}
        />
        <SelectField
          label="Status"
          value={form.status}
          onChange={set("status")}
          options={[
            { value: "prospect", label: "Prospect" },
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
          ]}
        />
        <SelectField
          label="Country"
          value={form.country_code}
          onChange={set("country_code")}
          options={COUNTRIES}
        />
        <TextField label="City" maxLength={120} value={form.city} onChange={set("city")} />
        <TextField
          label="Industry"
          maxLength={120}
          value={form.industry}
          onChange={set("industry")}
        />
        <TextField
          label="Email"
          type="email"
          maxLength={320}
          value={form.email}
          onChange={set("email")}
        />
        <TextField
          label="Phone"
          type="tel"
          maxLength={40}
          value={form.phone}
          onChange={set("phone")}
        />
      </div>
      <label className={styles.textareaLabel}>
        Notes
        <textarea
          className={styles.textarea}
          rows={3}
          maxLength={5000}
          value={form.notes}
          onChange={set("notes")}
        />
      </label>
    </FormDialog>
  );
}

export function ContactDialog({
  open,
  onClose,
  onSaved,
  customerId,
  contact,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  customerId: string;
  contact?: Contact;
}) {
  const [form, setForm] = useState({
    name: contact?.name ?? "",
    job_title: contact?.job_title ?? "",
    email: contact?.email ?? "",
    phone: contact?.phone ?? "",
    is_primary: contact?.is_primary ?? false,
  });
  return (
    <FormDialog
      open={open}
      title={contact ? "Edit contact" : "Add contact"}
      submitLabel={contact ? "Save contact" : "Add contact"}
      onClose={onClose}
      onSubmit={async () => {
        const body = compact(form);
        if (contact) await send("PUT", `/crm/contacts/${contact.id}`, { body });
        else await send("POST", `/crm/customers/${customerId}/contacts`, { body });
        onSaved();
      }}
    >
      <div className={styles.formGrid}>
        <TextField
          label="Contact name"
          required
          minLength={2}
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <TextField
          label="Job title"
          value={form.job_title}
          onChange={(e) => setForm({ ...form, job_title: e.target.value })}
        />
        <TextField
          label="Contact email"
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <TextField
          label="Contact phone"
          type="tel"
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
        />
      </div>
      <label className={styles.check}>
        <input
          type="checkbox"
          checked={form.is_primary}
          onChange={(e) => setForm({ ...form, is_primary: e.target.checked })}
        />
        Primary contact
      </label>
    </FormDialog>
  );
}

export function OpportunityDialog({
  open,
  onClose,
  onSaved,
  customerId,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: (opportunity: Opportunity) => void;
  customerId: string;
}) {
  const [form, setForm] = useState({
    title: "",
    division: "general_supplies",
    value_amount: "",
    currency: "MWK",
    probability: "10",
    expected_close: "",
  });
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });
  return (
    <FormDialog
      open={open}
      title="New opportunity"
      submitLabel="Create opportunity"
      onClose={onClose}
      onSubmit={async () => {
        const body = {
          ...compact(form),
          customer_id: customerId,
          probability: Number(form.probability),
        };
        const { data } = await send<Opportunity>("POST", "/crm/opportunities", { body });
        onSaved(data);
      }}
    >
      <div className={styles.formGrid}>
        <TextField
          label="Title"
          required
          minLength={2}
          value={form.title}
          onChange={set("title")}
        />
        <SelectField
          label="Division"
          value={form.division}
          onChange={set("division")}
          options={DIVISIONS.map((d) => ({ value: d, label: DIVISION_LABEL[d] }))}
        />
        <TextField
          label="Estimated value"
          inputMode="decimal"
          pattern="^\d{1,16}(\.\d{1,2})?$"
          hint="Optional. An estimate, not revenue."
          value={form.value_amount}
          onChange={set("value_amount")}
        />
        <SelectField
          label="Currency"
          value={form.currency}
          onChange={set("currency")}
          options={CURRENCIES.map((c) => ({ value: c, label: c }))}
        />
        <TextField
          label="Probability %"
          type="number"
          min={0}
          max={100}
          value={form.probability}
          onChange={set("probability")}
        />
        <TextField
          label="Expected close"
          type="date"
          value={form.expected_close}
          onChange={set("expected_close")}
        />
      </div>
    </FormDialog>
  );
}

export function ActivityDialog({
  open,
  onClose,
  onSaved,
  customerId,
  defaultKind = "note",
}: {
  open: boolean;
  onClose: () => void;
  onSaved: (activity: Activity) => void;
  customerId: string;
  defaultKind?: (typeof ACTIVITY_KINDS)[number];
}) {
  const [form, setForm] = useState({
    kind: defaultKind as string,
    subject: "",
    body: "",
    due_at: "",
  });
  const followUp = form.kind === "follow_up";
  return (
    <FormDialog
      open={open}
      title="Log activity"
      submitLabel="Save activity"
      onClose={onClose}
      onSubmit={async () => {
        const body = {
          customer_id: customerId,
          kind: form.kind,
          subject: form.subject,
          ...(form.body ? { body: form.body } : {}),
          ...(followUp && form.due_at ? { due_at: new Date(form.due_at).toISOString() } : {}),
        };
        const { data } = await send<Activity>("POST", "/crm/activities", { body });
        onSaved(data);
      }}
    >
      <div className={styles.formGrid}>
        <SelectField
          label="Kind"
          value={form.kind}
          onChange={(e) => setForm({ ...form, kind: e.target.value })}
          options={ACTIVITY_KINDS.map((k) => ({ value: k, label: ACTIVITY_LABEL[k] }))}
        />
        <TextField
          label="Subject"
          required
          minLength={2}
          value={form.subject}
          onChange={(e) => setForm({ ...form, subject: e.target.value })}
        />
        {followUp && (
          <TextField
            label="Due"
            type="datetime-local"
            required
            value={form.due_at}
            onChange={(e) => setForm({ ...form, due_at: e.target.value })}
          />
        )}
      </div>
      <label className={styles.textareaLabel}>
        Details
        <textarea
          className={styles.textarea}
          rows={3}
          value={form.body}
          onChange={(e) => setForm({ ...form, body: e.target.value })}
        />
      </label>
    </FormDialog>
  );
}

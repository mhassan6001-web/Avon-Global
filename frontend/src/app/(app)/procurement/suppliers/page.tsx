"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
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
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { COUNTRIES, query } from "@/lib/crm/types";
import { SUPPLIER_STATUSES, type Page, type Supplier } from "@/lib/procurement/types";

import page from "@/app/pages.module.css";

export default function SuppliersPage() {
  const { can } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const { data, error } = useResource<Page<Supplier>>(
    `/procurement/suppliers${query({ q: q.trim(), status, size: 100 })}`,
  );
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    country_code: "MW",
    city: "",
    categories: "",
    contact_name: "",
    email: "",
    phone: "",
  });
  const [formError, setFormError] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Procurement"
        title="Suppliers"
        description="Supplier register and verification. Bank details are encrypted and change only with Director approval."
        actions={
          can("procurement.records.edit") ? (
            <Button
              variant="primary"
              icon={<LuPlus aria-hidden="true" />}
              onClick={() => setOpen(true)}
            >
              New supplier
            </Button>
          ) : undefined
        }
      />
      <ProcurementNav />
      <Panel title="Supplier register">
        <div className={styles.toolbar} role="search">
          <TextField
            className={styles.grow}
            label="Search"
            placeholder="Name, reference, category or city"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <SelectField
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            options={[
              { value: "", label: "All" },
              ...SUPPLIER_STATUSES.map((s) => ({ value: s, label: s })),
            ]}
          />
        </div>
        <FormError message={error} />
        {data && data.items.length === 0 ? (
          <EmptyState title="No suppliers">
            Add suppliers you actually deal with. Nothing is pre-filled.
          </EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Supplier</th>
                  <th scope="col">Categories</th>
                  <th scope="col">Location</th>
                  <th scope="col">Bank details</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <Link href={`/procurement/suppliers/${s.id}`} className={styles.rowLink}>
                        {s.name}
                      </Link>
                      <div className={styles.ref}>{s.reference}</div>
                    </td>
                    <td>{s.categories ?? "—"}</td>
                    <td>{[s.city, s.country_code].filter(Boolean).join(", ")}</td>
                    <td>
                      {s.pending_bank_change ? (
                        <Badge tone="gold">Change pending</Badge>
                      ) : s.has_active_bank_account ? (
                        <Badge tone="success">On file</Badge>
                      ) : (
                        <span className={page.muted}>None</span>
                      )}
                    </td>
                    <td>
                      <Badge
                        tone={
                          s.status === "verified"
                            ? "success"
                            : s.status === "suspended"
                              ? "danger"
                              : "warning"
                        }
                      >
                        {s.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <Dialog open={open} title="New supplier" onClose={() => setOpen(false)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const body = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ""));
            send<Supplier>("POST", "/procurement/suppliers", { body })
              .then(({ data: s }) => router.push(`/procurement/suppliers/${s.id}`))
              .catch((err: unknown) => setFormError(errorMessage(err)));
          }}
        >
          <div className={styles.formGrid}>
            <TextField
              label="Supplier name"
              required
              minLength={2}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <SelectField
              label="Country"
              value={form.country_code}
              onChange={(e) => setForm({ ...form, country_code: e.target.value })}
              options={COUNTRIES}
            />
            <TextField
              label="City"
              value={form.city}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
            />
            <TextField
              label="Categories"
              placeholder="e.g. Stationery, IT hardware"
              value={form.categories}
              onChange={(e) => setForm({ ...form, categories: e.target.value })}
            />
            <TextField
              label="Contact person"
              value={form.contact_name}
              onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
            />
            <TextField
              label="Email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <TextField
              label="Phone"
              type="tel"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <FormError message={formError} />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create supplier
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

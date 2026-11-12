"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LuPlus } from "react-icons/lu";

import { CrmNav } from "@/components/crm/CrmNav";
import { CustomerDialog } from "@/components/crm/forms";
import styles from "@/components/crm/crm.module.css";
import {
  Badge,
  Button,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SelectField,
  Spinner,
  TextField,
} from "@/components/ui";
import { useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  COUNTRIES,
  CUSTOMER_STATUSES,
  KIND_LABEL,
  query,
  STATUS_LABEL,
  type Customer,
  type Page,
} from "@/lib/crm/types";

import page from "@/app/pages.module.css";

const STATUS_TONE = {
  prospect: "gold",
  active: "success",
  inactive: "neutral",
  archived: "neutral",
} as const;
const SIZE = 25;

export default function CustomersPage() {
  const { can } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [country, setCountry] = useState("");
  const [pageNo, setPageNo] = useState(1);
  const [creating, setCreating] = useState(false);
  const path = `/crm/customers${query({ q: q.trim(), status, country, page: pageNo, size: SIZE })}`;
  const { data, error, loading } = useResource<Page<Customer>>(path);
  const pages = data ? Math.max(1, Math.ceil(data.total / SIZE)) : 1;
  const filtered = Boolean(q.trim() || status || country);

  return (
    <>
      <PageHeader
        eyebrow="Business Development"
        title="CRM & Sales"
        description="Customers, contacts, opportunities and follow-ups. Every change is recorded in the audit log."
        actions={
          can("crm.records.edit") ? (
            <Button
              variant="primary"
              icon={<LuPlus aria-hidden="true" />}
              onClick={() => setCreating(true)}
            >
              New customer
            </Button>
          ) : undefined
        }
      />
      <CrmNav />
      <Panel
        title="Customers"
        actions={data ? <Badge tone="neutral">{data.total} total</Badge> : undefined}
      >
        <div className={styles.toolbar} role="search">
          <TextField
            className={styles.grow}
            label="Search"
            placeholder="Name, reference, industry or city"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPageNo(1);
            }}
          />
          <SelectField
            label="Status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPageNo(1);
            }}
            options={[
              { value: "", label: "All current" },
              ...CUSTOMER_STATUSES.map((s) => ({ value: s, label: STATUS_LABEL[s] })),
            ]}
          />
          <SelectField
            label="Country"
            value={country}
            onChange={(e) => {
              setCountry(e.target.value);
              setPageNo(1);
            }}
            options={[{ value: "", label: "All countries" }, ...COUNTRIES]}
          />
        </div>
        <FormError message={error} />
        {loading && !data ? (
          <Spinner label="Loading customers" />
        ) : data && data.items.length === 0 ? (
          <EmptyState title={filtered ? "No customers match" : "No customers yet"}>
            {filtered
              ? "Try a different search or clear the filters."
              : "Add your first real customer. Nothing is pre-filled or invented."}
          </EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Customer</th>
                  <th scope="col">Type</th>
                  <th scope="col">Location</th>
                  <th scope="col">Open opportunities</th>
                  <th scope="col">Owner</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <Link href={`/crm/customers/${c.id}`} className={styles.rowLink}>
                        {c.name}
                      </Link>
                      {c.is_demo && (
                        <>
                          {" "}
                          <Badge tone="warning">Demo</Badge>
                        </>
                      )}
                      <div className={styles.ref}>{c.reference}</div>
                    </td>
                    <td>{KIND_LABEL[c.kind]}</td>
                    <td>
                      {[
                        c.city,
                        COUNTRIES.find((x) => x.value === c.country_code)?.label ?? c.country_code,
                      ]
                        .filter(Boolean)
                        .join(", ")}
                    </td>
                    <td className="tabular">{c.open_opportunities}</td>
                    <td>
                      {c.owner?.display_name ?? <span className={page.muted}>Unassigned</span>}
                    </td>
                    <td>
                      <Badge tone={STATUS_TONE[c.status]}>{STATUS_LABEL[c.status]}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && data.total > SIZE && (
          <div className={styles.pager}>
            <Button size="sm" disabled={pageNo <= 1} onClick={() => setPageNo(pageNo - 1)}>
              Previous
            </Button>
            <span>
              Page {pageNo} of {pages}
            </span>
            <Button size="sm" disabled={pageNo >= pages} onClick={() => setPageNo(pageNo + 1)}>
              Next
            </Button>
          </div>
        )}
      </Panel>
      {creating && (
        <CustomerDialog
          open
          onClose={() => setCreating(false)}
          onSaved={(customer) => router.push(`/crm/customers/${customer.id}`)}
        />
      )}
    </>
  );
}

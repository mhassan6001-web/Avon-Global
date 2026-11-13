"use client";

import Link from "next/link";
import { useState } from "react";
import { LuFileDown, LuFileSpreadsheet, LuFileText } from "react-icons/lu";

import crm from "@/components/crm/crm.module.css";
import { EmptyState, PageHeader, Panel, SelectField, TextField } from "@/components/ui";
import { API_PREFIX } from "@/lib/api/client";
import { useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDateTime } from "@/lib/tenders/types";

import page from "@/app/pages.module.css";

interface RegisterRow {
  id: string;
  kind: string;
  subject: string;
  number: string;
  format: string;
  version: number;
  sha256: string;
  size_bytes: number;
  generated_by: string;
  created_at: string;
}

const WORKBOOKS = [
  { name: "trial_balance", label: "Trial balance", permission: "finance.ledger.view" },
  { name: "receivables", label: "Receivables ageing", permission: "finance.records.view" },
  { name: "payables", label: "Payables ageing", permission: "finance.records.view" },
  { name: "stock", label: "Stock levels", permission: "inventory.records.view" },
];

interface Party {
  id: string;
  name: string;
}

/** Finance only: customer account statements from posted records. */
function Statements() {
  const parties = useResource<Party[]>("/finance/parties?kind=customer");
  const [customer, setCustomer] = useState("");
  const [from, setFrom] = useState(`${new Date().getFullYear()}-01-01`);
  const [to, setTo] = useState(new Date().toISOString().slice(0, 10));
  const base = `${API_PREFIX}/documents/statements/${customer}?date_from=${from}&date_to=${to}`;
  return (
    <Panel title="Customer statements">
      <div className={crm.formGrid}>
        <SelectField
          label="Customer"
          value={customer}
          onChange={(e) => setCustomer(e.target.value)}
          options={[
            { value: "", label: "Choose" },
            ...(parties.data ?? []).map((p) => ({ value: p.id, label: p.name })),
          ]}
        />
        <TextField
          label="From"
          type="date"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
        />
        <TextField label="To" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
      </div>
      {customer ? (
        <p>
          {(["pdf", "docx", "xlsx"] as const).map((f) => (
            <a
              key={f}
              className={page.inlineLink}
              href={`${base}&format=${f}`}
              download
              style={{ marginRight: 16 }}
            >
              <LuFileDown aria-hidden="true" /> Statement (
              {f === "pdf" ? "PDF" : f === "docx" ? "Word" : "Excel"})
            </a>
          ))}
        </p>
      ) : (
        <p className={page.muted}>Choose a customer to download their statement of account.</p>
      )}
      <p className={page.note}>
        Statements list issued invoices, receipts and posted credit notes only. Balances are shown
        per currency and are not converted.
      </p>
    </Panel>
  );
}

export default function DocumentsPage() {
  const { can } = useAuth();
  const register = useResource<RegisterRow[]>("/documents/register?limit=100");
  const workbooks = WORKBOOKS.filter((w) => can(w.permission));

  return (
    <>
      <PageHeader
        eyebrow="Documents"
        title="Documents"
        description="Branded documents generated from the system's records. Each download is recorded with its version and fingerprint. The system never adds a signature."
      />
      <div className={page.grid}>
        <div className={page.span6}>
          <Panel title="Company letterhead">
            <p className={page.muted}>
              The AVEN GLOBAL letterhead for letters and notices. Word to type in, PDF to print.
            </p>
            <p>
              <a
                className={page.inlineLink}
                href={`${API_PREFIX}/documents/letterhead?format=docx`}
                download
              >
                <LuFileText aria-hidden="true" /> Letterhead (Word)
              </a>
              {"  ·  "}
              <a
                className={page.inlineLink}
                href={`${API_PREFIX}/documents/letterhead?format=pdf`}
                download
              >
                <LuFileDown aria-hidden="true" /> Letterhead (PDF)
              </a>
            </p>
            <p className={page.note}>
              Quotations, invoices, receipts, purchase orders and delivery notes are downloaded from
              their own lists (PDF or Word). Tender packs are downloaded from each tender.
            </p>
            {(can("crm.records.view") || can("procurement.records.view")) && (
              <p>
                <Link className={page.inlineLink} href="/documents/contracts">
                  Contracts and service agreements
                </Link>
              </p>
            )}
          </Panel>
        </div>
        <div className={page.span6}>
          <Panel title="Excel workbooks">
            {workbooks.length === 0 ? (
              <EmptyState title="No workbooks for your role">
                Reports follow your department access.
              </EmptyState>
            ) : (
              <ul className={page.scopeList}>
                {workbooks.map((w) => (
                  <li key={w.name}>
                    <a
                      className={page.inlineLink}
                      href={`${API_PREFIX}/documents/reports/${w.name}`}
                      download
                    >
                      <LuFileSpreadsheet aria-hidden="true" /> {w.label} (.xlsx)
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
        {can("finance.records.view") && (
          <div>
            <Statements />
          </div>
        )}
        <div>
          <Panel title="Generated documents">
            {register.data && register.data.length === 0 ? (
              <EmptyState title="Nothing generated yet">
                Downloads appear here with their version.
              </EmptyState>
            ) : (
              <div className={page.tableWrap}>
                <table className={page.table}>
                  <thead>
                    <tr>
                      <th scope="col">Document</th>
                      <th scope="col">Format</th>
                      <th scope="col">Version</th>
                      <th scope="col">By</th>
                      <th scope="col">When</th>
                      <th scope="col">Fingerprint (SHA-256)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {register.data?.map((r) => (
                      <tr key={r.id}>
                        <td>
                          {r.number}
                          <div className={page.muted}>{r.kind.replace(/_/g, " ")}</div>
                        </td>
                        <td>{r.format.toUpperCase()}</td>
                        <td className="tabular">v{r.version}</td>
                        <td>{r.generated_by}</td>
                        <td>{formatDateTime(r.created_at)}</td>
                        <td className="tabular" title={r.sha256}>
                          {r.sha256.slice(0, 12)}…
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </>
  );
}

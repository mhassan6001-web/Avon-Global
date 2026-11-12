"use client";

import { LuFileDown, LuFileSpreadsheet, LuFileText } from "react-icons/lu";

import { EmptyState, PageHeader, Panel } from "@/components/ui";
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
              Invoices, receipts, purchase orders and delivery notes are downloaded from their own
              lists (PDF or Word).
            </p>
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

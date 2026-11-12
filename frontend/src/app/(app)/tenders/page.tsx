"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LuCalendarClock, LuFileWarning, LuPlus, LuTrophy } from "react-icons/lu";

import { KpiCard } from "@/components/charts/Charts";
import styles from "@/components/crm/crm.module.css";
import { TenderDialog } from "@/components/tenders/TenderDialog";
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
import { query } from "@/lib/crm/types";
import {
  countdown,
  formatDateTime,
  KIND_LABEL,
  TENDER_STATUS_LABEL,
  TENDER_STATUSES,
  type Page,
  type Tender,
  type TenderSummary,
} from "@/lib/tenders/types";

import page from "@/app/pages.module.css";

export default function TendersPage() {
  const { can } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("active");
  const [creating, setCreating] = useState(false);
  const list = useResource<Page<Tender>>(
    `/tenders${query({ q: q.trim(), status: status === "active" ? "" : status, active_only: status === "active", size: 100 })}`,
  );
  const summary = useResource<TenderSummary>("/tenders/summary");
  const s = summary.data;

  return (
    <>
      <PageHeader
        eyebrow="Business Development"
        title="Tenders"
        description="RFQs, RFPs and EOIs with deadlines and eligibility checklists. A bid is submitted by a person, only after Director approval."
        actions={
          can("tenders.records.edit") ? (
            <Button
              variant="primary"
              icon={<LuPlus aria-hidden="true" />}
              onClick={() => setCreating(true)}
            >
              New tender
            </Button>
          ) : undefined
        }
      />
      <div className={page.grid}>
        <div className={page.span4}>
          <KpiCard
            icon={<LuCalendarClock />}
            label="Deadlines in 7 days"
            value={s?.has_records ? String(s.due_within_7_days) : null}
            note={s?.has_records ? `${s.active} active tenders` : undefined}
          />
        </div>
        <div className={page.span4}>
          <KpiCard
            icon={<LuFileWarning />}
            label="Past deadline, not submitted"
            value={s?.has_records ? String(s.overdue_unsubmitted) : null}
          />
        </div>
        <div className={page.span4}>
          <KpiCard
            icon={<LuTrophy />}
            label="Won of decided"
            value={
              s?.has_records ? (s.decided ? `${s.won} of ${s.decided}` : "None decided") : null
            }
          />
        </div>
        <div className={page.span12}>
          <Panel
            title="Tender register"
            actions={list.data ? <Badge tone="neutral">{list.data.total} shown</Badge> : undefined}
          >
            <div className={styles.toolbar} role="search">
              <TextField
                className={styles.grow}
                label="Search"
                placeholder="Title, issuer or reference"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <SelectField
                label="Status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                options={[
                  { value: "active", label: "Active" },
                  { value: "", label: "All" },
                  ...TENDER_STATUSES.map((v) => ({ value: v, label: TENDER_STATUS_LABEL[v] })),
                ]}
              />
            </div>
            <FormError message={list.error} />
            {list.loading && !list.data ? (
              <Spinner label="Loading tenders" />
            ) : list.data?.items.length === 0 ? (
              <EmptyState title="No tenders here">
                Add tenders you are tracking. Nothing is pre-filled.
              </EmptyState>
            ) : (
              <div className={page.tableWrap}>
                <table className={page.table}>
                  <thead>
                    <tr>
                      <th scope="col">Tender</th>
                      <th scope="col">Issuer</th>
                      <th scope="col">Type</th>
                      <th scope="col">Deadline</th>
                      <th scope="col">Checklist</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.data?.items.map((t) => {
                      const due = countdown(t.submission_deadline);
                      const active = [
                        "identified",
                        "reviewing",
                        "bidding",
                        "awaiting_approval",
                        "approved",
                      ].includes(t.status);
                      return (
                        <tr key={t.id}>
                          <td>
                            <Link href={`/tenders/${t.id}`} className={styles.rowLink}>
                              {t.title}
                            </Link>
                            <div className={styles.ref}>
                              {t.reference}
                              {t.issuer_reference ? ` · ${t.issuer_reference}` : ""}
                            </div>
                          </td>
                          <td>{t.issuer_name}</td>
                          <td>{KIND_LABEL[t.kind]}</td>
                          <td>
                            {formatDateTime(t.submission_deadline)}
                            {active && (
                              <div>
                                <Badge tone={due.tone}>{due.text}</Badge>
                              </div>
                            )}
                          </td>
                          <td className="tabular">
                            {t.requirements_total === 0 ? (
                              <span className={page.muted}>None</span>
                            ) : t.requirements_open === 0 ? (
                              <Badge tone="success">Ready</Badge>
                            ) : (
                              `${t.requirements_open} open`
                            )}
                          </td>
                          <td>
                            <Badge
                              tone={
                                t.status === "won"
                                  ? "success"
                                  : t.status === "awaiting_approval"
                                    ? "gold"
                                    : active
                                      ? "signal"
                                      : "neutral"
                              }
                            >
                              {TENDER_STATUS_LABEL[t.status]}
                            </Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      </div>
      {creating && (
        <TenderDialog
          open
          onClose={() => setCreating(false)}
          onSaved={(d) => router.push(`/tenders/${d.tender.id}`)}
        />
      )}
    </>
  );
}

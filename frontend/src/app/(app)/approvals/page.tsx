"use client";

import Link from "next/link";
import { useState } from "react";
import { LuCheck, LuX } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
import {
  Badge,
  Button,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SegmentedControl,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useStepUp } from "@/lib/auth/StepUpProvider";
import { formatDateTime } from "@/lib/tenders/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

interface Approval {
  id: string;
  subject_type: string;
  subject_id: string;
  summary: string;
  payload: Record<string, unknown>;
  status: string;
  requested_by: string;
  created_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_note: string | null;
  can_decide: boolean;
  blocked_reason: string | null;
}

const VIEWS = [
  { value: "to_decide", label: "Waiting for me" },
  { value: "mine", label: "My requests" },
  { value: "decided", label: "Decided" },
] as const;
type View = (typeof VIEWS)[number]["value"];

/** Where the subject of an approval lives in the app. */
function subjectLink(a: Approval): string | null {
  if (a.subject_type === "tender_submission") return `/tenders/${a.subject_id}`;
  if (a.subject_type === "purchase_request") return `/procurement/requests/${a.subject_id}`;
  if (a.subject_type === "crm_quotation") return "/crm/quotations";
  if (a.subject_type === "supplier_payment") return "/finance/bills";
  if (a.subject_type === "credit_note") return "/finance/invoices";
  if (a.subject_type === "manual_journal" || a.subject_type === "journal_reversal")
    return "/finance/journals";
  return null;
}

interface Rule {
  key: string;
  label: string;
  configurable: boolean;
  note: string;
  enabled: boolean;
  threshold: string | null;
  functional_currency: string;
  second_approver_exists: boolean;
}

/** Director only: approval limits, and whether a second approver exists for each control. */
function ApprovalRules() {
  const { can } = useAuth();
  const allowed = can("admin.permissions.manage");
  const rules = useResource<Rule[]>(allowed ? "/approvals/rules" : null);
  const withStepUp = useStepUp();
  const [draft, setDraft] = useState<Record<string, { enabled: boolean; threshold: string }>>({});
  const [error, setError] = useState<string | null>(null);
  if (!allowed || !rules.data) return null;

  async function save(rule: Rule) {
    const d = draft[rule.key] ?? { enabled: rule.enabled, threshold: rule.threshold ?? "" };
    setError(null);
    try {
      await withStepUp(() =>
        send("PUT", `/approvals/rules/${rule.key}`, {
          body: { enabled: d.enabled, threshold: d.threshold === "" ? null : d.threshold },
        }).then(() => undefined),
      );
      await rules.reload();
    } catch (e) {
      if (e && typeof e === "object" && "code" in e && (e as { code: string }).code === "cancelled")
        return;
      setError(errorMessage(e));
    }
  }

  return (
    <Panel title="Approval rules">
      <FormError message={error} />
      <ul className={styles.timeline}>
        {rules.data.map((rule) => {
          const d = draft[rule.key] ?? { enabled: rule.enabled, threshold: rule.threshold ?? "" };
          return (
            <li key={rule.key} className={styles.timelineItem}>
              <Badge tone={rule.second_approver_exists ? "success" : "warning"}>
                {rule.second_approver_exists
                  ? "Second approver exists"
                  : "You are the only approver"}
              </Badge>
              <div>
                <strong>{rule.label}</strong>
                <div className={page.muted}>
                  {rule.note}
                  {!rule.second_approver_exists &&
                    " Requests you raise yourself stay blocked; requests from staff come to you."}
                </div>
                {rule.configurable && (
                  <div className={styles.formGrid} style={{ alignItems: "end", marginTop: 8 }}>
                    <label className={styles.check}>
                      <input
                        type="checkbox"
                        checked={d.enabled}
                        onChange={(e) =>
                          setDraft({ ...draft, [rule.key]: { ...d, enabled: e.target.checked } })
                        }
                      />
                      Approval required
                    </label>
                    <TextField
                      label={`Only at or above (${rule.functional_currency}); empty = always`}
                      inputMode="decimal"
                      value={d.threshold}
                      disabled={!d.enabled}
                      onChange={(e) =>
                        setDraft({ ...draft, [rule.key]: { ...d, threshold: e.target.value } })
                      }
                    />
                    <Button size="sm" onClick={() => void save(rule)}>
                      Save rule
                    </Button>
                  </div>
                )}
              </div>
              <span />
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

export default function ApprovalsPage() {
  const [view, setView] = useState<View>("to_decide");
  const { data, error, reload } = useResource<Approval[]>(`/approvals?view=${view}`);
  const withStepUp = useStepUp();
  const { play } = useSound();
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [actionError, setActionError] = useState<string | null>(null);

  async function decide(a: Approval, approve: boolean) {
    setActionError(null);
    try {
      await withStepUp(() =>
        send("POST", `/approvals/${a.id}/decide`, {
          body: { approve, ...(notes[a.id] ? { note: notes[a.id] } : {}) },
        }).then(() => undefined),
      );
      play(approve ? "approval" : "navigation");
      await reload();
    } catch (e) {
      if (e && typeof e === "object" && "code" in e && (e as { code: string }).code === "cancelled")
        return;
      setActionError(errorMessage(e));
      play("warning");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Controls"
        title="Approvals"
        description="Restricted actions wait here for a different person to decide. Nobody can approve their own request, and each decision asks you to confirm your identity."
      />
      <Panel title="Approval queue">
        <SegmentedControl label="Approval view" value={view} options={VIEWS} onChange={setView} />
        <FormError message={error ?? actionError} />
        {data && data.length === 0 ? (
          <EmptyState title="Nothing here">
            {view === "to_decide"
              ? "No requests are waiting for you."
              : "No requests in this view."}
          </EmptyState>
        ) : (
          <ul className={styles.timeline} style={{ marginTop: 16 }}>
            {data?.map((a) => {
              const link = subjectLink(a);
              return (
                <li key={a.id} className={styles.timelineItem} data-testid={`approval-${a.id}`}>
                  <Badge
                    tone={
                      a.status === "approved"
                        ? "success"
                        : a.status === "rejected"
                          ? "danger"
                          : "gold"
                    }
                  >
                    {a.status}
                  </Badge>
                  <div>
                    <strong>
                      {link ? (
                        <Link href={link} className={styles.rowLink}>
                          {a.summary}
                        </Link>
                      ) : (
                        a.summary
                      )}
                    </strong>
                    <div className={page.muted}>
                      Requested by {a.requested_by} · {formatDateTime(a.created_at)}
                      {a.decided_by &&
                        ` · decided by ${a.decided_by} ${formatDateTime(a.decided_at)}`}
                    </div>
                    {a.decision_note && <p className={styles.timelineBody}>“{a.decision_note}”</p>}
                    {a.blocked_reason && (
                      <p className={styles.overdue} role="status">
                        {a.blocked_reason}
                      </p>
                    )}
                    {a.can_decide && (
                      <TextField
                        label="Decision note (optional)"
                        maxLength={2000}
                        value={notes[a.id] ?? ""}
                        onChange={(e) => setNotes({ ...notes, [a.id]: e.target.value })}
                      />
                    )}
                  </div>
                  {a.can_decide ? (
                    <span style={{ display: "flex", gap: 8 }}>
                      <Button
                        size="sm"
                        variant="primary"
                        icon={<LuCheck aria-hidden="true" />}
                        onClick={() => void decide(a, true)}
                      >
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        icon={<LuX aria-hidden="true" />}
                        onClick={() => void decide(a, false)}
                      >
                        Reject
                      </Button>
                    </span>
                  ) : (
                    <span />
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
      <ApprovalRules />
    </>
  );
}

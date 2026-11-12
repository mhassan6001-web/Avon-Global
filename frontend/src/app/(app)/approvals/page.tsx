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
  return null;
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
    </>
  );
}

"use client";

import Link from "next/link";
import { useState } from "react";
import { LuCheck } from "react-icons/lu";

import { CrmNav } from "@/components/crm/CrmNav";
import styles from "@/components/crm/crm.module.css";
import {
  Badge,
  Button,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SegmentedControl,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDate, isOverdue, query, type Activity } from "@/lib/crm/types";
import { useSound } from "@/lib/sound/SoundProvider";

const VIEWS = [
  { value: "overdue", label: "Overdue" },
  { value: "upcoming", label: "Next 7 days" },
  { value: "open", label: "All open" },
] as const;
type View = (typeof VIEWS)[number]["value"];

export default function FollowUpsPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const [view, setView] = useState<View>("overdue");
  const [mine, setMine] = useState(false);
  const { data, error, reload } = useResource<Activity[]>(
    `/crm/activities${query({ due: view, mine, limit: 200 })}`,
  );
  const [actionError, setActionError] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Business Development"
        title="Follow-ups"
        description="Commitments to customers, by due date."
      />
      <CrmNav />
      <Panel
        title="Follow-ups"
        actions={
          <label className={styles.check}>
            <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} />
            Only mine
          </label>
        }
      >
        <SegmentedControl label="Follow-up view" value={view} options={VIEWS} onChange={setView} />
        <FormError message={error ?? actionError} />
        {data && data.length === 0 ? (
          <EmptyState title="Nothing here">No follow-ups in this view.</EmptyState>
        ) : (
          <ol className={styles.timeline} style={{ marginTop: 16 }}>
            {data?.map((a) => (
              <li key={a.id} className={styles.timelineItem}>
                <Badge tone={isOverdue(a) ? "danger" : "gold"}>
                  {isOverdue(a) ? "Overdue" : "Due"}
                </Badge>
                <div>
                  <strong>{a.subject}</strong>
                  <div className={isOverdue(a) ? styles.overdue : undefined}>
                    {formatDate(a.due_at)} ·{" "}
                    <Link href={`/crm/customers/${a.customer_id}`} className={styles.rowLink}>
                      {a.customer_name}
                    </Link>
                    {a.assigned_to && ` · ${a.assigned_to.display_name}`}
                  </div>
                </div>
                {can("crm.records.edit") ? (
                  <Button
                    size="sm"
                    icon={<LuCheck aria-hidden="true" />}
                    onClick={() =>
                      void send("POST", `/crm/activities/${a.id}/complete`)
                        .then(() => {
                          play("complete");
                          return reload();
                        })
                        .catch((e: unknown) => setActionError(errorMessage(e)))
                    }
                  >
                    Mark done
                  </Button>
                ) : (
                  <span />
                )}
              </li>
            ))}
          </ol>
        )}
      </Panel>
    </>
  );
}

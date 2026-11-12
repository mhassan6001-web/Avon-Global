"use client";

import Link from "next/link";
import { useState } from "react";

import { CrmNav } from "@/components/crm/CrmNav";
import styles from "@/components/crm/crm.module.css";
import {
  Badge,
  Button,
  Dialog,
  EmptyState,
  FormError,
  PageHeader,
  SelectField,
  Spinner,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  DIVISION_LABEL,
  DIVISIONS,
  formatDate,
  formatMoney,
  query,
  STAGE_LABEL,
  STAGES,
  type Opportunity,
  type Page,
  type Stage,
} from "@/lib/crm/types";
import { useSound } from "@/lib/sound/SoundProvider";

/** Sum decimal strings per currency without floating-point error (cents as BigInt). */
function totals(items: Opportunity[]): string {
  const byCurrency = new Map<string, bigint>();
  for (const o of items) {
    if (o.value_amount === null) continue;
    const [whole = "0", fraction = ""] = o.value_amount.split(".");
    const cents = BigInt(whole) * 100n + BigInt((fraction + "00").slice(0, 2));
    byCurrency.set(o.currency, (byCurrency.get(o.currency) ?? 0n) + cents);
  }
  return [...byCurrency.entries()]
    .map(([currency, cents]) =>
      formatMoney(`${cents / 100n}.${String(cents % 100n).padStart(2, "0")}`, currency),
    )
    .join(" · ");
}

export default function PipelinePage() {
  const { can } = useAuth();
  const { play } = useSound();
  const [division, setDivision] = useState("");
  const [q, setQ] = useState("");
  const { data, error, loading, reload } = useResource<Page<Opportunity>>(
    `/crm/opportunities${query({ division, q: q.trim(), size: 100 })}`,
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [losing, setLosing] = useState<Opportunity | null>(null);
  const [reason, setReason] = useState("");
  const editable = can("crm.records.edit");

  async function move(o: Opportunity, stage: Stage, lost_reason?: string) {
    setActionError(null);
    try {
      await send("PATCH", `/crm/opportunities/${o.id}`, {
        body: { stage, ...(lost_reason ? { lost_reason } : {}) },
      });
      play(stage === "won" ? "approval" : "navigation");
      await reload();
    } catch (e) {
      setActionError(errorMessage(e));
      play("warning");
    }
  }

  const items = data?.items ?? [];
  return (
    <>
      <PageHeader
        eyebrow="Business Development"
        title="Sales pipeline"
        description="Opportunity values are estimates in their own currency. They are not revenue and are never converted at an invented rate."
      />
      <CrmNav />
      <div className={styles.toolbar}>
        <TextField
          className={styles.grow}
          label="Search"
          placeholder="Title, reference or customer"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <SelectField
          label="Division"
          value={division}
          onChange={(e) => setDivision(e.target.value)}
          options={[
            { value: "", label: "All divisions" },
            ...DIVISIONS.map((d) => ({ value: d, label: DIVISION_LABEL[d] })),
          ]}
        />
      </div>
      <FormError message={error ?? actionError} />
      {loading && !data ? (
        <Spinner label="Loading pipeline" />
      ) : items.length === 0 ? (
        <EmptyState title="No opportunities yet">
          Create opportunities from a customer&apos;s page.
        </EmptyState>
      ) : (
        <div className={styles.board}>
          {STAGES.map((stage) => {
            const column = items.filter((o) => o.stage === stage);
            return (
              <section
                key={stage}
                className={styles.column}
                aria-label={`${STAGE_LABEL[stage]} stage`}
              >
                <header className={styles.columnHead}>
                  <span className="hud-label">{STAGE_LABEL[stage]}</span>
                  <Badge tone="neutral">{column.length}</Badge>
                </header>
                {column.length > 0 && (
                  <p className={styles.amount} style={{ margin: 0, fontSize: 12 }}>
                    {totals(column) || "No values"}
                  </p>
                )}
                {column.map((o) => (
                  <article key={o.id} className={styles.card}>
                    <p className={styles.cardTitle}>{o.title}</p>
                    <Link href={`/crm/customers/${o.customer_id}`} className={styles.rowLink}>
                      {o.customer_name}
                    </Link>
                    <span className={styles.amount}>{formatMoney(o.value_amount, o.currency)}</span>
                    <span className={styles.ref}>
                      {o.reference} · {DIVISION_LABEL[o.division]} · close{" "}
                      {formatDate(o.expected_close)}
                    </span>
                    {o.lost_reason && (
                      <span className={styles.timelineBody}>Lost: {o.lost_reason}</span>
                    )}
                    {editable && (
                      <SelectField
                        label={`Stage for ${o.title}`}
                        value={o.stage}
                        onChange={(e) => {
                          const next = e.target.value as Stage;
                          if (next === "lost") {
                            setReason("");
                            setLosing(o);
                          } else void move(o, next);
                        }}
                        options={STAGES.map((s) => ({ value: s, label: STAGE_LABEL[s] }))}
                      />
                    )}
                  </article>
                ))}
              </section>
            );
          })}
        </div>
      )}
      <Dialog
        open={losing !== null}
        title="Why was this opportunity lost?"
        onClose={() => setLosing(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (losing) void move(losing, "lost", reason.trim()).then(() => setLosing(null));
          }}
        >
          <TextField
            label="Reason"
            required
            minLength={2}
            maxLength={2000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setLosing(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Mark as lost
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

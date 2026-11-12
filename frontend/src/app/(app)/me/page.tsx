"use client";

import { useState } from "react";

import styles from "@/components/crm/crm.module.css";
import {
  Badge,
  Button,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SelectField,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { formatDate, formatMoney } from "@/lib/crm/types";
import { inclusiveDays, LEAVE_KINDS, type MyHr } from "@/lib/hr";
import { label } from "@/lib/inventory/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

/** Self-service: only the signed-in person's own HR record, leave, KPIs, reviews and payslips. */
export default function MyWorkPage() {
  const { play } = useSound();
  const me = useResource<MyHr>("/hr/me");
  const [leave, setLeave] = useState({ kind: "annual", start_date: "", end_date: "", reason: "" });
  const [comment, setComment] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const days = inclusiveDays(leave.start_date, leave.end_date);

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      play("complete");
      await me.reload();
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  if (me.error) {
    return (
      <>
        <PageHeader
          eyebrow="Self-service"
          title="My HR"
          description="Your own record, leave, objectives and payslips."
        />
        <EmptyState title="Not linked yet">{me.error}</EmptyState>
      </>
    );
  }
  const d = me.data;
  return (
    <>
      <PageHeader
        eyebrow="Self-service"
        title="My HR"
        description="Only you, HR and the Director can see this. Nothing here is monitored or tracked."
      />
      <FormError message={error} />
      {d && (
        <div className={page.grid}>
          <div className={page.span5}>
            <Panel
              title="Annual leave"
              actions={<Badge tone="gold">{`${d.leave_balance.remaining} days left`}</Badge>}
            >
              <p
                className={page.muted}
              >{`${d.leave_balance.entitlement} days for ${d.leave_balance.year} · ${d.leave_balance.taken} taken · ${d.leave_balance.pending} pending`}</p>
              <form
                className={styles.formGrid}
                style={{ marginTop: 12, alignItems: "end" }}
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(() =>
                    send("POST", "/hr/me/leave", {
                      body: {
                        ...leave,
                        days: String(days),
                        ...(leave.reason ? {} : { reason: undefined }),
                      },
                    }),
                  );
                }}
              >
                <SelectField
                  label="Leave type"
                  value={leave.kind}
                  onChange={(e) => setLeave({ ...leave, kind: e.target.value })}
                  options={LEAVE_KINDS.map((k) => ({ value: k, label: label(k) }))}
                />
                <TextField
                  label="First day"
                  type="date"
                  required
                  value={leave.start_date}
                  onChange={(e) => setLeave({ ...leave, start_date: e.target.value })}
                />
                <TextField
                  label="Last day"
                  type="date"
                  required
                  value={leave.end_date}
                  onChange={(e) => setLeave({ ...leave, end_date: e.target.value })}
                />
                <TextField
                  label="Reason"
                  value={leave.reason}
                  onChange={(e) => setLeave({ ...leave, reason: e.target.value })}
                />
                <Button
                  type="submit"
                  disabled={days === 0}
                >{`Request ${days || ""} day(s)`}</Button>
              </form>
              <ul className={styles.timeline} style={{ marginTop: 16 }}>
                {d.leave.map((l) => (
                  <li key={l.id} className={styles.timelineItem}>
                    <Badge
                      tone={
                        l.status === "approved"
                          ? "success"
                          : l.status === "rejected"
                            ? "danger"
                            : "gold"
                      }
                    >
                      {label(l.status)}
                    </Badge>
                    <div>
                      {label(l.kind)} · {formatDate(l.start_date)} – {formatDate(l.end_date)} ·{" "}
                      {l.days} days
                      {l.decision_note && <div className={page.muted}>{l.decision_note}</div>}
                    </div>
                    <span />
                  </li>
                ))}
              </ul>
            </Panel>
          </div>
          <div className={page.span7}>
            <Panel title="My objectives (KPIs)">
              {d.kpis.length === 0 ? (
                <EmptyState title="No KPIs yet">
                  Your manager will agree objectives with you.
                </EmptyState>
              ) : (
                <ul className={styles.timeline}>
                  {d.kpis.map((k) => (
                    <li key={k.id} className={styles.timelineItem}>
                      <Badge tone="neutral">{label(k.status)}</Badge>
                      <div>
                        <strong>{k.title}</strong> · target {k.target} · {k.period}
                        {k.actual && <div className={page.muted}>Actual: {k.actual}</div>}
                      </div>
                      {k.employee_agreed_at ? (
                        <span className={page.muted}>Agreed</span>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => void act(() => send("POST", `/hr/me/kpis/${k.id}/agree`))}
                        >
                          I agree
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
            <div style={{ height: 20 }} />
            <Panel title="My reviews">
              {d.reviews.length === 0 ? (
                <EmptyState title="No reviews yet">
                  Performance reviews appear here for you to read and acknowledge.
                </EmptyState>
              ) : (
                <ul className={styles.timeline}>
                  {d.reviews.map((r) => (
                    <li key={r.id} className={styles.timelineItem}>
                      <Badge tone="gold">{`${r.rating}/5`}</Badge>
                      <div>
                        <strong>{r.period}</strong>
                        <p className="serif-text">Strengths: {r.strengths}</p>
                        <p className="serif-text">To improve: {r.improvements}</p>
                        {r.acknowledged_at ? (
                          <div className={page.muted}>
                            Acknowledged {formatDate(r.acknowledged_at)}
                            {r.employee_comment ? ` · “${r.employee_comment}”` : ""}
                          </div>
                        ) : (
                          <form
                            className={page.actionsRow}
                            onSubmit={(e) => {
                              e.preventDefault();
                              void act(() =>
                                send("POST", `/hr/me/reviews/${r.id}/acknowledge`, {
                                  body: comment[r.id] ? { comment: comment[r.id] } : {},
                                }),
                              );
                            }}
                          >
                            <TextField
                              label="Your comment (optional)"
                              value={comment[r.id] ?? ""}
                              onChange={(e) => setComment({ ...comment, [r.id]: e.target.value })}
                            />
                            <Button size="sm" type="submit">
                              Acknowledge
                            </Button>
                          </form>
                        )}
                      </div>
                      <span />
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
          <div className={page.span12}>
            <Panel title="My payslips">
              {d.payslips.length === 0 ? (
                <EmptyState title="No payslips yet">
                  Payslips appear after the Director approves a payroll run.
                </EmptyState>
              ) : (
                <div className={page.tableWrap}>
                  <table className={page.table}>
                    <thead>
                      <tr>
                        <th scope="col">Period</th>
                        <th scope="col">Gross</th>
                        <th scope="col">Deductions</th>
                        <th scope="col">Net pay</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.payslips.map((p) => (
                        <tr key={p.id}>
                          <td>{p.period}</td>
                          <td className="tabular">{formatMoney(p.gross, "MWK")}</td>
                          <td className="tabular">{formatMoney(p.deductions, "MWK")}</td>
                          <td className={styles.amount}>{formatMoney(p.net, "MWK")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}

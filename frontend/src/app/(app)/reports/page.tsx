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
import { useAuth } from "@/lib/auth/AuthProvider";
import type { Person, Report, ReportRequest, TeamRow } from "@/lib/comms";
import { formatDate } from "@/lib/crm/types";
import { isoToday } from "@/lib/finance/types";
import { label } from "@/lib/inventory/types";
import { useRealtimeEvent } from "@/lib/realtime/RealtimeProvider";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

export default function ReportsPage() {
  const { me, can } = useAuth();
  const { play } = useSound();
  const director = can("comms.announcements.send");
  const reports = useResource<Report[]>("/comms/reports");
  const requests = useResource<ReportRequest[]>("/comms/report-requests");
  const team = useResource<TeamRow[]>(director ? "/comms/team" : null);
  const people = useResource<Person[]>(director ? "/comms/people" : null);
  const [form, setForm] = useState({
    kind: "morning_plan",
    report_date: isoToday(),
    body: "",
    request_id: "",
  });
  const [ask, setAsk] = useState({ requested_from: "", topic: "" });
  const [error, setError] = useState<string | null>(null);
  useRealtimeEvent("report", () => void requests.reload());
  const open = (requests.data ?? []).filter(
    (r) => r.status === "open" && r.requested_from.id === me.user.id,
  );

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      play("complete");
      await Promise.all([reports.reload(), requests.reload(), team.reload()]);
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Communications"
        title="Work reports"
        description="Morning work plans, end-of-day reports and reports the Director asks for. You choose what to write; nothing is collected automatically."
      />
      <FormError message={error ?? reports.error} />
      <div className={page.grid}>
        <div className={page.span6}>
          <Panel title="Submit a report">
            <form
              className={styles.dialogForm}
              style={{ minWidth: 0 }}
              onSubmit={(e) => {
                e.preventDefault();
                const body = {
                  ...form,
                  ...(form.kind === "requested" ? {} : { request_id: undefined }),
                };
                void act(async () => {
                  await send("POST", "/comms/reports", { body });
                  setForm({ ...form, body: "" });
                });
              }}
            >
              <div className={styles.formGrid}>
                <SelectField
                  label="Report type"
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}
                  options={[
                    { value: "morning_plan", label: "Morning work plan" },
                    { value: "end_of_day", label: "End-of-day report" },
                    ...(open.length ? [{ value: "requested", label: "Requested report" }] : []),
                  ]}
                />
                <TextField
                  label="Date"
                  type="date"
                  required
                  value={form.report_date}
                  onChange={(e) => setForm({ ...form, report_date: e.target.value })}
                />
                {form.kind === "requested" && (
                  <SelectField
                    label="Answering"
                    required
                    value={form.request_id}
                    onChange={(e) => setForm({ ...form, request_id: e.target.value })}
                    options={[
                      { value: "", label: "Choose" },
                      ...open.map((r) => ({ value: r.id, label: r.topic })),
                    ]}
                  />
                )}
              </div>
              <label className={styles.textareaLabel}>
                Report
                <textarea
                  className={styles.textarea}
                  rows={6}
                  required
                  minLength={3}
                  value={form.body}
                  onChange={(e) => setForm({ ...form, body: e.target.value })}
                />
              </label>
              <div className={styles.dialogActions}>
                <Button type="submit" variant="primary">
                  Submit report
                </Button>
              </div>
            </form>
            {open.length > 0 && (
              <p className={page.note}>
                {open.length} report(s) requested from you: {open.map((r) => r.topic).join("; ")}.
              </p>
            )}
          </Panel>
        </div>
        <div className={page.span6}>
          {director ? (
            <Panel title="Team today">
              <form
                className={styles.formGrid}
                style={{ alignItems: "end", marginBottom: 16 }}
                onSubmit={(e) => {
                  e.preventDefault();
                  void act(() => send("POST", "/comms/report-requests", { body: ask }));
                }}
              >
                <SelectField
                  label="Request a report from"
                  required
                  value={ask.requested_from}
                  onChange={(e) => setAsk({ ...ask, requested_from: e.target.value })}
                  options={[
                    { value: "", label: "Choose" },
                    ...(people.data ?? [])
                      .filter((p) => p.id !== me.user.id)
                      .map((p) => ({ value: p.id, label: p.display_name })),
                  ]}
                />
                <TextField
                  label="About"
                  required
                  minLength={3}
                  value={ask.topic}
                  onChange={(e) => setAsk({ ...ask, topic: e.target.value })}
                />
                <Button type="submit">Request</Button>
              </form>
              <div className={page.tableWrap}>
                <table className={page.table}>
                  <thead>
                    <tr>
                      <th scope="col">Person</th>
                      <th scope="col">Open tasks</th>
                      <th scope="col">Overdue</th>
                      <th scope="col">Done (7 days)</th>
                      <th scope="col">Plan today</th>
                      <th scope="col">EOD yesterday</th>
                    </tr>
                  </thead>
                  <tbody>
                    {team.data?.map((r) => (
                      <tr key={r.user.id}>
                        <td>
                          {r.user.display_name}
                          <div className={page.muted}>{r.user.department}</div>
                        </td>
                        <td className="tabular">{r.open_tasks}</td>
                        <td className={r.overdue_tasks ? styles.overdue : "tabular"}>
                          {r.overdue_tasks}
                        </td>
                        <td className="tabular">{r.done_last_7_days}</td>
                        <td>{r.morning_plan_today ? "Yes" : "—"}</td>
                        <td>{r.end_of_day_yesterday ? "Yes" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          ) : (
            <Panel title="Requests to you">
              {(requests.data ?? []).length === 0 ? (
                <EmptyState title="No requests">
                  Report requests from the Director appear here.
                </EmptyState>
              ) : (
                <ul className={styles.timeline}>
                  {requests.data?.map((r) => (
                    <li key={r.id} className={styles.timelineItem}>
                      <Badge tone={r.status === "open" ? "gold" : "success"}>
                        {label(r.status)}
                      </Badge>
                      <div>
                        {r.topic}
                        <div className={page.muted}>from {r.requested_by.display_name}</div>
                      </div>
                      <span />
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          )}
        </div>
        <div>
          <Panel title={director ? "Reports" : "My reports"}>
            {reports.data && reports.data.length === 0 ? (
              <EmptyState title="No reports yet">Submitted reports appear here.</EmptyState>
            ) : (
              <ul className={styles.timeline}>
                {reports.data?.map((r) => (
                  <li key={r.id} className={styles.timelineItem}>
                    <Badge tone="neutral">{label(r.kind)}</Badge>
                    <div>
                      <strong>{r.author.display_name}</strong> · {formatDate(r.report_date)}
                      <p className="serif-text" style={{ whiteSpace: "pre-wrap" }}>
                        {r.body}
                      </p>
                    </div>
                    <span />
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>
    </>
  );
}

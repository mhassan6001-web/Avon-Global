"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge, Button, EmptyState, FormError, PageHeader, Panel } from "@/components/ui";
import { ApiError, send } from "@/lib/api/client";

import styles from "@/app/pages.module.css";

interface AuditEventOut {
  seq: number;
  occurred_at: string;
  actor_id: string | null;
  actor_kind: string;
  action: string;
  target_type: string | null;
  outcome: string;
}
interface LoginEventOut {
  occurred_at: string;
  email_attempted: string;
  outcome: string;
  ip: string | null;
}
interface AlertOut {
  id: string;
  created_at: string;
  kind: string;
  severity: string;
  message: string;
}
interface ChainOut {
  ok: boolean;
  events_checked: number;
  first_bad_seq: number | null;
}

const when = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "medium" });

export default function SecurityPage() {
  const [events, setEvents] = useState<AuditEventOut[]>([]);
  const [logins, setLogins] = useState<LoginEventOut[]>([]);
  const [alerts, setAlerts] = useState<AlertOut[]>([]);
  const [chain, setChain] = useState<ChainOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [a, l, s] = await Promise.all([
      send<AuditEventOut[]>("GET", "/admin/audit?limit=100"),
      send<LoginEventOut[]>("GET", "/admin/login-history?limit=50"),
      send<AlertOut[]>("GET", "/admin/security-alerts"),
    ]);
    setEvents(a.data);
    setLogins(l.data);
    setAlerts(s.data);
  }, []);

  useEffect(() => {
    void load().catch((e: unknown) =>
      setError(e instanceof ApiError ? e.message : "Could not load."),
    );
  }, [load]);

  async function verify() {
    const { data } = await send<ChainOut>("POST", "/admin/audit/verify");
    setChain(data);
    await load();
  }

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Security & audit"
        description="The audit log is append-only and hash-chained: any alteration is detectable."
        actions={<Button onClick={() => void verify()}>Verify audit chain</Button>}
      />
      <FormError message={error} />
      {chain && (
        <p className={styles.notice} role="status">
          {chain.ok ? (
            <>
              <Badge tone="success">Intact</Badge> {chain.events_checked} events verified.
            </>
          ) : (
            <>
              <Badge tone="danger">Broken</Badge> Verification failed at event {chain.first_bad_seq}
              . A security alert has been raised.
            </>
          )}
        </p>
      )}
      <div className={styles.grid} style={{ marginTop: 20 }}>
        <div className={styles.span12}>
          <Panel title="Security alerts">
            {alerts.length === 0 ? (
              <EmptyState title="No security alerts">
                Lockouts and integrity problems appear here.
              </EmptyState>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {alerts.map((a) => (
                  <li key={a.id} style={{ marginBottom: 6 }}>
                    <Badge tone={a.severity === "critical" ? "danger" : "warning"}>
                      {a.kind.replaceAll("_", " ")}
                    </Badge>{" "}
                    {a.message} <span className={styles.muted}>{when(a.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
        <div className={styles.span7}>
          <Panel title="Audit log (latest 100)">
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>When</th>
                    <th>Action</th>
                    <th>Actor</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.seq}>
                      <td className={styles.mono}>{e.seq}</td>
                      <td>{when(e.occurred_at)}</td>
                      <td className={styles.mono}>{e.action}</td>
                      <td className={styles.muted}>{e.actor_kind}</td>
                      <td>
                        <Badge tone={e.outcome === "success" ? "success" : "warning"}>
                          {e.outcome}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
        <div className={styles.span5}>
          <Panel title="Sign-in history (all users)">
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Account</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {logins.map((l, i) => (
                    <tr key={`${l.occurred_at}-${i}`}>
                      <td>{when(l.occurred_at)}</td>
                      <td className={styles.muted}>{l.email_attempted}</td>
                      <td>{l.outcome.replaceAll("_", " ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}

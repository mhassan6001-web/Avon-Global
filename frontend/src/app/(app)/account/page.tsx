"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Badge, Button, FormError, PageHeader, Panel, TextField } from "@/components/ui";
import { ApiError, send } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { passwordProblem } from "@/lib/auth/types";

import styles from "@/app/pages.module.css";

interface SessionOut {
  id: string;
  created_at: string;
  last_seen_at: string;
  ip: string | null;
  user_agent: string | null;
  current: boolean;
}
interface LoginEventOut {
  occurred_at: string;
  outcome: string;
  ip: string | null;
  user_agent: string | null;
}

const when = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });

export default function AccountPage() {
  const { me } = useAuth();
  const [sessions, setSessions] = useState<SessionOut[]>([]);
  const [history, setHistory] = useState<LoginEventOut[]>([]);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [s, h] = await Promise.all([
      send<SessionOut[]>("GET", "/auth/sessions"),
      send<LoginEventOut[]>("GET", "/auth/login-history?limit=20"),
    ]);
    setSessions(s.data);
    setHistory(h.data);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function changePassword() {
    setError(null);
    setMessage(null);
    const problem = passwordProblem(next, confirm);
    if (problem) return setError(problem);
    try {
      await send("POST", "/auth/password/change", {
        body: { current_password: current, new_password: next },
      });
      setCurrent("");
      setNext("");
      setConfirm("");
      setMessage("Password changed. Your other sessions have been signed out.");
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not change the password.");
    }
  }

  async function revoke(id: string) {
    await send("DELETE", `/auth/sessions/${id}`);
    await load();
  }

  const { user } = me;
  return (
    <>
      <PageHeader eyebrow="Account" title="Account & security" description={user.email} />
      <div className={styles.grid}>
        <div className={styles.span6}>
          <Panel title="Profile">
            <dl className={styles.fieldList}>
              <div className={styles.field}>
                <dt>Name</dt>
                <dd>{user.display_name}</dd>
              </div>
              <div className={styles.field}>
                <dt>Role</dt>
                <dd>{user.role_name}</dd>
              </div>
              <div className={styles.field}>
                <dt>Department</dt>
                <dd>{user.department}</dd>
              </div>
              <div className={styles.field}>
                <dt>Two-factor sign-in</dt>
                <dd>
                  {user.mfa_enabled ? (
                    <Badge tone="success">On</Badge>
                  ) : (
                    <Link className={styles.inlineLink} href="/two-factor/setup">
                      Turn on
                    </Link>
                  )}
                </dd>
              </div>
            </dl>
          </Panel>
        </div>
        <div className={styles.span6}>
          <Panel title="Change password">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void changePassword();
              }}
            >
              <TextField
                label="Current password"
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                required
              />
              <TextField
                label="New password"
                type="password"
                autoComplete="new-password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                required
              />
              <TextField
                label="Repeat new password"
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
              />
              <FormError message={error} />
              {message && (
                <p className={styles.notice} role="status">
                  {message}
                </p>
              )}
              <div className={styles.actionsRow}>
                <Button variant="primary" type="submit">
                  Change password
                </Button>
              </div>
            </form>
          </Panel>
        </div>
        <div className={styles.span6}>
          <Panel title="Active sessions">
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Last active</th>
                    <th>Device</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s) => (
                    <tr key={s.id}>
                      <td>
                        {when(s.last_seen_at)}
                        <div className={styles.muted}>{s.ip ?? "—"}</div>
                      </td>
                      <td className={styles.muted}>{s.user_agent ?? "Unknown"}</td>
                      <td>
                        {s.current ? (
                          <Badge tone="gold">This device</Badge>
                        ) : (
                          <Button size="sm" onClick={() => void revoke(s.id)}>
                            Sign out
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
        <div className={styles.span6}>
          <Panel title="Recent sign-ins">
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Result</th>
                    <th>From</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h, i) => (
                    <tr key={`${h.occurred_at}-${i}`}>
                      <td>{when(h.occurred_at)}</td>
                      <td>
                        <Badge
                          tone={
                            h.outcome === "success"
                              ? "success"
                              : h.outcome.startsWith("password_ok")
                                ? "neutral"
                                : "warning"
                          }
                        >
                          {h.outcome.replaceAll("_", " ")}
                        </Badge>
                      </td>
                      <td className={styles.muted}>{h.ip ?? "—"}</td>
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

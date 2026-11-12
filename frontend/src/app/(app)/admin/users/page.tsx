"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Badge,
  Button,
  Dialog,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SelectField,
  TextField,
} from "@/components/ui";
import { ApiError, send } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useStepUp } from "@/lib/auth/StepUpProvider";
import type { UserOut } from "@/lib/auth/types";

import styles from "@/app/pages.module.css";

interface RoleOut {
  code: string;
  name: string;
  mfa_required: boolean;
  permissions: string[];
}
interface PermissionOut {
  code: string;
  description: string;
  sensitive: boolean;
  director_only: boolean;
}
interface OverrideOut {
  permission: string;
  effect: "grant" | "deny";
  reason: string;
}

const STATUS_TONE = { active: "success", invited: "gold", suspended: "danger" } as const;

export default function UsersPage() {
  const { me } = useAuth();
  const withStepUp = useStepUp();
  const [users, setUsers] = useState<UserOut[]>([]);
  const [roles, setRoles] = useState<RoleOut[]>([]);
  const [perms, setPerms] = useState<PermissionOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [link, setLink] = useState<{ label: string; url: string } | null>(null);
  const [form, setForm] = useState({ email: "", display_name: "", role: "business_development" });
  const [editing, setEditing] = useState<UserOut | null>(null);

  const load = useCallback(async () => {
    const [u, r, p] = await Promise.all([
      send<UserOut[]>("GET", "/admin/users"),
      send<RoleOut[]>("GET", "/admin/roles"),
      send<PermissionOut[]>("GET", "/admin/permissions"),
    ]);
    setUsers(u.data);
    setRoles(r.data);
    setPerms(p.data);
  }, []);

  useEffect(() => {
    void load().catch((e: unknown) =>
      setError(e instanceof ApiError ? e.message : "Could not load users."),
    );
  }, [load]);

  async function run(action: () => Promise<void>) {
    setError(null);
    try {
      await withStepUp(action);
      await load();
    } catch (e) {
      if (e instanceof ApiError && e.code === "cancelled") return;
      setError(e instanceof ApiError ? e.message : "The action failed.");
    }
  }

  const staffRoles = roles.filter((r) => r.code !== "director");

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Users & access"
        description="Only the Director sees all records. Each staff member works within their department. Individual exceptions are audited."
      />
      <FormError message={error} />
      {link && (
        <div className={styles.notice} role="status" data-testid="one-time-link">
          <strong>{link.label}</strong> Give this one-time link to the person securely. It is shown
          only once.
          <div className={styles.mono} style={{ marginTop: 8 }}>
            {link.url}
          </div>
          <div className={styles.actionsRow}>
            <Button size="sm" onClick={() => void navigator.clipboard?.writeText(link.url)}>
              Copy link
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setLink(null)}>
              Dismiss
            </Button>
          </div>
        </div>
      )}
      <div className={styles.grid} style={{ marginTop: 20 }}>
        <div className={styles.span12}>
          <Panel eyebrow="New staff account" title="Invite a staff member">
            <form
              className={styles.formGrid}
              onSubmit={(e) => {
                e.preventDefault();
                void run(async () => {
                  const { data } = await send<{ invitation_url: string; user: UserOut }>(
                    "POST",
                    "/admin/users",
                    { body: form },
                  );
                  setLink({
                    label: `Invitation for ${data.user.display_name}.`,
                    url: data.invitation_url,
                  });
                  setForm({ ...form, email: "", display_name: "" });
                });
              }}
            >
              <TextField
                label="Full name"
                value={form.display_name}
                required
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              />
              <TextField
                label="Work email"
                type="email"
                value={form.email}
                required
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
              <SelectField
                label="Department role"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                options={staffRoles.map((r) => ({ value: r.code, label: r.name }))}
              />
              <div className={styles.field}>
                <Button variant="primary" type="submit">
                  Create & get invitation link
                </Button>
              </div>
            </form>
          </Panel>
        </div>
        <div className={styles.span12}>
          <Panel title="Accounts">
            {users.length === 0 ? (
              <EmptyState title="No accounts yet">Invite your first staff member above.</EmptyState>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Role</th>
                      <th>Status</th>
                      <th>2FA</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => {
                      const self = u.id === me.user.id;
                      return (
                        <tr key={u.id} data-testid={`user-${u.email}`}>
                          <td>
                            {u.display_name}
                            {u.is_dev_account && (
                              <>
                                {" "}
                                <Badge tone="warning">Dev</Badge>
                              </>
                            )}
                            <div className={styles.muted}>{u.email}</div>
                          </td>
                          <td>
                            {u.role_name}
                            <div className={styles.muted}>{u.department}</div>
                          </td>
                          <td>
                            <Badge tone={STATUS_TONE[u.status]}>{u.status}</Badge>
                          </td>
                          <td>
                            {u.mfa_enabled ? (
                              <Badge tone="success">On</Badge>
                            ) : (
                              <span className={styles.muted}>Off</span>
                            )}
                          </td>
                          <td>
                            {self ? (
                              <span className={styles.muted}>You</span>
                            ) : (
                              <div className={styles.rowActions}>
                                {u.status === "suspended" ? (
                                  <Button
                                    size="sm"
                                    onClick={() =>
                                      void run(async () => {
                                        await send("POST", `/admin/users/${u.id}/reactivate`);
                                      })
                                    }
                                  >
                                    Reactivate
                                  </Button>
                                ) : (
                                  <Button
                                    size="sm"
                                    onClick={() =>
                                      void run(async () => {
                                        await send("POST", `/admin/users/${u.id}/suspend`);
                                      })
                                    }
                                  >
                                    Suspend
                                  </Button>
                                )}
                                <Button
                                  size="sm"
                                  onClick={() =>
                                    void run(async () => {
                                      const { data } = await send<{ url: string }>(
                                        "POST",
                                        `/admin/users/${u.id}/reset-link`,
                                      );
                                      setLink({
                                        label: `${u.status === "invited" ? "Invitation" : "Password reset"} link for ${u.display_name}.`,
                                        url: data.url,
                                      });
                                    })
                                  }
                                >
                                  {u.status === "invited" ? "New invitation link" : "Reset link"}
                                </Button>
                                <Button size="sm" variant="ghost" onClick={() => setEditing(u)}>
                                  Access…
                                </Button>
                              </div>
                            )}
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
      {editing && (
        <AccessDialog
          user={editing}
          roles={staffRoles}
          perms={perms}
          onClose={() => setEditing(null)}
          run={run}
        />
      )}
    </>
  );
}

function AccessDialog({
  user,
  roles,
  perms,
  onClose,
  run,
}: {
  user: UserOut;
  roles: RoleOut[];
  perms: PermissionOut[];
  onClose: () => void;
  run: (action: () => Promise<void>) => Promise<void>;
}) {
  const [overrides, setOverrides] = useState<OverrideOut[]>([]);
  const [role, setRole] = useState(user.role);
  const [permission, setPermission] = useState("");
  const [effect, setEffect] = useState<"grant" | "deny">("grant");
  const [reason, setReason] = useState("");
  const grantable = perms.filter((p) => !p.director_only);

  const load = useCallback(async () => {
    const { data } = await send<OverrideOut[]>("GET", `/admin/users/${user.id}/overrides`);
    setOverrides(data);
  }, [user.id]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Dialog open title={`Access for ${user.display_name}`} onClose={onClose}>
      <SelectField
        label="Department role"
        value={role}
        onChange={(e) => setRole(e.target.value)}
        options={roles.map((r) => ({ value: r.code, label: r.name }))}
      />
      <Button
        size="sm"
        disabled={role === user.role}
        onClick={() =>
          void run(async () => {
            await send("PUT", `/admin/users/${user.id}/role`, { body: { role } });
            onClose();
          })
        }
      >
        Change role (signs them out)
      </Button>

      <h3 style={{ margin: "20px 0 8px", fontSize: 15 }}>Individual exceptions</h3>
      {overrides.length === 0 && <p className={styles.muted}>None. The role defines all access.</p>}
      <ul style={{ listStyle: "none", padding: 0, margin: "0 0 12px" }}>
        {overrides.map((o) => (
          <li
            key={o.permission}
            className={styles.rowActions}
            style={{ alignItems: "center", marginBottom: 6 }}
          >
            <Badge tone={o.effect === "grant" ? "gold" : "danger"}>{o.effect}</Badge>
            <span className={styles.mono}>{o.permission}</span>
            <Button
              size="sm"
              variant="ghost"
              onClick={() =>
                void run(async () => {
                  await send("DELETE", `/admin/users/${user.id}/overrides/${o.permission}`);
                  await load();
                })
              }
            >
              Remove
            </Button>
          </li>
        ))}
      </ul>
      <SelectField
        label="Permission"
        value={permission}
        onChange={(e) => setPermission(e.target.value)}
        options={[
          { value: "", label: "Choose…" },
          ...grantable.map((p) => ({
            value: p.code,
            label: `${p.description}${p.sensitive ? " (sensitive)" : ""}`,
          })),
        ]}
      />
      <SelectField
        label="Effect"
        value={effect}
        onChange={(e) => setEffect(e.target.value as "grant" | "deny")}
        options={[
          { value: "grant", label: "Grant" },
          { value: "deny", label: "Deny" },
        ]}
      />
      <TextField
        label="Reason (recorded in the audit log)"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <div className={styles.rowActions} style={{ justifyContent: "flex-end", marginTop: 12 }}>
        <Button variant="ghost" onClick={onClose}>
          Close
        </Button>
        <Button
          variant="primary"
          disabled={!permission || reason.trim().length < 5}
          onClick={() =>
            void run(async () => {
              await send("POST", `/admin/users/${user.id}/overrides`, {
                body: { permission, effect, reason },
              });
              setPermission("");
              setReason("");
              await load();
            })
          }
        >
          Save exception
        </Button>
      </div>
    </Dialog>
  );
}

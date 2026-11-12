"use client";

import { useState } from "react";
import { LuPlus } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
import {
  Badge,
  Button,
  Dialog,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SegmentedControl,
  SelectField,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { PRIORITY_TONE, type Person, type Task } from "@/lib/comms";
import { label } from "@/lib/inventory/types";
import { useRealtimeEvent } from "@/lib/realtime/RealtimeProvider";
import { formatDateTime } from "@/lib/tenders/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

export default function TasksPage() {
  const { me, can } = useAuth();
  const { play } = useSound();
  const [view, setView] = useState<"mine" | "assigned_by_me">("mine");
  const [closed, setClosed] = useState(false);
  const tasks = useResource<Task[]>(`/comms/tasks?view=${view}&include_closed=${closed}`);
  const people = useResource<Person[]>("/comms/people");
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<Task | null>(null);
  const [form, setForm] = useState({
    title: "",
    description: "",
    assigned_to: "",
    due_at: "",
    priority: "normal",
  });
  const [update, setUpdate] = useState({ status: "", note: "" });
  const [error, setError] = useState<string | null>(null);
  const director = can("comms.announcements.send");
  useRealtimeEvent("task", () => void tasks.reload());

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      play("complete");
      await tasks.reload();
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Communications"
        title="Tasks"
        description={
          director
            ? "Assign work, set deadlines and follow progress."
            : "Your assigned work. Update progress or ask for clarification in the task."
        }
        actions={
          <Button
            variant="primary"
            icon={<LuPlus aria-hidden="true" />}
            onClick={() => setOpen(true)}
          >
            {director ? "Assign task" : "Add my task"}
          </Button>
        }
      />
      <div className={styles.toolbar}>
        <SegmentedControl
          label="Task view"
          value={view}
          options={[
            { value: "mine", label: "Assigned to me" },
            { value: "assigned_by_me", label: "Assigned by me" },
          ]}
          onChange={setView}
        />
        <label className={styles.check}>
          <input type="checkbox" checked={closed} onChange={(e) => setClosed(e.target.checked)} />{" "}
          Show finished
        </label>
      </div>
      <FormError message={error ?? tasks.error} />
      <Panel title="Tasks">
        {tasks.data && tasks.data.length === 0 ? (
          <EmptyState title="Nothing here">No tasks in this view.</EmptyState>
        ) : (
          <ul className={styles.timeline}>
            {tasks.data?.map((t) => (
              <li key={t.id} className={styles.timelineItem}>
                <Badge
                  tone={
                    t.overdue
                      ? "danger"
                      : t.status === "done"
                        ? "success"
                        : PRIORITY_TONE[t.priority]
                  }
                >
                  {t.overdue ? "Overdue" : label(t.status)}
                </Badge>
                <div>
                  <button
                    type="button"
                    className={styles.rowLink}
                    style={{
                      background: "none",
                      border: 0,
                      padding: 0,
                      cursor: "pointer",
                      font: "inherit",
                    }}
                    onClick={() => {
                      setUpdate({ status: "", note: "" });
                      void send<Task>("GET", `/comms/tasks/${t.id}`).then(({ data }) =>
                        setDetail(data),
                      );
                    }}
                  >
                    {t.title}
                  </button>
                  <div className={page.muted}>
                    {view === "mine"
                      ? `from ${t.assigned_by.id === me.user.id ? "me" : t.assigned_by.display_name}`
                      : `to ${t.assigned_to.display_name}`}
                    {t.due_at && ` · due ${formatDateTime(t.due_at)}`} · {label(t.priority)}
                    {t.ai_generated && " · prepared by JARVIS"}
                    {view === "assigned_by_me" &&
                      (t.acknowledged_at ? " · seen" : " · not yet seen")}
                  </div>
                </div>
                <span />
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Dialog
        open={open}
        title={director ? "Assign task" : "Add my task"}
        onClose={() => setOpen(false)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const body = {
              ...Object.fromEntries(Object.entries(form).filter(([, v]) => v !== "")),
              ...(form.due_at ? { due_at: new Date(form.due_at).toISOString() } : {}),
            };
            void act(async () => {
              await send("POST", "/comms/tasks", { body });
              setOpen(false);
              setForm({ ...form, title: "", description: "" });
            });
          }}
        >
          <div className={styles.formGrid}>
            <TextField
              label="Task"
              required
              minLength={2}
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            {director && (
              <SelectField
                label="Assign to"
                value={form.assigned_to}
                onChange={(e) => setForm({ ...form, assigned_to: e.target.value })}
                options={[
                  { value: "", label: "Me" },
                  ...(people.data ?? [])
                    .filter((p) => p.id !== me.user.id)
                    .map((p) => ({ value: p.id, label: p.display_name })),
                ]}
              />
            )}
            <TextField
              label="Deadline"
              type="datetime-local"
              value={form.due_at}
              onChange={(e) => setForm({ ...form, due_at: e.target.value })}
            />
            <SelectField
              label="Priority"
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              options={["low", "normal", "high", "urgent"].map((p) => ({
                value: p,
                label: label(p),
              }))}
            />
          </div>
          <label className={styles.textareaLabel}>
            Details
            <textarea
              className={styles.textarea}
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save task
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={detail !== null}
        title={detail?.title ?? "Task"}
        onClose={() => setDetail(null)}
      >
        {detail && (
          <div className={styles.dialogForm}>
            {detail.description && <p className="serif-text">{detail.description}</p>}
            <ol className={styles.timeline}>
              {detail.updates.map((u, i) => (
                <li key={i} className={styles.timelineItem}>
                  <strong>{u.author.display_name}</strong>
                  <div>
                    {u.note}
                    <div className={page.muted}>
                      {formatDateTime(u.created_at)}
                      {u.status ? ` · ${label(u.status)}` : ""}
                    </div>
                  </div>
                  <span />
                </li>
              ))}
            </ol>
            <form
              className={styles.formGrid}
              style={{ alignItems: "end" }}
              onSubmit={(e) => {
                e.preventDefault();
                void act(async () => {
                  const { data } = await send<Task>("POST", `/comms/tasks/${detail.id}/updates`, {
                    body: {
                      note: update.note,
                      ...(update.status ? { status: update.status } : {}),
                    },
                  });
                  setDetail(data);
                  setUpdate({ status: "", note: "" });
                });
              }}
            >
              <TextField
                label="Update or question"
                required
                value={update.note}
                onChange={(e) => setUpdate({ ...update, note: e.target.value })}
              />
              <SelectField
                label="Status"
                value={update.status}
                onChange={(e) => setUpdate({ ...update, status: e.target.value })}
                options={[
                  { value: "", label: "No change" },
                  ...[
                    "in_progress",
                    "blocked",
                    "done",
                    ...(detail.assigned_by.id === me.user.id ? ["cancelled", "open"] : []),
                  ].map((s) => ({ value: s, label: label(s) })),
                ]}
              />
              <Button type="submit" variant="primary">
                Post update
              </Button>
            </form>
          </div>
        )}
      </Dialog>
    </>
  );
}

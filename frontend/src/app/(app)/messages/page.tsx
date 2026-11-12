"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { LuCheck, LuSend } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
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
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { Conversation, Message, Person } from "@/lib/comms";
import { useRealtimeEvent } from "@/lib/realtime/RealtimeProvider";
import { formatDateTime } from "@/lib/tenders/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

function Messages() {
  const { me, can } = useAuth();
  const { play } = useSound();
  const params = useSearchParams();
  const convs = useResource<Conversation[]>("/comms/conversations");
  const people = useResource<Person[]>("/comms/people");
  const [active, setActive] = useState<string | null>(params.get("c"));
  const thread = useResource<Message[]>(active ? `/comms/conversations/${active}/messages` : null);
  const [text, setText] = useState("");
  const [needsAck, setNeedsAck] = useState(false);
  const [dialog, setDialog] = useState<"direct" | "channel" | null>(null);
  const [pick, setPick] = useState("");
  const [channel, setChannel] = useState({ name: "", department_code: "" });
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const director = can("comms.announcements.send");
  const current = convs.data?.find((c) => c.id === active);

  useEffect(() => {
    if (!active && convs.data?.length) setActive(convs.data[0]!.id);
  }, [active, convs.data]);
  useEffect(() => end.current?.scrollIntoView({ block: "end" }), [thread.data]);
  useRealtimeEvent("message", (event) => {
    void convs.reload();
    if (event.conversation_id === active) void thread.reload();
  });

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      await Promise.all([convs.reload(), thread.reload()]);
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Communications"
        title="Messages"
        description="Direct messages, department channels and company announcements. Only members can read a conversation; nobody is added silently."
        actions={
          <div className={page.actionsRow} style={{ marginTop: 0 }}>
            <Button onClick={() => setDialog("direct")}>New message</Button>
            {director && <Button onClick={() => setDialog("channel")}>New channel</Button>}
          </div>
        }
      />
      <FormError message={error ?? convs.error} />
      <div className={page.grid}>
        <div className={page.span4}>
          <Panel title="Conversations">
            <ul className={styles.timeline}>
              {convs.data?.map((c) => (
                <li
                  key={c.id}
                  className={styles.timelineItem}
                  style={{ gridTemplateColumns: "1fr auto" }}
                >
                  <button
                    type="button"
                    onClick={() => setActive(c.id)}
                    aria-current={c.id === active ? "true" : undefined}
                    className={styles.rowLink}
                    style={{
                      background: "none",
                      border: 0,
                      padding: 0,
                      textAlign: "left",
                      cursor: "pointer",
                      font: "inherit",
                      fontWeight: c.id === active ? 700 : 500,
                    }}
                  >
                    {c.title}
                    <div className={page.muted}>
                      {c.kind === "announcements"
                        ? "Company-wide"
                        : c.kind === "channel"
                          ? `${c.members.length} members`
                          : "Direct"}
                    </div>
                  </button>
                  {c.unread > 0 ? <Badge tone="gold">{String(c.unread)}</Badge> : <span />}
                </li>
              ))}
            </ul>
          </Panel>
        </div>
        <div className={page.span8}>
          <Panel title={current?.title ?? "Conversation"}>
            {!current ? (
              <EmptyState title="No conversation selected">
                Choose a conversation or start a new one.
              </EmptyState>
            ) : (
              <>
                <ol
                  className={styles.timeline}
                  aria-label="Messages"
                  style={{ maxHeight: 420, overflowY: "auto" }}
                >
                  {thread.data?.length === 0 && <li className={page.muted}>No messages yet.</li>}
                  {thread.data?.map((m) => (
                    <li key={m.id} className={styles.timelineItem}>
                      <strong>{m.sender.id === me.user.id ? "You" : m.sender.display_name}</strong>
                      <div>
                        <p className={styles.timelineBody} style={{ color: "var(--text-primary)" }}>
                          {m.body}
                        </p>
                        <div className={page.muted}>
                          {formatDateTime(m.created_at)}
                          {m.ai_generated && " · prepared by JARVIS"}
                          {m.requires_ack &&
                            m.sender.id === me.user.id &&
                            ` · ${m.ack_count} acknowledged`}
                        </div>
                      </div>
                      {m.requires_ack && m.sender.id !== me.user.id ? (
                        m.acknowledged_by_me ? (
                          <Badge tone="success">Acknowledged</Badge>
                        ) : (
                          <Button
                            size="sm"
                            icon={<LuCheck aria-hidden="true" />}
                            onClick={() =>
                              void act(() => send("POST", `/comms/messages/${m.id}/acknowledge`))
                            }
                          >
                            Acknowledge
                          </Button>
                        )
                      ) : (
                        <span />
                      )}
                    </li>
                  ))}
                  <div ref={end} />
                </ol>
                {(current.kind !== "announcements" || director) && (
                  <form
                    className={styles.formGrid}
                    style={{
                      gridTemplateColumns: "1fr auto auto",
                      alignItems: "end",
                      marginTop: 12,
                    }}
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (!text.trim()) return;
                      void act(async () => {
                        await send("POST", `/comms/conversations/${current.id}/messages`, {
                          body: { body: text, requires_ack: needsAck },
                        });
                        setText("");
                        setNeedsAck(false);
                      });
                    }}
                  >
                    <TextField
                      label="Message"
                      value={text}
                      maxLength={10000}
                      onChange={(e) => setText(e.target.value)}
                    />
                    <label className={styles.check}>
                      <input
                        type="checkbox"
                        checked={needsAck}
                        onChange={(e) => setNeedsAck(e.target.checked)}
                      />
                      Ask to acknowledge
                    </label>
                    <Button type="submit" variant="primary" icon={<LuSend aria-hidden="true" />}>
                      Send
                    </Button>
                  </form>
                )}
              </>
            )}
          </Panel>
        </div>
      </div>

      <Dialog open={dialog === "direct"} title="New message" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(async () => {
              const { data } = await send<Conversation>("POST", "/comms/conversations/direct", {
                body: { user_id: pick },
              });
              setActive(data.id);
              setDialog(null);
            });
          }}
        >
          <SelectField
            label="To"
            required
            value={pick}
            onChange={(e) => setPick(e.target.value)}
            options={[
              { value: "", label: "Choose a colleague" },
              ...(people.data ?? [])
                .filter((p) => p.id !== me.user.id)
                .map((p) => ({
                  value: p.id,
                  label: `${p.display_name}${p.department ? ` · ${p.department}` : ""}`,
                })),
            ]}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Open conversation
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={dialog === "channel"} title="New channel" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(async () => {
              const { data } = await send<Conversation>("POST", "/comms/conversations/channels", {
                body: {
                  name: channel.name,
                  ...(channel.department_code ? { department_code: channel.department_code } : {}),
                },
              });
              setActive(data.id);
              setDialog(null);
            });
          }}
        >
          <TextField
            label="Channel name"
            required
            minLength={2}
            value={channel.name}
            onChange={(e) => setChannel({ ...channel, name: e.target.value })}
          />
          <SelectField
            label="Department (adds everyone in it)"
            value={channel.department_code}
            onChange={(e) => setChannel({ ...channel, department_code: e.target.value })}
            options={[
              { value: "", label: "None" },
              ...["business_development", "procurement", "finance", "logistics", "hr_admin"].map(
                (d) => ({ value: d, label: d.replace("_", " ") }),
              ),
            ]}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create channel
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

export default function MessagesPage() {
  return (
    <Suspense>
      <Messages />
    </Suspense>
  );
}

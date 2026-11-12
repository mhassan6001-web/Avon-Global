"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { LuPlus, LuSend } from "react-icons/lu";

import { JarvisPresence } from "@/components/jarvis/JarvisPresence";
import { TaskFlow } from "@/components/jarvis/TaskFlow";
import { Badge, Button, EmptyState, FormError, PageHeader, Panel } from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import {
  applyStep,
  toolLabel,
  type Briefing,
  type Chain,
  type GatewayStep,
  type JarvisAction,
  type JarvisConversation,
  type JarvisMessage,
  type JarvisStatus,
} from "@/lib/jarvis";
import { useRealtimeEvent } from "@/lib/realtime/RealtimeProvider";
import { useSound } from "@/lib/sound/SoundProvider";
import { formatDateTime } from "@/lib/tenders/types";

import styles from "./jarvis.module.css";

const ACTION_TONE = {
  proposed: "gold",
  executed: "success",
  cancelled: "neutral",
  failed: "danger",
  expired: "neutral",
} as const;

export default function JarvisPage() {
  const { play } = useSound();
  const status = useResource<JarvisStatus>("/jarvis/status");
  const briefing = useResource<Briefing>("/jarvis/briefing");
  const conversations = useResource<JarvisConversation[]>("/jarvis/conversations");
  const [current, setCurrent] = useState<string | null>(null);
  const thread = useResource<JarvisMessage[]>(
    current ? `/jarvis/conversations/${current}/messages` : null,
  );
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chain, setChain] = useState<Chain>({});
  const [target, setTarget] = useState<string | undefined>();
  const end = useRef<HTMLDivElement>(null);
  const configured = status.data?.ai_configured ?? false;

  useRealtimeEvent("jarvis.step", (event) => {
    const e = event as unknown as { step: GatewayStep; tool: string };
    if (e.step === "interpreting") setChain({});
    setChain((c) => applyStep(e.step === "interpreting" ? {} : c, e.step));
    setTarget(toolLabel(e.tool));
  });

  useEffect(() => {
    if (!current && conversations.data?.length) setCurrent(conversations.data[0]!.id);
  }, [conversations.data, current]);

  useEffect(() => end.current?.scrollIntoView({ block: "end" }), [thread.data]);

  const ask = useCallback(async () => {
    const question = text.trim();
    if (!question || busy) return;
    setBusy(true);
    setError(null);
    play("processing");
    try {
      let id = current;
      if (!id) {
        const { data } = await send<JarvisConversation>("POST", "/jarvis/conversations", {
          body: {},
        });
        id = data.id;
        setCurrent(id);
      }
      await send("POST", `/jarvis/conversations/${id}/messages`, { body: { text: question } });
      setText("");
      play("response");
      await Promise.all([thread.reload(), conversations.reload()]);
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    } finally {
      setBusy(false);
    }
  }, [text, busy, current, play, thread, conversations]);

  async function decide(action: JarvisAction, verb: "confirm" | "cancel") {
    setError(null);
    try {
      const { data } = await send<JarvisAction>("POST", `/jarvis/actions/${action.id}/${verb}`);
      if (data.status === "failed" || data.status === "expired") {
        setError(data.error ?? "The action could not be completed.");
        play("warning");
      } else {
        play(verb === "confirm" ? "complete" : "navigation");
      }
      await thread.reload();
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Executive intelligence"
        title="JARVIS"
        description="Ask about the records you are allowed to see. JARVIS prepares changes; you confirm them. Nothing is paid, approved or submitted by JARVIS."
        actions={
          <Button icon={<LuPlus aria-hidden="true" />} onClick={() => setCurrent(null)}>
            New conversation
          </Button>
        }
      />
      <FormError message={error ?? status.error} />

      <div className={styles.layout}>
        <div style={{ display: "grid", gap: "var(--space-5)", alignContent: "start" }}>
          <Panel title="Presence">
            <div className={styles.presence}>
              <JarvisPresence
                state={
                  !status.data ? "idle" : !configured ? "offline" : busy ? "processing" : "idle"
                }
                size={240}
              />
              <TaskFlow statuses={chain} target={target} />
            </div>
          </Panel>
          <Panel title="Conversations">
            {conversations.data && conversations.data.length === 0 ? (
              <EmptyState title="No conversations yet">Ask a question to start one.</EmptyState>
            ) : (
              <ul className={styles.convList}>
                {conversations.data?.map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      className={styles.convButton}
                      aria-current={c.id === current}
                      onClick={() => setCurrent(c.id)}
                      title={c.title}
                    >
                      {c.title}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>

        <div style={{ display: "grid", gap: "var(--space-5)", alignContent: "start" }}>
          <Panel title="Daily briefing">
            {briefing.data && (
              <div className={styles.briefing}>
                <p>
                  {briefing.data.greeting} Briefing for {briefing.data.local_date}, from recorded
                  data only.
                </p>
                {briefing.data.sections.map((s) => (
                  <section key={s.key} aria-labelledby={`brief-${s.key}`}>
                    <h3 id={`brief-${s.key}`}>
                      {s.href ? <Link href={s.href}>{s.title}</Link> : s.title}
                    </h3>
                    <ul data-empty={s.empty}>
                      {s.lines.map((line, i) => (
                        <li key={i}>{line}</li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Conversation">
            {!configured && status.data && (
              <p className="serif-text" role="status">
                JARVIS&apos;s AI service is not configured yet. It needs the Director&apos;s API key
                on the server. The briefing above works without it.
              </p>
            )}
            <div className={styles.thread} aria-live="polite">
              {current === null && (
                <EmptyState title="New conversation">
                  Your question starts a new conversation.
                </EmptyState>
              )}
              {thread.data?.map((m) => (
                <div key={m.id} className={styles.turn} data-role={m.role}>
                  {m.text && <div className={styles.bubble}>{m.text}</div>}
                  {m.tools_used.length > 0 && (
                    <div className={styles.tools}>
                      {m.tools_used.map((t, i) => (
                        <Badge key={i} tone="neutral">
                          Used: {toolLabel(t)}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {m.actions.map((a) => (
                    <div
                      key={a.id}
                      className={styles.card}
                      role="group"
                      aria-label="Prepared action"
                    >
                      <div>
                        <Badge tone={ACTION_TONE[a.status]}>
                          {a.status === "proposed" ? "Needs your confirmation" : a.status}
                        </Badge>
                      </div>
                      <div>{a.summary}</div>
                      {a.error && <div className="tabular">{a.error}</div>}
                      {a.status === "proposed" ? (
                        <div className={styles.cardActions}>
                          <Button variant="ghost" onClick={() => void decide(a, "cancel")}>
                            Cancel
                          </Button>
                          <Button variant="primary" onClick={() => void decide(a, "confirm")}>
                            Confirm
                          </Button>
                        </div>
                      ) : (
                        <div className="tabular" style={{ color: "var(--text-muted)" }}>
                          Prepared {formatDateTime(a.created_at)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))}
              <div ref={end} />
            </div>
            <form
              className={styles.composer}
              onSubmit={(e) => {
                e.preventDefault();
                void ask();
              }}
            >
              <label htmlFor="jarvis-input" className="visually-hidden">
                Ask JARVIS
              </label>
              <textarea
                id="jarvis-input"
                value={text}
                maxLength={4000}
                disabled={!configured || busy}
                placeholder={configured ? "Ask JARVIS…" : "AI service not configured"}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void ask();
                  }
                }}
              />
              <div className={styles.cardActions}>
                <Button
                  type="submit"
                  variant="primary"
                  icon={<LuSend aria-hidden="true" />}
                  disabled={!configured || busy || !text.trim()}
                >
                  {busy ? "Working…" : "Ask"}
                </Button>
              </div>
            </form>
          </Panel>
        </div>
      </div>
    </>
  );
}

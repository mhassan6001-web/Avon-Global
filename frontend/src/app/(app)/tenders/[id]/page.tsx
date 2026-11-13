"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { LuPlus, LuSend, LuTrash2 } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
import {
  Badge,
  Button,
  Dialog,
  EmptyState,
  FormError,
  IconButton,
  PageHeader,
  Panel,
  SelectField,
  Spinner,
  TextField,
} from "@/components/ui";
import { API_PREFIX, send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { DIVISION_LABEL, formatMoney } from "@/lib/crm/types";
import { useSound } from "@/lib/sound/SoundProvider";
import {
  ACTIVE_STATUSES,
  countdown,
  formatDateTime,
  KIND_LABEL,
  METHOD_LABEL,
  REQUIREMENT_KINDS,
  REQUIREMENT_STATUS_LABEL,
  REQUIREMENT_STATUSES,
  TENDER_STATUS_LABEL,
  type TenderDetail,
} from "@/lib/tenders/types";

import page from "@/app/pages.module.css";

type Prompt = { kind: "outcome" | "no_bid" | "approval" | "requirement" } | null;

export default function TenderPage() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAuth();
  const { play } = useSound();
  const { data, error, loading, reload } = useResource<TenderDetail>(`/tenders/${id}`);
  const [actionError, setActionError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<Prompt>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState("won");
  const [award, setAward] = useState("");
  const [reqForm, setReqForm] = useState({ kind: "document", description: "", mandatory: true });
  const editable = can("tenders.records.edit");

  async function act(
    fn: () => Promise<unknown>,
    cue: "approval" | "complete" | "navigation" = "navigation",
  ) {
    setActionError(null);
    try {
      await fn();
      play(cue);
      setPrompt(null);
      await reload();
    } catch (e) {
      setActionError(errorMessage(e));
      play("warning");
    }
  }

  if (loading && !data) return <Spinner label="Loading tender" />;
  if (!data)
    return (
      <EmptyState title="Tender not available">
        {error ?? "This tender could not be loaded."}
      </EmptyState>
    );
  const { tender: t, requirements, approval } = data;
  const active = ACTIVE_STATUSES.includes(t.status);
  const frozen = t.status === "awaiting_approval" || t.status === "approved";
  const canEditChecklist = editable && active && !frozen;
  const due = countdown(t.submission_deadline);
  const openMandatory = requirements.filter(
    (r) => r.mandatory && (r.status === "pending" || r.status === "not_met"),
  );

  return (
    <>
      <PageHeader
        eyebrow={
          <>
            {`${t.reference} · ${KIND_LABEL[t.kind]} · `}
            <a href={`${API_PREFIX}/documents/tender-packs/${t.id}`} download>
              Download tender pack (ZIP)
            </a>
          </>
        }
        title={t.title}
        description={`${t.issuer_name}${t.issuer_reference ? ` · ${t.issuer_reference}` : ""}`}
        actions={
          <Badge
            tone={t.status === "won" ? "success" : frozen ? "gold" : active ? "signal" : "neutral"}
          >
            {TENDER_STATUS_LABEL[t.status]}
          </Badge>
        }
      />
      <p className={page.note}>
        <Link href="/tenders" className={page.inlineLink}>
          All tenders
        </Link>
      </p>
      <FormError message={actionError} />
      <div className={page.grid}>
        <div className={page.span5}>
          <Panel title="Key dates and details">
            <dl className={styles.facts}>
              <dt>Submission deadline</dt>
              <dd>
                {formatDateTime(t.submission_deadline)}{" "}
                {active && <Badge tone={due.tone}>{due.text}</Badge>}
              </dd>
              <dt>Clarifications by</dt>
              <dd>{formatDateTime(t.clarification_deadline)}</dd>
              <dt>Method</dt>
              <dd>{METHOD_LABEL[t.submission_method]}</dd>
              <dt>Division</dt>
              <dd>{t.division ? DIVISION_LABEL[t.division] : "—"}</dd>
              <dt>Estimated value</dt>
              <dd>{t.estimated_value ? formatMoney(t.estimated_value, t.currency) : "—"}</dd>
              <dt>Bid security</dt>
              <dd>{t.bid_security_required ? "Required" : "Not required"}</dd>
              <dt>Source</dt>
              <dd>{t.source ?? "—"}</dd>
              {t.submitted_at && (
                <>
                  <dt>Submitted</dt>
                  <dd>
                    {formatDateTime(t.submitted_at)}
                    {t.submitted_by && ` by ${t.submitted_by.display_name}`}
                  </dd>
                </>
              )}
              {t.award_value && (
                <>
                  <dt>Award value</dt>
                  <dd className={styles.amount}>{formatMoney(t.award_value, t.currency)}</dd>
                </>
              )}
              {t.outcome_note && (
                <>
                  <dt>Outcome note</dt>
                  <dd>{t.outcome_note}</dd>
                </>
              )}
            </dl>
            {t.notes && (
              <p className="serif-text" style={{ marginTop: 16, whiteSpace: "pre-wrap" }}>
                {t.notes}
              </p>
            )}
          </Panel>
        </div>
        <div className={page.span7}>
          <Panel
            title="Eligibility and submission checklist"
            actions={
              canEditChecklist ? (
                <Button
                  size="sm"
                  icon={<LuPlus aria-hidden="true" />}
                  onClick={() => setPrompt({ kind: "requirement" })}
                >
                  Add requirement
                </Button>
              ) : undefined
            }
          >
            {requirements.length === 0 ? (
              <EmptyState title="No requirements yet">
                List the eligibility criteria and every document the tender asks for.
              </EmptyState>
            ) : (
              <ul className={styles.timeline} aria-label="Requirements">
                {requirements.map((r) => (
                  <li key={r.id} className={styles.timelineItem}>
                    <Badge
                      tone={
                        r.status === "met"
                          ? "success"
                          : r.status === "not_met"
                            ? "danger"
                            : r.status === "not_applicable"
                              ? "neutral"
                              : "gold"
                      }
                    >
                      {REQUIREMENT_STATUS_LABEL[r.status]}
                    </Badge>
                    <div>
                      <strong>{r.description}</strong>
                      <div className={page.muted}>
                        {r.kind} · {r.mandatory ? "Mandatory" : "Optional"}
                      </div>
                    </div>
                    {canEditChecklist ? (
                      <span style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                        <SelectField
                          label={`Status of ${r.description}`}
                          value={r.status}
                          onChange={(e) =>
                            void act(() =>
                              send("PATCH", `/tenders/requirements/${r.id}`, {
                                body: { status: e.target.value },
                              }),
                            )
                          }
                          options={REQUIREMENT_STATUSES.map((s) => ({
                            value: s,
                            label: REQUIREMENT_STATUS_LABEL[s],
                          }))}
                        />
                        <IconButton
                          label={`Remove ${r.description}`}
                          onClick={() =>
                            void act(() => send("DELETE", `/tenders/requirements/${r.id}`))
                          }
                        >
                          <LuTrash2 />
                        </IconButton>
                      </span>
                    ) : (
                      <span />
                    )}
                  </li>
                ))}
              </ul>
            )}
            {active && !frozen && openMandatory.length > 0 && (
              <p className={page.note}>
                {openMandatory.length} mandatory item(s) must be met before the bid can go for
                approval.
              </p>
            )}
          </Panel>
        </div>
        <div className={page.span12}>
          <Panel title="Bid decision and submission">
            {approval && (
              <p className={page.note} style={{ marginTop: 0 }}>
                Approval {approval.status} · requested by {approval.requested_by}
                {approval.decided_by &&
                  ` · decided by ${approval.decided_by} on ${formatDateTime(approval.decided_at)}`}
                {approval.decision_note && ` · “${approval.decision_note}”`}
              </p>
            )}
            {editable ? (
              <div className={page.actionsRow}>
                {(t.status === "identified" || t.status === "reviewing") && (
                  <Button
                    size="sm"
                    onClick={() =>
                      void act(() =>
                        send("PATCH", `/tenders/${t.id}`, {
                          body: { status: t.status === "identified" ? "reviewing" : "bidding" },
                        }),
                      )
                    }
                  >
                    {t.status === "identified" ? "Start review" : "Decide to bid"}
                  </Button>
                )}
                {(t.status === "reviewing" || t.status === "bidding") && (
                  <Button
                    size="sm"
                    variant="primary"
                    disabled={openMandatory.length > 0}
                    onClick={() => {
                      setText("");
                      setPrompt({ kind: "approval" });
                    }}
                  >
                    Request Director approval
                  </Button>
                )}
                {t.status === "approved" && (
                  <Button
                    size="sm"
                    variant="primary"
                    icon={<LuSend aria-hidden="true" />}
                    onClick={() =>
                      void act(
                        () => send("POST", `/tenders/${t.id}/submitted`, { body: {} }),
                        "complete",
                      )
                    }
                  >
                    Record as submitted
                  </Button>
                )}
                {(t.status === "submitted" || active) && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setText("");
                      setAward("");
                      setResult(t.status === "submitted" ? "won" : "cancelled");
                      setPrompt({ kind: "outcome" });
                    }}
                  >
                    Record outcome
                  </Button>
                )}
                {["identified", "reviewing", "bidding"].includes(t.status) && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setText("");
                      setPrompt({ kind: "no_bid" });
                    }}
                  >
                    No bid
                  </Button>
                )}
                {t.status === "awaiting_approval" && (
                  <span className={page.muted}>
                    Waiting for the Director. Details are frozen until a decision.
                  </span>
                )}
              </div>
            ) : (
              <p className={page.muted}>View only.</p>
            )}
            <p className={page.note}>
              JARVIS and the system never submit a bid. A person records the submission after the
              Director approves.
            </p>
          </Panel>
        </div>
      </div>

      <Dialog
        open={prompt?.kind === "requirement"}
        title="Add requirement"
        onClose={() => setPrompt(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(() => send("POST", `/tenders/${t.id}/requirements`, { body: reqForm })).then(
              () => setReqForm({ ...reqForm, description: "" }),
            );
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Requirement type"
              value={reqForm.kind}
              onChange={(e) => setReqForm({ ...reqForm, kind: e.target.value })}
              options={REQUIREMENT_KINDS.map((k) => ({ value: k, label: k }))}
            />
            <TextField
              label="Requirement"
              required
              minLength={3}
              maxLength={500}
              value={reqForm.description}
              onChange={(e) => setReqForm({ ...reqForm, description: e.target.value })}
            />
          </div>
          <label className={styles.check}>
            <input
              type="checkbox"
              checked={reqForm.mandatory}
              onChange={(e) => setReqForm({ ...reqForm, mandatory: e.target.checked })}
            />
            Mandatory
          </label>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setPrompt(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Add requirement
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={prompt?.kind === "approval"}
        title="Request Director approval"
        onClose={() => setPrompt(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(
              () =>
                send("POST", `/tenders/${t.id}/request-approval`, {
                  body: text ? { note: text } : {},
                }),
              "approval",
            );
          }}
        >
          <TextField
            label="Note for the Director"
            maxLength={2000}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setPrompt(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Send for approval
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={prompt?.kind === "no_bid"}
        title="Record a no-bid decision"
        onClose={() => setPrompt(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(() => send("POST", `/tenders/${t.id}/no-bid`, { body: { reason: text } }));
          }}
        >
          <TextField
            label="Reason"
            required
            minLength={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setPrompt(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Record no bid
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={prompt?.kind === "outcome"}
        title="Record outcome"
        onClose={() => setPrompt(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const body = {
              result,
              ...(text ? { note: text } : {}),
              ...(result === "won" && award ? { award_value: award } : {}),
            };
            void act(
              () => send("POST", `/tenders/${t.id}/outcome`, { body }),
              result === "won" ? "approval" : "navigation",
            );
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Result"
              value={result}
              onChange={(e) => setResult(e.target.value)}
              options={(t.status === "submitted"
                ? ["won", "lost", "cancelled"]
                : ["cancelled"]
              ).map((v) => ({ value: v, label: v[0]!.toUpperCase() + v.slice(1) }))}
            />
            {result === "won" && (
              <TextField
                label="Award value"
                inputMode="decimal"
                pattern="^\d{1,16}(\.\d{1,2})?$"
                value={award}
                onChange={(e) => setAward(e.target.value)}
              />
            )}
          </div>
          <TextField
            label="Note"
            required={result !== "won"}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setPrompt(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save outcome
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

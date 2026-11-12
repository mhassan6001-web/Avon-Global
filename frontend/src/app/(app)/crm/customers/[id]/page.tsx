"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { LuArchive, LuArchiveRestore, LuCheck, LuPencil, LuPlus, LuTrash2 } from "react-icons/lu";

import { CrmNav } from "@/components/crm/CrmNav";
import {
  ActivityDialog,
  ContactDialog,
  CustomerDialog,
  OpportunityDialog,
} from "@/components/crm/forms";
import styles from "@/components/crm/crm.module.css";
import {
  Badge,
  Button,
  EmptyState,
  FormError,
  IconButton,
  PageHeader,
  Panel,
  Spinner,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  ACTIVITY_LABEL,
  COUNTRIES,
  DIVISION_LABEL,
  formatDate,
  formatMoney,
  isOverdue,
  KIND_LABEL,
  STAGE_LABEL,
  STATUS_LABEL,
  type Contact,
  type CustomerDetail,
} from "@/lib/crm/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

type DialogKind = "edit" | "contact" | "opportunity" | "activity" | "follow_up" | null;

export default function CustomerPage() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAuth();
  const { play } = useSound();
  const { data, error, loading, reload } = useResource<CustomerDetail>(`/crm/customers/${id}`);
  const [dialog, setDialog] = useState<DialogKind>(null);
  const [contact, setContact] = useState<Contact | undefined>();
  const [actionError, setActionError] = useState<string | null>(null);
  const editable = can("crm.records.edit");

  async function act(fn: () => Promise<unknown>) {
    setActionError(null);
    try {
      await fn();
      await reload();
    } catch (e) {
      setActionError(errorMessage(e));
      play("warning");
    }
  }

  if (loading && !data) return <Spinner label="Loading customer" />;
  if (!data) {
    return (
      <>
        <CrmNav />
        <EmptyState title="Customer not available">
          {error ?? "This customer could not be loaded."}
        </EmptyState>
      </>
    );
  }
  const { customer, contacts, opportunities, activities } = data;
  const archived = customer.status === "archived";
  const country =
    COUNTRIES.find((c) => c.value === customer.country_code)?.label ?? customer.country_code;

  return (
    <>
      <PageHeader
        eyebrow={customer.reference}
        title={customer.name}
        description={[
          KIND_LABEL[customer.kind],
          customer.industry,
          [customer.city, country].filter(Boolean).join(", "),
        ]
          .filter(Boolean)
          .join(" · ")}
        actions={
          editable ? (
            <div className={page.actionsRow} style={{ marginTop: 0 }}>
              {!archived && (
                <Button
                  size="sm"
                  icon={<LuPencil aria-hidden="true" />}
                  onClick={() => setDialog("edit")}
                >
                  Edit
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                icon={
                  archived ? (
                    <LuArchiveRestore aria-hidden="true" />
                  ) : (
                    <LuArchive aria-hidden="true" />
                  )
                }
                onClick={() =>
                  void act(() =>
                    send(
                      "POST",
                      `/crm/customers/${customer.id}/${archived ? "restore" : "archive"}`,
                    ),
                  )
                }
              >
                {archived ? "Restore" : "Archive"}
              </Button>
            </div>
          ) : undefined
        }
      />
      <CrmNav />
      <FormError message={actionError} />
      <div className={page.grid}>
        <div className={page.span5}>
          <Panel
            title="Profile"
            actions={
              <Badge tone={archived ? "neutral" : "gold"}>{STATUS_LABEL[customer.status]}</Badge>
            }
          >
            <dl className={styles.facts}>
              <dt>Email</dt>
              <dd>{customer.email ?? "—"}</dd>
              <dt>Phone</dt>
              <dd>{customer.phone ?? "—"}</dd>
              <dt>Owner</dt>
              <dd>{customer.owner?.display_name ?? "Unassigned"}</dd>
              <dt>Added</dt>
              <dd>{formatDate(customer.created_at)}</dd>
            </dl>
            {customer.notes && (
              <p className="serif-text" style={{ marginTop: 16 }}>
                {customer.notes}
              </p>
            )}
          </Panel>
        </div>
        <div className={page.span7}>
          <Panel
            title="Contacts"
            actions={
              editable && !archived ? (
                <Button
                  size="sm"
                  icon={<LuPlus aria-hidden="true" />}
                  onClick={() => {
                    setContact(undefined);
                    setDialog("contact");
                  }}
                >
                  Add contact
                </Button>
              ) : undefined
            }
          >
            {contacts.length === 0 ? (
              <EmptyState title="No contacts yet">
                Add the people you deal with at this customer.
              </EmptyState>
            ) : (
              <ul className={styles.timeline}>
                {contacts.map((c) => (
                  <li key={c.id} className={styles.timelineItem}>
                    <span>{c.is_primary && <Badge tone="gold">Primary</Badge>}</span>
                    <div>
                      <strong>{c.name}</strong>
                      {c.job_title && <span className={page.muted}> · {c.job_title}</span>}
                      <div className={page.muted}>
                        {[c.email, c.phone].filter(Boolean).join(" · ") || "No contact details"}
                      </div>
                    </div>
                    {editable && !archived && (
                      <span>
                        <IconButton
                          label={`Edit ${c.name}`}
                          onClick={() => {
                            setContact(c);
                            setDialog("contact");
                          }}
                        >
                          <LuPencil />
                        </IconButton>
                        <IconButton
                          label={`Remove ${c.name}`}
                          onClick={() => void act(() => send("DELETE", `/crm/contacts/${c.id}`))}
                        >
                          <LuTrash2 />
                        </IconButton>
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
        <div className={page.span12}>
          <Panel
            title="Opportunities"
            actions={
              editable && !archived ? (
                <Button
                  size="sm"
                  icon={<LuPlus aria-hidden="true" />}
                  onClick={() => setDialog("opportunity")}
                >
                  New opportunity
                </Button>
              ) : undefined
            }
          >
            {opportunities.length === 0 ? (
              <EmptyState title="No opportunities yet">
                Opportunity values are estimates and are never shown as revenue.
              </EmptyState>
            ) : (
              <div className={page.tableWrap}>
                <table className={page.table}>
                  <thead>
                    <tr>
                      <th scope="col">Opportunity</th>
                      <th scope="col">Division</th>
                      <th scope="col">Estimated value</th>
                      <th scope="col">Expected close</th>
                      <th scope="col">Stage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {opportunities.map((o) => (
                      <tr key={o.id}>
                        <td>
                          {o.title}
                          <div className={styles.ref}>{o.reference}</div>
                        </td>
                        <td>{DIVISION_LABEL[o.division]}</td>
                        <td className={styles.amount}>{formatMoney(o.value_amount, o.currency)}</td>
                        <td>{formatDate(o.expected_close)}</td>
                        <td>
                          <Badge
                            tone={
                              o.stage === "won" ? "success" : o.stage === "lost" ? "danger" : "gold"
                            }
                          >
                            {STAGE_LABEL[o.stage]}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className={page.note}>
              <Link href="/crm/pipeline" className={page.inlineLink}>
                Move opportunities between stages on the pipeline
              </Link>
            </p>
          </Panel>
        </div>
        <div className={page.span12}>
          <Panel
            title="Activity and follow-ups"
            actions={
              editable && !archived ? (
                <div className={page.actionsRow} style={{ marginTop: 0 }}>
                  <Button size="sm" onClick={() => setDialog("follow_up")}>
                    Schedule follow-up
                  </Button>
                  <Button
                    size="sm"
                    icon={<LuPlus aria-hidden="true" />}
                    onClick={() => setDialog("activity")}
                  >
                    Log activity
                  </Button>
                </div>
              ) : undefined
            }
          >
            {activities.length === 0 ? (
              <EmptyState title="No activity yet">
                Meetings, calls, emails, notes and follow-ups appear here.
              </EmptyState>
            ) : (
              <ol className={styles.timeline} aria-label="Customer history">
                {activities.map((a) => {
                  const late = isOverdue(a);
                  return (
                    <li key={a.id} className={styles.timelineItem}>
                      <Badge
                        tone={
                          a.kind === "follow_up"
                            ? a.completed_at
                              ? "success"
                              : late
                                ? "danger"
                                : "gold"
                            : "neutral"
                        }
                      >
                        {ACTIVITY_LABEL[a.kind]}
                      </Badge>
                      <div>
                        <strong>{a.subject}</strong>
                        <div className={late ? styles.overdue : page.muted}>
                          {a.kind === "follow_up"
                            ? `${a.completed_at ? "Done" : late ? "Overdue" : "Due"} ${formatDate(a.completed_at ?? a.due_at)}${a.assigned_to ? ` · ${a.assigned_to.display_name}` : ""}`
                            : `${formatDate(a.occurred_at ?? a.created_at)}${a.created_by ? ` · ${a.created_by.display_name}` : ""}`}
                        </div>
                        {a.body && <p className={styles.timelineBody}>{a.body}</p>}
                      </div>
                      {editable && a.kind === "follow_up" && !a.completed_at ? (
                        <Button
                          size="sm"
                          icon={<LuCheck aria-hidden="true" />}
                          onClick={() =>
                            void act(async () => {
                              await send("POST", `/crm/activities/${a.id}/complete`);
                              play("complete");
                            })
                          }
                        >
                          Mark done
                        </Button>
                      ) : (
                        <span />
                      )}
                    </li>
                  );
                })}
              </ol>
            )}
          </Panel>
        </div>
      </div>

      {dialog === "edit" && (
        <CustomerDialog
          open
          customer={customer}
          onClose={() => setDialog(null)}
          onSaved={() => void reload()}
        />
      )}
      {dialog === "contact" && (
        <ContactDialog
          open
          customerId={customer.id}
          contact={contact}
          onClose={() => setDialog(null)}
          onSaved={() => void reload()}
        />
      )}
      {dialog === "opportunity" && (
        <OpportunityDialog
          open
          customerId={customer.id}
          onClose={() => setDialog(null)}
          onSaved={() => void reload()}
        />
      )}
      {(dialog === "activity" || dialog === "follow_up") && (
        <ActivityDialog
          open
          customerId={customer.id}
          defaultKind={dialog === "follow_up" ? "follow_up" : "note"}
          onClose={() => setDialog(null)}
          onSaved={() => void reload()}
        />
      )}
    </>
  );
}

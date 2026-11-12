"use client";

import { Fragment, useState } from "react";
import { LuPlus, LuTrash2 } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
import { FinanceNav } from "@/components/finance/FinanceNav";
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
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDate } from "@/lib/crm/types";
import {
  DOC_STATUS_LABEL,
  isoToday,
  sumMoney,
  type Account,
  type Journal,
} from "@/lib/finance/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

interface Draft {
  account_id: string;
  debit: string;
  credit: string;
}

export default function JournalsPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const journals = useResource<Journal[]>("/finance/journals?limit=100");
  const accounts = useResource<Account[]>("/finance/accounts");
  const [open, setOpen] = useState(false);
  const [reversing, setReversing] = useState<Journal | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [head, setHead] = useState({ entry_date: isoToday(), description: "" });
  const [lines, setLines] = useState<Draft[]>([
    { account_id: "", debit: "", credit: "" },
    { account_id: "", debit: "", credit: "" },
  ]);
  const debit = sumMoney(lines.map((l) => l.debit || "0"));
  const credit = sumMoney(lines.map((l) => l.credit || "0"));
  const editable = can("finance.records.edit");

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      play("approval");
      setOpen(false);
      setReversing(null);
      await journals.reload();
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Finance"
        title="Journals"
        description="Every posting, automatic or manual. Manual journals and reversals are posted only after the Director approves them."
        actions={
          editable ? (
            <Button
              variant="primary"
              icon={<LuPlus aria-hidden="true" />}
              onClick={() => setOpen(true)}
            >
              Manual journal
            </Button>
          ) : undefined
        }
      />
      <FinanceNav />
      <FormError message={error ?? journals.error} />
      <Panel title="Journal entries">
        {journals.data && journals.data.length === 0 ? (
          <EmptyState title="No journals yet">
            Postings appear here as invoices, receipts, bills and payments are recorded.
          </EmptyState>
        ) : (
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th scope="col">Entry</th>
                  <th scope="col">Account</th>
                  <th scope="col">Debit</th>
                  <th scope="col">Credit</th>
                </tr>
              </thead>
              <tbody>
                {journals.data?.map((j) => (
                  <Fragment key={j.id}>
                    <tr>
                      <td colSpan={4} style={{ background: "rgba(255,255,255,0.02)" }}>
                        <strong>{j.number ?? "Not posted"}</strong> · {formatDate(j.entry_date)} ·{" "}
                        {j.description}{" "}
                        <Badge
                          tone={
                            j.status === "posted"
                              ? "success"
                              : j.status === "reversed"
                                ? "neutral"
                                : j.status === "rejected"
                                  ? "danger"
                                  : "gold"
                          }
                        >
                          {DOC_STATUS_LABEL[j.status] ?? j.status}
                        </Badge>{" "}
                        <span className={styles.ref}>{j.source_type.replace("_", " ")}</span>
                        {editable &&
                          j.status === "posted" &&
                          (j.source_type === "manual" || j.source_type === "reversal") && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setReason("");
                                setReversing(j);
                              }}
                            >
                              Request reversal
                            </Button>
                          )}
                      </td>
                    </tr>
                    {j.lines.map((l) => (
                      <tr key={`${j.id}-${l.line_no}`}>
                        <td className={page.muted}>{l.description ?? ""}</td>
                        <td>
                          {l.account_code} {l.account_name}
                          {l.currency !== "MWK" && (
                            <span className={styles.ref}>
                              {" "}
                              · {l.currency} {l.amount}
                            </span>
                          )}
                        </td>
                        <td className="tabular">{l.debit !== "0.00" ? l.debit : ""}</td>
                        <td className="tabular">{l.credit !== "0.00" ? l.credit : ""}</td>
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Dialog open={open} title="Manual journal" onClose={() => setOpen(false)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const body = {
              ...head,
              lines: lines.map((l) => ({
                account_id: l.account_id,
                ...(l.debit ? { debit: l.debit } : {}),
                ...(l.credit ? { credit: l.credit } : {}),
              })),
            };
            void act(() => send("POST", "/finance/journals", { body }));
          }}
        >
          <div className={styles.formGrid}>
            <TextField
              label="Date"
              type="date"
              required
              value={head.entry_date}
              onChange={(e) => setHead({ ...head, entry_date: e.target.value })}
            />
            <TextField
              label="Narration"
              required
              minLength={3}
              value={head.description}
              onChange={(e) => setHead({ ...head, description: e.target.value })}
            />
          </div>
          {lines.map((l, i) => (
            <div
              key={i}
              className={styles.formGrid}
              style={{ gridTemplateColumns: "2fr 1fr 1fr auto", alignItems: "end" }}
            >
              <SelectField
                label={`Account ${i + 1}`}
                required
                value={l.account_id}
                onChange={(e) =>
                  setLines(
                    lines.map((x, k) => (k === i ? { ...x, account_id: e.target.value } : x)),
                  )
                }
                options={[
                  { value: "", label: "Choose" },
                  ...(accounts.data ?? []).map((a) => ({
                    value: a.id,
                    label: `${a.code} ${a.name}`,
                  })),
                ]}
              />
              <TextField
                label={`Debit ${i + 1}`}
                inputMode="decimal"
                pattern="^\d{1,16}(\.\d{1,2})?$"
                value={l.debit}
                onChange={(e) =>
                  setLines(
                    lines.map((x, k) =>
                      k === i ? { ...x, debit: e.target.value, credit: "" } : x,
                    ),
                  )
                }
              />
              <TextField
                label={`Credit ${i + 1}`}
                inputMode="decimal"
                pattern="^\d{1,16}(\.\d{1,2})?$"
                value={l.credit}
                onChange={(e) =>
                  setLines(
                    lines.map((x, k) =>
                      k === i ? { ...x, credit: e.target.value, debit: "" } : x,
                    ),
                  )
                }
              />
              <IconButton
                label={`Remove line ${i + 1}`}
                disabled={lines.length <= 2}
                onClick={() => setLines(lines.filter((_, k) => k !== i))}
              >
                <LuTrash2 />
              </IconButton>
            </div>
          ))}
          <div className={page.actionsRow} style={{ marginTop: 0 }}>
            <Button
              type="button"
              size="sm"
              onClick={() => setLines([...lines, { account_id: "", debit: "", credit: "" }])}
            >
              Add line
            </Button>
            <span className={debit === credit ? page.muted : styles.overdue} role="status">
              Debits {debit} · Credits {credit} {debit === credit ? "· balanced" : "· not balanced"}
            </span>
          </div>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={debit !== credit || debit === "0.00"}>
              Send for approval
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={reversing !== null} title="Request reversal" onClose={() => setReversing(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (reversing)
              void act(() =>
                send("POST", `/finance/journals/${reversing.id}/reverse`, {
                  body: { entry_date: isoToday(), reason },
                }),
              );
          }}
        >
          <TextField
            label="Reason"
            required
            minLength={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setReversing(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Send for approval
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

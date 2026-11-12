"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { LuLock, LuShieldCheck } from "react-icons/lu";

import styles from "@/components/crm/crm.module.css";
import { ProcurementNav } from "@/components/procurement/ProcurementNav";
import {
  Badge,
  Button,
  Dialog,
  EmptyState,
  FormError,
  PageHeader,
  Panel,
  SelectField,
  Spinner,
  TextField,
} from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { CURRENCIES, formatDate } from "@/lib/crm/types";
import { maskAccount, type SupplierDetail } from "@/lib/procurement/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

export default function SupplierPage() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAuth();
  const { play } = useSound();
  const { data, error, loading, reload } = useResource<SupplierDetail>(
    `/procurement/suppliers/${id}`,
  );
  const [dialog, setDialog] = useState<"verify" | "bank" | null>(null);
  const [verify, setVerify] = useState({ status: "verified", note: "" });
  const [bank, setBank] = useState({
    bank_name: "",
    account_name: "",
    account_number: "",
    branch: "",
    swift: "",
    currency: "MWK",
    reason: "",
  });
  const [actionError, setActionError] = useState<string | null>(null);

  async function act(fn: () => Promise<unknown>) {
    setActionError(null);
    try {
      await fn();
      play("complete");
      setDialog(null);
      await reload();
    } catch (e) {
      setActionError(errorMessage(e));
      play("warning");
    }
  }

  if (loading && !data) return <Spinner label="Loading supplier" />;
  if (!data)
    return (
      <EmptyState title="Not available">{error ?? "This supplier could not be loaded."}</EmptyState>
    );
  const { supplier: s, bank_accounts: accounts, bank_details_visible: visible } = data;

  return (
    <>
      <PageHeader
        eyebrow={s.reference}
        title={s.name}
        description={[s.categories, [s.city, s.country_code].filter(Boolean).join(", ")]
          .filter(Boolean)
          .join(" · ")}
        actions={
          <Badge
            tone={
              s.status === "verified" ? "success" : s.status === "suspended" ? "danger" : "warning"
            }
          >
            {s.status}
          </Badge>
        }
      />
      <ProcurementNav />
      <FormError message={actionError} />
      <div className={page.grid}>
        <div className={page.span5}>
          <Panel
            title="Verification"
            actions={
              can("procurement.records.edit") ? (
                <Button
                  size="sm"
                  icon={<LuShieldCheck aria-hidden="true" />}
                  onClick={() => setDialog("verify")}
                >
                  Update status
                </Button>
              ) : undefined
            }
          >
            <dl className={styles.facts}>
              <dt>Contact</dt>
              <dd>{s.contact_name ?? "—"}</dd>
              <dt>Email</dt>
              <dd>{s.email ?? "—"}</dd>
              <dt>Phone</dt>
              <dd>{s.phone ?? "—"}</dd>
              <dt>Registration no.</dt>
              <dd>{s.registration_number ?? "—"}</dd>
              <dt>Tax no.</dt>
              <dd>{s.tax_number ?? "—"}</dd>
              <dt>Verified</dt>
              <dd>
                {s.verified_at
                  ? `${formatDate(s.verified_at)} by ${s.verified_by?.display_name ?? "—"}`
                  : "Not verified"}
              </dd>
              {s.verification_note && (
                <>
                  <dt>Note</dt>
                  <dd>{s.verification_note}</dd>
                </>
              )}
            </dl>
          </Panel>
        </div>
        <div className={page.span7}>
          <Panel
            title="Bank details"
            actions={
              can("procurement.supplier_bank.request_change") ? (
                <Button
                  size="sm"
                  disabled={s.pending_bank_change}
                  onClick={() => setDialog("bank")}
                >
                  Request bank-detail change
                </Button>
              ) : undefined
            }
          >
            <p className={page.note} style={{ marginTop: 0 }}>
              <LuLock aria-hidden="true" /> Encrypted at rest.{" "}
              {visible
                ? "Viewing full details is recorded in the audit log."
                : "Only the Director can see full account numbers."}{" "}
              A change takes effect only after a different person approves it.
            </p>
            {accounts.length === 0 ? (
              <EmptyState title="No bank details on file">
                Request a change to add the first account.
              </EmptyState>
            ) : (
              <ul className={styles.timeline}>
                {accounts.map((a) => (
                  <li key={a.id} className={styles.timelineItem}>
                    <Badge
                      tone={
                        a.status === "active"
                          ? "success"
                          : a.status === "pending"
                            ? "gold"
                            : "neutral"
                      }
                    >
                      {a.status}
                    </Badge>
                    <div>
                      <strong>
                        {a.bank_name} ·{" "}
                        {visible && a.account_number
                          ? a.account_number
                          : maskAccount(a.account_last4)}{" "}
                        · {a.currency}
                      </strong>
                      {visible && a.account_name && (
                        <div>
                          {a.account_name}
                          {a.branch ? ` · ${a.branch}` : ""}
                          {a.swift ? ` · ${a.swift}` : ""}
                        </div>
                      )}
                      <div className={page.muted}>
                        Requested by {a.requested_by} on {formatDate(a.created_at)} · {a.reason}
                      </div>
                    </div>
                    <span />
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>

      <Dialog
        open={dialog === "verify"}
        title="Supplier verification"
        onClose={() => setDialog(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(() =>
              send("POST", `/procurement/suppliers/${s.id}/verification`, { body: verify }),
            );
          }}
        >
          <SelectField
            label="Status"
            value={verify.status}
            onChange={(e) => setVerify({ ...verify, status: e.target.value })}
            options={["verified", "unverified", "suspended"].map((v) => ({ value: v, label: v }))}
          />
          <TextField
            label="What was checked"
            required
            minLength={3}
            value={verify.note}
            onChange={(e) => setVerify({ ...verify, note: e.target.value })}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog
        open={dialog === "bank"}
        title="Request bank-detail change"
        onClose={() => setDialog(null)}
      >
        <form
          className={styles.dialogForm}
          autoComplete="off"
          onSubmit={(e) => {
            e.preventDefault();
            const body = Object.fromEntries(Object.entries(bank).filter(([, v]) => v !== ""));
            void act(() =>
              send("POST", `/procurement/suppliers/${s.id}/bank-change`, { body }),
            ).then(() =>
              setBank({
                bank_name: "",
                account_name: "",
                account_number: "",
                branch: "",
                swift: "",
                currency: "MWK",
                reason: "",
              }),
            );
          }}
        >
          <p className={page.note} style={{ marginTop: 0 }}>
            Confirm new bank details with the supplier by phone on a number you already hold, never
            one given in the same email.
          </p>
          <div className={styles.formGrid}>
            <TextField
              label="Bank"
              required
              value={bank.bank_name}
              onChange={(e) => setBank({ ...bank, bank_name: e.target.value })}
            />
            <TextField
              label="Account name"
              required
              value={bank.account_name}
              onChange={(e) => setBank({ ...bank, account_name: e.target.value })}
            />
            <TextField
              label="Account number"
              required
              value={bank.account_number}
              onChange={(e) => setBank({ ...bank, account_number: e.target.value })}
            />
            <TextField
              label="Branch"
              value={bank.branch}
              onChange={(e) => setBank({ ...bank, branch: e.target.value })}
            />
            <TextField
              label="SWIFT/BIC"
              value={bank.swift}
              onChange={(e) => setBank({ ...bank, swift: e.target.value.toUpperCase() })}
            />
            <SelectField
              label="Account currency"
              value={bank.currency}
              onChange={(e) => setBank({ ...bank, currency: e.target.value })}
              options={CURRENCIES.map((c) => ({ value: c, label: c }))}
            />
          </div>
          <TextField
            label="Reason and how it was confirmed"
            required
            minLength={5}
            value={bank.reason}
            onChange={(e) => setBank({ ...bank, reason: e.target.value })}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
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

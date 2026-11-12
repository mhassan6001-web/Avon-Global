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
import { formatDate, formatMoney } from "@/lib/crm/types";
import { type Employee, type Leave, type Run } from "@/lib/hr";
import { label } from "@/lib/inventory/types";
import { useSound } from "@/lib/sound/SoundProvider";

import page from "@/app/pages.module.css";

const VIEWS = [
  { value: "people", label: "People" },
  { value: "leave", label: "Leave" },
  { value: "payroll", label: "Payroll" },
] as const;

interface Component {
  id: string;
  code: string;
  name: string;
  kind: string;
  method: string;
  amount: string;
  rate_pct: string;
  bands: Array<{ from_amount: string; to_amount: string | null; rate_pct: string }>;
  source_note: string;
}

export default function HrPage() {
  const { can } = useAuth();
  const { play } = useSound();
  const [view, setView] = useState<(typeof VIEWS)[number]["value"]>("people");
  const employees = useResource<Employee[]>("/hr/employees");
  const leave = useResource<Leave[]>(view === "leave" ? "/hr/leave" : null);
  const runs = useResource<Run[]>(
    view === "payroll" && can("hr.payroll.view") ? "/hr/payroll-runs" : null,
  );
  const components = useResource<Component[]>(
    view === "payroll" && can("hr.payroll.view") ? "/hr/pay-components" : null,
  );
  const [dialog, setDialog] = useState<"employee" | "pay" | "component" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [emp, setEmp] = useState({
    full_name: "",
    job_title: "",
    department_code: "logistics",
    employment_type: "permanent",
    start_date: "",
    leave_days_per_year: "0",
  });
  const [pay, setPay] = useState({
    employee_id: "",
    basic_pay: "",
    effective_from: "",
    reason: "",
  });
  const [comp, setComp] = useState({
    code: "",
    name: "",
    kind: "deduction",
    method: "percent",
    amount: "0",
    rate_pct: "0",
    base: "gross",
    source_note: "",
    bands: "",
  });
  const [period, setPeriod] = useState("");
  const editable = can("hr.records.edit");
  const prepare = can("hr.payroll.prepare");

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      play("complete");
      setDialog(null);
      await Promise.all([employees.reload(), leave.reload(), runs.reload(), components.reload()]);
    } catch (e) {
      setError(errorMessage(e));
      play("warning");
    }
  }

  /** Bands are typed one per line as "from,to,rate" (empty "to" = no upper limit). */
  function parseBands(text: string) {
    return text
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        const [from_amount = "0", to_amount = "", rate_pct = "0"] = l
          .split(",")
          .map((x) => x.trim());
        return { from_amount, to_amount: to_amount || null, rate_pct };
      });
  }

  return (
    <>
      <PageHeader
        eyebrow="HR/Admin"
        title="HR & Payroll"
        description="People records, leave and payroll. Pay rates and deductions are configured here and approved by the Director; none are built in."
        actions={
          <div className={page.actionsRow} style={{ marginTop: 0 }}>
            {editable && (
              <Button
                variant="primary"
                icon={<LuPlus aria-hidden="true" />}
                onClick={() => setDialog("employee")}
              >
                New employee
              </Button>
            )}
            {prepare && <Button onClick={() => setDialog("pay")}>Set basic pay</Button>}
          </div>
        }
      />
      <SegmentedControl label="HR view" value={view} options={VIEWS} onChange={setView} />
      <div style={{ height: 16 }} />
      <FormError message={error ?? employees.error} />

      {view === "people" && (
        <Panel title="Employees">
          {employees.data && employees.data.length === 0 ? (
            <EmptyState title="No employees yet">
              Add real staff records. Nothing is pre-filled.
            </EmptyState>
          ) : (
            <div className={page.tableWrap}>
              <table className={page.table}>
                <thead>
                  <tr>
                    <th scope="col">Employee</th>
                    <th scope="col">Role</th>
                    <th scope="col">Department</th>
                    <th scope="col">Started</th>
                    <th scope="col">Login</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.data?.map((e) => (
                    <tr key={e.id}>
                      <td>
                        <strong>{e.full_name}</strong>
                        <div className={styles.ref}>{e.employee_no}</div>
                      </td>
                      <td>{e.job_title}</td>
                      <td>{label(e.department_code)}</td>
                      <td>{formatDate(e.start_date)}</td>
                      <td>
                        {e.user_id ? (
                          <Badge tone="success">Linked</Badge>
                        ) : (
                          <span className={page.muted}>None</span>
                        )}
                      </td>
                      <td>
                        <Badge tone={e.status === "active" ? "success" : "neutral"}>
                          {label(e.status)}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}

      {view === "leave" && (
        <Panel title="Leave requests">
          {leave.data && leave.data.length === 0 ? (
            <EmptyState title="No leave requests">Requests from staff appear here.</EmptyState>
          ) : (
            <ul className={styles.timeline}>
              {leave.data?.map((l) => (
                <li key={l.id} className={styles.timelineItem}>
                  <Badge
                    tone={
                      l.status === "approved"
                        ? "success"
                        : l.status === "rejected"
                          ? "danger"
                          : "gold"
                    }
                  >
                    {label(l.status)}
                  </Badge>
                  <div>
                    <strong>{l.employee_name}</strong> · {label(l.kind)} ·{" "}
                    {formatDate(l.start_date)} – {formatDate(l.end_date)} · {l.days} days
                    {l.reason && <div className={page.muted}>{l.reason}</div>}
                  </div>
                  {editable && l.status === "pending" ? (
                    <span style={{ display: "flex", gap: 8 }}>
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() =>
                          void act(() =>
                            send("POST", `/hr/leave/${l.id}/decide`, { body: { approve: true } }),
                          )
                        }
                      >
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          void act(() =>
                            send("POST", `/hr/leave/${l.id}/decide`, { body: { approve: false } }),
                          )
                        }
                      >
                        Reject
                      </Button>
                    </span>
                  ) : (
                    <span />
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}

      {view === "payroll" &&
        (can("hr.payroll.view") ? (
          <div className={page.grid}>
            <div className={page.span5}>
              <Panel
                title="Pay components"
                actions={
                  prepare ? (
                    <Button size="sm" onClick={() => setDialog("component")}>
                      Add
                    </Button>
                  ) : undefined
                }
              >
                <p className={page.note} style={{ marginTop: 0 }}>
                  Every rate and band is entered here with its source and must be confirmed by a
                  qualified local accountant.
                </p>
                {components.data && components.data.length === 0 ? (
                  <EmptyState title="No components">
                    Basic pay only until components are added.
                  </EmptyState>
                ) : (
                  <ul className={styles.timeline}>
                    {components.data?.map((c) => (
                      <li key={c.id} className={styles.timelineItem}>
                        <span className={styles.ref}>{c.code}</span>
                        <div>
                          {c.name} · {label(c.kind)} ·{" "}
                          {c.method === "fixed"
                            ? c.amount
                            : c.method === "percent"
                              ? `${Number(c.rate_pct)}%`
                              : `${c.bands.length} bands`}
                          <div className={page.muted}>{c.source_note}</div>
                        </div>
                        <span />
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>
            <div className={page.span7}>
              <Panel title="Payroll runs">
                {prepare && (
                  <form
                    className={styles.formGrid}
                    style={{ alignItems: "end", marginBottom: 16 }}
                    onSubmit={(e) => {
                      e.preventDefault();
                      void act(() => send("POST", "/hr/payroll-runs", { body: { period } }));
                    }}
                  >
                    <TextField
                      label="Period (YYYY-MM)"
                      required
                      pattern="^[0-9]{4}-(0[1-9]|1[0-2])$"
                      value={period}
                      onChange={(e) => setPeriod(e.target.value)}
                    />
                    <Button type="submit">Prepare run</Button>
                  </form>
                )}
                {runs.data && runs.data.length === 0 ? (
                  <EmptyState title="No payroll runs">
                    Prepare a run once basic pay is recorded.
                  </EmptyState>
                ) : (
                  runs.data?.map((r) => (
                    <section key={r.id} className={styles.card} style={{ marginBottom: 12 }}>
                      <header className={styles.columnHead}>
                        <strong>{r.period}</strong>
                        <Badge
                          tone={
                            r.status === "approved"
                              ? "success"
                              : r.status === "awaiting_approval"
                                ? "gold"
                                : "neutral"
                          }
                        >
                          {label(r.status)}
                        </Badge>
                      </header>
                      <span>{`${r.payslips.length} payslips · gross ${formatMoney(r.total_gross, r.currency)} · net ${formatMoney(r.total_net, r.currency)}`}</span>
                      {prepare && r.status === "draft" && (
                        <div className={page.actionsRow} style={{ marginTop: 0 }}>
                          <Button
                            size="sm"
                            onClick={() =>
                              void act(() => send("POST", `/hr/payroll-runs/${r.id}/recalculate`))
                            }
                          >
                            Recalculate
                          </Button>
                          <Button
                            size="sm"
                            variant="primary"
                            onClick={() =>
                              void act(() => send("POST", `/hr/payroll-runs/${r.id}/submit`))
                            }
                          >
                            Send to Director
                          </Button>
                        </div>
                      )}
                      <details>
                        <summary>Payslips</summary>
                        <table className={page.table}>
                          <thead>
                            <tr>
                              <th scope="col">Employee</th>
                              <th scope="col">Gross</th>
                              <th scope="col">Deductions</th>
                              <th scope="col">Net</th>
                            </tr>
                          </thead>
                          <tbody>
                            {r.payslips.map((p) => (
                              <tr key={p.id}>
                                <td>{p.employee_name}</td>
                                <td className="tabular">{p.gross}</td>
                                <td className="tabular">{p.deductions}</td>
                                <td className={styles.amount}>{p.net}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </details>
                    </section>
                  ))
                )}
              </Panel>
            </div>
          </div>
        ) : (
          <EmptyState title="Payroll is restricted">
            Only payroll staff and the Director can see pay.
          </EmptyState>
        ))}

      <Dialog open={dialog === "employee"} title="New employee" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void act(() => send("POST", "/hr/employees", { body: emp }));
          }}
        >
          <div className={styles.formGrid}>
            <TextField
              label="Full name"
              required
              minLength={2}
              value={emp.full_name}
              onChange={(e) => setEmp({ ...emp, full_name: e.target.value })}
            />
            <TextField
              label="Job title"
              required
              minLength={2}
              value={emp.job_title}
              onChange={(e) => setEmp({ ...emp, job_title: e.target.value })}
            />
            <SelectField
              label="Department"
              value={emp.department_code}
              onChange={(e) => setEmp({ ...emp, department_code: e.target.value })}
              options={[
                "executive",
                "business_development",
                "procurement",
                "finance",
                "logistics",
                "hr_admin",
              ].map((d) => ({ value: d, label: label(d) }))}
            />
            <SelectField
              label="Employment type"
              value={emp.employment_type}
              onChange={(e) => setEmp({ ...emp, employment_type: e.target.value })}
              options={["permanent", "fixed_term", "casual", "intern", "consultant"].map((d) => ({
                value: d,
                label: label(d),
              }))}
            />
            <TextField
              label="Start date"
              type="date"
              required
              value={emp.start_date}
              onChange={(e) => setEmp({ ...emp, start_date: e.target.value })}
            />
            <TextField
              label="Annual leave days"
              inputMode="decimal"
              value={emp.leave_days_per_year}
              onChange={(e) => setEmp({ ...emp, leave_days_per_year: e.target.value })}
            />
          </div>
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create employee
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={dialog === "pay"} title="Set basic pay" onClose={() => setDialog(null)}>
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const { employee_id, ...body } = pay;
            void act(() => send("POST", `/hr/employees/${employee_id}/compensation`, { body }));
          }}
        >
          <div className={styles.formGrid}>
            <SelectField
              label="Employee"
              required
              value={pay.employee_id}
              onChange={(e) => setPay({ ...pay, employee_id: e.target.value })}
              options={[
                { value: "", label: "Choose" },
                ...(employees.data ?? []).map((x) => ({
                  value: x.id,
                  label: `${x.employee_no} ${x.full_name}`,
                })),
              ]}
            />
            <TextField
              label="Monthly basic pay (MWK)"
              required
              inputMode="decimal"
              value={pay.basic_pay}
              onChange={(e) => setPay({ ...pay, basic_pay: e.target.value })}
            />
            <TextField
              label="Effective from"
              type="date"
              required
              value={pay.effective_from}
              onChange={(e) => setPay({ ...pay, effective_from: e.target.value })}
            />
            <TextField
              label="Reason"
              required
              minLength={3}
              value={pay.reason}
              onChange={(e) => setPay({ ...pay, reason: e.target.value })}
            />
          </div>
          <p className={page.note}>Pay history is kept: a change is a new entry, never an edit.</p>
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
        open={dialog === "component"}
        title="Add pay component"
        onClose={() => setDialog(null)}
      >
        <form
          className={styles.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            const { bands, ...rest } = comp;
            void act(() =>
              send("POST", "/hr/pay-components", {
                body: { ...rest, bands: comp.method === "bands" ? parseBands(bands) : [] },
              }),
            );
          }}
        >
          <div className={styles.formGrid}>
            <TextField
              label="Code"
              required
              pattern="^[A-Z0-9_\-]{2,20}$"
              value={comp.code}
              onChange={(e) => setComp({ ...comp, code: e.target.value.toUpperCase() })}
            />
            <TextField
              label="Name"
              required
              minLength={2}
              value={comp.name}
              onChange={(e) => setComp({ ...comp, name: e.target.value })}
            />
            <SelectField
              label="Kind"
              value={comp.kind}
              onChange={(e) => setComp({ ...comp, kind: e.target.value })}
              options={["earning", "deduction", "employer"].map((v) => ({
                value: v,
                label: label(v),
              }))}
            />
            <SelectField
              label="Method"
              value={comp.method}
              onChange={(e) => setComp({ ...comp, method: e.target.value })}
              options={["fixed", "percent", "bands"].map((v) => ({ value: v, label: label(v) }))}
            />
            <SelectField
              label="Calculated on"
              value={comp.base}
              onChange={(e) => setComp({ ...comp, base: e.target.value })}
              options={["gross", "taxable", "basic"].map((v) => ({ value: v, label: label(v) }))}
            />
            {comp.method === "fixed" && (
              <TextField
                label="Amount"
                inputMode="decimal"
                value={comp.amount}
                onChange={(e) => setComp({ ...comp, amount: e.target.value })}
              />
            )}
            {comp.method === "percent" && (
              <TextField
                label="Rate %"
                inputMode="decimal"
                value={comp.rate_pct}
                onChange={(e) => setComp({ ...comp, rate_pct: e.target.value })}
              />
            )}
          </div>
          {comp.method === "bands" && (
            <label className={styles.textareaLabel}>
              Bands, one per line: from, to, rate% (leave “to” empty for the top band)
              <textarea
                className={styles.textarea}
                rows={4}
                value={comp.bands}
                onChange={(e) => setComp({ ...comp, bands: e.target.value })}
              />
            </label>
          )}
          <TextField
            label="Source of these figures"
            required
            minLength={3}
            hint="e.g. the official notice and date. Confirm with your accountant."
            value={comp.source_note}
            onChange={(e) => setComp({ ...comp, source_note: e.target.value })}
          />
          <div className={styles.dialogActions}>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Add component
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}

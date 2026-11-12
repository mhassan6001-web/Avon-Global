"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { LuArrowRight, LuBanknote, LuFileCheck2, LuReceipt, LuShieldCheck } from "react-icons/lu";

import {
  AreaChart,
  BarChart,
  ChartCard,
  Donut,
  HBarList,
  KpiCard,
} from "@/components/charts/Charts";
import { JarvisPresence } from "@/components/jarvis/JarvisPresence";
import { DependencyList, RefreshButton } from "@/components/system/PlatformStatus";
import { Badge, PageHeader, Panel } from "@/components/ui";
import { riseIn, staggerContainer } from "@/lib/motion/tokens";
import { useResource } from "@/lib/api/useResource";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDate, OPEN_STAGES, STAGE_LABEL, type CrmSummary } from "@/lib/crm/types";
import { usePreferences } from "@/lib/preferences/PreferencesProvider";
import { STAGES, STAGE_STATE_LABEL, type StageState } from "@/lib/roadmap";

import cc from "./command-centre.module.css";

interface DirectorDashboard {
  functional_currency: string;
  crm: CrmSummary;
  top_customers_open_pipeline: Array<{
    customer_id: string;
    name: string;
    open_value: string;
    open_count: number;
  }>;
  approvals_pending: Array<{
    id: string;
    summary: string;
    subject_type: string;
    requested_by: string;
    created_at: string;
  }>;
  approvals_pending_count: number;
  security_alerts_open: number;
}

const STAGE_TONE: Record<StageState, "success" | "gold" | "signal" | "neutral"> = {
  approved: "success",
  verified: "gold",
  in_progress: "signal",
  awaiting_approval: "gold",
  queued: "neutral",
};

/**
 * Director Command Centre, composed after reference 08. Every figure is
 * ``null`` until it comes from real posted records (Stage 4 onwards): the
 * charts show a designed "No data yet" state, never sample numbers (C5).
 */
export default function CommandCentrePage() {
  const { motionScale } = usePreferences();
  const { can } = useAuth();
  const item = riseIn(motionScale);
  const isDirector = can("director.dashboard.view");
  const director = useResource<DirectorDashboard>(isDirector ? "/director/dashboard" : null);
  const crmOnly = useResource<CrmSummary>(
    !isDirector && can("crm.records.view") ? "/crm/summary" : null,
  );
  const crm = director.data?.crm ?? crmOnly.data ?? null;

  // null → "No data yet" (no records); a real array → counts, which may be zero.
  const pipeline = crm?.has_records
    ? crm.pipeline
        .filter((s) => OPEN_STAGES.includes(s.stage))
        .map((s) => ({ label: STAGE_LABEL[s.stage], value: s.count }))
    : null;
  const openTotal = pipeline?.reduce((sum, p) => sum + p.value, 0) ?? 0;
  const currency = director.data?.functional_currency ?? "MWK";
  const top =
    director.data && crm?.has_records
      ? director.data.top_customers_open_pipeline.map((t) => ({
          label: t.name,
          value: Number(t.open_value),
        }))
      : null;
  const approvals = director.data?.approvals_pending ?? null;

  return (
    <>
      <PageHeader
        eyebrow="Director workspace"
        title="Command Centre"
        description="Figures appear only once they come from real records. Opportunity values are labelled as estimates; nothing is sample data."
      />

      <motion.div
        className={cc.layout}
        variants={staggerContainer(motionScale, 0.06)}
        initial="initial"
        animate="enter"
      >
        <div className={cc.main}>
          <motion.div variants={item} className={cc.kpis}>
            <KpiCard
              icon={<LuBanknote />}
              label="Cash position (MWK)"
              value={null}
              note="From the cashbook (Finance)"
            />
            <KpiCard
              icon={<LuReceipt />}
              label="Invoiced this month"
              value={null}
              note="Revenue invoiced, not cash"
            />
            <KpiCard
              icon={<LuFileCheck2 />}
              label="Collected this month"
              value={null}
              note="Receipts posted"
            />
          </motion.div>

          <div className={cc.centre}>
            <div className={cc.stack}>
              <motion.div variants={item}>
                <ChartCard title="Revenue invoiced" meta="Last 12 months · MWK" empty>
                  <AreaChart data={null} height={190} />
                </ChartCard>
              </motion.div>
              <motion.div variants={item}>
                <ChartCard title="Cash collected" meta="Last 12 months · MWK" empty>
                  <BarChart data={null} height={150} />
                </ChartCard>
              </motion.div>
            </div>
            <div className={cc.stack}>
              <motion.div variants={item}>
                <ChartCard
                  title="Open opportunities"
                  meta="By stage · CRM"
                  empty={pipeline === null || openTotal === 0}
                  emptyLabel={pipeline === null ? "No data yet" : "None open"}
                >
                  <Donut
                    data={pipeline}
                    size={140}
                    centre={pipeline ? <span className="tabular">{openTotal}</span> : undefined}
                  />
                </ChartCard>
              </motion.div>
              <motion.div variants={item}>
                <ChartCard title="Revenue by division" meta="This year · Finance" empty>
                  <Donut data={null} size={120} />
                </ChartCard>
              </motion.div>
            </div>
          </div>

          <motion.div variants={item}>
            <section className={cc.tableCard} aria-label="Approvals waiting for you">
              <header className={cc.tableHead}>
                <h3>Approvals waiting for you</h3>
                <Badge tone={approvals?.length ? "gold" : "neutral"}>
                  {director.data ? `${director.data.approvals_pending_count} pending` : "Approvals"}
                </Badge>
              </header>
              <table className={cc.table}>
                <thead>
                  <tr>
                    <th scope="col">Request</th>
                    <th scope="col">Module</th>
                    <th scope="col">Requested by</th>
                    <th scope="col" className={cc.num}>
                      Amount
                    </th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {approvals && approvals.length > 0 ? (
                    approvals.map((a) => (
                      <tr key={a.id}>
                        <td>
                          <Link href="/approvals" className={cc.jarvisLink}>
                            {a.summary}
                          </Link>
                        </td>
                        <td>{a.subject_type.replace(/_/g, " ")}</td>
                        <td>{a.requested_by}</td>
                        <td className={cc.num}>—</td>
                        <td>
                          <Badge tone="gold">{`Pending since ${formatDate(a.created_at)}`}</Badge>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className={cc.emptyRow}>
                        {approvals
                          ? "Nothing is waiting for your approval."
                          : "No approval requests yet. Bids, purchases and payments will need approval here."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </section>
          </motion.div>
        </div>

        <aside className={cc.side} aria-label="Pipeline and JARVIS">
          <motion.div variants={item}>
            <section className={cc.jarvisCard} aria-label="JARVIS">
              <JarvisPresence state="idle" size={180} label={false} />
              <div>
                <p className="hud-label">JARVIS</p>
                <p className={cc.jarvisText}>
                  Your daily briefing will appear here once JARVIS is connected (Stage 11).
                </p>
                <Link href="/modules/jarvis" className={cc.jarvisLink}>
                  Preview JARVIS <LuArrowRight aria-hidden="true" />
                </Link>
              </div>
            </section>
          </motion.div>
          {crm?.has_records && (
            <motion.div variants={item}>
              <section className={cc.tableCard} aria-label="Follow-ups">
                <header className={cc.tableHead}>
                  <h3>Follow-ups</h3>
                  <Link href="/crm/follow-ups" className={cc.jarvisLink}>
                    Open <LuArrowRight aria-hidden="true" />
                  </Link>
                </header>
                <p className={cc.followUps}>
                  <span className={crm.follow_ups_overdue ? cc.alert : undefined}>
                    <strong className="tabular">{crm.follow_ups_overdue}</strong> overdue
                  </span>
                  <span>
                    <strong className="tabular">{crm.follow_ups_due_7_days}</strong> due in 7 days
                  </span>
                </p>
              </section>
            </motion.div>
          )}
          <motion.div variants={item}>
            <ChartCard title="Debtors" meta="Outstanding · Finance" empty>
              <AreaChart data={null} height={90} />
            </ChartCard>
          </motion.div>
          <motion.div variants={item}>
            <ChartCard
              title="Top customers"
              meta={`Open pipeline · ${currency} estimates`}
              empty={top === null || top.length === 0}
              emptyLabel={top === null ? "No data yet" : "No open values"}
            >
              <HBarList data={top} currency={currency} />
            </ChartCard>
          </motion.div>
          <motion.div variants={item}>
            <ChartCard title="Tender pipeline" meta="Open tenders by stage" empty>
              <Donut data={null} size={120} />
            </ChartCard>
          </motion.div>
        </aside>
      </motion.div>

      <div className={cc.lower}>
        <Panel eyebrow="Live" title="Platform status" actions={<RefreshButton />}>
          <DependencyList />
        </Panel>
        <Panel eyebrow="Build" title="Delivery stages">
          <ol className={cc.stageList}>
            {STAGES.map((stage) => (
              <li key={stage.number} className={cc.stageRow}>
                <span className={`${cc.stageNumber} tabular`}>
                  {String(stage.number).padStart(2, "0")}
                </span>
                <span className={cc.stageTitle}>{stage.title}</span>
                <Badge tone={STAGE_TONE[stage.state]}>{STAGE_STATE_LABEL[stage.state]}</Badge>
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      <div className={cc.securityStrip}>
        <LuShieldCheck aria-hidden="true" />
        <p>
          Sign-in, department roles, two-factor verification and the audit log are active. Business
          modules arrive stage by stage.
        </p>
      </div>
    </>
  );
}

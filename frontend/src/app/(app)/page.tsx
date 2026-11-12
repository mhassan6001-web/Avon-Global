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
import { usePreferences } from "@/lib/preferences/PreferencesProvider";
import { STAGES, STAGE_STATE_LABEL, type StageState } from "@/lib/roadmap";

import cc from "./command-centre.module.css";

const STAGE_TONE: Record<StageState, "success" | "gold" | "signal" | "neutral"> = {
  approved: "success",
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
  const item = riseIn(motionScale);

  return (
    <>
      <PageHeader
        eyebrow="Director workspace"
        title="Command Centre"
        description="Figures appear here only once they come from real, posted records. Nothing is estimated or sample data."
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
            <motion.div variants={item}>
              <ChartCard title="Revenue by division" meta="This year" empty>
                <Donut data={null} />
              </ChartCard>
            </motion.div>
          </div>

          <motion.div variants={item}>
            <section className={cc.tableCard} aria-label="Approvals waiting for you">
              <header className={cc.tableHead}>
                <h3>Approvals waiting for you</h3>
                <Badge tone="neutral">Approvals</Badge>
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
                  <tr>
                    <td colSpan={5} className={cc.emptyRow}>
                      No approval requests yet. They appear here as Procurement and Finance are
                      built.
                    </td>
                  </tr>
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
          <motion.div variants={item}>
            <ChartCard title="Debtors" meta="Outstanding · MWK" empty>
              <AreaChart data={null} height={90} />
            </ChartCard>
          </motion.div>
          <motion.div variants={item}>
            <ChartCard title="Top customers" meta="Invoiced this year" empty>
              <HBarList data={null} />
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

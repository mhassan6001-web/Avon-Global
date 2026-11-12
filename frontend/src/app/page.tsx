"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { LuArrowRight, LuChartLine, LuShieldCheck } from "react-icons/lu";

import { DependencyList, RefreshButton } from "@/components/system/PlatformStatus";
import { Badge, EmptyState, PageHeader, Panel } from "@/components/ui";
import { riseIn, staggerContainer } from "@/lib/motion/tokens";
import { BUSINESS_MODULES } from "@/lib/navigation";
import { usePreferences } from "@/lib/preferences/PreferencesProvider";
import { STAGES, STAGE_STATE_LABEL, TOTAL_STAGES } from "@/lib/roadmap";

import styles from "./pages.module.css";

export default function CommandCentrePage() {
  const { motionScale } = usePreferences();

  return (
    <>
      <PageHeader
        eyebrow="Director workspace"
        title="Command Centre"
        description="The platform foundation is in place. Business figures will appear here only once they come from real, posted records."
      />

      <motion.div
        className={styles.grid}
        variants={staggerContainer(motionScale, 0.07)}
        initial="initial"
        animate="enter"
      >
        <motion.div variants={riseIn(motionScale)} className={styles.span7}>
          <Panel eyebrow="Live" title="Platform status" actions={<RefreshButton />}>
            <DependencyList />
          </Panel>
        </motion.div>

        <motion.div variants={riseIn(motionScale)} className={styles.span5}>
          <Panel eyebrow="Build" title="Delivery stages">
            <ol className={styles.stageList}>
              {STAGES.map((stage) => (
                <li key={stage.number} className={styles.stageRow} data-state={stage.state}>
                  <span className={`${styles.stageNumber} tabular`}>
                    {String(stage.number).padStart(2, "0")}
                  </span>
                  <span className={styles.stageTitle}>{stage.title}</span>
                  <Badge
                    tone={
                      stage.state === "approved"
                        ? "success"
                        : stage.state === "awaiting_approval"
                          ? "gold"
                          : "neutral"
                    }
                  >
                    {STAGE_STATE_LABEL[stage.state]}
                  </Badge>
                </li>
              ))}
            </ol>
            <p className={styles.note}>
              Stages {STAGES.length + 1}–{TOTAL_STAGES} are listed in ROADMAP.md. Each stage stops
              for your approval.
            </p>
          </Panel>
        </motion.div>

        <motion.div variants={riseIn(motionScale)} className={styles.span5}>
          <Panel eyebrow="Executive" title="Business overview">
            <EmptyState icon={<LuChartLine />} title="No business figures yet">
              Revenue, cash position, approvals and alerts will appear once Finance, CRM and
              Approvals are built. Nothing here is estimated or sample data.
            </EmptyState>
          </Panel>
        </motion.div>

        <motion.div variants={riseIn(motionScale)} className={styles.span7}>
          <Panel
            eyebrow="Structure"
            title="Business modules"
            actions={<Badge tone="neutral">{BUSINESS_MODULES.length} planned</Badge>}
          >
            <ul className={styles.moduleGrid}>
              {BUSINESS_MODULES.map((entry) => {
                const Icon = entry.icon;
                return (
                  <li key={entry.slug}>
                    <Link href={entry.href} className={styles.moduleTile}>
                      <Icon className={styles.moduleIcon} aria-hidden="true" />
                      <span className={styles.moduleName}>{entry.label}</span>
                      <LuArrowRight className={styles.moduleArrow} aria-hidden="true" />
                    </Link>
                  </li>
                );
              })}
            </ul>
          </Panel>
        </motion.div>

        <motion.div variants={riseIn(motionScale)} className={styles.span12}>
          <div className={styles.securityStrip}>
            <LuShieldCheck aria-hidden="true" />
            <p>
              Sign-in, roles and audit logging are the next stage. Until then, no business data is
              stored or exposed by this system.
            </p>
          </div>
        </motion.div>
      </motion.div>
    </>
  );
}

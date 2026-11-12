"use client";

import { motion } from "framer-motion";
import { LuCircleAlert, LuRefreshCw } from "react-icons/lu";

import { Badge, Button, EmptyState, Skeleton, StatusDot, type Tone } from "@/components/ui";
import { CHECK_LABELS, type DependencyCheck } from "@/lib/api/health";
import { riseIn, staggerContainer } from "@/lib/motion/tokens";
import { usePreferences } from "@/lib/preferences/PreferencesProvider";
import { useSystemStatus } from "@/lib/system/SystemStatusProvider";

import styles from "./system.module.css";

function checkTone(check: DependencyCheck): Tone {
  if (check.status === "ok") return "success";
  return check.required ? "danger" : "warning";
}

export function formatTime(date: Date | null): string {
  if (!date) return "—";
  return date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function RefreshButton() {
  const { refresh, loading } = useSystemStatus();
  return (
    <Button size="sm" icon={<LuRefreshCw aria-hidden="true" />} onClick={refresh} loading={loading}>
      Refresh
    </Button>
  );
}

/** Live list of dependency checks from GET /api/v1/health/ready. */
export function DependencyList({ detailed = false }: { detailed?: boolean }) {
  const { report, error, loading, lastChecked } = useSystemStatus();
  const { motionScale } = usePreferences();

  if (error) {
    return (
      <EmptyState icon={<LuCircleAlert />} title="The API could not be reached">
        {error.message} The web app is running, but it cannot confirm the state of the backend,
        database or Redis. ({error.code}
        {error.requestId ? `, request ${error.requestId}` : ""})
      </EmptyState>
    );
  }

  if (!report) {
    return (
      <ul className={styles.checkList} aria-busy={loading}>
        {[0, 1, 2].map((key) => (
          <li key={key} className={styles.checkRow}>
            <Skeleton width={8} height={8} />
            <Skeleton width="45%" height={13} />
            <Skeleton width={56} height={13} />
          </li>
        ))}
      </ul>
    );
  }

  return (
    <>
      <motion.ul
        className={styles.checkList}
        variants={staggerContainer(motionScale)}
        initial="initial"
        animate="enter"
      >
        {report.checks.map((check) => (
          <motion.li key={check.name} className={styles.checkRow} variants={riseIn(motionScale)}>
            <StatusDot tone={checkTone(check)} live={check.status === "ok"} />
            <div className={styles.checkName}>
              <span>{CHECK_LABELS[check.name] ?? check.name}</span>
              {detailed && (
                <span className={styles.checkMeta}>
                  {check.required ? "Required" : "Optional"}
                  {check.detail ? ` · ${check.detail}` : ""}
                </span>
              )}
            </div>
            <span className={`${styles.checkLatency} tabular`}>
              {check.latency_ms !== null ? `${check.latency_ms.toFixed(1)} ms` : ""}
            </span>
            <Badge tone={checkTone(check)}>{check.status === "ok" ? "OK" : "Failing"}</Badge>
          </motion.li>
        ))}
      </motion.ul>
      <p className={styles.footnote}>
        Last checked {formatTime(lastChecked)} · refreshes every 30 seconds
      </p>
    </>
  );
}

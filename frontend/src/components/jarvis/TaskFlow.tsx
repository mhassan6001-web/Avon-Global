"use client";

import { motion } from "framer-motion";
import { LuCheck, LuCircleSlash, LuLoader } from "react-icons/lu";

import { usePreferences } from "@/lib/preferences/PreferencesProvider";

import styles from "./jarvis.module.css";

/** The fixed control chain every JARVIS action passes through (AI_ARCHITECTURE §6). */
export const ACTION_STEPS = [
  { key: "authentication", label: "Authentication" },
  { key: "permission", label: "Permission" },
  { key: "validation", label: "Validation" },
  { key: "rules", label: "Business rules" },
  { key: "approval", label: "Approval" },
  { key: "execution", label: "Execution" },
  { key: "audit", label: "Audit" },
] as const;
export type ActionStep = (typeof ACTION_STEPS)[number]["key"];
export type StepStatus = "pending" | "active" | "done" | "blocked" | "skipped";

/**
 * Task-execution connection visual. Each node's status must come from real
 * backend progress events (Stage 11). This component only renders what it is given.
 */
export function TaskFlow({
  statuses,
  target,
}: {
  statuses: Partial<Record<ActionStep, StepStatus>>;
  target?: string;
}) {
  const { motionScale } = usePreferences();
  return (
    <div className={styles.flow}>
      <ol className={styles.flowList} aria-label="Action control steps">
        {ACTION_STEPS.map((step, i) => {
          const status = statuses[step.key] ?? "pending";
          return (
            <li key={step.key} className={styles.flowStep} data-status={status}>
              {i > 0 && (
                <span className={styles.flowLine} aria-hidden="true">
                  <motion.span
                    className={styles.flowLineFill}
                    initial={false}
                    animate={{ scaleX: status === "pending" ? 0 : 1 }}
                    transition={{ duration: 0.45 * motionScale }}
                  />
                </span>
              )}
              <span className={styles.flowNode} aria-hidden="true">
                {status === "done" && <LuCheck />}
                {status === "active" && <LuLoader className={styles.spin} />}
                {status === "blocked" && <LuCircleSlash />}
              </span>
              <span className={`${styles.flowLabel} hud-label`}>
                {step.label}
                <span className="visually-hidden">: {status}</span>
              </span>
            </li>
          );
        })}
      </ol>
      {target && <p className={styles.flowTarget}>Target: {target}</p>}
    </div>
  );
}

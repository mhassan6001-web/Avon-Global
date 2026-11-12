import { getJson, type RequestOptions } from "./client";

/** Mirrors backend `app/schemas/health.py`. */
export type CheckStatus = "ok" | "failing" | "skipped";

export interface DependencyCheck {
  name: string;
  status: CheckStatus;
  required: boolean;
  latency_ms: number | null;
  detail: string | null;
}

export interface ReadinessReport {
  status: CheckStatus;
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  checks: DependencyCheck[];
}

export function fetchReadiness(options: RequestOptions = {}) {
  // 503 is a valid readiness answer ("not ready"), not a transport failure.
  return getJson<ReadinessReport>("/health/ready", { ...options, acceptStatuses: [503] });
}

export type PlatformState = "operational" | "degraded" | "unreachable" | "checking";

/** Summarise a readiness result into one state for the header indicator. */
export function platformState(report: ReadinessReport | null, error: unknown): PlatformState {
  if (error) return "unreachable";
  if (!report) return "checking";
  if (report.status !== "ok") return "degraded";
  return report.checks.some((c) => c.status !== "ok") ? "degraded" : "operational";
}

export const CHECK_LABELS: Record<string, string> = {
  database: "Database",
  migrations: "Schema migrations",
  redis: "Cache & job queue (Redis)",
};

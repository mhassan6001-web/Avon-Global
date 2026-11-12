"use client";

import type { ReactNode } from "react";

import { DependencyList, RefreshButton, formatTime } from "@/components/system/PlatformStatus";
import { Badge, PageHeader, Panel, Skeleton } from "@/components/ui";
import { useSystemStatus } from "@/lib/system/SystemStatusProvider";

import styles from "../pages.module.css";

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className={styles.field}>
      <dt>{label}</dt>
      <dd>{value ?? <Skeleton width={90} height={13} />}</dd>
    </div>
  );
}

export default function SystemStatusPage() {
  const { report, error, state, lastChecked, requestId } = useSystemStatus();
  const overall =
    state === "operational" ? (
      <Badge tone="success">Ready</Badge>
    ) : state === "degraded" ? (
      <Badge tone="warning">Not ready</Badge>
    ) : state === "unreachable" ? (
      <Badge tone="danger">Unreachable</Badge>
    ) : null;

  return (
    <>
      <PageHeader
        eyebrow="Infrastructure"
        title="System status"
        description="Live readiness of the API and its dependencies, read from GET /api/v1/health/ready."
        actions={<RefreshButton />}
      />
      <div className={styles.grid}>
        <div className={styles.span8}>
          <Panel eyebrow="Readiness" title="Dependencies">
            <DependencyList detailed />
          </Panel>
        </div>
        <div className={styles.span4}>
          <Panel eyebrow="Service" title="API">
            <dl className={styles.fieldList}>
              <Field
                label="Overall"
                value={overall ?? (error ? <Badge tone="danger">Unreachable</Badge> : null)}
              />
              <Field label="Service" value={error ? "—" : report?.service} />
              <Field
                label="Version"
                value={error ? "—" : report && <span className="tabular">{report.version}</span>}
              />
              <Field label="Environment" value={error ? "—" : report?.environment} />
              <Field
                label="Last checked"
                value={<span className="tabular">{formatTime(lastChecked)}</span>}
              />
              <Field
                label="Request ID"
                value={<code className={styles.code}>{requestId ?? error?.requestId ?? "—"}</code>}
              />
            </dl>
          </Panel>
        </div>
      </div>
    </>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LuMenu } from "react-icons/lu";

import { Badge, IconButton, StatusDot, type Tone } from "@/components/ui";
import type { PlatformState } from "@/lib/api/health";
import { titleForPath } from "@/lib/navigation";
import { useSystemStatus } from "@/lib/system/SystemStatusProvider";

import { NotificationArea } from "./NotificationArea";
import styles from "./shell.module.css";
import { UserMenu } from "./UserMenu";

const STATE_DISPLAY: Record<PlatformState, { label: string; tone: Tone }> = {
  operational: { label: "All systems operational", tone: "success" },
  degraded: { label: "Degraded", tone: "warning" },
  unreachable: { label: "API unreachable", tone: "danger" },
  checking: { label: "Checking…", tone: "neutral" },
};

export function Header({ onOpenNavigation }: { onOpenNavigation: () => void }) {
  const pathname = usePathname();
  const { state, report } = useSystemStatus();
  const display = STATE_DISPLAY[state];

  return (
    <header className={styles.header}>
      <div className={styles.headerLeft}>
        <span className={styles.mobileOnly}>
          <IconButton label="Open navigation" onClick={onOpenNavigation}>
            <LuMenu />
          </IconButton>
        </span>
        <p className={styles.headerTitle}>{titleForPath(pathname)}</p>
      </div>

      <div className={styles.headerRight}>
        {report && report.environment !== "production" && (
          <span className={styles.desktopOnly}>
            <Badge tone="gold">{report.environment}</Badge>
          </span>
        )}
        <Link
          href="/system"
          className={styles.statusPill}
          aria-label={`Platform status: ${display.label}. Open system status.`}
        >
          <StatusDot tone={display.tone} live={state === "operational"} />
          <span className={styles.statusLabel}>{display.label}</span>
        </Link>
        <span className={styles.headerDivider} aria-hidden="true" />
        <NotificationArea />
        <UserMenu />
      </div>
    </header>
  );
}

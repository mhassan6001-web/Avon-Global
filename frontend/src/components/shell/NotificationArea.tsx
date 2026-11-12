"use client";

import Link from "next/link";
import { LuBell } from "react-icons/lu";

import { Button, EmptyState } from "@/components/ui";
import { useRealtime } from "@/lib/realtime/RealtimeProvider";

import { Popover } from "./Popover";
import styles from "./shell.module.css";

/** Live notices from the event stream (messages, tasks, report requests). */
export function NotificationArea() {
  const { notices, clearNotices, connected } = useRealtime();
  return (
    <Popover
      label="Notifications"
      trigger={({ ref, ...props }) => (
        <button
          ref={ref}
          type="button"
          className={styles.headerIconButton}
          aria-label={notices.length ? `Notifications, ${notices.length} new` : "Notifications"}
          {...props}
        >
          <LuBell aria-hidden="true" />
          {notices.length > 0 && <span className={styles.badgeDot} aria-hidden="true" />}
        </button>
      )}
    >
      <div className={styles.popoverHeader}>
        <p className={styles.popoverTitle}>Notifications</p>
        {notices.length > 0 && (
          <Button size="sm" variant="ghost" onClick={clearNotices}>
            Clear
          </Button>
        )}
      </div>
      <div className={styles.popoverBody}>
        {notices.length === 0 ? (
          <EmptyState icon={<LuBell />} title="Nothing new">
            {connected
              ? "You are up to date."
              : "Live updates are reconnecting; pages still refresh when opened."}
          </EmptyState>
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
            {notices.map((n) => (
              <li key={n.id}>
                <Link href={n.href}>{n.text}</Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Popover>
  );
}

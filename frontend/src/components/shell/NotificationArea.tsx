"use client";

import { LuBell } from "react-icons/lu";

import { EmptyState } from "@/components/ui";

import { Popover } from "./Popover";
import styles from "./shell.module.css";

/**
 * Notification area. The notification service (events, approvals, alerts)
 * depends on authentication and is not built yet, so this shows an honest
 * empty state rather than sample notifications.
 */
export function NotificationArea() {
  return (
    <Popover
      label="Notifications"
      trigger={({ ref, ...props }) => (
        <button
          ref={ref}
          type="button"
          className={styles.headerIconButton}
          aria-label="Notifications"
          {...props}
        >
          <LuBell aria-hidden="true" />
        </button>
      )}
    >
      <div className={styles.popoverHeader}>
        <p className={styles.popoverTitle}>Notifications</p>
      </div>
      <div className={styles.popoverBody}>
        <EmptyState icon={<LuBell />} title="No notifications">
          Approvals, alerts and messages will appear here once sign-in and the notification service
          are live.
        </EmptyState>
      </div>
    </Popover>
  );
}

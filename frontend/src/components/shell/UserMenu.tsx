"use client";

import Link from "next/link";
import { LuLogOut, LuSettings2, LuShieldCheck, LuUserRound } from "react-icons/lu";

import { useAuth } from "@/lib/auth/AuthProvider";
import { useSound } from "@/lib/sound/SoundProvider";

import { Popover } from "./Popover";
import styles from "./shell.module.css";

function initials(name: string): string {
  return name
    .replace(/^DEV-ONLY\s+/i, "")
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** Profile area: the signed-in user, their role and account actions. */
export function UserMenu() {
  const { me, signOut } = useAuth();
  const { play } = useSound();
  const { user } = me;
  return (
    <Popover
      label="Account"
      width={290}
      trigger={({ ref, ...props }) => (
        <button
          ref={ref}
          type="button"
          className={styles.profileButton}
          aria-label="Account"
          {...props}
        >
          <span className={styles.avatar} aria-hidden="true">
            {initials(user.display_name) || <LuUserRound />}
          </span>
          <span className={styles.profileText}>
            <span className={styles.profileName}>{user.display_name}</span>
            <span className={styles.profileRole}>{user.role_name}</span>
          </span>
        </button>
      )}
    >
      <div className={styles.popoverHeader}>
        <p className={styles.popoverTitle}>{user.display_name}</p>
        <p className={styles.profileRole}>
          {user.email} · {user.department}
        </p>
      </div>
      <ul className={styles.menuList}>
        <li>
          <Link href="/account" className={styles.menuItem}>
            <LuShieldCheck aria-hidden="true" /> Account & security
          </Link>
        </li>
        <li>
          <Link href="/settings" className={styles.menuItem}>
            <LuSettings2 aria-hidden="true" /> Display preferences
          </Link>
        </li>
        <li>
          <button
            type="button"
            className={styles.menuItem}
            onClick={() => {
              play("shutdown");
              void signOut();
            }}
          >
            <LuLogOut aria-hidden="true" /> Sign out
          </button>
        </li>
      </ul>
    </Popover>
  );
}

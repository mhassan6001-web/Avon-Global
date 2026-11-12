"use client";

import Link from "next/link";
import { LuLogIn, LuSettings2, LuUserRound } from "react-icons/lu";

import { Popover } from "./Popover";
import styles from "./shell.module.css";

/**
 * User profile area. Authentication arrives in Stage 2; until then the shell
 * states plainly that nobody is signed in instead of showing a placeholder user.
 */
export function UserMenu() {
  return (
    <Popover
      label="Account"
      width={280}
      trigger={({ ref, ...props }) => (
        <button
          ref={ref}
          type="button"
          className={styles.profileButton}
          aria-label="Account"
          {...props}
        >
          <span className={styles.avatar} aria-hidden="true">
            <LuUserRound />
          </span>
          <span className={styles.profileText}>
            <span className={styles.profileName}>Not signed in</span>
            <span className={styles.profileRole}>Sign-in arrives in Stage 2</span>
          </span>
        </button>
      )}
    >
      <div className={styles.popoverHeader}>
        <p className={styles.popoverTitle}>Account</p>
      </div>
      <ul className={styles.menuList}>
        <li>
          <Link href="/settings" className={styles.menuItem}>
            <LuSettings2 aria-hidden="true" /> Display preferences
          </Link>
        </li>
        <li>
          <span className={styles.menuItem} aria-disabled="true">
            <LuLogIn aria-hidden="true" /> Sign in
            <span className={styles.menuHint}>Stage 2</span>
          </span>
        </li>
      </ul>
    </Popover>
  );
}

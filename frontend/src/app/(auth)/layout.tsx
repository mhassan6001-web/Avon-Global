import type { ReactNode } from "react";

import { Emblem } from "@/components/brand/Emblem";
import { Wordmark } from "@/components/brand/Wordmark";

import styles from "./auth.module.css";

/** Sign-in area: ref 03 atmosphere (navy-black, gold architectural lines). */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className={styles.scene}>
      <div className={styles.lines} aria-hidden="true" />
      <div className={styles.card}>
        <div className={styles.brand}>
          <Emblem size={52} decorative />
          <Wordmark size="md" />
        </div>
        {children}
      </div>
      <p className={styles.footer}>Authorised AVEN GLOBAL staff only. Activity is audited.</p>
    </main>
  );
}

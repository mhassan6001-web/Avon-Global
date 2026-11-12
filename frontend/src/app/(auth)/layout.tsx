import type { ReactNode } from "react";

import { Logo } from "@/components/brand/Logo";

import styles from "./auth.module.css";

/** Sign-in area: ref 03 atmosphere (navy-black, gold architectural lines). */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className={styles.scene}>
      <div className={styles.lines} aria-hidden="true" />
      <div className={styles.card}>
        <div className={styles.brand}>
          <Logo variant="lockup" height={150} priority />
        </div>
        {children}
      </div>
      <p className={styles.footer}>Authorised AVEN GLOBAL staff only. Activity is audited.</p>
    </main>
  );
}

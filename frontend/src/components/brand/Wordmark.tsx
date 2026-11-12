import styles from "./brand.module.css";

export function Wordmark({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  return (
    <span className={`${styles.wordmark} ${styles[size]}`} aria-label="AVEN GLOBAL">
      <span className={styles.primary} aria-hidden="true">
        AVEN
      </span>
      <span className={styles.secondary} aria-hidden="true">
        GLOBAL
      </span>
    </span>
  );
}

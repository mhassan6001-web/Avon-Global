import { Skeleton } from "@/components/ui";

import styles from "./pages.module.css";

/** Route-level loading state, shaped like a page so content does not jump. */
export default function Loading() {
  return (
    <div aria-busy="true" aria-live="polite">
      <span className="visually-hidden">Loading page</span>
      <Skeleton width={120} height={12} />
      <div style={{ height: 12 }} />
      <Skeleton width="min(420px, 80%)" height={30} />
      <div style={{ height: 40 }} />
      <div className={styles.grid}>
        {[0, 1, 2, 3].map((key) => (
          <div key={key} className={styles.skeletonPanel}>
            <Skeleton width="40%" height={14} />
            <Skeleton width="90%" height={12} />
            <Skeleton width="75%" height={12} />
            <Skeleton width="60%" height={12} />
          </div>
        ))}
      </div>
    </div>
  );
}

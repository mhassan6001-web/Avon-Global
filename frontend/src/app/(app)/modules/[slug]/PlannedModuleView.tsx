"use client";

import Link from "next/link";

import { Badge, EmptyState, PageHeader, Panel } from "@/components/ui";
import { findModule } from "@/lib/navigation";

import styles from "@/app/pages.module.css";

/**
 * Information view for a module that has not been built. It describes the
 * planned scope and says plainly that nothing here works yet.
 * (Client component because module icons are rendered here.)
 */
export function PlannedModuleView({ slug }: { slug: string }) {
  const entry = findModule(slug);
  if (!entry) return null;
  const Icon = entry.icon;

  return (
    <>
      <PageHeader
        eyebrow="Business module"
        title={entry.label}
        description={entry.summary}
        actions={<Badge tone="gold">Planned</Badge>}
      />
      <div className={styles.grid}>
        <div className={styles.span7}>
          <Panel title="Planned scope">
            <ul className={styles.scopeList}>
              {entry.scope.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Panel>
        </div>
        <div className={styles.span5}>
          <Panel title="Status">
            <EmptyState icon={<Icon />} title="Not built yet">
              This module has no screens, data or actions yet. It will be designed, approved and
              tested in its own stage before it appears here.
            </EmptyState>
            <p className={styles.note}>
              <Link href="/" className={styles.inlineLink}>
                Back to the Command Centre
              </Link>
            </p>
          </Panel>
        </div>
      </div>
    </>
  );
}

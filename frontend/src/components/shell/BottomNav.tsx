"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LuLayoutGrid } from "react-icons/lu";

import { SETTINGS_NAV, WORKSPACE_NAV, isActive } from "@/lib/navigation";

import styles from "./shell.module.css";

/** Phone-width bottom navigation. Modules open in the navigation drawer. */
export function BottomNav({ onOpenNavigation }: { onOpenNavigation: () => void }) {
  const pathname = usePathname();
  const items = [...WORKSPACE_NAV, ...SETTINGS_NAV];
  return (
    <nav className={styles.bottomNav} aria-label="Quick navigation">
      {items.map((item) => {
        const Icon = item.icon;
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={styles.bottomItem}
            data-active={active || undefined}
            aria-current={active ? "page" : undefined}
          >
            <Icon aria-hidden="true" />
            <span>{item.label.split(" ")[0]}</span>
          </Link>
        );
      })}
      <button type="button" className={styles.bottomItem} onClick={onOpenNavigation}>
        <LuLayoutGrid aria-hidden="true" />
        <span>Modules</span>
      </button>
    </nav>
  );
}

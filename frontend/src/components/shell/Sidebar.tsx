"use client";

import { AnimatePresence, LayoutGroup, motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LuPanelLeftClose, LuPanelLeftOpen, LuX } from "react-icons/lu";

import { Emblem } from "@/components/brand/Emblem";
import { Wordmark } from "@/components/brand/Wordmark";
import { IconButton } from "@/components/ui";
import { usePreferences } from "@/lib/preferences/PreferencesProvider";
import {
  BUSINESS_MODULES,
  SETTINGS_NAV,
  WORKSPACE_NAV,
  isActive,
  type NavItem,
} from "@/lib/navigation";

import styles from "./shell.module.css";

function NavLink({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const pathname = usePathname();
  const active = isActive(pathname, item.href);
  const Icon = item.icon;
  const planned = item.status === "planned";
  return (
    <li>
      <Link
        href={item.href}
        className={styles.navLink}
        data-active={active || undefined}
        data-planned={planned || undefined}
        aria-current={active ? "page" : undefined}
        title={collapsed ? `${item.label}${planned ? " (planned)" : ""}` : undefined}
      >
        {active && (
          <motion.span
            layoutId="sidebar-active"
            className={styles.navActive}
            transition={{ type: "spring", stiffness: 420, damping: 38 }}
          />
        )}
        <Icon className={styles.navIcon} aria-hidden="true" />
        <span className={styles.navLabel}>{item.label}</span>
        {planned && <span className={styles.navTag}>Planned</span>}
      </Link>
    </li>
  );
}

function NavSection({
  title,
  items,
  collapsed,
}: {
  title: string;
  items: NavItem[];
  collapsed: boolean;
}) {
  return (
    <div className={styles.navSection}>
      <p className={styles.navSectionTitle}>{title}</p>
      <ul className={styles.navList}>
        {items.map((item) => (
          <NavLink key={item.href} item={item} collapsed={collapsed} />
        ))}
      </ul>
    </div>
  );
}

function SidebarContents({
  collapsed,
  onToggleCollapsed,
  onClose,
}: {
  collapsed: boolean;
  onToggleCollapsed?: () => void;
  onClose?: () => void;
}) {
  return (
    <>
      <div className={styles.brand}>
        <Link href="/" className={styles.brandLink} aria-label="AVEN GLOBAL — Command Centre">
          <Emblem size={34} decorative />
          <span className={styles.brandWordmark}>
            <Wordmark size="sm" />
          </span>
        </Link>
        {onClose && (
          <IconButton label="Close navigation" onClick={onClose}>
            <LuX />
          </IconButton>
        )}
      </div>

      <nav className={styles.nav} aria-label="Main">
        <NavSection title="Workspace" items={WORKSPACE_NAV} collapsed={collapsed} />
        <NavSection title="Business modules" items={BUSINESS_MODULES} collapsed={collapsed} />
        <NavSection title="Settings" items={SETTINGS_NAV} collapsed={collapsed} />
      </nav>

      <div className={styles.sidebarFooter}>
        <p className={styles.buildTag}>
          <span className={styles.buildDot} aria-hidden="true" />
          <span className={styles.navLabel}>Stage 1 · Core infrastructure</span>
        </p>
        {onToggleCollapsed && (
          <IconButton
            label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={onToggleCollapsed}
            aria-expanded={!collapsed}
          >
            {collapsed ? <LuPanelLeftOpen /> : <LuPanelLeftClose />}
          </IconButton>
        )}
      </div>
    </>
  );
}

export function Sidebar({
  collapsed,
  onToggleCollapsed,
  drawerOpen,
  onCloseDrawer,
}: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  drawerOpen: boolean;
  onCloseDrawer: () => void;
}) {
  const { motionScale } = usePreferences();
  return (
    <>
      <aside className={styles.sidebar} data-collapsed={collapsed || undefined}>
        <SidebarContents collapsed={collapsed} onToggleCollapsed={onToggleCollapsed} />
      </aside>

      <AnimatePresence>
        {drawerOpen && (
          <>
            <motion.div
              key="scrim"
              className={styles.scrim}
              onClick={onCloseDrawer}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 * motionScale }}
            />
            <motion.aside
              key="drawer"
              className={styles.drawer}
              role="dialog"
              aria-modal="true"
              aria-label="Navigation"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ duration: 0.32 * motionScale, ease: [0.16, 1, 0.3, 1] }}
            >
              <LayoutGroup id="drawer">
                <SidebarContents collapsed={false} onClose={onCloseDrawer} />
              </LayoutGroup>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

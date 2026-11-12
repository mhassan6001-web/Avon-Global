"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { SystemStatusProvider } from "@/lib/system/SystemStatusProvider";

import { BottomNav } from "./BottomNav";
import { Header } from "./Header";
import styles from "./shell.module.css";
import { Sidebar } from "./Sidebar";

const COLLAPSE_KEY = "aven.sidebar.collapsed";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem(COLLAPSE_KEY) === "1");
    } catch {
      // storage unavailable
    }
  }, []);

  // Close the mobile drawer on navigation.
  useEffect(() => setDrawerOpen(false), [pathname]);

  // Escape closes the drawer; lock background scroll while it is open.
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setDrawerOpen(false);
    window.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [drawerOpen]);

  const toggleCollapsed = () => {
    setCollapsed((value) => {
      try {
        window.localStorage.setItem(COLLAPSE_KEY, value ? "0" : "1");
      } catch {
        // storage unavailable
      }
      return !value;
    });
  };

  return (
    <SystemStatusProvider>
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <div className={styles.shell} data-collapsed={collapsed || undefined}>
        <Sidebar
          collapsed={collapsed}
          onToggleCollapsed={toggleCollapsed}
          drawerOpen={drawerOpen}
          onCloseDrawer={() => setDrawerOpen(false)}
        />
        <div className={styles.workspace}>
          <Header onOpenNavigation={() => setDrawerOpen(true)} />
          <main id="main-content" className={styles.main} tabIndex={-1}>
            <div className={styles.content}>{children}</div>
          </main>
        </div>
        <BottomNav onOpenNavigation={() => setDrawerOpen(true)} />
      </div>
    </SystemStatusProvider>
  );
}

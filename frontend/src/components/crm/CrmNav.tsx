"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./crm.module.css";

const LINKS = [
  { href: "/crm", label: "Customers" },
  { href: "/crm/pipeline", label: "Pipeline" },
  { href: "/crm/follow-ups", label: "Follow-ups" },
];

export function CrmNav() {
  const pathname = usePathname();
  return (
    <nav className={styles.tabs} aria-label="CRM sections">
      {LINKS.map((link) => {
        const active =
          link.href === "/crm"
            ? pathname === "/crm" || pathname.startsWith("/crm/customers")
            : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={styles.tab}
            aria-current={active ? "page" : undefined}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

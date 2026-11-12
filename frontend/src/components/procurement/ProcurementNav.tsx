"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "@/components/crm/crm.module.css";

const LINKS = [
  {
    href: "/procurement",
    label: "Purchase requests",
    match: (p: string) => p === "/procurement" || p.startsWith("/procurement/requests"),
  },
  {
    href: "/procurement/suppliers",
    label: "Suppliers",
    match: (p: string) => p.startsWith("/procurement/suppliers"),
  },
  {
    href: "/procurement/orders",
    label: "Purchase orders",
    match: (p: string) => p.startsWith("/procurement/orders"),
  },
  {
    href: "/procurement/landed-cost",
    label: "Landed cost",
    match: (p: string) => p.startsWith("/procurement/landed-cost"),
  },
];

export function ProcurementNav() {
  const pathname = usePathname();
  return (
    <nav className={styles.tabs} aria-label="Procurement sections">
      {LINKS.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={styles.tab}
          aria-current={link.match(pathname) ? "page" : undefined}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}

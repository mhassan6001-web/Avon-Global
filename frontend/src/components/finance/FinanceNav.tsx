"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "@/components/crm/crm.module.css";

const LINKS = [
  { href: "/finance", label: "Overview" },
  { href: "/finance/invoices", label: "Sales & receipts" },
  { href: "/finance/bills", label: "Bills & payments" },
  { href: "/finance/journals", label: "Journals" },
  { href: "/finance/reports", label: "Reports" },
  { href: "/finance/settings", label: "Setup" },
];

export function FinanceNav() {
  const pathname = usePathname();
  return (
    <nav className={styles.tabs} aria-label="Finance sections">
      {LINKS.map((link) => {
        const active =
          link.href === "/finance" ? pathname === "/finance" : pathname.startsWith(link.href);
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

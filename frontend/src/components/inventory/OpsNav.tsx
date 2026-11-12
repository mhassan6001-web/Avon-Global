"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "@/components/crm/crm.module.css";

const INVENTORY = [
  { href: "/inventory", label: "Stock" },
  { href: "/inventory/receiving", label: "Goods received" },
];
const LOGISTICS = [
  { href: "/logistics", label: "Shipments" },
  { href: "/logistics/deliveries", label: "Deliveries" },
];

export function OpsNav({ section }: { section: "inventory" | "logistics" }) {
  const pathname = usePathname();
  const links = section === "inventory" ? INVENTORY : LOGISTICS;
  return (
    <nav className={styles.tabs} aria-label={`${section} sections`}>
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={styles.tab}
          aria-current={pathname === link.href ? "page" : undefined}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}

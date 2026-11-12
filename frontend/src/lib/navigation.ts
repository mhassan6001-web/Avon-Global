/**
 * Navigation and module registry.
 *
 * Business modules are listed so the Director can see the planned structure.
 * A module is `available` only once it is built and tested; until then it is
 * `planned` and routes to an information page, so nothing pretends to work.
 */

import type { IconType } from "react-icons";
import {
  LuBadgeCheck,
  LuBot,
  LuBoxes,
  LuBriefcase,
  LuBuilding2,
  LuFileText,
  LuGavel,
  LuLandmark,
  LuLayoutDashboard,
  LuMessagesSquare,
  LuServer,
  LuSettings2,
  LuShieldCheck,
  LuShoppingCart,
  LuTruck,
  LuUserRound,
  LuUsers,
  LuUsersRound,
} from "react-icons/lu";

export type ModuleStatus = "available" | "planned";

export interface NavItem {
  label: string;
  href: string;
  icon: IconType;
  status: ModuleStatus;
  /** UI visibility only; the API enforces access independently. */
  permission?: string;
}

export interface BusinessModule extends NavItem {
  slug: string;
  summary: string;
  scope: string[];
}

export const WORKSPACE_NAV: NavItem[] = [
  { label: "Command Centre", href: "/", icon: LuLayoutDashboard, status: "available" },
  { label: "Approvals", href: "/approvals", icon: LuBadgeCheck, status: "available" },
  { label: "System Status", href: "/system", icon: LuServer, status: "available" },
];

export const SETTINGS_NAV: NavItem[] = [
  { label: "My account", href: "/account", icon: LuUserRound, status: "available" },
  { label: "Preferences", href: "/settings", icon: LuSettings2, status: "available" },
];

export const ADMIN_NAV: NavItem[] = [
  {
    label: "Users & access",
    href: "/admin/users",
    icon: LuUsersRound,
    status: "available",
    permission: "admin.users.manage",
  },
  {
    label: "Security & audit",
    href: "/admin/security",
    icon: LuShieldCheck,
    status: "available",
    permission: "admin.audit.view",
  },
  {
    label: "Organisation",
    href: "/admin/organisation",
    icon: LuBuilding2,
    status: "available",
    permission: "org.profile.edit",
  },
];

function planned(
  slug: string,
  label: string,
  icon: IconType,
  summary: string,
  scope: string[],
): BusinessModule {
  return { slug, label, icon, summary, scope, href: `/modules/${slug}`, status: "planned" };
}

function available(
  slug: string,
  label: string,
  icon: IconType,
  summary: string,
  scope: string[],
  href: string,
  permission: string,
): BusinessModule {
  return { slug, label, icon, summary, scope, href, status: "available", permission };
}

export const BUSINESS_MODULES: BusinessModule[] = [
  available(
    "crm",
    "CRM & Sales",
    LuBriefcase,
    "Customers, contacts, opportunities and follow-ups.",
    [
      "Customer profiles and contacts",
      "Opportunities, meetings and follow-ups",
      "Customer history and quotations",
    ],
    "/crm",
    "crm.records.view",
  ),
  available(
    "tenders",
    "Tenders",
    LuGavel,
    "Tender register, deadlines, eligibility and bid approvals.",
    [
      "RFQ, RFP and EOI register with deadlines",
      "Eligibility and submission-document checklists",
      "Bid approvals and award tracking",
    ],
    "/tenders",
    "tenders.records.view",
  ),
  available(
    "procurement",
    "Procurement",
    LuShoppingCart,
    "Suppliers, quotations, purchase requests and orders.",
    [
      "Supplier register and verification",
      "Supplier quotation comparison",
      "Purchase requests, approvals and orders",
      "Landed-cost calculations",
    ],
    "/procurement",
    "procurement.records.view",
  ),
  available(
    "finance",
    "Finance",
    LuLandmark,
    "Double-entry accounting, invoicing, payments and reporting.",
    [
      "Chart of accounts and balanced journals",
      "Invoices, bills, receipts, payments and expenses",
      "Bank reconciliation, debtors and creditors",
      "Multi-currency: MWK, USD, ZAR, ZMW",
    ],
    "/finance",
    "finance.records.view",
  ),
  available(
    "inventory",
    "Inventory",
    LuBoxes,
    "Catalogue, warehouses, stock movements and valuation.",
    [
      "Products, SKUs and warehouses",
      "Goods received, dispatches and adjustments",
      "Reorder alerts and stock valuation",
    ],
    "/inventory",
    "inventory.records.view",
  ),
  available(
    "logistics",
    "Logistics",
    LuTruck,
    "Shipments, freight, customs and proof of delivery.",
    [
      "Shipment and freight records",
      "Customs documentation",
      "Delivery schedules, notes and proof of delivery",
    ],
    "/logistics",
    "logistics.records.view",
  ),
  planned("hr", "HR & Payroll", LuUsers, "Employees, contracts, leave, payroll and performance.", [
    "Employee records and contracts",
    "Leave and attendance",
    "Payroll and commission (restricted access)",
    "Performance reviews and agreed KPIs",
  ]),
  planned(
    "communications",
    "Communications",
    LuMessagesSquare,
    "Staff messaging, announcements and tasks.",
    [
      "One-to-one and department messaging",
      "Announcements with acknowledgements",
      "Tasks, deadlines, work plans and reports",
    ],
  ),
  planned(
    "documents",
    "Documents",
    LuFileText,
    "Branded PDF, Excel and Word documents from validated records.",
    [
      "Quotations, invoices, receipts and statements",
      "Purchase orders, delivery notes and contracts",
      "Tender packs and financial reports",
    ],
  ),
  planned(
    "jarvis",
    "JARVIS",
    LuBot,
    "Executive AI assistant with voice, under permission controls.",
    [
      "Briefings, analysis and document preparation",
      "Voice conversation (push-to-talk)",
      "Actions only through permission-checked, audited tools",
    ],
  ),
];

export function findModule(slug: string): BusinessModule | undefined {
  return BUSINESS_MODULES.find((entry) => entry.slug === slug);
}

/** Modules not built yet; each has an information page at /modules/<slug>. */
export function plannedModules(): BusinessModule[] {
  return BUSINESS_MODULES.filter((entry) => entry.status === "planned");
}

/** Title for the header, derived from the current path. */
export function titleForPath(pathname: string): string {
  const all: NavItem[] = [...WORKSPACE_NAV, ...SETTINGS_NAV, ...ADMIN_NAV, ...BUSINESS_MODULES];
  const exact = all.find((item) => item.href === pathname);
  if (exact) return exact.label;
  const prefix = all
    .filter((item) => item.href !== "/" && pathname.startsWith(`${item.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0];
  return prefix?.label ?? "AVEN GLOBAL";
}

export function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

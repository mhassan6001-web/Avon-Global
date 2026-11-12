import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = { title: "Finance" };

export default function FinanceLayout({ children }: { children: ReactNode }) {
  return children;
}

import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = { title: "Approvals" };

export default function ApprovalsLayout({ children }: { children: ReactNode }) {
  return children;
}

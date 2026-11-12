import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = { title: "CRM & Sales" };

export default function CrmLayout({ children }: { children: ReactNode }) {
  return children;
}

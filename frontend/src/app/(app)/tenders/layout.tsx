import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = { title: "Tenders" };

export default function TendersLayout({ children }: { children: ReactNode }) {
  return children;
}

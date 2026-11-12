import Link from "next/link";

import { EmptyState, PageHeader } from "@/components/ui";

export default function NotFound() {
  return (
    <>
      <PageHeader eyebrow="404" title="Page not found" />
      <EmptyState
        title="This address does not exist in AVEN GLOBAL"
        action={
          <Link href="/" style={{ color: "var(--gold-300)", fontWeight: 600 }}>
            Return to the Command Centre →
          </Link>
        }
      >
        Check the link, or use the navigation to find what you need.
      </EmptyState>
    </>
  );
}

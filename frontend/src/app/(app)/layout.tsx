import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/AppShell";
import { AuthProvider } from "@/lib/auth/AuthProvider";
import { StepUpProvider } from "@/lib/auth/StepUpProvider";

/** Authenticated application area: requires a fully signed-in session. */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <StepUpProvider>
        <AppShell>{children}</AppShell>
      </StepUpProvider>
    </AuthProvider>
  );
}

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/AppShell";
import { StartupScreen } from "@/components/startup/StartupScreen";
import { PRE_PAINT_SCRIPT } from "@/lib/preferences/preferences";
import { PreferencesProvider } from "@/lib/preferences/PreferencesProvider";

// Fonts are self-hosted from npm (OFL licence): no request to Google at build or run time.
import "@fontsource-variable/inter";
import "@fontsource/sora/500.css";
import "@fontsource/sora/600.css";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "AVEN GLOBAL", template: "%s · AVEN GLOBAL" },
  description: "AVEN GLOBAL business operating system",
  applicationName: "AVEN GLOBAL",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: "#070d1f",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en-GB" suppressHydrationWarning>
      <head>
        {/* Applies motion/contrast preferences before first paint. Static, no user input. */}
        <script dangerouslySetInnerHTML={{ __html: PRE_PAINT_SCRIPT }} />
      </head>
      <body>
        <PreferencesProvider>
          <StartupScreen />
          <AppShell>{children}</AppShell>
        </PreferencesProvider>
      </body>
    </html>
  );
}

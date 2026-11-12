import type { Metadata, Viewport } from "next";
import { Inter, Sora } from "next/font/google";
import type { ReactNode } from "react";

import { AppShell } from "@/components/shell/AppShell";
import { StartupScreen } from "@/components/startup/StartupScreen";
import { PRE_PAINT_SCRIPT } from "@/lib/preferences/preferences";
import { PreferencesProvider } from "@/lib/preferences/PreferencesProvider";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  display: "swap",
  weight: ["500", "600"],
});

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
    <html lang="en-GB" className={`${inter.variable} ${sora.variable}`} suppressHydrationWarning>
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

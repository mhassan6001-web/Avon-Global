import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { StartupScreen } from "@/components/startup/StartupScreen";
import { PRE_PAINT_SCRIPT } from "@/lib/preferences/preferences";
import { RegisterServiceWorker } from "@/lib/pwa/RegisterServiceWorker";
import { PreferencesProvider } from "@/lib/preferences/PreferencesProvider";
import { SoundProvider } from "@/lib/sound/SoundProvider";

// Fonts are self-hosted from npm (OFL licence): no request to Google at build or run time.
import "@fontsource-variable/inter";
import "@fontsource/sora/500.css";
import "@fontsource/sora/600.css";
import "@fontsource/rajdhani/500.css";
import "@fontsource/rajdhani/600.css";
import "@fontsource/cormorant-garamond/500.css";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "AVEN GLOBAL", template: "%s · AVEN GLOBAL" },
  description: "AVEN GLOBAL business operating system",
  applicationName: "AVEN GLOBAL",
  robots: { index: false, follow: false },
  icons: {
    icon: [
      { url: "/brand/icon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/brand/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: { url: "/brand/icon-180.png", sizes: "180x180" },
  },
};

export const viewport: Viewport = {
  themeColor: "#08090c",
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
          <SoundProvider>
            <StartupScreen />
            <RegisterServiceWorker />
            {children}
          </SoundProvider>
        </PreferencesProvider>
      </body>
    </html>
  );
}

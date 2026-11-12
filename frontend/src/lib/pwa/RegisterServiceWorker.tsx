"use client";

import { useEffect } from "react";

/** Registers the shell-only service worker in production builds (not in dev). */
export function RegisterServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      /* installability is optional; the app works without it */
    });
  }, []);
  return null;
}

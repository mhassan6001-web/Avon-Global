import type { MetadataRoute } from "next";

/** Installable app (PWA). One central backend; no data is stored offline. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AVEN GLOBAL",
    short_name: "AVEN GLOBAL",
    description: "AVEN GLOBAL business operating system",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "any",
    background_color: "#01060e",
    theme_color: "#08090c",
    icons: [
      { src: "/brand/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/brand/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/brand/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}

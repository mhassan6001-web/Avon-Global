/* eslint-disable @next/next/no-img-element -- static brand artwork, served as-is */
import styles from "./brand.module.css";

/**
 * The Director's AVEN GLOBAL logo artwork (design-references / public/brand).
 * The artwork sits on a near-black field; `lighten` blending drops that field
 * into the dark interface so only the mark shows. Not a registered trademark.
 */
export function Logo({
  variant = "lockup",
  height,
  priority = false,
  decorative = false,
}: {
  variant?: "lockup" | "emblem" | "wordmark" | "full";
  height: number;
  priority?: boolean;
  decorative?: boolean;
}) {
  const src = {
    lockup: { url: "/brand/aven-global-lockup.jpg", ratio: 1280 / 788 },
    emblem: { url: "/brand/aven-global-emblem.jpg", ratio: 1030 / 435 },
    wordmark: { url: "/brand/aven-global-wordmark.jpg", ratio: 1270 / 265 },
    full: { url: "/brand/aven-global-logo.jpg", ratio: 1536 / 1024 },
  }[variant];
  return (
    <img
      src={src.url}
      alt={decorative ? "" : "AVEN GLOBAL"}
      aria-hidden={decorative || undefined}
      width={Math.round(height * src.ratio)}
      height={height}
      className={styles.logo}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
      draggable={false}
    />
  );
}

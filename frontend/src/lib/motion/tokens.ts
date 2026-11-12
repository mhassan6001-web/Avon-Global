/**
 * Motion tokens. Every animation in the app derives from these so motion
 * stays consistent and can be scaled down by the user's preference.
 */

import type { Variants } from "framer-motion";

type CubicBezier = [number, number, number, number];

export const EASE_OUT: CubicBezier = [0.16, 1, 0.3, 1];
export const EASE_IN_OUT: CubicBezier = [0.65, 0, 0.35, 1];

export const DURATION = {
  fast: 0.14,
  base: 0.22,
  slow: 0.42,
  page: 0.32,
} as const;

export function pageVariants(scale: number): Variants {
  const distance = scale >= 1 ? 10 : 0;
  return {
    initial: { opacity: 0, y: distance },
    enter: { opacity: 1, y: 0, transition: { duration: DURATION.page * scale, ease: EASE_OUT } },
  };
}

export function staggerContainer(scale: number, stagger = 0.05): Variants {
  return {
    initial: {},
    enter: { transition: { staggerChildren: stagger * scale, delayChildren: 0.04 * scale } },
  };
}

export function riseIn(scale: number): Variants {
  return {
    initial: { opacity: 0, y: scale >= 1 ? 8 : 0 },
    enter: { opacity: 1, y: 0, transition: { duration: DURATION.slow * scale, ease: EASE_OUT } },
  };
}

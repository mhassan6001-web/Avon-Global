"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { pageVariants } from "@/lib/motion/tokens";
import { usePreferences } from "@/lib/preferences/PreferencesProvider";

/** Route transition: a short fade-and-rise on every navigation. */
export default function Template({ children }: { children: ReactNode }) {
  const { motionScale } = usePreferences();
  return (
    <motion.div variants={pageVariants(motionScale)} initial="initial" animate="enter">
      {children}
    </motion.div>
  );
}

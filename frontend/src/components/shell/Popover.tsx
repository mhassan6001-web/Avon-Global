"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useId, useRef, useState, type ReactNode, type Ref } from "react";

import { usePreferences } from "@/lib/preferences/PreferencesProvider";

import styles from "./shell.module.css";

/**
 * Header popover (notifications, profile). Closes on Escape, outside click and
 * focus leaving; returns focus to the trigger.
 */
export function Popover({
  trigger,
  label,
  children,
  width = 340,
}: {
  trigger: (props: {
    "aria-expanded": boolean;
    "aria-controls": string;
    "aria-haspopup": "dialog";
    onClick: () => void;
    ref: Ref<HTMLButtonElement>;
  }) => ReactNode;
  label: string;
  children: ReactNode;
  width?: number;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const { motionScale } = usePreferences();

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    const onPointer = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!panelRef.current?.contains(target) && !triggerRef.current?.contains(target))
        setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointer);
    panelRef.current?.focus();
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  return (
    <div className={styles.popoverAnchor}>
      {trigger({
        "aria-expanded": open,
        "aria-controls": id,
        "aria-haspopup": "dialog",
        onClick: () => setOpen((value) => !value),
        ref: triggerRef,
      })}
      <AnimatePresence>
        {open && (
          <motion.div
            ref={panelRef}
            id={id}
            role="dialog"
            aria-label={label}
            tabIndex={-1}
            className={styles.popover}
            style={{ width }}
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.18 * motionScale, ease: [0.16, 1, 0.3, 1] }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

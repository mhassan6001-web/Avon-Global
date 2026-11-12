"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { STARTUP_SEEN_KEY, type EffectiveMotion } from "@/lib/preferences/preferences";
import { useSound } from "@/lib/sound/SoundProvider";
import { usePreferences } from "@/lib/preferences/PreferencesProvider";
import { EASE_OUT } from "@/lib/motion/tokens";

import styles from "./startup.module.css";

/** Total on-screen time at full motion, in seconds. Kept short by design. */
const FULL_SEQUENCE_S = 2.3;
const REDUCED_SEQUENCE_S = 0.9;

/**
 * Restrained startup sequence, shown once per browser session.
 *
 * - Renders server-side so there is no flash of the app before it appears;
 *   the pre-paint script sets `data-startup="skip"` when it should not show.
 * - Skippable with the button, Escape, Enter, Space or a click.
 * - Reduced motion: a short fade. Motion off: never shown.
 * - It overlays the app; the app loads underneath and is never blocked.
 */
export const REPLAY_STARTUP_EVENT = "aven:replay-startup";

export function StartupScreen() {
  const { effectiveMotion } = usePreferences();
  const { play } = useSound();
  const [visible, setVisible] = useState(true);
  // The level actually used for this run. Read from the attribute the pre-paint
  // script set, because stored preferences reach React state one tick later.
  const [level, setLevel] = useState<EffectiveMotion>("full");
  const [replayToken, setReplayToken] = useState(0);

  const finish = useCallback(() => {
    try {
      window.sessionStorage.setItem(STARTUP_SEEN_KEY, "1");
    } catch {
      // ignore unavailable storage
    }
    document.documentElement.dataset.startup = "skip";
    setVisible(false);
  }, []);

  useEffect(() => {
    const onReplay = () => setReplayToken((token) => token + 1);
    window.addEventListener(REPLAY_STARTUP_EVENT, onReplay);
    return () => window.removeEventListener(REPLAY_STARTUP_EVENT, onReplay);
  }, []);

  // Decide whether to play: on first mount, and whenever a replay is requested.
  useEffect(() => {
    const root = document.documentElement;
    const attr = root.dataset.motion;
    const current: EffectiveMotion =
      replayToken > 0 || !attr ? effectiveMotion : (attr as EffectiveMotion);
    const alreadySeen = root.dataset.startup === "skip" && replayToken === 0;
    if (alreadySeen || current === "off") {
      setVisible(false);
      return;
    }
    delete root.dataset.startup;
    setLevel(current);
    setVisible(true);
    // Audio is only possible after a gesture, so the chime plays on replay (or later visits once unlocked).
    play("startup");
    const total = current === "full" ? FULL_SEQUENCE_S : REDUCED_SEQUENCE_S;
    const timer = window.setTimeout(finish, total * 1000);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once per (re)play request
  }, [replayToken]);

  useEffect(() => {
    if (!visible) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" || event.key === "Enter" || event.key === " ") finish();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, finish]);

  const full = level === "full";
  const s = full ? 1 : 0.4;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="startup"
          className={styles.overlay}
          data-startup-overlay
          role="presentation"
          onClick={finish}
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.45 * s, ease: EASE_OUT } }}
        >
          <div className={styles.grid} aria-hidden="true" />
          <div className={styles.glow} aria-hidden="true" />

          <div className={styles.center}>
            <p className="visually-hidden" role="status">
              Starting AVEN GLOBAL
            </p>

            <motion.div
              className={styles.logo}
              initial={{ opacity: 0, scale: full ? 0.92 : 1, filter: full ? "blur(6px)" : "none" }}
              animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
              transition={{ duration: 0.9 * s, ease: EASE_OUT }}
            >
              <Logo variant="lockup" height={300} priority decorative />
            </motion.div>

            <motion.span
              className={styles.hairline}
              aria-hidden="true"
              initial={{ scaleX: 0, opacity: 0 }}
              animate={{ scaleX: 1, opacity: 1 }}
              transition={{ duration: 0.8 * s, delay: 1.15 * s, ease: EASE_OUT }}
            />

            <motion.p
              className={styles.caption}
              aria-hidden="true"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 * s, delay: 1.35 * s }}
            >
              Business Operating System
            </motion.p>
          </div>

          <button
            type="button"
            className={styles.skip}
            onClick={(event) => {
              event.stopPropagation();
              finish();
            }}
          >
            Skip
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

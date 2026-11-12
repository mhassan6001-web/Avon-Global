"use client";

import { MotionConfig } from "framer-motion";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  DEFAULT_PREFERENCES,
  STORAGE_KEY,
  motionScale,
  parsePreferences,
  resolveMotion,
  type DisplayPreferences,
  type EffectiveMotion,
} from "./preferences";

interface PreferencesContextValue {
  preferences: DisplayPreferences;
  effectiveMotion: EffectiveMotion;
  /** Multiplier for animation durations: 1 (full), 0.4 (reduced), 0 (off). */
  motionScale: number;
  update: (patch: Partial<DisplayPreferences>) => void;
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

function readStored(): DisplayPreferences {
  try {
    return parsePreferences(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

function useSystemReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<DisplayPreferences>(DEFAULT_PREFERENCES);
  const systemReduced = useSystemReducedMotion();

  useEffect(() => setPreferences(readStored()), []);

  const effectiveMotion = resolveMotion(preferences.motion, systemReduced);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.motion = effectiveMotion;
    root.dataset.contrast = preferences.contrast;
  }, [effectiveMotion, preferences.contrast]);

  const update = useCallback((patch: Partial<DisplayPreferences>) => {
    setPreferences((current) => {
      const next = { ...current, ...patch };
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // Storage can be unavailable (private mode, policy). The choice still applies this session.
      }
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ preferences, effectiveMotion, motionScale: motionScale(effectiveMotion), update }),
    [preferences, effectiveMotion, update],
  );

  return (
    <PreferencesContext.Provider value={value}>
      <MotionConfig
        reducedMotion={effectiveMotion === "full" ? "never" : "always"}
        transition={effectiveMotion === "off" ? { duration: 0 } : undefined}
      >
        {children}
      </MotionConfig>
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): PreferencesContextValue {
  const context = useContext(PreferencesContext);
  if (!context) throw new Error("usePreferences must be used inside <PreferencesProvider>");
  return context;
}

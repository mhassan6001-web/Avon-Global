/**
 * Display preferences (motion intensity, contrast).
 *
 * Pure functions only — shared by the React provider, the pre-paint script
 * and unit tests. Preferences are stored per device until account-level
 * settings arrive with authentication.
 */

export const MOTION_PREFERENCES = ["system", "full", "reduced", "off"] as const;
export type MotionPreference = (typeof MOTION_PREFERENCES)[number];
export type EffectiveMotion = Exclude<MotionPreference, "system">;

export const CONTRAST_PREFERENCES = ["standard", "high"] as const;
export type ContrastPreference = (typeof CONTRAST_PREFERENCES)[number];

export interface DisplayPreferences {
  motion: MotionPreference;
  contrast: ContrastPreference;
}

export const DEFAULT_PREFERENCES: DisplayPreferences = { motion: "system", contrast: "standard" };

export const STORAGE_KEY = "aven.preferences.v1";
export const STARTUP_SEEN_KEY = "aven.startup.seen";

function isOneOf<T extends string>(values: readonly T[], value: unknown): value is T {
  return typeof value === "string" && (values as readonly string[]).includes(value);
}

/** Parse stored JSON defensively; any invalid field falls back to its default. */
export function parsePreferences(raw: string | null | undefined): DisplayPreferences {
  if (!raw) return { ...DEFAULT_PREFERENCES };
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
  const record = (data && typeof data === "object" ? data : {}) as Record<string, unknown>;
  return {
    motion: isOneOf(MOTION_PREFERENCES, record.motion) ? record.motion : DEFAULT_PREFERENCES.motion,
    contrast: isOneOf(CONTRAST_PREFERENCES, record.contrast)
      ? record.contrast
      : DEFAULT_PREFERENCES.contrast,
  };
}

/** Resolve the user's choice against the operating-system reduced-motion setting. */
export function resolveMotion(
  preference: MotionPreference,
  systemPrefersReduced: boolean,
): EffectiveMotion {
  if (preference === "system") return systemPrefersReduced ? "reduced" : "full";
  return preference;
}

/** Durations (seconds) used by Framer Motion for each motion level. */
export function motionScale(effective: EffectiveMotion): number {
  switch (effective) {
    case "full":
      return 1;
    case "reduced":
      return 0.4;
    case "off":
      return 0;
  }
}

/**
 * Script injected into <head> so motion/contrast attributes are applied
 * before first paint (no flash of the wrong theme or a replayed intro).
 */
export const PRE_PAINT_SCRIPT = `(function(){try{
var d=document.documentElement,p={};
try{p=JSON.parse(localStorage.getItem(${JSON.stringify(STORAGE_KEY)})||"{}")||{};}catch(e){}
var m=["full","reduced","off"].indexOf(p.motion)>=0?p.motion:
(window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches?"reduced":"full");
d.dataset.motion=m;
d.dataset.contrast=p.contrast==="high"?"high":"standard";
if(m==="off"||sessionStorage.getItem(${JSON.stringify(STARTUP_SEEN_KEY)})==="1"){d.dataset.startup="skip";}
}catch(e){}})();`;

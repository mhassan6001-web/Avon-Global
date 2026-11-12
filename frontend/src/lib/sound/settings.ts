/** Sound settings model, presets and the event catalogue (pure, unit-tested). */

export const CATEGORIES = [
  "system",
  "interface",
  "typing",
  "notification",
  "feedback",
  "alert",
  "jarvis",
] as const;
export type Category = (typeof CATEGORIES)[number];
export type Bus = "interface" | "notification" | "jarvis";
export type Preset = "immersive" | "balanced" | "quiet" | "custom";

export const EVENTS = {
  startup: { category: "system", bus: "interface", label: "Startup" },
  shutdown: { category: "system", bus: "interface", label: "Sign-out" },
  navigation: { category: "interface", bus: "interface", label: "Navigation" },
  module: { category: "interface", bus: "interface", label: "Open module" },
  typing: { category: "typing", bus: "interface", label: "Typing" },
  notification: { category: "notification", bus: "notification", label: "Notification" },
  message: { category: "notification", bus: "notification", label: "Incoming message" },
  approval: { category: "feedback", bus: "interface", label: "Approval" },
  complete: { category: "feedback", bus: "interface", label: "Task completed" },
  warning: { category: "alert", bus: "notification", label: "Warning" },
  urgent: { category: "alert", bus: "notification", label: "Urgent alert" },
  jarvisOn: { category: "jarvis", bus: "jarvis", label: "JARVIS activation" },
  jarvisOff: { category: "jarvis", bus: "jarvis", label: "JARVIS deactivation" },
  listening: { category: "jarvis", bus: "jarvis", label: "Listening" },
  processing: { category: "jarvis", bus: "jarvis", label: "Processing" },
  response: { category: "jarvis", bus: "jarvis", label: "Response" },
} as const satisfies Record<string, { category: Category; bus: Bus; label: string }>;
export type SoundEvent = keyof typeof EVENTS;

export interface SoundSettings {
  preset: Preset;
  muted: boolean;
  master: number; // 0..1
  volumes: Record<Bus, number> & { voice: number }; // voice = JARVIS speech (Stage 12)
  categories: Record<Category, boolean>;
}

const allOn = Object.fromEntries(CATEGORIES.map((c) => [c, true])) as Record<Category, boolean>;

export const PRESETS: Record<Exclude<Preset, "custom">, Omit<SoundSettings, "muted">> = {
  // Default (Director decision: IMMERSIVE) — still restrained; typing very subtle.
  immersive: {
    preset: "immersive",
    master: 0.7,
    volumes: { interface: 0.6, notification: 0.8, jarvis: 0.8, voice: 0.9 },
    categories: { ...allOn },
  },
  balanced: {
    preset: "balanced",
    master: 0.6,
    volumes: { interface: 0.3, notification: 0.7, jarvis: 0.7, voice: 0.85 },
    categories: { ...allOn, typing: false },
  },
  quiet: {
    preset: "quiet",
    master: 0.45,
    volumes: { interface: 0, notification: 0.5, jarvis: 0.5, voice: 0.7 },
    categories: {
      system: false,
      interface: false,
      typing: false,
      notification: false,
      feedback: false,
      alert: true,
      jarvis: true,
    },
  },
};

export const DEFAULT_SOUND: SoundSettings = { ...PRESETS.immersive, muted: false };

export function applyPreset(
  current: SoundSettings,
  preset: Exclude<Preset, "custom">,
): SoundSettings {
  return { ...PRESETS[preset], muted: current.muted };
}

const clamp = (n: unknown, fallback: number) =>
  typeof n === "number" && Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : fallback;

export function parseSound(raw: unknown): SoundSettings {
  const r = (raw && typeof raw === "object" ? raw : {}) as Partial<SoundSettings>;
  const d = DEFAULT_SOUND;
  const presets = ["immersive", "balanced", "quiet", "custom"];
  return {
    preset: presets.includes(r.preset as string) ? (r.preset as Preset) : d.preset,
    muted: typeof r.muted === "boolean" ? r.muted : d.muted,
    master: clamp(r.master, d.master),
    volumes: {
      interface: clamp(r.volumes?.interface, d.volumes.interface),
      notification: clamp(r.volumes?.notification, d.volumes.notification),
      jarvis: clamp(r.volumes?.jarvis, d.volumes.jarvis),
      voice: clamp(r.volumes?.voice, d.volumes.voice),
    },
    categories: Object.fromEntries(
      CATEGORIES.map((c) => [
        c,
        typeof r.categories?.[c] === "boolean" ? r.categories[c] : d.categories[c],
      ]),
    ) as Record<Category, boolean>,
  };
}

/** Final gain for an event, or 0 if it must not play. */
export function gainFor(settings: SoundSettings, event: SoundEvent): number {
  const { category, bus } = EVENTS[event];
  if (settings.muted || !settings.categories[category]) return 0;
  return settings.master * settings.volumes[bus];
}

/** Minimum spacing (ms) per event so sounds never pile up. */
export const MIN_GAP_MS: Partial<Record<SoundEvent, number>> = {
  typing: 90,
  navigation: 80,
  module: 80,
  processing: 1500,
};

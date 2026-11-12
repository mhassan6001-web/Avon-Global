"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { SoundEngine } from "./engine";
import {
  applyPreset,
  DEFAULT_SOUND,
  parseSound,
  type Preset,
  type SoundEvent,
  type SoundSettings,
} from "./settings";

export const SOUND_STORAGE_KEY = "aven.sound.v1";

interface SoundContextValue {
  settings: SoundSettings;
  /** True once a user gesture has allowed audio in this tab. */
  unlocked: boolean;
  play: (event: SoundEvent) => void;
  update: (patch: Partial<SoundSettings>) => void;
  choosePreset: (preset: Exclude<Preset, "custom">) => void;
  /** Replace settings wholesale (e.g. loaded from the account). */
  replace: (settings: SoundSettings) => void;
}

const SoundContext = createContext<SoundContextValue | null>(null);

function audioFactory(): (() => AudioContext) | null {
  if (typeof window === "undefined") return null;
  const Ctor =
    window.AudioContext ??
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  return Ctor ? () => new Ctor() : null;
}

function store(settings: SoundSettings) {
  try {
    window.localStorage.setItem(SOUND_STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // storage unavailable: settings still apply for this session
  }
}

export function SoundProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<SoundSettings>(DEFAULT_SOUND);
  const [unlocked, setUnlocked] = useState(false);
  const engine = useRef<SoundEngine | null>(null);

  useEffect(() => {
    let initial = DEFAULT_SOUND;
    try {
      const raw = window.localStorage.getItem(SOUND_STORAGE_KEY);
      if (raw) initial = parseSound(JSON.parse(raw));
    } catch {
      // ignore corrupt storage
    }
    engine.current = new SoundEngine(initial, audioFactory());
    setSettings(initial);
  }, []);

  useEffect(() => {
    engine.current?.update(settings);
    if (settings.muted) engine.current?.silenceNow();
    else engine.current?.restore();
  }, [settings]);

  // Browsers block audio until the person interacts; unlock on the first gesture.
  useEffect(() => {
    const unlock = () => {
      if (engine.current?.unlock()) {
        setUnlocked(true);
        window.removeEventListener("pointerdown", unlock);
        window.removeEventListener("keydown", unlock);
      }
    };
    window.addEventListener("pointerdown", unlock);
    window.addEventListener("keydown", unlock);
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, []);

  // Very subtle, throttled typing ticks for printable keys in text fields only.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (!target || event.key.length !== 1 || event.repeat) return;
      if (target instanceof HTMLInputElement && target.type === "password") return;
      if (target.matches("input, textarea, [contenteditable='true']"))
        engine.current?.play("typing");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const play = useCallback((event: SoundEvent) => {
    engine.current?.play(event);
  }, []);

  const update = useCallback((patch: Partial<SoundSettings>) => {
    setSettings((current) => {
      const changesLevels = "master" in patch || "volumes" in patch || "categories" in patch;
      const next = {
        ...current,
        ...patch,
        preset: changesLevels ? "custom" : (patch.preset ?? current.preset),
      };
      store(next);
      return next;
    });
  }, []);

  const choosePreset = useCallback((preset: Exclude<Preset, "custom">) => {
    setSettings((current) => {
      const next = applyPreset(current, preset);
      store(next);
      return next;
    });
  }, []);

  const replace = useCallback((next: SoundSettings) => {
    const parsed = parseSound(next);
    store(parsed);
    setSettings(parsed);
  }, []);

  const value = useMemo(
    () => ({ settings, unlocked, play, update, choosePreset, replace }),
    [settings, unlocked, play, update, choosePreset, replace],
  );
  return <SoundContext.Provider value={value}>{children}</SoundContext.Provider>;
}

const SILENT: SoundContextValue = {
  settings: DEFAULT_SOUND,
  unlocked: false,
  play: () => undefined,
  update: () => undefined,
  choosePreset: () => undefined,
  replace: () => undefined,
};

/** Never throws: components outside the provider simply stay silent. */
export function useSound(): SoundContextValue {
  return useContext(SoundContext) ?? SILENT;
}

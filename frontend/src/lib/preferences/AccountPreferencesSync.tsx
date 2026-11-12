"use client";

import { useEffect, useRef } from "react";

import { send } from "@/lib/api/client";
import { usePreferences } from "@/lib/preferences/PreferencesProvider";
import type { DisplayPreferences } from "@/lib/preferences/preferences";
import { parseSound, type SoundSettings } from "@/lib/sound/settings";
import { useSound } from "@/lib/sound/SoundProvider";

interface AccountPreferences {
  display: DisplayPreferences;
  sound: SoundSettings;
  stored: boolean;
}

/**
 * Keeps display and sound preferences in step with the signed-in account so
 * they follow the person across devices. On load the account copy wins; if
 * the account has none yet, this device's choices are saved to it. Changes
 * are saved (debounced). Failures are silent: preferences still apply locally.
 */
export function AccountPreferencesSync() {
  const { preferences, update } = usePreferences();
  const { settings, replace } = useSound();
  const loaded = useRef(false);
  const skipNextSave = useRef(false);

  useEffect(() => {
    let cancelled = false;
    send<AccountPreferences>("GET", "/auth/preferences")
      .then(({ data }) => {
        if (cancelled) return;
        if (data.stored) {
          skipNextSave.current = true;
          update(data.display);
          replace(parseSound(data.sound));
        } else {
          void send("PUT", "/auth/preferences", {
            body: { display: preferences, sound: settings },
          });
        }
      })
      .catch(() => undefined)
      .finally(() => {
        loaded.current = true;
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once per signed-in shell
  }, []);

  useEffect(() => {
    if (!loaded.current) return;
    if (skipNextSave.current) {
      skipNextSave.current = false;
      return;
    }
    const timer = window.setTimeout(() => {
      void send("PUT", "/auth/preferences", {
        body: { display: preferences, sound: settings },
      }).catch(() => undefined);
    }, 800);
    return () => window.clearTimeout(timer);
  }, [preferences, settings]);

  return null;
}

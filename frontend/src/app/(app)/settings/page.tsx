"use client";

import { LuPlay } from "react-icons/lu";

import { SoundSettingsPanel } from "@/components/sound/SoundSettingsPanel";
import { REPLAY_STARTUP_EVENT } from "@/components/startup/StartupScreen";
import { Button, PageHeader, Panel, SegmentedControl } from "@/components/ui";
import type { ContrastPreference, MotionPreference } from "@/lib/preferences/preferences";
import { usePreferences } from "@/lib/preferences/PreferencesProvider";

import styles from "@/app/pages.module.css";

const MOTION_OPTIONS = [
  { value: "system", label: "Match device" },
  { value: "full", label: "Full" },
  { value: "reduced", label: "Reduced" },
  { value: "off", label: "Off" },
] as const satisfies ReadonlyArray<{ value: MotionPreference; label: string }>;

const CONTRAST_OPTIONS = [
  { value: "standard", label: "Standard" },
  { value: "high", label: "High contrast" },
] as const satisfies ReadonlyArray<{ value: ContrastPreference; label: string }>;

const MOTION_DESCRIPTIONS: Record<string, string> = {
  full: "Smooth transitions and the animated startup sequence.",
  reduced: "Short fades only, with no movement or scaling.",
  off: "No animation. The startup sequence is skipped.",
};

export default function SettingsPage() {
  const { preferences, effectiveMotion, update } = usePreferences();

  return (
    <>
      <PageHeader
        eyebrow="Preferences"
        title="Display, sound & accessibility"
        description="Saved to your account, so they follow you to every device you sign in on."
      />
      <div className={styles.grid}>
        <div className={styles.span6}>
          <Panel eyebrow="Motion" title="Animation intensity">
            <SegmentedControl
              label="Animation intensity"
              value={preferences.motion}
              options={MOTION_OPTIONS}
              onChange={(motion) => update({ motion })}
            />
            <p className={styles.note} aria-live="polite">
              Currently: <strong>{effectiveMotion}</strong>. {MOTION_DESCRIPTIONS[effectiveMotion]}
              {preferences.motion === "system" && " Follows your device's reduce-motion setting."}
            </p>
            <div className={styles.actionsRow}>
              <Button
                size="sm"
                icon={<LuPlay aria-hidden="true" />}
                disabled={effectiveMotion === "off"}
                onClick={() => window.dispatchEvent(new Event(REPLAY_STARTUP_EVENT))}
              >
                Replay startup sequence
              </Button>
            </div>
          </Panel>
        </div>
        <div className={styles.span6}>
          <Panel eyebrow="Contrast" title="Visual contrast">
            <SegmentedControl
              label="Visual contrast"
              value={preferences.contrast}
              options={CONTRAST_OPTIONS}
              onChange={(contrast) => update({ contrast })}
            />
            <p className={styles.note}>
              High contrast replaces translucent glass panels with solid surfaces and brightens text
              and borders.
            </p>
          </Panel>
        </div>
        <div className={styles.span12}>
          <SoundSettingsPanel />
        </div>
      </div>
    </>
  );
}

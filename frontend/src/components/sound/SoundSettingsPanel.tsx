"use client";

import { LuVolume2, LuVolumeX } from "react-icons/lu";

import { Button, Panel, SegmentedControl } from "@/components/ui";
import {
  CATEGORIES,
  EVENTS,
  type Category,
  type Preset,
  type SoundEvent,
} from "@/lib/sound/settings";
import { useSound } from "@/lib/sound/SoundProvider";

import styles from "./sound.module.css";

const PRESET_OPTIONS = [
  { value: "immersive", label: "Immersive" },
  { value: "balanced", label: "Balanced" },
  { value: "quiet", label: "Quiet" },
] as const satisfies ReadonlyArray<{ value: Exclude<Preset, "custom">; label: string }>;

const CATEGORY_LABEL: Record<Category, string> = {
  system: "Startup and sign-out",
  interface: "Navigation and modules",
  typing: "Typing (very subtle)",
  notification: "Notifications and messages",
  feedback: "Approvals and completions",
  alert: "Warnings and urgent alerts",
  jarvis: "JARVIS cues",
};

const PREVIEWS: SoundEvent[] = [
  "startup",
  "navigation",
  "module",
  "typing",
  "notification",
  "message",
  "approval",
  "complete",
  "warning",
  "urgent",
  "jarvisOn",
  "listening",
  "processing",
  "response",
  "jarvisOff",
  "shutdown",
];

function Slider({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  const id = `vol-${label.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <div className={styles.slider}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="range"
        min={0}
        max={100}
        step={5}
        value={Math.round(value * 100)}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        aria-valuetext={`${Math.round(value * 100)} percent`}
      />
      <span className={`${styles.sliderValue} tabular`}>{Math.round(value * 100)}%</span>
    </div>
  );
}

export function SoundSettingsPanel() {
  const { settings, unlocked, play, update, choosePreset } = useSound();
  const presetValue = settings.preset === "custom" ? "immersive" : settings.preset;

  return (
    <Panel
      eyebrow="Sound"
      title="Sound design"
      actions={
        <Button
          size="sm"
          variant={settings.muted ? "primary" : "secondary"}
          icon={
            settings.muted ? <LuVolumeX aria-hidden="true" /> : <LuVolume2 aria-hidden="true" />
          }
          aria-pressed={settings.muted}
          onClick={() => update({ muted: !settings.muted })}
        >
          {settings.muted ? "Muted" : "Mute all"}
        </Button>
      }
    >
      <div className={styles.columns}>
        <div>
          <SegmentedControl
            label="Sound profile"
            value={presetValue}
            options={PRESET_OPTIONS}
            onChange={choosePreset}
          />
          <p className={styles.note} aria-live="polite">
            Profile: <strong>{settings.preset === "custom" ? "Custom" : settings.preset}</strong>.
            Sound is always optional; every feature works silently.
            {!unlocked && " Your browser allows sound after your first click or key press."}
          </p>
          <div className={styles.sliders}>
            <Slider
              label="Master"
              value={settings.master}
              onChange={(master) => update({ master })}
              disabled={settings.muted}
            />
            <Slider
              label="Interface"
              value={settings.volumes.interface}
              onChange={(v) => update({ volumes: { ...settings.volumes, interface: v } })}
              disabled={settings.muted}
            />
            <Slider
              label="Notifications"
              value={settings.volumes.notification}
              onChange={(v) => update({ volumes: { ...settings.volumes, notification: v } })}
              disabled={settings.muted}
            />
            <Slider
              label="JARVIS cues"
              value={settings.volumes.jarvis}
              onChange={(v) => update({ volumes: { ...settings.volumes, jarvis: v } })}
              disabled={settings.muted}
            />
            <Slider
              label="JARVIS voice"
              value={settings.volumes.voice}
              onChange={(v) => update({ volumes: { ...settings.volumes, voice: v } })}
              disabled={settings.muted}
            />
          </div>
        </div>
        <div>
          <fieldset className={styles.toggles}>
            <legend className="hud-label">Sound categories</legend>
            {CATEGORIES.map((category) => (
              <label key={category} className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={settings.categories[category]}
                  onChange={(e) =>
                    update({ categories: { ...settings.categories, [category]: e.target.checked } })
                  }
                />
                <span>{CATEGORY_LABEL[category]}</span>
              </label>
            ))}
          </fieldset>
        </div>
      </div>
      <div className={styles.previews}>
        <p className="hud-label">Preview</p>
        <div className={styles.previewGrid}>
          {PREVIEWS.map((event) => (
            <button
              key={event}
              type="button"
              className={styles.preview}
              onClick={() => play(event)}
              data-sound={event}
            >
              {EVENTS[event].label}
            </button>
          ))}
        </div>
        <p className={styles.note}>
          All sounds are original, synthesised in your browser by AVEN GLOBAL&apos;s own code. No
          film audio or recordings are used. JARVIS&apos;s spoken voice arrives with the voice
          stage.
        </p>
      </div>
    </Panel>
  );
}

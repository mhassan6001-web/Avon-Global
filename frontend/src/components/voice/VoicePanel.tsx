"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { LuMic, LuMicOff, LuSquare } from "react-icons/lu";

import { Badge, Button, Dialog, Panel, SelectField } from "@/components/ui";
import { send } from "@/lib/api/client";
import { errorMessage, useResource } from "@/lib/api/useResource";
import { useSound } from "@/lib/sound/SoundProvider";
import {
  closeMic,
  openMic,
  record,
  speak,
  transcribe,
  type Playback,
  type Recording,
} from "@/lib/voice/media";
import {
  MIC_LABEL,
  micOpen,
  nextMic,
  permissionHelp,
  type MicEvent,
  type MicState,
} from "@/lib/voice/state";

import styles from "./voice.module.css";

/** The on-device wake-word engine loads only once the licence is configured. */
const WAKE_WORD_ARMED = false;

export interface VoiceStatus {
  stt_configured: boolean;
  tts_configured: boolean;
  voices: { id: string; name: string; description: string }[];
  voice_id: string | null;
  speed: string;
  speak_replies: boolean;
  wake_word_licensed: boolean;
  wake_word_enabled: boolean;
  max_clip_kb: number;
}

/**
 * Push-to-talk, spoken replies and wake-word consent for JARVIS.
 * The microphone is never opened until the user presses push-to-talk.
 * ``onQuestion`` sends the transcript through the normal (typed) chain and
 * resolves with JARVIS's reply text.
 */
export function VoicePanel({
  onQuestion,
  onState,
}: {
  onQuestion: (text: string) => Promise<string | null>;
  onState?: (state: MicState) => void;
}) {
  const { settings, play } = useSound();
  const status = useResource<VoiceStatus>("/jarvis/voice/status");
  const [state, setState] = useState<MicState>("off");
  const [notice, setNotice] = useState<string | null>(null);
  const [consentOpen, setConsentOpen] = useState(false);
  const stream = useRef<MediaStream | null>(null);
  const rec = useRef<Recording | null>(null);
  const playback = useRef<Playback | null>(null);
  const s = status.data;

  const dispatch = useCallback(
    (event: MicEvent) =>
      setState((prev) => {
        const next = nextMic(prev, event, WAKE_WORD_ARMED);
        onState?.(next);
        return next;
      }),
    [onState],
  );

  const stopAll = useCallback(() => {
    rec.current?.cancel();
    rec.current = null;
    playback.current?.stop();
    playback.current = null;
    closeMic(stream.current);
    stream.current = null;
    dispatch({ type: "stop" });
  }, [dispatch]);

  // Close the microphone when leaving the page or hiding the tab (no background listening).
  useEffect(() => {
    const hide = () => document.visibilityState === "hidden" && stopAll();
    document.addEventListener("visibilitychange", hide);
    return () => {
      document.removeEventListener("visibilitychange", hide);
      stopAll();
    };
  }, [stopAll]);

  const finish = useCallback(async () => {
    const r = rec.current;
    if (!r) return;
    rec.current = null;
    dispatch({ type: "release" });
    const clip = await r.finish();
    closeMic(stream.current);
    stream.current = null;
    try {
      const text = await transcribe(clip);
      if (!text.trim()) {
        setNotice("I did not catch that. Try again, or type your question.");
        dispatch({ type: "error" });
        return;
      }
      const reply = await onQuestion(text);
      const shouldSpeak = Boolean(reply && s?.speak_replies && s.tts_configured && !settings.muted);
      dispatch({ type: "replied", speak: shouldSpeak });
      if (shouldSpeak && reply) {
        try {
          playback.current = await speak(reply, settings.master * settings.volumes.voice);
          await playback.current.done;
        } catch (e) {
          setNotice(`Voice reply unavailable: ${errorMessage(e)} The answer is on screen.`);
        }
        playback.current = null;
        dispatch({ type: "spoken" });
      }
    } catch (e) {
      setNotice(errorMessage(e));
      play("warning");
      dispatch({ type: "error" });
    }
  }, [dispatch, onQuestion, play, s, settings]);

  const start = useCallback(async () => {
    setNotice(null);
    playback.current?.stop();
    playback.current = null;
    if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setNotice("This browser cannot record audio. Type your question instead.");
      return;
    }
    try {
      stream.current = await openMic();
    } catch {
      setNotice(`Microphone access was refused. ${permissionHelp(navigator.userAgent)}`);
      dispatch({ type: "error" });
      return;
    }
    stream.current.getTracks().forEach((t) =>
      t.addEventListener("ended", () => {
        setNotice("The microphone was turned off by the browser or system.");
        stopAll();
      }),
    );
    play("listening");
    dispatch({ type: "press" });
    rec.current = record(stream.current, () => void finish());
  }, [dispatch, finish, play, stopAll]);

  async function saveSettings(
    patch: Partial<Pick<VoiceStatus, "voice_id" | "speed" | "speak_replies">>,
  ) {
    if (!s) return;
    try {
      await send("PUT", "/jarvis/voice/settings", {
        body: { voice_id: s.voice_id, speed: s.speed, speak_replies: s.speak_replies, ...patch },
      });
      await status.reload();
    } catch (e) {
      setNotice(errorMessage(e));
    }
  }

  async function decideConsent(granted: boolean) {
    setConsentOpen(false);
    try {
      await send("POST", "/jarvis/voice/wake-word/consent", {
        body: { granted, device: navigator.userAgent.slice(0, 120) },
      });
      await status.reload();
    } catch (e) {
      setNotice(errorMessage(e));
    }
  }

  const sttReady = s?.stt_configured ?? false;

  return (
    <Panel title="Voice">
      <div className={styles.row}>
        <span className={styles.indicator} data-state={state} role="status" aria-live="polite">
          {state === "off" ? <LuMicOff aria-hidden="true" /> : <LuMic aria-hidden="true" />}
          {MIC_LABEL[state]}
        </span>
        {(micOpen(state) || state === "speaking") && (
          <Button variant="secondary" icon={<LuSquare aria-hidden="true" />} onClick={stopAll}>
            Stop
          </Button>
        )}
      </div>

      <div className={styles.row}>
        <Button
          variant="primary"
          icon={<LuMic aria-hidden="true" />}
          disabled={!sttReady || state === "processing"}
          aria-pressed={state === "listening"}
          onClick={() => (state === "listening" ? void finish() : void start())}
        >
          {state === "listening" ? "Send what I said" : "Push to talk"}
        </Button>
      </div>
      <p className={styles.note}>
        {sttReady
          ? "Press to speak (up to 15 seconds), then press again to send. The microphone opens only while you speak and audio is not kept."
          : "Speech recognition is not configured yet. Type your question instead."}
      </p>
      {notice && (
        <p className={styles.notice} role="alert">
          {notice}
        </p>
      )}

      {s && (
        <div className={styles.settings}>
          <label className={styles.check}>
            <input
              type="checkbox"
              checked={s.speak_replies}
              disabled={!s.tts_configured}
              onChange={(e) => void saveSettings({ speak_replies: e.target.checked })}
            />
            Speak JARVIS&apos;s replies{!s.tts_configured && " (voice not configured yet)"}
          </label>
          {s.voices.length > 0 && (
            <SelectField
              label="Voice"
              value={s.voice_id ?? ""}
              onChange={(e) => void saveSettings({ voice_id: e.target.value || null })}
              options={[
                { value: "", label: "Default" },
                ...s.voices.map((v) => ({ value: v.id, label: v.name })),
              ]}
            />
          )}
          <label className={styles.range}>
            Speech speed {Number(s.speed).toFixed(2)}×
            <input
              type="range"
              min={0.8}
              max={1.25}
              step={0.05}
              value={Number(s.speed)}
              disabled={!s.tts_configured}
              onChange={(e) => void saveSettings({ speed: Number(e.target.value).toFixed(2) })}
            />
          </label>
          <div className={styles.wake}>
            <div>
              <strong>Wake word</strong>{" "}
              <Badge tone={s.wake_word_enabled ? "gold" : "neutral"}>
                {s.wake_word_enabled ? "Consent given" : "Off"}
              </Badge>
            </div>
            <p className={styles.note}>
              {s.wake_word_licensed
                ? "Hands-free activation while AVEN GLOBAL is open. Detection runs on this device; nothing is sent until the wake phrase is heard."
                : "Not available yet: the wake-word licence is not configured. Push-to-talk always works."}
            </p>
            {s.wake_word_enabled ? (
              <Button variant="ghost" onClick={() => void decideConsent(false)}>
                Turn off and withdraw consent
              </Button>
            ) : (
              <Button
                variant="ghost"
                disabled={!s.wake_word_licensed}
                onClick={() => setConsentOpen(true)}
              >
                Enable wake word…
              </Button>
            )}
          </div>
        </div>
      )}

      <Dialog
        open={consentOpen}
        title="Enable the wake word?"
        onClose={() => setConsentOpen(false)}
      >
        <div className={styles.consent}>
          <p>
            While AVEN GLOBAL is open and visible, this device listens for the wake phrase only.
          </p>
          <ul>
            <li>Detection happens on this device. No audio leaves it until the phrase is heard.</li>
            <li>
              After the phrase, up to 15 seconds of what you say is sent for transcription and not
              kept.
            </li>
            <li>
              It pauses when the tab is hidden or the device sleeps. It never listens in the
              background.
            </li>
            <li>Stop it at any time with the Stop button or by turning it off here.</li>
            <li>Your decision is recorded with this device and the time.</li>
          </ul>
          <div className={styles.actions}>
            <Button variant="ghost" onClick={() => void decideConsent(false)}>
              Not now
            </Button>
            <Button variant="primary" onClick={() => void decideConsent(true)}>
              I agree, enable
            </Button>
          </div>
        </div>
      </Dialog>
    </Panel>
  );
}

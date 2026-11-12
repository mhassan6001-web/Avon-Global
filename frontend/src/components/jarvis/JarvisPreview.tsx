"use client";

import { useEffect, useState } from "react";
import { LuPlay } from "react-icons/lu";

import { Badge, Button, Panel, SegmentedControl } from "@/components/ui";
import { useSound } from "@/lib/sound/SoundProvider";

import { JARVIS_STATES, STATE_LABEL, type JarvisState } from "./head";
import { JarvisPresence } from "./JarvisPresence";
import styles from "./jarvis.module.css";
import { ACTION_STEPS, TaskFlow, type ActionStep, type StepStatus } from "./TaskFlow";

const STATE_SOUND: Partial<
  Record<JarvisState, "jarvisOn" | "listening" | "processing" | "response" | "jarvisOff">
> = {
  listening: "listening",
  processing: "processing",
  speaking: "response",
  muted: "jarvisOff",
  idle: "jarvisOn",
};

/**
 * Stage 3 design preview of JARVIS's visual identity. JARVIS itself (Stage 11)
 * and voice (Stage 12) are not built: nothing here listens, thinks or acts.
 */
export function JarvisPreview() {
  const [state, setState] = useState<JarvisState>("idle");
  const [statuses, setStatuses] = useState<Partial<Record<ActionStep, StepStatus>>>({});
  const [running, setRunning] = useState(false);
  const { play } = useSound();

  useEffect(() => {
    if (!running) return;
    let i = 0;
    const timer = window.setInterval(() => {
      const next: Partial<Record<ActionStep, StepStatus>> = {};
      ACTION_STEPS.forEach((step, k) => {
        next[step.key] = k < i ? "done" : k === i ? "active" : "pending";
      });
      setStatuses(next);
      if (i === ACTION_STEPS.length) {
        window.clearInterval(timer);
        setRunning(false);
        play("complete");
      }
      i += 1;
    }, 650);
    return () => window.clearInterval(timer);
  }, [running, play]);

  return (
    <div className={styles.previewGrid}>
      <Panel
        eyebrow="Identity"
        title="JARVIS presence"
        actions={<Badge tone="gold">Design preview</Badge>}
      >
        <JarvisPresence state={state} />
        <div className={styles.stateChooser}>
          <SegmentedControl
            label="Preview state"
            value={state}
            options={JARVIS_STATES.map((value) => ({ value, label: STATE_LABEL[value] }))}
            onChange={(value) => {
              setState(value);
              const cue = STATE_SOUND[value];
              if (cue) play(cue);
            }}
          />
        </div>
        <p className={styles.previewNote}>
          Visual states only. This preview is not connected to JARVIS: it does not listen, record or
          answer. The microphone is never used on this page.
        </p>
      </Panel>
      <Panel eyebrow="Control chain" title="How JARVIS carries out a task">
        <TaskFlow statuses={statuses} />
        <p className={styles.previewNote}>
          When JARVIS works for real (Stage 11), each step lights up from the server&apos;s own
          progress events. JARVIS cannot skip a step, initiate payments, change supplier bank
          details, submit tenders or approve its own requests.
        </p>
        <div className={styles.previewActions}>
          <Button
            size="sm"
            icon={<LuPlay aria-hidden="true" />}
            disabled={running}
            onClick={() => {
              setStatuses({});
              setRunning(true);
            }}
          >
            Play simulated sequence
          </Button>
          <span className={styles.previewNote}>
            Simulation for design review. No action is performed.
          </span>
        </div>
      </Panel>
    </div>
  );
}

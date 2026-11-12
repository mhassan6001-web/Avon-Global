/**
 * Microphone and voice state (pure). The indicator always shows one of these
 * states (VOICE_AND_SOUND §3.2): Off · Standby · Listening · Processing, plus
 * Speaking while JARVIS's reply plays.
 */

export type MicState = "off" | "standby" | "listening" | "processing" | "speaking";

export type MicEvent =
  | { type: "press" } // push-to-talk pressed
  | { type: "wake" } // wake word detected (on-device)
  | { type: "release" } // push-to-talk released: clip is sent
  | { type: "timeout" } // 15-second cap reached: clip is sent
  | { type: "replied"; speak: boolean }
  | { type: "spoken" }
  | { type: "stop" } // stop control: microphone closed, speech halted
  | { type: "error" }
  | { type: "arm" } // wake word armed (consented, licensed, page visible)
  | { type: "disarm" }; // wake word paused (page hidden, consent withdrawn)

export const MAX_CLIP_MS = 15_000;

export const MIC_LABEL: Record<MicState, string> = {
  off: "Microphone off",
  standby: "Standby: wake word armed",
  listening: "Listening",
  processing: "Processing",
  speaking: "Speaking",
};

/** Next state. ``armed`` says whether the wake word should resume afterwards. */
export function nextMic(state: MicState, event: MicEvent, armed: boolean): MicState {
  const rest: MicState = armed ? "standby" : "off";
  switch (event.type) {
    case "press":
      // Push-to-talk always works, and interrupts speech (VO-03).
      return "listening";
    case "wake":
      return state === "standby" ? "listening" : state;
    case "release":
    case "timeout":
      return state === "listening" ? "processing" : state;
    case "replied":
      return state === "processing" ? (event.speak ? "speaking" : rest) : state;
    case "spoken":
      return state === "speaking" ? rest : state;
    case "stop":
      return "off";
    case "error":
      return rest;
    case "arm":
      return state === "off" ? "standby" : state;
    case "disarm":
      return state === "standby" ? "off" : state;
    default:
      return state;
  }
}

/** Is the microphone stream open in this state? (Stop control visible.) */
export function micOpen(state: MicState): boolean {
  return state === "standby" || state === "listening";
}

/** Recording format the browser supports, preferring compact Opus. */
export function pickMimeType(isSupported: (t: string) => boolean): string | null {
  for (const t of ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4", "audio/webm"]) {
    if (isSupported(t)) return t;
  }
  return null;
}

/** Plain-language recovery for a refused microphone (MP-01), per browser. */
export function permissionHelp(userAgent: string): string {
  if (/Edg\//.test(userAgent))
    return "In Edge, select the lock icon in the address bar, then allow Microphone.";
  if (/Chrome\//.test(userAgent))
    return "In Chrome, select the site settings icon in the address bar, then allow Microphone.";
  if (/Firefox\//.test(userAgent))
    return "In Firefox, select the microphone icon in the address bar and remove the block.";
  if (/Safari\//.test(userAgent))
    return "In Safari, open Settings for This Website and set Microphone to Allow.";
  return "Allow microphone access for this site in your browser settings.";
}

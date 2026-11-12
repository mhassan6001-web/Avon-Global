/** Browser microphone, recording and playback (thin wrappers, client only). */

import { API_PREFIX, ApiError, CSRF_COOKIE, readCookie } from "@/lib/api/client";

import { MAX_CLIP_MS, pickMimeType } from "./state";

/** Ask for the microphone. Audio processing stays on (echo cancellation etc.). */
export async function openMic(): Promise<MediaStream> {
  return navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
}

/** Close the microphone fully: every track ended, not just muted (WW-06). */
export function closeMic(stream: MediaStream | null): void {
  stream?.getTracks().forEach((t) => t.stop());
}

export interface Recording {
  /** Finish and return the clip (also called automatically at 15 seconds). */
  finish(): Promise<Blob>;
  cancel(): void;
}

export function record(stream: MediaStream, onCap: () => void): Recording {
  const mimeType = pickMimeType((t) => MediaRecorder.isTypeSupported(t)) ?? undefined;
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
  const chunks: Blob[] = [];
  recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  const done = new Promise<Blob>((resolve) => {
    recorder.onstop = () => resolve(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
  });
  recorder.start();
  const cap = window.setTimeout(onCap, MAX_CLIP_MS);
  return {
    async finish() {
      window.clearTimeout(cap);
      if (recorder.state !== "inactive") recorder.stop();
      return done;
    },
    cancel() {
      window.clearTimeout(cap);
      if (recorder.state !== "inactive") recorder.stop();
      chunks.length = 0;
    },
  };
}

function csrfHeaders(): Record<string, string> {
  const csrf = readCookie(CSRF_COOKIE);
  return csrf ? { "X-CSRF-Token": csrf } : {};
}

async function fail(response: Response): Promise<never> {
  const body = (await response.json().catch(() => null)) as {
    error?: { code?: string; message?: string };
  } | null;
  throw new ApiError({
    status: response.status,
    code: body?.error?.code ?? "voice_failed",
    message: body?.error?.message ?? "Voice request failed.",
    requestId: response.headers.get("x-request-id"),
    body,
  });
}

/** Send one clip for transcription. The server keeps no audio. */
export async function transcribe(clip: Blob): Promise<string> {
  const form = new FormData();
  form.append("audio", clip, `clip.${clip.type.includes("mp4") ? "m4a" : "webm"}`);
  const response = await fetch(`${API_PREFIX}/jarvis/voice/transcribe`, {
    method: "POST",
    body: form,
    headers: { Accept: "application/json", ...csrfHeaders() },
    credentials: "same-origin",
  });
  if (!response.ok) await fail(response);
  return ((await response.json()) as { text: string }).text;
}

export interface Playback {
  done: Promise<void>;
  stop(): void;
}

/** Fetch and play JARVIS's spoken reply; ``stop`` halts it immediately (VO-03). */
export async function speak(
  text: string,
  volume: number,
  style = "conversation",
): Promise<Playback> {
  const response = await fetch(`${API_PREFIX}/jarvis/voice/speak`, {
    method: "POST",
    body: JSON.stringify({ text: text.slice(0, 2000), style }),
    headers: { "Content-Type": "application/json", ...csrfHeaders() },
    credentials: "same-origin",
  });
  if (!response.ok) await fail(response);
  const url = URL.createObjectURL(await response.blob());
  const audio = new Audio(url);
  audio.volume = Math.max(0, Math.min(1, volume));
  const cleanup = () => URL.revokeObjectURL(url);
  const done = new Promise<void>((resolve) => {
    audio.onended = () => {
      cleanup();
      resolve();
    };
    audio.onerror = () => {
      cleanup();
      resolve();
    };
  });
  await audio.play();
  return {
    done,
    stop() {
      audio.pause();
      audio.currentTime = 0;
      cleanup();
      audio.dispatchEvent(new Event("ended"));
    },
  };
}

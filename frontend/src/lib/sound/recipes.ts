/**
 * Original AVEN GLOBAL sound designs, synthesised with the Web Audio API.
 * No recorded, sampled or third-party audio is used (licence record:
 * docs/legal/AUDIO_LICENCES.md).
 */
import type { SoundEvent } from "./settings";

type Ctx = BaseAudioContext;

function tone(
  ctx: Ctx,
  out: AudioNode,
  t: number,
  freq: number,
  dur: number,
  peak: number,
  type: OscillatorType = "sine",
  glideTo?: number,
) {
  const osc = ctx.createOscillator();
  const g = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t);
  if (glideTo) osc.frequency.exponentialRampToValueAtTime(glideTo, t + dur);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(Math.max(peak, 0.0002), t + Math.min(0.02, dur / 4));
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  osc.connect(g).connect(out);
  osc.start(t);
  osc.stop(t + dur + 0.02);
}

function noise(
  ctx: Ctx,
  out: AudioNode,
  t: number,
  dur: number,
  peak: number,
  filter: BiquadFilterType,
  from: number,
  to?: number,
) {
  const length = Math.max(1, Math.floor(ctx.sampleRate * dur));
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / length);
  const src = ctx.createBufferSource();
  src.buffer = buffer;
  const f = ctx.createBiquadFilter();
  f.type = filter;
  f.frequency.setValueAtTime(from, t);
  if (to) f.frequency.exponentialRampToValueAtTime(to, t + dur);
  const g = ctx.createGain();
  g.gain.setValueAtTime(peak, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  src.connect(f).connect(g).connect(out);
  src.start(t);
  src.stop(t + dur + 0.02);
}

export const RECIPES: Record<SoundEvent, (ctx: Ctx, out: AudioNode, t: number) => void> = {
  startup: (c, o, t) => {
    tone(c, o, t, 110, 2.2, 0.35, "sine");
    tone(c, o, t + 0.05, 164.8, 2.1, 0.22, "sine");
    tone(c, o, t + 0.9, 1318.5, 1.2, 0.05, "triangle");
    tone(c, o, t + 1.05, 1975.5, 1.1, 0.03, "sine");
  },
  shutdown: (c, o, t) => tone(c, o, t, 440, 0.7, 0.18, "sine", 196),
  navigation: (c, o, t) => {
    tone(c, o, t, 1760, 0.035, 0.05, "sine");
    noise(c, o, t, 0.03, 0.02, "highpass", 4000);
  },
  module: (c, o, t) => {
    noise(c, o, t, 0.2, 0.05, "bandpass", 400, 2400);
    tone(c, o, t + 0.06, 659.3, 0.12, 0.05, "sine");
  },
  typing: (c, o, t) => noise(c, o, t, 0.008, 0.012, "highpass", 6000),
  notification: (c, o, t) => {
    tone(c, o, t, 1318.5, 0.35, 0.12, "sine");
    tone(c, o, t + 0.12, 1760, 0.45, 0.1, "sine");
  },
  message: (c, o, t) => tone(c, o, t, 1568, 0.4, 0.1, "sine"),
  approval: (c, o, t) => {
    tone(c, o, t, 880, 0.25, 0.12, "sine");
    tone(c, o, t + 0.11, 1318.5, 0.4, 0.12, "sine");
  },
  complete: (c, o, t) => {
    tone(c, o, t, 988, 0.2, 0.08, "sine");
    tone(c, o, t + 0.09, 1480, 0.3, 0.08, "sine");
  },
  warning: (c, o, t) => {
    tone(c, o, t, 330, 0.18, 0.14, "triangle");
    tone(c, o, t + 0.24, 330, 0.18, 0.14, "triangle");
  },
  urgent: (c, o, t) => {
    for (let i = 0; i < 3; i++) tone(c, o, t + i * 0.2, 294, 0.14, 0.18, "triangle");
  },
  jarvisOn: (c, o, t) => {
    [523.3, 784, 1046.5].forEach((f, i) => tone(c, o, t + i * 0.08, f, 0.5, 0.1, "sine"));
    tone(c, o, t, 130.8, 0.9, 0.12, "sine");
  },
  jarvisOff: (c, o, t) =>
    [1046.5, 784, 523.3].forEach((f, i) => tone(c, o, t + i * 0.08, f, 0.4, 0.08, "sine")),
  listening: (c, o, t) => tone(c, o, t, 600, 0.18, 0.08, "sine", 900),
  processing: (c, o, t) => tone(c, o, t, 440, 0.14, 0.05, "sine"),
  response: (c, o, t) => tone(c, o, t, 784, 0.16, 0.07, "sine"),
};

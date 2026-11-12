/**
 * Geometry for JARVIS's abstract particle head (original design, inspired by
 * reference 07's composition only). Pure functions, unit-tested.
 */

export type JarvisState = "idle" | "listening" | "processing" | "speaking" | "muted" | "offline";

export const JARVIS_STATES: readonly JarvisState[] = [
  "idle",
  "listening",
  "processing",
  "speaking",
  "muted",
  "offline",
];

export const STATE_LABEL: Record<JarvisState, string> = {
  idle: "Standing by",
  listening: "Listening",
  processing: "Thinking",
  speaking: "Speaking",
  muted: "Microphone off",
  offline: "Offline",
};

export interface Point3 {
  x: number;
  y: number;
  z: number;
}

/** Deterministic pseudo-random sequence so the head is identical on every render. */
export function seeded(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/** Horizontal radius of the head at height y (−1.5 neck … 1 crown). */
export function profileRadius(y: number): number {
  if (y > 1 || y < -1.5) return 0;
  if (y >= -0.35) return Math.sqrt(Math.max(0, 1 - ((y - 0.05) / 1.0) ** 2)) * 0.82; // cranium
  if (y >= -0.95) return 0.62 - (-0.35 - y) * 0.45; // jaw taper
  return 0.34; // neck
}

/** Points on the head surface, with a forward-facing nose/chin bias. */
export function headPoints(count: number, seed = 7): Point3[] {
  const rand = seeded(seed);
  const points: Point3[] = [];
  while (points.length < count) {
    const y = -1.5 + rand() * 2.5;
    const r = profileRadius(y);
    if (r <= 0) continue;
    const a = rand() * Math.PI * 2;
    let x = Math.cos(a) * r;
    const z = Math.sin(a) * r * 0.92;
    // Facial profile: push the front (x > 0) out slightly around nose and chin height.
    if (x > 0 && y > -0.75 && y < 0.1) x *= 1 + 0.12 * Math.exp(-(((y + 0.25) / 0.18) ** 2));
    points.push({ x, y, z });
  }
  return points;
}

/** Rotate around the vertical axis. */
export function rotateY(p: Point3, angle: number): Point3 {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return { x: p.x * c + p.z * s, y: p.y, z: -p.x * s + p.z * c };
}

/** Waveform amplitude (0..1) for each state. */
export function amplitudeFor(state: JarvisState): number {
  switch (state) {
    case "speaking":
      return 1;
    case "listening":
      return 0.45;
    case "processing":
      return 0.25;
    case "idle":
      return 0.1;
    default:
      return 0;
  }
}

/** Sum-of-sines waveform sample at x (0..1), time t (s). */
export function waveSample(x: number, t: number, amplitude: number, layer = 0): number {
  const envelope = Math.sin(Math.PI * x) ** 2;
  const v =
    Math.sin(x * 18 + t * 3.1 + layer) * 0.55 +
    Math.sin(x * 41 - t * 5.3 + layer * 2) * 0.3 +
    Math.sin(x * 77 + t * 8.7 + layer * 3) * 0.15;
  return v * envelope * amplitude;
}

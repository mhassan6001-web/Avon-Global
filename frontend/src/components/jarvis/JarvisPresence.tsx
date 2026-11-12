"use client";

import { useEffect, useMemo, useRef } from "react";

import { usePreferences } from "@/lib/preferences/PreferencesProvider";

import {
  amplitudeFor,
  headPoints,
  rotateY,
  STATE_LABEL,
  waveSample,
  type JarvisState,
} from "./head";
import styles from "./jarvis.module.css";

const ICE = [140, 203, 232] as const;
const GOLD = [230, 200, 138] as const;

/**
 * JARVIS identity visual: an abstract particle head with a ribbon waveform
 * (gold for JARVIS, ice for the person). Canvas-drawn, original artwork.
 * With motion off it renders one still frame. Decorative: state is also
 * given as text for assistive technology.
 */
export function JarvisPresence({
  state,
  size = 320,
  label = true,
}: {
  state: JarvisState;
  size?: number;
  label?: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const { effectiveMotion } = usePreferences();
  const points = useMemo(() => headPoints(size > 200 ? 1400 : 700), [size]);
  const stateRef = useRef(state);
  stateRef.current = state;
  // With motion off a single still frame is drawn, so it is redrawn when the state changes.
  const stillFrameKey = effectiveMotion === "off" ? state : null;

  useEffect(() => {
    const el = canvas.current;
    const ctx = el?.getContext("2d");
    if (!el || !ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    el.width = size * dpr;
    el.height = size * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    let amp = amplitudeFor(stateRef.current);
    let frame = 0;
    const start = performance.now();
    const speed = effectiveMotion === "full" ? 1 : effectiveMotion === "reduced" ? 0.35 : 0;

    const draw = (now: number) => {
      const t = ((now - start) / 1000) * speed;
      const s = stateRef.current;
      amp += (amplitudeFor(s) - amp) * 0.08;
      const dim = s === "offline" ? 0.25 : s === "muted" ? 0.55 : 1;
      ctx.clearRect(0, 0, size, size);

      // Base glow (navy depth tone, ice core).
      const glow = ctx.createRadialGradient(
        size / 2,
        size * 0.86,
        4,
        size / 2,
        size * 0.86,
        size * 0.5,
      );
      glow.addColorStop(0, `rgba(${ICE.join(",")},${0.28 * dim})`);
      glow.addColorStop(1, "rgba(16,32,72,0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, size, size);

      // Head particles.
      const angle = -0.55 + Math.sin(t * 0.25) * 0.25;
      const scale = size * 0.3;
      const cx = size / 2;
      const cy = size * 0.47;
      const pulse = s === "processing" ? 0.5 + 0.5 * Math.sin(t * 4) : 0;
      for (const p of points) {
        const r = rotateY(p, angle);
        const depth = (r.z + 1) / 2;
        const alpha = (0.12 + depth * 0.6) * dim + pulse * 0.08;
        ctx.fillStyle = `rgba(${ICE.join(",")},${alpha.toFixed(3)})`;
        const px = cx + r.x * scale;
        const py = cy - r.y * scale;
        const d = 0.6 + depth * 0.9;
        ctx.fillRect(px, py, d, d);
      }

      // Ribbon waveform across the head.
      const wy = size * 0.5;
      const layers: Array<[readonly number[], number]> =
        s === "listening"
          ? [
              [ICE, 0],
              [ICE, 1.3],
            ]
          : [
              [GOLD, 0],
              [ICE, 1.7],
              [GOLD, 3.1],
            ];
      layers.forEach(([rgb, layer], i) => {
        ctx.beginPath();
        for (let k = 0; k <= 160; k++) {
          const x = k / 160;
          const y = wy + waveSample(x, t, amp, layer) * size * 0.16;
          if (k === 0) ctx.moveTo(x * size, y);
          else ctx.lineTo(x * size, y);
        }
        ctx.strokeStyle = `rgba(${rgb.join(",")},${((0.85 - i * 0.22) * Math.max(dim, 0.3)).toFixed(3)})`;
        ctx.lineWidth = i === 0 ? 1.6 : 1;
        ctx.shadowColor = `rgba(${rgb.join(",")},0.6)`;
        ctx.shadowBlur = i === 0 ? 8 : 0;
        ctx.stroke();
        ctx.shadowBlur = 0;
      });

      if (speed > 0 && !document.hidden) frame = requestAnimationFrame(draw);
    };

    frame = requestAnimationFrame(draw);
    const onVisible = () => {
      if (!document.hidden && speed > 0) {
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(draw);
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [points, size, effectiveMotion, stillFrameKey]);

  return (
    <figure className={styles.presence} data-state={state} style={{ width: size }}>
      <canvas
        ref={canvas}
        style={{ width: size, height: size }}
        aria-hidden="true"
        data-testid="jarvis-canvas"
      />
      {label && (
        <figcaption className={`${styles.stateLabel} hud-label`} role="status">
          JARVIS · {STATE_LABEL[state]}
        </figcaption>
      )}
    </figure>
  );
}

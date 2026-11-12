/** Pure chart geometry (unit-tested). */

export interface Point {
  label: string;
  value: number;
}

export function niceMax(max: number): number {
  if (max <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(max));
  const step = [1, 2, 2.5, 5, 10].find((s) => s * magnitude >= max) ?? 10;
  return step * magnitude;
}

/** Map points to SVG coordinates inside a width × height box (y grows down). */
export function project(points: Point[], width: number, height: number, pad = 4) {
  const max = niceMax(Math.max(0, ...points.map((p) => p.value)));
  const n = points.length;
  return points.map((p, i) => ({
    ...p,
    x: n === 1 ? width / 2 : pad + (i * (width - 2 * pad)) / (n - 1),
    y: height - pad - (Math.max(0, p.value) / max) * (height - 2 * pad),
  }));
}

/** Smooth path through points (monotone-ish Catmull-Rom → cubic Bézier). */
export function smoothPath(pts: Array<{ x: number; y: number }>): string {
  if (pts.length === 0) return "";
  if (pts.length === 1) return `M${pts[0]!.x},${pts[0]!.y}`;
  let d = `M${pts[0]!.x},${pts[0]!.y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i]!;
    const p1 = pts[i]!;
    const p2 = pts[i + 1]!;
    const p3 = pts[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C${c1x.toFixed(2)},${c1y.toFixed(2)} ${c2x.toFixed(2)},${c2y.toFixed(2)} ${p2.x},${p2.y}`;
  }
  return d;
}

/** Donut arcs: start/end angles (radians) for each share; zero total → no arcs. */
export function arcs(values: number[]): Array<{ start: number; end: number }> {
  const total = values.reduce((a, b) => a + Math.max(0, b), 0);
  if (total <= 0) return [];
  let angle = -Math.PI / 2;
  return values.map((v) => {
    const sweep = (Math.max(0, v) / total) * Math.PI * 2;
    const seg = { start: angle, end: angle + sweep };
    angle += sweep;
    return seg;
  });
}

export function arcPath(cx: number, cy: number, r: number, start: number, end: number): string {
  const large = end - start > Math.PI ? 1 : 0;
  const sx = cx + r * Math.cos(start);
  const sy = cy + r * Math.sin(start);
  const ex = cx + r * Math.cos(end - 1e-6);
  const ey = cy + r * Math.sin(end - 1e-6);
  return `M${sx.toFixed(2)},${sy.toFixed(2)} A${r},${r} 0 ${large} 1 ${ex.toFixed(2)},${ey.toFixed(2)}`;
}

export function formatAmount(value: number, currency?: string): string {
  const abs = Math.abs(value);
  const compact =
    abs >= 1e9
      ? `${(value / 1e9).toFixed(1)}B`
      : abs >= 1e6
        ? `${(value / 1e6).toFixed(1)}M`
        : abs >= 1e3
          ? `${(value / 1e3).toFixed(1)}K`
          : value.toFixed(0);
  return currency ? `${currency} ${compact}` : compact;
}

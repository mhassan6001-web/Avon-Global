"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { usePreferences } from "@/lib/preferences/PreferencesProvider";

import styles from "./charts.module.css";
import { arcPath, arcs, formatAmount, niceMax, project, smoothPath, type Point } from "./scale";

const GOLD = ["#c9a464", "#8f7444", "#e6c88a", "#5f4d2e", "#b39255", "#3a3122"];
const EMPTY_BARS = [30, 45, 38, 60, 42, 70, 55, 48, 65, 40, 52, 58];

/**
 * Chart card. ``data === null`` means the source module has no records yet:
 * a faint placeholder silhouette is shown with "No data yet" — never sample
 * numbers (Director decision C5). An empty array means "zero records in range".
 */
export function ChartCard({
  title,
  meta,
  empty,
  emptyLabel = "No data yet",
  children,
  className,
}: {
  title: string;
  meta?: ReactNode;
  empty: boolean;
  emptyLabel?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`${styles.card} ${className ?? ""}`} aria-label={title}>
      <header className={styles.head}>
        <h3 className={styles.title}>{title}</h3>
        {meta && <span className={styles.meta}>{meta}</span>}
      </header>
      <div className={empty ? styles.ghost : undefined} aria-hidden={empty || undefined}>
        {children}
      </div>
      {empty && (
        <div className={styles.empty}>
          <span className={styles.emptyText}>{emptyLabel}</span>
        </div>
      )}
    </section>
  );
}

function useScale() {
  return usePreferences().motionScale;
}

export function AreaChart({
  data,
  height = 160,
  currency,
}: {
  data: Point[] | null;
  height?: number;
  currency?: string;
}) {
  const s = useScale();
  const width = 600;
  const points =
    data && data.length > 1 ? data : EMPTY_BARS.map((v, i) => ({ label: `${i}`, value: v }));
  const pts = project(points, width, height, 8);
  const line = smoothPath(pts);
  const area = `${line} L${pts[pts.length - 1]!.x},${height} L${pts[0]!.x},${height} Z`;
  const max = niceMax(Math.max(...points.map((p) => p.value)));
  return (
    <svg
      viewBox={`0 0 ${width} ${height + 18}`}
      className={styles.svg}
      role="img"
      aria-label={data ? `Trend, maximum ${formatAmount(max, currency)}` : "No data"}
    >
      <defs>
        <linearGradient id="aven-area" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#c9a464" stopOpacity="0.45" />
          <stop offset="1" stopColor="#c9a464" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((f) => (
        <line
          key={f}
          x1="0"
          x2={width}
          y1={height * f}
          y2={height * f}
          stroke="rgba(255,255,255,0.05)"
        />
      ))}
      <motion.path
        d={area}
        fill="url(#aven-area)"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8 * s, delay: 0.3 * s }}
      />
      <motion.path
        d={line}
        fill="none"
        stroke="#e6c88a"
        strokeWidth="2"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.2 * s, ease: "easeOut" }}
      />
      {data &&
        pts.map((p, i) => (
          <motion.circle
            key={i}
            cx={p.x}
            cy={p.y}
            r="3.5"
            fill="#f2e6c8"
            style={{ filter: "drop-shadow(0 0 6px rgba(230,200,138,0.9))" }}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: (0.6 + i * 0.05) * s }}
          >
            <title>{`${p.label}: ${formatAmount(p.value, currency)}`}</title>
          </motion.circle>
        ))}
      {data &&
        pts.map((p, i) => (
          <text
            key={`t${i}`}
            x={p.x}
            y={height + 14}
            textAnchor="middle"
            fontSize="10"
            fill="#6b7286"
          >
            {p.label}
          </text>
        ))}
    </svg>
  );
}

export function BarChart({
  data,
  height = 140,
  currency,
}: {
  data: Point[] | null;
  height?: number;
  currency?: string;
}) {
  const s = useScale();
  const width = 600;
  const points =
    data && data.length ? data : EMPTY_BARS.map((v, i) => ({ label: `${i}`, value: v }));
  const max = niceMax(Math.max(...points.map((p) => p.value)));
  const slot = width / points.length;
  const bw = Math.max(6, slot * 0.46);
  return (
    <svg
      viewBox={`0 0 ${width} ${height + 18}`}
      className={styles.svg}
      role="img"
      aria-label={data ? `Bar chart, maximum ${formatAmount(max, currency)}` : "No data"}
    >
      {points.map((p, i) => {
        const h = (Math.max(0, p.value) / max) * (height - 4);
        return (
          <g key={i}>
            <motion.rect
              x={i * slot + (slot - bw) / 2}
              y={height - h}
              width={bw}
              height={h}
              rx="2"
              fill="url(#aven-bar)"
              style={{ transformOrigin: `0px ${height}px` }}
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ duration: 0.6 * s, delay: i * 0.04 * s, ease: [0.16, 1, 0.3, 1] }}
            >
              <title>{`${p.label}: ${formatAmount(p.value, currency)}`}</title>
            </motion.rect>
            {data && (
              <text
                x={i * slot + slot / 2}
                y={height + 14}
                textAnchor="middle"
                fontSize="10"
                fill="#6b7286"
              >
                {p.label}
              </text>
            )}
          </g>
        );
      })}
      <defs>
        <linearGradient id="aven-bar" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#e6c88a" />
          <stop offset="1" stopColor="#8f7444" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function Donut({
  data,
  size = 150,
  centre,
}: {
  data: Point[] | null;
  size?: number;
  centre?: ReactNode;
}) {
  const s = useScale();
  const values = data && data.some((d) => d.value > 0) ? data.map((d) => d.value) : [3, 2, 1.4, 1];
  const segs = arcs(values);
  const r = size / 2 - 12;
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `${size}px 1fr`,
        gap: 16,
        alignItems: "center",
      }}
    >
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        role="img"
        aria-label="Share chart"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth="14"
        />
        {segs.map((seg, i) => (
          <motion.path
            key={i}
            d={arcPath(size / 2, size / 2, r, seg.start, seg.end)}
            fill="none"
            stroke={GOLD[i % GOLD.length]}
            strokeWidth="14"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.7 * s, delay: i * 0.12 * s }}
          />
        ))}
        <text
          x="50%"
          y="52%"
          textAnchor="middle"
          fontSize="16"
          fill="#faf6ee"
          fontFamily="var(--font-display)"
        >
          {centre}
        </text>
      </svg>
      {data && (
        <ul className={styles.legend}>
          {data.map((d, i) => (
            <li key={d.label}>
              <span className={styles.swatch} style={{ background: GOLD[i % GOLD.length] }} />
              <span>{d.label}</span>
              <span className="tabular">{formatAmount(d.value)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function HBarList({ data, currency }: { data: Point[] | null; currency?: string }) {
  const s = useScale();
  const rows =
    data && data.length ? data : [80, 64, 52, 40, 30].map((v, i) => ({ label: `—${i}`, value: v }));
  const max = niceMax(Math.max(...rows.map((r) => r.value)));
  return (
    <ul className={styles.hbar}>
      {rows.map((r, i) => (
        <li key={r.label} className={styles.hbarRow}>
          <span>{data ? r.label : "—"}</span>
          <span className={styles.hbarTrack}>
            <motion.span
              className={styles.hbarFill}
              style={{ display: "block", width: `${(r.value / max) * 100}%` }}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.6 * s, delay: i * 0.06 * s }}
            />
          </span>
          <span className="tabular">{data ? formatAmount(r.value, currency) : ""}</span>
        </li>
      ))}
    </ul>
  );
}

export function Sparkline({
  data,
  width = 120,
  height = 32,
}: {
  data: number[] | null;
  width?: number;
  height?: number;
}) {
  const s = useScale();
  const values = data && data.length > 1 ? data : [3, 4, 3.5, 5, 4.2, 5.5, 5, 6];
  const pts = project(
    values.map((v, i) => ({ label: `${i}`, value: v })),
    width,
    height,
    2,
  );
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      aria-hidden="true"
      style={{ opacity: data ? 1 : 0.2 }}
    >
      <motion.path
        d={smoothPath(pts)}
        fill="none"
        stroke="#c9a464"
        strokeWidth="1.6"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.9 * s }}
      />
    </svg>
  );
}

/** KPI tile (ref 08 top row). ``value === null`` → "No data yet", never a fake number. */
export function KpiCard({
  icon,
  label,
  value,
  note,
  trend,
}: {
  icon: ReactNode;
  label: string;
  value: string | null;
  note?: string;
  trend?: number[] | null;
}) {
  return (
    <div className={styles.kpi}>
      <span className={styles.kpiIcon} aria-hidden="true">
        {icon}
      </span>
      <div>
        <p className={styles.kpiLabel}>{label}</p>
        <p className={styles.kpiValue}>
          {value ?? <span style={{ color: "var(--text-muted)", fontSize: 14 }}>No data yet</span>}
        </p>
        {note && <p className={styles.kpiNote}>{note}</p>}
      </div>
      <Sparkline data={value === null ? null : (trend ?? null)} />
    </div>
  );
}

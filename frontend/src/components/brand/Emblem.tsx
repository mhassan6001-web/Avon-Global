import { useId } from "react";

/**
 * AVEN GLOBAL emblem — an original mark: a stylised "A" whose crossbar is a
 * horizon arc, set inside an orbit ring (A + globe). Not a registered
 * trademark; see docs/design-system.md.
 *
 * `drawn` paths carry `data-draw` so the startup sequence can animate strokes.
 */
export function Emblem({
  size = 40,
  title = "AVEN GLOBAL",
  decorative = false,
}: {
  size?: number;
  title?: string;
  decorative?: boolean;
}) {
  const gradientId = useId();
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      role={decorative ? undefined : "img"}
      aria-hidden={decorative || undefined}
      aria-label={decorative ? undefined : title}
    >
      <defs>
        <linearGradient
          id={gradientId}
          x1="10"
          y1="6"
          x2="54"
          y2="58"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#F2E6C8" />
          <stop offset="0.55" stopColor="#D6BB83" />
          <stop offset="1" stopColor="#A1824C" />
        </linearGradient>
      </defs>
      <circle
        data-draw="ring"
        cx="32"
        cy="32"
        r="29"
        stroke={`url(#${gradientId})`}
        strokeOpacity="0.55"
        strokeWidth="1.25"
        pathLength={1}
      />
      <path
        data-draw="letter"
        d="M14.5 50 L32 13 L49.5 50"
        stroke={`url(#${gradientId})`}
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
      />
      <path
        data-draw="horizon"
        d="M19.5 39.5 Q32 33 44.5 39.5"
        stroke={`url(#${gradientId})`}
        strokeWidth="2.25"
        strokeLinecap="round"
        pathLength={1}
      />
      <path
        data-draw="meridian"
        d="M9 41 Q32 54 55 41"
        stroke={`url(#${gradientId})`}
        strokeOpacity="0.35"
        strokeWidth="1"
        strokeLinecap="round"
        pathLength={1}
      />
      <circle data-draw="apex" cx="32" cy="13" r="2.4" fill="#F2E6C8" />
    </svg>
  );
}

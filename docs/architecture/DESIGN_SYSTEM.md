# AVEN GLOBAL design system (Stage 1 foundation)

> **Superseded in part (Director decisions, 2026-11-12).** Stage 3 will
> change these tokens and styles:
>
> - **grey-black/graphite base surfaces**, with navy kept as a secondary depth
>   tone
> - two-tier gold
> - a solid gold active pill
> - a HUD typeface for JARVIS and a serif for long text
> - dark only
> - rich motion graphics at Full intensity
>
> See `REFERENCE_IMAGE_SPECIFICATION.md` §6.1.

Tokens live in `frontend/src/app/globals.css`. Components use tokens only and
never raw colour values.

## Direction

Taken from the Director's reference images (2026-11-12):

- **Base:** a navy and champagne-gold boardroom feel. Midnight navy surfaces,
  thin gold lines and edges, warm white text.
- **Panels:** layered glass with a gold hairline along the top edge. This is
  the signature detail.
- **Signal accent:** a restrained ice blue (`--ice-400`), used only for live
  system values such as latency and status glows.
- **Layout:** a practical dashboard structure. Left sidebar with a highlighted
  active item, a top bar with status, notifications and profile, card grids,
  and bottom tabs on phones.
- **Excluded:** hot-pink/cyan neon and constant motion, as the master
  instructions require.

## Palette

| Token | Value | Use |
|-------|-------|-----|
| `--navy-950` | `#070d1f` | App background |
| `--navy-900` / `850` / `800` | `#0b1428` / `#0f1a33` / `#142241` | Elevated surfaces |
| `--blue-600` | `#24427d` | Deep-blue atmosphere |
| `--gold-400` | `#d6bb83` | Champagne gold: accent, active, focus |
| `--gold-300` / `500` | `#e7d3a4` / `#c3a268` | Gold highlight and depth |
| `--ivory-50` | `#faf6ee` | Warm white: primary text |
| `--graphite-400…700` | | Muted text and dividers |
| `--ice-400` | `#8ccbe8` | Live system signals only |
| success / warning / danger | `#6cc596` / `#e3b85c` / `#e67a74` | Status |

Contrast: primary text on the background is about 17:1, secondary text about
10:1, and gold on navy about 9:1. High-contrast mode removes translucency and
brightens text and borders.

## Typography

- Sora (500/600) for display text: headings and the wordmark.
- Inter for the interface.
- A system monospace font for technical values.

All fonts are self-hosted through `next/font`, so there are no third-party
requests at runtime.

## Identity

- **Emblem:** an original mark. A stylised "A" whose crossbar is a horizon
  arc, inside an orbit ring (A + globe), in a gold gradient.
- **Wordmark:** "AVEN" in wide-tracked Sora, with "GLOBAL" in small gold
  capitals.
- This is not a registered trademark. Registration is a separate legal step.

## Motion

- Tokens: `--dur-fast` 140 ms, `--dur-base` 220 ms, `--dur-slow` 420 ms,
  ease-out `cubic-bezier(0.16, 1, 0.3, 1)`. In TypeScript the equivalent is
  `src/lib/motion/tokens.ts`.
- **Preference:** match device, full, reduced or off. Reduced uses 0.4×
  durations with no movement or scaling. Off disables animation completely and
  skips the startup sequence.
- The preference is applied before first paint by an inline script, so there
  is no flash.
- **Startup sequence:** about 2.3 s at full motion and 0.9 s reduced. It plays
  once per browser session and can be skipped with the Skip button, Esc, Enter,
  Space or a click. It overlays the app without blocking it.
- **Route transitions:** a 10 px rise with a fade over 320 ms.
- **Sidebar active indicator:** a shared-layout spring.

## Components (`src/components/ui`)

`Button`, `IconButton`, `Panel`, `Badge`, `StatusDot`, `Skeleton`, `Spinner`,
`EmptyState`, `PageHeader`, `SegmentedControl` (an accessible radio group that
supports arrow keys).

The shell components are in `src/components/shell`.

## JARVIS visual states (specified; built in Stage 12)

These are confirmed by the Director's JARVIS design specification. The details
are in `VOICE_AND_SOUND.md` §6:

- Off and Standby (wake word armed)
- Listening: live microphone waveform with an ice-blue pulse
- Processing: orbiting gold arc
- Speaking: waveform driven by the TTS output
- Muted, and Error/offline

They are built from these tokens:

- gold for identity
- ice blue (`--ice-400`) for live audio only
- amber (`--warning-400`) for errors

Reduced or off motion replaces the waveforms with a static level meter and
text labels.

## Sound profile

The default sound preset is **Immersive**, as confirmed by the Director. It
still follows the restraint rules in `VOICE_AND_SOUND.md` §4. Every sound has a
visual equivalent, so muting never removes information.

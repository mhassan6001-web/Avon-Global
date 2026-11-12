# Reference image specification

- Status: **Approved by the Director on 2026-11-12, with the decisions in
  §6.** Implementation starts in Stage 3.
- Instruction: `docs/reference-image-fidelity-instruction.md`. The reference
  images are the **primary visual design specification**.
- Images: `design-references/` (copied unchanged from the Director's uploads
  of 2026-11-12).

## 1. Inspection record

| # | Repository file | Original upload name | Size (px) | Inspected |
|---|-----------------|----------------------|-----------|-----------|
| 01 | `ref-01-voice-assistant-console.jpg` | Screenshot_12-11-2026_111212_chatgpt.com.jpeg | 697 × 678 | ✔ |
| 02 | `ref-02-holographic-control-room.jpg` | Screenshot_12-11-2026_111150_chatgpt.com.jpeg | 1248 × 707 | ✔ |
| 03 | `ref-03-navy-gold-boardroom.jpg` | Screenshot_12-11-2026_111124_chatgpt.com.jpeg | 1300 × 703 | ✔ |
| 04 | `ref-04-hologram-reception-multilingual.jpg` | Screenshot_12-11-2026_111023_chatgpt.com.jpeg | 1242 × 707 | ✔ |
| 05 | `ref-05-dark-teams-dashboard.jpg` | Screenshot_12-11-2026_11954_chatgpt.com.jpeg | 1064 × 662 | ✔ |
| 06 | `ref-06-multi-device-messaging-tasks.jpg` | Screenshot_12-11-2026_11918_chatgpt.com.jpeg | 1352 × 767 | ✔ |
| 07 | `ref-07-holographic-head-waveform.jpg` | Screenshot_12-11-2026_11837_chatgpt.com.jpeg | 1040 × 694 | ✔ |
| 08 | `ref-08-black-gold-analytics-dashboard.jpg` | Screenshot_12-11-2026_11716_chatgpt.com.jpeg | 1084 × 726 | ✔ |

All 8 supplied images were accessible and inspected. None is missing or
corrupted.

**Inspection method:**

- Each image was viewed in full.
- Image 08 was also enlarged (dashboard crop at 2×).
- Dominant and accent colours were measured from pixels (median of filtered
  pixel sets), not estimated by eye.

**Limits of the source material (stated, not hidden):**

- All 8 are browser **screenshots of AI-generated images**: JPEG, 697–1352 px
  wide.
- Exact pixel dimensions, font names and fine border widths cannot be
  measured. Proportions are approximate (±5%), and typography is *matched by
  style*, not identified.
- If higher-resolution originals exist, please add them to `design-references/`.
- Images 02 and 04 contain **garbled, AI-generated text**. Image 01 shows
  invented metrics ("98.6% ACCURACY", "USER ID 74903"). These are not
  reproduced: real labels and real data replace them.
- Images 05 and 06 show **third-party product designs** ("OrgaNize",
  "Workfast.ai", with people's photos). Image 01 shows a "CORP-AI SOLUTIONS"
  logo. Their **layout patterns** are adopted. Their names, logos, icons,
  photos and exact trade dress are not.

## 2. Classification

| Type | Images | How they are used |
|------|--------|-------------------|
| **Application screens** (direct layout specifications) | **08** (primary dashboard), **05** (desktop module with side panel), **06** (messaging desktop and two phone screens) | Reproduce composition, proportions, density and components |
| **JARVIS identity and states** | **01**, **07**, **04** | Reproduce waveform forms, status panel structure and hologram motifs inside the app |
| **Atmosphere and material** | **03**, **02** | Reproduce colour relationships, gold architectural line work, glass panels and glow treatment |

Images 02, 03, 04 and 07 are photographic 3D scenes: rooms, people, cities.
A web application cannot reproduce the rooms themselves. What is
reproducible is the **interface elements shown within them** and their
**lighting and colour language**. This is recorded for each image below.

## 3. Register

### Ref 08: black and gold analytics dashboard — PRIMARY desktop reference

- **Represents:** a desktop analytics dashboard, plus a laptop variant at
  bottom-left. → **Director Command Centre** and the base app frame.
- **Layout**, measured on the monitor crop:
  - **Left rail** ≈ 8% of width: a gold dot logo at the top, then 7 items
    (a small icon with a short label). The **active item is a solid gold
    filled pill** with dark icon and label.
  - **Top row:** 3 KPI cards, each with a circular gold icon, two text lines
    and a gold sparkline. The third card is wider.
  - **Main grid, about 3 columns (≈ 52% / 16% / 22%):**
    - left: a large **gold area chart** with glowing data points over a
      gradient fill to transparent; below it a **gold bar chart** with
      uneven heights
    - middle: a tall card with a **gold donut** and a 5-item legend list with
      gold circle bullets
    - right: a column of an area chart card, a **horizontal gold bar ranking**
      and a gold donut with legend
  - **Bottom:** a wide table with star icons in the first column, inline gold
    sparklines and gold status dots, plus a side list with gold toggles.
- **Colour (measured):**
  - surfaces near-black charcoal `#141617` / `#0d0e0e`
  - card fill slightly lighter, about `#1a1814`–`#211e19`
  - gold elements median `#B39255` (deep antique gold)
  - gold highlights lighter, about `#E6C88A`
  - text and labels in muted grey
- **Typography:** labels are placeholder bars in the image (unreadable).
  Implied: a small, light, uppercase-free sans with tabular numerals.
- **Cards:** radius about 10–12 px, a 1 px low-contrast border, no heavy
  shadow, generous inner padding, consistent ~16 px gutters.
- **Interaction implied:** hover on data points, toggles, an active nav pill.
- **Responsive (from its laptop variant):** the same rail and card language,
  fewer columns, donut and stat cards stacked.
- **Implementation notes:**
  - This image defines the **density and the gold-on-dark data
    visualisation language** for every dashboard.
  - Charts animate in (line draw and bar grow) once, on load.
  - **No figures may be invented.** Until real records exist, each chart
    frame shows an explicit "no data yet" state in the same position
    (Decision C5).

### Ref 05: dark module page with cards and a side chat panel

- **Represents:** a "Teams" module page. → **HR / Departments**, **Staff
  overview**, and the **page template "card grid + right utility panel"**.
- **Layout:**
  - **Sidebar** about 17% of width: logo at the top, 8 items with icon and
    label. The **active item is a solid filled rounded pill** (electric blue
    in the image).
  - **Header row:** page title on the left, a wide rounded search field in
    the centre-right, a theme toggle, a bell in an outlined circle, and an
    avatar circle.
  - **Toolbar:** a dropdown ("overview") and a primary filled button.
  - **Content:** a **2 × 2 grid of entity cards**, each with:
    - title and overflow menu (⋯)
    - overlapping avatar stack with a "+N" chip
    - lead avatar, name and role
    - **ring progress chart** with a number in the centre and a 2-item
      legend
    - a description paragraph
    - a right-aligned text link
  - A **right panel** about 25% of width (team chat): message bubbles with
    avatar, name and timestamp; own messages right-aligned; a composer at
    the bottom with a send icon.
  - The whole app sits inside a rounded device frame with a light border.
- **Colour (measured):**
  - background `#131313`, cards `#1b1b1d`–`#292a2e`
  - accent `#0554ED`, a saturated blue (**conflict C4**)
  - secondary status colour red
  - text white and grey
- **Typography:**
  - headings and UI in a geometric sans (Poppins-like)
  - card description paragraphs in a **serif** (a distinctive detail)
- **Responsive:** the right panel collapses into a drawer or tab below 1200 px.
- **Implementation notes:**
  - Avatars use real staff photos only once uploaded, otherwise initials. No
    stock faces.
  - Progress rings show real task counts (Stage 10).

### Ref 06: messaging desktop, tasks phone and project dashboard phone

- **Represents** three screens:
  - **(a) desktop team messaging** → Staff Communications (Stage 10)
  - **(b) phone task inbox** → mobile Tasks
  - **(c) phone project dashboard** → mobile Director and project overview
- **(a) Desktop:**
  - top bar with logo, history icon, centred search, user chip
  - thin **icon rail** (Channel, Project)
  - **channel list** with "#" icons and member counts; the active channel is
    a solid highlight
  - conversation header with channel name, member avatars and count
  - messages with avatar, bold name, timestamp and wrapped body
  - composer with formatting toolbar
  - a floating round action button (yellow)
- **(b) Phone tasks:**
  - hamburger, title and filter icon
  - rounded search field
  - list rows, each with a **coloured rounded-square icon**, a label, a
    right-hand count badge (red "99+") or a lock icon
  - a floating "+" button and an "Add quick tasks" row
  - a **5-tab bottom bar** with icon and label; the active tab is accent
    coloured and one tab has a badge
- **(c) Phone dashboard:**
  - back, title and a status chip dropdown
  - segmented tabs (Dashboard, Tasks, Comments)
  - a **2-column grid of stat tiles**, each with a large coloured number, a
    label and a sub-label
  - a "Priority breakdown" coloured bar chart by month
  - a weekly progress card with a bar
- **Colour (measured):** navy `#181e2c` / `#101725`, borders `#272f3b`; accents
  yellow (actions and active), red (overdue), blue (open), green
  (completed).
- **Typography:** rounded system sans (SF-like); bold numerals in tiles.
- **Implementation notes:**
  - Map yellow to **gold**. Keep red, blue and green only as semantic status
    colours.
  - This is the **primary mobile reference**: bottom tab bar, list rows, stat
    tiles.

### Ref 01: JARVIS voice console (glass HUD panel)

- **Represents:** an AI voice-assistant status panel. → **JARVIS console**
  (expanded voice mode) and the listening, processing and speaking visuals.
- **Elements:**
  - a large glass panel with a **glowing thin border and chamfered (cut)
    corners**
  - title in **wide-tracked uppercase techno type** with the state word in an
    accent ("ACTIVE")
  - a **multi-strand ribbon waveform**: dozens of thin sinusoidal strands
    across the full width, brightest at the centre
  - a lower-left **status block**: connection state with a horizontal
    progress bar, and live log lines in monospace
  - a centre **emblem hexagon** with circuit traces to node dots
  - lower-right metrics
  - bottom-right **tab strip** (Options | Logs | Settings)
  - a hologram projector ring under the panel
- **Colour (measured):** cyan `#61A2B9`-family glow on near-black
  `#010306`–`#143A4D`, with **magenta/pink** accents (**conflict C3**).
- **Implementation notes:**
  - Reproduce the panel geometry, the ribbon waveform (canvas or WebGL,
    driven by the real microphone or TTS analyser), the status block and the
    tab strip.
  - Replace the hexagon with the **AVEN emblem**.
  - Show **only real values**: connection state, mic level, latency measured
    by the client. Never decorative fake statistics.
  - Reduced motion uses a static level meter.

### Ref 07: holographic head with a spectrum waveform

- **Represents:** an AI presence. → the **JARVIS identity visual** (idle,
  speaking) and the startup or JARVIS-activation centrepiece.
- **Elements:**
  - a large translucent **particle-filled human head in profile** on a
    **circular glowing pedestal**
  - a horizontal **spectrum-bar waveform** (vertical bars, symmetric)
    passing through the head
  - a deep blue-violet palette
- **Colour (measured):** `#0B1743`, `#344284`, `#6982C3`, with violet and pink
  highlights.
- **Implementation notes:**
  - Stylised particle head (WebGL or canvas point cloud, or a pre-rendered
    video loop with a poster frame), recoloured to navy, ice and gold.
  - Spectrum bars react to TTS output when speaking.
  - Must be original artwork, not traced from the image.
  - Lazy-loaded, and disabled when motion is off.

### Ref 04: hologram receptionist and multilingual greeting

- **Represents:** a voice-agent scene. → **reference for JARVIS speaking
  feedback** (the waveform stream) and the **wall-of-dashboards density**.
- **Elements:**
  - a translucent humanoid figure (female) with a headset
  - a **dual-colour particle waveform** (amber and cyan) flowing from the
    speaker across the scene
  - a desk with **orange and blue neon edge lines**
  - curved walls of dashboards (donuts, bars, gauges)
  - a top banner with a multilingual greeting (garbled text)
- **Colour (measured):** steel blue `#3E596B`–`#61899A`, with amber and cyan
  accents.
- **Implementation notes:**
  - Adopt the **amber (gold) and cyan dual-tone waveform** for "JARVIS
    speaking", with gold for JARVIS and ice for the user.
  - Do not adopt the female figure (JARVIS is male-voiced). See **C7**.
  - Do not reproduce the garbled text.

### Ref 03: navy and gold executive boardroom — PRIMARY atmosphere reference

- **Represents:** the brand atmosphere. → global background, **startup and
  sign-in scene**, panel lighting.
- **Elements:**
  - deep navy walls
  - **thin champagne-gold architectural lines** (straight and diagonal inlays
    on the walls and glass)
  - warm gold cove lighting rectangles in the ceiling
  - a glossy black surface with reflections
  - small **translucent floating panels** (gauges, line and bar charts,
    gold chat bubbles)
  - a glass partition with gold and blue line graphs
  - a night-city window
- **Colour (measured):**
  - navy `#090E1B`, `#1A2B46`, `#0C182D`
  - warm light `#ECC990`
  - hologram blue `#73A3C3`
- **Implementation notes:**
  - This image **confirms the brand palette**: navy, gold lines, a cool blue
    holographic accent.
  - Gold line-work becomes a decorative SVG layer (startup, sign-in, empty
    states, panel corners).
  - Floating mini-panels become the glass card style.

### Ref 02: holographic control room

- **Represents:** an operations centre. → **Tenders and international trade
  map**, network visualisation, and glass panel framing.
- **Elements:**
  - floating translucent panels with **thin cyan borders and corner accents**
  - **world maps with glowing points**
  - radar circles
  - a central **network node graph** (hub-and-spoke glow)
  - warm amber LED lines tracing the architecture
  - multi-monitor desks
- **Colour (measured):**
  - teal-grey `#26444E`, `#4B6261`
  - cyan glow `#7ABBC0`
  - amber `#E1C29A`
- **Implementation notes:**
  - A world or regional map (Malawi, South Africa, Zambia first) with
    supplier, customer and shipment nodes, from **real records only**.
  - Glass panels get corner-bracket accents.
  - Amber is mapped to brand gold.

## 4. Component-to-reference mapping

| Application screen or component | Primary ref | Secondary | Stage |
|---------------------------------|-------------|-----------|-------|
| App frame and background | 03 | 08 | 3 |
| Sidebar or left rail (solid filled active pill) | 08 | 05 | 3 |
| Header (title, search, notifications, avatar) | 05 | 06a | 3 (search when global search exists) |
| KPI card with sparkline | 08 (top row) | — | 3/4 |
| Area, bar, donut and horizontal-bar charts | 08 | 03 | 3 (components), 4 (data) |
| Data table with inline sparklines and status dots | 08 (bottom) | — | 3/4 |
| **Director Command Centre** | **08** | 03 | 4 |
| Glass panel (border glow, corner accents) | 02 | 01, 03 | 3 |
| Startup and sign-in scene | 03 | 07 | 3 (startup), 2 (sign-in form) |
| **JARVIS console** (voice mode) | **01** | 04 | 12 |
| JARVIS identity visual (idle and speaking) | **07** | 01 | 3 (placeholder), 12 |
| Listening, processing and speaking waveforms | 01 (ribbon), 07 (spectrum), 04 (dual-tone) | — | 3/12 |
| Microphone and connection status block | 01 | — | 12 |
| Staff Communications (desktop) | **06a** | 05 (chat panel) | 10 |
| Tasks (mobile) | **06b** | — | 10/15 |
| Mobile Director and project dashboard | **06c** | 08 | 4/15 |
| Mobile bottom tab bar | 06b | — | 3/15 |
| HR, Departments and Staff overview cards | **05** | — | 9 |
| Tenders map and international trade view | **02** | — | 5/6 |
| Notifications panel | 05 (bell) | 06 | 3 |

Stage 2 screens (sign-in, 2FA, admin users, audit log) have **no dedicated
reference**. They will use ref 03 atmosphere for sign-in, and the ref 05 and
08 component language for admin tables and forms.

## 5. Current Stage 1 shell against the references (side by side)

Comparison: `design-references/comparison-stage1-vs-ref08.png` (ref 08 crop
next to the Stage 1 Command Centre at 1440 × 900).

| Aspect | Reference | Stage 1 today | Deviation |
|--------|-----------|---------------|-----------|
| Surface colour | Near-black charcoal (08), deep navy (03) | Navy `#070d1f` with blue radial glow | Lighter and bluer than 08. Matches 03. |
| Gold | Deep antique `#B39255` fills, with lighter highlights | Champagne `#D6BB83` used thinly | Too pale. Gold under-used as fill. |
| Sidebar active state | **Solid filled pill** (08 gold, 05 blue) | Subtle gradient with outline and gold bar | Does not match |
| Sidebar content | Short icon list (08), 8 items (05) | 3 sections, 14 items with "Planned" tags | Much denser and text-heavy |
| Dashboard composition | Dense multi-chart grid (KPIs, area, bar, donut, ranking, table) | 4 text-led panels, no charts | **Major** |
| Cards | Solid dark, ~12 px radius, subtle border | Glass with blur and gold hairline | Partly matches 02/03, not 05/08 |
| Header | Search, toggle, bell, avatar (05) | Status pill, environment badge, bell, profile | No search (deliberate: no fake features) |
| Typography | Geometric sans and serif body (05); techno uppercase for HUD (01) | Sora and Inter | HUD typeface missing |
| JARVIS visuals | 01, 04, 07 | None | Not built (Stage 3 placeholder, Stage 12) |

**Conclusion:** the Stage 1 shell is functionally sound, but visually it is
**not yet faithful** to refs 08 and 05. Correcting it is Stage 3 work, done
screen by screen with the comparison procedure in §7.

## 6. Conflicts: Director decisions (2026-11-12)

| # | Conflict | Proposed resolution |
|---|----------|---------------------|
| C1 | Ref 08 base is charcoal-black. The brand palette and ref 03 are midnight navy. | **Navy-black:** surfaces at ref 08 luminance with a navy hue (about `#0A0F1C`, cards about `#111827`). Preserves 08's contrast and the brand. |
| C2 | Ref 08 gold `#B39255` vs the current champagne `#D6BB83` | **Two-tier gold:** antique `#B39255` for fills, charts and active pills; champagne `#E6C88A` for highlights, focus and text accents. |
| C3 | Refs 01, 02 and 04 use cyan and **magenta/pink neon**. The master instructions say no excessive neon. | Cyan/ice glow **only for JARVIS and live data**. **No pink or magenta.** Glow kept soft. |
| C4 | Ref 05 accent is saturated blue `#0554ED`. | Use the **gold filled pill** (ref 08). Blue only as a semantic status colour ("open"). |
| C5 | Ref 08 shows dense charts, but the rules forbid invented figures. | Build the full chart composition. Each chart shows a designed "No data yet" state until real records exist. **No sample numbers**, except in clearly labelled development-only demo mode. |
| C6 | Ref 05 has a light/dark theme toggle. | **Dark only** (the brand). The toggle is replaced by sound and motion quick settings. |
| C7 | JARVIS figure: female hologram (04) vs abstract male-profile head (07) | **Abstract particle head (07)**, recoloured, consistent with the male voice. |
| C8 | Ref 05 serif body text | Adopt a refined serif for long descriptive text only (for example Cormorant or Source Serif, OFL licence). The UI stays sans. |
| C9 | Ref 01 HUD uppercase typeface | Add an OFL techno face (for example Rajdhani or Orbitron) for **JARVIS and HUD labels only**. |

### 6.1 Decisions recorded

| # | Decision |
|---|----------|
| C1 | **Grey-black and gold.** Base surfaces follow ref 08's charcoal/graphite black, not navy-black. Midnight navy and deep blue stay in the palette as **secondary depth tones** (gradients, the JARVIS glow and hologram light), so the brand palette is kept, not dropped. |
| C2 | Two-tier gold: antique gold for fills, champagne gold for highlights. Approved. |
| C3 | Cyan/ice only for JARVIS and live data, and no pink. Approved, **with "a lot of motion graphics"** requested. At Full intensity, motion is rich and purposeful: chart draw-ins, data-flow lines, panel reveals, waveform and particle work, and connection animations. Every effect still respects the motion setting (Full, Reduced or Off), the reduced-motion preference and performance budgets. There are no endless distracting loops on working screens (master §5). |
| C4 | Solid gold active pill. Approved. |
| C5 | Full chart layout with designed "No data yet" states, and no sample numbers. Approved. |
| C6 | Dark only. Approved. |
| C7 | Abstract particle head for JARVIS. Approved, **plus task-execution visuals**: when JARVIS works, animated connection lines run from the JARVIS core to the module or record involved. The real execution steps (permission → validation → approval → execution → audit) light up as connected nodes. They reflect actual backend progress events and are never decorative fakes. See AI_ARCHITECTURE §6. |
| C8 | Serif for long text. Approved, **and JARVIS briefs the Director**: the daily briefing has a serif reading view and can be spoken by JARVIS (Stage 11 briefing tool, Stage 12 voice). |
| C9 | HUD/techno typeface for JARVIS and HUD labels. Approved. |

## 7. Implementation and quality-control procedure (per screen)

1. Open the mapped reference(s) from §4.
2. Write the screen's structure and component list in the stage plan.
3. Build with shared components (tokens updated per §6 decisions).
4. Capture screenshots at **matching viewport sizes**: 1440 × 900 desktop,
   1024 × 768 tablet, 390 × 844 phone.
5. Produce a **side-by-side comparison image** saved in
   `design-references/comparisons/`.
6. List the deviations. Fix them, or record a justified exception (rule,
   data or legal reason).
7. Only then mark the screen complete. **Never claim pixel-perfect accuracy.**
   The references are low-resolution AI renders, so fidelity is judged on
   composition, proportion, colour relationships, density and distinctive
   details.

## 8. Missing references

**None missing among the supplied images.** These screens have no reference,
and one would help:

- the sign-in screen
- data-entry forms (invoice, purchase order)
- tender detail
- finance reports
- the settings and sound panel

If the Director has references for these, place them in
`design-references/` with descriptive names.

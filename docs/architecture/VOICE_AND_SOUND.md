# JARVIS voice, wake word and sound: architecture and acceptance criteria

- Status: **Specification approved by the Director 2026-11-12. Not implemented.**
- Source: `docs/jarvis-design-specification.md` (confirmed by the Director on
  2026-11-12), the master project instructions §6, §10 and §11, and
  `ROADMAP.md`.
- Implementation stages:
  - **Stage 3:** sound engine and sound settings.
  - **Stage 11:** JARVIS AI core.
  - **Stage 12:** voice, wake word and JARVIS visual states.
  - **Stage 15:** mobile and native assessment.

## 1. Confirmed decisions

| Decision | Value | Meaning |
|----------|-------|---------|
| Voice profile | `CINEMATIC` | An original, deep, refined, male-sounding executive voice. |
| Activation mode | `WAKE_WORD` | Hands-free activation is a product requirement. It stays user-controllable, is off until consented to, and push-to-talk is always available. |
| Sound profile | `IMMERSIVE` | The default sound preset is Immersive. Balanced and Quiet presets are also provided. |

These decisions sit alongside the existing master-instruction requirements and
replace none of them. Where requirements interact, this document records how
they are reconciled (§7).

## 2. Voice (CINEMATIC)

**Character:** deep, rich and composed. Articulate and conversational.
Authoritative without sounding robotic. An executive-butler manner with dry
humour, clear pronunciation and natural pauses. Personality text:
`backend/app/ai/prompts/jarvis_personality.md`.

**Architecture:**

- A provider-independent `TextToSpeechProvider` interface on the server, with
  `synthesize(text, voice_id, speed, style)` returning a stream. Provider keys
  stay on the server only.
- **Delivery styles** are passed as provider parameters where supported:
  `briefing`, `conversation`, `alert` and `urgent`. Otherwise they are
  expressed through SSML or prosody, or simply through pacing.
- **Streaming playback** with interruption: the Stop button, a new
  push-to-talk press, or the wake word cancels playback within 150 ms.
- **Voice selection:** the Director previews the candidate voices (a fixed
  sample script) and selects one. The selection is stored per user.
- **Controls:** speech speed (0.8×–1.25×) and JARVIS voice volume.

**Originality rules (hard requirements):**

- No imitation of any actor, celebrity, fictional character or copyrighted
  voice. Prompts and voice descriptions must not reference one.
- Cloning a real person's voice requires that person's written consent and a
  commercial licence, such as a contracted voice actor. Otherwise only
  provider-designed or stock voices whose licence permits commercial use are
  allowed.
- Every voice asset and provider licence is recorded in
  `docs/legal/AUDIO_LICENCES.md` (created in Stage 3).

## 3. Wake word (WAKE_WORD)

### 3.1 Design

1. **Detection runs on the device only.** A wake-word engine runs inside the
   app (WebAssembly in a Web Worker / AudioWorklet). Until the wake word is
   detected, **no audio leaves the device and none is stored.**
2. After detection, the app plays the activation cue and shows the
   **Listening** state. It records only the following utterance (voice-activity
   endpointing, 15 s maximum) and sends that clip for speech-to-text.
3. After the response, the app returns to wake-word standby. Conversation audio
   is not retained by default. The transcript is kept as conversation history
   under the retention policy.
4. **Push-to-talk** (hold the button or a keyboard shortcut) works whether or
   not the wake word is enabled.
5. **A microphone stop control is always visible** while the microphone is
   open. It closes the microphone stream immediately (all `MediaStreamTrack`s
   stopped, not just muted).

### 3.2 Consent and control

- The wake word is **disabled by default for every user**. Enabling it shows a
  plain-language consent screen: what is listened for, that detection is
  on-device, what is sent after detection, and how to stop. The consent is
  recorded in the audit log with its time and device.
- The Director configures:
  - the wake phrase, chosen from the trained phrases available (§3.4)
  - sensitivity (low/medium/high)
  - automatic standby timeout
  - whether the wake word is allowed per device
- A persistent indicator shows the microphone state: **Off · Standby (wake
  word armed) · Listening · Processing**. The browser's own recording
  indicator is never hidden.

### 3.3 Platform capabilities and limits (researched 2026-11-12)

| Platform | Wake word available | Limits we will document to users |
|----------|---------------------|----------------------------------|
| Windows / macOS: Chrome, Edge, Firefox, Safari | **Yes, while AVEN GLOBAL is open** and microphone permission is granted. | Stops when the browser closes, the computer sleeps, or the OS revokes the microphone. Background tabs may be throttled, so the supported mode is "app open". |
| iPhone / iPad: Safari and installed PWA | **Foreground only.** | Web pages lose microphone capture when backgrounded. Installed home-screen apps stop capture when minimised or when Control Centre opens. **No background or locked-screen listening.** |
| Android: Chrome and installed PWA | **Foreground only.** | Same limitation for web apps: no background or locked-screen listening. |
| Future native Android app (Stage 15 assessment) | Possibly in the background, via a foreground service with a persistent notification. | To be verified against the Android version and Play policy at the time. Not promised. |
| Future native iOS app (Stage 15 assessment) | Background microphone use is tightly restricted and subject to App Store review. | Not promised. Push-to-talk and Siri Shortcuts are the likely fallback. |
| Desktop native wrapper (optional, later) | While the app is running. | Only if the Director requests a desktop app. |

**We will never promise background or locked-screen listening on a platform
that does not permit it.** The app detects the capability at runtime and shows
the fallback: "Wake word works while AVEN GLOBAL is open. Use push-to-talk
otherwise."

### 3.4 Engine options (Director decision required before Stage 12)

| Option | Pros | Constraints |
|--------|------|-------------|
| **A. Picovoice Porcupine (Web/WASM, iOS, Android SDKs)** | Mature and on-device. Supports Chrome, Edge, Firefox and Safari. Custom phrases are trained in their console. Native SDKs exist for a later mobile app. | Commercial licence and an AccessKey are required. Internet is needed for licence validation. Recurring cost. |
| **B. openWakeWord architecture, with our own trained phrase model** | The code is Apache-2.0. Runs in the browser through ONNX Runtime Web. No per-device fees. | **The ready-made pre-trained models (including "hey jarvis") are CC BY-NC-SA 4.0 and cannot be used commercially.** We would need to train our own phrase head and verify the licence of every component. More engineering and accuracy testing. |
| ~~C. Browser Web Speech API in continuous mode~~ | | **Rejected.** In Chrome it sends audio to a remote service by default, which would mean continuous transmission. On-device mode (`processLocally`) is experimental and not available across all target browsers. |

**Director decision (2026-11-12): Option A, a Picovoice Porcupine paid
licence.** The Director will supply the AccessKey at the end of development.

- It is stored only as the server-held environment secret
  `PICOVOICE_ACCESS_KEY`, never committed, and delivered to clients only in
  the form the SDK requires.
- Until the key is configured, the wake word shows "not configured" and
  push-to-talk works normally.
- Option B stays possible later behind the same `WakeWordEngine` interface.

**Suggested phrase:** "Hey JARVIS" or "JARVIS". Two to three syllables with
distinct phonemes reduce false triggers. The final choice follows false-accept
testing (§8).

### 3.5 Voice never authorises

Recognising the wake word or a voice proves nothing about identity. Commands
from voice go through the same chain as typed ones:

authentication → permission check → interpretation → validation → approval →
execution → audit.

Restricted operations always require **on-screen confirmation by the signed-in
user**, and step-up re-authentication (second factor) where the action policy
requires it. See `docs/security/SECURITY_MODEL.md`.

## 4. Immersive audio identity

**Originality:** every sound is original. They are either synthesised in-house
with the Web Audio API (procedural tones, filtered noise, FM bells) or
commissioned or licensed with written commercial rights, and logged in
`docs/legal/AUDIO_LICENCES.md`. Film soundtracks, dialogue and film sound
effects are never extracted, reproduced or imitated.

| Category | Events | Character |
|----------|--------|-----------|
| `system` | Startup (cinematic, ≤ 2.5 s), shutdown/sign-out | Low warm swell with a gold "shimmer" tail |
| `interface` | Navigation, module open, typing feedback | Very short (≤ 60 ms) soft ticks and airy whooshes |
| `notification` | Notification, incoming message | Two-note glass chime |
| `feedback` | Approval, task completed | Rising perfect-fifth chime |
| `alert` | Warning, urgent alert | Distinct but restrained: lower pitch, no sirens, never looping |
| `jarvis` | Activation, deactivation, listening start, processing, response start | A signature motif shared across JARVIS cues |

**Restraint rules:**

- No sound longer than 2.5 s except the startup sound.
- Never more than one interface sound per 80 ms.
- Typing feedback is throttled to at most one tick per 90 ms. It is off by
  default in the Quiet and Balanced presets, and quieter than any other
  interface sound in Immersive.
- The processing cue plays once. It never loops.
- Alerts do not repeat unless the user has not acknowledged them, and then at
  most every 60 s.

**Engine:** one shared `AudioContext` and a bus graph:
master → {interface, notification, jarvisVoice} gain nodes. Sounds are
pre-decoded into buffers. Fewer than 30 KB per sound for UI cues. The engine is
lazy-loaded after first interaction.

## 5. Sound settings panel

Remembered per user once sign-in exists (Stage 2), and per device before that.

- Master volume.
- Interface, notification and JARVIS voice volumes.
- Category toggles: system, interface, typing, notification, feedback, alert,
  JARVIS cues.
- **Presets:**
  - **Immersive** (default): all categories, typing subtle.
  - **Balanced:** no typing, interface at half level.
  - **Quiet:** only alerts and JARVIS voice, at reduced level.
- Mute all (keyboard shortcut and header control).
- Preview buttons for every sound and for each candidate JARVIS voice.
- **Autoplay:** the `AudioContext` is created or resumed only after a user
  gesture. Because browsers block audio before interaction, the **startup sound
  plays on the first interaction (for example the sign-in press)**, never on
  page load.
- **Accessibility:**
  - Sounds never carry information alone. Every sound has a visual equivalent.
  - The "reduce motion" setting does not mute audio, but a separate "reduce
    sound" option follows Quiet.
  - The OS mute and silent switch are respected. Mobile web cannot override
    the iPhone silent switch for Web Audio, and we will not try.

## 6. JARVIS visual states (built in Stage 12 on the Stage 3 components)

| State | Visual |
|-------|--------|
| Off | Emblem idle, microphone icon struck through |
| Standby (wake word armed) | Small steady gold ring and "Wake word on" label |
| Listening | Live waveform from the microphone `AnalyserNode` and an ice-blue pulse |
| Processing | Orbiting gold arc, distinct from listening |
| Speaking | Waveform driven by the TTS output analyser, synchronised where the browser exposes output audio |
| Muted | Voice-off icon, and text responses only |
| Error / offline | Amber state, plain-language message and retry |

Reduced or off motion replaces waveforms with a static level meter and text
labels. The brand stays AVEN GLOBAL. "2050-inspired" is a styling direction
only.

## 7. How the confirmed decisions fit the existing requirements

| Existing requirement | Confirmed decision | Resolution |
|----------------------|--------------------|------------|
| Optional wake word, only where feasible and privacy-safe (master §11) | `WAKE_WORD` | The wake word is the primary hands-free mode. It is on-device, opt-in with consent, foreground-only on web, and push-to-talk is always available. |
| No continuous recording without explicit consent (master §11) | `WAKE_WORD` | Detection is on-device with no retention. Consent is recorded. Only the post-detection utterance is sent. |
| Sounds subtle and non-disruptive; typing very subtle (master §6) | `IMMERSIVE` | Immersive is the richest preset but follows the restraint rules in §4. Quiet is available. |
| Audio never required for use (master §6) | `IMMERSIVE` | Every function works muted. Every sound has a visual equivalent. |

## 8. Acceptance criteria (testable)

IDs are referenced in `USER_ACCEPTANCE_TESTS.md` (Stage 14).

**Wake word**

- **WW-01:** A fresh user has the wake word off. No microphone permission is
  requested until the user enables it or presses push-to-talk.
- **WW-02:** Enabling the wake word shows the consent screen. Declining leaves
  it off. Accepting creates an audit entry (user, device, time).
- **WW-03:** In standby, a network capture for 10 minutes shows **zero** audio
  bytes sent. Spoken non-wake phrases trigger nothing.
- **WW-04:** The wake phrase triggers the activation cue and the Listening state
  within 500 ms (desktop Chrome reference machine).
- **WW-05:** False accepts are ≤ 1 per 10 hours of mixed office audio and TV
  playback on the reference set. False rejects are ≤ 10% across a speaker set
  that includes Malawian-English accents.
- **WW-06:** The stop control ends capture: every track is `readyState ===
  "ended"`, the browser indicator disappears, and the state shows Off within
  200 ms.
- **WW-07:** Backgrounding on iOS/Android and returning shows a "Wake word
  paused" state. No claim of background listening appears anywhere in the UI.
- **WW-08:** Unsupported capability (no WASM, AudioWorklet or permission)
  falls back to push-to-talk with an explanation.

**Microphone permissions**

- **MP-01:** Denied permission shows recovery instructions per browser and
  never loops prompts.
- **MP-02:** Revoking permission mid-session moves to Off with a message, with
  no crash.

**Voice**

- **VO-01:** The Director can preview every candidate voice and the choice
  persists across sessions and devices.
- **VO-02:** Speed and voice volume changes apply to the next utterance, within
  bounds of 0.8–1.25×.
- **VO-03:** Stop speaking halts audio within 150 ms. Push-to-talk during
  speech interrupts and starts listening.
- **VO-04:** A TTS provider failure falls back to an on-screen text response
  with an error notice.

**Sound controls and accessibility**

- **SC-01:** No sound plays before the first user gesture. This is verified in
  Chrome, Safari and Firefox with autoplay policies at default.
- **SC-02:** Master, interface, notification and voice volumes and each
  category toggle affect only their own sounds.
- **SC-03:** Mute all silences every sound immediately, including a sound
  already playing.
- **SC-04:** Presets apply the documented levels, and the choice persists.
- **SC-05:** Every audible event has a visual equivalent. All core tasks pass
  with audio muted.
- **SC-06:** Typing feedback never exceeds 1 tick per 90 ms, and the sound
  engine adds < 2 ms main-thread time per event (performance trace).
- **SC-07:** A licence record exists for every audio file in the build (CI
  check against `AUDIO_LICENCES.md`).

**Security**

- **SV-01:** A voice command for a restricted action (payment, approval,
  supplier bank change, payroll) never executes without on-screen confirmation
  by the signed-in user plus step-up authentication where the policy requires
  it.
- **SV-02:** A voice command for an action outside the user's permissions is
  refused with the same result as the typed equivalent, and is audit-logged.
- **SV-03:** Audio clips are not persisted server-side after transcription
  (storage inspection). Transcripts follow the retention policy.

**Platform compatibility** (run on real devices)

- **PC-01:** Windows 11 with Chrome and Edge, macOS with Safari and Chrome,
  iOS Safari and installed PWA, and Android Chrome and installed PWA. Each must
  pass WW-01–08 and SC-01–05 within the documented limits in §3.3.

## 9. Open decisions for the Director

1. ~~Wake-word engine~~: **decided: Porcupine, paid licence; AccessKey
   supplied at the end of development.**
2. Wake phrase (trained in the Picovoice Console once the licence exists).
3. TTS provider shortlist for the CINEMATIC voice auditions.
4. Audio source: in-house synthesised sounds or a commissioned sound designer.

<!-- Director-confirmed JARVIS design specification, received 2026-11-12. Verbatim. -->

# AVEN GLOBAL JARVIS: CONFIRMED DESIGN SPECIFICATION

Update the existing AVEN GLOBAL project instructions and build specification using the following confirmed decisions.

## 1. Official design decisions

- Voice profile: `CINEMATIC`
- Activation mode: `WAKE_WORD`
- Sound profile: `IMMERSIVE`

These are confirmed product requirements, not suggestions or temporary placeholders.

## 2. JARVIS cinematic voice

Design JARVIS with an original, premium, deep male-sounding executive voice.

Voice characteristics:
- Deep, rich and composed.
- Intelligent, articulate and naturally conversational.
- Confident and authoritative without sounding robotic.
- Professional executive butler personality.
- Subtle dry humour and occasional clever sarcasm when appropriate.
- Clear pronunciation and natural pauses.
- Adaptable delivery for briefings, alerts, conversations and urgent situations.

Do not imitate a specific actor, celebrity, fictional character or copyrighted voice. Use an original voice identity.

Provide configurable speech speed and volume. Allow the Director to preview available voices before selecting one.

## 3. Wake-word activation

Implement an optional wake-word system for hands-free interaction.

Requirements:
- Let the Director configure and enable or disable the wake word.
- Provide a clear microphone/listening indicator.
- Support manual push-to-talk as an alternative.
- Include an immediate microphone stop control.
- Do not record or retain conversations unnecessarily.
- Do not transmit audio continuously without appropriate consent.
- Require explicit authentication and permission checks before executing commands.
- Voice recognition alone must never authorise payments, financial approvals, sensitive employee actions or other restricted operations.

Important technical requirement:

Investigate actual wake-word and microphone capabilities across supported browsers, Windows, macOS, iOS and Android. Do not promise background or locked-screen listening where the platform does not permit it. Use a compatible native integration or supported platform capability when necessary. Clearly document limitations and fallback behaviour.

## 4. Immersive audio experience

Implement an original AVEN GLOBAL audio identity.

Include:
- Cinematic application startup sound.
- JARVIS activation and deactivation sounds.
- Subtle keyboard and typing feedback.
- Navigation and module-opening sounds.
- Notifications and incoming-message sounds.
- Approval and task-completion feedback.
- Distinct but restrained urgent alert sounds.
- Voice interaction start, processing and response cues.

Audio must feel premium, futuristic and restrained. Avoid excessive noise, repetitive effects or distracting sound.

Use original audio or properly licensed assets. Never extract or reproduce copyrighted movie soundtracks, dialogue or film sound effects.

## 5. Audio settings

Build a dedicated sound settings panel with:
- Master volume.
- Separate interface, notification and JARVIS voice volume.
- Enable/disable individual sound categories.
- Immersive, balanced and quiet presets.
- Sound preview controls.
- Mute all.
- Remembered user preferences.
- Accessibility and reduced-motion compatibility.

Respect browser autoplay restrictions. Start audio only after an appropriate user interaction or permission.

## 6. Visual integration

JARVIS activation must integrate with the AVEN GLOBAL interface.

Create:
- A premium animated listening indicator.
- A distinct processing state.
- A speaking state with synchronized visual feedback where supported.
- Elegant waveform animations.
- Clear microphone and connection status.
- Restrained cinematic transitions.

Maintain the existing AVEN GLOBAL brand identity. The application and product name must remain AVEN GLOBAL. Futuristic 2050-inspired styling is a visual direction only, never part of the official product name.

## 7. Security and execution

All JARVIS commands must follow the existing secure execution architecture:

Authentication → permission verification → command interpretation → validation → approval where required → execution → audit log.

JARVIS must never:
- Bypass user permissions.
- Execute arbitrary SQL.
- Circumvent financial approvals.
- Initiate unauthorised payments.
- Modify supplier bank details without approval.
- Submit tenders without human approval.
- Impersonate employees.
- Perform restricted actions based solely on a recognised voice.

## 8. Documentation and implementation

Update the following project documents where applicable:

- CLAUDE.md
- docs/architecture/AI_ARCHITECTURE.md
- docs/architecture/VOICE_AND_SOUND.md
- docs/architecture/DESIGN_SYSTEM.md
- docs/security/SECURITY_MODEL.md
- ROADMAP.md
- PROJECT_STATUS.md

Add testable acceptance criteria for wake-word behaviour, microphone permissions, voice settings, sound controls, audio accessibility, security and platform compatibility.

Do not silently remove existing requirements or overwrite previous approved architecture.

## 9. Current execution instruction

This is a specification update only.

Inspect the existing repository and relevant project documents. Update the documentation, identify any technical constraints, and report exactly what changed.

Do not begin the next development stage, write unrelated application code, deploy, or change production infrastructure.

Present the updated documents and wait for the Director's approval.
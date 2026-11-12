# JARVIS AI architecture

- Status: **Specification approved 2026-11-12. Not implemented** (JARVIS AI core is Stage 11; voice
  is Stage 12).
- Sources: Stage 0 §4B and §6, master instructions §10–§11, `docs/jarvis-design-specification.md`
  and `docs/director-stage-plan.md`.

## 1. Components

```text
Browser (text / push-to-talk / wake word)
   │  HTTPS + WebSocket, authenticated session
   ▼
API  /api/v1/jarvis/*
   ├── ConversationService      conversation + message history (PostgreSQL)
   ├── AIProvider (interface)   AnthropicProvider (Claude) — swappable
   ├── ToolRegistry             typed tools that wrap business services only
   ├── ActionGateway            auth → permission → validation → rules → approval → execute → audit
   ├── ApprovalService          human confirmation + step-up auth for sensitive actions
   ├── AIUsageLedger            tokens, cost, latency per request/user
   └── AuditLog                 every tool call (inputs, decision, outcome)
   │
   ├── SpeechToTextProvider (interface)   used only after push-to-talk / wake word
   └── TextToSpeechProvider (interface)   CINEMATIC voice, streaming
```

- **System prompt:** `backend/app/ai/prompts/jarvis_personality.md`
  (Director-supplied), plus a generated context block containing the user's
  name, role, permissions summary, current date and time in Africa/Blantyre,
  and base currency.
- **Provider abstraction:** the business code never imports a vendor SDK
  directly. Keys live in server environment secrets only.

## 2. Tool rules

- Tools call **backend business services**. They never use SQL, never use ORM
  sessions directly, and never call raw HTTP to internal services.
- Each tool declares a category: **read**, **prepare** (creates drafts only) or
  **execute** (changes state).
- Each tool also declares the permission it needs, an input schema (Pydantic),
  and whether it needs approval.
- Results are filtered by the caller's permissions **before** they reach the
  model. The model never sees data the user could not see.
- **Only tools whose module exists are registered.** The initial tool list in
  the Director's plan is gated on Stages 4–10.
- Never permitted, by any tool: initiating payments, changing supplier bank
  details, submitting tenders, approving its own requests, or bypassing
  approvals.

## 3. Execution chain (identical for text and voice)

1. **Authentication:** a valid session, and the user is not suspended.
2. **Permission:** a role or individual grant exists for the tool's
   permission.
3. **Interpretation:** the model proposes a tool call. A low-confidence or
   ambiguous intent produces a clarifying question, never a guess.
4. **Validation:** the schema and the referenced records exist and are visible
   to the user.
5. **Business rules:** the module service enforces the domain rules.
6. **Approval:** for sensitive actions, an on-screen confirmation card is
   required. Step-up authentication is required where the policy says so. A
   voice match alone is never enough.
7. **Execution:** done through the service, in a transaction.
8. **Audit:** a record is written with who, what, inputs, decision, outcome,
   AI request ID and cost.

JARVIS reports only outcomes the system has confirmed, as the personality rule
"never claim an action succeeded until the system confirms it" requires.

## 4. Messaging integrity

Messages that JARVIS sends to staff are labelled **"Sent by JARVIS on behalf of
<user>"**. They are distinct from messages the Director sends personally.
JARVIS never impersonates an employee.

## 5. Daily briefing (Director decision, 2026-11-12)

JARVIS briefs the Director, as the personality file's briefing priorities
require.

- **Text:** a serif reading view with sections for important developments,
  financial position, outstanding customer payments, tender deadlines,
  procurement, staff activity, pending approvals and recommended actions.
- **Voice:** a spoken version in the CINEMATIC voice (Stage 12).
- **Delivery:** on request ("JARVIS, brief me"), and optionally as a
  scheduled morning briefing.
- **Content rules:** every figure states its period and currency. Sections
  with no recorded data say so instead of guessing.

## 6. Task-execution visualisation (Director decision, 2026-11-12)

While a tool runs, the ActionGateway emits progress events over the
WebSocket: `interpreting`, `permission_ok`, `validated`,
`awaiting_approval`, `executing`, `audited`, `failed`.

The JARVIS interface shows:

- the JARVIS core connected by animated lines to the module or record being
  used
- a node chain that lights up step by step as each **real** event arrives

A failure or refusal shows on the exact node where it stopped. The animation
never runs ahead of the backend, never shows success before `audited`, and
reduces to a plain step list at Reduced or Off motion.

## 7. Naming note

"JARVIS" is the assistant name chosen by the Director. Because the name is
widely associated with an existing fictional character, the voice and visuals
must stay original, and **a trademark or legal check of the assistant name is
recommended before commercial launch** (Stage 14 checklist item). The product
name is, and remains, AVEN GLOBAL.

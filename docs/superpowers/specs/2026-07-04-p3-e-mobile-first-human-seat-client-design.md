# P3-E Mobile-First Human Seat Client Design

> Status: **DESIGN — brainstorm approved, implementation not started**  
> Date: 2026-07-04  
> Scope: mobile-first Flutter client information architecture, live room UX, human-seat action UI, P3-E-1 protocol spike boundary  
> Decision: **IA + Composer Rail MVP first, with a thin participant protocol spike**

---

## 1. Context

P3-C has completed the backend foundation for a profile-driven single human seat:
one seat can be configured with `provider="human"`, can map to any current role,
and is driven by server-owned participant action windows instead of an AI provider.

P3-E now needs a mobile-first client direction before implementation. The client
must not become a Qt observer port, a god-view replay surface, or a pure technical
protocol demo. The first mobile product shape should make the human player feel
seated in a live AI Werewolf room, with enough information to participate but no
hidden data leaks or assistant-style deduction hints.

This design builds on the P3-E route decision:

- Flutter-first cross-platform client.
- Qt/QML remains legacy until parity.
- Backend protocol retained.
- New UI does not inherit the old parchment/storybook/tabletop visual direction.

---

## 2. Product Decision

Build the first P3-E mobile client around **IA + Composer Rail MVP**.

The first slice prioritizes the player-facing information architecture:

- role-safe live room;
- natural speech feed;
- collapsible bottom action composer;
- human action-window rendering;
- reconnect recovery;
- a thin Flutter protocol spike that proves these structures can run against the
  existing observer/participant REST + SSE boundary.

This explicitly rejects two weaker routes:

- **Protocol-only demo first:** too likely to produce a debug UI that later gets
  thrown away.
- **Full static visual prototype first:** too likely to design beyond the current
  participant protocol and delay the first real mobile loop.

---

## 3. First-Slice User Model

The primary user is a **single human player sitting in one AI game seat**.

First slice assumptions:

- The backend profile already marks one seat as `provider="human"`.
- The phone joins or resumes that bound human seat.
- The phone does not choose providers, edit profile seat providers, read local run
  artifacts, access provider keys, or request god-view state.
- All actions come from server-owned `open_action_window`.
- The client renders only participant-authorized state and submits candidate
  actions.

Future seat picking is preserved in the IA, but not required for the first
implementation. When multi-human play exists, a seat picker can be inserted
between join and identity confirmation.

---

## 4. Entry And Seat Flow

### 4.1 Connect

The first mobile slice is a local/LAN product:

- The user manually configures the observer base URL.
- No account system, matchmaking, cloud lobby, push notification, or automatic
  server discovery is required.

### 4.2 Join Or Resume

The user enters a join code or local development token. The server resolves the
single profile-bound human seat.

The mobile app must not modify the backend profile or infer the human seat from
local files.

### 4.3 First Identity Confirmation

First join shows a strong identity confirmation screen:

- controlled seat, such as `P3`;
- public persona/seat label when available;
- true role only when that is legal for the participant to know;
- current run state;
- a short boundary reminder that this is a participant perspective, not god view.

This screen is intentionally confirmatory and ceremonial. It prevents the player
from entering the room with the wrong mental model.

### 4.4 Reconnect

Reconnect does not show a blocking identity page.

When SSE drops, the app resumes from `GET participant/state`, shows a lightweight
status such as "已回到 P3 视角", and returns to the live room. If the server returns
an `open_action_window`, the Composer Rail restores the matching input or selection
state. Only an invalid/expired participant session returns the user to join/resume.

---

## 5. Live Room Information Architecture

The live room is the core page. It is not a compressed god-view theater; it is the
phone surface for a player seated in the match.

### 5.1 Top Role-Safe Status Bar

The status bar may show:

- current phase;
- public alive count;
- the player's own seat and legal identity information;
- public flow position, such as discussion, voting, or night;
- connection state, such as connected, reconnecting, or restored.

The status bar must not reveal invisible action ownership. During night, a villager
or unrelated role sees safe state such as "夜间行动中" or "等待其他玩家行动", not which
seat is acting. Role-specific information appears only inside that participant's
legal action window or legal private state.

### 5.2 Natural Speech Feed

The speech feed is the main room surface.

Rules:

- Use a chat-like chronological feed for readability.
- Show speaker seat/persona clearly.
- Distinguish the human player's own speech without making it look like a debug
  log.
- Keep public history readable during night waiting.
- Render player/AI text as untrusted game data only.

### 5.3 Subtle Semantic Highlighting

The feed may highlight text for scanability and visual quality:

- `P1` through `P6` seat mentions can be bold or lightweight chips.
- Role terms such as `狼人`, `预言家`, `女巫`, `猎人`, `守卫`, `村民` can use stable role
  colors.

These highlights mean only "this word appeared in visible text." They must not
imply that the role claim is true, that a hidden identity is known, or that the UI
has performed deduction.

### 5.4 Public Rule Events Only

The feed may naturally insert true public rule events:

- phase changed;
- voting started or ended;
- public death/execution;
- final words;
- public win/end state.

The feed must not insert coaching-style blocks:

- no accusation summaries;
- no vote-intention summaries;
- no contradiction hints;
- no "重点插入";
- no assistant-style advice about which speech matters.

The player should feel table pressure from the conversation, not UI pressure from
deduction hints.

---

## 6. Composer Rail

The Composer Rail is the bottom participant action surface. It looks and feels like
an elegant chat composer, but it is a structured renderer for server action windows.

It must not parse free text into game actions. It renders `open_action_window` and
submits explicit payloads.

### 6.1 States

#### Collapsed

The rail hides at the bottom and leaves only an upward handle. This maximizes
speech-reading space. Collapsing the rail is a view choice, not a pass or timeout.

#### Idle Text Composer

For `speech` and `final_words`, the rail shows a small bottom input bar similar to
modern iOS/ChatGPT-style mobile input. It occupies minimal vertical space before
focus.

#### Keyboard Editing

When the player focuses the input, the keyboard raises the composer. The input area
plus keyboard should occupy about the lower third of the screen, while recent speech
context remains visible above.

#### Structured Selection

For votes and role actions, the rail becomes a structured selector:

- legal seat targets;
- action choices such as save, poison, pass, or confirm;
- submit/confirm controls;
- optional pass only when the server marks the window passable.

The selector should remain compact when possible. It is not a half-screen modal by
default.

### 6.2 Action Mapping

| Action type | Mobile Composer Rail |
|---|---|
| `speech` | Text composer + submit |
| `response` | Protocol reserved; first mobile slice waits for P3-B table-talk rules |
| `vote` | Lightweight vote drawer with legal targets + confirm |
| `final_words` | Optional text composer + skip/pass when legal |
| `pass` | Explicit pass only when legal for the current window |
| `werewolf_kill` | Legal target selection + confirm |
| `seer_check` | Legal target selection + confirm |
| `witch_save` | Save / do not save choices from server window |
| `witch_poison` | Legal target selection or pass from server window |
| `guard_protect` | Legal target selection + confirm |
| `hunter_shoot` | Legal target selection or pass when legal |

### 6.3 Submit Semantics

Every submit must include:

- `action_window_id`;
- `game_revision`;
- `idempotency_key`;
- `action_type`;
- action-specific payload.

Duplicate, stale, closed, conflict, and illegal-action responses should be displayed
inside the Composer Rail and recovered through `participant/state`, not by leaving
the live room.

---

## 7. Phase-Specific Experience

### 7.1 Day Speech

The live room remains on the speech feed. When it is the human player's turn, the
Composer Rail becomes a text composer. The first slice has no time pressure.

### 7.2 Night Waiting

Night waiting keeps the room readable. The player can review public history and
legal private information, while the status bar shows a role-safe night state.

The UI must not show which invisible seat is acting.

### 7.3 Night Action

When the human player's role has a legal night action, the Composer Rail changes
to a private structured selection state. The action area shows only legal targets
and legal role information.

### 7.4 Voting

Voting stays in the live room. The Composer Rail becomes a lightweight voting
drawer with legal targets and explicit confirmation.

Vote counts/results are shown only if the rules/server expose them publicly. The
UI does not infer or summarize vote intention.

### 7.5 Final Words

When death or execution opens a legal final-words window, the rail offers a small
optional final-words composer. The player can write or skip. Submitted final words
enter the public feed as game text.

### 7.6 Timeout And Timed Mode

The first slice defaults to **no time limit** for human actions. The UI may show
"等待你操作" or "无时间限制"; it should not design around countdown pressure.

Timed mode is a future host/setup option. When enabled later, deadlines and timeout
policy can be shown in the status bar and Composer Rail.

---

## 8. Visual Direction

The mobile client should use a **high-contrast dark social deduction** direction
with an Apple-style product feel.

Principles:

- mature, tense, and readable;
- iOS-native clarity, tactile controls, smooth transitions, and refined spacing;
- elegant bottom input/composer behavior;
- restrained blur/material only where it improves hierarchy;
- comfortable rounded shapes without becoming playful or cute;
- role colors used for recognition, not as a one-note palette;
- no parchment, antique gold, storybook, fantasy tabletop, or board-game-demo
  framing.

The result should feel like a premium iPhone social deduction room, not a SaaS
dashboard, not a debug client, and not SillyTavern UI. SillyTavern is only a loose
reference for role-centered conversational participation.

---

## 9. P3-E-1 Protocol Spike Boundary

P3-E-1 should be a thin Flutter spike that proves the IA can run on the existing
observer/participant protocol.

Required capabilities:

- configure observer base URL;
- enter or select the current run in a first-slice way;
- join/resume the profile-bound human seat;
- call `GET participant/state`;
- render a role-safe top status bar;
- render a minimal natural speech feed;
- follow participant SSE;
- recover through reconnect cursor by reloading participant state;
- render Composer Rail states from `open_action_window`;
- submit at least `speech`;
- submit at least one structured action, preferably `vote`;
- handle duplicate/stale/closed/illegal errors without leaving the live room.

The spike UI may be visually simple, but it must preserve the final product skeleton:
status bar, speech feed, Composer Rail. It must not be a JSON viewer or a pile of
debug buttons.

---

## 10. Non-Goals

This design does not include:

- implementation code;
- full Flutter visual polish;
- Qt/QML changes;
- Qt parity;
- multi-human rooms;
- mobile seat picker implementation;
- account system;
- matchmaking;
- cloud lobby;
- mobile push notifications;
- provider credential management;
- direct provider calls from the client;
- local artifact reads from `.runs`;
- god-view participant state;
- deduction helpers, contradiction summaries, vote-intention summaries, or AI
  coaching.

---

## 11. Verification Strategy

### Docs-Only Verification

For this design document:

- changed files should stay under docs plus required tree metadata;
- no runtime, scoring, provider, validator, generated fixture, Qt/QML, Flutter, or
  workflow files should change;
- no tests are required because no executable behavior changes.

### Future Flutter Verification

For implementation:

- `flutter analyze`;
- `flutter test`;
- protocol tests with fake observer/participant responses;
- phone portrait screenshot checks for text overflow, Composer Rail states,
  reconnect state, and structured action state;
- desktop responsive screenshot checks once desktop target is introduced;
- local observer-server smoke for join/resume, participant SSE, speech submit,
  vote or structured action submit, and reconnect recovery.


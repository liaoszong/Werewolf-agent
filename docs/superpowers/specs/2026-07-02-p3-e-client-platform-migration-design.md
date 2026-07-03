# P3-E Client Platform Migration Design

> Status: **DESIGN — route decision locked**  
> Date: 2026-07-02  
> Scope: client platform, UI direction, migration boundary  
> Decision: **Flutter-first client rewrite + Qt legacy until parity + backend protocol retained**

---

## 1. Context

The project has already proven the backend foundation: a Python Werewolf engine, event-sourced logs, strict visibility projections, local observer server, REST/SSE protocol, and a Qt spectator client. The product problem has moved from "can we run and observe a full AI-vs-AI match?" to "is this match interesting enough for people to watch and join?"

Current UI feedback is clear:

- The Qt client feels simple and low-texture.
- The current storybook / parchment / fantasy-tabletop direction reads too fairy-tale.
- Desktop-only play is too much friction for most players.
- The future product needs humans to join as real seats, not only watch AI agents.

P3 therefore needs a product-surface pivot as well as an Agent-layer pivot. Richer agents make the game more interesting; a mobile-first participant client makes it playable.

---

## 2. Decision

Build the next client as a **Flutter-first cross-platform app**.

Retain the Python backend, game engine, provider gateway, observer server, REST/SSE event stream, visibility projection, logs, and invariant safety net. The client migration must not rewrite the game core.

Treat the existing Qt/QML client as **legacy until parity**:

- Keep it available for current desktop observing, demos, and maintenance.
- Apply only critical fixes or low-risk compatibility updates.
- Do not invest further in the parchment/storybook visual direction.
- Do not add major new human-participant UX only to Qt unless a migration blocker forces it.

Flutter becomes the default target for new player-facing UI, especially mobile and human-seat flows.

---

## 3. Framework Evaluation

| Candidate | Fit for this product | Decision |
|---|---|---|
| **Flutter** | Strong mobile-first app framework with stable desktop targets. Good fit for custom visual systems, animation, touch-first game UX, and one codebase across phone + desktop. Official docs cover desktop compilation for Windows/macOS/Linux and Flutter's broader mobile/web/desktop support. | **Choose as default.** |
| **Tauri v2** | Excellent desktop story: small, fast, secure, web-stack friendly, and v2 supports Android/iOS. Risk: mobile WebView app feel, mobile tooling maturity, and web rendering consistency are weaker fits for a premium social game client. | Keep as fallback if web stack or tiny desktop package becomes the overriding goal. |
| **Electron** | Mature desktop app shell, huge web ecosystem, stable rendering target through bundled Chromium. It does not solve mobile and carries desktop package/runtime weight. | Reject for this phase. |
| **Avalonia** | Strong cross-platform .NET UI option with desktop/mobile/WebAssembly support. Risk: mobile support tiering, .NET/MAUI lifecycle complexity, smaller mobile-first consumer app ecosystem. | Reject unless the project becomes .NET-centered. |
| **React Native / Expo** | Excellent mobile-native route, with native iOS/Android UI components and a mature app ecosystem. Desktop support exists through partner/community out-of-tree platforms. | Reject for this phase; desktop parity is a hard requirement. |
| **Qt/QML evolution** | The most conservative project-local option: keep Qt, redesign the visuals, and investigate Qt mobile. It avoids a second client stack but keeps the project inside the current QML surface, mobile deployment/UX risk remains high, and the existing storybook direction is already deeply embedded in Qt assets and components. | Reject as the primary route. Keep Qt as legacy/developer surface until Flutter reaches parity. |

Primary external references:

- Flutter desktop support: <https://docs.flutter.dev/platform-integration/desktop>
- Flutter FAQ: <https://docs.flutter.dev/resources/faq>
- Tauri v2: <https://v2.tauri.app/>
- Avalonia supported platforms: <https://docs.avaloniaui.net/docs/supported-platforms>
- Electron: <https://www.electronjs.org/>
- React Native: <https://reactnative.dev/>
- React Native out-of-tree platforms: <https://reactnative.dev/docs/out-of-tree-platforms>
- Qt mobile app development: <https://www.qt.io/development/multiplatform-mobile-app-development>
- Qt for Android documentation: <https://doc.qt.io/qt-6/android-getting-started.html>

---

## 4. Architecture Boundary

The migration is a client rewrite, not a backend rewrite.

```text
Python game runtime
  - engine
  - action runtime
  - provider gateway
  - visibility projection
  - event log / snapshots / invariants
        |
        | REST + SSE / future participant action endpoints
        v
Flutter client
  - mobile-first player app
  - desktop app from the same product surface
  - observer view
  - human-seat action windows
  - role/agent presentation
```

Hard boundaries:

- The client never calls model providers directly.
- The client never reads local `.runs` artifacts to fake a seat view.
- The client never receives god-view state when controlling a non-god human seat.
- All human actions go through server-issued action windows, session tokens, idempotency keys, and reconnect cursors.
- User speech, AI speech, memory summaries, Agent Cards, and retrieved playbook text are always rendered as untrusted data. The client must not execute them as code, dynamic UI templates, scripts, provider instructions, or local commands.
- Existing event logs remain the audit source of truth.

Desktop packaging can later choose between launching a local Python observer process or connecting to a remote/lobby server. Mobile should be designed as a network client from the start; embedding Python into the mobile app is not a P3 goal.

### P3-E-2/3 Network Scope

The first mobile slices are local-network products, not cloud products.

Scope for P3-E-2/3:

- A desktop or developer machine runs the Python observer server.
- The phone connects over the same LAN by manually configured base URL.
- No account system, matchmaking, cloud lobby, push service, or room-code discovery is required for the first slice.
- API cost belongs to the server/provider configuration that runs the match.
- If the app is backgrounded, the first slice relies on in-app countdowns, reconnect, and server timeout policy. Real mobile push notification is a later decision.

---

## 5. UI Direction Reset

The existing visual direction is retired for new work.

Deprecated direction:

- storybook tabletop theater
- warm parchment as the dominant surface
- candlelit fantasy room art
- antique gold hairlines
- cute/fantasy role medallions as the core identity language

New direction:

- mobile-first social deduction theater
- mature, tense, high-contrast game room
- identity pressure, suspicion, alliance, accusation, and deception as first-class UI material
- modern dossier / case-room / live broadcast language rather than fairy-tale board game language
- tactile but not cute; dramatic but readable

This spec does **not** lock final page layouts. Each page family must be redesigned separately before implementation:

- Home / entry
- Lobby / seat selection
- Match setup / host controls
- Live game room
- Human seat action panel
- Night private-action flow
- Day speech / response / voting flow
- Agent card / role card editor
- Settlement / replay / "why this game was interesting" recap
- Settings / provider credentials / local server connection

---

## 6. Migration Plan

### P3-E-0 Route Decision

Document the client-platform pivot and deprecate the old visual direction.

Acceptance:

- `PROJECT_MAP.md` names P3-E as the cross-platform participant client migration.
- `DESIGN.md` says the parchment/storybook style is legacy, not the target for new UI.
- This spec records Flutter-first, Qt legacy until parity, and backend protocol retained.

### P3-E-1 Flutter Protocol Spike

Create the smallest Flutter app that connects to the existing observer server.

Acceptance:

- App can configure observer base URL.
- App can list runs and follow one run's SSE stream.
- App renders a minimal live room from public/god projection without local artifact reads.
- Protocol risk probe: if the P3-C-0 server action protocol stub exists, the app can submit a trivial test action and render accepted/rejected; if it does not exist, P3-E-1 records P3-C-0 as the explicit blocker for P3-E-3.
- No product-level human-seat UI yet.

### P3-E-2 Mobile-First Live Room Slice

Design and implement the first real mobile live-room experience.

Acceptance:

- Phone portrait is the primary layout.
- Desktop is a responsive expansion, not a separate product.
- AI-vs-AI observing is usable enough to replace the Qt theater for basic watching.
- Visual direction no longer resembles parchment/storybook fantasy.

### P3-E-3 Human Seat Slice

Implement the first local human villager seat on the Flutter client.

Preconditions:

- P3-C-0 server action protocol spec is accepted.
- Minimal server action-window endpoints exist for the villager slice.

Acceptance:

- Human can observe only their legal information set.
- Human can speak, respond, vote, leave final words where allowed, time out, reconnect, and resume.
- Server controls action windows and rejects stale or duplicate submissions.

### P3-E-4 Desktop Parity And Qt Retirement Gate

Reach enough parity to stop treating Qt as the default player app.

Player parity:

- Start or attach to a local match.
- Observe live game state.
- Configure at least the common AI-vs-AI setup path.
- Join as the first supported human seat.
- View settlement and replay summary.

Developer/tooling parity:

- Inspect evidence, event history, and AI reasoning/provider traces at least as well as the current Qt debug surfaces needed for P3/P4 work.
- Manage provider credentials and common local server connection settings.
- Preserve a desktop packaging/update answer for normal testers, or explicitly keep Qt as the desktop distribution tool until this exists.

After player parity only, Qt can stop being the default player surface but must remain as a developer/power-observer tool. Archiving or removing Qt requires developer/tooling parity or a separate explicit decision.

---

## 7. Design Workflow For Pages

Every major page redesign needs its own short brief before implementation.

The brief must answer:

- Who is using this page: observer, human player, host, or developer?
- What action must be obvious in the first 5 seconds?
- What state changes in real time?
- What information is hidden from this user?
- What is the phone portrait layout?
- What is the desktop expansion?
- What mood should this page create?

Visual exploration is required before coding. It may use generated references, screenshots, Figma, sketches, or static mockups, but the final implementation must be checked against rendered screenshots on phone and desktop sizes.

---

## 8. Non-Goals

- Do not rewrite the Python engine in Dart.
- Do not replace the observer protocol with direct database or artifact reads.
- Do not ship multiplayer accounts, matchmaking, or cloud hosting as part of the first migration slice.
- Do not lock final page UI in this spec.
- Do not continue the old fairy-tale/parchment design language for new product surfaces.

---

## 9. Verification Strategy

Docs-only verification for P3-E-0:

- Confirm changed files are limited to route/design docs, the new spec, and generated tree metadata.
- Confirm no `src/**`, `tests/**`, `clients/**`, provider, runtime, validator, fixture, or workflow files changed.

Future Flutter verification:

- `flutter analyze`
- `flutter test`
- protocol client unit tests against fake observer responses
- screenshot/golden checks for phone portrait and desktop layouts
- integration smoke against deterministic fake games

Qt verification remains necessary only when touching legacy Qt/QML files.

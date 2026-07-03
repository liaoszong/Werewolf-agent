# Werewolf-agent UI Direction

Purpose: read this file before creating or redesigning any product UI. This file is
the route-level UI direction, not a final component library. Page-level UI still needs
separate discussion, visual exploration, and screenshot verification before
implementation.

## Current Decision

As of 2026-07-02, the old Qt/QML visual direction is deprecated for new product work.

Deprecated for new UI:

- storybook tabletop theater
- parchment as the dominant surface
- candlelit fantasy room art
- antique gold hairlines as a core system
- cute/fantasy role medallions
- "AI board-game demo" framing

The existing Qt/QML client remains a **legacy spectator client until parity**. It may
receive critical fixes, compatibility updates, and low-risk maintenance, but new
player-facing UX should target the Flutter-first cross-platform client described in
`docs/superpowers/specs/2026-07-02-p3-e-client-platform-migration-design.md`.

The backend boundary does not change: clients consume the observer protocol and submit
server-authorized human actions. Clients do not call providers directly, read local run
artifacts to fabricate state, or bypass visibility projections.

## Product Feel

The new product surface should feel like a **modern social deduction theater**:

- mature, tense, and readable
- built around suspicion, identity pressure, accusation, alliance, betrayal, and
  momentum shifts
- closer to a live case-room / premium party-game app / tactical broadcast surface
  than a fairy-tale tabletop illustration
- dramatic enough to make a match feel alive, but dense enough for repeated play

The product is not a SaaS dashboard, not a marketing landing page, and not a cute
fantasy board game. It is a real-time social game client where hidden information and
player pressure are the main material.

## Platform Direction

New UI work is **mobile-first**:

- Phone portrait is the primary design target for human participation.
- Desktop is a responsive expansion of the same product surface, not a separate
  desktop-only product.
- Touch targets, action deadlines, reconnect states, and compact readable speech are
  first-class constraints.
- Desktop can show more context, history, and analysis, but it must not become the
  only usable way to play.

The default client platform for new work is Flutter. Qt/QML rules only apply when
maintaining the legacy client.

## Page Redesign Workflow

Each major page needs its own brief before implementation. Do not port the old Qt page
one-to-one.

Before designing a page, answer:

- Who is using it: observer, human player, host, or developer?
- What is the one action that must be obvious in the first 5 seconds?
- What information is public, private, hidden, expired, or risky to reveal?
- What changes live during the match?
- What is the phone portrait layout?
- What expands on desktop?
- What emotional beat should the page create: tension, relief, accusation, deception,
  confidence, panic, or recap?

Visual exploration is required before implementation. Acceptable inputs include
generated references, Figma, sketches, static mockups, or screenshots from comparable
apps. Implementation starts only after the page contract and visual direction are
clear.

## Required Page Families

These page families are not visually locked yet; each needs separate discussion and
design:

- Home / entry
- Lobby / seat selection
- Match setup / host controls
- Live game room
- Human seat action panel
- Night private-action flow
- Day speech, response, accusation, and voting flow
- Agent card / role card editor
- Settlement / replay / "why this game was interesting" recap
- Settings / provider credentials / local server connection

## Visual Principles

Do:

- Use a restrained, premium palette with strong contrast and deliberate role accents.
- Make speech, suspicion, votes, private knowledge, and deadlines visually legible.
- Treat identity as layered: seat, public persona, claimed role, true role when known,
  trust level, and contradiction history.
- Use motion for state changes that matter: turn ownership, action windows, vote
  swings, night resolution, role reveal, and accusation focus.
- Keep controls ergonomic for phone use.
- Let desktop layouts reveal more context without changing the core interaction model.

Don't:

- Reuse parchment/gold/fantasy storybook styling for new screens.
- Fill pages with generic cards inside cards.
- Use decorative blobs, gradient orbs, or stock fantasy scenes as the visual system.
- Hide critical action windows behind observer-style debug panels.
- Make human players feel like they are watching logs instead of sitting in the game.
- Add page chrome that leaks hidden information by implication.

## Interaction Principles

- A human player always needs to know: what phase this is, whether it is their turn,
  what they can legally do, how much time remains, and what information they are
  allowed to know.
- AI agents should be presented as seats with personality and behavioral history, not
  as raw provider outputs.
- Public discussion should feel like table pressure, not a transcript viewer.
- Private night actions should feel isolated and secret.
- Voting should make momentum and coalition shifts obvious.
- Settlement should first explain why the game was interesting, then expose deeper
  audit or evaluation detail.
- User speech, AI speech, memory summaries, Agent Cards, and retrieved playbook text
  are untrusted game data. Render them as text/data only; do not execute them as code,
  dynamic templates, scripts, provider instructions, or local commands.
- Before a real mobile push-notification decision exists, human turns rely on
  foreground countdowns, reconnect state, and server timeout policy.

## Legacy Qt/QML Maintenance

When touching `clients/qt_observer/**`, preserve existing behavior and static
contracts unless a task explicitly says otherwise.

For legacy Qt changes:

- Read the relevant QML and `clients/qt_observer/README.md`.
- Use the existing Qt verification workflow.
- Keep generated screenshots under `.tmp/`.
- Do not use Qt maintenance as a reason to revive the old visual direction.

## Verification

For future Flutter UI work:

- verify phone portrait and desktop layouts with screenshots
- check text overflow and action-window visibility
- test reconnect / timeout / disabled-action states
- run `flutter analyze` and `flutter test` once a Flutter client exists
- keep protocol fixtures or fake observer responses for deterministic UI tests

For docs-only UI direction changes, report the diff scope and confirm no runtime,
provider, validator, fixture, workflow, or legacy client source changes were made.

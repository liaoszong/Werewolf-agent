# ADR: Role facts single-source — ruleset authoritative, protocol re-export

Date: 2026-06-11 · Status: Accepted

## Decision
- `action_runtime/ruleset.py` is THE declaration point for role→team facts: adding a role
  is one `RoleDefinition`. A new `known_role_teams()` returns the union over
  `all_rulesets()` (append-only registry) in declaration order, failing loud if a role
  ever maps to two teams.
- `observer_protocol` re-exports the derived `KNOWN_ROLE_TEAMS`. Observer-side modules
  (`observer_visibility`, `runtime_events`) import it from the protocol module ONLY —
  same R-06 discipline as `PUBLIC_LIKE_EVENT_VISIBILITIES` — and never import
  `action_runtime` directly. The three former verbatim copies
  (`profile_config.ROLE_TEAMS` / `observer_visibility._KNOWN_ROLE_TEAMS` /
  `runtime_events._KNOWN_ROLE_TEAMS`) are deleted in favor of derivation.
- `profile_config.ALLOWED_ROLES` stays an explicit hand-written product gate (new engine
  roles do NOT auto-appear in the launch UI; shipping a role to users is a product
  decision). Guarded by a subset sentinel (gate ⊆ ruleset roles).
  `profile_config.ROLE_TEAMS` becomes the gate-filtered projection of
  `known_role_teams()`, preserving declaration order (capabilities payload bytes).
- The two Chinese vocabularies stay physically separate — `prompt_v2` (村民/好人阵营,
  model-facing, golden-locked bytes) vs `display_labels` (平民/村民阵营, UI-facing).
  Coverage sentinels only: every role/team/ability in any ruleset must have an entry in
  each table. Never merge them.
- `NIGHT_DISPATCH_ORDER` stays engine data (subset sentinel only): night-order
  datafication is NightPlan (SYS-A1) and waits for the first new night role (guard),
  per PROJECT_MAP "不预建".

## Why ruleset-authoritative (not a standalone RoleCatalog layer)
A catalog module that owns role→team with `ruleset.py` deriving from it was considered
(external review suggestion) and REJECTED:
- Power inversion recreates the tax this ADR removes: adding a role would again require
  two mandatory touchpoints (catalog entry + RoleDefinition). Ontologically a role
  exists by being declared in a ruleset; its team is part of the win-condition rules
  (settler/scorer consume it). The rules data is the fact's birthplace.
- Deletion test: a standalone catalog is a pass-through — delete it and the complexity
  moves intact back into `ruleset.py`; nothing is concentrated.
- The protocol re-export already satisfies the legitimate concern behind the catalog
  (observer import surface unchanged) without the inversion. `action_runtime` is a pure
  data/function package; `observer_protocol` importing it creates no cycle (verified:
  `action_runtime` imports nothing outside itself).
- ADR-0001's client-agnostic boundary is the HTTP protocol layer (Qt/clients), not
  intra-package Python imports — all modules involved are server-side `werewolf_eval`.
- SYS-A4's dual-implementation witness covers visibility LOGIC, not constants. R-06
  already single-sourced shared constants across the two implementations ("so the
  filter can never drift apart"). A facts table duplicated per side is a drift vector,
  not a witness: a future wolf-side role missing from an observer copy would default to
  team "villager" and leak its role string to villager observers instead of "unknown"
  (`observer_visibility.py:413` / `runtime_events.py:478` both
  `.get(role, "villager")`). The single source makes that failure mode structural-impossible.

## Net
- Acceptance bar: byte-identical. `test_emergent_ledger_golden`, `test_rng_draw_order`,
  prompt_v1/v2 goldens, witch one-shot sentinels all pass unchanged; hunter boards too
  (hunter's team IS the lookup default "villager", so deriving it in is behavior-neutral).
- Permanent net: `tests/test_role_single_source.py` — derivation identity (`assertIs`),
  gate subset, night-order subset, vocab completeness ×6 tables. The completeness
  sentinels caught a real gap on arrival: `display_labels` had no hunter entries
  (R-28-class i18n gap), fixed additively in the same change.
- "Add a role" now = one `RoleDefinition` + genuinely-new behavior branches; every
  remaining table is either derived or sentinel-guarded, so the old 27-touchpoint
  checklist becomes executable tests.
- Implementation plan: `docs/harness/plans/2026-06-11--sys-a2-role-single-source-plan.md`.

# ADR — Layer observer visibility into trust-index / projection / artifact-enrichment with the trust boundary as the single audited surface

- **Status:** Accepted (user-approved health-check item B-4, 2026-06-11)
- **Deciders:** owner + agent (health-check `docs/health-check/03-architecture-optimization.md` §B-4)

## Context

`src/werewolf_eval/observer_visibility.py` (~935 LOC) is the **anti-leak security
boundary** behind `/projection`: it decides what each observer perspective
(`god` / `public` / `role:pN` / `team:werewolf`) may see. Today it mixes three
concerns in one file:

1. **Trust-source resolution** — `build_seat_role_index` (L100-310): which artifact
   backs each player's `role`/`team`/`alive` (`role_projection_snapshot` vs
   `god_snapshot` vs `unknown`), including latest-snapshot ordering and the
   "deaths are public, god snapshot is alive-authority" rule.
2. **Perspective projection** — `build_player_projection`,
   `event_visible_in_projection`, `project_events`, `project_snapshots`,
   `_build_proof` (L318-736, L892-935): the *enforcement* code that reads the
   `*_source` provenance tags and grants/denies field exposure per perspective.
3. **Artifact join + enrichment** — `_load_game_log_summaries`,
   `_load_decision_reasons`, `build_projection_envelope` (L744-889): joining
   game-log summaries and decision-log reasons onto already-filtered events,
   including the **private `reason_summary` actor gate** (god or the deciding
   player only).

The trust rules (what a non-god perspective may expose) are the hardest part to
audit, and they are interleaved with greedy decision-to-event matching and JSON
loader plumbing. Health-check B-4 rates this medium-risk precisely because any
split must preserve the exact visibility decisions.

**Witness structure that must survive (SYS-A4 / I4b, same constraint as the B-2
ADR):** the observer side is a *deliberate independent implementation* of
visibility — it checks the engines from the outside. The engine-side single source
is `role_visibility.py`; the sentinel test
(`tests/test_role_visibility.py::WitnessBoundarySentinelTest`) fails if
`observer_visibility.py`, `observer_protocol.py`, or anything under `invariants/`
ever mentions the string `role_visibility`. Splitting the observer file must not
open a side door around that sentinel: the new modules join the scanned witness
surface.

## Decision

1. **Split into three modules, one concern each; `observer_visibility.py` becomes a
   pure facade** (re-exports only, zero logic):

   - **`src/werewolf_eval/observer_trust_index.py`** — trust-source resolution.
     Verbatim move of `_PHASE_RANK`, `_snap_order`, `_SNAPSHOTS_DIR`,
     `build_seat_role_index`, `_find_player_role_in_god_snaps`,
     `_find_player_team_in_god_snaps`. This is the **only module that assigns
     provenance** (`role_source` / `team_source` / `alive_source`,
     `projected_known_roles` ownership). Imports no sibling visibility module.
   - **`src/werewolf_eval/observer_projection.py`** — perspective vocabulary +
     enforcement. Verbatim move of the contract constants (`CONTRACT_VERSION`,
     `ROLE_PERSPECTIVE_PREFIX`, `DEFAULT_PLAYER_IDS`,
     `ROLE_SPECIFIC_EVENT_VISIBILITIES`, the R-06 re-exports from
     `observer_protocol`), `VisibilityProjectionError`, `perspective_kind`,
     `is_werewolf_role`, `infer_player_ids`, `unknown_player`,
     `build_player_projection`, `event_visible_in_projection`,
     `_trusted_role_for_player`, `_trusted_team_for_player`, `project_events`,
     `project_snapshots`, `_snapshot_visible_to_projection`,
     `_build_detail_endpoint`, `_build_proof`. This is the **only module that
     reads `*_source` tags** to decide exposure (the trust boundary's enforcement
     half — `_build_proof` reads provenance too, so it lives here, not with the
     envelope). Imports `observer_protocol` (visibility sets, role-team table) and
     `observer_trust_index` (only `_SNAPSHOTS_DIR`).
   - **`src/werewolf_eval/observer_enrichment.py`** — artifact join + envelope.
     Verbatim move of `_load_game_log_summaries`, `_load_decision_reasons`,
     `build_projection_envelope`. It composes the other two layers
     (index → project → join) and owns exactly one perspective-sensitive rule: the
     private `reason_summary` gate (`kind == "god"` or deciding actor == self),
     which is an *actor-identity* gate, not provenance — now adjacent to the loader
     it guards. It must **never read snapshots or `*_source` tags directly**.
   - **`src/werewolf_eval/observer_visibility.py`** — facade. Re-exports the
     existing public surface unchanged (`CONTRACT_VERSION`,
     `ROLE_PERSPECTIVE_PREFIX`, `DEFAULT_PLAYER_IDS`,
     `ROLE_SPECIFIC_EVENT_VISIBILITIES`, `PUBLIC_LIKE_EVENT_VISIBILITIES`,
     `WEREWOLF_TEAM_EVENT_VISIBILITIES`, `VisibilityProjectionError`,
     `perspective_kind`, `is_werewolf_role`, `infer_player_ids`, `unknown_player`,
     `build_seat_role_index`, `build_player_projection`,
     `event_visible_in_projection`, `project_events`, `project_snapshots`,
     `build_projection_envelope`) **plus `_KNOWN_ROLE_TEAMS`** —
     `tests/test_role_single_source.py` asserts `assertIs` identity with
     `observer_protocol.KNOWN_ROLE_TEAMS`, which re-exporting the same object
     preserves. All current importers (`observer/handler.py`,
     `invariants/visibility_oracle.py`, `tests/test_observer_visibility.py`,
     `tests/test_visibility_parity.py`, `tests/test_observer_emergent_bridge.py`,
     `tests/test_emergent_role_projection.py`, `tests/test_role_single_source.py`)
     keep importing the facade with **zero changes**.

2. **The trust boundary is the single audited surface, stated as module
   invariants:** provenance is *assigned* only in `observer_trust_index.py` and
   *consumed* only in `observer_projection.py`; `observer_enrichment.py` joins
   public narration onto already-visible events and gates private reasons by actor
   identity only. Auditing "what can a non-god perspective expose" = reading the
   first two modules, with no artifact-join noise.

3. **Witness boundary stays locked and widens:** none of the new modules may
   import or mention `role_visibility`. The sentinel's scanned file list in
   `tests/test_role_visibility.py` is extended to include all three new modules
   (and the facade stays listed). The witness-boundary docstring in
   `role_visibility.py` is updated to name the new observer-side files
   (docstring-only edit, no code).

4. **Behavior-identical by construction and by proof:** function bodies move
   verbatim (only `import` lines and module docstrings change). Gates: full
   visibility test surface green (`test_observer_visibility.py`,
   `test_visibility_parity.py`, `test_role_visibility.py` incl. widened sentinel,
   `test_role_single_source.py` incl. cold import of the facade,
   `test_observer_emergent_bridge.py`, `test_emergent_role_projection.py`), plus a
   **before/after envelope byte-diff**: build `build_projection_envelope` output
   for every perspective (`god`, `public`, `role:p1..p6`, `team:werewolf`) against
   the same pre-generated fake-game run dir at the base commit and after the
   split; canonical-JSON bytes must be identical. `/projection` HTTP behavior is
   unchanged because the handler imports only `build_projection_envelope` +
   `VisibilityProjectionError` from the facade.

## Consequences

- The leak-relevant rules become auditable in isolation: ~210 lines of provenance
  assignment + ~480 lines of enforcement, with envelope/join plumbing out of the
  way; the private `reason_summary` gate sits next to its own loader.
- The sentinel surface grows from one observer file to four — drift of any layered
  module toward the engine-side single source is caught the same way.
- One new intra-package import direction: `enrichment → {projection, trust_index}`,
  `projection → trust_index`; `trust_index` imports no siblings — no cycle risk,
  and the cold-import test on the facade exercises all three transitively.
- Future role/perspective additions touch `observer_projection.py` only; new
  artifact enrichments touch `observer_enrichment.py` only.

## Out of scope

- Any behavior or rule change to visibility decisions (byte-identical envelopes
  are a gate, not an aspiration).
- Merging observer-side with engine-side visibility (forbidden — witness
  structure; B-2 ADR).
- Converting `observer_visibility` into a package (would break the sentinel's
  file-path scan and the cold-import list for no benefit).
- `observer_protocol.py` (already the R-06 single source the projection layer
  imports), prompt renderers, engines, scoring, launchers (other tracks / T17).

## References

- Health check: `docs/health-check/03-architecture-optimization.md` §B-4.
- Mirror engine-side decision: `docs/adr/2026-06-11-engine-visibility-single-source.md` (B-2).
- Enforcing tests: `tests/test_role_visibility.py` (witness sentinel),
  `tests/test_visibility_parity.py` (R-06 parity),
  `tests/test_observer_visibility.py`, `tests/test_role_single_source.py`
  (`_KNOWN_ROLE_TEAMS` identity + cold import).
- Plan: `docs/harness/plans/2026-06-11--b4-observer-visibility-layering-plan.md`.

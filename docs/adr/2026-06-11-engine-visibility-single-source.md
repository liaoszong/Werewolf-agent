# ADR — Engine-side role-visibility single source (`role_visibility.py`)

- **Status:** Accepted (user-approved health-check item B-2, 2026-06-11)
- **Deciders:** owner + agent (health-check `docs/health-check/03-architecture-optimization.md` §B-2)

## Context

"Which event ids does a seat see" is decided by one security-bearing rule:

- public set: `visibility ∈ {"public", "all"}`
- private set: `visibility == "all"`, OR `visibility ==` the seat's role, OR
  `visibility == "werewolf_team"` for werewolf seats

Before this ADR the rule existed as **four engine-side copies**:

1. `game_engine.GameEngine.observation_for` (live/mock per-player observation),
2. the scripted-arc closures `_public_refs` / `_private_refs_for_role` / `_private_refs`
   inside `game_engine.run_scripted_game` (plus two inline `visible_info_refs`
   comprehensions of the public predicate, and a fourth full one-pass copy in
   `_resolve_wolf_consensus`'s `g1f_provider_consensus` branch — found in review;
   the health-check enumeration had missed it),
3. `emergent_engine.EmergentGameEngine._public_refs` / `_private_refs` / `_build_obs`.

This is exactly the invariant the P2-A-2 **"no feed leak" hard gate** renders prompts
from: an edit to one engine's filter could silently diverge from the other (health-check
B-2). The risk is not hypothetical — the same copy-pasted-rule class produced the
`witch_kill`/`witch_poison` vocabulary bug and the R-18 wolf-snapshot leak.

**Witness structure that must survive (SYS-A4 / safety-net I4b):** the observer side
(`observer_visibility.py`, `observer_protocol.py`) and the invariants oracle
(`invariants/visibility_oracle.py`, which builds on `observer_visibility`) are
*deliberate independent implementations* of visibility. They check the engines from the
outside; if they shared code with the engines, the leak net would verify the engine
against itself (circular witness).

## Decision

1. Add a small pure module **`src/werewolf_eval/role_visibility.py`** exposing the rule
   verbatim: `public_refs(events)` and `private_refs_for_role(events, role)`.
2. **Both engines delegate to it** at every site listed above. Engine observation
   *assembly* (known_roles, runtime emits, game ids) stays per-engine — only the
   filtering rule is shared (no over-unification).
3. **The witness boundary is locked, not just documented:** a sentinel test
   (`tests/test_role_visibility.py`) fails if `observer_visibility.py`,
   `observer_protocol.py`, or anything under `invariants/` ever mentions
   `role_visibility`.
4. The refactor is **byte-identical by construction and by proof**: the predicate moves
   verbatim; gold/scripted fixture tests, the visibility invariant guards
   (`test_event_visibility_invariant.py`, `test_guard_visibility.py`,
   `test_emergent_role_projection.py`), and a before/after artifact byte-snapshot of the
   deterministic fake runners gate the change.

## Consequences

- Engine-vs-engine drift of the visibility rule becomes impossible; a future rule change
  (e.g. a new team channel) is made once and reviewed once.
- Role-generic matching (`visibility == role`) keeps working for new roles (guard landed
  this way) — now in one audited place.
- The observer/oracle implementations intentionally remain duplicates; the parity tests
  (`test_visibility_parity.py`) and the new sentinel keep that duplication honest.

## Out of scope

- Merging engine-side and observer-side visibility (forbidden — see witness structure).
- The wolf-consensus entry-shape duplication noted in health-check B-2's evidence
  (`game_engine._resolve_wolf_consensus` vs `emergent_engine._build_consensus_entry`) —
  that is bookkeeping-shape, not visibility; separate candidate.

## References

- Enforcing tests: `tests/test_role_visibility.py` (rule + sentinel),
  `tests/test_event_visibility_invariant.py` (R-17), `tests/test_guard_visibility.py`,
  `tests/test_visibility_parity.py` (observer-side R-06), gold/scripted fixture suites.
- Health check: `docs/health-check/03-architecture-optimization.md` §B-2.
- Plan: `docs/harness/plans/2026-06-11--b2-engine-visibility-single-source-plan.md`.

# P3-A Replay Data Pipeline Fix: C12-06 + A45-7

> Bound audit: `docs/health-check/2026-06-12-system-view-audit.md`
> Design confirmed: A2 (round required in engine, additive optional in Phase 1 validator) + B3 (round-aware composite join + decision stores request_id) + C1 (speech is explicit non-goal)
> Boundary corrections: (1) Phase 1 validator does NOT enforce new fields; (2) enrichment marks ambiguity on duplicate keys instead of silently taking latest.

## Goal

Make the P3-A per-player replay chain reliably answer "what did this seat see, what was the model's raw output, and why did it take this action?" by:

1. Adding `round` and `request_id` to engine-produced decision records.
2. Upgrading the observer_enrichment decision→event reason join from greedy `(actor, action, target)` to `(round, phase, actor, action, target)`, with fail-soft ambiguity marking on duplicate keys.
3. Making the Phase 1 decision_log validator accept (but not require) `round` and `request_id` as additive optional fields.

Non-goals:
- Do NOT change settlement, scoring formula, or game-log event schema.
- Do NOT add speech to the decision chain (explicit non-goal; P3-A can find speech model output via request_id→provider-trace).
- Do NOT change reason_summary content (still template; request_id→provider-trace is the path to model raw output).

## Architecture

### Decision record schema change (engine side)

Current `_decision()` produces:
```python
{"decision_id", "actor", "decision_scope", "consensus_id", "phase",
 "action", "target", "visible_info_refs", "reason_summary",
 "decision_type", "confidence", "strategy_tag"}
```

New additive fields:
```python
{"round": int,            # required: current round number
 "request_id": str | None  # required: provider request_id when available, None for consensus/team decisions
}
```

- `round`: Always present. The engine knows the current round at every `_decision()` call site.
- `request_id`: Present for all individual player decisions (seer check, guard protect, witch save/poison/pass, day vote, hunter shoot/pass). `None` for `wolf_kill` consensus decisions (those have a `consensus_id` instead; wolf team doesn't have a single request).

### Call-site request_id mapping

| Call site | request_id source | Notes |
|-----------|------------------|-------|
| `_run_single_turn` (seer, guard, day_vote) | `turn["request_id"]` ← `_provider_action` | C12-01 already adds `_vote` suffix for day phase |
| `_run_wolf_kill` → `_decision(r.primary, "team", "night", "werewolf_kill", ...)` | `None` (consensus decision) | Has `consensus_id` instead |
| `_resolve_witch` (save/poison/pass) | `request.request_id` ← witch `ProviderRequest` | Format: `{game_id}_r{rnd:02d}_{witch}_witch` |
| `_resolve_hunter_shot` (shoot/pass) | `turn["request_id"]` ← `_provider_action` | Format: `{game_id}_r{rnd:02d}_{hunter}_shot` |

### Enrichment join upgrade

Current (A45-7 bug):
```python
pending[(actor, action, target)] -> queue of reason_summary  # greedy, no round
```

New:
```python
pending[(round, phase, actor, action, target)] -> list[dict]  # each dict has reason_summary, decision_id, request_id
```

On duplicate key (same tuple appears >1 times in decisions):
- Do NOT silently take latest.
- Mark ALL matching events with `"reason_source": "ambiguous", "reason_detail": f"{count} decisions match this key"` instead of a single reason_summary.
- This is a fail-soft signal to P3-A consumers that the replay chain can't uniquely attribute.

### Phase 1 validator (decision_log.py)

Add `round` and `request_id` as optional fields in `Decision` dataclass:
```python
@dataclass(frozen=True)
class Decision:
    # ... existing required fields ...
    round: int | None = None        # additive: engine always provides, Phase 1 fixtures may omit
    request_id: str | None = None   # additive: engine may be None for consensus decisions
```

Validation rules:
- If `round` is present, must be non-negative int → validate; if absent → accept (backward compat).
- If `request_id` is present, must be non-empty string or null → validate; if absent → accept (backward compat).
- Existing Phase 1 hand-written fixtures (`g001-decision-log.json`, etc.) remain valid without modification.

## File Structure

### Modify

```text
src/werewolf_eval/emergent_engine.py          # _decision() signature + 7 call sites
src/werewolf_eval/observer_enrichment.py      # _load_decision_reasons() join upgrade
src/werewolf_eval/decision_log.py             # additive optional fields + validation
tests/test_emergent_engine.py                 # decision record round + request_id assertions
tests/test_observer_enrichment.py             # cross-round join + ambiguity tests
tests/test_decision_log.py                    # additive field backward compat tests
```

### Do NOT modify

```text
src/werewolf_eval/scoring.py                  # scoring uses its own decision→event matching
src/werewolf_eval/scoring_records.py          # not touched
src/werewolf_eval/settlement_bundle.py        # not touched
src/werewolf_eval/game_log.py                 # game-log event schema NOT changed
src/werewolf_eval/observer_projection.py      # not touched
docs/gold-game/g001-decision-log.json         # Phase 1 fixture — NOT modified (additive only)
docs/generated-games/*.json                   # NOT modified (runtime fixture regeneration separate concern)
docs/ROADMAP.md                               # Not touched
docs/TASKS.md                                 # Not touched
docs/adr/**                                   # Not touched
```

## Implementation Tasks

### Task 1: Add `round` and `request_id` to `_decision()` and engine output

**Files:** `src/werewolf_eval/emergent_engine.py`, `tests/test_emergent_engine.py`

- [ ] **1a.** Update `_decision()` signature to accept `round: int` and `request_id: str | None = None`; include both in the dict appended to `self._decisions`.
- [ ] **1b.** Update all 7 `_decision()` call sites to pass `round` (always available from the enclosing scope) and `request_id` (from the corresponding provider turn or `None` for wolf consensus):
  - `_run_single_turn` line 634: pass `rnd` and `turn["request_id"]`
  - `_run_wolf_kill` line 716: pass `rnd` and `None` (consensus)
  - `_resolve_witch` save line 860: pass `rnd` and `request.request_id`
  - `_resolve_witch` poison line 864: pass `rnd` and `request.request_id`
  - `_resolve_witch` pass line 868: pass `rnd` and `request.request_id`
  - `_resolve_hunter_shot` shoot line 1074: pass the round and `turn["request_id"]`
  - `_resolve_hunter_shot` pass line 1077: pass the round and `turn["request_id"]`
- [ ] **1c.** Add test: run a minimal game and assert every decision in the outcome has `round` (int ≥ 1) and `request_id` (str for individual decisions, null for wolf consensus).

### Task 2: Upgrade enrichment join key with ambiguity fail-soft

**Files:** `src/werewolf_eval/observer_enrichment.py`, `tests/test_observer_enrichment.py`

- [ ] **2a.** Rewrite `_load_decision_reasons()`:
  - Build `pending` dict keyed by `(round, phase, actor, action, target)`.
  - Each entry stores `(reason_summary, decision_id, request_id)`.
  - On duplicate key: instead of appending, mark entry as ambiguous (count matches, store first reason + decision_id for traceability).
  - When joining to events (which have `round` and `phase` fields), match on the full composite key.
  - For ambiguous entries, emit `"reason_source": "ambiguous"` + `"reason_detail": "N decisions match (round, phase, actor, action, target)"` instead of `"reason_summary"`.
  - For matched (unique) entries, emit `"reason_summary"` + `"decision_id"` + `"request_id"` (when not null).
  - Backward compat: if `round` is missing from a decision record (old logs), fall back to `(actor, action, target)` greedy with a warning annotation `"reason_source": "legacy_no_round"`.
- [ ] **2b.** Add test: `test_cross_round_same_actor_action_target_enriched_correctly` — craft a game-log + decision-log where p1 kills p3 in round 1 and p1 votes p5 in round 2, assert enrichment maps the right reason to the right event.
- [ ] **2c.** Add test: `test_ambiguous_key_marked_not_silently_resolved` — same `(round, phase, actor, action, target)` appears twice in decisions, assert enrichment marks both events as `"reason_source": "ambiguous"`.
- [ ] **2d.** Add test: `test_legacy_decision_without_round_falls_back_gracefully` — decision-log entries without `round` field still produce enrichment results with `"reason_source": "legacy_no_round"`.

### Task 3: Additive optional fields in Phase 1 validator

**Files:** `src/werewolf_eval/decision_log.py`, `tests/test_decision_log.py`

- [ ] **3a.** Add `round: int | None = None` and `request_id: str | None = None` to `Decision` dataclass.
- [ ] **3b.** Update `_parse_decision()`: parse `round` and `request_id` from raw dict if present; validate types if present (round → non-negative int, request_id → non-empty str or null).
- [ ] **3c.** Update `_validate_decision()`: if `round` is present, validate non-negative int; if `request_id` is present, validate it's a string (allow empty string for consensus/None case). Do NOT require either field.
- [ ] **3d.** Add tests: existing fixtures parse without `round`/`request_id` (backward compat); fixtures with `round`/`request_id` validate correctly; invalid `round` (negative, non-int) and `request_id` (non-string) are rejected.

### Task 4: Cross-round regression test

**Files:** `tests/test_observer_enrichment.py`

- [ ] **4a.** End-to-end scenario: game-log with guard protecting p3 in rounds 1 AND 2 (same `actor=guard, action=guard_protect, target=p3` in both rounds). Decision-log entries have different `round`. Assert enrichment maps round-1 reason to round-1 event, round-2 reason to round-2 event (no cross-talk).
- [ ] **4b.** Variant: same scenario but decision-log entries are missing `round` field. Assert enrichment still works with legacy greedy match and `"reason_source": "legacy_no_round"` annotation.

### Task 5: Validation and acceptance

- [ ] **5a.** Run targeted tests: `PYTHONPATH=src python -m unittest tests.test_emergent_engine tests.test_observer_enrichment tests.test_decision_log -v`
- [ ] **5b.** Run full suite: `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
- [ ] **5c.** Output `git diff --stat` and `git diff --name-only`
- [ ] **5d.** Allowlist check: only the 6 files listed in "Modify" section are changed in `src/` and `tests/`.
- [ ] **5e.** Forbidden scope check: no changes to scoring, settlement, game-log event schema, Roadmap, TASKS, ADRs.

## Acceptance Criteria

```
A1. Only allowlisted files changed (6 files in src/ + tests/).
A2. Every engine decision record includes round (int ≥ 1) and request_id (str or null).
A3. Cross-round same (actor, action, target) enrichment produces correct per-round matches.
A4. Duplicate composite key (round, phase, actor, action, target) is marked ambiguous, not silently resolved.
A5. Phase 1 validator accepts decisions without round/request_id (backward compat).
A6. Phase 1 validator validates round/request_id when present (forward compat).
A7. Full unittest passes.
A8. No changes to scoring formula, settlement, game-log event schema.
A9. No AI semantic review introduced.
A10. Speech is explicitly a non-goal (no _decision() call added to _resolve_speech).
```

## Risk Notes

1. `_resolve_witch` has three `_decision()` call sites (save/poison/pass) — each needs the same `request.request_id` where `request` is the witch's `ProviderRequest` constructed at line 783.
2. `_resolve_hunter_shot` uses `_provider_action` which builds the turn tracking dict with `request_id` — need to pass the hunter's `request_id` from the turn context.
3. `_run_single_turn` is used by seer, guard, and day_vote — the `turn` dict is available in scope after `_provider_action` returns, so `turn["request_id"]` is the correct source.
4. `wolf_kill` consensus has no single request_id — pass `None`. The `consensus_id` field already identifies the wolf team consensus.
5. Enrichment backward compat with legacy decision-logs (missing `round`): the greedy `(actor, action, target)` fallback must NOT silently produce cross-round mismatches — it must annotate `"reason_source": "legacy_no_round"` so consumers know the match is unreliable.
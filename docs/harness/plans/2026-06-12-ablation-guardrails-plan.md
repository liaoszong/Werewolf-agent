# Ablation Guardrails Hardening — Batch ① (C3-4 + C12-04 + C12-03 + C12-10/11)

**Date**: 2026-06-12
**Binding**: `docs/health-check/2026-06-12-system-view-audit.md` (entries C3-4 / C12-04 / C12-03 / C12-10/11)
**Worktree**: `.worktrees/ablation-guardrails` on branch `codex/ablation-guardrails`, base `main` (`8b6d32c`)
**Scope (allowlist)**:
- `src/werewolf_eval/ablation/harness.py`
- `src/werewolf_eval/ablation/metrics.py`
- `src/werewolf_eval/ablation/__main__.py` (read-only; no change expected)
- `tests/test_ablation_guardrails.py` (new)
- `tests/test_ablation_metrics.py` (additive tests only)
- `tests/test_l4_metrics.py` (additive tests only)

**Forbidden scope (must NOT touch)**: `src/werewolf_eval/emergent_engine.py`, `src/werewolf_eval/llm_providers.py`, `src/werewolf_eval/scoring*.py`, `src/werewolf_eval/invariants/**`, `src/werewolf_eval/observer/**`, any other `src/**`, `docs/ROADMAP.md`, `docs/TASKS.md`, `docs/adr/**`, `.agents/skills/**`, `.github/**`.

**Non-goal**: changes to the live-rate ≥0.7 gate, scaffold-coverage gate, or any existing metric removal. All new fields are additive.

---

## 1. Goal (atomic)

Make the ablation harness self-auditing so the next live batch cannot silently ship:

1. **C3-4** — a run with zero invariant violations goes from "someone ran `check_run` by hand" to "the harness ran it and wrote the result into `_metrics.json`".
2. **C12-04** — cross-bucket aggregation becomes fail-loud, and re-running into a populated arm dir becomes fail-loud (no more silent mixing of old-version completed games).
3. **C12-03** — `milk_pierce_*` on a non-guard board reports `None` (no mechanism) instead of `0` (mechanism measured at zero), aligning with the `guard_target_seer_rate` / `_mean` family convention.
4. **C12-10/11** — `milk_pierce_*_count` becomes a rate (per-n_valid), and `classify_event` stops mis-classifying day speeches that contain night-action keywords (`saves` / `poison` / `no potion`).

## 2. Expected outcome (concrete deliverables)

- `_metrics.json` gains a `validity.invariants` block:
  ```json
  "validity": {
    "invariants": {
      "n_games_checked": 45,
      "n_games_clean": 45,
      "n_violations": 0,
      "violations_by_id": {}
    }
  }
  ```
- `aggregate()` raises `ValueError` when run dirs carry non-identical `evaluation_bucket` tuples (legacy runs with no manifest bucket are tolerated only when ALL runs are legacy; mixed legacy/modern is also an error). The matching bucket (or `null` for all-legacy) is written into `_metrics.json` under `evaluation_bucket`.
- `run_arm()` raises `FileExistsError` when `arm_dir` already contains any `*_NNN/` game subdir or a `_metrics.json`. Fresh empty `arm_dir` (just-created) is still allowed.
- `aggregate_games()` emits `milk_pierce_overlap` and `milk_pierce_death` (rates, per-n_valid) in addition to the existing `_count` totals; `milk_pierce_overlap_count` / `milk_pierce_death_count` are preserved (additive, NOT removed). On non-guard boards both new rate fields are `None`.
- `classify_event()` only matches `saves` / `poison` / `no potion` when `phase == "night"` (or phase is missing, preserving legacy callers). Day-phase speeches containing those keywords classify as `speech`.
- Full suite green: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`.
- `git diff --stat` + file allowlist check + forbidden-scope check reported below.

## 3. Required tools

- `Read`, `Write`, `Edit`, `Bash` (PowerShell 7).
- `grep` for sanity checks only (no subagent exploration needed — scope is 3 files + tests, all read above).
- `lsp_diagnostics` on changed files before final report.

## 4. Must do (exhaustive)

### 4.1 TDD discipline
- Write ALL failing tests FIRST in a new `tests/test_ablation_guardrails.py` (plus additive tests in `tests/test_l4_metrics.py` for the milk-pierce rate family).
- Run the suite once to confirm each new test fails for the RIGHT reason (RED).
- Implement one item, re-run only the affected tests (GREEN), then move on.
- Final full-suite run at the end.

### 4.2 C3-4 wiring
- Import `check_run` from `werewolf_eval.invariants.checker` inside `harness.py` (lazy import is fine; `checker` is pure-Python and cheap).
- After each game's `run_emergent_deepseek_game(...)` returns and `game-log.json` exists, call `check_run(out_dir)`.
- Filter to `severity == "error"` violations (artifact_gap is reported separately and is not a hard invariant fail).
- Accumulate per-game: `violations: list[str]` (each entry = `f"{v.id}: {v.detail}"`), and a per-arm rollup.
- Write per-game `invariants` into the matching `_index.jsonl` row (additive field).
- Write per-arm `validity.invariants` into the `_metrics.json` result dict with keys `n_games_checked`, `n_games_clean`, `n_violations`, `violations_by_id` (counter).
- If `check_run` itself raises (it shouldn't — docstring says "never raises"), catch `Exception`, record as `invariants_error` in the index row, and continue (the harness must not abort on checker bugs).

### 4.3 C12-04 bucket assertion
- In `metrics.aggregate()`, after reading each valid game's `game-log.json`, also call `read_manifest_bucket(d)` (import from `werewolf_eval.evaluation_versions`).
- Collect the set of distinct buckets seen across VALID games only (invalid games are dropped anyway).
- If more than one distinct bucket (after `json.dumps(b, sort_keys=True)` canonicalization) is seen → raise `ValueError("evaluation_bucket mismatch within arm: ...")` with the distinct buckets listed.
- If exactly one bucket → write it into `out["evaluation_bucket"]`.
- If zero valid games → `out["evaluation_bucket"] = None` (no assertion needed).
- Legacy runs (no manifest → `None` bucket) are allowed only when ALL valid games are legacy; a mix of `None` and a real bucket is also an error.

### 4.4 C12-04 run_arm non-empty rejection
- At the top of `run_arm`, after `arm_dir = out_root / arm.label` and `arm_dir.mkdir(parents=True, exist_ok=True)`, scan for existing game subdirs matching `f"{arm.label}_NNN"` or an existing `_metrics.json` / `_index.jsonl`.
- If any are found → raise `FileExistsError(f"arm_dir {arm_dir} is not empty; refusing to mix with prior run. Delete or pick a new label.")`.
- This check runs BEFORE the game loop so the user gets a clean error before any side effects.

### 4.5 C12-03 milk_pierce None for non-guard boards
- In `analyze_game_dict`, detect `has_guard = "guard" in roles.values()` (already computed at line 286).
- When `has_guard is False`: set `milk_pierce_overlap = None` and `milk_pierce_death = None` instead of `0`.
- When `has_guard is True`: keep current integer counts (0, 1, 2, ...).
- In `aggregate_games`:
  - Existing `milk_pierce_overlap_count` / `milk_pierce_death_count` become `sum(g.get("milk_pierce_overlap") or 0 ...)` — i.e. treat `None` as 0 for the total, preserving the current numeric output on guard boards and returning `0` on non-guard boards (the aggregate count is still meaningful as "no piercings observed").
  - NEW: `milk_pierce_overlap_rate` and `milk_pierce_death_rate` = `_mean([g.get("milk_pierce_overlap") for g in games])` — this is the C12-10 fix. `_mean` already filters `None`, so a non-guard arm returns `None` (no mechanism), a guard arm returns the per-game average.
  - Add both new rate fields to `DEFAULT_COMPARE_KEYS` (additive).
- The C12-03 fix is the `_mean`-family alignment: on a non-guard arm, `compare` now prints `None vs 0.28` (clear "no mechanism" signal) instead of `0 vs 12` (misleading "zero is better").

### 4.6 C12-11 classify_event phase guard
- Move the `saves` / `no potion` / `poison` branches AFTER the `phase == "day" and actor and re.match(r"p\d$", actor)` speech branch, OR (safer, smaller diff) add `and (ph != "day")` to each of those three keyword predicates.
- Chosen approach: add `ph != "day"` guards to the three keyword predicates. This preserves behavior for legacy events with no `phase` field (`ph != "day"` is `True` when `ph is None`).
- No changes to the `Guard (p\d) protects` / `Seer .* checks` / `Wolf team kills` regex branches — those are already unambiguous.

### 4.7 Verification
- Run `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"` from the worktree root. All tests must pass (including the existing ~1216).
- Run `lsp_diagnostics` on the three changed src files.
- Run `git diff --stat` and `git diff --name-only` and confirm the allowlist.

## 5. Must not do (forbidden)

- Do NOT modify `src/werewolf_eval/invariants/**` (the checker API is stable; this plan only consumes it).
- Do NOT modify `src/werewolf_eval/emergent_engine.py`, `provider_agent.py`, `llm_providers.py`, `scoring*.py`, `settlement_bundle.py`, `observer/**`, or any file outside `ablation/`.
- Do NOT change the `LIVE_RATE_MIN` (0.7) or `SCAFFOLD_COVERAGE_MIN` (0.5) gates.
- Do NOT remove `milk_pierce_overlap_count` / `milk_pierce_death_count` — they are additive; the new rate fields are siblings, not replacements.
- Do NOT change the `_metrics.json` schema in a breaking way (additive fields only).
- Do NOT change `__main__.py` CLI surface (no new flags needed — the bucket assertion and non-empty-dir rejection are internal correctness checks).
- Do NOT hand-edit `.oh-my-harness/tree.md` (the hook regenerates it).
- Do NOT commit until the user explicitly asks (PR-first discipline; this plan is the pre-commit gate).

## 6. Context (file paths, existing patterns, constraints)

- `src/werewolf_eval/ablation/harness.py` — 87 lines, current `run_arm` at L34-87.
- `src/werewolf_eval/ablation/metrics.py` — 324 lines, `aggregate` at L134-161, `aggregate_games` at L85-131, `classify_event` at L14-41, `analyze_game_dict` at L234-324.
- `src/werewolf_eval/ablation/__main__.py` — 51 lines, no changes expected.
- `src/werewolf_eval/invariants/checker.py` — `check_run(source) -> list[InvariantViolation]`, accepts `str | Path | RunArtifacts | GameOutcome`. Never raises.
- `src/werewolf_eval/evaluation_versions.py` — `read_manifest_bucket(run_dir) -> dict | None`, returns the `evaluation_bucket` dict from `prompt-manifest.json` or `None` for legacy runs.
- `tests/fixtures/ablation/` — 3 legacy diagnostic fixtures with NO `prompt-manifest.json` (so `read_manifest_bucket` returns `None` for them). The bucket assertion must tolerate all-legacy arms.
- `tests/test_ablation_harness_fake.py` — uses `build_emergent_fake_agents` + `build_villager_win_script` for fast fake runs; the new harness wiring test should reuse this pattern.
- Existing `_metrics.json` shape: `{"arm": ..., "prompt_version": ..., "n_games": ..., "metrics": {...}}`. The new `validity` block is a SIBLING of `metrics`, not nested inside it (keeps the metrics dict schema stable).
- `InvariantViolation` fields: `id`, `severity`, `game_id`, `event_ids`, `detail`. Only `severity == "error"` counts as a hard violation; `artifact_gap` severity is informational.

## 7. Test plan (RED-first order)

New file: `tests/test_ablation_guardrails.py`. Each test is written to FAIL against the current code, then pass after the matching implementation step.

| Test | Item | Fails today because |
|---|---|---|
| `test_run_arm_writes_invariants_into_metrics` | C3-4 | `_metrics.json` has no `validity` block |
| `test_run_arm_counts_violations_per_id` | C3-4 | no violations rollup |
| `test_run_arm_rejects_nonempty_arm_dir` | C12-04 | `run_arm` silently reuses populated dirs |
| `test_aggregate_asserts_uniform_bucket` | C12-04 | `aggregate` ignores manifests |
| `test_aggregate_all_legacy_bucket_is_none` | C12-04 | no bucket field at all |
| `test_aggregate_mixed_legacy_and_modern_is_error` | C12-04 | no assertion |
| `test_milk_pierce_is_none_on_non_guard_board` | C12-03 | returns `0` today |
| `test_milk_pierce_rate_is_mean_over_guard_boards` | C12-10 | no rate field |
| `test_milk_pierce_rate_is_none_on_non_guard_board` | C12-10 | no rate field |
| `test_classify_event_day_saves_speech_not_witch_save` | C12-11 | classifies as `witch_save` |
| `test_classify_event_day_poison_speech_not_witch_poison` | C12-11 | classifies as `witch_poison` |
| `test_classify_event_night_saves_still_witch_save` | C12-11 (regression guard) | already passes — pins the preserved path |

Additive tests in `tests/test_l4_metrics.py`:
- `test_aggregate_milk_pierce_rate_guard_board` — pins the new rate field on a guard board.
- `test_aggregate_milk_pierce_rate_non_guard_board_is_none` — pins the None convention.

## 8. Risk register

- **Risk**: `check_run` on a fake-script game may return violations that fail the smoke test. **Mitigation**: the harness records violations but does NOT abort the arm; the smoke test asserts the field is present, not that it's empty. A separate test asserts empty-on-clean-games using a known-good fixture.
- **Risk**: bucket assertion breaks the existing `test_aggregate_reads_dirs_and_reports_invalid` test (legacy fixtures have no manifest). **Mitigation**: all-legacy arms are tolerated (`evaluation_bucket = None`); only mixed arms raise.
- **Risk**: `milk_pierce_*` becoming `None` on non-guard boards could break `compare` delta arithmetic. **Mitigation**: `compare` already handles `None` gracefully — `delta` becomes `None` when either side is `None` (L180). No change needed.
- **Risk**: phase-guard on `classify_event` could break legitimate night-phase witch events that lack a `phase` field. **Mitigation**: `ph != "day"` is `True` when `ph is None`, so legacy phase-less events still classify as before.

## 9. Acceptance checklist

- [ ] Worktree clean (`git status --short` empty before implementation).
- [ ] All new tests RED on current code (one baseline run).
- [ ] All new tests GREEN after implementation.
- [ ] Full suite GREEN: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`.
- [ ] `git diff --name-only` ⊆ allowlist.
- [ ] `lsp_diagnostics` clean on all three changed src files.
- [ ] No forbidden-scope changes.
- [ ] Plan checkbox (this file) all ticked.

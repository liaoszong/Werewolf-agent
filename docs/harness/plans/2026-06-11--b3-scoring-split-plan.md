# B-3 Scoring Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `scoring.py` (992 LOC, two concerns) into `scoring_types.py` + `scoring_records.py` + `scoring_metrics.py` + a `gold_game_fixtures.py` constants table, with `scoring.py` kept as a pure facade — byte-identical outputs, zero import breakage (health-check B-3; no ADR required per the health check).

**Architecture:** Mirror the proven SYS-C2 observer-split recipe: move code verbatim into leaf modules, keep the original module as an explicit re-export facade so all 12 importers (5 src + 7 test files) keep working unchanged. The scattered `g001` literals get lifted into one constants table consumed by both halves. The byte gate is three-layered: the committed s2/s5 expected fixtures (already test-pinned), a before/after dump harness over all 7 fixture game combos, and the full suite.

**Tech Stack:** Python 3.12 stdlib, unittest-style tests. Test command (both prefixes mandatory): `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q`

**Coordination:** SYS-B1 renderer-registry track is pending in its own worktree — it does NOT touch scoring; zero overlap. Do not touch prompt renderers, `emergent_engine.py`, `game_engine.py`, `observer_visibility.py`, launchers, or `role_visibility.py`.

**Verified facts (read on main `6f91ae0`, 2026-06-11):**
- Structure of `scoring.py`:
  - Types & serialization (L12-129): 8 frozen dataclasses (`ScoreRecord`, `DecisionAssessment`, `ScoringBoundary`, `ScoreLog`, `ResultMetrics`, `ProcessMetrics`, `ScoreSummary`, `MetricsSummary`), `score_log_to_dict` (uses `_evaluation_bucket`/`UNKNOWN_VERSION`/`SCORING_VERSION` imports), `metrics_summary_to_dict`.
  - Constants: `SCORE_RELEVANT_EVENT_TYPES` (L132), `KEY_VILLAGER_ROLES` (L140), `SCORE_RELEVANT_DECISION_ACTIONS` (L192, alias), `SEMANTIC_QUALITY_SCORE_BY_LABEL` (L279).
  - Records half (L143-739): `_player_by_id` … `_assess_decision`, `_scoring_boundary`, `_score_werewolf_kill/_seer_check/_witch_save/_witch_poison/_player_vote`, `_score_id_prefix`/`_score_log_id`/`_score_source_label`, **module-global mutable `_current_score_id_prefix` (L652, rebound via `global` inside `score_game`, read by `_record` L667)**, `_record`, `score_game` (L685).
  - Metrics half (L740-992): `_round_float` … `_vote_accuracy_by_player`, `_seer_metrics`, `_witch_metrics`, `_team_metrics`, `_result_metrics`, `_score_summary`, `summarize_metrics` (L893), `_known_rubric_gaps` (L932).
- g001 literal sites: e007 note (L477-478), `_score_id_prefix`/`_score_log_id` (L631-638), `_score_source_label` scripted check (L643), `score_game` is_g001 source path (L722-723), metrics ids + source path (L895-898), canonical rubric-gap list (L939-948).
- External consumers of names (zero may break): src importers = `attribute_game.py`, `attribution.py`, `render_demo.py`, `score_game.py`, `settlement_bundle.py`; tests import `score_game`, `summarize_metrics`, `score_log_to_dict`, `metrics_summary_to_dict`, `SCORE_RELEVANT_EVENT_TYPES`, **`_result_metrics` (private!)**, `MetricsSummary`, `ScoreLog`. No external reference to `_current_score_id_prefix`; no dynamic `scoring.<attr>` access.
- Byte gate fixtures: `docs/gold-game/s2-score-log.json`, `s2-metrics-summary.json` (+ s5 variants) are test-pinned expected outputs; generated-games score/metrics JSONs likewise.

**Hard rule for every move:** code moves VERBATIM (comments included). The only permitted edits are import lines and the g001-literal → table substitutions in Task 4 (each one a named, reviewed mapping). Anything else = scope violation.

---

### Task 1: Commit plan

- [ ] `node .codex/hooks/tree.mjs --force`
- [ ] `git add docs/harness/plans/2026-06-11--b3-scoring-split-plan.md .oh-my-harness/tree.md && git commit -m "docs(plan): b3 scoring split — types/records/metrics + gold fixtures table, facade keeps 12 importers byte-stable"`

---

### Task 2: Baseline dump harness (BEFORE any src change)

**Files:** `.tmp/b3_dump.py` (gitignored, never committed)

- [ ] **Step 1:** Create `.tmp/b3_dump.py`:

```python
import json, sys
from pathlib import Path

sys.path.insert(0, "src")
from werewolf_eval.game_log import load_game_log
from werewolf_eval.decision_log import load_decision_log
from werewolf_eval.semantic_labels import load_semantic_label_log
from werewolf_eval.scoring import (
    metrics_summary_to_dict,
    score_game,
    score_log_to_dict,
    summarize_metrics,
)

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)


def dump(name, game_path, dec_path=None, s5_path=None):
    game = load_game_log(game_path)
    dec = load_decision_log(dec_path, game) if dec_path else None
    s5 = load_semantic_label_log(s5_path, dec) if s5_path else None
    sl = score_game(game, dec, s5)
    ms = summarize_metrics(game, sl)
    (out / f"{name}-score.json").write_text(
        json.dumps(score_log_to_dict(sl), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8")
    (out / f"{name}-metrics.json").write_text(
        json.dumps(metrics_summary_to_dict(ms), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8")


dump("g001", "docs/gold-game/g001-game-log.json")
dump("g001-dec", "docs/gold-game/g001-game-log.json", "docs/gold-game/g001-decision-log.json")
dump("g001-s5", "docs/gold-game/g001-game-log.json", "docs/gold-game/g001-decision-log.json",
     "docs/gold-game/s5-semantic-label-output.example.json")
dump("g1", "docs/generated-games/g1-scripted-game-log.json", "docs/generated-games/g1-scripted-decision-log.json")
dump("g1b", "docs/generated-games/g1b-mock-agent-game-log.json", "docs/generated-games/g1b-mock-agent-decision-log.json")
dump("g1c", "docs/generated-games/g1c-wolf-consensus-game-log.json", "docs/generated-games/g1c-wolf-consensus-decision-log.json")
dump("g1d", "docs/generated-games/g1d-fake-provider-game-log.json", "docs/generated-games/g1d-fake-provider-decision-log.json")
print("dumped:", len(list(out.glob('*.json'))), "files")
```

(If a loader signature differs, adapt the harness — it's throwaway tooling; report the adaptation. If any fixture path 404s, check `ls docs/generated-games/` and fix the path.)

- [ ] **Step 2:** `NO_PROXY='*' python .tmp/b3_dump.py .tmp/b3-base` → expect "dumped: 14 files". Then `(cd .tmp/b3-base && find . -type f | sort | xargs sha256sum) > .tmp/b3-base.sha256`. Scoring is pure/deterministic — no double-run needed.
- [ ] **Step 3:** `git status --short` clean (nothing tracked changed). No commit.

---

### Task 3: Extract `scoring_types.py` (types + serializers + constants), facade re-exports

**Files:**
- Create: `src/werewolf_eval/scoring_types.py`
- Modify: `src/werewolf_eval/scoring.py` (delete moved block, add re-export)

- [ ] **Step 1:** Create `scoring_types.py` with module docstring:

```python
"""Score/metrics datatypes, serializers, and scoring constants (health-check B-3 split).

Moved verbatim from ``scoring.py``; that module remains the public facade —
import from ``werewolf_eval.scoring`` unless you are inside the scoring package."""
```

then move VERBATIM from `scoring.py`: the 8 dataclasses (L12-103), `score_log_to_dict` + `metrics_summary_to_dict` (L105-129), and the four constants `SCORE_RELEVANT_EVENT_TYPES`, `KEY_VILLAGER_ROLES`, `SCORE_RELEVANT_DECISION_ACTIONS`, `SEMANTIC_QUALITY_SCORE_BY_LABEL` (lift `SCORE_RELEVANT_DECISION_ACTIONS = SCORE_RELEVANT_EVENT_TYPES` next to its base). Bring along exactly the imports those lines need (`dataclasses.asdict/dataclass/field`, `typing.Any`, `_evaluation_bucket`/`UNKNOWN_VERSION`/`SCORING_VERSION` from `evaluation_versions` — check the actual import lines at the top of `scoring.py` and copy the needed subset; `SemanticLabel` type for the label-score dict if referenced).

- [ ] **Step 2:** In `scoring.py`, delete the moved block and add at the top (right after the module docstring/imports):

```python
from werewolf_eval.scoring_types import (  # noqa: F401 — facade re-exports (B-3 split)
    DecisionAssessment,
    KEY_VILLAGER_ROLES,
    MetricsSummary,
    ProcessMetrics,
    ResultMetrics,
    SCORE_RELEVANT_DECISION_ACTIONS,
    SCORE_RELEVANT_EVENT_TYPES,
    ScoreLog,
    ScoreRecord,
    ScoreSummary,
    ScoringBoundary,
    SEMANTIC_QUALITY_SCORE_BY_LABEL,
    metrics_summary_to_dict,
    score_log_to_dict,
)
```

Remove imports in `scoring.py` that became unused by the move (verify each before removing).

- [ ] **Step 3:** Gates: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_scoring.py tests/test_attribution.py tests/test_render_demo.py tests/test_settlement_bundle.py tests/test_engine_to_scoring_e2e.py tests/test_scripted_game_runner.py -q` PASS; then `NO_PROXY='*' python .tmp/b3_dump.py .tmp/b3-t3 && (cd .tmp/b3-t3 && find . -type f | sort | xargs sha256sum) | diff .tmp/b3-base.sha256 - && echo BYTE-IDENTICAL`.
- [ ] **Step 4:** `node .codex/hooks/tree.mjs --force`; commit: `git add src/werewolf_eval/scoring.py src/werewolf_eval/scoring_types.py .oh-my-harness/tree.md && git commit -m "refactor(scoring): extract scoring_types (dataclasses+serializers+constants), scoring.py re-exports (B-3 step 1/3, byte gate green)"`

---

### Task 4: Extract `gold_game_fixtures.py` + `scoring_records.py` (score-log half)

**Files:**
- Create: `src/werewolf_eval/gold_game_fixtures.py`
- Create: `src/werewolf_eval/scoring_records.py`
- Modify: `src/werewolf_eval/scoring.py`

- [ ] **Step 1:** Create `gold_game_fixtures.py`:

```python
"""docs/gold-game ``g001`` fixture constants — the one place the scorer knows the
gold game by name (health-check B-3: lifted from ~10 scattered literals in
``scoring.py``). Everything here is byte-load-bearing for the s2/s5 expected
fixtures; change only together with regenerated fixtures."""

from __future__ import annotations

from typing import Any

GOLD_GAME_ID = "g001"
GOLD_SCORE_ID_PREFIX = "s2_g001"
GOLD_SCORE_LOG_ID_S2 = "s2_g001_expected_score_log"
GOLD_SCORE_LOG_ID_S5 = "s5_g001_expected_score_log"
GOLD_METRICS_ID_S2 = "s2_g001_expected_metrics"
GOLD_METRICS_ID_S5 = "s5_g001_expected_metrics"
GOLD_SOURCE_GAME_LOG = "docs/gold-game/g001-game-log.json"
GOLD_E007_EVENT_ID = "g001_e007"
GOLD_E007_NOTE = (
    "Wolf team chose a villager target; p5 is later revealed as villager, while "
    "g001_e009 records that the Night 1 save prevented the kill from taking effect."
)
GOLD_KNOWN_RUBRIC_GAPS: list[dict[str, Any]] = [
    {
        "gap": "werewolf_day_vote_without_elimination",
        "events": ["g001_e033"],
        "S2_policy": "count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR",
    },
    {
        "gap": "witch_day_vote_outcome_not_explicit",
        "events": ["g001_e019", "g001_e034"],
        "S2_policy": "count in vote_accuracy metrics; assign outcome_score 0 in score log; do not modify EVALUATION_RUBRIC.md in this PR",
    },
]
```

⚠️ Before committing, verify each constant against the CURRENT literals in `scoring.py` (lines noted in Verified facts) — character-for-character (the E007 note and S2_policy strings especially). If any differs from this plan, the FILE is right, the plan is wrong: copy from the file and report.

- [ ] **Step 2:** Create `scoring_records.py` (docstring: `"""Score Log generation — the per-decision scoring half of the B-3 split. Moved verbatim from scoring.py; import via the werewolf_eval.scoring facade."""`) and move VERBATIM `scoring.py` L143-739: all record-half helpers, `_assess_decision`, `_scoring_boundary`, the five `_score_*` scorers, `_score_id_prefix`/`_score_log_id`/`_score_source_label`, `_current_score_id_prefix`, `_record`, `score_game`. The `global _current_score_id_prefix` statement inside `score_game` and its reader `_record` now live in the SAME module — the mutable state keeps working. Replace each g001 literal in the moved code with the table constant (g001 equality checks → `== GOLD_GAME_ID`, e007 check/note → `GOLD_E007_EVENT_ID`/`GOLD_E007_NOTE`, id prefixes/log ids → the `GOLD_*` constants, `is_g001` source path → `GOLD_SOURCE_GAME_LOG`). Imports: from `scoring_types` (types/constants), `gold_game_fixtures`, plus the game_log/decision_log/semantic_labels/evaluation_versions imports those lines need.
- [ ] **Step 3:** In `scoring.py`: delete the moved block; extend the facade re-export with `score_game` and (for safety) the private names the codebase/tests touch from this half — minimum `_assess_decision`, `_scoring_boundary`, `_record`, the five `_score_*` functions, `_score_id_prefix`, `_score_log_id`, `_score_source_label` (cheap insurance; explicit list, `# noqa: F401`). NOTE: do NOT re-export `_current_score_id_prefix` (mutable rebinding makes a facade alias a stale-value trap; no external consumer exists — verified).
- [ ] **Step 4:** Gates: same 6-suite run as Task 3 + `tests/test_emergent_engine.py tests/test_game_engine.py` (they import score_game paths); dump diff: `NO_PROXY='*' python .tmp/b3_dump.py .tmp/b3-t4` → sha256 diff vs `.tmp/b3-base.sha256` → `BYTE-IDENTICAL`.
- [ ] **Step 5:** Tree hook; commit: `git commit -m "refactor(scoring): extract scoring_records + gold_game_fixtures table (B-3 step 2/3, g001 literals single-sourced, byte gate green)"` (add the 4 files incl. tree.md).

---

### Task 5: Extract `scoring_metrics.py` (metrics half), facade final form

**Files:**
- Create: `src/werewolf_eval/scoring_metrics.py`
- Modify: `src/werewolf_eval/scoring.py`

- [ ] **Step 1:** Create `scoring_metrics.py` (docstring: `"""Metrics Summary aggregation — the per-game metrics half of the B-3 split. Moved verbatim from scoring.py; import via the werewolf_eval.scoring facade."""`) and move VERBATIM `scoring.py` L740-992 (post-Task-4 numbering will differ — move everything that remains except the facade imports/docstring): `_round_float` through `summarize_metrics` and `_known_rubric_gaps`. Replace metrics-half g001 literals with table constants (`GOLD_GAME_ID`, `GOLD_METRICS_ID_S2/S5`, `GOLD_SOURCE_GAME_LOG`, `GOLD_KNOWN_RUBRIC_GAPS` — `_known_rubric_gaps`'s g001 branch returns the table list; keep the non-g001 derivation code verbatim). Imports from `scoring_types` + `gold_game_fixtures` + whatever the moved lines need.
- [ ] **Step 2:** `scoring.py` final form = docstring + three re-export blocks ONLY (types, records, metrics). Metrics block must include `summarize_metrics`, **`_result_metrics` (test-imported!)**, and for safety `_score_summary`, `_known_rubric_gaps`, `_vote_accuracy_by_player`, `_seer_metrics`, `_witch_metrics`, `_team_metrics`. Update the module docstring to describe the facade role and point to the three modules. Sanity: `python -c "import sys; sys.path.insert(0,'src'); import werewolf_eval.scoring as s; print(len([n for n in dir(s) if not n.startswith('__')]))"` and spot-check `s._result_metrics`, `s.score_game`, `s.ScoreLog`.
- [ ] **Step 3:** Gates: full scoring-consumer suite (the 8 files from Task 4) + dump diff vs baseline → `BYTE-IDENTICAL` + **full suite** `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q` (expect 1228+/2 skipped, zero fail).
- [ ] **Step 4:** Tree hook; commit: `git commit -m "refactor(scoring): extract scoring_metrics; scoring.py is now a pure facade (B-3 step 3/3, byte gate + full suite green)"`.

---

### Task 6: Validation report + final review + merge

- [ ] AGENTS.md report: `git diff --stat main...HEAD` / `--name-only`; allowlist = {scoring.py, scoring_types.py, scoring_records.py, scoring_metrics.py, gold_game_fixtures.py, plan, tree.md}; forbidden-scope: zero test changes (this split must not need ANY test edit — that's the facade working), zero touches elsewhere.
- [ ] Final whole-branch review (code-reviewer template; range main..HEAD).
- [ ] Merge to main (--no-ff, message style `merge(b3): ...`), full suite on merged main, dry-run push, push, cleanup worktree/branch (is-ancestor check first).

---

## Self-Review (planning time)

- All four B-3 deliverables covered (records/metrics split ✓, g001 table ✓, facade ✓, byte verification ✓). Tests untouched by design — `_result_metrics` and `SCORE_RELEVANT_EVENT_TYPES` re-exports keep the 7 test files green.
- The one real hazard (`_current_score_id_prefix` mutable global) is named, its setter+reader co-located in `scoring_records`, and its facade re-export explicitly forbidden with reasoning.
- Placeholder scan: harness code complete; table code complete; moves are verbatim-by-line-range with named literal substitutions (the only permitted edits).
- Line numbers drift after each task — Tasks 4/5 say "everything that remains", anchored by function names, not stale numbers.

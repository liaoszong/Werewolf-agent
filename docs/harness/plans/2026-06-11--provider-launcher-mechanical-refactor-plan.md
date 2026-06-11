# Provider/Launcher Mechanical Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 6 small health-check items (D-3, D-4, D-5+T-2, validate_failure_audit wiring, dead-fixture removal, E-5) in one mechanical PR that has **zero file overlap** with the in-flight L4 guard arm.

**Architecture:** No new subsystems. `DeepSeekProviderConfig` becomes a frozen-dataclass *subclass* of `ChatProviderConfig` (same fields/order, deepseek defaults), which lets the 4 remaining direct `DeepSeekProvider(config)` constructions route through `provider_registry.build_provider("deepseek", ...)` — making the registry the literal single source for all live provider construction. The 6 `validate_*` CLIs get one uniform error contract (`invalid <label>: <exc>` + exit 1) and their first-ever tests; `validate_failure_audit` gets wired into `validate_brief.py` (it is the only family member with zero consumers — a wiring gap, not dead code).

**Tech Stack:** Python 3.12 stdlib only, `unittest` runner. Test command (both prefixes mandatory, see `.agents/skills/testing-and-process-control/SKILL.md`):

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q
```

**Hard scope boundary (L4 guard arm runs in parallel):** do NOT touch `emergent_engine.py`, `action_runtime/**`, `src/werewolf_eval/invariants/**`, any prompt/observation renderer, `observer_visibility.py`, `scoring.py`, ablation metrics scripts, or any test file covering those. Worktree isolation is mandatory (`.agents/skills/committing-in-shared-worktrees/SKILL.md`).

**Verified facts this plan rests on (re-checked 2026-06-11 on main):**
- `ChatProviderConfig` (`llm_providers.py:42`) IS `@dataclass(frozen=True)`; field order `api_key, base_url, model, timeout_seconds, max_tokens, max_requests, persona_prompt, temperature` is byte-identical to `DeepSeekProviderConfig` (`deepseek_provider.py:27-37`) — only `base_url`/`model` defaults differ.
- `provider_registry.build_provider` (`provider_registry.py:187`) accepts any `ChatProviderConfig`, stamps `PROVIDER_NAME`/`SOURCE_LABEL` from the spec; for deepseek these equal the class defaults (no-op stamp → byte-identical artifacts).
- Import direction: `provider_registry` → `deepseek_provider` → `llm_providers`. Launcher/run_* modules may import `provider_registry` without cycles.
- The 4 direct constructions: `deepseek_launcher.py:71`, `run_emergent_deepseek_game.py:219`, `run_deepseek_provider_game.py:124`, `run_deepseek_consensus_game.py:240`.
- All 6 log loaders raise `ValueError` subclasses (`GameLogValidationError` etc.); `json.JSONDecodeError ⊂ ValueError`; missing file → `OSError`. So `except (OSError, ValueError)` is the complete uniform catch.
- No gold-game failure-audit fixture exists; the tested pair is `docs/generated-games/g1c-wolf-consensus-failure-audit.json` + `g1c-wolf-consensus-game-log.json` (already loaded by `tests/test_failure_audit.py`).
- `g1d-fake-provider-failure-audit.example.json`: zero static + zero dynamic refs (health-check DEAD-CONFIRMED, re-verified).

---

### Task 1: D-3 — `DeepSeekProviderConfig` becomes a subclass of `ChatProviderConfig`

**Files:**
- Modify: `src/werewolf_eval/deepseek_provider.py:27-37`
- Test: `tests/test_deepseek_provider.py` (append one test class)

- [ ] **Step 1: Write the failing test** — append to `tests/test_deepseek_provider.py`:

```python
class DeepSeekConfigShapeTest(unittest.TestCase):
    """D-3: DeepSeekProviderConfig is the shared ChatProviderConfig shape with
    deepseek defaults — no second 8-field clone to keep in sync."""

    def test_is_chat_provider_config_with_deepseek_defaults(self):
        import dataclasses
        from werewolf_eval.llm_providers import ChatProviderConfig

        cfg = DeepSeekProviderConfig(api_key="sk-test-key")
        self.assertIsInstance(cfg, ChatProviderConfig)
        self.assertEqual(cfg.base_url, "https://api.deepseek.com")
        self.assertEqual(cfg.model, "deepseek-v4-flash")
        self.assertEqual(cfg.timeout_seconds, 30)
        self.assertEqual(cfg.max_tokens, 256)
        self.assertEqual(cfg.max_requests, 11)
        self.assertEqual(cfg.persona_prompt, "")
        self.assertIsNone(cfg.temperature)
        self.assertEqual(
            [f.name for f in dataclasses.fields(cfg)],
            [f.name for f in dataclasses.fields(ChatProviderConfig)],
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            cfg.api_key = "x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_deepseek_provider.py -q`
Expected: FAIL on `assertIsInstance` (today it's an independent dataclass).

- [ ] **Step 3: Implement** — in `deepseek_provider.py`, replace the field-clone dataclass with:

```python
from werewolf_eval.llm_providers import (  # re-exported for back-compat
    ChatProviderConfig,
    OpenAICompatibleProvider,
    Transport,
    _default_transport,
)


@dataclass(frozen=True)
class DeepSeekProviderConfig(ChatProviderConfig):
    """DeepSeek defaults over the shared ``ChatProviderConfig`` shape (health-check
    D-3). Field names/order/behavior unchanged — existing tests are the safety net;
    being a subclass lets ``provider_registry.build_provider`` accept it directly."""

    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
```

(Keep the `@dataclass(frozen=True)` decorator on the subclass; inherited fields keep their declaration order, so the constructor signature is unchanged.)

- [ ] **Step 4: Run the deepseek + provider test files**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_deepseek_provider.py tests/test_deepseek_launcher.py tests/test_p2a2_live_path.py tests/test_provider_registry.py -q`
Expected: PASS (frozen/equality/repr semantics preserved for same-class comparisons).

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/deepseek_provider.py tests/test_deepseek_provider.py
git commit -m "refactor(provider): DeepSeekProviderConfig subclasses ChatProviderConfig (health-check D-3)"
```

---

### Task 2: D-4 — route the 4 direct `DeepSeekProvider(config)` constructions through `build_provider`

**Files:**
- Modify: `src/werewolf_eval/deepseek_launcher.py` (`_default_provider_factory`, line ~71)
- Modify: `src/werewolf_eval/run_emergent_deepseek_game.py` (`_deepseek_factory`, line ~219)
- Modify: `src/werewolf_eval/run_deepseek_provider_game.py` (`_build_deepseek_agent`, line ~124)
- Modify: `src/werewolf_eval/run_deepseek_consensus_game.py` (`_build_deepseek_agent`, line ~240)
- Test: `tests/test_provider_registry.py` (append sentinel test)

- [ ] **Step 1: Write the failing sentinel test** — append to `tests/test_provider_registry.py`:

```python
class ProviderConstructionSingleSourceTest(unittest.TestCase):
    """D-4: build_provider is the only live construction path. A direct
    DeepSeekProvider(config) call silently skips the registry identity stamp,
    so registry changes (base-url/source-label) would not reach that path."""

    def test_no_direct_deepseek_provider_construction_in_src(self):
        src = Path(__file__).resolve().parents[1] / "src" / "werewolf_eval"
        allowed = {"deepseek_provider.py", "provider_registry.py"}
        offenders = sorted(
            p.name
            for p in src.rglob("*.py")
            if p.name not in allowed
            and "DeepSeekProvider(" in p.read_text(encoding="utf-8")
        )
        self.assertEqual(offenders, [])
```

(If `tests/test_provider_registry.py` doesn't already import `Path`/`unittest`, add the imports matching the file's existing header style.)

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_provider_registry.py -q`
Expected: FAIL listing the 4 offender files.

- [ ] **Step 3: Implement** — in each of the 4 files, replace the direct construction with the registry call and fix imports:

`deepseek_launcher.py`:
```python
from werewolf_eval.deepseek_provider import DeepSeekProviderConfig
from werewolf_eval.provider_registry import build_provider
...
def _default_provider_factory(config: DeepSeekProviderConfig) -> ProviderFactory:
    """One shared provider across all seats so ``max_requests`` is a true global
    budget for the whole game (mirrors ``_build_deepseek_agent``). Built via the
    registry so the identity stamp is the single construction path (D-4)."""
    shared_provider = build_provider("deepseek", config)
```
(Drop the now-unused `DeepSeekProvider` import from this file.)

`run_emergent_deepseek_game.py` (`_deepseek_factory`):
```python
    shared = build_provider("deepseek", config)
```

`run_deepseek_provider_game.py` and `run_deepseek_consensus_game.py` (`_build_deepseek_agent`):
```python
    shared_provider = build_provider("deepseek", config)
```

In each file add `from werewolf_eval.provider_registry import build_provider` and remove the `DeepSeekProvider` name from imports **only if** it has no other uses in that file (grep the file first; keep `DeepSeekProviderConfig`).

- [ ] **Step 4: Run the affected test files + sentinel**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_provider_registry.py tests/test_deepseek_launcher.py tests/test_deepseek_provider_game.py tests/test_deepseek_consensus_game.py tests/test_run_emergent_deepseek_game.py tests/test_p2a2_live_path.py tests/test_multi_provider_launcher.py -q`
Expected: PASS — the registry stamp equals the class defaults for deepseek, so provider traces/manifests are byte-identical (existing source_label assertions prove it).

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/deepseek_launcher.py src/werewolf_eval/run_emergent_deepseek_game.py src/werewolf_eval/run_deepseek_provider_game.py src/werewolf_eval/run_deepseek_consensus_game.py tests/test_provider_registry.py
git commit -m "refactor(provider): route all live DeepSeek construction through build_provider (health-check D-4)"
```

---

### Task 3: D-5 + T-2 — uniform validate-CLI error contract + first CLI tests

**Files:**
- Modify: `src/werewolf_eval/validate_game_log.py`
- Modify: `src/werewolf_eval/validate_decision_log.py`
- Modify: `src/werewolf_eval/validate_consensus_log.py`
- Modify: `src/werewolf_eval/validate_failure_audit.py`
- Modify: `src/werewolf_eval/validate_log_bundle.py`
- Modify: `src/werewolf_eval/validate_semantic_labels.py`
- Create: `tests/test_validate_clis.py`

Contract: every CLI gains `main(argv: list[str] | None = None)` (for in-process tests; `parse_args(argv)` with `None` still reads `sys.argv`), and wraps its loads in `except (OSError, ValueError)` printing `invalid <label>: {exc}` + `return 1`. **Success stdout must stay byte-identical** (`validate_brief.py` captures it as an informal contract).

- [ ] **Step 1: Write the failing tests** — create `tests/test_validate_clis.py`:

```python
"""T-2/D-5: first behavior tests for the six validate_* CLIs.

Locks (a) exit 0 + summary line on good fixtures, (b) the uniform error
contract `invalid <label>: <exc>` + exit 1 on bad input (was: 5 of 6 CLIs
dumped a raw traceback)."""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval import (
    validate_consensus_log,
    validate_decision_log,
    validate_failure_audit,
    validate_game_log,
    validate_log_bundle,
    validate_semantic_labels,
)

GOLD = ROOT / "docs" / "gold-game"
GEN = ROOT / "docs" / "generated-games"
GAME = str(GOLD / "g001-game-log.json")
DECISION = str(GOLD / "g001-decision-log.json")
CONSENSUS = str(GOLD / "g001-consensus-log.json")
LABELS = str(GOLD / "s5-semantic-label-output.example.json")
G1C_GAME = str(GEN / "g1c-wolf-consensus-game-log.json")
G1C_AUDIT = str(GEN / "g1c-wolf-consensus-failure-audit.json")


def _run(main, argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


class ValidateCliSuccessTest(unittest.TestCase):
    def test_game_log(self):
        code, out = _run(validate_game_log.main, [GAME])
        self.assertEqual(code, 0)
        self.assertIn("validated game_id=", out)

    def test_decision_log(self):
        code, out = _run(validate_decision_log.main, [DECISION, GAME])
        self.assertEqual(code, 0)
        self.assertIn("validated decision_log_id=", out)

    def test_consensus_log(self):
        code, out = _run(validate_consensus_log.main, [CONSENSUS, GAME])
        self.assertEqual(code, 0)
        self.assertIn("validated consensus_log_id=", out)

    def test_failure_audit(self):
        code, out = _run(validate_failure_audit.main, [G1C_AUDIT, G1C_GAME])
        self.assertEqual(code, 0)
        self.assertIn("validated failure_audit game_id=", out)

    def test_log_bundle(self):
        code, out = _run(validate_log_bundle.main, [GAME, "--decision-log", DECISION])
        self.assertEqual(code, 0)
        self.assertIn("validated log_bundle game_id=", out)

    def test_semantic_labels(self):
        code, out = _run(validate_semantic_labels.main, [GAME, DECISION, LABELS])
        self.assertEqual(code, 0)
        self.assertIn("validated semantic_label_log_id=", out)


class ValidateCliInvalidInputTest(unittest.TestCase):
    """Uniform error contract: bad input -> `invalid <label>: ...` + exit 1,
    never an uncaught traceback."""

    def test_bad_input_exits_1_with_uniform_message(self):
        cases = [
            (validate_game_log.main, ["missing.json"], "invalid game log:"),
            (validate_decision_log.main, ["missing.json", GAME], "invalid decision log:"),
            (validate_consensus_log.main, ["missing.json", GAME], "invalid consensus log:"),
            (validate_failure_audit.main, ["missing.json", G1C_GAME], "invalid failure audit:"),
            (validate_log_bundle.main, ["missing.json"], "invalid log bundle:"),
            (validate_semantic_labels.main, [GAME, DECISION, "missing.json"], "invalid semantic label log:"),
        ]
        for main, argv, label in cases:
            with self.subTest(label=label):
                code, out = _run(main, argv)
                self.assertEqual(code, 1)
                self.assertIn(label, out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify the right failures**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_validate_clis.py -q`
Expected: success tests FAIL with `TypeError: main() takes 0 positional arguments` (no `argv` param yet); error-contract subtests for the 5 unwrapped CLIs FAIL with raised `OSError`.

- [ ] **Step 3: Implement** — apply the same two changes to each CLI. Full new `main` bodies:

`validate_game_log.py`:
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Game Log JSON file.")
    parser.add_argument("path", help="Path to Game Log JSON")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.path)
    except (OSError, ValueError) as exc:
        print(f"invalid game log: {exc}")
        return 1

    print(f"validated game_id={game.game_id}")
    print(f"source_label={game.source_label}")
    print(f"players={len(game.players)}")
    print(f"events={len(game.events)}")
    print(f"winner={game.result.winner}")
    print(f"end_round={game.result.end_round}")
    return 0
```

`validate_decision_log.py`:
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Decision Log JSON file.")
    parser.add_argument("decision_log_path", help="Path to Decision Log JSON")
    parser.add_argument("game_log_path", help="Path to matching Game Log JSON")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.game_log_path)
        decision_log = load_decision_log(args.decision_log_path, game)
    except (OSError, ValueError) as exc:
        print(f"invalid decision log: {exc}")
        return 1

    print(f"validated decision_log_id={decision_log.decision_log_id}")
    print(f"game_id={decision_log.game_id}")
    print(f"decisions={len(decision_log.decisions)}")
    print(f"source_label={decision_log.source_label}")
    return 0
```

`validate_consensus_log.py` — keep its existing message byte-identical; simplify the catch (both `*ValidationError` classes are `ValueError` subclasses, drop their now-unused imports):
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Consensus Log JSON file.")
    parser.add_argument("path", help="Path to Consensus Log JSON")
    parser.add_argument("game_log_path", help="Path to Game Log JSON")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.game_log_path)
        consensus_log = load_consensus_log(args.path, game)
    except (OSError, ValueError) as exc:
        print(f"invalid consensus log: {exc}")
        return 1

    print(
        "validated "
        f"consensus_log_id={consensus_log.consensus_log_id} "
        f"game_id={consensus_log.game_id} "
        f"consensuses={len(consensus_log.consensuses)} "
        f"source_label={consensus_log.source_label}"
    )
    return 0
```

`validate_failure_audit.py`:
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Failure Audit JSON file.")
    parser.add_argument("failure_audit_path", help="Path to Failure Audit JSON")
    parser.add_argument("game_log_path", help="Path to matching Game Log JSON")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.game_log_path)
        audit = load_failure_audit(args.failure_audit_path, game)
    except (OSError, ValueError) as exc:
        print(f"invalid failure audit: {exc}")
        return 1

    print(f"validated failure_audit game_id={audit.game_id}")
    print(f"failures={len(audit.failures)}")
    print(f"source_label={audit.source_label}")
    return 0
```

`validate_log_bundle.py`:
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate cross-log Werewolf-agent bundle invariants.")
    parser.add_argument("game_log_path", help="Path to Game Log JSON")
    parser.add_argument("--decision-log", help="Path to Decision Log JSON")
    parser.add_argument("--consensus-log", help="Path to Consensus Log JSON")
    parser.add_argument("--failure-audit", help="Path to Failure Audit JSON")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.game_log_path)
        decision_log = load_decision_log(args.decision_log, game) if args.decision_log else None
        consensus_log = load_consensus_log(args.consensus_log, game) if args.consensus_log else None
        failure_audit = load_failure_audit(args.failure_audit, game) if args.failure_audit else None
        result = validate_log_bundle(
            game,
            decision_log=decision_log,
            consensus_log=consensus_log,
            failure_audit=failure_audit,
        )
    except (OSError, ValueError) as exc:
        print(f"invalid log bundle: {exc}")
        return 1

    print(f"validated log_bundle game_id={result.game_id}")
    print(f"decision_log={'enabled' if result.decision_log_enabled else 'disabled'}")
    print(f"consensus_log={'enabled' if result.consensus_log_enabled else 'disabled'}")
    print(f"failure_audit={'enabled' if result.failure_audit_enabled else 'disabled'}")
    print(f"team_consensus_links={result.team_consensus_links}")
    return 0
```

`validate_semantic_labels.py`:
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate saved S5 Semantic Label Log JSON.")
    parser.add_argument("game_log_path")
    parser.add_argument("decision_log_path")
    parser.add_argument("semantic_label_path")
    args = parser.parse_args(argv)

    try:
        game = load_game_log(args.game_log_path)
        decision_log = load_decision_log(args.decision_log_path, game)
        label_log = load_semantic_label_log(args.semantic_label_path, decision_log)
    except (OSError, ValueError) as exc:
        print(f"invalid semantic label log: {exc}")
        return 1

    print(f"validated semantic_label_log_id={label_log.label_log_id}")
    print(f"game_id={label_log.game_id}")
    print(f"labels={len(label_log.labels)}")
    print(f"source_label={label_log.source_label}")
    return 0
```

- [ ] **Step 4: Run new tests + the family's existing consumers**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_validate_clis.py tests/test_decision_log.py tests/test_semantic_labels.py tests/test_context_budget.py -q`
Expected: PASS.

- [ ] **Step 5: Update the file tree** (new file added):

Run: `node .codex/hooks/tree.mjs --force`

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/validate_*.py tests/test_validate_clis.py .oh-my-harness/tree.md
git commit -m "refactor(validate): uniform invalid-input contract + first CLI tests for all six validate_* (health-check D-5/T-2)"
```

---

### Task 4: Wire `validate_failure_audit` into `validate_brief.py` (closes the family's only dangling member)

**Files:**
- Modify: `scripts/dev/validate_brief.py:11-16` (`DEFAULT_COMMANDS`)
- Test: `tests/test_context_budget.py` (read first — extend only if it pins `DEFAULT_COMMANDS`)

- [ ] **Step 1: Read `tests/test_context_budget.py`** to see what it asserts about `validate_brief` (command names/count). If it pins the command list, extend the expectation in the same edit.

- [ ] **Step 2: Implement** — insert after the `validate_consensus_log` entry in `DEFAULT_COMMANDS`:

```python
    ("validate_failure_audit", [sys.executable, "-m", "werewolf_eval.validate_failure_audit", "docs/generated-games/g1c-wolf-consensus-failure-audit.json", "docs/generated-games/g1c-wolf-consensus-game-log.json"]),
```

(g1c is the canonical tested failure-audit pair; gold-game has no failure-audit fixture.)

- [ ] **Step 3: Verify end-to-end**

Run: `NO_PROXY='*' python scripts/dev/validate_brief.py --log-dir .logs/validate/plan-task4`
Expected: JSON summary with `"ok": true` and a `validate_failure_audit` entry with `"exit_code": 0`. (This also runs the full unit-test suite as its last command — budget a few minutes.)

- [ ] **Step 4: Run the pinning test**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_context_budget.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dev/validate_brief.py tests/test_context_budget.py
git commit -m "fix(validate): wire validate_failure_audit into validate_brief (health-check DEAD-LIKELY -> wiring gap closed)"
```

---

### Task 5: Remove the dead g1d example fixture (health-check DEAD-CONFIRMED)

**Files:**
- Delete: `docs/generated-games/g1d-fake-provider-failure-audit.example.json`

- [ ] **Step 1: Re-verify zero references right before deleting**

Run: `git grep -l "g1d-fake-provider-failure-audit" -- ':!docs/harness' ':!docs/health-check' ':!docs/HEALTH_CHECK_2026-06-08.md'`
Expected: no hits in `src/`, `tests/`, `scripts/`, `tools/` (history/plan docs referencing it are fine and stay).

- [ ] **Step 2: Delete + update tree**

```bash
git rm docs/generated-games/g1d-fake-provider-failure-audit.example.json
node .codex/hooks/tree.mjs --force
```

- [ ] **Step 3: Run the fixture-consuming tests to prove zero regression**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_failure_audit.py tests/test_fake_provider_game.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add .oh-my-harness/tree.md
git commit -m "chore(fixtures): remove orphan g1d failure-audit example (health-check DEAD-CONFIRMED, zero consumers)"
```

---

### Task 6: E-5 — mark `run_emergent_game.py` as the log-only/no-spine runner

**Files:**
- Modify: `src/werewolf_eval/run_emergent_game.py:1-6` (docstring only)

- [ ] **Step 1: Check nothing pins the docstring**

Run: `git grep -n "P2-A-1 emergent Werewolf engine" -- tests/`
Expected: no hits (if a static-contract test pins wording, update it in the same commit).

- [ ] **Step 2: Implement** — extend the module docstring's first paragraph:

```python
"""CLI runner for the P2-A-1 emergent Werewolf engine.

LEGACY/log-only: this CLI deliberately does NOT wire the observer runtime spine
(no events.jsonl/snapshots) — the canonical product path is
``run_emergent_fake_runtime`` (used by the observer launcher). Kept for quick
log-only runs and its own regression test (health-check E-5).

Fake-deterministic by default (offline, free, reproducible). Writes the four
...(rest of the existing docstring unchanged)...
"""
```

- [ ] **Step 3: Run its test**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_run_emergent_game.py -q`
Expected: PASS (docstring-only change).

- [ ] **Step 4: Commit**

```bash
git add src/werewolf_eval/run_emergent_game.py
git commit -m "docs(entrypoints): mark run_emergent_game as LEGACY/log-only vs spine runner (health-check E-5)"
```

---

### Task 7: Full-suite validation + report

- [ ] **Step 1: Full suite**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q`
Expected: all green (baseline on main was ~1107 OK; this branch adds ~10 tests).

- [ ] **Step 2: Validation report** (AGENTS.md contract) — produce and include in the PR/handoff:
  - `git diff --stat main...HEAD` and `git diff --name-only main...HEAD`
  - Allowlist check: every changed path ∈ {`deepseek_provider.py`, `deepseek_launcher.py`, `run_emergent_deepseek_game.py`, `run_deepseek_provider_game.py`, `run_deepseek_consensus_game.py`, `validate_*.py` ×6, `run_emergent_game.py`, `scripts/dev/validate_brief.py`, `tests/test_deepseek_provider.py`, `tests/test_provider_registry.py`, `tests/test_validate_clis.py`, `tests/test_context_budget.py`, deleted g1d example, `.oh-my-harness/tree.md`, this plan}.
  - Forbidden-scope check: **zero** changes to `emergent_engine.py`, `action_runtime/**`, `invariants/**`, `observer_visibility.py`, `scoring.py`, prompts/renderers, `docs/ROADMAP.md`, `docs/TASKS.md`, `docs/adr/**`, `.agents/skills/**`, `.github/**`.

- [ ] **Step 3: Hand off integration** via superpowers:finishing-a-development-branch (merge to main per the repo's cross-tree recipe `git fetch . <branch>:main`, only after review; pushing follows the testing-and-process-control git recipe).

---

## Self-Review (done at planning time)

- **Spec coverage:** D-3→Task 1, D-4→Task 2, D-5+T-2→Task 3, wiring gap→Task 4, DEAD-CONFIRMED→Task 5, E-5→Task 6. ✓
- **Placeholder scan:** all code steps carry full code; the only "check first" steps (Task 4 Step 1, Task 6 Step 1) are explicit read-then-decide gates with the decision rule stated. ✓
- **Type consistency:** `main(argv: list[str] | None = None)` uniform across all six CLIs; `build_provider("deepseek", config)` matches `provider_registry.py:187` signature; subclass keeps `DeepSeekProviderConfig` constructor signature. ✓
- **Known byte-contracts respected:** validate CLI success stdout unchanged; deepseek registry stamp is a no-op (class defaults == spec values); prompt bytes untouched (no model-visible files in scope). ✓

# Prompt Versioning & Evaluation Comparison Tuple — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the prompt-versioning mechanism from `docs/superpowers/specs/2026-06-10-prompt-versioning-design.md`: version constants, the evaluation comparison tuple, golden-prompt byte locks with CI guards, the prompt-version ledger, and tuple stamping into non-frozen runtime artifacts.

**Architecture:** Two tiny new constant modules (`prompt_version.py`, `evaluation_versions.py`) feed a single `evaluation_bucket()` source. A canonical-sample module (`prompt_goldens.py`) renders the full baseline prompt chain into named samples; a generation tool writes them as full-text golden files under `tests/golden_prompts/<version>/`, and a guard test enforces the three CI rules byte-exactly. Stamping is additive-only into prompt-manifest, status.json, score-log dict, and settlement bundle — never into byte-frozen game logs.

**Tech Stack:** Python 3.12 stdlib only (unittest, hashlib, json, pathlib). No new dependencies. Tests run via the existing `python -m unittest discover -s tests -p "test_*.py"`.

**HARD CONSTRAINTS (from spec + review):**

1. **Zero prompt byte change.** This plan must not alter any rendered prompt byte. `prompt_v1` golden files lock the CURRENT rendering as-is. If any step appears to require changing prompt text — STOP, that step is wrong.
2. **Do NOT touch `.github/workflows/tests.yml`.** Verified: it runs `python -m unittest discover -s tests -p "test_*.py"`, which auto-discovers every new `tests/test_*.py` file. No workflow change is needed. If an implementer believes a workflow change is required, that belief is a bug in the plan — stop and escalate; `.github/**` changes are NOT authorized by this plan.
3. **Frozen artifacts untouched:** never write version fields into game-log / decision-log / consensus-log writers, and never edit files under `docs/generated-games/` EXCEPT the new `prompt-version-ledger.json` (explicitly authorized by the spec §6.1 and this plan). **Separately authorized (plan-review finding 2):** the gold score-log EXPECTATION files `docs/gold-game/s2-score-log.json` and `docs/gold-game/s5-score-log.json` MUST be regenerated in Task 9 — they are whole-dict `assertEqual` targets in `tests/test_scoring.py`, not byte-frozen replay gates. No other `docs/gold-game/` file may be touched.
4. Initial ledger entry: `golden_prompt_hashes.before` is **null**; `.after` records the full prompt_v1 sample hash map (review decision).
5. Pre-verified facts implementers may rely on: fake providers never call the prompt builders; the g1 score-log fixture tests (`test_scripted_game_runner.py:122-147`, `test_game_engine.py:179-206`) are structural/provenance checks, NOT byte comparisons — **but `tests/test_scoring.py:47-50` and `:262-269` DO whole-dict-compare against the s2/s5 gold files** (hence constraint 3's regeneration). Caution: provider traces DO carry the rendered `observation_text` (ProviderRequest is asdict'ed into provider-trace.json); harmless for this zero-byte plan, but do NOT rely on "traces contain no rendered prompt text" at future bumps.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/werewolf_eval/prompt_version.py` | Create | `PROMPT_VERSION` constant — single source |
| `src/werewolf_eval/evaluation_versions.py` | Create | `SCORING_VERSION`, `UNKNOWN_VERSION`, `evaluation_bucket()`, `read_manifest_bucket()` (Task 8) — single source for tuple+key; imports NOTHING from werewolf_eval (anti-circular-import rule; stdlib json/pathlib only) |
| `src/werewolf_eval/prompt_goldens.py` | Create | `canonical_prompt_samples()` — the one place the golden sample set is defined; imported by both the guard test and the generation tool |
| `tools/generate_golden_prompts.py` | Create | Writes `tests/golden_prompts/<PROMPT_VERSION>/*.txt` + prints sha256 map |
| `tests/golden_prompts/prompt_v1/*.txt` | Generate | Full-text golden files (UTF-8, LF, byte-exact) |
| `.gitattributes` | Create/Modify | `tests/golden_prompts/** text eol=lf` |
| `docs/generated-games/prompt-version-ledger.json` | Create | Ledger with prompt_v1 initial entry |
| `tests/test_evaluation_versions.py` | Create | Unit tests for constants + bucket |
| `tests/test_prompt_versioning.py` | Create | CI rules 1–3 guard tests + ledger checks |
| `src/werewolf_eval/llm_providers.py` | Modify | `BaseChatProvider` runtime-kind declaration (class attrs only — NO prompt text change) |
| `src/werewolf_eval/fake_provider.py` | Modify | `DeterministicFakeProvider` runtime-kind declaration |
| `src/werewolf_eval/runtime_events.py:560-606` | Modify | `build_prompt_manifest` gains `evaluation_bucket` / `prompt_used_by_runtime` kwargs |
| `src/werewolf_eval/emergent_engine.py` (~line 281 + ~line 919) | Modify | Expose `self.rules_version` from the constructed ruleset; byte-neutral extraction of the hunter-shot observation suffix into `HUNTER_SHOT_OBSERVATION_SUFFIX` (Task 3) |
| `src/werewolf_eval/run_emergent_fake_runtime.py`, `run_g1h_fake_runtime.py`, `run_emergent_deepseek_game.py`, `run_deepseek_consensus_game.py` | Modify | Pass bucket + flag into `build_prompt_manifest` (consensus runner has TWO call sites: ~143 failure branch + ~210 success branch); `run_g1h_fake_runtime.py:32`'s PRIVATE `_DeterministicFakeProvider` copy class also gets the runtime-kind declarations (Task 6) |
| `src/werewolf_eval/observer_protocol.py:191-205` | Modify | `write_run_status` gains optional bucket + preserve semantics |
| `src/werewolf_eval/observer_server.py:489` | Modify | Completion write passes bucket via `read_manifest_bucket(run_dir)` |
| `src/werewolf_eval/scoring.py:104` | Modify | `score_log_to_dict` stamps the bucket (unknown-fallback) |
| `src/werewolf_eval/settlement_bundle.py` | Modify | `build_settlement_bundle` gains `evaluation_bucket` kwarg; settle entry wires it from the run's manifest; **bump `BUNDLE_VERSION` (`p2d.settlement.v1` → `v2`)** so cached pre-bucket bundles self-heal (R-08 contract) |
| `docs/gold-game/s2-score-log.json`, `docs/gold-game/s5-score-log.json` | Regenerate | Whole-dict assertEqual expectation files — gain the `evaluation_bucket` key (Task 9, mandatory) |
| `docs/PROJECT_MAP.md` (SYS-B1 row) | Modify | Status note: prompt versioning mechanism landed |

Conventions (copy from `tests/test_action_runtime_registry.py`): every test file starts with

```python
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
```

---

### Task 1: `evaluation_versions.py` — tuple single source

**Files:**
- Create: `src/werewolf_eval/evaluation_versions.py`
- Test: `tests/test_evaluation_versions.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.evaluation_versions import (
    SCORING_VERSION,
    UNKNOWN_VERSION,
    evaluation_bucket,
)


class EvaluationVersionsTests(unittest.TestCase):
    def test_scoring_version_initial_value(self) -> None:
        self.assertEqual(SCORING_VERSION, "scoring_v1")

    def test_unknown_version_sentinel(self) -> None:
        self.assertEqual(UNKNOWN_VERSION, "unknown")

    def test_bucket_shape_and_key_format(self) -> None:
        b = evaluation_bucket(
            rules_version="rules_v1_1",
            prompt_version="prompt_v1",
            scoring_version=SCORING_VERSION,
        )
        self.assertEqual(
            b,
            {
                "rules_version": "rules_v1_1",
                "prompt_version": "prompt_v1",
                "scoring_version": "scoring_v1",
                "comparison_key": "rules_v1_1__prompt_v1__scoring_v1",
            },
        )

    def test_bucket_requires_keyword_args(self) -> None:
        with self.assertRaises(TypeError):
            evaluation_bucket("rules_v1_1", "prompt_v1", "scoring_v1")  # type: ignore[misc]

    def test_unknown_components_form_browsable_key(self) -> None:
        b = evaluation_bucket(
            rules_version=UNKNOWN_VERSION,
            prompt_version=UNKNOWN_VERSION,
            scoring_version=SCORING_VERSION,
        )
        self.assertEqual(b["comparison_key"], "unknown__unknown__scoring_v1")

    def test_module_has_no_werewolf_eval_imports(self) -> None:
        # Anti-circular-import contract (spec §4.1): callers of the tuple must not
        # transitively import scoring or any other werewolf_eval module.
        # AST-based on purpose: a substring check would be tripped by the module's
        # own docstring mentioning the package name (plan-review finding 4).
        import ast

        import werewolf_eval.evaluation_versions as ev

        tree = ast.parse(Path(ev.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                bad = [a.name for a in node.names if a.name.startswith("werewolf_eval")]
                self.assertFalse(bad, f"forbidden import: {bad}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                self.assertFalse(mod.startswith("werewolf_eval"), f"forbidden import from: {mod}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_evaluation_versions -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'werewolf_eval.evaluation_versions'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Evaluation comparison tuple — single source (spec 2026-06-10-prompt-versioning).

Deliberately imports NOTHING from werewolf_eval: run-status / manifest / scoring
writers all call evaluation_bucket(), and none of them may be forced to import the
scoring main module (circular-import guard, spec §4.1). scoring.py imports
SCORING_VERSION from here — never the reverse.
"""
from __future__ import annotations

SCORING_VERSION = "scoring_v1"

# Legacy artifacts with no version fields read as "unknown" for every missing
# component. The unknown bucket is browsable but never rankable (spec §4.5).
UNKNOWN_VERSION = "unknown"


def evaluation_bucket(
    *, rules_version: str, prompt_version: str, scoring_version: str
) -> dict[str, str]:
    """The leaderboard bucket: results are comparable ONLY within one identical
    tuple. All stamping sites MUST call this — hand-assembled tuples are forbidden
    (single source for the key format)."""
    return {
        "rules_version": rules_version,
        "prompt_version": prompt_version,
        "scoring_version": scoring_version,
        "comparison_key": f"{rules_version}__{prompt_version}__{scoring_version}",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_evaluation_versions -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/evaluation_versions.py tests/test_evaluation_versions.py
git commit -m "feat(versioning): evaluation_versions module — SCORING_VERSION + evaluation_bucket single source"
```

### Task 2: `prompt_version.py` — declared prompt version

**Files:**
- Create: `src/werewolf_eval/prompt_version.py`
- Modify (test): `tests/test_evaluation_versions.py` (append one test class)

- [ ] **Step 1: Append the failing test to `tests/test_evaluation_versions.py`**

```python
class PromptVersionTests(unittest.TestCase):
    def test_initial_prompt_version(self) -> None:
        from werewolf_eval.prompt_version import PROMPT_VERSION

        self.assertEqual(PROMPT_VERSION, "prompt_v1")

    def test_version_label_format(self) -> None:
        # Human-readable label, not a hash (review decision: hash is the lock,
        # the label is the product/leaderboard tag).
        from werewolf_eval.prompt_version import PROMPT_VERSION

        self.assertRegex(PROMPT_VERSION, r"^prompt_v\d+$")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_evaluation_versions -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'werewolf_eval.prompt_version'`

- [ ] **Step 3: Write minimal implementation** — `src/werewolf_eval/prompt_version.py`:

```python
"""Declared baseline prompt version (spec 2026-06-10-prompt-versioning §3).

Bump rule: ANY model-visible byte change in the rendered baseline prompt
assembly chain (build_action_system_prompt / build_speech_system_prompt /
compose_system / render_observation_text — incl. augment_witch_observation
and HUNTER_SHOT_OBSERVATION_SUFFIX, the model-visible inline augmentations)
requires bumping this constant, regenerating tests/golden_prompts/<version>/,
and adding a ledger entry in docs/generated-games/prompt-version-ledger.json.
No cosmetic exemption. Enforced byte-exactly by tests/test_prompt_versioning.py.
"""
from __future__ import annotations

PROMPT_VERSION = "prompt_v1"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m unittest tests.test_evaluation_versions -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/prompt_version.py tests/test_evaluation_versions.py
git commit -m "feat(versioning): PROMPT_VERSION constant (prompt_v1)"
```

### Task 3: `prompt_goldens.py` — canonical sample set

**Files:**
- Create: `src/werewolf_eval/prompt_goldens.py`
- Test: `tests/test_prompt_versioning.py` (first test class only; guard rules come in Task 5)

The sample set covers every link of the chain: action prompts for all 5 roles × their phases (incl. hunter day-vote and hunter-shot), speech prompts, persona composition, observation rendering with events and known roles, and BOTH model-visible inline augmentations — the witch victim line AND the hunter-shot suffix (`emergent_engine.py:919` appends `"\n你已出局,..."` to the hunter's observation; same class as the witch augmentation, so same byte-lock reasoning applies — plan-review finding 5).

- [ ] **Step 0: Byte-neutral extraction of the hunter-shot suffix.** In `emergent_engine.py`, add next to `augment_witch_observation` (~line 167):

```python
# Model-visible inline augmentation (byte-locked via tests/golden_prompts —
# spec 2026-06-10-prompt-versioning §3). Changing this string requires a
# PROMPT_VERSION bump.
HUNTER_SHOT_OBSERVATION_SUFFIX = "\n你已出局,作为猎人可开枪带走一名存活玩家,或选择不开枪。"
```

and at ~line 919 replace the inline literal so the request uses `observation_text=rendered.text + HUNTER_SHOT_OBSERVATION_SUFFIX`. **The constant's value MUST be copied byte-for-byte from the existing inline literal** (source-only refactor; rendered bytes unchanged per spec §3). Run `python -m unittest tests.test_action_runtime_hunter -v` → PASS (hunter scripts unchanged) before proceeding.

- [ ] **Step 1: Write the failing test** — `tests/test_prompt_versioning.py`:

```python
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.prompt_goldens import canonical_prompt_samples

EXPECTED_SAMPLE_NAMES = {
    "action_werewolf_night",
    "action_seer_night",
    "action_witch_night",
    "action_villager_day_vote",
    "action_hunter_day_vote",
    "action_hunter_shot",
    "speech_villager_day1",
    "speech_werewolf_day1",
    "compose_persona_action",
    "obs_villager_day",
    "obs_werewolf_night",
    "obs_witch_night_victim",
    "obs_witch_night_no_victim",
    "obs_hunter_shot",
}


class CanonicalSampleTests(unittest.TestCase):
    def test_sample_set_complete_unique_nonempty(self) -> None:
        samples = canonical_prompt_samples()
        names = [name for name, _ in samples]
        self.assertEqual(sorted(names), sorted(set(names)), "duplicate sample names")
        self.assertEqual(set(names), EXPECTED_SAMPLE_NAMES)
        for name, text in samples:
            self.assertIsInstance(text, str)
            self.assertTrue(text, f"empty rendered sample: {name}")

    def test_samples_are_deterministic(self) -> None:
        a = dict(canonical_prompt_samples())
        b = dict(canonical_prompt_samples())
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_prompt_versioning -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'werewolf_eval.prompt_goldens'`

- [ ] **Step 3: Write the implementation** — `src/werewolf_eval/prompt_goldens.py`:

```python
"""Canonical golden-prompt sample set (spec 2026-06-10-prompt-versioning §5).

The ONE definition of which rendered prompts are byte-locked. Imported by
tests/test_prompt_versioning.py (the lock) and tools/generate_golden_prompts.py
(the generator) so the two can never drift.

Fixtures are hand-frozen literals — they must NEVER depend on RNG, time, or
engine state, or the lock becomes nondeterministic.
"""
from __future__ import annotations

from werewolf_eval.emergent_engine import (
    HUNTER_SHOT_OBSERVATION_SUFFIX,
    augment_witch_observation,
    render_observation_text,
)
from werewolf_eval.game_engine import AgentObservation
from werewolf_eval.llm_providers import (
    build_action_system_prompt,
    build_speech_system_prompt,
    compose_system,
)
from werewolf_eval.provider_contract import ProviderRequest

_ALIVE = ["p1", "p2", "p3", "p4", "p5", "p6"]

_EVENTS = {
    "e1": {"round": 1, "phase": "night", "data": {"summary": "夜晚开始。"}},
    "e2": {"round": 1, "phase": "day", "data": {"summary": "p2 死亡。"}},
}


def _req(
    actor: str,
    phase: str,
    allowed_actions: list[str],
    allowed_targets: list[str],
    response_kind: str = "action",
) -> ProviderRequest:
    return ProviderRequest(
        request_id="golden_fixture",
        game_id="golden_fixture",
        actor=actor,
        phase=phase,
        round=1,
        observation={},
        allowed_actions=allowed_actions,
        allowed_targets=allowed_targets,
        response_kind=response_kind,
    )


def _obs(player_id: str, role: str, team: str, phase: str, known: dict[str, str]) -> AgentObservation:
    return AgentObservation(
        game_id="golden_fixture",
        player_id=player_id,
        role=role,
        team=team,
        phase=phase,
        round=1,
        alive_players=list(_ALIVE),
        public_event_ids=["e1", "e2"],
        private_event_ids=[],
        known_roles=known,
    )


def canonical_prompt_samples() -> list[tuple[str, str]]:
    villager_vote = _req("p5", "day", ["player_vote"], _ALIVE)
    witch_obs = render_observation_text(
        _obs("p4", "witch", "villager", "night", {"p4": "witch"}), _EVENTS
    ).text
    return [
        ("action_werewolf_night",
         build_action_system_prompt(_req("p1", "night", ["werewolf_kill"], _ALIVE))),
        ("action_seer_night",
         build_action_system_prompt(_req("p3", "night", ["seer_check"], _ALIVE))),
        ("action_witch_night",
         build_action_system_prompt(
             _req("p4", "night", ["witch_save", "witch_poison", "witch_pass"], _ALIVE))),
        ("action_villager_day_vote", build_action_system_prompt(villager_vote)),
        ("action_hunter_day_vote",
         build_action_system_prompt(_req("p6", "day", ["player_vote"], _ALIVE))),
        ("action_hunter_shot",
         build_action_system_prompt(
             _req("p6", "hunter_shot", ["hunter_shoot", "hunter_pass"], _ALIVE))),
        ("speech_villager_day1",
         build_speech_system_prompt(_req("p5", "day", [], [], response_kind="speech"))),
        ("speech_werewolf_day1",
         build_speech_system_prompt(_req("p1", "day", [], [], response_kind="speech"))),
        ("compose_persona_action",
         compose_system("你是谨慎的分析型玩家。", build_action_system_prompt(villager_vote))),
        ("obs_villager_day",
         render_observation_text(
             _obs("p5", "villager", "villager", "day", {"p5": "villager"}), _EVENTS).text),
        ("obs_werewolf_night",
         render_observation_text(
             _obs("p1", "werewolf", "werewolf", "night",
                  {"p1": "werewolf", "p2": "werewolf"}), _EVENTS).text),
        ("obs_witch_night_victim", augment_witch_observation(witch_obs, "p5")),
        ("obs_witch_night_no_victim", augment_witch_observation(witch_obs, None)),
        ("obs_hunter_shot",
         render_observation_text(
             _obs("p6", "hunter", "villager", "hunter_shot", {"p6": "hunter"}), _EVENTS
         ).text + HUNTER_SHOT_OBSERVATION_SUFFIX),
    ]
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m unittest tests.test_prompt_versioning -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/prompt_goldens.py src/werewolf_eval/emergent_engine.py tests/test_prompt_versioning.py
git commit -m "feat(versioning): canonical golden-prompt sample set (14 samples incl. hunter-shot suffix, byte-neutral extraction)"
```

### Task 4: golden files + `.gitattributes` + generation tool

**Files:**
- Create: `tools/generate_golden_prompts.py`
- Create: `.gitattributes` entry (file may not exist yet — check first; append if it does)
- Generate: `tests/golden_prompts/prompt_v1/*.txt`

- [ ] **Step 1: Write the generation tool** — `tools/generate_golden_prompts.py`:

```python
"""Regenerate tests/golden_prompts/<PROMPT_VERSION>/ from the canonical sample set.

Run from repo root:  python tools/generate_golden_prompts.py
Prints the sha256 fingerprint map for the ledger's golden_prompt_hashes field.
Writes bytes directly (no newline translation) — .gitattributes pins LF.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.prompt_goldens import canonical_prompt_samples
from werewolf_eval.prompt_version import PROMPT_VERSION


def main() -> None:
    out_dir = ROOT / "tests" / "golden_prompts" / PROMPT_VERSION
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for name, text in canonical_prompt_samples():
        data = text.encode("utf-8")
        (out_dir / f"{name}.txt").write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    print(json.dumps({PROMPT_VERSION: hashes}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add the `.gitattributes` rule**

Check whether `.gitattributes` exists at repo root (`ls -la /g/Werewolf-agent/.gitattributes`). Create or append this line:

```
tests/golden_prompts/** text eol=lf
```

- [ ] **Step 3: Generate the prompt_v1 goldens**

Run: `python tools/generate_golden_prompts.py`
Expected: prints a JSON map of 14 sample names → sha256 hex digests. **Save this output — Task 5 pastes it into the ledger.**
Verify: `ls tests/golden_prompts/prompt_v1/` shows 14 `.txt` files; spot-check one (`cat tests/golden_prompts/prompt_v1/action_villager_day_vote.txt`) — it must read as a plausible current prompt, e.g. starting `You are p5 in a Werewolf game (round 1, phase day).`

- [ ] **Step 4: Verify LF bytes survived git**

Run: `git add .gitattributes tests/golden_prompts tools/generate_golden_prompts.py && git status --short`
Then: `python -c "p=open('tests/golden_prompts/prompt_v1/obs_villager_day.txt','rb').read(); assert b'\r' not in p, 'CRLF leaked'; print('LF clean')"`
Expected: `LF clean`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(versioning): prompt_v1 golden files (full text, UTF-8+LF) + generation tool + gitattributes"
```

### Task 5: ledger + CI guard rules 1–3

**Files:**
- Create: `docs/generated-games/prompt-version-ledger.json`
- Modify (test): `tests/test_prompt_versioning.py` (append the guard class)

- [ ] **Step 1: Write the ledger initial entry** — `docs/generated-games/prompt-version-ledger.json` (paste the REAL hash map printed by Task 4 Step 3 into `after`; set the real date):

```json
[
  {
    "prompt_version": "prompt_v1",
    "base_version": null,
    "reason": "initial baseline lock — freeze the current rendering as the archived reference anchor",
    "expected_change": "none (mechanism landing; zero prompt byte change is an acceptance criterion)",
    "touched_chain": [],
    "golden_prompt_hashes": {
      "before": null,
      "after": { "<PASTE the sample->sha256 map printed by tools/generate_golden_prompts.py>": "..." }
    },
    "behavior_evidence": {
      "status": "not_applicable",
      "reason_if_not_run": "initial version; no behavior change to evidence"
    },
    "blessed_by": "user (spec review 2026-06-10)",
    "blessed_at": "2026-06-10"
  }
]
```

- [ ] **Step 2: Append the failing guard tests** to `tests/test_prompt_versioning.py`:

```python
from werewolf_eval.prompt_version import PROMPT_VERSION

GOLDEN_ROOT = ROOT / "tests" / "golden_prompts"
LEDGER_PATH = ROOT / "docs" / "generated-games" / "prompt-version-ledger.json"


def _ledger() -> list[dict]:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def _current_entry() -> dict:
    matches = [e for e in _ledger() if e.get("prompt_version") == PROMPT_VERSION]
    assert len(matches) == 1, f"expected exactly one ledger entry for {PROMPT_VERSION}"
    return matches[0]


class PromptVersionGuardTests(unittest.TestCase):
    """The three CI rules of spec §5.2 — all hard FAIL, no warnings."""

    def test_rule1_rendered_bytes_match_current_golden(self) -> None:
        golden_dir = GOLDEN_ROOT / PROMPT_VERSION
        self.assertTrue(
            golden_dir.is_dir(),
            f"no golden dir for {PROMPT_VERSION}: run tools/generate_golden_prompts.py "
            f"and add a ledger entry (rule 2)",
        )
        samples = dict(canonical_prompt_samples())
        files = {p.stem: p for p in golden_dir.glob("*.txt")}
        self.assertEqual(
            sorted(samples), sorted(files),
            "sample set drifted from golden files — regenerate goldens under a version bump",
        )
        for name, text in samples.items():
            self.assertEqual(
                files[name].read_bytes(),
                text.encode("utf-8"),
                f"RULE 1: rendered prompt bytes changed for '{name}' without a "
                f"PROMPT_VERSION bump. Any model-visible byte change requires a new "
                f"prompt_version + regenerated goldens + a ledger entry (no cosmetic "
                f"exemption).",
            )

    def test_rule2_ledger_entry_and_hashes_exist_for_current_version(self) -> None:
        entry = _current_entry()
        for field in ("reason", "expected_change", "behavior_evidence", "blessed_by", "blessed_at"):
            self.assertIn(field, entry, f"RULE 2: ledger entry missing '{field}'")
        after = entry["golden_prompt_hashes"]["after"]
        samples = dict(canonical_prompt_samples())
        self.assertEqual(
            sorted(after), sorted(samples),
            "RULE 2: ledger golden_prompt_hashes.after does not cover the sample set",
        )
        import hashlib

        for name, text in samples.items():
            self.assertEqual(
                after[name],
                hashlib.sha256(text.encode("utf-8")).hexdigest(),
                f"RULE 2: ledger hash stale for '{name}'",
            )

    def test_rule2_behavior_evidence_contract(self) -> None:
        ev = _current_entry()["behavior_evidence"]
        self.assertIn(ev["status"], ("not_run", "attached", "not_applicable"))
        if ev["status"] != "attached":
            self.assertTrue(
                str(ev.get("reason_if_not_run", "")).strip(),
                "RULE 2: behavior evidence omitted without a stated reason",
            )

    def test_rule3_no_meaningless_bump(self) -> None:
        entry = _current_entry()
        base = entry.get("base_version")
        if base is None:
            self.skipTest("initial version has no base to compare")
        base_dir = GOLDEN_ROOT / base
        cur_dir = GOLDEN_ROOT / PROMPT_VERSION
        base_files = {p.stem: p.read_bytes() for p in base_dir.glob("*.txt")}
        cur_files = {p.stem: p.read_bytes() for p in cur_dir.glob("*.txt")}
        self.assertFalse(
            base_files == cur_files,
            f"RULE 3: {PROMPT_VERSION} is byte-identical to {base} — meaningless bump",
        )
```

- [ ] **Step 3: Run to verify the guards pass against the real goldens/ledger**

Run: `python -m unittest tests.test_prompt_versioning -v`
Expected: PASS (rule 3 reports skipped for prompt_v1). If rule 2 fails on hashes, the ledger paste in Step 1 is wrong — re-run the generator and re-paste.

- [ ] **Step 4: Negative check (manual, do not commit the mutation)**

Temporarily append a space to one golden file, re-run, confirm RULE 1 fires; revert:

```bash
echo -n " " >> tests/golden_prompts/prompt_v1/speech_villager_day1.txt
python -m unittest tests.test_prompt_versioning -v   # expect RULE 1 FAIL
git checkout -- tests/golden_prompts/prompt_v1/speech_villager_day1.txt
python -m unittest tests.test_prompt_versioning -v   # expect PASS again
```

- [ ] **Step 5: Commit**

```bash
git add docs/generated-games/prompt-version-ledger.json tests/test_prompt_versioning.py
git commit -m "feat(versioning): prompt-version ledger (prompt_v1 initial entry) + CI guard rules 1-3"
```

### Task 6: provider runtime-kind declarations

**Files:**
- Modify: `src/werewolf_eval/llm_providers.py` (`BaseChatProvider`, class body top, ~line 133)
- Modify: `src/werewolf_eval/fake_provider.py` (`DeterministicFakeProvider`, class body top, ~line 14)
- Modify: `src/werewolf_eval/run_g1h_fake_runtime.py` (~line 32 — **a PRIVATE `_DeterministicFakeProvider` copy class that does NOT inherit the public one**; plan-review finding 3: without its own declaration, Task 7's `getattr(..., True)` default stamps the g1h fake run as `prompt_used_by_runtime=True` — a lying manifest violating spec §4.4/§9.4)
- Modify (test): `tests/test_evaluation_versions.py` (append)

`OpenAICompatibleProvider` / `OpenAIProvider` / `AnthropicProvider` / `DeepSeekProvider` all inherit from `BaseChatProvider` — one declaration covers every live provider. Fake providers are TWO independent classes (public + the g1h private copy); both must declare.

- [ ] **Step 1: Append the failing test**

```python
class ProviderRuntimeKindTests(unittest.TestCase):
    def test_live_providers_declare_baseline_prompt_use(self) -> None:
        from werewolf_eval.llm_providers import BaseChatProvider

        self.assertEqual(BaseChatProvider.provider_runtime_kind, "live_model")
        self.assertTrue(BaseChatProvider.uses_baseline_prompt)

    def test_fake_provider_declares_no_prompt_use(self) -> None:
        from werewolf_eval.fake_provider import DeterministicFakeProvider

        self.assertEqual(
            DeterministicFakeProvider.provider_runtime_kind, "fake_deterministic"
        )
        self.assertFalse(DeterministicFakeProvider.uses_baseline_prompt)

    def test_deepseek_inherits_live_declaration(self) -> None:
        from werewolf_eval.deepseek_provider import DeepSeekProvider

        self.assertEqual(DeepSeekProvider.provider_runtime_kind, "live_model")
        self.assertTrue(DeepSeekProvider.uses_baseline_prompt)

    def test_g1h_private_fake_provider_also_declares(self) -> None:
        # run_g1h_fake_runtime has its OWN _DeterministicFakeProvider copy class
        # (no inheritance from the public one). Pin it so the g1h manifest can
        # never claim prompt_used_by_runtime=True (plan-review finding 3).
        from werewolf_eval.run_g1h_fake_runtime import _DeterministicFakeProvider

        self.assertEqual(
            _DeterministicFakeProvider.provider_runtime_kind, "fake_deterministic"
        )
        self.assertFalse(_DeterministicFakeProvider.uses_baseline_prompt)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_evaluation_versions -v`
Expected: FAIL — `AttributeError: ... has no attribute 'provider_runtime_kind'`

- [ ] **Step 3: Add the class attributes**

In `llm_providers.py`, first lines inside `class BaseChatProvider:` (after its docstring):

```python
    # Spec 2026-06-10-prompt-versioning §4.4: declared mechanism, NOT name-sniffing.
    # prompt_used_by_runtime is derived from these declarations by runners.
    provider_runtime_kind = "live_model"
    uses_baseline_prompt = True
```

In `fake_provider.py`, first lines inside `class DeterministicFakeProvider:` (note: this class has NO docstring — put the attributes as the first class-body lines):

```python
    # Scripted by (actor, phase, round) keys — never reads the rendered prompt.
    provider_runtime_kind = "fake_deterministic"
    uses_baseline_prompt = False
```

In `run_g1h_fake_runtime.py`, first lines inside `class _DeterministicFakeProvider:` (~line 32) — the SAME two attributes with the same comment (this private copy class inherits nothing; without its own declaration the g1h manifest lies).

- [ ] **Step 4: Run to verify it passes**

Run: `python -m unittest tests.test_evaluation_versions -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/llm_providers.py src/werewolf_eval/fake_provider.py src/werewolf_eval/run_g1h_fake_runtime.py tests/test_evaluation_versions.py
git commit -m "feat(versioning): provider runtime-kind + uses_baseline_prompt declarations (incl. g1h private fake class)"
```

### Task 7: manifest stamping (builder + engine attr + 4 runners)

**Files:**
- Modify: `src/werewolf_eval/runtime_events.py:560-606` (`build_prompt_manifest`)
- Modify: `src/werewolf_eval/emergent_engine.py` (~line 281, right after `_ruleset = rules_v1_1()`)
- Modify: `src/werewolf_eval/run_emergent_fake_runtime.py` (~line 135), `run_g1h_fake_runtime.py`, `run_emergent_deepseek_game.py`, `run_deepseek_consensus_game.py` (~line 143) — locate each call with `grep -n "build_prompt_manifest(" src/werewolf_eval/run_*.py`
- Modify (test): `tests/test_runtime_events.py` (append; existing manifest tests must stay green — the new kwargs are optional)

- [ ] **Step 1: Append the failing test to `tests/test_runtime_events.py`** (mirror its existing import style):

```python
class PromptManifestBucketTests(unittest.TestCase):
    def test_manifest_carries_bucket_and_flag_when_provided(self) -> None:
        manifest = build_prompt_manifest(
            run_id="r1",
            source_label="[test]",
            agents=[{"player_id": "p1", "role": "villager"}],
            evaluation_bucket={
                "rules_version": "rules_v1_1",
                "prompt_version": "prompt_v1",
                "scoring_version": "scoring_v1",
                "comparison_key": "rules_v1_1__prompt_v1__scoring_v1",
            },
            prompt_used_by_runtime=False,
        )
        self.assertEqual(manifest["evaluation_bucket"]["comparison_key"],
                         "rules_v1_1__prompt_v1__scoring_v1")
        self.assertIs(manifest["prompt_used_by_runtime"], False)

    def test_manifest_back_compat_without_new_kwargs(self) -> None:
        manifest = build_prompt_manifest(
            run_id="r1", source_label="[test]", agents=[]
        )
        self.assertNotIn("evaluation_bucket", manifest)
        self.assertNotIn("prompt_used_by_runtime", manifest)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_runtime_events -v`
Expected: FAIL — `TypeError: build_prompt_manifest() got an unexpected keyword argument 'evaluation_bucket'`

- [ ] **Step 3: Extend `build_prompt_manifest`** — change the signature and the final dict (runtime_events.py:560 and :601):

```python
def build_prompt_manifest(
    *,
    run_id: str,
    source_label: str,
    agents: list[dict[str, object]],
    evaluation_bucket: dict[str, str] | None = None,
    prompt_used_by_runtime: bool | None = None,
) -> dict[str, object]:
```

and replace the closing block (`manifest: dict[str, object] = {...}` / `return redact_secret_values(manifest)`) with:

```python
    manifest: dict[str, object] = {
        "run_id": run_id,
        "source_label": source_label,
        "agents": hashed_agents,
    }
    # Spec 2026-06-10-prompt-versioning §4.3: the tuple lands in run/eval
    # explanation artifacts, never in byte-frozen canonical game logs.
    if evaluation_bucket is not None:
        manifest["evaluation_bucket"] = dict(evaluation_bucket)
    if prompt_used_by_runtime is not None:
        manifest["prompt_used_by_runtime"] = bool(prompt_used_by_runtime)
    return redact_secret_values(manifest)  # type: ignore[return-value]
```

- [ ] **Step 4: Expose `rules_version` on the engine** — in `emergent_engine.py` `__init__`, immediately after the line `_ruleset = rules_v1_1()`:

```python
        self.rules_version = _ruleset.rules_version
```

- [ ] **Step 5: Wire the four runners.** For each `build_prompt_manifest(` call site, add the two kwargs. Pattern for the emergent runners (`run_emergent_fake_runtime.py`, `run_g1h_fake_runtime.py`, `run_emergent_deepseek_game.py`) — they construct the engine and the per-seat providers:

```python
    from werewolf_eval.evaluation_versions import SCORING_VERSION, evaluation_bucket
    from werewolf_eval.prompt_version import PROMPT_VERSION

    manifest = build_prompt_manifest(
        run_id=game_id,
        source_label=...,          # unchanged existing arg
        agents=[...],              # unchanged existing arg
        evaluation_bucket=evaluation_bucket(
            rules_version=engine.rules_version,
            prompt_version=PROMPT_VERSION,
            scoring_version=SCORING_VERSION,
        ),
        # getattr default True is the SAFE-for-live direction but LIES for an
        # undeclared fake provider — every fake provider class MUST declare
        # uses_baseline_prompt=False (pinned in test_evaluation_versions.py).
        prompt_used_by_runtime=any(
            getattr(p, "uses_baseline_prompt", True) for p in providers
        ),
    )
```

Adapt the local variable names per runner (`engine`, `providers` — find them above each call site). For the fake runtimes the flag computes to `False` via the Task 6 declarations — `run_emergent_fake_runtime` uses the public `DeterministicFakeProvider`, and `run_g1h_fake_runtime` uses its PRIVATE copy class which Task 6 also declared (plan-review finding 3: without that, g1h would stamp `True` through the getattr default). For `run_deepseek_consensus_game.py` — note it has **TWO** `build_prompt_manifest` call sites (~line 143 failure branch AND ~line 210 success branch); wire BOTH (non-emergent `game_engine` path — there is NO BoardRuleset on this path; claiming `rules_v1_1` would be a false statement):

```python
        evaluation_bucket=evaluation_bucket(
            rules_version=UNKNOWN_VERSION,  # consensus path predates RulesVariant; honest unknown
            prompt_version=PROMPT_VERSION,
            scoring_version=SCORING_VERSION,
        ),
        prompt_used_by_runtime=True,  # live DeepSeek providers consume the baseline prompt
```

(import `UNKNOWN_VERSION` alongside the others).

- [ ] **Step 6: Run the affected suites**

Run: `python -m unittest tests.test_runtime_events -v` → PASS
Run: `python -m unittest discover -s tests -p "test_*emergent*.py" -v` → PASS (runner smoke paths)

- [ ] **Step 7: Commit**

```bash
git add src/werewolf_eval/runtime_events.py src/werewolf_eval/emergent_engine.py src/werewolf_eval/run_*.py tests/test_runtime_events.py
git commit -m "feat(versioning): stamp evaluation bucket + prompt_used_by_runtime into prompt-manifest (4 runners)"
```

### Task 8: status stamping with preserve semantics

**Files:**
- Modify: `src/werewolf_eval/observer_protocol.py:191-205` (`write_run_status`)
- Modify: `src/werewolf_eval/evaluation_versions.py` (add `read_manifest_bucket` — stdlib only, keeps the no-werewolf_eval-imports contract)
- Modify: `src/werewolf_eval/observer_server.py:489` (the completion write)
- Modify (test): `tests/test_observer_protocol.py` — it ALREADY imports `write_run_status`/`read_run_status` (lines ~37/43) and has existing status tests (~52-67); append there (plan-review minor fix: do NOT create a new test file). Also append the `read_manifest_bucket` tests to `tests/test_evaluation_versions.py`.

- [ ] **Step 1: Append the failing tests to `tests/test_observer_protocol.py`** (mirror its existing imports — add `evaluation_bucket` usage as plain dict literals, no new imports needed):

```python
BUCKET = {
    "rules_version": "rules_v1_1",
    "prompt_version": "prompt_v1",
    "scoring_version": "scoring_v1",
    "comparison_key": "rules_v1_1__prompt_v1__scoring_v1",
}


class RunStatusBucketTests(unittest.TestCase):
    def test_status_carries_bucket_when_provided(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            write_run_status(run_dir, "completed", evaluation_bucket=BUCKET)
            payload = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["evaluation_bucket"], BUCKET)

    def test_later_write_without_bucket_preserves_it(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            write_run_status(run_dir, "running", evaluation_bucket=BUCKET)
            write_run_status(run_dir, "completed")  # no bucket passed
            payload = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["evaluation_bucket"], BUCKET,
                             "bucket lost on a bucket-less rewrite")

    def test_legacy_write_stays_minimal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            write_run_status(run_dir, "completed")
            payload = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(payload, {"status": "completed"})
```

(use `tempfile` — add it to the file's imports if not already present). And append to `tests/test_evaluation_versions.py`:

```python
class ReadManifestBucketTests(unittest.TestCase):
    def test_reads_bucket_from_stamped_manifest(self) -> None:
        import json
        import tempfile

        from werewolf_eval.evaluation_versions import read_manifest_bucket

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "prompt-manifest.json").write_text(
                json.dumps({"run_id": "r1", "evaluation_bucket": {
                    "rules_version": "rules_v1_1", "prompt_version": "prompt_v1",
                    "scoring_version": "scoring_v1",
                    "comparison_key": "rules_v1_1__prompt_v1__scoring_v1"}}),
                encoding="utf-8",
            )
            bucket = read_manifest_bucket(run_dir)
            self.assertEqual(bucket["comparison_key"], "rules_v1_1__prompt_v1__scoring_v1")

    def test_returns_none_for_legacy_or_missing_manifest(self) -> None:
        import tempfile

        from werewolf_eval.evaluation_versions import read_manifest_bucket

        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(read_manifest_bucket(Path(td)))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_observer_protocol tests.test_evaluation_versions -v`
Expected: FAIL — `TypeError: write_run_status() got an unexpected keyword argument 'evaluation_bucket'` and `ImportError: cannot import name 'read_manifest_bucket'`

- [ ] **Step 3: Extend `write_run_status`** (replace observer_protocol.py:191-205; keep the never-raise + atomic temp+replace contract):

```python
def write_run_status(
    run_dir: Path, status: str, evaluation_bucket: dict[str, str] | None = None
) -> None:
    """Persist the run status durably so it survives a server restart. The server's
    in-memory run_status dict is lost on bounce, which otherwise makes every prior
    completed run report 'unknown' and become permanently un-settleable (the
    settlement route gates on status=='completed'). Atomic temp+replace; best-effort
    (never raises into the run thread). A previously stamped evaluation_bucket is
    preserved across bucket-less rewrites (spec 2026-06-10-prompt-versioning §4.3)."""
    if status not in RUN_STATUS_VALUES:
        return
    try:
        payload: dict[str, object] = {"status": status}
        if evaluation_bucket is not None:
            payload["evaluation_bucket"] = dict(evaluation_bucket)
        else:
            try:
                prev = json.loads((run_dir / _STATUS_FILE).read_text(encoding="utf-8"))
                if isinstance(prev, dict) and "evaluation_bucket" in prev:
                    payload["evaluation_bucket"] = prev["evaluation_bucket"]
            except (OSError, ValueError):
                pass
        run_dir.mkdir(parents=True, exist_ok=True)
        tmp = run_dir / (_STATUS_FILE + ".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(run_dir / _STATUS_FILE)
    except OSError:
        pass
```

- [ ] **Step 4: Add the shared helper** to `src/werewolf_eval/evaluation_versions.py` (stdlib only — the module's no-werewolf_eval-imports contract holds; used by observer_server here and by the settle entry in Task 9):

```python
import json
from pathlib import Path


def read_manifest_bucket(run_dir: Path) -> dict[str, str] | None:
    """The run's stamped bucket, read from prompt-manifest.json (the single
    source). None for legacy runs without a stamped manifest."""
    try:
        manifest = json.loads(
            (run_dir / "prompt-manifest.json").read_text(encoding="utf-8")
        )
        bucket = manifest.get("evaluation_bucket")
        return dict(bucket) if isinstance(bucket, dict) else None
    except (OSError, ValueError):
        return None
```

Then wire the server completion write at `observer_server.py:489` (`write_run_status(state.runs_dir / run_id, status)`):

```python
        write_run_status(
            state.runs_dir / run_id,
            status,
            evaluation_bucket=read_manifest_bucket(state.runs_dir / run_id),
        )
```

(import `read_manifest_bucket` from `werewolf_eval.evaluation_versions` at the top of observer_server.py).

- [ ] **Step 5: Run to verify**

Run: `python -m unittest tests.test_observer_protocol tests.test_evaluation_versions tests.test_observer_server -v`
Expected: PASS (observer_server suite must stay green — the change is additive; note env limit: observer tests that need localhost HTTP are already skipped/designed around in this repo).

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/observer_protocol.py src/werewolf_eval/observer_server.py src/werewolf_eval/evaluation_versions.py tests/test_observer_protocol.py tests/test_evaluation_versions.py
git commit -m "feat(versioning): status.json carries evaluation_bucket (preserve-on-rewrite, mirrored from manifest via shared read_manifest_bucket)"
```

### Task 9: score-log + settlement-bundle stamping

**Files:**
- Modify: `src/werewolf_eval/scoring.py:104` (`score_log_to_dict`)
- Modify: `src/werewolf_eval/settlement_bundle.py` (bundle skeleton ~line 120-130 + the score-merge ~line 243)
- Modify (test): `tests/test_scoring.py` (append), `tests/test_settlement_bundle.py` (append)

- [ ] **Step 1: Append the failing test to `tests/test_scoring.py`** (reuse whatever ScoreLog factory/fixture the file already builds in its existing tests — e.g. score a loaded gold game; the assertion is on the dict shape only):

```python
class ScoreLogBucketTests(unittest.TestCase):
    def test_score_log_dict_default_stamps_unknown_bucket(self) -> None:
        score_log = _any_existing_scorelog_fixture()  # reuse the file's existing helper/pattern
        d = score_log_to_dict(score_log)
        self.assertEqual(
            d["evaluation_bucket"],
            {
                "rules_version": "unknown",
                "prompt_version": "unknown",
                "scoring_version": "scoring_v1",
                "comparison_key": "unknown__unknown__scoring_v1",
            },
        )

    def test_score_log_dict_accepts_explicit_bucket(self) -> None:
        score_log = _any_existing_scorelog_fixture()
        bucket = {
            "rules_version": "rules_v1_1",
            "prompt_version": "prompt_v1",
            "scoring_version": "scoring_v1",
            "comparison_key": "rules_v1_1__prompt_v1__scoring_v1",
        }
        d = score_log_to_dict(score_log, evaluation_bucket=bucket)
        self.assertEqual(d["evaluation_bucket"], bucket)
```

(`_any_existing_scorelog_fixture` is a placeholder NAME only for this plan's brevity in locating the right helper: the implementer MUST reuse the concrete ScoreLog the existing tests in `tests/test_scoring.py` already construct — e.g. the `score_game(...)` result used around its g1 tests — not invent a new fixture.)

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_scoring -v`
Expected: the two new tests FAIL (`KeyError: 'evaluation_bucket'`); all pre-existing tests still PASS. (After Step 3 the s2/s5 whole-dict gold comparisons at `tests/test_scoring.py:47-50` and `:262-269` will START failing — that is expected and is resolved by the MANDATORY gold regeneration in Step 5, plan-review finding 2.)

- [ ] **Step 3: Extend `score_log_to_dict`** (scoring.py:104; also add the import at the top of scoring.py: `from werewolf_eval.evaluation_versions import SCORING_VERSION, UNKNOWN_VERSION, evaluation_bucket as _evaluation_bucket`):

```python
def score_log_to_dict(
    score_log: ScoreLog, *, evaluation_bucket: dict[str, str] | None = None
) -> dict[str, Any]:
    d = asdict(score_log)
    # Spec 2026-06-10-prompt-versioning §4.3/§4.5: score records always carry the
    # bucket. Callers without version context (re-scoring legacy logs) get the
    # honest "unknown" stamp — browsable, never rankable.
    d["evaluation_bucket"] = (
        dict(evaluation_bucket)
        if evaluation_bucket is not None
        else _evaluation_bucket(
            rules_version=UNKNOWN_VERSION,
            prompt_version=UNKNOWN_VERSION,
            scoring_version=SCORING_VERSION,
        )
    )
    return d
```

- [ ] **Step 4: Stamp the settlement bundle — REAL bucket via the settle entry (plan-review finding 1).** `build_settlement_bundle` calls `score_game()` ITSELF internally (settlement_bundle.py:175) — there is no "loaded score-log dict" to copy from, and nothing inside the builder knows the run's versions. The bucket must flow in from the settle entry, which already holds `run_dir` and reads the manifest for `_load_seat_meta(run_dir)` (~line 353).

(a) Give `build_settlement_bundle` a kwarg, with unknown fallback (near the imports add `from werewolf_eval.evaluation_versions import SCORING_VERSION, UNKNOWN_VERSION, evaluation_bucket as _evaluation_bucket` and the helper):

```python
def _unknown_bucket() -> dict[str, str]:
    return _evaluation_bucket(
        rules_version=UNKNOWN_VERSION,
        prompt_version=UNKNOWN_VERSION,
        scoring_version=SCORING_VERSION,
    )
```

Add `evaluation_bucket: dict[str, str] | None = None` to `build_settlement_bundle`'s signature, and where the bundle dict is assembled (after the `bundle["score_records"] = [...]` merge ~line 243):

```python
    bundle["evaluation_bucket"] = (
        dict(evaluation_bucket) if evaluation_bucket is not None else _unknown_bucket()
    )
```

(b) Wire the settle entry (~line 353, next to `_load_seat_meta(run_dir)`): pass `evaluation_bucket=read_manifest_bucket(run_dir)` (the Task 8 shared helper from `evaluation_versions`) into the `build_settlement_bundle` call.

(c) **Bump `BUNDLE_VERSION`** at settlement_bundle.py:29: `"p2d.settlement.v1"` → `"p2d.settlement.v2"` (plan-review finding 6: the cache at :333 serves a bundle ONLY when bundle_version matches — without the bump, cached pre-bucket bundles would be served as current schema forever, violating the R-08 "never silently serve a stale schema" contract; with it, old caches recompute and self-heal).

(d) Tests in `tests/test_settlement_bundle.py` (mirror its existing builder/settle-entry call patterns): ① builder without kwarg → `bundle["evaluation_bucket"]["comparison_key"] == "unknown__unknown__scoring_v1"`; ② **settle entry with a run_dir containing a STAMPED prompt-manifest.json → bundle carries the REAL bucket** (`comparison_key == "rules_v1_1__prompt_v1__scoring_v1"`) — this is the test that catches finding 1's failure mode (the unknown-tolerant assertion alone would not); ③ existing bundle tests updated for `BUNDLE_VERSION == "p2d.settlement.v2"` if any pin it.

- [ ] **Step 5: MANDATORY gold regeneration (s2/s5) + ledger schema_addition**

Run: `python -m unittest tests.test_scoring -v`
Expected: the s2 (`:47-50`) and s5 (`:262-269`) whole-dict assertions FAIL with the added `evaluation_bucket` key — this is the planned main path, NOT a contingency.

Regenerate the two gold expectation files: open `tests/test_scoring.py` around each failing assertion, replicate the EXACT construction the test's left-hand side uses (same gold-game inputs, same `score_log_to_dict(...)` call), and `json.dump` the new dict over `docs/gold-game/s2-score-log.json` / `docs/gold-game/s5-score-log.json` **matching the existing files' JSON formatting** (inspect the current files for indent/ensure_ascii before dumping; there is no generator script for these — they are expectation files, regeneration = dumping the new expected output). Verification gate: `git diff docs/gold-game/` must show ONLY the added `evaluation_bucket` key (plus adjacent punctuation lines); any other change means wrong inputs — revert and retry.

Append the MANDATORY `schema_addition` entry to `docs/generated-games/prompt-version-ledger.json`:

```json
{
  "schema_addition": "score_log.evaluation_bucket + settlement_bundle.evaluation_bucket (BUNDLE_VERSION p2d.settlement.v2)",
  "reason": "additive tuple stamp per spec §4.5; s2/s5 gold score-log expectation dicts regenerated (whole-dict assertEqual targets)",
  "regenerated_fixtures": ["docs/gold-game/s2-score-log.json", "docs/gold-game/s5-score-log.json"],
  "blessed_by": "<implementer>",
  "blessed_at": "<date>"
}
```

Then the full suite: `python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -15` → all green. Moving the stamp out of score_records to dodge regeneration is forbidden (spec §4.5).

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/scoring.py src/werewolf_eval/settlement_bundle.py tests/test_scoring.py tests/test_settlement_bundle.py docs/gold-game/s2-score-log.json docs/gold-game/s5-score-log.json docs/generated-games/prompt-version-ledger.json
git commit -m "feat(versioning): score-log + settlement bundle carry evaluation_bucket; bundle v2; s2/s5 gold regen (schema_addition)"
```

### Task 10: regression + docs + closeout

**Files:**
- Modify: `docs/PROJECT_MAP.md` (SYS-B1 row)

- [ ] **Step 1: Full suite**

Run: `python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -5`
Expected: `OK` (with the usual environment-gated skips). Any FAIL → fix before proceeding; do not close out on red.

- [ ] **Step 2: Zero-prompt-byte acceptance check**

The guard test IS the proof, but state it explicitly: `python -m unittest tests.test_prompt_versioning -v` green on `prompt_v1` goldens generated from UNCHANGED rendering code means this plan landed with zero prompt byte change. Confirm no diff touched prompt text: `git log --oneline -10` then `git diff <first-task-commit>~1..HEAD -- src/werewolf_eval/llm_providers.py | grep -E '^[-+].*(You are|狼人杀)'` → expected: empty (only the class-attribute hunk in Task 6 touches this file).

- [ ] **Step 3: Update `docs/PROJECT_MAP.md` SYS-B1 row** — in the 现状与已知债务 cell, append:

```
prompt 版本化机制已落地(prompt_v1 字节锁 + ledger + 三元组戳,spec 2026-06-10):baseline prompt 修订有合法出口
```

- [ ] **Step 4: Commit**

```bash
git add docs/PROJECT_MAP.md
git commit -m "docs(map): SYS-B1 — prompt versioning mechanism landed"
```

---

## Self-Review Notes

- **Spec coverage:** §2 policy needs no code (policy doc). §3 → Tasks 2/4/5 (+ Task 3 Step 0 byte-neutral extraction, explicitly allowed by §3's refactor clause). §4.1-4.2 → Tasks 1/2. §4.3 → Tasks 7/8/9. §4.4 → Tasks 6/7. §4.5 → Task 1 (UNKNOWN), Task 9 (legacy stamp + mandatory s2/s5 regen). §5 → Tasks 3/4/5. §6 → Task 5. §7 touchstone is paper-only (no task, by design). §8 acceptance → Task 10. §9 testing list → Tasks 1-9 tests; §9.4 fake→false covered by Task 6 declarations (BOTH fake classes) + Task 7 derivation.
- **Review nails:** nail #1 (ledger before=null) → Task 5 Step 1. Nail #2 (workflow untouched) → HARD CONSTRAINT 2, verified `unittest discover` auto-collects.
- **Spec §4.3 "run status / run detail" interpretation (on record):** the tuple is stamped into the status.json ARTIFACT; the run-detail API response does not carry the bucket as a field (it references the manifest, which does). Artifact-layer reading of the spec table; if P3 wants it in the API payload, that is a one-line follow-up in observer_server, out of scope here.
- **Independent plan review (2026-06-10, applied in r2):** finding 1 (bundle real-bucket wiring via settle entry + the catching test) → Task 9 Step 4; finding 2 (s2/s5 whole-dict golds → mandatory regen + gold-game authorization) → HARD CONSTRAINT 3/5 + Task 9 Steps 2/5; finding 3 (g1h private fake class) → Task 6 + pin test; finding 4 (docstring-substring self-trap) → Task 1 ast-based test; finding 5 (hunter-shot suffix model-visible) → Task 3 Step 0 + 14th sample; finding 6 (BUNDLE_VERSION bump) → Task 9 Step 4(c). Minor: Task 8 targets `tests/test_observer_protocol.py`; consensus runner has two manifest call sites; trace `observation_text` caveat recorded in fact #5.

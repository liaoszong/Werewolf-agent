# l4_guard_witch_coord Arm (prompt_v4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `prompt_v4` (= prompt_v3 + witch antidote-coordination guidance, injected only into the witch's own night action observation on guard boards) plus first-class milk-pierce metrics, so the `l4_guard_witch_coord` ablation arm can run with zero CLI/harness changes.

**Architecture:** One new locked prompt module (`prompt_v4.py`) + one adapter in the SYS-B1 PromptRenderer registry (`PromptRendererV4(PromptRendererV3)` overriding a NEW base hook `witch_obs_suffix`, which returns `""` for v1/v2/v3) + one engine line in `_resolve_witch`. Metrics gain `milk_pierce_overlap/death` per-game keys and aggregate counts. Everything else (board card, speech, vote scaffold, scribe, rules, settler) is inherited untouched.

**Tech Stack:** Python stdlib unittest, golden-prompt byte locks (`tests/test_prompt_versioning.py` + `tools/generate_golden_prompts.py` + ledger), ablation metrics (`werewolf_eval.ablation.metrics`).

**Spec:** `docs/superpowers/specs/2026-06-12-l4-guard-witch-coord-arm-design.md` (user verdict: ACCEPTED_WITH_SMALL_EDITS; all 4 edits incorporated).

---

## Hard boundaries (spec §10 — violating any of these is a plan failure)

- `prompt_v1.py` / `prompt_v2.py` / `prompt_v3.py` files: **zero edits** (not even comments). `prompt_v4.py` imports `_board_card_has_guard` from prompt_v3 — import only.
- `tests/golden_prompts/prompt_v1|v2|v3/**`: **zero byte changes** (gate: `git diff --exit-code` in Task 7).
- `PROMPT_VERSION` constant stays `"prompt_v1"`.
- No changes to: rules (`action_runtime/ruleset.py`), settler, action strict-JSON, `arms.py`, `ablation/harness.py`, `ablation/__main__.py`, `clients/**`, `max_day_rounds`.
- The guidance hook must never receive or reference guard-private runtime state (actual guard target, `last_guarded_target`, guard aliveness). Inputs are exactly: `board_card` (public), `victim` (witch-visible per R-04 precedent), `save_used` (witch's own state).

## Process requirements (repo discipline)

- Execute in an **isolated worktree** (`superpowers:using-git-worktrees`); never run subagents in the shared main checkout. Before every commit: `git branch --show-current` + `git status --short` (stray-staged check) — see `.agents/skills/committing-in-shared-worktrees/SKILL.md`.
- **Read `.agents/skills/guarding-prompt-bytes/SKILL.md` before Tasks 1-4** (spec §5: the whole prompt surface goes through that runbook — coexisting-version path: KNOWN extension + own golden dir + ledger entry, NO `PROMPT_VERSION` bump; Tasks 4/7 implement its mechanical steps).
- **Chinese text must be written with the Edit/Write tools, NEVER via bash heredoc** (Windows bash heredoc corrupts Chinese to mojibake — verified gotcha).
- Test runs need `NO_PROXY='*'` (localhost server tests false-fail behind proxy).
- Baseline test count: measure `python -m unittest discover` on the branch base commit FIRST and pin that number; cross-session counts are not comparable.
- New files ⇒ run `node .codex/hooks/tree.mjs --force` before the final commit.

---

### Task 1: `prompt_v4.py` — the locked guidance + 3-condition gate

**Files:**
- Create: `src/werewolf_eval/prompt_v4.py`
- Create: `tests/test_prompt_v4.py`

- [ ] **Step 1.1: Write the failing test**

Create `tests/test_prompt_v4.py` with the Write tool (Chinese content — no heredoc):

```python
"""prompt_v4 witch coordination suffix: 3-condition truth table + content
discipline locks (spec 2026-06-12-l4-guard-witch-coord-arm-design §3/§4)."""
from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1_1, rules_v1_2
from werewolf_eval.prompt_v2 import build_board_rules_card
from werewolf_eval.prompt_v4 import WITCH_COORD_GUIDANCE, render_witch_coord_suffix

_STD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
              "p4": "witch", "p5": "villager", "p6": "villager"}
_GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                "p4": "witch", "p5": "guard", "p6": "villager"}

GUARD_CARD = build_board_rules_card(rules_v1_2(), _GUARD_SEATS)
STD_CARD = build_board_rules_card(rules_v1_1(), _STD_SEATS)


class TruthTableTest(unittest.TestCase):
    """spec §9: 8-combination truth table — ONLY guard∧victim∧antidote-unused injects."""

    def test_only_full_conjunction_injects(self):
        for has_guard, has_victim, save_used in itertools.product((True, False), repeat=3):
            card = GUARD_CARD if has_guard else STD_CARD
            victim = "p5" if has_victim else None
            out = render_witch_coord_suffix(card, victim, save_used)
            if has_guard and has_victim and not save_used:
                self.assertEqual(out, "\n" + WITCH_COORD_GUIDANCE)
            else:
                self.assertEqual(out, "", (has_guard, has_victim, save_used))

    def test_v1_style_empty_or_none_board_card_is_non_guard(self):
        # prompt_v1's renderer board_card is "" — must behave like a non-guard board.
        self.assertEqual(render_witch_coord_suffix("", "p5", False), "")
        self.assertEqual(render_witch_coord_suffix(None, "p5", False), "")


class GuidanceContentTest(unittest.TestCase):
    """spec §4 文案纪律: risk-tradeoff wording, no 「高价值就救」, no lies."""

    def test_guidance_markers(self):
        self.assertIn("【解药协调提示】", WITCH_COORD_GUIDANCE)
        self.assertIn("同守同救", WITCH_COORD_GUIDANCE)
        self.assertIn("你无法知道守卫今晚守了谁", WITCH_COORD_GUIDANCE)
        self.assertIn("不要机械地夜1必救", WITCH_COORD_GUIDANCE)
        self.assertIn("死亡风险高", WITCH_COORD_GUIDANCE)
        self.assertNotIn("高价值", WITCH_COORD_GUIDANCE)
        # 引号字节钉死(独立审 B-1):spec §4 用 ASCII 直引号,不许被"美化"成 CJK 弯引号
        self.assertIn('你认为"死亡风险高、且不太可能同时被守卫守护"的目标', WITCH_COORD_GUIDANCE)
        self.assertNotIn("“", WITCH_COORD_GUIDANCE)
        self.assertNotIn("”", WITCH_COORD_GUIDANCE)

    def test_guidance_has_no_newlines(self):
        # Single paragraph; the injected suffix's ONLY newline is the leading join.
        self.assertNotIn("\n", WITCH_COORD_GUIDANCE)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 1.2: Run it, verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_prompt_v4 -v`
Expected: ERROR — `ModuleNotFoundError: No module named 'werewolf_eval.prompt_v4'`

- [ ] **Step 1.3: Implement `prompt_v4.py`**

Create `src/werewolf_eval/prompt_v4.py` with the Write tool. The guidance string is the spec §4 text **verbatim, byte-for-byte** — copy from the spec file. NOTE: the quotes around 死亡风险高...守护 are **ASCII straight quotes `"` (U+0022)**, matching the user's original ruling text. Do NOT "beautify" them into CJK quotes `“”` — that is a byte drift the content tests below pin against:

```python
"""prompt_v4 (l4_guard_witch_coord): witch antidote-coordination guidance.
Injected into the witch's OWN night action observation only (engine
_resolve_witch), gated on board-has-guard AND victim present AND antidote
unused; every other state renders "" so prompt_v4 stays byte-identical to
prompt_v3 there (spec §5 canaries). NO engine / llm_providers import (they
import US). Spec: docs/superpowers/specs/2026-06-12-l4-guard-witch-coord-arm-design.md.
Visibility hard gate (spec §3): inputs are public board composition plus the
witch's own state — NEVER the guard's actual target or aliveness."""
from __future__ import annotations

from werewolf_eval.prompt_v3 import _board_card_has_guard

WITCH_COORD_GUIDANCE = (
    "【解药协调提示】本局存在守卫。守卫每晚守护一名玩家;若你解药救下的人当晚同时被守卫守护,"
    "该玩家会因「同守同救」规则死亡。你无法知道守卫今晚守了谁。用药前请权衡:该目标是否很可能"
    "正被守卫保护,例如已公开跳出且被全场关注的预言家。信息不足时不要机械地夜1必救;解药整局"
    "仅一瓶,应优先用于你认为\"死亡风险高、且不太可能同时被守卫守护\"的目标。"
)


def render_witch_coord_suffix(board_card: str | None, victim: str | None, save_used: bool) -> str:
    """The ONLY prompt_v4 surface. Three-condition gate (spec §3): all other
    states return "" so the composed witch observation is byte-identical to
    prompt_v3 (spec §5 canaries pin this)."""
    if _board_card_has_guard(board_card) and victim is not None and not save_used:
        return "\n" + WITCH_COORD_GUIDANCE
    return ""
```

Note: `_board_card_has_guard` (prompt_v3.py:104) keys on the `"- 守卫("` rules-card role line — the plain substring `守卫` would false-positive on the standard board's 「没有守卫或守夜人」 line. Reuse, don't reinvent.

- [ ] **Step 1.4: Run the test, verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_prompt_v4 -v`
Expected: all PASS.

- [ ] **Step 1.5: Commit**

```bash
git add src/werewolf_eval/prompt_v4.py tests/test_prompt_v4.py
git commit -m "feat(prompt_v4): witch antidote-coordination guidance module — 3-condition gate (guard board AND victim AND antidote unused), spec-verbatim locked text"
```

---

### Task 2: registry seam — `witch_obs_suffix` base hook + `PromptRendererV4`

**Files:**
- Modify: `src/werewolf_eval/prompt_version.py:19` (KNOWN_PROMPT_VERSIONS)
- Modify: `src/werewolf_eval/prompt_renderers.py`
- Modify: `tests/test_prompt_renderers.py`

Note: KNOWN and REGISTRY must change in the SAME commit — the sentinel `tuple(REGISTRY) == KNOWN_PROMPT_VERSIONS` fails red if they drift.

- [ ] **Step 2.1: Write the failing tests**

In `tests/test_prompt_renderers.py` (use Edit tool — Chinese content), extend the imports:

```python
from werewolf_eval.action_runtime.ruleset import rules_v1_1, rules_v1_2
from werewolf_eval.prompt_v4 import WITCH_COORD_GUIDANCE
```

(`rules_v1_1` is already imported; change that line to import both.)

Add a guard-seats fixture next to `_SEATS`:

```python
_GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                "p4": "witch", "p5": "guard", "p6": "villager"}
```

In `RegistrySentinelTest`, extend `test_requires_scaffold_flags`:

```python
        self.assertTrue(REGISTRY["prompt_v4"].requires_scaffold)
```

Add to `AdapterByteEquivalenceTest` — v4 inherits every v3 surface:

```python
    def test_v4_inherits_v3_surfaces(self):
        req = _req()
        r4 = get_renderer("prompt_v4")
        self.assertEqual(r4.speech_contract(req), build_speech_system_prompt_v3(req))
        self.assertEqual(r4.action_obs_suffix("day", _CLAIMS), "\n" + render_vote_scaffold(_CLAIMS))
        self.assertEqual(r4.speech_obs_suffix(_CLAIMS), "\n" + render_claim_digest(_CLAIMS))
        rs = rules_v1_1()
        self.assertEqual(r4.board_card(rs, _SEATS),
                         get_renderer("prompt_v3").board_card(rs, _SEATS))
```

Add a new test class — the hook dispatch:

```python
class WitchObsSuffixDispatchTest(unittest.TestCase):
    """v4 注入 hook:v1/v2/v3 恒返 ""(既有版本字节零影响);v4 走 3 条件门。"""

    def setUp(self):
        # build_board_rules_card is already module-level imported in this file
        self.guard_card = build_board_rules_card(rules_v1_2(), _GUARD_SEATS)

    def test_v1_v2_v3_always_empty(self):
        for v in ("prompt_v1", "prompt_v2", "prompt_v3"):
            self.assertEqual(get_renderer(v).witch_obs_suffix(self.guard_card, "p5", False), "")

    def test_v4_injects_only_on_full_conjunction(self):
        r4 = get_renderer("prompt_v4")
        self.assertEqual(r4.witch_obs_suffix(self.guard_card, "p5", False),
                         "\n" + WITCH_COORD_GUIDANCE)
        self.assertEqual(r4.witch_obs_suffix(self.guard_card, None, False), "")
        self.assertEqual(r4.witch_obs_suffix(self.guard_card, "p5", True), "")
        std_card = get_renderer("prompt_v2").board_card(rules_v1_1(), _SEATS)
        self.assertEqual(r4.witch_obs_suffix(std_card, "p5", False), "")
```

- [ ] **Step 2.2: Run, verify failures**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_prompt_renderers -v`
Expected: FAIL/ERROR — a mix of `KeyError: 'prompt_v4'` (direct `REGISTRY[...]` access), `ValueError: unknown prompt_version` (`get_renderer` wraps the KeyError, prompt_renderers.py:104-107), and `AttributeError: ... no attribute 'witch_obs_suffix'`.

- [ ] **Step 2.3: Implement**

`src/werewolf_eval/prompt_version.py` — extend the literal and its comment block:

```python
# prompt_v3 = SYS-B4 claim-ledger/vote-scaffold chain (scribe + restrained speech).
# prompt_v4 = v3 + witch antidote-coordination guidance on guard boards
# (l4_guard_witch_coord arm, spec 2026-06-12).
KNOWN_PROMPT_VERSIONS = ("prompt_v1", "prompt_v2", "prompt_v3", "prompt_v4")
```

`src/werewolf_eval/prompt_renderers.py`:

Add import:

```python
from werewolf_eval.prompt_v4 import render_witch_coord_suffix
```

Add the base hook to `PromptRendererV1` (next to the other suffix hooks):

```python
    def witch_obs_suffix(self, board_card: str | None, victim: str | None, save_used: bool) -> str:
        return ""
```

Add the adapter after `PromptRendererV3`:

```python
class PromptRendererV4(PromptRendererV3):
    """l4_guard_witch_coord arm: the full v3 chain + witch antidote-coordination
    guidance injected ONLY into the witch's night action observation
    (3-condition gate in prompt_v4.render_witch_coord_suffix; spec 2026-06-12 §3)."""

    version = "prompt_v4"

    def witch_obs_suffix(self, board_card: str | None, victim: str | None, save_used: bool) -> str:
        return render_witch_coord_suffix(board_card, victim, save_used)
```

Extend the registry literal:

```python
REGISTRY: dict[str, PromptRendererV1] = {
    r.version: r for r in (PromptRendererV1(), PromptRendererV2(), PromptRendererV3(), PromptRendererV4())
}
```

- [ ] **Step 2.4: Run, verify green (renderers + v4 + versioning sentinel)**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_prompt_renderers tests.test_prompt_v4 -v`
Expected: all PASS. (Golden tests for v4 don't exist yet — that's Task 4; `tests.test_prompt_versioning` is NOT expected to reference v4 yet.)

- [ ] **Step 2.5: Commit**

```bash
git add src/werewolf_eval/prompt_version.py src/werewolf_eval/prompt_renderers.py tests/test_prompt_renderers.py
git commit -m "feat(renderers): witch_obs_suffix base hook (v1/v2/v3 return '') + PromptRendererV4 + KNOWN_PROMPT_VERSIONS entry — registry sentinel stays pinned"
```

---

### Task 3: engine wiring + spec §5 canaries at engine level

**Files:**
- Modify: `src/werewolf_eval/emergent_engine.py:770` (one line added after `augment_witch_observation`)
- Create: `tests/test_prompt_v4_engine.py`

- [ ] **Step 3.1: Write the failing test**

Create `tests/test_prompt_v4_engine.py` (Write tool). Pattern precedent: `tests/test_emergent_engine.py::test_witch_cannot_poison_twice` calls `engine._resolve_witch` directly after emitting a setup event.

```python
"""Engine-level prompt_v4 wiring + spec §5 canaries: the witch night
observation gains the coordination suffix EXACTLY when board-has-guard AND
victim present AND antidote unused; otherwise byte-identical to prompt_v3."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
)
from werewolf_eval.prompt_v4 import WITCH_COORD_GUIDANCE

_GUARD_SEATS = {"p1": "werewolf", "p2": "werewolf", "p3": "seer",
                "p4": "witch", "p5": "guard", "p6": "villager"}


class _RecordingProvider:
    """Wraps the witch's fake provider and captures the ProviderRequest so the
    rendered observation_text can be asserted byte-exactly."""

    def __init__(self, inner):
        self._inner = inner
        self.requests = []
        self.model = getattr(inner, "model", None)

    def respond(self, request):
        self.requests.append(request)
        return self._inner.respond(request)


def _witch_obs_text(prompt_version, seat_roles=None, victim="p5", save_used=False):
    agents = build_emergent_fake_agents(build_villager_win_script())
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id="v4wire", seat_roles=seat_roles),
        agents=agents,
        seed=0,
        prompt_version=prompt_version,
        scaffold_agent=(agents["p4"] if prompt_version in ("prompt_v3", "prompt_v4") else None),
    )
    rec = _RecordingProvider(engine._agents["p4"].provider)
    engine._agents["p4"] = SimpleNamespace(provider=rec)
    engine._emit("setup", 0, "role_assignment", "system", "none", "public", "setup")
    engine._resolve_witch(rnd=1, victim=victim, save_used=save_used, poison_used=False)
    return rec.requests[0].observation_text


class PromptV4EngineWiringTest(unittest.TestCase):
    def test_guard_board_victim_unused_injects(self):
        v4 = _witch_obs_text("prompt_v4", _GUARD_SEATS)
        v3 = _witch_obs_text("prompt_v3", _GUARD_SEATS)
        self.assertEqual(v4, v3 + "\n" + WITCH_COORD_GUIDANCE)

    def test_canary1_standard_board_byte_identical_to_v3(self):
        # spec §5 canary 1: non-guard board → v4 witch night observation == v3
        self.assertEqual(_witch_obs_text("prompt_v4"), _witch_obs_text("prompt_v3"))

    def test_canary2_guard_board_no_victim_byte_identical_to_v3(self):
        # spec §5 canary 2: guard board but victim is None → identical to v3
        self.assertEqual(_witch_obs_text("prompt_v4", _GUARD_SEATS, victim=None),
                         _witch_obs_text("prompt_v3", _GUARD_SEATS, victim=None))

    def test_guard_board_antidote_spent_byte_identical_to_v3(self):
        # spec §5 third identity: antidote already used → identical to v3
        self.assertEqual(_witch_obs_text("prompt_v4", _GUARD_SEATS, save_used=True),
                         _witch_obs_text("prompt_v3", _GUARD_SEATS, save_used=True))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3.2: Run, verify the injection test fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_prompt_v4_engine -v`
Expected: `test_guard_board_victim_unused_injects` FAILS (v4 == v3, suffix missing — hook not wired). The three identity tests pass vacuously (both sides un-suffixed). If anything ERRORS instead (helper-signature drift), fix the test harness first.

- [ ] **Step 3.3: Wire the engine**

`src/werewolf_eval/emergent_engine.py` — in `_resolve_witch`, directly after line 770:

```python
        witch_obs_text = augment_witch_observation(rendered.text, victim)
        witch_obs_text += self._renderer.witch_obs_suffix(self._board_card, victim, save_used)
```

(The second line is the only engine change. `self._board_card` is built at :266; `victim`/`save_used` are already parameters.)

- [ ] **Step 3.4: Run, verify all green**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_prompt_v4_engine tests.test_emergent_engine -v`
Expected: all PASS (including the untouched engine suite — v1/v2/v3 hooks return `""`, so existing games are byte-unaffected).

- [ ] **Step 3.5: Commit**

```bash
git add src/werewolf_eval/emergent_engine.py tests/test_prompt_v4_engine.py
git commit -m "feat(engine): append renderer.witch_obs_suffix to the witch night observation — engine-level canaries pin v4==v3 bytes on standard board / no-victim / spent-antidote"
```

---

### Task 4: golden lock + ledger for prompt_v4

**Files:**
- Modify: `src/werewolf_eval/prompt_goldens.py`
- Modify: `tools/generate_golden_prompts.py`
- Modify: `tests/test_prompt_versioning.py`
- Create: `tests/golden_prompts/prompt_v4/*.txt` (generated)
- Modify: `docs/generated-games/prompt-version-ledger.json`

- [ ] **Step 4.1: Write the failing golden-guard tests**

Append to `tests/test_prompt_versioning.py` (Edit tool), mirroring `PromptV3GuardTests`:

```python
from werewolf_eval.prompt_goldens import canonical_prompt_samples_v4

PROMPT_V4 = "prompt_v4"


class PromptV4GuardTests(unittest.TestCase):
    """prompt_v4 coexists with v1/v2/v3; lock its bytes + ledger the same way."""

    def test_v4_rendered_bytes_match_golden(self) -> None:
        golden_dir = GOLDEN_ROOT / PROMPT_V4
        self.assertTrue(golden_dir.is_dir(), "missing tests/golden_prompts/prompt_v4")
        samples = dict(canonical_prompt_samples_v4())
        files = {p.stem: p for p in golden_dir.glob("*.txt")}
        self.assertEqual(sorted(samples), sorted(files))
        for name, text in samples.items():
            self.assertEqual(files[name].read_bytes(), text.encode("utf-8"),
                             f"prompt_v4 bytes changed for '{name}' without regen+ledger")

    def test_v4_ledger_entry_hashes(self) -> None:
        import hashlib
        matches = [e for e in _ledger() if e.get("prompt_version") == PROMPT_V4]
        self.assertEqual(len(matches), 1)
        after = matches[0]["golden_prompt_hashes"]["after"]
        samples = dict(canonical_prompt_samples_v4())
        self.assertEqual(sorted(after), sorted(samples))
        for name, text in samples.items():
            self.assertEqual(after[name], hashlib.sha256(text.encode("utf-8")).hexdigest())

    def test_v4_carries_coordination_markers(self) -> None:
        # 实质标记断言(同 v2/v3 先例,不做恒真比较):注入态含协调提示与文案纪律;
        # 恒等态样本不含提示(它就是 v3 字节,锁的是「v4 在该态没加任何字节」)。
        samples = dict(canonical_prompt_samples_v4())
        self.assertIn("【解药协调提示】", samples["witch_coord_suffix_injected"])
        self.assertIn("同守同救", samples["witch_coord_suffix_injected"])
        self.assertNotIn("高价值", samples["witch_coord_suffix_injected"])
        self.assertIn("【解药协调提示】", samples["obs_witch_guard_board_victim_coord"])
        self.assertNotIn("【解药协调提示】",
                         samples["obs_witch_guard_board_no_victim_identity"])
```

- [ ] **Step 4.2: Run, verify failure**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_prompt_versioning -v`
Expected: ImportError — `canonical_prompt_samples_v4` doesn't exist.

- [ ] **Step 4.3: Add the v4 sample set + generator line**

`src/werewolf_eval/prompt_goldens.py` — add import and function:

```python
from werewolf_eval.prompt_v4 import render_witch_coord_suffix
```

```python
def canonical_prompt_samples_v4() -> list[tuple[str, str]]:
    """prompt_v4 golden set — only the NEW surface (spec §5/§9): the injected
    suffix, the fully composed injected witch observation, and the no-victim
    identity state (whose bytes ARE prompt_v3's — locking that v4 adds nothing
    there). The "" states can't be golden files; they are pinned by the canary
    unit tests (tests/test_prompt_v4*.py)."""
    guard_card = build_board_rules_card(rules_v1_2(), _GUARD_SEATS)
    witch_text = _v2_text("p4", "witch", "villager", "night", {"p4": "witch"}, [])
    return [
        ("witch_coord_suffix_injected",
         render_witch_coord_suffix(guard_card, "p5", False)),
        ("obs_witch_guard_board_victim_coord",
         augment_witch_observation(witch_text, "p5")
         + render_witch_coord_suffix(guard_card, "p5", False)),
        ("obs_witch_guard_board_no_victim_identity",
         augment_witch_observation(witch_text, None)
         + render_witch_coord_suffix(guard_card, None, False)),
    ]
```

(`_GUARD_SEATS`, `_v2_text`, `augment_witch_observation`, `build_board_rules_card`, `rules_v1_2` already exist in this module.)

`tools/generate_golden_prompts.py` — extend the import line with `canonical_prompt_samples_v4` and add in `main()`:

```python
    all_hashes["prompt_v4"] = _write_dir("prompt_v4", canonical_prompt_samples_v4())
```

- [ ] **Step 4.4: Generate goldens, capture hashes**

Run: `NO_PROXY='*' PYTHONPATH=src python tools/generate_golden_prompts.py`
Expected: prints the hash map including a `"prompt_v4"` block with the 3 sample names; creates `tests/golden_prompts/prompt_v4/*.txt` (3 files). **Verify v1/v2/v3 dirs unchanged:** `git diff --exit-code tests/golden_prompts/prompt_v1 tests/golden_prompts/prompt_v2 tests/golden_prompts/prompt_v3` → exit 0.

- [ ] **Step 4.5: Add the ledger entry**

Append ONE entry to the array in `docs/generated-games/prompt-version-ledger.json` (paste the `prompt_v4` hash block from Step 4.4 into `after` — never hand-compute hashes):

```json
{
  "prompt_version": "prompt_v4",
  "base_version": "prompt_v3",
  "reason": "l4_guard_witch_coord arm: witch antidote-coordination guidance injected into the witch's own night action observation on guard boards (spec 2026-06-12-l4-guard-witch-coord-arm-design)",
  "expected_change": "witch night observation gains the coordination suffix ONLY when board-has-guard AND victim present AND antidote unused; all other surfaces and states byte-identical to prompt_v3 (canary-pinned)",
  "touched_chain": ["prompt_v4.render_witch_coord_suffix", "prompt_renderers.PromptRendererV4.witch_obs_suffix", "emergent_engine._resolve_witch"],
  "golden_prompt_hashes": {"before": null, "after": {"<paste generator output for prompt_v4>": "<sha256>"}},
  "behavior_evidence": {"status": "not_run", "reason_if_not_run": "live 45-game l4_guard_witch_coord arm is the user-triggered T-live step; metrics snapshot + verdict will attach there"},
  "blessed_by": "user (spec verdict ACCEPTED_WITH_SMALL_EDITS, 2026-06-12)",
  "blessed_at": "2026-06-12"
}
```

- [ ] **Step 4.6: Run the full versioning suite, verify green**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_prompt_versioning -v`
Expected: all PASS, including the untouched v1/v2/v3 guard classes.

- [ ] **Step 4.7: Commit**

```bash
git add src/werewolf_eval/prompt_goldens.py tools/generate_golden_prompts.py tests/test_prompt_versioning.py tests/golden_prompts/prompt_v4 docs/generated-games/prompt-version-ledger.json
git commit -m "feat(goldens): prompt_v4 byte lock (injected suffix + composed witch obs + no-victim identity sample) + ledger entry; v1/v2/v3 goldens zero-change verified"
```

---

### Task 5: milk-pierce metrics — overlap/death split + night-1 save share

**Files:**
- Modify: `src/werewolf_eval/ablation/metrics.py` (analyze_game_dict, aggregate_games, DEFAULT_COMPARE_KEYS)
- Modify: `tests/test_l4_metrics.py`

Data-source note (documented deviation from spec §6's "decision-log + game-log" wording): the implementation reads game-log events only. This is equivalent for the spec's purpose — the `guard_protect` event is rendered from the ADJUDICATED target (action_runtime/turn.py:164), i.e. it already carries the fallback-resolved actual effective target the spec requires. Independently verified during plan review; the Task 6 backfill gate (12/12 reproduction) re-proves it on real artifacts.

- [ ] **Step 5.1: Write the failing tests**

Append to `tests/test_l4_metrics.py` (Edit tool; reuse the module's `_ev` helper):

```python
def _witch_coord_game(events, end_round=2):
    players = [
        {"player_id": "p1", "role": "werewolf"}, {"player_id": "p2", "role": "werewolf"},
        {"player_id": "p3", "role": "seer"}, {"player_id": "p4", "role": "witch"},
        {"player_id": "p5", "role": "guard"}, {"player_id": "p6", "role": "villager"},
    ]
    return {"players": players, "events": events,
            "result": {"winner": "werewolf", "end_round": end_round}}


_PIERCE_R1 = [
    _ev(1, "night", "guard_protect", "p5", "p3", "Guard p5 protects p3."),
    _ev(1, "night", "werewolf_kill", "p1", "p3", "Wolf team kills p3."),
    _ev(1, "night", "witch_action", "p4", "p3", "Witch saves p3."),
    _ev(1, "night", "player_died", "system", "p3", "p3 died during the night."),
]


class MilkPierceMetricsTests(unittest.TestCase):
    """spec 2026-06-12 §6: overlap/death two-layer split; denominator = n_valid set."""

    def test_pierce_counts_overlap_and_death(self):
        row = analyze_game_dict(_witch_coord_game(list(_PIERCE_R1)))
        self.assertEqual(row["milk_pierce_overlap"], 1)
        self.assertEqual(row["milk_pierce_death"], 1)
        self.assertEqual(row["witch_save_round"], 1)

    def test_overlap_without_night_death_is_not_a_pierce_death(self):
        # 规则不可知层:重叠但目标活到天亮 → overlap=1, death=0(标准规则下
        # 两键应恒等;不等=结算异常,verdict 须解释 — spec §6)
        row = analyze_game_dict(_witch_coord_game([
            _ev(1, "night", "guard_protect", "p5", "p3", "Guard p5 protects p3."),
            _ev(1, "night", "werewolf_kill", "p1", "p3", "Wolf team kills p3."),
            _ev(1, "night", "witch_action", "p4", "p3", "Witch saves p3."),
            _ev(1, "day", "day_announcement", "system", "none", "A peaceful night: nobody died."),
        ]))
        self.assertEqual(row["milk_pierce_overlap"], 1)
        self.assertEqual(row["milk_pierce_death"], 0)

    def test_disjoint_guard_and_save_targets_no_overlap(self):
        row = analyze_game_dict(_witch_coord_game([
            _ev(1, "night", "guard_protect", "p5", "p6", "Guard p5 protects p6."),
            _ev(1, "night", "werewolf_kill", "p1", "p3", "Wolf team kills p3."),
            _ev(1, "night", "witch_action", "p4", "p3", "Witch saves p3."),
            _ev(1, "day", "day_announcement", "system", "none", "A peaceful night: nobody died."),
        ]))
        self.assertEqual(row["milk_pierce_overlap"], 0)
        self.assertEqual(row["milk_pierce_death"], 0)

    def test_vote_death_same_round_is_not_a_pierce_death(self):
        # 死亡链边界:重叠 + 当轮被票出(白天死,cause=vote)→ death 不计
        row = analyze_game_dict(_witch_coord_game([
            _ev(1, "night", "guard_protect", "p5", "p3", "Guard p5 protects p3."),
            _ev(1, "night", "witch_action", "p4", "p3", "Witch saves p3."),
            _ev(1, "day", "vote_result", "system", "p3", "p3 eliminated by vote."),
        ]))
        self.assertEqual(row["milk_pierce_overlap"], 1)
        self.assertEqual(row["milk_pierce_death"], 0)

    def test_poison_death_of_other_player_is_not_a_pierce_death(self):
        # spec §9 边界:重叠在 p3 上、同夜 p6 死于其他死亡链(如毒)——pid 不匹配,不计
        row = analyze_game_dict(_witch_coord_game([
            _ev(1, "night", "guard_protect", "p5", "p3", "Guard p5 protects p3."),
            _ev(1, "night", "witch_action", "p4", "p3", "Witch saves p3."),
            _ev(1, "night", "player_died", "system", "p6", "p6 died during the night."),
        ]))
        self.assertEqual(row["milk_pierce_overlap"], 1)
        self.assertEqual(row["milk_pierce_death"], 0)

    def test_aggregate_counts_and_night1_share(self):
        g_pierce = analyze_game_dict(_witch_coord_game(list(_PIERCE_R1)))
        g_late_save = analyze_game_dict(_witch_coord_game([
            _ev(2, "night", "witch_action", "p4", "p6", "Witch saves p6."),
        ], end_round=3))
        g_no_save = analyze_game_dict(_witch_coord_game([
            _ev(1, "night", "witch_action", "p4", "none", "Witch uses no potion."),
        ]))
        agg = aggregate_games([g_pierce, g_late_save, g_no_save])
        self.assertEqual(agg["milk_pierce_overlap_count"], 1)
        self.assertEqual(agg["milk_pierce_death_count"], 1)
        # 用药局 2(夜1 + 夜2),其中夜1 用药 1 → share 0.5;不用药局不进分母
        self.assertEqual(agg["witch_save_night1_share"], 0.5)

    def test_no_save_games_yield_none_share(self):
        g = analyze_game_dict(_witch_coord_game([
            _ev(1, "night", "witch_action", "p4", "none", "Witch uses no potion."),
        ]))
        agg = aggregate_games([g])
        self.assertEqual(agg["milk_pierce_overlap_count"], 0)
        self.assertEqual(agg["milk_pierce_death_count"], 0)
        self.assertIsNone(agg["witch_save_night1_share"])
```

Also assert the compare surface (same file, same class):

```python
    def test_compare_keys_include_milk_pierce_family(self):
        from werewolf_eval.ablation.metrics import DEFAULT_COMPARE_KEYS
        for k in ("milk_pierce_overlap_count", "milk_pierce_death_count", "witch_save_night1_share"):
            self.assertIn(k, DEFAULT_COMPARE_KEYS)
```

- [ ] **Step 5.2: Run, verify failures**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_l4_metrics -v`
Expected: KeyError `milk_pierce_overlap` etc. (existing tests stay green).

- [ ] **Step 5.3: Implement in `metrics.py`**

In `analyze_game_dict`, add a tracker next to `guards_by_round` (line ~234):

```python
    guards_by_round = {}                     # round -> guard target (L4)
    saves_by_round = {}                      # round -> saved target (v4 milk-pierce, spec 2026-06-12 §6)
```

Change the `witch_save` branch of the event loop (currently `elif kind == "witch_save": save = True`):

```python
        elif kind == "witch_save":
            save = True
            if t is not None and re.match(r"p\d$", str(t)):
                saves_by_round[r] = t
```

(The target guard matters: classify falls back to `ev["target"]` when the regex misses, which can be `"none"` — only seat ids count as saves with a target.)

After the event loop, next to the `gn = len(guards_by_round)` block:

```python
    overlap_rounds = [r for r, t in saves_by_round.items() if guards_by_round.get(r) == t]
    milk_death = sum(
        1 for r in overlap_rounds
        if any(dr == r and pid == saves_by_round[r] and cause == "night"
               for (dr, pid, cause) in deaths))
```

Add to the returned dict (after the `"n_peaceful_nights"` line):

```python
        "witch_save_round": (min(saves_by_round) if saves_by_round else None),
        "milk_pierce_overlap": len(overlap_rounds),
        "milk_pierce_death": milk_death,
```

In `aggregate_games`, add a precompute next to `kill_dist`:

```python
    saved_games = [g for g in games if g.get("witch_save_round") is not None]
```

Add to the returned dict (after the L4 guard family block):

```python
        # ---- v4 witch-coordination arm (spec 2026-06-12 §6); totals over the n_valid set ----
        "milk_pierce_overlap_count": sum(g.get("milk_pierce_overlap") or 0 for g in games),
        "milk_pierce_death_count": sum(g.get("milk_pierce_death") or 0 for g in games),
        "witch_save_night1_share": (
            sum(1 for g in saved_games if g["witch_save_round"] == 1) / len(saved_games)
        ) if saved_games else None,
```

Extend `DEFAULT_COMPARE_KEYS` (append to the last line of the tuple):

```python
    "guard_target_seer_rate","guard_success_rate","avg_peaceful_nights",
    "milk_pierce_overlap_count","milk_pierce_death_count","witch_save_night1_share",
```

- [ ] **Step 5.4: Run, verify green (l4 + ablation metrics suites)**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_l4_metrics tests.test_ablation_metrics -v`
Expected: all PASS.

- [ ] **Step 5.5: Commit**

```bash
git add src/werewolf_eval/ablation/metrics.py tests/test_l4_metrics.py
git commit -m "feat(metrics): milk_pierce overlap/death two-layer counts + witch_save_round/night1_share — primary criterion key is milk_pierce_death_count (spec 2026-06-12 §6)"
```

---

### Task 6: backfill correctness gate — reproduce overlap=death=12 on l4_guard

**Files:** none (read-only verification; raw games live in the MAIN checkout's `.runs/ablation/l4_guard/`, untracked — use the absolute path, NOT the worktree)

- [ ] **Step 6.1: Run the backfill (ASCII-only heredoc is safe)**

```bash
NO_PROXY='*' PYTHONPATH=src python - <<'EOF'
from pathlib import Path
from werewolf_eval.ablation.metrics import aggregate
dirs = sorted(p for p in Path("G:/Werewolf-agent/.runs/ablation/l4_guard").iterdir() if p.is_dir())
m = aggregate(dirs)
print("n_valid:", m["n_valid"])
print("milk_pierce_overlap_count:", m["milk_pierce_overlap_count"])
print("milk_pierce_death_count:", m["milk_pierce_death_count"])
print("witch_save_night1_share:", m["witch_save_night1_share"])
EOF
```

Expected (HARD GATE, spec §11): `n_valid: 44`, `milk_pierce_overlap_count: 12`, `milk_pierce_death_count: 12`. `witch_save_night1_share` has no pinned reference (expect ≈1.0 given witch_save_rate=1.0 with night-1 saves; record the actual value).

**If 12/12 does not reproduce:** STOP. Do not adjust the expected number to match — diff the per-game `milk_pierce_*` rows against `docs/harness/reviews/2026-06-11-l4-guard-prompt-v3-metrics.json` (`guard_mechanics_detail.milk_pierce_deaths=12` and per-game detail) to find which game disagrees, fix the metric (or escalate to the user if the VERDICT number itself looks wrong). The gate exists to align machine and hand counts.

- [ ] **Step 6.2: Record the gate output**

Commit an empty-change record (or fold into Task 7's commit message) quoting the four printed lines verbatim:

```bash
git commit --allow-empty -m "chore(gate): milk_pierce backfill on l4_guard raw games reproduces overlap=death=12 (n_valid=44) — machine count aligned with 2026-06-11 verdict hand count" -m "<paste the four output lines here>"
```

---

### Task 7: closeout — full regression + byte gates + tree

**Files:**
- Modify: `.oh-my-harness/tree.md` (hook-generated)

- [ ] **Step 7.1: v1/v2/v3 golden zero-change gate**

Run: `git diff --exit-code tests/golden_prompts/prompt_v1 tests/golden_prompts/prompt_v2 tests/golden_prompts/prompt_v3`
Expected: exit 0 (no output). Also confirm no edits slipped into the locked modules: `git diff --name-only <branch-base>..HEAD` must NOT list `prompt_v1.py`, `prompt_v2.py`, `prompt_v3.py`, `arms.py`, `harness.py`, `ablation/__main__.py`, anything under `action_runtime/`, or `clients/**`.

- [ ] **Step 7.2: Full regression**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
Expected: 0 failures/errors; count = (branch-base baseline measured at worktree creation) + new tests. Record both numbers.

- [ ] **Step 7.3: Tree hook (new files: prompt_v4.py, 3 test files, golden dir)**

Run: `node .codex/hooks/tree.mjs --force`

- [ ] **Step 7.4: Validation report + final commit**

Produce the AGENTS.md validation block: `git diff --stat`, `git diff --name-only` vs branch base, allowlist check (exactly the files named in Tasks 1-5 + tree.md), forbidden-scope check (§Hard boundaries). Commit tree.md:

```bash
git add .oh-my-harness/tree.md
git commit -m "chore(tree): regenerate after prompt_v4 module + tests + golden dir"
```

Merge flow follows house rules (merge-gate review, then `git fetch . <branch>:main` from the main checkout or merge per `testing-and-process-control` / shared-worktree skill; push only per standing authorization with a dry-run first).

---

### Task 8 (T-live, USER-TRIGGERED — not part of plan execution): 45-game live arm + verdict

Blocked on: Tasks 1-7 merged to main; user supplies the trigger (live DeepSeek budget). Follow `.agents/skills/running-live-games/SKILL.md`.

- [ ] Run (from the main checkout):

```bash
PYTHONPATH=src python -m werewolf_eval.ablation run l4_guard_witch_coord --prompt-version prompt_v4 --board guard --n 45 --seed-base 1000
```

(Zero CLI changes needed: label is free-form; `--prompt-version prompt_v4` passes the harness `KNOWN_PROMPT_VERSIONS` gate; `requires_scaffold=True` auto-attaches the DeepSeek scribe factory. Budget reference: l4_guard ran 1225 requests / ~108K completion tokens / 50.2 min.)

- [ ] All 45 games through `check_run` (invariants I1-I8c, 0 violations = hard gate).
- [ ] Snapshot `docs/harness/reviews/2026-06-XX-l4-guard-witch-coord-prompt-v4-metrics.json` (comparison vs `2026-06-11-l4-guard-prompt-v3-metrics.json` — seat-level paired, no b4 recompute needed).
- [ ] Verdict doc per spec §8 criteria: milk_pierce_death_count 12→≤5 · wolf win ≤65% · L4's 5 primary criteria still pass their ORIGINAL L4 thresholds · witch_save_rate ≥0.3 · hallucination/coverage/invariants no regression. Branch rule: pierce drops but wolf win >65% → next batch = cap=4 (user decision point).

---

## Self-review notes (already applied)

- **Spec coverage:** §3 hook+conditions → T1/T2/T3; §4 verbatim text → T1 (copy from spec, CJK quotes); §5 canaries 1/2 + spent-antidote → T3 (engine level) + T1 (pure level); golden+ledger → T4; §6 metrics split + denominator → T5; §11 backfill gate → T6; §9 regression/visibility → T1 truth table (inputs are public-only by signature) + T7; §7/§8 run+criteria → T8.
- **Ordering:** KNOWN_PROMPT_VERSIONS and REGISTRY change together (T2) or the registry sentinel breaks; golden guard tests (T4) come after the adapter exists (T2) because `canonical_prompt_samples_v4` imports prompt_v4.
- **Known accepted tradeoff (spec §11):** guidance still injects after the guard has died — gating on guard aliveness would BE the private-state leak §3 forbids. Do not "fix" this during execution.
- **`_board_card_has_guard` is a private import** from prompt_v3 — intentional: making it public would edit prompt_v3.py, which is forbidden scope.

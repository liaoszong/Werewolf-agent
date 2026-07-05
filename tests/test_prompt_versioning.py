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


from werewolf_eval.prompt_version import PROMPT_VERSION

GOLDEN_ROOT = ROOT / "tests" / "golden_prompts"
LEDGER_PATH = ROOT / "docs" / "generated-games" / "prompt-version-ledger.json"


def _ledger() -> list[dict]:
    try:
        raw = LEDGER_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise AssertionError(
            f"RULE 2: ledger file missing/unreadable at {LEDGER_PATH} — every "
            f"prompt_version requires a blessed ledger entry"
        ) from exc
    try:
        entries = json.loads(raw)
    except ValueError as exc:
        raise AssertionError(
            f"RULE 2: ledger file is not valid JSON at {LEDGER_PATH}"
        ) from exc
    assert isinstance(entries, list), "RULE 2: ledger root must be a JSON array"
    return entries


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
        for field in (
            "base_version",
            "reason",
            "expected_change",
            "golden_prompt_hashes",
            "behavior_evidence",
            "blessed_by",
            "blessed_at",
        ):
            self.assertIn(field, entry, f"RULE 2: ledger entry missing '{field}'")
        self.assertIn(
            "before", entry["golden_prompt_hashes"],
            "RULE 2: golden_prompt_hashes must carry an explicit 'before' (null for the initial version)",
        )
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
        # Rule 1 is the primary guard for missing/empty golden dirs; assert here too
        # so rule 3 is self-contained and can't silently pass on an unregenerated bump.
        self.assertTrue(base_files, f"RULE 3: base golden dir {base_dir} is empty/missing")
        self.assertTrue(cur_files, f"RULE 3: current golden dir {cur_dir} is empty/missing")
        self.assertFalse(
            base_files == cur_files,
            f"RULE 3: {PROMPT_VERSION} is byte-identical to {base} — meaningless bump",
        )


from werewolf_eval.prompt_goldens import canonical_prompt_samples_v2

PROMPT_V2 = "prompt_v2"


class PromptV2GuardTests(unittest.TestCase):
    """prompt_v2 coexists with prompt_v1; lock its bytes + ledger the same way."""

    def test_v2_rendered_bytes_match_golden(self) -> None:
        golden_dir = GOLDEN_ROOT / PROMPT_V2
        self.assertTrue(golden_dir.is_dir(), "missing tests/golden_prompts/prompt_v2")
        samples = dict(canonical_prompt_samples_v2())
        files = {p.stem: p for p in golden_dir.glob("*.txt")}
        self.assertEqual(sorted(samples), sorted(files))
        for name, text in samples.items():
            self.assertEqual(files[name].read_bytes(), text.encode("utf-8"),
                             f"prompt_v2 bytes changed for '{name}' without regen+ledger")

    def test_v2_ledger_entry_hashes(self) -> None:
        import hashlib
        matches = [e for e in _ledger() if e.get("prompt_version") == PROMPT_V2]
        self.assertEqual(len(matches), 1)
        after = matches[0]["golden_prompt_hashes"]["after"]
        samples = dict(canonical_prompt_samples_v2())
        self.assertEqual(sorted(after), sorted(samples))
        for name, text in samples.items():
            self.assertEqual(after[name], hashlib.sha256(text.encode("utf-8")).hexdigest())

    def test_v2_carries_b1_markers(self) -> None:
        # NOT a v1!=v2 dict compare (sample names differ -> trivially true, zero
        # discrimination). Lock the B1 substance instead: the card exists, the
        # structured sections exist, and the full composition is card-topped.
        samples = dict(canonical_prompt_samples_v2())
        self.assertIn("【本局规则卡】", samples["board_card_standard_6p"])
        self.assertIn("不要在发言中讨论", samples["board_card_standard_6p"])
        for name in ("obs_v2_seer_day", "obs_v2_werewolf_night", "obs_v2_villager_day"):
            self.assertIn("【你的私有信息】", samples[name])
            self.assertIn("【发言记录】", samples[name])
        self.assertTrue(samples["compose_full_v2_speech"].startswith("【本局规则卡】"))
        self.assertIn("表态", samples["speech_villager_v2"])


from werewolf_eval.prompt_goldens import canonical_prompt_samples_v3

PROMPT_V3 = "prompt_v3"


class PromptV3GuardTests(unittest.TestCase):
    """prompt_v3 coexists with v1/v2; lock its bytes + ledger the same way."""

    def test_v3_rendered_bytes_match_golden(self) -> None:
        golden_dir = GOLDEN_ROOT / PROMPT_V3
        self.assertTrue(golden_dir.is_dir(), "missing tests/golden_prompts/prompt_v3")
        samples = dict(canonical_prompt_samples_v3())
        files = {p.stem: p for p in golden_dir.glob("*.txt")}
        self.assertEqual(sorted(samples), sorted(files))
        for name, text in samples.items():
            self.assertEqual(files[name].read_bytes(), text.encode("utf-8"),
                             f"prompt_v3 bytes changed for '{name}' without regen+ledger")

    def test_v3_ledger_entry_hashes(self) -> None:
        import hashlib
        matches = [e for e in _ledger() if e.get("prompt_version") == PROMPT_V3]
        self.assertEqual(len(matches), 1)
        after = matches[0]["golden_prompt_hashes"]["after"]
        samples = dict(canonical_prompt_samples_v3())
        self.assertEqual(sorted(after), sorted(samples))
        for name, text in samples.items():
            self.assertEqual(after[name], hashlib.sha256(text.encode("utf-8")).hexdigest())

    def test_v3_carries_b4_markers(self) -> None:
        # B4 实质标记断言(不做 v2!=v3 恒真比较):scribe=提取非裁判;digest=出处定位;
        # vote scaffold=程序+护栏;speech v3=克制(无判别词)
        samples = dict(canonical_prompt_samples_v3())
        self.assertIn("只负责提取", samples["scribe_system_prompt"])
        self.assertIn("source_quote", samples["scribe_system_prompt"])
        self.assertIn("以原文为准", samples["claim_digest_two_claims"])
        self.assertIn("[不确定]", samples["claim_digest_two_claims"])
        self.assertIn("【投票前判断程序】", samples["vote_scaffold_with_claims"])
        self.assertIn("不要因为出现对跳就自动否定先声称者", samples["vote_scaffold_with_claims"])
        self.assertIn("【投票前判断程序】", samples["vote_scaffold_empty_ledger"])
        self.assertNotIn("【声称账本】", samples["vote_scaffold_empty_ledger"])
        self.assertNotIn("对跳", samples["speech_villager_v3"])
        self.assertNotIn("表态", samples["speech_villager_v3"])


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


from werewolf_eval.prompt_goldens import canonical_prompt_samples_v5

PROMPT_V5 = "prompt_v5"


class PromptV5GuardTests(unittest.TestCase):
    """prompt_v5 coexists with v1-v4; lock the P3-A roleplay context bytes."""

    def test_v5_rendered_bytes_match_golden(self) -> None:
        golden_dir = GOLDEN_ROOT / PROMPT_V5
        self.assertTrue(golden_dir.is_dir(), "missing tests/golden_prompts/prompt_v5")
        samples = dict(canonical_prompt_samples_v5())
        files = {p.stem: p for p in golden_dir.glob("*.txt")}
        self.assertEqual(sorted(samples), sorted(files))
        for name, text in samples.items():
            self.assertEqual(files[name].read_bytes(), text.encode("utf-8"),
                             f"prompt_v5 bytes changed for '{name}' without regen+ledger")

    def test_v5_ledger_entry_hashes(self) -> None:
        import hashlib
        matches = [e for e in _ledger() if e.get("prompt_version") == PROMPT_V5]
        self.assertEqual(len(matches), 1)
        after = matches[0]["golden_prompt_hashes"]["after"]
        samples = dict(canonical_prompt_samples_v5())
        self.assertEqual(sorted(after), sorted(samples))
        for name, text in samples.items():
            self.assertEqual(after[name], hashlib.sha256(text.encode("utf-8")).hexdigest())

    def test_v5_carries_roleplay_markers(self) -> None:
        samples = dict(canonical_prompt_samples_v5())
        text = samples["roleplay_context_werewolf_with_packet"]
        self.assertIn("【角色策略】", text)
        self.assertIn("【上下文记忆】", text)
        self.assertIn("hide team identity", text)
        self.assertIn("this is not engine truth", text)


if __name__ == "__main__":
    unittest.main()

# tests/test_ablation_guardrails.py
"""Ablation guardrails hardening — batch ① (C3-4 + C12-04 + C12-03 + C12-10/11).

Each test is written RED-first against `main` (8b6d32c). The matching
implementation lives in `src/werewolf_eval/ablation/{harness,metrics}.py`.
See `docs/harness/plans/2026-06-12-ablation-guardrails-plan.md` for scope.
"""
from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.ablation.arms import Arm
from werewolf_eval.ablation.harness import run_arm
from werewolf_eval.ablation.metrics import (
    aggregate,
    aggregate_games,
    analyze_game_dict,
    classify_event,
)
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
)


FIX = Path(__file__).parent / "fixtures" / "ablation"


def _fake_factory(arm, api_key):
    agents = build_emergent_fake_agents(build_villager_win_script())
    return lambda pid: agents[pid]


def _ev(rnd, phase, actor, target, summary):
    return {"round": rnd, "phase": phase, "actor": actor, "target": target,
            "data": {"summary": summary}}


# ---------------------------------------------------------------------------
# C3-4: harness.run_arm calls check_run and writes validity.invariants
# ---------------------------------------------------------------------------


class HarnessInvariantsWiringTests(unittest.TestCase):
    """`check_run` runs after every game; the per-arm rollup is written into
    `_metrics.json` under `validity.invariants` (additive field)."""

    def test_run_arm_writes_validity_invariants_block(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            arm = Arm(label="c34_inv", prompt_version="prompt_v1", n_games=1, seed_base=7)
            result = run_arm(arm, out_root=Path(tmp), factory_builder=_fake_factory)
            self.assertIn("validity", result)
            inv = result["validity"].get("invariants")
            self.assertIsInstance(inv, dict)
            self.assertEqual(inv["n_games_checked"], 1)
            self.assertIn("n_games_clean", inv)
            self.assertIn("n_violations", inv)
            self.assertIn("violations_by_id", inv)

    def test_run_arm_writes_per_index_row_invariants(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            arm = Arm(label="c34_idx", prompt_version="prompt_v1", n_games=1, seed_base=7)
            run_arm(arm, out_root=Path(tmp), factory_builder=_fake_factory)
            rows = [json.loads(line) for line in
                    (Path(tmp) / "c34_idx" / "_index.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertIn("invariants", rows[0])
            # Each per-row invariants block carries the game's own violation list.
            self.assertIn("violations", rows[0]["invariants"])

    def test_validity_invariants_persisted_in_metrics_json(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            arm = Arm(label="c34_disk", prompt_version="prompt_v1", n_games=1, seed_base=7)
            run_arm(arm, out_root=Path(tmp), factory_builder=_fake_factory)
            on_disk = json.loads(
                (Path(tmp) / "c34_disk" / "_metrics.json").read_text(encoding="utf-8"))
            self.assertIn("validity", on_disk)
            self.assertIn("invariants", on_disk["validity"])

    def test_run_arm_counts_violations_per_id(self):
        """P2-1: monkeypatch _check_run to return violations, verify rollup."""
        import tempfile
        from unittest.mock import patch
        from werewolf_eval.invariants.checker import InvariantViolation

        fake_violations = [
            InvariantViolation("I4b", "error", "g1", (), "leak detected"),
            InvariantViolation("I4b", "error", "g1", (), "leak detected again"),
            InvariantViolation("I1", "error", "g1", (), "double death"),
            InvariantViolation("artifact_gap", "artifact_gap", "g1", (), "missing trace"),
        ]

        def fake_check_run(out_dir):
            return fake_violations

        with tempfile.TemporaryDirectory() as tmp:
            arm = Arm(label="c34_viol", prompt_version="prompt_v1", n_games=1, seed_base=7)
            with patch("werewolf_eval.ablation.harness._check_run", side_effect=fake_check_run):
                result = run_arm(arm, out_root=Path(tmp), factory_builder=_fake_factory)
            inv = result["validity"]["invariants"]
            self.assertEqual(inv["n_games_checked"], 1)
            self.assertEqual(inv["n_games_clean"], 0)  # has violations
            self.assertEqual(inv["n_violations"], 3)   # 2x I4b + 1x I1, not artifact_gap
            self.assertEqual(inv["violations_by_id"], {"I4b": 2, "I1": 1})
            self.assertEqual(inv["n_checker_errors"], 0)
            self.assertEqual(inv["checker_error_games"], [])

    def test_run_arm_tracks_checker_errors(self):
        """P2-1: monkeypatch _check_run to raise, verify n_checker_errors."""
        import tempfile
        from unittest.mock import patch

        def broken_check_run(out_dir):
            raise RuntimeError("checker exploded")

        with tempfile.TemporaryDirectory() as tmp:
            arm = Arm(label="c34_err", prompt_version="prompt_v1", n_games=2, seed_base=7)
            with patch("werewolf_eval.ablation.harness._check_run", side_effect=broken_check_run):
                result = run_arm(arm, out_root=Path(tmp), factory_builder=_fake_factory)
            inv = result["validity"]["invariants"]
            self.assertEqual(inv["n_games_checked"], 0)  # checker never succeeded
            self.assertEqual(inv["n_games_clean"], 0)
            self.assertEqual(inv["n_violations"], 0)
            self.assertEqual(inv["n_checker_errors"], 2)  # both games failed
            self.assertEqual(len(inv["checker_error_games"]), 2)
            # Per-row invariants should record the error
            rows = [json.loads(line) for line in
                    (Path(tmp) / "c34_err" / "_index.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()]
            for row in rows:
                self.assertIn("invariants_error", row["invariants"])
                self.assertIn("RuntimeError", row["invariants"]["invariants_error"])

    def test_non_completed_game_has_null_invariants(self):
        """P3-3: non-completed games get explicit null invariants for schema uniformity."""
        import tempfile
        from unittest.mock import patch

        def fail_factory(arm, api_key):
            raise RuntimeError("provider exploded")

        with tempfile.TemporaryDirectory() as tmp:
            arm = Arm(label="c34_fail", prompt_version="prompt_v1", n_games=1, seed_base=7)
            result = run_arm(arm, out_root=Path(tmp), factory_builder=fail_factory)
            rows = [json.loads(line) for line in
                    (Path(tmp) / "c34_fail" / "_index.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0]["invariants"])  # P3-3: explicit null


# ---------------------------------------------------------------------------
# C12-04: run_arm rejects non-empty arm_dir
# ---------------------------------------------------------------------------


class RunArmNonEmptyDirTests(unittest.TestCase):
    """Re-running into a populated arm_dir must fail loud (no silent mixing)."""

    def test_run_arm_rejects_dir_with_prior_games(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            arm = Arm(label="c1204_reuse", prompt_version="prompt_v1", n_games=1, seed_base=7)
            run_arm(arm, out_root=Path(tmp), factory_builder=_fake_factory)
            with self.assertRaises(FileExistsError):
                run_arm(arm, out_root=Path(tmp), factory_builder=_fake_factory)

    def test_run_arm_allows_fresh_empty_dir(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            arm = Arm(label="c1204_fresh", prompt_version="prompt_v1", n_games=1, seed_base=7)
            # out_root itself may not even exist yet — run_arm creates it.
            result = run_arm(arm, out_root=Path(tmp) / "nested", factory_builder=_fake_factory)
            self.assertEqual(result["arm"], "c1204_fresh")


# ---------------------------------------------------------------------------
# C12-04: aggregate asserts uniform evaluation_bucket across valid games
# ---------------------------------------------------------------------------


def _stamp_manifest(run_dir: Path, bucket):
    """Write a minimal prompt-manifest.json with the given evaluation_bucket."""
    manifest = {"evaluation_bucket": bucket}
    (run_dir / "prompt-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")


class AggregateBucketAssertionTests(unittest.TestCase):
    """aggregate() reads each run's prompt-manifest.json and fails loud on
    cross-bucket mixing; the matching bucket is written into the output."""

    def test_uniform_bucket_is_written_into_output(self):
        import tempfile
        bucket = {"rules_version": "rules_v1_2", "prompt_version": "prompt_v1",
                  "scoring_version": "scoring_v1",
                  "comparison_key": "rules_v1_2__prompt_v1__scoring_v1"}
        with tempfile.TemporaryDirectory() as tmp:
            dirs = []
            for name in ("g_a", "g_b"):
                d = Path(tmp) / name
                shutil.copytree(FIX / "diag_A_seer_p1_0", d)
                _stamp_manifest(d, bucket)
                dirs.append(d)
            agg = aggregate(dirs)
            self.assertEqual(agg["evaluation_bucket"], bucket)

    def test_mismatched_buckets_raise(self):
        import tempfile
        bA = {"rules_version": "rules_v1_2", "prompt_version": "prompt_v1",
              "scoring_version": "scoring_v1",
              "comparison_key": "rules_v1_2__prompt_v1__scoring_v1"}
        bB = {"rules_version": "rules_v1_2", "prompt_version": "prompt_v2",
              "scoring_version": "scoring_v1",
              "comparison_key": "rules_v1_2__prompt_v2__scoring_v1"}
        with tempfile.TemporaryDirectory() as tmp:
            dA = Path(tmp) / "g_a"; shutil.copytree(FIX / "diag_A_seer_p1_0", dA)
            dB = Path(tmp) / "g_b"; shutil.copytree(FIX / "diag_A_seer_p2_3", dB)
            _stamp_manifest(dA, bA)
            _stamp_manifest(dB, bB)
            with self.assertRaises(ValueError) as ctx:
                aggregate([dA, dB])
            self.assertIn("evaluation_bucket", str(ctx.exception))

    def test_all_legacy_bucket_is_none(self):
        # Existing fixtures have NO prompt-manifest.json → all-legacy arm.
        dirs = sorted(p for p in FIX.iterdir() if p.is_dir())
        agg = aggregate(dirs)
        self.assertIsNone(agg["evaluation_bucket"])

    def test_mixed_legacy_and_modern_raises(self):
        import tempfile
        bucket = {"rules_version": "rules_v1_2", "prompt_version": "prompt_v1",
                  "scoring_version": "scoring_v1",
                  "comparison_key": "rules_v1_2__prompt_v1__scoring_v1"}
        with tempfile.TemporaryDirectory() as tmp:
            d_modern = Path(tmp) / "modern"
            shutil.copytree(FIX / "diag_A_seer_p1_0", d_modern)
            _stamp_manifest(d_modern, bucket)
            d_legacy = Path(tmp) / "legacy"
            shutil.copytree(FIX / "diag_A_seer_p2_3", d_legacy)
            # legacy dir has no manifest — that's the point.
            with self.assertRaises(ValueError):
                aggregate([d_modern, d_legacy])

    def test_manifest_exists_but_no_bucket_raises(self):
        """P1-1: manifest exists but evaluation_bucket is missing/None → fail-loud."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "bad_manifest"
            shutil.copytree(FIX / "diag_A_seer_p1_0", d)
            # Write a manifest WITHOUT evaluation_bucket
            (d / "prompt-manifest.json").write_text(
                json.dumps({"some_other_field": "value"}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                aggregate([d])
            self.assertIn("evaluation_bucket", str(ctx.exception))

    def test_manifest_exists_but_bucket_is_null_raises(self):
        """P1-1: manifest exists but evaluation_bucket is explicitly null → fail-loud."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "null_bucket"
            shutil.copytree(FIX / "diag_A_seer_p1_0", d)
            (d / "prompt-manifest.json").write_text(
                json.dumps({"evaluation_bucket": None}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                aggregate([d])
            self.assertIn("evaluation_bucket", str(ctx.exception))


# ---------------------------------------------------------------------------
# C12-03: milk_pierce None on non-guard boards (per-game)
# ---------------------------------------------------------------------------


def _non_guard_game(events):
    """Standard 6p board (no guard)."""
    return {
        "players": [
            {"player_id": "p1", "role": "werewolf"}, {"player_id": "p2", "role": "werewolf"},
            {"player_id": "p3", "role": "seer"}, {"player_id": "p4", "role": "witch"},
            {"player_id": "p5", "role": "villager"}, {"player_id": "p6", "role": "villager"},
        ],
        "events": events,
        "result": {"winner": "villager", "end_round": 2},
    }


class MilkPierceNoneOnNonGuardBoardTests(unittest.TestCase):
    """Per-game: non-guard boards report milk_pierce_{overlap,death} as None,
    aligning with the guard_target_seer_rate/_mean family convention."""

    def test_per_game_milk_pierce_none_on_non_guard_board(self):
        row = analyze_game_dict(_non_guard_game([
            _ev(1, "night", "p1", "p3", "Wolf team kills p3."),
            _ev(1, "night", "p4", "p3", "Witch saves p3."),
        ]))
        self.assertIsNone(row["milk_pierce_overlap"])
        self.assertIsNone(row["milk_pierce_death"])

    def test_per_game_milk_pierce_integer_on_guard_board(self):
        # Regression pin: guard boards still produce integer counts.
        guard_game = {
            "players": [
                {"player_id": "p1", "role": "werewolf"}, {"player_id": "p2", "role": "werewolf"},
                {"player_id": "p3", "role": "seer"}, {"player_id": "p4", "role": "witch"},
                {"player_id": "p5", "role": "guard"}, {"player_id": "p6", "role": "villager"},
            ],
            "events": [
                _ev(1, "night", "p5", "p3", "Guard p5 protects p3."),
                _ev(1, "night", "p1", "p3", "Wolf team kills p3."),
                _ev(1, "night", "p4", "p3", "Witch saves p3."),
                _ev(1, "night", "system", "p3", "p3 died during the night."),
            ],
            "result": {"winner": "werewolf", "end_round": 1},
        }
        row = analyze_game_dict(guard_game)
        self.assertEqual(row["milk_pierce_overlap"], 1)
        self.assertEqual(row["milk_pierce_death"], 1)


# ---------------------------------------------------------------------------
# C12-10: milk_pierce_*_rate (per-n_valid mean) — additive over the counts
# ---------------------------------------------------------------------------


class MilkPierceRateTests(unittest.TestCase):
    """aggregate_games emits milk_pierce_{overlap,death}_rate as _mean over
    valid games; None on non-guard boards, float on guard boards."""

    def test_rate_is_none_on_non_guard_arm(self):
        rows = [analyze_game_dict(_non_guard_game([])) for _ in range(3)]
        agg = aggregate_games(rows)
        self.assertIsNone(agg.get("milk_pierce_overlap_rate"))
        self.assertIsNone(agg.get("milk_pierce_death_rate"))

    def test_rate_is_mean_over_guard_arm(self):
        guard_games = []
        for overlap, death in [(1, 1), (0, 0), (1, 0)]:
            evs = []
            if overlap:
                evs += [
                    _ev(1, "night", "p5", "p3", "Guard p5 protects p3."),
                    _ev(1, "night", "p1", "p3", "Wolf team kills p3."),
                    _ev(1, "night", "p4", "p3", "Witch saves p3."),
                ]
                if death:
                    evs.append(_ev(1, "night", "system", "p3", "p3 died during the night."))
            else:
                evs += [
                    _ev(1, "night", "p5", "p6", "Guard p5 protects p6."),
                    _ev(1, "night", "p1", "p3", "Wolf team kills p3."),
                ]
            guard_games.append({
                "players": [
                    {"player_id": "p1", "role": "werewolf"},
                    {"player_id": "p2", "role": "werewolf"},
                    {"player_id": "p3", "role": "seer"},
                    {"player_id": "p4", "role": "witch"},
                    {"player_id": "p5", "role": "guard"},
                    {"player_id": "p6", "role": "villager"},
                ],
                "events": evs,
                "result": {"winner": "werewolf", "end_round": 1},
            })
        rows = [analyze_game_dict(g) for g in guard_games]
        agg = aggregate_games(rows)
        # overlap: 1, 0, 1 -> mean 2/3; death: 1, 0, 0 -> mean 1/3
        self.assertAlmostEqual(agg["milk_pierce_overlap_rate"], 2 / 3)
        self.assertAlmostEqual(agg["milk_pierce_death_rate"], 1 / 3)

    def test_rate_in_default_compare_keys(self):
        from werewolf_eval.ablation.metrics import DEFAULT_COMPARE_KEYS
        self.assertIn("milk_pierce_overlap_rate", DEFAULT_COMPARE_KEYS)
        self.assertIn("milk_pierce_death_rate", DEFAULT_COMPARE_KEYS)


# ---------------------------------------------------------------------------
# P2-2: aggregate_games([]) returns full schema (all DEFAULT_COMPARE_KEYS present)
# ---------------------------------------------------------------------------


class AggregateGamesEmptySchemaTests(unittest.TestCase):
    """P2-2: aggregate_games([]) returns the full schema so downstream
    consumers can iterate DEFAULT_COMPARE_KEYS without KeyError."""

    def test_empty_games_returns_full_schema(self):
        from werewolf_eval.ablation.metrics import DEFAULT_COMPARE_KEYS
        agg = aggregate_games([])
        self.assertEqual(agg["n_valid"], 0)
        for key in DEFAULT_COMPARE_KEYS:
            self.assertIn(key, agg, f"missing key {key!r} in empty aggregate")

    def test_empty_games_rates_are_none_counts_are_zero(self):
        agg = aggregate_games([])
        # Rates/means should be None
        self.assertIsNone(agg["wolf_win_rate"])
        self.assertIsNone(agg["day1_hit"])
        self.assertIsNone(agg["milk_pierce_overlap_rate"])
        self.assertIsNone(agg["guard_target_seer_rate"])
        # Counts should be 0
        self.assertEqual(agg["milk_pierce_overlap_count"], 0)
        self.assertEqual(agg["milk_pierce_death_count"], 0)
        self.assertEqual(agg["verify_wolf_followed_n"], 0)
        self.assertEqual(agg["seer_claim_to_night_survival_n"], 0)
        # Distributions should be empty
        self.assertEqual(agg["night1_kill_dist"], {})


# ---------------------------------------------------------------------------
# C12-11: classify_event phase guard — day-phase keyword speeches classify
# as `speech`, not as night-action kinds.
# ---------------------------------------------------------------------------


class ClassifyEventPhaseGuardTests(unittest.TestCase):
    """Day-phase speeches containing `saves` / `poison` / `no potion` keywords
    must NOT be mis-classified as witch actions."""

    def test_day_saves_speech_classifies_as_speech(self):
        kind, *_ = classify_event(_ev(
            1, "day", "p5", None,
            "我觉得女巫昨晚 saves 了人，节奏不对。"))
        self.assertEqual(kind, "speech")

    def test_day_poison_speech_classifies_as_speech(self):
        kind, *_ = classify_event(_ev(
            1, "day", "p5", None,
            "他可能在 poison 别人，大家小心。"))
        self.assertEqual(kind, "speech")

    def test_day_no_potion_speech_classifies_as_speech(self):
        kind, *_ = classify_event(_ev(
            1, "day", "p5", None,
            "如果女巫 no potion 那今晚很危险。"))
        self.assertEqual(kind, "speech")

    def test_night_saves_still_classifies_as_witch_save(self):
        # Regression pin: legitimate night witch events still work.
        kind, actor, tgt, _ = classify_event(_ev(
            1, "night", "p4", "p3", "Witch p4 saves p3."))
        self.assertEqual(kind, "witch_save")
        self.assertEqual((actor, tgt), ("p4", "p3"))

    def test_night_poison_still_classifies_as_witch_poison(self):
        kind, actor, tgt, _ = classify_event(_ev(
            1, "night", "p4", "p5", "Witch p4 poisons p5."))
        self.assertEqual(kind, "witch_poison")

    def test_phase_missing_still_classifies_as_witch_action(self):
        # Legacy events with no phase field — preserve old behavior.
        kind, *_ = classify_event({
            "round": 1, "actor": "p4", "target": "p3",
            "data": {"summary": "Witch p4 saves p3."},
        })
        self.assertEqual(kind, "witch_save")


if __name__ == "__main__":
    unittest.main()

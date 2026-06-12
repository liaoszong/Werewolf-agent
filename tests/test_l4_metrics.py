# tests/test_l4_metrics.py
"""L4 metrics: board-aware mechanic words, guard metrics, peaceful nights."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.ablation.metrics import analyze_game_dict, aggregate_games, classify_event


def _ev(rnd, phase, etype, actor, target, summary):
    return {"event_id": f"e{rnd}{etype}", "sequence": 0, "round": rnd, "phase": phase,
            "type": etype, "actor": actor, "target": target, "visibility": "internal",
            "data": {"summary": summary}}


def _guard_game(speech_text="大家好"):
    players = [
        {"player_id": "p1", "role": "werewolf"}, {"player_id": "p2", "role": "werewolf"},
        {"player_id": "p3", "role": "seer"}, {"player_id": "p4", "role": "witch"},
        {"player_id": "p5", "role": "guard"}, {"player_id": "p6", "role": "villager"},
    ]
    events = [
        _ev(1, "night", "guard_protect", "p5", "p3", "Guard p5 protects p3."),
        _ev(1, "night", "werewolf_kill", "p1", "p3", "Wolf team kills p3."),
        _ev(1, "day", "day_announcement", "system", "none", "A peaceful night: nobody died."),
        _ev(1, "day", "player_speech", "p6", "none", speech_text),
        _ev(2, "night", "guard_protect", "p5", "p6", "Guard p5 protects p6."),
        _ev(2, "night", "werewolf_kill", "p1", "p4", "Wolf team kills p4."),
        _ev(2, "night", "player_died", "system", "p4", "p4 died during the night."),
    ]
    return {"players": players, "events": events,
            "result": {"winner": "werewolf", "end_round": 2}}


class ClassifyGuardEventsTests(unittest.TestCase):
    def test_guard_and_peaceful_kinds(self):
        kind, actor, tgt, _ = classify_event(
            _ev(1, "night", "guard_protect", "p5", "p3", "Guard p5 protects p3."))
        self.assertEqual((kind, actor, tgt), ("guard", "p5", "p3"))
        kind, _, _, _ = classify_event(
            _ev(1, "day", "day_announcement", "system", "none", "A peaceful night: nobody died."))
        self.assertEqual(kind, "peaceful")


class GuardMetricsTests(unittest.TestCase):
    def test_per_game_guard_metrics(self):
        row = analyze_game_dict(_guard_game())
        self.assertEqual(row["guard_nights"], 2)
        self.assertEqual(row["guard_target_seer_share"], 0.5)   # r1 守 seer p3
        self.assertEqual(row["guard_block_share"], 0.5)         # r1 守==刀
        self.assertEqual(row["n_peaceful_nights"], 1)
        self.assertIsNone(row["seer_death"])                    # seer 没死

    def test_guard_board_mechanic_words_exclude_guard(self):
        # 守卫板上正当讨论守卫 ≠ 机制幻觉;警长仍是幻觉词
        row = analyze_game_dict(_guard_game(speech_text="我觉得守卫昨晚守对了"))
        self.assertFalse(row["has_mechanic_halluc"])
        row2 = analyze_game_dict(_guard_game(speech_text="警长应该带队"))
        self.assertTrue(row2["has_mechanic_halluc"])

    def test_non_guard_board_words_unchanged(self):
        g = _guard_game(speech_text="守卫会救我们")
        for p in g["players"]:
            if p["role"] == "guard":
                p["role"] = "villager"
        g["events"] = [e for e in g["events"] if e["type"] != "guard_protect"]
        row = analyze_game_dict(g)
        self.assertTrue(row["has_mechanic_halluc"])   # 无守卫板:守卫仍是幻觉词

    def test_aggregate_keys(self):
        agg = aggregate_games([analyze_game_dict(_guard_game())])
        self.assertEqual(agg["guard_target_seer_rate"], 0.5)
        self.assertEqual(agg["guard_success_rate"], 0.5)
        self.assertEqual(agg["avg_peaceful_nights"], 1.0)
        self.assertEqual(agg["seer_death_rate"], 0.0)
        self.assertEqual(agg["seer_night_death_rate"], 0.0)


class SeerClaimSurvivalTests(unittest.TestCase):
    """provider-trace.json in its REAL shape ({requests, responses} joined on
    request_id — verified against .runs/ablation/b4/b4_000)."""

    def _trace_dir(self, tmp, claims_json, rnd=1):
        d = Path(tmp)
        trace = {
            "game_id": "t", "provider_name": "x", "source_label": "x", "failures": [],
            "requests": [{"actor": "scribe", "round": rnd, "request_id": f"t_r{rnd:02d}_scribe",
                          "response_kind": "scaffold", "phase": "day"}],
            "responses": [{"request_id": f"t_r{rnd:02d}_scribe", "raw_content": claims_json,
                           "latency_ms": 1, "provider_name": "x", "source_label": "x",
                           "token_usage": {}}],
        }
        (d / "provider-trace.json").write_text(
            __import__("json").dumps(trace, ensure_ascii=False), encoding="utf-8")
        return d

    def test_claim_then_night_death_is_false(self):
        import tempfile
        from werewolf_eval.ablation.metrics import seer_claim_to_night_survival
        claims = ('{"claims":[{"claimant":"p3","claim_type":"check_report","target":"p1",'
                  '"result":"狼人","refutes":null,"source":1,"source_quote":"我验了p1","uncertain":false}]}')
        with tempfile.TemporaryDirectory() as tmp:
            d = self._trace_dir(tmp, claims)
            row = {"seer": "p3", "end_round": 2, "seer_death": [2, "night"]}
            self.assertIs(seer_claim_to_night_survival(d, row), False)

    def test_claim_then_survival_is_true(self):
        import tempfile
        from werewolf_eval.ablation.metrics import seer_claim_to_night_survival
        claims = ('{"claims":[{"claimant":"p3","claim_type":"identity_claim","target":null,'
                  '"result":"预言家","refutes":null,"source":1,"source_quote":"我是预言家","uncertain":false}]}')
        with tempfile.TemporaryDirectory() as tmp:
            d = self._trace_dir(tmp, claims)
            row = {"seer": "p3", "end_round": 3, "seer_death": None}
            self.assertIs(seer_claim_to_night_survival(d, row), True)

    def test_no_claim_or_no_exposure_is_none(self):
        import tempfile
        from werewolf_eval.ablation.metrics import seer_claim_to_night_survival
        with tempfile.TemporaryDirectory() as tmp:
            d = self._trace_dir(tmp, '{"claims":[]}')
            self.assertIsNone(seer_claim_to_night_survival(
                d, {"seer": "p3", "end_round": 2, "seer_death": None}))
            # 报验在终局轮:没有下一夜 -> 无暴露,不计入分母
            d2 = self._trace_dir(tmp, '{"claims":[{"claimant":"p3","claim_type":"check_report",'
                                      '"target":"p1","result":"狼人","refutes":null,"source":1,'
                                      '"source_quote":"我验了p1","uncertain":false}]}')
            self.assertIsNone(seer_claim_to_night_survival(
                d2, {"seer": "p3", "end_round": 1, "seer_death": None}))


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

    def test_compare_keys_include_milk_pierce_family(self):
        from werewolf_eval.ablation.metrics import DEFAULT_COMPARE_KEYS
        for k in ("milk_pierce_overlap_count", "milk_pierce_death_count", "witch_save_night1_share"):
            self.assertIn(k, DEFAULT_COMPARE_KEYS)

    def test_aggregate_milk_pierce_rate_guard_board(self):
        """P3-1: milk_pierce_{overlap,death}_rate on guard boards = _mean over games."""
        g_pierce = analyze_game_dict(_witch_coord_game(list(_PIERCE_R1)))
        g_no_pierce = analyze_game_dict(_witch_coord_game([
            _ev(1, "night", "guard_protect", "p5", "p6", "Guard p5 protects p6."),
            _ev(1, "night", "werewolf_kill", "p1", "p3", "Wolf team kills p3."),
        ]))
        agg = aggregate_games([g_pierce, g_no_pierce])
        # overlap: 1, 0 -> mean 0.5; death: 1, 0 -> mean 0.5
        self.assertAlmostEqual(agg["milk_pierce_overlap_rate"], 0.5)
        self.assertAlmostEqual(agg["milk_pierce_death_rate"], 0.5)

    def test_aggregate_milk_pierce_rate_non_guard_board_is_none(self):
        """P3-1: milk_pierce_{overlap,death}_rate on non-guard boards = None."""
        # Non-guard board: no guard role
        non_guard_game = {
            "players": [
                {"player_id": "p1", "role": "werewolf"}, {"player_id": "p2", "role": "werewolf"},
                {"player_id": "p3", "role": "seer"}, {"player_id": "p4", "role": "witch"},
                {"player_id": "p5", "role": "villager"}, {"player_id": "p6", "role": "villager"},
            ],
            "events": [
                _ev(1, "night", "werewolf_kill", "p1", "p3", "Wolf team kills p3."),
                _ev(1, "night", "witch_action", "p4", "p3", "Witch saves p3."),
            ],
            "result": {"winner": "villager", "end_round": 2},
        }
        row = analyze_game_dict(non_guard_game)
        agg = aggregate_games([row])
        self.assertIsNone(agg["milk_pierce_overlap_rate"])
        self.assertIsNone(agg["milk_pierce_death_rate"])
        # Counts should still be 0 (not None) for backward compatibility
        self.assertEqual(agg["milk_pierce_overlap_count"], 0)
        self.assertEqual(agg["milk_pierce_death_count"], 0)


if __name__ == "__main__":
    unittest.main()

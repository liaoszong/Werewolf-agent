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


if __name__ == "__main__":
    unittest.main()

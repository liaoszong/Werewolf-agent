from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.decision_log import load_decision_log, parse_decision_log
from werewolf_eval.game_log import Event, GameLog, GameResult, Player, load_game_log
from werewolf_eval.scoring import (
    _result_metrics,
    metrics_summary_to_dict,
    score_game,
    score_log_to_dict,
    summarize_metrics,
)
from werewolf_eval.semantic_labels import load_semantic_label_log


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class DeterministicScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.decision_log = load_decision_log(ROOT / "docs/gold-game/g001-decision-log.json", self.game)
        self.score_log = score_game(self.game)
        self.metrics = summarize_metrics(self.game, self.score_log)
        self.d2_score_log = score_game(self.game, decision_log=self.decision_log)
        self.d2_metrics = summarize_metrics(self.game, self.d2_score_log)
        self.semantic_label_log = load_semantic_label_log(
            ROOT / "docs/gold-game/s5-semantic-label-output.example.json",
            self.decision_log,
        )
        self.s5_score_log = score_game(
            self.game,
            decision_log=self.decision_log,
            semantic_label_log=self.semantic_label_log,
        )
        self.s5_metrics = summarize_metrics(self.game, self.s5_score_log)

    def test_score_log_matches_s2_expected_records(self) -> None:
        actual = score_log_to_dict(self.d2_score_log)
        expected = load_json("docs/gold-game/s2-score-log.json")
        self.assertEqual(actual, expected)

    def test_metrics_summary_matches_s2_expected(self) -> None:
        actual = metrics_summary_to_dict(self.d2_metrics)
        expected = load_json("docs/gold-game/s2-metrics-summary.json")
        self.assertEqual(actual, expected)

    def test_decision_quality_is_zero_without_decision_log(self) -> None:
        self.assertTrue(self.score_log.records)
        for record in self.score_log.records:
            self.assertIsNone(record.decision_id)
            self.assertEqual(record.decision_quality_score, 0)

    def test_rule_integrity_defaults_to_zero_without_flag_events(self) -> None:
        self.assertTrue(self.score_log.records)
        for record in self.score_log.records:
            self.assertEqual(record.rule_integrity_score, 0)

    def test_score_records_reference_existing_events(self) -> None:
        event_ids = self.game.event_ids
        for record in self.score_log.records:
            self.assertIn(record.event_id, event_ids)
            for evidence_event_id in record.evidence_event_ids:
                self.assertIn(evidence_event_id, event_ids)

    def test_known_rubric_gaps_are_preserved(self) -> None:
        score_payload = score_log_to_dict(self.score_log)
        metrics_payload = metrics_summary_to_dict(self.metrics)
        score_rules = {
            rule
            for record in score_payload["records"]
            for rule in record["rules_triggered"]
        }
        self.assertIn("rubric-gap:werewolf_day_vote_without_elimination", score_rules)
        self.assertIn("rubric-gap:witch_day_vote_outcome_not_explicit", score_rules)

        gaps = {item["gap"] for item in metrics_payload["known_rubric_gaps_recorded_not_fixed"]}
        self.assertEqual(
            gaps,
            {"werewolf_day_vote_without_elimination", "witch_day_vote_outcome_not_explicit"},
        )

    def test_d2_decision_log_attaches_decision_id_and_preserves_quality_zero(self) -> None:
        records = {record.event_id: record for record in self.d2_score_log.records}

        self.assertEqual(records["g001_e019"].decision_id, "g001_d007")
        self.assertEqual(records["g001_e019"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.decision_logged", records["g001_e019"].rules_triggered)

        self.assertEqual(records["g001_e025"].decision_id, "g001_d009")
        self.assertEqual(records["g001_e025"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.decision_logged", records["g001_e025"].rules_triggered)

        self.assertEqual(records["g001_e035"].decision_id, "g001_d010")
        self.assertEqual(records["g001_e035"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.decision_logged", records["g001_e035"].rules_triggered)

    def test_d2_default_or_empty_ref_decisions_keep_quality_zero(self) -> None:
        records = {record.event_id: record for record in self.d2_score_log.records}

        self.assertEqual(records["g001_e020"].decision_id, "g001_d008")
        self.assertEqual(records["g001_e020"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.no_decision_quality_for_default", records["g001_e020"].rules_triggered)

    def test_d2_illegal_visible_info_ref_penalizes_rule_integrity(self) -> None:
        raw = load_json("docs/gold-game/g001-decision-log.json")
        raw["decisions"] = [
            {
                "decision_id": "bad_d001",
                "actor": "p5",
                "decision_scope": "single",
                "consensus_id": None,
                "phase": "day",
                "action": "player_vote",
                "target": "p3",
                "visible_info_refs": ["g001_e008"],
                "reason_summary": "p5 illegally relies on the seer-only check result.",
                "decision_type": "inference_based",
                "confidence": 0.5,
                "strategy_tag": "illegal_ref_test",
            }
        ]
        decision_log = parse_decision_log(raw, self.game)

        score_log = score_game(self.game, decision_log=decision_log)
        records = {record.event_id: record for record in score_log.records}

        self.assertEqual(records["g001_e020"].decision_id, "bad_d001")
        self.assertEqual(records["g001_e020"].decision_quality_score, 0)
        self.assertEqual(records["g001_e020"].rule_integrity_score, -3)
        self.assertIn("rubric:G.1.illegal_visible_info_ref", records["g001_e020"].rules_triggered)

    def test_d2_metrics_summary_reflects_decision_log_input(self) -> None:
        payload = metrics_summary_to_dict(self.d2_metrics)
        decision_scores = payload["score_summary"]["player_decision_quality_scores"]

        # D2 does not assign positive decision_quality_score.
        # All scores remain 0; the value is in decision_id traceability and rule_integrity checks.
        self.assertEqual(decision_scores["p4"], 0)
        self.assertEqual(decision_scores["p6"], 0)
        self.assertEqual(decision_scores["p5"], 0)

        # D2-only mode must not add any semantic rules
        d2_records = {record.event_id: record for record in self.d2_score_log.records}
        self.assertNotIn("rubric:G.1.semantic_label_missing", d2_records["g001_e019"].rules_triggered)
        self.assertNotIn("rubric:G.1.semantic.supported_good", d2_records["g001_e035"].rules_triggered)

    def test_score_game_cli_accepts_decision_log(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.score_game",
                str(ROOT / "docs/gold-game/g001-game-log.json"),
                "--decision-log",
                str(ROOT / "docs/gold-game/g001-decision-log.json"),
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("decision_log=enabled", result.stdout)
        self.assertIn("decision_quality_total=", result.stdout)

    def test_score_game_cli_accepts_semantic_labels(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.score_game",
                str(ROOT / "docs/gold-game/g001-game-log.json"),
                "--decision-log",
                str(ROOT / "docs/gold-game/g001-decision-log.json"),
                "--semantic-labels",
                str(ROOT / "docs/gold-game/s5-semantic-label-output.example.json"),
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("decision_log=enabled", result.stdout)
        self.assertIn("semantic_labels=enabled", result.stdout)
        self.assertIn("decision_quality_total=1", result.stdout)

    def test_score_game_cli_rejects_semantic_labels_without_decision_log(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "werewolf_eval.score_game",
                str(ROOT / "docs/gold-game/g001-game-log.json"),
                "--semantic-labels",
                str(ROOT / "docs/gold-game/s5-semantic-label-output.example.json"),
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--semantic-labels requires --decision-log", result.stderr)

    def test_s5_semantic_labels_assign_decision_quality_scores(self) -> None:
        records = {record.event_id: record for record in self.s5_score_log.records}

        self.assertEqual(records["g001_e007"].decision_id, "g001_d001")
        self.assertEqual(records["g001_e007"].decision_quality_score, 1)
        self.assertIn("rubric:G.1.semantic.supported_neutral", records["g001_e007"].rules_triggered)

        self.assertEqual(records["g001_e008"].decision_id, "g001_d002")
        self.assertEqual(records["g001_e008"].decision_quality_score, -1)
        self.assertIn("rubric:G.1.semantic.unsupported", records["g001_e008"].rules_triggered)

        self.assertEqual(records["g001_e009"].decision_id, "g001_d003")
        self.assertEqual(records["g001_e009"].decision_quality_score, -1)
        self.assertIn("rubric:G.1.semantic.unsupported", records["g001_e009"].rules_triggered)

        self.assertEqual(records["g001_e020"].decision_id, "g001_d008")
        self.assertEqual(records["g001_e020"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.semantic.random_or_default", records["g001_e020"].rules_triggered)

        self.assertEqual(records["g001_e035"].decision_id, "g001_d010")
        self.assertEqual(records["g001_e035"].decision_quality_score, 2)
        self.assertIn("rubric:G.1.semantic.supported_good", records["g001_e035"].rules_triggered)

    def test_s5_semantic_labels_without_decision_log_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "semantic_label_log requires decision_log"):
            score_game(self.game, semantic_label_log=self.semantic_label_log)

    def test_s5_missing_label_keeps_score_zero_and_records_rule(self) -> None:
        records = {record.event_id: record for record in self.s5_score_log.records}

        self.assertEqual(records["g001_e019"].decision_id, "g001_d007")
        self.assertEqual(records["g001_e019"].decision_quality_score, 0)
        self.assertIn("rubric:G.1.semantic_label_missing", records["g001_e019"].rules_triggered)

    def test_s5_metrics_summary_reflects_semantic_scores(self) -> None:
        payload = metrics_summary_to_dict(self.s5_metrics)
        decision_scores = payload["score_summary"]["player_decision_quality_scores"]
        self.assertEqual(decision_scores["p3"], -1)
        self.assertEqual(decision_scores["p4"], -1)
        self.assertEqual(decision_scores["p6"], 2)
        self.assertEqual(sum(decision_scores.values()), 0)
        self.assertEqual(payload["score_summary"]["team_outcome_scores"]["wolf_team"], 2)

    def test_s5_score_outputs_match_expected_files(self) -> None:
        score_payload = score_log_to_dict(self.s5_score_log)
        metrics_payload = metrics_summary_to_dict(self.s5_metrics)
        self.assertEqual(score_payload["score_log_id"], "s5_g001_expected_score_log")
        self.assertEqual(score_payload["phase"], "Phase 2B-S5")
        self.assertEqual(metrics_payload["metrics_id"], "s5_g001_expected_metrics")
        self.assertEqual(metrics_payload["source_score_log"], "docs/gold-game/s5-score-log.json")
        self.assertEqual(score_payload, load_json("docs/gold-game/s5-score-log.json"))
        self.assertEqual(metrics_payload, load_json("docs/gold-game/s5-metrics-summary.json"))


    def test_score_game_cli_records_bundle_validation(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            score_path = Path(tmpdir) / "score.json"
            metrics_path = Path(tmpdir) / "metrics.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "werewolf_eval.score_game",
                    str(ROOT / "docs/generated-games/g1c-wolf-consensus-game-log.json"),
                    "--decision-log",
                    str(ROOT / "docs/generated-games/g1c-wolf-consensus-decision-log.json"),
                    "--consensus-log",
                    str(ROOT / "docs/generated-games/g1c-wolf-consensus-consensus-log.json"),
                    "--failure-audit",
                    str(ROOT / "docs/generated-games/g1c-wolf-consensus-failure-audit.json"),
                    "--score-log-out",
                    str(score_path),
                    "--metrics-out",
                    str(metrics_path),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn("bundle_validation=enabled", result.stdout)
            self.assertIn("team_consensus_links=2", result.stdout)

            score_payload = json.loads(score_path.read_text(encoding="utf-8"))
            self.assertEqual(score_payload["bundle_validation"]["enabled"], True)
            self.assertEqual(score_payload["bundle_validation"]["decision_log"], True)
            self.assertEqual(score_payload["bundle_validation"]["consensus_log"], True)
            self.assertEqual(score_payload["bundle_validation"]["failure_audit"], True)
            self.assertEqual(score_payload["bundle_validation"]["team_consensus_links"], 2)

            metrics_payload = json.loads(metrics_path.read_text(encoding="utf-8"))
            self.assertEqual(metrics_payload["bundle_validation"]["enabled"], True)

    def test_non_g001_score_log_uses_dynamic_provenance(self) -> None:
        game = load_game_log(
            ROOT / "docs/generated-games/g1-scripted-game-log.json"
        )
        decision_log = load_decision_log(
            ROOT / "docs/generated-games/g1-scripted-decision-log.json", game
        )
        score_log = score_game(game, decision_log=decision_log)
        payload = score_log_to_dict(score_log)

        self.assertEqual(payload["game_id"], "g1_scripted_001")
        self.assertNotIn("s2_g001", json.dumps(payload, ensure_ascii=False))
        self.assertEqual(
            payload["source_label"], "[scripted deterministic output][decision-log]"
        )


class MalformedInputRobustnessTests(unittest.TestCase):
    """Scoring must not crash on logs that pass game-log validation but have
    degenerate team composition (0 wolves / 0 villagers) or non-player vote
    targets (``none`` / ``*_team``). game_log validation permits both."""

    @staticmethod
    def _player(pid: str, role: str, team: str) -> Player:
        return Player(player_id=pid, role=role, team=team)

    @staticmethod
    def _vote(actor: str, target: str) -> Event:
        return Event(
            event_id=f"e_{actor}_{target}",
            sequence=1,
            round=1,
            phase="day",
            type="player_vote",
            actor=actor,
            target=target,
            visibility="public",
            data={},
        )

    def test_summarize_metrics_handles_board_with_zero_werewolves(self) -> None:
        # 6 villager-team players (with the usual special villager roles so the
        # seer/witch process-metrics are well-defined), 0 werewolves -> the team
        # survival-rate division would otherwise raise ZeroDivisionError.
        roles = ["seer", "witch", "hunter", "villager", "villager", "villager"]
        players = [self._player(f"p{i+1}", role, "villager") for i, role in enumerate(roles)]
        game = GameLog(
            game_id="zero_wolf",
            source_label="emergent_offline",
            players=players,
            events=[],
            result=GameResult(
                winner="villager",
                end_round=1,
                survivors=[p.player_id for p in players],
                end_condition="all_werewolves_eliminated",
            ),
        )
        metrics = summarize_metrics(game, score_game(game))  # must not raise ZeroDivisionError
        self.assertEqual(metrics.result_metrics.werewolf_survival_rate, 0.0)
        self.assertEqual(metrics.result_metrics.villager_survival_rate, 1.0)

    def test_result_metrics_handles_board_with_zero_villagers(self) -> None:
        # A 0-villager-team board has no seer/witch by definition, so exercise the
        # symmetric guard directly on _result_metrics (the unit with the division).
        players = [self._player(f"p{i}", "werewolf", "werewolf") for i in range(1, 7)]
        game = GameLog(
            game_id="zero_villager",
            source_label="emergent_offline",
            players=players,
            events=[],
            result=GameResult(
                winner="werewolf",
                end_round=1,
                survivors=[p.player_id for p in players],
                end_condition="all_villagers_eliminated",
            ),
        )
        metrics = _result_metrics(game)  # must not raise ZeroDivisionError
        self.assertEqual(metrics.villager_survival_rate, 0.0)
        self.assertEqual(metrics.werewolf_survival_rate, 1.0)

    def _board(self) -> list[Player]:
        return [
            self._player("p1", "werewolf", "werewolf"),
            self._player("p2", "werewolf", "werewolf"),
            self._player("p3", "seer", "villager"),
            self._player("p4", "witch", "villager"),
            self._player("p5", "villager", "villager"),
            self._player("p6", "villager", "villager"),
        ]

    def test_score_game_does_not_crash_on_non_player_vote_target(self) -> None:
        # target="none" (abstain) passes game-log validation but is not a player id.
        players = self._board()
        game = GameLog(
            game_id="abstain",
            source_label="emergent_offline",
            players=players,
            events=[self._vote("p5", "none")],
            result=GameResult(
                winner="werewolf",
                end_round=1,
                survivors=[p.player_id for p in players],
                end_condition="all_villagers_eliminated",
            ),
        )
        score_log = score_game(game)  # must not raise KeyError
        record = next(r for r in score_log.records if r.event_id == "e_p5_none")
        self.assertEqual(record.outcome_score, 0)
        self.assertIn("rubric-gap:vote_target_not_a_player", record.rules_triggered)

    def test_score_game_does_not_crash_on_non_player_vote_actor(self) -> None:
        # game_log validation permits actor in {"system","wolf_team"} on any event
        # type, including player_vote. Such an actor is not a player id.
        players = self._board()
        game = GameLog(
            game_id="bad_actor",
            source_label="emergent_offline",
            players=players,
            events=[self._vote("wolf_team", "p3")],
            result=GameResult(
                winner="werewolf",
                end_round=1,
                survivors=[p.player_id for p in players],
                end_condition="all_villagers_eliminated",
            ),
        )
        score_log = score_game(game)  # must not raise KeyError on the actor lookup
        record = next(r for r in score_log.records if r.event_id == "e_wolf_team_p3")
        self.assertEqual(record.outcome_score, 0)
        self.assertIn("rubric-gap:vote_target_not_a_player", record.rules_triggered)

    def test_vote_accuracy_excludes_non_player_vote_actor(self) -> None:
        players = self._board()
        game = GameLog(
            game_id="bad_actor_metrics",
            source_label="emergent_offline",
            players=players,
            events=[self._vote("wolf_team", "p3")],
            result=GameResult(
                winner="werewolf",
                end_round=1,
                survivors=[p.player_id for p in players],
                end_condition="all_villagers_eliminated",
            ),
        )
        metrics = summarize_metrics(game, score_game(game))  # must not raise KeyError
        self.assertNotIn("wolf_team", metrics.process_metrics.vote_accuracy_by_player)

    def test_vote_accuracy_excludes_non_player_vote_target(self) -> None:
        players = self._board()
        game = GameLog(
            game_id="abstain_metrics",
            source_label="emergent_offline",
            players=players,
            events=[self._vote("p5", "none")],
            result=GameResult(
                winner="werewolf",
                end_round=1,
                survivors=[p.player_id for p in players],
                end_condition="all_villagers_eliminated",
            ),
        )
        metrics = summarize_metrics(game, score_game(game))  # must not raise KeyError
        p5 = metrics.process_metrics.vote_accuracy_by_player["p5"]
        self.assertEqual(p5["total_votes"], 0)
        self.assertEqual(p5["vote_accuracy"], 0.0)


class ScoreLogBucketTests(unittest.TestCase):
    def setUp(self) -> None:
        game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        decision_log = load_decision_log(ROOT / "docs/gold-game/g001-decision-log.json", game)
        self.score_log = score_game(game, decision_log=decision_log)

    def test_score_log_dict_default_stamps_unknown_bucket(self) -> None:
        d = score_log_to_dict(self.score_log)
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
        bucket = {
            "rules_version": "rules_v1_1",
            "prompt_version": "prompt_v1",
            "scoring_version": "scoring_v1",
            "comparison_key": "rules_v1_1__prompt_v1__scoring_v1",
        }
        d = score_log_to_dict(self.score_log, evaluation_bucket=bucket)
        self.assertEqual(d["evaluation_bucket"], bucket)


class ScoreIdPrefixRaceTests(unittest.TestCase):
    """C12-05: Module-level _current_score_id_prefix is a threading race.
    score_game() must be re-entrant — two concurrent calls with different
    game_ids must NOT cross-contaminate each other's score_id prefixes."""

    @staticmethod
    def _make_game(game_id: str, role: str = "villager") -> GameLog:
        return GameLog(
            game_id=game_id,
            source_label="emergent_offline",
            players=[
                Player(player_id="p1", role="werewolf", team="werewolf"),
                Player(player_id="p2", role="werewolf", team="werewolf"),
                Player(player_id="p3", role="seer", team="villager"),
                Player(player_id="p4", role="witch", team="villager"),
                Player(player_id="p5", role=role, team="villager"),
                Player(player_id="p6", role="villager", team="villager"),
            ],
            events=[
                Event(
                    event_id="e001",
                    sequence=1,
                    round=1,
                    phase="night",
                    type="werewolf_kill",
                    actor="wolf_team",
                    target="p5",
                    visibility="werewolf_team",
                    data={},
                ),
            ],
            result=GameResult(
                winner="werewolf",
                end_round=1,
                survivors=["p1", "p2", "p3", "p4", "p6"],
                end_condition="all_villagers_eliminated",
            ),
        )

    def test_concurrent_score_game_prefixes_do_not_leak(self) -> None:
        import threading

        game_a = self._make_game("race_test_a")
        game_b = self._make_game("race_test_b")
        results: dict[str, object] = {}
        errors: list[Exception] = []

        def score_and_capture(game: GameLog) -> None:
            try:
                log = score_game(game)
                results[game.game_id] = log
            except Exception as exc:
                errors.append(exc)

        # Fire many concurrent pairs to stress the race window.
        for _ in range(30):
            results.clear()
            errors.clear()
            t1 = threading.Thread(target=score_and_capture, args=(game_a,))
            t2 = threading.Thread(target=score_and_capture, args=(game_b,))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            self.assertEqual(errors, [])
            for game_id, log in results.items():
                expected_prefix = f"score_{game_id}_"
                for record in log.records:
                    self.assertTrue(
                        record.score_id.startswith(expected_prefix),
                        f"score_id={record.score_id!r} does not start with "
                        f"expected prefix {expected_prefix!r} (game_id={game_id})",
                    )


if __name__ == "__main__":
    unittest.main()

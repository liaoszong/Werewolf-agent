from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GAME_LOG: dict[str, Any] = {
    "game_id": "g1g_fixture",
    "source_label": "[DeepSeek API output]",
    "players": [
        {"player_id": "p1", "role": "werewolf", "team": "werewolf"},
        {"player_id": "p2", "role": "werewolf", "team": "werewolf"},
        {"player_id": "p3", "role": "seer", "team": "villager"},
        {"player_id": "p4", "role": "witch", "team": "villager"},
        {"player_id": "p5", "role": "villager", "team": "villager"},
        {"player_id": "p6", "role": "villager", "team": "villager"},
    ],
    "events": [
        {
            "event_id": "g1g_e001",
            "sequence": 1,
            "round": 0,
            "phase": "setup",
            "type": "role_assignment",
            "actor": "system",
            "target": "none",
            "visibility": "public",
            "data": {"summary": "roles assigned", "visible_info_refs": []},
        },
        {
            "event_id": "g1g_e002",
            "sequence": 2,
            "round": 1,
            "phase": "night",
            "type": "werewolf_kill",
            "actor": "wolf_team",
            "target": "p5",
            "visibility": "werewolf_team",
            "data": {"summary": "wolves target p5", "visible_info_refs": []},
        },
    ],
    "result": {
        "winner": "villager",
        "end_round": 1,
        "survivors": ["p1", "p2", "p3", "p4", "p6"],
        "end_condition": "fixture",
    },
}

DECISION_LOG: dict[str, Any] = {
    "decision_log_id": "g1g_dl001",
    "game_id": "g1g_fixture",
    "source_label": "[DeepSeek API output]",
    "decisions": [
        {
            "decision_id": "g1g_d001",
            "actor": "wolf_team",
            "decision_scope": "team",
            "consensus_id": "g1g_c001",
            "phase": "night",
            "action": "werewolf_kill",
            "target": "p5",
            "visible_info_refs": [],
            "reason_summary": "consensus reached to eliminate p5",
            "decision_type": "team_coordinated",
            "confidence": 0.85,
            "strategy_tag": "eliminate_non_wolf",
        }
    ],
}

CONSENSUS_LOG: dict[str, Any] = {
    "consensus_log_id": "g1g_cl001",
    "game_id": "g1g_fixture",
    "source_label": "[DeepSeek API output]",
    "consensuses": [
        {
            "consensus_id": "g1g_c001",
            "game_id": "g1g_fixture",
            "round": 1,
            "phase": "night",
            "team": "werewolf",
            "participants": ["p1", "p2"],
            "coordinator": "p1",
            "max_rounds": 2,
            "actual_rounds": 1,
            "status": "consensus",
            "proposals": [
                {
                    "proposal_id": 1,
                    "proposer": "p1",
                    "proposed_target": "p5",
                    "visible_info_refs": [],
                    "reason_summary": "p5 is not wolf",
                    "confidence": 0.9,
                    "action_round": 1,
                }
            ],
            "responses": [
                {
                    "response_id": 1,
                    "to_proposal_id": 1,
                    "responder": "p2",
                    "response_type": "support_with_reason",
                    "reason_summary": "agree on p5",
                    "visible_info_refs": [],
                    "action_round": 1,
                }
            ],
            "final_decision": {
                "target": "p5",
                "decision_type": "consensus",
                "primary_proposer": "p1",
                "supporters": ["p1", "p2"],
                "dissenters": [],
                "resolution_round": 1,
            },
        }
    ],
}

PROVIDER_TRACE: dict[str, Any] = {
    "game_id": "g1g_fixture",
    "provider_name": "DeepSeek",
    "source_label": "[DeepSeek API output]",
    "requests": [
        {
            "request_id": "g1g_r001",
            "game_id": "g1g_fixture",
            "actor": "wolf_team",
            "phase": "night",
            "round": 1,
            "observation": {"visible_players": ["p1", "p2", "p3", "p4", "p5", "p6"]},
            "allowed_actions": ["werewolf_kill"],
            "allowed_targets": ["p3", "p4", "p5", "p6"],
            "response_format_version": "g1d-action-v1",
        }
    ],
    "responses": [
        {
            "request_id": "g1g_r001",
            "provider_name": "DeepSeek",
            "source_label": "[DeepSeek API output]",
            "raw_content": '{"action": "werewolf_kill", "target": "p5"}',
            "latency_ms": 2340,
            "token_usage": {"prompt_tokens": 850, "completion_tokens": 32, "total_tokens": 882},
        }
    ],
    "failures": [],
}

FAILURE_AUDIT: dict[str, Any] = {
    "game_id": "g1g_fixture",
    "source_label": "[DeepSeek API output]",
    "failures": [],
}

UNSAFE_PROVIDER_TRACE: dict[str, Any] = {
    "game_id": "g1g_fixture",
    "provider_name": "DeepSeek",
    "source_label": "[DeepSeek API output]",
    "requests": [
        {
            "request_id": "g1g_r002",
            "game_id": "g1g_fixture",
            "actor": "wolf_team",
            "phase": "night",
            "round": 1,
            "observation": {"visible_players": ["p1", "p2", "p3", "p4", "p5", "p6"]},
            "allowed_actions": ["werewolf_kill"],
            "allowed_targets": ["p3", "p4", "p5", "p6"],
            "response_format_version": "g1d-action-v1",
        }
    ],
    "responses": [
        {
            "request_id": "g1g_r002",
            "provider_name": "DeepSeek",
            "source_label": "[DeepSeek API output]",
            "raw_content": '<unsafe>{"action": "werewolf_kill", "target": "p3"}</unsafe>',
            "latency_ms": 1200,
            "token_usage": {"prompt_tokens": 800, "completion_tokens": 28, "total_tokens": 828},
        }
    ],
    "failures": [],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class ProviderReplayHtmlTests(unittest.TestCase):
    """Provider replay HTML renderer tests."""

    def setUp(self) -> None:
        from werewolf_eval.render_provider_replay import build_replay_context

        self.context = build_replay_context(
            game_log=GAME_LOG,
            decision_log=DECISION_LOG,
            consensus_log=CONSENSUS_LOG,
            provider_trace=PROVIDER_TRACE,
            failure_audit=FAILURE_AUDIT,
        )

    def test_build_replay_context_counts_sections(self) -> None:
        """build_replay_context returns correct section counts."""
        self.assertEqual(self.context["game"]["game_id"], "g1g_fixture")
        self.assertEqual(self.context["game"]["winner"], "villager")
        self.assertEqual(self.context["game"]["end_round"], 1)
        self.assertEqual(self.context["game"]["player_count"], 6)
        self.assertEqual(self.context["game"]["event_count"], 2)
        self.assertEqual(len(self.context["players"]), 6)
        self.assertEqual(len(self.context["events"]), 2)
        self.assertEqual(len(self.context["decisions"]), 1)
        self.assertEqual(len(self.context["consensuses"]), 1)
        self.assertTrue(self.context["provider_trace"]["has_trace"])
        self.assertEqual(self.context["provider_trace"]["request_count"], 1)
        self.assertEqual(self.context["provider_trace"]["response_count"], 1)
        self.assertEqual(self.context["provider_trace"]["failure_count"], 0)
        self.assertEqual(self.context["provider_trace"]["total_tokens"], 882)

    def test_render_html_contains_required_sections(self) -> None:
        """render_provider_replay_html includes all required sections."""
        from werewolf_eval.render_provider_replay import render_provider_replay_html

        html = render_provider_replay_html(self.context)

        self.assertIn("Provider 回放", html)
        self.assertIn("[DeepSeek API output]", html)
        self.assertIn("共识回放", html)
        self.assertIn("Provider 调用记录", html)
        self.assertIn("失败审计", html)
        self.assertIn("渲染过程中未发起任何实时 API 调用", html)

    def test_render_html_escapes_provider_content(self) -> None:
        """render_provider_replay_html escapes unsafe content."""
        from werewolf_eval.render_provider_replay import build_replay_context, render_provider_replay_html

        unsafe_context = build_replay_context(
            game_log=GAME_LOG,
            decision_log=DECISION_LOG,
            consensus_log=CONSENSUS_LOG,
            provider_trace=UNSAFE_PROVIDER_TRACE,
            failure_audit=FAILURE_AUDIT,
        )
        html = render_provider_replay_html(unsafe_context)

        self.assertIn("&lt;unsafe&gt;", html)
        self.assertNotIn("<script", html.lower())

    def test_write_provider_replay_html_escapes_provider_content(self) -> None:
        """write_provider_replay_html writes escaped HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            game_path = tmp / "game.json"
            game_path.write_text(json.dumps(GAME_LOG), encoding="utf-8")
            dl_path = tmp / "decision.json"
            dl_path.write_text(json.dumps(DECISION_LOG), encoding="utf-8")
            cl_path = tmp / "consensus.json"
            cl_path.write_text(json.dumps(CONSENSUS_LOG), encoding="utf-8")
            pt_path = tmp / "provider_trace.json"
            pt_path.write_text(json.dumps(UNSAFE_PROVIDER_TRACE), encoding="utf-8")
            fa_path = tmp / "failure_audit.json"
            fa_path.write_text(json.dumps(FAILURE_AUDIT), encoding="utf-8")
            html_path = tmp / "output.html"

            from werewolf_eval.render_provider_replay import write_provider_replay_html

            write_provider_replay_html(
                game_log_path=game_path,
                output_path=html_path,
                decision_log_path=dl_path,
                consensus_log_path=cl_path,
                provider_trace_path=pt_path,
                failure_audit_path=fa_path,
            )

            html = html_path.read_text(encoding="utf-8")
            self.assertIn("&lt;unsafe&gt;", html)
            self.assertNotIn("<script", html.lower())

    def test_write_provider_replay_html_without_optional_logs(self) -> None:
        """write_provider_replay_html works with only game log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            game_path = tmp / "game.json"
            game_path.write_text(json.dumps(GAME_LOG), encoding="utf-8")
            html_path = tmp / "output.html"

            from werewolf_eval.render_provider_replay import write_provider_replay_html

            write_provider_replay_html(
                game_log_path=game_path,
                output_path=html_path,
            )

            html = html_path.read_text(encoding="utf-8")
            self.assertIn("Provider 回放", html)
            self.assertIn("g1g_fixture", html)
            self.assertIn("渲染过程中未发起任何实时 API 调用", html)

    # ------------------------------------------------------------------
    # CLI tests
    # ------------------------------------------------------------------

    def test_cli_requires_game_log_and_html_out(self) -> None:
        """CLI requires --game-log and --html-out."""
        from werewolf_eval.render_provider_replay import main

        with self.assertRaises(SystemExit):
            main([])

    def test_cli_writes_expected_output_path(self) -> None:
        """CLI writes output to the specified path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            game_path = tmp / "game.json"
            game_path.write_text(json.dumps(GAME_LOG), encoding="utf-8")
            html_path = tmp / "output.html"

            from werewolf_eval.render_provider_replay import main

            ret = main([
                "--game-log", str(game_path),
                "--html-out", str(html_path),
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(html_path.exists())
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("Provider 回放", html)

    def test_cli_accepts_optional_logs(self) -> None:
        """CLI accepts all optional log paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            game_path = tmp / "game.json"
            game_path.write_text(json.dumps(GAME_LOG), encoding="utf-8")
            dl_path = tmp / "decision.json"
            dl_path.write_text(json.dumps(DECISION_LOG), encoding="utf-8")
            cl_path = tmp / "consensus.json"
            cl_path.write_text(json.dumps(CONSENSUS_LOG), encoding="utf-8")
            pt_path = tmp / "provider_trace.json"
            pt_path.write_text(json.dumps(PROVIDER_TRACE), encoding="utf-8")
            fa_path = tmp / "failure_audit.json"
            fa_path.write_text(json.dumps(FAILURE_AUDIT), encoding="utf-8")
            html_path = tmp / "output.html"

            from werewolf_eval.render_provider_replay import main

            ret = main([
                "--game-log", str(game_path),
                "--decision-log", str(dl_path),
                "--consensus-log", str(cl_path),
                "--provider-trace", str(pt_path),
                "--failure-audit", str(fa_path),
                "--html-out", str(html_path),
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(html_path.exists())

"""B5 closeout focused tests (B34-06 + B34-03).

B34-06: deepseek-only env fallback retired.
B34-03: token naming corrected, scribe tokens separated.

These tests verify the EXTERNAL BEHAVIOR changes:
- Env-only launch → explicit 403 (not silent success/fallback)
- Per-seat token/cost aggregation is honest (no scribe inflation)
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from werewolf_eval.credential_store import CredentialStore
from werewolf_eval.observer.state import ObserverServerState
from werewolf_eval.observer_server import (
    _build_capabilities_payload,
    _check_live_capability,
    _resolve_live_launcher_for_launch,
)


class EnvFallbackRetiredTests(unittest.TestCase):
    """B34-06: env-key fallback retired. External behavior: without a client
    credential, live launch → 403 missing_api_key (not silent success)."""

    def test_env_var_set_but_no_client_cred_returns_403(self) -> None:
        """Even if DEEPSEEK_API_KEY is set in the server's environment, without a
        client credential the capability gate returns 403 missing_api_key."""
        with TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            # No credential_store key set — simulates env-only deployment.
            state = ObserverServerState(
                runs_dir=runs,
                launcher=lambda r, d: 0,
                live_enabled=True,
                credential_store=CredentialStore(),  # empty
            )
            result = _check_live_capability(state, "live")
            self.assertIsNotNone(result)
            self.assertEqual(result[0], 403)
            self.assertEqual(result[1], "missing_api_key")

    def test_client_cred_present_proceeds(self) -> None:
        """With a client credential, the capability gate proceeds (returns None)."""
        with TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            cs = CredentialStore()
            cs.set("deepseek", "sk-test-fake-key")
            state = ObserverServerState(
                runs_dir=runs,
                launcher=lambda r, d: 0,
                live_enabled=True,
                credential_store=cs,
            )
            result = _check_live_capability(state, "live")
            self.assertIsNone(result)

    def test_capabilities_payload_deepseek_unavailable_without_cred(self) -> None:
        """The capabilities payload reports deepseek unavailable when no client
        credential is present (env var ignored)."""
        with TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            state = ObserverServerState(
                runs_dir=runs,
                launcher=lambda r, d: 0,
                live_enabled=True,
                credential_store=CredentialStore(),  # empty
            )
            payload = _build_capabilities_payload(state)
            ds = payload["live_api"]["providers"]["deepseek"]
            self.assertFalse(ds["available"])
            self.assertEqual(ds["reason_code"], "missing_api_key")

    def test_launcher_resolution_requires_client_cred(self) -> None:
        """_resolve_live_launcher_for_launch returns 403 when no client credential
        is present, even for uniform deepseek profiles."""
        with TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            state = ObserverServerState(
                runs_dir=runs,
                launcher=lambda r, d: 0,
                live_enabled=True,
                credential_store=CredentialStore(),  # empty
                multi_provider_launcher_factory=lambda seats, creds: (lambda r, d: 0),
            )
            seats = [
                {"player_id": f"p{i}", "provider": "deepseek", "model": "deepseek-chat"}
                for i in range(1, 7)
            ]
            launcher, err = _resolve_live_launcher_for_launch(state, seats)
            self.assertIsNone(launcher)
            self.assertIsNotNone(err)
            self.assertEqual(err[0], 403)
            self.assertEqual(err[1], "missing_provider_credential")


class PerSeatTokenCostTests(unittest.TestCase):
    """B34-03: token naming corrected, scribe tokens separated."""

    def test_provider_turns_summary_honest_naming(self) -> None:
        """_provider_turns_summary uses honest token naming (not total_completion_tokens)."""
        from werewolf_eval.run_emergent_deepseek_game import _provider_turns_summary

        turns = [
            {
                "actor": "p1",
                "kind": "live_success",
                "token_usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            },
            {
                "actor": "p2",
                "kind": "live_success",
                "token_usage": {
                    "prompt_tokens": 200,
                    "completion_tokens": 100,
                    "total_tokens": 300,
                },
            },
        ]
        summary = _provider_turns_summary(turns)
        # Honest naming: player_* fields, not total_completion_tokens.
        self.assertEqual(summary["player_prompt_tokens"], 300)
        self.assertEqual(summary["player_completion_tokens"], 150)
        self.assertEqual(summary["player_total_tokens"], 450)
        # Scribe fields are zero when no scribe turns.
        self.assertEqual(summary["scaffold_prompt_tokens"], 0)
        self.assertEqual(summary["scaffold_completion_tokens"], 0)
        self.assertEqual(summary["scaffold_total_tokens"], 0)
        # total_tokens is the sum of player + scaffold.
        self.assertEqual(summary["total_tokens"], 450)

    def test_provider_turns_summary_excludes_scribe_from_player_sums(self) -> None:
        """Scribe (scaffold) tokens are tracked separately, not in player sums."""
        from werewolf_eval.run_emergent_deepseek_game import _provider_turns_summary

        turns = [
            {
                "actor": "p1",
                "kind": "live_success",
                "token_usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            },
            {
                "actor": "scribe",
                "kind": "live_success",
                "response_kind": "scaffold",
                "token_usage": {
                    "prompt_tokens": 500,
                    "completion_tokens": 250,
                    "total_tokens": 750,
                },
            },
        ]
        summary = _provider_turns_summary(turns)
        # Player sums exclude scribe.
        self.assertEqual(summary["player_prompt_tokens"], 100)
        self.assertEqual(summary["player_completion_tokens"], 50)
        self.assertEqual(summary["player_total_tokens"], 150)
        # Scaffold sums are separate.
        self.assertEqual(summary["scaffold_prompt_tokens"], 500)
        self.assertEqual(summary["scaffold_completion_tokens"], 250)
        self.assertEqual(summary["scaffold_total_tokens"], 750)
        # total_tokens is the sum of both.
        self.assertEqual(summary["total_tokens"], 900)

    def test_settlement_bundle_has_usage_summary(self) -> None:
        """Settlement bundle includes usage_summary with seats/scaffold/total."""
        from werewolf_eval.settlement_bundle import build_settlement_bundle
        from werewolf_eval.game_log import load_game_log

        gold = Path(__file__).resolve().parent.parent / "docs" / "gold-game"
        game = load_game_log(gold / "g001-game-log.json")
        decision_log_path = gold / "g001-decision-log.json"
        from werewolf_eval.decision_log import load_decision_log
        decision_log = load_decision_log(decision_log_path, game)

        bundle = build_settlement_bundle(game, decision_log, run_id="r1")
        self.assertIn("usage_summary", bundle)
        usage = bundle["usage_summary"]
        self.assertIn("seats", usage)
        self.assertIn("scaffold", usage)
        self.assertIn("total", usage)
        # Each has prompt_tokens, completion_tokens, total_tokens.
        for key in ("seats", "scaffold", "total"):
            self.assertIn("prompt_tokens", usage[key])
            self.assertIn("completion_tokens", usage[key])
            self.assertIn("total_tokens", usage[key])

    def test_settlement_bundle_per_seat_cost_estimate_null_without_pricing(self) -> None:
        """Without pricing metadata, per-seat cost_estimate is null."""
        from werewolf_eval.settlement_bundle import build_settlement_bundle
        from werewolf_eval.game_log import load_game_log

        gold = Path(__file__).resolve().parent.parent / "docs" / "gold-game"
        game = load_game_log(gold / "g001-game-log.json")
        decision_log_path = gold / "g001-decision-log.json"
        from werewolf_eval.decision_log import load_decision_log
        decision_log = load_decision_log(decision_log_path, game)

        bundle = build_settlement_bundle(game, decision_log, run_id="r1")
        for player in bundle["players"]:
            # No pricing configured → cost_estimate is null.
            self.assertIsNone(player["cost_estimate"])


if __name__ == "__main__":
    unittest.main()

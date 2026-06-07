"""Integration tests for the observer -> EmergentGameEngine bridge slice.

All offline (localhost HTTP is env-blocked): the server route logic is driven
directly via `build_settlement_response` / `build_projection_envelope` /
`filter_events_for_perspective` on a run_dir produced by the bridge launchers,
exactly as `test_settlement_response.py` does.

Covers:
* Adapter B (live emergent launcher) — budget exhaustion translates to exit 3,
  a completed run returns 0 and still writes the smoke's provider-turns input,
  a resilient fallback run completes (rc 0) but is honestly NOT live_success,
  and the budget-audit helper matches the structured `kind` (not a substring).
* Protocol — emergent observer-exposed artifacts ⊆ ALLOWED_ARTIFACTS;
  provider-turns.json is server-local (not exposed); templates unchanged.
* Settlement — a fake emergent run settles and caches.
* Visibility — `/events` thin filter + `/projection` role downgrade across
  perspectives, with the §5.3 god-only-snapshot seam locked as current behavior.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.deepseek_launcher import (
    _audit_is_budget_exhausted,
    build_emergent_deepseek_launcher,
)
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.observer_protocol import (
    ALLOWED_ARTIFACTS,
    ALLOWED_TEMPLATES,
    filter_events_for_perspective,
)
from werewolf_eval.observer_visibility import (
    build_projection_envelope,
    build_seat_role_index,
    event_visible_in_projection,
)
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.run_emergent_fake_runtime import default_emergent_fake_launcher
from werewolf_eval.runtime_events import read_events_jsonl
from werewolf_eval.settlement_bundle import build_settlement_response

# game event types the engine emits as PRIVATE (role/team-scoped) — never visible
# to a public or non-matching role perspective.
_PRIVATE_TYPES = {"werewolf_kill", "seer_check", "witch_save", "witch_poison", "witch_pass"}


def _ok_factory():
    agents = build_emergent_fake_agents(build_villager_win_script())
    return lambda pid: agents[pid]


def _game_types(events: list[dict]) -> set[str]:
    """Game-event types carried in the runtime stream (payload.type)."""
    out: set[str] = set()
    for e in events:
        payload = e.get("payload")
        if isinstance(payload, dict) and e.get("kind") == "game_event_emitted":
            t = payload.get("type")
            if isinstance(t, str):
                out.add(t)
    return out


# ---------------------------------------------------------------------------
# Adapter B — live emergent launcher
# ---------------------------------------------------------------------------


class AdapterBLiveLauncherTests(unittest.TestCase):
    def _build(self, *, max_requests: int, provider_factory) -> object:
        return build_emergent_deepseek_launcher(
            api_key="sk-test-fake-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            max_tokens=256,
            max_requests=max_requests,
            provider_factory=provider_factory,
        )

    def test_completed_run_returns_0_with_provider_turns(self) -> None:
        launcher = self._build(max_requests=64, provider_factory=_ok_factory())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertEqual(launcher("br_ok", out), 0)
            self.assertTrue((out / "game-log.json").exists())
            # provider-turns.json is the smoke's server-local input and must survive
            self.assertTrue((out / "provider-turns.json").exists())
            self.assertTrue((out / "events.jsonl").exists())
            self.assertTrue((out / "prompt-manifest.json").exists())

    def test_budget_exhaustion_translates_to_exit_3(self) -> None:
        launcher = self._build(max_requests=0, provider_factory=_ok_factory())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertEqual(launcher("br_budget", out), 3)
            self.assertFalse((out / "game-log.json").exists())
            # provider-turns still written in the fail-closed branch (live evidence)
            self.assertTrue((out / "provider-turns.json").exists())
            audit = json.loads((out / "failure-audit.json").read_text(encoding="utf-8"))
            self.assertTrue(any(f.get("kind") == "budget_exhausted" for f in audit["failures"]))

    def test_raising_provider_completes_via_fallback_but_not_live_success(self) -> None:
        # The emergent engine is resilient: a provider error becomes an engine
        # fallback, so the game COMPLETES (rc 0) rather than failing closed. The
        # honesty gate is post-hoc: provider-turns records zero live_success, so
        # the offline smoke (not the exit code) rejects an all-fallback run.
        class _Boom:
            def __init__(self) -> None:
                self.requests: list = []
                self.responses: list = []

            def respond(self, request: object) -> object:
                raise RuntimeError("simulated provider failure")

        def boom_factory(pid: str) -> ProviderAgent:
            return ProviderAgent(pid, _Boom())

        launcher = self._build(max_requests=64, provider_factory=boom_factory)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertEqual(launcher("br_fallback", out), 0)
            summary = json.loads((out / "provider-turns.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["live_success_actions"], 0)

    def test_audit_helper_matches_kind_not_substring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            budget = d / "budget.json"
            budget.write_text(
                json.dumps({"failures": [{"kind": "budget_exhausted", "reason": "budget exhausted: 1/0 requests"}]}),
                encoding="utf-8",
            )
            self.assertTrue(_audit_is_budget_exhausted(budget))

            other = d / "other.json"
            other.write_text(
                json.dumps({"failures": [{"kind": "round_cap", "reason": "no winner within 3 day-rounds"}]}),
                encoding="utf-8",
            )
            self.assertFalse(_audit_is_budget_exhausted(other))

            # missing / corrupt -> conservative False, never raises
            self.assertFalse(_audit_is_budget_exhausted(d / "nope.json"))
            corrupt = d / "corrupt.json"
            corrupt.write_text("{ truncated", encoding="utf-8")
            self.assertFalse(_audit_is_budget_exhausted(corrupt))


# ---------------------------------------------------------------------------
# Protocol — zero-change contract
# ---------------------------------------------------------------------------


class BridgeProtocolContractTests(unittest.TestCase):
    def test_emergent_exposed_artifacts_subset_of_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            default_emergent_fake_launcher("br_proto", out)
            produced = {p.name for p in out.iterdir() if p.is_file()}
            # provider-turns.json is server-local (live only) and not part of the
            # fake run; every other top-level artifact must be in the allowlist.
            exposed = produced - {"provider-turns.json"}
            self.assertTrue(
                exposed <= set(ALLOWED_ARTIFACTS),
                f"non-allowlisted exposed artifacts: {exposed - set(ALLOWED_ARTIFACTS)}",
            )

    def test_provider_turns_is_server_local_not_exposed(self) -> None:
        self.assertNotIn("provider-turns.json", ALLOWED_ARTIFACTS)

    def test_templates_unchanged(self) -> None:
        self.assertEqual(ALLOWED_TEMPLATES, ("default_6p_fake",))


# ---------------------------------------------------------------------------
# Settlement — fake emergent run settles + caches
# ---------------------------------------------------------------------------


class BridgeSettlementTests(unittest.TestCase):
    def test_emergent_run_settles_and_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            default_emergent_fake_launcher("br_settle", out)
            r = build_settlement_response(out, run_status="completed", run_id="br_settle")
            self.assertTrue(r["available"])
            self.assertFalse(r["bundle"]["degraded"])
            self.assertTrue((out / "settlement-bundle.json").exists())  # cached


# ---------------------------------------------------------------------------
# Visibility — two channels, per perspective (§5.4)
# ---------------------------------------------------------------------------


class BridgeVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._dir = Path(self._tmp.name)
        default_emergent_fake_launcher("br_vis", self._dir)
        self._events = read_events_jsonl(self._dir / "events.jsonl")

    # ---- channel A: /events, /stream thin filter ----

    def test_events_thin_filter_role_and_public_are_public_only(self) -> None:
        for perspective in ("public", "role:p3"):
            view = filter_events_for_perspective(self._events, perspective)
            self.assertGreater(view["hidden_count"], 0, perspective)
            self.assertEqual(
                _game_types(view["events"]) & _PRIVATE_TYPES,
                set(),
                f"{perspective} leaked a private event via thin filter",
            )

    def test_events_thin_filter_team_werewolf_sees_kill_only(self) -> None:
        view = filter_events_for_perspective(self._events, "team:werewolf")
        types = _game_types(view["events"])
        self.assertIn("werewolf_kill", types)
        self.assertNotIn("seer_check", types)
        self.assertNotIn("witch_save", types)
        self.assertNotIn("witch_poison", types)

    def test_events_thin_filter_god_sees_everything(self) -> None:
        view = filter_events_for_perspective(self._events, "god")
        self.assertEqual(view["hidden_count"], 0)
        self.assertGreaterEqual(_game_types(view["events"]) & _PRIVATE_TYPES, {"werewolf_kill", "seer_check"})

    # ---- channel B: /projection trust projection (§5.3 seam) ----

    def test_projection_role_private_events_downgrade_to_hidden(self) -> None:
        # Emergent writes ONLY god snapshots, so role:pN has no trusted role
        # snapshot -> seer/witch/werewolf-team events downgrade to hidden and
        # NONE of the unlock reasons appear. This locks the known seam.
        seat_index = build_seat_role_index(self._dir)
        reasons = {
            event_visible_in_projection(e, "role:p3", seat_index)[1]
            for e in self._events
        }
        self.assertNotIn("seer_event", reasons)
        self.assertNotIn("witch_event", reasons)
        self.assertNotIn("werewolf_team_event", reasons)

        envelope = build_projection_envelope(
            run_dir=self._dir, run_id="br_vis", perspective="role:p3", events=self._events
        )
        self.assertGreater(envelope["hidden_event_count"], 0)
        self.assertEqual(_game_types(envelope["events"]) & _PRIVATE_TYPES, set())

    def test_projection_team_werewolf_unlocks_kill_without_snapshot(self) -> None:
        envelope = build_projection_envelope(
            run_dir=self._dir, run_id="br_vis", perspective="team:werewolf", events=self._events
        )
        self.assertIn("werewolf_kill", _game_types(envelope["events"]))

    def test_projection_god_sees_all(self) -> None:
        envelope = build_projection_envelope(
            run_dir=self._dir, run_id="br_vis", perspective="god", events=self._events
        )
        self.assertEqual(envelope["hidden_event_count"], 0)


if __name__ == "__main__":
    unittest.main()

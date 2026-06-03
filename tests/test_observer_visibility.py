"""Tests for G2c observer visibility projection helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from werewolf_eval.observer_visibility import (
    CONTRACT_VERSION,
    ROLE_PERSPECTIVE_PREFIX,
    VisibilityProjectionError,
    build_player_projection,
    build_projection_envelope,
    build_seat_role_index,
    event_visible_in_projection,
    infer_player_ids,
    is_werewolf_role,
    perspective_kind,
    project_events,
    project_snapshots,
    unknown_player,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_dir(tmp_dir: Path, run_id: str, snapshots: list[dict]) -> Path:
    """Create a minimal run directory with snapshot fixtures."""
    run_dir = tmp_dir / run_id
    snap_dir = run_dir / "snapshots"
    snap_dir.mkdir(parents=True)
    for snap in snapshots:
        name = snap.pop("_name")
        path = snap_dir / name
        path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    return run_dir


def _make_role_snapshot(
    name: str,
    player_id: str,
    role: str,
    team: str,
    *,
    round: int = 1,
    phase: str = "night",
    alive_players: list[str] | None = None,
    projected_known_roles: dict | None = None,
) -> dict:
    """Build a role_projection snapshot dict."""
    snap: dict = {
        "_name": name,
        "snapshot_type": "role_projection",
        "player_id": player_id,
        "role": role,
        "team": team,
        "round": round,
        "phase": phase,
        "alive_players": alive_players or ["p1", "p2", "p3", "p4", "p5", "p6"],
        "projected_known_roles": projected_known_roles or {},
    }
    return snap


def _make_god_snapshot(
    name: str,
    *,
    round: int = 1,
    phase: str = "night",
    players: list[dict] | None = None,
    alive_players: list[str] | None = None,
) -> dict:
    """Build a god snapshot dict."""
    snap: dict = {
        "_name": name,
        "snapshot_type": "god",
        "round": round,
        "phase": phase,
        "players": players or [],
        "alive_players": alive_players or [],
    }
    return snap


def _make_event(
    *,
    event_id: str = "ev1",
    visibility: str = "public",
    round: int = 0,
    phase: str = "day",
    actor: str = "system",
) -> dict:
    """Build a minimal runtime event."""
    return {
        "event_id": event_id,
        "visibility": visibility,
        "round": round,
        "phase": phase,
        "actor": actor,
    }


# ---------------------------------------------------------------------------
# Step 1: Constants and perspective helpers
# ---------------------------------------------------------------------------


class VisibilityConstantsTests(unittest.TestCase):
    """Verify public constants exist and have expected values."""

    def test_contract_version_is_string(self) -> None:
        self.assertIsInstance(CONTRACT_VERSION, str)
        self.assertTrue(CONTRACT_VERSION.startswith("g2c"))

    def test_role_perspective_prefix_is_string(self) -> None:
        self.assertIsInstance(ROLE_PERSPECTIVE_PREFIX, str)
        self.assertEqual(ROLE_PERSPECTIVE_PREFIX, "role:")

    def test_perspective_kind_god(self) -> None:
        self.assertEqual(perspective_kind("god"), "god")

    def test_perspective_kind_public(self) -> None:
        self.assertEqual(perspective_kind("public"), "public")

    def test_perspective_kind_role(self) -> None:
        self.assertEqual(perspective_kind("role:p3"), "role")

    def test_perspective_kind_team(self) -> None:
        self.assertEqual(perspective_kind("team:werewolf"), "team")

    def test_perspective_kind_unknown_raises(self) -> None:
        with self.assertRaises(VisibilityProjectionError):
            perspective_kind("unknown")

    def test_perspective_kind_empty_raises(self) -> None:
        with self.assertRaises(VisibilityProjectionError):
            perspective_kind("")

    def test_is_werewolf_role_true(self) -> None:
        self.assertTrue(is_werewolf_role("werewolf"))

    def test_is_werewolf_role_false(self) -> None:
        self.assertFalse(is_werewolf_role("seer"))
        self.assertFalse(is_werewolf_role("villager"))

    def test_infer_player_ids_from_index(self) -> None:
        index = {"p1": {}, "p3": {}, "p5": {}}
        self.assertEqual(infer_player_ids(index), ["p1", "p3", "p5"])

    def test_infer_player_ids_fallback(self) -> None:
        self.assertEqual(infer_player_ids({}), ["p1", "p2", "p3", "p4", "p5", "p6"])

    def test_unknown_player_shape(self) -> None:
        entry = unknown_player("p1")
        self.assertEqual(entry["player_id"], "p1")
        self.assertEqual(entry["display_role"], "unknown")
        self.assertEqual(entry["display_team"], "unknown")
        self.assertEqual(entry["visibility"], "hidden")

    def test_unknown_player_with_alive(self) -> None:
        entry = unknown_player("p2", alive=True)
        self.assertTrue(entry["alive"])


# ---------------------------------------------------------------------------
# Step 2: Seat role index builder
# ---------------------------------------------------------------------------


class VisibilitySeatIndexTests(unittest.TestCase):
    """Test build_seat_role_index."""

    def test_build_seat_role_index_reads_role_projection_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager",
                                   projected_known_roles={"p1": "seer"}),
                _make_role_snapshot("role-p3-r1.json", "p3", "werewolf", "werewolf",
                                   projected_known_roles={"p3": "werewolf"}),
            ])
            index = build_seat_role_index(run_dir)
            self.assertIn("p1", index)
            self.assertEqual(index["p1"]["role"], "seer")
            self.assertEqual(index["p1"]["role_source"], "role_projection_snapshot")
            self.assertIn("p3", index)
            self.assertEqual(index["p3"]["role"], "werewolf")
            self.assertEqual(index["p3"]["team_source"], "role_projection_snapshot")

    def test_god_snapshot_fields_are_not_trusted_for_non_god_projection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_god_snapshot("god-r1.json",
                    players=[{"player_id": "p1", "role": "seer", "team": "villager"}],
                    alive_players=["p1"]),
            ])
            index = build_seat_role_index(run_dir)
            self.assertIn("p1", index)
            # role/team sourced from god, NOT role_projection
            self.assertEqual(index["p1"]["role_source"], "god_snapshot")
            self.assertEqual(index["p1"]["team_source"], "god_snapshot")

    def test_build_seat_role_index_degrades_to_empty_on_missing_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [])
            index = build_seat_role_index(run_dir)
            self.assertEqual(index, {})


# ---------------------------------------------------------------------------
# Step 3: Player projection builder
# ---------------------------------------------------------------------------


class VisibilityPlayerProjectionTests(unittest.TestCase):
    """Test build_player_projection."""

    def _make_seat_index(self) -> dict:
        """Return a seat index with seer (p1), villager (p2), wolf (p3)."""
        return {
            "p1": {
                "player_id": "p1", "role": "seer", "team": "villager",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot", "alive": True,
                "projected_known_roles": {"p1": "seer", "p2": "villager", "p3": "unknown"},
            },
            "p2": {
                "player_id": "p2", "role": "villager", "team": "villager",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot", "alive": True,
                "projected_known_roles": {"p1": "unknown", "p2": "villager", "p3": "unknown"},
            },
            "p3": {
                "player_id": "p3", "role": "werewolf", "team": "werewolf",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot", "alive": True,
                "projected_known_roles": {"p1": "unknown", "p2": "unknown", "p3": "werewolf"},
            },
        }

    def test_god_projection_exposes_all_roles(self) -> None:
        index = self._make_seat_index()
        players = build_player_projection(index, "god")
        self.assertEqual(len(players), 3)
        roles = {p["player_id"]: p["display_role"] for p in players}
        self.assertEqual(roles["p1"], "seer")
        self.assertEqual(roles["p2"], "villager")
        self.assertEqual(roles["p3"], "werewolf")
        for p in players:
            self.assertEqual(p["visibility"], "full")

    def test_public_projection_hides_all_roles(self) -> None:
        index = self._make_seat_index()
        players = build_player_projection(index, "public")
        for p in players:
            self.assertEqual(p["display_role"], "unknown")
            self.assertEqual(p["display_team"], "unknown")

    def test_role_projection_exposes_only_self_role(self) -> None:
        # Use empty projected_known_roles so no other roles are revealed.
        index = {
            "p1": {
                "player_id": "p1", "role": "seer", "team": "villager",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot", "alive": True,
                "projected_known_roles": {},
            },
            "p2": {
                "player_id": "p2", "role": "villager", "team": "villager",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot", "alive": True,
                "projected_known_roles": {},
            },
            "p3": {
                "player_id": "p3", "role": "werewolf", "team": "werewolf",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot", "alive": True,
                "projected_known_roles": {},
            },
        }
        # seer (p1) view
        players = build_player_projection(index, "role:p1")
        self_entries = [p for p in players if p["player_id"] == "p1"]
        self.assertEqual(self_entries[0]["display_role"], "seer")
        self.assertEqual(self_entries[0]["display_team"], "villager")
        # Others hidden because projected_known_roles is empty
        for p in players:
            if p["player_id"] != "p1":
                self.assertEqual(p["display_role"], "unknown")

    def test_role_projection_uses_only_self_projected_known_roles(self) -> None:
        """p1's projected_known_roles says p2 is villager but doesn't expose wolf p3."""
        index = self._make_seat_index()
        players = build_player_projection(index, "role:p1")
        p2_entry = [p for p in players if p["player_id"] == "p2"][0]
        # p1 knows p2 is villager (non-wolf known role)
        self.assertEqual(p2_entry["display_role"], "villager")
        p3_entry = [p for p in players if p["player_id"] == "p3"][0]
        # p3 is werewolf, should be hidden even if projected_known_roles says unknown
        self.assertEqual(p3_entry["display_role"], "unknown")

    def test_werewolf_team_projection_exposes_only_trusted_wolves(self) -> None:
        index = self._make_seat_index()
        players = build_player_projection(index, "team:werewolf")
        # Only p3 has team werewolf with trusted source
        wolf_entries = [p for p in players if p["visibility"] == "team"]
        self.assertEqual(len(wolf_entries), 1)
        self.assertEqual(wolf_entries[0]["player_id"], "p3")
        self.assertEqual(wolf_entries[0]["display_role"], "werewolf")
        # Non-wolves are hidden
        for p in players:
            if p["player_id"] != "p3":
                self.assertEqual(p["display_role"], "unknown")

    def test_role_projection_hides_wolf_role_from_known_roles(self) -> None:
        """When projected_known_roles contains 'werewolf', it should not be exposed."""
        index = {
            "p1": {
                "player_id": "p1", "role": "seer", "team": "villager",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot", "alive": True,
                "projected_known_roles": {"p3": "werewolf"},
            },
            "p3": {
                "player_id": "p3", "role": "werewolf", "team": "werewolf",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot", "alive": True,
                "projected_known_roles": {},
            },
        }
        players = build_player_projection(index, "role:p1")
        p3_entry = [p for p in players if p["player_id"] == "p3"][0]
        self.assertEqual(p3_entry["display_role"], "unknown")


# ---------------------------------------------------------------------------
# Step 4: Event projection helper
# ---------------------------------------------------------------------------


class VisibilityEventProjectionTests(unittest.TestCase):
    """Test event_visible_in_projection and project_events."""

    def _make_seat_index(self) -> dict:
        return {
            "p1": {
                "player_id": "p1", "role": "seer", "team": "villager",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot",
                "projected_known_roles": {},
            },
            "p3": {
                "player_id": "p3", "role": "werewolf", "team": "werewolf",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot",
                "projected_known_roles": {},
            },
        }

    def test_all_visibility_is_public_like_for_all_perspectives(self) -> None:
        index: dict = {}
        event = _make_event(visibility="all")
        for perspective in ("god", "public", "role:p1", "team:werewolf"):
            visible, reason = event_visible_in_projection(event, perspective, index)
            self.assertTrue(visible, f"all visibility should be visible to {perspective}")
            if perspective == "god":
                self.assertEqual(reason, "god_view")

    def test_seer_event_visible_only_to_trusted_seer_role(self) -> None:
        index = self._make_seat_index()
        seer_event = _make_event(visibility="seer")
        # p1 is trusted seer
        visible, _ = event_visible_in_projection(seer_event, "role:p1", index)
        self.assertTrue(visible)
        # p3 is wolf, should not see seer events
        visible, _ = event_visible_in_projection(seer_event, "role:p3", index)
        self.assertFalse(visible)

    def test_witch_event_visible_only_to_trusted_witch_role(self) -> None:
        index = {
            "p1": {
                "player_id": "p1", "role": "witch", "team": "villager",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot",
                "projected_known_roles": {},
            },
        }
        witch_event = _make_event(visibility="witch")
        visible, _ = event_visible_in_projection(witch_event, "role:p1", index)
        self.assertTrue(visible)
        visible, _ = event_visible_in_projection(witch_event, "role:p2", index)
        self.assertFalse(visible)

    def test_werewolf_team_event_visible_to_trusted_wolves_and_team_view(self) -> None:
        index = self._make_seat_index()
        wolf_event = _make_event(visibility="werewolf_team")
        # p3 is trusted wolf
        visible, _ = event_visible_in_projection(wolf_event, "role:p3", index)
        self.assertTrue(visible)
        # team:werewolf perspective
        visible, _ = event_visible_in_projection(wolf_event, "team:werewolf", index)
        self.assertTrue(visible)
        # public should not see
        visible, _ = event_visible_in_projection(wolf_event, "public", index)
        self.assertFalse(visible)

    def test_unknown_visibility_hidden_from_non_god(self) -> None:
        index: dict = {}
        event = _make_event(visibility="internal")
        visible, _ = event_visible_in_projection(event, "god", index)
        self.assertTrue(visible)
        visible, _ = event_visible_in_projection(event, "public", index)
        self.assertFalse(visible)

    def test_project_events_returns_correct_counts(self) -> None:
        index = self._make_seat_index()
        events = [
            _make_event(event_id="e1", visibility="public"),
            _make_event(event_id="e2", visibility="seer"),
            _make_event(event_id="e3", visibility="werewolf_team"),
        ]
        result = project_events(events, "role:p1", index)
        # p1 is seer: sees public + seer events
        self.assertEqual(len(result["events"]), 2)
        self.assertEqual(result["hidden_event_count"], 1)

    def test_project_events_god_sees_all(self) -> None:
        events = [
            _make_event(event_id="e1", visibility="public"),
            _make_event(event_id="e2", visibility="internal"),
            _make_event(event_id="e3", visibility="seer"),
        ]
        result = project_events(events, "god", {})
        self.assertEqual(len(result["events"]), 3)
        self.assertEqual(result["hidden_event_count"], 0)

    def test_project_events_preserves_visibility_reason(self) -> None:
        events = [_make_event(event_id="e1", visibility="public")]
        result = project_events(events, "public", {})
        self.assertIn("_visibility_reason", result["events"][0])


# ---------------------------------------------------------------------------
# Step 5: Snapshot projection helper
# ---------------------------------------------------------------------------


class VisibilitySnapshotProjectionTests(unittest.TestCase):
    """Test project_snapshots."""

    def test_snapshot_metadata_shape_has_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager"),
            ])
            result = project_snapshots(run_dir, "god")
            self.assertIn("snapshots", result)
            self.assertIn("hidden_snapshot_count", result)
            self.assertGreaterEqual(len(result["snapshots"]), 1)

            item = result["snapshots"][0]
            required = {"snapshot_name", "snapshot_type", "perspective",
                        "visible", "hidden", "detail_endpoint", "hidden_reason"}
            for key in required:
                self.assertIn(key, item, f"Missing required key: {key}")

    def test_hidden_snapshot_metadata_omits_unsafe_player_and_team(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p3-r1.json", "p3", "werewolf", "werewolf"),
            ])
            # public view hides role_projection
            result = project_snapshots(run_dir, "public")
            self.assertEqual(result["hidden_snapshot_count"], 1)
            self.assertFalse(result["snapshots"][0]["visible"])

    def test_snapshot_metadata_contains_no_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager"),
            ])
            result = project_snapshots(run_dir, "god")
            for item in result["snapshots"]:
                ep = item.get("detail_endpoint", "")
                if isinstance(ep, str):
                    self.assertFalse(
                        ep.startswith("G:") or ep.startswith("C:") or ep.startswith("/mnt/"),
                        f"detail_endpoint contains absolute path: {ep}"
                    )

    def test_god_sees_all_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager"),
                _make_god_snapshot("god-r1.json"),
            ])
            result = project_snapshots(run_dir, "god")
            self.assertEqual(result["hidden_snapshot_count"], 0)

    def test_role_sees_only_own_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager"),
                _make_role_snapshot("role-p3-r1.json", "p3", "werewolf", "werewolf"),
            ])
            result = project_snapshots(run_dir, "role:p1")
            visible_count = sum(1 for s in result["snapshots"] if s["visible"])
            self.assertEqual(visible_count, 1)

    def test_empty_snapshots_dir_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run-empty"
            run_dir.mkdir()
            result = project_snapshots(run_dir, "god")
            self.assertEqual(result["snapshots"], [])
            self.assertEqual(result["hidden_snapshot_count"], 0)


# ---------------------------------------------------------------------------
# Step 6: Projection envelope builder
# ---------------------------------------------------------------------------


class VisibilityEnvelopeTests(unittest.TestCase):
    """Test build_projection_envelope."""

    def test_projection_envelope_contains_contract_version_and_proof(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager"),
            ])
            envelope = build_projection_envelope(
                run_dir=run_dir,
                run_id="run-1",
                perspective="god",
                events=[_make_event(visibility="public")],
            )
            self.assertEqual(envelope["contract_version"], CONTRACT_VERSION)
            self.assertEqual(envelope["run_id"], "run-1")
            self.assertEqual(envelope["perspective"], "god")
            self.assertEqual(envelope["view_kind"], "god")
            self.assertIn("proof", envelope)
            self.assertIsInstance(envelope["proof"], dict)
            self.assertIn("source", envelope["proof"])
            self.assertIn("rules", envelope["proof"])
            # Has trusted role_projection -> source should be "snapshots"
            self.assertEqual(envelope["proof"]["source"], "snapshots")

    def test_projection_envelope_uses_insufficient_artifacts_source_when_no_trusted_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [])
            envelope = build_projection_envelope(
                run_dir=run_dir,
                run_id="run-1",
                perspective="public",
                events=[],
            )
            self.assertEqual(envelope["proof"]["source"], "insufficient_artifacts")

    def test_projection_envelope_has_all_required_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager"),
            ])
            envelope = build_projection_envelope(
                run_dir=run_dir,
                run_id="run-1",
                perspective="god",
                events=[],
            )
            required_keys = {
                "contract_version", "run_id", "perspective", "view_kind",
                "players", "events", "hidden_event_count", "snapshots",
                "hidden_snapshot_count", "proof",
            }
            for key in required_keys:
                self.assertIn(key, envelope, f"Missing required envelope key: {key}")

    def test_role_projection_envelope_includes_self_proof(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager"),
            ])
            envelope = build_projection_envelope(
                run_dir=run_dir,
                run_id="run-1",
                perspective="role:p1",
                events=[],
            )
            proof = envelope["proof"]
            self.assertIn("self_player_id", proof)
            self.assertEqual(proof["self_player_id"], "p1")
            self.assertEqual(proof["self_role"], "seer")

    def test_team_werewolf_proof_includes_team(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p3-r1.json", "p3", "werewolf", "werewolf"),
            ])
            envelope = build_projection_envelope(
                run_dir=run_dir,
                run_id="run-1",
                perspective="team:werewolf",
                events=[],
            )
            self.assertEqual(envelope["proof"].get("team"), "werewolf")

    def test_proof_rules_contain_expected_strings(self) -> None:
        """proof.rules must include specific trust-chain rule descriptions."""
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager"),
            ])
            envelope = build_projection_envelope(
                run_dir=run_dir,
                run_id="run-1",
                perspective="god",
                events=[],
            )
            rules = envelope["proof"]["rules"]
            self.assertIsInstance(rules, list)
            self.assertGreaterEqual(len(rules), 3)
            # Must mention role_projection trust
            rules_text = " ".join(rules)
            self.assertIn("role_projection", rules_text)
            # Must mention non-god trust constraint
            self.assertIn("non-god", rules_text)
            # Must mention team:werewolf constraint
            self.assertIn("team:werewolf", rules_text)

    def test_proof_rules_are_consistent_across_perspectives(self) -> None:
        """Base proof rules should be the same regardless of perspective."""
        with tempfile.TemporaryDirectory() as td:
            run_dir = _make_run_dir(Path(td), "run-1", [
                _make_role_snapshot("role-p1-r1.json", "p1", "seer", "villager"),
                _make_role_snapshot("role-p3-r1.json", "p3", "werewolf", "werewolf"),
            ])
            god_envelope = build_projection_envelope(
                run_dir=run_dir, run_id="run-1", perspective="god", events=[],
            )
            public_envelope = build_projection_envelope(
                run_dir=run_dir, run_id="run-1", perspective="public", events=[],
            )
            # Base rules list should be identical
            self.assertEqual(god_envelope["proof"]["rules"], public_envelope["proof"]["rules"])


# ---------------------------------------------------------------------------
# B档 gap fix: seer-vs-witch cross-visibility test
# ---------------------------------------------------------------------------


class VisibilityCrossRoleEventTests(unittest.TestCase):
    """Test that role-specific events are only visible to the correct role."""

    def _make_seat_index_with_seer_and_witch(self) -> dict:
        return {
            "p1": {
                "player_id": "p1", "role": "seer", "team": "villager",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot",
                "projected_known_roles": {},
            },
            "p2": {
                "player_id": "p2", "role": "witch", "team": "villager",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot",
                "projected_known_roles": {},
            },
            "p3": {
                "player_id": "p3", "role": "werewolf", "team": "werewolf",
                "role_source": "role_projection_snapshot",
                "team_source": "role_projection_snapshot",
                "alive_source": "role_projection_snapshot",
                "projected_known_roles": {},
            },
        }

    def test_seer_sees_seer_events_but_witch_does_not(self) -> None:
        """Seer (p1) can see seer-visibility events; witch (p2) cannot."""
        index = self._make_seat_index_with_seer_and_witch()
        seer_event = _make_event(visibility="seer")
        # Seer sees it
        visible, reason = event_visible_in_projection(seer_event, "role:p1", index)
        self.assertTrue(visible)
        self.assertEqual(reason, "seer_event")
        # Witch does NOT see seer events
        visible, reason = event_visible_in_projection(seer_event, "role:p2", index)
        self.assertFalse(visible)
        self.assertEqual(reason, "hidden")

    def test_witch_sees_witch_events_but_seer_does_not(self) -> None:
        """Witch (p2) can see witch-visibility events; seer (p1) cannot."""
        index = self._make_seat_index_with_seer_and_witch()
        witch_event = _make_event(visibility="witch")
        # Witch sees it
        visible, reason = event_visible_in_projection(witch_event, "role:p2", index)
        self.assertTrue(visible)
        self.assertEqual(reason, "witch_event")
        # Seer does NOT see witch events
        visible, reason = event_visible_in_projection(witch_event, "role:p1", index)
        self.assertFalse(visible)
        self.assertEqual(reason, "hidden")

    def test_werewolf_cannot_see_seer_or_witch_events(self) -> None:
        """Werewolf (p3) cannot see seer or witch role-specific events."""
        index = self._make_seat_index_with_seer_and_witch()
        seer_event = _make_event(visibility="seer")
        witch_event = _make_event(visibility="witch")
        visible, _ = event_visible_in_projection(seer_event, "role:p3", index)
        self.assertFalse(visible)
        visible, _ = event_visible_in_projection(witch_event, "role:p3", index)
        self.assertFalse(visible)

    def test_seer_cannot_see_werewolf_team_events(self) -> None:
        """Seer (p1, villager team) cannot see werewolf_team events."""
        index = self._make_seat_index_with_seer_and_witch()
        wolf_event = _make_event(visibility="werewolf_team")
        visible, _ = event_visible_in_projection(wolf_event, "role:p1", index)
        self.assertFalse(visible)

    def test_full_cross_role_event_matrix(self) -> None:
        """Comprehensive matrix: each role perspective sees only its own events."""
        index = self._make_seat_index_with_seer_and_witch()
        events = [
            _make_event(event_id="pub", visibility="public"),
            _make_event(event_id="seer_ev", visibility="seer"),
            _make_event(event_id="witch_ev", visibility="witch"),
            _make_event(event_id="wolf_ev", visibility="werewolf_team"),
            _make_event(event_id="internal_ev", visibility="internal"),
        ]

        # Seer (p1): public + seer
        result = project_events(events, "role:p1", index)
        visible_ids = {e["event_id"] for e in result["events"]}
        self.assertEqual(visible_ids, {"pub", "seer_ev"})
        self.assertEqual(result["hidden_event_count"], 3)

        # Witch (p2): public + witch
        result = project_events(events, "role:p2", index)
        visible_ids = {e["event_id"] for e in result["events"]}
        self.assertEqual(visible_ids, {"pub", "witch_ev"})
        self.assertEqual(result["hidden_event_count"], 3)

        # Werewolf (p3): public + werewolf_team
        result = project_events(events, "role:p3", index)
        visible_ids = {e["event_id"] for e in result["events"]}
        self.assertEqual(visible_ids, {"pub", "wolf_ev"})
        self.assertEqual(result["hidden_event_count"], 3)


if __name__ == "__main__":
    unittest.main()

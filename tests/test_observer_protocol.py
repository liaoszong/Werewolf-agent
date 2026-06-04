"""Unit tests for the observer protocol helpers (G2a)."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from werewolf_eval.observer_protocol import (
    ALLOWED_ARTIFACTS,
    ALLOWED_MODES,
    ALLOWED_PERSPECTIVES,
    ALLOWED_TEMPLATES,
    RUN_STATUS_VALUES,
    ObserverProtocolError,
    artifact_path,
    build_artifact_registry,
    build_run_detail,
    build_run_summary,
    build_snapshot_registry,
    event_visible_to_perspective,
    filter_events_for_perspective,
    format_sse_event,
    format_sse_status,
    generate_run_id,
    list_run_dirs,
    load_snapshot_detail,
    normalize_perspective,
    parse_launch_request,
    parse_profile_launch_request,
    safe_child_path,
    snapshot_path,
    snapshot_visible_to_perspective,
    validate_run_id,
    validate_snapshot_name,
)


# ---------------------------------------------------------------------------
# ObserverPathSafetyTests
# ---------------------------------------------------------------------------


class ObserverPathSafetyTests(TestCase):
    def test_validate_run_id_rejects_path_traversal(self) -> None:
        bad = ["..", "../etc", "a/b", "a\\b", "/etc", "c:..", "", "a%2e%2e"]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ObserverProtocolError):
                    validate_run_id(value)

    def test_artifact_path_rejects_unknown_artifact(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_01"
            run_dir.mkdir()
            with self.assertRaises(ObserverProtocolError):
                artifact_path(run_dir, "secret.txt")

    def test_safe_child_path_stays_under_root(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "runs"
            root.mkdir()
            child_path = safe_child_path(root, "run_01")
            self.assertEqual(child_path, root / "run_01")

            with self.assertRaises(ObserverProtocolError):
                safe_child_path(root, "../outside")
            with self.assertRaises(ObserverProtocolError):
                safe_child_path(root, "")
            with self.assertRaises(ObserverProtocolError):
                safe_child_path(root, "sub/dir")

    def test_validate_snapshot_name_rejects_nested_paths(self) -> None:
        bad = ["../snap.json", "a/b.json", "a\\b.json", "", ".json", "bad.txt"]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ObserverProtocolError):
                    validate_snapshot_name(value)

        good = ["snap_001.json", "r3_p1.json", "abc-123_.json"]
        for value in good:
            with self.subTest(value=value):
                self.assertEqual(validate_snapshot_name(value), value)


# ---------------------------------------------------------------------------
# ObserverRunSummaryTests
# ---------------------------------------------------------------------------


class ObserverRunSummaryTests(TestCase):
    def test_build_run_summary_counts_events_and_snapshots(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_01"
            run_dir.mkdir()
            (run_dir / "events.jsonl").write_text(
                json.dumps({"kind": "game_started", "visibility": "public"}) + "\n"
                + json.dumps({"kind": "round_started", "visibility": "public"}) + "\n",
                encoding="utf-8",
            )
            snap_dir = run_dir / "snapshots"
            snap_dir.mkdir()
            (snap_dir / "snap_001.json").write_text(
                json.dumps({"snapshot_type": "god", "round": 1, "phase": "night"}),
                encoding="utf-8",
            )
            (snap_dir / "snap_002.json").write_text(
                json.dumps({"snapshot_type": "role_projection", "player_id": "p1", "round": 2}),
                encoding="utf-8",
            )

            summary = build_run_summary(run_dir)
            self.assertEqual(summary["run_id"], "run_01")
            self.assertEqual(summary["event_count"], 2)
            self.assertEqual(summary["snapshot_count"], 2)
            self.assertIn("snap_001.json", summary["snapshot_names"])
            self.assertIn("snap_002.json", summary["snapshot_names"])

    def test_build_artifact_registry_reports_allowed_artifacts_only(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_01"
            run_dir.mkdir()
            (run_dir / "events.jsonl").write_text("{}", encoding="utf-8")

            registry = build_artifact_registry(run_dir)
            self.assertEqual(len(registry), len(ALLOWED_ARTIFACTS))
            for name in ALLOWED_ARTIFACTS:
                self.assertIn(name, registry)
            self.assertTrue(registry["events.jsonl"]["exists"])
            self.assertFalse(registry["game-log.json"]["exists"])


# ---------------------------------------------------------------------------
# ObserverLaunchContractTests
# ---------------------------------------------------------------------------


class ObserverLaunchContractTests(TestCase):
    def test_parse_launch_request_accepts_default_fake_template(self) -> None:
        result = parse_launch_request({})
        self.assertEqual(result["template"], "default_6p_fake")
        self.assertEqual(result["mode"], "fake")
        self.assertTrue(result["run_id"].startswith("default_6p_fake_"))

    def test_parse_launch_request_rejects_unknown_template(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            parse_launch_request({"template": "bad_template"})

    def test_parse_launch_request_rejects_extra_keys(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            parse_launch_request({"template": "default_6p_fake", "extra": True})

    def test_generate_run_id_uses_safe_uuid_suffix(self) -> None:
        rid1 = generate_run_id()
        rid2 = generate_run_id()
        self.assertNotEqual(rid1, rid2)
        uuid_re = re.compile(r"[a-f0-9]{8}")
        for rid in (rid1, rid2):
            parts = rid.rsplit("_", 1)
            self.assertEqual(len(parts), 2)
            self.assertTrue(uuid_re.match(parts[1]), f"no UUID suffix in {rid}")
        validate_run_id(rid1)
        validate_run_id(rid2)


# ---------------------------------------------------------------------------
# ObserverVisibilityTests
# ---------------------------------------------------------------------------


class ObserverVisibilityTests(TestCase):
    @staticmethod
    def _make_event(visibility: str) -> dict[str, object]:
        return {"kind": "test", "visibility": visibility}

    def test_god_sees_all_events(self) -> None:
        for visibility in ("public", "private", "internal", "all", "seer", "witch", "werewolf_team"):
            event = self._make_event(visibility)
            self.assertTrue(event_visible_to_perspective(event, "god"), visibility)

    def test_public_hides_private_internal_all_seer_and_witch_events(self) -> None:
        hidden = {"private", "internal", "seer", "witch", "werewolf_team"}
        for visibility in ("public", "private", "internal", "all", "seer", "witch", "werewolf_team"):
            event = self._make_event(visibility)
            result = event_visible_to_perspective(event, "public")
            if visibility in hidden:
                self.assertFalse(result, f"public should not see {visibility}")
            else:
                self.assertTrue(result, f"public should see {visibility}")

    def test_role_hides_private_internal_all_seer_and_witch_events(self) -> None:
        hidden = {"private", "internal", "seer", "witch", "werewolf_team"}
        for visibility in ("public", "private", "internal", "all", "seer", "witch", "werewolf_team"):
            event = self._make_event(visibility)
            result = event_visible_to_perspective(event, "role:p1")
            if visibility in hidden:
                self.assertFalse(result, f"role:p1 should not see {visibility}")
            else:
                self.assertTrue(result, f"role:p1 should see {visibility}")

    def test_werewolf_team_sees_public_and_werewolf_team_events(self) -> None:
        visible = {"public", "all", "werewolf_team"}
        hidden = {"private", "internal", "seer", "witch"}
        for visibility in ("public", "private", "internal", "all", "seer", "witch", "werewolf_team"):
            event = self._make_event(visibility)
            result = event_visible_to_perspective(event, "team:werewolf")
            if visibility in visible:
                self.assertTrue(result, f"werewolf team should see {visibility}")
            else:
                self.assertFalse(result, f"werewolf team should not see {visibility}")

    def test_unknown_perspective_is_rejected(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            normalize_perspective("bad_perspective")
        with self.assertRaises(ObserverProtocolError):
            event_visible_to_perspective({}, "bad_perspective")

    def test_sse_format_contains_event_and_data_lines(self) -> None:
        event = {"kind": "game_started", "visibility": "public"}
        output = format_sse_event(event)
        text = output.decode("utf-8")
        self.assertIn("event: runtime_event", text)
        self.assertIn("data: ", text)
        self.assertTrue(text.endswith("\n\n"))

    def test_sse_status_contains_run_status_event(self) -> None:
        output = format_sse_status("run_01", "completed")
        text = output.decode("utf-8")
        self.assertIn("event: run_status", text)
        self.assertIn("run_01", text)
        self.assertIn("completed", text)
        self.assertTrue(text.endswith("\n\n"))

    def test_filter_events_for_perspective_returns_dict_with_count(self) -> None:
        events = [
            self._make_event("public"),
            self._make_event("private"),
            self._make_event("public"),
        ]
        result = filter_events_for_perspective(events, "public")
        self.assertIsInstance(result, dict)
        self.assertIn("events", result)
        self.assertIn("perspective", result)
        self.assertIn("hidden_count", result)
        self.assertEqual(result["perspective"], "public")
        self.assertEqual(len(result["events"]), 2)  # type: ignore[arg-type]
        self.assertEqual(result["hidden_count"], 1)


# ---------------------------------------------------------------------------
# ObserverSnapshotVisibilityTests
# ---------------------------------------------------------------------------


class ObserverSnapshotVisibilityTests(TestCase):
    @staticmethod
    def _make_god_snapshot() -> dict[str, object]:
        return {"snapshot_type": "god", "round": 1, "phase": "night"}

    @staticmethod
    def _make_role_projection(player_id: str, team: str) -> dict[str, object]:
        return {
            "snapshot_type": "role_projection",
            "player_id": player_id,
            "team": team,
            "round": 2,
            "phase": "day",
        }

    def _setup_run_dir(self, tmp: str, snapshots: list[dict[str, object]]) -> Path:
        run_dir = Path(tmp) / "run_01"
        snap_dir = run_dir / "snapshots"
        snap_dir.mkdir(parents=True)
        for i, snap in enumerate(snapshots):
            (snap_dir / f"snap_{i:03d}.json").write_text(
                json.dumps(snap), encoding="utf-8"
            )
        return run_dir

    def test_god_can_read_god_snapshot_detail(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = self._setup_run_dir(tmp, [self._make_god_snapshot()])
            detail = load_snapshot_detail(run_dir, "snap_000.json", "god")
            self.assertEqual(detail["snapshot_type"], "god")

    def test_public_cannot_read_god_snapshot_detail(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = self._setup_run_dir(tmp, [self._make_god_snapshot()])
            with self.assertRaises(ObserverProtocolError):
                load_snapshot_detail(run_dir, "snap_000.json", "public")

    def test_role_can_read_only_own_projection_snapshot(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = self._setup_run_dir(tmp, [
                self._make_role_projection("p1", "villager"),
                self._make_role_projection("p2", "villager"),
            ])
            detail = load_snapshot_detail(run_dir, "snap_000.json", "role:p1")
            self.assertEqual(detail["player_id"], "p1")
            with self.assertRaises(ObserverProtocolError):
                load_snapshot_detail(run_dir, "snap_001.json", "role:p1")

    def test_werewolf_team_can_read_werewolf_projection_snapshot(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = self._setup_run_dir(tmp, [
                self._make_role_projection("p2", "werewolf"),
                self._make_role_projection("p1", "villager"),
            ])
            detail = load_snapshot_detail(run_dir, "snap_000.json", "team:werewolf")
            self.assertEqual(detail["team"], "werewolf")
            with self.assertRaises(ObserverProtocolError):
                load_snapshot_detail(run_dir, "snap_001.json", "team:werewolf")

    def test_snapshot_registry_marks_hidden_snapshots_for_public(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = self._setup_run_dir(tmp, [
                self._make_god_snapshot(),
                self._make_role_projection("p1", "villager"),
            ])
            registry = build_snapshot_registry(run_dir, "public")
            self.assertEqual(len(registry), 2)
            for entry in registry:
                self.assertTrue(entry["hidden"], f"public should not see {entry['name']}")

    def test_snapshot_registry_god_sees_all(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = self._setup_run_dir(tmp, [
                self._make_god_snapshot(),
                self._make_role_projection("p1", "villager"),
            ])
            registry = build_snapshot_registry(run_dir, "god")
            self.assertEqual(len(registry), 2)
            for entry in registry:
                self.assertFalse(entry["hidden"])


# ---------------------------------------------------------------------------
# ObserverHelperEdgeCases
# ---------------------------------------------------------------------------


class ObserverHelperEdgeCases(TestCase):
    def test_list_run_dirs_empty_when_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            result = list_run_dirs(Path(tmp) / "nonexistent")
            self.assertEqual(result, [])

    def test_list_run_dirs_returns_sorted_dirs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run_c").mkdir()
            (root / "run_a").mkdir()
            (root / "run_b").mkdir()
            (root / "file.txt").touch()
            result = list_run_dirs(root)
            names = [d.name for d in result]
            self.assertEqual(names, ["run_a", "run_b", "run_c"])

    def test_build_run_detail_includes_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_01"
            run_dir.mkdir()
            detail = build_run_detail(run_dir)
            self.assertIn("artifacts", detail)
            self.assertIn("run_id", detail)

    def test_snapshot_path_uses_snapshots_subdir(self) -> None:
        with TemporaryDirectory() as tmp:
            snap_dir = Path(tmp) / "run_01" / "snapshots"
            snap_dir.mkdir(parents=True)
            result = snapshot_path(Path(tmp) / "run_01", "test.json")
            self.assertEqual(result.parent.name, "snapshots")

    def test_generate_run_id_custom_prefix(self) -> None:
        rid = generate_run_id("my_run")
        self.assertTrue(rid.startswith("my_run_"))
        validate_run_id(rid)

    def test_normalize_perspective_defaults_to_god(self) -> None:
        self.assertEqual(normalize_perspective(None), "god")

    def test_parse_launch_with_explicit_run_id(self) -> None:
        result = parse_launch_request({
            "template": "default_6p_fake",
            "run_id": "my_custom_id",
            "mode": "fake",
        })
        self.assertEqual(result["run_id"], "my_custom_id")

    def test_parse_launch_rejects_unsafe_run_id(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            parse_launch_request({"template": "default_6p_fake", "run_id": "../escape"})

    def test_parse_launch_rejects_bad_mode(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            parse_launch_request({"mode": "hacked"})

    def test_event_visible_with_none_visibility_field(self) -> None:
        event: dict[str, object] = {"kind": "test"}
        with self.assertRaises(ObserverProtocolError):
            event_visible_to_perspective(event, "bad_perspective")
        self.assertTrue(event_visible_to_perspective(event, "god"))
        self.assertFalse(event_visible_to_perspective(event, "public"))

    def test_snapshot_visible_unknown_type(self) -> None:
        snap = {"snapshot_type": "unknown"}
        self.assertTrue(snapshot_visible_to_perspective(snap, "god"))
        self.assertFalse(snapshot_visible_to_perspective(snap, "public"))
        self.assertFalse(snapshot_visible_to_perspective(snap, "role:p1"))
        self.assertFalse(snapshot_visible_to_perspective(snap, "team:werewolf"))


# ---------------------------------------------------------------------------
# ObserverProtocolTraversalTests
# ---------------------------------------------------------------------------


class ObserverProtocolTraversalTests(TestCase):
    def test_validate_run_id_rejects_backslash_traversal(self) -> None:
        bad = ["..\\x", "x\\y", "a\\..\\b"]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ObserverProtocolError):
                    validate_run_id(value)

    def test_validate_snapshot_name_rejects_all_traversal_variants(self) -> None:
        bad = ["../x", "..\\x", "x/y", "x\\y"]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ObserverProtocolError):
                    validate_snapshot_name(value)

    def test_safe_child_path_rejects_all_traversal_variants(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = ["../x", "..\\x", "x/y", "x\\y"]
            for value in bad:
                with self.subTest(value=value):
                    with self.assertRaises(ObserverProtocolError):
                        safe_child_path(root, value)

    def test_artifact_path_rejects_traversal_in_artifact_name(self) -> None:
        with TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_01"
            run_dir.mkdir()
            with self.assertRaises(ObserverProtocolError):
                artifact_path(run_dir, "../events.jsonl")


class ProfileLaunchRequestTests(TestCase):
    def test_resolved_profile_in_allowed_artifacts(self) -> None:
        self.assertIn("resolved-profile.json", ALLOWED_ARTIFACTS)

    def test_accepts_inline_profile(self) -> None:
        out = parse_profile_launch_request({"profile": {"name": "x"}})
        self.assertEqual(out["kind"], "inline")
        self.assertEqual(out["mode"], "fake")
        self.assertTrue(out["run_id"])

    def test_accepts_named_profile(self) -> None:
        out = parse_profile_launch_request({"profile_name": "demo"})
        self.assertEqual(out["kind"], "named")
        self.assertEqual(out["profile_name"], "demo")

    def test_rejects_both_sources(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"profile": {}, "profile_name": "demo"})

    def test_rejects_profile_with_template(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"profile_name": "demo", "template": "default_6p_fake"})

    def test_rejects_neither_source(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"mode": "fake"})

    def test_rejects_unsafe_profile_name(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"profile_name": "../escape"})

    def test_rejects_non_string_profile_name(self) -> None:
        for bad in (None, 123, ["x"]):
            with self.assertRaises(ObserverProtocolError):
                parse_profile_launch_request({"profile_name": bad})

    def test_rejects_non_string_run_id(self) -> None:
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"profile_name": "demo", "run_id": 123})

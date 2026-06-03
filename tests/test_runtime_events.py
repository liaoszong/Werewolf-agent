"""Unit tests for :mod:`werewolf_eval.runtime_events`."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from werewolf_eval.runtime_events import (
    RUNTIME_EVENT_KINDS,
    RUNTIME_EVENT_VISIBILITIES,
    RuntimeEventError,
    RuntimeEventWriter,
    assert_no_secret_patterns,
    build_god_snapshot,
    build_prompt_manifest,
    build_role_projection_snapshot,
    read_events_jsonl,
    redact_secret_values,
    validate_runtime_event,
)


def _make_event(
    *,
    event_id: str | None = None,
    seq: int = 0,
    kind: str = "game_started",
    round_num: int = 1,
    phase: str = "night",
    actor: str = "p1",
    visibility: str = "public",
    ts: str = "2026-06-03T00:00:00+00:00",
    payload: dict | None = None,
    refs: dict | None = None,
) -> dict:
    ev: dict = {
        "event_id": event_id or str(uuid.uuid4()),
        "seq": seq,
        "kind": kind,
        "round": round_num,
        "phase": phase,
        "actor": actor,
        "visibility": visibility,
        "ts": ts,
    }
    if payload is not None:
        ev["payload"] = payload
    if refs is not None:
        ev["refs"] = refs
    return ev


class RuntimeEventWriterTests(TestCase):
    """Tests for :class:`RuntimeEventWriter` integration."""

    def test_emit_writes_monotonic_jsonl_events(self) -> None:
        """Emit three events and verify JSONL content and monotonic seq."""
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            writer = RuntimeEventWriter("test_run", out, clock=lambda: "T")

            e0 = writer.emit(
                "game_started",
                round=0,
                phase="setup",
                actor="system",
                visibility="public",
            )
            e1 = writer.emit(
                "round_started",
                round=1,
                phase="night",
                actor="system",
                visibility="public",
            )
            e2 = writer.emit(
                "observation_delivered",
                round=1,
                phase="night",
                actor="p1",
                visibility="private",
            )

            lines = out.joinpath("events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 3)

            for i, line in enumerate(lines):
                ev = json.loads(line)
                self.assertEqual(ev["seq"], i)
                self.assertEqual(ev["event_id"], [e0, e1, e2][i]["event_id"])

    def test_read_events_rejects_duplicate_event_id(self) -> None:
        """read_events_jsonl must reject lines sharing an event_id."""
        dup_id = str(uuid.uuid4())
        lines = [
            json.dumps(_make_event(event_id=dup_id, seq=0), ensure_ascii=False, sort_keys=True),
            json.dumps(_make_event(event_id=dup_id, seq=1), ensure_ascii=False, sort_keys=True),
        ]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(RuntimeEventError) as ctx:
                read_events_jsonl(path)
            self.assertIn("Duplicate event_id", str(ctx.exception))

    def test_read_events_rejects_non_monotonic_sequence(self) -> None:
        """read_events_jsonl must reject sequences where seq does not increase."""
        lines = [
            json.dumps(_make_event(seq=0), ensure_ascii=False, sort_keys=True),
            json.dumps(_make_event(seq=2), ensure_ascii=False, sort_keys=True),  # gap is fine
            json.dumps(_make_event(seq=1), ensure_ascii=False, sort_keys=True),  # not monotonic
        ]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(RuntimeEventError) as ctx:
                read_events_jsonl(path)
            self.assertIn("Non-monotonic seq", str(ctx.exception))

    def test_prompt_manifest_redacts_secret_like_values(self) -> None:
        """write_prompt_manifest must redact values containing secret fragments."""
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            writer = RuntimeEventWriter("test_manifest", out)

            manifest: dict = {
                "system_prompt": "You are a helpful assistant.",
                "api_key_value": "sk-this-is-a-secret",
                "nested": {"token": "Bearer eyJhbGci"},
                "safe_list": ["hello", "world"],
            }
            manifest_path = writer.write_prompt_manifest(manifest)
            self.assertTrue(manifest_path.exists())
            self.assertEqual(manifest_path, out / "prompt-manifest.json")

            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["system_prompt"], "You are a helpful assistant.")
            self.assertEqual(loaded["api_key_value"], "<REDACTED>")
            self.assertEqual(loaded["nested"]["token"], "<REDACTED>")
            self.assertEqual(loaded["safe_list"], ["hello", "world"])

    def test_snapshot_writer_emits_snapshot_event_and_file(self) -> None:
        """write_snapshot must write the snapshot file and emit a
        snapshot_written event."""
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            writer = RuntimeEventWriter("test_snap", out)

            snapshot: dict = {
                "game_state": "active",
                "alive": ["p1", "p2"],
                "secret_api_key": "sk-very-secret",
            }
            rel_path = writer.write_snapshot(
                "round01",
                snapshot,
                visibility="internal",
                round=1,
                phase="night",
                actor="system",
            )

            # Snapshot file written
            snapshot_file = out / rel_path
            self.assertTrue(snapshot_file.exists())
            loaded = json.loads(snapshot_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded["game_state"], "active")
            self.assertEqual(loaded["secret_api_key"], "<REDACTED>")

            # snapshot_written event emitted
            lines = writer.events_path.read_text(encoding="utf-8").splitlines()
            events = [json.loads(line) for line in lines]
            snap_events = [e for e in events if e["kind"] == "snapshot_written"]
            self.assertEqual(len(snap_events), 1)
            self.assertEqual(snap_events[0]["payload"]["snapshot_name"], "round01")

    def test_validate_event_rejects_secret_payload(self) -> None:
        """validate_runtime_event must reject payloads containing secrets."""
        bad_event = _make_event(
            payload={"key": "sk-this-is-leaked"},
        )
        with self.assertRaises(RuntimeEventError) as ctx:
            validate_runtime_event(bad_event)
        self.assertIn("Secret pattern", str(ctx.exception))

    # -- additional edge-case coverage -------------------------------------

    def test_read_events_rejects_empty_lines(self) -> None:
        """Empty lines in events.jsonl must be rejected."""
        lines = [
            json.dumps(_make_event(seq=0), ensure_ascii=False, sort_keys=True),
            "",
            json.dumps(_make_event(seq=1), ensure_ascii=False, sort_keys=True),
        ]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text("\n".join(lines), encoding="utf-8")
            with self.assertRaises(RuntimeEventError) as ctx:
                read_events_jsonl(path)
            self.assertIn("Empty line", str(ctx.exception))

    def test_read_events_rejects_malformed_json(self) -> None:
        """Malformed JSON lines must be rejected."""
        ev = _make_event(seq=0)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                json.dumps(ev, ensure_ascii=False, sort_keys=True)
                + "\n{invalid json}\n",
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeEventError) as ctx:
                read_events_jsonl(path)
            self.assertIn("Malformed JSON", str(ctx.exception))

    def test_validate_event_valid(self) -> None:
        """A correctly-formed event must pass validation without error."""
        event = _make_event()
        # Should not raise.
        validate_runtime_event(event)

    def test_validate_event_missing_field(self) -> None:
        """An event missing a required field must raise."""
        event = _make_event()
        del event["kind"]
        with self.assertRaises(RuntimeEventError) as ctx:
            validate_runtime_event(event)
        self.assertIn("Missing required event field", str(ctx.exception))

    def test_validate_event_invalid_kind(self) -> None:
        """An event with an unrecognised kind must raise."""
        event = _make_event(kind="invalid_kind_xyz")
        with self.assertRaises(RuntimeEventError) as ctx:
            validate_runtime_event(event)
        self.assertIn("Invalid event kind", str(ctx.exception))

    def test_validate_event_invalid_visibility(self) -> None:
        """An event with an unrecognised visibility must raise."""
        event = _make_event(visibility="top_secret")
        with self.assertRaises(RuntimeEventError) as ctx:
            validate_runtime_event(event)
        self.assertIn("Invalid visibility", str(ctx.exception))

    def test_validate_event_negative_seq(self) -> None:
        """A negative seq value must be rejected."""
        event = _make_event(seq=-1)
        with self.assertRaises(RuntimeEventError) as ctx:
            validate_runtime_event(event)
        self.assertIn("non-negative", str(ctx.exception))

    def test_redact_secret_values_deep(self) -> None:
        """redact_secret_values must traverse nested structures."""
        data: dict = {
            "outer": {
                "inner_key": "sk-deep-secret",
                "safe": "hello",
            },
            "items": ["sk-first", "ok", {"api_key": "Bearer xxx"}],
        }
        result = redact_secret_values(data)
        self.assertEqual(result["outer"]["inner_key"], "<REDACTED>")
        self.assertEqual(result["outer"]["safe"], "hello")
        self.assertEqual(result["items"][0], "<REDACTED>")
        self.assertEqual(result["items"][1], "ok")
        self.assertEqual(result["items"][2]["api_key"], "<REDACTED>")

    def test_assert_no_secret_patterns_passes_clean(self) -> None:
        """assert_no_secret_patterns must not raise for clean data."""
        assert_no_secret_patterns({"safe": "value", "nested": {"also_safe": 42}})

    def test_assert_no_secret_patterns_raises_on_secret(self) -> None:
        """assert_no_secret_patterns must raise when it finds a secret."""
        with self.assertRaises(RuntimeEventError):
            assert_no_secret_patterns({"key": "sk-leaked"})

    def test_read_events_fails_file_not_found(self) -> None:
        """read_events_jsonl must raise when the file does not exist."""
        with self.assertRaises(RuntimeEventError):
            read_events_jsonl(Path("/nonexistent/events.jsonl"))


class RuntimeSnapshotProjectionTests(TestCase):
    """Tests for snapshot / projection builders."""

    def test_non_wolf_projection_does_not_include_hidden_wolf_roles(self) -> None:
        """A villager/seer observer should see "unknown" for werewolf roles."""
        obs_dict: dict = {
            "player_id": "p1",
            "role": "villager",
            "team": "villager",
            "phase": "night",
            "round": 1,
            "alive_players": ["p1", "p2", "p3"],
            "public_event_ids": [],
            "private_event_ids": [],
            "known_roles": {"p1": "villager", "p2": "werewolf", "p3": "seer"},
        }
        proj = build_role_projection_snapshot(run_id="test", observation=obs_dict)
        roles = proj["projected_known_roles"]
        assert isinstance(roles, dict)
        self.assertEqual(roles.get("p1"), "villager")
        self.assertEqual(roles.get("p2"), "unknown")
        self.assertEqual(roles.get("p3"), "seer")

    def test_wolf_projection_may_include_wolf_teammate_roles(self) -> None:
        """A werewolf observer must see full known_roles including wolf teammates."""
        obs_dict: dict = {
            "player_id": "p2",
            "role": "werewolf",
            "team": "werewolf",
            "phase": "night",
            "round": 1,
            "alive_players": ["p1", "p2", "p3"],
            "public_event_ids": [],
            "private_event_ids": [],
            "known_roles": {"p1": "villager", "p2": "werewolf", "p3": "werewolf"},
        }
        proj = build_role_projection_snapshot(run_id="test", observation=obs_dict)
        roles = proj["projected_known_roles"]
        assert isinstance(roles, dict)
        self.assertEqual(roles.get("p1"), "villager")
        self.assertEqual(roles.get("p2"), "werewolf")
        self.assertEqual(roles.get("p3"), "werewolf")

    def test_god_snapshot_keeps_full_role_table(self) -> None:
        """god snapshot must preserve full player list without redaction."""
        players: list[dict] = [
            {"player_id": "p1", "role": "villager", "team": "villager"},
            {"player_id": "p2", "role": "werewolf", "team": "werewolf"},
        ]
        snap = build_god_snapshot(
            run_id="r1",
            game_id="g1",
            round=1,
            phase="night",
            players=players,
            alive_players=["p1", "p2"],
            public_event_ids=[],
            private_event_ids=[],
        )
        self.assertEqual(snap["run_id"], "r1")
        self.assertEqual(len(snap["players"]), 2)
        self.assertEqual(snap["snapshot_type"], "god")

    def test_prompt_manifest_contains_redaction_status_and_no_secret_values(self) -> None:
        """build_prompt_manifest must redact secrets and include prompt_hash."""
        agents: list[dict] = [
            {
                "player_id": "p1",
                "role": "villager",
                "prompt": "You are a villager. Vote wisely.",
                "provider": "fake",
            },
            {
                "player_id": "p2",
                "role": "werewolf",
                "prompt": "Your api_key is sk-leaked-value",
                "provider": "fake",
            },
        ]
        manifest = build_prompt_manifest(
            run_id="test", source_label="[test]", agents=agents
        )
        self.assertEqual(manifest["run_id"], "test")
        self.assertEqual(manifest["source_label"], "[test]")

        agent_entries = manifest["agents"]
        assert isinstance(agent_entries, list)
        self.assertEqual(len(agent_entries), 2)

        # First agent: has prompt_hash, no secrets.
        a0 = agent_entries[0]
        assert isinstance(a0, dict)
        self.assertIn("prompt_hash", a0)
        self.assertEqual(a0["player_id"], "p1")
        # Prompt text must NOT be in the output.
        self.assertNotIn("Vote wisely", str(manifest))

        # Second agent: secret value must be redacted.
        a1 = agent_entries[1]
        assert isinstance(a1, dict)
        self.assertIn("prompt_hash", a1)
        # The raw prompt containing "sk-leaked-value" was redacted — but the
        # hash was computed BEFORE redaction, so hash exists.
        self.assertIsInstance(a1["prompt_hash"], str)
        self.assertNotIn("sk-leaked", str(manifest))

    def test_role_projection_accepts_object_with_to_dict(self) -> None:
        """build_role_projection_snapshot must accept objects that have to_dict()."""
        class FakeObservation:
            def to_dict(self) -> dict:
                return {
                    "player_id": "p1",
                    "role": "seer",
                    "team": "villager",
                    "phase": "night",
                    "round": 1,
                    "alive_players": ["p1", "p2"],
                    "public_event_ids": [],
                    "private_event_ids": [],
                    "known_roles": {"p1": "seer", "p2": "werewolf"},
                }

        proj = build_role_projection_snapshot(run_id="test", observation=FakeObservation())
        roles = proj["projected_known_roles"]
        assert isinstance(roles, dict)
        self.assertEqual(roles["p2"], "unknown")

    def test_prompt_manifest_hashes_metadata_when_no_prompt(self) -> None:
        """When prompt text is absent, hash deterministic metadata fields."""
        agents: list[dict] = [
            {
                "player_id": "p3",
                "role": "seer",
                "provider": "deepseek",
                "model": "deepseek-chat",
            }
        ]
        manifest = build_prompt_manifest(
            run_id="test", source_label="[test]", agents=agents
        )
        entries = manifest["agents"]
        assert isinstance(entries, list)
        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, dict)
        self.assertIn("prompt_hash", entry)
        self.assertNotEqual(entry["prompt_hash"], "")
        # No prompt key in entry.
        self.assertNotIn("prompt", entry)

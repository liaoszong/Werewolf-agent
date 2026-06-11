"""Unit tests for the SSE streaming seam (SYS-C2 split).

``stream_run_events`` takes an injected sink + status/error callables, so frame
order, perspective filtering, and disconnect behavior are testable without a
socket. HTTP-level SSE behavior stays pinned by ``test_observer_server.py``.
"""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from werewolf_eval.observer.sse import stream_run_events
from werewolf_eval.observer_protocol import format_sse_event, format_sse_status


def _event(kind: str = "game_started", visibility: str = "public", seq: int = 0) -> dict[str, object]:
    return {
        "event_id": f"evt_{seq}_{kind}",
        "seq": seq,
        "kind": kind,
        "round": 0,
        "phase": "lobby",
        "actor": "system",
        "visibility": visibility,
        "ts": "2026-01-01T00:00:00Z",
    }


class _Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run_dir = Path(self._tmp.name) / "run1"
        self.run_dir.mkdir()

    def _write_events(self, events: list[dict[str, object]]) -> None:
        (self.run_dir / "events.jsonl").write_text(
            "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8"
        )

    def _stream(self, *, status: str = "completed", error: str | None = None) -> tuple[bytes, bool]:
        sink = io.BytesIO()
        should_close = stream_run_events(
            sink,
            run_id="run1",
            run_dir=self.run_dir,
            perspective="god",
            get_status=lambda: status,
            get_error=lambda: error,
            poll_interval=0.0,
        )
        return sink.getvalue(), should_close


class FrameOrderTests(_Fixture):
    def test_terminal_run_without_events_emits_two_status_frames(self) -> None:
        out, should_close = self._stream(status="completed")
        expected = format_sse_status("run1", "completed") + format_sse_status(
            "run1", "completed", None
        )
        self.assertEqual(out, expected)
        self.assertTrue(should_close)

    def test_events_framed_between_initial_and_final_status(self) -> None:
        events = [
            _event("game_started", "public", 0),
            _event("game_ended", "public", 1),
        ]
        self._write_events(events)
        out, should_close = self._stream(status="completed")
        expected = (
            format_sse_status("run1", "completed")
            + format_sse_event(events[0])
            + format_sse_event(events[1])
            + format_sse_status("run1", "completed", None)
        )
        self.assertEqual(out, expected)
        self.assertTrue(should_close)

    def test_final_status_carries_reason(self) -> None:
        out, _ = self._stream(status="failed", error="budget_exhausted")
        self.assertEqual(
            out,
            format_sse_status("run1", "failed")
            + format_sse_status("run1", "failed", "budget_exhausted"),
        )


class PerspectiveFilterTests(_Fixture):
    def test_hidden_events_are_skipped_but_counted(self) -> None:
        events = [
            _event("decision_made", "private", 0),
            _event("game_started", "public", 1),
        ]
        self._write_events(events)
        sink = io.BytesIO()
        stream_run_events(
            sink,
            run_id="run1",
            run_dir=self.run_dir,
            perspective="public",
            get_status=lambda: "completed",
            get_error=lambda: None,
            poll_interval=0.0,
        )
        out = sink.getvalue()
        self.assertNotIn(b"decision_made", out)
        self.assertIn(b"game_started", out)


class DisconnectTests(_Fixture):
    def test_broken_pipe_returns_false_without_raising(self) -> None:
        class _BrokenSink:
            def write(self, data: bytes) -> int:
                raise BrokenPipeError

            def flush(self) -> None:
                pass

        should_close = stream_run_events(
            _BrokenSink(),
            run_id="run1",
            run_dir=self.run_dir,
            perspective="god",
            get_status=lambda: "completed",
            get_error=lambda: None,
            poll_interval=0.0,
        )
        self.assertFalse(should_close)


if __name__ == "__main__":
    unittest.main()

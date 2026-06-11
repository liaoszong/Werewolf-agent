"""SSE event streaming for a run (SYS-C2 split).

``stream_run_events`` is transport-agnostic: it writes SSE frames to any
file-like sink and reads status/error through injected callables, so the frame
protocol is unit-testable without a socket. The HTTP handler owns the response
headers AND the ``close_connection`` flag — a ``True`` return means the stream
ended on the terminal-status path and the connection should be closed; ``False``
means the client disconnected (the historical path did NOT set
``close_connection`` there, so the wrapper must not either).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Protocol

from werewolf_eval.observer.run_manager import _read_events_jsonl_safe
from werewolf_eval.observer_protocol import (
    event_visible_to_perspective,
    format_sse_event,
    format_sse_status,
)


class _Sink(Protocol):
    def write(self, data: bytes) -> object: ...
    def flush(self) -> None: ...


def stream_run_events(
    wfile: _Sink,
    *,
    run_id: str,
    run_dir: Path,
    perspective: str,
    get_status: Callable[[], str],
    get_error: Callable[[], str | None],
    poll_interval: float,
) -> bool:
    """Serve an SSE event stream with live tailing of events.jsonl.

    Frame order: initial status frame → perspective-filtered event frames
    (``sent_count`` counts ALL events, including hidden ones) → on terminal
    status a final drain + final status frame (with the key-free reason).
    Returns True on the terminal-status path (caller should close), False when
    the client disconnected mid-stream."""
    sent_count = 0
    last_size = -1
    events_path = run_dir / "events.jsonl"

    def _read_new_events() -> list[dict[str, object]]:
        nonlocal sent_count, last_size
        # events.jsonl is append-only: skip the (whole-file) read+validate on idle
        # ticks where the file hasn't grown. Without this gate the SSE loop re-read +
        # re-validated the entire file every 100ms per connected client, forever
        # (O(file × clients × 10/s) — quadratic-ish on a long game). (risk appendix)
        try:
            size = events_path.stat().st_size
        except OSError:
            return []
        if size == last_size:
            return []
        last_size = size
        all_events = _read_events_jsonl_safe(events_path)
        new_events = all_events[sent_count:]
        return new_events

    try:
        status_sse = format_sse_status(run_id, get_status())
        wfile.write(status_sse)
        wfile.flush()

        while True:
            current_status = get_status()
            new_events = _read_new_events()
            for event in new_events:
                if event_visible_to_perspective(event, perspective):
                    wfile.write(format_sse_event(event))
                    wfile.flush()
                sent_count += 1

            if current_status not in ("queued", "running"):
                final_events = _read_new_events()
                for event in final_events:
                    if event_visible_to_perspective(event, perspective):
                        wfile.write(format_sse_event(event))
                        wfile.flush()
                    sent_count += 1
                final_sse = format_sse_status(run_id, current_status, get_error())
                wfile.write(final_sse)
                wfile.flush()
                return True

            time.sleep(poll_interval)
    except (BrokenPipeError, ConnectionResetError):
        return False
    except OSError:
        return False

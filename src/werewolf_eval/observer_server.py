"""Local observer HTTP server with live run state (G2a).

Provides a threaded HTTP server that serves run listings, events, snapshots,
SSE streaming, and asynchronous run launch.  All I/O is local-filesystem only.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

from werewolf_eval.observer_protocol import (
    ALLOWED_ARTIFACTS,
    ObserverProtocolError,
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
    safe_child_path,
    validate_run_id,
)
from werewolf_eval.run_g1h_fake_runtime import run_fake_runtime

RunLauncher = Callable[[str, Path], int]


def default_fake_launcher(run_id: str, run_dir: Path) -> int:
    return run_fake_runtime(game_id=run_id, out_dir=run_dir)


@dataclass
class ObserverServerState:
    runs_dir: Path
    launcher: RunLauncher
    run_status: dict[str, str] = field(default_factory=dict)
    run_errors: dict[str, str] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------


class ObserverRequestHandler(BaseHTTPRequestHandler):
    """Handles observer HTTP requests with JSON/SSE responses.

    Attach an ``ObserverServerState`` instance as ``server.state`` before
    starting the server.
    """

    _POLL_INTERVAL_S = 0.1
    _SSE_TICK_S = 0.1

    server: ThreadingHTTPServer

    # -- helpers -----------------------------------------------------------

    def _send_json(
        self, status: int, payload: dict[str, object] | list[object]
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_error_json(
        self, status: int, code: str, message: str
    ) -> None:
        self._send_json(status, {"code": code, "message": message})

    def _read_json_body(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            raise ObserverProtocolError("Empty request body")
        raw = self.rfile.read(content_length)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ObserverProtocolError(f"Invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ObserverProtocolError("Request body must be a JSON object")
        return data

    def _get_state(self) -> ObserverServerState:
        return self.server.state  # type: ignore[attr-defined]

    def _get_status(self, run_id: str, run_dir: Path) -> str:
        state = self._get_state()
        with state.lock:
            return state.run_status.get(run_id, "unknown")

    def _set_status(self, run_id: str, status: str) -> None:
        state = self._get_state()
        with state.lock:
            state.run_status[run_id] = status

    def _set_error(self, run_id: str, error: str) -> None:
        state = self._get_state()
        with state.lock:
            state.run_errors[run_id] = error

    def _run_dir(self, run_id: str) -> Path:
        validate_run_id(run_id)
        return self._get_state().runs_dir / run_id

    # -- URL helpers -------------------------------------------------------

    def _path_segments(self) -> list[str]:
        parsed = urlparse(self.path)
        return [seg for seg in parsed.path.split("/") if seg]

    def _query_perspective(self) -> str:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        raw = qs.get("perspective", ["god"])[0]
        return normalize_perspective(raw)

    # -- logging -----------------------------------------------------------

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Suppress default stderr logging."""
        pass

    # -- dispatch ----------------------------------------------------------

    def do_GET(self) -> None:
        segments = self._path_segments()
        try:
            if segments == ["health"]:
                self._send_json(200, {"status": "ok", "service": "werewolf-observer"})
                return

            if segments == ["api", "runs"]:
                state = self._get_state()
                dirs = list_run_dirs(state.runs_dir)
                runs: list[object] = []
                for d in dirs:
                    mem_status = self._get_status(d.name, d)
                    runs.append(build_run_summary(d, status=mem_status))
                self._send_json(200, {"runs": runs})
                return

            if len(segments) >= 3 and segments[0] == "api" and segments[1] == "runs":
                run_id = segments[2]
                run_dir = self._run_dir(run_id)
                if not run_dir.is_dir():
                    self._send_error_json(404, "not_found", f"Run not found: {run_id}")
                    return

                sub_path = segments[3:]
                perspective = self._query_perspective()

                if sub_path == ["events"]:
                    events_path = run_dir / "events.jsonl"
                    events = _read_events(events_path)
                    result = filter_events_for_perspective(events, perspective)
                    self._send_json(200, result)
                    return

                if sub_path == ["stream"]:
                    self._send_event_stream(run_id, run_dir, perspective)
                    return

                if sub_path == ["snapshots"]:
                    registry = build_snapshot_registry(run_dir, perspective)
                    self._send_json(200, {"snapshots": registry})
                    return

                if len(sub_path) >= 2 and sub_path[0] == "snapshots":
                    snapshot_name = sub_path[1]
                    try:
                        detail = load_snapshot_detail(
                            run_dir, snapshot_name, perspective
                        )
                    except ObserverProtocolError as exc:
                        if "cannot view" in str(exc):
                            self._send_error_json(
                                403, "snapshot_hidden", str(exc)
                            )
                        else:
                            self._send_error_json(404, "not_found", str(exc))
                        return
                    self._send_json(200, detail)
                    return

                # /api/runs/{run_id} with no sub-path -> run detail
                if not sub_path:
                    mem_status = self._get_status(run_id, run_dir)
                    detail = build_run_detail(run_dir, status=mem_status)
                    self._send_json(200, detail)
                    return

            # artifact aliases
            artifact_aliases: dict[str, str] = {
                "manifest": "prompt-manifest.json",
                "provider-trace": "provider-trace.json",
                "failure-audit": "failure-audit.json",
            }
            if len(segments) == 1 and segments[0] in artifact_aliases:
                artifact_name = artifact_aliases[segments[0]]
                # artifact aliases need a run context; require query param
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                run_id = qs.get("run_id", [None])[0]
                if not run_id:
                    self._send_error_json(
                        400, "missing_run_id", "run_id query parameter is required"
                    )
                    return
                run_dir = self._run_dir(run_id)
                if not run_dir.is_dir():
                    self._send_error_json(404, "not_found", f"Run not found: {run_id}")
                    return
                art_path = safe_child_path(run_dir, artifact_name)
                if not art_path.exists():
                    self._send_error_json(
                        404, "not_found", f"Artifact not found: {artifact_name}"
                    )
                    return
                self._send_artifact_file(art_path)
                return

            self._send_error_json(404, "not_found", "Not found")

        except ObserverProtocolError as exc:
            self._send_error_json(400, "invalid_request", str(exc))
        except Exception:
            self._send_error_json(500, "internal_error", "Internal server error")

    def do_POST(self) -> None:
        segments = self._path_segments()
        try:
            if segments == ["api", "runs"]:
                body = self._read_json_body()
                launch = parse_launch_request(body)
                run_id = launch["run_id"]
                run_dir = self._get_state().runs_dir / run_id
                if run_dir.exists():
                    self._send_error_json(
                        409, "conflict", f"Run already exists: {run_id}"
                    )
                    return
                run_dir.mkdir(parents=True)

                self._set_status(run_id, "queued")

                state = self._get_state()
                launcher = state.launcher

                def _run_thread() -> None:
                    self._set_status(run_id, "running")
                    try:
                        ret = launcher(run_id, run_dir)
                    except Exception as exc:
                        self._set_error(run_id, str(exc))
                        self._set_status(run_id, "failed")
                        return
                    if ret == 0:
                        self._set_status(run_id, "completed")
                    else:
                        self._set_error(run_id, f"Launcher returned code {ret}")
                        self._set_status(run_id, "failed")

                t = Thread(target=_run_thread, daemon=True)
                t.start()

                self._send_json(
                    202,
                    {
                        "run_id": run_id,
                        "template": launch["template"],
                        "mode": launch["mode"],
                        "status": "queued",
                    },
                )
                return

            self._send_error_json(404, "not_found", "Not found")

        except ObserverProtocolError as exc:
            self._send_error_json(400, "invalid_request", str(exc))
        except json.JSONDecodeError:
            self._send_error_json(400, "invalid_json", "Request body is not valid JSON")
        except Exception:
            self._send_error_json(500, "internal_error", "Internal server error")

    # -- artifact file serving ---------------------------------------------

    def _send_artifact_file(self, path: Path) -> None:
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # -- SSE stream --------------------------------------------------------

    def _send_event_stream(
        self, run_id: str, run_dir: Path, perspective: str
    ) -> None:
        """Serve an SSE event stream with live tailing of events.jsonl."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        sent_count = 0
        events_path = run_dir / "events.jsonl"

        def _read_new_events() -> list[dict[str, object]]:
            nonlocal sent_count
            all_events = _read_events(events_path)
            new_events = all_events[sent_count:]
            return new_events

        try:
            status_sse = format_sse_status(run_id, self._get_status(run_id, run_dir))
            self.wfile.write(status_sse)
            self.wfile.flush()

            while True:
                current_status = self._get_status(run_id, run_dir)
                new_events = _read_new_events()
                for event in new_events:
                    if event_visible_to_perspective(event, perspective):
                        self.wfile.write(format_sse_event(event))
                        self.wfile.flush()
                    sent_count += 1

                if current_status not in ("queued", "running"):
                    final_events = _read_new_events()
                    for event in final_events:
                        if event_visible_to_perspective(event, perspective):
                            self.wfile.write(format_sse_event(event))
                            self.wfile.flush()
                        sent_count += 1
                    final_sse = format_sse_status(run_id, current_status)
                    self.wfile.write(final_sse)
                    self.wfile.flush()
                    self.close_connection = True
                    return

                time.sleep(self._POLL_INTERVAL_S)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


def create_observer_server(
    host: str,
    port: int,
    runs_dir: Path,
    launcher: RunLauncher | None = None,
) -> ThreadingHTTPServer:
    """Create and configure a threaded observer HTTP server."""
    if launcher is None:
        launcher = default_fake_launcher
    runs_dir.mkdir(parents=True, exist_ok=True)

    state = ObserverServerState(runs_dir=runs_dir, launcher=launcher)

    class _BoundHandler(ObserverRequestHandler):
        pass

    server = ThreadingHTTPServer((host, port), _BoundHandler)
    server.state = state  # type: ignore[attr-defined]
    return server


# ---------------------------------------------------------------------------
# Event helpers
# ---------------------------------------------------------------------------


def _read_events(path: Path) -> list[dict[str, object]]:
    """Read all events from a JSONL file with retry for concurrent access."""
    if not path.exists():
        return []
    for _attempt in range(3):
        try:
            text = path.read_text(encoding="utf-8")
            break
        except OSError:
            time.sleep(0.05)
    else:
        return []
    events: list[dict[str, object]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            try:
                events.append(json.loads(stripped))
            except json.JSONDecodeError:
                pass
    return events

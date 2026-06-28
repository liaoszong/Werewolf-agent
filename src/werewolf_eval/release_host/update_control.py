"""Qt-session update control endpoint owned by the release host.

This is separate from the single-instance host-control endpoint. Qt gets a
short-lived update session id/token for this client launch only; it can request
check/download/apply, but only the host owns Velopack objects and apply rights.
"""
from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse


SCHEMA_VERSION = 1
DEFAULT_UPDATE_REPO_URL = "https://github.com/liaoszong/Werewolf-agent"


def new_update_session() -> tuple[str, str]:
    return secrets.token_hex(16), secrets.token_hex(32)


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _failure(code: str, message: str | None = None) -> dict:
    payload = {"schema_version": SCHEMA_VERSION, "ok": False, "code": code}
    if message:
        payload["message"] = message
    return payload


def _get_attr(obj: object, names: tuple[str, ...], default=None):
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            return value() if callable(value) and not isinstance(value, str) else value
    return default


def _target_asset(update_info: object) -> object | None:
    return _get_attr(
        update_info,
        (
            "target_full_release",
            "targetFullRelease",
            "TargetFullRelease",
            "target_asset",
            "TargetAsset",
        ),
    )


def _asset_version(asset: object | None) -> str:
    if asset is None:
        return ""
    value = _get_attr(asset, ("version", "Version"), "")
    return str(value or "")


def _asset_notes_markdown(asset: object | None) -> str:
    if asset is None:
        return ""
    value = _get_attr(
        asset,
        (
            "notes_markdown",
            "NotesMarkdown",
            "release_notes_markdown",
            "ReleaseNotesMarkdown",
        ),
        "",
    )
    return str(value or "")


@dataclass(frozen=True)
class UpdateSourceSpec:
    kind: str
    location: str


class VelopackSourceFactory:
    """Single source selector for production GitHub and spike-only local sources."""

    def __init__(self, spec: UpdateSourceSpec):
        self._spec = spec

    @property
    def kind(self) -> str:
        return self._spec.kind

    def create(self):
        if self._spec.kind == "local":
            return self._spec.location

        import velopack

        return velopack.GithubSource(DEFAULT_UPDATE_REPO_URL, None, False)


def create_update_source_factory(test_update_source: str | None = None) -> VelopackSourceFactory:
    if test_update_source:
        path = Path(test_update_source).expanduser().resolve(strict=True)
        if not path.is_dir():
            raise ValueError("velopack test update source must be a directory")
        if not ((path / "releases.win.json").is_file() or (path / "RELEASES").is_file()):
            raise ValueError("velopack test update source is missing release index")
        return VelopackSourceFactory(UpdateSourceSpec("local", str(path)))
    return VelopackSourceFactory(UpdateSourceSpec("github", DEFAULT_UPDATE_REPO_URL))


class VelopackUpdateBackend:
    """Thin runtime adapter around the Velopack Python binding."""

    def __init__(self, source_factory: VelopackSourceFactory):
        self._source_factory = source_factory
        self._manager = None
        self._update_info = None

    def _get_manager(self):
        if self._manager is None:
            import velopack

            source = self._source_factory.create()
            self._manager = velopack.UpdateManager(source)
        return self._manager

    def check_for_update(self) -> dict:
        manager = self._get_manager()
        update_info = manager.check_for_updates()
        if not update_info:
            self._update_info = None
            current = _get_attr(manager, ("get_current_version", "current_version"), "")
            return {
                "available": False,
                "current_version": str(current or ""),
                "target_version": "",
                "release_notes": "",
            }

        self._update_info = update_info
        asset = _target_asset(update_info)
        current = _get_attr(manager, ("get_current_version", "current_version"), "")
        return {
            "available": True,
            "current_version": str(current or ""),
            "target_version": _asset_version(asset),
            "release_notes": _asset_notes_markdown(asset),
        }

    def download_update(self, progress: Callable[[int], None]) -> dict:
        if self._update_info is None:
            raise RuntimeError("no update has been checked")

        manager = self._get_manager()

        def on_progress(value):
            try:
                progress(int(value))
            except (TypeError, ValueError):
                progress(0)

        manager.download_updates(self._update_info, on_progress)
        asset = _target_asset(self._update_info)
        return {
            "downloaded": True,
            "target_version": _asset_version(asset),
        }

    def apply_downloaded_update(self) -> dict:
        if self._update_info is None:
            raise RuntimeError("no downloaded update is available")
        manager = self._get_manager()
        manager.wait_exit_then_apply_updates(
            self._update_info, silent=True, restart=True, restart_args=None
        )
        return {"applying": True, "restart": True}


class UpdateState:
    def __init__(self):
        self.phase = "idle"
        self.current_version = ""
        self.target_version = ""
        self.release_notes = ""
        self.progress = 0
        self.error = ""
        self.error_detail = ""

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "release_notes": self.release_notes,
            "progress": self.progress,
            "error": self.error,
            "error_detail": self.error_detail,
        }


class UpdateControlServer:
    def __init__(
        self,
        *,
        backend,
        active_run_checker: Callable[[], bool],
        session_id: str,
        session_token: str,
    ):
        self._backend = backend
        self._active_run_checker = active_run_checker
        self._session_id = session_id
        self._session_token = session_token
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._state = UpdateState()
        self._apply_requested = False

    @property
    def port(self) -> int:
        if self._httpd is None:
            return 0
        return int(self._httpd.server_address[1])

    @property
    def apply_requested(self) -> bool:
        with self._lock:
            return self._apply_requested

    def _authorized(self, payload: dict) -> bool:
        return (
            payload.get("schema_version") == SCHEMA_VERSION
            and payload.get("session_id") == self._session_id
            and payload.get("session_token") == self._session_token
        )

    def _status_payload(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "status": self._state.to_dict(),
        }

    def _progress(self, value: int) -> None:
        with self._lock:
            self._state.progress = max(0, min(100, int(value)))
            self._state.phase = "downloading" if self._state.progress < 100 else "downloaded"

    def handle_action(self, action: str, payload: dict) -> tuple[int, dict]:
        if not self._authorized(payload):
            return 403, _failure("forbidden")
        if action not in {
            "check_for_update",
            "download_update",
            "apply_downloaded_update",
        }:
            return 404, _failure("unknown_update_action")

        try:
            if action == "check_for_update":
                result = self._backend.check_for_update()
                with self._lock:
                    self._state.error = ""
                    self._state.error_detail = ""
                    self._state.progress = 0
                    self._state.current_version = str(result.get("current_version", ""))
                    self._state.target_version = str(result.get("target_version", ""))
                    self._state.release_notes = str(result.get("release_notes", ""))
                    self._state.phase = "available" if result.get("available") else "current"
                return 200, self._status_payload()

            if action == "download_update":
                with self._lock:
                    self._state.error = ""
                    self._state.error_detail = ""
                    self._state.phase = "downloading"
                    self._state.progress = 0
                result = self._backend.download_update(self._progress)
                with self._lock:
                    self._state.error = ""
                    self._state.error_detail = ""
                    self._state.progress = 100
                    self._state.phase = "downloaded"
                    target = str(result.get("target_version", ""))
                    if target:
                        self._state.target_version = target
                return 200, self._status_payload()

            with self._lock:
                downloaded = self._state.phase == "downloaded"
            if not downloaded:
                with self._lock:
                    self._state.phase = "apply_blocked"
                    self._state.error = "update_not_downloaded"
                    self._state.error_detail = ""
                return 409, self._status_payload()

            if self._active_run_checker():
                with self._lock:
                    self._state.phase = "blocked_active_run"
                    self._state.error = "active_run_exists"
                    self._state.error_detail = ""
                return 409, self._status_payload()

            result = self._backend.apply_downloaded_update()
            with self._lock:
                self._apply_requested = bool(result.get("applying", True))
                self._state.error = ""
                self._state.error_detail = ""
                self._state.phase = "applying"
            return 200, self._status_payload()
        except Exception as exc:
            with self._lock:
                self._state.phase = "error"
                self._state.error = {
                    "check_for_update": "check_failed",
                    "download_update": "download_failed",
                    "apply_downloaded_update": "apply_failed",
                }.get(action, "update_failed")
                self._state.error_detail = exc.__class__.__name__
            return 500, self._status_payload()

    def handle_status(self, query: dict[str, list[str]]) -> tuple[int, dict]:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "session_id": (query.get("session_id") or [""])[0],
            "session_token": (query.get("session_token") or [""])[0],
        }
        if not self._authorized(payload):
            return 403, _failure("forbidden")
        return 200, self._status_payload()

    def start(self) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A002 - stdlib signature
                return

            def do_GET(self):  # noqa: N802 - stdlib hook
                parsed = urlparse(self.path)
                if parsed.path != "/update/status":
                    _json_response(self, 404, _failure("not_found"))
                    return
                status, body = owner.handle_status(parse_qs(parsed.query))
                _json_response(self, status, body)

            def do_POST(self):  # noqa: N802 - stdlib hook
                parsed = urlparse(self.path)
                action = parsed.path.removeprefix("/update/")
                length = int(self.headers.get("Content-Length", "0"))
                try:
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    _json_response(self, 400, _failure("invalid_request"))
                    return
                status, body = owner.handle_action(action, payload)
                _json_response(self, status, body)

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._httpd = None
        self._thread = None

    def __enter__(self) -> "UpdateControlServer":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()

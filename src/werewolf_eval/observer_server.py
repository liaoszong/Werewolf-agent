"""Local observer HTTP server with live run state (G2a).

Provides a threaded HTTP server that serves run listings, events, snapshots,
SSE streaming, and asynchronous run launch.  All I/O is local-filesystem only.
"""

from __future__ import annotations

import json
import re
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
    artifact_path,
    build_artifact_registry,
    build_run_detail,
    build_run_summary,
    build_runtime_capabilities,
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
    read_run_status,
    safe_child_path,
    validate_run_id,
    write_run_status,
)
from werewolf_eval.credential_store import CredentialStore
from werewolf_eval.observer_visibility import (
    VisibilityProjectionError,
    build_projection_envelope,
)
from werewolf_eval.profile_config import (
    ProfileValidationError,
    build_profile_schema,
    build_resolved_profile_artifact,
    list_profiles,
    load_profile,
    resolve_profile,
    validate_profile,
)
from werewolf_eval.run_g1h_fake_runtime import run_fake_runtime
from werewolf_eval.settlement_bundle import build_settlement_response
from werewolf_eval.runtime_events import (
    RuntimeEventError,
    read_events_jsonl,
    redact_secret_values,
)

RunLauncher = Callable[[str, Path], int]

_PROFILE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,255}$")


def default_fake_launcher(run_id: str, run_dir: Path) -> int:
    return run_fake_runtime(game_id=run_id, out_dir=run_dir)


@dataclass
class ObserverServerState:
    runs_dir: Path
    launcher: RunLauncher
    profiles_dir: Path = field(default_factory=lambda: Path("profiles"))
    run_status: dict[str, str] = field(default_factory=dict)
    run_errors: dict[str, str] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)
    # G3-1 live opt-in: ``live_enabled`` reflects ``--allow-live-api``;
    # ``live_launcher`` is wired only when an env API key was present at start.
    live_enabled: bool = False
    live_launcher: RunLauncher | None = None
    # P2-B-1 BYO-key: in-memory client credentials + a per-launch live launcher
    # factory (built from a key at launch). live_launcher above stays as the
    # prebuilt ENV launcher (back-compat / fallback); env_key_available records
    # whether the server started with an env key.
    credential_store: CredentialStore = field(default_factory=CredentialStore)
    live_launcher_factory: Callable[[str], RunLauncher] | None = None
    env_key_available: bool = False


def _resolve_live_launcher_for_launch(
    state: ObserverServerState,
) -> tuple[RunLauncher | None, tuple[int, str, str] | None]:
    """Pick the live launcher for THIS launch: a fresh one built from the client's
    in-memory key (preferred), else the prebuilt env launcher, else a 403. The key
    flows ONLY into the launcher closure (provider Authorization), never returned."""
    client_key = state.credential_store.get("deepseek")
    if client_key is not None and state.live_launcher_factory is not None:
        return state.live_launcher_factory(client_key), None
    if state.live_launcher is not None:
        return state.live_launcher, None
    return None, (403, "missing_api_key", "no DeepSeek credential is available")


def _check_live_capability(
    state: ObserverServerState, mode: str
) -> tuple[int, str, str] | None:
    """Capability gate for live launches — evaluated BEFORE the profile is
    loaded/validated, so an un-provisioned server rejects even a malformed or
    non-deepseek profile with a capability code (never ``invalid_profile`` or a
    shape error).  Returns ``(status, code, message)`` to reject, or ``None`` to
    proceed.  Non-live modes always proceed."""
    if mode != "live":
        return None
    if not state.live_enabled:
        return (403, "live_api_disabled", "live API is not enabled on this server")
    # BYO-key: a credential is available if the client synced one OR the server
    # started with an env key (back-compat). Prefer the legacy prebuilt launcher
    # signal when present so existing env-only deployments are unchanged.
    has_credential = (
        state.credential_store.has("deepseek")
        or state.env_key_available
        or state.live_launcher is not None
    )
    if not has_credential:
        return (403, "missing_api_key", "no DeepSeek credential is available (set one in the client)")
    return None


def _check_live_profile_shape(
    resolved_seats: list[dict],
) -> tuple[int, str, str] | None:
    """Shape gate for live launches — evaluated AFTER validation, only for live
    mode.  Provider check precedes the model check (gate order E before F).
    Returns ``(status, code, message)`` to reject, or ``None`` to proceed."""
    providers = {seat.get("provider") for seat in resolved_seats}
    if providers - {"deepseek"}:
        return (
            400,
            "unsupported_live_provider",
            "live launch requires every seat to use the deepseek provider",
        )
    models = {seat.get("model") for seat in resolved_seats}
    if len(models) > 1:
        return (
            400,
            "mixed_models",
            "live launch requires a single shared deepseek model",
        )
    return None


def _build_capabilities_payload(state: ObserverServerState) -> dict[str, object]:
    """Derive the read-only ``g3.runtime_capabilities.v1`` payload from the live
    capability gate.

    Posture comes ONLY from ``_check_live_capability(state, "live")`` (None ⇒
    available; tuple ⇒ the launch-time ``(status, reason_code, message)``), so
    the capabilities ``reason_code`` is identical to the launch-time 403 code.
    Read-only: no writes, no provider call, and never a secret."""
    reject = _check_live_capability(state, "live")
    if reject is None:
        return build_runtime_capabilities(
            live_enabled=state.live_enabled, deepseek_available=True
        )
    _status, reason_code, message = reject
    return build_runtime_capabilities(
        live_enabled=state.live_enabled,
        deepseek_available=False,
        reason_code=reason_code,
        message=message,
    )


# P2-B-1: credentials this slice accepts (deepseek-only; multi-provider is P2-B-3).
_CREDENTIAL_PROVIDERS: frozenset[str] = frozenset({"deepseek"})


def _credentials_post_result(
    store: "CredentialStore", content_type: str, body: dict[str, object]
) -> tuple[int, dict[str, object]]:
    """Pure logic for POST /api/credentials. NEVER returns or logs the key."""
    if str(content_type or "").split(";")[0].strip() != "application/json":
        return (415, {"error": "unsupported_media_type"})
    provider = body.get("provider")
    api_key = body.get("api_key")
    if not isinstance(provider, str) or provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    if not isinstance(api_key, str) or not api_key:
        return (400, {"error": "missing_api_key"})
    store.set(provider, api_key)
    return (200, {"stored": [provider]})


def _credentials_delete_result(
    store: "CredentialStore", provider: str
) -> tuple[int, dict[str, object]]:
    """Pure logic for DELETE /api/credentials/{provider}. Idempotent."""
    if provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    store.clear(provider)
    return (200, {"cleared": provider})


def _read_execution_mode(run_dir: Path) -> str | None:
    """Read ``execution_mode`` from the run's OWN ``resolved-profile.json``.

    Returns the string value when present, else ``None`` (missing/corrupt
    artifact, or a non-string value → the HUD chip conservatively falls back to
    ``SYS: SIMULATION``).  Guards JSON/OS errors, never raises, and never exposes
    a path.  This is a server-local file read, NOT a secret — the Qt client
    performs no file I/O and consumes this only as a run-detail JSON field."""
    path = run_dir / "resolved-profile.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(data, dict):
        value = data.get("execution_mode")
        if isinstance(value, str):
            return value
    return None


def _map_launcher_exit_reason(code: int) -> str:
    """Map a launcher exit code to a key-free run-status reason (G3-1, A7).

    The live deepseek launcher returns 3 when the request budget was exhausted
    and 2 on any other provider failure; both fail closed with no secret."""
    if code == 3:
        return "budget_exhausted"
    return "provider_failure"


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

    def _is_loopback(self) -> bool:
        host = self.client_address[0] if self.client_address else ""
        return host in ("127.0.0.1", "::1")

    def _get_status(self, run_id: str, run_dir: Path) -> str:
        state = self._get_state()
        with state.lock:
            if run_id in state.run_status:
                return state.run_status[run_id]
        # Not in memory (e.g. server restarted since the run finished) -> fall back to
        # the durable status.json so prior completed runs stay settleable.
        return read_run_status(run_dir)

    def _set_status(self, run_id: str, status: str) -> None:
        state = self._get_state()
        with state.lock:
            state.run_status[run_id] = status
        # Persist durably (outside the lock — file I/O) so the status survives a restart.
        write_run_status(state.runs_dir / run_id, status)

    def _set_error(self, run_id: str, error: str) -> None:
        state = self._get_state()
        with state.lock:
            state.run_errors[run_id] = error

    def _get_error(self, run_id: str) -> str | None:
        state = self._get_state()
        with state.lock:
            return state.run_errors.get(run_id)

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

            # G3-2 read-only live posture — no writes, no provider call, no
            # secret; reuses the G3-1 capability gate so reason_code == the
            # launch-time 403 code.
            if segments == ["api", "runtime", "capabilities"]:
                self._send_json(200, _build_capabilities_payload(self._get_state()))
                return

            if segments == ["api", "runs"]:
                state = self._get_state()
                dirs = list_run_dirs(state.runs_dir)
                runs: list[object] = []
                for d in dirs:
                    mem_status = self._get_status(d.name, d)
                    summary = build_run_summary(d, status=mem_status)
                    reason = self._get_error(d.name)
                    if reason is not None:
                        summary["reason"] = reason
                    runs.append(summary)
                self._send_json(200, {"runs": runs})
                return

            if segments == ["api", "profiles", "schema"]:
                self._send_json(200, build_profile_schema())
                return

            if segments == ["api", "profiles"]:
                profiles = list_profiles(self._get_state().profiles_dir)
                self._send_json(200, {"profiles": profiles})
                return

            if (
                len(segments) == 3
                and segments[:2] == ["api", "profiles"]
                and segments[2] != "schema"
            ):
                name = segments[2]
                if not _PROFILE_NAME_RE.match(name):
                    self._send_error_json(400, "invalid_request", "unsafe profile name")
                    return
                path = self._get_state().profiles_dir / f"{name}.json"
                if not path.exists():
                    self._send_error_json(404, "not_found", "profile not found")
                    return
                try:
                    data = load_profile(path)
                    validate_profile(data)
                except ProfileValidationError as exc:
                    self._send_error_json(400, "invalid_profile", str(exc))
                    return
                self._send_json(200, redact_secret_values(data))
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
                    events = _read_events_jsonl_safe(events_path)
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

                # /api/runs/{run_id}/projection (G2c God View / Role View)
                if sub_path == ["projection"]:
                    try:
                        events_path = run_dir / "events.jsonl"
                        events = _read_events_jsonl_safe(events_path)
                        envelope = build_projection_envelope(
                            run_dir=run_dir,
                            run_id=run_id,
                            perspective=perspective,
                            events=events,
                        )
                        self._send_json(200, envelope)
                    except VisibilityProjectionError as exc:
                        self._send_error_json(400, "invalid_perspective", str(exc))
                    return

                # /api/runs/{run_id} with no sub-path -> run detail
                if not sub_path:
                    detail = self._run_detail_with_reason(run_id, run_dir)
                    self._send_json(200, detail)
                    return

                # /api/runs/{run_id}/artifacts
                if sub_path == ["artifacts"]:
                    registry = build_artifact_registry(run_dir)
                    self._send_json(200, {"artifacts": registry})
                    return

                # /api/runs/{run_id}/settlement  (P2-D §6.2)
                if sub_path == ["settlement"]:
                    status = str(
                        self._run_detail_with_reason(run_id, run_dir).get("status", "")
                    )
                    try:
                        payload = build_settlement_response(run_dir, status, run_id)
                    except Exception:  # reason CODE, not an opaque 500 (P2-D fix)
                        self._send_error_json(
                            500, "settlement_failed", "Settlement build failed"
                        )
                        return
                    self._send_json(200, payload)
                    return

                # /api/runs/{run_id}/artifacts/{name}
                if len(sub_path) >= 2 and sub_path[0] == "artifacts":
                    art_name = sub_path[1]
                    try:
                        art_path = artifact_path(run_dir, art_name)
                    except ObserverProtocolError as exc:
                        self._send_error_json(400, "invalid_request", str(exc))
                        return
                    if not art_path.exists():
                        self._send_error_json(
                            404, "not_found", f"Artifact not found: {art_name}"
                        )
                        return
                    self._send_artifact_file(art_path)
                    return

                # artifact aliases under run path
                artifact_aliases: dict[str, str] = {
                    "manifest": "prompt-manifest.json",
                    "provider-trace": "provider-trace.json",
                    "failure-audit": "failure-audit.json",
                }
                if len(sub_path) == 1 and sub_path[0] in artifact_aliases:
                    art_name = artifact_aliases[sub_path[0]]
                    art_path = safe_child_path(run_dir, art_name)
                    if not art_path.exists():
                        self._send_error_json(
                            404, "not_found", f"Artifact not found: {art_name}"
                        )
                        return
                    self._send_artifact_file(art_path)
                    return

            self._send_error_json(404, "not_found", "Not found")

        except ObserverProtocolError as exc:
            self._send_error_json(400, "invalid_request", str(exc))
        except Exception:
            self._send_error_json(500, "internal_error", "Internal server error")

    def _execute_run(
        self, run_id: str, run_dir: Path, launcher: RunLauncher
    ) -> None:
        """Run *launcher* synchronously and record status + a key-free reason.

        Always records a canonical run-status reason on failure
        (``budget_exhausted``/``provider_failure``) — never raw exception text —
        because the reason is exposed via run detail/list/SSE (A7)."""
        self._set_status(run_id, "running")
        try:
            ret = launcher(run_id, run_dir)
        except Exception:  # noqa: BLE001
            self._set_error(run_id, "provider_failure")
            self._set_status(run_id, "failed")
            return
        if ret == 0:
            self._set_status(run_id, "completed")
        else:
            self._set_error(run_id, _map_launcher_exit_reason(ret))
            self._set_status(run_id, "failed")

    def _launch_run_async(
        self, run_id: str, run_dir: Path, launcher: RunLauncher
    ) -> None:
        self._set_status(run_id, "queued")
        Thread(
            target=self._execute_run, args=(run_id, run_dir, launcher), daemon=True
        ).start()

    def _run_detail_with_reason(self, run_id: str, run_dir: Path) -> dict[str, object]:
        """Build run detail and attach the key-free run-status reason (if any)
        plus the executed-truth ``execution_mode`` read from the run's OWN
        ``resolved-profile.json`` (G3-2).  ``execution_mode`` is the HUD chip's
        ONLY source of truth; it is omitted when no string value is present so
        the chip falls back to ``SYS: SIMULATION``."""
        mem_status = self._get_status(run_id, run_dir)
        detail = build_run_detail(run_dir, status=mem_status)
        reason = self._get_error(run_id)
        if reason is not None:
            detail["reason"] = reason
        execution_mode = _read_execution_mode(run_dir)
        if execution_mode is not None:
            detail["execution_mode"] = execution_mode
        return detail

    def _handle_profile_launch(self, body: dict[str, object]) -> None:
        plr = parse_profile_launch_request(body)
        state = self._get_state()
        mode = str(plr["mode"])

        # CAPABILITY gate (BEFORE load/validate) — live only.  Capability
        # precedes validity/shape: an un-provisioned server returns
        # live_api_disabled/missing_api_key even for a malformed or
        # non-deepseek profile, and never creates a run_dir.
        cap_reject = _check_live_capability(state, mode)
        if cap_reject is not None:
            self._send_error_json(*cap_reject)
            return

        if plr["kind"] == "named":
            ppath = state.profiles_dir / f"{plr['profile_name']}.json"
            if not ppath.exists():
                self._send_error_json(404, "not_found", "profile not found")
                return
            try:
                profile = load_profile(ppath)
            except ProfileValidationError as exc:
                self._send_error_json(400, "invalid_profile", str(exc))
                return
        else:
            profile = plr["profile"]  # type: ignore[assignment]
        try:
            validate_profile(profile)
        except ProfileValidationError as exc:
            self._send_error_json(400, "invalid_profile", str(exc))
            return

        # SHAPE gate (AFTER validate) — live only.
        if mode == "live":
            shape_reject = _check_live_profile_shape(resolve_profile(profile))
            if shape_reject is not None:
                self._send_error_json(*shape_reject)
                return

        run_id = str(plr["run_id"])
        run_dir = state.runs_dir / run_id
        if run_dir.exists():
            self._send_error_json(409, "conflict", f"Run already exists: {run_id}")
            return
        run_dir.mkdir(parents=True)

        is_live = mode == "live"
        if is_live:
            base, live_reject = _resolve_live_launcher_for_launch(state)
            if live_reject is not None:
                self._send_error_json(*live_reject)
                return
        else:
            base = state.launcher

        def _profile_launcher(
            rid: str,
            rdir: Path,
            base: RunLauncher = base,
            profile: dict = profile,
            is_live: bool = is_live,
        ) -> int:
            code = base(rid, rdir)
            artifact = build_resolved_profile_artifact(
                profile,
                rid,
                execution_mode="live" if is_live else "fake",
                live_api="used" if is_live else "not_used",
            )
            (rdir / "resolved-profile.json").write_text(
                json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            return code

        self._launch_run_async(run_id, run_dir, _profile_launcher)
        self._send_json(
            202,
            {
                "run_id": run_id,
                "profile_name": profile["name"],
                "mode": plr["mode"],
                "status": "queued",
            },
        )

    def do_DELETE(self) -> None:
        segments = self._path_segments()
        try:
            if len(segments) == 3 and segments[:2] == ["api", "credentials"]:
                if not self._is_loopback():
                    self._send_error_json(403, "forbidden", "credentials endpoint is loopback-only")
                    return
                status, payload = _credentials_delete_result(
                    self._get_state().credential_store, segments[2]
                )
                if status == 200:
                    self._send_json(200, payload)
                else:
                    self._send_error_json(status, str(payload.get("error", "bad_request")), "")
                return
            self._send_error_json(404, "not_found", "unknown endpoint")
        except ObserverProtocolError as exc:
            self._send_error_json(400, "bad_request", str(exc))
        except Exception:
            self._send_error_json(500, "internal_error", "Internal server error")

    def do_POST(self) -> None:
        segments = self._path_segments()
        try:
            if segments == ["api", "credentials"]:
                if not self._is_loopback():
                    self._send_error_json(403, "forbidden", "credentials endpoint is loopback-only")
                    return
                content_type = self.headers.get("Content-Type", "")
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 8192:
                    self._send_error_json(413, "payload_too_large", "credential body too large")
                    return
                raw = self.rfile.read(content_length) if content_length else b""
                try:
                    body = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    self._send_error_json(400, "invalid_json", "credential body must be JSON")
                    return
                if raw and not isinstance(body, dict):
                    self._send_error_json(400, "invalid_json", "credential body must be a JSON object")
                    return
                status, payload = _credentials_post_result(
                    self._get_state().credential_store, content_type, body
                )
                if status == 200:
                    self._send_json(200, payload)
                else:
                    self._send_error_json(status, str(payload.get("error", "bad_request")), "")
                return

            if segments == ["api", "runs"]:
                body = self._read_json_body()
                if "profile" in body or "profile_name" in body:
                    self._handle_profile_launch(body)
                    return
                launch = parse_launch_request(body)
                run_id = launch["run_id"]
                run_dir = self._get_state().runs_dir / run_id
                if run_dir.exists():
                    self._send_error_json(
                        409, "conflict", f"Run already exists: {run_id}"
                    )
                    return
                run_dir.mkdir(parents=True)
                self._launch_run_async(run_id, run_dir, self._get_state().launcher)
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

            if segments == ["api", "profiles", "validate"]:
                body = self._read_json_body()
                errors: list[str] = []
                resolved: list[dict[str, object]] = []
                try:
                    validate_profile(body)
                    resolved = resolve_profile(body)
                except ProfileValidationError as exc:
                    errors.append(str(exc))
                self._send_json(
                    200,
                    {"valid": not errors, "errors": errors, "resolved_seats": resolved},
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
                    final_sse = format_sse_status(
                        run_id, current_status, self._get_error(run_id)
                    )
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
    profiles_dir: Path | None = None,
    live_enabled: bool = False,
    live_launcher: RunLauncher | None = None,
) -> ThreadingHTTPServer:
    """Create and configure a threaded observer HTTP server.

    ``live_enabled``/``live_launcher`` wire the G3-1 opt-in live path: live is
    the only mode that consults them, and only a profile launch (not a template
    launch) may select it.  Both default off so the server stays fake-only."""
    if launcher is None:
        launcher = default_fake_launcher
    runs_dir.mkdir(parents=True, exist_ok=True)
    if profiles_dir is None:
        profiles_dir = runs_dir.parent / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    state = ObserverServerState(
        runs_dir=runs_dir,
        launcher=launcher,
        profiles_dir=profiles_dir,
        live_enabled=live_enabled,
        live_launcher=live_launcher,
    )

    class _BoundHandler(ObserverRequestHandler):
        pass

    server = ThreadingHTTPServer((host, port), _BoundHandler)
    server.state = state  # type: ignore[attr-defined]
    return server


# ---------------------------------------------------------------------------
# Event helpers
# ---------------------------------------------------------------------------


def _read_events_jsonl_safe(path: Path) -> list[dict[str, object]]:
    """Read events via ``read_events_jsonl`` with retry for concurrent access.

    Returns an empty list when the file does not exist or contains
    invalid/incomplete JSONL (e.g. while a launcher is writing).
    """
    if not path.exists():
        return []
    for _attempt in range(3):
        try:
            return read_events_jsonl(path)  # type: ignore[return-value]
        except (OSError, RuntimeEventError):
            time.sleep(0.05)
    return []

"""Observer HTTP request handler — protocol translation only (SYS-C2 split).

Dispatch is table-driven (``observer.routes``); business logic lives in
``run_manager``/``credentials_api``/``launch``/``sse``. The methods below that
look like plumbing are a FROZEN surface — do-not-touch test files subclass this
handler, override the response sinks (``_send_json``/``_send_error_json``),
the state accessor (``_get_state``), the guards (``_is_loopback``), the body
reader (``_read_json_body``) and the async-launch hook (``_launch_run_async``),
and call ``_handle_profile_launch``/``_execute_run``/``_get_status``/
``_get_error``/``_set_error``/``_run_detail_with_reason`` directly. Keep their
names, signatures, and call-chain positions.
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

from werewolf_eval.observer.credentials_api import (
    _credentials_delete_result,
    _credentials_post_result,
    _provider_models_result,
)
from werewolf_eval.observer.launch import execute_profile_launch
from werewolf_eval.observer.routes import (
    DELETE_ROUTES,
    GET_ROUTES,
    POST_ROUTES,
    RUN_SUB_ROUTES,
    Route,
    match_route,
)
from werewolf_eval.observer.run_manager import (
    RunManager,
    _build_capabilities_payload,
    _read_events_jsonl_safe,
    _schema_payload,
)
from werewolf_eval.observer.security import is_loopback_client, is_same_origin_local
from werewolf_eval.observer.sse import stream_run_events
from werewolf_eval.observer.state import ObserverServerState, RunLauncher
from werewolf_eval.observer_protocol import (
    ObserverProtocolError,
    artifact_path,
    build_artifact_registry,
    build_run_summary,
    build_snapshot_registry,
    filter_events_for_perspective,
    list_run_dirs,
    load_snapshot_detail,
    normalize_perspective,
    parse_launch_request,
    safe_child_path,
    validate_run_id,
)
from werewolf_eval.observer_visibility import (
    VisibilityProjectionError,
    build_projection_envelope,
)
from werewolf_eval.profile_config import (
    ProfileValidationError,
    list_profiles,
    load_profile,
    resolve_profile,
    validate_profile,
)
from werewolf_eval.runtime_events import redact_secret_values
from werewolf_eval.settlement_bundle import build_settlement_response
from werewolf_eval.user_config_library import (
    UserConfigError,
    export_user_config,
    import_user_config,
    list_user_configs,
    load_user_config,
    save_user_config,
)

_PROFILE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,255}$")

# artifact aliases under the run path
_ARTIFACT_ALIASES: dict[str, str] = {
    "manifest": "prompt-manifest.json",
    "provider-trace": "provider-trace.json",
    "failure-audit": "failure-audit.json",
}


class ObserverRequestHandler(BaseHTTPRequestHandler):
    """Handles observer HTTP requests with JSON/SSE responses.

    Attach an ``ObserverServerState`` instance as ``server.state`` before
    starting the server.
    """

    _POLL_INTERVAL_S = 0.1
    _SSE_TICK_S = 0.1

    server: ThreadingHTTPServer

    # -- helpers (FROZEN surface — see module docstring) ---------------------

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
        return is_loopback_client(host)

    def _is_same_origin_local(self) -> bool:
        """True when a state-changing request is safe to honour (loopback Host,
        loopback-or-absent Origin) — see ``observer.security.is_same_origin_local``."""
        return is_same_origin_local(self.headers)

    def _reject_cross_origin(self) -> bool:
        """Guard for state-changing endpoints (credential writes, run launches).
        Sends a 403 and returns True when the request must be rejected for a
        DNS-rebind / cross-origin reason; returns False to proceed."""
        if not self._is_same_origin_local():
            self._send_error_json(403, "forbidden", "cross-origin or non-loopback Host rejected")
            return True
        return False

    def _run_manager(self) -> RunManager:
        return RunManager(self._get_state())

    def _get_status(self, run_id: str, run_dir: Path) -> str:
        return self._run_manager().get_status(run_id, run_dir)

    def _set_status(self, run_id: str, status: str) -> None:
        self._run_manager().set_status(run_id, status)

    def _set_error(self, run_id: str, error: str) -> None:
        self._run_manager().set_error(run_id, error)

    def _get_error(self, run_id: str) -> str | None:
        return self._run_manager().get_error(run_id)

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

    def _dispatch(self, routes: tuple[Route, ...], fallback_message: str) -> None:
        """Table dispatch. Guards are translated into the OVERRIDABLE methods
        ``self._is_loopback()`` / ``self._reject_cross_origin()`` — never into
        direct pure-function calls (tests override the methods)."""
        segments = self._path_segments()
        matched = match_route(routes, segments)
        if matched is None:
            self._send_error_json(404, "not_found", fallback_message)
            return
        route, params = matched
        if route.loopback_message is not None and not self._is_loopback():
            self._send_error_json(403, "forbidden", route.loopback_message)
            return
        if route.same_origin and self._reject_cross_origin():
            return
        getattr(self, route.handler_name)(params)

    def do_GET(self) -> None:
        try:
            self._dispatch(GET_ROUTES, "Not found")
        except ObserverProtocolError as exc:
            self._send_error_json(400, "invalid_request", str(exc))
        except Exception:
            self._send_error_json(500, "internal_error", "Internal server error")

    def do_POST(self) -> None:
        try:
            self._dispatch(POST_ROUTES, "Not found")
        except ObserverProtocolError as exc:
            self._send_error_json(400, "invalid_request", str(exc))
        except json.JSONDecodeError:
            self._send_error_json(400, "invalid_json", "Request body is not valid JSON")
        except Exception:
            self._send_error_json(500, "internal_error", "Internal server error")

    def do_DELETE(self) -> None:
        try:
            self._dispatch(DELETE_ROUTES, "unknown endpoint")
        except ObserverProtocolError as exc:
            self._send_error_json(400, "bad_request", str(exc))
        except Exception:
            self._send_error_json(500, "internal_error", "Internal server error")

    # -- GET endpoints -------------------------------------------------------

    def _route_health(self, params: dict[str, str]) -> None:
        self._send_json(200, {"status": "ok", "service": "werewolf-observer"})

    def _route_capabilities(self, params: dict[str, str]) -> None:
        # G3-2 read-only live posture — no writes, no provider call, no
        # secret; reuses the G3-1 capability gate so reason_code == the
        # launch-time 403 code.
        self._send_json(200, _build_capabilities_payload(self._get_state()))

    def _route_runs_list(self, params: dict[str, str]) -> None:
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

    def _route_profile_schema(self, params: dict[str, str]) -> None:
        self._send_json(200, _schema_payload())

    def _route_provider_models(self, params: dict[str, str]) -> None:
        # P2-B-1 r2: dynamic model discovery for a configured provider.
        # Loopback-only (it uses the session credential), like /api/credentials.
        status, payload = _provider_models_result(
            self._get_state().credential_store, params["provider"]
        )
        if status == 200:
            self._send_json(200, payload)
        else:
            self._send_error_json(status, str(payload.get("error", "bad_request")), "")

    def _route_profiles_list(self, params: dict[str, str]) -> None:
        profiles = list_profiles(self._get_state().profiles_dir)
        self._send_json(200, {"profiles": profiles})

    def _route_configs_list(self, params: dict[str, str]) -> None:
        configs = list_user_configs(self._get_state().configs_dir)
        self._send_json(200, {"configs": configs})

    def _route_config_detail(self, params: dict[str, str]) -> None:
        try:
            payload = load_user_config(self._get_state().configs_dir, params["config_id"])
        except UserConfigError as exc:
            self._send_user_config_error(exc)
            return
        self._send_json(200, redact_secret_values(payload))

    def _route_config_export(self, params: dict[str, str]) -> None:
        try:
            payload = export_user_config(self._get_state().configs_dir, params["config_id"])
        except UserConfigError as exc:
            self._send_user_config_error(exc)
            return
        self._send_json(200, redact_secret_values(payload))

    def _route_profile_detail(self, params: dict[str, str]) -> None:
        name = params["name"]
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

    # -- GET run group --------------------------------------------------------

    def _route_run_scoped(self, params: dict[str, str]) -> None:
        """Run group prelude (historical block structure): validate run_id
        (raises → 400), missing dir → 404 ``Run not found: {id}``, perspective
        parsed BEFORE sub-dispatch (a bad perspective 400s on every sub-path),
        then the sub-table; no sub-match falls through to 404 ``Not found``."""
        run_id = params["run_id"]
        run_dir = self._run_dir(run_id)
        if not run_dir.is_dir():
            self._send_error_json(404, "not_found", f"Run not found: {run_id}")
            return

        sub_path = self._path_segments()[3:]
        perspective = self._query_perspective()

        matched = match_route(RUN_SUB_ROUTES, sub_path)
        if matched is None:
            self._send_error_json(404, "not_found", "Not found")
            return
        route, sub_params = matched
        getattr(self, route.handler_name)(run_id, run_dir, perspective, sub_path, sub_params)

    def _route_run_events(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        events_path = run_dir / "events.jsonl"
        events = _read_events_jsonl_safe(events_path)
        result = filter_events_for_perspective(events, perspective)
        self._send_json(200, result)

    def _route_run_stream(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        self._send_event_stream(run_id, run_dir, perspective)

    def _route_run_snapshots(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        registry = build_snapshot_registry(run_dir, perspective)
        self._send_json(200, {"snapshots": registry})

    def _route_run_snapshot_detail(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        snapshot_name = params["name"]
        try:
            detail = load_snapshot_detail(run_dir, snapshot_name, perspective)
        except ObserverProtocolError as exc:
            if "cannot view" in str(exc):
                self._send_error_json(403, "snapshot_hidden", str(exc))
            else:
                self._send_error_json(404, "not_found", str(exc))
            return
        self._send_json(200, detail)

    def _route_run_projection(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        # /api/runs/{run_id}/projection (G2c God View / Role View)
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

    def _route_run_detail(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        # /api/runs/{run_id} with no sub-path -> run detail
        detail = self._run_detail_with_reason(run_id, run_dir)
        self._send_json(200, detail)

    def _route_run_artifacts(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        registry = build_artifact_registry(run_dir)
        self._send_json(200, {"artifacts": registry})

    def _route_run_settlement(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        # /api/runs/{run_id}/settlement  (P2-D §6.2)
        status = str(self._run_detail_with_reason(run_id, run_dir).get("status", ""))
        try:
            payload = build_settlement_response(run_dir, status, run_id)
        except Exception:  # reason CODE, not an opaque 500 (P2-D fix)
            self._send_error_json(500, "settlement_failed", "Settlement build failed")
            return
        self._send_json(200, payload)

    def _route_run_artifact_detail(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        # /api/runs/{run_id}/artifacts/{name}
        art_name = params["name"]
        try:
            art_path = artifact_path(run_dir, art_name)
        except ObserverProtocolError as exc:
            self._send_error_json(400, "invalid_request", str(exc))
            return
        if not art_path.exists():
            self._send_error_json(404, "not_found", f"Artifact not found: {art_name}")
            return
        self._send_artifact_file(art_path)

    def _route_run_artifact_alias(
        self, run_id: str, run_dir: Path, perspective: str,
        sub_path: list[str], params: dict[str, str],
    ) -> None:
        art_name = _ARTIFACT_ALIASES[sub_path[0]]
        art_path = safe_child_path(run_dir, art_name)
        if not art_path.exists():
            self._send_error_json(404, "not_found", f"Artifact not found: {art_name}")
            return
        self._send_artifact_file(art_path)

    # -- run execution (FROZEN surface) --------------------------------------

    def _execute_run(
        self, run_id: str, run_dir: Path, launcher: RunLauncher
    ) -> None:
        """Run *launcher* synchronously and record status + a key-free reason —
        see ``RunManager.execute_run`` (A7: canonical reasons, never raw text)."""
        self._run_manager().execute_run(run_id, run_dir, launcher)

    def _launch_run_async(
        self, run_id: str, run_dir: Path, launcher: RunLauncher
    ) -> None:
        self._set_status(run_id, "queued")
        Thread(
            target=self._execute_run, args=(run_id, run_dir, launcher), daemon=True
        ).start()

    def _run_detail_with_reason(self, run_id: str, run_dir: Path) -> dict[str, object]:
        """Run detail + key-free reason + executed-truth ``execution_mode`` —
        see ``RunManager.run_detail_with_reason`` (G3-2)."""
        return self._run_manager().run_detail_with_reason(run_id, run_dir)

    def _handle_profile_launch(self, body: dict[str, object]) -> None:
        """Profile launch — gate sequence + side effects live in
        ``observer.launch.execute_profile_launch``; this shell only translates
        the outcome (error → ``_send_error_json``; launch → dispatch through
        ``self._launch_run_async`` then the 202)."""
        outcome = execute_profile_launch(self._get_state(), body)
        if outcome[0] == "error":
            _, status, code, message = outcome
            self._send_error_json(status, code, message)  # type: ignore[arg-type]
            return
        _, run_id, run_dir, launcher, payload = outcome
        self._launch_run_async(run_id, run_dir, launcher)  # type: ignore[arg-type]
        self._send_json(202, payload)  # type: ignore[arg-type]

    # -- DELETE endpoints ------------------------------------------------------

    def _route_credentials_delete(self, params: dict[str, str]) -> None:
        status, payload = _credentials_delete_result(
            self._get_state().credential_store, params["provider"]
        )
        if status == 200:
            self._send_json(200, payload)
        else:
            self._send_error_json(status, str(payload.get("error", "bad_request")), "")

    def _route_runs_delete(self, params: dict[str, str]) -> None:
        run_id = params["run_id"]
        run_dir = self._run_dir(run_id)          # validate_run_id -> raises on illegal id
        # memory-first status read, delete decision, in-memory eviction
        code, payload = self._run_manager().delete_run(run_id, run_dir)
        if code == 200:
            self._send_json(200, payload)
        else:
            self._send_error_json(code, str(payload.get("error", "bad_request")),
                                  str(payload.get("detail", "")))

    # -- POST endpoints ----------------------------------------------------------

    def _route_runs_interrupt(self, params: dict[str, str]) -> None:
        run_id = params["run_id"]
        run_dir = self._run_dir(run_id)          # validate_run_id -> raises on illegal id
        code, payload = self._run_manager().interrupt_run(run_id, run_dir)
        if code == 200:
            self._send_json(200, payload)
        else:
            self._send_error_json(code, str(payload.get("error", "bad_request")),
                                  str(payload.get("detail", "")))

    def _route_credentials_post(self, params: dict[str, str]) -> None:
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

    def _route_runs_post(self, params: dict[str, str]) -> None:
        body = self._read_json_body()
        if "profile" in body or "profile_name" in body:
            self._handle_profile_launch(body)
            return
        launch = parse_launch_request(body)
        run_id = launch["run_id"]
        run_dir = self._get_state().runs_dir / run_id
        if run_dir.exists():
            self._send_error_json(409, "conflict", f"Run already exists: {run_id}")
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

    def _route_profile_validate(self, params: dict[str, str]) -> None:
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

    def _route_configs_post(self, params: dict[str, str]) -> None:
        body = self._read_json_body()
        profile = body.get("profile")
        if not isinstance(profile, dict):
            self._send_error_json(400, "invalid_profile", "config profile must be a JSON object")
            return
        try:
            item = save_user_config(
                self._get_state().configs_dir,
                display_name=str(body.get("display_name", "")),
                profile=profile,
                script_id=body.get("script_id") if isinstance(body.get("script_id"), str) else None,
                base_profile=body.get("base_profile") if isinstance(body.get("base_profile"), str) else None,
            )
        except UserConfigError as exc:
            self._send_user_config_error(exc)
            return
        self._send_json(201, item)

    def _route_configs_import(self, params: dict[str, str]) -> None:
        body = self._read_json_body()
        try:
            item = import_user_config(self._get_state().configs_dir, body)
        except UserConfigError as exc:
            self._send_user_config_error(exc)
            return
        self._send_json(201, item)

    def _send_user_config_error(self, exc: UserConfigError) -> None:
        status_by_code = {
            "config_not_found": 404,
            "config_write_failed": 500,
            "config_import_failed": 400,
            "invalid_config_file": 400,
            "unsupported_config_version": 400,
            "secret_detected": 400,
            "invalid_profile": 400,
            "config_name_required": 400,
        }
        self._send_error_json(status_by_code.get(exc.code, 400), exc.code, str(exc))

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
        """Serve an SSE event stream — headers + close_connection here, frame
        protocol in ``observer.sse.stream_run_events``."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        should_close = stream_run_events(
            self.wfile,
            run_id=run_id,
            run_dir=run_dir,
            perspective=perspective,
            get_status=lambda: self._get_status(run_id, run_dir),
            get_error=lambda: self._get_error(run_id),
            poll_interval=self._POLL_INTERVAL_S,
        )
        if should_close:
            self.close_connection = True

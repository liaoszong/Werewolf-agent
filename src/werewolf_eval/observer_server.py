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
from werewolf_eval.deepseek_launcher import build_multi_provider_launcher
from werewolf_eval.llm_providers import ChatProviderConfig
from werewolf_eval.provider_registry import PROVIDER_REGISTRY, list_models, provider_specs_payload
from werewolf_eval.seat_agents import ProviderCredential
from werewolf_eval.observer_visibility import (
    VisibilityProjectionError,
    build_projection_envelope,
)
from werewolf_eval.profile_config import (
    ProfileValidationError,
    build_default_profile,
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
    # P2-B-3/B-4: per-seat multi-provider launcher builder. Given the resolved
    # seats + a {provider: ProviderCredential} map, returns a RunLauncher that runs
    # the game with each seat on its own provider/model/persona. Injectable so
    # tests can pass a fake (no network); built with the server live limits in
    # create_observer_server.
    multi_provider_launcher_factory: Callable[..., RunLauncher] | None = None


def _resolve_live_launcher_for_launch(
    state: ObserverServerState,
    resolved_seats: list[dict],
) -> tuple[RunLauncher | None, tuple[int, str, str] | None]:
    """Pick the live launcher for THIS launch. P2-B-4 multi-provider:

    1. If EVERY provider used by the seats has a client credential → a per-seat
       multi-provider launcher (the general path; handles mixed and single-provider).
    2. Back-compat deepseek-only: client deepseek key via the single-key factory,
       else the prebuilt env launcher.
    3. No silent fallback: a seat whose provider lacks a credential → 403.

    Keys flow ONLY into the launcher closures (provider Authorization), never
    returned."""
    used = {str(seat.get("provider")) for seat in resolved_seats}
    creds: dict[str, ProviderCredential] = {}
    missing: list[str] = []
    for provider in sorted(used):
        key = state.credential_store.get(provider)
        if key:
            creds[provider] = ProviderCredential(
                key=key, base_url=state.credential_store.get_base_url(provider) or ""
            )
        else:
            missing.append(provider)

    if not missing and state.multi_provider_launcher_factory is not None:
        return state.multi_provider_launcher_factory(resolved_seats, creds), None
    # Back-compat (deepseek-only) paths. The legacy launchers run ONE shared model
    # for all seats, so they may only serve a UNIFORM profile (single provider +
    # single model); a mixed-model deepseek profile must go through the multi
    # launcher above (per-seat) to avoid resolved-profile.json claiming models the
    # run never used.
    uniform = len({(str(s.get("provider")), str(s.get("model"))) for s in resolved_seats}) == 1
    if used == {"deepseek"} and uniform and "deepseek" in creds and state.live_launcher_factory is not None:
        return state.live_launcher_factory(creds["deepseek"].key), None
    if used == {"deepseek"} and uniform and state.live_launcher is not None:
        return state.live_launcher, None
    if missing:
        return None, (
            403,
            "missing_provider_credential",
            f"no credential for provider(s): {', '.join(sorted(set(missing)))}",
        )
    return None, (403, "missing_api_key", "no live credential is available")


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
    # BYO-key: a credential is available if the client synced ANY supported
    # provider key OR the server started with an env key (back-compat). This is a
    # COARSE gate; the per-seat credential check happens at launcher resolution.
    has_credential = (
        any(state.credential_store.has(p) for p in PROVIDER_REGISTRY)
        or state.env_key_available
        or state.live_launcher is not None
    )
    if not has_credential:
        return (403, "missing_api_key", "no live credential is available (set one in the client)")
    return None


def _check_live_profile_shape(
    resolved_seats: list[dict],
) -> tuple[int, str, str] | None:
    """Shape gate for live launches — evaluated AFTER validation, only for live
    mode.  P2-B-3: every seat's provider must be a SUPPORTED live provider (in the
    registry); ``fake_deterministic`` and unknown providers are rejected. Mixed
    providers AND mixed models are now allowed (that is the multi-provider feature)
    — the per-seat credential requirement is enforced at launcher resolution.
    Returns ``(status, code, message)`` to reject, or ``None`` to proceed."""
    providers = {seat.get("provider") for seat in resolved_seats}
    unsupported = providers - set(PROVIDER_REGISTRY)
    if unsupported:
        return (
            400,
            "unsupported_live_provider",
            f"live launch does not support provider(s): {', '.join(sorted(str(p) for p in unsupported))}",
        )
    return None


def _provider_live_posture(
    state: ObserverServerState, provider: str
) -> tuple[bool, str | None, str | None]:
    """Per-provider live posture for the capabilities payload.

    Mirrors ``_check_live_capability`` but scoped to ONE provider so the HUD /
    arming control can report which providers are actually usable (the head
    feature: each seat may pick a different AI).  Reason CODES are identical to
    the launch-time 403 codes:

    * live disabled (global) → ``live_api_disabled`` for every provider.
    * live enabled but this provider has no credential → ``missing_api_key``.
      ``deepseek`` additionally counts the legacy env key / prebuilt env launcher
      (back-compat); other providers are credential-only.

    Never reads or returns a secret."""
    if not state.live_enabled:
        return (False, "live_api_disabled", "live API is not enabled on this server")
    has_credential = state.credential_store.has(provider)
    if provider == "deepseek":
        has_credential = (
            has_credential or state.env_key_available or state.live_launcher is not None
        )
    if has_credential:
        return (True, None, None)
    return (
        False,
        "missing_api_key",
        f"no credential is available for {provider} (set one in the client)",
    )


def _schema_payload() -> dict[str, object]:
    """The profile-schema response: the pure validation schema plus the
    registry-derived provider UI metadata (kept here so profile_config stays
    registry-free)."""
    schema = build_profile_schema()
    schema["provider_specs"] = provider_specs_payload()
    return schema


def _build_capabilities_payload(state: ObserverServerState) -> dict[str, object]:
    """Derive the read-only ``g3.runtime_capabilities.v1`` payload from the live
    capability gate, one entry per registered provider.

    Each provider's posture comes from ``_provider_live_posture`` so the
    ``reason_code`` matches the launch-time 403 code.  The aggregate "is live
    available at all" (any provider available) equals ``_check_live_capability``
    proceeding — the client derives that by OR-ing the per-provider ``available``
    flags.  Read-only: no writes, no provider call, and never a secret."""
    providers: dict[str, dict[str, object]] = {}
    for provider in PROVIDER_REGISTRY:
        available, reason_code, message = _provider_live_posture(state, provider)
        info: dict[str, object] = {"available": available}
        if not available:
            info["reason_code"] = reason_code
            info["message"] = message
        providers[provider] = info
    return build_runtime_capabilities(
        live_enabled=state.live_enabled, providers=providers
    )


# P2-B-1 r2: credential writes now accept every registry provider (the single
# source of truth). Custom OpenAI-compatible endpoints additionally require a
# base_url. (The live-launch GATE that requires a credential per seat is P2-B-4.)
_CREDENTIAL_PROVIDERS: frozenset[str] = frozenset(PROVIDER_REGISTRY)


def _credentials_post_result(
    store: "CredentialStore", content_type: str, body: dict[str, object]
) -> tuple[int, dict[str, object]]:
    """Pure logic for POST /api/credentials. NEVER returns or logs the key."""
    if str(content_type or "").split(";")[0].strip() != "application/json":
        return (415, {"error": "unsupported_media_type"})
    provider = body.get("provider")
    api_key = body.get("api_key")
    base_url = body.get("base_url", "")
    if not isinstance(provider, str) or provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    if not isinstance(api_key, str) or not api_key:
        return (400, {"error": "missing_api_key"})
    if not isinstance(base_url, str):
        return (400, {"error": "invalid_base_url"})
    # Only http(s) endpoints are fetchable; reject file://, gopher://, schemeless,
    # etc. (localhost/private hosts are intentionally allowed — local model servers
    # like Ollama/LM Studio are a first-class BYO-key use case).
    if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
        return (400, {"error": "invalid_base_url"})
    if PROVIDER_REGISTRY[provider].requires_base_url and not base_url:
        return (400, {"error": "missing_base_url"})
    store.set(provider, api_key, base_url)
    return (200, {"stored": [provider]})


def _credentials_delete_result(
    store: "CredentialStore", provider: str
) -> tuple[int, dict[str, object]]:
    """Pure logic for DELETE /api/credentials/{provider}. Idempotent."""
    if provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    store.clear(provider)
    return (200, {"cleared": provider})


def _provider_models_result(
    store: "CredentialStore", provider: str, transport=None
) -> tuple[int, dict[str, object]]:
    """Pure logic for GET /api/providers/{provider}/models. Fetches the live model
    list from the provider using the session credential. NEVER returns or logs the
    key; upstream failures collapse to a sanitized code."""
    if provider not in _CREDENTIAL_PROVIDERS:
        return (400, {"error": "unsupported_provider"})
    key = store.get(provider)
    if not key:
        return (403, {"error": "missing_api_key"})
    base_url = store.get_base_url(provider) or ""
    config = ChatProviderConfig(api_key=key, base_url=base_url)
    try:
        models = list_models(provider, config, transport=transport)
    except Exception:
        # Never surface the upstream message (could carry url/auth); fail closed.
        return (502, {"error": "provider_unavailable"})
    return (200, {"provider": provider, "models": models})


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


def _sanitize_launcher_error(exc: BaseException) -> str:
    """Map a launcher EXCEPTION to a key-free canonical reason. Inspects only the
    exception CLASS and a lowercased 'is this auth?' check on the type/args — never
    embeds the message (which could carry an Authorization header / key / url)."""
    text = f"{type(exc).__name__} {exc}".lower()
    if "401" in text or "unauthor" in text or "forbidden" in text or "invalid api key" in text:
        return "provider_auth_failed"
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
                self._send_json(200, _schema_payload())
                return

            # P2-B-1 r2: dynamic model discovery for a configured provider.
            # Loopback-only (it uses the session credential), like /api/credentials.
            if (
                len(segments) == 4
                and segments[:2] == ["api", "providers"]
                and segments[3] == "models"
            ):
                if not self._is_loopback():
                    self._send_error_json(403, "forbidden", "providers endpoint is loopback-only")
                    return
                status, payload = _provider_models_result(
                    self._get_state().credential_store, segments[2]
                )
                if status == 200:
                    self._send_json(200, payload)
                else:
                    self._send_error_json(status, str(payload.get("error", "bad_request")), "")
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
        except Exception as exc:  # noqa: BLE001
            self._set_error(run_id, _sanitize_launcher_error(exc))
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

        # SHAPE gate (AFTER validate) — live only. Resolve seats once and reuse
        # for the launcher resolution (per-seat credential check).
        resolved_seats: list[dict] = []
        if mode == "live":
            resolved_seats = resolve_profile(profile)
            shape_reject = _check_live_profile_shape(resolved_seats)
            if shape_reject is not None:
                self._send_error_json(*shape_reject)
                return

        run_id = str(plr["run_id"])
        run_dir = state.runs_dir / run_id
        if run_dir.exists():
            self._send_error_json(409, "conflict", f"Run already exists: {run_id}")
            return

        is_live = mode == "live"
        if is_live:
            base, live_reject = _resolve_live_launcher_for_launch(state, resolved_seats)
            if live_reject is not None:
                self._send_error_json(*live_reject)
                return
        else:
            base = state.launcher
        run_dir.mkdir(parents=True)

        # Write the resolved-profile (which carries execution_mode) SYNCHRONOUSLY here,
        # before the async run starts and before the 202 returns. The artifact is built
        # entirely from launch-time inputs, so the content is identical to writing it
        # after the run — but writing it up front means the client's immediate openRun
        # finds execution_mode, so the HUD shows the real live/fake posture DURING the
        # run (the run-detail execution_mode is read from this file), not only after it
        # completes. Previously it was written in the launcher thread, which raced the
        # client's openRun → the HUD was stuck on SIMULATION for the whole live run.
        artifact = build_resolved_profile_artifact(
            profile,
            run_id,
            execution_mode="live" if is_live else "fake",
            live_api="used" if is_live else "not_used",
        )
        (run_dir / "resolved-profile.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        def _profile_launcher(rid: str, rdir: Path, base: RunLauncher = base) -> int:
            return base(rid, rdir)

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


def _seed_default_profile(profiles_dir: Path) -> None:
    """Seed a baseline default profile when the dir has no VALID profile yet, so a
    fresh setup page is never an empty 'no profiles' state. Idempotent and
    non-fatal: never overwrites an existing file (respects user edits); a read-only
    dir is silently ignored (the empty state simply shows)."""
    if any(entry["valid"] for entry in list_profiles(profiles_dir)):
        return
    profile = build_default_profile()
    path = profiles_dir / f"{profile['name']}.json"
    if path.exists():
        return
    try:
        path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def create_observer_server(
    host: str,
    port: int,
    runs_dir: Path,
    launcher: RunLauncher | None = None,
    profiles_dir: Path | None = None,
    live_enabled: bool = False,
    live_launcher: RunLauncher | None = None,
    live_launcher_factory: Callable[[str], RunLauncher] | None = None,
    env_key_available: bool = False,
    live_max_requests: int = 32,
    live_max_tokens: int = 256,
    seed_default_profile: bool = False,
) -> ThreadingHTTPServer:
    """Create and configure a threaded observer HTTP server.

    ``live_enabled``/``live_launcher`` wire the G3-1 opt-in live path: live is
    the only mode that consults them, and only a profile launch (not a template
    launch) may select it.  Both default off so the server stays fake-only.

    ``live_launcher_factory`` is the per-launch builder used with a client-supplied
    key (P2-B-1 BYO-key path); ``env_key_available`` records whether the server
    started with an env key (back-compat signal for capability gate).

    P2-B-4: when live is enabled, a ``multi_provider_launcher_factory`` is built
    with the server live limits — the per-seat multi-provider launch path."""
    if launcher is None:
        launcher = default_fake_launcher
    runs_dir.mkdir(parents=True, exist_ok=True)
    if profiles_dir is None:
        profiles_dir = runs_dir.parent / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    # Opt-in (the CLI passes True): a fresh server isn't an empty setup page. Tests
    # using this factory leave it off so their temp profiles dirs stay pristine.
    if seed_default_profile:
        _seed_default_profile(profiles_dir)

    multi_provider_launcher_factory: Callable[..., RunLauncher] | None = None
    if live_enabled:
        def multi_provider_launcher_factory(resolved_seats, credentials):  # type: ignore[misc]
            return build_multi_provider_launcher(
                resolved_seats=resolved_seats,
                credentials=credentials,
                max_requests=live_max_requests,
                default_max_tokens=live_max_tokens,
            )

    state = ObserverServerState(
        runs_dir=runs_dir,
        launcher=launcher,
        profiles_dir=profiles_dir,
        live_enabled=live_enabled,
        live_launcher=live_launcher,
        live_launcher_factory=live_launcher_factory,
        env_key_available=env_key_available,
        multi_provider_launcher_factory=multi_provider_launcher_factory,
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

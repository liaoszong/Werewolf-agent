"""Run state machine + live-launcher selection (SYS-C2 split).

``RunManager`` hosts the implementation behind the handler's frozen method
surface (``_get_status``/``_set_status``/``_get_error``/``_set_error``/
``_execute_run``/``_run_detail_with_reason`` and the DELETE flow). The handler
methods remain thin delegates — tests subclass the handler and call those
methods directly, so they are the contract; this class is the host.

Module-level functions (launcher resolution, capability/shape/posture gates,
reason mappers, payload builders) stay module-level because the do-not-touch
test files import them by name through the ``observer_server`` facade.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from werewolf_eval.evaluation_versions import read_manifest_bucket
from werewolf_eval.observer.state import ObserverServerState, RunLauncher
from werewolf_eval.observer_protocol import (
    build_run_detail,
    build_runtime_capabilities,
    read_run_status,
    write_run_status,
)
from werewolf_eval.profile_config import build_profile_schema
from werewolf_eval.provider_registry import PROVIDER_REGISTRY, provider_specs_payload
from werewolf_eval.runtime_events import RuntimeEventError, read_events_jsonl
from werewolf_eval.seat_agents import ProviderCredential

_STATUS_FILE = "status.json"
_PROVIDER_TURNS_FILE = "provider-turns.json"
_LOW_LIVE_SUCCESS_RATE_THRESHOLD = 0.80
_LOW_LIVE_SUCCESS_RATE_REASON = "low_live_success_rate"


def _resolve_live_launcher_for_launch(
    state: ObserverServerState,
    resolved_seats: list[dict],
) -> tuple[RunLauncher | None, tuple[int, str, str] | None]:
    """Pick the live launcher for THIS launch. P2-B-4 multi-provider:

    1. If EVERY provider used by the seats has a client credential → a per-seat
       multi-provider launcher (the general path; handles mixed and single-provider).
    2. No silent fallback: a seat whose provider lacks a credential → 403.

    B5 closeout: the deepseek-only env-key fallback has been retired. All live
    launches require client-supplied credentials via POST /api/credentials.

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
    proceed.  Non-live modes always proceed.

    B5 closeout: the deepseek-only env-key fallback has been retired. A credential
    is available only if the client has synced at least one provider key via
    POST /api/credentials."""
    if mode != "live":
        return None
    if not state.live_enabled:
        return (403, "live_api_disabled", "live API is not enabled on this server")
    # BYO-key: a credential is available if the client has synced ANY supported
    # provider key. This is a COARSE gate; the per-seat credential check happens
    # at launcher resolution.
    has_credential = any(state.credential_store.has(p) for p in PROVIDER_REGISTRY)
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

    B5 closeout: the deepseek-only env-key fallback has been retired. A provider
    is available only if the client has synced a credential for it.

    Never reads or returns a secret."""
    if not state.live_enabled:
        return (False, "live_api_disabled", "live API is not enabled on this server")
    has_credential = state.credential_store.has(provider)
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


def _run_delete_result(run_dir: Path, run_id: str, status: str) -> tuple[int, dict[str, object]]:
    """Pure logic for DELETE /api/runs/{run_id}. An active run (running/queued)
    is never deleted (409); a missing dir is 404; an rmtree failure (e.g. a
    Windows file lock) reports 500 — NEVER success on a partial delete."""
    if status in ("running", "queued"):
        return (409, {"error": "run_active"})
    if not run_dir.is_dir():
        return (404, {"error": "not_found"})
    try:
        shutil.rmtree(run_dir)
    except OSError as exc:
        return (500, {"error": "delete_failed", "detail": str(exc)})
    return (200, {"deleted": run_id})


def _run_interrupt_result(
    run_dir: Path, run_id: str, status: str
) -> tuple[int, dict[str, object]]:
    """Mark an active run interrupted without deleting local artifacts.

    Only ``queued``/``running`` are active. ``interrupted`` is idempotent so
    launcher shutdown can safely retry; completed/failed runs keep their terminal
    truth and are not downgraded.
    """
    if not run_dir.is_dir():
        return (404, {"error": "not_found"})
    if status == "interrupted":
        return (200, {"interrupted": run_id})
    if status not in ("running", "queued"):
        return (409, {"error": "run_not_active"})
    write_run_status(run_dir, "interrupted")
    _write_status_metadata(run_dir, {"reason": "user_interrupted"})
    return (200, {"interrupted": run_id})


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


def _read_status_metadata(run_dir: Path) -> dict[str, object]:
    path = run_dir / _STATUS_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_status_metadata(run_dir: Path, metadata: dict[str, object]) -> None:
    if not metadata:
        return
    try:
        payload = _read_status_metadata(run_dir)
        payload.update(metadata)
        run_dir.mkdir(parents=True, exist_ok=True)
        tmp = run_dir / (_STATUS_FILE + ".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(run_dir / _STATUS_FILE)
    except OSError:
        pass


def _read_live_success_metadata(run_dir: Path) -> dict[str, object]:
    path = run_dir / _PROVIDER_TURNS_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}

    metadata: dict[str, object] = {}
    rate = data.get("live_success_rate")
    requested = data.get("live_requested_actions")
    actions = data.get("live_success_actions")
    if isinstance(rate, (int, float)) and not isinstance(rate, bool):
        metadata["live_success_rate"] = float(rate)
    if isinstance(requested, (int, float)) and not isinstance(requested, bool):
        metadata["live_requested_actions"] = int(requested)
    if isinstance(actions, (int, float)) and not isinstance(actions, bool):
        metadata["live_success_actions"] = int(actions)
    return metadata


def _is_low_live_success_rate(metadata: dict[str, object]) -> bool:
    rate = metadata.get("live_success_rate")
    requested = metadata.get("live_requested_actions")
    if not isinstance(rate, (int, float)) or isinstance(rate, bool):
        return False
    if not isinstance(requested, int) or isinstance(requested, bool) or requested <= 0:
        return False
    return float(rate) < _LOW_LIVE_SUCCESS_RATE_THRESHOLD


class RunManager:
    """Run state machine over an ``ObserverServerState``: in-memory status map
    with durable ``status.json`` dual-write, key-free error reasons, synchronous
    run execution, deletion, and run-detail assembly.

    Stateless wrapper — cheap to construct per request from the handler's
    ``self._get_state()`` so handler subclass state injection keeps working."""

    def __init__(self, state: ObserverServerState) -> None:
        self._state = state

    # -- status / error ------------------------------------------------------

    def get_status(self, run_id: str, run_dir: Path) -> str:
        state = self._state
        with state.lock:
            if run_id in state.run_status:
                return state.run_status[run_id]
        # Not in memory (e.g. server restarted since the run finished) -> fall back to
        # the durable status.json so prior completed runs stay settleable.
        durable = read_run_status(run_dir)
        if durable in ("running", "queued"):
            # The server owns run threads. If it restarted and no in-memory entry
            # exists, that run can no longer complete; archive it as interrupted
            # instead of leaving an undeletable zombie.
            _run_interrupt_result(run_dir, run_id, durable)
            return "interrupted"
        return durable

    def set_status(self, run_id: str, status: str) -> None:
        state = self._state
        with state.lock:
            state.run_status[run_id] = status
        # Persist durably (outside the lock — file I/O) so the status survives a restart.
        write_run_status(
            state.runs_dir / run_id,
            status,
            evaluation_bucket=read_manifest_bucket(state.runs_dir / run_id),
        )

    def set_error(self, run_id: str, error: str) -> None:
        state = self._state
        with state.lock:
            state.run_errors[run_id] = error

    def get_error(self, run_id: str) -> str | None:
        state = self._state
        with state.lock:
            return state.run_errors.get(run_id)

    # -- execution -----------------------------------------------------------

    def execute_run(self, run_id: str, run_dir: Path, launcher: RunLauncher) -> None:
        """Run *launcher* synchronously and record status + a key-free reason.

        Always records a canonical run-status reason on failure
        (``budget_exhausted``/``provider_failure``/``low_live_success_rate``) —
        never raw exception text — because the reason is exposed via run
        detail/list/SSE (A7)."""
        self.set_status(run_id, "running")
        try:
            ret = launcher(run_id, run_dir)
        except Exception as exc:  # noqa: BLE001
            if self.get_status(run_id, run_dir) == "interrupted":
                return
            reason = _sanitize_launcher_error(exc)
            self.set_error(run_id, reason)
            self.set_status(run_id, "failed")
            _write_status_metadata(run_dir, {"reason": reason})
            return
        if self.get_status(run_id, run_dir) == "interrupted":
            return
        live_metadata = _read_live_success_metadata(run_dir)
        if ret == 0:
            if _is_low_live_success_rate(live_metadata):
                self.set_error(run_id, _LOW_LIVE_SUCCESS_RATE_REASON)
                self.set_status(run_id, "failed")
                _write_status_metadata(
                    run_dir,
                    {
                        **live_metadata,
                        "live_success_threshold": _LOW_LIVE_SUCCESS_RATE_THRESHOLD,
                        "reason": _LOW_LIVE_SUCCESS_RATE_REASON,
                    },
                )
                return
            self.set_status(run_id, "completed")
            _write_status_metadata(run_dir, live_metadata)
        else:
            reason = _map_launcher_exit_reason(ret)
            self.set_error(run_id, reason)
            self.set_status(run_id, "failed")
            _write_status_metadata(run_dir, {**live_metadata, "reason": reason})

    # -- deletion ------------------------------------------------------------

    def delete_run(self, run_id: str, run_dir: Path) -> tuple[int, dict[str, object]]:
        """DELETE /api/runs/{run_id} flow: memory-first status read, the pure
        delete decision, then in-memory eviction on success."""
        status_now = self.get_status(run_id, run_dir)
        code, payload = _run_delete_result(run_dir, run_id, status_now)
        if code == 200:
            state = self._state
            with state.lock:  # drop stale in-memory entries
                state.run_status.pop(run_id, None)
                state.run_errors.pop(run_id, None)
        return code, payload

    def interrupt_run(self, run_id: str, run_dir: Path) -> tuple[int, dict[str, object]]:
        """POST /api/runs/{run_id}/interrupt flow: active-only terminal mark."""
        status_now = self.get_status(run_id, run_dir)
        code, payload = _run_interrupt_result(run_dir, run_id, status_now)
        if code == 200:
            state = self._state
            with state.lock:
                state.run_status[run_id] = "interrupted"
                state.run_errors.pop(run_id, None)
        return code, payload

    # -- detail --------------------------------------------------------------

    def run_detail_with_reason(self, run_id: str, run_dir: Path) -> dict[str, object]:
        """Build run detail and attach the key-free run-status reason (if any)
        plus the executed-truth ``execution_mode`` read from the run's OWN
        ``resolved-profile.json`` (G3-2).  ``execution_mode`` is the HUD chip's
        ONLY source of truth; it is omitted when no string value is present so
        the chip falls back to ``SYS: SIMULATION``."""
        mem_status = self.get_status(run_id, run_dir)
        detail = build_run_detail(run_dir, status=mem_status)
        status_metadata = _read_status_metadata(run_dir)
        reason = self.get_error(run_id)
        if reason is None:
            persisted_reason = status_metadata.get("reason")
            if isinstance(persisted_reason, str):
                reason = persisted_reason
        if reason is not None:
            detail["reason"] = reason
        for key in (
            "live_success_rate",
            "live_requested_actions",
            "live_success_actions",
            "live_success_threshold",
        ):
            if key in status_metadata:
                detail[key] = status_metadata[key]
        execution_mode = _read_execution_mode(run_dir)
        if execution_mode is not None:
            detail["execution_mode"] = execution_mode
        return detail

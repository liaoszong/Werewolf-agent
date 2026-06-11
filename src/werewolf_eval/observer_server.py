"""Local observer HTTP server with live run state (G2a).

Pure facade (SYS-C2 split): the implementation lives in
``werewolf_eval.observer.*`` (security / state / run_manager / credentials_api
/ launch / sse / routes / handler / factory). This module re-exports the
historical import surface — test files and ``run_observer_server`` import
these names from here. The re-export list below is pinned by a parity test;
extend it rather than pruning it.
"""

from __future__ import annotations

from werewolf_eval.observer.credentials_api import (
    _CREDENTIAL_PROVIDERS,
    _credentials_delete_result,
    _credentials_post_result,
    _provider_models_result,
)
from werewolf_eval.observer.factory import (
    _seed_default_profile,
    create_observer_server,
    default_fake_launcher,
)
from werewolf_eval.observer.handler import _PROFILE_NAME_RE, ObserverRequestHandler
from werewolf_eval.observer.run_manager import (
    _build_capabilities_payload,
    _check_live_capability,
    _check_live_profile_shape,
    _map_launcher_exit_reason,
    _provider_live_posture,
    _read_events_jsonl_safe,
    _read_execution_mode,
    _resolve_live_launcher_for_launch,
    _run_delete_result,
    _sanitize_launcher_error,
    _schema_payload,
)
from werewolf_eval.observer.security import (
    _LOOPBACK_HOSTNAMES,
    _hostname_of,
    _is_loopback_hostname,
)
from werewolf_eval.observer.state import ObserverServerState, RunLauncher

__all__ = [
    "ObserverRequestHandler",
    "ObserverServerState",
    "RunLauncher",
    "create_observer_server",
    "default_fake_launcher",
    "_CREDENTIAL_PROVIDERS",
    "_LOOPBACK_HOSTNAMES",
    "_PROFILE_NAME_RE",
    "_build_capabilities_payload",
    "_check_live_capability",
    "_check_live_profile_shape",
    "_credentials_delete_result",
    "_credentials_post_result",
    "_hostname_of",
    "_is_loopback_hostname",
    "_map_launcher_exit_reason",
    "_provider_live_posture",
    "_provider_models_result",
    "_read_events_jsonl_safe",
    "_read_execution_mode",
    "_resolve_live_launcher_for_launch",
    "_run_delete_result",
    "_sanitize_launcher_error",
    "_schema_payload",
    "_seed_default_profile",
]

"""Declarative routing tables for the observer HTTP handler (SYS-C2 split).

A ``Route`` declares its path pattern and its guard flags; the handler's
dispatcher translates guards into calls to the OVERRIDABLE handler methods
(``self._is_loopback()`` / ``self._reject_cross_origin()``) — never into direct
pure-function calls, because tests subclass the handler and override those
methods. Table declaration order IS the historical if-chain order: first match
wins (e.g. ``api/profiles/schema`` is declared before ``api/profiles/{name}``).

The guard matrix is ASYMMETRIC by design — do not "normalize" it:
POST/DELETE credentials and DELETE runs check loopback + cross-origin;
POST /api/runs checks cross-origin only; GET providers/models checks loopback
only; all other GETs are unguarded.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    pattern: tuple[str, ...]  # literal segments; "{name}" captures one segment
    handler_name: str  # method name on ObserverRequestHandler
    loopback_message: str | None = None  # non-None = loopback gate w/ this 403 text
    same_origin: bool = False  # Host/Origin (DNS-rebind / CSRF) guard
    allow_trailing: bool = False  # extra trailing segments are ignored


def match_route(
    routes: tuple[Route, ...], segments: list[str]
) -> tuple[Route, dict[str, str]] | None:
    """First-match-wins over the table. ``{name}`` captures exactly one
    segment; with ``allow_trailing`` extra trailing segments are ignored
    (historical behavior of ``snapshots/{name}`` and ``artifacts/{name}``)."""
    for route in routes:
        pattern = route.pattern
        if route.allow_trailing:
            if len(segments) < len(pattern):
                continue
        elif len(segments) != len(pattern):
            continue
        params: dict[str, str] = {}
        for expected, actual in zip(pattern, segments):
            if expected.startswith("{") and expected.endswith("}"):
                params[expected[1:-1]] = actual
            elif expected != actual:
                break
        else:
            return route, params
    return None


GET_ROUTES: tuple[Route, ...] = (
    Route(("health",), "_route_health"),
    Route(("api", "runtime", "capabilities"), "_route_capabilities"),
    Route(("api", "runs"), "_route_runs_list"),
    Route(("api", "profiles", "schema"), "_route_profile_schema"),
    Route(
        ("api", "providers", "{provider}", "models"),
        "_route_provider_models",
        loopback_message="providers endpoint is loopback-only",
    ),
    Route(("api", "configs"), "_route_configs_list"),
    Route(("api", "configs", "{config_id}", "export"), "_route_config_export"),
    Route(("api", "configs", "{config_id}"), "_route_config_detail"),
    Route(("api", "profiles"), "_route_profiles_list"),
    Route(("api", "profiles", "{name}"), "_route_profile_detail"),
    # Run group: validate_run_id → 404 "Run not found: {id}" → perspective →
    # RUN_SUB_ROUTES, all inside _route_run_scoped (matches the historical
    # single-block structure, including 404 wording precedence).
    Route(("api", "runs", "{run_id}"), "_route_run_scoped", allow_trailing=True),
)

# Sub-table over segments AFTER api/runs/{run_id}; declaration order mirrors the
# historical if-chain. No match here falls through to 404 "Not found".
RUN_SUB_ROUTES: tuple[Route, ...] = (
    Route(("events",), "_route_run_events"),
    Route(("stream",), "_route_run_stream"),
    Route(("snapshots",), "_route_run_snapshots"),
    Route(("snapshots", "{name}"), "_route_run_snapshot_detail", allow_trailing=True),
    Route(("projection",), "_route_run_projection"),
    Route((), "_route_run_detail"),
    Route(("artifacts",), "_route_run_artifacts"),
    Route(("settlement",), "_route_run_settlement"),
    Route(("artifacts", "{name}"), "_route_run_artifact_detail", allow_trailing=True),
    Route(("manifest",), "_route_run_artifact_alias"),
    Route(("provider-trace",), "_route_run_artifact_alias"),
    Route(("failure-audit",), "_route_run_artifact_alias"),
)

POST_ROUTES: tuple[Route, ...] = (
    Route(
        ("api", "credentials"),
        "_route_credentials_post",
        loopback_message="credentials endpoint is loopback-only",
        same_origin=True,
    ),
    Route(("api", "runs"), "_route_runs_post", same_origin=True),
    Route(("api", "profiles", "validate"), "_route_profile_validate"),
    Route(
        ("api", "configs", "import"),
        "_route_configs_import",
        loopback_message="configs endpoint is loopback-only",
        same_origin=True,
    ),
    Route(
        ("api", "configs"),
        "_route_configs_post",
        loopback_message="configs endpoint is loopback-only",
        same_origin=True,
    ),
)

DELETE_ROUTES: tuple[Route, ...] = (
    Route(
        ("api", "credentials", "{provider}"),
        "_route_credentials_delete",
        loopback_message="credentials endpoint is loopback-only",
        same_origin=True,
    ),
    Route(
        ("api", "runs", "{run_id}"),
        "_route_runs_delete",
        loopback_message="runs delete is loopback-only",
        same_origin=True,
    ),
)

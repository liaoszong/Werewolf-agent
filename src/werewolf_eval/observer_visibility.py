"""G2c observer visibility facade (B-4 layering, ADR 2026-06-11).

Pure re-export surface — zero logic. The implementation is layered into:

* ``observer_trust_index``  — provenance ASSIGNMENT (which artifact backs each
  seat's role/team/alive; the trust source of truth),
* ``observer_projection``   — provenance ENFORCEMENT (what each perspective may
  see; the only reader of ``*_source`` tags),
* ``observer_enrichment``   — artifact join onto already-filtered events + the
  /projection envelope.

Auditing the anti-leak boundary = reading the first two modules. Importers keep
using this facade.

Part of the SYS-A4 observer-side witness: this facade and all three layered
modules must stay independent of the engine-side single source (B-2 ADR);
enforced by the witness-boundary sentinel test.
"""

from __future__ import annotations

from werewolf_eval.observer_enrichment import build_projection_envelope
from werewolf_eval.observer_projection import (
    CONTRACT_VERSION,
    DEFAULT_PLAYER_IDS,
    PUBLIC_LIKE_EVENT_VISIBILITIES,
    ROLE_PERSPECTIVE_PREFIX,
    ROLE_SPECIFIC_EVENT_VISIBILITIES,
    WEREWOLF_TEAM_EVENT_VISIBILITIES,
    VisibilityProjectionError,
    _KNOWN_ROLE_TEAMS,
    build_player_projection,
    event_visible_in_projection,
    infer_player_ids,
    is_werewolf_role,
    perspective_kind,
    project_events,
    project_snapshots,
    unknown_player,
)
from werewolf_eval.observer_trust_index import build_seat_role_index

__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_PLAYER_IDS",
    "PUBLIC_LIKE_EVENT_VISIBILITIES",
    "ROLE_PERSPECTIVE_PREFIX",
    "ROLE_SPECIFIC_EVENT_VISIBILITIES",
    "WEREWOLF_TEAM_EVENT_VISIBILITIES",
    "VisibilityProjectionError",
    "build_player_projection",
    "build_projection_envelope",
    "build_seat_role_index",
    "event_visible_in_projection",
    "infer_player_ids",
    "is_werewolf_role",
    "perspective_kind",
    "project_events",
    "project_snapshots",
    "unknown_player",
]

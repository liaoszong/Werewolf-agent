"""Single source of truth for the ENGINE-side role-filtered event visibility rule
(health-check B-2; ADR ``docs/adr/2026-06-11-engine-visibility-single-source.md``).

Both engines (``GameEngine`` scripted/mock arcs and ``EmergentGameEngine``) decide
"which event ids does this seat see" with this rule:

* public set:  ``visibility in {"public", "all"}``
* private set: ``visibility == "all"``, OR ``visibility ==`` the seat's role, OR
  ``visibility == "werewolf_team"`` for werewolf seats

This is the invariant the P2-A-2 "no feed leak" hard gate renders prompts from.

WITNESS BOUNDARY (do not widen): ``observer_visibility.py`` / ``observer_protocol.py``
and ``invariants/`` are deliberate INDEPENDENT implementations (SYS-A4 dual witness /
safety-net I4b anti-circularity). They must never import this module —
``tests/test_role_visibility.py`` enforces that with a sentinel."""

from __future__ import annotations

from typing import Any

PUBLIC_VISIBILITIES = ("public", "all")


def public_refs(events: list[dict[str, Any]]) -> list[str]:
    """Event ids every seat sees, in event order."""
    return [e["event_id"] for e in events if e["visibility"] in PUBLIC_VISIBILITIES]


def private_refs_for_role(events: list[dict[str, Any]], role: str) -> list[str]:
    """Event ids a seat of ``role`` privately sees, in event order: "all" events,
    its own role-private events, and the wolf-team channel for werewolves."""
    refs: list[str] = []
    for e in events:
        v = e["visibility"]
        if v == "all" or v == role or (v == "werewolf_team" and role == "werewolf"):
            refs.append(e["event_id"])
    return refs

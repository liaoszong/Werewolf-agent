"""Observer-side artifact join + projection envelope (B-4 layering, ADR 2026-06-11).

Joins game-log summaries and decision-log reasons onto ALREADY-FILTERED events
and assembles the /projection envelope. Must never read snapshots or provenance
tags directly; its only perspective-sensitive rule is the private
``reason_summary`` actor gate (god or the deciding player), which is an
actor-identity gate, not provenance.

Part of the SYS-A4 observer-side witness: must stay independent of the
engine-side single source (B-2 ADR); enforced by the witness-boundary sentinel test.
"""

from __future__ import annotations

import json
from pathlib import Path

from werewolf_eval.observer_projection import (
    CONTRACT_VERSION,
    ROLE_PERSPECTIVE_PREFIX,
    _build_proof,
    build_player_projection,
    perspective_kind,
    project_events,
    project_snapshots,
)
from werewolf_eval.observer_trust_index import build_seat_role_index


# ---------------------------------------------------------------------------
# Projection envelope builder (Step 6)
# ---------------------------------------------------------------------------


def _load_game_log_summaries(run_dir: Path) -> dict[str, dict[str, str]]:
    """Return ``{game_log_event_id: {"summary", "target"}}`` from ``game-log.json``,
    or ``{}`` when absent/malformed.  Never raises.

    Summaries are public/role-visible game narration (NOT prompt/provider secrets);
    the visibility filter in :func:`project_events` decides which events reach the
    client BEFORE this lookup is joined in :func:`build_projection_envelope`, so
    attaching summaries to already-visible events cannot leak hidden facts (P2-C-1 §7).
    """
    path = run_dir / "game-log.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for event in data.get("events", []):
        if not isinstance(event, dict):
            continue
        eid = str(event.get("event_id", ""))
        if not eid:
            continue
        event_data = event.get("data", {})
        summary = str(event_data.get("summary", "")) if isinstance(event_data, dict) else ""
        target = event.get("target", "")
        out[eid] = {"summary": summary, "target": "" if target is None else str(target)}
    return out


def _load_decision_reasons(run_dir: Path) -> dict[str, dict[str, str]]:
    """Return ``{game_log_event_id: {...}}`` by joining ``decision-log.json`` reasons
    onto ``game-log.json`` events, or ``{}`` when absent/malformed.  Never raises.

    UNLIKE summaries, a ``reason_summary`` is PRIVATE strategy: even when the
    underlying event is public (e.g. a vote), the reasoning behind it must only
    reach god or the deciding player.  This loader only builds the join and
    records the deciding ``actor``; :func:`build_projection_envelope` enforces the
    per-actor gate.  Decisions are matched by ``(round, phase, actor, action,
    target)`` — a composite key that disambiguates repeated same-actor/action/target
    decisions across rounds (C12-06/A45-7 fix).  When duplicate composite keys
    exist in the decision log, the enrichment marks them as ambiguous rather than
    silently resolving to one entry.  For legacy decision logs that lack ``round``,
    a greedy ``(actor, action, target)`` fallback is used and annotated as
    ``legacy_no_round``.
    """
    try:
        gl = json.loads((run_dir / "game-log.json").read_text(encoding="utf-8"))
        dl = json.loads((run_dir / "decision-log.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(gl, dict) or not isinstance(dl, dict):
        return {}

    decisions = dl.get("decisions", [])
    if not isinstance(decisions, list):
        return {}

    # Build pending decisions keyed by composite (round, phase, actor, action, target).
    # Track ambiguity: if >1 decisions share the same key, mark as ambiguous.
    pending: dict[tuple[int, str, str, str, str], list[dict[str, str]]] = {}
    legacy_pending: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    has_round = False

    for d in decisions:
        if not isinstance(d, dict):
            continue
        reason = d.get("reason_summary")
        if not reason:
            continue
        entry = {
            "reason_summary": str(reason),
            "decision_id": str(d.get("decision_id", "")),
            "request_id": d.get("request_id"),  # may be None/missing
        }
        round_val = d.get("round")
        phase = str(d.get("phase", ""))
        actor = str(d.get("actor", ""))
        action = str(d.get("action", ""))
        target = "" if d.get("target") is None else str(d.get("target"))

        if round_val is not None and isinstance(round_val, int) and round_val >= 0:
            has_round = True
            key = (round_val, phase, actor, action, target)
            pending.setdefault(key, []).append(entry)
        else:
            # Legacy decision without round: fall back to greedy (actor, action, target)
            legacy_key = (actor, action, target)
            legacy_pending.setdefault(legacy_key, []).append(entry)

    out: dict[str, dict[str, str]] = {}
    for event in gl.get("events", []):
        if not isinstance(event, dict):
            continue
        eid = str(event.get("event_id", ""))
        actor = str(event.get("actor", ""))
        if not eid or not actor or actor == "system":
            continue
        phase = str(event.get("phase", ""))
        action = str(event.get("type", ""))
        target = "" if event.get("target") is None else str(event.get("target", ""))
        round_val = event.get("round")
        # Mirror the decision-side round check (incl. the bool exclusion): a JSON
        # ``true`` is an int subclass but never a valid round.
        event_has_round = (
            isinstance(round_val, int)
            and not isinstance(round_val, bool)
            and round_val >= 0
        )

        # Try composite key match first (when both decision and event have round).
        if has_round and event_has_round:
            key = (round_val, phase, actor, action, target)
            entries = pending.get(key)
            if entries is not None:
                if len(entries) == 1:
                    # Unique match: consume and attach.
                    entry = entries.pop(0)
                    if not entries:
                        del pending[key]
                    out[eid] = {
                        "reason_summary": entry["reason_summary"],
                        "actor": actor,
                        "decision_id": entry.get("decision_id", ""),
                        "request_id": entry.get("request_id") or "",
                        "reason_source": "matched",
                    }
                else:
                    # Ambiguous: multiple decisions share this composite key. Mark.
                    # Do NOT consume — all matching events get the ambiguity annotation.
                    out[eid] = {
                        "reason_summary": entries[0]["reason_summary"],
                        "actor": actor,
                        "decision_id": "",
                        "request_id": "",
                        "reason_source": "ambiguous",
                        "reason_detail": f"{len(entries)} decisions match key (round={round_val}, phase={phase}, actor={actor}, action={action}, target={target})",
                    }
                continue

        # Fallback: greedy match by (actor, action, target) without round.
        legacy_key = (actor, action, target)
        legacy_entries = legacy_pending.get(legacy_key)
        if legacy_entries:
            entry = legacy_entries.pop(0)
            if not legacy_entries:
                del legacy_pending[legacy_key]
            out[eid] = {
                "reason_summary": entry["reason_summary"],
                "actor": actor,
                "decision_id": entry.get("decision_id", ""),
                "request_id": entry.get("request_id") or "",
                "reason_source": "legacy_no_round",
            }
            continue

        # Last-resort greedy match against round-bearing decisions — ONLY for an
        # event that itself lacks a usable round. A round-bearing event that missed
        # its same-round decision in step 1 must stay UNMATCHED: grabbing a
        # different round's decision here would re-open the A45-7 cross-round
        # mislabel (round-2 event stamped with the round-1 reason).
        if event_has_round:
            continue
        for rk, entries in list(pending.items()):
            if entries and rk[2] == actor and rk[3] == action and rk[4] == target:
                entry = entries.pop(0)
                if not entries:
                    del pending[rk]
                out[eid] = {
                    "reason_summary": entry["reason_summary"],
                    "actor": actor,
                    "decision_id": entry.get("decision_id", ""),
                    "request_id": entry.get("request_id") or "",
                    "reason_source": "legacy_no_round",
                }
                break
    return out


def build_projection_envelope(
    *,
    run_dir: Path,
    run_id: str,
    perspective: str,
    events: list[dict[str, object]],
) -> dict[str, object]:
    """Build the top-level projection envelope consumed by observer clients.

    Required output keys:
        contract_version, run_id, perspective, view_kind, players,
        events, hidden_event_count, snapshots, hidden_snapshot_count, proof.
    """
    kind = perspective_kind(perspective)

    # Build seat index and projection
    seat_index = build_seat_role_index(run_dir)
    players = build_player_projection(seat_index, perspective)

    # Project events (visibility filter first), then back-fill summary/target from
    # game-log.json onto ALREADY-VISIBLE events only (P2-C-1 §7, D6) — post-filter, no leak.
    event_projection = project_events(events, perspective, seat_index)
    summaries = _load_game_log_summaries(run_dir)
    reasons = _load_decision_reasons(run_dir)
    # reason_summary is private strategy: god sees all; role:pN sees only pN's own;
    # public/team see none. Gate by the DECIDING actor, never the event's visibility.
    reason_self = perspective[len(ROLE_PERSPECTIVE_PREFIX):] if kind == "role" else None
    enriched_events: list[dict[str, object]] = []
    for ev in event_projection["events"]:
        payload = ev.get("payload")
        gid = str(payload.get("event_id", "")) if isinstance(payload, dict) else ""
        match = summaries.get(gid)
        reason = reasons.get(gid)
        if match is not None or reason is not None:
            ev = dict(ev)
            # Canonical shape (spec §7): data.summary nested + target top-level.
            data = dict(ev.get("data") or {})
            if match is not None:
                data["summary"] = match["summary"]
                if match.get("target"):
                    ev["target"] = match["target"]
            if reason is not None and (kind == "god" or reason_self == reason["actor"]):
                data["reason_summary"] = reason["reason_summary"]
                # Attach enrichment metadata for P3-A replay traceability (C12-06/A45-7).
                src = reason.get("reason_source", "matched")
                data["reason_source"] = src
                if src == "ambiguous":
                    data["reason_detail"] = reason.get("reason_detail", "")
                if reason.get("decision_id"):
                    data["decision_id"] = reason["decision_id"]
                if reason.get("request_id"):
                    data["request_id"] = reason["request_id"]
            ev["data"] = data
        enriched_events.append(ev)

    # Project snapshots (metadata only)
    snapshot_projection = project_snapshots(run_dir, perspective)

    # Build proof
    proof = _build_proof(seat_index, perspective, kind)

    return {
        "contract_version": CONTRACT_VERSION,
        "run_id": run_id,
        "perspective": perspective,
        "view_kind": kind,
        "players": players,
        "events": enriched_events,
        "hidden_event_count": event_projection["hidden_event_count"],
        "snapshots": snapshot_projection["snapshots"],
        "hidden_snapshot_count": snapshot_projection["hidden_snapshot_count"],
        "proof": proof,
    }

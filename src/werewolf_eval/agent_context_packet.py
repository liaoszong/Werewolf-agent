"""P3-A AgentContextPacket schema helpers.

This module is deliberately pure and runtime-neutral. It validates memory
records and selects visible packet records without rendering provider prompts or
changing engine behavior.
"""

from __future__ import annotations

import copy
import re
from typing import Any

AGENT_CONTEXT_PACKET_SCHEMA_VERSION = "p3a.agent_context_packet.v1"

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")
_SEAT_RE = re.compile(r"^p[1-9][0-9]*$")

_RECORD_KINDS = frozenset(
    {
        "FactRecord",
        "ClaimRecord",
        "BeliefRecord",
        "CommitmentRecord",
        "TeamPlanRecord",
        "StaticPlaybookRecord",
    }
)
_SECTIONS = frozenset(
    {
        "board_facts",
        "self_facts",
        "private_facts",
        "public_timeline",
        "episodic_notes",
        "commitments",
        "team_memory",
        "retrieved_playbook",
    }
)
_WRITERS = frozenset(
    {
        "engine",
        "runtime",
        "public_event",
        "scribe",
        "seat_agent",
        "team_scaffold",
        "user_asset",
    }
)
_VISIBILITY_SCOPES = frozenset(
    {"public", "seat_private", "faction_private", "engine_only", "postgame_only"}
)
_TRUST_CLASSES = frozenset(
    {"built_in_vetted", "local_user", "legacy_opaque", "run_derived"}
)
_RENDER_MODES = frozenset(
    {"control", "guidance", "quoted_evidence", "state_summary", "ui_only"}
)
_STATUSES = frozenset({"active", "superseded", "retracted"})
_FACT_WRITERS = frozenset({"engine", "runtime"})


class AgentContextPacketError(ValueError):
    """Raised when an AgentContextPacket object violates P3-A memory rules."""


def validate_agent_context_packet(packet: object) -> None:
    packet = _check_object(packet, where="AgentContextPacket")
    _check_no_extra(
        packet,
        {
            "schema_version",
            "run_id",
            "seat_id",
            "decision_id",
            "records",
            "context_budget",
        },
        where="AgentContextPacket",
    )
    if packet.get("schema_version") != AGENT_CONTEXT_PACKET_SCHEMA_VERSION:
        raise AgentContextPacketError("AgentContextPacket.schema_version invalid")
    for key in ("run_id", "decision_id"):
        _check_id(packet.get(key), where=f"AgentContextPacket.{key}")
    _check_seat_id(packet.get("seat_id"), where="AgentContextPacket.seat_id")
    records = packet.get("records")
    if not isinstance(records, list):
        raise AgentContextPacketError("AgentContextPacket.records must be list")
    for record in records:
        validate_memory_record(record)
    _validate_context_budget(packet.get("context_budget"))


def validate_memory_record(record: object) -> None:
    record = _check_object(record, where="MemoryRecord")
    _check_no_extra(
        record,
        {
            "record_id",
            "kind",
            "section",
            "writer",
            "visibility_scope",
            "audience_scope",
            "trust_class",
            "render_mode",
            "source_provenance",
            "status",
            "summary",
            "supersedes",
        },
        where="MemoryRecord",
    )
    _check_id(record.get("record_id"), where="MemoryRecord.record_id")
    if record.get("kind") not in _RECORD_KINDS:
        raise AgentContextPacketError("MemoryRecord.kind invalid")
    if record.get("section") not in _SECTIONS:
        raise AgentContextPacketError("MemoryRecord.section invalid")
    if record.get("writer") not in _WRITERS:
        raise AgentContextPacketError("MemoryRecord.writer invalid")
    if record.get("visibility_scope") not in _VISIBILITY_SCOPES:
        raise AgentContextPacketError("MemoryRecord.visibility_scope invalid")
    if record.get("trust_class") not in _TRUST_CLASSES:
        raise AgentContextPacketError("MemoryRecord.trust_class invalid")
    if record.get("render_mode") not in _RENDER_MODES:
        raise AgentContextPacketError("MemoryRecord.render_mode invalid")
    if record.get("status") not in _STATUSES:
        raise AgentContextPacketError("MemoryRecord.status invalid")
    if not isinstance(record.get("summary"), str) or not record["summary"]:
        raise AgentContextPacketError("MemoryRecord.summary must be non-empty string")
    if "supersedes" in record:
        _check_str_list(record["supersedes"], where="MemoryRecord.supersedes")
    _validate_audience_scope(record)
    _validate_source_provenance(record)
    _validate_record_semantics(record)


def render_record_summary(record: dict[str, Any]) -> dict[str, Any]:
    validate_memory_record(record)
    kind = record["kind"]
    summary = record["summary"]
    status = record["status"]
    inactive_prefix = "" if status == "active" else f"{status} "
    if kind == "FactRecord":
        fact_semantics = "engine_fact"
        text = f"{inactive_prefix}Fact: {summary}"
    elif kind == "ClaimRecord":
        fact_semantics = "claim_only"
        text = (
            f"{inactive_prefix}Claim: a seat claimed {summary}; "
            "this is not engine truth."
        )
    elif kind == "BeliefRecord":
        fact_semantics = "agent_belief"
        if status == "active":
            text = (
                f"Belief: this agent currently believes {summary}; "
                "this is not engine truth."
            )
        else:
            text = (
                f"{status} Belief: this agent previously believed {summary}; "
                "this is not current engine truth."
            )
    else:
        fact_semantics = "non_fact"
        text = f"{inactive_prefix}{kind}: {summary}; this is not engine truth."
    return {
        "block_id": record["record_id"],
        "text": text,
        "fact_semantics": fact_semantics,
        "trust_class": record["trust_class"],
        "render_mode": record["render_mode"],
        "visibility_scope": record["visibility_scope"],
        "source_provenance": copy.deepcopy(record["source_provenance"]),
    }


def select_visible_packet(
    packet: dict[str, Any],
    *,
    seat_id: str,
    team_ids: set[str] | None = None,
    max_records: int | None = None,
    compacted_record_ids: set[str] | None = None,
) -> dict[str, Any]:
    validate_agent_context_packet(packet)
    _check_seat_id(seat_id, where="seat_id")
    if max_records is not None and max_records < 0:
        raise AgentContextPacketError("max_records must be non-negative")
    team_ids = set(team_ids or set())
    compacted_record_ids = set(compacted_record_ids or set())
    records = packet["records"]
    visible_records: list[dict[str, Any]] = []
    dropped_blocks: list[str] = []
    for record in records:
        if _is_record_visible_to(record, seat_id=seat_id, team_ids=team_ids):
            visible_records.append(copy.deepcopy(record))

    included_blocks: list[str] = []
    compacted_blocks: list[str] = []
    selected_records: list[dict[str, Any]] = []
    included_count = 0
    for record in visible_records:
        record_id = record["record_id"]
        if record_id in compacted_record_ids:
            selected_records.append(record)
            compacted_blocks.append(record_id)
            continue
        if max_records is not None and included_count >= max_records:
            dropped_blocks.append(record_id)
            continue
        selected_records.append(record)
        included_blocks.append(record_id)
        included_count += 1

    selected = copy.deepcopy(packet)
    selected["seat_id"] = seat_id
    selected["records"] = selected_records
    selected["context_budget"] = {
        "included_blocks": included_blocks,
        "compacted_blocks": compacted_blocks,
        "dropped_blocks": dropped_blocks,
    }
    validate_agent_context_packet(selected)
    return selected


def _validate_record_semantics(record: dict[str, Any]) -> None:
    kind = record["kind"]
    if kind == "FactRecord":
        if record["writer"] not in _FACT_WRITERS:
            raise AgentContextPacketError("FactRecord writer must be runtime or engine")
        provenance = record["source_provenance"]
        if not provenance.get("source_event_ids") and not provenance.get("static_source"):
            raise AgentContextPacketError(
                "FactRecord requires source_event_ids or static_source"
            )
    elif kind == "ClaimRecord":
        if record["render_mode"] != "quoted_evidence":
            raise AgentContextPacketError("ClaimRecord.render_mode must be quoted_evidence")
    elif kind in {"BeliefRecord", "CommitmentRecord", "TeamPlanRecord"}:
        if record["render_mode"] != "state_summary":
            raise AgentContextPacketError(f"{kind}.render_mode must be state_summary")
    elif kind == "StaticPlaybookRecord":
        if record["render_mode"] != "guidance":
            raise AgentContextPacketError("StaticPlaybookRecord.render_mode must be guidance")
    if kind == "TeamPlanRecord":
        audience = record["audience_scope"]
        if record["visibility_scope"] != "faction_private":
            raise AgentContextPacketError("TeamPlanRecord must be faction_private")
        if not audience.get("team_ids") or not audience.get("authorized_seat_ids"):
            raise AgentContextPacketError(
                "TeamPlanRecord requires team_ids and authorized_seat_ids"
            )


def _validate_context_budget(value: object) -> None:
    budget = _check_object(value, where="AgentContextPacket.context_budget")
    _check_no_extra(
        budget,
        {"included_blocks", "compacted_blocks", "dropped_blocks"},
        where="AgentContextPacket.context_budget",
    )
    for key in ("included_blocks", "compacted_blocks", "dropped_blocks"):
        _check_str_list(budget.get(key), where=f"AgentContextPacket.context_budget.{key}")


def _validate_audience_scope(record: dict[str, Any]) -> None:
    scope = _check_object(record.get("audience_scope"), where="MemoryRecord.audience_scope")
    _check_no_extra(
        scope,
        {"seat_ids", "team_ids", "authorized_seat_ids"},
        where="MemoryRecord.audience_scope",
    )
    for key in ("seat_ids", "team_ids", "authorized_seat_ids"):
        if key in scope:
            _check_str_list(scope[key], where=f"MemoryRecord.audience_scope.{key}")
    if record["visibility_scope"] == "seat_private" and not scope.get("seat_ids"):
        raise AgentContextPacketError("seat_private record requires seat_ids")
    if record["visibility_scope"] == "faction_private":
        if not scope.get("team_ids") or not scope.get("authorized_seat_ids"):
            raise AgentContextPacketError(
                "faction_private record requires team_ids and authorized_seat_ids"
            )


def _validate_source_provenance(record: dict[str, Any]) -> None:
    provenance = _check_object(
        record.get("source_provenance"),
        where="MemoryRecord.source_provenance",
    )
    _check_no_extra(
        provenance,
        {"source_event_ids", "asset_hashes", "static_source", "generated_by"},
        where="MemoryRecord.source_provenance",
    )
    if "source_event_ids" in provenance:
        _check_str_list(
            provenance["source_event_ids"],
            where="MemoryRecord.source_provenance.source_event_ids",
        )
    if "asset_hashes" in provenance:
        _check_str_list(
            provenance["asset_hashes"],
            where="MemoryRecord.source_provenance.asset_hashes",
        )
    if "static_source" in provenance and not isinstance(provenance["static_source"], str):
        raise AgentContextPacketError("MemoryRecord.source_provenance.static_source must be string")
    if not isinstance(provenance.get("generated_by"), str) or not provenance["generated_by"]:
        raise AgentContextPacketError("MemoryRecord.source_provenance.generated_by required")


def _is_record_visible_to(
    record: dict[str, Any],
    *,
    seat_id: str,
    team_ids: set[str],
) -> bool:
    visibility = record["visibility_scope"]
    audience = record["audience_scope"]
    if visibility == "public":
        return True
    if visibility == "seat_private":
        return seat_id in audience.get("seat_ids", [])
    if visibility == "faction_private":
        return seat_id in audience.get("authorized_seat_ids", []) and bool(
            team_ids & set(audience.get("team_ids", []))
        )
    return False


def _check_object(obj: object, *, where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise AgentContextPacketError(f"{where} must be object")
    return obj


def _check_no_extra(obj: dict[str, Any], allowed: set[str], *, where: str) -> None:
    extra = sorted(set(obj) - allowed)
    if extra:
        raise AgentContextPacketError(f"{where} has unexpected keys: {extra}")


def _check_id(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID_RE.match(value):
        raise AgentContextPacketError(f"{where} must be safe id string")
    return value


def _check_seat_id(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SEAT_RE.match(value):
        raise AgentContextPacketError(f"{where} must be seat id like p1")
    return value


def _check_str_list(value: object, *, where: str) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AgentContextPacketError(f"{where} must be list[str]")

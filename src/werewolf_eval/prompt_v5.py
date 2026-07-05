"""prompt_v5 (P3-A-2c roleplay context): RolePolicy + AgentContextPacket
observation-side guidance for the first roleplay arm.

This module owns the new model-visible bytes. It is a coexisting prompt version:
prompt_v1 stays the default, and older prompt_v1-v4 renderers do not call this
path. The renderer exposes only strategy text plus hash/provenance metadata; it
does not render RolePolicy ids, versions, true-role fields, team ids, or runtime
state refs.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from werewolf_eval.agent_assets import validate_role_policy
from werewolf_eval.agent_context_packet import (
    render_record_summary,
    select_visible_packet,
)

ROLEPLAY_CONTEXT_SCHEMA_VERSION = "prompt_v5.roleplay_context.v1"
ROLEPLAY_CONTEXT_BLOCK_ORDER = ("role_policy", "agent_context")


def render_roleplay_context_suffix(
    *,
    role_policy: dict[str, Any] | None,
    agent_context_packet: dict[str, Any] | None,
    seat_id: str,
    team_ids: set[str] | None = None,
    max_context_records: int | None = 6,
) -> dict[str, Any]:
    """Render seat-private roleplay guidance for prompt_v5.

    The return shape is intentionally audit-friendly and free of raw asset refs:
    ``text`` is appended to observation_text; ``blocks`` records hashes and
    source provenance for the provider turn.
    """
    blocks: list[dict[str, Any]] = []
    text_blocks: list[str] = []

    if role_policy is not None:
        policy_text = _render_role_policy(role_policy)
        text_blocks.append(policy_text)
        blocks.append(
            _block(
                block_name="role_policy",
                text=policy_text,
                trust_class="built_in_vetted",
                render_mode="guidance",
                visibility_scope="seat_private",
                source_provenance={
                    "asset_hashes": [f"sha256:{_sha256_json(role_policy)}"],
                    "generated_by": "RolePolicyRegistry",
                },
            )
        )

    if agent_context_packet is not None:
        packet = select_visible_packet(
            agent_context_packet,
            seat_id=seat_id,
            team_ids=team_ids or set(),
            max_records=max_context_records,
        )
        rendered_records = [
            render_record_summary(record) for record in packet["records"]
        ]
        if rendered_records:
            context_text = _render_context_records(rendered_records)
            text_blocks.append(context_text)
            blocks.append(
                _block(
                    block_name="agent_context",
                    text=context_text,
                    trust_class="run_derived",
                    render_mode="state_summary",
                    visibility_scope="seat_private",
                    source_provenance=_merge_record_provenance(rendered_records),
                )
            )

    if not text_blocks:
        return {
            "schema_version": ROLEPLAY_CONTEXT_SCHEMA_VERSION,
            "text": "",
            "blocks": [],
        }
    return {
        "schema_version": ROLEPLAY_CONTEXT_SCHEMA_VERSION,
        "text": "\n" + "\n".join(text_blocks),
        "blocks": blocks,
    }


def _render_role_policy(policy: dict[str, Any]) -> str:
    validate_role_policy(policy)
    lines = ["【角色策略】"]
    _append_list(lines, "目标", policy.get("goals", []))
    _append_list(lines, "信息优先级", policy.get("information_priorities", []))
    _append_mapping(lines, "能力使用", policy.get("ability_use_policy", {}))
    _append_mapping(lines, "身份声明", policy.get("claim_policy", {}))
    _append_mapping(lines, "欺骗边界", policy.get("deception_policy", {}))
    _append_mapping(lines, "协作倾向", policy.get("team_policy", {}))
    _append_list(lines, "禁止行为", policy.get("forbidden_behavior", []))
    return "\n".join(lines)


def _render_context_records(records: list[dict[str, Any]]) -> str:
    lines = ["【上下文记忆】"]
    for record in records:
        lines.append(
            "- "
            f"[{record['fact_semantics']}; {record['trust_class']}; "
            f"{record['render_mode']}] {record['text']}"
        )
    return "\n".join(lines)


def _append_list(lines: list[str], label: str, values: Any) -> None:
    if not values:
        return
    if not isinstance(values, list):
        values = [str(values)]
    lines.append(f"- {label}: " + "; ".join(str(item) for item in values))


def _append_mapping(lines: list[str], label: str, value: Any) -> None:
    if not value:
        return
    if not isinstance(value, dict):
        lines.append(f"- {label}: {value}")
        return
    parts = [f"{key}={value[key]}" for key in sorted(value)]
    lines.append(f"- {label}: " + "; ".join(parts))


def _block(
    *,
    block_name: str,
    text: str,
    trust_class: str,
    render_mode: str,
    visibility_scope: str,
    source_provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "block_name": block_name,
        "trust_class": trust_class,
        "render_mode": render_mode,
        "visibility_scope": visibility_scope,
        "source_provenance": source_provenance,
        "content_hash": f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}",
    }


def _merge_record_provenance(records: list[dict[str, Any]]) -> dict[str, Any]:
    source_event_ids: set[str] = set()
    asset_hashes: set[str] = set()
    generated_by: set[str] = set()
    static_sources: set[str] = set()
    for record in records:
        provenance = record.get("source_provenance") or {}
        source_event_ids.update(provenance.get("source_event_ids") or [])
        asset_hashes.update(provenance.get("asset_hashes") or [])
        if provenance.get("generated_by"):
            generated_by.add(str(provenance["generated_by"]))
        if provenance.get("static_source"):
            static_sources.add(str(provenance["static_source"]))
    merged: dict[str, Any] = {
        "generated_by": ",".join(sorted(generated_by)) or "AgentContextPacket",
    }
    if source_event_ids:
        merged["source_event_ids"] = sorted(source_event_ids)
    if asset_hashes:
        merged["asset_hashes"] = sorted(asset_hashes)
    if static_sources:
        merged["static_source"] = ",".join(sorted(static_sources))
    return merged


def _sha256_json(obj: object) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

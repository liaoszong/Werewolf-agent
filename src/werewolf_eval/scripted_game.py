"""LEGACY (R-35): early-generation scripted runner, reachable only from its own
tests — NOT on the canonical product path (`run_observer_server` →
`run_g1h_fake_runtime` for fake / `deepseek_launcher` for live). Kept for its passing
tests; do not build new features on it. See `docs/PROJECT_MAP.md` for current entries."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

SCRIPTED_SOURCE_LABEL = "[scripted deterministic output]"


@dataclass(frozen=True)
class ScriptedGame:
    script_id: str
    game_id: str
    source_label: str
    players: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    result: dict[str, Any]


@dataclass(frozen=True)
class ScriptedGameOutputs:
    game_log: dict[str, Any]
    decision_log: dict[str, Any]
    consensus_log: dict[str, Any]


def load_scripted_game(path: str | Path) -> ScriptedGame:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("scripted game root must be an object")
    required = {"script_id", "game_id", "source_label", "players", "steps", "result"}
    missing = required - set(raw)
    if missing:
        raise ValueError(f"scripted game missing fields: {sorted(missing)}")
    if raw["source_label"] != SCRIPTED_SOURCE_LABEL:
        raise ValueError(
            "scripted game source_label must be [scripted deterministic output]"
        )
    return ScriptedGame(
        script_id=str(raw["script_id"]),
        game_id=str(raw["game_id"]),
        source_label=str(raw["source_label"]),
        players=list(raw["players"]),
        steps=list(raw["steps"]),
        result=dict(raw["result"]),
    )


def _event_id(game_id: str, sequence: int) -> str:
    return f"{game_id}_e{sequence:03d}"


def _decision_id(game_id: str, index: int) -> str:
    return f"{game_id}_d{index:03d}"


def _consensus_id(game_id: str, index: int) -> str:
    return f"{game_id}_c{index:03d}"


def _event_from_step(
    game_id: str, step: dict[str, Any], sequence: int
) -> dict[str, Any]:
    event = {
        "event_id": _event_id(game_id, sequence),
        "sequence": sequence,
        "round": step["round"],
        "phase": step["phase"],
        "type": step["type"],
        "actor": step["actor"],
        "target": step["target"],
        "visibility": step["visibility"],
        "data": {"summary": step["summary"]},
    }
    if "visible_info_refs" in step:
        event["data"]["visible_info_refs"] = list(step["visible_info_refs"])
    return event


def _decision_from_step(
    game_id: str,
    step: dict[str, Any],
    decision_index: int,
    consensus_id: str | None,
) -> dict[str, Any]:
    return {
        "decision_id": _decision_id(game_id, decision_index),
        "game_id": game_id,
        "actor": step["decision_actor"],
        "decision_scope": "team" if step["decision_actor"] == "wolf_team" else "single",
        "consensus_id": consensus_id,
        "phase": step["phase"],
        "action": step["type"],
        "target": step["target"],
        "visible_info_refs": list(step.get("visible_info_refs", [])),
        "reason_summary": step["reason_summary"],
        "decision_type": step["decision_type"],
        "confidence": 1.0,
        "strategy_tag": "scripted_deterministic",
    }


def _consensus_from_step(
    game_id: str, step: dict[str, Any], consensus_index: int
) -> dict[str, Any]:
    raw = step["consensus"]
    consensus_id = _consensus_id(game_id, consensus_index)
    primary = raw["primary_proposer"]
    supporters = list(raw["supporters"])
    responses = [
        {
            "response_id": index,
            "to_proposal_id": 1,
            "responder": supporter,
            "response_type": "support_with_reason",
            "reason_summary": "Scripted supporter accepts the deterministic target.",
            "visible_info_refs": list(step.get("visible_info_refs", [])),
            "action_round": 1,
        }
        for index, supporter in enumerate(supporters, start=1)
        if supporter != primary
    ]
    return {
        "consensus_id": consensus_id,
        "game_id": game_id,
        "round": step["round"],
        "phase": step["phase"],
        "team": "werewolf",
        "participants": list(raw["participants"]),
        "coordinator": raw["coordinator"],
        "max_rounds": 3,
        "actual_rounds": 1,
        "status": raw["status"],
        "proposals": [
            {
                "proposal_id": 1,
                "proposer": primary,
                "proposed_target": step["target"],
                "visible_info_refs": list(step.get("visible_info_refs", [])),
                "reason_summary": step["reason_summary"],
                "confidence": 1.0,
                "action_round": 1,
            }
        ],
        "responses": responses,
        "final_decision": {
            "target": step["target"],
            "decision_type": raw["status"],
            "primary_proposer": primary,
            "supporters": supporters,
            "dissenters": list(raw["dissenters"]),
            "resolution_round": 1,
        },
    }


def run_scripted_game(script: ScriptedGame) -> ScriptedGameOutputs:
    events = [
        _event_from_step(script.game_id, step, sequence)
        for sequence, step in enumerate(script.steps, start=1)
    ]
    decisions: list[dict[str, Any]] = []
    consensuses: list[dict[str, Any]] = []
    consensus_by_step_id: dict[str, str] = {}

    for step in script.steps:
        if step["type"] == "werewolf_kill" and "consensus" in step:
            consensus = _consensus_from_step(
                script.game_id, step, len(consensuses) + 1
            )
            consensuses.append(consensus)
            consensus_by_step_id[step["step_id"]] = consensus["consensus_id"]

    for step in script.steps:
        if "decision_actor" in step:
            decisions.append(
                _decision_from_step(
                    script.game_id,
                    step,
                    len(decisions) + 1,
                    consensus_by_step_id.get(step["step_id"]),
                )
            )

    return ScriptedGameOutputs(
        game_log={
            "game_id": script.game_id,
            "source_label": SCRIPTED_SOURCE_LABEL,
            "players": script.players,
            "events": events,
            "result": script.result,
        },
        decision_log={
            "decision_log_id": f"{script.game_id}_decision_log",
            "game_id": script.game_id,
            "source_label": SCRIPTED_SOURCE_LABEL,
            "decisions": decisions,
        },
        consensus_log={
            "consensus_log_id": f"{script.game_id}_consensus_log",
            "game_id": script.game_id,
            "source_label": SCRIPTED_SOURCE_LABEL,
            "consensuses": consensuses,
        },
    )

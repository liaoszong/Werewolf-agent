from __future__ import annotations

import json
from typing import Any

from werewolf_eval.game_engine import AgentAction, AgentObservation
from werewolf_eval.provider_contract import (
    ProviderFailure,
    ProviderRequest,
)


class ProviderActionError(ValueError):
    def __init__(self, failure: ProviderFailure) -> None:
        super().__init__(failure.reason)
        self.failure = failure


ALLOWED_ACTIONS_BY_ROLE_PHASE: dict[tuple[str, str], list[str]] = {
    ("seer", "night"): ["seer_check"],
    ("witch", "night"): ["witch_save", "witch_kill"],
    ("werewolf", "night"): ["werewolf_kill"],
    ("seer", "day"): ["player_vote"],
    ("witch", "day"): ["player_vote"],
    ("villager", "day"): ["player_vote"],
    ("werewolf", "day"): ["player_vote"],
}


class ProviderAgent:
    def __init__(
        self,
        player_id: str,
        provider: Any,
        override_raw_content: str | None = None,
        failure_mode: str | None = None,
    ) -> None:
        self._player_id = player_id
        self._provider = provider
        self._override_raw_content = override_raw_content
        self._failure_mode = failure_mode
        self._failures: list[ProviderFailure] = []

    @property
    def provider(self) -> Any:
        return self._provider

    @property
    def failures(self) -> list[ProviderFailure]:
        return list(self._failures)

    def decide(self, observation: AgentObservation | dict[str, Any]) -> AgentAction:
        if isinstance(observation, dict):
            observation = AgentObservation(
                game_id=str(observation["game_id"]),
                player_id=str(observation["player_id"]),
                role=str(observation["role"]),
                team=str(observation["team"]),
                phase=str(observation["phase"]),
                round=int(observation["round"]),
                alive_players=list(observation["alive_players"]),
                public_event_ids=list(observation.get("public_event_ids", [])),
                private_event_ids=list(observation.get("private_event_ids", [])),
                known_roles=dict(observation.get("known_roles", {})),
            )

        game_id = observation.game_id
        actor = observation.player_id
        phase = observation.phase
        round_num = observation.round
        role = observation.role

        allowed_actions = ALLOWED_ACTIONS_BY_ROLE_PHASE.get((role, phase), [])
        allowed_targets = list(observation.alive_players)

        request_id = f"{game_id}_r{round_num:02d}_{actor}"

        if self._failure_mode == "timeout":
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind="timeout",
                reason=f"{actor} timed out",
            )
            raise ProviderActionError(failure)

        request = ProviderRequest(
            request_id=request_id,
            game_id=game_id,
            actor=actor,
            phase=phase,
            round=round_num,
            observation=observation.to_dict(),
            allowed_actions=allowed_actions,
            allowed_targets=allowed_targets,
        )

        try:
            response = self._provider.respond(request)
        except Exception as exc:
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind="timeout",
                reason=f"provider error: {exc}",
            )
            raise ProviderActionError(failure) from exc

        raw = self._override_raw_content if self._override_raw_content is not None else response.raw_content

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind="parse_failure",
                reason=f"provider response was not valid JSON: {exc}",
            )
            raise ProviderActionError(failure) from exc

        if not isinstance(parsed, dict):
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind="parse_failure",
                reason="provider response is not a JSON object",
            )
            raise ProviderActionError(failure)

        action_name = parsed.get("action")
        target = parsed.get("target")

        # All five fields are mandatory — no fallback defaults allowed.
        # Missing fields must produce a ProviderFailure, not a repaired valid action.
        _REQUIRED_FIELDS = ("action", "target", "reason_summary", "decision_type", "confidence")
        missing = [f for f in _REQUIRED_FIELDS if f not in parsed]
        if missing:
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind="parse_failure",
                reason=f"provider response missing required field(s): {', '.join(missing)}",
            )
            raise ProviderActionError(failure)

        reason_summary = parsed["reason_summary"]
        decision_type = parsed["decision_type"]
        confidence_raw = parsed["confidence"]

        if not action_name or not isinstance(action_name, str):
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind="parse_failure",
                reason="provider response missing valid 'action' field",
            )
            raise ProviderActionError(failure)

        # confidence must be a valid number
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind="parse_failure",
                reason=f"provider response has invalid confidence: {confidence_raw!r} is not a number",
            )
            raise ProviderActionError(failure)

        if action_name not in allowed_actions:
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind="invalid_action",
                reason=f"action '{action_name}' not in allowed_actions {allowed_actions}",
                target=target,
            )
            raise ProviderActionError(failure)

        if target not in allowed_targets:
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind="invalid_action",
                reason=f"target '{target}' not in allowed_targets {allowed_targets}",
                target=target,
            )
            raise ProviderActionError(failure)

        return AgentAction(
            actor=actor,
            action=action_name,
            target=target,
            phase=phase,
            round=round_num,
            reason_summary=reason_summary,
            decision_type=decision_type,
            confidence=confidence,
            source_label=response.source_label,
        )

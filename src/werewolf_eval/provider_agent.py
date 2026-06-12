from __future__ import annotations

import json
from typing import Any

from werewolf_eval.action_runtime import RoleAbilityRegistry, rules_v1_2
from werewolf_eval.game_engine import AgentAction, AgentObservation
from werewolf_eval.provider_contract import (
    ProviderFailure,
    ProviderRequest,
    classify_provider_failure_kind,
)


class ProviderActionError(ValueError):
    def __init__(self, failure: ProviderFailure) -> None:
        super().__init__(failure.reason)
        self.failure = failure


# Single source of allowed actions (replaced the static ALLOWED_ACTIONS_BY_ROLE_PHASE
# map). decide() reaches wolf-kill/seer-check/guard-protect/day-vote — the witch and
# speeches call provider.respond() directly — and rules_v1_2 is a backward-compatible
# superset (hunter + guard): boards without them get identical lists (same order), so
# prompt bytes are unchanged. Built once at import (the ruleset builder is pure/cheap).
_ALLOWED_ACTIONS_RULESET = rules_v1_2()
_ALLOWED_ACTIONS_RULESET_VERSION = _ALLOWED_ACTIONS_RULESET.rules_version
_ALLOWED_ACTIONS_REGISTRY = RoleAbilityRegistry(_ALLOWED_ACTIONS_RULESET)
# External engine phase -> registry phase. The engine emits 'day' for votes; the registry
# keys day votes under 'day_vote'. MUST map: an unmapped phase degrades to [] (registry
# hardening), which would silently reject every vote (contract A / audit B4-1).
_REGISTRY_PHASE = {"day": "day_vote"}


class ProviderAgent:
    def __init__(
        self,
        player_id: str,
        provider: Any,
        override_raw_content: str | None = None,
        failure_mode: str | None = None,
        runtime_events: Any | None = None,
    ) -> None:
        self._player_id = player_id
        self._provider = provider
        self._override_raw_content = override_raw_content
        self._failure_mode = failure_mode
        self._runtime_events = runtime_events
        self._failures: list[ProviderFailure] = []
        self._last_response: Any | None = None

    @property
    def provider(self) -> Any:
        return self._provider

    @property
    def failures(self) -> list[ProviderFailure]:
        return list(self._failures)

    @property
    def last_response(self) -> Any | None:
        """The most recent ProviderResponse (P2-A-2: lets the engine read
        per-turn source_label / token_usage evidence). None before any call."""
        return self._last_response

    def _emit_provider_event(
        self,
        kind: str,
        *,
        round: int,
        phase: str,
        actor: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        """Emit an event via the optional runtime event writer."""
        if self._runtime_events is not None:
            self._runtime_events.emit(
                kind,
                round=round,
                phase=phase,
                actor=actor,
                visibility="internal",
                payload=payload,
            )

    def decide(
        self,
        observation: AgentObservation | dict[str, Any],
        observation_text: str = "",
        response_kind: str = "action",
        max_output_tokens: int | None = None,
        prompt_version: str = "prompt_v1",
        board_card: str = "",
    ) -> AgentAction:
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

        allowed_actions = _ALLOWED_ACTIONS_REGISTRY.allowed_actions(
            role, _REGISTRY_PHASE.get(phase, phase)
        )
        allowed_targets = list(observation.alive_players)

        # C12-01: day-phase action = vote; append _vote so the ProviderRequest
        # request_id matches the engine's turn request_id and never collides with
        # the same actor's night action (same bare stem).
        _req_suffix = "_vote" if phase == "day" else ""
        request_id = f"{game_id}_r{round_num:02d}_{actor}{_req_suffix}"

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
            self._emit_provider_event(
                "provider_timeout",
                round=round_num,
                phase=phase,
                actor=actor,
                payload={"request_id": request_id, "kind": "timeout"},
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
            observation_text=observation_text,
            response_kind=response_kind,
            max_output_tokens=max_output_tokens,
            prompt_version=prompt_version,
            board_card=board_card,
        )

        self._emit_provider_event(
            "provider_request_prepared",
            round=round_num,
            phase=phase,
            actor=actor,
            payload={
                "request_id": request_id,
                "allowed_actions": allowed_actions,
                "allowed_targets": allowed_targets,
            },
        )

        self._last_response = None
        try:
            response = self._provider.respond(request)
            self._last_response = response
        except Exception as exc:
            # B34-10: classify the transport/respond exception into a structured
            # kind (budget_exhausted / transport_error / auth_failed /
            # provider_error) instead of flattening everything to "timeout". The
            # original message stays in `reason`, so substring detectors that
            # predate this (deepseek_launcher._failure_is_budget_exhausted) and
            # diagnostics keep working.
            kind = classify_provider_failure_kind(exc)
            failure = ProviderFailure(
                request_id=request_id,
                game_id=game_id,
                round=round_num,
                phase=phase,
                actor=actor,
                kind=kind,
                reason=f"provider error: {exc}",
            )
            self._emit_provider_event(
                "provider_failed",
                round=round_num,
                phase=phase,
                actor=actor,
                payload={"request_id": request_id, "kind": kind, "reason": str(exc)},
            )
            raise ProviderActionError(failure) from exc

        self._emit_provider_event(
            "provider_response_received",
            round=round_num,
            phase=phase,
            actor=actor,
            payload={
                "request_id": request_id,
                "provider_name": response.provider_name,
                "latency_ms": response.latency_ms,
                "token_usage": dict(response.token_usage),
            },
        )

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
            self._emit_provider_event(
                "provider_parse_failed",
                round=round_num,
                phase=phase,
                actor=actor,
                payload={"request_id": request_id, "kind": "parse_failure", "reason": str(exc)},
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
            self._emit_provider_event(
                "provider_parse_failed",
                round=round_num,
                phase=phase,
                actor=actor,
                payload={"request_id": request_id, "kind": "parse_failure", "reason": "not a JSON object"},
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
            self._emit_provider_event(
                "provider_parse_failed",
                round=round_num,
                phase=phase,
                actor=actor,
                payload={"request_id": request_id, "kind": "parse_failure", "reason": f"missing fields: {', '.join(missing)}"},
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
            self._emit_provider_event(
                "provider_parse_failed",
                round=round_num,
                phase=phase,
                actor=actor,
                payload={"request_id": request_id, "kind": "parse_failure", "reason": "missing valid action field"},
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
            self._emit_provider_event(
                "provider_parse_failed",
                round=round_num,
                phase=phase,
                actor=actor,
                payload={"request_id": request_id, "kind": "parse_failure", "reason": f"invalid confidence: {confidence_raw!r}"},
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
            self._emit_provider_event(
                "provider_action_invalid",
                round=round_num,
                phase=phase,
                actor=actor,
                payload={
                    "request_id": request_id,
                    "kind": "invalid_action",
                    "action": action_name,
                    "target": target,
                    "reason": f"action '{action_name}' not in allowed_actions",
                },
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
            self._emit_provider_event(
                "provider_action_invalid",
                round=round_num,
                phase=phase,
                actor=actor,
                payload={
                    "request_id": request_id,
                    "kind": "invalid_action",
                    "action": action_name,
                    "target": target,
                    "reason": f"target '{target}' not in allowed_targets",
                },
            )
            raise ProviderActionError(failure)

        self._emit_provider_event(
            "provider_parse_succeeded",
            round=round_num,
            phase=phase,
            actor=actor,
            payload={"request_id": request_id},
        )

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

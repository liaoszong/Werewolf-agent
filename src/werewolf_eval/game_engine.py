from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from werewolf_eval.role_visibility import private_refs_for_role, public_refs
from werewolf_eval.runtime_events import (
    build_god_snapshot,
    build_role_projection_snapshot,
)

MOCK_AGENT_SOURCE_LABEL = "[deterministic mock agent output]"
CONSENSUS_SOURCE_LABEL = "[deterministic mock agent output]"


def build_failure(game_id: str, round_number: int, phase: str, actor: str, kind: str, reason: str, target: str | None = None) -> dict:
    return {
        "game_id": game_id,
        "round": round_number,
        "phase": phase,
        "actor": actor,
        "kind": kind,
        "target": target,
        "reason": reason,
        "repaired_to_valid_action": False,
    }


@dataclass(frozen=True)
class EnginePlayer:
    player_id: str
    role: str
    team: str


@dataclass(frozen=True)
class GameConfig:
    game_id: str
    players: list[EnginePlayer]


@dataclass(frozen=True)
class AgentObservation:
    game_id: str
    player_id: str
    role: str
    team: str
    phase: str
    round: int
    alive_players: list[str]
    public_event_ids: list[str]
    private_event_ids: list[str]
    known_roles: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "player_id": self.player_id,
            "role": self.role,
            "team": self.team,
            "phase": self.phase,
            "round": self.round,
            "alive_players": list(self.alive_players),
            "public_event_ids": list(self.public_event_ids),
            "private_event_ids": list(self.private_event_ids),
            "known_roles": dict(self.known_roles),
        }


@dataclass(frozen=True)
class AgentAction:
    actor: str
    action: str
    target: str
    phase: str
    round: int
    reason_summary: str
    decision_type: str
    confidence: float = 1.0
    source_label: str = MOCK_AGENT_SOURCE_LABEL
    visible_info_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EngineOutputs:
    game_log: dict[str, Any]
    decision_log: dict[str, Any]
    consensus_log: dict[str, Any] | None = None
    failure_audit: dict[str, Any] | None = None


_DEFAULT_SEAT_ORDER = ("p1", "p2", "p3", "p4", "p5", "p6")


def _team_for_role(role: str) -> str:
    from werewolf_eval.observer_protocol import KNOWN_ROLE_TEAMS

    return KNOWN_ROLE_TEAMS.get(role, "werewolf" if role == "werewolf" else "villager")


def build_default_config(game_id: str = "g1b_mock_001", seat_roles: dict[str, str] | None = None) -> GameConfig:
    if seat_roles is None:
        return GameConfig(
            game_id=game_id,
            players=[
                EnginePlayer("p1", "werewolf", "werewolf"),
                EnginePlayer("p2", "werewolf", "werewolf"),
                EnginePlayer("p3", "seer", "villager"),
                EnginePlayer("p4", "witch", "villager"),
                EnginePlayer("p5", "villager", "villager"),
                EnginePlayer("p6", "villager", "villager"),
            ],
        )
    # seat_roles given: per-seat role override (multiset preserved upstream). team derives
    # from the ruleset role table; seat_roles == default -> identical board.
    return GameConfig(
        game_id=game_id,
        players=[
            EnginePlayer(pid, seat_roles[pid], _team_for_role(seat_roles[pid]))
            for pid in _DEFAULT_SEAT_ORDER
        ],
    )


class MockAgent:
    def __init__(self, player_id: str) -> None:
        self.player_id = player_id

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

        key = (observation.player_id, observation.phase, observation.round)
        actions: dict[tuple[str, str, int], AgentAction] = {
            ("p3", "night", 1): AgentAction(
                actor="p3", action="seer_check", target="p1",
                phase="night", round=1, reason_summary="p3 seer checks p1",
                decision_type="inference_based",
            ),
            ("p4", "night", 1): AgentAction(
                actor="p4", action="witch_save", target="p5",
                phase="night", round=1, reason_summary="p4 witch saves p5",
                decision_type="inference_based",
            ),
            ("p3", "day", 1): AgentAction(
                actor="p3", action="player_vote", target="p1",
                phase="day", round=1, reason_summary="p3 votes p1 based on seer result",
                decision_type="inference_based",
            ),
            ("p4", "day", 1): AgentAction(
                actor="p4", action="player_vote", target="p1",
                phase="day", round=1, reason_summary="p4 follows vote on p1",
                decision_type="inference_based",
            ),
            ("p5", "day", 1): AgentAction(
                actor="p5", action="player_vote", target="p1",
                phase="day", round=1, reason_summary="p5 follows vote on p1",
                decision_type="inference_based",
            ),
            ("p6", "day", 1): AgentAction(
                actor="p6", action="player_vote", target="p1",
                phase="day", round=1, reason_summary="p6 follows vote on p1",
                decision_type="inference_based",
            ),
            ("p4", "day", 2): AgentAction(
                actor="p4", action="player_vote", target="p2",
                phase="day", round=2, reason_summary="p4 votes p2",
                decision_type="inference_based",
            ),
            ("p5", "day", 2): AgentAction(
                actor="p5", action="player_vote", target="p2",
                phase="day", round=2, reason_summary="p5 follows vote on p2",
                decision_type="inference_based",
            ),
            ("p6", "day", 2): AgentAction(
                actor="p6", action="player_vote", target="p2",
                phase="day", round=2, reason_summary="p6 follows vote on p2",
                decision_type="inference_based",
            ),
        }

        if key not in actions:
            raise ValueError(
                f"no deterministic mock action for {observation.player_id} {observation.phase} {observation.round}"
            )
        return actions[key]


class WolfTeamMockAgent:
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

        key = (observation.phase, observation.round)
        actions: dict[tuple[str, int], AgentAction] = {
            ("night", 1): AgentAction(
                actor="wolf_team", action="werewolf_kill", target="p5",
                phase="night", round=1, reason_summary="wolf team kills p5",
                decision_type="team_coordinated",
            ),
            ("night", 2): AgentAction(
                actor="wolf_team", action="werewolf_kill", target="p3",
                phase="night", round=2, reason_summary="wolf team kills seer p3",
                decision_type="team_coordinated",
            ),
        }

        if key not in actions:
            raise ValueError(
                f"no deterministic mock action for wolf_team {observation.phase} {observation.round}"
            )
        return actions[key]


class GameEngine:
    def __init__(
        self,
        config: GameConfig,
        agents: dict[str, Any] | None = None,
        wolf_agent: Any | None = None,
        source_label: str | None = None,
        runtime_events: Any | None = None,
    ) -> None:
        self._config = config
        self._players_by_id: dict[str, EnginePlayer] = {
            p.player_id: p for p in config.players
        }
        if agents is not None:
            self._mock_agents = dict(agents)
        else:
            self._mock_agents = {
                p.player_id: MockAgent(p.player_id) for p in config.players
            }
        self._wolf_agent = wolf_agent if wolf_agent is not None else WolfTeamMockAgent()
        self._source_label = source_label if source_label is not None else MOCK_AGENT_SOURCE_LABEL
        self._runtime_events = runtime_events
        self._events: list[dict[str, Any]] = []
        self._decisions: list[dict[str, Any]] = []
        self._alive: set[str] = set(self._players_by_id.keys())
        self._current_round: int = 0
        self._current_phase: str = "setup"

    @classmethod
    def from_config(
        cls,
        config: GameConfig,
        agents: dict[str, Any] | None = None,
        wolf_agent: Any | None = None,
        source_label: str | None = None,
        runtime_events: Any | None = None,
    ) -> "GameEngine":
        return cls(config, agents=agents, wolf_agent=wolf_agent, source_label=source_label, runtime_events=runtime_events)

    def observation_for(self, player_id: str) -> AgentObservation:
        player = self._players_by_id[player_id]
        known_roles: dict[str, str] = {player_id: player.role}

        if player.team == "werewolf":
            for pid, p in self._players_by_id.items():
                if p.team == "werewolf":
                    known_roles[pid] = p.role

        public_event_ids = public_refs(self._events)
        private_event_ids = private_refs_for_role(self._events, player.role, team=player.team)

        return AgentObservation(
            game_id=self._config.game_id,
            player_id=player_id,
            role=player.role,
            team=player.team,
            phase=self._current_phase,
            round=self._current_round,
            alive_players=sorted(self._alive),
            public_event_ids=public_event_ids,
            private_event_ids=private_event_ids,
            known_roles=known_roles,
        )

    def _resolve_wolf_consensus(self, game_id: str, round_num: int, phase: str, wolf_players: list[str], alive: set[str], mode: str, events: list[dict]) -> tuple[dict | None, list[dict], str | None]:
        """Resolve wolf consensus for a night phase. Returns (consensus_entry, failures, resolved_target)."""
        failures: list[dict] = []
        consensus_id = f"{game_id}_consensus_r{round_num:02d}"
        c_proposals: list[dict] = []
        c_responses: list[dict] = []
        valid_targets: list[tuple[str, str]] = []
        failed_participants: list[str] = []

        for i, wolf_id in enumerate(wolf_players):
            if mode == "g1f_provider_consensus":
                player = self._players_by_id[wolf_id]
                known_roles = {
                    pid: self._players_by_id[pid].role
                    for pid in wolf_players
                    if pid in alive and self._players_by_id[pid].team == "werewolf"
                }
                public_event_ids = public_refs(events)
                private_event_ids = private_refs_for_role(events, player.role, team=player.team)

                obs = AgentObservation(
                    game_id=game_id,
                    player_id=wolf_id,
                    role=player.role,
                    team=player.team,
                    phase=phase,
                    round=round_num,
                    alive_players=sorted(alive),
                    public_event_ids=public_event_ids,
                    private_event_ids=private_event_ids,
                    known_roles=known_roles,
                )
                try:
                    action = self._mock_agents[wolf_id].decide(obs)
                except Exception as exc:
                    failures.append(build_failure(game_id, round_num, phase, wolf_id, "agent_error", f"{wolf_id} raised {type(exc).__name__}: {exc}"))
                    failed_participants.append(wolf_id)
                    continue

                if action.actor != wolf_id:
                    failures.append(build_failure(game_id, round_num, phase, wolf_id, "invalid_action", f"{wolf_id} returned actor={action.actor}", target=action.target))
                    failed_participants.append(wolf_id)
                    continue

                if action.action != "werewolf_kill":
                    failures.append(build_failure(game_id, round_num, phase, wolf_id, "invalid_action", f"{wolf_id} returned action={action.action} not werewolf_kill", target=action.target))
                    failed_participants.append(wolf_id)
                    continue

                if action.phase != phase:
                    failures.append(build_failure(game_id, round_num, phase, wolf_id, "invalid_action", f"{wolf_id} returned phase={action.phase}", target=action.target))
                    failed_participants.append(wolf_id)
                    continue

                if action.round != round_num:
                    failures.append(build_failure(game_id, round_num, phase, wolf_id, "invalid_action", f"{wolf_id} returned round={action.round}", target=action.target))
                    failed_participants.append(wolf_id)
                    continue

                if not (isinstance(action.target, str) and action.target in alive and action.target not in set(wolf_players)):
                    failures.append(build_failure(game_id, round_num, phase, wolf_id, "invalid_action", f"{wolf_id} proposed invalid target {action.target}", target=action.target))
                    failed_participants.append(wolf_id)
                    continue

                target = action.target
                valid_targets.append((wolf_id, target))
                c_proposals.append({
                    "proposal_id": i + 1,
                    "proposer": wolf_id,
                    "proposed_target": target,
                    "visible_info_refs": list(action.visible_info_refs),
                    "reason_summary": action.reason_summary,
                    "confidence": action.confidence,
                    "action_round": 1,
                })
                continue

            if mode == "g1c_timeout_parse_failure" and round_num == 1 and i == 0:
                failures.append(build_failure(game_id, round_num, phase, wolf_id, "timeout", f"{wolf_id} timed out during night consensus"))
                failed_participants.append(wolf_id)
                continue

            if mode == "g1c_timeout_parse_failure" and round_num == 1 and i == 1:
                failures.append(build_failure(game_id, round_num, phase, wolf_id, "parse_failure", f"{wolf_id} produced unparseable action"))
                failed_participants.append(wolf_id)
                continue

            if mode == "g1c_invalid_wolf_action" and round_num == 1 and i == 0:
                invalid_target = "p99"
                failures.append(build_failure(game_id, round_num, phase, wolf_id, "invalid_action", f"{wolf_id} proposed invalid target {invalid_target}", target=invalid_target))
                failed_participants.append(wolf_id)
                continue

            if mode == "g1c_split_wolf_vote" and round_num == 1:
                target = "p5" if i == 0 else "p6"
            else:
                target = "p5" if round_num == 1 else "p3"

            valid_targets.append((wolf_id, target))
            c_proposals.append({
                "proposal_id": i + 1,
                "proposer": wolf_id,
                "proposed_target": target,
                "visible_info_refs": public_refs(events),
                "reason_summary": f"{wolf_id} proposes {target}",
                "confidence": 1.0,
                "action_round": 1,
            })

        if not valid_targets:
            return None, failures, None

        unique_targets = set(t for _, t in valid_targets)
        if len(unique_targets) == 1:
            target = valid_targets[0][1]
            status = "consensus"
        else:
            target = valid_targets[0][1]
            status = "coordinator_tie_break"
            failures.append(build_failure(game_id, round_num, phase, "wolf_team", "wolf_consensus_failure", f"split vote: targets {sorted(unique_targets)}", target=target))

        supporters = [w for w, t in valid_targets if t == target]
        dissenters = [w for w, t in valid_targets if t != target]

        if failed_participants:
            dissenters = dissenters + failed_participants
            if status == "consensus":
                status = "coordinator_tie_break"

        primary_proposer = valid_targets[0][0]
        c_proposals = [{
            "proposal_id": 1,
            "proposer": primary_proposer,
            "proposed_target": target,
            "visible_info_refs": public_refs(events),
            "reason_summary": f"{primary_proposer} proposes {target}",
            "confidence": 1.0,
            "action_round": 1,
        }]
        c_responses: list[dict] = []
        for j, (w, _) in enumerate(valid_targets):
            if w == primary_proposer:
                continue
            resp_type = "support_with_reason" if w in supporters else "oppose_with_reason"
            c_responses.append({
                "response_id": j + 1,
                "to_proposal_id": 1,
                "responder": w,
                "response_type": resp_type,
                "reason_summary": f"{w} {'supports' if w in supporters else 'opposes'} {primary_proposer} proposal",
                "visible_info_refs": [],
                "action_round": 1,
            })

        consensus_entry = {
            "consensus_id": consensus_id,
            "game_id": game_id,
            "round": round_num,
            "phase": phase,
            "team": "werewolf",
            "participants": wolf_players,
            "coordinator": wolf_players[0],
            "max_rounds": 1,
            "actual_rounds": 1,
            "status": status,
            "proposals": c_proposals,
            "responses": c_responses,
            "final_decision": {
                "target": target,
                "decision_type": status,
                "primary_proposer": primary_proposer,
                "supporters": supporters,
                "dissenters": dissenters,
                "resolution_round": 1,
            },
        }
        return consensus_entry, failures, target

    def run(self, mode: str = "g1b_default") -> EngineOutputs:
        game_id = self._config.game_id
        events: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []
        alive: set[str] = {p.player_id for p in self._config.players}
        d_counter = 0
        is_consensus_mode = mode.startswith("g1c_") or mode == "g1f_provider_consensus"
        consensus_entries: list[dict[str, Any]] = []
        failure_records: list[dict[str, Any]] = []

        def _event(seq: int, phase: str, rnd: int, etype: str, actor: str, target: str, visibility: str, summary: str, refs: list[str] | None = None) -> dict[str, Any]:
            return {
                "event_id": f"{game_id}_e{seq:03d}",
                "sequence": seq,
                "round": rnd,
                "phase": phase,
                "type": etype,
                "actor": actor,
                "target": target,
                "visibility": visibility,
                "data": {"summary": summary, "visible_info_refs": refs if refs is not None else []},
            }

        _event_seq = 1
        def _emit(phase: str, rnd: int, etype: str, actor: str, target: str, visibility: str, summary: str, refs: list[str] | None = None) -> dict[str, Any]:
            nonlocal _event_seq
            evt = _event(_event_seq, phase, rnd, etype, actor, target, visibility, summary, refs)
            events.append(evt)
            _event_seq += 1
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "game_event_emitted",
                    round=rnd,
                    phase=phase,
                    actor=actor,
                    visibility=visibility,
                    payload={"event_id": evt["event_id"], "type": etype},
                )
            return evt

        def _decision(actor: str, scope: str, phase: str, action: str, target: str, dtype: str, reason: str, refs: list[str] | None = None, consensus_id: str | None = None) -> dict[str, Any]:
            nonlocal d_counter
            d_counter += 1
            return {
                "decision_id": f"{game_id}_d{d_counter:03d}",
                "actor": actor,
                "decision_scope": scope,
                "consensus_id": consensus_id,
                "phase": phase,
                "action": action,
                "target": target,
                "visible_info_refs": refs if refs is not None else [],
                "reason_summary": reason,
                "decision_type": dtype,
                "confidence": 1.0,
                "strategy_tag": None,
            }

        def _public_refs() -> list[str]:
            return public_refs(events)

        def _private_refs_for_role(role: str, team: str | None = None) -> list[str]:
            return private_refs_for_role(events, role, team=team)

        def _private_refs(player_id: str) -> list[str]:
            p = self._players_by_id[player_id]
            return _private_refs_for_role(p.role, p.team)

        def _wolf_obs(phase: str, rnd: int, wolf_players: list[str]) -> AgentObservation:
            obs = AgentObservation(
                game_id=game_id, player_id="wolf_team", role="werewolf", team="werewolf",
                phase=phase, round=rnd, alive_players=sorted(alive),
                public_event_ids=_public_refs(),
                # R-18: filter to the werewolf role's visible set (all + werewolf_team) —
                # NOT every event id. Copying all ids leaked seer/witch event ids/counts
                # (metadata) into the wolf role-projection snapshot in g1b/mock mode.
                private_event_ids=_private_refs_for_role("werewolf", "werewolf"),
                known_roles={pid: self._players_by_id[pid].role for pid in wolf_players},
            )
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "observation_built",
                    round=rnd, phase=phase, actor="wolf_team",
                    visibility="internal",
                )
            return obs

        def _player_obs(player_id: str, phase: str, rnd: int) -> AgentObservation:
            p = self._players_by_id[player_id]
            obs = AgentObservation(
                game_id=game_id, player_id=player_id, role=p.role, team=p.team,
                phase=phase, round=rnd, alive_players=sorted(alive),
                public_event_ids=_public_refs(),
                private_event_ids=_private_refs(player_id),
                known_roles={player_id: p.role},
            )
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "observation_built",
                    round=rnd, phase=phase, actor=player_id,
                    visibility="internal",
                )
            return obs

        # Event 1: setup
        if self._runtime_events is not None:
            self._runtime_events.emit(
                "run_started",
                round=0, phase="setup", actor="system",
                visibility="internal",
                payload={"game_id": game_id},
            )
            self._runtime_events.emit(
                "phase_started",
                round=0, phase="setup", actor="system",
                visibility="internal",
                payload={"phase": "setup"},
            )
        _emit("setup", 0, "role_assignment", "system", "none", "public",
              "Roles assigned to all 6 players.")
        # God snapshot after setup
        if self._runtime_events is not None:
            players_list = [
                {"player_id": p.player_id, "role": p.role, "team": p.team}
                for p in self._config.players
            ]
            snap = build_god_snapshot(
                run_id=game_id,
                game_id=game_id,
                round=0,
                phase="setup",
                players=players_list,
                alive_players=sorted(self._players_by_id.keys()),
                public_event_ids=[],
                private_event_ids=[],
            )
            self._runtime_events.write_snapshot(
                "setup_god_view", snap,
                visibility="internal", round=0, phase="setup", actor="system",
            )

        # Night 1: wolf kill
        if self._runtime_events is not None:
            self._runtime_events.emit(
                "phase_started",
                round=1, phase="night", actor="system",
                visibility="internal",
                payload={"phase": "night"},
            )
        if is_consensus_mode:
            n1_wolves = ["p1", "p2"]
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "consensus_started",
                    round=1, phase="night", actor="system",
                    visibility="internal",
                    payload={"mode": mode, "participants": n1_wolves},
                )
            c_entry, c_failures, c_target = self._resolve_wolf_consensus(game_id, 1, "night", n1_wolves, alive, mode, events)
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "consensus_resolved",
                    round=1, phase="night", actor="system",
                    visibility="internal",
                    payload={"resolved": c_target is not None, "target": c_target},
                )
            if c_entry is not None:
                consensus_entries.append(c_entry)
            failure_records.extend(c_failures)
            if c_target is not None:
                cid = c_entry["consensus_id"] if c_entry is not None else None
                d_actor = c_entry["coordinator"] if mode == "g1f_provider_consensus" else "wolf_team"
                decisions.append(_decision(d_actor, "team", "night", "werewolf_kill", c_target, "team_coordinated", f"wolf team kills {c_target}", consensus_id=cid))
                _emit("night", 1, "werewolf_kill", d_actor, c_target, "werewolf_team", f"Wolf team kills {c_target}.")
        else:
            obs_wolf_n1 = _wolf_obs("night", 1, ["p1", "p2"])
            if self._runtime_events is not None:
                snap = build_role_projection_snapshot(run_id=game_id, observation=obs_wolf_n1)
                self._runtime_events.write_snapshot(
                    "obs_wolf_n1", snap,
                    visibility="internal", round=1, phase="night", actor="wolf_team",
                )
            wa1 = self._wolf_agent.decide(obs_wolf_n1)
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "agent_action_selected",
                    round=1, phase="night", actor=wa1.actor,
                    visibility="internal",
                    payload={"action": wa1.action, "target": wa1.target},
                )
            decisions.append(_decision(wa1.actor, "team", wa1.phase, wa1.action, wa1.target, wa1.decision_type, wa1.reason_summary))
            _emit("night", 1, wa1.action, wa1.actor, wa1.target, "werewolf_team", f"Wolf team kills {wa1.target}.")

        # Night 1: seer check
        obs_p3_n1 = _player_obs("p3", "night", 1)
        if self._runtime_events is not None:
            snap = build_role_projection_snapshot(run_id=game_id, observation=obs_p3_n1)
            self._runtime_events.write_snapshot(
                "obs_p3_n1", snap,
                visibility="internal", round=1, phase="night", actor="p3",
            )
        sa1 = self._mock_agents["p3"].decide(obs_p3_n1)
        if self._runtime_events is not None:
            self._runtime_events.emit(
                "agent_action_selected",
                round=1, phase="night", actor=sa1.actor,
                visibility="internal",
                payload={"action": sa1.action, "target": sa1.target},
            )
        decisions.append(_decision(sa1.actor, "single", sa1.phase, sa1.action, sa1.target, sa1.decision_type, sa1.reason_summary))
        _emit("night", 1, sa1.action, sa1.actor, sa1.target, "seer", f"Seer p3 checks p1, result: werewolf.")

        # Night 1: witch save
        obs_p4_n1 = _player_obs("p4", "night", 1)
        if self._runtime_events is not None:
            snap = build_role_projection_snapshot(run_id=game_id, observation=obs_p4_n1)
            self._runtime_events.write_snapshot(
                "obs_p4_n1", snap,
                visibility="internal", round=1, phase="night", actor="p4",
            )
        wa2 = self._mock_agents["p4"].decide(obs_p4_n1)
        if self._runtime_events is not None:
            self._runtime_events.emit(
                "agent_action_selected",
                round=1, phase="night", actor=wa2.actor,
                visibility="internal",
                payload={"action": wa2.action, "target": wa2.target},
            )
        decisions.append(_decision(wa2.actor, "single", wa2.phase, wa2.action, wa2.target, wa2.decision_type, wa2.reason_summary))
        _emit("night", 1, wa2.action, wa2.actor, wa2.target, "witch", f"Witch p4 saves p5.")

        # Day 1: votes (p3, p4, p5, p6 → p1)
        if self._runtime_events is not None:
            self._runtime_events.emit(
                "phase_started",
                round=1, phase="day", actor="system",
                visibility="internal",
                payload={"phase": "day"},
            )
        day1_voters = ["p3", "p4", "p5", "p6"]
        day1_refs = _public_refs()
        for vid in day1_voters:
            obs_vid = _player_obs(vid, "day", 1)
            if self._runtime_events is not None:
                snap = build_role_projection_snapshot(run_id=game_id, observation=obs_vid)
                self._runtime_events.write_snapshot(
                    f"obs_{vid}_d1", snap,
                    visibility="internal", round=1, phase="day", actor=vid,
                )
            va = self._mock_agents[vid].decide(obs_vid)
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "agent_action_selected",
                    round=1, phase="day", actor=va.actor,
                    visibility="internal",
                    payload={"action": va.action, "target": va.target},
                )
            decisions.append(_decision(va.actor, "single", va.phase, va.action, va.target, va.decision_type, va.reason_summary, refs=day1_refs))
            _emit("day", 1, va.action, va.actor, va.target, "public", f"{vid} votes {va.target}.")

        # p1 eliminated
        _emit("day", 1, "player_eliminated", "system", "p1", "all", "p1 eliminated by vote.")
        _emit("day", 1, "role_revealed", "system", "p1", "all", "p1 revealed as werewolf.")
        alive.discard("p1")

        # Night 2: wolf kill
        if self._runtime_events is not None:
            self._runtime_events.emit(
                "phase_started",
                round=2, phase="night", actor="system",
                visibility="internal",
                payload={"phase": "night"},
            )
        if is_consensus_mode:
            n2_wolves = ["p2"]
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "consensus_started",
                    round=2, phase="night", actor="system",
                    visibility="internal",
                    payload={"mode": mode, "participants": n2_wolves},
                )
            c_entry, c_failures, c_target = self._resolve_wolf_consensus(game_id, 2, "night", n2_wolves, alive, mode, events)
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "consensus_resolved",
                    round=2, phase="night", actor="system",
                    visibility="internal",
                    payload={"resolved": c_target is not None, "target": c_target},
                )
            if c_entry is not None:
                consensus_entries.append(c_entry)
            failure_records.extend(c_failures)
            if c_target is not None:
                cid = c_entry["consensus_id"] if c_entry is not None else None
                d_actor = c_entry["coordinator"] if mode == "g1f_provider_consensus" else "wolf_team"
                decisions.append(_decision(d_actor, "team", "night", "werewolf_kill", c_target, "team_coordinated", f"wolf team kills {c_target}", consensus_id=cid))
                _emit("night", 2, "werewolf_kill", d_actor, c_target, "werewolf_team", f"Wolf team kills {c_target}.")
        else:
            obs_wolf_n2 = _wolf_obs("night", 2, ["p2"])
            if self._runtime_events is not None:
                snap = build_role_projection_snapshot(run_id=game_id, observation=obs_wolf_n2)
                self._runtime_events.write_snapshot(
                    "obs_wolf_n2", snap,
                    visibility="internal", round=2, phase="night", actor="wolf_team",
                )
            wa3 = self._wolf_agent.decide(obs_wolf_n2)
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "agent_action_selected",
                    round=2, phase="night", actor=wa3.actor,
                    visibility="internal",
                    payload={"action": wa3.action, "target": wa3.target},
                )
            decisions.append(_decision(wa3.actor, "team", wa3.phase, wa3.action, wa3.target, wa3.decision_type, wa3.reason_summary))
            _emit("night", 2, wa3.action, wa3.actor, wa3.target, "werewolf_team", f"Wolf team kills {wa3.target}.")
        _emit("night", 2, "player_died", "system", "p3", "all", "p3 died during the night.")
        alive.discard("p3")

        # Day 2: votes (p4, p5, p6 → p2)
        if self._runtime_events is not None:
            self._runtime_events.emit(
                "phase_started",
                round=2, phase="day", actor="system",
                visibility="internal",
                payload={"phase": "day"},
            )
        day2_voters = ["p4", "p5", "p6"]
        day2_refs = _public_refs()
        for vid in day2_voters:
            obs_vid = _player_obs(vid, "day", 2)
            if self._runtime_events is not None:
                snap = build_role_projection_snapshot(run_id=game_id, observation=obs_vid)
                self._runtime_events.write_snapshot(
                    f"obs_{vid}_d2", snap,
                    visibility="internal", round=2, phase="day", actor=vid,
                )
            va = self._mock_agents[vid].decide(obs_vid)
            if self._runtime_events is not None:
                self._runtime_events.emit(
                    "agent_action_selected",
                    round=2, phase="day", actor=va.actor,
                    visibility="internal",
                    payload={"action": va.action, "target": va.target},
                )
            decisions.append(_decision(va.actor, "single", va.phase, va.action, va.target, va.decision_type, va.reason_summary, refs=day2_refs))
            _emit("day", 2, va.action, va.actor, va.target, "public", f"{vid} votes {va.target}.")

        # p2 eliminated
        _emit("day", 2, "player_eliminated", "system", "p2", "all", "p2 eliminated by vote.")
        _emit("day", 2, "role_revealed", "system", "p2", "all", "p2 revealed as werewolf.")
        alive.discard("p2")

        # Game end
        if self._runtime_events is not None:
            self._runtime_events.emit(
                "phase_started",
                round=2, phase="game_end", actor="system",
                visibility="internal",
                payload={"phase": "game_end"},
            )
        _emit("game_end", 2, "game_over", "system", "villager_team", "all", "All werewolves eliminated. Villager team wins.")
        # Final god snapshot
        if self._runtime_events is not None:
            players_list = [
                {"player_id": p.player_id, "role": p.role, "team": p.team}
                for p in self._config.players
            ]
            snap = build_god_snapshot(
                run_id=game_id,
                game_id=game_id,
                round=2,
                phase="game_end",
                players=players_list,
                alive_players=sorted(alive),
                public_event_ids=_public_refs(),
                private_event_ids=[],
            )
            self._runtime_events.write_snapshot(
                "final_god_view", snap,
                visibility="internal", round=2, phase="game_end", actor="system",
            )

        game_log: dict[str, Any] = {
            "game_id": game_id,
            "source_label": self._source_label,
            "players": [{"player_id": p.player_id, "role": p.role, "team": p.team} for p in self._config.players],
            "events": events,
            "result": {"winner": "villager", "end_round": 2, "survivors": sorted(alive), "end_condition": "all_werewolves_eliminated"},
        }

        decision_log: dict[str, Any] = {
            "decision_log_id": f"{game_id}_decision_log",
            "game_id": game_id,
            "source_label": self._source_label,
            "decisions": decisions,
        }

        self._events = events
        self._decisions = decisions
        self._alive = alive

        consensus_log: dict[str, Any] | None = None
        failure_audit: dict[str, Any] | None = None
        if is_consensus_mode:
            consensus_log = {
                "consensus_log_id": f"{game_id}_consensus_log",
                "game_id": game_id,
                "source_label": self._source_label,
                "consensuses": consensus_entries,
            }
            failure_audit = {
                "game_id": game_id,
                "source_label": self._source_label,
                "failures": failure_records,
            }

        return EngineOutputs(game_log=game_log, decision_log=decision_log, consensus_log=consensus_log, failure_audit=failure_audit)

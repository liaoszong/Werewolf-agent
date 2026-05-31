from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MOCK_AGENT_SOURCE_LABEL = "[deterministic mock agent output]"


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


def build_default_config(game_id: str = "g1b_mock_001") -> GameConfig:
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
    def __init__(self, config: GameConfig) -> None:
        self._config = config
        self._players_by_id: dict[str, EnginePlayer] = {
            p.player_id: p for p in config.players
        }
        self._mock_agents: dict[str, MockAgent] = {
            p.player_id: MockAgent(p.player_id) for p in config.players
        }
        self._wolf_agent = WolfTeamMockAgent()
        self._events: list[dict[str, Any]] = []
        self._decisions: list[dict[str, Any]] = []
        self._alive: set[str] = set(self._players_by_id.keys())
        self._current_round: int = 0
        self._current_phase: str = "setup"

    @classmethod
    def from_config(cls, config: GameConfig) -> "GameEngine":
        return cls(config)

    def observation_for(self, player_id: str) -> AgentObservation:
        player = self._players_by_id[player_id]
        known_roles: dict[str, str] = {player_id: player.role}

        if player.role == "werewolf":
            for pid, p in self._players_by_id.items():
                if p.role == "werewolf":
                    known_roles[pid] = p.role

        public_event_ids: list[str] = []
        private_event_ids: list[str] = []

        for event in self._events:
            visibility = event["visibility"]
            eid = event["event_id"]
            if visibility in ("public", "all"):
                public_event_ids.append(eid)
            if visibility == "all":
                private_event_ids.append(eid)
            elif visibility == player.role:
                private_event_ids.append(eid)
            elif visibility == "werewolf_team" and player.role == "werewolf":
                private_event_ids.append(eid)

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

    def run(self) -> EngineOutputs:
        game_id = self._config.game_id
        events: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []
        alive: set[str] = {p.player_id for p in self._config.players}
        d_counter = 0

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

        def _decision(actor: str, scope: str, phase: str, action: str, target: str, dtype: str, reason: str, refs: list[str] | None = None) -> dict[str, Any]:
            nonlocal d_counter
            d_counter += 1
            return {
                "decision_id": f"{game_id}_d{d_counter:03d}",
                "actor": actor,
                "decision_scope": scope,
                "consensus_id": None,
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
            return [e["event_id"] for e in events if e["visibility"] in ("public", "all")]

        def _private_refs(player_id: str) -> list[str]:
            role = self._players_by_id[player_id].role
            result: list[str] = []
            for e in events:
                v = e["visibility"]
                if v == "all":
                    result.append(e["event_id"])
                elif v == role:
                    result.append(e["event_id"])
                elif v == "werewolf_team" and role == "werewolf":
                    result.append(e["event_id"])
            return result

        def _wolf_obs(phase: str, rnd: int, wolf_players: list[str]) -> AgentObservation:
            return AgentObservation(
                game_id=game_id, player_id="wolf_team", role="werewolf", team="werewolf",
                phase=phase, round=rnd, alive_players=sorted(alive),
                public_event_ids=_public_refs(),
                private_event_ids=[e["event_id"] for e in events],
                known_roles={pid: "werewolf" for pid in wolf_players},
            )

        def _player_obs(player_id: str, phase: str, rnd: int) -> AgentObservation:
            p = self._players_by_id[player_id]
            return AgentObservation(
                game_id=game_id, player_id=player_id, role=p.role, team=p.team,
                phase=phase, round=rnd, alive_players=sorted(alive),
                public_event_ids=_public_refs(),
                private_event_ids=_private_refs(player_id),
                known_roles={player_id: p.role},
            )

        # Event 1: setup
        events.append(_event(1, "setup", 0, "role_assignment", "system", "none", "all",
                             "Roles assigned: 2 werewolves (p1, p2), 1 seer (p3), 1 witch (p4), 2 villagers (p5, p6)."))

        # Night 1: wolf kill
        wa1 = self._wolf_agent.decide(_wolf_obs("night", 1, ["p1", "p2"]))
        decisions.append(_decision(wa1.actor, "team", wa1.phase, wa1.action, wa1.target, wa1.decision_type, wa1.reason_summary))
        events.append(_event(2, "night", 1, wa1.action, wa1.actor, wa1.target, "werewolf_team", f"Wolf team kills {wa1.target}."))

        # Night 1: seer check
        sa1 = self._mock_agents["p3"].decide(_player_obs("p3", "night", 1))
        decisions.append(_decision(sa1.actor, "single", sa1.phase, sa1.action, sa1.target, sa1.decision_type, sa1.reason_summary))
        events.append(_event(3, "night", 1, sa1.action, sa1.actor, sa1.target, "seer", f"Seer p3 checks p1, result: werewolf."))

        # Night 1: witch save
        wa2 = self._mock_agents["p4"].decide(_player_obs("p4", "night", 1))
        decisions.append(_decision(wa2.actor, "single", wa2.phase, wa2.action, wa2.target, wa2.decision_type, wa2.reason_summary))
        events.append(_event(4, "night", 1, wa2.action, wa2.actor, wa2.target, "witch", f"Witch p4 saves p5."))

        # Day 1: votes (p3, p4, p5, p6 → p1)
        day1_voters = ["p3", "p4", "p5", "p6"]
        day1_refs = _public_refs()
        seq = 5
        for vid in day1_voters:
            va = self._mock_agents[vid].decide(_player_obs(vid, "day", 1))
            decisions.append(_decision(va.actor, "single", va.phase, va.action, va.target, va.decision_type, va.reason_summary, refs=day1_refs))
            events.append(_event(seq, "day", 1, va.action, va.actor, va.target, "public", f"{vid} votes {va.target}."))
            seq += 1

        # p1 eliminated
        events.append(_event(9, "day", 1, "player_eliminated", "system", "p1", "all", "p1 eliminated by vote."))
        events.append(_event(10, "day", 1, "role_revealed", "system", "p1", "all", "p1 revealed as werewolf."))
        alive.discard("p1")

        # Night 2: wolf kill
        wa3 = self._wolf_agent.decide(_wolf_obs("night", 2, ["p2"]))
        decisions.append(_decision(wa3.actor, "team", wa3.phase, wa3.action, wa3.target, wa3.decision_type, wa3.reason_summary))
        events.append(_event(11, "night", 2, wa3.action, wa3.actor, wa3.target, "werewolf_team", f"Wolf team kills {wa3.target}."))
        events.append(_event(12, "night", 2, "player_died", "system", "p3", "all", "p3 died during the night."))
        alive.discard("p3")

        # Day 2: votes (p4, p5, p6 → p2)
        day2_voters = ["p4", "p5", "p6"]
        day2_refs = _public_refs()
        seq = 13
        for vid in day2_voters:
            va = self._mock_agents[vid].decide(_player_obs(vid, "day", 2))
            decisions.append(_decision(va.actor, "single", va.phase, va.action, va.target, va.decision_type, va.reason_summary, refs=day2_refs))
            events.append(_event(seq, "day", 2, va.action, va.actor, va.target, "public", f"{vid} votes {va.target}."))
            seq += 1

        # p2 eliminated
        events.append(_event(16, "day", 2, "player_eliminated", "system", "p2", "all", "p2 eliminated by vote."))
        events.append(_event(17, "day", 2, "role_revealed", "system", "p2", "all", "p2 revealed as werewolf."))
        alive.discard("p2")

        # Game end
        events.append(_event(18, "game_end", 2, "game_over", "system", "villager_team", "all", "All werewolves eliminated. Villager team wins."))

        game_log: dict[str, Any] = {
            "game_id": game_id,
            "source_label": MOCK_AGENT_SOURCE_LABEL,
            "players": [{"player_id": p.player_id, "role": p.role, "team": p.team} for p in self._config.players],
            "events": events,
            "result": {"winner": "villager", "end_round": 2, "survivors": sorted(alive), "end_condition": "all_werewolves_eliminated"},
        }

        decision_log: dict[str, Any] = {
            "decision_log_id": f"{game_id}_decision_log",
            "game_id": game_id,
            "source_label": MOCK_AGENT_SOURCE_LABEL,
            "decisions": decisions,
        }

        self._events = events
        self._decisions = decisions
        self._alive = alive

        return EngineOutputs(game_log=game_log, decision_log=decision_log)

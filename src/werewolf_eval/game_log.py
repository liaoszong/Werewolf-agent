from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from werewolf_eval.source_labels import VALID_SOURCE_LABELS

VALID_PHASES = {"setup", "night", "day", "game_end"}
VALID_VISIBILITIES = {
    "public",
    "all",
    "werewolf_team",
    "seer",
    "witch",
    "hunter",
    "specific_player_ids",
}


@dataclass(frozen=True)
class Player:
    player_id: str
    role: str
    team: str


@dataclass(frozen=True)
class Event:
    event_id: str
    sequence: int
    round: int
    phase: str
    type: str
    actor: str
    target: str
    visibility: str
    data: dict[str, Any]


@dataclass(frozen=True)
class GameResult:
    winner: str
    end_round: int
    survivors: list[str]
    end_condition: str


@dataclass(frozen=True)
class GameLog:
    game_id: str
    source_label: str
    players: list[Player]
    events: list[Event]
    result: GameResult

    @property
    def player_ids(self) -> set[str]:
        return {player.player_id for player in self.players}

    @property
    def event_ids(self) -> set[str]:
        return {event.event_id for event in self.events}

    def event_by_id(self, event_id: str) -> Event:
        for event in self.events:
            if event.event_id == event_id:
                return event
        raise GameLogValidationError(f"unknown event_id: {event_id}")


class GameLogValidationError(ValueError):
    """Raised when a Game Log cannot be accepted as a Phase 2 runtime input."""


def load_game_log(path: str | Path) -> GameLog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise GameLogValidationError("Game Log root must be an object")
    return parse_game_log(raw)


def parse_game_log(raw: dict[str, Any]) -> GameLog:
    required_top_level = {"game_id", "source_label", "players", "events", "result"}
    missing = required_top_level - set(raw)
    if missing:
        raise GameLogValidationError(f"missing top-level fields: {sorted(missing)}")

    players = [_parse_player(player) for player in raw["players"]]
    events = [_parse_event(event) for event in raw["events"]]
    result = _parse_result(raw["result"])

    game = GameLog(
        game_id=str(raw["game_id"]),
        source_label=str(raw["source_label"]),
        players=players,
        events=events,
        result=result,
    )
    validate_game_log(game)
    return game


def validate_game_log(game: GameLog) -> None:
    if not game.game_id:
        raise GameLogValidationError("game_id must not be empty")

    if game.source_label not in VALID_SOURCE_LABELS:
        raise GameLogValidationError(f"invalid source_label: {game.source_label!r}")

    if len(game.players) != 6:
        raise GameLogValidationError(f"expected 6 players, got {len(game.players)}")

    player_ids = [player.player_id for player in game.players]
    if len(set(player_ids)) != len(player_ids):
        raise GameLogValidationError("player_id values must be unique")

    if len(game.events) == 0:
        raise GameLogValidationError("events must not be empty")

    sequences = [event.sequence for event in game.events]
    expected_sequences = list(range(1, len(game.events) + 1))
    if sequences != expected_sequences:
        raise GameLogValidationError("event sequence must be continuous from 1 to N")

    event_ids = [event.event_id for event in game.events]
    if len(set(event_ids)) != len(event_ids):
        raise GameLogValidationError("event_id values must be unique")

    known_players = set(player_ids)
    known_events = set(event_ids)

    for event in game.events:
        _validate_event(event, known_players, known_events)

    if game.result.winner not in {"villager", "werewolf"}:
        raise GameLogValidationError(f"invalid winner: {game.result.winner!r}")

    unknown_survivors = set(game.result.survivors) - known_players
    if unknown_survivors:
        raise GameLogValidationError(
            f"result.survivors contains unknown players: {sorted(unknown_survivors)}"
        )


def _parse_player(raw: Any) -> Player:
    if not isinstance(raw, dict):
        raise GameLogValidationError("player entries must be objects")
    for field in ["player_id", "role", "team"]:
        if field not in raw:
            raise GameLogValidationError(f"player missing field: {field}")
    return Player(
        player_id=str(raw["player_id"]),
        role=str(raw["role"]),
        team=str(raw["team"]),
    )


def _parse_event(raw: Any) -> Event:
    if not isinstance(raw, dict):
        raise GameLogValidationError("event entries must be objects")
    for field in ["event_id", "sequence", "round", "phase", "type", "actor", "target", "visibility"]:
        if field not in raw:
            raise GameLogValidationError(f"event missing field: {field}")
    data = raw.get("data", {})
    if not isinstance(data, dict):
        raise GameLogValidationError(f"{raw.get('event_id', '<unknown>')}: data must be an object")
    return Event(
        event_id=str(raw["event_id"]),
        sequence=int(raw["sequence"]),
        round=int(raw["round"]),
        phase=str(raw["phase"]),
        type=str(raw["type"]),
        actor=str(raw["actor"]),
        target=str(raw["target"]),
        visibility=str(raw["visibility"]),
        data=data,
    )


def _parse_result(raw: Any) -> GameResult:
    if not isinstance(raw, dict):
        raise GameLogValidationError("result must be an object")
    for field in ["winner", "end_round", "survivors", "end_condition"]:
        if field not in raw:
            raise GameLogValidationError(f"result missing field: {field}")
    if not isinstance(raw["survivors"], list):
        raise GameLogValidationError("result.survivors must be a list")
    return GameResult(
        winner=str(raw["winner"]),
        end_round=int(raw["end_round"]),
        survivors=[str(player_id) for player_id in raw["survivors"]],
        end_condition=str(raw["end_condition"]),
    )


def _validate_event(event: Event, known_players: set[str], known_events: set[str]) -> None:
    if not event.event_id:
        raise GameLogValidationError("event_id must not be empty")

    if event.phase not in VALID_PHASES:
        raise GameLogValidationError(f"{event.event_id}: invalid phase {event.phase!r}")

    if event.visibility not in VALID_VISIBILITIES:
        raise GameLogValidationError(f"{event.event_id}: invalid visibility {event.visibility!r}")

    if event.actor not in known_players and event.actor not in {"system", "wolf_team"}:
        raise GameLogValidationError(f"{event.event_id}: unknown actor {event.actor!r}")

    if (
        event.target not in known_players
        and event.target not in {"villager_team", "werewolf_team", "none"}
    ):
        raise GameLogValidationError(f"{event.event_id}: unknown target {event.target!r}")

    if "summary" not in event.data:
        raise GameLogValidationError(f"{event.event_id}: data.summary is required")

    visible_info_refs = event.data.get("visible_info_refs", [])
    if visible_info_refs:
        if not isinstance(visible_info_refs, list):
            raise GameLogValidationError(f"{event.event_id}: data.visible_info_refs must be a list")
        unknown_refs = set(visible_info_refs) - known_events
        if unknown_refs:
            raise GameLogValidationError(
                f"{event.event_id}: data.visible_info_refs contains unknown refs: {sorted(unknown_refs)}"
            )

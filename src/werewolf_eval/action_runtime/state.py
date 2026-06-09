from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeState:
    """Minimal read-model the rule layer needs to project allowed targets and
    validate envelopes. Built from the engine's live state at projection time;
    holds no behavior."""

    alive: frozenset[str]
    roles: dict[str, str]            # player_id -> role
    night_victim: str | None = None  # tonight's pending wolf victim (witch save rule)

    def is_wolf(self, pid: str) -> bool:
        return self.roles.get(pid) == "werewolf"

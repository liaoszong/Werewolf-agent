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
    # last target the guard ACTUALLY protected on the previous guard night —
    # fallback-chosen targets count (spec §2 patch). None on night 1 / guardless boards.
    last_guarded_target: str | None = None

    def is_wolf(self, pid: str) -> bool:
        return self.roles.get(pid) == "werewolf"

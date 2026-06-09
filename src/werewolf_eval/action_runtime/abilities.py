from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from werewolf_eval.action_runtime.state import RuntimeState

# A target predicate: (state, actor, candidate) -> is candidate a legal target?
TargetPredicate = Callable[[RuntimeState, str, str], bool]


def _alive_only(s: RuntimeState, actor: str, cand: str) -> bool:
    return cand in s.alive


def _exclude_self(s: RuntimeState, actor: str, cand: str) -> bool:
    return cand in s.alive and cand != actor


def _alive_non_wolf(s: RuntimeState, actor: str, cand: str) -> bool:
    return cand in s.alive and not s.is_wolf(cand)


def _is_night_victim(s: RuntimeState, actor: str, cand: str) -> bool:
    return cand is not None and cand == s.night_victim


TARGET_RULES: dict[str, TargetPredicate] = {
    "alive_only": _alive_only,
    "exclude_self": _exclude_self,
    "alive_non_wolf": _alive_non_wolf,
    "is_night_victim": _is_night_victim,
}

# Target arity per ability (how many targets the envelope must carry).
ARITY_NONE = "none"   # pass / speech
ARITY_ONE = "one"     # kill / check / vote / save / poison
ARITY_MANY = "many"   # cupid link (future)


@dataclass(frozen=True)
class AbilityDefinition:
    action_id: str
    trigger: str          # "phase:night" | "phase:day_vote" | "event:on_death"
    target_rule: str      # key in TARGET_RULES ("" when arity none)
    target_arity: str     # ARITY_NONE | ARITY_ONE | ARITY_MANY
    visibility: str        # one of RUNTIME_EVENT_VISIBILITIES


@dataclass(frozen=True)
class RoleDefinition:
    role: str
    team: str
    ability_ids: tuple[str, ...]

from __future__ import annotations

from dataclasses import dataclass

from werewolf_eval.action_runtime.ruleset import BoardRuleset
from werewolf_eval.action_runtime.state import RuntimeState


@dataclass(frozen=True)
class NightIntents:
    """The collected, already-validated pending night intents for one round."""

    wolf_victim: str | None = None
    saved: bool = False             # witch used the antidote on the wolf victim
    poison_target: str | None = None
    guard_target: str | None = None  # v1.5 (guard) — unused in rules_v1


@dataclass(frozen=True)
class NightResult:
    deaths: list[str]


class JointSettler:
    """Resolves the night from collected pending intents using the active
    ruleset's interaction table — the night is one JOINT computation, not each
    ability resolving itself.

    For ``rules_v1`` (no guard) this reproduces the engine's night-death logic
    (emergent_engine.py `_run_inner`:804-811): the wolf victim dies unless the
    witch saved it; the poison adds a second death; both are gated on the target
    still being alive and de-duplicated, in victim-then-poison order.

    The ``guard`` path (v1.5) reads the ruleset's ``guard+save_same_target`` rule
    (奶穿) — not a global constant — and is intentionally inert here because
    ``rules_v1`` boards have no guard.
    """

    def __init__(self, ruleset: BoardRuleset) -> None:
        self._rs = ruleset

    def resolve_night(self, intents: NightIntents, state: RuntimeState) -> NightResult:
        deaths: list[str] = []

        protected = intents.saved
        # v1.5 (guard present): guard cancels the kill UNLESS the witch also saved
        # the same target — the ruleset's 奶穿 rule then says "death".
        if intents.guard_target is not None and intents.wolf_victim is not None:
            if intents.guard_target == intents.wolf_victim:
                if intents.saved and self._rs.night_settlement_rule("guard+save_same_target") == "death":
                    protected = False   # 奶穿: double-protection -> dies anyway
                else:
                    protected = True    # guard alone cancels the kill

        v = intents.wolf_victim
        if v is not None and not protected and v in state.alive:
            deaths.append(v)

        p = intents.poison_target
        if p is not None and p in state.alive and p not in deaths:
            deaths.append(p)

        return NightResult(deaths=deaths)

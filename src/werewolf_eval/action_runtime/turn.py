# src/werewolf_eval/action_runtime/turn.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from werewolf_eval.action_runtime.envelope import ActionEnvelope
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.validator import ActionValidator
from werewolf_eval.game_engine import AgentAction


@dataclass(frozen=True)
class RngPick:
    """A deferred seeded draw the ENGINE performs against its own self._rng at the
    legacy draw site, so ALL randomness stays on the engine (draw order preserved).
      kind 'choice'          -> self._rng.choice(list(over))           (legacy :584/:681/:839)
      kind 'randrange_index' -> over[self._rng.randrange(len(over))]   (legacy :600/:853)
    For a given `over` these consume identical randomness; `kind` records the legacy call
    so the swap is obviously byte-equivalent rather than relying on that equivalence."""
    kind: str
    over: tuple[str, ...]


@dataclass(frozen=True)
class FailureRow:
    kind: str
    reason: str
    target: str | None = None


@dataclass(frozen=True)
class DecisionRow:
    actor: str
    scope: str
    phase: str            # EMIT phase ('night' | 'day')
    action: str
    target: str | None
    dtype: str
    reason: str
    refs: tuple[str, ...] = ()
    consensus_id: str | None = None


@dataclass(frozen=True)
class EventRow:
    phase: str            # EMIT phase
    etype: str
    actor: str
    target: str           # literal 'none' for no-target rows (NEVER None) — n/a for these 3 abilities
    visibility: str
    summary: str


@dataclass(frozen=True)
class EmitPlan:
    decision: DecisionRow
    event: EventRow


@dataclass(frozen=True)
class Adjudication:
    """Phase-1 (pure) verdict for a SINGLE-actor turn (seer, one voter). Exactly one of
    {skip, accepted_target set, rng_pick set} drives the engine."""
    skip: bool = False                  # no candidates -> emit nothing (legacy return/continue)
    accepted_target: str | None = None  # live action legal -> use this target, NO draw
    rng_pick: RngPick | None = None     # else: engine draws the fallback target
    decision_type: str = ""             # final dtype (accepted vs fallback)
    failure: FailureRow | None = None   # engine records (invalid-action path; err-path is engine-recorded)
    downgrade_reason: str | None = None # engine downgrades the live turn (invalid-action path only)


@dataclass(frozen=True)
class DecisionWindow:
    """THE LOCKED single-actor boundary. Read-only view a resolver decides over, built by
    the engine AFTER the provider call but BEFORE any rng draw / emit. Carries NO engine
    byte-state (no _rng/_seq/log lists) — pure inputs only."""
    rnd: int
    actor: str
    role: str
    emit_phase: str                     # 'night' (seer) | 'day' (vote)
    registry_phase: str                 # 'night' | 'day_vote'
    alive_seat_order: tuple[str, ...]   # full alive set, seat order
    roles: Mapping[str, str]            # pid -> role (read-only)
    public_refs: tuple[str, ...]        # decision visible_info_refs (vote uses; seer empty)
    live_action: AgentAction | None     # the validated AgentAction, or None if the provider errored
    validator: ActionValidator
    runtime_state: RuntimeState         # snapshot (night_victim=None this cut)

    def candidates(self) -> tuple[str, ...]:
        """Seeded-fallback candidates: alive in seat order excluding self — the EXACT list
        the legacy resolver feeds self._rng.choice (emergent_engine.py:678 / :836)."""
        return tuple(p for p in self.alive_seat_order if p != self.actor)

    def is_legal(self) -> bool:
        """Validate the live action's (action, target) via the validator — the Phase-3
        `_action_legal` predicate (alive-gating already done by ProviderAgent.decide)."""
        a = self.live_action
        if a is None:
            return False
        env = ActionEnvelope.from_legacy(
            actor=self.actor, role=self.role, phase=self.registry_phase,
            action=a.action, target=a.target,
            reason_summary="", decision_type="", confidence=1.0,
        )
        return self.validator.validate_in_state(env, self.runtime_state).ok


# ---- single-actor resolvers (pure) ---------------------------------------

class SeerResolver:
    """Pure port of _resolve_seer (emergent_engine.py:660-687)."""

    def adjudicate(self, w: DecisionWindow) -> Adjudication:
        if w.live_action is not None and w.is_legal():
            return Adjudication(accepted_target=w.live_action.target, decision_type="inference_based")
        failure = downgrade = None
        if w.live_action is not None:   # present but illegal (err-path is engine-recorded, live_action=None)
            tgt = w.live_action.target
            failure = FailureRow("invalid_action", f"{w.actor} bad seer_check {tgt}", tgt)
            downgrade = f"engine rejected seer_check {tgt}"
        cands = w.candidates()
        if not cands:
            return Adjudication(skip=True)
        return Adjudication(rng_pick=RngPick("choice", cands), decision_type="default",
                            failure=failure, downgrade_reason=downgrade)

    def render(self, w: DecisionWindow, target: str, dtype: str) -> EmitPlan:
        result = "werewolf" if w.roles.get(target) == "werewolf" else "good"
        return EmitPlan(
            decision=DecisionRow(w.actor, "single", "night", "seer_check", target, dtype, f"seer checks {target}"),
            event=EventRow("night", "seer_check", w.actor, target, "seer",
                           f"Seer {w.actor} checks {target}, result: {result}."),
        )


class VoteResolver:
    """Pure port of one voter's turn in _resolve_votes (emergent_engine.py:822-845)."""

    def adjudicate(self, w: DecisionWindow) -> Adjudication:
        if w.live_action is not None and w.is_legal():
            return Adjudication(accepted_target=w.live_action.target, decision_type="inference_based")
        failure = downgrade = None
        if w.live_action is not None:
            tgt = w.live_action.target
            failure = FailureRow("invalid_action", f"{w.actor} bad vote {tgt}", tgt)
            downgrade = f"engine rejected vote {tgt}"
        cands = w.candidates()
        if not cands:
            return Adjudication(skip=True)
        return Adjudication(rng_pick=RngPick("choice", cands), decision_type="default",
                            failure=failure, downgrade_reason=downgrade)

    def render(self, w: DecisionWindow, target: str, dtype: str) -> EmitPlan:
        return EmitPlan(
            decision=DecisionRow(w.actor, "single", "day", "player_vote", target, dtype,
                                 f"{w.actor} votes {target}", refs=w.public_refs),
            event=EventRow("day", "player_vote", w.actor, target, "public", f"{w.actor} votes {target}."),
        )


# ---- wolf team boundary (pure) -------------------------------------------

@dataclass(frozen=True)
class WolfWindow:
    rnd: int
    wolves: tuple[str, ...]
    proposals: tuple[tuple[str, str], ...]   # (wolf, target) for VALID proposals, in proposal order
    candidates: tuple[str, ...]              # alive non-wolf in seat order (no-proposal fallback)
    consensus_id: str


@dataclass(frozen=True)
class WolfAdjudication:
    skip: bool = False                # no proposals AND no candidates
    fixed_target: str | None = None   # single-leader -> no draw
    rng_pick: RngPick | None = None   # tie (randrange over leaders) OR no-proposal (choice over candidates)
    status: str = ""                  # 'consensus' | 'coordinator_tie_break'
    decision_type: str = ""           # 'team_coordinated' | 'default'
    is_fallback: bool = False         # no-proposal fallback (primary=wolves[0], supporters=[])


@dataclass(frozen=True)
class WolfRender:
    primary: str
    supporters: tuple[str, ...]
    reason: str


class WolfResolver:
    """Pure port of the consensus core of _resolve_wolf_kill (emergent_engine.py:577-607).
    The per-wolf provider loop + validation + failure/downgrade stay in the engine driver
    (side-effecting); this resolver only adjudicates the COLLECTED proposals."""

    def adjudicate(self, w: WolfWindow) -> WolfAdjudication:
        if not w.proposals:
            if not w.candidates:
                return WolfAdjudication(skip=True)
            return WolfAdjudication(rng_pick=RngPick("choice", w.candidates),
                                    status="coordinator_tie_break", decision_type="default", is_fallback=True)
        counts: dict[str, int] = {}
        for _, t in w.proposals:
            counts[t] = counts.get(t, 0) + 1
        top = max(counts.values())
        leaders = sorted(t for t, c in counts.items() if c == top)
        if len(leaders) == 1:
            status = "consensus" if len({t for _, t in w.proposals}) == 1 else "coordinator_tie_break"
            return WolfAdjudication(fixed_target=leaders[0], status=status, decision_type="team_coordinated")
        return WolfAdjudication(rng_pick=RngPick("randrange_index", tuple(leaders)),
                                status="coordinator_tie_break", decision_type="team_coordinated")

    def render(self, w: WolfWindow, target: str, is_fallback: bool) -> WolfRender:
        if is_fallback:
            return WolfRender(primary=w.wolves[0], supporters=(), reason=f"fallback kill {target}")
        primary = next(wf for wf, t in w.proposals if t == target)
        supporters = tuple(wf for wf, t in w.proposals if t == target)
        return WolfRender(primary=primary, supporters=supporters, reason=f"wolf team kills {target}")

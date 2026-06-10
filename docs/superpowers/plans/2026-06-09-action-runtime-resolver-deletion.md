# Action Runtime ②a — Delete wolf/seer/vote `_resolve_*`, route through a registry-driven orchestrator

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Replace the hardcoded `_resolve_wolf_kill` / `_resolve_seer` / `_resolve_votes` orchestration in `emergent_engine.py` with a **registry-driven dispatch** over **pure resolver units** (new `action_runtime/turn.py`), producing **byte-identical** output. The witch, speech, and hunter resolvers are **DEFERRED** (see Scope).

**Architecture:** In-engine restructure — `EmergentGameEngine` stays the single owner of every byte-producing field (`self._rng`, `self._seq`, `self._d_counter`, the `_events`/`_decisions`/`_consensus_entries`/`_failures`/`_provider_turns` lists); `_emit`/`_decision`/`_record_failure`/`_downgrade_turn`/`_provider_action`/`_build_consensus_entry` stay VERBATIM. Only the *decision logic* moves into pure units behind a locked **`DecisionWindow`** boundary; the units NEVER touch rng/counters/logs — they return data the engine enacts at the legacy call sites. RNG draws are returned as **`RngPick`** requests the engine performs against its own `self._rng` at the exact legacy draw point.

**Tech Stack:** Python 3.12, stdlib `unittest`. Test cmd: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`.

---

## Scope (BLOCKING constraint, user-directed)

**This cut (②a) touches ONLY wolf / seer / vote.** Per the user's BLOCKING ruling (audit ROT#2/B1-2/B4-3 + ROT#3/A1-9):

- ✅ Delete/route `_resolve_wolf_kill`, `_resolve_seer`, `_resolve_votes` — no one-shot state, no intra-night info dependency, legality fully delegable to `RoleAbilityRegistry`/`ActionValidator`.
- ⛔ **Do NOT delete `_resolve_witch`** and **do NOT route the witch through `validate_in_state`** in this cut. The witch's one-shot potion state has no home in `RuntimeState`/the validator yet (`validate_in_state` would accept a 2nd potion → cross-round divergence), and `_runtime_state()` is called with `night_victim=None` so `is_night_victim` is dead. The witch's proper migration (RuntimeState capability ledger `uses_left`/`consumed_at_event_id` + threading the night victim + multi-round parity) is a SEPARATE later cut (②b, tracked).
- ⛔ Keep `_resolve_speech` (not a registry ability; trivially safe; keeping it means `tests/test_p2a2_live_path.py:202` stays untouched) and `_resolve_hunter_shot`/`_trigger_on_death` (death-trigger path, recently shipped byte-correct, out of original scope) as-is.

**Consequence:** both white-box tests (`test_emergent_engine.py:229` → `_resolve_witch`; `test_p2a2_live_path.py:202` → `_resolve_speech`) are **untouched** in ②a.

**Shared-module freeze (BLOCKING — closes the differential gate's blind spot):** the frozen oracle imports the LIVE `action_runtime/*` (validator/registry/settler), `provider_agent`, and `game_engine` for its deps, so if ②a changed any of THEIR behavior the oracle would drift in lock-step and the gate would pass silently. ②a is therefore allowed to **add** `action_runtime/turn.py` + the `__init__.py` re-exports ONLY; it must NOT change the behavior of `validator.py` / `registry.py` / `settler.py` / `state.py` / `envelope.py` / `provider_agent.py` / `game_engine.py`. If any such change becomes necessary, the gate no longer protects it — stop and re-scope.

**Parity standard:** byte-identical (the spec's runtime_v2 RNG-reorder re-baseline is explicitly NOT taken; deferred to a future behavior phase). The net is the existing 879-test suite + a NEW real differential gate (Task 0).

**Alignment with the broader Action-Runtime frame.** The user's architecture frames four upcoming layers — `CapabilityLedger` (②b), `EffectQueue` (replaces the orphan `TriggerSystem`/`DeathTrigger`), **`DecisionWindow`**, `NightPlan` — plus a separate *semantic invariant safety net* (`docs/superpowers/specs/2026-06-09-p2a-invariant-safety-net-design.md`, ordering net→ledger→EffectQueue→NightPlan). ②a builds the **`DecisionWindow` boundary** for the 4-role path as a pure **byte-parity refactor** — it introduces no new behavior, so the differential gate (Task 0) nets it completely; the *semantic* invariant net is for the new-behavior layers, not ②a. The `DecisionWindow` here is transient/per-turn and carries no identity; if the invariant net's I5 (`decision_settled_once`, keyed on `pending_window_id`) later needs one, it attaches when the net + full `DecisionWindow` formalize. ②a stays within the byte-parity lane and does not pre-build the ledger/queue/net.

---

## The byte-parity ledger (what the orchestrator MUST reproduce, audit B4-5)

Every swap is gated against this. Enumerated from the legacy resolver bodies:

- **RNG draw sites (5, in `self._rng`), order load-bearing.** night: wolf no-proposal `self._rng.choice(candidates)` (`:584`) OR wolf multi-leader tie `self._rng.randrange(len(leaders))` (`:600`); seer fallback `self._rng.choice(cands)` (`:681`). day: per-voter fallback `self._rng.choice(cands)` (`:839`) inside the seat-order loop; vote tie-break `self._rng.randrange(len(leaders))` (`:853`). Witch/speech/hunter draw **zero**. Candidate lists come from `_alive_in_seat_order(exclude={actor})` / `[pid for pid in seat_order if alive and not wolf]` — order matters.
- **decision_type:** wolf valid `team_coordinated` / fallback `default`; seer valid `inference_based` / fallback `default`; vote valid `inference_based` / fallback `default`. (`FALLBACK_DECISION_TYPE = "default"`.)
- **consensus_entry (wolf):** `coordinator = wolves[0]`; `status` = `"consensus"` iff `len({proposal targets}) == 1` else `"coordinator_tie_break"`; synthesized proposals/responses; `_build_consensus_entry` kept VERBATIM.
- **provider_turns:** one dict per provider call, **same list order** (STRICT path appends AFTER `decide()`; this cut only touches STRICT callers, so append stays inside `_provider_action`). Compared index-by-index.
- **`_downgrade_turn`:** sets `kind=INVALID_FALLBACK`, nulls `source_label` + `token_usage`.
- **failure kinds:** `invalid_action`, `agent_error`, plus `ProviderActionError.failure.kind` passthrough.
- **votes emit `phase='day'`** in game_log + decision row (registry keys votes under `day_vote`; the EMIT phase stays `day`).
- **decision `visible_info_refs`:** vote = `_public_refs()`; seer = none. Event rows carry no refs for these.
- **event ids `{game_id}_e{seq:03d}` / decision ids `{game_id}_d{d_counter:03d}`** — preserved by keeping `_emit`/`_decision` on the engine and calling them in legacy per-turn order (consensus append BEFORE `_decision` for the wolf).

---

## File Structure

- **Create** `src/werewolf_eval/action_runtime/turn.py` — pure decision layer: `RngPick`, `FailureRow`, `DecisionRow`, `EventRow`, `EmitPlan`, `Adjudication`, **`DecisionWindow`** (single-actor boundary), `WolfWindow` + `WolfAdjudication` (wolf-team boundary), and the three pure resolvers `SeerResolver` / `VoteResolver` / `WolfResolver`. No engine state, no rng, no IO.
- **Modify** `src/werewolf_eval/action_runtime/__init__.py` — export the new turn.py symbols used by the engine.
- **Modify** `src/werewolf_eval/emergent_engine.py` — add `_draw`, `_run_single_turn`, `_run_seer`, `_run_vote_round`, `_run_wolf_kill`, `_RESOLVERS`, `NIGHT_DISPATCH_ORDER`; convert `_run_inner`'s night/day to registry-driven dispatch; delete the three resolver bodies.
- **Create** `tests/_oracle/emergent_engine_oracle.py` — a FROZEN verbatim copy of the `dceac69` engine (the OLD parity oracle). Deleted in the final task.
- **Create** `tests/parity_scripts.py` — shared adversarial script builders + `(matrix, seeds)`. A NON-test helper (filename ≠ `test_*.py`, never collected) with NO oracle import, imported by the diff/rng/golden tests; SURVIVES the Task-7 oracle deletion.
- **Create** `tests/test_emergent_parity_diff.py` — the real OLD-vs-NEW full-ledger differential gate (Tightening 1).
- **Create** `tests/test_rng_draw_order.py` — counting-`Random` per-round draw-count parity.
- **Create** `tests/test_witch_potion_one_shot_sentinel.py` — antidote + poison one-shot guards (green now; go RED if a future witch swap forgets the ledger).
- **Create** `tests/test_action_runtime_turn.py` — pure unit tests for the resolvers.

---

## Locked interface — `turn.py` (Tightening 2: purity + `DecisionWindow`)

```python
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
```

> **Why two phases (adjudicate → engine draws rng → render):** the fallback/tie target comes from `self._rng`, which must stay on the engine; the rendered summary/result depends on the final target. So adjudicate decides "accept X" or "draw over Y"; the engine draws; render bakes the rows. Both phases are pure. `_build_consensus_entry` is NOT called from the resolver (it reads `self._public_refs()`/`self._game_id`); the engine calls it verbatim with the render's `primary`/`supporters`/`status`.

---

---

## Task 0: The real differential gate (Tightening 1) — MUST land before any swap

**Files:** Create `tests/_oracle/__init__.py`, `tests/_oracle/emergent_engine_oracle.py`, `tests/parity_scripts.py`, `tests/test_emergent_parity_diff.py`, `tests/test_rng_draw_order.py`, `tests/test_witch_potion_one_shot_sentinel.py`.

**Why:** the existing determinism test (`test_emergent_engine.py:84-94`) runs the engine twice with the same seed → it is **NEW-vs-NEW** and cannot catch OLD-vs-NEW drift. `tests/test_action_runtime_parity.py` covers only the settler + 3 legality swaps. Neither guards the consensus/decision_type/provider_turn/failure/RNG-fallback stack this cut deletes. Task 0 builds the missing OLD-oracle full-ledger differential gate and **proves it RED then GREEN**.

- [ ] **Step 1: Freeze the OLD engine as the oracle.**

Copy the current (`dceac69`) engine verbatim:

```bash
mkdir -p tests/_oracle
touch tests/_oracle/__init__.py
cp src/werewolf_eval/emergent_engine.py tests/_oracle/emergent_engine_oracle.py
```

The copy keeps the class name `EmergentGameEngine` and imports `werewolf_eval.*` for its (unchanged) deps. It is FROZEN — never edited after this step; deleted in Task 7. Add a one-line header comment at the top of the copy:

```python
# FROZEN OLD ORACLE — verbatim copy of emergent_engine.py @ dceac69 for the ②a parity gate.
# DO NOT EDIT. Deleted once ②a is proven byte-identical (plan Task 7).
```

- [ ] **Step 2a: Write the shared script module** `tests/parity_scripts.py`.

The adversarial builders + `(matrix, seeds)` live in a NON-test helper module (filename does
NOT match the `test_*.py` discover pattern, so unittest never collects it). It carries **no
oracle import**, so it SURVIVES the Task-7 oracle deletion that removes the differential gate —
which is what lets `test_rng_draw_order.py` and `test_emergent_ledger_golden.py` keep importing
`_wolf_split_tie` / `DEFAULT_MATRIX` / `SEEDS` after Task 7. (This `from tests.parity_scripts
import ...` is the repo's first cross-test import; it works via the implicit namespace package +
each test's `sys.path` insert. Keep the three importers pointed here, never at a `test_*` module.)

```python
# tests/parity_scripts.py
"""Shared adversarial script variants + (matrix, seeds) for the ②a parity gate.

NOT a test module (filename doesn't match `test_*.py`, so discover never collects it). Holds
only the builders imported by test_emergent_parity_diff.py, test_rng_draw_order.py, and
test_emergent_ledger_golden.py. Carries NO oracle import -> survives the Task-7 oracle deletion.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_fake_script import (
    build_villager_win_script,
    build_werewolf_win_script,
    build_hunter_night_kill_script,
    build_hunter_voteout_script,
)
import werewolf_eval.emergent_fake_script as efs  # for _act


# --- adversarial script variants (mutations of the canonical villager-win) ---

def _villager_win():
    return build_villager_win_script()

def _bad_vote():
    s = build_villager_win_script()
    s[("p6", "day", 1)] = efs._act("player_vote", "p99", "inference_based", "bad")  # invalid -> fallback
    return s

def _self_vote():
    s = build_villager_win_script()
    s[("p6", "day", 1)] = efs._act("player_vote", "p6", "inference_based", "self")  # invalid -> fallback
    return s

def _wolf_kills_teammate():
    s = build_villager_win_script()
    s[("p1", "night", 1)] = efs._act("werewolf_kill", "p2", "team_coordinated", "bad")  # invalid -> p2's proposal wins
    return s

def _seer_checks_self():
    s = build_villager_win_script()
    s[("p3", "night", 1)] = efs._act("seer_check", "p3", "inference_based", "self")  # invalid -> seer fallback (rng)
    return s

def _vote_tie():
    # p3/p4 -> p1 ; p5/p6 -> p2 ; p1->p3 p2->p4 => p1,p2 tie (vote tie-break randrange :853)
    s = build_villager_win_script()
    for pid, tgt in (("p5", "p2"), ("p6", "p2"), ("p1", "p3"), ("p2", "p4")):
        s[(pid, "day", 1)] = efs._act("player_vote", tgt, "inference_based", f"{pid}->{tgt}")
    return s

def _wolf_both_invalid():
    # both wolves kill a teammate -> no proposals -> no-proposal fallback (rng.choice :584)
    s = build_villager_win_script()
    s[("p1", "night", 1)] = efs._act("werewolf_kill", "p2", "team_coordinated", "bad")
    s[("p2", "night", 1)] = efs._act("werewolf_kill", "p1", "team_coordinated", "bad")
    return s

def _wolf_split_tie():
    # wolves split p5 vs p6 -> 2 leaders -> wolf tie randrange (:600)
    s = build_villager_win_script()
    s[("p1", "night", 1)] = efs._act("werewolf_kill", "p5", "team_coordinated", "p5")
    s[("p2", "night", 1)] = efs._act("werewolf_kill", "p6", "team_coordinated", "p6")
    # witch tries to save p5; if the rng picked p6 the save is illegal -> still completes
    return s


DEFAULT_MATRIX = [
    ("villager_win", _villager_win),
    ("werewolf_win", build_werewolf_win_script),
    ("bad_vote", _bad_vote),
    ("self_vote", _self_vote),
    ("wolf_kills_teammate", _wolf_kills_teammate),
    ("seer_checks_self", _seer_checks_self),
    ("vote_tie", _vote_tie),
    ("wolf_both_invalid", _wolf_both_invalid),
    ("wolf_split_tie", _wolf_split_tie),
]
HUNTER_MATRIX = [
    ("hunter_night_kill", build_hunter_night_kill_script),
    ("hunter_voteout", build_hunter_voteout_script),
]
SEEDS = [0, 1, 2, 7, 13, 42, 99]
```

- [ ] **Step 2b: Write the differential gate** (imports the shared scripts from `tests.parity_scripts`).

```python
# tests/test_emergent_parity_diff.py
"""OLD-vs-NEW full-ledger differential gate for the ②a resolver-deletion swap.

Runs the FROZEN dceac69 oracle (tests/_oracle/emergent_engine_oracle.py) and the LIVE
engine on the SAME (script, board, seed) and asserts byte-equality on every output
artifact + provider_turns (index-by-index). This is the real differential the
determinism canary (NEW-vs-NEW) and the settler-only parity test cannot provide.

The adversarial scripts + (matrix, seeds) live in tests/parity_scripts.py (a non-test helper)
so test_rng_draw_order.py and test_emergent_ledger_golden.py share them and they SURVIVE this
file's deletion in Task 7.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_engine import (
    EmergentGameEngine as LiveEngine,
    build_emergent_config,
    build_emergent_hunter_config,
)
from tests._oracle.emergent_engine_oracle import EmergentGameEngine as OracleEngine
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents
from tests.parity_scripts import DEFAULT_MATRIX, HUNTER_MATRIX, SEEDS


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _run(engine_cls, config_builder, script, seed):
    eng = engine_cls(config=config_builder(game_id="diff"),
                     agents=build_emergent_fake_agents(script), seed=seed)
    return eng.run()


class ParityDiffTests(unittest.TestCase):
    def _assert_identical(self, name, config_builder, script_builder, seed):
        old = _run(OracleEngine, config_builder, script_builder(), seed)
        new = _run(LiveEngine, config_builder, script_builder(), seed)
        ctx = f"{name} seed={seed}"
        self.assertEqual(old.status, new.status, ctx)
        self.assertEqual(old.end_condition, new.end_condition, ctx)
        for attr in ("game_log", "decision_log", "consensus_log", "failure_audit"):
            self.assertEqual(_j(getattr(old, attr)), _j(getattr(new, attr)), f"{attr} differs: {ctx}")
        # provider_turns: index-by-index (catches append-order drift)
        self.assertEqual(len(old.provider_turns), len(new.provider_turns), f"provider_turns len: {ctx}")
        for i, (o, n) in enumerate(zip(old.provider_turns, new.provider_turns)):
            self.assertEqual(_j(o), _j(n), f"provider_turns[{i}] differs: {ctx}")

    def test_default_board_matrix(self):
        for name, sb in DEFAULT_MATRIX:
            for seed in SEEDS:
                with self.subTest(name=name, seed=seed):
                    self._assert_identical(name, build_emergent_config, sb, seed)

    def test_hunter_board_matrix(self):
        for name, sb in HUNTER_MATRIX:
            for seed in SEEDS:
                with self.subTest(name=name, seed=seed):
                    self._assert_identical(name, build_emergent_hunter_config, sb, seed)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Write the draw-count parity test.**

```python
# tests/test_rng_draw_order.py
"""Counting-Random per-round draw-count parity (OLD vs NEW). The differential gate
compares OUTPUT bytes; this asserts the engines consume self._rng in the same NUMBER
of draws — a direct guard on RNG-order drift independent of the resolved targets."""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_engine import EmergentGameEngine as LiveEngine, build_emergent_config
from tests._oracle.emergent_engine_oracle import EmergentGameEngine as OracleEngine
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents
from tests.parity_scripts import DEFAULT_MATRIX, SEEDS  # shared, NOT the (deletable) diff gate


class _CountingRandom(random.Random):
    def __init__(self, seed):
        super().__init__(seed)
        self.draws = 0
    def choice(self, seq):
        self.draws += 1
        return super().choice(seq)
    def randrange(self, *a, **k):
        self.draws += 1
        return super().randrange(*a, **k)


def _draws(engine_cls, script, seed):
    eng = engine_cls(config=build_emergent_config(game_id="rng"),
                     agents=build_emergent_fake_agents(script), seed=seed)
    eng._rng = _CountingRandom(seed)   # swap in the counter (same seed)
    eng.run()
    return eng._rng.draws


class DrawCountParityTests(unittest.TestCase):
    def test_same_total_draws(self):
        for name, sb in DEFAULT_MATRIX:
            for seed in SEEDS:
                with self.subTest(name=name, seed=seed):
                    self.assertEqual(_draws(OracleEngine, sb(), seed), _draws(LiveEngine, sb(), seed),
                                     f"draw count differs: {name} seed={seed}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Add the witch one-shot sentinels** (antidote guard + poison mirror). Drop in the COMPLETE self-contained file below. Both tests are GREEN now (inline `_resolve_witch`) and stay green through ②a (witch untouched); they go RED the day a future witch swap (②b) routes the witch through `validate_in_state` without a RuntimeState one-shot ledger. The witch-save refusal rides the exact same `_resolve_witch` guard as poison (`emergent_engine.py:742-746`: a 2nd `witch_save` is refused via `save_used` → `invalid_action` failure + `_downgrade_turn` → falls back to `pass`). **Both scripts were run against the live `dceac69` engine and confirmed `status=="completed"` with exactly one potion event each + an `invalid_action` failure recorded** — embed verbatim; do NOT re-derive the board dynamics.

```python
# tests/test_witch_potion_one_shot_sentinel.py
"""Witch one-shot potion sentinels (antidote + poison). GREEN now (inline _resolve_witch);
go RED the day a future witch swap (②b) routes the witch through validate_in_state without a
RuntimeState one-shot ledger. The witch is DEFERRED in ②a, so these stay green throughout.

Each script: witch uses a potion in R1 (consumes it), then ILLEGALLY tries the same potion in
R2 -> the 2nd use MUST be refused (only the R1 event lands; an invalid_action failure is logged).
Both reach wolf-parity by R2 night, so the game terminates with no R3 script needed.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config
from werewolf_eval.emergent_fake_script import (
    _act, build_emergent_fake_agents, SPEECH_REQUEST_PHASE,
)


def build_witch_second_save_script():
    """女巫 R1 救 p5(消耗解药),R2 又非法地对 p3 再用一次解药 -> 第二次救必须被拒。"""
    s = {}
    # R1 night: wolves kill p5; seer checks p1; witch SAVES p5 (consumes antidote -> no death)
    s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("witch_save", "p5", "inference_based", "save p5")
    # R1 day: all 6 alive -> vote out villager p6 (thin the good side; keep BOTH wolves for R2 parity)
    for pid in ("p1", "p2", "p3", "p4", "p5", "p6"):
        s[(pid, SPEECH_REQUEST_PHASE, 1)] = f"{pid}: vote p6"
    for pid in ("p1", "p2", "p3", "p4", "p5"):
        s[(pid, "day", 1)] = _act("player_vote", "p6", "inference_based", f"{pid}->p6")
    s[("p6", "day", 1)] = _act("player_vote", "p1", "inference_based", "p6->p1")
    # after R1 day: alive p1,p2(wolves),p3(seer),p4(witch),p5(villager). R2 night:
    s[("p1", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 2)] = _act("witch_save", "p3", "inference_based", "2nd save (ILLEGAL)")
    # R2 night kills p3 (save refused) -> alive p1,p2(wolves),p4,p5 -> 2v2 parity -> wolf win
    return s


def build_witch_second_poison_script():
    """女巫 R1 毒杀狼 p1(消耗毒药),R2 又非法地对 p2 再用一次毒药 -> 第二次毒必须被拒。"""
    s = {}
    # R1 night: wolves kill p5; seer checks p1; witch POISONS wolf p1 (consumes poison)
    s[("p1", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p2", "night", 1)] = _act("werewolf_kill", "p5", "team_coordinated", "kill p5")
    s[("p3", "night", 1)] = _act("seer_check", "p1", "inference_based", "check p1")
    s[("p4", "night", 1)] = _act("witch_poison", "p1", "retaliatory", "poison wolf p1")
    # deaths R1 night: p5 (wolf victim) + p1 (poison). alive p2,p3,p4,p6 (1 wolf)
    # R1 day: vote out villager p6 (KEEP wolf p2 for R2): p2/p3/p4 -> p6 ; p6 -> p2
    for pid in ("p2", "p3", "p4", "p6"):
        s[(pid, SPEECH_REQUEST_PHASE, 1)] = f"{pid}: vote p6"
    for pid in ("p2", "p3", "p4"):
        s[(pid, "day", 1)] = _act("player_vote", "p6", "inference_based", f"{pid}->p6")
    s[("p6", "day", 1)] = _act("player_vote", "p2", "inference_based", "p6->p2")
    # after R1 day: alive p2(wolf),p3(seer),p4(witch). R2 night:
    s[("p2", "night", 2)] = _act("werewolf_kill", "p3", "team_coordinated", "kill p3")
    s[("p3", "night", 2)] = _act("seer_check", "p2", "inference_based", "check p2")
    s[("p4", "night", 2)] = _act("witch_poison", "p2", "retaliatory", "2nd poison (ILLEGAL)")
    return s


class WitchAntidoteOneShotSentinel(unittest.TestCase):
    def test_second_save_refused_antidote_is_one_shot(self):
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="witch_save_one_shot"),
            agents=build_emergent_fake_agents(build_witch_second_save_script()),
            seed=0,
        )
        outcome = engine.run()
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        saves = [e for e in events if e["type"] == "witch_save"]
        self.assertEqual([e["target"] for e in saves], ["p5"])  # only the R1 save landed
        self.assertIn("invalid_action", [f["kind"] for f in outcome.failure_audit["failures"]])


class WitchPoisonOneShotSentinel(unittest.TestCase):
    def test_second_poison_refused_potion_is_one_shot(self):
        engine = EmergentGameEngine(
            config=build_emergent_config(game_id="witch_poison_one_shot"),
            agents=build_emergent_fake_agents(build_witch_second_poison_script()),
            seed=0,
        )
        outcome = engine.run()
        self.assertEqual(outcome.status, "completed")
        events = outcome.game_log["events"]
        poisons = [e for e in events if e["type"] == "witch_poison"]
        self.assertEqual([e["target"] for e in poisons], ["p1"])  # only the R1 poison landed
        self.assertIn("invalid_action", [f["kind"] for f in outcome.failure_audit["failures"]])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5: Run — all green** (engine unchanged → oracle ≡ live trivially; sentinels green on inline witch):

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_emergent_parity_diff tests.test_rng_draw_order tests.test_witch_potion_one_shot_sentinel -v`
Expected: PASS.

- [ ] **Step 6: PROVE the gate is RED on a real divergence** (do NOT commit this — verification only). Temporarily edit `src/werewolf_eval/emergent_engine.py:584` from `target = self._rng.choice(candidates)` to `target = candidates[0]` (kills a seeded fallback draw). Run the gate:

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_emergent_parity_diff tests.test_rng_draw_order -v`
Expected: **FAIL** — `test_wolf_both_invalid` diverges in `test_emergent_parity_diff`, and `test_rng_draw_order` reports a draw-count mismatch. Then `git checkout src/werewolf_eval/emergent_engine.py` to revert. (If it does NOT fail, the matrix doesn't reach `:584` — widen a script before trusting the gate.)

- [ ] **Step 7: Commit.**

```bash
git add tests/_oracle tests/test_emergent_parity_diff.py tests/test_rng_draw_order.py tests/test_witch_potion_one_shot_sentinel.py
git commit -m "test(action-runtime): OLD-oracle full-ledger differential gate + draw-count + witch one-shot sentinels (②a Step 0)"
```

---

## Task 1: Create `turn.py` (pure) + unit tests + exports

**Files:** Create `src/werewolf_eval/action_runtime/turn.py` (the full "Locked interface" code above); Modify `src/werewolf_eval/action_runtime/__init__.py`; Test `tests/test_action_runtime_turn.py`.

- [ ] **Step 1: Write the failing unit tests** (pure resolvers — no engine):

```python
# tests/test_action_runtime_turn.py
from __future__ import annotations
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1_1
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.validator import ActionValidator
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.turn import (
    DecisionWindow, SeerResolver, VoteResolver, WolfResolver, WolfWindow, RngPick,
)
from werewolf_eval.game_engine import AgentAction

ROLES = {"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p4": "witch", "p5": "villager", "p6": "villager"}
VALIDATOR = ActionValidator(RoleAbilityRegistry(rules_v1_1()))
ALIVE = ("p1", "p2", "p3", "p4", "p5", "p6")


def _win(actor, role, emit_phase, registry_phase, action=None, target=None):
    la = None
    if action is not None:
        la = AgentAction(actor=actor, action=action, target=target, phase=emit_phase, round=1,
                         reason_summary="", decision_type="", confidence=1.0)
    return DecisionWindow(rnd=1, actor=actor, role=role, emit_phase=emit_phase, registry_phase=registry_phase,
                          alive_seat_order=ALIVE, roles=ROLES, public_refs=("r1",), live_action=la,
                          validator=VALIDATOR, runtime_state=RuntimeState(alive=frozenset(ALIVE), roles=dict(ROLES)))


class SeerResolverTests(unittest.TestCase):
    def test_legal_check_accepted(self):
        adj = SeerResolver().adjudicate(_win("p3", "seer", "night", "night", "seer_check", "p1"))
        self.assertEqual((adj.accepted_target, adj.decision_type, adj.rng_pick), ("p1", "inference_based", None))

    def test_self_check_falls_back_to_rng_over_others(self):
        adj = SeerResolver().adjudicate(_win("p3", "seer", "night", "night", "seer_check", "p3"))
        self.assertEqual(adj.decision_type, "default")
        self.assertEqual(adj.rng_pick, RngPick("choice", ("p1", "p2", "p4", "p5", "p6")))
        self.assertEqual(adj.failure.kind, "invalid_action")
        self.assertEqual(adj.downgrade_reason, "engine rejected seer_check p3")

    def test_provider_error_falls_back_no_failure_no_downgrade(self):
        adj = SeerResolver().adjudicate(_win("p3", "seer", "night", "night"))  # live_action=None
        self.assertEqual(adj.decision_type, "default")
        self.assertIsNone(adj.failure)
        self.assertIsNone(adj.downgrade_reason)

    def test_render_result_truthful(self):
        w = _win("p3", "seer", "night", "night", "seer_check", "p1")
        plan = SeerResolver().render(w, "p1", "inference_based")
        self.assertEqual(plan.event.summary, "Seer p3 checks p1, result: werewolf.")
        self.assertEqual(plan.decision.target, "p1")
        self.assertEqual(plan.decision.refs, ())  # seer decision carries no refs


class VoteResolverTests(unittest.TestCase):
    def test_legal_vote_accepted_with_refs(self):
        plan = VoteResolver().render(_win("p5", "villager", "day", "day_vote", "player_vote", "p1"), "p1", "inference_based")
        self.assertEqual(plan.decision.phase, "day")            # EMIT phase (not day_vote)
        self.assertEqual(plan.decision.refs, ("r1",))           # vote decision carries public_refs
        self.assertEqual(plan.event.summary, "p5 votes p1.")

    def test_self_vote_falls_back(self):
        adj = VoteResolver().adjudicate(_win("p5", "villager", "day", "day_vote", "player_vote", "p5"))
        self.assertEqual(adj.rng_pick.kind, "choice")
        self.assertEqual(adj.failure.kind, "invalid_action")


class WolfResolverTests(unittest.TestCase):
    def _ww(self, proposals, candidates=("p3", "p4", "p5", "p6")):
        return WolfWindow(rnd=1, wolves=("p1", "p2"), proposals=tuple(proposals), candidates=candidates, consensus_id="c")

    def test_unanimous_is_consensus_no_rng(self):
        adj = WolfResolver().adjudicate(self._ww([("p1", "p5"), ("p2", "p5")]))
        self.assertEqual((adj.fixed_target, adj.status, adj.decision_type, adj.rng_pick), ("p5", "consensus", "team_coordinated", None))

    def test_split_single_majority_is_tiebreak_label_no_rng(self):
        adj = WolfResolver().adjudicate(self._ww([("p1", "p5"), ("p2", "p5"), ("p1", "p6")]))  # p5=2,p6=1
        self.assertEqual((adj.fixed_target, adj.status), ("p5", "coordinator_tie_break"))

    def test_two_leaders_uses_randrange_over_sorted_leaders(self):
        adj = WolfResolver().adjudicate(self._ww([("p1", "p6"), ("p2", "p5")]))  # p5,p6 tie
        self.assertEqual(adj.rng_pick, RngPick("randrange_index", ("p5", "p6")))
        self.assertEqual(adj.decision_type, "team_coordinated")

    def test_no_proposals_falls_back_over_candidates(self):
        adj = WolfResolver().adjudicate(self._ww([]))
        self.assertEqual(adj.rng_pick, RngPick("choice", ("p3", "p4", "p5", "p6")))
        self.assertTrue(adj.is_fallback)
        self.assertEqual(adj.decision_type, "default")

    def test_no_proposals_no_candidates_skips(self):
        self.assertTrue(WolfResolver().adjudicate(self._ww([], candidates=())).skip)

    def test_render_fallback_primary_is_first_wolf(self):
        r = WolfResolver().render(self._ww([]), "p5", is_fallback=True)
        self.assertEqual((r.primary, r.supporters, r.reason), ("p1", (), "fallback kill p5"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — FAIL** (`ImportError: ... turn`).

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_turn -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Create `turn.py`** with the exact code from the "Locked interface" section above.

- [ ] **Step 4: Export from `__init__.py`** — add to the imports + `__all__`:

```python
from werewolf_eval.action_runtime.turn import (
    DecisionWindow, RngPick, Adjudication, EmitPlan, DecisionRow, EventRow, FailureRow,
    SeerResolver, VoteResolver, WolfResolver, WolfWindow, WolfAdjudication, WolfRender,
)
```
(append each name to `__all__`).

- [ ] **Step 5: Run — PASS** (turn unit tests) and the **full suite** stays green (nothing wired yet).

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_turn -v` → PASS, then full suite → OK.

- [ ] **Step 6: Commit.**

```bash
git add src/werewolf_eval/action_runtime/turn.py src/werewolf_eval/action_runtime/__init__.py tests/test_action_runtime_turn.py
git commit -m "feat(action-runtime): pure turn.py resolvers behind a DecisionWindow boundary (unwired)"
```

---

## Task 2: Swap SEER (lowest risk — single call, single fallback draw, no consensus)

**Files:** Modify `src/werewolf_eval/emergent_engine.py`.

- [ ] **Step 1: Add the engine helpers** (after `_provider_action`/`_downgrade_turn`, before `_win_check`). Import the turn symbols at the top: add `DecisionWindow, RngPick, SeerResolver, VoteResolver, WolfResolver, WolfWindow` to the `from werewolf_eval.action_runtime import (...)` block.

```python
    def _draw(self, pick: "RngPick") -> str:
        """Perform a resolver's deferred seeded draw against self._rng at the legacy site."""
        if pick.kind == "choice":
            return self._rng.choice(list(pick.over))
        return pick.over[self._rng.randrange(len(pick.over))]

    def _decision_window(self, rnd, actor, role, registry_phase, emit_phase, live_action, refs):
        return DecisionWindow(
            rnd=rnd, actor=actor, role=role, emit_phase=emit_phase, registry_phase=registry_phase,
            alive_seat_order=tuple(self._alive_in_seat_order()),
            roles={pid: p.role for pid, p in self._players_by_id.items()},
            public_refs=tuple(refs), live_action=live_action,
            validator=self._validator, runtime_state=self._runtime_state(),
        )

    def _run_single_turn(self, resolver, actor, role, registry_phase, emit_phase, request_phase, rnd, refs=()):
        """Drive ONE strict-path actor turn (seer / one voter) through a pure resolver.
        Side-effects (provider call, budget, turn dict, err-failure, rng draw, decision, emit)
        stay here; the resolver only decides. Returns the resolved target, or None on skip."""
        action, err, turn = self._provider_action(actor, request_phase, rnd)
        if err is not None:
            if isinstance(err, ProviderActionError):
                self._record_failure(rnd, emit_phase, actor, err.failure.kind, err.failure.reason, err.failure.target)
            else:
                self._record_failure(rnd, emit_phase, actor, "agent_error", f"{actor} raised {type(err).__name__}: {err}")
        window = self._decision_window(rnd, actor, role, registry_phase, emit_phase,
                                       action if err is None else None, refs)
        adj = resolver.adjudicate(window)
        if adj.skip:
            return None  # no-candidates bail. UNREACHABLE in live games (win-check guarantees
                         # >=1 candidate before any turn). LOW deviation vs legacy: legacy recorded a
                         # same-turn invalid-action failure/downgrade BEFORE bailing; the skip Adjudication
                         # drops it. Byte-inert (path dead + gate can't reach it). If a future board makes
                         # this reachable, record adj.failure/adj.downgrade_reason here before returning.
        if adj.failure is not None:
            self._record_failure(rnd, emit_phase, actor, adj.failure.kind, adj.failure.reason, adj.failure.target)
        if adj.downgrade_reason is not None:
            self._downgrade_turn(turn, adj.downgrade_reason)
        target = adj.accepted_target if adj.rng_pick is None else self._draw(adj.rng_pick)
        plan = resolver.render(window, target, adj.decision_type)
        d = plan.decision
        self._decision(d.actor, d.scope, d.phase, d.action, d.target, d.dtype, d.reason,
                       refs=list(d.refs) or None, consensus_id=d.consensus_id)
        e = plan.event
        self._emit(e.phase, rnd, e.etype, e.actor, e.target, e.visibility, e.summary)
        return target

    def _run_seer(self, rnd):
        seers = [pid for pid in self._alive if self._players_by_id[pid].role == "seer"]
        if not seers:
            return None
        return self._run_single_turn(SeerResolver(), seers[0], "seer", "night", "night", "night", rnd)
```

> **No new engine state.** `_decision_window` takes `rnd` as a parameter (threaded from `_run_single_turn(rnd=...)` → the call site above) and sets `DecisionWindow.rnd=rnd`. Do NOT add a `self._cur_rnd` field — the round is already in scope at every call site. (`DecisionWindow.rnd` / `WolfWindow.rnd` are carried for the window's self-description; no resolver currently reads them, so they're byte-inert — keep them for symmetry.)

- [ ] **Step 2: Wire + delete.** In `_run_inner`'s night, replace `self._resolve_seer(rnd)` with `self._run_seer(rnd)`. Delete the `_resolve_seer` method body (`emergent_engine.py:660-687`).

- [ ] **Step 3: Gate.**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_emergent_parity_diff tests.test_rng_draw_order tests.test_action_runtime_turn -v`
Expected: PASS (byte-identical). Then full suite → OK.

- [ ] **Step 4: Commit** `refactor(engine): route seer through pure SeerResolver; delete _resolve_seer`.

---

## Task 3: Swap VOTE

**Files:** Modify `src/werewolf_eval/emergent_engine.py`.

- [ ] **Step 1: Add `_run_vote_round`.**

```python
    def _run_vote_round(self, rnd):
        refs = self._public_refs()
        tally: dict[str, int] = {}
        for voter in self._alive_in_seat_order():
            role = self._players_by_id[voter].role
            target = self._run_single_turn(VoteResolver(), voter, role, "day_vote", "day", "day", rnd, refs=refs)
            if target is not None:
                tally[target] = tally.get(target, 0) + 1
        if not tally:
            return None
        top = max(tally.values())
        leaders = sorted(t for t, c in tally.items() if c == top)
        if len(leaders) == 1:
            return leaders[0]
        return leaders[self._rng.randrange(len(leaders))]
```

> Byte note: the per-voter fallback draw (`_run_single_turn` → `_draw(choice)`) fires INSIDE the seat-order loop at the same stream position as legacy `:839`; the final tie-break `randrange` (`:853`) fires after the loop, exactly as legacy.

- [ ] **Step 2: Wire + delete.** In `_run_inner`'s day, replace `eliminated = self._resolve_votes(rnd)` with `eliminated = self._run_vote_round(rnd)`. Delete `_resolve_votes` (`emergent_engine.py:819-853`).

- [ ] **Step 3: Gate** (same command as Task 2 Step 3) → PASS; full suite → OK.

- [ ] **Step 4: Commit** `refactor(engine): route votes through pure VoteResolver; delete _resolve_votes`.

---

## Task 4: Swap WOLF (consensus; keep `_build_consensus_entry` verbatim)

**Files:** Modify `src/werewolf_eval/emergent_engine.py`.

- [ ] **Step 1: Add `_run_wolf_kill`.**

```python
    def _run_wolf_kill(self, rnd):
        wolves = [w for w in self._wolves() if w in self._alive]
        if not wolves:
            return None
        consensus_id = f"{self._game_id}_consensus_r{rnd:02d}"
        proposals: list[tuple[str, str]] = []
        for wolf in wolves:
            action, err, turn = self._provider_action(wolf, "night", rnd)
            if err is not None:
                if isinstance(err, ProviderActionError):
                    self._record_failure(rnd, "night", wolf, err.failure.kind, err.failure.reason, err.failure.target)
                else:
                    self._record_failure(rnd, "night", wolf, "agent_error", f"{wolf} raised {type(err).__name__}: {err}")
                continue
            if not self._action_legal(wolf, "werewolf", "night", action):
                self._record_failure(rnd, "night", wolf, "invalid_action", f"{wolf} proposed invalid kill {action.target}", action.target)
                self._downgrade_turn(turn, f"engine rejected kill target {action.target}")
                continue
            proposals.append((wolf, action.target))
        candidates = tuple(pid for pid in self._seat_order
                           if pid in self._alive and self._players_by_id[pid].role != "werewolf")
        ww = WolfWindow(rnd=rnd, wolves=tuple(wolves), proposals=tuple(proposals),
                        candidates=candidates, consensus_id=consensus_id)
        adj = WolfResolver().adjudicate(ww)
        if adj.skip:
            return None
        target = adj.fixed_target if adj.rng_pick is None else self._draw(adj.rng_pick)
        r = WolfResolver().render(ww, target, adj.is_fallback)
        self._consensus_entries.append(
            self._build_consensus_entry(consensus_id, rnd, wolves, target, r.primary, list(r.supporters), status=adj.status))
        self._decision(r.primary, "team", "night", "werewolf_kill", target, adj.decision_type, r.reason, consensus_id=consensus_id)
        self._emit("night", rnd, "werewolf_kill", r.primary, target, "werewolf_team", f"Wolf team kills {target}.")
        return target
```

> Byte note: `_build_consensus_entry` is UNCHANGED and is called BEFORE `_decision` (legacy `:585`/`:604` → `:586`/`:605` order). `r.supporters` is a tuple → `list(...)` for the verbatim builder signature. The no-proposal fallback draw (`choice`, `:584`) and the multi-leader tie (`randrange`, `:600`) fire via `_draw` at the same stream position.

- [ ] **Step 2: Wire + delete.** In `_run_inner`'s night, replace `victim = self._resolve_wolf_kill(rnd)` with `victim = self._run_wolf_kill(rnd)`. Delete `_resolve_wolf_kill` (`emergent_engine.py:556-607`). **Keep** `_build_consensus_entry` (`:609-658`).

- [ ] **Step 3: Gate** (same command) → PASS; full suite → OK. (`consensus_log` is in the differential.)

- [ ] **Step 4: Commit** `refactor(engine): route wolf consensus through pure WolfResolver; delete _resolve_wolf_kill`.

---

## Task 5: Registry-driven dispatch (the orchestrator deliverable)

**Files:** Modify `src/werewolf_eval/emergent_engine.py`.

The three direct calls become a registry-driven dispatch so "add a night/day-acting role = data (+ one plugin)".

- [ ] **Step 1: Add the dispatch table + order.** In `__init__` (after `self._validator = ...`):

```python
        # Registry-driven action dispatch (Phase-3 ②a). Each migrated ability id maps to a
        # driver. Night order is explicit DATA (load-bearing: wolf BEFORE seer — both may draw
        # 0/1 from self._rng). The witch is DEFERRED (inline, ②b) so it is NOT in this map/order.
        self._RESOLVERS = {
            "werewolf_kill": self._run_wolf_kill,
            "seer_check": self._run_seer,
            "player_vote": self._run_vote_round,
        }
```

Add a module constant near the other constants:

```python
# Night abilities dispatched via _RESOLVERS, in their byte-load-bearing order (wolf before
# seer). The witch is deferred (inline) until its RuntimeState potion ledger lands (②b), so it
# is absent here; when it migrates it joins this tuple. Kept as a constant (not derived from
# seat order) so the order can't silently flip on a re-seated board.
NIGHT_DISPATCH_ORDER = ("werewolf_kill", "seer_check")
```

- [ ] **Step 2: Convert `_run_inner` night** — replace the two direct calls:

```python
            # ---- NIGHT ---- registry-driven dispatch for migrated abilities
            victim = None
            for ability_id in NIGHT_DISPATCH_ORDER:
                result = self._RESOLVERS[ability_id](rnd)
                if ability_id == "werewolf_kill":
                    victim = result
            # witch — DEFERRED inline (BLOCKING: RuntimeState potion ledger pending, ②b)
            saved, poison_target, save_used, poison_used = self._resolve_witch(rnd, victim, save_used, poison_used)
```

- [ ] **Step 3: Convert `_run_inner` day vote** — replace `eliminated = self._run_vote_round(rnd)` with:

```python
            eliminated = self._RESOLVERS["player_vote"](rnd)
```

(speeches above stay the inline `for speaker ...: self._resolve_speech(...)` loop — speech is not a registry ability.)

- [ ] **Step 4: Gate** (same command) → PASS; full suite → OK.

- [ ] **Step 5: Commit** `feat(engine): registry-driven night/day action dispatch (witch deferred inline)`.

---

## Task 6: White-box test check + add-role note

**Files:** none (verification) + a short comment.

- [ ] **Step 1:** Confirm the two white-box tests still pass UNTOUCHED (witch + speech kept):

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_emergent_engine.RobustnessTests.test_witch_cannot_poison_twice tests.test_p2a2_live_path -v`
Expected: PASS (no edits to these tests in ②a).

- [ ] **Step 2:** Add a comment above `NIGHT_DISPATCH_ORDER` documenting that the witch's migration (joining `_RESOLVERS` + this order) is gated on the RuntimeState one-shot ledger (②b), pointing at the sentinel tests. (No code change.)

- [ ] **Step 3: Commit** (if any comment change) `docs(engine): note witch dispatch is gated on the potion ledger (②b)`.

---

## Task 7: Cleanup + ADR + final gate

**Files:** Delete `tests/_oracle/`; Create `docs/adr/2026-06-09-action-runtime-orchestrator.md`; (optional) Create `tests/fixtures/emergent_ledger_golden.json` + a permanent golden test.

- [ ] **Step 1: Freeze a permanent golden** (so the differential's coverage survives the oracle deletion). Add a small generator + test that pins the NOW-PROVEN-EQUAL live engine's full ledger for the canonical scripts (villager_win, werewolf_win, wolf_split_tie, hunter_night_kill) at seeds [0, 7, 42]:

```python
# tests/test_emergent_ledger_golden.py
"""Permanent full-ledger regression guard. The golden was captured from the ②a-swapped
engine, PROVEN byte-equal to the dceac69 oracle by test_emergent_parity_diff before that
oracle was deleted. Regenerate ONLY on an intentional, reviewed behavior change."""
from __future__ import annotations
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
GOLDEN = Path(__file__).resolve().parent / "fixtures" / "emergent_ledger_golden.json"

from werewolf_eval.emergent_engine import EmergentGameEngine, build_emergent_config, build_emergent_hunter_config
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents, build_villager_win_script, build_werewolf_win_script,
    build_hunter_night_kill_script,
)
from tests.parity_scripts import _wolf_split_tie  # shared module survives the Task-7 oracle deletion

CASES = [
    ("villager_win", build_emergent_config, build_villager_win_script, 0),
    ("werewolf_win", build_emergent_config, build_werewolf_win_script, 7),
    ("wolf_split_tie", build_emergent_config, _wolf_split_tie, 42),
    ("hunter_night_kill", build_emergent_hunter_config, build_hunter_night_kill_script, 0),
]

def _ledger(o):
    return {k: getattr(o, k) for k in ("game_log", "decision_log", "consensus_log", "failure_audit", "provider_turns")}

def _run(cfg, sb, seed):
    return EmergentGameEngine(config=cfg(game_id="gold"), agents=build_emergent_fake_agents(sb()), seed=seed).run()

class GoldenLedgerTests(unittest.TestCase):
    def test_matches_golden(self):
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        for name, cfg, sb, seed in CASES:
            with self.subTest(name=name):
                got = json.dumps(_ledger(_run(cfg, sb, seed)), ensure_ascii=False, sort_keys=True)
                self.assertEqual(got, golden[name], f"{name} drifted from golden")

# one-off generator (run manually, never in CI). Use a module alias, NOT `import *` —
# `_ledger`/`_run` are underscore-private and `import *` would skip them (NameError):
#   PYTHONPATH=src python -c "import json, tests.test_emergent_ledger_golden as g; \
#     d={n: json.dumps(g._ledger(g._run(c,s,seed)),ensure_ascii=False,sort_keys=True) for n,c,s,seed in g.CASES}; \
#     g.GOLDEN.parent.mkdir(exist_ok=True); g.GOLDEN.write_text(json.dumps(d,ensure_ascii=False,indent=1),encoding='utf-8')"
```

Generate the golden with the one-off command (while the oracle still exists, so the bytes are oracle-verified by `test_emergent_parity_diff`), then run the golden test → PASS.

- [ ] **Step 2: Delete the frozen oracle + its differential** (served its swap-time purpose; the golden + draw-count + sentinels + 879 suite are the permanent net):

```bash
git rm -r tests/_oracle tests/test_emergent_parity_diff.py
```
**Do NOT delete `tests/parity_scripts.py`** — it is the shared builder module the golden test (`_wolf_split_tie`) and the rng test (`DEFAULT_MATRIX`/`SEEDS`) still import; it has no oracle dependency so it stands alone. Only `tests/_oracle/` and the differential gate go.

Then edit `tests/test_rng_draw_order.py` to drop its TWO oracle-coupled lines — the `from tests._oracle... import ... as OracleEngine` import and the `OracleEngine` arm of the `assertEqual` — and assert against a draw-count GOLDEN dict instead (capture the counts once from the live engine, which equals the oracle by construction), OR delete the file entirely if the golden ledger subsumes it. Its `from tests.parity_scripts import DEFAULT_MATRIX, SEEDS` line STAYS (that module survives). **Keep at least the golden ledger + the witch sentinels.**

- [ ] **Step 3: Write the ADR.**

```markdown
# ADR: Action Runtime orchestrator (②a) — registry-driven dispatch, byte-identical

Date: 2026-06-09 · Status: Accepted

## Decision
- wolf/seer/vote resolution moved to pure `action_runtime/turn.py` units behind a `DecisionWindow`
  boundary; `EmergentGameEngine` stays the single owner of all byte-producing state and enacts the
  units' decisions at the legacy call sites (registry-driven dispatch via `_RESOLVERS` /
  `NIGHT_DISPATCH_ORDER`). Output is byte-identical (gated by a real OLD-oracle differential).
- Parity standard = byte-identical. The spec §7.2/§9-Q1 runtime_v2 RNG-reorder re-baseline is
  DEFERRED to a future behavior phase (would forfeit the byte oracle).
- `TriggerSystem` (triggers.py) stays ORPHAN: `_trigger_on_death` is already data-driven via
  `registry.on_death_abilities`, and `DeathTrigger=(RuntimeState,str)->list[str]` cannot host the
  model-driven hunter shot (no provider/budget/rng). Wiring it is a later behavior-phase PR with a
  `TriggerContext` port (audit B3-5/B4-2). `ARITY_MANY` / `NightIntents.guard_target` /
  `death_order_key` remain intentional forward-scaffolding.
- The WITCH (+ speech, hunter) were DEFERRED from ②a. The witch's migration (②b) is BLOCKED on a
  `RuntimeState` one-shot potion capability ledger + threading the night victim into
  `_runtime_state()` (audit ROT#2/ROT#3); guarded by `test_witch_potion_one_shot_sentinel.py`.

## Why in-engine (not a standalone module + EnginePort)
An EnginePort facade would route every byte-producer (`_emit` bumps `_seq` + flushes; `_decision`
bumps `_d_counter`; `_rng`) through ~15 methods purely to relocate control flow — a re-threading
surface that adds byte-risk for no extensibility the in-engine dispatch lacks.
```

- [ ] **Step 4: Final full suite + commit.**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`
Expected: OK (count = prior 879 − removed diff/oracle tests + the new turn/sentinel/golden tests).

```bash
git add -A
git commit -m "chore(action-runtime): freeze ledger golden, retire OLD oracle, ADR (②a complete)"
```

---

## Known non-blocking deviations (recorded, not gating)

These were surfaced by a byte-level plan review and judged non-blocking. None changes ②a's byte-parity claim; recorded so the executor doesn't mistake them for bugs.

- **L1 — skip path drops failure/downgrade.** `Adjudication(skip=True)` discards a same-turn invalid-action failure/downgrade that legacy would have recorded *before* its no-candidates bail (legacy seer `:675-680` / vote `:833-838`). The path is **unreachable in a live game** (win-check guarantees ≥1 candidate), so it is byte-inert and the differential gate can't reach it. Mitigation: the inline comment at the `if adj.skip` site (Task 2) says to record `adj.failure`/`adj.downgrade_reason` first if a future board ever makes it reachable.
- **L2 — gate is blind to shared-module behavior changes.** The oracle imports the LIVE `action_runtime/*` / `provider_agent` / `game_engine`, so a semantic change there would move the oracle too and pass silently. Closed by the **Shared-module freeze (BLOCKING)** constraint in Scope: ②a may only ADD `turn.py` + `__init__.py` re-exports.
- **L3 — first cross-test import in the repo.** `from tests.parity_scripts import ...` is the repo's first `tests.*` import (no `tests/__init__.py`; relies on the implicit namespace package + each test's `sys.path` insert). The HIGH-1 consolidation into the single non-test `parity_scripts.py` (imported by diff/rng/golden) is what makes this load-bearing — and also removes the original fragility of importing helpers from a soon-deleted `test_*` module.

---

## Self-Review (writing-plans checklist)

**Spec coverage (vs the BLOCKING-narrowed ②a):**
- "delete wolf/seer/vote `_resolve_*` + registry-driven orchestrator" → Tasks 2/3/4 (delete bodies) + Task 5 (dispatch).
- Tightening 1 (real differential gate) → Task 0 (OLD oracle + full-ledger diff + draw-count, proven RED-then-GREEN).
- Tightening 2 (turn.py purity, `DecisionWindow` interface) → Task 1 (pure units, no engine state; rng as `RngPick` requests the engine enacts).
- Witch/speech/hunter deferred, white-box tests untouched → Task 6 verifies; ②b tracked.
- Witch one-shot sentinels (antidote + poison mirror) → Task 0 Step 4: a COMPLETE self-contained file, both tests run against the live engine and confirmed green before embedding.
- Byte-ledger (consensus/decision_type/provider_turns order/'none'/phase='day'/refs) → enumerated above; gated by Task 0.
- Shared test scripts survive oracle deletion → `tests/parity_scripts.py` (non-test module), imported by diff/rng/golden; Task 7 deletes only the oracle + diff gate.

**Placeholder scan:** none — every step has the real code or the exact legacy line range to delete + the gate command. The former "antidote test as the user supplied it" placeholder is resolved: Task 0 Step 4 now embeds the full verified file.

**Type consistency:** `DecisionWindow`/`Adjudication`/`RngPick`/`EmitPlan`/`WolfWindow`/`WolfAdjudication`/`WolfRender` are defined once (turn.py) and used with matching fields in the engine drivers (`_run_single_turn`/`_run_wolf_kill`). `_decision_window` takes `rnd` (no `self._cur_rnd` state — see Task 2 Step 1 note). `_RESOLVERS` keys (`werewolf_kill`/`seer_check`/`player_vote`) match `NIGHT_DISPATCH_ORDER` + the registry ability ids.

**Risk for the reviewer:**
(a) Confirm the per-voter fallback draw fires at the same stream position as legacy `:839` (inside the seat loop) and the wolf no-proposal/tie draws at `:584`/`:600` — the draw-count test + differential guard this, but eyeball `_run_single_turn`'s order.
(b) Confirm `provider_turns` append-order is unchanged (this cut only touches STRICT callers; `_provider_action` still appends after `decide()`).
(c) Confirm `_build_consensus_entry` is byte-unchanged and called BEFORE `_decision` in `_run_wolf_kill`.
(d) Confirm `NIGHT_DISPATCH_ORDER` excludes the witch and the inline `_resolve_witch` call still receives `victim` from the wolf dispatch + threads `save_used/poison_used` exactly as before.
(e) Confirm the differential matrix actually reaches every RNG site (Task 0 Step 6 RED-proof covers `:584`; verify `:600`/`:681`/`:839`/`:853` are each exercised by `wolf_split_tie`/`seer_checks_self`/`bad_vote`/`vote_tie`).

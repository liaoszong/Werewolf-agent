# Agent Action Runtime — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded action-resolution core in `emergent_engine.py` with a data-driven Agent Action Runtime (registry + scheduler + joint settler + trigger system), behind a semantic-parity gate, then prove extensibility by adding the hunter.

**Architecture:** New additive module `src/werewolf_eval/action_runtime/`. Phase 1 builds the data model (BoardRuleset / Registry / ActionEnvelope / Validator) and proves it **reproduces** today's `ALLOWED_ACTIONS_BY_ROLE_PHASE` + the engine's per-action target rules — **without touching the engine** (the existing ~824-test suite stays green). Phase 2 adds the scheduler + joint settler + the old-vs-new parity harness. Phase 3 swaps the engine onto the new runtime (semantic parity locked = v1.0), deletes the old `_resolve_*`, then adds hunter (v1.1).

**Tech Stack:** Python 3.12, stdlib only, `unittest` (run with `NO_PROXY='*' PYTHONPATH=src python -m unittest`). Spec: `docs/superpowers/specs/2026-06-09-agent-action-runtime-architecture-design.md`.

**Parity discipline (non-negotiable, from spec §7):** Phase 1–2 change **no gameplay behavior**. The old engine is the oracle. Semantic parity is the hard gate; byte divergences go in the blessed diff ledger. Behavior improvements (anti-self-vote reasoning, real wolf consensus, memory) are out of scope here.

---

## File Structure

**Phase 1 (additive — new module, no engine edits):**
- Create `src/werewolf_eval/action_runtime/__init__.py` — public exports.
- Create `src/werewolf_eval/action_runtime/state.py` — `RuntimeState` (the minimal read-model the rules need: alive set, roles, night_victim).
- Create `src/werewolf_eval/action_runtime/abilities.py` — `AbilityDefinition`, `RoleDefinition`, `TARGET_RULES` predicate table.
- Create `src/werewolf_eval/action_runtime/ruleset.py` — `BoardRuleset` + `rules_v1()` (the current standard board encoded as data).
- Create `src/werewolf_eval/action_runtime/registry.py` — `RoleAbilityRegistry`.
- Create `src/werewolf_eval/action_runtime/envelope.py` — `ActionEnvelope` (targets[]+params, legacy `target` projection).
- Create `src/werewolf_eval/action_runtime/validator.py` — `ActionValidator`.
- Create `tests/test_action_runtime_registry.py`, `tests/test_action_runtime_validator.py`.

**Phase 2 (outline):** `scheduler.py`, `settler.py`, `triggers.py`, `runtime.py` (orchestrator), `tests/test_action_runtime_parity.py` (old-vs-new harness).

**Phase 3 (outline):** wire `emergent_engine` onto the runtime; delete `_resolve_*`; add hunter ability + `hunter_shoot` resolver.

---

## Phase 1 — Data model + parity with the static contract

### Task 1: Module skeleton + RuntimeState

**Files:**
- Create: `src/werewolf_eval/action_runtime/__init__.py`
- Create: `src/werewolf_eval/action_runtime/state.py`
- Test: `tests/test_action_runtime_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_action_runtime_registry.py
from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.state import RuntimeState


class RuntimeStateTests(unittest.TestCase):
    def test_state_holds_alive_roles_victim(self) -> None:
        s = RuntimeState(
            alive=frozenset({"p1", "p2", "p3"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer"},
            night_victim="p3",
        )
        self.assertIn("p1", s.alive)
        self.assertEqual(s.roles["p3"], "seer")
        self.assertEqual(s.night_victim, "p3")
        self.assertFalse(s.is_wolf("p3"))
        self.assertTrue(s.is_wolf("p1"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_registry -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'werewolf_eval.action_runtime'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/werewolf_eval/action_runtime/__init__.py
"""Agent Action Runtime (P-AAR). Data-driven action resolution; see
docs/superpowers/specs/2026-06-09-agent-action-runtime-architecture-design.md."""
```

```python
# src/werewolf_eval/action_runtime/state.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_registry -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/__init__.py src/werewolf_eval/action_runtime/state.py tests/test_action_runtime_registry.py
git commit -m "feat(action-runtime): RuntimeState read-model skeleton"
```

---

### Task 2: Target-rule predicates

The engine's per-action target rules, encoded as named predicates. Source of truth (current behavior to reproduce):
- `werewolf_kill` → alive AND non-wolf (`emergent_engine.py:519-523`)
- `seer_check` → alive AND ≠ self (`:626`)
- `witch_save` → == tonight's victim (`augment_witch_observation`, R-04)
- `witch_poison` → alive AND ≠ self (the real guard is `:702` `target == witch` → reject; `:662` is only the broad target *list* shown to the model, NOT the adjudication guard — do not derive the rule from it)
- `player_vote` → alive AND ≠ self (`:733`)

**Files:**
- Create: `src/werewolf_eval/action_runtime/abilities.py`
- Test: `tests/test_action_runtime_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_action_runtime_registry.py
from werewolf_eval.action_runtime.abilities import TARGET_RULES


class TargetRuleTests(unittest.TestCase):
    def _state(self):
        return RuntimeState(
            alive=frozenset({"p1", "p2", "p3", "p4", "p5"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p4": "witch", "p5": "villager"},
            night_victim="p5",
        )

    def test_alive_non_wolf_excludes_wolves_and_dead(self) -> None:
        s = self._state()
        rule = TARGET_RULES["alive_non_wolf"]
        self.assertTrue(rule(s, "p1", "p5"))    # villager alive -> ok
        self.assertFalse(rule(s, "p1", "p2"))   # wolf -> rejected
        self.assertFalse(rule(s, "p1", "p9"))   # dead/unknown -> rejected

    def test_exclude_self(self) -> None:
        s = self._state()
        rule = TARGET_RULES["exclude_self"]
        self.assertFalse(rule(s, "p3", "p3"))   # self -> rejected
        self.assertTrue(rule(s, "p3", "p1"))

    def test_is_night_victim(self) -> None:
        s = self._state()
        rule = TARGET_RULES["is_night_victim"]
        self.assertTrue(rule(s, "p4", "p5"))    # p5 is tonight's victim
        self.assertFalse(rule(s, "p4", "p1"))

    def test_alive_only(self) -> None:
        s = self._state()
        rule = TARGET_RULES["alive_only"]
        self.assertTrue(rule(s, "p4", "p1"))
        self.assertFalse(rule(s, "p4", "p9"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_registry.TargetRuleTests -v`
Expected: FAIL — `ModuleNotFoundError ... abilities`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/werewolf_eval/action_runtime/abilities.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_registry.TargetRuleTests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/abilities.py tests/test_action_runtime_registry.py
git commit -m "feat(action-runtime): target-rule predicates + ability/role defs"
```

---

### Task 3: BoardRuleset `rules_v1` (the current board as data)

Encodes the default board (`p1/p2` wolves, `p3` seer, `p4` witch, `p5/p6` villagers — `build_default_config`) + each role's abilities, matching today's `ALLOWED_ACTIONS_BY_ROLE_PHASE` and the day-vote action. Night/day-vote phase only in Phase 1 (speech is a separate non-adjudicating path, unchanged).

**Files:**
- Create: `src/werewolf_eval/action_runtime/ruleset.py`
- Test: `tests/test_action_runtime_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_action_runtime_registry.py
from werewolf_eval.action_runtime.ruleset import rules_v1


class RulesV1Tests(unittest.TestCase):
    def test_rules_v1_has_versioned_id_and_roles(self) -> None:
        rs = rules_v1()
        self.assertEqual(rs.rules_version, "rules_v1")
        roles = {r.role for r in rs.roles}
        self.assertEqual(roles, {"werewolf", "seer", "witch", "villager"})

    def test_wolf_has_night_kill_and_day_vote(self) -> None:
        rs = rules_v1()
        ids = {a.action_id for a in rs.abilities}
        self.assertIn("werewolf_kill", ids)
        self.assertIn("seer_check", ids)
        self.assertIn("witch_save", ids)
        self.assertIn("witch_poison", ids)
        self.assertIn("player_vote", ids)

    def test_naede_穿_is_a_settlement_rule_not_global(self) -> None:
        # 奶穿 lives in the ruleset's night interaction table, not a constant.
        rs = rules_v1()
        self.assertEqual(rs.night_settlement_rule("guard+save_same_target"), "death")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_registry.RulesV1Tests -v`
Expected: FAIL — `ModuleNotFoundError ... ruleset`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/werewolf_eval/action_runtime/ruleset.py
from __future__ import annotations
from dataclasses import dataclass

from werewolf_eval.action_runtime.abilities import (
    ARITY_NONE, ARITY_ONE, AbilityDefinition, RoleDefinition,
)


@dataclass(frozen=True)
class BoardRuleset:
    rules_version: str
    roles: tuple[RoleDefinition, ...]
    abilities: tuple[AbilityDefinition, ...]
    # night interaction rule table (奶穿 etc.) — data, not a global constant.
    _night_rules: dict[str, str]
    # death-trigger ordering key components (Phase 2/3 uses this).
    death_order_key: tuple[str, ...] = ("phase_priority", "cause_priority", "seat_index")

    def night_settlement_rule(self, key: str) -> str:
        return self._night_rules[key]

    def ability(self, action_id: str) -> AbilityDefinition:
        for a in self.abilities:
            if a.action_id == action_id:
                return a
        raise KeyError(action_id)


def rules_v1() -> BoardRuleset:
    """The current standard 6-player board, encoded as data. Mirrors
    ALLOWED_ACTIONS_BY_ROLE_PHASE (provider_agent.py) + the engine target rules."""
    abilities = (
        AbilityDefinition("werewolf_kill", "phase:night", "alive_non_wolf", ARITY_ONE, "werewolf_team"),
        AbilityDefinition("seer_check",    "phase:night", "exclude_self",   ARITY_ONE, "seer"),
        AbilityDefinition("witch_save",    "phase:night", "is_night_victim", ARITY_ONE, "witch"),
        AbilityDefinition("witch_poison",  "phase:night", "exclude_self",   ARITY_ONE, "witch"),
        AbilityDefinition("witch_pass",    "phase:night", "",               ARITY_NONE, "witch"),
        AbilityDefinition("player_vote",   "phase:day_vote", "exclude_self", ARITY_ONE, "public"),
    )
    roles = (
        RoleDefinition("werewolf", "werewolf", ("werewolf_kill", "player_vote")),
        RoleDefinition("seer",     "villager", ("seer_check", "player_vote")),
        RoleDefinition("witch",    "villager", ("witch_save", "witch_poison", "witch_pass", "player_vote")),
        RoleDefinition("villager", "villager", ("player_vote",)),
    )
    night_rules = {
        # 奶穿: guard-protect AND witch-save on the same target -> still dies.
        "guard+save_same_target": "death",
        "save_cancels_kill": "true",
        "poison_stacks": "true",
    }
    return BoardRuleset("rules_v1", roles, abilities, night_rules)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_registry.RulesV1Tests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/ruleset.py tests/test_action_runtime_registry.py
git commit -m "feat(action-runtime): rules_v1 BoardRuleset (current board as data)"
```

---

### Task 4: RoleAbilityRegistry + **parity with `ALLOWED_ACTIONS_BY_ROLE_PHASE`**

This is the Phase 1 keystone gate: the registry's projected `allowed_actions(role, phase)` must **exactly equal** the existing static map for every entry.

**Files:**
- Create: `src/werewolf_eval/action_runtime/registry.py`
- Test: `tests/test_action_runtime_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_action_runtime_registry.py
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.provider_agent import ALLOWED_ACTIONS_BY_ROLE_PHASE


class RegistryParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reg = RoleAbilityRegistry(rules_v1())

    def test_allowed_actions_match_static_map_exactly(self) -> None:
        # Map the runtime's phase names to the static map's phase names.
        # runtime "night" -> static "night"; runtime "day_vote" -> static "day".
        phase_map = {"night": "night", "day_vote": "day"}
        for (role, static_phase), expected in ALLOWED_ACTIONS_BY_ROLE_PHASE.items():
            rt_phase = next(rt for rt, st in phase_map.items() if st == static_phase)
            got = self.reg.allowed_actions(role, rt_phase)
            # witch night has save+poison+pass in the registry; the static map lists
            # only the adjudicating [witch_save, witch_poison]. Compare the
            # adjudicating subset for parity (pass is a no-target engine path).
            adjudicating = [a for a in got if a != "witch_pass"]
            self.assertEqual(
                sorted(adjudicating), sorted(expected),
                f"{role}/{static_phase}: {adjudicating} != {expected}",
            )

    def test_allowed_targets_wolf_kill_excludes_wolves(self) -> None:
        s = RuntimeState(
            alive=frozenset({"p1", "p2", "p3", "p5"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p5": "villager"},
        )
        targets = self.reg.allowed_targets("werewolf_kill", "p1", s)
        self.assertEqual(sorted(targets), ["p3", "p5"])  # no wolves, no dead
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_registry.RegistryParityTests -v`
Expected: FAIL — `ModuleNotFoundError ... registry`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/werewolf_eval/action_runtime/registry.py
from __future__ import annotations

from werewolf_eval.action_runtime.abilities import TARGET_RULES
from werewolf_eval.action_runtime.ruleset import BoardRuleset
from werewolf_eval.action_runtime.state import RuntimeState

# runtime phase -> the trigger string used in AbilityDefinition.trigger
_PHASE_TRIGGER = {"night": "phase:night", "day_vote": "phase:day_vote"}


class RoleAbilityRegistry:
    """Projects the active ruleset: which actions a (role, phase) may take, and
    which targets are legal in a given state. Single source for allowed_actions /
    allowed_targets / ability cards (cards land in Phase 2)."""

    def __init__(self, ruleset: BoardRuleset) -> None:
        self._rs = ruleset
        self._by_role = {r.role: r for r in ruleset.roles}

    def abilities_for(self, role: str, phase: str):
        trig = _PHASE_TRIGGER[phase]
        role_def = self._by_role[role]
        return [
            self._rs.ability(aid)
            for aid in role_def.ability_ids
            if self._rs.ability(aid).trigger == trig
        ]

    def allowed_actions(self, role: str, phase: str) -> list[str]:
        return [a.action_id for a in self.abilities_for(role, phase)]

    def allowed_targets(self, action_id: str, actor: str, state: RuntimeState) -> list[str]:
        ability = self._rs.ability(action_id)
        if not ability.target_rule:
            return []
        pred = TARGET_RULES[ability.target_rule]
        return [pid for pid in sorted(state.alive) if pred(state, actor, pid)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_registry.RegistryParityTests -v`
Expected: PASS. (If it fails, the registry — not the static map — is wrong; the static map is the oracle.)

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/registry.py tests/test_action_runtime_registry.py
git commit -m "feat(action-runtime): RoleAbilityRegistry + parity with static action map"
```

---

### Task 5: ActionEnvelope (`targets[]` + `params{}`, legacy projection)

**Files:**
- Create: `src/werewolf_eval/action_runtime/envelope.py`
- Test: `tests/test_action_runtime_validator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_action_runtime_validator.py
from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.envelope import ActionEnvelope


class EnvelopeTests(unittest.TestCase):
    def test_legacy_target_maps_to_targets0(self) -> None:
        e = ActionEnvelope.from_legacy(
            actor="p1", role="werewolf", phase="night", action="werewolf_kill",
            target="p3", reason_summary="x", decision_type="inference_based", confidence=0.9,
        )
        self.assertEqual(e.targets, ["p3"])
        self.assertEqual(e.target, "p3")           # projection back to single target

    def test_no_target_action(self) -> None:
        e = ActionEnvelope(actor="p4", role="witch", phase="night", action="witch_pass",
                           targets=[], params={}, reason_summary="save it",
                           decision_type="default", confidence=1.0)
        self.assertEqual(e.targets, [])
        self.assertIsNone(e.target)

    def test_multi_target(self) -> None:
        e = ActionEnvelope(actor="cupid", role="cupid", phase="setup", action="cupid_link",
                           targets=["p2", "p5"], params={}, reason_summary="", 
                           decision_type="inference_based", confidence=1.0)
        self.assertEqual(e.targets, ["p2", "p5"])
        self.assertEqual(e.target, "p2")           # projection = first


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_validator -v`
Expected: FAIL — `ModuleNotFoundError ... envelope`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/werewolf_eval/action_runtime/envelope.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionEnvelope:
    """Uniform internal action intent. `targets` is 0/1/N; `params` carries
    ability-specific extras. `.target` projects to the legacy single-target field
    so decision_log / game_log stay byte-identical for existing roles (spec §4.7)."""

    actor: str
    role: str
    phase: str
    action: str
    targets: list[str]
    params: dict[str, Any]
    reason_summary: str
    decision_type: str
    confidence: float

    @property
    def target(self) -> str | None:
        return self.targets[0] if self.targets else None

    @classmethod
    def from_legacy(cls, *, actor: str, role: str, phase: str, action: str,
                    target: str | None, reason_summary: str, decision_type: str,
                    confidence: float) -> "ActionEnvelope":
        return cls(
            actor=actor, role=role, phase=phase, action=action,
            targets=[] if target in (None, "", "none") else [target],
            params={}, reason_summary=reason_summary,
            decision_type=decision_type, confidence=confidence,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_validator -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/envelope.py tests/test_action_runtime_validator.py
git commit -m "feat(action-runtime): ActionEnvelope with targets[] + legacy projection"
```

---

### Task 6: ActionValidator (reproduces the engine's accept/reject)

**Files:**
- Create: `src/werewolf_eval/action_runtime/validator.py`
- Test: `tests/test_action_runtime_validator.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_action_runtime_validator.py
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import rules_v1
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.validator import ActionValidator


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.v = ActionValidator(RoleAbilityRegistry(rules_v1()))
        self.s = RuntimeState(
            alive=frozenset({"p1", "p2", "p3", "p4", "p5"}),
            roles={"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p4": "witch", "p5": "villager"},
            night_victim="p5",
        )

    def _env(self, role, phase, action, target):
        return ActionEnvelope.from_legacy(
            actor={"werewolf": "p1", "seer": "p3", "witch": "p4", "villager": "p5"}[role],
            role=role, phase=phase, action=action, target=target,
            reason_summary="x", decision_type="inference_based", confidence=0.9)

    # --- target legality: use validate_in_state (needs the RuntimeState) ---
    def test_wolf_kill_villager_ok(self) -> None:
        self.assertTrue(self.v.validate_in_state(self._env("werewolf", "night", "werewolf_kill", "p5"), self.s).ok)

    def test_wolf_kill_wolf_rejected(self) -> None:
        r = self.v.validate_in_state(self._env("werewolf", "night", "werewolf_kill", "p2"), self.s)
        self.assertFalse(r.ok)
        self.assertEqual(r.reason_kind, "invalid_target")

    def test_seer_check_self_rejected(self) -> None:
        self.assertFalse(self.v.validate_in_state(self._env("seer", "night", "seer_check", "p3"), self.s).ok)

    def test_witch_save_non_victim_rejected(self) -> None:
        self.assertFalse(self.v.validate_in_state(self._env("witch", "night", "witch_save", "p1"), self.s).ok)
        self.assertTrue(self.v.validate_in_state(self._env("witch", "night", "witch_save", "p5"), self.s).ok)

    def test_witch_poison_self_rejected(self) -> None:
        # engine rejects the witch poisoning herself (emergent_engine.py:702)
        self.assertFalse(self.v.validate_in_state(self._env("witch", "night", "witch_poison", "p4"), self.s).ok)
        self.assertTrue(self.v.validate_in_state(self._env("witch", "night", "witch_poison", "p1"), self.s).ok)

    # --- action allowed / arity: stateless validate() ---
    def test_action_not_allowed_for_role_phase(self) -> None:
        r = self.v.validate(self._env("villager", "night", "werewolf_kill", "p1"))
        self.assertFalse(r.ok)
        self.assertEqual(r.reason_kind, "invalid_action")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_validator.ValidatorTests -v`
Expected: FAIL — `ModuleNotFoundError ... validator`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/werewolf_eval/action_runtime/validator.py
from __future__ import annotations
from dataclasses import dataclass

from werewolf_eval.action_runtime.abilities import ARITY_NONE, TARGET_RULES
from werewolf_eval.action_runtime.envelope import ActionEnvelope
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.state import RuntimeState


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason_kind: str = ""   # "" | "invalid_action" | "invalid_target" | "bad_arity"


class ActionValidator:
    """Validates an ActionEnvelope against the active ruleset. Mirrors the
    accept/reject decisions today split across ProviderAgent.decide + the
    per-resolver inline checks. Does NOT perform fallback — the caller keeps the
    existing seeded R-29 fallback on rejection (Phase 2)."""

    def __init__(self, registry: RoleAbilityRegistry) -> None:
        self._reg = registry

    def validate(self, env: ActionEnvelope) -> ValidationResult:
        allowed = self._reg.allowed_actions(env.role, env.phase)
        if env.action not in allowed:
            return ValidationResult(False, "invalid_action")
        ability = self._reg._rs.ability(env.action)
        if ability.target_arity == ARITY_NONE:
            return ValidationResult(True) if not env.targets else ValidationResult(False, "bad_arity")
        if len(env.targets) != 1:
            return ValidationResult(False, "bad_arity")
        pred = TARGET_RULES[ability.target_rule]
        # state is threaded in via validate_in_state; default rejects unknown.
        return ValidationResult(False, "invalid_target")

    def validate_in_state(self, env: ActionEnvelope, state: RuntimeState) -> ValidationResult:
        base = self.validate(env)
        if not base.ok or base.reason_kind in ("invalid_action", "bad_arity"):
            return base
        ability = self._reg._rs.ability(env.action)
        if ability.target_arity == ARITY_NONE:
            return ValidationResult(True)
        pred = TARGET_RULES[ability.target_rule]
        if all(pred(state, env.actor, t) for t in env.targets):
            return ValidationResult(True)
        return ValidationResult(False, "invalid_target")
```

> Design note (already reflected in the Step-1 test above): `validate()` is **stateless** — it judges only action-allowed-for-(role,phase) + arity. `validate_in_state(env, state)` adds **target legality**. Target-legality cases therefore go through `validate_in_state`; the action-allowed/arity case through `validate`. Keep that split when writing the test — do not call `validate()` for a target-legality assertion (it cannot see the state and rejects unconditionally).

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_action_runtime_validator.ValidatorTests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/action_runtime/validator.py tests/test_action_runtime_validator.py
git commit -m "feat(action-runtime): ActionValidator reproducing engine accept/reject"
```

---

### Task 7: Phase 1 gate — full suite green, public exports

**Files:**
- Modify: `src/werewolf_eval/action_runtime/__init__.py`

- [ ] **Step 1: Export the public surface**

```python
# src/werewolf_eval/action_runtime/__init__.py  (append)
from werewolf_eval.action_runtime.abilities import AbilityDefinition, RoleDefinition, TARGET_RULES
from werewolf_eval.action_runtime.envelope import ActionEnvelope
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import BoardRuleset, rules_v1
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.validator import ActionValidator, ValidationResult

__all__ = [
    "AbilityDefinition", "RoleDefinition", "TARGET_RULES", "ActionEnvelope",
    "RoleAbilityRegistry", "BoardRuleset", "rules_v1", "RuntimeState",
    "ActionValidator", "ValidationResult",
]
```

- [ ] **Step 2: Run the FULL suite — engine untouched, must stay green**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests 2>&1 | grep -E "^(Ran|OK|FAILED)"`
Expected: `OK` (count = prior 824 + the new action_runtime tests). **Zero changes to existing engine behavior** — if any pre-existing test changed, Phase 1 touched something it must not.

- [ ] **Step 3: Commit**

```bash
git add src/werewolf_eval/action_runtime/__init__.py
git commit -m "feat(action-runtime): Phase 1 complete — data model + static-contract parity"
```

**Phase 1 done when:** the new module reproduces `ALLOWED_ACTIONS_BY_ROLE_PHASE` + the engine target rules, and the full suite is green with the engine byte-unchanged.

---

## Phase 2 — Scheduler + JointSettler + parity harness (outline)

> Detailed into bite-sized tasks **after Phase 1 lands** (its emergent shapes inform the exact signatures). Each task stays additive + behavior-preserving; the old engine remains the oracle.

- **`scheduler.py` — PhaseScheduler.** Data-driven turn loop over the ruleset; night as a DAG of pending intents (witch_save depends on the wolf victim, not the seer). Collects validated `ActionEnvelope`s as pending intents.
- **`settler.py` — JointSettler.** Night joint resolution from the ruleset's interaction table (`save_cancels_kill`, `poison_stacks`, 奶穿 once guard exists). Produces the death list. Reproduces today's `_resolve_witch(victim,…)` outcome for the 4-role board.
- **`triggers.py` — TriggerSystem.** Death-resolution queue with the deterministic `death_order_key`, cycle termination, transitive closure. No triggers fire for the 4-role board (no hunter yet) — but the queue exists and is unit-tested against chain-death fixtures.
- **`context.py` — RoleContract + AgentContextPacket (spec §4.4/4.5; do NOT drop).** Stable per-turn identity injection (the spec's named fix for "the model forgot it is p5") + the enhancement seam `build(actor, phase, state, enhancements={})`. Baseline reproduces today's `render_observation_text` identity lines byte-for-byte. `ProviderInputMode` (§4.6) renders the packet as strict-JSON in baseline.
- **`runtime.py` — orchestrator.** Wires registry + scheduler + settler + triggers + context into a `run_actions(state, agents)` that emits the SAME events (event_id/type/target/visibility/summary) the engine emits today, feeding the existing spine.
- **`tests/test_action_runtime_parity.py` — the harness.** Run the new runtime and the old `EmergentGameEngine` on the SAME seed × the canonical fake scripts (villager-win, werewolf-win). Assert Layer-1 semantic parity (winner, deaths, votes, night targets, check results, visibility, fallback). Emit any byte divergence into `docs/generated-games/runtime-v2-parity-diff-ledger.json` + `.logs/review/latest/parity-diff-summary.md` (spec §7.3 fields). **Phase 2 gate: semantic parity passes on all seeds in the harness; 824 suite green.**

---

## Phase 3 — Swap-delete + hunter v1.1 (outline)

> Detailed after Phase 2's parity harness is green.

- **Swap:** route `EmergentGameEngine`'s night/day resolution through `action_runtime.runtime.run_actions`; keep the witch unified through the common path (closes health-check **B-5**). Re-run the parity harness → **v1.0 parity locked**. Bless any remaining byte diffs into the ledger; bump `runtime_v2` for the emergent reference outputs (spec §9.1).
- **Delete:** remove `_resolve_wolf_kill/_resolve_seer/_resolve_witch/_resolve_votes/_build_consensus_entry` + `ALLOWED_ACTIONS_BY_ROLE_PHASE` (now registry-sourced). Full suite green. (Closes **B-2/D-4/E-5** as part of the consolidation; coordinate B-2 with the visibility ADR.)
- **Hunter (v1.1):** add a `hunter` RoleDefinition + `hunter_shoot`/`hunter_pass` AbilityDefinition (`trigger: event:on_death`, `target_rule: exclude_self`) + one `hunter_shoot` resolver in `triggers.py`. **Acceptance: hunter works with ZERO edits to scheduler.py / runtime.py / the run loop** — the structural proof that "add role = add data". New tests: hunter shoots on night-death and on vote-out; chain into the trigger queue.

---

## Self-Review (writing-plans checklist)

- **Spec coverage:** §2 principles → encoded as Phase-1 data + parity discipline; §4 components → Phase 1 builds 4.0/4.1/4.2/4.3/4.7, Phase 2 builds 4.8/4.9/4.10/4.11, RoleContract/AgentContextPacket/ProviderInputMode (4.4/4.5/4.6) land in Phase 2's `runtime.py` (prompt assembly) — **noted gap: add an explicit Phase-2 task for RoleContract injection + AgentContextPacket seam** when detailing Phase 2. §5 hard cases → Phase 2 trigger fixtures + Phase 3 hunter. §6 v1.0/v1.1/v1.5 → Phase 2 parity (v1.0) / Phase 3 hunter (v1.1) / future guard (v1.5). §7 parity → Phase 2 harness + Phase 3 swap discipline. §8 testing → per-task tests + the parity harness.
- **Placeholder scan:** Phase 1 tasks carry complete code; Phases 2–3 are explicitly outlines to be detailed post-Phase-1 (not placeholders within an executable task).
- **Type consistency:** `RuntimeState`, `AbilityDefinition(action_id, trigger, target_rule, target_arity, visibility)`, `ActionEnvelope(targets[], params{})`, `RoleAbilityRegistry.allowed_actions/allowed_targets`, `ActionValidator.validate/validate_in_state` — names consistent across tasks.

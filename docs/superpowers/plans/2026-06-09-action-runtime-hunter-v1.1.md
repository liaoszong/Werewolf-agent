# Hunter v1.1 — add a role as DATA + wire the death-triggered shot

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Add the **hunter** — a role that, on death (night kill OR vote-out), takes a
model-driven shot at another player. Prove the spec's headline "**add role = add data**":
the role + its abilities are new DATA (`rules_v1_1`), and the only new *code* is one death
trigger + one shot resolver (the audit's "new effect needs a small resolver plugin" boundary).

**Architecture:** Additive. No existing 4-role game has a hunter, so the existing suite +
byte-determinism are the safety net — they must stay **green and byte-identical** throughout.
Honors audit contract C (`docs/harness/reviews/2026-06-09-action-runtime-audit-REPORT.md`):
a NEW versioned `rules_v1_1()` (not an edit to `rules_v1`); the shot is a real model decision
(provider call + validate + seeded fallback + budget + decision row + event), reached through
a narrow trigger hook (not the bare `(RuntimeState,str)` `TriggerSystem` signature, which the
audit showed can't host a provider call).

**THE LINCHPIN (byte-safety):** the allowed_actions swap fixed `provider_agent.decide` to a
module `RoleAbilityRegistry(rules_v1())`; a hunter's day-vote would hit `decide(role="hunter")`
→ `rules_v1` has no hunter → `allowed_actions=[]` → every hunter vote silently rejected. Fix:
bump the **default ruleset everywhere** (`provider_agent` registry, engine settler+validator)
from `rules_v1()` to **`rules_v1_1()`**, a backward-compatible **superset** (rules_v1 + hunter).
For a 4-role game the hunter role is never queried, so `rules_v1_1` yields byte-identical
`allowed_actions`/settlement/validation → the determinism test stays green (the gate).

**Tech Stack:** Python 3.12, `unittest` (`NO_PROXY='*' PYTHONPATH=src python -m unittest`).
Gate after EACH task: `test_deterministic_same_seed_byte_identical` + full suite green.

---

## File Structure

- Modify `src/werewolf_eval/action_runtime/ruleset.py` — add `rules_v1_1()` (new fn; do NOT
  edit `rules_v1`).
- Modify `src/werewolf_eval/action_runtime/registry.py` — add `on_death_abilities(role)`.
- Modify `src/werewolf_eval/action_runtime/__init__.py` — export `rules_v1_1`.
- Modify `src/werewolf_eval/provider_agent.py` — module registry `rules_v1()` → `rules_v1_1()`.
- Modify `src/werewolf_eval/emergent_engine.py` — settler+validator use `rules_v1_1()`; add
  `_trigger_on_death` hook after night deaths + after vote elimination; add `_resolve_hunter_shot`;
  add `build_emergent_hunter_config`.
- New fake script + tests: extend `src/werewolf_eval/emergent_fake_script.py` with a hunter
  game; new `tests/test_action_runtime_hunter.py`.

---

## Task 1: `rules_v1_1()` — hunter as data (NEW ruleset, superset of rules_v1)

**Files:** Modify `ruleset.py`, `__init__.py`; Test `tests/test_action_runtime_hunter.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_action_runtime_hunter.py
from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.ruleset import rules_v1, rules_v1_1


class RulesV11Tests(unittest.TestCase):
    def test_is_a_superset_versioned_variant(self) -> None:
        rs = rules_v1_1()
        self.assertEqual(rs.rules_version, "rules_v1_1")
        roles = {r.role for r in rs.roles}
        self.assertEqual(roles, {"werewolf", "seer", "witch", "villager", "hunter"})
        # backward-compatible: the 4 original roles' abilities are unchanged vs rules_v1
        v1 = {r.role: r.ability_ids for r in rules_v1().roles}
        for r in rules_v1_1().roles:
            if r.role in v1:
                self.assertEqual(r.ability_ids, v1[r.role], f"{r.role} drifted")

    def test_hunter_has_day_vote_and_on_death_shot(self) -> None:
        reg = RoleAbilityRegistry(rules_v1_1())
        self.assertEqual(reg.allowed_actions("hunter", "day_vote"), ["player_vote"])
        on_death = [a.action_id for a in reg.on_death_abilities("hunter")]
        self.assertEqual(on_death, ["hunter_shoot", "hunter_pass"])
        self.assertEqual(reg.ability("hunter_shoot").target_rule, "exclude_self")
```

- [ ] **Step 2: Run — FAIL** (`ImportError: rules_v1_1`).

- [ ] **Step 3: Implement `rules_v1_1()` (ruleset.py) + `on_death_abilities` (registry.py)**

```python
# ruleset.py — add after rules_v1()
def rules_v1_1() -> BoardRuleset:
    """rules_v1 + the hunter (a versioned superset — does NOT edit rules_v1, per audit
    contract C). Backward-compatible: the 4 original roles are byte-identical, so a 4-role
    game under rules_v1_1 behaves exactly as under rules_v1 (the determinism gate proves it)."""
    base = rules_v1()
    hunter_abilities = (
        AbilityDefinition("hunter_shoot", "event:on_death", "exclude_self", ARITY_ONE, "public"),
        AbilityDefinition("hunter_pass", "event:on_death", "", ARITY_NONE, "public"),
    )
    hunter = RoleDefinition("hunter", "villager", ("player_vote", "hunter_shoot", "hunter_pass"))
    return BoardRuleset(
        "rules_v1_1",
        base.roles + (hunter,),
        base.abilities + hunter_abilities,
        dict(base._night_rules),
        base.death_order_key,
    )
```

```python
# registry.py — add to RoleAbilityRegistry
    def on_death_abilities(self, role: str) -> list[AbilityDefinition]:
        """Abilities a role's death triggers (trigger == 'event:on_death'). [] for unknown
        roles or roles with no death trigger."""
        role_def = self._by_role.get(role)
        if role_def is None:
            return []
        return [
            self._rs.ability(aid)
            for aid in role_def.ability_ids
            if self._rs.ability(aid).trigger == "event:on_death"
        ]
```

Export `rules_v1_1` in `__init__.py` (add to the import + `__all__`).

- [ ] **Step 4: Run — PASS.**  **Step 5: Commit** `feat(action-runtime): rules_v1_1 superset adds the hunter as data`.

---

## Task 2: Bump the default ruleset to `rules_v1_1` (byte-identical for 4-role)

**Files:** Modify `provider_agent.py`, `emergent_engine.py`.

- [ ] **Step 1:** In `provider_agent.py`, change `_ALLOWED_ACTIONS_REGISTRY = RoleAbilityRegistry(rules_v1())`
  → `rules_v1_1()`, and the import. In `emergent_engine.py.__init__`, change
  `_ruleset = rules_v1()` → `_ruleset = rules_v1_1()` (the import too). The settler + validator now
  build from the superset.

- [ ] **Step 2: Run the byte-determinism gate — MUST stay green**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_emergent_engine.VillagerWinTests.test_deterministic_same_seed_byte_identical tests.test_action_runtime_parity tests.test_action_runtime_registry -v`
Expected: all PASS. (Determinism green = the superset is byte-identical for the 4-role board.
`test_allowed_actions_pinned` still passes — it pins the 4 original roles, which are unchanged.)

- [ ] **Step 3: Full suite** → `OK`. **Step 4: Commit** `feat(action-runtime): default ruleset -> rules_v1_1 (byte-identical for 4-role)`.

---

## Task 3: Hunter board config + the death-trigger hook + shot resolver

**Files:** Modify `emergent_engine.py`.

- [ ] **Step 1: Add the board builder**

```python
# emergent_engine.py — near build_emergent_config
def build_emergent_hunter_config(game_id: str = "hunter_v11") -> GameConfig:
    """6-player board with a hunter at p6 (replaces a villager)."""
    cfg = build_default_config(game_id=game_id)
    players = list(cfg.players)
    players[5] = EnginePlayer("p6", "hunter", "villager")
    return GameConfig(game_id=game_id, players=players)
```

- [ ] **Step 2: Add `_trigger_on_death` + `_resolve_hunter_shot` to EmergentGameEngine**

```python
    def _trigger_on_death(self, dead: str, rnd: int, phase: str) -> None:
        """Fire a dead player's on_death ability (data-driven via the ruleset). For the
        hunter that is a model-driven shot; the shot victim may itself trigger (cascade,
        terminates because each pid is removed from _alive before recursing)."""
        role = self._players_by_id[dead].role
        if not self._registry.on_death_abilities(role):
            return
        target = self._resolve_hunter_shot(dead, rnd, phase)
        if target is not None and target in self._alive:
            self._alive.discard(target)
            self._emit(phase, rnd, "player_died", "system", target, "all",
                       f"{target} was shot by {dead}.")
            self._trigger_on_death(target, rnd, phase)

    def _resolve_hunter_shot(self, hunter: str, rnd: int, phase: str) -> str | None:
        """Ask the hunter's provider for a shot target (hunter_shoot) or a pass. Validate
        via the registry (exclude_self/alive); seeded R-29 fallback on failure; charge
        budget; record a decision + provider_turn; emit the hunter_shoot event. Returns the
        shot target, or None for a pass / no valid target."""
        self._budget.charge()
        obs = self._build_obs(hunter, phase, rnd)
        rendered = render_observation_text(obs, self._events_by_id())
        request = ProviderRequest(
            request_id=f"{self._game_id}_r{rnd:02d}_{hunter}_shot",
            game_id=self._game_id, actor=hunter, phase=phase, round=rnd,
            observation=obs.to_dict(),
            allowed_actions=["hunter_shoot", "hunter_pass"],
            allowed_targets=sorted(self._alive),
            observation_text=rendered.text + "\n你已出局,作为猎人可开枪带走一名存活玩家,或选择不开枪。",
            response_kind="action", max_output_tokens=ACTION_MAX_OUTPUT_TOKENS,
        )
        turn: dict[str, Any] = {
            "request_id": request.request_id, "round": rnd, "phase": phase, "actor": hunter,
            "response_kind": "action", "live_requested": True, "kind": None,
            "fallback_reason": None, "source_label": None,
            "model": getattr(self._agents[hunter].provider, "model", None), "token_usage": None,
            "observation_source_event_ids": list(rendered.source_event_ids),
        }
        self._provider_turns.append(turn)
        action_name, target = "hunter_pass", None
        try:
            response = self._agents[hunter].provider.respond(request)
            turn["source_label"] = response.source_label
            turn["token_usage"] = dict(response.token_usage)
            parsed = json.loads(response.raw_content)
            action_name = parsed.get("action", "hunter_pass")
            target = parsed.get("target")
            turn["kind"] = LIVE_SUCCESS
        except Exception as exc:  # noqa: BLE001
            self._record_failure(rnd, phase, hunter, "parse_failure", f"{hunter} hunter parse failed: {exc}")
            turn["kind"] = INVALID_FALLBACK
            turn["fallback_reason"] = f"hunter parse failed: {exc}"
            action_name, target = "hunter_pass", None

        # validate the shot via the registry (exclude_self/alive)
        if action_name == "hunter_shoot":
            legal = self._validator.validate_in_state(
                ActionEnvelope.from_legacy(actor=hunter, role="hunter", phase=phase,
                                           action="hunter_shoot", target=target,
                                           reason_summary="", decision_type="", confidence=1.0),
                self._runtime_state(),
            ).ok
            if not legal:
                self._record_failure(rnd, phase, hunter, "invalid_action", f"{hunter} invalid hunter_shoot {target}", target)
                self._downgrade_turn(turn, f"invalid hunter_shoot {target}")
                action_name, target = "hunter_pass", None

        if action_name == "hunter_shoot" and target is not None:
            self._decision(hunter, "single", phase, "hunter_shoot", target, "retaliatory", f"hunter {hunter} shoots {target}")
            self._emit(phase, rnd, "hunter_shoot", hunter, target, "public", f"Hunter {hunter} shoots {target}.")
            return target
        # pass
        self._decision(hunter, "single", phase, "hunter_pass", "none", FALLBACK_DECISION_TYPE, f"{hunter} does not shoot")
        self._emit(phase, rnd, "hunter_pass", hunter, "none", "public", f"Hunter {hunter} does not shoot.")
        return None
```

> Note: this reuses the existing constants (`ACTION_MAX_OUTPUT_TOKENS`, `LIVE_SUCCESS`,
> `INVALID_FALLBACK`, `FALLBACK_DECISION_TYPE`) and helpers (`_build_obs`, `_emit`, `_decision`,
> `_record_failure`, `_downgrade_turn`, `_runtime_state`, `_validator`). The shot has NO seeded
> random-target fallback (a failed shot = pass), so it adds **no** `self._rng` draw → it cannot
> perturb the seeded RNG order of any 4-role game (there is no hunter in those).

- [ ] **Step 3: Wire the hook at the two death sites** (in `_run_inner`)

After the night death loop (`for pid in deaths: ... player_died`), append inside the loop body:
```python
                self._trigger_on_death(pid, rnd, "night")
```
After the day vote elimination block (`player_eliminated` + `role_revealed`):
```python
                self._trigger_on_death(eliminated, rnd, "day")
```

- [ ] **Step 4: Byte-determinism gate — 4-role still byte-identical** (the hook is a no-op when
  no role has an on_death ability). Run the determinism test + full suite → green.
  **Step 5: Commit** `feat(engine): hunter death-trigger hook + model-driven shot resolver`.

---

## Task 4: Hunter fake script + integration tests

**Files:** Modify `emergent_fake_script.py`; Test `tests/test_action_runtime_hunter.py`.

- [ ] **Step 1:** Add `build_hunter_game_script()` to `emergent_fake_script.py` — a deterministic
  6-player game on the hunter board where the hunter (p6) is wolf-killed night 1 and shoots a
  wolf (`hunter_shoot` keyed `(p6, "night", 1)` returning `{"action":"hunter_shoot","target":"p1",...}`),
  plus a variant for vote-out + a pass. (Keys: night actions `(pid,"night",r)`, speeches
  `(pid, SPEECH_REQUEST_PHASE, r)`, votes `(pid,"day",r)`, hunter shot `(p6, phase, r)`.)

- [ ] **Step 2: Integration tests** (`tests/test_action_runtime_hunter.py`)

```python
    def test_hunter_shot_on_night_death_kills_target(self) -> None:
        engine = EmergentGameEngine(config=build_emergent_hunter_config(),
                                    agents=build_emergent_fake_agents(build_hunter_game_script()), seed=0)
        outcome = engine.run()
        # a hunter_shoot event exists; its target died
        shots = [e for e in outcome.game_log["events"] if e["type"] == "hunter_shoot"]
        self.assertTrue(shots)
        shot = shots[0]
        died = [e["target"] for e in outcome.game_log["events"]
                if e["type"] == "player_died" and e.get("target") == shot["target"]]
        self.assertTrue(died, "hunter's shot target must die")

    def test_hunter_pass_kills_no_one(self) -> None:
        ... # a script where the hunter passes; assert hunter_pass event + no extra player_died
```

- [ ] **Step 3:** Run the hunter tests → PASS. **Step 4:** Full suite → green. **Step 5: Commit**
  `test(action-runtime): hunter game fake script + shot/pass integration tests`.

---

## Task 5: Acceptance gate

- [ ] Full suite green; determinism green; `grep -rn "rules_v1()" src/` shows only `rules_v1_1`'s
  internal `base = rules_v1()` call (rules_v1 retained as the historical baseline, not deleted).
- [ ] **Done when:** a hunter board runs, the hunter takes a model-driven shot on death (night +
  vote) that kills its target, passing works, and every 4-role game is byte-unchanged.

---

## Self-Review (writing-plans checklist)

- **Coverage:** "add role = add data" = Task 1 (data) + the single new resolver `_resolve_hunter_shot`
  (the documented "new effect = small plugin" boundary). Contract C: versioned `rules_v1_1` (Task 1,
  not editing rules_v1); model-driven shot via a real provider call (Task 3); the trigger is
  data-driven via `on_death_abilities` (not a hardcoded `role=="hunter"`). Linchpin (decide needs
  the hunter): Task 2 bump, gated by determinism.
- **Byte-safety:** Tasks 2 & 3 each re-run the determinism gate; the superset + the no-op hook are
  byte-identical for 4-role by construction (hunter never appears) — the gate confirms empirically.
- **Risk for the reviewer:** (a) confirm `rules_v1_1` is a true byte-compatible superset (4 original
  roles' `allowed_actions`/abilities unchanged); (b) confirm `_trigger_on_death` is genuinely a no-op
  for 4-role (no role has an `event:on_death` ability) so determinism holds; (c) confirm the shot's
  ProviderRequest/parse/validate/fallback path matches the witch's pattern and records a faithful
  provider_turn/decision without perturbing seeded RNG; (d) confirm the cascade terminates
  (target removed from `_alive` before recursing) and can't double-fire; (e) the night/day death
  events keep their existing types (player_died vs player_eliminated) — the hook is additive.

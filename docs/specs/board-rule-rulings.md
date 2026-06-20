# Board Rule Rulings — adjudications for previously-undecided rule gaps

> Authoritative text for rule gaps the engine resolved by default but never had a
> written ruling or pin test. Each ruling names the cause, the code single source,
> and the pin test. Closed out from the 2026-06-12 system-view audit items
> **A-2** and **A-3** (user-adjudicated 2026-06-12).
>
> Scope: these are RULINGS on existing roles (hunter, witch). They add NO role and
> change NO undecided board rule (奶穿 / 连守 / death-announcement order stay as-is).
> System view: SYS-A1 (game loop / death triggers), SYS-A2 (ability system), SYS-A3
> (night joint settlement).

---

## A-2 — A poisoned hunter does not shoot

**Ruling.** When a hunter dies by the witch's **poison**, the hunter's on-death shot
is **suppressed** — the hunter gets no shot. Every other death cause still triggers
the shot: **werewolf kill**, **vote-out**, and **being shot** by another hunter
(cascade).

**Rationale.** Matches the common 狼人杀 board rule that poison "destroys" the
target's ability; a poisoned hunter cannot retaliate. The audit found the engine's
death loop fired `_trigger_on_death` for every death indiscriminately, including
poison deaths —偏离标准规则, with no spec and no pin test.

**Single source (data-driven).** The suppression is encoded on the ability, not as
an engine special-case:

- `action_runtime/abilities.py` — `AbilityDefinition.suppressed_by_cause: frozenset[str]`
  (default empty → every other ability unchanged).
- `action_runtime/ruleset.py` — `rules_v1_1()` sets `hunter_shoot`'s
  `suppressed_by_cause = frozenset({"witch_poison"})`.
- `action_runtime/registry.py` — `death_trigger_suppressing_causes(role)` unions the
  causes over a role's on-death abilities.
- `action_runtime/settler.py` — `NightResult.death_causes` maps each dead player to its
  ACTUAL lethal source (`werewolf_kill` / `witch_poison`). This is authoritative: a wolf
  victim whose kill is guard-canceled but who then dies to poison is `witch_poison`, NOT
  `werewolf_kill`. The engine must not infer the cause from `pid == wolf_victim`.
- `emergent_engine.py` — `_trigger_on_death(dead, rnd, phase, cause)` carries the death
  cause and returns early when `cause ∈ registry.death_trigger_suppressing_causes(role)`.
  Causes wired at the call sites: night deaths → `night_result.death_causes[pid]` (from the
  settler); day vote-out → `vote`; cascade shot → `hunter_shoot`.

**Honesty.** Suppression produces no `hunter_shoot`/`hunter_pass` event and no
provider call (the hunter is never asked). The poison death event itself is recorded
truthfully; nothing claims a shot occurred.

**Pin tests** (`tests/test_rule_rulings.py::PoisonedHunterRulingTests`):
`test_poison_death_hunter_no_shoot`, `test_wolf_kill_hunter_triggers_shoot`,
`test_vote_out_hunter_triggers_shoot`.

---

## A-3 — The witch may self-save only on the first night

**Ruling.** The witch may use her antidote on **herself only on the first night**.
A self-save attempt on **any later night** is **illegal**: it is rejected, recorded
as an honest `invalid_action`, the turn is downgraded (the live result is not used),
and the action falls back to a pass — so the witch dies if she was the wolf victim.

**Rationale.** Common board rule: 女巫首夜可自救，此后不可自救. The audit found
`witch_save` validation had no self-exclusion and no first-night gate, so the witch
could self-save on any night.

**Single source.** The temporal gate lives where the witch's other potion guards
already live, in `emergent_engine.py::_resolve_witch`. `witch_save` already requires
`target == victim` (she can only antidote the wolf victim), so a self-save means the
witch **is** the victim; the new condition rejects that when `rnd != 1`:

```
self_save_late = target == witch and rnd != 1
if save_used or victim is None or target != victim or self_save_late: -> invalid + downgrade + pass
```

The `witch_save` target predicate (`is_night_victim`) in `action_runtime/ruleset.py`
is unchanged; the first-night-only rule is temporal (needs the round) and stays in the
engine validation block alongside the one-shot `save_used` guard.

**Honesty.** The rejected late self-save records
`invalid_action` (`reason = "witch self-save only allowed on the first night"`) in the
failure audit and downgrades the provider turn — no silent pass, no inflated
`live_success`.

**Pin tests** (`tests/test_rule_rulings.py::WitchSelfSaveRulingTests`):
`test_witch_first_night_self_save_legal`, `test_witch_non_first_night_self_save_rejected`.

---

## Out of scope (explicitly NOT changed by these rulings)

- No new role; hunter and guard are already shipped (`rules_v1_1` / `rules_v1_2`).
- 奶穿 (guard + witch-save same target), 连守 (no-consecutive-guard), and the
  night death-announcement order are untouched.
- No prompt-visible bytes change: the hunter is simply not asked when poisoned, and
  the witch's shown `allowed_targets` are unchanged — only adjudication changed.
</content>

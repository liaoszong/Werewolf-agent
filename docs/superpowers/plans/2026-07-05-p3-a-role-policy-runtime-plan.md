# P3-A Role Policy Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete P3-A-2a, P3-A-2b, P3-A-3, P3-A-2c, and P3-A-4 as small, reviewable slices that keep asset ownership, hidden-information safety, and prompt-version boundaries explicit.

**Architecture:** Start with a Flutter-only local RolePolicy editor projection, then add an authoritative Python RolePolicyPack registry, then add AgentContextPacket memory records, then let runtime consume RolePolicy through a single renderer path. P3-A-4 wires the pieces into a shadow-safe roleplay arm without changing engine authority or allowing client/runtime leaks.

**Tech Stack:** Flutter widget tests and UI code under `clients/flutter_app/`; Python standard-library modules under `src/werewolf_eval/`; unittest under `tests/`; prompt byte/version workflow before any model-visible runtime change.

---

## File Structure

- Modify `clients/flutter_app/lib/src/screens/home_shell.dart`: P3-A-2a mobile role grid, full-screen detail page, local draft state, setting picker.
- Modify `clients/flutter_app/lib/src/app/app_strings.dart`: localized copy for RolePolicyPack scope, draft mode, boundaries, and role editor sections.
- Modify `clients/flutter_app/test/widget/home_shell_test.dart`: widget coverage for role grid, detail navigation, local draft, and forbidden real save/version/frozen wording.
- Create `src/werewolf_eval/role_policy_registry.py`: P3-A-2b file-backed RolePolicyPack / RolePolicy registry with draft, publish, revision, and reference checks.
- Create `tests/test_role_policy_registry.py`: registry read/write, draft/publish, referenced-policy versioning, and forbidden ownership field tests.
- Create `src/werewolf_eval/agent_context_packet.py`: P3-A-3 records and packet validation for Fact, Claim, Belief, Commitment, TeamPlan, StaticPlaybook, render metadata, and visibility-safe selection.
- Create `tests/test_agent_context_packet.py`: record semantics, provenance, belief-vs-fact separation, team authorization, and context budget tests.
- Modify runtime prompt/render integration files only in P3-A-2c after invoking `guarding-prompt-bytes`; likely candidates are `src/werewolf_eval/emergent_engine.py`, `src/werewolf_eval/provider_agent.py`, or prompt rendering helpers after inspection.
- Add/modify focused runtime tests for P3-A-2c and P3-A-4 only after identifying the existing prompt/render entry point.
- Update `docs/PROJECT_MAP.md`, `docs/TASKS.md`, and `MEMORY.md` at task closeouts.

---

### Task 0: Plan Checkpoint

**Files:**
- Create: `docs/superpowers/plans/2026-07-05-p3-a-role-policy-runtime-plan.md`

- [ ] **Step 1: Save this plan**

Use this file as the execution checklist.

- [ ] **Step 2: Validate scope**

Run:

```powershell
git diff --stat
git diff --name-only
```

Expected: only this plan file is changed.

- [ ] **Step 3: Update tree for new file**

Run:

```powershell
node .codex/hooks/tree.mjs --force
```

Expected: `.oh-my-harness/tree.md` updates if the navigation tree tracks the new plan.

- [ ] **Step 4: Commit the plan**

Run the shared-worktree checks first:

```powershell
git branch --show-current
git status --short
```

Expected: branch is `main`; staged area has no unrelated staged files.

Commit:

```powershell
git add docs/superpowers/plans/2026-07-05-p3-a-role-policy-runtime-plan.md .oh-my-harness/tree.md
git commit -m "docs: plan p3-a role policy runtime work"
```

---

### Task 1: P3-A-2a Flutter Local Draft RolePolicy Editor

**Files:**
- Modify: `clients/flutter_app/test/widget/home_shell_test.dart`
- Modify: `clients/flutter_app/lib/src/screens/home_shell.dart`
- Modify: `clients/flutter_app/lib/src/app/app_strings.dart`

- [ ] **Step 1: Write failing widget tests**

Replace the existing `roles tab exposes agent harness detail` expectation with tests that assert:

- Roles tab shows `角色策略` and `标准六人局 · 本地草稿`.
- Roles render in a grid with cards for `狼人`, `预言家`, `女巫`, `村民`, `守卫`, `猎人`.
- Tapping `预言家` opens a full-screen route, not a modal sheet.
- Detail contains sections in this order: `身份边界`, `策略总览`, `决策倾向`, `行动策略`, `证据与上下文`, `运行时组合`.
- Tapping `强势带队` changes the local draft and shows `草稿未保存`.
- Flutter-only mode does not show `已保存`, `本局已冻结`, `v1.3`, or `引用`.

- [ ] **Step 2: Verify RED**

Run:

```powershell
cd clients/flutter_app
flutter test test/widget/home_shell_test.dart
```

Expected: fails because the page still uses the old `全部角色` documentation list and `Agent harness` sheet.

- [ ] **Step 3: Implement minimal UI**

Implement:

- `_RolesPage` as `StatefulWidget`.
- A pack header with local draft wording.
- A two-column `GridView`/`SliverGrid` role-card grid.
- `_RolePolicyDraft` and `_RolePolicyTemplate` local in `home_shell.dart`.
- Full-screen `_RolePolicyDetailPage` pushed via `Navigator`.
- A preset picker using buttons/chips and a focused bottom sheet for one setting row.
- Read-only boundary copy that states engine owns timing, legality, visibility, transitions, and victory.
- Runtime composition preview that says RolePolicy does not bind personality, provider, execution contract, runtime state, or team plan.

No backend calls, protocol fields, prompt text, provider settings, generated fixtures, or runtime changes.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
cd clients/flutter_app
flutter test test/widget/home_shell_test.dart
flutter analyze
flutter test
```

Expected: all pass.

- [ ] **Step 5: Commit and review**

Before commit:

```powershell
git branch --show-current
git status --short
git diff --stat
git diff --name-only
```

Commit:

```powershell
git add clients/flutter_app/lib/src/screens/home_shell.dart clients/flutter_app/lib/src/app/app_strings.dart clients/flutter_app/test/widget/home_shell_test.dart docs/PROJECT_MAP.md docs/TASKS.md MEMORY.md
git commit -m "feat: add p3-a2a local role policy editor"
```

Then run a code review for the commit range and fix Critical/Important issues before continuing.

---

### Task 2: P3-A-2b Minimal RolePolicy Asset Registry

**Files:**
- Create: `src/werewolf_eval/role_policy_registry.py`
- Create: `tests/test_role_policy_registry.py`
- Modify: `docs/PROJECT_MAP.md`
- Modify: `docs/TASKS.md`
- Modify: `MEMORY.md`

- [ ] **Step 1: Write failing registry tests**

Create tests that assert:

- Built-in seed registry exposes a `standard_six_player_balanced` RolePolicyPack with werewolf, seer, witch, villager, guard, and hunter refs.
- `RolePolicyPack` refs resolve to `validate_role_policy()`-valid RolePolicy objects.
- A draft can be created for one role without changing the published pack.
- Publishing an unreferenced draft can update the pack ref in place.
- Publishing a draft for a referenced policy creates a new policy version and keeps historical refs immutable.
- Registry rejects RolePolicy payloads containing `seat_character_card_ref`, `provider_profile_ref`, `execution_contract_ref`, `runtime_state_ref`, `team_plan`, `extra_call_budget`, `visibility_entitlement`, or `legal_action_window`.
- Registry stores no secrets and no provider credentials.

- [ ] **Step 2: Verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest tests.test_role_policy_registry -v
```

Expected: import failure for the new registry module.

- [ ] **Step 3: Implement registry**

Implement a standard-library registry with:

- `RolePolicyRegistry`
- `RolePolicyPackRef`
- `RolePolicyDraft`
- `RolePolicyRegistryError`
- JSON read/write helpers using canonical JSON.
- In-memory default seed data for P3-A-2b tests.
- Optional file-backed save/load path, but no observer endpoint and no runtime consumption.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest tests.test_role_policy_registry tests.test_agent_assets -v
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest discover -s tests -p "test_*.py"
```

Expected: all pass.

- [ ] **Step 5: Commit and review**

Commit:

```powershell
git add src/werewolf_eval/role_policy_registry.py tests/test_role_policy_registry.py docs/PROJECT_MAP.md docs/TASKS.md MEMORY.md .oh-my-harness/tree.md
git commit -m "feat: add p3-a2b role policy registry"
```

Then run a code review for the commit range and fix Critical/Important issues before continuing.

---

### Task 3: P3-A-3 AgentContextPacket

**Files:**
- Create: `src/werewolf_eval/agent_context_packet.py`
- Create: `tests/test_agent_context_packet.py`
- Modify: `docs/PROJECT_MAP.md`
- Modify: `docs/TASKS.md`
- Modify: `MEMORY.md`

- [ ] **Step 1: Write failing packet tests**

Create tests that assert:

- Minimal packet accepts Board facts, Self facts, Private facts, Public timeline, and Episodic notes.
- `FactRecord` can be rendered as engine fact only when writer is runtime/engine and source ids are present or static public source is declared.
- `ClaimRecord` renders as "seat claimed" semantics, never as truth.
- `BeliefRecord` renders as "this agent currently believes/suspects" semantics, never as engine truth.
- `CommitmentRecord` and `TeamPlanRecord` are non-fact records.
- Superseded/retracted records remain present and are not silently overwritten.
- `TeamPlanRecord` requires faction-private scope and authorized seat ids.
- Every renderable block includes `trust_class`, `render_mode`, `visibility_scope`, and `source_provenance`.
- Context budget reports included, compacted, and dropped blocks.

- [ ] **Step 2: Verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest tests.test_agent_context_packet -v
```

Expected: import failure for the new packet module.

- [ ] **Step 3: Implement packet model**

Implement pure schema helpers:

- `validate_agent_context_packet`
- `validate_memory_record`
- `render_record_summary`
- `select_visible_packet`
- `AgentContextPacketError`

No provider calls, no prompt byte changes, no engine behavior changes.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest tests.test_agent_context_packet tests.test_agent_assets tests.test_role_policy_registry -v
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest discover -s tests -p "test_*.py"
```

Expected: all pass.

- [ ] **Step 5: Commit and review**

Commit:

```powershell
git add src/werewolf_eval/agent_context_packet.py tests/test_agent_context_packet.py docs/PROJECT_MAP.md docs/TASKS.md MEMORY.md .oh-my-harness/tree.md
git commit -m "feat: add p3-a3 agent context packet"
```

Then run a code review for the commit range and fix Critical/Important issues before continuing.

---

### Task 4: P3-A-2c Runtime Consumption

**Files:**
- Inspect before editing: `src/werewolf_eval/emergent_engine.py`, `src/werewolf_eval/provider_agent.py`, prompt rendering helpers, prompt version tests.
- Modify only the minimal prompt/render path selected after inspection.
- Modify or create focused tests for prompt versioning, legacy byte-exact projection, role-policy block gating, and public leak scans.
- Modify `docs/specs/text-injection-channels.md` only if a new injection channel is introduced.
- Modify docs closeout files.

- [ ] **Step 1: Invoke prompt byte workflow**

Before changing model-visible text, read and follow `guarding-prompt-bytes`.

Decision gate:

- If preserving baseline bytes is feasible, add a coexisting roleplay prompt/render mode selected explicitly by runtime arm.
- If baseline bytes must change, bump prompt version and update ledger/goldens according to the skill.

Stop and ask the user if the correct prompt-version strategy is ambiguous.

- [ ] **Step 2: Write failing runtime tests**

Tests must assert:

- Legacy baseline render remains byte-exact when roleplay mode is off.
- Roleplay mode renders blocks only through a single PromptRenderer path.
- RolePolicy guidance appears only for the true role's entitled seat.
- Public observer artifacts/SSE payloads do not include hidden RolePolicy ids, roles, teams, RuntimeTeamState refs, or private memory refs.
- Human seats do not receive player provider profile refs.
- Runtime consumption records prompt block hashes and source provenance.

- [ ] **Step 3: Verify RED**

Run the focused prompt/runtime tests selected in Step 2.

Expected: tests fail because RolePolicy/AgentContextPacket is not consumed yet.

- [ ] **Step 4: Implement minimal consumption**

Implement:

- Single `PromptRenderer` entry point for roleplay mode.
- Fixed block order from the P3-A-1 spec.
- Render metadata: `trust_class`, `render_mode`, `visibility_scope`, `source_provenance`.
- RolePolicy block injected only after role entitlement passes.
- AgentContextPacket-derived beliefs/claims rendered as non-fact summaries.
- Explicit runtime arm flag so old baseline stays available.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest tests.test_prompt_versioning -v
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest discover -s tests -p "test_*.py"
```

Also run any focused Flutter tests only if UI copy changed.

- [ ] **Step 6: Commit and review**

Commit:

```powershell
git add <focused-runtime-files> <focused-tests> docs/PROJECT_MAP.md docs/TASKS.md MEMORY.md
git commit -m "feat: consume role policy in roleplay prompt path"
```

Then run a code review for the commit range and fix Critical/Important issues before continuing.

---

### Task 5: P3-A-4 First Playable Roleplay Arm

**Files:**
- Modify runtime/profile/launcher files only as required to expose an explicit shadow-safe roleplay arm.
- Modify tests for roleplay arm, cost accounting, leak scans, and baseline comparability.
- Modify docs closeout files.

- [ ] **Step 1: Write failing arm tests**

Tests must assert:

- A 6-player fake deterministic game can launch with roleplay arm enabled.
- SeatCharacterCard differences are represented in the resolved prompt/context metadata without encoding true roles.
- RolePolicy is true-role scoped and never appears in live public artifacts.
- Belief/claim records are not rendered as engine facts.
- Werewolf RuntimeTeamState is visible only to authorized wolf seats.
- Old baseline still runs with roleplay arm disabled.
- Provider/scaffold/team call accounting records owner, visibility scope, token usage when available, latency when available, context block hash, and fallback result.
- Shadow output is auditable without changing engine adjudication or legal action validation.

- [ ] **Step 2: Verify RED**

Run focused new tests.

Expected: fail because no roleplay arm launch path exists.

- [ ] **Step 3: Implement minimal arm**

Implement:

- Explicit roleplay-arm option in profile/launcher or runtime config.
- Built-in starter RolePolicyPack from P3-A-2b.
- Built-in starter SeatCharacterCards that remain role-agnostic.
- RuntimeSeatState/RuntimeTeamState initialization for the arm.
- Shadow-safe prompt/context metadata and audit artifacts.
- No new open-ended planner loop; ordinary player action remains one player model call.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest <focused-roleplay-arm-tests> -v
$env:PYTHONPATH='src'; $env:NO_PROXY='*'; python -m unittest discover -s tests -p "test_*.py"
```

- [ ] **Step 5: Commit and review**

Commit:

```powershell
git add <focused-runtime-files> <focused-tests> docs/PROJECT_MAP.md docs/TASKS.md MEMORY.md
git commit -m "feat: add p3-a4 roleplay shadow arm"
```

Then run a final code review for the commit range and fix Critical/Important issues before marking the goal complete.

---

## Global Stop Conditions

Stop and ask the user if any of these happen:

- A prompt-version decision is ambiguous.
- Runtime consumption would require broad provider, validator, generated fixture, or observer protocol rewrites.
- The asset registry starts duplicating profile_config instead of staying RolePolicyPack-scoped.
- Flutter local draft UI needs real persistence to be honest.
- Tests indicate hidden-role or faction-state leakage.
- The implementation begins turning RolePolicy into SeatCharacterCard, ProviderProfile, ExecutionContract, RuntimeState, or team-plan storage.

## Global Validation Contract

At every task closeout report:

- `git diff --stat`
- `git diff --name-only`
- allowlist check for the task
- forbidden-scope check for unintended `src/**`, `tests/**`, `clients/**`, `docs/secrets/**`, `docs/adr/**`, `docs/generated-games/**`, `docs/gold-game/**`, `docs/demo/**`, `docs/game-scripts/**`, or `.github/workflows/**`
- tests run and exact outcome
- code review result and any fixes applied


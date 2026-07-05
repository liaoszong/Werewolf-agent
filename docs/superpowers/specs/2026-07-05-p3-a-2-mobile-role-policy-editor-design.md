# P3-A-2 Mobile Role Policy Editor Design

> Status: DESIGN
> Date: 2026-07-05
> Scope: P3-A-2, SYS-B5 Agent Card / Playbook assets, SYS-C6 Flutter client
> Decision: mobile role page is a RolePolicyPack-scoped editor. It explains
> and edits how each identity plays, without binding role strategy to seat
> personality, provider settings, runtime memory, prompt bytes, or engine
> authority.

---

## 1. Context

The Flutter client already has a mobile role library shell. Today each role
card opens a read-only sheet with agent harness, memory, and prompt summaries.
That was useful for P3-E-2, but it still reads like documentation. P3-A needs
the role page to become a concrete entry point for configuring role-specific
agent behavior.

P3-A-1 split agent ownership into four layers:

1. `SeatCharacterCard`: role-agnostic personality and speech style.
2. `RolePolicy`: true-role-specific strategy and playbook.
3. `RuntimeState`: run-scoped seat and faction state.
4. `ProviderProfile`: provider/model/budget execution knobs.

The mobile role page should not mirror those four layers as four equal tabs.
The user task is simpler: when they tap "狼人", "预言家", "女巫", or "村民",
they want to understand and tune how that identity plays. Therefore the role
page's main subject is `RolePolicy` within a selected `RolePolicyPack`.
Personality, provider settings, execution contracts, runtime memory, and team
plans are not owned by this page and must not become persisted RolePolicy
fields.

Route note: `docs/PROJECT_MAP.md` currently names P3-A-2 as "Agent memory
packet". This spec uses the user's requested P3-A-2 title for a UI-facing
RolePolicy editor design. Before implementation planning, the route index
should be reconciled so the memory-packet work and mobile role-policy editor do
not share the same task id silently.

This design is docs-only. It does not change runtime behavior, provider calls,
prompt bytes, validators, generated fixtures, or engine adjudication.

---

## 2. Decision

Build the mobile role page as a role strategy entry point:

```text
Roles
  -> current RolePolicyPack selector
  -> two-column role policy card grid
  -> full-screen role detail page
     -> read-only role boundary
     -> strategy preset
     -> decision tendencies
     -> role-specific action strategy
     -> evidence focus and context preferences
     -> read-only runtime composition preview
     -> version and frozen-run status
```

Primary user promise:

> "For this role in the selected strategy pack, I can see what evidence the
> agent prioritizes, what tactical posture it takes, when it accepts risk, how
> it prefers to use role abilities, and how those preferences will combine with
> each seat's own personality and runtime configuration at game launch."

Primary safety promise:

> "The editor never changes role permissions, legal action windows, information
> entitlement, victory rules, PromptRenderer block order, or live run snapshots."

Object relationship:

```text
RolePolicyPack
  -> per-role RolePolicy refs for one ruleset/strategy package

AgentPreset / MatchProfile
  -> seat SeatCharacterCard assignments
  -> seat/provider ProviderProfile assignments
  -> ExecutionContract selection
  -> RolePolicyPack ref

Game launch
  -> seat p1 draws werewolf
     -> p1 SeatCharacterCard
     -> p1 ProviderProfile
     -> selected pack's werewolf RolePolicy
     -> RuntimeSeatState[p1]
  -> werewolf faction
     -> RuntimeTeamState[werewolf]
```

The role page edits only the RolePolicy selected by the active RolePolicyPack.
It may preview how final composition works, but it does not bind a role to a
seat personality, provider profile, execution contract, runtime state, or team
plan.

---

## 3. Design Goals

1. Make every role feel like a distinct agent design, especially on mobile.
2. Keep the default path understandable without exposing prompt engineering.
3. Preserve the P3-A-1 ownership split: RolePolicy is the main editable object;
   RolePolicyPack gives it a visible strategy-package scope; SeatCharacterCard,
   ProviderProfile, ExecutionContract, RuntimeState, and RuntimeTeamState stay
   outside the RolePolicy payload.
4. Make safe edits obvious: strategy presets and structured controls, not a
   free-form prompt box.
5. Keep pregame editing separate from live-run inspection. A policy used by a
   run is frozen for that run.
6. Produce a later implementation plan that can remain client/protocol-safe
   before runtime prompt integration.
7. Keep RolePolicy preferences separate from execution authorization: a policy
   may request review or targeted history, but only ExecutionContract,
   ProviderProfile, visibility, and remaining budget decide whether extra work
   actually runs.

---

## 4. Non-goals

- No runtime prompt byte changes.
- No provider or model request changes.
- No participant protocol changes in this design.
- No engine legality, phase, visibility, or victory-rule edits.
- No direct editing of `RuntimeSeatState` or `RuntimeTeamState`.
- No free-form "insert into prompt" editor.
- No role policy consumption by runtime in this slice.
- No desktop Qt redesign. Qt may keep its legacy seat editor until parity
  decisions are made.
- No route-authority edit inside this spec. `PROJECT_MAP.md` reconciliation is
  a follow-up route maintenance action.
- No RolePolicy field may persist `seat_character_card_ref`,
  `provider_profile_ref`, `execution_contract_ref`, `runtime_state_ref`, or
  team plan refs.
- No RolePolicy field may authorize extra model calls, tool budgets, visibility
  entitlement, or legal action windows.

---

## 5. UX Information Architecture

### 5.0 Strategy pack scope

The role index must show the current strategy-pack scope before showing role
cards:

```text
角色策略

当前策略包
标准六人局 · 平衡版 v1.2 >
```

The pack defines which RolePolicy is active for each role in the selected
ruleset. Editing "狼人" means:

```text
edit werewolf RolePolicy
  -> create or update a RolePolicy draft/revision
  -> update current RolePolicyPack's werewolf ref when saved/published
  -> do not affect other packs or historical run snapshots
```

This scope avoids ambiguous "current strategy" wording. A strategy is current
only relative to the selected RolePolicyPack, not globally and not for every
future match.

### 5.1 Role index

The role index should use a two-column grid, not a long list. Each card is a
compact strategy summary:

```text
[ 狼人            ] [ 预言家          ]
  平衡控场策略        信息主导策略
  已启用 · 自定义      已启用 · 默认
  平衡               稳健

[ 女巫            ] [ 村民            ]
  资源时机策略        证据推理策略
  已启用 · 自定义      已启用 · 默认
  谨慎               主动
```

Each card shows only:

- Role icon and localized role name.
- Current strategy summary.
- Configuration state:
  `available_default | available_custom | needs_policy |
  not_in_ruleset | not_available_in_current_pack`.
- One tendency tag: `保守 | 平衡 | 激进 | 稳健 | 主动`.

The card must not show model parameters, prompt text, runtime memory records,
hashes, provider traces, or hidden run facts.

Cards for roles outside the selected ruleset should not appear in the main
grid. If the product wants discovery for future roles, place them under a
separate "其他规则角色" section with `not_in_ruleset` status.

### 5.2 Role detail page

The detail surface should be a full-screen mobile page, not a dense bottom
sheet. A bottom sheet can still be used for editing one setting at a time.

Page structure:

1. Header: role, enabled/frozen badge, current RolePolicyPack, current
   strategy, ruleset, policy version.
2. Role boundary: read-only ability, team, victory condition, and rule limits.
3. Strategy overview: selected preset and short explanation.
4. Decision tendencies: role-general strategy controls.
5. Role-specific action strategy: ability and action policy controls.
6. Evidence focus and context preferences: what evidence this role prioritizes.
7. Runtime composition preview: how this policy combines with seat assets later.
8. Version and frozen-run status.
9. Sticky primary action in editable mode: Save / Create New Version.

The page is vertically scrollable. It should not use four or five complex tabs
on mobile.

---

## 6. Editable Surface

### 6.1 Strategy overview

Every role has three initial presets plus custom mode. Presets map to structured
RolePolicy settings, not raw prompt text.

| Role | Presets |
|---|---|
| Werewolf | `保守潜伏` / `平衡控场` / `激进带节奏` |
| Seer | `稳健验人` / `强势带队` / `隐藏身份` |
| Witch | `保守保药` / `信息优先` / `关键轮次强干预` |
| Villager | `跟踪票型` / `发言矛盾优先` / `主动带讨论` |
| Guard | `保守守护` / `反逻辑守护` / `风险博弈` |
| Hunter | `低调存活` / `威慑控场` / `关键反制` |

Changing a preset updates a draft. It does not immediately mutate a frozen
policy used by existing runs.

### 6.2 Decision tendencies

These settings are shared in shape across roles but have role-specific labels
and choices.

Example rows:

- Evidence priority: claim conflicts, vote shifts, speech contradictions,
  death rhythm, pressure on self, pressure on teammates.
- Day discussion posture: observe conservatively, explain evidence, apply
  gentle pressure, lead assertively, reconcile conflicts.
- Risk posture: conservative, balanced, high-pressure.
- Claim posture: avoid claim, claim under pressure, proactive claim when useful.
- Vote posture: independent reasoning, follow trusted lead, pressure swing
  votes, protect role information.
- Team coordination, for werewolf roles only: protect teammates, conditional
  protection, strategic distancing, self-preservation.

Each row opens a bottom-sheet picker with 3-5 choices and one explanation:

```text
队友协作

○ 尽量保护队友
○ 有条件保护
● 有限保护，必要时切割
○ 优先隐藏自己

说明:
该设置影响发言与投票倾向，不会改变狼人之间的信息权限或游戏规则。
```

For werewolf team coordination, the drawer must also state:

```text
该设置只影响该身份的个人决策倾向。
实际狼队计划属于对局运行状态，不会在这里创建、共享或修改。
```

### 6.3 Role-specific action strategy

This is the highest-value section. It makes each role feel different.

Werewolf:

- Night kill target priority.
- Teammate exposure handling.
- Counterclaim tendency.
- Day vote steering style.
- Self-preservation vs team-protection balance.

Seer:

- Check target priority.
- Claim timing.
- Information release cadence.
- Response when challenged.
- Vote guidance confidence threshold.

Witch:

- Save threshold.
- Poison threshold.
- Potion conservation posture.
- Evidence priority before poison.
- Decision review preference, such as prefer review when high risk.

Villager:

- Public stance threshold.
- Follow-vote tendency.
- Contradiction tracking emphasis.
- Commitment follow-through preference.
- Pressure-question style.

Guard:

- Guard target priority.
- Repeat-guard constraint explanation.
- Protection around claimed roles.
- Anti-obvious-protect risk posture.
- Decision review preference.

Hunter:

- Shot restraint.
- Target ranking basis.
- Final-word posture.
- Anti-bait rule.
- Threat signaling posture.

Decision review and targeted history settings are preferences only. They do not
grant extra API calls, extra tool rounds, or extra token budget. The execution
path is:

```text
RolePolicy requests review/history
  + ExecutionContract allows the loop/tool
  + ProviderProfile budget remains available
  + visibility entitlement passes
  -> harness may execute the review/history step
```

### 6.4 Evidence focus and context preferences

The UI should translate context-selection preferences into user-facing
language. It does not edit RuntimeState and does not expose JSON, event cursors,
hashes, or sealed snapshot ids.

Editable settings:

- Role claim conflict priority: low / medium / high.
- Vote-shift priority: low / medium / high.
- Public commitment attention: low / medium / high.
- Self-suspicion attention: low / medium / high.
- Contradiction priority: low / medium / high.
- Teammate-risk attention, only for faction-authorized roles: low / medium /
  high.
- History retrieval preference: recent only / recent plus high-relevance
  history / prioritize vote and claim evidence.
- Citation preference: player only / player and round / player, round, and
  evidence type.
- Commitment follow-through: low / medium / high.

Forbidden settings:

- Read another seat's private memory.
- Read true hidden roles outside entitlement.
- Read judge/engine state not visible to the role.
- Treat beliefs or claims as engine facts.
- Bypass the PromptRenderer or visibility oracle.

Ownership chain:

```text
RolePolicy
  -> defines evidence/context preferences
ContextSelector
  -> selects visible evidence within budget
RuntimeSeatState
  -> stores actual claims, votes, commitments, beliefs, and updates for a run
```

### 6.5 Runtime composition preview

The role page may explain composition, but it must not persist personality or
provider refs inside RolePolicy:

```text
运行时组合

本策略不会绑定具体人格或模型。
开局后，它将与每个 AI 座位自己的角色人格和运行配置组合。

查看 Agent 配置 >
查看本局实际组合 >
```

Rules:

- Personality edits belong to a character/personality library or match setup.
- ProviderProfile edits belong to AI runtime settings or match setup.
- ExecutionContract selection belongs to match/runtime configuration.
- The role page can show a read-only composition explanation.
- "查看本局实际组合" is available only in an entitled live/history context.
- Provider secrets are never shown or edited here.
- RolePolicy payloads must not contain `seat_character_card_ref`,
  `provider_profile_ref`, `execution_contract_ref`, `runtime_state_ref`, or
  `team_plan_ref`.

---

## 7. Read-only Boundaries

The role detail page must show what cannot be edited. This prevents users from
mistaking strategy controls for engine controls.

Read-only role boundary fields:

- Role ability.
- Team.
- Victory condition.
- Legal action windows.
- Information entitlement summary.
- Ruleset compatibility.

Hard non-editable authority:

- Engine determines decision windows, legal action space, information
  entitlement, state transitions, and victory adjudication.
- PromptRenderer determines fixed model-visible block order.
- RuleEngine validates and executes actions.
- Visibility oracle filters every live and prompt-facing context source.
- RuntimeState for an active run is frozen to that run's execution contract and
  asset snapshot.

---

## 8. Editing Modes and Versioning

### 8.1 Implementation slices

The UI can be implemented in stages, but each stage must be honest about what
is real.

P3-A-2a: Flutter local draft UI

Behavior:

- Shows the role grid, detail page, pickers, and local draft preview.
- Does not claim a policy was saved, versioned, frozen, or referenced by runs.
- Labels the surface as local preview/draft.
- Does not add backend persistence, protocol fields, prompt consumption, or
  runtime behavior.

P3-A-2b: minimal asset registry

Behavior:

- Adds authoritative RolePolicyPack / RolePolicy read and write paths.
- Supports draft creation, revision publishing, and reference checks.
- Can truthfully show version numbers, frozen state, and run reference counts.
- Still does not change provider behavior, prompt rendering, validators, or
  game engine adjudication.

P3-A-2c: runtime consumption

Behavior:

- Runtime consumes RolePolicy through PromptRenderer / AgentContextPacket.
- Any model-visible byte change follows prompt version/golden/ledger rules.
- ExecutionContract and ProviderProfile remain responsible for loop/tool
  permissions and budgets.

### 8.2 Pregame library mode

The role page is editable when the user is configuring future runs and the
implementation has either local-draft mode or asset-registry support.

Behavior:

- Edits are draft-first.
- In local-draft mode, the primary action is preview/apply-to-local-draft only.
- With asset registry support, save writes a new RolePolicy version when the
  policy has existing run references.
- Existing run artifacts remain immutable.
- The UI explains whether the save mutates an unused draft, saves only local
  preview state, or creates a new version.

### 8.3 Live or history inspection mode

A role policy referenced by a live or completed run is read-only.

UI copy:

```text
本局已冻结
当前使用: 狼人策略 v1.2
```

Available action:

```text
[复制为新版本]
```

The copy is for future runs only. It must not affect the current run, replay,
or audit output.

This mode requires asset registry or run snapshot support. A Flutter-only local
draft implementation must not show real frozen/reference claims.

### 8.4 Unsaved draft state

The editor should show:

- `草稿未保存`
- `保存将创建 v1.3，不会改写旧对局`
- `当前配置正被 N 局历史对局引用`

The latter two messages are allowed only when backed by asset registry data.
Drafts are client-visible configuration state, not runtime facts.

---

## 9. Conceptual Data Shape

This design does not require final backend schema, but later implementation
should preserve these concepts.

```json
{
  "schema_version": "p3a.mobile_role_policy_editor.v2",
  "policy_pack_ref": {
    "pack_id": "standard_six_player_balanced",
    "version": "1.2.0"
  },
  "role": "werewolf",
  "policy_ref": {
    "policy_id": "standard_werewolf_balanced",
    "version": "1.2.0",
    "status": "custom",
    "frozen_for_run": false
  },
  "applicability": {
    "ruleset_id": "rules_v1_2",
    "seat_count": [6]
  },
  "preset_ref": {
    "preset_id": "balanced_control",
    "version": "1.0.0"
  },
  "tactical_preferences": {
    "evidence_priority": ["vote_shift", "claim_conflict", "speech_contradiction"],
    "discussion_posture": "gentle_pressure",
    "risk_posture": "balanced",
    "claim_strategy": "claim_under_pressure",
    "vote_strategy": "soft_consensus"
  },
  "action_preferences": {
    "night_kill_priority": "high_threat_non_wolf",
    "teammate_exposure_posture": "conditional_distancing",
    "decision_review_preference": "prefer_when_high_risk",
    "targeted_history_preference": "allow_when_relevant"
  },
  "evidence_context_preferences": {
    "priority_order": ["vote_shift", "claim_conflict", "speech_contradiction"],
    "commitment_follow_through": "high",
    "history_retrieval_preference": "recent_plus_targeted",
    "citation_preference": "player_and_round"
  }
}
```

This object is a UI/editor projection, not the engine's authority. The actual
runtime still resolves through P3-A-1 assets and execution contracts.

Fields that must not appear in this RolePolicy editor projection:

- `seat_character_card_ref`
- `provider_profile_ref`
- `execution_contract_ref`
- `runtime_state`
- `runtime_state_ref`
- `team_plan`
- `extra_call_budget`
- `history_tool_budget`
- `visibility_entitlement`
- `legal_action_window`

---

## 10. Safety and Visibility Requirements

- Public role-library pages may show generic role strategy templates.
- Live participant pages may show only the participant's entitled role/private
  state.
- Public observer pages must not reveal another hidden seat's true role,
  RolePolicy id, faction plan, private memory, or joinable hash.
- RolePolicy text and user-provided labels are untrusted data when rendered to
  a model later.
- The mobile editor must not create arbitrary prompt insertion points.
- Any future runtime consumption of edited policies must follow prompt
  byte/version/golden/ledger rules if model-visible bytes change.
- RolePolicy choices can influence speech, strategy, and action proposals only
  within engine-created decision windows.
- Illegal action proposals remain server-rejected.
- Visibility filtering occurs server-side before Flutter serialization. The
  Flutter client must never receive another seat's role-private policy,
  faction state, private memory, or hidden asset reference during a live game.

Endpoint expectations for later protocol work:

- Public role library endpoint: returns only generic role templates and public
  strategy descriptions.
- Participant endpoint: returns only the participant's entitled private policy
  projection and private state.
- Observer endpoint: returns public role templates and public run state, not any
  hidden seat's RolePolicy ref.
- Postgame/audit endpoint: returns sealed snapshots only after game end or
  explicit audit authorization.

---

## 11. Implementation Options Considered

### Option A: RolePolicyPack-scoped mobile editor with staged persistence (recommended)

Build a mobile grid and full-screen role detail around structured RolePolicy
settings inside an explicit RolePolicyPack. Keep personality, provider,
execution, runtime memory, and team plans outside the RolePolicy payload. Start
with local drafts only if backend persistence is not approved; add a minimal
asset registry before showing true save/version/frozen/reference semantics.

Pros:

- Matches the mobile user task.
- Preserves P3-A-1 ownership boundaries.
- Avoids exposing prompt internals as the main editing surface.
- Supports future A/B testing by structured policy version.
- Keeps implementation honest: UI-only mode cannot pretend to save authoritative
  versions.

Cons:

- Requires mapping user-friendly controls into RolePolicy schema later.
- Requires a minimal asset registry before real version/freeze/reference UI.
- Does not make runtime agents behave differently until an integration slice
  consumes the policy.

### Option B: Four-layer technical editor

Expose SeatCharacterCard, RolePolicy, RuntimeState, and ProviderProfile as
parallel tabs.

Pros:

- Directly mirrors architecture.
- Useful for developers.

Cons:

- Poor mobile UX.
- Encourages users to treat personality, role strategy, provider settings, and
  runtime state as the same kind of object.
- Risky around RuntimeState and hidden-information boundaries.
- Breaks role shuffle semantics if role pages bind persona/model choices to
  identities.

### Option C: Prompt editor

Let users edit role prompts directly.

Pros:

- Fast to build on top of existing legacy prompt fields.

Cons:

- Recreates the P2 problem of blended prompt strings.
- Unsafe for prompt byte/versioning and visibility.
- Hard to audit, compare, or attribute in P4.

Decision: choose Option A.

---

## 12. Validation Strategy for the Future Implementation Plan

UI structure tests:

- Role page uses a role-card grid, not a single long documentation list.
- Role index displays the selected RolePolicyPack before role cards.
- Role detail opens as a full-screen page on mobile.
- Cards show role name, summary, pack-scoped config state, and tendency tag
  only.
- Role detail contains the required sections in order.
- Editing one setting uses a focused picker/sheet rather than exposing raw JSON
  or prompt text.

Schema/projection tests:

- Editor projection can represent all built-in roles: werewolf, seer, witch,
  villager, guard, hunter.
- Preset selection maps to structured draft fields.
- Editor projection includes RolePolicyPack, RolePolicy, applicability,
  tactical preferences, action preferences, and evidence/context preferences.
- Editor projection does not include `seat_character_card_ref`,
  `provider_profile_ref`, `execution_contract_ref`, runtime state refs, team
  plans, extra-call budgets, visibility entitlement, or legal action windows.
- Frozen policies cannot be mutated in place.
- Saving a referenced policy creates a new version only in asset-registry mode.
- Flutter-only local draft mode does not show authoritative saved version,
  frozen, or run-reference claims.
- `available_default`, `available_custom`, `needs_policy`, `not_in_ruleset`,
  and `not_available_in_current_pack` are distinguishable.

Boundary tests:

- No mobile role-policy editor path changes runtime prompt bytes.
- No editor payload can set role/team visibility entitlement, legal actions, or
  phase windows.
- No RolePolicy setting grants extra model calls, extra tool rounds, token
  budget, or timeout budget.
- No public observer path can read seat-private RolePolicy refs or runtime
  memory.
- RuntimeState is displayed only as capability explanation or frozen run
  status, not as editable live state.
- Flutter never receives another seat's role-private policy, faction state,
  private memory, or hidden asset reference during a live game.

Flutter tests:

- Widget tests cover grid layout, detail navigation, editable and frozen modes,
  dirty draft label, and "copy as new version" state.
- In Flutter-only local draft mode, widget tests verify no real version/frozen
  wording appears.
- Accessibility labels exist for role cards, setting rows, and bottom-sheet
  choices.
- Text fits within cards on narrow mobile widths.

No backend/runtime tests are required for P3-A-2a local-draft UI. P3-A-2b asset
registry requires backend persistence and authorization tests. P3-A-2c runtime
consumption requires prompt byte/version validation and runtime tests.

---

## 13. Acceptance Criteria

For this design:

- Role page is explicitly RolePolicy-first.
- Role page is scoped by a selected RolePolicyPack.
- Mobile UX uses a two-column role grid plus full-screen detail.
- Editable fields are structured strategy controls, not raw prompt text.
- SeatCharacterCard, ProviderProfile, ExecutionContract, RuntimeSeatState, and
  RuntimeTeamState are not persisted in RolePolicy or its editor projection.
- RuntimeState is not directly editable.
- Evidence and context controls are preferences for ContextSelector, not direct
  RuntimeState edits.
- Review/history controls are preferences only; budgets and permissions remain
  in ExecutionContract, ProviderProfile, visibility, and runtime budget checks.
- Pregame edits and live/history inspection are separated.
- Flutter-only local draft mode is distinguished from real asset-registry save
  and version semantics.
- Server-side visibility filtering is required before Flutter serialization for
  any live private policy or state projection.
- Existing P3-A-1 prompt/runtime/provider/validator/generated-fixture
  boundaries remain closed.
- Route conflict with the existing P3-A-2 "Agent memory packet" label is called
  out for follow-up reconciliation before implementation planning.

For the follow-up implementation plan:

- Start with a Flutter-only UI/projection slice unless backend persistence is
  explicitly approved; if so, label it local draft/preview and do not show real
  save/version/frozen/reference claims.
- If real saving/versioning is required, first add a minimal RolePolicyPack /
  RolePolicy asset registry without runtime consumption.
- Keep observer/participant protocol unchanged unless a later plan opens it.
- Include widget tests for mobile layout and frozen/editable states.
- Include forbidden-scope checks proving no `src/**`, provider, prompt golden,
  validator, generated fixture, or runtime behavior changed.

---

## 14. References

- P3 pivot: `docs/superpowers/specs/2026-07-02-agent-roleplay-human-game-pivot-design.md`
- P3-A-1 ownership schema: `docs/superpowers/specs/2026-07-05-p3-a-1-agent-asset-ownership-schema-design.md`
- Project authority: `docs/PROJECT_MAP.md`
- Task index: `docs/TASKS.md`
- Flutter role shell: `clients/flutter_app/lib/src/screens/home_shell.dart`
- Flutter strings: `clients/flutter_app/lib/src/app/app_strings.dart`
- Prompt injection registry: `docs/specs/text-injection-channels.md`

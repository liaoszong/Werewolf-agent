# P3-A-2 Mobile Role Policy Editor Design

> Status: DESIGN
> Date: 2026-07-05
> Scope: P3-A-2, SYS-B5 Agent Card / Playbook assets, SYS-C6 Flutter client
> Decision: mobile role page is a RolePolicy-first editor. It explains and
> edits how each identity plays, without exposing runtime secrets, prompt bytes,
> or engine authority.

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
page's main subject is `RolePolicy`. Personality, provider, runtime memory,
and execution budget appear only as references, summaries, or advanced exits.

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
  -> two-column role policy card grid
  -> full-screen role detail page
     -> read-only role boundary
     -> strategy preset
     -> decision tendencies
     -> role-specific action strategy
     -> memory and evidence behavior
     -> linked personality/provider summaries
     -> version and frozen-run status
```

Primary user promise:

> "For this role, I can see what evidence the agent prioritizes, how it speaks,
> when it takes risks, how it uses role abilities, what it remembers, and which
> shared personality/provider profile it references."

Primary safety promise:

> "The editor never changes role permissions, legal action windows, information
> entitlement, victory rules, PromptRenderer block order, or live run snapshots."

---

## 3. Design Goals

1. Make every role feel like a distinct agent design, especially on mobile.
2. Keep the default path understandable without exposing prompt engineering.
3. Preserve the P3-A-1 ownership split: RolePolicy is the main editable object;
   SeatCharacterCard and ProviderProfile are linked assets; RuntimeState is
   run-scoped and mostly read-only.
4. Make safe edits obvious: strategy presets and structured controls, not a
   free-form prompt box.
5. Keep pregame editing separate from live-run inspection. A policy used by a
   run is frozen for that run.
6. Produce a later implementation plan that can remain client/protocol-safe
   before runtime prompt integration.

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

---

## 5. UX Information Architecture

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
- Configuration state: `default | custom | missing | disabled`.
- One tendency tag: `保守 | 平衡 | 激进 | 稳健 | 主动`.

The card must not show model parameters, prompt text, runtime memory records,
hashes, provider traces, or hidden run facts.

### 5.2 Role detail page

The detail surface should be a full-screen mobile page, not a dense bottom
sheet. A bottom sheet can still be used for editing one setting at a time.

Page structure:

1. Header: role, enabled/frozen badge, current strategy, ruleset, policy
   version.
2. Role boundary: read-only ability, team, victory condition, and rule limits.
3. Strategy overview: selected preset and short explanation.
4. Decision tendencies: role-general strategy controls.
5. Role-specific action strategy: ability and action policy controls.
6. Memory and evidence: what the agent tracks and how it cites evidence.
7. Linked assets: personality and provider summaries.
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
- Day speech style: reserved, explanatory, assertive, pressure-building,
  conciliatory.
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
- High-risk action review toggle.

Villager:

- Public stance threshold.
- Follow-vote tendency.
- Contradiction tracking emphasis.
- Commitment tracking toggle.
- Pressure-question style.

Guard:

- Guard target priority.
- Repeat-guard constraint explanation.
- Protection around claimed roles.
- Anti-obvious-protect risk posture.
- Night action review toggle.

Hunter:

- Shot restraint.
- Target ranking basis.
- Final-word posture.
- Anti-bait rule.
- Threat signaling posture.

### 6.4 Memory and evidence behavior

The UI should translate RuntimeState concepts into user-facing behavior. It
does not expose JSON, event cursors, hashes, or sealed snapshot ids.

Editable settings:

- Track public role claims.
- Track vote changes.
- Track public commitments.
- Track who suspects this seat.
- Track contradictions.
- Track teammate risk, only for faction-authorized roles.
- Read recent speech by default, with optional targeted historical lookup.
- Prefer citing player and round when speaking.
- Carry own commitments into later speech.

Forbidden settings:

- Read another seat's private memory.
- Read true hidden roles outside entitlement.
- Read judge/engine state not visible to the role.
- Treat beliefs or claims as engine facts.
- Bypass the PromptRenderer or visibility oracle.

### 6.5 Linked personality and provider summaries

The role page may show references, but not make them the main path:

```text
角色表现
人格风格: 冷静证据派 >
运行模型: 标准对局配置 >
```

Rules:

- Personality edits belong to a character/personality library.
- ProviderProfile edits belong to AI runtime settings.
- The role page can choose a linked profile.
- "Make role-specific copy" creates a draft copy instead of mutating the shared
  asset.
- Provider secrets are never shown or edited here.

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

### 8.1 Pregame library mode

The role page is editable when the user is configuring future runs.

Behavior:

- Edits are draft-first.
- Save writes a new RolePolicy version when the policy has existing run
  references.
- Existing run artifacts remain immutable.
- The UI explains whether the save mutates an unused draft or creates a new
  version.

### 8.2 Live or history inspection mode

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

### 8.3 Unsaved draft state

The editor should show:

- `草稿未保存`
- `保存将创建 v1.3，不会改写旧对局`
- `当前配置正被 N 局历史对局引用`

Drafts are client-visible configuration state, not runtime facts.

---

## 9. Conceptual Data Shape

This design does not require final backend schema, but later implementation
should preserve these concepts.

```json
{
  "schema_version": "p3a.mobile_role_policy_editor.v1",
  "role": "werewolf",
  "policy_ref": {
    "policy_id": "standard_werewolf_balanced",
    "version": "1.2.0",
    "status": "custom",
    "frozen_for_run": false
  },
  "strategy_preset": "balanced_control",
  "decision_tendencies": {
    "evidence_priority": ["vote_shift", "claim_conflict", "speech_contradiction"],
    "day_speech_style": "gentle_pressure",
    "risk_posture": "balanced",
    "claim_posture": "claim_under_pressure"
  },
  "role_action_strategy": {
    "night_kill_priority": "high_threat_non_wolf",
    "teammate_coordination": "conditional_distancing",
    "vote_steering": "soft_consensus"
  },
  "memory_evidence_settings": {
    "track_claims": true,
    "track_votes": true,
    "track_commitments": true,
    "track_self_suspicion": true,
    "history_lookup_mode": "recent_plus_targeted",
    "citation_style": "player_and_round"
  },
  "linked_assets": {
    "seat_character_card_ref": "calm_logician@1.0.0",
    "provider_profile_ref": "standard_game@1.0.0"
  }
}
```

This object is a UI/editor projection, not the engine's authority. The actual
runtime still resolves through P3-A-1 assets and execution contracts.

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

---

## 11. Implementation Options Considered

### Option A: RolePolicy-first mobile editor (recommended)

Build a mobile grid and full-screen role detail around structured RolePolicy
settings. Keep personality and provider as linked summaries.

Pros:

- Matches the mobile user task.
- Preserves P3-A-1 ownership boundaries.
- Avoids exposing prompt internals as the main editing surface.
- Supports future A/B testing by structured policy version.

Cons:

- Requires mapping user-friendly controls into RolePolicy schema later.
- Does not immediately make runtime agents behave differently until an
  integration slice consumes the policy.

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
- Role detail opens as a full-screen page on mobile.
- Cards show role name, summary, config state, and tendency tag only.
- Role detail contains the required sections in order.
- Editing one setting uses a focused picker/sheet rather than exposing raw JSON
  or prompt text.

Schema/projection tests:

- Editor projection can represent all built-in roles: werewolf, seer, witch,
  villager, guard, hunter.
- Preset selection maps to structured draft fields.
- Linked personality/provider refs remain references, not inline prompt or
  secret-bearing data.
- Frozen policies cannot be mutated in place.
- Saving a referenced policy creates a new version.

Boundary tests:

- No mobile role-policy editor path changes runtime prompt bytes.
- No editor payload can set role/team visibility entitlement, legal actions, or
  phase windows.
- No public observer path can read seat-private RolePolicy refs or runtime
  memory.
- RuntimeState is displayed only as capability explanation or frozen run
  status, not as editable live state.

Flutter tests:

- Widget tests cover grid layout, detail navigation, editable and frozen modes,
  dirty draft label, and "copy as new version" state.
- Accessibility labels exist for role cards, setting rows, and bottom-sheet
  choices.
- Text fits within cards on narrow mobile widths.

No backend/runtime tests are required for the initial UI-only implementation
unless the implementation adds protocol or persistence.

---

## 13. Acceptance Criteria

For this design:

- Role page is explicitly RolePolicy-first.
- Mobile UX uses a two-column role grid plus full-screen detail.
- Editable fields are structured strategy controls, not raw prompt text.
- SeatCharacterCard and ProviderProfile are references/summaries, not the main
  role page body.
- RuntimeState is not directly editable.
- Pregame edits and live/history inspection are separated.
- Existing P3-A-1 prompt/runtime/provider/validator/generated-fixture
  boundaries remain closed.
- Route conflict with the existing P3-A-2 "Agent memory packet" label is called
  out for follow-up reconciliation before implementation planning.

For the follow-up implementation plan:

- Start with a Flutter-only UI/projection slice unless backend persistence is
  explicitly approved.
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

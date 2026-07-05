# P3-A-1 Agent Asset Ownership / Schema Design

> Status: DESIGN
> Date: 2026-07-05
> Scope: P3-A-1, SYS-B5 Agent Card / Playbook assets
> Decision: schema-first bridge. Define ownership and resolved artifact shape before changing runtime prompts.

---

## 1. Context

P3 has already pivoted from evaluation-first to Agent roleplay plus human
participation. The current system can run, watch, audit, and join a single
human seat, but AI seats are still mostly "provider call plus persona text".

Existing implementation already contains two partial asset ideas:

- `profile_config.role_defaults[role].prompt`: role-tracking strategy text.
- `profile_config.seat_personas[seat]`: seat-tracking, role-agnostic
  personality text.

`_resolve_seat()` currently concatenates them into one `prompt` string, and
`seat_agents.build_seat_agents()` passes that string to provider config as
`persona_prompt`. This was a good P2/P3 bridge, but P3-A needs explicit asset
ownership so role shuffle, human seats, memory, harness state, artifacts, and
future P4 rankings do not all depend on one blended prompt string.

P3-A-1 therefore defines four layers:

1. `SeatCharacterCard`: role-agnostic personality.
2. `RolePolicy`: true-role-specific strategy and playbook.
3. `RuntimeState`: one-run seat state plus faction/team state.
4. `ProviderProfile`: model/provider/execution budget.

P3-A-1 also defines an adjacent `ExecutionContract` so prompt template,
action schema, parser, context selector, and capability manifest versions are
not smuggled into ProviderProfile.

This slice is a schema and ownership slice. It does not change runtime
behavior, provider calls, prompt bytes, validators, generated fixtures, or
engine adjudication.

---

## 2. Reference Weighting

### 2.0 Primary reference: Codex Harness

Codex is treated as the primary reference for agent-runtime engineering.

Relevant concepts:

- A stable agent loop separates model reasoning from real-world execution.
- The runtime owns thread lifecycle, persistence, event streaming,
  configuration, approvals, tool execution, and recovery.
- Clients render stable events and submit user input; they do not duplicate
  agent-loop logic.
- Tools are capability-scoped and return structured results to the loop.
- The model proposes actions; the harness validates, executes, records, and
  returns outcomes.

Translation to Werewolf-agent:

| Codex harness concept | Werewolf-agent translation |
|---|---|
| Thread | One seat's run-scoped decision history. |
| Turn | One engine-created decision window. |
| Tool | Role-safe deterministic query or action capability. |
| Tool permission | Role / team / phase / visibility entitlement. |
| Approval request | Human-seat action window or explicit moderator intervention. |
| Thread persistence | RuntimeSeatState / RuntimeTeamState snapshots. |
| Event stream | Observer events, audit records, replay timeline. |
| Client | Qt/QML spectator UI and Flutter participant UI. |
| Execution result | RuleEngine adjudication result. |

Hard boundary:

The engine, not the model, determines decision timing, information entitlement,
legal action space, state transitions, and victory adjudication. The model may
only propose speech, strategy, and actions through declared capabilities.

### 2.1 Primary reference: learn-claude-code as an explanatory harness model

`shareAI-lab/learn-claude-code` is the main explanatory harness reference:

- Agent product = model plus harness.
- The loop stays simple; tools, knowledge, observation, action interfaces, and
  permissions make the model effective in a domain.
- Useful mechanisms layer around the loop: tool handlers, permission gates,
  hooks, task graphs, subagents, team protocols, context compaction, memory,
  runtime prompt assembly, error recovery, and external capability routing.

Translation to Werewolf-agent:

| Harness concept | Werewolf-agent translation |
|---|---|
| Observation | Role-safe `AgentContextPacket` built from visible events, board rules, and run-scoped state. |
| Action interface | Existing `ActionEnvelope` / strict JSON / participant action window contracts. |
| Tools | Future deterministic context tools: query claims, suspicion graph, own notes, team plan, playbook snippets. |
| Permissions | Role/phase/visibility gates. The harness decides what may be seen or used before a model call. |
| Hooks | Future deterministic hooks around speech/vote/night actions, such as extract commitments or check speech-vote consistency. |
| Context compaction | Run-scoped memory selection and summarization with source provenance and prompt budget accounting. |
| Team protocols | Werewolf-team private plan channel, not arbitrary agent chat. |

The key explanatory rule is negative as much as positive: do not replace the
model with a brittle hand-authored decision tree. The harness provides the
world, legal action space, memory access, and guardrails. The model still plays.

### 2.2 Primary reference: SillyTavern roleplay assets

SillyTavern is the main roleplay asset reference:

- Character definitions separate name, description, personality, scenario,
  first message, example dialogue, talkativeness, metadata, and notes.
- Character/persona/world-info/lorebook sources can be scoped to different
  contexts.
- World Info dynamically inserts relevant lore into prompt context using
  activation, ordering, recursion, and token budget controls.

Translation to Werewolf-agent:

| SillyTavern concept | Werewolf-agent translation |
|---|---|
| Character card permanent tokens | `SeatCharacterCard` fields that are always eligible for a seat, independent of true role. |
| Personality summary / examples | Speech style and role-agnostic behavior examples. |
| Talkativeness | Table-talk scheduling preference consumed later by P3-B, not action legality. |
| Character lore / persona lore / chat lore | Role policy, seat card, and run-scoped memory as separate context sources. |
| World Info activation | Future playbook retrieval with activation rules, source ids, priority, and budget. |
| Context budget | `AgentContextPacket` budget report: included, compacted, or dropped blocks. |

The borrowing scope is asset layering and context visualization. The project
may learn from SillyTavern's card/lore/preset concepts and its practical
attention to context budgets. It must not copy arbitrary prompt insertion
positions, user-card prompt overrides, or character text replacing system
instructions. Werewolf-agent is a hidden-information game. Every injected
roleplay asset, lore snippet, memory, or claim must have a declared visibility
scope and provenance, and model-visible text changes must follow the prompt
byte/version rules.

### 2.3 Secondary references

LangGraph, Microsoft Agent Framework, and CrewAI are secondary references only.
They are useful for vocabulary and cross-checking, especially stateful workflow,
persistence, human-in-the-loop, typed routing, middleware, telemetry, crews,
flows, tasks, memory, knowledge, guardrails, and observability.

They do not drive this design. P3-A-1 must not turn Werewolf-agent into a
generic orchestration framework or bypass the existing engine, observer
protocol, action runtime, visibility oracle, prompt goldens, or event sourcing.

### 2.4 Allowed borrowing matrix

| Source | May absorb | Explicitly not absorbed |
|---|---|---|
| Codex Harness | Mature runtime separation: thread/turn lifecycle, event streaming, capability-scoped tools, permission checks, execution recording, recovery. | Clients duplicating agent-loop logic; model directly controlling state transitions or hidden-information entitlement. |
| learn-claude-code | Agent loop, capability interfaces, permission gates, tool visibility, context compaction, hooks, memory, team mailbox ideas. | Rule trees replacing model decisions; models directly mutating game state. |
| SillyTavern | Card assets, personality layer, example dialogue, lore layering, context budget, presets, context visualization. | Arbitrary prompt positions, character cards overriding system prompts, keyword-driven free lore injection without entitlement checks. |
| LangGraph | Checkpoints, state snapshots, resume, human-in-the-loop, trace vocabulary. | Rewriting the Werewolf game executor as a StateGraph. |
| Microsoft Agent Framework | Typed routing, middleware, telemetry, session state vocabulary. | Workflow machinery taking over the phase scheduler or adjudicator. |
| CrewAI | Role/goal/task vocabulary, structured output, guardrail ideas. | Crew/manager/delegation as in-game faction scheduling. |

---

## 3. Design Goals

1. Make ownership explicit: personality, role strategy, run state, and provider
   execution config must be distinct objects.
2. Preserve current behavior until a later explicit runtime integration slice.
3. Keep legacy profiles mappable into the new four-layer model.
4. Keep artifacts honest enough for P4 attribution: model strength, card
   strength, role policy strength, and memory/harness strength must be separable.
5. Keep human seats first-class: a human-controlled seat may have UI-facing
   character assets, but no provider-backed player model call.
6. Make prompt injection boundaries explicit before memory/playbook retrieval
   enters model-visible context.

---

## 4. Non-goals

- No runtime prompt byte changes.
- No new provider behavior or provider request fields.
- No change to `ActionEnvelope`, participant protocol, validators, generated
  fixtures, or engine adjudication.
- No roleplay UI/editor implementation.
- No cross-run self-learning or automatic writeback into reusable cards.
- No generic LangGraph/CrewAI-style workflow runtime.
- No attempt to fully implement `AgentContextPacket`; P3-A-2 owns that.

---

## 5. The Four Layers

### 5.1 SeatCharacterCard

Purpose: reusable role-agnostic personality and communication style.

Ownership:

- User-editable asset.
- Follows the seat/card identity, not the true role.
- May be packaged into presets and shared.
- Must never be automatically mutated by a run.

Minimal schema:

```json
{
  "schema_version": "p3a.seat_character_card.v1",
  "card_id": "calm_logician",
  "version": "1.0.0",
  "display_name": "Calm Logician",
  "summary": "Careful, evidence-driven, reluctant to overclaim.",
  "personality": ["patient", "skeptical", "low-drama"],
  "speech_style": {
    "tone": "calm",
    "sentence_length": "medium",
    "uses_questions": true
  },
  "social_tendencies": {
    "talkativeness": 0.45,
    "assertiveness": 0.35,
    "conflict_tolerance": 0.4,
    "risk_tolerance": 0.3
  },
  "example_dialogue": [
    {
      "situation": "early_day_suspicion",
      "text": "我先不急着定狼,但 p4 的票型和发言顺序需要解释。"
    }
  ],
  "role_scope": "role_agnostic",
  "asset_certification": {
    "status": "built_in_vetted",
    "attribution_eligible": true,
    "review_notes": "No true-role strategy or team policy."
  },
  "metadata": {
    "author": "local",
    "tags": ["logic", "reserved"]
  }
}
```

Hard constraints:

- It cannot say "I am a werewolf", "always kill the seer", "as witch, save on
  night one", or any other true-role strategy.
- It can describe how the player talks, asks questions, reacts to conflict,
  handles uncertainty, and presents arguments.
- It is untrusted model-visible data when rendered. It never overrides system
  rules, action contracts, or visibility policy.
- `role_scope` is mandatory and must be `role_agnostic` for a
  SeatCharacterCard.
- `asset_certification.status` is governance, not a magical text scanner:
  `built_in_vetted` may enter formal P4 attribution; `user_unreviewed` may run
  but must be labeled as uncertified; `legacy_opaque` is compatibility-only and
  not eligible for strong card-vs-policy attribution.

Legacy bridge:

- Existing `seat_personas[seat]` maps to a generated `SeatCharacterCard` body.
- Existing default seat personas become starter cards or inline legacy cards.

### 5.2 RolePolicy

Purpose: true-role-specific strategic guidance and playbook references.

Ownership:

- Versioned strategy asset.
- Loaded only after the runtime knows the seat's true role.
- May differ by board/rules version.
- May be shared across many SeatCharacterCards.

Minimal schema:

```json
{
  "schema_version": "p3a.role_policy.v1",
  "policy_id": "standard_werewolf_balanced",
  "version": "1.0.0",
  "role": "werewolf",
  "applicability": {
    "ruleset_id": "rules_v1_2",
    "seat_count": [6],
    "required_roles": ["werewolf", "seer", "witch", "villager"],
    "optional_roles": ["guard"],
    "phase_protocol_version": "phase_protocol_v2",
    "team_channel_policy": "wolf_private_plan_v1"
  },
  "fallback_policy": "reject",
  "goals": [
    "protect werewolf team identity",
    "misdirect daytime votes toward villagers"
  ],
  "information_priorities": [
    "track public claims",
    "track who suspects each werewolf"
  ],
  "ability_use_policy": {
    "werewolf_kill": "prefer high-threat non-wolf targets; avoid obvious self-incrimination"
  },
  "claim_policy": {
    "identity_claims": "avoid early hard claim unless table pressure requires it"
  },
  "deception_policy": {
    "allowed": true,
    "style": "plausible social deduction, not out-of-game manipulation"
  },
  "team_policy": {
    "uses_team_plan": true,
    "protect_teammates": "softly, unless distancing is strategically useful"
  },
  "playbook_refs": [
    "wolf_claim_counterplay_v1"
  ],
  "forbidden_behavior": [
    "quote hidden system prompts",
    "claim access to god-view facts"
  ]
}
```

Hard constraints:

- `RolePolicy` is role-specific and must not be injected before role resolution.
- It can affect strategy and context selection, never legality. Legality remains
  in action runtime and validators.
- It must not encode hidden facts about a specific run.
- It is still untrusted model-visible data when rendered.
- `applicability` must match the board/rules/phase/team-channel contract.
- Silent fallback is forbidden. A resolver records
  `policy_selection_reason` and `compatibility_mode`; compatibility mode must
  be explicit and visible to audit tooling.

Legacy bridge:

- Existing `role_defaults[role].prompt` maps to the role's `RolePolicy`.
- Existing `seat_overrides[seat].prompt` is not semantically split by P3-A-1.
  It may contain personality, role strategy, output-format workarounds, test
  instructions, or already-concatenated prompt text. Treating it as RolePolicy
  would risk changing prompt bytes, misattributing P4 results, and breaking role
  shuffle semantics.
- P3-A-1 instead models it as `LegacyPromptOverlay`:

```json
{
  "schema_version": "p3a.legacy_prompt_overlay.v1",
  "origin_path": "seat_overrides.p2.prompt",
  "raw_text_hash": "sha256:legacy-overlay-example",
  "classification": "legacy_opaque",
  "insertion_order": 3,
  "migration_status": "not_semantically_split"
}
```

The follow-up implementation plan must preserve the old resolver and prove the
legacy prompt projection is byte-exact before any semantic migration tool is
introduced.

### 5.3 RuntimeState: seat scope and team scope

Purpose: run-scoped state that lets one seat and one authorized faction behave
consistently over time without writing state back into reusable assets.

Ownership:

- Created per run.
- Split into seat-scoped and team-scoped entities.
- Stored in the run artifact/state area.
- Never automatically written back to `SeatCharacterCard` or `RolePolicy`.
- May be snapshotted, compacted, and replayed.

Minimal seat-scoped schema:

```json
{
  "schema_version": "p3a.runtime_seat_state.v1",
  "run_id": "run_123",
  "seat_id": "p2",
  "initialized_from": {
    "seat_character_card_id": "calm_logician",
    "role_policy_id": "standard_werewolf_balanced",
    "provider_profile_id": "deepseek_flash_default"
  },
  "status": "active",
  "memory_records": [],
  "suspicion_graph": {},
  "commitments": [],
  "active_intent": null,
  "private_notes": [],
  "context_budget": {
    "last_prompt_blocks": [],
    "dropped_blocks": []
  },
  "last_updated_event_id": null
}
```

Minimal team-scoped schema:

```json
{
  "schema_version": "p3a.runtime_team_state.v1",
  "run_id": "run_123",
  "team_id": "werewolf",
  "visibility_scope": "faction_private",
  "authorized_seat_ids": ["p1", "p2"],
  "active_plan": {
    "summary": "p1 applies pressure while p2 keeps distance",
    "source_event_ids": [],
    "revision": 2
  },
  "shared_commitments": [],
  "team_message_history": [],
  "revision_history": [
    {
      "revision": 1,
      "created_at_event_id": "run_123_e004",
      "writer": "team_harness"
    }
  ]
}
```

P3-A-1 only defines the container and ownership. P3-A-2 owns the concrete memory
record taxonomy and `AgentContextPacket` content selection.

Hard constraints:

- Run state is not an asset library.
- Beliefs, claims, commitments, and team plans are not engine facts.
- Team plans belong to `RuntimeTeamState`, not to one player's
  `RuntimeSeatState`.
- `RuntimeTeamState` is authoritative for shared faction plans, authorized seat
  list, and plan revision history.
- Old records are superseded or retracted, not silently overwritten.
- Any future prompt injection from this state must carry source/provenance and
  pass visibility entitlement or a documented injection-channel exemption.

### 5.4 ProviderProfile

Purpose: requested model gateway and sampling/execution parameters.

Ownership:

- Configuration asset or profile-scoped configuration.
- Does not contain secrets.
- Does not define character personality or role strategy.
- Does not define prompt templates, action schemas, context selectors, parser
  versions, or tool/capability manifests.
- May be shared across many seats/cards.

Minimal schema:

```json
{
  "schema_version": "p3a.provider_profile.v1",
  "provider_profile_id": "deepseek_flash_default",
  "provider": "deepseek",
  "model": "deepseek-chat",
  "temperature": 0.8,
  "max_tokens": 256,
  "request_budget": {
    "per_seat_max_requests": 80,
    "per_action_player_calls": 1,
    "extra_scaffold_calls_allowed": false
  },
  "timeout_policy": {
    "seconds": 30,
    "fallback": "deterministic"
  },
  "credential_slot": "deepseek"
}
```

Hard constraints:

- Secrets stay in the existing credential store / environment flow, never in
  ProviderProfile.
- ProviderProfile controls execution knobs only.
- Scaffold/team calls, when introduced later, must be owned and accounted for
  separately from player turns.
- ProviderProfile does not promise deterministic replay. A provider/model name
  can be a drifting vendor alias. Reproducibility comes from the asset snapshots
  and ExecutionContract; model output may still differ because the vendor or
  sampling path changed.

Legacy bridge:

- Existing `provider`, `model`, `temperature`, and `max_tokens` fields map to a
  generated ProviderProfile or inline legacy provider profile.
- Existing `provider="human"` creates no player ProviderProfile for model calls.

### 5.5 ExecutionContract

Purpose: record the runtime/prompt/action contract used to compile context and
parse the model's proposal. This is not a personality asset and not a provider
profile.

Minimal schema:

```json
{
  "schema_version": "p3a.execution_contract.v1",
  "execution_contract_id": "baseline_prompt_v1_action_runtime_v1_2",
  "prompt_template_version": "prompt_v1",
  "prompt_renderer_version": "prompt_renderer_v1",
  "action_schema_version": "g1d-action-v1",
  "tool_capability_manifest_version": "none",
  "context_selector_version": "legacy_visible_events_v1",
  "response_parser_version": "provider_agent_json_v1",
  "fallback_behavior_version": "emergent_fallback_v1",
  "visibility_oracle_version": "i4b_v1"
}
```

Hard constraints:

- ExecutionContract is recorded with the run and hashable for audit.
- It may be referenced by public artifacts only as a non-secret execution
  summary. If a future contract name itself reveals hidden role policy choices,
  the reference must move to a private/postgame artifact.
- Changing any model-visible prompt template still follows prompt
  version/golden/ledger rules.

---

## 6. AgentPreset as a user-facing bundle

Users may want to import or share one "agent card". Runtime must still split it.

Minimal bundle shape:

```json
{
  "schema_version": "p3a.agent_preset.v1",
  "preset_id": "reserved_deduction_player",
  "display_name": "Reserved Deduction Player",
  "seat_character_card_ref": "calm_logician@1.0.0",
  "role_policy_pack_refs": {
    "werewolf": "standard_werewolf_balanced@1.0.0",
    "seer": "standard_seer_information_lead@1.0.0",
    "witch": "standard_witch_resource_timing@1.0.0",
    "villager": "standard_villager_claim_review@1.0.0"
  },
  "provider_profile_ref": "deepseek_flash_default"
}
```

Import/export rules:

- Presets may contain assets or references.
- Presets must not contain API keys, participant tokens, local paths, run logs,
  provider traces, RuntimeSeatState, or RuntimeTeamState.
- On launch, the preset compiles into four resolved layers.
- Artifacts record the layer ids, versions, and hashes, not secret values.

---

## 7. Resolution and Data Flow

Target resolution flow:

```text
profile / preset / legacy fields
  -> validate asset schemas
  -> resolve per-seat and per-team private asset snapshots
  -> write audience-scoped manifests/snapshots
  -> current runtime behavior unchanged in P3-A-1
  -> P3-A-2/P3-B later consume bundle to build AgentContextPacket
```

There is no single live `AgentAssetBundle` that every observer may read. A
single object containing `role`, `team`, `role_policy_ref`, and runtime memory
would leak hidden identities if it reached observer APIs, frontend state,
downloadable artifacts, live logs, or a human player's run directory. P3-A-1
therefore splits resolved asset data by audience.

All resolved asset objects use:

```json
{
  "visibility_scope": "public",
  "release_condition": "immediate"
}
```

Allowed values:

- `visibility_scope`: `public | seat_private | faction_private | engine_only |
  postgame_only`
- `release_condition`: `immediate | game_end | audit_authorized`

### 7.1 PublicRunManifest

Purpose: safe live/public run metadata. It may be exposed to ordinary observer
clients and non-seat public views during a live game.

It must not contain true role, team, role-policy id, private memory refs,
faction state refs, or hashes that can be joined against public files to infer
hidden roles.

```json
{
  "schema_version": "p3a.public_run_manifest.v1",
  "run_id": "run_123",
  "visibility_scope": "public",
  "release_condition": "immediate",
  "seats": [
    {
      "seat_id": "p2",
      "controller": "ai",
      "public_card": {
        "display_name": "Calm Logician",
        "card_hash_public": "sha256:public-card-summary"
      },
      "provider_profile_summary": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "temperature": 0.8
      }
    }
  ],
  "execution_contract_summary": {
    "prompt_template_version": "prompt_v1",
    "action_schema_version": "g1d-action-v1"
  }
}
```

### 7.2 SeatPrivateAssetSnapshot

Purpose: true per-seat resolved asset view for the engine, the seat owner, and
authorized postgame/audit tools.

```json
{
  "schema_version": "p3a.seat_private_asset_snapshot.v1",
  "run_id": "run_123",
  "seat_id": "p2",
  "visibility_scope": "seat_private",
  "release_condition": "audit_authorized",
  "controller": "ai",
  "true_role": "werewolf",
  "team": "werewolf",
  "seat_character_card_ref": {
    "id": "calm_logician",
    "version": "1.0.0",
    "hash": "sha256:card-example"
  },
  "role_policy_ref": {
    "id": "standard_werewolf_balanced",
    "version": "1.0.0",
    "hash": "sha256:policy-example",
    "policy_selection_reason": "exact_ruleset_match",
    "compatibility_mode": false
  },
  "provider_profile_ref": {
    "id": "deepseek_flash_default",
    "hash": "sha256:provider-example"
  },
  "execution_contract_ref": {
    "id": "baseline_prompt_v1_action_runtime_v1_2",
    "hash": "sha256:execution-contract-example"
  },
  "runtime_seat_state_ref": {
    "run_id": "run_123",
    "seat_id": "p2"
  },
  "legacy_bridge": {
    "used_role_defaults_prompt": true,
    "used_seat_persona": true,
    "used_legacy_prompt_overlay": false,
    "legacy_projection_byte_exact": true
  }
}
```

### 7.3 FactionPrivateAssetSnapshot

Purpose: shared faction state and team policy for seats that are entitled to
faction-private information.

```json
{
  "schema_version": "p3a.faction_private_asset_snapshot.v1",
  "run_id": "run_123",
  "team_id": "werewolf",
  "visibility_scope": "faction_private",
  "release_condition": "audit_authorized",
  "authorized_seat_ids": ["p1", "p2"],
  "team_policy_ref": {
    "id": "wolf_private_plan_v1",
    "hash": "sha256:team-policy-example"
  },
  "runtime_team_state_ref": {
    "run_id": "run_123",
    "team_id": "werewolf"
  }
}
```

### 7.4 PostgameAuditAssetSnapshot

Purpose: complete reveal and reproducibility material after the game ends or an
authorized audit explicitly requests it.

This is where hidden roles, full private snapshots, sealed asset bytes, and
cross-seat comparisons belong. It is not a live public artifact.

```json
{
  "schema_version": "p3a.postgame_audit_asset_snapshot.v1",
  "run_id": "run_123",
  "visibility_scope": "postgame_only",
  "release_condition": "game_end",
  "asset_snapshot_manifest": {
    "snapshot_store_version": "v1",
    "seat_card_hash": "sha256:card-example",
    "role_policy_hash": "sha256:policy-example",
    "provider_profile_hash": "sha256:provider-example",
    "execution_contract_hash": "sha256:execution-contract-example",
    "prompt_template_hash": "sha256:prompt-template-example",
    "action_schema_hash": "sha256:action-schema-example",
    "context_selector_hash": "sha256:context-selector-example"
  },
  "sealed_blobs": [
    {
      "content_hash": "sha256:card-example",
      "visibility_scope": "postgame_only",
      "canonical_json_bytes_ref": "content-addressed:sha256:card-example"
    }
  ]
}
```

The sealed snapshot exists because ids, versions, and hashes alone are
insufficient for P4 audit. If `Calm Logician@1.0.0` is later edited or deleted,
postgame analysis still needs the exact canonical JSON bytes used in the run.
The sealed store must not contain secrets, participant tokens, local paths, raw
provider traces, or unauthorized live private data.

For human seats:

- `controller = "human"`.
- public manifest may show public card metadata.
- seat-private snapshot may record true role and role-safe help/policy refs for
  the seat owner and backend.
- provider profile is absent for player model calls.
- `RuntimeSeatState` may be absent or replaced by participant session state.
- UI may display role-safe policy/help text later, but no model call consumes it.

---

## 8. Prompt and Injection Boundary

P3-A-1 does not render these schemas into prompts.

Later slices must follow these rules:

1. Only `PromptRenderer` may create model-visible prompt bytes.
2. No asset, memory module, hook, tool, observer route, provider adapter, or
   participant client may append text directly.
3. Any model-visible byte change requires the prompt version/golden/ledger
   process, or a coexisting prompt version selected at runtime.
4. New prompt suffixes or context blocks must be registered in
   `docs/specs/text-injection-channels.md` if they append outside the normal
   rendered observation path.
5. Role-private data must either source a visible event id or ship with a
   negative-scan test proving other seats do not receive it.
6. SeatCharacterCard, RolePolicy, playbook text, human speech, AI speech,
   memory summaries, and retrieved lore are untrusted game data. They never
   override system/developer instructions, action contracts, visibility policy,
   or tool permissions.
7. `BeliefRecord` and `ClaimRecord` must never be rendered as engine facts.

Fixed block order:

```text
1. Immutable game/system contract
   - game rules
   - visibility policy
   - action JSON schema
   - tool permission contract
   - anti-leak / anti-prompt-injection rules

2. Trusted runtime control block
   - current phase
   - allowed action types
   - hard response constraints

3. SeatCharacterCard guidance block
   - tone
   - speaking habits
   - uncertainty style
   - social tendencies

4. RolePolicy guidance block
   - included only when role entitlement passes
   - strategy guidance, never legality

5. Role-safe observation block
   - visible events
   - public claims
   - private role information
   - allowed team information

6. Retrieved memory / playbook block
   - quoted as evidence or advisory data
   - source ids and provenance
   - never rendered as engine fact

7. Final action request
   - strict JSON schema
   - action legality checked outside the model
```

Every renderable block carries:

```json
{
  "trust_class": "built_in_vetted",
  "render_mode": "guidance",
  "visibility_scope": "seat_private",
  "source_provenance": {
    "source_event_ids": [],
    "asset_hashes": ["sha256:card-example"],
    "generated_by": "prompt_renderer_v1"
  }
}
```

Allowed `trust_class` values:

- `built_in_vetted`
- `local_user`
- `legacy_opaque`
- `run_derived`

Allowed `render_mode` values:

- `control`: only trusted runtime/game contracts.
- `guidance`: cards and policies that intentionally influence style or strategy.
- `quoted_evidence`: player speech, AI speech, claim records, memory summaries,
  retrieved lore, and other untrusted game data.
- `ui_only`: visible to client UI but never rendered to the model.

RolePolicy is rendered as `guidance` only after entitlement passes. Speech,
chat logs, memory summaries, and claim records are rendered as
`quoted_evidence`, never as system rules or engine facts.

---

## 9. Validation Strategy for the Future Implementation Plan

Pure schema tests:

- Accept minimal valid `SeatCharacterCard`, `RolePolicy`, `RuntimeSeatState`,
  `RuntimeTeamState`, `ProviderProfile`, `ExecutionContract`, and
  `AgentPreset`.
- Reject unknown schema versions, unknown roles, invalid seat ids, invalid
  numeric ranges, and secret-like keys/values.
- Enforce provider profiles have no secrets and human seats do not create player
  model calls.
- Enforce `SeatCharacterCard.role_scope == "role_agnostic"`.
- Enforce RolePolicy `applicability` exact match or explicit compatibility
  mode.
- Enforce ProviderProfile does not contain prompt/action/tool/parser contract
  versions.

Legacy bridge tests:

- Existing default profile maps to four layers without changing current resolved
  seat prompt output.
- `role_defaults[role].prompt` maps to RolePolicy.
- `seat_personas[seat]` maps to SeatCharacterCard.
- `provider`, `model`, `temperature`, `max_tokens` map to ProviderProfile.
- `seat_overrides[seat].prompt` maps to `LegacyPromptOverlay`, not RolePolicy,
  and legacy projection remains byte-exact.

Artifact tests:

- `PublicRunManifest` contains no true role, team, RolePolicy id, private memory
  refs, faction refs, or joinable hash references that reveal hidden identity.
- `SeatPrivateAssetSnapshot` contains role/team/policy refs only under
  `visibility_scope=seat_private`.
- `FactionPrivateAssetSnapshot` is readable only by authorized faction seats and
  trusted backend/audit paths.
- `PostgameAuditAssetSnapshot` is generated only after game end or explicit
  audit authorization.
- No raw secrets, tokens, local paths, or full prompt text are written.
- Existing `resolved-profile.json` compatibility remains either unchanged or
  receives additive fields only after an explicit plan.
- Asset snapshot manifest records hashes for seat cards, role policies,
  provider profiles, execution contracts, prompt templates, action schemas, and
  context selectors.

Prompt safety tests:

- P3-A-1 implementation must not modify prompt goldens.
- If a later plan renders any new asset text into model prompts, that plan must
  invoke the prompt byte/version workflow.
- Only `PromptRenderer` emits model-visible text.
- Rendered block order is fixed.
- Each block carries `trust_class`, `render_mode`, `visibility_scope`, and
  source provenance.

Hidden-information negative scans:

- A live public observer SSE/REST payload during the game must not contain
  unrevealed role names such as `werewolf`, `seer`, or `witch` for hidden seats.
- A human participant for `p2` cannot read another seat's
  `SeatPrivateAssetSnapshot` or `role_policy_ref`.
- Live downloadable/public artifacts cannot reveal hidden identity through file
  names, public hashes, policy ids, role/team fields, or manifest joins.
- Postgame reveal or audit authorization is required before complete asset
  snapshots are available.
- `RuntimeTeamState` rejects unauthorized seat access and records authorized
  seat ids in every snapshot.

---

## 10. Implementation Options Considered

### Option A: schema-first bridge (recommended)

Add pure asset schemas and audience-scoped artifact snapshots while keeping
current runtime prompt assembly unchanged.

Pros:

- Makes ownership explicit with low behavioral risk.
- Preserves prompt bytes.
- Gives P3-A-2/P3-B a stable input contract.
- Lets artifacts and P4 attribution start separating card/policy/provider.

Cons:

- Does not immediately make agents more interesting.
- Requires one more integration slice before runtime consumes the assets.

### Option B: direct prompt integration

Immediately split the current prompt into card/policy/context blocks and render
them into provider requests.

Pros:

- Faster visible behavior change.
- Tests roleplay assets sooner.

Cons:

- Touches model-visible bytes, prompt versioning, golden prompts, injection
  registry, and likely safety-net tests all at once.
- Easy to mix ownership/schema work with behavior tuning.

### Option C: UI/editor first

Build role cards and asset editor UI before backend schema.

Pros:

- Product surface becomes tangible quickly.

Cons:

- Risks building an attractive editor for data the runtime cannot safely own or
  audit.
- Does not solve provenance, visibility, or P4 attribution.

Decision: use Option A for P3-A-1.

---

## 11. Acceptance Criteria

For this design:

- Four layers are defined with ownership, writeback rules, and legacy mapping.
- Primary reference translations from Codex Harness, learn-claude-code, and
  SillyTavern are explicit.
- Secondary agent frameworks are acknowledged but do not drive the architecture.
- Runtime/provider/prompt/validator/generated-fixture boundaries remain closed.
- Live public artifacts and public observer payloads must not contain unrevealed
  role, team, RolePolicy id, faction state ref, private memory ref, or
  joinable hash/reference that can infer hidden identity.
- Role/team/RolePolicy data belongs in seat-private, faction-private,
  engine-only, or postgame/audit artifacts according to explicit
  `visibility_scope` and `release_condition`.
- Runtime team plans belong to `RuntimeTeamState`, not to an individual seat's
  state.
- Only `PromptRenderer` may create model-visible prompt bytes; all renderable
  blocks must carry trust/render/visibility/provenance metadata.

For the follow-up implementation plan:

- No prompt version bump is required for the schema-only bridge.
- No runtime behavior changes are allowed unless explicitly added to a later
  approved slice.
- The plan should stay in pure schema/validation/artifact code first.
- It must include live secret-leak negative scans, artifact audience tests,
  legacy byte-exact projection tests, and team-state authorization tests.

---

## 12. References

- P3 pivot: `docs/superpowers/specs/2026-07-02-agent-roleplay-human-game-pivot-design.md`
- Project authority: `docs/PROJECT_MAP.md`
- Injection registry: `docs/specs/text-injection-channels.md`
- learn-claude-code: https://github.com/shareAI-lab/learn-claude-code
- SillyTavern: https://github.com/SillyTavern/SillyTavern
- SillyTavern Character Design: https://docs.sillytavern.app/usage/core-concepts/characterdesign/
- SillyTavern World Info: https://docs.sillytavern.app/usage/core-concepts/worldinfo/
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- Microsoft Agent Framework overview: https://learn.microsoft.com/en-us/agent-framework/overview/
- CrewAI docs: https://docs.crewai.com/

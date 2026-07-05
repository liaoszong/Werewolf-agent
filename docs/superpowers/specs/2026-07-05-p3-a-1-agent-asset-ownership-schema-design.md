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
3. `RuntimeAgentState`: one-run state, memory, plans, commitments.
4. `ProviderProfile`: model/provider/execution budget.

This slice is a schema and ownership slice. It does not change runtime
behavior, provider calls, prompt bytes, validators, generated fixtures, or
engine adjudication.

---

## 2. Reference Weighting

### 2.1 Primary reference: learn-claude-code harness engineering

`shareAI-lab/learn-claude-code` is the main engineering harness reference:

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

The key design rule is negative as much as positive: do not replace the model
with a brittle hand-authored decision tree. The harness provides the world,
legal action space, memory access, and guardrails. The model still plays.

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

The critical difference is that Werewolf-agent is a hidden-information game.
SillyTavern can be permissive about prompt injection. This project cannot.
Every injected roleplay asset, lore snippet, memory, or claim must have a
declared visibility scope and provenance, and model-visible text changes must
follow the prompt byte/version rules.

### 2.3 Secondary references

LangGraph, Microsoft Agent Framework, and CrewAI are secondary references only.
They are useful for vocabulary and cross-checking, especially stateful workflow,
persistence, human-in-the-loop, typed routing, middleware, telemetry, crews,
flows, tasks, memory, knowledge, guardrails, and observability.

They do not drive this design. P3-A-1 must not turn Werewolf-agent into a
generic orchestration framework or bypass the existing engine, observer
protocol, action runtime, visibility oracle, prompt goldens, or event sourcing.

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
  "forbidden_content": [
    "true role claims",
    "role ability policy",
    "team strategy"
  ],
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
  "rules_versions": ["rules_v1_1", "rules_v1_2"],
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

Legacy bridge:

- Existing `role_defaults[role].prompt` maps to the role's `RolePolicy`.
- Existing `seat_overrides[seat].prompt` is treated as a legacy policy override
  for that run/profile, not as a durable SeatCharacterCard.

### 5.3 RuntimeAgentState

Purpose: run-scoped state that lets one seat behave consistently over time.

Ownership:

- Created per run and per AI-controlled seat.
- Stored in the run artifact/state area.
- Never automatically written back to `SeatCharacterCard` or `RolePolicy`.
- May be snapshotted, compacted, and replayed.

Minimal schema:

```json
{
  "schema_version": "p3a.runtime_agent_state.v1",
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
  "team_plan_refs": [],
  "context_budget": {
    "last_prompt_blocks": [],
    "dropped_blocks": []
  },
  "last_updated_event_id": null
}
```

P3-A-1 only defines the container and ownership. P3-A-2 owns the concrete memory
record taxonomy and `AgentContextPacket` content selection.

Hard constraints:

- Run state is not an asset library.
- Beliefs, claims, commitments, and team plans are not engine facts.
- Old records are superseded or retracted, not silently overwritten.
- Any future prompt injection from this state must carry source/provenance and
  pass visibility entitlement or a documented injection-channel exemption.

### 5.4 ProviderProfile

Purpose: model gateway and execution policy.

Ownership:

- Configuration asset or profile-scoped configuration.
- Does not contain secrets.
- Does not define character personality or role strategy.
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

Legacy bridge:

- Existing `provider`, `model`, `temperature`, and `max_tokens` fields map to a
  generated ProviderProfile or inline legacy provider profile.
- Existing `provider="human"` creates no player ProviderProfile for model calls.

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
  provider traces, or RuntimeAgentState.
- On launch, the preset compiles into four resolved layers.
- Artifacts record the layer ids, versions, and hashes, not secret values.

---

## 7. Resolution and Data Flow

Target resolution flow:

```text
profile / preset / legacy fields
  -> validate asset schemas
  -> resolve per-seat four-layer AgentAssetBundle
  -> write resolved agent asset artifact with hashes
  -> current runtime behavior unchanged in P3-A-1
  -> P3-A-2/P3-B later consume bundle to build AgentContextPacket
```

`AgentAssetBundle` is a resolved internal read model:

```json
{
  "schema_version": "p3a.agent_asset_bundle.v1",
  "run_id": "run_123",
  "seat_id": "p2",
  "controller": "ai",
  "role": "werewolf",
  "team": "werewolf",
  "seat_character_card_ref": {
    "id": "calm_logician",
    "version": "1.0.0",
    "hash": "sha256:card-example"
  },
  "role_policy_ref": {
    "id": "standard_werewolf_balanced",
    "version": "1.0.0",
    "hash": "sha256:policy-example"
  },
  "provider_profile_ref": {
    "id": "deepseek_flash_default",
    "hash": "sha256:provider-example"
  },
  "runtime_state_ref": {
    "run_id": "run_123",
    "seat_id": "p2"
  },
  "legacy_bridge": {
    "used_role_defaults_prompt": true,
    "used_seat_persona": true,
    "used_seat_override_prompt": false
  }
}
```

For human seats:

- `controller = "human"`.
- `provider_profile_ref = null`.
- `RuntimeAgentState` may be absent or replaced by participant session state.
- UI may display role-safe policy/help text later, but no model call consumes it.

---

## 8. Prompt and Injection Boundary

P3-A-1 does not render these schemas into prompts.

Later slices must follow these rules:

1. Any model-visible byte change requires the prompt version/golden/ledger
   process, or a coexisting prompt version selected at runtime.
2. New prompt suffixes or context blocks must be registered in
   `docs/specs/text-injection-channels.md` if they append outside the normal
   rendered observation path.
3. Role-private data must either source a visible event id or ship with a
   negative-scan test proving other seats do not receive it.
4. SeatCharacterCard, RolePolicy, playbook text, human speech, AI speech,
   memory summaries, and retrieved lore are untrusted game data. They never
   override system/developer instructions, action contracts, visibility policy,
   or tool permissions.
5. `BeliefRecord` and `ClaimRecord` must never be rendered as engine facts.

---

## 9. Validation Strategy for the Future Implementation Plan

Pure schema tests:

- Accept minimal valid `SeatCharacterCard`, `RolePolicy`, `RuntimeAgentState`,
  `ProviderProfile`, and `AgentPreset`.
- Reject unknown schema versions, unknown roles, invalid seat ids, invalid
  numeric ranges, and secret-like keys/values.
- Enforce provider profiles have no secrets and human seats do not create player
  model calls.

Legacy bridge tests:

- Existing default profile maps to four layers without changing current resolved
  seat prompt output.
- `role_defaults[role].prompt` maps to RolePolicy.
- `seat_personas[seat]` maps to SeatCharacterCard.
- `provider`, `model`, `temperature`, `max_tokens` map to ProviderProfile.

Artifact tests:

- Resolved artifact contains ids, versions, hashes, controller, role/team, and
  legacy bridge markers.
- No raw secrets, tokens, local paths, or full prompt text are written.
- Existing `resolved-profile.json` compatibility remains either unchanged or
  receives additive fields only after an explicit plan.

Prompt safety tests:

- P3-A-1 implementation must not modify prompt goldens.
- If a later plan renders any new asset text into model prompts, that plan must
  invoke the prompt byte/version workflow.

---

## 10. Implementation Options Considered

### Option A: schema-first bridge (recommended)

Add pure asset schemas and a resolved asset artifact while keeping current
runtime prompt assembly unchanged.

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
- Primary reference translations from learn-claude-code and SillyTavern are
  explicit.
- Secondary agent frameworks are acknowledged but do not drive the architecture.
- Runtime/provider/prompt/validator/generated-fixture boundaries remain closed.

For the follow-up implementation plan:

- No prompt version bump is required for the schema-only bridge.
- No runtime behavior changes are allowed unless explicitly added to a later
  approved slice.
- The plan should stay in pure schema/validation/artifact code first.

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

# Prompt Versioning & Evaluation Comparison Tuple — Design

- **Date:** 2026-06-10
- **Status:** DESIGN (approved in discussion; awaiting spec review)
- **Systems:** SYS-B1 (prompt assembly / context engineering), SYS-C1 (evaluation), SYS-C3 (parity/audit culture)
- **Relation:** extends the parity regime of `2026-06-09-agent-action-runtime-architecture-design.md` §7.3 (semantic-hard / byte-diagnostic / blessed ledger) with a new controlled-change category: baseline prompt revisions. Orthogonal to the in-flight ②a resolver-deletion work (this spec changes zero prompt bytes).

## 1. Problem

The baseline prompt is a behavior-critical input with known defects (e.g. the day-vote target list invites self-votes), but every model-visible byte is implicitly frozen by the parity culture: there is no legal exit for a prompt fix, no version marker anywhere on the prompt assembly chain, and no machine-readable way to tell which leaderboard results were produced under which prompt. Without a versioning mechanism, all prompt-layer improvements are either blocked or would silently pollute score comparability. Additionally, P3's planned leaderboard needs a comparison boundary wider than the prompt alone: results are only comparable within the same `rules_version + prompt_version + scoring_version`.

## 2. Policy (decided)

**Versioned baseline (option b), with an archived anchor — not dual-track.**

> v1 baseline prompt is immutable as an archived reference anchor, but the active baseline policy is *versioned baseline*, not dual-track operation.

- The baseline prompt MAY evolve. Every evolution MUST produce a new `prompt_version` and go through the controlled re-bless flow (§6).
- Leaderboard ranking compares only within one bucket: identical `rules_version + prompt_version + scoring_version`. Cross-bucket results are historical reference only, never directly ranked.
- Permanent freeze (option a) is rejected: it would permanently enshrine known baseline defects and force scaffolds to absorb prompt-layer fixes, polluting future ablation experiments. Formal dual-track (option c) is rejected as too heavy for the current P2/P3 stage: two blessing chains and two explanation regimes would slow iteration for marginal benefit.

## 3. Version bump rule (decided)

**Version object = the final rendered bytes sent to the model on the baseline path.** The covered assembly chain:

```
build_action_system_prompt   (llm_providers.py)
build_speech_system_prompt   (llm_providers.py)
compose_system               (llm_providers.py)
render_observation_text      (emergent_engine.py)
```

> Any model-visible byte change in the baseline prompt assembly chain requires a new `prompt_version` and a re-blessed golden prompt ledger entry. Source-only refactors are allowed only when rendered canonical prompt bytes remain unchanged.

Bump triggers (non-exhaustive in spirit, exhaustive in mechanism — the byte lock catches everything):

1. System-prompt wording changes.
2. Action/speech prompt constraints, role descriptions, output-format instructions.
3. `compose_system` section order, separators, headings, concatenation.
4. `render_observation_text` changes to the model-visible expression of the same observation.
5. Allowed-targets / legal-action hints / vote-target list presentation.
6. Example JSON, field descriptions, fallback/error-recovery instructions.
7. Any model-visible whitespace, newline, punctuation, or heading change.

**No cosmetic exemption.** Whitespace and ordering can change LLM output, especially under structured-JSON constraints; introducing an "I think it's harmless" human judgment on this high-sensitivity input is exactly the class of error the audit proved happens.

**The only non-bump change:** a code refactor after which the same canonical fixtures render byte-identical prompts (function splits, renames, non-model-visible log fields, manifest metadata).

## 4. Version constants & evaluation tuple

### 4.1 Constants

| Constant | Value (initial) | Location |
|---|---|---|
| `PROMPT_VERSION` | `"prompt_v1"` | `src/werewolf_eval/prompt_version.py` (new, single source) |
| `SCORING_VERSION` | `"scoring_v1"` | `src/werewolf_eval/evaluation_versions.py` (new); `scoring.py` imports it from there |
| `rules_version` | `"rules_v1_1"` (current) | existing `BoardRuleset.rules_version` — read, not redeclared |

`SCORING_VERSION` lives in `evaluation_versions.py` rather than `scoring.py` so that callers of the tuple (run status, manifest, observer-side writers) never transitively import the scoring main module — the same circular-import concern that keeps `evaluation_bucket()` out of `scoring.py`. `scoring.py` imports the constant from `evaluation_versions.py` (reverse direction, no cycle).

`SCORING_VERSION` exists now even with a single value: it is the breakpoint for future scoring-formula changes. Without it, future score_records would mix old-formula and new-formula scores with no machine-readable discriminator.

### 4.2 `evaluation_bucket()`

Location: `src/werewolf_eval/evaluation_versions.py`. Explicit arguments — no global reads:

```python
evaluation_bucket(
    rules_version=ruleset.rules_version,
    prompt_version=PROMPT_VERSION,
    scoring_version=SCORING_VERSION,
)
# -> {"rules_version": "rules_v1_1",
#     "prompt_version": "prompt_v1",
#     "scoring_version": "scoring_v1",
#     "comparison_key": "rules_v1_1__prompt_v1__scoring_v1"}
```

All stamping sites MUST call this function; hand-assembled tuples are forbidden (single source for the key format).

### 4.3 Stamping into non-frozen artifacts

The tuple is written into artifacts that *describe the run and explain scoring* — never into byte-frozen canonical game logs.

| Artifact | Stamped | Notes |
|---|---|---|
| `prompt-manifest.json` | YES — **extend existing** | The prompt manifest already exists as a runtime deliverable (G1h realtime-skeleton; G3-3 runtime-manifest honesty). This spec extends it with `evaluation_bucket` and `prompt_used_by_runtime`. If a runner currently does not emit `prompt-manifest.json`, this spec makes it mandatory for new non-frozen runtime artifacts. |
| run status / run detail | YES | |
| `score_records` | YES | See §4.5 fixture-impact note. |
| game-log / decision-log / consensus-log | **NO** | Protects the byte-frozen scripted gold-game replay gate (g1b/g1c/g1f) and avoids fake-parity churn. |

### 4.4 `prompt_used_by_runtime`

Definition (mechanism, not provider-name matching):

> `prompt_used_by_runtime = true` iff the baseline rendered system prompt was actually passed across the provider/model-call boundary as runtime input.

Implementation: providers/runners expose a declared field rather than being name-sniffed:

```
provider_runtime_kind: fake_deterministic | scripted | live_model
uses_baseline_prompt:  true | false
```

Current mapping: `fake_deterministic`/`scripted` → `false`, `live_model` → `true`. This spec requires only a **run-level** boolean; when mixed-seat / replay / recorded / hybrid providers appear, the field MAY be extended to a per-seat map without breaking the run-level contract.

Rationale for recording the version even when unused: an empty field forces special-case branches in every future aggregator; an explicit "current declared version + whether this run actually consumed it" is self-explaining.

### 4.5 Legacy artifacts & fixture impact

- **Legacy:** artifacts with no version fields read as `"unknown"` for all three components. The unknown bucket is browsable but **not rankable**.
- **Fixture-impact note (implementation must verify):** adding tuple fields to `score_records` may touch regenerable golden score fixtures (e.g. `docs/generated-games/g1-scripted-score-log.json`). Implementation MUST check which score fixtures are byte-compared in tests; fixtures *outside* the frozen replay gate are regenerated in the same commit with a ledger `schema_addition` entry. Moving the stamp out of `score_records` to dodge fixture regeneration is **forbidden**.

## 5. Golden prompt byte lock + CI

### 5.1 Golden files — full text, not hashes

```
tests/golden_prompts/
  prompt_v1/
    action_werewolf_night.txt
    action_seer_night.txt
    action_witch_night.txt          # includes a night_victim sample
    action_villager_day_vote.txt
    action_hunter_day_vote.txt
    action_hunter_shot.txt
    speech_villager_day1.txt
    speech_werewolf_day1.txt
    ...
```

- Files store the **full rendered prompt text**. Full-text diffs are the review evidence at bump time (a hash only says "changed", a diff says *what* changed); byte-lock strength is identical.
- **Encoding discipline:** files are UTF-8 + LF. Add `.gitattributes`: `tests/golden_prompts/** text eol=lf`.
- **Comparison discipline:** tests read files as **bytes** and compare byte-exact — no strip, no newline normalization.
- The canonical fixture set: fixed-seed observation fixtures covering every role × phase representative sample (all-role action prompts including hunter, speech prompts, hunter-shot prompt, witch sample with a live `night_victim`). Pure unit-test layer — render functions called directly; no game run, no localhost (env constraint).
- The ledger (§6) records sha256 fingerprints of these full-text files: **full text for review, hash for audit reference and machine summary.** Not redundant — different consumers.

### 5.2 CI rules (all FAIL, no warnings)

1. Rendered bytes changed but `PROMPT_VERSION` unchanged → **FAIL** (silent drift).
2. `PROMPT_VERSION` bumped but no new `tests/golden_prompts/<new_version>/` directory or no new ledger entry → **FAIL** (unblessed bump).
3. `PROMPT_VERSION` bumped but rendered bytes unchanged → **FAIL** (meaningless bump).

These run in the existing test workflow (`.github/workflows/tests.yml`) as ordinary unit tests.

## 6. Prompt version ledger & re-bless flow

### 6.1 Ledger artifact

`docs/generated-games/prompt-version-ledger.json` — same directory and same culture as `runtime-v2-parity-diff-ledger.json` ("no silent blessing").

**Governance note:** `docs/generated-games/` is policy-protected — AGENTS rules forbid casual reads/writes there, and changes to runtime/scoring/providers/validators/generated fixtures/tests must be bound to an active plan. Implementers touch this file **only** under the plan derived from this spec.

### 6.2 Entry schema

```jsonc
{
  "prompt_version": "prompt_v2",
  "base_version": "prompt_v1",
  "reason": "fix self-vote invitation in daytime vote target list",
  "expected_change": "reduce or eliminate self-vote suggestions in legal target hints",
  "touched_chain": ["build_action_system_prompt", "render_observation_text"],
  "golden_prompt_hashes": { "before": { "<sample>": "sha256..." },
                            "after":  { "<sample>": "sha256..." } },
  "behavior_evidence": {
    "status": "not_run | attached | not_applicable",
    "reason_if_not_run": "...",
    // when attached:
    "model": "...", "games": "5-10 each",
    "metrics": ["self_vote_attempt_count", "invalid_vote_count",
                "fallback_vote_count", "live_success_rate"],
    "result_summary": "...", "artifact_path": "..."
  },
  "blessed_by": "...",
  "blessed_at": "..."
}
```

The initial entry records `prompt_v1` itself: `base_version: null`, `reason: "initial baseline lock"`, `behavior_evidence.status: "not_applicable"`.

### 6.3 Re-bless policy (decided)

> Prompt re-blessing is mandatory for **auditability**, not for behavioral proof. Every `prompt_version` bump MUST include updated golden prompt files (and their hashes in the ledger), a ledger entry with reason / expected_change / touched_chain / blessed_by, and normal code review. For intent-bearing prompt changes — especially bug fixes or behavioral steering — a small live-model A/B SHOULD be attached to the ledger when practical, but it is **not a merge gate**. If omitted, the ledger MUST say why.

A hard evidence gate is rejected: 5–10 live games lack the statistical power to "prove" improvement, would manufacture false certainty, and would let API cost block legitimate fixes (driving people to dodge `prompt_version` entirely, destroying the audit culture). A pure-compliance flow is rejected: it leaves no version-evolution narrative for P3 review/leaderboard explanation.

## 7. Touchstone walkthrough (paper-only — NOT implemented by this spec)

The P5 self-vote fix as `prompt_v2`, validating the mechanism end-to-end:

1. Edit the vote-target presentation in `render_observation_text` / action prompt (exclude self).
2. CI rule 1 fires: bytes changed, version unchanged → red.
3. Bump `PROMPT_VERSION = "prompt_v2"`, regenerate `tests/golden_prompts/prompt_v2/`.
4. Write the ledger entry (schema above; behavior_evidence: DeepSeek 5–10 game A/B on `self_vote_attempt_count` / `fallback_vote_count`).
5. Normal code review; merge. Leaderboard buckets split automatically via `comparison_key`.

No mechanism gap appears at any step. **The self-vote fix itself is out of scope** — it touches the shown-vs-legal target-list design tension (audit NON-BLOCKING #3) and needs its own evaluation when attempted.

## 8. Scope

**IN SCOPE**

- `PROMPT_VERSION` / `SCORING_VERSION` constants + bump rules (§3, §4.1).
- `evaluation_bucket()` + `comparison_key` (§4.2).
- Tuple stamping into non-frozen runtime/evaluation artifacts; `prompt_used_by_runtime` run-level field (§4.3–4.4).
- Golden prompt full-text byte lock + `.gitattributes` + CI rules (§5).
- `prompt-version-ledger.json` with the `prompt_v1` initial entry (§6).
- Legacy `"unknown"` compatibility policy (§4.5).
- CI/tests guaranteeing new artifacts carry the tuple.

**OUT OF SCOPE**

- No scoring-formula change. No game-rule change. No leaderboard UI.
- No retrofit of byte-frozen gold logs; no rewrite of historical artifacts.
- **No prompt revision of any kind.** Landing this spec changes **zero** prompt bytes — `prompt_v1` golden files lock the *current* rendering as-is, and that is an explicit acceptance criterion: the mechanism PR must be reviewable as pure mechanism, never mixed with behavior change.

## 9. Testing

1. Golden prompt byte-compare test over the canonical fixture set (pure unit layer).
2. The three CI rules of §5.2 (drift / unblessed bump / meaningless bump).
3. `evaluation_bucket()` unit tests (shape, key format, explicit-args contract).
4. Stamping tests: prompt-manifest / run status / score_records carry the tuple; fake-deterministic run yields `prompt_used_by_runtime: false`; live-provider config yields `true` (contract-level, no network).
5. Legacy read test: artifact without version fields → `"unknown"` bucket, excluded from ranking aggregation.
6. Regression: full suite stays green; scripted gold-game replay bytes untouched.

## 10. Relationship to in-flight work

- **②a resolver deletion:** orthogonal. That work is byte-parity-bound; this spec does not alter prompt bytes. No ordering constraint either way.
- **B1 memory / B4 scaffolding (future):** baseline-side improvements ride this mechanism (legal landing path via version bump); enhancement-axis changes remain governed by the scaffold boundary (upstream of ActionEnvelope, baseline as judge) and do not bump `prompt_version`.
- **P3 leaderboard:** consumes `comparison_key` for bucketing; this spec deliberately ships the stamps early so P3 has day-one bucketed data.

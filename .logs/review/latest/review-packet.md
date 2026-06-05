# Review Packet — G3-1 Live DeepSeek Execution (opt-in, fake-by-default)

## Metadata
- **Branch:** `feat/g3-1-live-deepseek-execution`  •  **Base:** `main`
- **Date:** 2026-06-05  •  **Author:** liaoszong
- **Spec:** `docs/superpowers/specs/2026-06-05-g3-1-live-deepseek-execution-design.md`
- **Plan:** `docs/harness/plans/2026-06-05--g3-1-live-deepseek-execution-plan.md`
- **Scope:** thin WIRING slice — reuse `DeepSeekProvider` / `ProviderAgent` /
  `run_deepseek_consensus_game_with_provider_factory(write_runtime_spine=True)` verbatim.
- **Implementation commits (TDD, one per task):**
  - `99a84df` feat(g3-1): allow mode=live for profile launches (protocol)
  - `b2f8647` feat(g3-1): server live-mode gate matrix + launcher dispatch
  - `edca049` feat(g3-1): build_deepseek_launcher delegating to spine consensus runner (budget=32)
  - `dfb560b` feat(g3-1): honest execution markers in resolved-profile artifact
  - `eaaca99` feat(g3-1): run_observer_server --allow-live-api/--api-key-env/--max-live-requests
  - `ce3fa17` test(g3-1): secret-scan + artifact-contract regression for live path
  - `34dfbf1` feat(g3-1): gated manual DeepSeek live smoke (script + skipUnless wrapper)
  - `69454e8` docs(g3-1): tree refresh + normalize fake-key fixture + review packet
  - `4a1a2ba` fix(g3-1): expose key-free run-status reason in run detail/list/SSE *(review round 1, P1)*

> **Review round 1 (BLOCK) — addressed.** P1: the key-free run reason
> (`budget_exhausted`/`provider_failure`) was recorded in `state.run_errors` but
> not surfaced; now exposed in run detail (`/api/runs/{id}`), the run list, and the
> final SSE `run_status` (commit `4a1a2ba`). P2: the packet under
> `.logs/review/latest/` is **tracked** (the `latest/` dir holds the current
> slice's packet — G2d-2 set that precedent); this slice replaces the stale G2d-2
> packet with this one. The earlier "gitignored/local-only" handoff note was
> incorrect.

## Changed files & diff stat (implementation, `2435caa..HEAD`)
```
 scripts/dev/run_deepseek_live_smoke.py   | 145 +  (new, gated, not in default suite)
 src/werewolf_eval/deepseek_launcher.py   | 121 +  (new)
 src/werewolf_eval/observer_protocol.py   |   7 +
 src/werewolf_eval/observer_server.py     | 104 +-
 src/werewolf_eval/profile_config.py      |  19 +-
 src/werewolf_eval/run_observer_server.py |  69 +-
 tests/test_deepseek_launcher.py          | 195 +  (new)
 tests/test_deepseek_live_smoke.py        |  70 +  (new, skipUnless wrapper)
 tests/test_observer_protocol.py          |  34 +
 tests/test_observer_server.py            | 491 +
 tests/test_profile_config.py             |  50 +
 11 files changed, 1291 insertions(+), 14 deletions(-)
```
Plus the previously-committed docs (spec 178, plan 215) already on the branch.
`compileall src tests scripts` → clean.

## Allowlist conformance
- Every changed file is in the plan Allowlist. PASS
- **Forbidden files untouched** (verified `git diff --name-only main...HEAD`):
  no `deepseek_provider.py` / `provider_agent.py` / `provider_contract.py` /
  `game_engine.py` / `run_deepseek_consensus_game.py`; no Qt; no
  `docs/ROADMAP|TASKS|adr`; no new third-party deps. PASS

## A1 — Gate matrix (capability -> validate -> shape; no run_dir on any reject)
Two pure helpers + an in-process dispatch harness validate every branch
**offline** (localhost HTTP is blocked in this env -> socket tests error by
design; the helpers + harness need no socket).

| # | Request | Result | Code | run_dir | Test |
|---|---------|--------|------|---------|------|
| 1 | mode omitted + deepseek | fake launcher | 202 | created | `LiveDispatchTests.test_mode_omitted_runs_fake_launcher` |
| 2 | mode=fake | fake launcher | 202 | created | `...test_mode_fake_runs_fake_launcher` |
| 3 | live, not `--allow-live-api` | reject | 403 `live_api_disabled` | **none** | `...test_live_not_enabled_403_disabled_no_run_dir` |
| 4 | live, flag on, no key | reject | 403 `missing_api_key` | **none** | `...test_live_enabled_no_key_403_missing_no_run_dir` |
| 5 | live, non-deepseek seat | reject | 400 `unsupported_live_provider` | **none** | `...test_live_non_deepseek_400_unsupported_no_run_dir` |
| 6 | live, >1 deepseek model | reject | 400 `mixed_models` | **none** | `...test_live_mixed_models_400_no_run_dir` |
| 7 | live, single-model deepseek + launcher | live launcher | 202 | created | `...test_live_valid_runs_live_launcher` |
| 8 | template + live | reject (parser) | `ObserverProtocolError` | — | `LiveModeTests.test_template_launch_rejects_live_mode` |
| 9 | **capability precedes validity**: live disabled + malformed | reject | 403 `live_api_disabled` (not `invalid_profile`) | **none** | `...test_capability_precedes_validity_disabled_with_malformed` |
| 10 | **capability precedes shape**: live disabled + non-deepseek | reject | 403 `live_api_disabled` (not shape error) | **none** | `...test_capability_precedes_shape_disabled_with_non_deepseek` |
| 11 | flag-on + key-missing + malformed | reject | 403 `missing_api_key` (capability wins) | **none** | `...test_capability_missing_key_precedes_validity` |

`_check_live_capability` runs BEFORE profile load/validate; `_check_live_profile_shape`
(provider-check before model-check) runs AFTER validate; all rejects precede
`run_dir.mkdir`. `LiveGateHelperTests` (12) unit-tests both helpers directly.

## A7 — Budget=32 default, fail-closed classification
- `DEFAULT_MAX_LIVE_REQUESTS = 32` (`deepseek_launcher.py:32`); server-override-only via
  `--max-live-requests`; never per-request.
- `build_deepseek_provider_config` default `max_requests=32`; explicit overrides.
  Tests: `DeepSeekLauncherConfigTests.test_default_budget_is_32` / `..._explicit_budget_overrides_default`.
- Fail-closed chain (reuse verbatim): provider raises `RuntimeError("request budget exceeded: N")`
  -> `ProviderAgent` wraps reason `"provider error: request budget exceeded: N"` -> runner writes
  `failure-audit.json` + returns 2. `deepseek_launcher._classify_failure` reads that audit:
  reason contains `"budget exceeded"` -> **exit 3** (`budget_exhausted`), else **exit 2**
  (`provider_failure`); corrupt/missing audit -> 2 (no crash). Tests:
  `...test_budget_exhaustion_classified_exit_3`, `...test_generic_provider_failure_classified_exit_2`.
- Server maps the code to a **key-free** run-status reason via `_map_launcher_exit_reason`
  (3->`budget_exhausted`, else->`provider_failure`). Tests: `LiveGateHelperTests.test_exit_code_*`.
- **The reason is exposed** (not just recorded): `_execute_run` stores a canonical key-free
  reason in `state.run_errors` (exceptions also map to `provider_failure`, never raw text), and
  `_run_detail_with_reason` attaches it to `GET /api/runs/{id}` and the run list; the final SSE
  `run_status` carries it via `format_sse_status(..., reason)`. Tests:
  `LiveRunStatusReasonTests` (exit 3->`budget_exhausted`, exit 2->`provider_failure`, exit 0->no
  reason, exception->`provider_failure`) + `ObserverVisibilityTests.test_sse_status_*`.

## A2/A3 — Live execution + honest artifacts
- A2: the live launcher delegates to `run_deepseek_consensus_game_with_provider_factory(
  write_runtime_spine=True)` and writes the full spine (`events.jsonl`, `snapshots/`,
  `prompt-manifest.json`) + bundle (`game/decision/consensus/provider-trace/failure-audit`).
  Proven with an injected fake provider: `DeepSeekLauncherTests.test_launcher_writes_spine_and_bundle`.
- A3: `build_resolved_profile_artifact(..., execution_mode, live_api)` is parameterized; the server
  `_profile_launcher` wrapper stamps `execution_mode="live"`/`live_api="used"` only for live
  (else `fake`/`not_used`), `secrets_redacted=True` always, and records the **resolved real
  per-seat model** (authoritative). The launcher does NOT write `resolved-profile.json` (server
  wrapper's artifact). Runtime-spine `prompt-manifest.json` model stays `"unknown"` — documented
  runner limitation, **named follow-up** (not a bug). Tests: `LiveArtifactTests`,
  `LiveDispatchTests.test_live_dispatch_stamps_live_markers` / `..._fake_dispatch_stamps_fake_markers`.

## A4 — Fake is the unconditional default
Live requires the quadruple gate: `mode=live` + `--allow-live-api` + env key +
all-deepseek single-model seats. `create_observer_server` defaults `live_enabled=False`,
`live_launcher=None`. `resolve_live_launcher` wires the launcher only with flag+key.
Tests: `ObserverServerLiveOptInTests` (no-flag->disabled; flag+no-key->no launcher;
flag+key->launcher; custom `--api-key-env` honored).

## A5 — No secrets; default suite never reads the key or opens a socket
- **Secret-scan over the diff:** the only `sk-...` literals are clearly-fake (`sk-test-fake*`,
  `sk-test-fake-unused`); no real key, no real `Authorization` header value committed
  (`Authorization`/`Bearer `/`api_key`/`DEEPSEEK_API_KEY`/`sk-` appear only as **scan markers**).
- **Key read:** the ONLY `os.environ` read of `DEEPSEEK_API_KEY` in tests is INSIDE the
  `@skipUnless(RUN_DEEPSEEK_LIVE_SMOKE==1)` body of `test_deepseek_live_smoke.py` (never at
  discovery). The smoke script reads the key only after the `RUN_DEEPSEEK_LIVE_SMOKE` gate and
  never prints key/Authorization/raw request.
- **No socket in the default suite:** every *executed* launcher uses an injected fake
  `provider_factory`. The one test that builds a real-provider launcher
  (`test_flag_on_with_key_builds_launcher`) only asserts `callable(...)` — never calls it
  (a `DeepSeekProvider` opens no socket until `respond()`).
- **Artifact non-leak:** `DeepSeekLauncherTests.test_key_never_in_artifacts` and
  `LiveArtifactContractTests.test_faked_live_artifacts_contain_no_secret_markers` rglob the
  output dir for the marker set -> none; `..._config_key_absent_from_raised_errors` proves the
  key never surfaces in a raised error string; `secrets_redacted=True` in manifest + resolved-profile.

> Forbidden-pattern note: this packet and the G3-1 tests contain the literal scan markers
> `Authorization` / `Bearer ` / `api_key` / `DEEPSEEK_API_KEY` / `sk-test-*` **only** as
> redaction/secret-scan patterns and clearly-fake fixtures — never a real credential.

## A6 — Offline suite green; smoke skips; artifact contract
- Full suite `python -m unittest discover -s tests -p "test_*.py"`:
  **489 ran, 1 failure, 47 errors, 1 skipped.**
  - 47 errors = ALL `test_observer_server` **HTTP-socket** tests (env-blocked `RemoteDisconnected`);
    every exception is a connection error, none a refactor regression (verified).
  - 1 failure = pre-existing `test_context_budget.ContextBudgetGateDocsTests` (AGENTS.md docs gate,
    unrelated to this slice).
  - 1 skipped = the live smoke (gated; never reads the key).
- Focused offline G3-1 classes: **52 tests OK (1 skipped).**
- Artifact contract: a faked live launch yields the **same top-level artifact set** as a fake
  launch (`LiveArtifactContractTests.test_live_and_fake_produce_same_top_level_artifact_set`); only
  the execution markers differ (`...test_only_execution_markers_differ`).

## Adversarial review (workflow `wf_b457156c-e8a`)
5 independent skeptic agents reviewed the committed code across `gate-order`,
`secret-offline`, `budget-failclosed`, `artifact-honesty`, `scope-compliance`,
each finding verified by a second agent. **0 candidate findings, 0 confirmed
findings.** (~397k tokens, 259 tool uses.)

## Manual real-DeepSeek smoke (A6) — PENDING owner, pre-merge
**Not run in this environment** — it requires a real `DEEPSEEK_API_KEY` and outbound
network, and this env blocks both (localhost/socket access is blocked; no key present, and
the default suite must never read one). Owner to run once before merge:
```
RUN_DEEPSEEK_LIVE_SMOKE=1 DEEPSEEK_API_KEY=... PYTHONPATH=src python scripts/dev/run_deepseek_live_smoke.py
```
Record the **text-free** result here: `smoke=PASS/FAIL`, `exit_code`, `real_response_count`,
`check_*` booleans (no model text, no key). If `max_requests=32` truncated the game, note it and
bump to 48/64 in a separate evidence-based commit. The optional wrapper
`tests/test_deepseek_live_smoke.py` runs the same path when `RUN_DEEPSEEK_LIVE_SMOKE=1`.

## Open / follow-ups (named, out of scope)
- Thread the real model into runtime-spine `prompt-manifest.json` (stays `"unknown"`; needs a
  consensus-runner change). `resolved-profile.json` is the authoritative model record.
- Qt live/fake toggle = **G3-2**.
- Per-seat distinct models; template live launch; retries — all deferred.

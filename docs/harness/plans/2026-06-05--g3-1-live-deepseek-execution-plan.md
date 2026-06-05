# G3-1 Live DeepSeek Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. **TDD is mandatory**: write the failing test, run it red, implement, run it green, commit. **The default test suite MUST stay 100% offline — no test may read `DEEPSEEK_API_KEY` or make a real network call.**

**Goal:** Let a `POST /api/runs` **profile** launch execute via the **real `DeepSeekProvider`** through the observer server, behind an explicit server-side opt-in (`--allow-live-api` + env key) and `mode=live`, with **fake-deterministic as the unconditional default**. Wiring only — reuse the existing provider/agent/consensus-runner verbatim.

**Spec:** `docs/superpowers/specs/2026-06-05-g3-1-live-deepseek-execution-design.md` (reviewed; decisions locked: `max_requests=32`, server-only, one-shared-model, offline suite + gated manual smoke).

**Tech Stack:** Python stdlib only (extends G2d observer/profile layer). No new third-party deps. No Qt changes this slice.

---

## Context Basis (verified via understanding pass `wf_48a0b954`; executor MUST re-confirm signatures in each task's Step 0)

- **Reusable verbatim (do NOT modify):**
  - `run_deepseek_consensus_game.py` → `run_deepseek_consensus_game_with_provider_factory(*, game_id, out_dir, provider_factory, write_runtime_spine=True)` (~:73) — creates `RuntimeEventWriter`, writes full bundle + spine, maps `ProviderActionError → exit 2`.
  - `deepseek_provider.py` → `DeepSeekProvider` + `DeepSeekProviderConfig(api_key, base_url, model, timeout_seconds, max_tokens, max_requests)` + injectable `Transport` (default urllib). Key stays out of logs/traces/errors; hard `max_requests` budget; no retry.
  - `run_deepseek_provider_game.py` → `_build_deepseek_agent(api_key, base_url, model, timeout_seconds, max_tokens, max_requests) -> provider_factory` (~:137) — ONE shared provider for all seats.
  - `provider_agent.py` → `ProviderAgent`; `provider_contract.py` → `DEEPSEEK_PROVIDER_SOURCE_LABEL`.
  - `runtime_events.py` → `RuntimeEventWriter`, `redact_secret_values`, `assert_no_secret_patterns` (fail-closed on secret substrings).
- **Extend (this plan's edits):**
  - `observer_server.py`: `RunLauncher = Callable[[str, Path], int]` (:60); `default_fake_launcher` (:65); `ObserverServerState` (:69); `create_observer_server(..., launcher=None)` (:525); `_handle_profile_launch` (:341); `_profile_launcher` closure (:380, calls `base(rid,rdir)` then writes `resolved-profile.json`); `_launch_run_async` (:329, records `run_errors`).
  - `observer_protocol.py`: `ALLOWED_MODES = ("fake",)`; `parse_profile_launch_request` (carries `mode`); `parse_launch_request` (template).
  - `profile_config.py`: `resolve_profile` (:219); `build_resolved_profile_artifact(profile, run_id)` (:229) — hard-codes `execution_mode="fake"`, `live_api="not_used"`, `secrets_redacted=True`.
- **Test fakes to reuse (zero network):**
  - `tests/test_deepseek_provider.py` — `fake_transport` seam for `DeepSeekProvider`.
  - `tests/test_deepseek_consensus_game.py` — `_FakeDeepSeekProvider` + `provider_factory` injection.
  - `tests/test_deepseek_provider_game.py` — missing-key subprocess pattern (`--api-key-env DOES_NOT_EXIST_XXXX`).
  - `tests/test_observer_server.py` — `_request_json`, `_start_server`, `_valid_profile_payload`, `_wait_for_status`, `ObserverServerProfileTests`, `ObserverServerSecretScanTests`.
  - `tests/test_g1h_runtime_spine.py` — secret-scan marker set `['Authorization','Bearer ','api_key','DEEPSEEK_API_KEY','sk-']`.

**Build/verify (offline):**
```bash
PYTHONPATH=src python -m unittest tests.test_observer_protocol tests.test_observer_server tests.test_profile_config tests.test_deepseek_launcher -v
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"   # full suite, must stay offline
PYTHONPATH=src python -m compileall src tests
```
> NOTE: in THIS environment localhost HTTP is blocked (`RemoteDisconnected`), so `tests.test_observer_server.*` error here exactly as the existing server tests do — document, do not "fix". Logic is validated by the launcher/protocol/profile unit tests (no server socket).

---

## Allowlist
```
src/werewolf_eval/deepseek_launcher.py            (new)
src/werewolf_eval/observer_server.py
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/profile_config.py
src/werewolf_eval/run_observer_server.py
scripts/dev/run_deepseek_live_smoke.py            (new, gated, not in default suite)
tests/test_deepseek_launcher.py                   (new)
tests/test_deepseek_live_smoke.py                 (new, skipUnless wrapper)
tests/test_observer_server.py
tests/test_observer_protocol.py
tests/test_profile_config.py
docs/superpowers/specs/2026-06-05-g3-1-live-deepseek-execution-design.md
docs/harness/plans/2026-06-05--g3-1-live-deepseek-execution-plan.md
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

## Forbidden Scope
No edits to `deepseek_provider.py` / `provider_agent.py` / `provider_contract.py` / `game_engine.py` / consensus-runner internals (reuse verbatim). No Qt client changes (live UI toggle = G3-2). No `docs/ROADMAP.md` / `docs/TASKS.md` / `docs/adr/**` edits. No new deps. **No secret in any committed file/fixture; no test reads `DEEPSEEK_API_KEY` or opens a real socket to api.deepseek.com.** No per-seat models, no template live launch, no retries, no `g1b_default` live.

---

## Task 1 — `mode="live"` in the protocol (profile-only)

**Files:** `src/werewolf_eval/observer_protocol.py`, `tests/test_observer_protocol.py`

- [ ] **Step 1 (red):** In `tests/test_observer_protocol.py` add `LiveModeTests`:
  - `parse_profile_launch_request({"profile": <valid>, "mode": "live"})` returns `mode == "live"` (no raise).
  - `parse_launch_request({"template": "default_6p_fake", "mode": "live"})` **raises** `ObserverProtocolError` (template+live forbidden — live is profile-only).
  - `parse_profile_launch_request` with `mode` omitted still defaults to `DEFAULT_FAKE_MODE`.
  Run → fail.
- [ ] **Step 2 (green):** `observer_protocol.py`: add `"live"` to `ALLOWED_MODES`. In `parse_launch_request`, after computing `mode`, reject `mode == "live"` (template launches may not go live this slice). Leave `parse_profile_launch_request` mode validation as-is (now accepts `live`).
- [ ] **Step 3:** Run focused → OK. Commit: `feat(g3-1): allow mode=live for profile launches (protocol)`.

---

## Task 2 — Server gate matrix + dispatch (injected fake launcher)

**Files:** `src/werewolf_eval/observer_server.py`, `tests/test_observer_server.py`

- [ ] **Step 0:** Re-read `_handle_profile_launch` (:341) and `_profile_launcher` (:380) and `ObserverServerState` (:69) to confirm insertion points.
- [ ] **Step 1 (red):** Add `LiveDispatchTests` to `tests/test_observer_server.py` driving `create_observer_server(..., live_launcher=<fake>)` directly (NOT over HTTP — call the handler/launcher path via the existing in-process test harness, or via `_request_json` where the env allows). Use a **fake `live_launcher`** that writes a sentinel file + returns 0. Assert the **gate matrix** branch-by-branch:
  1. `mode` omitted + deepseek profile → **fake** launcher ran (no sentinel).
  2. `mode="fake"` → fake ran.
  3. `mode="live"`, server built **without** `live_launcher` → `403 live_api_disabled`; **`run_dir` NOT created**.
  4. `mode="live"`, server built with a `live_launcher` but flagged key-missing (see Task 5 seam: pass `live_enabled=True, live_launcher=None`) → `403 missing_api_key`; no `run_dir`.
  5. `mode="live"` + a seat resolving to a non-deepseek provider → `400 unsupported_live_provider`; no `run_dir`.
  6. `mode="live"` + deepseek seats with **>1 distinct model** → `400 mixed_models`; no `run_dir`.
  7. `mode="live"` + single-model deepseek profile + `live_launcher` set → the **fake live_launcher ran** (sentinel present) and `resolved-profile.json` shows `execution_mode="live"` (after Task 4).
  Run → fail.
- [ ] **Step 2 (green):** `observer_server.py`:
  - `ObserverServerState`: add `live_enabled: bool = False` and `live_launcher: RunLauncher | None = None`.
  - `create_observer_server(..., live_enabled=False, live_launcher=None)` → store on state.
  - `_handle_profile_launch`: after profile validation, compute `mode = plr["mode"]` and the resolved seats (`resolve_profile`). Implement the **canonical gate order** (all rejects BEFORE `run_dir.mkdir`):
    1. `mode != "live"` → `base = state.launcher` (fake).
    2. `mode == "live"` and `not state.live_enabled` → `_send_error_json(403,"live_api_disabled",...)`, return.
    3. `mode == "live"` and `state.live_launcher is None` → `_send_error_json(403,"missing_api_key",...)`, return.
    4. any resolved seat `provider != "deepseek"` → `_send_error_json(400,"unsupported_live_provider",...)`, return.
    5. distinct deepseek seat models > 1 → `_send_error_json(400,"mixed_models",...)`, return.
    6. else `base = state.live_launcher`.
  - Thread `execution_mode`/`live_api` into `_profile_launcher` so it stamps the artifact per the chosen base (`"live"`/`"used"` when `base is live_launcher`, else `"fake"`/`"not_used"`). (Artifact parameterization lands in Task 4.)
  Run → fail-then-green (server tests env-blocked here → validate the gate logic via a thin unit harness that calls the handler's gate helper directly; factor the gate decision into a pure helper `_resolve_launch_base(state, mode, resolved_seats) -> (base, error)` and unit-test THAT offline).
- [ ] **Step 3:** Focused tests OK (offline gate-helper unit tests green; document server-socket tests as env-blocked). Commit: `feat(g3-1): server live-mode gate matrix + launcher dispatch`.

> **Design note:** factor the gate into a pure `_resolve_launch_base(...)` so the full matrix is unit-tested with **no socket** (the env blocks localhost). The HTTP handler just calls it and maps to `_send_error_json`.

---

## Task 3 — `build_deepseek_launcher` (delegates to the consensus runner)

**Files:** `src/werewolf_eval/deepseek_launcher.py` (new), `tests/test_deepseek_launcher.py` (new)

- [ ] **Step 0:** Re-read `run_deepseek_consensus_game_with_provider_factory` signature + `_build_deepseek_agent` + `_FakeDeepSeekProvider`/`provider_factory` injection in `tests/test_deepseek_consensus_game.py`. Confirm how a provider failure / budget error surfaces (exit code + recorded reason).
- [ ] **Step 1 (red):** `tests/test_deepseek_launcher.py`:
  - `test_launcher_writes_spine_and_bundle`: build `build_deepseek_launcher(api_key="sk-test-… (fake)", base_url=..., model="deepseek-chat", timeout_seconds=30, max_tokens=..., max_requests=32, provider_factory=<fake returning _FakeDeepSeekProvider>)`. Call `launcher(run_id, run_dir)` → returns 0; assert `events.jsonl`, `snapshots/`, `prompt-manifest.json`, and the game/decision/consensus/provider-trace/failure-audit bundle exist; `prompt-manifest.json` model == the resolved real model (not `"unknown"`).
  - `test_launcher_default_budget_is_32`: assert the launcher passes `max_requests=32` into the provider config by default; an explicit arg overrides it.
  - `test_budget_exhaustion_fails_closed`: a fake provider that raises the budget error → launcher returns nonzero; `provider-trace.json` + `failure-audit.json` exist; no valid completed game log.
  - `test_key_never_in_artifacts`: pass a fake `sk-test-key`; rglob the output dir for `['Authorization','Bearer ','api_key','DEEPSEEK_API_KEY','sk-']` → none; assert the key string itself is absent.
  Run → fail (module missing).
- [ ] **Step 2 (green):** `deepseek_launcher.py`: `build_deepseek_launcher(*, api_key, base_url, model, timeout_seconds=30, max_tokens, max_requests=32, provider_factory=None) -> RunLauncher`. Default `provider_factory` = `_build_deepseek_agent(...)`-shaped (one shared `DeepSeekProvider`). The returned `Callable[[str,Path],int]` calls `run_deepseek_consensus_game_with_provider_factory(game_id=run_id, out_dir=run_dir, provider_factory=..., write_runtime_spine=True)` and returns its exit code; on budget/provider failure return nonzero and let the runner's artifacts record the reason. Inject `provider_factory` so tests pass a fake (no real transport).
- [ ] **Step 3:** Focused OK. Commit: `feat(g3-1): build_deepseek_launcher delegating to spine consensus runner (budget=32)`.

---

## Task 4 — Honest `resolved-profile.json` + prompt-manifest model

**Files:** `src/werewolf_eval/profile_config.py`, `tests/test_profile_config.py` (+ live-path wiring already in Tasks 2/3)

- [ ] **Step 1 (red):** `tests/test_profile_config.py` add `LiveArtifactTests`:
  - `build_resolved_profile_artifact(profile, run_id, execution_mode="live", live_api="used")` → dict with `execution_mode=="live"`, `live_api=="used"`, `secrets_redacted is True`, prompts still hash-only (no raw prompt text).
  - default call (no kwargs) still yields `execution_mode=="fake"`, `live_api=="not_used"` (back-compat).
  Run → fail.
- [ ] **Step 2 (green):** parameterize `build_resolved_profile_artifact(profile, run_id, *, execution_mode="fake", live_api="not_used")`. Ensure the live launcher / `_profile_launcher` passes `execution_mode="live", live_api="used"` on the live base. Ensure the live prompt-manifest model is the resolved model (fix the consensus runner's `"unknown"` ONLY via the launcher's inputs — do NOT edit the runner; if the runner hard-codes `"unknown"`, record the resolved model in `resolved-profile.json` instead and note the manifest limitation).
- [ ] **Step 3:** Focused OK. Commit: `feat(g3-1): honest execution markers in resolved-profile artifact`.

---

## Task 5 — `run_observer_server.py` live opt-in + key injection

**Files:** `src/werewolf_eval/run_observer_server.py`, `tests/test_observer_server.py`

- [ ] **Step 1 (red):** subprocess gate tests (mirror `tests/test_deepseek_provider_game.py`), kept offline by pointing at a non-existent env var:
  - start `run_observer_server --allow-live-api --api-key-env DOES_NOT_EXIST_XXXX` → server starts with `live_enabled=True`, `live_launcher=None`; a `mode=live` request → `403 missing_api_key`; nothing written. *(If localhost is blocked in this env, assert the wiring via importing `main`'s arg-parse + builder helpers directly instead of a live socket.)*
  - start without `--allow-live-api` → `mode=live` → `403 live_api_disabled`.
  Run → fail.
- [ ] **Step 2 (green):** `run_observer_server.py`: add `--allow-live-api`, `--api-key-env` (default `DEEPSEEK_API_KEY`), `--max-live-requests` (default `32`), `--deepseek-base-url`, `--deepseek-model`. When `--allow-live-api`: set `live_enabled=True`; read the key **once** from `os.environ[api_key_env]`; if present, build `build_deepseek_launcher(api_key=…, max_requests=…, …)` and pass `live_launcher=` to `create_observer_server`; if absent, pass `live_launcher=None` (→ `missing_api_key` at request time). **Never** log the key. Factor the builder into a pure helper for offline import-tests.
- [ ] **Step 3:** Focused OK. Commit: `feat(g3-1): run_observer_server --allow-live-api/--api-key-env/--max-live-requests`.

---

## Task 6 — Secret-scan + artifact-contract regression

**Files:** `tests/test_observer_server.py`, `tests/test_deepseek_launcher.py`

- [ ] **Step 1 (red):** add:
  - artifact-contract test: a faked live launch produces the **same file set** as the fake launch (only execution markers differ).
  - extend `ObserverServerSecretScanTests` so a faked live-launch response/artifacts are scanned against the marker set; assert `secrets_redacted is True` in manifest/resolved-profile.
  - exception-message test: a fake `sk-test-key` passed to `DeepSeekProviderConfig` never appears in any raised error string (reuse `deepseek_provider` patterns, offline).
  Run → fail.
- [ ] **Step 2 (green):** adjust as needed (most should pass if Tasks 2–4 are correct; treat any failure as a real regression).
- [ ] **Step 3:** Commit: `test(g3-1): secret-scan + artifact-contract regression for live path`.

---

## Task 7 — Gated manual real-DeepSeek smoke (NOT a default gate)

**Files:** `scripts/dev/run_deepseek_live_smoke.py` (new), `tests/test_deepseek_live_smoke.py` (new)

- [ ] **Step 1:** `scripts/dev/run_deepseek_live_smoke.py`: builds the live launcher from `os.environ[DEEPSEEK_API_KEY]`, runs ONE game into a temp dir, prints a **text-free** PASS/FAIL (run completed, spine + bundle exist, `live_api=used`, no secret marker in output). It **must not** print the key, the `Authorization` header, or the full raw request. Refuses to run unless `RUN_DEEPSEEK_LIVE_SMOKE=1` and the key is present.
- [ ] **Step 2:** `tests/test_deepseek_live_smoke.py`: a `unittest.skipUnless(os.environ.get("RUN_DEEPSEEK_LIVE_SMOKE")=="1" and os.environ.get("DEEPSEEK_API_KEY"), "live smoke disabled")` wrapper that invokes the script's entry and asserts structural success only. **By default this test SKIPS** — it is never a CI/acceptance gate.
- [ ] **Step 3:** Run the default suite → confirm the smoke test **skips** and nothing hits the network. Commit: `feat(g3-1): gated manual DeepSeek live smoke (script + skipUnless wrapper)`.
- [ ] **Step 4 (manual, pre-merge):** with a real key, run `RUN_DEEPSEEK_LIVE_SMOKE=1 DEEPSEEK_API_KEY=… python scripts/dev/run_deepseek_live_smoke.py`; record the **text-free** result (pass/fail, request count, `live_api=used`, no leak) in the review packet. If 32 truncated the game, note it and (separately) bump to 48/64 with evidence.

---

## Task 8 — Full validation + review packet + PR

- [ ] **Step 1:** `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"` — assert the **only** failures are the documented env-blocked `test_observer_server.*` (RemoteDisconnected) + the pre-existing `test_context_budget` one; the smoke test **skips**. `compileall` clean.
- [ ] **Step 2:** Forbidden/secret scan over the diff: no `DEEPSEEK_API_KEY` read in tests, no `sk-…` literals except clearly-fake `sk-test-…` markers, no real `Authorization` header in committed files, no socket to `api.deepseek.com` in the default suite.
- [ ] **Step 3:** `node .codex/hooks/tree.mjs --force` (new files: `deepseek_launcher.py`, smoke script/test).
- [ ] **Step 4:** Write `.logs/review/latest/review-packet.md` (≤300 lines): metadata, changed files, diff stat/check, allowlist, **gate-matrix evidence table**, budget=32 + `budget_exhausted` evidence, secret-scan, offline-suite confirmation, **manual smoke result (text-free)**, acceptance A1–A7.
- [ ] **Step 5:** Commit; push branch; open PR `feat: add G3-1 live DeepSeek execution (opt-in, fake-by-default)`; merge per owner approval.

---

## Acceptance Criteria (hard)
- **A1 — Gate matrix** holds branch-by-branch (omitted/fake→fake; live+no-flag→403 `live_api_disabled`; live+flag+no-key→403 `missing_api_key`; live+non-deepseek→400 `unsupported_live_provider`; live+mixed-models→400 `mixed_models`; live+valid→live launcher; template+live→400). **No `run_dir` on any reject.** *(Task 1/2)*
- **A2** Live launch runs via `DeepSeekProvider` (server-side env key) and writes the full spine + bundle. *(Task 3, injected fake)*
- **A3** `resolved-profile.json` honest (`execution_mode=live`/`live_api=used`/`secrets_redacted=true`); manifest model = resolved real model (or documented limitation). *(Task 4)*
- **A4** Fake is the unconditional default; live needs flag+key+mode+deepseek; mixed models → 400. *(Task 2/5)*
- **A5** No secret in any artifact/event/snapshot/response/error; **no default test reads the key or opens a real socket.** *(Task 6)*
- **A6** Default suite offline & green (env-blocked server tests excepted); smoke **skips** by default; manual smoke run once pre-merge, text-free result recorded. *(Task 7/8)*
- **A7** `max_requests=32` default, server-override-only; reaching it **fails closed** `budget_exhausted`. *(Task 3/5)*

---

## PR Description Draft
Title: `feat: add G3-1 live DeepSeek execution (opt-in, fake-by-default)`
- Wires the existing `DeepSeekProvider` + spine consensus runner into the observer profile-launch path behind `mode=live` + `--allow-live-api` + env key + deepseek-seats; fake stays default.
- Canonical gate matrix with distinct error codes; honest live artifacts; env-only key; `max_requests=32` fail-closed.
- Default suite 100% offline (injected fakes); gated manual smoke (`scripts/dev/run_deepseek_live_smoke.py`) run once pre-merge.

## Execution Handoff
Order: (1) protocol live mode, (2) server gate matrix via pure helper, (3) deepseek_launcher, (4) honest artifact, (5) run_observer_server opt-in, (6) secret/contract regression, (7) gated smoke, (8) validate+packet+PR. Each task commits. Keep the default suite offline; never read the real key in automated tests.

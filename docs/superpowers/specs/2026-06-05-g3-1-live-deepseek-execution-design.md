# G3-1 Live DeepSeek Execution — Design Spec

**Status:** draft (for spec review)
**Route:** Phase 3 / G3 experiment route — first slice (`docs/ROADMAP.md` §G3 "Replay + live dual mode"). Depends on G1h event spine + G2a/G2c/G2d observer contracts.
**Date:** 2026-06-05

---

## 1. Goal

Let a `POST /api/runs` **profile launch** execute via the **real `DeepSeekProvider`** through the observer server — behind an explicit, server-side opt-in, with env-only secret handling — while **fake-deterministic remains the unconditional default**. This closes the declared-vs-executed gap that the G2d-2 "Deterministic Mock" banner currently flags: a profile can declare `deepseek`/`deepseek-chat`, and (only when explicitly enabled) actually run it.

**Success criteria**
- A `deepseek` profile + `mode=live` + server started with `--allow-live-api` + a present API key produces a **real** game with the **full runtime spine** (`events.jsonl`, `snapshots/`, `prompt-manifest.json`) and the same artifact bundle the observer already consumes, with **honest** execution markers (`execution_mode=live`, `live_api=used`).
- Every other request stays fake/offline by construction.
- **Zero secrets** in any artifact, event, snapshot, or HTTP response.
- The **default automated test suite makes no real API call and never reads the key**; a separate **gated, manual smoke** proves the real interface.

---

## 2. Current state (verified)

The live primitives already exist and are independently offline-tested; this slice is **wiring only — no new provider/engine code**.

- **Provider seam (live-capable, CLI-only today).** `ProviderAgent` (`provider_agent.py:30`) wraps one seat + a duck-typed provider whose only call is `respond(ProviderRequest) -> ProviderResponse` (`provider_contract.py`). `DeepSeekProvider` (`deepseek_provider.py:40`) is a drop-in `respond` over an injectable `Transport` (default stdlib `urllib`); config `DeepSeekProviderConfig(api_key, base_url, model, timeout_seconds, max_tokens, max_requests)`; stamps `source_label="[DeepSeek API output]"`; hard `max_requests` budget; **no retry**; raises `RuntimeError` on any failure; the key lives only in the in-memory config + `Authorization` header — never logged/traced/stored.
- **Live game runner with spine.** `run_deepseek_consensus_game_with_provider_factory(*, game_id, out_dir, provider_factory, write_runtime_spine=True)` (`run_deepseek_consensus_game.py:73`) creates a `RuntimeEventWriter` and writes the **full** bundle + spine; maps `ProviderActionError → exit 2`. CLI runners double-gate live calls behind `--allow-live-api` + an env key (default `DEEPSEEK_API_KEY`); a shared provider drives all seats (`_build_deepseek_agent`, `run_deepseek_provider_game.py:137`).
- **Observer always launches fake.** `run_observer_server.py` calls `create_observer_server(host, port, runs_dir)` → defaults to `default_fake_launcher` → `run_fake_runtime`. The injection seam exists: `RunLauncher = Callable[[str, Path], int]` (`observer_server.py:60`), `create_observer_server(..., launcher=None)` (`:525`), stored on `ObserverServerState.launcher` (`:69`). `_handle_profile_launch` (`:350`) wraps the base launcher in `_profile_launcher` (`:380`) which calls `base(rid, rdir)` **unconditionally** then writes `resolved-profile.json` via `build_resolved_profile_artifact` (`profile_config.py:229`), hard-stamped `execution_mode="fake"`, `live_api="not_used"`.
- **`mode` parsed but unused.** `ALLOWED_MODES = ("fake",)` (`observer_protocol.py:23`); `mode` is validated/echoed in the 202 response but never selects a launcher.
- **Profile resolution ready.** `resolve_profile` (`profile_config.py:219`) returns per-seat `{player_id, role, team, provider, model, prompt, strategy}`; `ALLOWED_PROVIDERS` already includes `deepseek`; profiles **forbid** secret-like keys/values (`_reject_secret_like_*`).

---

## 3. Architecture

```
HTTP POST /api/runs {profile, mode:"live"}
   -> parse_profile_launch_request  (mode in ALLOWED_MODES incl. "live")
   -> _handle_profile_launch:
        validate profile
        dispatch = live?  AND  state.live_launcher set (server --allow-live-api + key)
                          AND  resolved seats all use provider "deepseek"
                          AND  all deepseek seats share ONE model   (else 400)
        if mode=="live" but not live-enabled -> 403 live_api_disabled (BEFORE run_dir)
        base = state.live_launcher  (else state.launcher = fake)
   -> _profile_launcher wraps base, writes resolved-profile.json (execution_mode/live_api per base)
   -> _launch_run_async (daemon thread): base(run_id, run_dir) -> int status
        live base = build_deepseek_launcher(...)(run_id, run_dir)
          -> run_deepseek_consensus_game_with_provider_factory(
                 game_id=run_id, out_dir=run_dir,
                 provider_factory=<shared DeepSeekProvider from server-side env key>,
                 write_runtime_spine=True)
          -> DeepSeekProvider x seats -> engine(g1f_provider_consensus)
          -> events.jsonl + snapshots/ + prompt-manifest + game/decision/consensus/provider-trace/failure-audit
```

**New/changed surfaces**
1. **`src/werewolf_eval/deepseek_launcher.py` (new):** `build_deepseek_launcher(*, api_key, base_url, model, timeout_seconds, max_tokens, max_requests) -> RunLauncher`. The returned `Callable[[str, Path], int]` delegates to `run_deepseek_consensus_game_with_provider_factory(write_runtime_spine=True)` with a `provider_factory` that builds one shared `DeepSeekProvider` (reusing `_build_deepseek_agent`'s shape). Returns 0/2 from the runner; returns a distinct nonzero for config errors. **Adds zero engine logic.**
2. **`observer_server.py`:** `ObserverServerState.live_launcher: RunLauncher | None`; `create_observer_server(..., live_launcher=None)`; `_handle_profile_launch` gains mode dispatch + the early `403 live_api_disabled` reject + the same-model guard (`400 mixed_models` / `400 not_deepseek`). `_profile_launcher` stamps `execution_mode`/`live_api` per the chosen base.
3. **`observer_protocol.py`:** add `"live"` to `ALLOWED_MODES`. Live is **profile-only**: a template launch (`parse_launch_request`) with `mode=live` is rejected.
4. **`profile_config.py`:** parameterize `build_resolved_profile_artifact(..., execution_mode="fake", live_api="not_used")`; `secrets_redacted` stays true, prompts stay hashed.
5. **`run_observer_server.py`:** add `--allow-live-api` and `--api-key-env` (default `DEEPSEEK_API_KEY`); when set, read the key **once** from `os.environ`, build the live launcher, pass it to `create_observer_server`. Without the flag, no live launcher is wired.
6. **Honest manifest:** the live path sets `prompt-manifest.json` model to the resolved real model (the consensus runner currently writes `"model":"unknown"`).

---

## 4. Decisions

**Confirmed with product owner:**
- **Test boundary:** default suite **100% offline** (injected fake provider/transport; key env var never read). **Plus** a separate **gated, manual real-DeepSeek smoke** (script / env-gated test, excluded from the default suite) that asserts only structural success (HTTP 200 / completed run + spine present), never specific model text. Rationale: external API flakiness (network, rate-limit, balance, 5xx) must not red the regression chain; the key boundary must stay hard; real output is non-deterministic.
- **Qt UI:** **server-only this slice** (HTTP `mode=live`). A Qt fake/live toggle is a follow-up (G3-2); the Qt client + its secret-scan contract are untouched here.
- **Per-seat models:** **one shared model in v1.** If a live profile's `deepseek` seats select different models, **reject with 400 `mixed_models`**. Per-seat models = follow-up.

**Defaulted (open to spec-review adjustment):**
- **Key source:** server process **env only**, var named by `--api-key-env` (default `DEEPSEEK_API_KEY`). Never via HTTP/profile/CLI value.
- **Guardrails:** reuse `DeepSeekProvider` hard `max_requests` budget (conservative server default, **not caller-adjustable**) + `timeout_seconds=30`, **no retry**, fail the run on first `ProviderActionError`. Cost knobs are server-config-only.
- **Engine mode:** `g1f_provider_consensus` only (it is the mode that writes the runtime spine the observer needs).
- **Failure surface:** distinct machine-readable reasons — `live_api_disabled` (403), `mixed_models`/`not_deepseek` (400) at request time; run status `failed` with a key-free reason (`key_missing`, `budget_exceeded`, `provider_failure`) for launch-time failures.
- **Determinism:** live runs are **non-deterministic but fully auditable** (provider-trace, `source_label` provenance, hashed prompt-manifest, `resolved-profile.json=live`). No byte-identical replay promised.

---

## 5. Scope

**In scope:** profile-only live launch via `mode=live`; server opt-in gate (`--allow-live-api` + env key); env-only key injection; full spine + bundle artifacts with honest live markers; same-model + deepseek-provider request guards; offline regression tests + a gated manual smoke.

**Non-goals:** per-seat distinct models; template (non-profile) live launches; `g1b_default` live mode; retries/backoff; real latency measurement; Qt UI live toggle; any change to provider/engine behavior beyond wiring; live-by-default or key-presence-as-trigger.

**Allowlist (planned):**
```
src/werewolf_eval/deepseek_launcher.py        (new)
src/werewolf_eval/observer_server.py
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/profile_config.py
src/werewolf_eval/run_observer_server.py
tests/test_deepseek_launcher.py               (new)
tests/test_observer_server.py
tests/test_observer_protocol.py
tests/test_profile_config.py
scripts/ or tests/  live smoke (gated)         (new)
docs/superpowers/specs/2026-06-05-g3-1-live-deepseek-execution-design.md
docs/harness/plans/2026-06-05--g3-1-...-plan.md
```

**Forbidden scope:** no edits to `deepseek_provider.py` / `provider_agent.py` / `provider_contract.py` / `game_engine.py` / the consensus runner internals (reuse verbatim); no Qt client changes; no `docs/ROADMAP.md` / `docs/TASKS.md` / `docs/adr/**` edits without a bound plan; no new third-party deps; no secrets in any committed file/fixture.

---

## 6. Secret & determinism contract

- Key enters only `DeepSeekProviderConfig` (in a launcher closure) and the `Authorization` header. **Never** in a profile, request body, CLI value, event, snapshot, manifest, trace, error, or HTTP response.
- All run output flows through `RuntimeEventWriter` (events fail-closed via `assert_no_secret_patterns`; snapshots/manifests via `redact_secret_values`).
- Live = non-deterministic, audit-complete via `provider-trace.json` + `source_label` + hashed `prompt-manifest.json` + `resolved-profile.json (execution_mode=live)`.

---

## 7. Test strategy

**Default suite — zero real API calls, no key read:**
1. **Launcher unit** (`test_deepseek_launcher.py`): build `build_deepseek_launcher` with a `provider_factory` returning a fake-transport `DeepSeekProvider` / `_FakeDeepSeekProvider` (reuse `tests/test_deepseek_provider.py`, `tests/test_deepseek_consensus_game.py`). Assert exit 0; full bundle + spine present; `resolved-profile.json` stamps `execution_mode=live`/`live_api=used`/`secrets_redacted=true`; manifest model = resolved model. Failing-factory variant → exit 2 + provider-trace/failure-audit.
2. **Server dispatch** (extend `test_observer_server.py`): inject a **fake** `live_launcher` into `create_observer_server`. `mode=live` + deepseek profile → live launcher ran; `mode=fake` or `fake_deterministic` profile → fake ran; `mode=live` when not live-enabled → `403 live_api_disabled`, **no `run_dir`**; mixed deepseek models → `400 mixed_models`.
3. **Gate (subprocess)** (mirror `test_deepseek_provider_game.py`): start `run_observer_server --allow-live-api --api-key-env DOES_NOT_EXIST_XXXX`; a live request fails with key-missing surface and writes nothing; without `--allow-live-api`, `mode=live` is rejected. No real env var read.
4. **Secret-scan + contract:** rglob the (faked) live output dir against `['Authorization','Bearer ','api_key','DEEPSEEK_API_KEY','sk-']`; extend `ObserverServerSecretScanTests` over the live-launch response; assert a fake `sk-test-key` never appears in any error/artifact; assert the live file set == fake file set (only markers differ).

**Gated manual smoke (NOT in default suite):** a script / env-gated test (e.g. requires `WEREWOLF_LIVE_SMOKE=1` + `--allow-live-api` + a real key) that launches one real game and asserts **structural** success only (run completes, spine + bundle exist, `live_api=used`, no secret leak) — never specific text. Documented as a pre-merge manual step; cost-bounded by `max_requests`.

---

## 8. Slice tasks (TDD order)

- **T1** — `observer_protocol.py`: add `"live"` to `ALLOWED_MODES`; reject template+live. Parser/handler tests.
- **T2** — `observer_server.py`: `ObserverServerState.live_launcher` + `create_observer_server(live_launcher=)`; `_handle_profile_launch` dispatch + `403 live_api_disabled` early-reject + `400 mixed_models`/`not_deepseek`. Injected-fake-launcher server tests.
- **T3** — `deepseek_launcher.py`: `build_deepseek_launcher` delegating to the consensus runner; launcher artifact tests (fake transport/provider factory).
- **T4** — `profile_config.py`: parameterize `build_resolved_profile_artifact`; fix prompt-manifest model on the live path. Artifact-marker tests.
- **T5** — `run_observer_server.py`: `--allow-live-api` / `--api-key-env`; build + inject the live launcher from env. Subprocess gate tests (`DOES_NOT_EXIST_XXXX`).
- **T6** — Secret-scan + artifact-contract regression tests; review packet.
- **T7** — Gated manual real-DeepSeek smoke script/test + docs; run it once before merge and record the (text-free) result.

---

## 9. Acceptance criteria

- **A1** `mode=live` accepted only for profile launches when live-enabled; template+live and not-enabled paths rejected with distinct codes; no `run_dir` on reject. *(T1/T2)*
- **A2** Live profile launch runs via `DeepSeekProvider` (server-side env key) and writes the full spine + bundle the observer consumes. *(T3, injected fake)*
- **A3** `resolved-profile.json` honest (`execution_mode=live`,`live_api=used`,`secrets_redacted=true`); prompt-manifest model = resolved real model. *(T4)*
- **A4** Fake stays the unconditional default; quadruple gate (flag+key+mode+deepseek) enforced; mixed models → 400. *(T2/T5)*
- **A5** No secret in any artifact/event/snapshot/response; key never read by the default suite. *(T6)*
- **A6** Default suite 100% offline & green; gated manual smoke executed once pre-merge with structural-only assertions. *(T6/T7)*

---

## 10. Open items for spec review
- Server-side `max_requests` default value (proposed conservative; confirm number).
- Smoke harness form: standalone `scripts/live_smoke_*.py` vs an `unittest` `skipUnless(env)` test (proposed: a script + a skipUnless test wrapper).
- Distinct run-status reason strings surfaced to the UI (proposed set in §4).

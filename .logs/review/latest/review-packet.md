# Review Packet — G2d-1 Prompt Configuration MVP (Backend)

## 1. Metadata

- Plan: `docs/harness/plans/2026-06-04--g2d-prompt-configuration-mvp-plan.md`
- Spec: `docs/superpowers/specs/2026-06-04-g2d-prompt-configuration-design.md`
- Implementer: Claude Code (superpowers executing-plans, inline)
- Date: 2026-06-04
- Branch: `feat/g2d-prompt-configuration`
- Base: `main`
- PR: https://github.com/liaoszong/Werewolf-agent/pull/39
- Verdict target: G2d-1 backend config layer only

## 2. Changed Files

`git diff --name-only main` (code/docs/packet/tree):

```
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
README.md
docs/ROADMAP.md
docs/TASKS.md
docs/harness/plans/2026-06-04--g2d-prompt-configuration-mvp-plan.md
docs/superpowers/specs/2026-06-04-g2d-prompt-configuration-design.md
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/observer_server.py
src/werewolf_eval/profile_config.py
tests/test_observer_protocol.py
tests/test_observer_server.py
tests/test_profile_config.py
```

## 3. Diff Stat

`git diff --stat main` → 13 files changed, +2861 / -267.
Key: `profile_config.py` +314 (new), `observer_server.py` +165, `observer_protocol.py` +51, `tests/test_profile_config.py` +182 (new), `tests/test_observer_server.py` +125, `tests/test_observer_protocol.py` +42.

## 4. Diff Check

`git diff --check main` → no output except Windows CRLF conversion warning for `tests/test_observer_server.py`. `DIFF_CHECK = PASS`.

## 5. Allowed Files Check

All 13 changed paths are in the plan allowlist (impl + tests + §2A route docs + spec/plan + review packet + tree). `ALLOWLIST_CHECK = PASS`.

## 6. Forbidden Patterns Check

`FORBIDDEN_SCOPE_CHECK = PASS` (no game_engine / fake runtime / scoring / provider / route-product-doc / generated-fixture changes).
`FORBIDDEN_PATTERN_CHECK = PASS` with two safe negative-test fixtures:

```
SAFE_TEST_MARKER_HITS:
- tests/test_profile_config.py: provider = "openai"   (test_rejects_disallowed_provider — asserts rejection)
- tests/test_profile_config.py: prompt = "...sk-ABCDEF0123456789TOKEN"  (test_rejects_secret_like_value_in_prompt — asserts rejection)
```

No real credentials, no live-provider imports, no `QProcess`/`file://`/PySide/PyQt.

## 7. Dependency / Import Diff

`DEPENDENCY_DIFF_CHECK = PASS` — no changes to `pyproject.toml`/`requirements.txt`/lockfiles.
`RISKY_IMPORT_CHECK = PASS` — `profile_config.py` is stdlib-only (`hashlib`, `json`, `re`, `pathlib`, `typing`); `observer_server.py` adds only intra-package imports (`profile_config`, `redact_secret_values`, `parse_profile_launch_request`) + stdlib `re`.

## 8. Test Summary

| Command | Result |
|---------|--------|
| `python -m unittest tests.test_profile_config` | **OK** — 22 tests |
| `python -m unittest tests.test_observer_protocol` | **OK** — 48 tests (39 prior + 9 new) |
| `python -m unittest tests.test_profile_config tests.test_observer_protocol` | **OK** — 70 tests |
| `python -m unittest tests.test_observer_server -v` | **OK** — 47 tests |
| `python -m unittest discover -s tests -p "test_*.py"` | 426 tests; 1 pre-existing unrelated failure (see below), 0 errors |
| `python -m compileall src tests` | **0 failures** |
| offline functional check (profile launch → fake run → `resolved-profile.json`) | **PASS** (92 runtime events, 11 snapshots, 6 seats, declared p3=deepseek, execution_mode=fake, no path leak) |

**Server-test status:** localhost loopback now works in this environment (`minimal http.server` returned `b'ok'`), and the full server suite passes. A follow-up fix removed a duplicate G2d-local `_wait_for_status` helper that shadowed the existing helper and broke one pre-existing server test's `timeout_s=` call.

**Pre-existing unrelated failure (documented):** `test_context_budget.ContextBudgetGateDocsTests.test_agents_documents_context_budget_gate` fails because `AGENTS.md` lacks "Context Budget Gate" strings. Proof it is pre-existing: `git diff main...HEAD -- AGENTS.md` is empty; `git show main:AGENTS.md | grep -c "Context Budget Gate"` = 0. Not touched by G2d.

## 9. Key Hunks

- `profile_config.py:19-77` — constants (`PROFILE_SCHEMA_VERSION`, allowlists, `_VALUE_SECRET_MARKERS`).
- `profile_config.py:88-117` — `_reject_secret_like_keys` + `_reject_secret_like_values` (keys+values gate).
- `profile_config.py:173-216` — `validate_profile` (9 rules incl. post-merge coherence).
- `profile_config.py:219-256` — `resolve_profile` + `build_resolved_profile_artifact` (execution_mode=fake, hashed prompts).
- `profile_config.py:258-313` — `load_profile` (basename-only errors), `save_profile`, `list_profiles`.
- `observer_protocol.py:27-36` — `ALLOWED_ARTIFACTS` += `resolved-profile.json`.
- `observer_protocol.py:341-391` — `parse_profile_launch_request` (exactly-one-source, type-checked).
- `observer_server.py:185-210` — `GET /api/profiles`, `GET /api/profiles/{name}`.
- `observer_server.py:320-411` — `_launch_run_async` + `_handle_profile_launch` (profile-bound launcher).
- `observer_server.py:413-435` — `POST /api/runs` profile routing + `POST /api/profiles/validate`.
- `tests/test_profile_config.py` — 22 unit tests; `tests/test_observer_server.py` `ObserverServerProfileTests` — 10 server tests incl. non-leak.

## 10. Evidence Map

| Acceptance | Evidence | Status |
|------------|----------|--------|
| A1 module + schema | `profile_config.py:19,173,219,229`; `test_profile_config` (22) | PASS |
| A2 three endpoints | `observer_server.py:185,190,422`; `ObserverServerProfileTests.test_list_profiles/get_profile/validate_*` | PASS |
| A3 launch from profile | `observer_server.py:341`; `test_launch_from_named/inline`; offline func check | PASS |
| A4 resolved-profile.json | `profile_config.py:229`; `ProfileArtifactTests`; offline func check | PASS |
| A5 validation rejects | `profile_config.py:173`; `ProfileValidationTests` (keys+values, coherence) | PASS |
| A6 template path unchanged | `observer_server.py:413` (routes only on profile/profile_name); `_launch_run_async` preserves template 202 | PASS |
| A7 no providers/deps/engine | §6/§7 checks; FORBIDDEN_SCOPE_OK; DEP_MANIFEST_OK | PASS |
| A8 tests pass/documented | §8 (70 focused OK; 47 server OK; 1 pre-existing failure proven) | PASS |
| A9 exactly-one-source | `observer_protocol.py:341`; `ProfileLaunchRequestTests` (both/neither/template/non-string) | PASS |
| A10 route docs aligned | `ROADMAP.md:255`, `README.md:31`, `TASKS.md:84,217,225` (G2c completed, G2d active) | PASS |

## 11. Acceptance Checklist

- [x] A1 `profile_config.py` schema `g2d.profile.v1` + validate/resolve/artifact/persist
- [x] A2 `/api/profiles`, `/api/profiles/{name}`, `/api/profiles/validate`
- [x] A3 `POST /api/runs` inline/named profile launch writes `resolved-profile.json`
- [x] A4 artifact records declared config + `execution_mode=fake`/`live_api=not_used`; no secrets/paths
- [x] A5 validation rejects bad schema/role/provider/model/strategy/name/extra/secret-keys/secret-values/incoherence
- [x] A6 template launch + G2a/G2c endpoints unchanged
- [x] A7 no live providers / new deps / engine / runtime changes
- [x] A8 focused tests pass; server tests pass; pre-existing failure proven
- [x] A9 `parse_profile_launch_request` exactly-one-source
- [x] A10 route docs mark G2c completed, G2d active

## 12. Implementer Risk Notes

- Server HTTP tests now pass locally. The suite emits ResourceWarning messages for unclosed sockets in existing SSE/server tests, but exits OK.
- `_launch_run_async` is a behavior-preserving extraction of the existing inline template-launch thread; the template 202 shape is unchanged.
- Declared-vs-executed split: profiles may declare `deepseek` provider/model, but execution stays fake-deterministic and `resolved-profile.json` marks `execution_mode=fake`/`live_api=not_used`. No live calls, no API keys.
- Secret gate is two walkers (keys broad, values narrow credential-markers) — generic prompt words like "secret" pass; prompts are hashed, never stored verbatim.

## 13. Review Trigger Result

```
PACKET_TOO_LARGE = NO
POTENTIAL_CODEX_B_DEEP_REVIEW_TRIGGER = YES (changed files = 11 > 8)
CHANGED_FILES_COUNT = 13
CHANGED_LINES = +2861 / -267
B_DEEP_REVIEW_RANGES =
  src/werewolf_eval/profile_config.py:88-313 (validation/secret-gate/artifact/persist)
  src/werewolf_eval/observer_server.py:185-435 (endpoints + profile launcher)
  src/werewolf_eval/observer_protocol.py:341-391 (launch parser)
  tests/test_observer_server.py ObserverServerProfileTests (server behavior to verify in normal env)
```

`profile_config.py` = 314 lines (< 350 trigger). `observer_server.py` change is additive (no unrelated endpoint behavior touched). No forbidden-scope changes.

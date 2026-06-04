# G2d-1 Prompt Configuration MVP (Backend) — Design Spec

- **Date:** 2026-06-04
- **Status:** Approved design — pending implementation plan
- **Roadmap item:** G2d Prompt Configuration MVP (charter Phase F)
- **Slice:** G2d-1 (backend config layer + observer endpoint). The Qt setup wizard is deferred to a later slice (G2d-2).
- **Author:** brainstormed via superpowers:brainstorming

---

## 1. Goal

Make match configuration **reusable, validated, and auditable** through a controlled JSON profile surface, without a UI and without live provider calls. A user (or test) can drop a profile JSON into a `profiles/` directory, list and validate it through the observer protocol, and launch a deterministic fake run whose **declared** per-seat provider / model / prompt / strategy is recorded in an auditable `resolved-profile.json` artifact — while execution stays fake-deterministic.

This mirrors the established platform pattern: G2a added a protocol/control-plane layer, G2c added a server-side visibility projection layer; G2d-1 adds a server-side **profile configuration layer**. Each is a pure Python helper module plus narrow observer endpoints plus tests, with no Qt and no third-party dependencies.

## 2. Locked decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Slice scope | Backend config layer + observer endpoint; **no Qt UI** | Mirrors the proven G2a→G2b split; focused, fully `unittest`-able. |
| D2 | Profile file format | **JSON** (stdlib `json`) | Platform has a strict no-third-party-dependency rule; YAML needs PyYAML. JSON matches every existing artifact (events.jsonl, snapshots, prompt-manifest). |
| D3 | Provider/model handling | **Declare-only allowlist, execute fake** | Live API calls are forbidden this milestone. Profiles declare provider/model/prompt/strategy from an allowlist; the run records the declared config with `execution_mode="fake"` / `live_api="not_used"`. No secrets, no live calls. |
| D4 | Persistence / API surface | **Read `profiles/` dir + inline launch** | Server only *reads* profiles (list/get/validate) and launches from inline-or-named profiles. No client-driven server file writes → no write-path security surface. "Save" is a pure Python helper. |
| D5 | Launch integration | **Approach A — companion `resolved-profile.json` artifact** | A profile-bound launcher closure runs the existing fake runtime untouched (execution truth = fake), then writes a separate `resolved-profile.json` (declared config). Zero changes to `game_engine.py` / `run_g1h_fake_runtime.py`; explicit declared-vs-executed separation; reuses the `ObserverServerState.launcher` seam. |

## 3. Context anchors (current code)

- `build_default_config()` (`src/werewolf_eval/game_engine.py:91`) fixes the canonical 6-player layout: `p1,p2 = werewolf`, `p3 = seer`, `p4 = witch`, `p5,p6 = villager`. Role multiset = `2 werewolf / 1 seer / 1 witch / 2 villager`; teams: `werewolf→werewolf`, `seer/witch/villager→villager`.
- `build_prompt_manifest(run_id, source_label, agents)` (`src/werewolf_eval/runtime_events.py:522`) records resolved per-seat config and hashes prompt text via `_hash_prompt_text` (`runtime_events.py:517`); `redact_secret_values` strips secret-like fields.
- The fake runtime currently hardcodes `provider="fake_deterministic"`, `model="none"` per seat (`run_g1h_fake_runtime.py:166-178`).
- `ObserverServerState.launcher` (`observer_server.py:55`) is a `(run_id, run_dir) -> int` callable invoked per run inside `POST /api/runs` (`observer_server.py:280-326`). Default is `default_fake_launcher` (`observer_server.py:48`).
- `parse_launch_request()` (`observer_protocol.py:301`) validates `{template, run_id, mode}` against `ALLOWED_TEMPLATES` (`observer_protocol.py:20`, includes `default_6p_fake`).
- `ALLOWED_ARTIFACTS` (`observer_protocol.py:27`) gates which run artifacts the registry lists and serves; `build_artifact_registry` (`observer_protocol.py:202`) and `artifact_path` (`observer_protocol.py:131`) read from it.

## 4. Architecture

```
                 profiles/<name>.json   (user/test drops a file = "import")
                          │
        ┌─────────────────┴───────────────────────────────┐
        ▼                                                  ▼
  GET /api/profiles                          POST /api/runs {profile | profile_name}
  GET /api/profiles/{name}                     │ parse_profile_launch_request
  POST /api/profiles/validate                  │ validate_profile + resolve_profile
        │                                       │ run_dir created, status=queued
        ▼                                       ▼
   profile_config.py  ◀── pure ──▶  profile-bound launcher closure (per run)
   (schema, validate,                  ├─ base fake launcher runs deterministic game
    resolve, artifact,                 │    → events / snapshots / prompt-manifest  (EXECUTION = fake)
    load/save/list)                    └─ build_resolved_profile_artifact
                                            → resolved-profile.json                 (DECLARED config)
                                                       │
                          GET /api/runs/{id}/artifacts/resolved-profile.json
```

The profile layer is a pure module. The server owns endpoints and the launcher closure. The game engine and fake runtime are untouched.

## 5. Components

### 5.1 `src/werewolf_eval/profile_config.py` (NEW — pure: no networking, engine, or Qt imports)

**Constants**
- `PROFILE_SCHEMA_VERSION = "g2d.profile.v1"`
- `ALLOWED_PROVIDERS: frozenset[str]` — e.g. `{"fake_deterministic", "deepseek"}` (declarable; only `fake_deterministic` executes).
- `ALLOWED_MODELS: dict[str, frozenset[str]]` — per-provider model allowlist, e.g. `{"fake_deterministic": {"none"}, "deepseek": {"deepseek-chat", "deepseek-reasoner"}}`.
- `ALLOWED_STRATEGIES: frozenset[str]` — e.g. `{"default", "aggressive", "cautious"}`.
- `ALLOWED_ROLES: frozenset[str]` = `{"werewolf", "seer", "witch", "villager"}`.
- `CANONICAL_DEFAULT_6P_ROLES: dict[str, int]` = `{"werewolf": 2, "seer": 1, "witch": 1, "villager": 2}`.
- `ROLE_TEAMS: dict[str, str]` = `{"werewolf": "werewolf", "seer": "villager", "witch": "villager", "villager": "villager"}`.
- `DEFAULT_SEAT_IDS: tuple[str, ...]` = `("p1", ..., "p6")`.
- `PROMPT_MAX_LEN = 8000` (reject pathologically large prompt blobs).

**Errors**
- `class ProfileValidationError(ValueError)` — raised on any invalid profile.

**Profile schema (`g2d.profile.v1`)**
```json
{
  "schema_version": "g2d.profile.v1",
  "name": "my_profile",
  "template": "default_6p_fake",
  "role_defaults": {
    "werewolf":  {"provider": "fake_deterministic", "model": "none", "prompt": "...", "strategy": "default"},
    "seer":      {"provider": "fake_deterministic", "model": "none", "prompt": "...", "strategy": "default"},
    "witch":     {"provider": "fake_deterministic", "model": "none", "prompt": "...", "strategy": "default"},
    "villager":  {"provider": "fake_deterministic", "model": "none", "prompt": "...", "strategy": "default"}
  },
  "seat_overrides": {
    "p3": {"model": "deepseek-chat", "prompt": "...seat-specific...", "strategy": "cautious"}
  }
}
```
- `role_defaults` keys must cover every role present in the template's layout.
- `seat_overrides` is optional; each key is a seat ID; each value is a partial config that overrides that seat's role default.
- A seat-override value may not change a seat's **role** (role layout is fixed by the template); it may only override `provider` / `model` / `prompt` / `strategy`.

**Public functions**
- `validate_profile(profile: dict) -> None` — raises `ProfileValidationError` on the first failure (message lists the problem). Rules in §6.
- `resolve_profile(profile: dict) -> list[dict]` — returns resolved seat configs `[{player_id, role, team, provider, model, prompt, strategy}, ...]` for every seat in template order. The **seat→role mapping comes from the template's canonical layout** (for `default_6p_fake`: p1,p2=werewolf, p3=seer, p4=witch, p5,p6=villager — see §3), not from the profile; `team` is derived via `ROLE_TEAMS`. For each seat: start from `role_defaults[role]`, then apply `seat_overrides[player_id]` (if any). Assumes a validated profile.
- `build_resolved_profile_artifact(profile: dict, run_id: str) -> dict` — returns the `resolved-profile.json` content:
  ```json
  {
    "schema_version": "g2d.profile.v1",
    "run_id": "<run_id>",
    "profile_name": "<name>",
    "template": "default_6p_fake",
    "execution_mode": "fake",
    "live_api": "not_used",
    "secrets_redacted": true,
    "seats": [
      {"player_id":"p1","role":"werewolf","team":"werewolf","provider":"fake_deterministic","model":"none","strategy":"default","prompt_hash":"<sha256>"}
    ]
  }
  ```
  Prompt text is **hashed** (reuse `_hash_prompt_text`) and never stored verbatim; `redact_secret_values` is applied to the whole artifact.
- `load_profile(path: Path) -> dict` — read + parse a profile JSON file; raises `ProfileValidationError` on malformed JSON.
- `save_profile(profile: dict, profiles_dir: Path) -> Path` — validate, then write `<profiles_dir>/<safe_name>.json`. The filename is derived from `name` through a path-safety check (reuse the existing `_SAFE_NAME_RE` / `validate_run_id` style); never escapes `profiles_dir`. **This is a pure module helper for tests, scripts, and the future G2d-2 UI — it is NOT wired to any server write endpoint this slice** (per D4, the server only reads profiles).
- `list_profiles(profiles_dir: Path) -> list[dict]` — return per-file metadata `[{name, template, valid, error?}]`; a malformed file is reported `valid: false` with a short reason and never raises.

### 5.2 `src/werewolf_eval/observer_protocol.py` (MODIFY — minimal)

- Add `"resolved-profile.json"` to `ALLOWED_ARTIFACTS` so the run artifact registry lists and serves it.
- Add `parse_profile_launch_request(payload: dict) -> dict` — accepts either:
  - `{"profile": { ...inline profile... }, "run_id"?: "...", "mode"?: "fake"}`, or
  - `{"profile_name": "my_profile", "run_id"?: "...", "mode"?: "fake"}`.
  It validates `mode` against `ALLOWED_MODES`, validates/normalizes `run_id` (reusing `validate_run_id` / `generate_run_id`), and path-checks `profile_name`. It does **not** itself read the file (the server resolves the directory); it returns a normalized `{kind: "inline"|"named", profile|profile_name, run_id, mode}`.
- The existing `parse_launch_request` template path is unchanged.

### 5.3 `src/werewolf_eval/observer_server.py` (MODIFY)

- `ObserverServerState` gains `profiles_dir: Path` (default: `runs_dir.parent / "profiles"`, created lazily; configurable for tests).
- New GET endpoints:
  - `GET /api/profiles` → `{ "profiles": [ {name, template, valid, error?} ] }` from `list_profiles`.
  - `GET /api/profiles/{name}` → the profile content (validated, `redact_secret_values` applied); `404` if missing, `400` if unsafe name, `400 invalid_profile` if on-disk profile fails validation.
  - `POST /api/profiles/validate` → body is an inline profile → `{ "valid": bool, "errors": [..], "resolved_seats": [..] }` (HTTP `200` even when invalid; `valid` carries the verdict).
- Extend `POST /api/runs`:
  - If the body contains `profile` or `profile_name`, route through `parse_profile_launch_request`; load the named profile from `profiles_dir` if needed; `validate_profile`; on failure return `400 invalid_profile`. On success, build a **profile-bound launcher closure**:
    ```python
    def _profile_launcher(run_id, run_dir, *, base=state.launcher, profile=profile):
        code = base(run_id, run_dir)            # runs the deterministic fake game
        artifact = build_resolved_profile_artifact(profile, run_id)
        _write_json(run_dir / "resolved-profile.json", artifact)
        return code
    ```
    and use it instead of `state.launcher` for this run's thread. The `202` response echoes `{run_id, profile_name, mode, status}`.
  - If the body contains neither `profile` nor `profile_name`, the existing template path runs unchanged.
- `resolved-profile.json` is served by the existing artifact endpoints (no new per-artifact handler needed) because it is now in `ALLOWED_ARTIFACTS`.

### 5.4 Tests

- `tests/test_profile_config.py` (NEW) — pure-module tests (see §9).
- `tests/test_observer_server.py` (MODIFY) — profile endpoints + launch-from-profile integration + non-leak/no-absolute-path checks.

## 6. Validation rules (`validate_profile`)

A profile is rejected (`ProfileValidationError`) unless **all** hold:

1. Top-level is a JSON object with exactly the keys `{schema_version, name, template, role_defaults, seat_overrides?}` — no extra keys.
2. `schema_version == "g2d.profile.v1"`.
3. `name` is a non-empty path-safe string (matches the existing safe-name regex; no `/`, `\`, `..`, control chars).
4. `template` is in `ALLOWED_TEMPLATES` (currently `default_6p_fake`).
5. `role_defaults` covers exactly the roles in the template layout (`werewolf, seer, witch, villager`); each value has keys ⊆ `{provider, model, prompt, strategy}` with `provider`, `model`, `strategy` required.
6. For each role default: `provider ∈ ALLOWED_PROVIDERS`; `model ∈ ALLOWED_MODELS[provider]`; `strategy ∈ ALLOWED_STRATEGIES`; `prompt` is a string with `len ≤ PROMPT_MAX_LEN`.
7. The resolved role multiset equals `CANONICAL_DEFAULT_6P_ROLES` (the template's fixed layout). Seat roles come from the template, not the profile, so this is enforced by construction; the validator additionally rejects any attempt to set a seat `role`.
8. `seat_overrides` (if present) keys ⊆ `DEFAULT_SEAT_IDS`; each value has keys ⊆ `{provider, model, prompt, strategy}` (no `role`); overridden provider/model/strategy/prompt obey the same allowlists/limits as rule 6.
9. No secret-like fields anywhere: reject keys matching the existing secret patterns (`api_key`, `api-key`, `authorization`, `token`, `bearer`, etc.) and reject string values that look like credentials (reuse the `redact_secret_values` / secret-marker detection already in the codebase).

`POST /api/profiles/validate` returns the full error list (collect-all mode) for UX, while module-internal `validate_profile` may raise on first failure; the endpoint wraps it to gather messages.

## 7. Data flow (launch-from-profile)

1. Client `POST /api/runs` with `{"profile_name": "my_profile"}` (or inline `{"profile": {...}}`).
2. Server resolves `profiles_dir/my_profile.json`, `load_profile`, `validate_profile`. Invalid → `400 invalid_profile`.
3. `run_dir` created, status `queued`→`running`.
4. Thread: base fake launcher runs the deterministic game → writes `events.jsonl`, snapshots, `prompt-manifest.json` (execution truth = fake).
5. Then `build_resolved_profile_artifact(profile, run_id)` → `resolved-profile.json` (declared config, `execution_mode="fake"`, `live_api="not_used"`, prompts hashed).
6. Status `completed`.
7. `GET /api/runs/{id}/artifacts` lists `resolved-profile.json`; `GET /api/runs/{id}/artifacts/resolved-profile.json` serves the declared per-seat config.

The G2c projection endpoints continue to work against the run's events/snapshots unchanged.

## 8. Error handling

| Condition | Response |
|-----------|----------|
| Invalid profile (inline or named) on launch | `400 invalid_profile` + message |
| Inline profile fails `POST /api/profiles/validate` | `200` with `{valid:false, errors:[...]}` |
| Unknown `profile_name` | `404 not_found` |
| Unsafe `profile_name` (traversal/illegal chars) | `400 invalid_request` |
| Malformed profile file in `list_profiles` | listed with `valid:false`, never raises |
| Secrets in a profile | rejected by validation; never written to any artifact |
| Any response | no absolute local paths, no secret values |
| Existing template launch + all G2a/G2c endpoints | unchanged |

## 9. Testing strategy

**Pure module — `tests/test_profile_config.py`** (handcrafted profiles under `TemporaryDirectory()`):
- valid profile passes; resolution applies role defaults then seat overrides in seat order;
- rejects: wrong `schema_version`, extra top-level keys, bad `template`, missing role default, seat override setting `role`, seat ID outside p1–p6, provider/model/strategy outside allowlist, oversized prompt, secret-like key/value;
- role multiset enforcement matches `CANONICAL_DEFAULT_6P_ROLES`;
- `build_resolved_profile_artifact` shape: has `execution_mode="fake"`, `live_api="not_used"`, `secrets_redacted=true`, prompt **hashed not stored**, no absolute paths;
- `save_profile`/`load_profile` round-trip; `save_profile` rejects unsafe names; `list_profiles` reports malformed files as `valid:false`.

**Server — `tests/test_observer_server.py`** (extends existing suite):
- `GET /api/profiles` lists dropped profiles; `GET /api/profiles/{name}` returns redacted content; `POST /api/profiles/validate` returns verdict + resolved seats;
- launch-from-profile (inline and named) yields a `completed` run whose `resolved-profile.json` records declared provider/model/prompt/strategy + `execution_mode=fake`;
- `400` on invalid profile launch; `404` on unknown name; `400` on unsafe name;
- response text contains no temp-dir absolute path and no secret markers; `live_api` never indicates a live call.

> **Environmental note:** the local HTTP-server test suite (`tests/test_observer_server.py`) cannot complete in the current sandbox — a minimal 5-line `http.server` round-trip fails with `RemoteDisconnected` here, affecting every server test on any branch (confirmed against the pre-existing G2a `/health` test). Server tests are still authored and pass in a normal environment; results are documented the same way G2c's plan handles it (Task 7 Step 5: record exact failing names + proof of environmental cause + passing pure-module evidence).

## 10. Boundaries — non-goals this slice

- No Qt/Web UI, no setup wizard (→ G2d-2).
- No live provider calls, API keys, credentials, or secret handling.
- No changes to `game_engine.py`, `run_g1h_fake_runtime.py`, `provider_agent.py`, scoring, attribution, validators unrelated to the observer protocol.
- No changes to route docs (`README.md`, `docs/ROADMAP.md`, `docs/TASKS.md`, `docs/PRODUCT_ONE_PAGER.md`).
- No client-driven server-side profile **writes** (save is a pure helper / file-drop).
- No new third-party dependencies; Python standard library only.

## 11. Allowlist (files this slice may touch)

```
src/werewolf_eval/profile_config.py          (new)
src/werewolf_eval/observer_protocol.py        (ALLOWED_ARTIFACTS + parse_profile_launch_request)
src/werewolf_eval/observer_server.py          (profile endpoints + profile-bound launcher)
tests/test_profile_config.py                  (new)
tests/test_observer_server.py                 (profile endpoint + launch tests)
docs/superpowers/specs/2026-06-04-g2d-prompt-configuration-design.md  (this spec)
.oh-my-harness/tree.md                         (refresh via tree hook only)
```

## 12. Acceptance criteria (high level — to be expanded in the implementation plan)

- A1. A pure `profile_config.py` module with schema version `g2d.profile.v1`, validation, resolution, and resolved-profile artifact builder.
- A2. `GET /api/profiles`, `GET /api/profiles/{name}`, `POST /api/profiles/validate` exist and behave per §5.3.
- A3. `POST /api/runs` launches a fake run from an inline or named profile and writes `resolved-profile.json`.
- A4. `resolved-profile.json` records declared per-seat provider/model/prompt(hash)/strategy + `execution_mode="fake"` / `live_api="not_used"`; contains no secrets or absolute paths.
- A5. Validation rejects bad schema, bad role layout, disallowed provider/model/strategy, unsafe names, secret-like fields, and extra keys.
- A6. The template launch path and all G2a/G2c endpoints are unchanged.
- A7. No live providers, no new dependencies, no changes to the game engine / fake runtime / route docs.
- A8. Pure-module tests pass; server tests pass in a normal environment or are documented with the exact environmental limitation.

## 13. Future (out of scope, noted for continuity)

- **G2d-2:** Qt setup wizard consuming `/api/profiles` + `POST /api/runs {profile}`, provider/model/prompt/strategy pickers, save/import UI.
- **G3+:** experiment profiles (batches of profiles), live provider execution behind authenticated, secret-safe adapters.

# G2d-1 Prompt Configuration MVP (Backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a server-side profile configuration layer so matches can be launched from reusable, validated JSON profiles whose declared per-seat provider/model/prompt/strategy is recorded in an auditable `resolved-profile.json` artifact — while execution stays fake-deterministic and no live providers, secrets, or Qt UI are introduced.

**Architecture:** A pure `profile_config.py` module (schema, validation, resolution, resolved-profile artifact, save/load/list) plus three observer endpoints (`GET /api/profiles`, `GET /api/profiles/{name}`, `POST /api/profiles/validate`) and a profile-bound launcher closure wired into `POST /api/runs`. The game engine and fake runtime are untouched; the launcher closure runs the existing fake run, then writes the declared config as a separate artifact (Approach A). Mirrors the G2a/G2c pattern: pure helper module + narrow endpoints + tests.

**Tech Stack:** Python standard library only (`json`, `hashlib`, `re`, `pathlib`, `unittest`), existing G2a stdlib HTTP server. No new third-party dependencies, no provider API calls, no Qt.

**Spec:** `docs/superpowers/specs/2026-06-04-g2d-prompt-configuration-design.md` (approved).

---

## Route Authority

This plan is authorized by the approved spec `docs/superpowers/specs/2026-06-04-g2d-prompt-configuration-design.md`. The canonical route docs still list G2c as the next candidate even though G2c is merged (commits `8b81fe6`…`2a3f08a`); **Task 1 corrects that** before any code lands. Until Task 1 completes, treat this committed spec as the route-of-record for G2d-1.

---

## Context Basis

Verified facts (current `main` / branch `feat/g2d-prompt-configuration`):

- `src/werewolf_eval/game_engine.py:91` `build_default_config()` fixes the canonical layout p1,p2=werewolf, p3=seer, p4=witch, p5,p6=villager (multiset 2/1/1/2).
- `src/werewolf_eval/runtime_events.py:522` `build_prompt_manifest()` records resolved per-seat config; `runtime_events.py:517` `_hash_prompt_text()` hashes prompts; `runtime_events.py:96` `redact_secret_values()` recurses on **values only** (it preserves dict keys).
- `src/werewolf_eval/observer_server.py:48` `default_fake_launcher`, `:53` `ObserverServerState(runs_dir, launcher, …)`, `:407` `create_observer_server(host, port, runs_dir, launcher=None)`; `POST /api/runs` handler at `:283`; helpers `_send_json`, `_send_error_json`, `_read_json_body`, `_get_state`, `_set_status`, `_set_error`, `_path_segments`; `do_POST` wraps handlers in `except ObserverProtocolError → 400` (`:330`).
- `src/werewolf_eval/observer_protocol.py:16` `DEFAULT_FAKE_TEMPLATE="default_6p_fake"`, `:17` `DEFAULT_FAKE_MODE="fake"`, `:23` `ALLOWED_MODES`, `:27` `ALLOWED_ARTIFACTS`, `:59` `_SAFE_NAME_RE`, `:301` `parse_launch_request`, `:340` `generate_run_id`; `validate_run_id`, `ObserverProtocolError` exported; module already imports `uuid`/`re`.
- `tests/test_observer_server.py:44` `_start_server(runs_dir, launcher=None) -> (server, base_url)`; `:59` `_request_json(base_url, path, *, method, payload, headers)`; tests use `setUpClass` + `TemporaryDirectory`.

---

## Scope Summary

G2d-1 includes:

- A pure `profile_config.py` module: schema `g2d.profile.v1`, `validate_profile`, `resolve_profile`, `build_resolved_profile_artifact`, `load_profile`, `save_profile`, `list_profiles`.
- `observer_protocol.py`: add `resolved-profile.json` to `ALLOWED_ARTIFACTS`; add `parse_profile_launch_request` with exactly-one-launch-source enforcement.
- `observer_server.py`: `profiles_dir` state, three profile endpoints, and a profile-bound launcher closure in `POST /api/runs`.
- A minimal route-doc alignment (G2c→completed, G2d→active) in `README.md`, `docs/ROADMAP.md`, `docs/TASKS.md`.
- Unit tests (`test_profile_config.py`), protocol tests (`test_observer_protocol.py`), and server tests (`test_observer_server.py`).

G2d-1 does NOT include:

- Qt/Web UI or setup wizard (deferred to G2d-2).
- Live provider calls, API keys, credentials, or secret handling.
- Changes to the game engine, fake runtime, scoring, attribution, or unrelated validators.
- Server-side client-driven profile writes (save is a pure helper).
- New third-party dependencies.

---

## Profile Contract

### Schema (`g2d.profile.v1`)

```json
{
  "schema_version": "g2d.profile.v1",
  "name": "my_profile",
  "template": "default_6p_fake",
  "role_defaults": {
    "werewolf": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
    "seer":     {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
    "witch":    {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
    "villager": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"}
  },
  "seat_overrides": {
    "p3": {"provider": "deepseek", "model": "deepseek-chat", "prompt": "...", "strategy": "cautious"}
  }
}
```

### Validation rules (enforced by `validate_profile`)

1. Top-level keys ⊆ `{schema_version, name, template, role_defaults, seat_overrides}`; no extras.
2. `schema_version == "g2d.profile.v1"`.
3. `name` matches `_SAFE_NAME_RE` (path-safe).
4. `template ∈ ALLOWED_TEMPLATES` (`default_6p_fake`).
5. `role_defaults` covers exactly `{werewolf, seer, witch, villager}`; each fragment keys ⊆ `{provider, model, prompt, strategy}`, no `role`, with `provider`/`model`/`strategy` required and all values strings.
6. `seat_overrides` keys ⊆ `p1..p6`; each fragment keys ⊆ `{provider, model, prompt, strategy}`, no `role`, values strings.
7. **Secret-like keys AND values rejected** via two dedicated walkers — independent of `redact_secret_values`. Keys: any fragment of `api_key`/`secret`/`token`/`bearer`/`authorization`/`password`/`credential`/`access_key`. Values: a *narrower* credential-marker set (`sk-`, `bearer ` with space, `api_key`, `api-key`, `apikey`, `authorization`, `access_key`, `deepseek_api_key`) so free-text prompts with generic words (e.g. "keep your role secret") still pass.
8. Role multiset == `{werewolf:2, seer:1, witch:1, villager:2}`.
9. **Resolved-seat coherence (post-merge):** each seat resolved (role default ← override) must satisfy `provider ∈ ALLOWED_PROVIDERS`, `model ∈ ALLOWED_MODELS[provider]`, `strategy ∈ ALLOWED_STRATEGIES`, `len(prompt) ≤ PROMPT_MAX_LEN`. A partial override (e.g. `model` alone over a `fake_deterministic` default) is rejected.

Defense-in-depth: `prompt` is hashed (never stored verbatim), provider/model/strategy are allowlisted, and `redact_secret_values` is applied to the output artifact.

### Launch payload (exactly one source)

`POST /api/runs` is a **profile launch** iff the body contains `profile` (inline object) or `profile_name` (string). `parse_profile_launch_request` rejects (`400`): both together, either combined with `template`, neither present, or unexpected keys. Template launches (`{template, mode, run_id}`) keep using `parse_launch_request`.

---

## File Plan

### Create

- `src/werewolf_eval/profile_config.py` — pure profile module (no networking, engine, or Qt).
- `tests/test_profile_config.py` — unit tests for schema/validation/resolution/artifact/persistence.

### Modify

- `src/werewolf_eval/observer_protocol.py` — `ALLOWED_ARTIFACTS` += `resolved-profile.json`; add `parse_profile_launch_request`.
- `src/werewolf_eval/observer_server.py` — `profiles_dir` state, profile endpoints, profile-bound launcher, `_launch_run_async` refactor.
- `tests/test_observer_protocol.py` — launch-payload + artifact-allowlist tests.
- `tests/test_observer_server.py` — profile endpoint + launch-from-profile + non-leak tests; extend `_start_server`.
- `README.md`, `docs/ROADMAP.md`, `docs/TASKS.md` — minimal G2c-completed / G2d-active alignment (Task 1 only).
- `.oh-my-harness/tree.md` — refresh via tree hook only.

### Do Not Modify

- `src/werewolf_eval/game_engine.py`, `run_g1h_fake_runtime.py`, `provider_agent.py`, `scoring.py`, `score_game.py`, `attribution.py`.
- `docs/PRODUCT_ONE_PAGER.md`, `docs/adr/**`, charter/designs, `docs/demo/**`, `docs/generated-games/**`, `docs/gold-game/**`, `.github/**`, `.agents/skills/**`.
- Dependency manifests (`pyproject.toml`, `requirements.txt`, lockfiles).

---

## Allowlist

Implementation may change only these paths:

```text
src/werewolf_eval/profile_config.py
src/werewolf_eval/observer_protocol.py
src/werewolf_eval/observer_server.py
tests/test_profile_config.py
tests/test_observer_protocol.py
tests/test_observer_server.py
README.md
docs/ROADMAP.md
docs/TASKS.md
docs/harness/plans/2026-06-04--g2d-prompt-configuration-mvp-plan.md
docs/superpowers/specs/2026-06-04-g2d-prompt-configuration-design.md
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

`README.md`, `docs/ROADMAP.md`, `docs/TASKS.md` are allowed **only** for the Task 1 status flip. `.logs/review/latest/review-packet.md` is allowed only for the Task 6 review packet (the file is git-tracked despite `.gitignore`). `.oh-my-harness/tree.md` is allowed only if refreshed by `node .codex/hooks/tree.mjs --force`.

## Forbidden Scope

Implementation must not: modify the game engine / fake runtime / scoring / attribution; add live provider calls, API keys, or secret handling; add Qt/Web/Electron UI; read local run files from any client; change dependency manifests; or claim G2d-2 / G3 / G4 completion.

---

## Task 1: Route alignment (G2c completed, G2d active)

**Files:**

- Modify: `docs/ROADMAP.md`, `README.md`, `docs/TASKS.md`

- [ ] **Step 1: Update ROADMAP Current Priority**

In `docs/ROADMAP.md`, find the *Current Priority* line:

```text
G1h Live Runtime Event Spine, G2a Local Observer Server / Protocol Control Plane, and G2b Qt Observer Cockpit MVP are now `completed`. The next implementation candidate is G2c God View / Role View.
```

Replace with:

```text
G1h Live Runtime Event Spine, G2a Local Observer Server / Protocol Control Plane, G2b Qt Observer Cockpit MVP, and G2c God View / Role View are now `completed`. The next implementation candidate is G2d Prompt Configuration MVP.
```

- [ ] **Step 2: Update README route line**

In `README.md`, find:

```text
G-track 后续路线已在 `docs/ROADMAP.md` 固化：G2b Qt Observer Cockpit MVP 已完成，下一候选开发点是 G2c God View / Role View。
```

Replace with:

```text
G-track 后续路线已在 `docs/ROADMAP.md` 固化：G2c God View / Role View 已完成，下一候选开发点是 G2d Prompt Configuration MVP。
```

- [ ] **Step 3a: Fix the stale TASKS.md status summary**

In `docs/TASKS.md`, the summary paragraph (around line 84) ends with a stale "next candidate" clause. Find:

```text
下一候选开发点是 G2b Qt Observer MVP；
```

Replace with:

```text
G2b Qt Observer MVP、G2c God View / Role View 已完成，下一候选开发点是 G2d Prompt Configuration MVP；
```

- [ ] **Step 3b: Insert exact G2c (completed) and G2d (active) entries**

In `docs/TASKS.md`, find the end of the G2b block (its Non-goals line, immediately before the `#### Backlog / prerequisite fix candidate` heading):

```text
- Non-goals：不做 prompt/profile editor，不做 Web observer client，不做 human-vs-AI UI，不做 multi-provider arena，不做 leaderboard，不做 Python runtime 直接绑定，不做本地 artifact 文件读取。

#### Backlog / prerequisite fix candidate：Decision Round Scoring Disambiguation
```

Replace with (insert the two new entries between them — exact text):

```text
- Non-goals：不做 prompt/profile editor，不做 Web observer client，不做 human-vs-AI UI，不做 multi-provider arena，不做 leaderboard，不做 Python runtime 直接绑定，不做本地 artifact 文件读取。

#### G2c：God View / Role View Visibility Trust

- 状态：`completed`（plan 文件 `docs/harness/plans/2026-06-03--g2c-god-role-view-visibility-trust-plan.md`）
- 作用：将 god-view state 与 role-view projection 分离，使隐藏信息在 God/Public/Role/Team 视角下显式、可审计、端到端可执行；通过 G2a protocol 暴露 server-side visibility projection。
- 核心产物：`src/werewolf_eval/observer_visibility.py`、`/api/runs/{run_id}/projection` 端点、`tests/test_observer_visibility.py`、`clients/qt_observer/qml/components/ViewBoundaryBadge.qml` / `ProjectionProofPanel.qml`。
- 依赖：G2a / G2b。
- Non-goals：不做 prompt/profile editor，不做 multi-run experiment system。

#### G2d：Prompt Configuration MVP

- 状态：`active`（spec `docs/superpowers/specs/2026-06-04-g2d-prompt-configuration-design.md`；plan `docs/harness/plans/2026-06-04--g2d-prompt-configuration-mvp-plan.md`）
- 作用：通过受控的 JSON profile surface 配置可复用、可校验、可审计的 role defaults / seat overrides / resolved seat configs，并以 fake-deterministic 执行记录 declared provider/model/prompt/strategy（G2d-1 backend slice，无 Qt UI）。
- 核心产物：`src/werewolf_eval/profile_config.py`、`/api/profiles` / `/api/profiles/{name}` / `/api/profiles/validate` 端点、`POST /api/runs` profile launch + `resolved-profile.json`、`tests/test_profile_config.py`。
- 依赖：G2a / G2c。
- Non-goals：不做 Qt/Web setup UI（留待 G2d-2），不做 live provider calls / API keys / secrets，不做 multi-provider arena，不做 leaderboard，不改 game engine / fake runtime。

#### Backlog / prerequisite fix candidate：Decision Round Scoring Disambiguation
```

- [ ] **Step 4: Verify route docs**

Run:

```powershell
Select-String -Path 'README.md','docs/ROADMAP.md' -Pattern 'G2c.*completed|下一候选开发点是 G2d|candidate is G2d Prompt'
Select-String -Path 'docs/TASKS.md' -Pattern 'G2c|G2d'
```

Expected: ROADMAP/README show G2c completed and G2d as next candidate; TASKS shows a G2c completed entry and a G2d active entry.

- [ ] **Step 5: Commit**

```powershell
git add README.md docs/ROADMAP.md docs/TASKS.md
git commit -m "docs(route): mark G2c completed, G2d active candidate"
```

---

## Task 2: profile_config schema + validation

**Files:**

- Create: `src/werewolf_eval/profile_config.py`
- Test: `tests/test_profile_config.py`

- [ ] **Step 1: Write the failing validation tests**

Create `tests/test_profile_config.py`:

```python
import unittest

from werewolf_eval.profile_config import (
    PROFILE_SCHEMA_VERSION,
    ProfileValidationError,
    validate_profile,
)


def _valid_profile(**overrides):
    base = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "name": "demo",
        "template": "default_6p_fake",
        "role_defaults": {
            "werewolf": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            "seer": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            "witch": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            "villager": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
        },
    }
    base.update(overrides)
    return base


class ProfileValidationTests(unittest.TestCase):
    def test_valid_profile_passes(self):
        validate_profile(_valid_profile())

    def test_valid_profile_with_coherent_override_passes(self):
        validate_profile(_valid_profile(seat_overrides={
            "p3": {"provider": "deepseek", "model": "deepseek-chat", "prompt": "x", "strategy": "cautious"},
        }))

    def test_rejects_bad_schema_version(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(schema_version="wrong"))

    def test_rejects_extra_top_level_key(self):
        p = _valid_profile()
        p["extra"] = 1
        with self.assertRaises(ProfileValidationError):
            validate_profile(p)

    def test_rejects_unknown_template(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(template="nope"))

    def test_rejects_unsafe_name(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(name="../escape"))

    def test_rejects_missing_role_default(self):
        p = _valid_profile()
        del p["role_defaults"]["witch"]
        with self.assertRaises(ProfileValidationError):
            validate_profile(p)

    def test_rejects_seat_override_setting_role(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_overrides={"p3": {"role": "werewolf"}}))

    def test_rejects_unknown_seat_id(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_overrides={"p9": {"strategy": "default"}}))

    def test_rejects_disallowed_provider(self):
        p = _valid_profile()
        p["role_defaults"]["seer"]["provider"] = "openai"
        with self.assertRaises(ProfileValidationError):
            validate_profile(p)

    def test_rejects_incoherent_partial_override(self):
        # model alone over a fake_deterministic provider -> invalid pair
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_overrides={"p3": {"model": "deepseek-chat"}}))

    def test_rejects_oversized_prompt(self):
        p = _valid_profile()
        p["role_defaults"]["seer"]["prompt"] = "x" * 9000
        with self.assertRaises(ProfileValidationError):
            validate_profile(p)

    def test_rejects_secret_like_key_even_with_innocuous_value(self):
        p = _valid_profile()
        p["role_defaults"]["seer"]["api_key"] = "harmless"
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile(p)
        self.assertIn("secret", str(ctx.exception).lower())

    def test_rejects_secret_like_value_in_prompt(self):
        p = _valid_profile()
        p["role_defaults"]["seer"]["prompt"] = "use key sk-ABCDEF0123456789TOKEN"
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile(p)
        self.assertIn("secret", str(ctx.exception).lower())

    def test_allows_generic_word_secret_in_prompt(self):
        # "secret" as a plain game word must NOT be rejected (no credential marker).
        p = _valid_profile()
        p["role_defaults"]["seer"]["prompt"] = "keep your seer role secret"
        validate_profile(p)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_profile_config -v
```

Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'werewolf_eval.profile_config'`.

- [ ] **Step 3: Implement the module (constants + validation)**

Create `src/werewolf_eval/profile_config.py`:

```python
"""G2d profile configuration helpers.

Pure profile schema, validation, resolution, and resolved-profile artifact
helpers for the prompt-configuration MVP.  No networking, no game engine,
no Qt.  Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

PROFILE_SCHEMA_VERSION = "g2d.profile.v1"

ALLOWED_TEMPLATES: frozenset[str] = frozenset({"default_6p_fake"})
ALLOWED_PROVIDERS: frozenset[str] = frozenset({"fake_deterministic", "deepseek"})
ALLOWED_MODELS: dict[str, frozenset[str]] = {
    "fake_deterministic": frozenset({"none"}),
    "deepseek": frozenset({"deepseek-chat", "deepseek-reasoner"}),
}
ALLOWED_STRATEGIES: frozenset[str] = frozenset({"default", "aggressive", "cautious"})
ALLOWED_ROLES: frozenset[str] = frozenset({"werewolf", "seer", "witch", "villager"})
CANONICAL_DEFAULT_6P_ROLES: dict[str, int] = {
    "werewolf": 2,
    "seer": 1,
    "witch": 1,
    "villager": 2,
}
ROLE_TEAMS: dict[str, str] = {
    "werewolf": "werewolf",
    "seer": "villager",
    "witch": "villager",
    "villager": "villager",
}
DEFAULT_6P_SEAT_ROLES: dict[str, str] = {
    "p1": "werewolf",
    "p2": "werewolf",
    "p3": "seer",
    "p4": "witch",
    "p5": "villager",
    "p6": "villager",
}
DEFAULT_SEAT_IDS: tuple[str, ...] = tuple(DEFAULT_6P_SEAT_ROLES)
PROMPT_MAX_LEN = 8000

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,255}$")
_CONFIG_KEYS = frozenset({"provider", "model", "prompt", "strategy"})
_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "secret",
    "token",
    "bearer",
    "password",
    "credential",
    "access_key",
)
# Value markers are intentionally NARROWER than key fragments: they target
# high-confidence credential shapes so free-text prompts (e.g. "keep your role
# secret") are NOT rejected, while real credentials (api keys, bearer tokens)
# are.  No bare "secret"/"token"/"password" here.
_VALUE_SECRET_MARKERS = (
    "sk-",
    "bearer ",
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "access_key",
    "deepseek_api_key",
)


class ProfileValidationError(ValueError):
    """Raised when a profile cannot be validated safely."""


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _reject_secret_like_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if any(frag in str(key).lower() for frag in _SECRET_KEY_FRAGMENTS):
                raise ProfileValidationError(
                    f"secret-like key not allowed: {path}{key}"
                )
            _reject_secret_like_keys(value, f"{path}{key}.")
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _reject_secret_like_keys(item, f"{path}{index}.")


def _reject_secret_like_values(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            _reject_secret_like_values(value, f"{path}{key}.")
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _reject_secret_like_values(item, f"{path}{index}.")
    elif isinstance(obj, str):
        lowered = obj.lower()
        if any(marker in lowered for marker in _VALUE_SECRET_MARKERS):
            raise ProfileValidationError(
                f"secret-like value not allowed at {path.rstrip('.')}"
            )


def _template_seat_roles(template: str) -> dict[str, str]:
    if template == "default_6p_fake":
        return dict(DEFAULT_6P_SEAT_ROLES)
    raise ProfileValidationError(f"unknown template: {template!r}")


def _check_fragment(fragment: object, *, where: str, required: bool) -> None:
    if not isinstance(fragment, dict):
        raise ProfileValidationError(f"{where} must be an object")
    if "role" in fragment:
        raise ProfileValidationError(f"{where} may not set 'role'")
    extra = set(fragment) - _CONFIG_KEYS
    if extra:
        raise ProfileValidationError(f"{where} has unexpected keys: {sorted(extra)}")
    if required:
        for field_name in ("provider", "model", "strategy"):
            if field_name not in fragment:
                raise ProfileValidationError(f"{where} missing {field_name!r}")
    for field_name, value in fragment.items():
        if not isinstance(value, str):
            raise ProfileValidationError(f"{where}.{field_name} must be a string")
    prompt = fragment.get("prompt")
    if isinstance(prompt, str) and len(prompt) > PROMPT_MAX_LEN:
        raise ProfileValidationError(f"{where}.prompt exceeds {PROMPT_MAX_LEN} chars")


def _resolve_seat(profile: dict, seat: str, role: str) -> dict[str, Any]:
    base = dict(profile["role_defaults"][role])
    override = dict(profile.get("seat_overrides", {}).get(seat, {}))
    merged = {**base, **override}
    return {
        "player_id": seat,
        "role": role,
        "team": ROLE_TEAMS[role],
        "provider": merged.get("provider"),
        "model": merged.get("model"),
        "prompt": merged.get("prompt", ""),
        "strategy": merged.get("strategy"),
    }


def _check_resolved_seat(seat_cfg: dict, seat: str) -> None:
    provider = seat_cfg["provider"]
    model = seat_cfg["model"]
    strategy = seat_cfg["strategy"]
    prompt = seat_cfg["prompt"]
    if provider not in ALLOWED_PROVIDERS:
        raise ProfileValidationError(f"{seat}: provider {provider!r} not allowed")
    if model not in ALLOWED_MODELS.get(provider, frozenset()):
        raise ProfileValidationError(
            f"{seat}: model {model!r} not valid for provider {provider!r}"
        )
    if strategy not in ALLOWED_STRATEGIES:
        raise ProfileValidationError(f"{seat}: strategy {strategy!r} not allowed")
    if not isinstance(prompt, str) or len(prompt) > PROMPT_MAX_LEN:
        raise ProfileValidationError(f"{seat}: prompt invalid or too long")


def validate_profile(profile: object) -> None:
    """Raise ``ProfileValidationError`` on the first failed rule; else return."""
    if not isinstance(profile, dict):
        raise ProfileValidationError("profile must be a JSON object")
    # Secret-like keys and values first, so the failure reason is explicit.
    _reject_secret_like_keys(profile)
    _reject_secret_like_values(profile)
    allowed_top = {"schema_version", "name", "template", "role_defaults", "seat_overrides"}
    extra = set(profile) - allowed_top
    if extra:
        raise ProfileValidationError(f"unexpected top-level keys: {sorted(extra)}")
    if profile.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise ProfileValidationError(
            f"schema_version must be {PROFILE_SCHEMA_VERSION!r}"
        )
    name = profile.get("name")
    if not isinstance(name, str) or not _SAFE_NAME_RE.match(name):
        raise ProfileValidationError(f"invalid profile name: {name!r}")
    template = profile.get("template")
    if template not in ALLOWED_TEMPLATES:
        raise ProfileValidationError(f"unknown template: {template!r}")
    seat_roles = _template_seat_roles(template)
    needed_roles = set(seat_roles.values())
    role_defaults = profile.get("role_defaults")
    if not isinstance(role_defaults, dict) or set(role_defaults) != needed_roles:
        raise ProfileValidationError(
            f"role_defaults must cover exactly {sorted(needed_roles)}"
        )
    for role, fragment in role_defaults.items():
        _check_fragment(fragment, where=f"role_defaults.{role}", required=True)
    seat_overrides = profile.get("seat_overrides", {})
    if not isinstance(seat_overrides, dict):
        raise ProfileValidationError("seat_overrides must be an object")
    for seat, fragment in seat_overrides.items():
        if seat not in DEFAULT_SEAT_IDS:
            raise ProfileValidationError(f"unknown seat id: {seat!r}")
        _check_fragment(fragment, where=f"seat_overrides.{seat}", required=False)
    counts: dict[str, int] = {}
    for role in seat_roles.values():
        counts[role] = counts.get(role, 0) + 1
    if counts != CANONICAL_DEFAULT_6P_ROLES:
        raise ProfileValidationError("role multiset must match canonical default_6p")
    for seat in DEFAULT_SEAT_IDS:
        _check_resolved_seat(_resolve_seat(profile, seat, seat_roles[seat]), seat)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_profile_config -v
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```powershell
git add src/werewolf_eval/profile_config.py tests/test_profile_config.py
git commit -m "feat(g2d): add profile_config schema and validation"
```

---

## Task 3: profile_config resolution, artifact, persistence

**Files:**

- Modify: `src/werewolf_eval/profile_config.py`
- Modify: `tests/test_profile_config.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_profile_config.py` (add imports `import json`, `import tempfile`, `from pathlib import Path`, and the new names to the existing import block: `build_resolved_profile_artifact`, `list_profiles`, `load_profile`, `resolve_profile`, `save_profile`):

```python
class ProfileResolutionTests(unittest.TestCase):
    def test_resolve_applies_role_defaults_in_seat_order(self):
        seats = resolve_profile(_valid_profile())
        self.assertEqual([s["player_id"] for s in seats], ["p1", "p2", "p3", "p4", "p5", "p6"])
        self.assertEqual(seats[0]["role"], "werewolf")
        self.assertEqual(seats[0]["team"], "werewolf")
        self.assertEqual(seats[2]["role"], "seer")
        self.assertEqual(seats[2]["team"], "villager")

    def test_resolve_applies_seat_override(self):
        seats = resolve_profile(_valid_profile(seat_overrides={
            "p3": {"provider": "deepseek", "model": "deepseek-chat", "prompt": "x", "strategy": "cautious"},
        }))
        p3 = next(s for s in seats if s["player_id"] == "p3")
        self.assertEqual(p3["provider"], "deepseek")
        self.assertEqual(p3["model"], "deepseek-chat")
        self.assertEqual(p3["strategy"], "cautious")


class ProfileArtifactTests(unittest.TestCase):
    def test_artifact_shape_and_hashing(self):
        art = build_resolved_profile_artifact(
            _valid_profile(seat_overrides={
                "p3": {"provider": "deepseek", "model": "deepseek-chat", "prompt": "custom-strategy-text", "strategy": "cautious"},
            }),
            run_id="run123",
        )
        self.assertEqual(art["schema_version"], PROFILE_SCHEMA_VERSION)
        self.assertEqual(art["run_id"], "run123")
        self.assertEqual(art["execution_mode"], "fake")
        self.assertEqual(art["live_api"], "not_used")
        self.assertTrue(art["secrets_redacted"])
        self.assertEqual(len(art["seats"]), 6)
        p3 = next(s for s in art["seats"] if s["player_id"] == "p3")
        self.assertEqual(len(p3["prompt_hash"]), 64)
        # raw prompt text never stored (only its hash)
        self.assertNotIn("custom-strategy-text", json.dumps(art))

    def test_artifact_has_no_absolute_paths(self):
        art = build_resolved_profile_artifact(_valid_profile(), run_id="run123")
        blob = json.dumps(art)
        self.assertNotIn(":\\\\", blob)
        self.assertNotIn("/home/", blob)


class ProfilePersistenceTests(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_profile(_valid_profile(name="rt"), Path(tmp))
            self.assertTrue(path.exists())
            loaded = load_profile(path)
            self.assertEqual(loaded["name"], "rt")

    def test_save_rejects_unsafe_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ProfileValidationError):
                save_profile(_valid_profile(name="../x"), Path(tmp))

    def test_list_profiles_reports_malformed_as_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "good.json").write_text(json.dumps(_valid_profile(name="good")), encoding="utf-8")
            (Path(tmp) / "bad.json").write_text("{ not json", encoding="utf-8")
            listed = {e["name"]: e for e in list_profiles(Path(tmp))}
            self.assertTrue(listed["good"]["valid"])
            self.assertFalse(listed["bad"]["valid"])
            self.assertIsNotNone(listed["bad"]["error"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_profile_config -v
```

Expected: FAIL with `ImportError` for `resolve_profile` / `build_resolved_profile_artifact` / persistence helpers.

- [ ] **Step 3: Implement resolution, artifact, persistence**

Append to `src/werewolf_eval/profile_config.py`:

```python
def resolve_profile(profile: dict) -> list[dict]:
    """Return resolved per-seat configs in template seat order.  Assumes a
    validated profile."""
    seat_roles = _template_seat_roles(profile["template"])
    return [
        _resolve_seat(profile, seat, seat_roles[seat])
        for seat in DEFAULT_SEAT_IDS
    ]


def build_resolved_profile_artifact(profile: dict, run_id: str) -> dict:
    """Build the ``resolved-profile.json`` content: declared per-seat config
    with hashed prompts and explicit fake-execution markers."""
    seats: list[dict[str, Any]] = []
    for seat_cfg in resolve_profile(profile):
        prompt = seat_cfg.get("prompt") or ""
        seats.append(
            {
                "player_id": seat_cfg["player_id"],
                "role": seat_cfg["role"],
                "team": seat_cfg["team"],
                "provider": seat_cfg["provider"],
                "model": seat_cfg["model"],
                "strategy": seat_cfg["strategy"],
                "prompt_hash": _hash_text(prompt) if prompt else "",
            }
        )
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_name": profile["name"],
        "template": profile["template"],
        "execution_mode": "fake",
        "live_api": "not_used",
        "secrets_redacted": True,
        "seats": seats,
    }


def load_profile(path: Path) -> dict:
    """Read and parse a profile JSON file; raise ProfileValidationError on
    malformed JSON or non-object content.  Error messages use the basename
    only — never the absolute path — so server responses cannot leak local
    paths."""
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileValidationError(f"invalid JSON in {p.name}: {exc}") from exc
    except OSError:
        raise ProfileValidationError(f"cannot read profile {p.name}")
    if not isinstance(data, dict):
        raise ProfileValidationError("profile file must contain a JSON object")
    return data


def save_profile(profile: dict, profiles_dir: Path) -> Path:
    """Validate then write ``<profiles_dir>/<name>.json``.  Pure helper — not a
    server endpoint this slice."""
    validate_profile(profile)
    name = profile["name"]
    if not _SAFE_NAME_RE.match(name):
        raise ProfileValidationError(f"unsafe profile name: {name!r}")
    target_dir = Path(profiles_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{name}.json"
    target.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def list_profiles(profiles_dir: Path) -> list[dict]:
    """Return per-file metadata; malformed files are reported valid=False and
    never raise."""
    target_dir = Path(profiles_dir)
    entries: list[dict] = []
    if not target_dir.is_dir():
        return entries
    for path in sorted(target_dir.glob("*.json")):
        entry: dict[str, Any] = {
            "name": path.stem,
            "template": None,
            "valid": False,
            "error": None,
        }
        try:
            data = load_profile(path)
            validate_profile(data)
            entry["template"] = data.get("template")
            entry["valid"] = True
        except ProfileValidationError as exc:
            entry["error"] = str(exc)
        entries.append(entry)
    return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_profile_config -v
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```powershell
git add src/werewolf_eval/profile_config.py tests/test_profile_config.py
git commit -m "feat(g2d): add profile resolution, artifact builder, persistence"
```

---

## Task 4: observer_protocol — artifact allowlist + launch parsing

**Files:**

- Modify: `src/werewolf_eval/observer_protocol.py`
- Modify: `tests/test_observer_protocol.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_observer_protocol.py` (reuse its existing imports; add `parse_profile_launch_request`, `ALLOWED_ARTIFACTS`, `ObserverProtocolError` if not already imported):

```python
class ProfileLaunchRequestTests(unittest.TestCase):
    def test_resolved_profile_in_allowed_artifacts(self):
        self.assertIn("resolved-profile.json", ALLOWED_ARTIFACTS)

    def test_accepts_inline_profile(self):
        out = parse_profile_launch_request({"profile": {"name": "x"}})
        self.assertEqual(out["kind"], "inline")
        self.assertEqual(out["mode"], "fake")
        self.assertTrue(out["run_id"])

    def test_accepts_named_profile(self):
        out = parse_profile_launch_request({"profile_name": "demo"})
        self.assertEqual(out["kind"], "named")
        self.assertEqual(out["profile_name"], "demo")

    def test_rejects_both_sources(self):
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"profile": {}, "profile_name": "demo"})

    def test_rejects_profile_with_template(self):
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"profile_name": "demo", "template": "default_6p_fake"})

    def test_rejects_neither_source(self):
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"mode": "fake"})

    def test_rejects_unsafe_profile_name(self):
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"profile_name": "../escape"})

    def test_rejects_non_string_profile_name(self):
        for bad in (None, 123, ["x"]):
            with self.assertRaises(ObserverProtocolError):
                parse_profile_launch_request({"profile_name": bad})

    def test_rejects_non_string_run_id(self):
        with self.assertRaises(ObserverProtocolError):
            parse_profile_launch_request({"profile_name": "demo", "run_id": 123})
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol -v
```

Expected: FAIL — `resolved-profile.json` not in `ALLOWED_ARTIFACTS` and `parse_profile_launch_request` undefined.

- [ ] **Step 3: Add the artifact and parser**

In `src/werewolf_eval/observer_protocol.py`, add `"resolved-profile.json"` to the `ALLOWED_ARTIFACTS` tuple:

```python
ALLOWED_ARTIFACTS: tuple[str, ...] = (
    "events.jsonl",
    "prompt-manifest.json",
    "game-log.json",
    "decision-log.json",
    "consensus-log.json",
    "provider-trace.json",
    "failure-audit.json",
    "resolved-profile.json",
)
```

Then add (near `parse_launch_request`):

```python
def parse_profile_launch_request(payload: dict[str, object]) -> dict[str, object]:
    """Validate and normalize a profile-launch payload.

    Exactly one launch source is required: ``profile`` (inline object) or
    ``profile_name`` (saved profile).  Allowed keys: ``profile``,
    ``profile_name``, ``run_id``, ``mode``.  ``template`` is not allowed here
    (template launches use ``parse_launch_request``).
    """
    if not isinstance(payload, dict):
        raise ObserverProtocolError("Launch request payload must be a JSON object")
    allowed_keys = {"profile", "profile_name", "run_id", "mode"}
    extra = set(payload.keys()) - allowed_keys
    if extra:
        raise ObserverProtocolError(
            f"Unexpected keys in profile launch: {sorted(extra)}.  Allowed: {sorted(allowed_keys)}"
        )
    has_inline = "profile" in payload
    has_named = "profile_name" in payload
    if has_inline and has_named:
        raise ObserverProtocolError("Provide either 'profile' or 'profile_name', not both")
    if not has_inline and not has_named:
        raise ObserverProtocolError("Profile launch requires 'profile' or 'profile_name'")

    mode = str(payload.get("mode", DEFAULT_FAKE_MODE))
    if mode not in ALLOWED_MODES:
        raise ObserverProtocolError(f"Unknown mode: {mode!r}.  Allowed: {ALLOWED_MODES}")

    run_id_raw = payload.get("run_id", "")
    if not isinstance(run_id_raw, str):
        raise ObserverProtocolError("run_id must be a string")
    run_id = run_id_raw
    if run_id:
        validate_run_id(run_id)
    else:
        run_id = generate_run_id(prefix="g2d_profile")
        if not run_id.startswith("g2d_profile"):
            run_id = f"g2d_profile_{uuid.uuid4().hex[:8]}"

    if has_inline:
        profile = payload["profile"]
        if not isinstance(profile, dict):
            raise ObserverProtocolError("'profile' must be a JSON object")
        return {"kind": "inline", "profile": profile, "run_id": run_id, "mode": mode}

    profile_name = payload["profile_name"]
    if not isinstance(profile_name, str) or not _SAFE_NAME_RE.match(profile_name):
        raise ObserverProtocolError(f"Unsafe profile_name: {profile_name!r}")
    return {"kind": "named", "profile_name": profile_name, "run_id": run_id, "mode": mode}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_protocol -v
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```powershell
git add src/werewolf_eval/observer_protocol.py tests/test_observer_protocol.py
git commit -m "feat(g2d): add resolved-profile artifact + profile launch parsing"
```

---

## Task 5: observer_server — profile endpoints + profile-bound launcher

**Files:**

- Modify: `src/werewolf_eval/observer_server.py`
- Modify: `tests/test_observer_server.py`

- [ ] **Step 1: Write the failing server tests**

Add to `tests/test_observer_server.py`. First extend the `_start_server` helper to accept an explicit profiles dir, and add a fixture writer. Update `_start_server`:

```python
def _start_server(
    runs_dir: Path,
    launcher: object = None,
    profiles_dir: Path | None = None,
) -> tuple[object, str]:
    """Start an observer server on a random port.  Returns (server, base_url)."""
    server = create_observer_server(
        "127.0.0.1", 0, runs_dir, launcher=launcher, profiles_dir=profiles_dir
    )
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, base_url
```

Then add the test class (uses a `profiles` dir beside `runs`):

```python
def _valid_profile_payload(name="demo", seat_overrides=None):
    p = {
        "schema_version": "g2d.profile.v1",
        "name": name,
        "template": "default_6p_fake",
        "role_defaults": {
            "werewolf": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            "seer": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            "witch": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            "villager": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
        },
    }
    if seat_overrides:
        p["seat_overrides"] = seat_overrides
    return p


class ObserverServerProfileTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        cls._runs = root / "runs"
        cls._profiles = root / "profiles"
        cls._runs.mkdir(parents=True)
        cls._profiles.mkdir(parents=True)
        (cls._profiles / "demo.json").write_text(
            json.dumps(_valid_profile_payload("demo")), encoding="utf-8"
        )
        cls._server, cls._base_url = _start_server(cls._runs, profiles_dir=cls._profiles)

    @classmethod
    def tearDownClass(cls):
        cls._server.shutdown()
        cls._tmp.cleanup()

    def test_list_profiles(self):
        result = _request_json(self._base_url, "/api/profiles")
        names = {p["name"] for p in result["profiles"]}
        self.assertIn("demo", names)

    def test_get_profile(self):
        result = _request_json(self._base_url, "/api/profiles/demo")
        self.assertEqual(result["name"], "demo")

    def test_get_unknown_profile_404(self):
        result = _request_json(self._base_url, "/api/profiles/nope")
        self.assertEqual(result.get("code"), "not_found")

    def test_validate_inline_profile(self):
        result = _request_json(
            self._base_url, "/api/profiles/validate", method="POST",
            payload=_valid_profile_payload("inline"),
        )
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["resolved_seats"]), 6)

    def test_validate_reports_invalid(self):
        bad = _valid_profile_payload("bad")
        bad["seat_overrides"] = {"p3": {"model": "deepseek-chat"}}
        result = _request_json(self._base_url, "/api/profiles/validate", method="POST", payload=bad)
        self.assertFalse(result["valid"])
        self.assertTrue(result["errors"])

    def test_launch_from_named_profile_writes_resolved_artifact(self):
        resp = _request_json(
            self._base_url, "/api/runs", method="POST",
            payload={"profile_name": "demo", "run_id": "g2d_named_run"},
        )
        self.assertEqual(resp["status"], "queued")
        _wait_for_status(self._base_url, "g2d_named_run", "completed")
        art = _request_json(self._base_url, "/api/runs/g2d_named_run/artifacts/resolved-profile.json")
        self.assertEqual(art["execution_mode"], "fake")
        self.assertEqual(art["live_api"], "not_used")
        self.assertEqual(len(art["seats"]), 6)

    def test_launch_from_inline_profile(self):
        resp = _request_json(
            self._base_url, "/api/runs", method="POST",
            payload={"profile": _valid_profile_payload("inlinerun"), "run_id": "g2d_inline_run"},
        )
        self.assertEqual(resp["status"], "queued")
        _wait_for_status(self._base_url, "g2d_inline_run", "completed")

    def test_launch_rejects_invalid_profile(self):
        bad = _valid_profile_payload("badrun")
        bad["template"] = "nope"
        result = _request_json(self._base_url, "/api/runs", method="POST", payload={"profile": bad})
        self.assertEqual(result.get("code"), "invalid_profile")

    def test_launch_rejects_mixed_template_and_profile(self):
        result = _request_json(
            self._base_url, "/api/runs", method="POST",
            payload={"profile_name": "demo", "template": "default_6p_fake"},
        )
        self.assertEqual(result.get("code"), "invalid_request")

    def test_responses_have_no_absolute_paths_or_secret_markers(self):
        # malformed-profile errors (listing + get-by-name) must not leak the
        # absolute profiles dir
        broken = self._profiles / "broken.json"
        broken.write_text("{ not json", encoding="utf-8")
        try:
            listing = _request_json(self._base_url, "/api/profiles")
            self.assertNotIn(str(self._profiles), json.dumps(listing))
            get_broken = _request_json(self._base_url, "/api/profiles/broken")
            self.assertNotIn(str(self._profiles), json.dumps(get_broken))
        finally:
            broken.unlink()
        # a launched run's resolved-profile artifact must not leak paths/secrets
        _request_json(
            self._base_url, "/api/runs", method="POST",
            payload={"profile_name": "demo", "run_id": "g2d_leak_run"},
        )
        _wait_for_status(self._base_url, "g2d_leak_run", "completed")
        art_text = _request_text(
            self._base_url, "/api/runs/g2d_leak_run/artifacts/resolved-profile.json"
        )
        self.assertNotIn(str(self._runs), art_text)
        for marker in ("sk-", "Bearer ", "DEEPSEEK_API_KEY", "api_key"):
            self.assertNotIn(marker, art_text)
```

Add a polling helper near the other module-level test helpers (if no equivalent exists):

```python
def _wait_for_status(base_url: str, run_id: str, target: str, timeout: float = 10.0) -> None:
    import time as _time
    deadline = _time.time() + timeout
    while _time.time() < deadline:
        detail = _request_json(base_url, f"/api/runs/{run_id}")
        if detail.get("status") == target:
            return
        _time.sleep(0.1)
    raise AssertionError(f"run {run_id} did not reach {target}")
```

> If `test_observer_server.py` already defines a status-wait helper, reuse it instead of adding a duplicate.

- [ ] **Step 2: Run server tests (record environment)**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_server -v
```

Expected in a normal environment: FAIL — `create_observer_server` has no `profiles_dir` arg / endpoints missing.

> **Sandbox note:** if every server test errors with `RemoteDisconnected` (a minimal `http.server` round-trip also fails), the local HTTP loopback is environmentally blocked. Record the exact symptom and proceed; this affects all server tests on any branch and is not a G2d defect (see Task 6 Step 6).

- [ ] **Step 3: Add profiles_dir to state and factory**

In `src/werewolf_eval/observer_server.py`, add imports:

```python
from werewolf_eval.observer_protocol import (
    # ... existing imports ...
    parse_profile_launch_request,
)
from werewolf_eval.profile_config import (
    ProfileValidationError,
    build_resolved_profile_artifact,
    list_profiles,
    load_profile,
    resolve_profile,
    validate_profile,
)
```

Add `profiles_dir` to `ObserverServerState`:

```python
@dataclass
class ObserverServerState:
    runs_dir: Path
    launcher: RunLauncher
    profiles_dir: Path = field(default_factory=lambda: Path("profiles"))
    run_status: dict[str, str] = field(default_factory=dict)
    run_errors: dict[str, str] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)
```

Update `create_observer_server`:

```python
def create_observer_server(
    host: str,
    port: int,
    runs_dir: Path,
    launcher: RunLauncher | None = None,
    profiles_dir: Path | None = None,
) -> ThreadingHTTPServer:
    """Create and configure a threaded observer HTTP server."""
    if launcher is None:
        launcher = default_fake_launcher
    runs_dir.mkdir(parents=True, exist_ok=True)
    if profiles_dir is None:
        profiles_dir = runs_dir.parent / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    state = ObserverServerState(
        runs_dir=runs_dir, launcher=launcher, profiles_dir=profiles_dir
    )

    class _BoundHandler(ObserverRequestHandler):
        pass

    server = ThreadingHTTPServer((host, port), _BoundHandler)
    server.state = state  # type: ignore[attr-defined]
    return server
```

- [ ] **Step 4: Add GET profile endpoints**

In `do_GET`, immediately after the `if segments == ["api", "runs"]:` block (before the `len(segments) >= 3 and segments[1] == "runs"` block), add:

```python
                if segments == ["api", "profiles"]:
                    profiles = list_profiles(self._get_state().profiles_dir)
                    self._send_json(200, {"profiles": profiles})
                    return

                if len(segments) == 3 and segments[:2] == ["api", "profiles"]:
                    name = segments[2]
                    if not _PROFILE_NAME_RE.match(name):
                        self._send_error_json(400, "invalid_request", "unsafe profile name")
                        return
                    path = self._get_state().profiles_dir / f"{name}.json"
                    if not path.exists():
                        self._send_error_json(404, "not_found", "profile not found")
                        return
                    try:
                        data = load_profile(path)
                        validate_profile(data)
                    except ProfileValidationError as exc:
                        self._send_error_json(400, "invalid_profile", str(exc))
                        return
                    self._send_json(200, redact_secret_values(data))
                    return
```

Add the import for `redact_secret_values` and a name regex near the top of `observer_server.py`:

```python
import re

from werewolf_eval.runtime_events import (
    RuntimeEventError,
    read_events_jsonl,
    redact_secret_values,
)

_PROFILE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,255}$")
```

- [ ] **Step 5: Add `_launch_run_async`, profile launch, and validate endpoint**

Add a handler method to `ObserverRequestHandler`:

```python
    def _launch_run_async(
        self, run_id: str, run_dir: Path, launcher: RunLauncher
    ) -> None:
        self._set_status(run_id, "queued")

        def _run_thread() -> None:
            self._set_status(run_id, "running")
            try:
                ret = launcher(run_id, run_dir)
            except Exception as exc:  # noqa: BLE001
                self._set_error(run_id, str(exc))
                self._set_status(run_id, "failed")
                return
            if ret == 0:
                self._set_status(run_id, "completed")
            else:
                self._set_error(run_id, f"Launcher returned code {ret}")
                self._set_status(run_id, "failed")

        Thread(target=_run_thread, daemon=True).start()

    def _handle_profile_launch(self, body: dict[str, object]) -> None:
        plr = parse_profile_launch_request(body)
        state = self._get_state()
        if plr["kind"] == "named":
            ppath = state.profiles_dir / f"{plr['profile_name']}.json"
            if not ppath.exists():
                self._send_error_json(404, "not_found", "profile not found")
                return
            try:
                profile = load_profile(ppath)
            except ProfileValidationError as exc:
                self._send_error_json(400, "invalid_profile", str(exc))
                return
        else:
            profile = plr["profile"]  # type: ignore[assignment]
        try:
            validate_profile(profile)
        except ProfileValidationError as exc:
            self._send_error_json(400, "invalid_profile", str(exc))
            return

        run_id = str(plr["run_id"])
        run_dir = state.runs_dir / run_id
        if run_dir.exists():
            self._send_error_json(409, "conflict", f"Run already exists: {run_id}")
            return
        run_dir.mkdir(parents=True)

        base = state.launcher

        def _profile_launcher(
            rid: str, rdir: Path, base: RunLauncher = base, profile: dict = profile
        ) -> int:
            code = base(rid, rdir)
            artifact = build_resolved_profile_artifact(profile, rid)
            (rdir / "resolved-profile.json").write_text(
                json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            return code

        self._launch_run_async(run_id, run_dir, _profile_launcher)
        self._send_json(
            202,
            {
                "run_id": run_id,
                "profile_name": profile["name"],
                "mode": plr["mode"],
                "status": "queued",
            },
        )
```

Then, in `do_POST`, replace the existing `if segments == ["api", "runs"]:` body so it routes profile launches first and reuses `_launch_run_async`:

```python
            if segments == ["api", "runs"]:
                body = self._read_json_body()
                if "profile" in body or "profile_name" in body:
                    self._handle_profile_launch(body)
                    return
                launch = parse_launch_request(body)
                run_id = launch["run_id"]
                run_dir = self._get_state().runs_dir / run_id
                if run_dir.exists():
                    self._send_error_json(
                        409, "conflict", f"Run already exists: {run_id}"
                    )
                    return
                run_dir.mkdir(parents=True)
                self._launch_run_async(run_id, run_dir, self._get_state().launcher)
                self._send_json(
                    202,
                    {
                        "run_id": run_id,
                        "template": launch["template"],
                        "mode": launch["mode"],
                        "status": "queued",
                    },
                )
                return

            if segments == ["api", "profiles", "validate"]:
                body = self._read_json_body()
                errors: list[str] = []
                resolved: list[dict[str, object]] = []
                try:
                    validate_profile(body)
                    resolved = resolve_profile(body)
                except ProfileValidationError as exc:
                    errors.append(str(exc))
                self._send_json(
                    200,
                    {"valid": not errors, "errors": errors, "resolved_seats": resolved},
                )
                return
```

> The existing inline `_run_thread` logic in `do_POST` is now provided by `_launch_run_async`; remove the old inline thread block when replacing the `["api", "runs"]` body.

- [ ] **Step 6: Run server tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_server -v
```

Expected: `OK` in a normal environment. If the sandbox HTTP limitation applies, record it per Task 6 Step 6 and confirm the profile module tests (Tasks 2-3) and protocol tests (Task 4) pass.

- [ ] **Step 7: Commit**

```powershell
git add src/werewolf_eval/observer_server.py tests/test_observer_server.py
git commit -m "feat(g2d): add profile endpoints and profile-bound launcher"
```

---

## Task 6: Full validation + review packet

**Files:**

- Modify: `.logs/review/latest/review-packet.md`
- Modify: `.oh-my-harness/tree.md` (tree hook only)

- [ ] **Step 1: Run focused G2d tests**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_profile_config tests.test_observer_protocol -v
```

Expected: `OK`. Record exact test counts.

- [ ] **Step 2: Run server tests**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_observer_server -v
```

Expected: `OK`, or documented environmental `RemoteDisconnected` limitation with exact failing names and proof (a minimal `http.server` round-trip also fails).

- [ ] **Step 3: Run full unit suite**

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```

Expected: `OK` or only the documented environmental server-test limitation.

- [ ] **Step 4: Compile Python**

```powershell
python -m compileall src tests
```

Expected: `0 failures`.

- [ ] **Step 5: Whitespace + allowlist + forbidden checks**

```powershell
git diff --check main...HEAD
git diff --name-only main...HEAD
git diff main...HEAD -- src tests | python -c "import sys,re; data=sys.stdin.read(); added=[l for l in data.splitlines() if l.startswith('+') and not l.startswith('+++')]; risky=[l for l in added if re.search(r'(requests|httpx|aiohttp|openai|anthropic|PySide|PyQt|api_key|Authorization|Bearer |sk-)', l)]; print('\n'.join(risky)); unsafe=[l for l in risky if 'secret' not in l.lower() and 'frag' not in l.lower() and 'reject' not in l.lower()]; assert not unsafe, 'unexpected risky additions: '+repr(unsafe)"
```

Expected: no whitespace errors; changed files within the allowlist; no unsafe secret/dependency additions (the `_SECRET_KEY_FRAGMENTS` literals in `profile_config.py` are safe and listed in the review packet).

- [ ] **Step 6: Document environmental server-test status (if applicable)**

If server tests cannot run, capture proof:

```powershell
python -c "import http.server,threading,urllib.request,socketserver; H=type('H',(http.server.BaseHTTPRequestHandler,),{'do_GET':lambda s:(s.send_response(200),s.end_headers(),s.wfile.write(b'ok')),'log_message':lambda *a:None}); srv=socketserver.TCPServer(('127.0.0.1',0),H); threading.Thread(target=srv.serve_forever,daemon=True).start(); import urllib.request as u; print(u.urlopen(f'http://127.0.0.1:{srv.server_address[1]}/',timeout=5).read())"
```

Record the result verbatim in the review packet (success → server tests are expected to pass; `RemoteDisconnected` → documented environmental limitation).

- [ ] **Step 7: Refresh tree**

```powershell
node .codex/hooks/tree.mjs --force
```

Expected: `.oh-my-harness/tree.md` includes `profile_config.py` and `test_profile_config.py`; excludes `.tmp/`, `.runs/`, build dirs.

- [ ] **Step 8: Write the review packet**

Create `.logs/review/latest/review-packet.md` (≤ 300 lines) with: Metadata (plan, branch `feat/g2d-prompt-configuration`, base `main`), Changed Files (`git diff --name-only main...HEAD`), Diff Stat, Diff Check result, Allowlist check, Forbidden/secret-scan result (listing `_SECRET_KEY_FRAGMENTS` as safe test/validator markers), Test Summary (per-command exit code + pass/fail; server-test environment note), Key Hunks (line ranges for `profile_config.py` validation, resolution, artifact; `observer_protocol.py` parser; `observer_server.py` endpoints + launcher), Evidence Map (A1-A10 → test/hunk), Acceptance Checklist, and Review Trigger Result.

- [ ] **Step 9: Commit**

```powershell
git add .logs/review/latest/review-packet.md .oh-my-harness/tree.md
git commit -m "docs(g2d): add review packet and refresh tree"
```

---

## Acceptance Criteria

- **A1.** `profile_config.py` exists with schema `g2d.profile.v1`, `validate_profile`, `resolve_profile`, `build_resolved_profile_artifact`, `load_profile`, `save_profile`, `list_profiles`. *(test_profile_config)*
- **A2.** `GET /api/profiles`, `GET /api/profiles/{name}`, `POST /api/profiles/validate` behave per spec §5.3. *(ObserverServerProfileTests)*
- **A3.** `POST /api/runs` launches a fake run from an inline or named profile and writes `resolved-profile.json`. *(test_launch_from_named_profile_writes_resolved_artifact, test_launch_from_inline_profile)*
- **A4.** `resolved-profile.json` records declared per-seat provider/model/prompt(hash)/strategy + `execution_mode="fake"` / `live_api="not_used"`; no secrets or absolute paths. *(ProfileArtifactTests)*
- **A5.** Validation rejects bad schema, bad role layout, disallowed provider/model/strategy, unsafe names, extra keys, secret-like keys, secret-like values (credential markers), and post-merge incoherence; generic words like "secret" in a prompt are allowed. *(ProfileValidationTests)*
- **A6.** Template launch path and all G2a/G2c endpoints unchanged. *(existing test_observer_server suites still pass)*
- **A7.** No live providers, no new dependencies, no engine/runtime changes; route-doc changes limited to §2A alignment. *(allowlist + forbidden checks)*
- **A8.** Focused tests pass; server tests pass or are documented with the exact environmental limitation. *(Task 6)*
- **A9.** `parse_profile_launch_request` enforces exactly one launch source. *(ProfileLaunchRequestTests)*
- **A10.** Route docs mark G2c `completed` and G2d active. *(Task 1 Step 4)*

---

## Review Packet Requirements

`.logs/review/latest/review-packet.md` must be ≤ 300 lines and include, in order: Metadata, Changed Files, Diff Stat, Diff Check, Allowlist Check, Forbidden/Secret-Scan (with `_SECRET_KEY_FRAGMENTS` listed as safe), Test Summary (exit codes + environment note), Key Hunks (post-implementation line ranges), Evidence Map (A1-A10), Acceptance Checklist, Review Trigger Result. If > 300 lines, set `PACKET_TOO_LARGE = YES` and provide B档 file ranges for `profile_config.py`, `observer_server.py`, `tests/test_profile_config.py`, `tests/test_observer_server.py`.

---

## Implementation PR Description Draft

Title:

```text
feat: add G2d-1 prompt configuration MVP (backend)
```

Body:

```markdown
## Summary
- Adds a pure `profile_config.py` layer: `g2d.profile.v1` JSON profiles, validation, resolution, resolved-profile artifact, save/load/list.
- Adds `/api/profiles`, `/api/profiles/{name}`, `/api/profiles/validate` and profile launch via `POST /api/runs` (inline or named), writing an auditable `resolved-profile.json` (declared config, `execution_mode=fake`).
- Aligns route docs: G2c completed, G2d active.

## Scope
- Backend config layer only; no Qt UI, no live providers, no secrets, no new dependencies.
- Execution stays fake-deterministic; the game engine and fake runtime are untouched.

## Validation
- `python -m unittest tests.test_profile_config tests.test_observer_protocol -v`
- `python -m unittest tests.test_observer_server -v` (or documented environmental limitation)
- `python -m unittest discover -s tests -p "test_*.py"`
- `python -m compileall src tests`
- allowlist / forbidden-scope / secret-scan recorded in `.logs/review/latest/review-packet.md`
```

---

## Execution Handoff

Implement task-by-task in order: (1) route alignment, (2) profile_config validation, (3) profile_config resolution/artifact/persistence, (4) observer_protocol parser + artifact allowlist, (5) observer_server endpoints + launcher, (6) full validation + review packet.

Do not modify the game engine or fake runtime. Do not add Qt, live providers, or secrets. Do not expand into G2d-2 (UI). Each task ends with its own commit.

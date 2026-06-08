# One-line Provider Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 9 first-party model vendors (zhipu/moonshot/qwen/minimax/siliconflow/xai/gemini/modelscope/openrouter) as one-line BYO-key presets so each game seat can use a different real AI.

**Architecture:** All 9 vendors speak the OpenAI-compatible wire, so they are added as `ProviderSpec` rows reusing the existing `OpenAIProvider` class — no new provider classes. Each gets its own `provider_id` (= credential slot), `default_base_url`, and `default_models`. `build_provider` stamps the registry identity (provider_name + source_label) onto each instance so per-seat artifacts name the real vendor, not the shared class default. The server merges registry UI metadata (`provider_specs`) into the profile-schema response; the Qt settings page and match-setup dropdowns become data-driven from it. `profile_config` stays registry-free (only its `ALLOWED_PROVIDERS` literal grows; a consistency test guards the superset).

**Tech Stack:** Python 3.12 stdlib (`werewolf_eval`), Qt 6.10 QML/C++ (`clients/qt_observer`), unittest. Tests run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.<module>`.

**Spec:** `docs/superpowers/specs/2026-06-08-byo-key-provider-presets-design.md`

**Key design decisions locked in (read before starting):**
- `default_models` lives ONLY in the registry (single source). `ALLOWED_MODELS` is NOT touched — `_check_resolved_seat` uses `ALLOWED_MODELS.get(provider, frozenset())` and only enforces the allowlist for `fake_deterministic`, so live vendors validate format-only.
- `source_label` for all 9 = the existing `OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL` ("[OpenAI-compatible API output]"), already in `VALID_SOURCE_LABELS` — no allowlist change.
- `credential_slot == provider_id` (convention, no new field). Credential store already keys by provider_id.
- `provider_cls` for all 9 = `OpenAIProvider`. Chat URL + model-list URL already `rstrip("/")`, so trailing-slash bases (Gemini) are safe — Task 7 is a regression guard.

---

## File Structure

**Backend (`src/werewolf_eval/`):**
- `provider_registry.py` — add `default_models` field to `ProviderSpec`; +9 rows; new `provider_specs_payload()`; stamp identity in `build_provider`.
- `run_emergent_deepseek_game.py` — `_provider_identity` reports the mixed label when provider names differ (not only when labels differ).
- `profile_config.py` — `ALLOWED_PROVIDERS` literal +9 ids. (No `ALLOWED_MODELS` change.)
- `observer_server.py` — profile-schema handler merges `provider_specs`.

**Frontend (`clients/qt_observer/`):**
- `qml/ProviderSettingsView.qml` — `providerCatalog`/`labelFor` derive from `profileSchema.provider_specs`; left list scrolls.
- `qml/components/SeatEditorPanel.qml` + `qml/MatchSetupView.qml` — provider labels + model fallback from `provider_specs`.

**Tests:** `tests/test_provider_registry.py`, `tests/test_run_emergent_deepseek_game.py`, `tests/test_profile_config.py`, `tests/test_observer_server.py`, `tests/test_qt_observer_static_contract.py`.

---

## Task 1: `ProviderSpec.default_models` field

**Files:**
- Modify: `src/werewolf_eval/provider_registry.py:39-48` (the `ProviderSpec` dataclass)
- Test: `tests/test_provider_registry.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_provider_registry.py` inside `ProviderRegistryTests`:

```python
    def test_spec_has_default_models_field_defaulting_empty(self) -> None:
        # Existing 4 providers carry no offline model hints by default.
        from werewolf_eval.provider_registry import ProviderSpec
        from werewolf_eval.llm_providers import OpenAIProvider
        spec = ProviderSpec(
            provider_id="x", label="X", provider_cls=OpenAIProvider,
            default_base_url="https://example/v1", models_path="/models",
            source_label="[OpenAI-compatible API output]",
        )
        self.assertEqual(spec.default_models, ())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_provider_registry -v 2>&1 | grep -E "default_models|FAIL|ERROR|OK"`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'default_models'` (field not yet defined).

- [ ] **Step 3: Add the field**

In `src/werewolf_eval/provider_registry.py`, add to `ProviderSpec` (after `requires_base_url`):

```python
@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    label: str
    provider_cls: type[BaseChatProvider]
    default_base_url: str
    models_path: str
    source_label: str
    requires_base_url: bool = False
    # Offline UI fallback model ids (live fetch overrides). NOT a validation
    # allowlist — live providers trust the fetched/typed model id.
    default_models: tuple[str, ...] = ()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_provider_registry -v 2>&1 | grep -E "default_models|OK|FAIL"`
Expected: the new test PASSES (existing tests still pass).

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/provider_registry.py tests/test_provider_registry.py
git commit -m "feat(byo-key): add default_models field to ProviderSpec"
```

---

## Task 2: Register the 9 vendor presets

**Files:**
- Modify: `src/werewolf_eval/provider_registry.py:50-84` (the `PROVIDER_REGISTRY` dict)
- Test: `tests/test_provider_registry.py:27-31` (replace the "four providers" assertion) + new per-vendor test

- [ ] **Step 1: Update the failing tests**

In `tests/test_provider_registry.py`, REPLACE `test_registry_covers_the_four_live_providers` with:

```python
    def test_registry_covers_all_live_providers(self) -> None:
        self.assertEqual(
            set(PROVIDER_REGISTRY),
            {
                "deepseek", "openai", "anthropic", "openai_compatible",
                "zhipu", "moonshot", "qwen", "minimax", "siliconflow",
                "xai", "gemini", "modelscope", "openrouter",
            },
        )

    def test_preset_vendors_reuse_openai_class_and_compatible_label(self) -> None:
        # The 9 presets all speak the OpenAI-compatible wire: one class, one
        # shared source_label (kept in VALID_SOURCE_LABELS), each its own base_url.
        presets = {
            "zhipu": "https://api.z.ai/api/paas/v4",
            "moonshot": "https://api.moonshot.ai/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "minimax": "https://api.minimax.io/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
            "xai": "https://api.x.ai/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
            "modelscope": "https://api-inference.modelscope.cn/v1",
            "openrouter": "https://openrouter.ai/api/v1",
        }
        for pid, base in presets.items():
            spec = PROVIDER_REGISTRY[pid]
            self.assertIs(spec.provider_cls, OpenAIProvider, pid)
            self.assertEqual(spec.default_base_url, base, pid)
            self.assertEqual(spec.models_path, "/models", pid)
            self.assertEqual(spec.source_label, OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL, pid)
            self.assertFalse(spec.requires_base_url, pid)
            self.assertTrue(len(spec.default_models) >= 1, pid)
```

- [ ] **Step 2: Run to verify it fails**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_provider_registry -v 2>&1 | grep -E "all_live_providers|preset_vendors|FAIL|ERROR"`
Expected: FAIL/ERROR — `KeyError: 'zhipu'` (vendors not registered yet).

- [ ] **Step 3: Add the 9 rows**

In `src/werewolf_eval/provider_registry.py`, inside `PROVIDER_REGISTRY`, AFTER the `openai_compatible` entry (before the closing `}`), add:

```python
    "zhipu": ProviderSpec(
        provider_id="zhipu",
        label="Zhipu GLM",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.z.ai/api/paas/v4",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("glm-4.7", "glm-4.6", "glm-4.5-air"),
    ),
    "moonshot": ProviderSpec(
        provider_id="moonshot",
        label="Moonshot Kimi",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.moonshot.ai/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("kimi-k2.6", "moonshot-v1-8k"),
    ),
    "qwen": ProviderSpec(
        provider_id="qwen",
        label="Alibaba Qwen",
        provider_cls=OpenAIProvider,
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("qwen3-max", "qwen-plus", "qwen-flash"),
    ),
    "minimax": ProviderSpec(
        provider_id="minimax",
        label="MiniMax",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.minimax.io/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("MiniMax-M3", "MiniMax-Text-01"),
    ),
    "siliconflow": ProviderSpec(
        provider_id="siliconflow",
        label="SiliconFlow",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.siliconflow.cn/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"),
    ),
    "xai": ProviderSpec(
        provider_id="xai",
        label="xAI Grok",
        provider_cls=OpenAIProvider,
        default_base_url="https://api.x.ai/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("grok-4.3", "grok-4"),
    ),
    "gemini": ProviderSpec(
        provider_id="gemini",
        label="Google Gemini",
        provider_cls=OpenAIProvider,
        default_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"),
    ),
    "modelscope": ProviderSpec(
        provider_id="modelscope",
        label="ModelScope",
        provider_cls=OpenAIProvider,
        default_base_url="https://api-inference.modelscope.cn/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"),
    ),
    "openrouter": ProviderSpec(
        provider_id="openrouter",
        label="OpenRouter",
        provider_cls=OpenAIProvider,
        default_base_url="https://openrouter.ai/api/v1",
        models_path="/models",
        source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
        default_models=("~openai/gpt-latest", "~anthropic/claude-sonnet-latest", "openrouter/auto"),
    ),
```

The `OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL` and `OpenAIProvider` imports already exist at the top of the file (lines 23-36).

- [ ] **Step 4: Run to verify it passes**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_provider_registry 2>&1 | grep -E "Ran|OK|FAIL"`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/provider_registry.py tests/test_provider_registry.py
git commit -m "feat(byo-key): register 9 OpenAI-compatible vendor presets"
```

---

## Task 3: `build_provider` stamps the registry identity onto the instance

This is the keystone for artifact honesty. `OpenAIProvider.PROVIDER_NAME == "openai"` and `SOURCE_LABEL == "[OpenAI API output]"` are CLASS attributes; without stamping, a Kimi seat would record `provider_name="openai"`. Stamping the registry's `provider_id` and `source_label` as INSTANCE attributes makes `respond()`, `_seat_manifest_agents`, and `_provider_identity` (all read `getattr(provider, "PROVIDER_NAME"/"SOURCE_LABEL")`) report the real vendor. No-op for the existing 4 (their class defaults already equal the spec values).

**Files:**
- Modify: `src/werewolf_eval/provider_registry.py:98-111` (`build_provider`)
- Test: `tests/test_provider_registry.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_provider_registry.py`:

```python
    def test_build_provider_stamps_vendor_identity(self) -> None:
        # A preset reusing OpenAIProvider must report ITS registry id + the
        # compatible source_label on the instance, not the class default "openai".
        cfg = ChatProviderConfig(api_key="sk-fake", model="kimi-k2.6")
        prov = build_provider("moonshot", cfg)
        self.assertEqual(prov.PROVIDER_NAME, "moonshot")
        self.assertEqual(prov.SOURCE_LABEL, OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL)
        # the stamped instance attrs shadow the class defaults respond() reads
        self.assertNotEqual(prov.PROVIDER_NAME, OpenAIProvider.PROVIDER_NAME)

    def test_build_provider_identity_unchanged_for_existing_four(self) -> None:
        cfg = ChatProviderConfig(api_key="sk-fake", model="m")
        self.assertEqual(build_provider("openai", cfg).PROVIDER_NAME, "openai")
        self.assertEqual(build_provider("deepseek", cfg).PROVIDER_NAME, "deepseek")
        self.assertEqual(
            build_provider("anthropic", cfg).SOURCE_LABEL,
            ANTHROPIC_PROVIDER_SOURCE_LABEL,
        )
```

(`ChatProviderConfig` is already imported at the top of the test file.)

- [ ] **Step 2: Run to verify it fails**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_provider_registry -v 2>&1 | grep -E "stamps_vendor|FAIL|ERROR"`
Expected: FAIL — `AssertionError: 'openai' != 'moonshot'`.

- [ ] **Step 3: Stamp identity in `build_provider`**

In `src/werewolf_eval/provider_registry.py`, change the end of `build_provider` from:

```python
    if not config.base_url:
        config = dataclasses.replace(config, base_url=spec.default_base_url)
    return spec.provider_cls(config, transport=transport)
```

to:

```python
    if not config.base_url:
        config = dataclasses.replace(config, base_url=spec.default_base_url)
    provider = spec.provider_cls(config, transport=transport)
    # Stamp the registry identity so per-seat artifacts (manifest, provider trace,
    # ProviderResponse.provider_name/source_label) name the REAL vendor, not the
    # shared class default ("openai"). Instance attrs shadow the class attrs that
    # respond() reads. No-op for the existing 4 (class defaults already match).
    provider.PROVIDER_NAME = spec.provider_id
    provider.SOURCE_LABEL = spec.source_label
    return provider
```

- [ ] **Step 4: Run to verify it passes**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_provider_registry 2>&1 | grep -E "Ran|OK|FAIL"`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/provider_registry.py tests/test_provider_registry.py
git commit -m "feat(byo-key): stamp registry vendor identity onto provider instances"
```

---

## Task 4: Honest mixed source_label when vendor names differ

`_provider_identity` currently flips to the mixed label only when the SOURCE_LABELs differ. Since all 9 presets share the compatible label, a seat1=moonshot + seat2=qwen game would otherwise be labeled "[OpenAI-compatible API output]" at the run level. Make it report the mixed label when the provider NAMES are heterogeneous too — the run-level label stays honest while per-seat manifest rows keep exact vendor ids.

**Files:**
- Modify: `src/werewolf_eval/run_emergent_deepseek_game.py:44-56` (`_provider_identity`)
- Test: `tests/test_run_emergent_deepseek_game.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_run_emergent_deepseek_game.py` (a new test class or an existing one). It uses a tiny stub provider with stamped attrs:

```python
class ProviderIdentityTests(unittest.TestCase):
    def _agent(self, name, label):
        from werewolf_eval.provider_contract import OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL
        class _P:
            PROVIDER_NAME = name
            SOURCE_LABEL = label
            requests = []
            responses = []
            model = "m"
            persona = ""
        class _A:
            provider = _P()
        return _A()

    def test_same_label_different_vendors_is_mixed(self) -> None:
        from werewolf_eval.run_emergent_deepseek_game import _provider_identity
        from werewolf_eval.provider_contract import (
            OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL, MIXED_PROVIDER_SOURCE_LABEL,
        )
        agents = {
            "p1": self._agent("moonshot", OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL),
            "p2": self._agent("qwen", OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL),
        }
        name, label = _provider_identity(agents)
        self.assertEqual(name, "mixed")
        self.assertEqual(label, MIXED_PROVIDER_SOURCE_LABEL)

    def test_uniform_vendor_keeps_its_label(self) -> None:
        from werewolf_eval.run_emergent_deepseek_game import _provider_identity
        from werewolf_eval.provider_contract import OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL
        agents = {
            "p1": self._agent("moonshot", OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL),
            "p2": self._agent("moonshot", OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL),
        }
        name, label = _provider_identity(agents)
        self.assertEqual(name, "moonshot")
        self.assertEqual(label, OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL)
```

Add `import unittest` at the top if the file doesn't already have it (it does — verify).

- [ ] **Step 2: Run to verify it fails**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_run_emergent_deepseek_game -v 2>&1 | grep -E "different_vendors|FAIL|ERROR"`
Expected: FAIL — label is the compatible label, not the mixed label.

- [ ] **Step 3: Make the label honest**

In `src/werewolf_eval/run_emergent_deepseek_game.py`, change the last two lines of `_provider_identity` from:

```python
    name = next(iter(names)) if len(names) == 1 else "mixed"
    label = next(iter(labels)) if len(labels) == 1 else MIXED_PROVIDER_SOURCE_LABEL
    return name, label
```

to:

```python
    name = next(iter(names)) if len(names) == 1 else "mixed"
    # Heterogeneous EITHER by name (e.g. moonshot+qwen, which share the compatible
    # label) or by label → the run-level label is the mixed label. Honest.
    if len(names) == 1 and len(labels) == 1:
        label = next(iter(labels))
    else:
        label = MIXED_PROVIDER_SOURCE_LABEL
    return name, label
```

- [ ] **Step 4: Run to verify it passes**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_run_emergent_deepseek_game 2>&1 | grep -E "Ran|OK|FAIL"`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/run_emergent_deepseek_game.py tests/test_run_emergent_deepseek_game.py
git commit -m "feat(byo-key): report mixed source_label when vendor names differ"
```

---

## Task 5: Allow the 9 vendors in `profile_config`

`profile_config` stays registry-free (stdlib-only). Add the 9 ids to the `ALLOWED_PROVIDERS` literal; the existing `test_allowed_providers_superset_of_registry` already enforces coverage. No `ALLOWED_MODELS` change (live vendors validate format-only).

**Files:**
- Modify: `src/werewolf_eval/profile_config.py:23-25` (`ALLOWED_PROVIDERS`)
- Test: `tests/test_profile_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_profile_config.py` (near the existing superset test at line 358):

```python
    def test_allowed_providers_includes_preset_vendors(self):
        from werewolf_eval.profile_config import ALLOWED_PROVIDERS
        for pid in ("zhipu", "moonshot", "qwen", "minimax",
                    "siliconflow", "xai", "gemini", "modelscope", "openrouter"):
            self.assertIn(pid, ALLOWED_PROVIDERS, pid)

    def test_preset_vendor_model_is_format_checked_not_allowlisted(self):
        # A live vendor seat validates with any non-empty model string (no
        # ALLOWED_MODELS entry needed); empty/non-string is rejected.
        from werewolf_eval.profile_config import _check_resolved_seat, ProfileValidationError
        ok = {"provider": "moonshot", "model": "kimi-k2.6",
              "strategy": "default", "prompt": ""}
        _check_resolved_seat(ok, "p1")  # no raise
        bad = {"provider": "moonshot", "model": "",
               "strategy": "default", "prompt": ""}
        with self.assertRaises(ProfileValidationError):
            _check_resolved_seat(bad, "p1")
```

- [ ] **Step 2: Run to verify it fails**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_profile_config -v 2>&1 | grep -E "preset_vendors|format_checked|FAIL|ERROR"`
Expected: FAIL — `'zhipu' not found in frozenset(...)`. Also `test_allowed_providers_superset_of_registry` FAILS (registry now has 13, ALLOWED_PROVIDERS has 5).

- [ ] **Step 3: Extend `ALLOWED_PROVIDERS`**

In `src/werewolf_eval/profile_config.py`, change:

```python
ALLOWED_PROVIDERS: frozenset[str] = frozenset(
    {"fake_deterministic", "deepseek", "openai", "anthropic", "openai_compatible"}
)
```

to:

```python
ALLOWED_PROVIDERS: frozenset[str] = frozenset(
    {
        "fake_deterministic", "deepseek", "openai", "anthropic", "openai_compatible",
        # P2-B preset vendors (OpenAI-compatible). Kept as a literal so this module
        # stays registry-free; test_allowed_providers_superset_of_registry guards it.
        "zhipu", "moonshot", "qwen", "minimax", "siliconflow",
        "xai", "gemini", "modelscope", "openrouter",
    }
)
```

- [ ] **Step 4: Run to verify it passes**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_profile_config 2>&1 | grep -E "Ran|OK|FAIL"`
Expected: OK (the superset test now passes too).

- [ ] **Step 5: Commit**

```bash
git add src/werewolf_eval/profile_config.py tests/test_profile_config.py
git commit -m "feat(byo-key): allow preset vendors in profile_config"
```

---

## Task 6: Serve `provider_specs` in the profile schema

Add a registry helper that emits UI metadata, and merge it into the schema response at the server layer (so `profile_config` stays registry-free).

**Files:**
- Modify: `src/werewolf_eval/provider_registry.py` (add `provider_specs_payload`)
- Modify: `src/werewolf_eval/observer_server.py:25-56` (import) and `:490-492` (handler)
- Test: `tests/test_provider_registry.py` and `tests/test_observer_server.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_provider_registry.py`:

```python
    def test_provider_specs_payload_shape(self) -> None:
        from werewolf_eval.provider_registry import provider_specs_payload
        payload = provider_specs_payload()
        ids = {row["id"] for row in payload}
        self.assertEqual(ids, set(PROVIDER_REGISTRY))
        moon = next(r for r in payload if r["id"] == "moonshot")
        self.assertEqual(
            set(moon),
            {"id", "label", "default_base_url", "requires_base_url", "default_models"},
        )
        self.assertEqual(moon["label"], "Moonshot Kimi")
        self.assertEqual(moon["default_base_url"], "https://api.moonshot.ai/v1")
        self.assertFalse(moon["requires_base_url"])
        self.assertIn("kimi-k2.6", moon["default_models"])
        self.assertIsInstance(moon["default_models"], list)  # JSON-serializable
```

Add to `tests/test_observer_server.py` (find the class with profile-schema coverage, e.g. search for `profiles/schema` or `build_profile_schema`; if none, add a new `ProfileSchemaEndpointTests`). Use the existing `_FakeServer`/handler pattern in that file — here is a self-contained pure-derivation test that does not need a socket:

```python
class ProviderSpecsInSchemaTests(TestCase):
    def test_schema_payload_includes_provider_specs(self) -> None:
        from werewolf_eval.observer_server import _schema_payload
        payload = _schema_payload()
        self.assertIn("provider_specs", payload)
        ids = {row["id"] for row in payload["provider_specs"]}
        self.assertIn("qwen", ids)
        self.assertIn("deepseek", ids)
        # the base profile-schema fields are still present
        self.assertIn("providers", payload)
        self.assertIn("roles", payload)
```

- [ ] **Step 2: Run to verify it fails**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_provider_registry tests.test_observer_server -v 2>&1 | grep -E "provider_specs|FAIL|ERROR"`
Expected: FAIL — `provider_specs_payload` / `_schema_payload` not defined.

- [ ] **Step 3: Add the registry helper**

Append to `src/werewolf_eval/provider_registry.py`:

```python
def provider_specs_payload() -> list[dict[str, object]]:
    """Read-only UI metadata for every registered provider. The observer server
    merges this into the profile-schema response so the Qt client can data-drive
    its provider list and per-provider model dropdowns. Never carries a secret."""
    return [
        {
            "id": spec.provider_id,
            "label": spec.label,
            "default_base_url": spec.default_base_url,
            "requires_base_url": spec.requires_base_url,
            "default_models": list(spec.default_models),
        }
        for spec in PROVIDER_REGISTRY.values()
    ]
```

- [ ] **Step 4: Wire it into the server**

In `src/werewolf_eval/observer_server.py`, add to the import that already pulls `build_profile_schema` (around line 55), the registry import (near the other `provider_registry` imports — search for `from werewolf_eval.provider_registry import`):

```python
from werewolf_eval.provider_registry import PROVIDER_REGISTRY, provider_specs_payload
```

(If `PROVIDER_REGISTRY` is already imported there, just add `provider_specs_payload` to that import list — do not duplicate.)

Add a module-level helper near `_build_capabilities_payload` (so it is unit-testable without a socket):

```python
def _schema_payload() -> dict[str, object]:
    """The profile-schema response: the pure validation schema plus the
    registry-derived provider UI metadata (kept here so profile_config stays
    registry-free)."""
    schema = build_profile_schema()
    schema["provider_specs"] = provider_specs_payload()
    return schema
```

Change the handler at `observer_server.py:490-492` from:

```python
            if segments == ["api", "profiles", "schema"]:
                self._send_json(200, build_profile_schema())
                return
```

to:

```python
            if segments == ["api", "profiles", "schema"]:
                self._send_json(200, _schema_payload())
                return
```

- [ ] **Step 5: Run to verify it passes**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_provider_registry tests.test_observer_server 2>&1 | grep -E "Ran|OK|FAIL"`
Expected: OK.

- [ ] **Step 6: Commit**

```bash
git add src/werewolf_eval/provider_registry.py src/werewolf_eval/observer_server.py tests/test_provider_registry.py tests/test_observer_server.py
git commit -m "feat(byo-key): serve provider_specs UI metadata in profile schema"
```

---

## Task 7: base_url trailing-slash normalization guard

`OpenAICompatibleProvider._build_url` and `model_list_url` already `rstrip("/")`. Gemini's default base has no trailing slash, but a user may paste the official `…/v1beta/openai/`. Lock the no-double-slash behavior with a regression test.

**Files:**
- Test: `tests/test_provider_registry.py`

- [ ] **Step 1: Write the test**

Add to `tests/test_provider_registry.py`:

```python
    def test_trailing_slash_base_url_does_not_double_slash(self) -> None:
        # model-list URL
        self.assertEqual(
            model_list_url("gemini", "https://host/v1beta/openai/"),
            "https://host/v1beta/openai/models",
        )
        # chat URL (built by the provider instance)
        cfg = ChatProviderConfig(api_key="k", base_url="https://host/v1beta/openai/", model="m")
        prov = build_provider("gemini", cfg)
        self.assertEqual(prov._build_url(), "https://host/v1beta/openai/chat/completions")
```

- [ ] **Step 2: Run to verify it passes (already-correct behavior)**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_provider_registry -v 2>&1 | grep -E "trailing_slash|OK|FAIL"`
Expected: PASS (the `rstrip("/")` is already in place — this is a guard). If it FAILS, add `.rstrip("/")` where the URL is concatenated.

- [ ] **Step 3: Commit**

```bash
git add tests/test_provider_registry.py
git commit -m "test(byo-key): guard base_url trailing-slash normalization"
```

---

## Task 8: Artifact honesty — mixed-vendor manifest preserves per-seat provider_id

End-to-end guard that the per-seat manifest names each real vendor even when seats mix vendors that share the compatible source_label.

**Files:**
- Test: `tests/test_run_emergent_deepseek_game.py`

- [ ] **Step 1: Write the test**

Add to `tests/test_run_emergent_deepseek_game.py` (reuse the `_seat_manifest_agents` helper which is already module-level):

```python
class SeatManifestHonestyTests(unittest.TestCase):
    def _agent(self, name, model):
        class _P:
            PROVIDER_NAME = name
            SOURCE_LABEL = "[OpenAI-compatible API output]"
            requests = []
            responses = []
            persona = ""
            def __init__(self, m): self._m = m
            @property
            def model(self): return self._m
        class _A:
            def __init__(self, p): self.provider = p
        return _A(_P(model))

    def test_manifest_keeps_each_vendor_id(self) -> None:
        from werewolf_eval.run_emergent_deepseek_game import _seat_manifest_agents, PLAYER_IDS
        agents = {
            PLAYER_IDS[0]: self._agent("moonshot", "kimi-k2.6"),
            PLAYER_IDS[1]: self._agent("qwen", "qwen3-max"),
        }
        rows = _seat_manifest_agents(agents, fallback_model="fallback")
        by_pid = {r["player_id"]: r for r in rows}
        self.assertEqual(by_pid[PLAYER_IDS[0]]["provider"], "moonshot")
        self.assertEqual(by_pid[PLAYER_IDS[0]]["model"], "kimi-k2.6")
        self.assertEqual(by_pid[PLAYER_IDS[1]]["provider"], "qwen")
        self.assertEqual(by_pid[PLAYER_IDS[1]]["model"], "qwen3-max")
```

- [ ] **Step 2: Run to verify it passes**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_run_emergent_deepseek_game -v 2>&1 | grep -E "keeps_each_vendor|OK|FAIL"`
Expected: PASS (the manifest already reads `getattr(provider, "PROVIDER_NAME")` per seat; this guards it stays honest).

- [ ] **Step 3: Commit**

```bash
git add tests/test_run_emergent_deepseek_game.py
git commit -m "test(byo-key): mixed-vendor manifest preserves per-seat provider_id"
```

---

## Task 9: Data-drive the provider settings page

Replace the hardcoded 4-entry `providerCatalog` + `labelFor` switch with derivation from `ObserverClient.profileSchema.provider_specs`; make the left list scroll (13 rows exceed the card height).

**Files:**
- Modify: `clients/qt_observer/qml/ProviderSettingsView.qml:18-50` (catalog + label helpers) and `:191-263` (left list → scrollable)

- [ ] **Step 1: Replace the hardcoded catalog with a schema-derived one**

In `clients/qt_observer/qml/ProviderSettingsView.qml`, replace the `providerCatalog` block (lines 18-25) and `labelFor` (lines 42-50) with:

```qml
    // Data-driven from the server PROVIDER_REGISTRY (profile schema provider_specs).
    // Falls back to an empty list until the schema loads; selectedProvider stays
    // valid because the default "deepseek" is always present in the registry.
    readonly property var providerCatalog: {
        var specs = (ObserverClient.profileSchema
                     && ObserverClient.profileSchema.provider_specs) || []
        var out = []
        for (var i = 0; i < specs.length; i++) {
            out.push({
                id: specs[i].id,
                label: specs[i].label,
                defaultBase: specs[i].default_base_url,
                requiresBase: specs[i].requires_base_url,
                defaultModels: specs[i].default_models || []
            })
        }
        return out
    }
```

Replace `labelFor` (lines 42-50) with a catalog lookup (the custom provider keeps its localized suffix):

```qml
    function labelFor(id) {
        var s = specFor(id)
        if (s && s.id === id)
            return s.label
        return id
    }
```

Update `specFor` (lines 33-38) to tolerate an empty catalog:

```qml
    function specFor(id) {
        for (var i = 0; i < providerCatalog.length; i++)
            if (providerCatalog[i].id === id)
                return providerCatalog[i]
        return { id: id, label: id, defaultBase: "", requiresBase: false, defaultModels: [] }
    }
```

- [ ] **Step 2: Make the left provider list scroll**

In the same file, the left-card inner `Column` that holds the `Repeater` (around lines 191-263) is fixed-height. Wrap the provider rows in a `ListView` so 13 rows scroll. Replace the inner `Column { ... Repeater { model: root.providerCatalog ... } }` (lines 191-263) with:

```qml
                ListView {
                    width: parent.width
                    height: parent.height - y    // fill remaining card height
                    clip: true
                    spacing: Theme.space.xs
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollIndicator.vertical: ScrollIndicator { }
                    model: root.providerCatalog
                    delegate: Rectangle {
                        id: providerRow
                        required property var modelData
                        width: ListView.view.width
                        height: 56
                        radius: Theme.radius.md
                        readonly property bool isSelected: root.selectedProvider === modelData.id
                        color: isSelected ? Theme.color.surfaceAlt
                                          : (rowHover.hovered ? Theme.color.surfaceInset : "transparent")
                        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }

                        Rectangle {
                            anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                            anchors.margins: Theme.space.sm
                            width: 2; radius: 1
                            color: Theme.color.primary
                            visible: providerRow.isSelected
                        }
                        GlowDot {
                            id: rowDot
                            anchors.left: parent.left; anchors.leftMargin: Theme.space.lg
                            anchors.verticalCenter: parent.verticalCenter
                            diameter: 9
                            color: root.dotColor(providerRow.modelData.id)
                        }
                        Column {
                            anchors.left: rowDot.right; anchors.leftMargin: Theme.space.md
                            anchors.right: parent.right; anchors.rightMargin: Theme.space.md
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2
                            Text {
                                width: parent.width; elide: Text.ElideRight
                                text: root.labelFor(providerRow.modelData.id)
                                color: Theme.color.text
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.body
                                font.weight: Theme.weight.medium
                            }
                            Text {
                                width: parent.width; elide: Text.ElideRight
                                text: (root.credRev, CredentialStore.hasCredential(providerRow.modelData.id))
                                      ? CredentialStore.maskedCredential(providerRow.modelData.id)
                                      : I18n.t("未配置", "Not configured")
                                color: Theme.color.textMuted
                                font.family: Theme.font.mono
                                font.pixelSize: Theme.size.micro
                            }
                        }
                        HoverHandler { id: rowHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: root.selectedProvider = providerRow.modelData.id }
                    }
                }
```

NOTE: keep the surrounding `SectionHeader` above it. The delegate body is identical to the old Repeater delegate — only the container changed from `Column`/`Repeater` to `ListView` (so it scrolls) and `width` uses `ListView.view.width`.

- [ ] **Step 3: Ensure the schema is fetched**

Verify the app already calls a schema fetch on startup (search `ObserverApiClient.cpp` for `profiles/schema` / `refreshProfileSchema`). It does (it populates `m_profileSchema`). No change needed — confirm by reading `clients/qt_observer/src/ObserverApiClient.cpp` for the schema request.

- [ ] **Step 4: Build to verify QML compiles**

Run:
```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer 2>&1 | tail -5
```
Expected: `[100%] Built target appqt_observer` (qmlcachegen AOT-compiles the QML — exit 0 means it parsed).

- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/qml/ProviderSettingsView.qml
git commit -m "feat(byo-key): data-drive provider settings page from provider_specs"
```

---

## Task 10: Per-provider model fallback in the match-setup inspector

The seat editor's model dropdown falls back to the static `profileSchema.models[provider]` when no live list is fetched. Switch the fallback to the provider's `default_models` from `provider_specs`, and source the provider's friendly label from `provider_specs` too.

**Files:**
- Modify: `clients/qt_observer/qml/components/SeatEditorPanel.qml` (model fallback + `_providerLabel`)
- Modify: `clients/qt_observer/qml/MatchSetupView.qml` (`providerLabel` helper)

- [ ] **Step 1: Read the current fallback**

Read `clients/qt_observer/qml/components/SeatEditorPanel.qml` and locate (a) where the model list is computed (`providerModels[p]` live OR `schema.models[p]` static — search `models[`), and (b) the `_providerLabel` / `providerOptions` helper. Read `clients/qt_observer/qml/MatchSetupView.qml` and locate `providerLabel`.

- [ ] **Step 2: Add a provider_specs lookup helper**

In `SeatEditorPanel.qml`, add a helper near the existing property declarations:

```qml
    function _specFor(pid) {
        var specs = (ObserverClient.profileSchema
                     && ObserverClient.profileSchema.provider_specs) || []
        for (var i = 0; i < specs.length; i++)
            if (specs[i].id === pid) return specs[i]
        return null
    }
```

- [ ] **Step 3: Use default_models as the static fallback**

Find the model-list computation (the expression like `ObserverClient.providerModels[p] || schema.models[p] || []`). Change the static fallback from `schema.models[p]` to the provider's `default_models`:

```qml
    // live fetched list wins; else the registry's per-provider default_models;
    // else empty (user types a model id).
    function _modelsFor(pid) {
        var live = ObserverClient.providerModels[pid]
        if (live && live.length > 0) return live
        var spec = _specFor(pid)
        return (spec && spec.default_models) ? spec.default_models : []
    }
```

Replace the dropdown's `model:` binding to call `_modelsFor(currentProvider)` (use the panel's existing "current provider" property name — confirm it while reading in Step 1).

- [ ] **Step 4: Source the provider label from provider_specs**

Replace the body of the existing `_providerLabel(pid)` (or `providerLabel`) function — in BOTH `SeatEditorPanel.qml` and `MatchSetupView.qml` — to prefer the spec label:

```qml
    function _providerLabel(pid) {
        var spec = _specFor(pid)            // in MatchSetupView use its own _specFor / inline lookup
        if (spec && spec.label) return spec.label
        if (pid === "fake_deterministic") return I18n.t("模拟（确定性）", "Simulation (deterministic)")
        return pid
    }
```

If `MatchSetupView.qml` has no `_specFor`, add the same helper there (it already reads `ObserverClient.profileSchema`).

- [ ] **Step 5: Build to verify QML compiles**

Run:
```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer 2>&1 | tail -5
```
Expected: `[100%] Built target appqt_observer`.

- [ ] **Step 6: Commit**

```bash
git add clients/qt_observer/qml/components/SeatEditorPanel.qml clients/qt_observer/qml/MatchSetupView.qml
git commit -m "feat(byo-key): per-provider model fallback + labels from provider_specs"
```

---

## Task 11: Static contract, full suite, screenshots

**Files:**
- Possibly modify: `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Run the static contract test**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract 2>&1 | grep -E "Ran|OK|FAIL"`
Expected: OK. The ProviderSettingsView assertions only check objectNames (preserved). If any assertion pinned the hardcoded 4-provider catalog (it should not), update it to assert `provider_specs` is referenced instead. If the test references removed text, fix inline.

- [ ] **Step 2: Run the FULL backend suite**

Run: `NO_PROXY="*" PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | grep -E "^(Ran|OK|FAILED)"`
Expected: `OK` (allow the 1 pre-existing skip). Investigate any FAILED before proceeding.

- [ ] **Step 3: Visual verification — settings page (13 rows) + a mixed seat dropdown**

Add a temporary grab harness to `clients/qt_observer/qml/AppShell.qml` (per memory `qt-observer-build-verify`): a `Timer` that navigates to ProviderSettings, waits ~800ms, and `grabToImage` → `G:/Werewolf-agent/.tmp/shot_presets.png`; then navigate to MatchSetup, open a seat, grab `shot_seat_dropdown.png`. Launch with the proxy STRIPPED:

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
  .tmp/qt-observer-build/appqt_observer.exe --observer-base-url http://127.0.0.1:8765
```

(Start a server first if the schema must be live: `NO_PROXY=127.0.0.1,localhost PYTHONPATH=src python src/werewolf_eval/run_observer_server.py --port 8765 --runs-dir .runs &`.)

Read the PNGs to confirm: 13 provider rows render and scroll; the seat editor lists e.g. Moonshot Kimi with `kimi-k2.6` in its model dropdown. Remove the temp harness afterward.

- [ ] **Step 4: Commit any static-contract fix**

```bash
git add tests/test_qt_observer_static_contract.py
git commit -m "test(byo-key): update Qt static contract for data-driven provider list"
```

(Skip if no change was needed.)

---

## Final integration

- [ ] **Step 1: Full suite once more + Qt build**

```bash
NO_PROXY="*" PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | grep -E "^(Ran|OK|FAILED)"
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer 2>&1 | tail -3
```
Expected: tests `OK`, build `[100%] Built target appqt_observer`.

- [ ] **Step 2: ff-merge to local main, leave push to the user**

```bash
git checkout main && git merge --ff-only feat/p2b-provider-presets
```
(Per `werewolf-env-network-test-limits`: the user pushes from their terminal — agent egress is unreliable.)

---

## Acceptance (from the spec)

- Settings page configures any new vendor (zhipu/moonshot/qwen/…), saves a key into its own slot, fetches models (or the user types one).
- A 6-seat game mixing ≥2 new vendors (seat1=Kimi, seat2=Qwen, seat3=Claude) runs live; `provider-turns.json` / prompt-manifest record each seat's real `provider_id` + `model`; a seat missing its credential is rejected pre-launch with a named 403.
- `source_label` is the generic compatible label per turn, the mixed label at the run level — never masking the per-seat vendor identity.

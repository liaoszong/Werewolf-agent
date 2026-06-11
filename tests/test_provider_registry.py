from __future__ import annotations

import unittest

from werewolf_eval.deepseek_provider import DeepSeekProvider
from werewolf_eval.llm_providers import (
    AnthropicProvider,
    ChatProviderConfig,
    OpenAICompatibleCustomProvider,
    OpenAIProvider,
)
from werewolf_eval.provider_contract import (
    ANTHROPIC_PROVIDER_SOURCE_LABEL,
    DEEPSEEK_PROVIDER_SOURCE_LABEL,
    OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL,
    OPENAI_PROVIDER_SOURCE_LABEL,
)
from werewolf_eval.provider_registry import (
    PROVIDER_REGISTRY,
    build_provider,
    list_models,
    model_list_url,
)


class ProviderRegistryTests(unittest.TestCase):
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

    def test_original_providers_have_offline_model_defaults(self) -> None:
        # Regression guard: the seat editor's offline model fallback reads
        # ProviderSpec.default_models. deepseek MUST carry its real models so a
        # deepseek seat that hasn't live-fetched still launches on a VALID model
        # (else every live call fails on a stray/empty model id and the game looks
        # fake). openai/anthropic carry sensible defaults too.
        self.assertIn("deepseek-chat", PROVIDER_REGISTRY["deepseek"].default_models)
        self.assertIn("deepseek-reasoner", PROVIDER_REGISTRY["deepseek"].default_models)
        self.assertTrue(PROVIDER_REGISTRY["openai"].default_models)
        self.assertTrue(PROVIDER_REGISTRY["anthropic"].default_models)

    def test_specs_pin_class_base_url_models_path_and_label(self) -> None:
        ds = PROVIDER_REGISTRY["deepseek"]
        self.assertIs(ds.provider_cls, DeepSeekProvider)
        self.assertEqual(ds.default_base_url, "https://api.deepseek.com")
        self.assertEqual(ds.models_path, "/models")
        self.assertEqual(ds.source_label, DEEPSEEK_PROVIDER_SOURCE_LABEL)
        self.assertFalse(ds.requires_base_url)

        oa = PROVIDER_REGISTRY["openai"]
        self.assertIs(oa.provider_cls, OpenAIProvider)
        self.assertEqual(oa.default_base_url, "https://api.openai.com/v1")
        self.assertEqual(oa.models_path, "/models")
        self.assertEqual(oa.source_label, OPENAI_PROVIDER_SOURCE_LABEL)

        an = PROVIDER_REGISTRY["anthropic"]
        self.assertIs(an.provider_cls, AnthropicProvider)
        self.assertEqual(an.default_base_url, "https://api.anthropic.com")
        self.assertEqual(an.models_path, "/v1/models")
        self.assertEqual(an.source_label, ANTHROPIC_PROVIDER_SOURCE_LABEL)

        cu = PROVIDER_REGISTRY["openai_compatible"]
        self.assertIs(cu.provider_cls, OpenAICompatibleCustomProvider)
        self.assertEqual(cu.source_label, OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL)
        self.assertTrue(cu.requires_base_url)

    def test_model_list_url_joins_base_and_models_path(self) -> None:
        # DeepSeek root has no /v1; OpenAI root carries /v1 → both land correctly.
        self.assertEqual(
            model_list_url("deepseek", "https://api.deepseek.com"),
            "https://api.deepseek.com/models",
        )
        self.assertEqual(
            model_list_url("openai", "https://api.openai.com/v1"),
            "https://api.openai.com/v1/models",
        )
        self.assertEqual(
            model_list_url("anthropic", "https://api.anthropic.com"),
            "https://api.anthropic.com/v1/models",
        )

    def test_model_list_url_uses_default_base_when_blank(self) -> None:
        self.assertEqual(
            model_list_url("deepseek", ""),
            "https://api.deepseek.com/models",
        )

    def test_model_list_url_strips_trailing_slash(self) -> None:
        self.assertEqual(
            model_list_url("deepseek", "https://api.deepseek.com/"),
            "https://api.deepseek.com/models",
        )

    def test_build_provider_returns_right_class(self) -> None:
        provider = build_provider("anthropic", ChatProviderConfig(api_key="k", model="m"))
        self.assertIsInstance(provider, AnthropicProvider)
        self.assertEqual(provider.model, "m")

    def test_build_provider_fills_default_base_url_when_blank(self) -> None:
        provider = build_provider("deepseek", ChatProviderConfig(api_key="k"))
        self.assertEqual(provider._config.base_url, "https://api.deepseek.com")

    def test_build_provider_keeps_explicit_base_url(self) -> None:
        provider = build_provider(
            "openai_compatible",
            ChatProviderConfig(api_key="k", base_url="https://my.proxy/v1"),
        )
        self.assertEqual(provider._config.base_url, "https://my.proxy/v1")

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

    def test_build_provider_rejects_unknown_provider(self) -> None:
        with self.assertRaises(KeyError):
            build_provider("nonexistent_provider", ChatProviderConfig(api_key="k"))

    def test_build_provider_requires_base_url_for_custom(self) -> None:
        # openai_compatible has no default base_url; building it without one must
        # fail loudly rather than produce a relative "/chat/completions" URL.
        with self.assertRaises(ValueError):
            build_provider("openai_compatible", ChatProviderConfig(api_key="k"))

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

    def test_list_models_coerces_ids_to_str(self) -> None:
        def transport(url, headers, timeout):
            return {"data": [{"id": "m1"}, {"id": 123}, {"no_id": 1}, "junk"]}

        models = list_models(
            "deepseek", ChatProviderConfig(api_key="k"), transport=transport
        )
        self.assertEqual(models, ["m1", "123"])

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

    def test_list_models_sanitizes_transport_error(self) -> None:
        def boom(url, headers, timeout):
            raise RuntimeError("HTTP 500 Bearer sk-secret-models")

        with self.assertRaises(RuntimeError) as ctx:
            list_models("deepseek", ChatProviderConfig(api_key="sk-secret-models"), transport=boom)
        self.assertNotIn("sk-secret-models", str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)
        self.assertTrue(ctx.exception.__suppress_context__)


class ProviderConstructionSingleSourceTest(unittest.TestCase):
    """D-4: build_provider is the only live construction path. A direct
    DeepSeekProvider(config) call silently skips the registry identity stamp,
    so registry changes (base-url/source-label) would not reach that path."""

    def test_no_direct_deepseek_provider_construction_in_src(self):
        from pathlib import Path

        src = Path(__file__).resolve().parents[1] / "src" / "werewolf_eval"
        allowed = {"deepseek_provider.py", "provider_registry.py"}
        offenders = sorted(
            p.name
            for p in src.rglob("*.py")
            if p.name not in allowed
            and "DeepSeekProvider(" in p.read_text(encoding="utf-8")
        )
        self.assertEqual(offenders, [])

    def test_build_provider_deepseek_keeps_default_base_url_and_stamp(self):
        from werewolf_eval.deepseek_provider import DeepSeekProviderConfig

        provider = build_provider("deepseek", DeepSeekProviderConfig(api_key="sk-test-key"))
        self.assertEqual(provider._config.base_url, "https://api.deepseek.com")
        self.assertEqual(provider.PROVIDER_NAME, "deepseek")
        self.assertEqual(provider.SOURCE_LABEL, DEEPSEEK_PROVIDER_SOURCE_LABEL)


if __name__ == "__main__":
    unittest.main()

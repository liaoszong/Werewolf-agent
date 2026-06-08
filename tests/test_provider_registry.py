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
    def test_registry_covers_the_four_live_providers(self) -> None:
        self.assertEqual(
            set(PROVIDER_REGISTRY),
            {"deepseek", "openai", "anthropic", "openai_compatible"},
        )

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
            build_provider("gemini", ChatProviderConfig(api_key="k"))

    def test_build_provider_requires_base_url_for_custom(self) -> None:
        # openai_compatible has no default base_url; building it without one must
        # fail loudly rather than produce a relative "/chat/completions" URL.
        with self.assertRaises(ValueError):
            build_provider("openai_compatible", ChatProviderConfig(api_key="k"))

    def test_list_models_coerces_ids_to_str(self) -> None:
        def transport(url, headers, timeout):
            return {"data": [{"id": "m1"}, {"id": 123}, {"no_id": 1}, "junk"]}

        models = list_models(
            "deepseek", ChatProviderConfig(api_key="k"), transport=transport
        )
        self.assertEqual(models, ["m1", "123"])

    def test_list_models_sanitizes_transport_error(self) -> None:
        def boom(url, headers, timeout):
            raise RuntimeError("HTTP 500 Bearer sk-secret-models")

        with self.assertRaises(RuntimeError) as ctx:
            list_models("deepseek", ChatProviderConfig(api_key="sk-secret-models"), transport=boom)
        self.assertNotIn("sk-secret-models", str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)
        self.assertTrue(ctx.exception.__suppress_context__)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from werewolf_eval.profile_config import (
    PROFILE_SCHEMA_VERSION,
    ProfileValidationError,
    build_default_profile,
    build_profile_schema,
    build_resolved_profile_artifact,
    list_profiles,
    load_profile,
    resolve_profile,
    save_profile,
    validate_profile,
)
from werewolf_eval.profile_config import _resolve_seat  # private: resolve a single seat
from werewolf_eval.profile_config import compute_role_shuffle, resolve_profile_for_run


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


class DefaultProfileTests(unittest.TestCase):
    def test_build_default_profile_validates(self):
        validate_profile(build_default_profile())  # must not raise

    def test_default_profile_shape(self):
        p = build_default_profile()
        self.assertEqual(p["schema_version"], PROFILE_SCHEMA_VERSION)
        self.assertEqual(p["template"], "default_6p_fake")
        self.assertEqual(sorted(p["role_defaults"]), ["seer", "villager", "werewolf", "witch"])

    def test_default_profile_prompts_are_prefilled(self):
        # The whole point of the seed: the per-seat prompt box is never blank.
        p = build_default_profile()
        for role, frag in p["role_defaults"].items():
            self.assertTrue(frag["prompt"].strip(), f"{role} default prompt must be non-empty")
            self.assertEqual(frag["provider"], "fake_deterministic")

    def test_default_profile_name_is_overridable(self):
        self.assertEqual(build_default_profile("custom")["name"], "custom")


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
        # The preset vendors (incl. gemini) are now allowed (P2-B); a provider id
        # that is in NO registry is still rejected.
        p = _valid_profile()
        p["role_defaults"]["seer"]["provider"] = "definitely_not_a_provider"
        with self.assertRaises(ProfileValidationError):
            validate_profile(p)

    def test_allows_anthropic_provider_seat(self):
        validate_profile(_valid_profile(seat_overrides={
            "p3": {"provider": "anthropic", "model": "claude-haiku-4-5", "prompt": "x", "strategy": "default"},
        }))

    def test_rejects_incoherent_partial_override(self):
        # model alone over a fake_deterministic provider -> invalid pair
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_overrides={"p3": {"model": "deepseek-chat"}}))

    def test_allows_current_deepseek_live_model(self):
        # P2-B-1 r2: live providers format-check the model (trust the live list).
        # Regression: the current default model deepseek-v4-flash was rejected by
        # the stale allowlist {deepseek-chat, deepseek-reasoner}.
        validate_profile(_valid_profile(seat_overrides={
            "p3": {"provider": "deepseek", "model": "deepseek-v4-flash", "prompt": "x", "strategy": "default"},
        }))

    def test_rejects_empty_live_model(self):
        # format check still rejects a blank model for a live provider
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_overrides={
                "p3": {"provider": "deepseek", "model": "", "prompt": "x", "strategy": "default"},
            }))

    def test_allows_per_seat_temperature_and_max_tokens(self):
        # P2-B-3: optional per-seat numeric knobs.
        validate_profile(_valid_profile(seat_overrides={
            "p3": {"provider": "deepseek", "model": "deepseek-v4-flash", "prompt": "x",
                   "strategy": "default", "temperature": 0.7, "max_tokens": 512},
        }))

    def test_allows_temperature_zero(self):
        # 0.0 is a meaningful (deterministic) temperature and must be accepted.
        validate_profile(_valid_profile(seat_overrides={
            "p3": {"provider": "deepseek", "model": "deepseek-v4-flash", "prompt": "x",
                   "strategy": "default", "temperature": 0.0},
        }))

    def test_rejects_out_of_range_temperature(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_overrides={
                "p3": {"provider": "deepseek", "model": "deepseek-v4-flash", "prompt": "x",
                       "strategy": "default", "temperature": 5.0},
            }))

    def test_rejects_non_numeric_temperature(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_overrides={
                "p3": {"provider": "deepseek", "model": "deepseek-v4-flash", "prompt": "x",
                       "strategy": "default", "temperature": "hot"},
            }))

    def test_rejects_bool_temperature(self):
        # bool is an int subclass — must not sneak through numeric validation.
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_overrides={
                "p3": {"provider": "deepseek", "model": "deepseek-v4-flash", "prompt": "x",
                       "strategy": "default", "temperature": True},
            }))

    def test_rejects_nonpositive_max_tokens(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_overrides={
                "p3": {"provider": "deepseek", "model": "deepseek-v4-flash", "prompt": "x",
                       "strategy": "default", "max_tokens": 0},
            }))

    def test_resolved_artifact_carries_temperature_and_max_tokens(self):
        from werewolf_eval.profile_config import build_resolved_profile_artifact
        p = _valid_profile(seat_overrides={
            "p3": {"provider": "deepseek", "model": "deepseek-v4-flash", "prompt": "x",
                   "strategy": "default", "temperature": 0.3, "max_tokens": 400},
        })
        art = build_resolved_profile_artifact(p, run_id="r")
        p3 = next(s for s in art["seats"] if s["player_id"] == "p3")
        self.assertEqual(p3["temperature"], 0.3)
        self.assertEqual(p3["max_tokens"], 400)

    def test_fake_provider_model_still_allowlisted(self):
        # fake_deterministic keeps its strict allowlist ({none}); a real model name
        # over the fake provider must still be rejected.
        p = _valid_profile()
        p["role_defaults"]["werewolf"]["model"] = "deepseek-v4-flash"
        with self.assertRaises(ProfileValidationError):
            validate_profile(p)

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
        self.assertNotIn(":\\", blob)
        self.assertNotIn("/home/", blob)


def _deepseek_profile(name="dsprofile", model="deepseek-chat"):
    rd = {
        role: {"provider": "deepseek", "model": model, "prompt": "p", "strategy": "default"}
        for role in ("werewolf", "seer", "witch", "villager")
    }
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "name": name,
        "template": "default_6p_fake",
        "role_defaults": rd,
    }


class LiveArtifactTests(unittest.TestCase):
    def test_live_markers_when_requested(self):
        art = build_resolved_profile_artifact(
            _deepseek_profile(), run_id="run_live",
            execution_mode="live", live_api="used",
        )
        self.assertEqual(art["execution_mode"], "live")
        self.assertEqual(art["live_api"], "used")
        self.assertTrue(art["secrets_redacted"])

    def test_records_resolved_real_per_seat_model(self):
        # Authoritative model record (A3): each seat carries its resolved model.
        art = build_resolved_profile_artifact(
            _deepseek_profile(model="deepseek-chat"), run_id="run_live",
            execution_mode="live", live_api="used",
        )
        self.assertEqual(len(art["seats"]), 6)
        for seat in art["seats"]:
            self.assertEqual(seat["provider"], "deepseek")
            self.assertEqual(seat["model"], "deepseek-chat")

    def test_live_artifact_stores_prompt_hash_only(self):
        art = build_resolved_profile_artifact(
            _deepseek_profile(), run_id="run_live",
            execution_mode="live", live_api="used",
        )
        # prompts are hash-only; the raw prompt "p" must not appear as a value
        for seat in art["seats"]:
            self.assertEqual(len(seat["prompt_hash"]), 64)
            self.assertNotIn("prompt", {k: v for k, v in seat.items() if k != "prompt_hash"}.values())

    def test_default_call_stays_fake_back_compat(self):
        art = build_resolved_profile_artifact(_deepseek_profile(), run_id="run_fake")
        self.assertEqual(art["execution_mode"], "fake")
        self.assertEqual(art["live_api"], "not_used")


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


class ProfileSchemaTests(unittest.TestCase):
    def test_schema_shape(self):
        s = build_profile_schema()
        self.assertEqual(s["schema_version"], PROFILE_SCHEMA_VERSION)
        self.assertEqual(
            set(s["providers"]),
            {
                "fake_deterministic", "deepseek", "openai", "anthropic", "openai_compatible",
                "zhipu", "moonshot", "qwen", "minimax", "siliconflow",
                "xai", "gemini", "modelscope", "openrouter",
            },
        )
        self.assertEqual(s["models"]["deepseek"], ["deepseek-chat", "deepseek-reasoner"])
        self.assertEqual(s["models"]["fake_deterministic"], ["none"])
        self.assertIn("default", s["strategies"])
        self.assertEqual(s["seat_roles"]["p1"], "werewolf")
        self.assertEqual(s["seat_roles"]["p3"], "seer")
        self.assertEqual(s["seat_ids"], ["p1", "p2", "p3", "p4", "p5", "p6"])
        self.assertEqual(s["prompt_max_len"], 8000)
        self.assertNotIn("templates", s)
        # sorted + leak-free
        self.assertEqual(s["providers"], sorted(s["providers"]))
        blob = json.dumps(s)
        self.assertNotIn(":\\", blob)

    def test_allowed_providers_superset_of_registry(self):
        # Single-source guard: every live provider in the registry must be an
        # allowed profile provider (profile_config stays pure by hardcoding the
        # set; this test enforces it never drifts behind the registry).
        from werewolf_eval.profile_config import ALLOWED_PROVIDERS
        from werewolf_eval.provider_registry import PROVIDER_REGISTRY
        self.assertTrue(set(PROVIDER_REGISTRY) <= ALLOWED_PROVIDERS)
        # Equality (minus the fake provider, which has no ProviderSpec) catches the
        # OTHER drift: a stale/typo'd id in the literal that no registry backs —
        # it would pass profile validation but be rejected at live launch as
        # unsupported_live_provider. The only allowed non-registry id is the fake.
        self.assertEqual(ALLOWED_PROVIDERS - {"fake_deterministic"}, set(PROVIDER_REGISTRY))

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


def _rd(prompts):
    """role_defaults with the given per-role prompt (fake provider)."""
    return {
        role: {"provider": "fake_deterministic", "model": "none", "prompt": prompts[role], "strategy": "default"}
        for role in ("werewolf", "seer", "witch", "villager")
    }


class ResolveSeatPersonaTests(unittest.TestCase):
    def test_no_seat_personas_is_byte_identical_strategy_only(self):
        # 组 1 parity:无 seat_personas、温度 null -> prompt == role_strategy、temperature 仍 null
        p = _valid_profile(role_defaults=_rd(
            {"werewolf": "STRAT_W", "seer": "STRAT_S", "witch": "STRAT_X", "villager": "STRAT_V"}))
        seat = _resolve_seat(p, "p1", "werewolf")
        self.assertEqual(seat["prompt"], "STRAT_W")
        self.assertIsNone(seat["temperature"])  # 兜底绝不在 _resolve_seat 发生

    def test_persona_appended_after_strategy(self):
        p = _valid_profile(
            role_defaults=_rd({"werewolf": "STRAT_W", "seer": "S", "witch": "X", "villager": "V"}),
            seat_personas={"p1": "PERSONA_1"},
        )
        self.assertEqual(_resolve_seat(p, "p1", "werewolf")["prompt"], "STRAT_W\n\nPERSONA_1")

    def test_two_wolves_distinct_persona(self):
        p = _valid_profile(
            role_defaults=_rd({"werewolf": "WOLF", "seer": "S", "witch": "X", "villager": "V"}),
            seat_personas={"p1": "AGGR", "p2": "CALM"},
        )
        self.assertNotEqual(_resolve_seat(p, "p1", "werewolf")["prompt"],
                            _resolve_seat(p, "p2", "werewolf")["prompt"])

    def test_persona_only_when_strategy_empty(self):
        p = _valid_profile(
            role_defaults=_rd({"werewolf": "", "seer": "", "witch": "", "villager": ""}),
            seat_personas={"p1": "ONLY_ME"},
        )
        self.assertEqual(_resolve_seat(p, "p1", "werewolf")["prompt"], "ONLY_ME")

    def test_seat_override_prompt_stacks_with_persona(self):
        # seat_overrides.prompt(覆盖角色策略)+ seat_personas 叠加正交
        p = _valid_profile(
            role_defaults=_rd({"werewolf": "ROLE_W", "seer": "S", "witch": "X", "villager": "V"}),
            seat_overrides={"p1": {"prompt": "OVERRIDE_W"}},
            seat_personas={"p1": "PERSONA_1"},
        )
        self.assertEqual(_resolve_seat(p, "p1", "werewolf")["prompt"], "OVERRIDE_W\n\nPERSONA_1")


class SeatPersonasValidationTests(unittest.TestCase):
    def test_valid_seat_personas_pass(self):
        validate_profile(_valid_profile(seat_personas={"p1": "谨慎", "p2": "激进"}))  # 不得抛

    def test_empty_and_absent_pass(self):
        validate_profile(_valid_profile(seat_personas={}))
        validate_profile(_valid_profile())  # 无该键

    def test_unknown_seat_id_rejected(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_personas={"p9": "x"}))

    def test_non_string_persona_rejected(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_personas={"p1": 123}))

    def test_non_dict_seat_personas_rejected(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_personas=["p1"]))

    def test_secret_like_persona_value_rejected(self):
        # _reject_secret_like_values 递归扫到新字段(注:此测试在实现前即 PASS)
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_personas={"p1": "my api_key=sk-secret"}))


class ArtifactEffectiveTemperatureTests(unittest.TestCase):
    def test_effective_temperature_fills_null_from_policy(self):
        from werewolf_eval.profile_config import DEFAULT_LIVE_TEMPERATURE
        art = build_resolved_profile_artifact(_valid_profile(), "run1")
        for seat in art["seats"]:
            self.assertIsNone(seat["temperature"])                        # 显式配置值(null)不变
            self.assertEqual(seat["effective_temperature"], DEFAULT_LIVE_TEMPERATURE)  # additive 留痕

    def test_effective_temperature_uses_explicit_when_set(self):
        p = _valid_profile(seat_overrides={"p1": {"temperature": 0.3}})
        art = build_resolved_profile_artifact(p, "run1")
        by_pid = {s["player_id"]: s for s in art["seats"]}
        self.assertEqual(by_pid["p1"]["temperature"], 0.3)
        self.assertEqual(by_pid["p1"]["effective_temperature"], 0.3)

    def test_existing_fields_unchanged_except_additive(self):
        art = build_resolved_profile_artifact(_valid_profile(), "run1")
        expected_keys = {"player_id", "role", "team", "provider", "model",
                         "strategy", "temperature", "max_tokens", "prompt_hash",
                         "effective_temperature"}
        self.assertEqual(set(art["seats"][0]), expected_keys)


class DefaultProfileSeatPersonasTests(unittest.TestCase):
    def test_default_has_six_distinct_personas(self):
        sp = build_default_profile()["seat_personas"]
        self.assertEqual(set(sp), {"p1", "p2", "p3", "p4", "p5", "p6"})
        self.assertEqual(len(set(sp.values())), 6)  # 互不相同

    def test_default_two_wolves_distinct_resolved_persona(self):
        p = build_default_profile()  # 默认 6p:p1/p2 = werewolf
        self.assertNotEqual(_resolve_seat(p, "p1", "werewolf")["prompt"],
                            _resolve_seat(p, "p2", "werewolf")["prompt"])

    def test_default_validates_and_has_no_seeded_temperature(self):
        p = build_default_profile()
        validate_profile(p)  # 不得抛
        for frag in p["role_defaults"].values():
            self.assertNotIn("temperature", frag)  # 温度单源于常量,不种进 fake 模板


class RoleShuffleTests(unittest.TestCase):
    def test_off_returns_default_layout(self):
        info = compute_role_shuffle(_valid_profile(), run_id="r", shuffle_seed=None)
        self.assertFalse(info["enabled"])
        self.assertIsNone(info["seed"])
        self.assertEqual(info["seat_roles"], {"p1":"werewolf","p2":"werewolf","p3":"seer","p4":"witch","p5":"villager","p6":"villager"})

    def test_on_preserves_multiset(self):
        info = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="run_abc", shuffle_seed=None)
        self.assertTrue(info["enabled"])
        self.assertEqual(sorted(info["seat_roles"].values()),
                         sorted(["werewolf","werewolf","seer","witch","villager","villager"]))
        self.assertEqual(info["seed_source"], "run_id")

    def test_explicit_seed_beats_run_id(self):
        a = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="X", shuffle_seed=12345)
        b = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="Y", shuffle_seed=12345)
        self.assertEqual(a["seat_roles"], b["seat_roles"])
        self.assertEqual(a["seed_source"], "explicit")

    def test_run_id_deterministic_and_varies(self):
        same1 = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="same", shuffle_seed=None)
        same2 = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="same", shuffle_seed=None)
        self.assertEqual(same1["seat_roles"], same2["seat_roles"])
        layouts = {tuple(compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id=f"r{i}", shuffle_seed=None)["seat_roles"].items()) for i in range(12)}
        self.assertGreater(len(layouts), 1)

    def test_enabled_but_no_seed_raises(self):
        with self.assertRaises(ProfileValidationError):
            resolve_profile_for_run(_valid_profile(role_shuffle={"enabled": True}), run_id=None, shuffle_seed=None)

    def test_for_run_off_equals_resolve_profile(self):
        p = _valid_profile()
        self.assertEqual(resolve_profile_for_run(p, run_id="r"), resolve_profile(p))

    def test_for_run_on_applies_shuffle_roles(self):
        p = _valid_profile(role_shuffle={"enabled": True})
        seats = {s["player_id"]: s["role"] for s in resolve_profile_for_run(p, run_id="run_zzz")}
        self.assertEqual(sorted(seats.values()), sorted(["werewolf","werewolf","seer","witch","villager","villager"]))

    def test_role_shuffle_field_validates(self):
        validate_profile(_valid_profile(role_shuffle={"enabled": True}))
        validate_profile(_valid_profile(role_shuffle={"enabled": False}))
        validate_profile(_valid_profile())
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(role_shuffle={"enabled": "yes"}))
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(role_shuffle=["x"]))

    def test_for_run_rechecks_shuffled_combos(self):
        # SHOULD-FIX 2: resolve_profile_for_run 对洗后每席补跑 _check_resolved_seat。8001 > PROMPT_MAX_LEN(8000)
        p = _valid_profile(role_shuffle={"enabled": True})
        p["role_defaults"]["seer"]["prompt"] = "x" * 8001
        with self.assertRaises(ProfileValidationError):
            resolve_profile_for_run(p, shuffle_seed=0)


class ArtifactRoleShuffleTests(unittest.TestCase):
    def test_off_no_shuffle_block_and_default_roles(self):
        art = build_resolved_profile_artifact(_valid_profile(), "run1")
        self.assertEqual(art["role_shuffle"], {"enabled": False, "seed": None, "seed_source": None})
        roles = {s["player_id"]: s["role"] for s in art["seats"]}
        self.assertEqual(roles["p1"], "werewolf")

    def test_on_records_seed_and_shuffled_roles(self):
        art = build_resolved_profile_artifact(_valid_profile(role_shuffle={"enabled": True}), "run_seed_x")
        self.assertTrue(art["role_shuffle"]["enabled"])
        self.assertEqual(art["role_shuffle"]["seed_source"], "run_id")
        self.assertIsInstance(art["role_shuffle"]["seed"], int)
        roles = sorted(s["role"] for s in art["seats"])
        self.assertEqual(roles, sorted(["werewolf","werewolf","seer","witch","villager","villager"]))

    def test_artifact_roles_match_resolve_for_run(self):
        p = _valid_profile(role_shuffle={"enabled": True})
        art = build_resolved_profile_artifact(p, "run_match")
        live = {s["player_id"]: s["role"] for s in resolve_profile_for_run(p, run_id="run_match")}
        self.assertEqual({s["player_id"]: s["role"] for s in art["seats"]}, live)


class CapabilitiesRolesExposureTests(unittest.TestCase):
    """Pin the capabilities 'roles' list (profile_config.py 'roles': sorted(ALLOWED_ROLES)).
    L4 adds the guard; hunter is INTENTIONALLY still excluded (spec §4 — it was
    never in ALLOWED_ROLES and the guard arm must not smuggle it in)."""

    def test_schema_roles_list_pinned(self):
        schema = build_profile_schema()
        self.assertEqual(schema["roles"],
                         ["guard", "seer", "villager", "werewolf", "witch"])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from werewolf_eval.profile_config import (
    PROFILE_SCHEMA_VERSION,
    ProfileValidationError,
    build_profile_schema,
    build_resolved_profile_artifact,
    list_profiles,
    load_profile,
    resolve_profile,
    save_profile,
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
        self.assertEqual(set(s["providers"]), {"fake_deterministic", "deepseek"})
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


if __name__ == "__main__":
    unittest.main()

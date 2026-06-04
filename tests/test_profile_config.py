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

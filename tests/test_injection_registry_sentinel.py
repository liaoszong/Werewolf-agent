"""C3-2 drift sentinel: the set of text-injection channels is FROZEN and must stay
in sync with docs/specs/text-injection-channels.md.

This is the one gap the existing negative scan (test_c3_negative_scan.py) doesn't
cover: that test proves the WITCH channels don't leak to other seats, but nothing
pins the *set* of injection channels — a new `*_obs_suffix` / `augment_*` / suffix
constant could be added and slip past I4b unregistered. This sentinel fails loudly
until the new channel is registered in the spec (and, if role-private, given a
negative scan). Lightweight: pure source/text scan, no game run.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.prompt_renderers import PromptRendererV1

# The frozen registry of injection channels (see spec §2). A new channel MUST be
# added here AND to docs/specs/text-injection-channels.md in the same change.
REGISTERED_CHANNELS = frozenset({
    "augment_witch_observation",
    "witch_obs_suffix",
    "speech_obs_suffix",
    "action_obs_suffix",
    "render_scribe_input",
    "HUNTER_SHOT_OBSERVATION_SUFFIX",
})

SPEC = ROOT / "docs" / "specs" / "text-injection-channels.md"
ENGINE_SRC = (ROOT / "src" / "werewolf_eval" / "emergent_engine.py").read_text(encoding="utf-8")


class InjectionRegistrySentinel(unittest.TestCase):
    def test_renderer_obs_suffix_methods_all_registered(self) -> None:
        """Every `*_obs_suffix` hook on the renderer base is a registered channel.
        Adding a new renderer suffix method without registering it fails here."""
        suffix_methods = {n for n in dir(PromptRendererV1) if n.endswith("_obs_suffix")}
        self.assertTrue(suffix_methods, "expected at least the known *_obs_suffix hooks")
        unregistered = suffix_methods - REGISTERED_CHANNELS
        self.assertEqual(unregistered, set(),
                         f"unregistered renderer injection hook(s): {sorted(unregistered)} "
                         "— add to REGISTERED_CHANNELS and docs/specs/text-injection-channels.md")

    def test_engine_obs_suffix_call_sites_all_registered(self) -> None:
        """Every `self._renderer.<x>_obs_suffix(` call in the engine is registered."""
        called = set(re.findall(r"self\._renderer\.(\w+_obs_suffix)\(", ENGINE_SRC))
        unregistered = called - REGISTERED_CHANNELS
        self.assertEqual(unregistered, set(),
                         f"unregistered injection call site(s): {sorted(unregistered)}")

    def test_engine_augment_call_sites_all_registered(self) -> None:
        """Every `augment_*(` injection call in the engine is registered (catches a
        new inline augmentation like augment_witch_observation)."""
        called = set(re.findall(r"\b(augment_\w+)\(", ENGINE_SRC))
        unregistered = called - REGISTERED_CHANNELS
        self.assertEqual(unregistered, set(),
                         f"unregistered augment injection(s): {sorted(unregistered)} "
                         "— register in the spec before merging")

    def test_spec_registers_every_channel(self) -> None:
        """The spec doc names every registered channel (keeps the table honest)."""
        spec_text = SPEC.read_text(encoding="utf-8")
        for name in REGISTERED_CHANNELS:
            self.assertIn(name, spec_text,
                          f"injection channel {name!r} missing from {SPEC.name}")


if __name__ == "__main__":
    unittest.main()

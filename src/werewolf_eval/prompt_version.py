"""Declared baseline prompt version (spec 2026-06-10-prompt-versioning §3).

Bump rule: ANY model-visible byte change in the rendered baseline prompt
assembly chain (build_action_system_prompt / build_speech_system_prompt /
compose_system / render_observation_text — incl. augment_witch_observation
and HUNTER_SHOT_OBSERVATION_SUFFIX, the model-visible inline augmentations)
requires bumping this constant, regenerating tests/golden_prompts/<version>/,
and adding a ledger entry in docs/generated-games/prompt-version-ledger.json.
No cosmetic exemption. Enforced byte-exactly by tests/test_prompt_versioning.py.
"""
from __future__ import annotations

PROMPT_VERSION = "prompt_v1"

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

# Runtime-selectable prompt renderers (spec 2026-06-10 quality §3.4): prompt_v1
# stays the default; prompt_v2 (SYS-B1 context repair) coexists and is selected
# per-arm/per-game. Each version has its own golden dir under tests/golden_prompts/.
# prompt_v3 = SYS-B4 claim-ledger/vote-scaffold chain (scribe + restrained speech).
KNOWN_PROMPT_VERSIONS = ("prompt_v1", "prompt_v2", "prompt_v3")

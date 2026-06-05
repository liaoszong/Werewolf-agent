"""Offline JUDGE for the P2-A-2 emergent live smoke (gate ①②③ + secret scan).

The user runs the live game (real DeepSeek, dev key); this module reads the RAW
artifacts and returns a text-free structural verdict. Pure + offline so it is
unit-tested on synthesized artifact dirs and so the agent can review a real run
WITHOUT touching the key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEEPSEEK_SOURCE_LABEL = "[DeepSeek API output]"
LIVE_SUCCESS = "live_success"
_SECRET_MARKERS = ("Authorization", "Bearer ", "api_key", "DEEPSEEK_API_KEY", "sk-")

MIN_LIVE_SUCCESS_RATE = 0.80
# Calibrated from two real live games (2026-06-05: 14- and 22-turn terminals): a
# 6-player emergent game ends in 1-2 rounds and produces ~14-22 provider turns, so
# the floor sits BELOW the shortest legit full game (~14) yet ABOVE a ~6-call dodge.
# It is also self-consistent with the 0.80 rate gate on the shortest game.
MIN_LIVE_SUCCESS_ACTIONS = 12


def scan_all_artifacts_for_secrets(run_dir: Path) -> bool:
    """True iff NO secret marker appears in ANY artifact file (gate: secret scan
    covers the whole run dir — logs, manifest, trace, snapshots, packet)."""
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(marker in text for marker in _SECRET_MARKERS):
            return False
    return True


def _load(run_dir: Path, name: str) -> Any | None:
    path = run_dir / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def evaluate_emergent_smoke(
    run_dir: Path,
    *,
    expected_model: str,
    allow_short_game: bool = False,
) -> dict:
    """Return a text-free verdict dict. `passed` is True iff every hard gate holds."""
    turns_doc = _load(run_dir, "provider-turns.json") or {}
    trace = _load(run_dir, "provider-trace.json") or {}
    manifest = _load(run_dir, "prompt-manifest.json")
    game_completed = (run_dir / "game-log.json").exists()

    turns: list[dict] = turns_doc.get("turns", [])
    live_requested = turns_doc.get("live_requested_actions", 0)
    live_success = turns_doc.get("live_success_actions", 0)
    rate = turns_doc.get("live_success_rate", 0.0)

    # gate ②: really live, not fallback-driven
    rate_ok = isinstance(rate, (int, float)) and rate >= MIN_LIVE_SUCCESS_RATE and live_requested > 0
    floor_ok = live_success >= MIN_LIVE_SUCCESS_ACTIONS or allow_short_game
    budget_not_exhausted = game_completed  # a budget/round-cap fail writes no game-log

    # gate ③ (per-turn honesty): every live_success turn has DeepSeek label + real
    # token usage; NO fallback turn masquerades as DeepSeek output.
    honesty_ok = True
    for t in turns:
        if t.get("kind") == LIVE_SUCCESS:
            tu = t.get("token_usage") or {}
            if t.get("source_label") != DEEPSEEK_SOURCE_LABEL or int(tu.get("total_tokens", 0)) <= 0:
                honesty_ok = False
        else:
            if t.get("source_label") == DEEPSEEK_SOURCE_LABEL:
                honesty_ok = False  # fallback turn must not claim DeepSeek output
    manifest_model_ok = bool(
        manifest
        and isinstance(manifest.get("agents"), list)
        and manifest["agents"]
        and all(a.get("model") == expected_model for a in manifest["agents"])
    )

    # gate ①(artifact-level): every live request carried non-empty observation_text
    # (empty -> the model only saw event ids; hard failure).
    requests = trace.get("requests", [])
    observation_text_ok = bool(requests) and all(
        (r.get("observation_text") or "").strip() for r in requests
    )

    no_secret = scan_all_artifacts_for_secrets(run_dir)

    checks = {
        "game_completed": game_completed,
        "live_success_rate_ok": rate_ok,
        "live_success_floor_ok": floor_ok,
        "budget_not_exhausted": budget_not_exhausted,
        "per_turn_honesty_ok": honesty_ok,
        "manifest_model_honest": manifest_model_ok,
        "observation_text_present": observation_text_ok,
        "no_secret_markers": no_secret,
    }
    return {
        "passed": all(checks.values()),
        "live_requested_actions": live_requested,
        "live_success_actions": live_success,
        "live_success_rate": rate,
        "by_provider_result_kind": turns_doc.get("by_provider_result_kind", {}),
        "checks": checks,
    }

"""Offline JUDGE for the P2-A-2 emergent live smoke (gate ①②③ + secret scan).

The user runs the live game (real provider, dev key); this module reads the RAW
artifacts and returns a text-free structural verdict. Pure + offline so it is
unit-tested on synthesized artifact dirs and so the agent can review a real run
WITHOUT touching the key.

B34-07 (audit 2026-06-12): the honesty gate is provider-AGNOSTIC. A live turn must
carry a REAL live-provider source label (∈ VALID_SOURCE_LABELS and not a
fake/simulation label) with real tokens; a fallback turn must never masquerade as a
live provider. The manifest gate supports a per-seat expected provider/model table
for mixed-provider games, while the single-provider `expected_model` path (DeepSeek
and any single live provider) stays backward-compatible. No live API call is made;
mixed-provider verification runs on offline fixtures only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from werewolf_eval.source_labels import VALID_SOURCE_LABELS

# Kept for backward compatibility (existing callers/tests import this).
DEEPSEEK_SOURCE_LABEL = "[DeepSeek API output]"
LIVE_SUCCESS = "live_success"

# Source labels that denote a REAL live provider call (NOT fake / simulation /
# human / scripted). A live_success turn must carry one of these; a fallback turn
# must carry NONE of these. This is the provider-agnostic generalization of the old
# `== DEEPSEEK_SOURCE_LABEL` check — every label here is also in VALID_SOURCE_LABELS.
LIVE_PROVIDER_SOURCE_LABELS = frozenset({
    "[DeepSeek API output]",
    "[OpenAI API output]",
    "[Anthropic API output]",
    "[OpenAI-compatible API output]",
    "[mixed provider output]",
})
# Drift guard: the live-provider set must stay a subset of the canonical allowlist.
assert LIVE_PROVIDER_SOURCE_LABELS <= VALID_SOURCE_LABELS, (
    "LIVE_PROVIDER_SOURCE_LABELS drifted from VALID_SOURCE_LABELS"
)

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


def _manifest_model_honest(
    manifest: Any,
    expected_model: str | None,
    expected_by_seat: dict[str, Any] | None,
) -> bool:
    """Per-seat OR single-provider manifest honesty.

    - ``expected_by_seat`` (mixed-provider): maps player_id -> expected model (str)
      or -> {"model": ..., "provider": ...}. Every listed seat must be present and
      match every key given. Catches a seat whose live provider/model differs from
      the configured per-seat plan.
    - ``expected_model`` (single provider, e.g. DeepSeek): every agent's model must
      equal it. Backward-compatible default.
    """
    if not manifest or not isinstance(manifest.get("agents"), list) or not manifest["agents"]:
        return False
    agents = manifest["agents"]
    if expected_by_seat is not None:
        by_id = {a.get("player_id"): a for a in agents}
        if not set(expected_by_seat) <= set(by_id):
            return False                       # a configured seat is missing
        for pid, exp in expected_by_seat.items():
            agent = by_id[pid]
            fields = exp if isinstance(exp, dict) else {"model": exp}
            for key, val in fields.items():
                if agent.get(key) != val:
                    return False
        return True
    if expected_model is not None:
        return all(a.get("model") == expected_model for a in agents)
    return False


def evaluate_emergent_smoke(
    run_dir: Path,
    *,
    expected_model: str | None = None,
    expected_models_by_seat: dict[str, Any] | None = None,
    expected_source_label: str | None = None,
    allow_short_game: bool = False,
) -> dict:
    """Return a text-free verdict dict. `passed` is True iff every hard gate holds.

    Provide EITHER ``expected_model`` (single provider — DeepSeek-compatible) OR
    ``expected_models_by_seat`` (mixed-provider per-seat plan). ``expected_source_label``
    optionally pins the live label for a single-provider run; when omitted, any real
    live-provider label is accepted (provider-agnostic).
    """
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

    # gate ③ (per-turn honesty, provider-agnostic): every live_success turn carries a
    # REAL live-provider label + real token usage; NO fallback turn masquerades as a
    # live provider output.
    honesty_ok = True
    for t in turns:
        label = t.get("source_label")
        if t.get("kind") == LIVE_SUCCESS:
            tu = t.get("token_usage") or {}
            if label not in LIVE_PROVIDER_SOURCE_LABELS or int(tu.get("total_tokens", 0)) <= 0:
                honesty_ok = False
            elif expected_source_label is not None and label != expected_source_label:
                honesty_ok = False
        else:
            if label in LIVE_PROVIDER_SOURCE_LABELS:
                honesty_ok = False  # a fallback turn must not claim live-provider output

    manifest_model_ok = _manifest_model_honest(manifest, expected_model, expected_models_by_seat)

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

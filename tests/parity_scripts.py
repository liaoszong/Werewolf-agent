# tests/parity_scripts.py
"""Shared adversarial script variants + (matrix, seeds) for the ②a parity gate.

NOT a test module (filename doesn't match `test_*.py`, so discover never collects it). Holds
only the builders imported by test_rng_draw_order.py and test_emergent_ledger_golden.py.
Carries NO oracle import -> it (correctly) survived the Task-7 oracle/diff-gate deletion that
removed test_emergent_parity_diff.py, which was the original third importer.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.emergent_fake_script import (
    build_villager_win_script,
    build_werewolf_win_script,
    build_hunter_night_kill_script,
    build_hunter_voteout_script,
)
import werewolf_eval.emergent_fake_script as efs  # for _act


# --- adversarial script variants (mutations of the canonical villager-win) ---

def _villager_win():
    return build_villager_win_script()

def _bad_vote():
    s = build_villager_win_script()
    s[("p6", "day", 1)] = efs._act("player_vote", "p99", "inference_based", "bad")  # invalid -> fallback
    return s

def _self_vote():
    s = build_villager_win_script()
    s[("p6", "day", 1)] = efs._act("player_vote", "p6", "inference_based", "self")  # invalid -> fallback
    return s

def _wolf_kills_teammate():
    s = build_villager_win_script()
    s[("p1", "night", 1)] = efs._act("werewolf_kill", "p2", "team_coordinated", "bad")  # invalid -> p2's proposal wins
    return s

def _seer_checks_self():
    s = build_villager_win_script()
    s[("p3", "night", 1)] = efs._act("seer_check", "p3", "inference_based", "self")  # invalid -> seer fallback (rng)
    return s

def _vote_tie():
    # p3/p4 -> p1 ; p5/p6 -> p2 ; p1->p3 p2->p4 => p1,p2 tie (vote tie-break randrange :853)
    s = build_villager_win_script()
    for pid, tgt in (("p5", "p2"), ("p6", "p2"), ("p1", "p3"), ("p2", "p4")):
        s[(pid, "day", 1)] = efs._act("player_vote", tgt, "inference_based", f"{pid}->{tgt}")
    return s

def _wolf_both_invalid():
    # both wolves kill a teammate -> no proposals -> no-proposal fallback (rng.choice :584)
    s = build_villager_win_script()
    s[("p1", "night", 1)] = efs._act("werewolf_kill", "p2", "team_coordinated", "bad")
    s[("p2", "night", 1)] = efs._act("werewolf_kill", "p1", "team_coordinated", "bad")
    return s

def _wolf_split_tie():
    # wolves split p5 vs p6 -> 2 leaders -> wolf tie randrange (:600)
    s = build_villager_win_script()
    s[("p1", "night", 1)] = efs._act("werewolf_kill", "p5", "team_coordinated", "p5")
    s[("p2", "night", 1)] = efs._act("werewolf_kill", "p6", "team_coordinated", "p6")
    # RNG tie-break selects the wolf victim; if p6 is chosen, the witch's scripted save target
    # (p5, from the base villager-win) != victim -> save is illegal -> game still completes
    return s


DEFAULT_MATRIX = [
    ("villager_win", _villager_win),
    ("werewolf_win", build_werewolf_win_script),
    ("bad_vote", _bad_vote),
    ("self_vote", _self_vote),
    ("wolf_kills_teammate", _wolf_kills_teammate),
    ("seer_checks_self", _seer_checks_self),
    ("vote_tie", _vote_tie),
    ("wolf_both_invalid", _wolf_both_invalid),
    ("wolf_split_tie", _wolf_split_tie),
]
HUNTER_MATRIX = [
    ("hunter_night_kill", build_hunter_night_kill_script),
    ("hunter_voteout", build_hunter_voteout_script),
]
SEEDS = [0, 1, 2, 7, 13, 42, 99]

"""P2-D settlement bundle builder (pure, eval-ready).

`build_settlement_bundle(game, decision_log) -> dict` produces the
`p2d.settlement.v2` bundle (spec §5/§6.1):

- Curtain layer (run_id/game_id/result/players-reveal/board_timeline) depends
  ONLY on the game-log and survives any scoring failure.
- Battle-report layer (core_metrics/top_attribution/turning_points/per-player
  scores) comes from score_game+summarize_metrics+attribute_game. A scoring crash
  FULLY degrades (degraded + bare reason CODE, never raw text). A missing/unusable
  decision-log only PARTIALLY degrades (product decision B): the result-type layer
  is still computed from the game-log; `decision_quality_available=False` +
  `decision_quality_reason` flag that only the decision-quality axis is missing.

`build_settlement_response(run_dir, run_status, run_id) -> dict` (Task 2) is the
filesystem-only route logic (lazy compute-or-cache settlement-bundle.json).
"""

from __future__ import annotations

import json
from pathlib import Path

from werewolf_eval.attribution import attribute_game
from werewolf_eval.decision_log import DecisionLog, load_decision_log
from werewolf_eval.evaluation_versions import (
    SCORING_VERSION,
    UNKNOWN_VERSION,
    evaluation_bucket as _evaluation_bucket,
    read_manifest_bucket,
)
from werewolf_eval.game_log import GameLog, load_game_log
from werewolf_eval.scoring import score_game, summarize_metrics

BUNDLE_VERSION = "p2d.settlement.v2"


def _unknown_bucket() -> dict[str, str]:
    return _evaluation_bucket(
        rules_version=UNKNOWN_VERSION,
        prompt_version=UNKNOWN_VERSION,
        scoring_version=SCORING_VERSION,
    )

# Death events that remove a player from the alive set (verified vs the gold
# game-log §13: night/poison kills surface as `player_died`, day votes as
# `player_eliminated`). `werewolf_kill` etc. are intents, not deaths.
_DEATH_TYPES = {"player_died", "player_eliminated"}
_PHASE_LABEL = {"setup": "开局", "night": "夜晚", "day": "白天", "game_end": "终局"}

_DECISION_DEGRADE = {
    "absent": "missing_decision_log",
    "invalid": "invalid_decision_log",
}


def _board_timeline(game: GameLog) -> list[dict]:
    """One node per (round, phase) group, in sequence order. Only needs the
    game-log; never raises. `alive_player_ids` is the state AFTER applying that
    group's deaths, so the last node's alive set == game.result.survivors."""
    alive = {p.player_id for p in game.players}
    nodes: list[dict] = []
    cur_key = None
    cur: dict | None = None
    for ev in sorted(game.events, key=lambda e: e.sequence):
        key = (ev.round, ev.phase)
        if key != cur_key:
            cur = {
                "cursor_index": len(nodes),
                "round": ev.round,
                "phase": ev.phase,
                "label": f"第{ev.round}{_PHASE_LABEL.get(ev.phase, ev.phase)}",
                "changed": [],
                "highlight": None,
                "alive_player_ids": sorted(alive),
            }
            nodes.append(cur)
            cur_key = key
        if ev.type in _DEATH_TYPES and ev.target in alive:
            alive.discard(ev.target)
            cur["changed"].append({"player_id": ev.target, "change": ev.type})
            # The death IS the spotlight for this round-phase — it always wins over
            # an earlier non-death action (e.g. a seer_check sequenced before the
            # night kill), so the docked sandbox highlights the kill, not the check.
            cur["highlight"] = {"actor": ev.actor, "target": ev.target, "kind": ev.type}
        elif cur["highlight"] is None and ev.target and ev.target != "none":
            cur["highlight"] = {"actor": ev.actor, "target": ev.target, "kind": ev.type}
        cur["alive_player_ids"] = sorted(alive)
    return nodes


def _curtain(
    game: GameLog,
    board: list[dict],
    run_id: str | None,
    seat_meta: dict[str, dict] | None = None,
) -> dict:
    survivors = set(game.result.survivors)
    seat_meta = seat_meta or {}
    return {
        "bundle_version": BUNDLE_VERSION,
        "run_id": run_id,
        "game_id": game.game_id,
        "degraded": False,
        "degraded_reason": None,
        # Partial-degrade axis (product decision B): the battle report stays available
        # without a decision-log; only the decision-QUALITY scores are unavailable.
        "decision_quality_available": False,
        "decision_quality_reason": None,
        "result": {
            "winner": game.result.winner,
            "end_round": game.result.end_round,
            "end_condition": game.result.end_condition,
            "survivors": sorted(survivors),
            "margin": None,
            "source_label": game.source_label,
        },
        "players": [
            {
                "player_id": p.player_id,
                "role": p.role,
                "team": p.team,
                "alive": p.player_id in survivors,
                "outcome_score": 0,
                "rule_integrity_score": 0,
                "decision_quality_score": 0,
                # R-09: per-seat model/provider/token for heterogeneous-AI fairness +
                # cost (additive, eval-v1). Resolved by the route from prompt-manifest +
                # provider-trace; None / {} when unavailable (fake runs report "none").
                "model": seat_meta.get(p.player_id, {}).get("model"),
                "provider": seat_meta.get(p.player_id, {}).get("provider"),
                "token_usage": seat_meta.get(p.player_id, {}).get("token_usage", {}),
            }
            for p in game.players
        ],
        "core_metrics": {},
        "top_attribution": None,
        "turning_points": [],
        # R-21: per-decision score records (additive, eval-v1) for P3 per-decision
        # review / rubric audit / decision→event traceability. Empty until scored.
        "score_records": [],
        "board_timeline": board,
        "evaluation_bucket": _unknown_bucket(),
    }


def _cursor_for(tp, game: GameLog, board: list[dict]) -> int:
    """Resolve a turn_point → board_timeline index via its evidence event's
    (round, phase). Falls back to the nearest preceding round node, then the
    last node. Never raises."""
    if not board:
        return 0
    rp = None
    for eid in getattr(tp, "evidence_event_ids", []) or []:
        try:
            ev = game.event_by_id(eid)
            rp = (ev.round, ev.phase)
            break
        except Exception:
            continue
    if rp is None:
        rp = (getattr(tp, "round", board[-1]["round"]), "day")
    for n in board:
        if (n["round"], n["phase"]) == rp:
            return n["cursor_index"]
    cand = [n for n in board if n["round"] <= rp[0]]
    return (cand[-1] if cand else board[-1])["cursor_index"]


def build_settlement_bundle(
    game: GameLog,
    decision_log: DecisionLog | None,
    *,
    run_id: str | None = None,
    decision_log_status: str = "present",
    seat_meta: dict[str, dict] | None = None,
    evaluation_bucket: dict[str, str] | None = None,
) -> dict:
    board = _board_timeline(game)
    bundle = _curtain(game, board, run_id, seat_meta)

    # PARTIAL DEGRADE (product decision B): a missing/unusable decision-log does NOT
    # blank the whole battle report. score_game(game, None) is a supported path that
    # still yields the RESULT-type layer (outcome scores, core_metrics, turning_points,
    # top_attribution) from the game-log alone — only the DECISION-QUALITY axis is
    # unavailable. So we score with the decision-log when present, None otherwise, and
    # flag decision_quality_available instead of degrading. FULL degrade stays reserved
    # for an actual scoring crash (and, upstream, a missing game-log).
    decision_available = decision_log_status == "present"
    try:
        score_log = score_game(game, decision_log if decision_available else None)
        metrics = summarize_metrics(game, score_log)
        attribution = attribute_game(game, score_log, metrics)
    except Exception:  # reason CODE only — never raw text/path/stack
        bundle["degraded"] = True
        bundle["degraded_reason"] = "scoring_failed"
        return bundle

    bundle["decision_quality_available"] = decision_available
    if not decision_available:
        bundle["decision_quality_reason"] = _DECISION_DEGRADE.get(
            decision_log_status, "missing_decision_log"
        )

    # metrics.* are dataclasses (ResultMetrics / ScoreSummary) — attribute access.
    ss = metrics.score_summary
    rm = metrics.result_metrics
    for p in bundle["players"]:
        pid = p["player_id"]
        p["outcome_score"] = ss.player_outcome_scores.get(pid, 0)
        p["rule_integrity_score"] = ss.player_rule_integrity_scores.get(pid, 0)
        p["decision_quality_score"] = ss.player_decision_quality_scores.get(pid, 0)

    bundle["result"]["margin"] = rm.margin
    mvp = (
        max(bundle["players"], key=lambda p: p["outcome_score"])["player_id"]
        if bundle["players"]
        else None
    )
    bundle["core_metrics"] = {
        "game_length": rm.game_length,
        "margin": rm.margin,
        "mvp_player_id": mvp,
        "villager_survival_rate": rm.villager_survival_rate,
        "werewolf_survival_rate": rm.werewolf_survival_rate,
    }

    # attribute_game ALWAYS returns a TopAttribution — when there are no turn_points
    # it yields a sentinel (turn_point_id == "none"). Treat that sentinel as null so
    # consumers can branch on a missing top_attribution instead of a fake "none" one.
    top = attribution.top_attribution
    bundle["top_attribution"] = (
        {"turn_point_id": top.turn_point_id, "description": top.description_template}
        if top and top.turn_point_id != "none"
        else None
    )

    def _tp_dict(tp) -> dict:
        cursor = _cursor_for(tp, game, board)  # resolve once (was computed twice)
        phase = next(
            (n["phase"] for n in board if n["cursor_index"] == cursor), "day"
        )
        return {
            "turn_point_id": tp.turn_point_id,
            "round": tp.round,
            "phase": phase,
            "title": (tp.description_template or "")[:40],
            "description": tp.description_template,
            "impact_score": tp.impact_score,
            "impact_sign": tp.impact_sign,
            "evidence_event_ids": list(tp.evidence_event_ids or []),
            "cursor_index": cursor,
        }

    bundle["turning_points"] = [_tp_dict(tp) for tp in attribution.turn_points]

    # R-21: keep the per-decision ScoreRecords (computed then discarded before) so P3
    # per-decision review / rubric audit doesn't need a schema migration.
    bundle["score_records"] = [
        {
            "score_id": r.score_id,
            "event_id": r.event_id,
            "decision_id": r.decision_id,
            "actor": r.actor,
            "round": r.round,
            "phase": r.phase,
            "action_type": r.action_type,
            "target": r.target,
            "outcome_score": r.outcome_score,
            "decision_quality_score": r.decision_quality_score,
            "rule_integrity_score": r.rule_integrity_score,
            "rules_triggered": list(r.rules_triggered),
            "evidence_event_ids": list(r.evidence_event_ids),
            "notes": r.notes,
        }
        for r in score_log.records
    ]
    bundle["evaluation_bucket"] = (
        dict(evaluation_bucket) if evaluation_bucket is not None else _unknown_bucket()
    )
    return bundle


def _load_seat_meta(run_dir: Path) -> dict[str, dict]:
    """Per-seat model/provider (prompt-manifest.json) + token rollup (provider-turns.json
    turns, summed by actor, excluding scribe). Both runners write these; absent/garbage -> empty.
    Pure filesystem read, never raises (best-effort enrichment, R-09)."""
    meta: dict[str, dict] = {}
    mpath = run_dir / "prompt-manifest.json"
    if mpath.exists():
        try:
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
            for agent in manifest.get("agents", []):
                pid = agent.get("player_id")
                if not pid:
                    continue
                entry = meta.setdefault(pid, {})
                if agent.get("model") is not None:
                    entry["model"] = agent["model"]
                if agent.get("provider") is not None:
                    entry["provider"] = agent["provider"]
        except (ValueError, OSError, AttributeError):
            pass
    # C12-02: token rollup reads provider-turns.json (each turn carries actor +
    # token_usage), NOT provider-trace.json whose ProviderResponse schema has no
    # actor field (the old code silently produced empty per-seat token_usage for
    # every live run). Scribe turns are excluded — they are scaffold, not player.
    tpath = run_dir / "provider-turns.json"
    if tpath.exists():
        try:
            pt = json.loads(tpath.read_text(encoding="utf-8"))
            turns = pt.get("turns", []) if isinstance(pt, dict) else []
            rollup: dict[str, dict] = {}
            for turn in turns:
                actor = turn.get("actor")
                if not actor or actor == "scribe":
                    continue
                usage = turn.get("token_usage")
                if not isinstance(usage, dict):
                    continue
                acc = rollup.setdefault(actor, {})
                for key, val in usage.items():
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        acc[key] = acc.get(key, 0) + val
            for pid, usage in rollup.items():
                meta.setdefault(pid, {})["token_usage"] = usage
        except (ValueError, OSError, AttributeError):
            pass
    return meta


def build_settlement_response(
    run_dir: Path, run_status: str, run_id: str | None
) -> dict:
    """Filesystem-only route logic for GET /api/runs/{id}/settlement (no socket).

    - not completed                  -> {"available": False, "reason": "not_completed"}
    - completed but no game-log      -> {"available": False, "reason": "no_game_log"}
    - completed + game-log           -> lazy compute-or-cache settlement-bundle.json,
                                        return {"available": True, "bundle": ...}

    Decision-log status is judged here (absent / invalid / present) and passed to
    the builder, which maps it to the missing_/invalid_decision_log degrade code.
    """
    run_dir = Path(run_dir)
    game_log_path = run_dir / "game-log.json"
    if run_status != "completed":
        return {"available": False, "reason": "not_completed"}
    if not game_log_path.exists():
        return {"available": False, "reason": "no_game_log"}

    cache = run_dir / "settlement-bundle.json"
    if cache.exists():
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            # Serve the cache ONLY if it's the current schema. A missing/mismatched
            # bundle_version (a bundle written by an older/newer build) is recomputed
            # so P3 never silently reads a stale schema (R-08).
            if isinstance(cached, dict) and cached.get("bundle_version") == BUNDLE_VERSION:
                return {"available": True, "bundle": cached}
        except (ValueError, OSError):
            pass  # corrupt/partial cache -> recompute below (self-heal, not 500)

    try:
        game = load_game_log(game_log_path)
    except Exception:
        return {"available": False, "reason": "invalid_game_log"}
    dpath = run_dir / "decision-log.json"
    decision_log: DecisionLog | None = None
    status = "absent"
    if dpath.exists():
        try:
            decision_log = load_decision_log(dpath, game)
            status = "present"
        except Exception:
            decision_log = None
            status = "invalid"

    bundle = build_settlement_bundle(
        game,
        decision_log,
        run_id=run_id,
        decision_log_status=status,
        seat_meta=_load_seat_meta(run_dir),
        evaluation_bucket=read_manifest_bucket(run_dir),
    )
    # Cache ONLY a COMPLETE bundle: not degraded AND decision-quality present. A
    # degraded bundle (scoring crash) OR a partial one (no decision-log yet) is a
    # transient state — caching it would freeze it even after the decision-log lands
    # or the cause is resolved. Incomplete bundles recompute each request (cheap) so
    # they auto-upgrade to the full report.
    if not bundle.get("degraded") and bundle.get("decision_quality_available"):
        # Atomic write (temp + replace) so a crash/concurrent write never leaves a
        # torn cache file for the next reader (R-08).
        tmp = cache.with_name(cache.name + ".tmp")
        tmp.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        tmp.replace(cache)
    return {"available": True, "bundle": bundle}

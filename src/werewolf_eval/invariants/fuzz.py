from __future__ import annotations

import random
from typing import Any

from werewolf_eval.invariants.artifacts import RunArtifacts

SEED_BANK = tuple(range(50))

_ROLES = [("p1", "seer", "villager"), ("p2", "witch", "villager"),
          ("p3", "hunter", "villager"), ("p4", "werewolf", "werewolf")]


def _players() -> list[dict[str, Any]]:
    return [{"player_id": pid, "role": r, "team": t} for pid, r, t in _ROLES]


def _ev(seq: int, etype: str, actor: str, target: str, vis: str, rnd: int = 1,
        phase: str = "night") -> dict[str, Any]:
    return {"event_id": f"g_e{seq:03d}", "sequence": seq, "round": rnd, "phase": phase,
            "type": etype, "actor": actor, "target": target, "visibility": vis,
            "data": {"summary": ""}}


def well_formed_game(seed: int) -> RunArtifacts:
    """A legal game whose shape varies by seed: wolf kills a random villager, the
    seer checks a random seat. Always inside the rules → must PASS every invariant."""
    rng = random.Random(seed)
    seq = 0
    events: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []

    def add(etype, actor, target, vis, phase="night"):
        nonlocal seq
        seq += 1
        events.append(_ev(seq, etype, actor, target, vis, phase=phase))
        return events[-1]["event_id"]

    victim = rng.choice(["p1", "p2", "p3"])
    wk = add("werewolf_kill", "p4", victim, "werewolf_team")
    sc = add("seer_check", "p1", rng.choice(["p2", "p3", "p4"]), "seer")
    turns.append({"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
                  "observation_source_event_ids": [wk]})
    turns.append({"request_id": "g_r01_p1", "phase": "night", "actor": "p1",
                  "observation_source_event_ids": [sc]})
    add("player_died", "system", victim, "all")
    return RunArtifacts(game_id="g", players=_players(), events=events,
                        decisions=[], provider_turns=turns, result=None)


def known_bad_games(seed: int) -> list[tuple[str, RunArtifacts, str]]:
    """Each entry = (label, artifacts, expected_failing_invariant_id)."""
    base = well_formed_game(seed)
    out: list[tuple[str, RunArtifacts, str]] = []

    # I1: commit the same death twice (reuse the legitimately-killed victim)
    evs = list(base.events) + [_ev(900, "player_died", "system", base.events[-1]["target"], "all")]
    out.append(("double_death", _clone(base, events=evs), "I1"))

    # I3: second witch_save by the same actor
    evs = list(base.events) + [
        _ev(910, "witch_save", "p2", "p1", "witch"),
        _ev(911, "witch_save", "p2", "p3", "witch")]
    out.append(("double_antidote", _clone(base, events=evs), "I3"))

    # I4b: a villager (p3) sources a seer-tagged event
    seer_ev = next(e for e in base.events if e["type"] == "seer_check")
    turns = list(base.provider_turns) + [
        {"request_id": "g_r01_p3", "phase": "night", "actor": "p3",
         "observation_source_event_ids": [seer_ev["event_id"]]}]
    out.append(("villager_reads_seer", _clone(base, provider_turns=turns), "I4b"))

    # I5: same (request_id, phase) twice
    turns = list(base.provider_turns) + [
        {"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
         "observation_source_event_ids": []}]
    out.append(("double_settle", _clone(base, provider_turns=turns), "I5"))

    # I6: an uncaused death
    evs = list(base.events) + [_ev(920, "player_died", "system", "p9_ghost", "all")]
    out.append(("uncaused_death", _clone(base, events=evs), "I6"))

    return out


def _clone(arts: RunArtifacts, **over: Any) -> RunArtifacts:
    return RunArtifacts(
        game_id=over.get("game_id", arts.game_id),
        players=over.get("players", arts.players),
        events=over.get("events", arts.events),
        decisions=over.get("decisions", arts.decisions),
        provider_turns=over.get("provider_turns", arts.provider_turns),
        result=over.get("result", arts.result),
        gaps=over.get("gaps", arts.gaps),
    )

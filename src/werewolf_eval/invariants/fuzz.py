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


# ---------------------------------------------------------------------------
# Engine-in-loop guard board generator (C3-3)
# ---------------------------------------------------------------------------
# The original SEED_BANK has no guard board -> I8a/I8b/I8c vacuously pass.
# This generator runs JointSettler (the real engine settlement component) to
# compute deaths, then builds RunArtifacts from the computed results. The
# checker validates against what the engine ACTUALLY produced - not hand-crafted
# synthetic events.
#
# Coverage target (audit C3-3): milk-pierce (I8b), guard block (I8a),
# guard-does-not-block-poison, hunter death cascade, consecutive guard (I8c).
#
# TODO: expand the seed space for more random shape coverage (currently covers
#  key combinatorial branches, not random Monte-Carlo).

_GUARD_ROLES = [
    ("p1", "seer", "villager"), ("p2", "witch", "villager"),
    ("p3", "hunter", "villager"), ("p4", "werewolf", "werewolf"),
    ("p5", "guard", "villager"), ("p6", "villager", "villager"),
]


def _guard_players() -> list[dict[str, Any]]:
    return [{"player_id": pid, "role": r, "team": t} for pid, r, t in _GUARD_ROLES]


def _guard_alive() -> frozenset[str]:
    return frozenset(pid for pid, _, _ in _GUARD_ROLES)


def _guard_roles_map() -> dict[str, str]:
    return {pid: r for pid, r, _ in _GUARD_ROLES}


def guard_board_game(seed: int) -> RunArtifacts:
    """Engine-in-loop: produces a well-formed guard board night whose shape varies
    by seed. Uses JointSettler to compute deaths -> builds RunArtifacts -> checker
    runs on real engine output. Must PASS every invariant (I8a/b/c included)."""
    from werewolf_eval.action_runtime.ruleset import rules_v1_2
    from werewolf_eval.action_runtime.settler import JointSettler, NightIntents
    from werewolf_eval.action_runtime.state import RuntimeState

    rng = random.Random(seed)
    settler = JointSettler(rules_v1_2())
    alive = _guard_alive()
    roles = _guard_roles_map()

    non_wolves = [pid for pid, r in roles.items() if r != "werewolf"]
    all_ids = list(roles)

    seq = 0
    events: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []

    def add(etype, actor, target, vis, phase="night", rnd=1):
        nonlocal seq
        seq += 1
        e = _ev(seq, etype, actor, target, vis, rnd=rnd, phase=phase)
        events.append(e)
        return e["event_id"]

    victim = rng.choice(non_wolves)
    guard_tgt = rng.choice(all_ids)
    saved = rng.choice([True, False])
    poison_tgt: str | None = rng.choice([None] + [p for p in non_wolves if p != "p2"])

    wk = add("werewolf_kill", "p4", victim, "werewolf_team")
    turns.append({"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
                  "observation_source_event_ids": [wk]})

    gp = add("guard_protect", "p5", guard_tgt, "guard")
    turns.append({"request_id": "g_r01_p5", "phase": "night", "actor": "p5",
                  "observation_source_event_ids": [gp]})

    if saved:
        sv = add("witch_save", "p2", victim, "witch")
        turns.append({"request_id": "g_r01_p2_save", "phase": "night", "actor": "p2",
                      "observation_source_event_ids": [sv]})
    if poison_tgt is not None:
        po = add("witch_poison", "p2", poison_tgt, "witch")
        turns.append({"request_id": "g_r01_p2_poison", "phase": "night", "actor": "p2",
                      "observation_source_event_ids": [po]})

    # engine-in-loop: JointSettler computes deaths
    intents = NightIntents(wolf_victim=victim, saved=saved,
                           poison_target=poison_tgt, guard_target=guard_tgt)
    result = settler.resolve_night(intents, RuntimeState(alive=alive, roles=roles))

    # seer_check (round 1, BEFORE deaths - keeps I2 and I4b exercised)
    seer_tgt = rng.choice([p for p in all_ids if p != "p1"])
    sc = add("seer_check", "p1", seer_tgt, "seer", rnd=1)
    turns.append({"request_id": "g_r01_p1", "phase": "night", "actor": "p1",
                  "observation_source_event_ids": [sc]})

    for death in result.deaths:
        add("player_died", "system", death, "all")

    # hunter_shoot (death cascade: if hunter is among victims, hunter shoots)
    hunter = "p3"
    if hunter in result.deaths:
        already_dying = set(result.deaths)
        candidates = [p for p in all_ids if p != hunter and p not in already_dying]
        if candidates:
            shoot_tgt = rng.choice(candidates)
            hs = add("hunter_shoot", hunter, shoot_tgt, "public", phase="night")
            turns.append({"request_id": "g_r01_p3_shoot", "phase": "night", "actor": hunter,
                          "observation_source_event_ids": [hs]})
            if shoot_tgt in alive:
                add("player_died", "system", shoot_tgt, "all")

    return RunArtifacts(game_id="g", players=_guard_players(), events=events,
                        decisions=[], provider_turns=turns, result=None)


def guard_board_known_bad() -> list[tuple[str, RunArtifacts, str]]:
    """Engine-in-loop known-bad guard scenarios. Each entry = (label, artifacts,
    expected_failing_invariant_id)."""
    out: list[tuple[str, RunArtifacts, str]] = []

    def build_artifacts(events, turns=None):
        return RunArtifacts(game_id="g", players=_guard_players(),
                            events=events, decisions=[],
                            provider_turns=turns or [], result=None)

    # I8a: guard blocked kill, but victim is marked died (violation)
    seq = 0
    events_i8a: list[dict[str, Any]] = []
    def _ea(etype, actor, target, vis, rnd=1):
        nonlocal seq
        seq += 1
        e = _ev(seq, etype, actor, target, vis, rnd=rnd)
        events_i8a.append(e)
        return e["event_id"]
    _ea("guard_protect", "p5", "p6", "guard")
    _ea("werewolf_kill", "p4", "p6", "werewolf_team")
    _ea("player_died", "system", "p6", "all")
    out.append(("i8a_blocked_kill_died", build_artifacts(events_i8a), "I8a"))

    # I8b: guard+save same target, but target survived (violation)
    seq = 0
    events_i8b: list[dict[str, Any]] = []
    def _eb(etype, actor, target, vis, rnd=1):
        nonlocal seq
        seq += 1
        e = _ev(seq, etype, actor, target, vis, rnd=rnd)
        events_i8b.append(e)
        return e["event_id"]
    _eb("guard_protect", "p5", "p6", "guard")
    _eb("werewolf_kill", "p4", "p6", "werewolf_team")
    _eb("witch_save", "p2", "p6", "witch")
    turns_i8b = [
        {"request_id": "g_r01_p4", "phase": "night", "actor": "p4",
         "observation_source_event_ids": [events_i8b[1]["event_id"]]},
        {"request_id": "g_r01_p5", "phase": "night", "actor": "p5",
         "observation_source_event_ids": [events_i8b[0]["event_id"]]},
        {"request_id": "g_r01_p2_save", "phase": "night", "actor": "p2",
         "observation_source_event_ids": [events_i8b[2]["event_id"]]},
    ]
    out.append(("i8b_milk_pierce_survived", build_artifacts(events_i8b, turns_i8b), "I8b"))

    # I8c: guard protects same target on consecutive nights (violation)
    seq = 0
    events_i8c: list[dict[str, Any]] = []
    def _ec(etype, actor, target, vis, rnd=1):
        nonlocal seq
        seq += 1
        e = _ev(seq, etype, actor, target, vis, rnd=rnd)
        events_i8c.append(e)
        return e["event_id"]
    _ec("guard_protect", "p5", "p6", "guard", rnd=1)
    _ec("guard_protect", "p5", "p6", "guard", rnd=2)
    out.append(("i8c_consecutive_same_target", build_artifacts(events_i8c), "I8c"))

    return out

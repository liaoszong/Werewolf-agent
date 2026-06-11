"""Read-only metrics over emergent-game artifacts. Pure functions; no side effects."""
from __future__ import annotations
import json, re, collections
from pathlib import Path

VISUAL_WORDS = ("眼神", "表情", "紧张", "躲闪", "支支吾吾", "语气", "闪躲")
MECHANIC_WORDS = ("警徽", "警长", "警上", "警下", "守卫", "守夜人")
LIVE_RATE_MIN = 0.7


def classify_event(ev: dict):
    """-> (kind, actor, target, extra). kind in {kill,check,witch_save,witch_pass,
    witch_poison,vote,elim,reveal,night_death,speech,other}."""
    s = (ev.get("data") or {}).get("summary", "") or ""
    actor, tgt, ph = ev.get("actor"), ev.get("target"), ev.get("phase")
    m = re.match(r"Wolf team kills (p\d)", s)
    if m: return ("kill", actor, m.group(1), None)
    m = re.match(r"Seer (p\d) checks (p\d), result: (\w+)", s)
    if m: return ("check", m.group(1), m.group(2), m.group(3))
    if "saves" in s:
        m = re.search(r"saves (p\d)", s); return ("witch_save", actor, m.group(1) if m else tgt, None)
    if "no potion" in s: return ("witch_pass", actor, None, None)
    if "poison" in s.lower():
        m = re.search(r"poisons? (p\d)", s); return ("witch_poison", actor, m.group(1) if m else tgt, None)
    m = re.match(r"(p\d) votes (p\d)", s)
    if m: return ("vote", m.group(1), m.group(2), None)
    if "eliminated by vote" in s: return ("elim", "system", tgt, None)
    m = re.search(r"(p\d) revealed as (\w+)", s)
    if m: return ("reveal", m.group(1), None, m.group(2))
    if "died during the night" in s: return ("night_death", "system", tgt, None)
    if ph == "day" and actor and re.match(r"p\d$", str(actor)) and "votes" not in s:
        return ("speech", actor, None, s)
    return ("other", actor, tgt, s)


def live_rate_from_turns(turns_doc) -> float:
    turns = turns_doc.get("turns") if isinstance(turns_doc, dict) else turns_doc
    if not turns: return 0.0
    return sum(1 for t in turns if t.get("kind") == "live_success") / len(turns)


def live_rate(run_dir: Path) -> float:
    p = Path(run_dir) / "provider-turns.json"
    if not p.exists(): return 0.0
    return live_rate_from_turns(json.loads(p.read_text(encoding="utf-8")))


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def aggregate_games(games: list[dict]) -> dict:
    """games = analyze_game_dict outputs of VALID (live) games only."""
    n = len(games)
    if n == 0: return {"n_valid": 0}
    def rate(pred): return sum(1 for g in games if pred(g)) / n
    d1 = [g["d1_majority_is_wolf"] for g in games if g["d1_majority_is_wolf"] is not None]
    d2 = [g.get("d2_majority_is_wolf") for g in games if g.get("d2_majority_is_wolf") is not None]
    vwf = [g["verify_wolf_followed"] for g in games if g["verify_wolf_followed"] is not None]
    tot_sp = sum(g["n_speeches"] for g in games) or 1
    kill_dist = collections.Counter(g["night1_kill"] for g in games if g["night1_kill"])
    return {
        "n_valid": n,
        "wolf_win_rate": rate(lambda g: g["winner"] == "werewolf"),
        "villager_win_rate": rate(lambda g: g["winner"] == "villager"),
        "day1_hit": (sum(d1)/len(d1)) if d1 else None,
        "day2_hit": (sum(d2)/len(d2)) if d2 else None,
        "verify_wolf_followed": (sum(vwf)/len(vwf)) if vwf else None,
        "verify_wolf_followed_n": len(vwf),
        "witch_save_rate": rate(lambda g: g["witch_save"]),
        "witch_poison_rate": rate(lambda g: g["witch_poison"]),
        "herding": _mean([g["herd_share"] for g in games]),
        "halluc_visual_speech_rate": sum(g["n_visual_speeches"] for g in games) / tot_sp,
        "halluc_visual_game_rate": rate(lambda g: g["has_visual_halluc"]),
        "halluc_mechanic_game_rate": rate(lambda g: g["has_mechanic_halluc"]),
        "seer_survives_d1_rate": rate(lambda g: g["seer_survives_d1"]),
        "avg_rounds": _mean([g["end_round"] for g in games]),
        "night1_kill_dist": dict(sorted(kill_dist.items())),
    }


def aggregate(run_dirs) -> dict:
    """Read run dirs, drop low-live (RNG) / incomplete / corrupt games, aggregate the valid ones."""
    run_dirs = [Path(d) for d in run_dirs]
    valid, invalid = [], 0
    for d in run_dirs:
        gl_path = d / "game-log.json"
        try:
            if not gl_path.exists() or live_rate(d) < LIVE_RATE_MIN:
                invalid += 1; continue
            gl = json.loads(gl_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            invalid += 1; continue
        if not (gl.get("result") or {}).get("winner"):
            invalid += 1; continue
        valid.append(analyze_game_dict(gl))
    out = aggregate_games(valid)
    out["n_total"] = len(run_dirs)
    out["n_invalid_lowlive"] = invalid
    return out


def analyze_game_dict(gl: dict) -> dict:
    roles = {p["player_id"]: p["role"] for p in gl["players"]}
    wolves = {k for k, v in roles.items() if v == "werewolf"}
    seer = next((k for k, v in roles.items() if v == "seer"), None)
    res = gl.get("result") or {}
    votes = collections.defaultdict(list)   # round -> [(voter,target)]
    speeches = []                            # (round, actor, text)
    kills, checks = {}, {}
    save = poison = False
    deaths = []                              # (round, pid, cause)
    for ev in gl["events"]:
        kind, a, t, extra = classify_event(ev)
        r = ev.get("round")
        if kind == "kill": kills[r] = t
        elif kind == "check": checks[r] = (t, extra)
        elif kind == "witch_save": save = True
        elif kind == "witch_poison": poison = True
        elif kind == "vote": votes[r].append((a, t))
        elif kind == "speech": speeches.append((r, a, extra))
        elif kind == "elim": deaths.append((r, t, "vote"))
        elif kind == "night_death": deaths.append((r, t, "night"))

    def majority(r):
        c = collections.Counter(t for _, t in votes.get(r, []))
        return c.most_common(1)[0] if c else (None, 0)

    d1, d1n = majority(1)
    seer_chk = checks.get(1)
    seer_chk_role = roles.get(seer_chk[0]) if seer_chk else None
    seer_death = next(((r, c) for (r, p, c) in deaths if p == seer), None)
    verify_wolf_followed = None
    if seer_chk and seer_chk[1] == "werewolf":
        verify_wolf_followed = (d1 == seer_chk[0])
    shares = []
    for r in votes:
        _, n = majority(r)
        tot = len(votes[r])
        if tot: shares.append(n / tot)
    text_all = " ".join(t for _, _, t in speeches)
    return {
        "roles": roles, "seer": seer, "wolves": sorted(wolves),
        "winner": res.get("winner"), "end_round": res.get("end_round"),
        "night1_kill": kills.get(1), "night1_kill_role": roles.get(kills.get(1)),
        "seer_r1_check": seer_chk, "seer_r1_target_role": seer_chk_role,
        "d1_majority": d1, "d1_majority_is_wolf": (d1 in wolves) if d1 else None,
        "d1_total": len(votes.get(1, [])),
        "d2_majority_is_wolf": (majority(2)[0] in wolves) if majority(2)[0] else None,
        "verify_wolf_followed": verify_wolf_followed,
        "witch_save": save, "witch_poison": poison,
        "seer_death_cause": seer_death[1] if seer_death else None,
        "seer_survives_d1": not (seer_death and seer_death[0] == 1),
        "herd_share": sum(shares) / len(shares) if shares else None,
        "has_visual_halluc": any(w in text_all for w in VISUAL_WORDS),
        "has_mechanic_halluc": any(w in text_all for w in MECHANIC_WORDS),
        "n_speeches": len(speeches),
        "n_visual_speeches": sum(1 for _, _, t in speeches if any(w in t for w in VISUAL_WORDS)),
        "n_mechanic_speeches": sum(1 for _, _, t in speeches if any(w in t for w in MECHANIC_WORDS)),
    }

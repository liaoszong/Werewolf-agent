"""Read-only metrics over emergent-game artifacts. Pure functions; no side effects."""
from __future__ import annotations
import json, re, collections
from pathlib import Path

from werewolf_eval.evaluation_versions import read_manifest_bucket

VISUAL_WORDS = ("眼神", "表情", "紧张", "躲闪", "支支吾吾", "语气", "闪躲")
MECHANIC_WORDS = ("警徽", "警长", "警上", "警下", "守卫", "守夜人")
# 守卫板上「守卫/守夜人」是真实机制,不是幻觉词(L4);非守卫板维持原词表
GUARD_BOARD_MECHANIC_WORDS = ("警徽", "警长", "警上", "警下")
LIVE_RATE_MIN = 0.7
SCAFFOLD_COVERAGE_MIN = 0.5  # arm purity, spec §5.2b; threshold adjustable, separate reporting NOT removable


def classify_event(ev: dict):
    """-> (kind, actor, target, extra). kind in {kill,check,witch_save,witch_pass,
    witch_poison,guard,hunter_shoot,hunter_pass,peaceful,vote,elim,reveal,night_death,speech,other}.
    NOTE: the p\\d patterns match single-digit seats only (p1-p9) — fine for 6p
    boards; a >9-seat board would silently drop events here."""
    s = (ev.get("data") or {}).get("summary", "") or ""
    actor, tgt, ph, etype = ev.get("actor"), ev.get("target"), ev.get("phase"), ev.get("type")
    if etype in {
        "werewolf_kill",
        "seer_check",
        "witch_save",
        "witch_pass",
        "witch_poison",
        "guard_protect",
        "hunter_shoot",
        "hunter_pass",
        "player_vote",
    }:
        by_type = {
            "werewolf_kill": "kill",
            "seer_check": "check",
            "witch_save": "witch_save",
            "witch_pass": "witch_pass",
            "witch_poison": "witch_poison",
            "guard_protect": "guard",
            "hunter_shoot": "hunter_shoot",
            "hunter_pass": "hunter_pass",
            "player_vote": "vote",
        }
        return (by_type[str(etype)], actor, tgt, None)
    m = re.match(r"Wolf team kills (p\d)", s)
    if m: return ("kill", actor, m.group(1), None)
    m = re.match(r"Seer (p\d) checks (p\d), result: (\w+)", s)
    if m: return ("check", m.group(1), m.group(2), m.group(3))
    # C12-11 phase guard: day-phase speeches that happen to mention night-action
    # keywords ("saves" / "no potion" / "poison") must NOT classify as witch
    # actions. `ph != "day"` preserves legacy phase-less events (None != "day").
    if "saves" in s and ph != "day":
        m = re.search(r"saves (p\d)", s); return ("witch_save", actor, m.group(1) if m else tgt, None)
    if "no potion" in s and ph != "day": return ("witch_pass", actor, None, None)
    if "poison" in s.lower() and ph != "day":
        m = re.search(r"poisons? (p\d)", s); return ("witch_poison", actor, m.group(1) if m else tgt, None)
    m = re.match(r"(p\d) votes (p\d)", s)
    if m: return ("vote", m.group(1), m.group(2), None)
    if "eliminated by vote" in s: return ("elim", "system", tgt, None)
    m = re.search(r"(p\d) revealed as (\w+)", s)
    if m: return ("reveal", m.group(1), None, m.group(2))
    m = re.match(r"Guard (p\d) protects (p\d)", s)
    if m: return ("guard", m.group(1), m.group(2), None)
    if "A peaceful night" in s: return ("peaceful", "system", None, None)
    if "died during the night" in s: return ("night_death", "system", tgt, None)
    if ph == "day" and actor and re.match(r"p\d$", str(actor)) and "votes" not in s:
        return ("speech", actor, None, s)
    return ("other", actor, tgt, s)


def live_rate_from_turns(turns_doc) -> float:
    turns = turns_doc.get("turns") if isinstance(turns_doc, dict) else turns_doc
    if turns is None:
        return 0.0
    player = [t for t in turns if t.get("response_kind") != "scaffold"]
    if not player:
        return 0.0
    return sum(1 for t in player if t.get("kind") == "live_success") / len(player)


def live_rate(run_dir: Path) -> float:
    p = Path(run_dir) / "provider-turns.json"
    if not p.exists(): return 0.0
    return live_rate_from_turns(json.loads(p.read_text(encoding="utf-8")))


def scaffold_coverage_from_turns(turns_doc):
    """scaffold_success / scaffold attempts; None when the game ran no scribe
    (non-v3 arms) so the validity gate is vacuous for them (spec §5.2b)."""
    turns = turns_doc.get("turns") if isinstance(turns_doc, dict) else (turns_doc or [])
    attempts = [t for t in turns if t.get("response_kind") == "scaffold"]
    if not attempts:
        return None
    return sum(1 for t in attempts if t.get("kind") == "scaffold_success") / len(attempts)


def scaffold_coverage(run_dir) -> float | None:
    p = Path(run_dir) / "provider-turns.json"
    if not p.exists():
        return None
    try:
        return scaffold_coverage_from_turns(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return None


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def aggregate_games(games: list[dict]) -> dict:
    """games = analyze_game_dict outputs of VALID (live) games only.

    P2-2: returns the full schema (all DEFAULT_COMPARE_KEYS present) even when
    `games` is empty, so downstream consumers can iterate keys without
    KeyError. Empty-set values are `None` for rates/means, `0` for counts,
    `{}` for distributions."""
    n = len(games)
    if n == 0:
        return {
            "n_valid": 0,
            "wolf_win_rate": None, "villager_win_rate": None,
            "day1_hit": None, "day2_hit": None,
            "verify_wolf_followed": None, "verify_wolf_followed_n": 0,
            "seer_voted_out_in_verify_cases": None,
            "witch_save_rate": None, "witch_poison_rate": None,
            "herding": None,
            "halluc_visual_speech_rate": None, "halluc_visual_game_rate": None,
            "halluc_mechanic_game_rate": None,
            "seer_survives_d1_rate": None, "avg_rounds": None,
            "night1_kill_dist": {},
            "guard_target_seer_rate": None, "guard_success_rate": None,
            "avg_peaceful_nights": None,
            "seer_death_rate": None, "seer_night_death_rate": None,
            "seer_claim_to_night_survival_rate": None,
            "seer_claim_to_night_survival_n": 0,
            "milk_pierce_overlap_count": 0, "milk_pierce_death_count": 0,
            "milk_pierce_overlap_rate": None, "milk_pierce_death_rate": None,
            "witch_save_night1_share": None,
        }
    def rate(pred): return sum(1 for g in games if pred(g)) / n
    d1 = [g["d1_majority_is_wolf"] for g in games if g["d1_majority_is_wolf"] is not None]
    d2 = [g.get("d2_majority_is_wolf") for g in games if g.get("d2_majority_is_wolf") is not None]
    vwf = [g["verify_wolf_followed"] for g in games if g["verify_wolf_followed"] is not None]
    svo = [g.get("verify_seer_voted_out") for g in games if g.get("verify_seer_voted_out") is not None]
    tot_sp = sum(g["n_speeches"] for g in games) or 1
    kill_dist = collections.Counter(g["night1_kill"] for g in games if g["night1_kill"])
    saved_games = [g for g in games if g.get("witch_save_round") is not None]
    return {
        "n_valid": n,
        "wolf_win_rate": rate(lambda g: g["winner"] == "werewolf"),
        "villager_win_rate": rate(lambda g: g["winner"] == "villager"),
        "day1_hit": (sum(d1)/len(d1)) if d1 else None,
        "day2_hit": (sum(d2)/len(d2)) if d2 else None,
        "verify_wolf_followed": (sum(vwf)/len(vwf)) if vwf else None,
        "verify_wolf_followed_n": len(vwf),
        "seer_voted_out_in_verify_cases": (sum(svo)/len(svo)) if svo else None,
        "witch_save_rate": rate(lambda g: g["witch_save"]),
        "witch_poison_rate": rate(lambda g: g["witch_poison"]),
        "herding": _mean([g["herd_share"] for g in games]),
        "halluc_visual_speech_rate": sum(g["n_visual_speeches"] for g in games) / tot_sp,
        "halluc_visual_game_rate": rate(lambda g: g["has_visual_halluc"]),
        "halluc_mechanic_game_rate": rate(lambda g: g["has_mechanic_halluc"]),
        "seer_survives_d1_rate": rate(lambda g: g["seer_survives_d1"]),
        "avg_rounds": _mean([g["end_round"] for g in games]),
        "night1_kill_dist": dict(sorted(kill_dist.items())),
        # ---- L4 guard arm + seer-survival family (spec §7) ----
        "guard_target_seer_rate": _mean([g.get("guard_target_seer_share") for g in games]),
        "guard_success_rate": _mean([g.get("guard_block_share") for g in games]),
        "avg_peaceful_nights": _mean([g.get("n_peaceful_nights") for g in games]),
        "seer_death_rate": rate(lambda g: g.get("seer_death") is not None),
        "seer_night_death_rate": rate(lambda g: (g.get("seer_death") or [None, None])[1] == "night"),
        "seer_claim_to_night_survival_rate": _mean(
            [g.get("seer_claimed_then_survived_night") for g in games]),
        "seer_claim_to_night_survival_n": sum(
            1 for g in games if g.get("seer_claimed_then_survived_night") is not None),
        # ---- v4 witch-coordination arm (spec 2026-06-12 §6); totals over the n_valid set ----
        # C12-03 alignment: per-game milk_pierce_{overlap,death} is None on
        # non-guard boards. `sum(... or 0)` preserves the historical total
        # (treating None as 0); the new _rate fields are the _mean-family
        # counterparts (None on non-guard arms, float on guard arms).
        "milk_pierce_overlap_count": sum(g.get("milk_pierce_overlap") or 0 for g in games),
        "milk_pierce_death_count": sum(g.get("milk_pierce_death") or 0 for g in games),
        "milk_pierce_overlap_rate": _mean([g.get("milk_pierce_overlap") for g in games]),
        "milk_pierce_death_rate": _mean([g.get("milk_pierce_death") for g in games]),
        "witch_save_night1_share": (
            sum(1 for g in saved_games if g["witch_save_round"] == 1) / len(saved_games)
        ) if saved_games else None,
    }


def aggregate(run_dirs) -> dict:
    """Read run dirs, drop low-live (RNG) / incomplete / corrupt games, aggregate the valid ones.

    C12-04: asserts all valid games share the same `evaluation_bucket` (read
    from each run's prompt-manifest.json). Mixed buckets within one arm raise
    `ValueError` — cross-bucket aggregation is silently meaningless. Legacy
    runs (no manifest → bucket=None) are tolerated only when ALL valid games
    are legacy; a mix of legacy and modern buckets is also an error.
    """
    run_dirs = [Path(d) for d in run_dirs]
    valid, invalid, invalid_scaffold = [], 0, 0
    valid_buckets: list[tuple[str, dict | None]] = []   # (run_dir_name, bucket)
    for d in run_dirs:
        gl_path = d / "game-log.json"
        try:
            if not gl_path.exists() or live_rate(d) < LIVE_RATE_MIN:
                invalid += 1; continue
            cov = scaffold_coverage(d)
            if cov is not None and cov < SCAFFOLD_COVERAGE_MIN:
                invalid_scaffold += 1; continue
            gl = json.loads(gl_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            invalid += 1; continue
        if not (gl.get("result") or {}).get("winner"):
            invalid += 1; continue
        row = analyze_game_dict(gl)
        row["run_dir"] = d.name
        row["scaffold_coverage"] = cov
        row["seer_claimed_then_survived_night"] = seer_claim_to_night_survival(d, row)
        valid.append(row)
        valid_buckets.append((d.name, read_manifest_bucket(d)))
    # C12-04 bucket assertion: all valid games must share one bucket.
    # P1-1: distinguish "no manifest" (legacy, tolerated) from "manifest exists
    # but bucket is None/missing" (corrupt, fail-loud). read_manifest_bucket
    # returns None for both cases, so we re-check file existence here.
    _LEGACY = "__LEGACY__"
    bucket_set: set[str] = set()
    bucket_by_run: dict[str, str] = {}   # run_dir_name -> canonical bucket key
    for run_name, b in valid_buckets:
        if b is not None:
            key = json.dumps(b, sort_keys=True)
        elif (Path(run_dirs[0].parent) / run_name / "prompt-manifest.json").exists():
            # Manifest exists but bucket is None → corrupt or missing bucket key.
            raise ValueError(
                f"evaluation_bucket invalid in {run_name}: prompt-manifest.json "
                f"exists but has no usable evaluation_bucket field"
            )
        else:
            key = _LEGACY
        bucket_set.add(key)
        bucket_by_run[run_name] = key
    if len(bucket_set) > 1:
        # P3-2: include run_dir→bucket mapping for easier live-batch diagnosis.
        seen = sorted(bucket_set)
        offenders = {rn: k for rn, k in bucket_by_run.items() if k != next(iter(bucket_set))}
        raise ValueError(
            f"evaluation_bucket mismatch within arm: {len(seen)} distinct buckets "
            f"across {len(valid_buckets)} valid games — buckets={seen}, "
            f"offending_runs={offenders}"
        )
    if bucket_set:
        only = next(iter(bucket_set))
        arm_bucket = None if only == _LEGACY else json.loads(only)
    else:
        arm_bucket = None
    out = aggregate_games(valid)
    out["games"] = valid
    out["n_total"] = len(run_dirs)
    out["n_invalid_lowlive"] = invalid
    out["n_invalid_scaffold"] = invalid_scaffold
    out["evaluation_bucket"] = arm_bucket
    return out


DEFAULT_COMPARE_KEYS = (
    "n_valid","wolf_win_rate","villager_win_rate","day1_hit","day2_hit",
    "verify_wolf_followed","seer_voted_out_in_verify_cases","witch_save_rate","witch_poison_rate","herding",
    "halluc_visual_speech_rate","halluc_visual_game_rate","halluc_mechanic_game_rate",
    "seer_survives_d1_rate","avg_rounds",
    "seer_death_rate","seer_night_death_rate","seer_claim_to_night_survival_rate",
    "guard_target_seer_rate","guard_success_rate","avg_peaceful_nights",
    "milk_pierce_overlap_count","milk_pierce_death_count",
    "milk_pierce_overlap_rate","milk_pierce_death_rate",
    "witch_save_night1_share",
)


def compare(a: dict, b: dict, keys=DEFAULT_COMPARE_KEYS) -> list[dict]:
    """Compare two aggregated metric dicts (armA vs armB), emitting delta rows."""
    rows = []
    for k in keys:
        va, vb = a.get(k), b.get(k)
        delta = (vb - va) if isinstance(va, (int, float)) and isinstance(vb, (int, float)) else None
        rows.append({"metric": k, "a": va, "b": vb, "delta": delta})
    return rows


def seer_claim_rounds(run_dir, seer: str) -> list[int]:
    """Rounds where the TRUE seer publicly claimed (any check_report, or an
    identity_claim whose result mentions 预言), parsed from the scribe turns in
    provider-trace.json. Real artifact shape (verified on .runs/ablation/b4):
    {"requests": [{actor, round, request_id, ...}], "responses": [{request_id,
    raw_content, ...}]} joined on request_id. Non-v3 runs (no scribe) -> []."""
    from werewolf_eval.prompt_v3 import parse_scribe_claims
    p = Path(run_dir) / "provider-trace.json"
    if not p.exists():
        return []
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(doc, dict):
        return []
    raw_by_id = {r.get("request_id"): r.get("raw_content")
                 for r in (doc.get("responses") or []) if isinstance(r, dict)}
    rounds: set[int] = set()
    for req in doc.get("requests") or []:
        if not isinstance(req, dict) or req.get("actor") != "scribe":
            continue
        claims = parse_scribe_claims(raw_by_id.get(req.get("request_id")) or "") or []
        for c in claims:
            if c["claimant"] != seer:
                continue
            if c["claim_type"] == "check_report" or (
                    c["claim_type"] == "identity_claim" and "预言" in str(c.get("result") or "")):
                rounds.add(int(req.get("round", 0)))
                break
    return sorted(rounds)


def seer_claim_to_night_survival(run_dir, row: dict) -> bool | None:
    """First public seer claim at round r: did the seer survive night r+1?
    None when no claim, no seer, or the game ended before night r+1 (no exposure)."""
    seer = row.get("seer")
    if not seer:
        return None
    rounds = seer_claim_rounds(run_dir, seer)
    if not rounds:
        return None
    r = rounds[0]
    if (row.get("end_round") or 0) <= r:
        return None
    sd = row.get("seer_death")
    return not (sd is not None and int(sd[0]) == r + 1 and sd[1] == "night")


def analyze_game_dict(gl: dict) -> dict:
    roles = {p["player_id"]: p["role"] for p in gl["players"]}
    teams = {
        p["player_id"]: p.get("team", "werewolf" if p.get("role") == "werewolf" else "villager")
        for p in gl["players"]
    }
    wolves = {pid for pid, team in teams.items() if team == "werewolf"}
    seer = next((k for k, v in roles.items() if v == "seer"), None)
    res = gl.get("result") or {}
    votes = collections.defaultdict(list)   # round -> [(voter,target)]
    speeches = []                            # (round, actor, text)
    kills, checks = {}, {}
    guards_by_round = {}                     # round -> guard target (L4)
    saves_by_round = {}                      # round -> saved target (v4 milk-pierce, spec 2026-06-12 §6)
    peaceful = 0
    save = poison = False
    deaths = []                              # (round, pid, cause)
    for ev in gl["events"]:
        kind, a, t, extra = classify_event(ev)
        r = ev.get("round")
        if kind == "kill": kills[r] = t
        elif kind == "check": checks[r] = (t, extra)
        elif kind == "witch_save":
            save = True
            if t is not None and re.match(r"p\d$", str(t)):
                saves_by_round[r] = t
        elif kind == "witch_poison": poison = True
        elif kind == "guard": guards_by_round[r] = t
        elif kind == "peaceful": peaceful += 1
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
    # SYS-B4 failure-chain metric: in a seer-checked-wolf game, did the day-1
    # majority vote out the TRUE SEER themself? (b1 baseline: 14/20 = 70%.)
    verify_seer_voted_out = None
    if seer_chk and seer_chk[1] == "werewolf" and d1 is not None:
        verify_seer_voted_out = (d1 == seer)
    shares = []
    for r in votes:
        _, n = majority(r)
        tot = len(votes[r])
        if tot: shares.append(n / tot)
    text_all = " ".join(t for _, _, t in speeches)
    has_guard = "guard" in roles.values()
    mech_words = GUARD_BOARD_MECHANIC_WORDS if has_guard else MECHANIC_WORDS
    gn = len(guards_by_round)
    overlap_rounds = [r for r, t in saves_by_round.items() if guards_by_round.get(r) == t]
    milk_death = sum(
        1 for r in overlap_rounds
        if any(dr == r and pid == saves_by_round[r] and cause == "night"
               for (dr, pid, cause) in deaths))
    # C12-03: non-guard boards have no milk-pierce mechanism — report None
    # (aligns with the guard_target_seer_rate/_mean family convention; compare
    # reads `None vs 0.28` as "no mechanism" instead of `0 vs 12` as "zero is
    # better"). Guard boards keep integer counts for backward compatibility.
    milk_overlap_val: int | None = len(overlap_rounds) if has_guard else None
    milk_death_val: int | None = milk_death if has_guard else None
    return {
        "roles": roles, "seer": seer, "wolves": sorted(wolves),
        "winner": res.get("winner"), "end_round": res.get("end_round"),
        "night1_kill": kills.get(1), "night1_kill_role": roles.get(kills.get(1)),
        "seer_r1_check": seer_chk, "seer_r1_target_role": seer_chk_role,
        "d1_majority": d1, "d1_majority_is_wolf": (d1 in wolves) if d1 else None,
        "d1_total": len(votes.get(1, [])),
        "d2_majority_is_wolf": (majority(2)[0] in wolves) if majority(2)[0] else None,
        "verify_wolf_followed": verify_wolf_followed,
        "verify_seer_voted_out": verify_seer_voted_out,
        "witch_save": save, "witch_poison": poison,
        "seer_death_cause": seer_death[1] if seer_death else None,
        "seer_death": list(seer_death) if seer_death else None,   # (round, cause) — claim 生存回算用
        "seer_survives_d1": not (seer_death and seer_death[0] == 1),
        "guard_nights": gn,
        "guard_target_seer_share": (sum(1 for t in guards_by_round.values() if t == seer) / gn) if gn else None,
        # TARGETING accuracy (守对率): guard target == that night's wolf target.
        # A milk-pierced night (guard+save -> death) still counts as a hit here —
        # this measures aiming, NOT survival; read verdict tables accordingly.
        "guard_block_share": (sum(1 for r2, t in guards_by_round.items() if kills.get(r2) == t) / gn) if gn else None,
        "n_peaceful_nights": peaceful,
        "witch_save_round": (min(saves_by_round) if saves_by_round else None),
        "milk_pierce_overlap": milk_overlap_val,
        "milk_pierce_death": milk_death_val,
        "herd_share": sum(shares) / len(shares) if shares else None,
        "has_visual_halluc": any(w in text_all for w in VISUAL_WORDS),
        "has_mechanic_halluc": any(w in text_all for w in mech_words),
        "n_speeches": len(speeches),
        "n_visual_speeches": sum(1 for _, _, t in speeches if any(w in t for w in VISUAL_WORDS)),
        "n_mechanic_speeches": sum(1 for _, _, t in speeches if any(w in t for w in mech_words)),
    }

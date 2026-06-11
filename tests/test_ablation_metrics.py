from pathlib import Path
from werewolf_eval.ablation.metrics import classify_event, analyze_game_dict, live_rate_from_turns, aggregate_games, aggregate, compare

def _ev(rnd, phase, actor, target, summary):
    return {"round": rnd, "phase": phase, "actor": actor, "target": target, "data": {"summary": summary}}

def test_classify_event_kinds():
    assert classify_event(_ev(1,"night","p4","p1","Wolf team kills p1."))[0] == "kill"
    assert classify_event(_ev(1,"night","p2","p1","Seer p2 checks p1, result: werewolf."))[0] == "check"
    assert classify_event(_ev(1,"night","p3",None,"Witch p3 saves p1."))[0] == "witch_save"
    assert classify_event(_ev(1,"night","p3",None,"Witch p3 uses no potion."))[0] == "witch_pass"
    assert classify_event(_ev(1,"night","p3","p5","Witch p3 poisons p5."))[0] == "witch_poison"
    assert classify_event(_ev(1,"day","p1","p3","p1 votes p3."))[0] == "vote"
    assert classify_event(_ev(1,"day","p1",None,"各位好，我怀疑p3。"))[0] == "speech"

def test_analyze_game_dict_basic():
    gl = {
        "players": [
            {"player_id":"p1","role":"seer","team":"villager"},
            {"player_id":"p2","role":"werewolf","team":"werewolf"},
            {"player_id":"p3","role":"villager","team":"villager"},
            {"player_id":"p4","role":"witch","team":"villager"},
            {"player_id":"p5","role":"werewolf","team":"werewolf"},
            {"player_id":"p6","role":"villager","team":"villager"},
        ],
        "result": {"winner":"villager","end_round":2},
        "events": [
            _ev(1,"night","p2","p1","Wolf team kills p1."),
            _ev(1,"night","p1","p2","Seer p1 checks p2, result: werewolf."),
            _ev(1,"night","p4",None,"Witch p4 saves p1."),
            _ev(1,"day","p1",None,"我验了p2是狼，投p2。他眼神躲闪。"),
            _ev(1,"day","p1","p2","p1 votes p2."),
            _ev(1,"day","p3","p2","p3 votes p2."),
            _ev(1,"day","p4","p2","p4 votes p2."),
            _ev(1,"day","p5","p1","p5 votes p1."),
            _ev(1,"day","p6","p2","p6 votes p2."),
        ],
    }
    g = analyze_game_dict(gl)
    assert g["winner"] == "villager"
    assert g["seer"] == "p1"
    assert g["night1_kill"] == "p1"
    assert g["seer_r1_check"] == ("p2","werewolf")
    assert g["witch_save"] is True and g["witch_poison"] is False
    assert g["d1_majority"] == "p2" and g["d1_majority_is_wolf"] is True
    assert g["verify_wolf_followed"] is True
    assert g["has_visual_halluc"] is True
    # 5 votes cast, p2 gets 4 -> herd share = 4/5
    assert abs(g["herd_share"] - 4/5) < 1e-9


def test_live_rate_from_turns():
    assert live_rate_from_turns({"turns":[{"kind":"live_success"}]*9 + [{"kind":"timeout_then_fallback"}]}) == 0.9
    assert live_rate_from_turns({"turns":[]}) == 0.0


def test_aggregate_filters_low_live_and_counts():
    g_win = {"winner":"villager","d1_majority_is_wolf":True,"verify_wolf_followed":True,
             "witch_save":True,"witch_poison":False,"herd_share":0.83,"has_visual_halluc":True,
             "has_mechanic_halluc":False,"n_speeches":6,"n_visual_speeches":2,"n_mechanic_speeches":0,
             "night1_kill":"p1","end_round":2,"seer_survives_d1":True}
    g_loss = dict(g_win); g_loss["winner"]="werewolf"; g_loss["d1_majority_is_wolf"]=False
    agg = aggregate_games([g_win, g_loss])
    assert agg["n_valid"] == 2
    assert agg["wolf_win_rate"] == 0.5
    assert agg["day1_hit"] == 0.5
    assert agg["witch_save_rate"] == 1.0 and agg["witch_poison_rate"] == 0.0


FIX = Path(__file__).parent / "fixtures" / "ablation"

def test_aggregate_reads_dirs_and_reports_invalid():
    run_dirs = sorted(p for p in FIX.iterdir() if p.is_dir())
    agg = aggregate(run_dirs)
    assert agg["n_total"] == 3
    assert agg["n_valid"] == 3              # all three fixtures are real live games (rate >= 0.89)
    assert agg["n_invalid_lowlive"] == 0
    assert abs(agg["villager_win_rate"] - 1/3) < 1e-9
    assert abs(agg["wolf_win_rate"] - 2/3) < 1e-9

def test_aggregate_counts_missing_and_corrupt_dirs_as_invalid(tmp_path):
    empty = tmp_path / "no_artifacts"; empty.mkdir()
    corrupt = tmp_path / "corrupt"; corrupt.mkdir()
    (corrupt / "game-log.json").write_text("{not json", encoding="utf-8")
    (corrupt / "provider-turns.json").write_text("{not json", encoding="utf-8")
    agg = aggregate([empty, corrupt])
    assert agg["n_total"] == 2
    assert agg["n_valid"] == 0
    assert agg["n_invalid_lowlive"] == 2

def test_compare_emits_deltas():
    a = {"label":"baseline","wolf_win_rate":0.78,"day1_hit":0.51,"halluc_visual_speech_rate":0.20}
    b = {"label":"b1","wolf_win_rate":0.55,"day1_hit":0.66,"halluc_visual_speech_rate":0.04}
    rows = compare(a, b, keys=["wolf_win_rate","day1_hit","halluc_visual_speech_rate"])
    d = {r["metric"]: r for r in rows}
    assert abs(d["wolf_win_rate"]["delta"] - (-0.23)) < 1e-9
    assert d["day1_hit"]["a"] == 0.51 and d["day1_hit"]["b"] == 0.66

def test_aggregate_emits_per_game_rows():
    run_dirs = sorted(p for p in FIX.iterdir() if p.is_dir())
    agg = aggregate(run_dirs)
    rows = agg["games"]
    assert len(rows) == 3
    assert {r["run_dir"] for r in rows} == {d.name for d in run_dirs}
    assert all("winner" in r and "herd_share" in r for r in rows)


from werewolf_eval.ablation.metrics import scaffold_coverage_from_turns

def test_live_rate_excludes_scaffold_turns():
    # spec §8.1 钉死测试:scribe turns 不得稀释玩家 live 率
    turns = [{"kind": "live_success"}] * 9 + [{"kind": "timeout_then_fallback"}] \
          + [{"kind": "scaffold_success", "response_kind": "scaffold"}] * 3 \
          + [{"kind": "scaffold_fallback", "response_kind": "scaffold"}]
    assert live_rate_from_turns({"turns": turns}) == 0.9      # 9/10,不是 9/14

def test_scaffold_coverage_from_turns():
    turns = [{"kind": "scaffold_success", "response_kind": "scaffold"},
             {"kind": "scaffold_fallback", "response_kind": "scaffold"},
             {"kind": "live_success"}]
    assert scaffold_coverage_from_turns({"turns": turns}) == 0.5
    assert scaffold_coverage_from_turns({"turns": [{"kind": "live_success"}]}) is None  # 非 v3 局

def test_aggregate_gates_low_scaffold_coverage(tmp_path):
    import json, shutil
    # 用真 fixture 复制一份,再伪造 scaffold turns:1 成功 3 失败 -> coverage 0.25 < 0.5
    src = FIX / "diag_A_seer_p2_3"
    bad = tmp_path / "low_cov"; shutil.copytree(src, bad)
    doc = json.loads((bad / "provider-turns.json").read_text(encoding="utf-8"))
    doc["turns"] += [{"kind": "scaffold_success", "response_kind": "scaffold", "live_requested": False}] \
                  + [{"kind": "scaffold_fallback", "response_kind": "scaffold", "live_requested": False}] * 3
    (bad / "provider-turns.json").write_text(json.dumps(doc), encoding="utf-8")
    ok = tmp_path / "good"; shutil.copytree(src, ok)
    agg = aggregate([bad, ok])
    assert agg["n_total"] == 2
    assert agg["n_valid"] == 1                 # low_cov 被臂纯度门剔除
    assert agg["n_invalid_scaffold"] == 1      # 单列计数(spec §8.9)
    assert agg["n_invalid_lowlive"] == 0
    assert agg["games"][0]["scaffold_coverage"] is None   # good 局非 v3 -> None


def test_verify_seer_voted_out_per_game_and_aggregate():
    # 验狼局,但多数票投向预言家自己(b1 失败链)
    gl = {
        "players": [
            {"player_id":"p1","role":"seer","team":"villager"},
            {"player_id":"p2","role":"werewolf","team":"werewolf"},
            {"player_id":"p3","role":"villager","team":"villager"},
            {"player_id":"p4","role":"witch","team":"villager"},
            {"player_id":"p5","role":"werewolf","team":"werewolf"},
            {"player_id":"p6","role":"villager","team":"villager"},
        ],
        "result": {"winner":"werewolf","end_round":2},
        "events": [
            {"round":1,"phase":"night","actor":"p1","target":"p2","data":{"summary":"Seer p1 checks p2, result: werewolf."}},
            {"round":1,"phase":"day","actor":"p2","target":"p1","data":{"summary":"p2 votes p1."}},
            {"round":1,"phase":"day","actor":"p3","target":"p1","data":{"summary":"p3 votes p1."}},
            {"round":1,"phase":"day","actor":"p5","target":"p1","data":{"summary":"p5 votes p1."}},
        ],
    }
    g = analyze_game_dict(gl)
    assert g["verify_wolf_followed"] is False
    assert g["verify_seer_voted_out"] is True          # 验狼局,多数票=预言家自己
    agg = aggregate_games([g])
    assert agg["seer_voted_out_in_verify_cases"] == 1.0
    # 非验狼局 -> None,不进分母
    g2 = dict(g); g2["verify_seer_voted_out"] = None; g2["verify_wolf_followed"] = None
    agg2 = aggregate_games([g, g2])
    assert agg2["seer_voted_out_in_verify_cases"] == 1.0

from werewolf_eval.ablation.metrics import classify_event, analyze_game_dict, live_rate_from_turns, aggregate_games

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

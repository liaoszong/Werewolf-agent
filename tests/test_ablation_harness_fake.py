from pathlib import Path
from werewolf_eval.ablation.arms import Arm
from werewolf_eval.ablation.harness import run_arm
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script


def build_fake_factory(arm, api_key):
    agents = build_emergent_fake_agents(build_villager_win_script())
    return lambda pid: agents[pid]


def test_run_arm_fake_smoke(tmp_path):
    arm = Arm(label="fake_smoke", prompt_version="prompt_v1", n_games=2, seed_base=7)
    result = run_arm(arm, out_root=tmp_path, factory_builder=build_fake_factory)
    assert result["arm"] == "fake_smoke"
    assert result["metrics"]["n_total"] == 2
    # Fake turns that return a usable action are recorded kind=="live_success"
    # (the engine has no fake/live concept), and the villager_win script's
    # 10/14 valid-action mix => live_rate 0.714 >= LIVE_RATE_MIN, so both fake
    # games PASS the live filter and enter behavior aggregates. This pins that
    # populated-aggregate path; the production filter still drops real RNG
    # fallbacks (timeout_then_fallback/invalid_then_fallback) which are NOT
    # live_success.
    assert result["metrics"]["n_valid"] == 2
    assert result["metrics"]["n_invalid_lowlive"] == 0
    assert (tmp_path / "fake_smoke" / "_metrics.json").exists()
    assert (tmp_path / "fake_smoke" / "_index.jsonl").exists()

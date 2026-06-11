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
    # fake games are not live -> filtered out; must not crash
    assert "n_valid" in result["metrics"]
    assert (tmp_path / "fake_smoke" / "_metrics.json").exists()
    assert (tmp_path / "fake_smoke" / "_index.jsonl").exists()

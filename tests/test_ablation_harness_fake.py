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


import pytest


def test_run_arm_rejects_unknown_prompt_version(tmp_path):
    # Unknown versions hard-fail before any side effects (no silent fallback).
    arm = Arm(label="bogus_arm", prompt_version="prompt_v99", n_games=1, seed_base=7)
    with pytest.raises(ValueError, match="prompt_version"):
        run_arm(arm, out_root=tmp_path, factory_builder=build_fake_factory)
    assert not (tmp_path / "bogus_arm").exists()


def test_run_arm_v2_smoke_threads_version(tmp_path):
    # prompt_v2 is now a real renderable arm (SYS-B1).
    arm = Arm(label="v2_smoke", prompt_version="prompt_v2", n_games=1, seed_base=7)
    result = run_arm(arm, out_root=tmp_path, factory_builder=build_fake_factory)
    assert result["prompt_version"] == "prompt_v2"
    assert (tmp_path / "v2_smoke" / "_metrics.json").exists()


def test_run_arm_v3_smoke_with_scaffold_factory(tmp_path):
    from fake_scribe import _FakeScribeProvider
    from werewolf_eval.provider_agent import ProviderAgent
    arm = Arm(label="v3_smoke", prompt_version="prompt_v3", n_games=1, seed_base=7)
    result = run_arm(arm, out_root=tmp_path, factory_builder=build_fake_factory,
                     scaffold_factory_builder=lambda a, k: (lambda: ProviderAgent("scribe", _FakeScribeProvider())))
    assert result["prompt_version"] == "prompt_v3"
    assert (tmp_path / "v3_smoke" / "_metrics.json").exists()

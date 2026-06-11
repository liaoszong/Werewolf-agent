"""SYS-B4 acceptance: a full fake game on prompt_v3 (scribe + injections) passes
ALL invariants (I1-I7 incl. I4b) over persisted artifacts — the injections are
derived from public speeches only, so the visibility oracle must stay green."""
import tempfile
import unittest
from pathlib import Path

from fake_scribe import _FakeScribeProvider
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script
from werewolf_eval.invariants.checker import check_run
from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game


class PromptV3InvariantsTests(unittest.TestCase):
    def test_v3_fake_game_passes_all_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            agents = build_emergent_fake_agents(build_villager_win_script())
            run_emergent_deepseek_game(
                game_id="v3_inv", out_dir=Path(d), provider_factory=lambda pid: agents[pid],
                model="none", seed=11, max_requests_per_game=80, max_day_rounds=3,
                prompt_version="prompt_v3",
                scaffold_provider_factory=lambda: ProviderAgent("scribe", _FakeScribeProvider()),
            )
            self.assertEqual(check_run(Path(d)), [])

    def test_v3_fake_game_with_broken_scribe_still_passes_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            agents = build_emergent_fake_agents(build_villager_win_script())
            run_emergent_deepseek_game(
                game_id="v3_inv_broken", out_dir=Path(d), provider_factory=lambda pid: agents[pid],
                model="none", seed=11, max_requests_per_game=80, max_day_rounds=3,
                prompt_version="prompt_v3",
                scaffold_provider_factory=lambda: ProviderAgent("scribe", _FakeScribeProvider(broken=True)),
            )
            self.assertEqual(check_run(Path(d)), [])

"""R-02 guard — the engine -> scoring -> attribution -> settlement seam.

Before this file NO test crossed that seam: `test_emergent_engine.py` never imported
`score_game`, and `test_scoring.py` only fed the gold fixture. That gap let the
`witch_kill` (emitted) vs `witch_poison` (consumed) vocabulary drift pass a 600+
green suite while silently zero-scoring every poison. These tests run a real
EmergentGameEngine and feed its OWN output through scoring + settlement, plus a
static registry check, so the whole emit/consume drift class can't reappear unseen.

Also covers R-04 (witch can never save): `augment_witch_observation` surfaces the
night's victim into the witch's prompt so a live witch can satisfy target==victim.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.attribution import attribute_game
from werewolf_eval.decision_log import parse_decision_log
from werewolf_eval.emergent_engine import (
    WITCH_POISON,
    WITCH_SAVE,
    EmergentGameEngine,
    augment_witch_observation,
    build_emergent_config,
)
from werewolf_eval.emergent_fake_script import (
    build_emergent_fake_agents,
    build_villager_win_script,
)
from werewolf_eval.game_log import parse_game_log
from werewolf_eval.scoring import (
    SCORE_RELEVANT_EVENT_TYPES,
    score_game,
    summarize_metrics,
)
from werewolf_eval.settlement_bundle import build_settlement_bundle


def _run_villager_win():
    # villager-win script ends night 2 via `witch_poison` (p4 poisons p2) — exactly the
    # poison action the vocab bug used to drop.
    engine = EmergentGameEngine(
        config=build_emergent_config(game_id="e2e_test"),
        agents=build_emergent_fake_agents(build_villager_win_script()),
        seed=0,
    )
    return engine.run()


class EngineToScoringSeamTests(unittest.TestCase):
    def test_engine_emits_witch_poison_and_scoring_consumes_it(self):
        outcome = _run_villager_win()
        self.assertEqual(outcome.status, "completed")
        game = parse_game_log(outcome.game_log)
        decision = parse_decision_log(outcome.decision_log, game)

        # the engine really emitted a witch_poison event...
        poison_events = [e for e in game.events if e.type == WITCH_POISON]
        self.assertTrue(poison_events, "engine should emit a witch_poison event")

        # ...and scoring CONSUMES it (the bug: scorer silently skipped the action).
        score_log = score_game(game, decision)
        poison_records = [r for r in score_log.records if r.action_type == WITCH_POISON]
        self.assertTrue(
            poison_records,
            "witch_poison emitted by the engine must produce a ScoreRecord (R-01/R-02)",
        )

    def test_settlement_bundle_reflects_engine_poison(self):
        outcome = _run_villager_win()
        game = parse_game_log(outcome.game_log)
        decision = parse_decision_log(outcome.decision_log, game)
        bundle = build_settlement_bundle(game, decision, run_id="e2e")

        self.assertFalse(bundle["degraded"])
        self.assertTrue(bundle["decision_quality_available"])
        # the poisoned wolf p2 is dead in the final board state
        self.assertNotIn("p2", bundle["board_timeline"][-1]["alive_player_ids"])
        # scoring ran end-to-end: at least one non-zero outcome score reached the bundle
        self.assertTrue(any(p["outcome_score"] != 0 for p in bundle["players"]))

    def test_attribution_runs_over_engine_output(self):
        outcome = _run_villager_win()
        game = parse_game_log(outcome.game_log)
        decision = parse_decision_log(outcome.decision_log, game)
        score_log = score_game(game, decision)
        metrics = summarize_metrics(game, score_log)
        # attribute_game must not raise on real engine output (the other half of the seam)
        attribution = attribute_game(game, score_log, metrics)
        self.assertIsNotNone(attribution.top_attribution)

    def test_witch_action_vocab_is_consumed_by_scoring(self):
        # Static registry guard: the engine's witch action constants must live in the
        # scorer's consumed set. This is the one comparison no test made before the
        # witch_kill/witch_poison drift shipped.
        self.assertIn(WITCH_SAVE, SCORE_RELEVANT_EVENT_TYPES)
        self.assertIn(WITCH_POISON, SCORE_RELEVANT_EVENT_TYPES)

    def test_every_emitted_event_type_has_a_display_label(self):
        # R-12/R-28 guard: any event type the engine can emit must have a Chinese
        # display label, or renderers show a raw English token. Exercise both arcs so
        # witch_pass / day_announcement etc. are all covered.
        from werewolf_eval.display_labels import TYPE_LABELS
        from werewolf_eval.emergent_fake_script import build_werewolf_win_script

        emitted: set[str] = set()
        for make in (build_villager_win_script, build_werewolf_win_script):
            engine = EmergentGameEngine(
                config=build_emergent_config(game_id="label_cov"),
                agents=build_emergent_fake_agents(make()),
                seed=0,
            )
            game = parse_game_log(engine.run().game_log)
            emitted |= {e.type for e in game.events}
        missing = sorted(emitted - set(TYPE_LABELS))
        self.assertEqual(missing, [], f"emitted event types with no display label: {missing}")


class WitchVictimVisibilityTests(unittest.TestCase):
    """R-04: the witch must be told tonight's victim (it is werewolf_team-visible and
    otherwise invisible to the witch), or `witch_save` (which requires target==victim)
    is structurally impossible for a live provider."""

    def test_victim_surfaced_into_witch_prompt(self):
        out = augment_witch_observation("BASE", "p5")
        self.assertIn("BASE", out)
        self.assertIn("p5", out)

    def test_no_victim_is_stated_explicitly(self):
        out = augment_witch_observation("BASE", None)
        self.assertIn("BASE", out)
        self.assertNotIn("p5", out)


if __name__ == "__main__":
    unittest.main()

# tests/test_action_runtime_turn.py
from __future__ import annotations
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.action_runtime.ruleset import rules_v1_1
from werewolf_eval.action_runtime.registry import RoleAbilityRegistry
from werewolf_eval.action_runtime.validator import ActionValidator
from werewolf_eval.action_runtime.state import RuntimeState
from werewolf_eval.action_runtime.turn import (
    DecisionWindow, SeerResolver, VoteResolver, WolfResolver, WolfWindow, RngPick,
)
from werewolf_eval.game_engine import AgentAction

ROLES = {"p1": "werewolf", "p2": "werewolf", "p3": "seer", "p4": "witch", "p5": "villager", "p6": "villager"}
VALIDATOR = ActionValidator(RoleAbilityRegistry(rules_v1_1()))
ALIVE = ("p1", "p2", "p3", "p4", "p5", "p6")


def _win(actor, role, emit_phase, registry_phase, action=None, target=None):
    la = None
    if action is not None:
        la = AgentAction(actor=actor, action=action, target=target, phase=emit_phase, round=1,
                         reason_summary="", decision_type="", confidence=1.0)
    return DecisionWindow(rnd=1, actor=actor, role=role, emit_phase=emit_phase, registry_phase=registry_phase,
                          alive_seat_order=ALIVE, roles=ROLES, public_refs=("r1",), live_action=la,
                          validator=VALIDATOR, runtime_state=RuntimeState(alive=frozenset(ALIVE), roles=dict(ROLES)))


class SeerResolverTests(unittest.TestCase):
    def test_legal_check_accepted(self):
        adj = SeerResolver().adjudicate(_win("p3", "seer", "night", "night", "seer_check", "p1"))
        self.assertEqual((adj.accepted_target, adj.decision_type, adj.rng_pick), ("p1", "inference_based", None))

    def test_self_check_falls_back_to_rng_over_others(self):
        adj = SeerResolver().adjudicate(_win("p3", "seer", "night", "night", "seer_check", "p3"))
        self.assertEqual(adj.decision_type, "default")
        self.assertEqual(adj.rng_pick, RngPick("choice", ("p1", "p2", "p4", "p5", "p6")))
        self.assertEqual(adj.failure.kind, "invalid_action")
        self.assertEqual(adj.downgrade_reason, "engine rejected seer_check p3")

    def test_provider_error_falls_back_no_failure_no_downgrade(self):
        adj = SeerResolver().adjudicate(_win("p3", "seer", "night", "night"))  # live_action=None
        self.assertEqual(adj.decision_type, "default")
        self.assertIsNone(adj.failure)
        self.assertIsNone(adj.downgrade_reason)

    def test_render_result_truthful(self):
        w = _win("p3", "seer", "night", "night", "seer_check", "p1")
        plan = SeerResolver().render(w, "p1", "inference_based")
        self.assertEqual(plan.event.summary, "Seer p3 checks p1, result: werewolf.")
        self.assertEqual(plan.decision.target, "p1")
        self.assertEqual(plan.decision.refs, ())  # seer decision carries no refs

    def test_render_result_uses_team_for_wolf_side_roles(self):
        roles = dict(ROLES)
        roles["p1"] = "wolf_variant"
        teams = {pid: "werewolf" if pid in {"p1", "p2"} else "villager" for pid in roles}
        w = DecisionWindow(
            rnd=1,
            actor="p3",
            role="seer",
            emit_phase="night",
            registry_phase="night",
            alive_seat_order=ALIVE,
            roles=roles,
            public_refs=("r1",),
            live_action=AgentAction(
                actor="p3",
                action="seer_check",
                target="p1",
                phase="night",
                round=1,
                reason_summary="",
                decision_type="",
                confidence=1.0,
            ),
            validator=VALIDATOR,
            runtime_state=RuntimeState(alive=frozenset(ALIVE), roles=roles, teams=teams),
        )
        plan = SeerResolver().render(w, "p1", "inference_based")
        self.assertEqual(plan.event.summary, "Seer p3 checks p1, result: werewolf.")


class VoteResolverTests(unittest.TestCase):
    def test_legal_vote_accepted_with_refs(self):
        plan = VoteResolver().render(_win("p5", "villager", "day", "day_vote", "player_vote", "p1"), "p1", "inference_based")
        self.assertEqual(plan.decision.phase, "day")            # EMIT phase (not day_vote)
        self.assertEqual(plan.decision.refs, ("r1",))           # vote decision carries public_refs
        self.assertEqual(plan.event.summary, "p5 votes p1.")

    def test_self_vote_falls_back(self):
        adj = VoteResolver().adjudicate(_win("p5", "villager", "day", "day_vote", "player_vote", "p5"))
        self.assertEqual(adj.rng_pick.kind, "choice")
        self.assertEqual(adj.failure.kind, "invalid_action")


class WolfResolverTests(unittest.TestCase):
    def _ww(self, proposals, candidates=("p3", "p4", "p5", "p6")):
        return WolfWindow(rnd=1, wolves=("p1", "p2"), proposals=tuple(proposals), candidates=candidates, consensus_id="c")

    def test_unanimous_is_consensus_no_rng(self):
        adj = WolfResolver().adjudicate(self._ww([("p1", "p5"), ("p2", "p5")]))
        self.assertEqual((adj.fixed_target, adj.status, adj.decision_type, adj.rng_pick), ("p5", "consensus", "team_coordinated", None))

    def test_split_single_majority_is_tiebreak_label_no_rng(self):
        adj = WolfResolver().adjudicate(self._ww([("p1", "p5"), ("p2", "p5"), ("p1", "p6")]))  # p5=2,p6=1
        self.assertEqual((adj.fixed_target, adj.status), ("p5", "coordinator_tie_break"))

    def test_two_leaders_uses_randrange_over_sorted_leaders(self):
        adj = WolfResolver().adjudicate(self._ww([("p1", "p6"), ("p2", "p5")]))  # p5,p6 tie
        self.assertEqual(adj.rng_pick, RngPick("randrange_index", ("p5", "p6")))
        self.assertEqual(adj.decision_type, "team_coordinated")

    def test_no_proposals_falls_back_over_candidates(self):
        adj = WolfResolver().adjudicate(self._ww([]))
        self.assertEqual(adj.rng_pick, RngPick("choice", ("p3", "p4", "p5", "p6")))
        self.assertTrue(adj.is_fallback)
        self.assertEqual(adj.decision_type, "default")

    def test_no_proposals_no_candidates_skips(self):
        self.assertTrue(WolfResolver().adjudicate(self._ww([], candidates=())).skip)

    def test_render_fallback_primary_is_first_wolf(self):
        r = WolfResolver().render(self._ww([]), "p5", is_fallback=True)
        self.assertEqual((r.primary, r.supporters, r.reason), ("p1", (), "fallback kill p5"))


if __name__ == "__main__":
    unittest.main()

import unittest

from werewolf_eval.agent_context_packet import (
    AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
    AgentContextPacketError,
    render_record_summary,
    select_visible_packet,
    validate_agent_context_packet,
    validate_memory_record,
)


def _record(
    record_id,
    *,
    kind,
    section,
    writer,
    visibility_scope,
    summary,
    render_mode,
    audience_scope=None,
    source_provenance=None,
    status="active",
    supersedes=None,
    trust_class="run_derived",
):
    record = {
        "record_id": record_id,
        "kind": kind,
        "section": section,
        "writer": writer,
        "visibility_scope": visibility_scope,
        "audience_scope": audience_scope or {"seat_ids": ["p1"]},
        "trust_class": trust_class,
        "render_mode": render_mode,
        "source_provenance": source_provenance
        or {"source_event_ids": ["evt_1"], "generated_by": "runtime"},
        "status": status,
        "summary": summary,
    }
    if supersedes is not None:
        record["supersedes"] = supersedes
    return record


def _packet(records):
    return {
        "schema_version": AGENT_CONTEXT_PACKET_SCHEMA_VERSION,
        "run_id": "run_1",
        "seat_id": "p1",
        "decision_id": "day1_speech_p1",
        "records": records,
        "context_budget": {
            "included_blocks": [],
            "compacted_blocks": [],
            "dropped_blocks": [],
        },
    }


class AgentContextPacketTests(unittest.TestCase):
    def test_accepts_minimal_memory_record_sections(self):
        records = [
            _record(
                "board_1",
                kind="FactRecord",
                section="board_facts",
                writer="engine",
                visibility_scope="public",
                audience_scope={"seat_ids": []},
                summary="six seats, werewolf team wins at parity",
                render_mode="control",
                source_provenance={
                    "static_source": "rules_v1_2",
                    "generated_by": "ruleset",
                },
            ),
            _record(
                "self_1",
                kind="FactRecord",
                section="self_facts",
                writer="runtime",
                visibility_scope="seat_private",
                summary="you are seat p1",
                render_mode="control",
            ),
            _record(
                "private_1",
                kind="FactRecord",
                section="private_facts",
                writer="runtime",
                visibility_scope="seat_private",
                summary="seer result visible to p1",
                render_mode="control",
            ),
            _record(
                "timeline_1",
                kind="ClaimRecord",
                section="public_timeline",
                writer="public_event",
                visibility_scope="public",
                audience_scope={"seat_ids": []},
                summary="p2 claimed seer",
                render_mode="quoted_evidence",
            ),
            _record(
                "note_1",
                kind="BeliefRecord",
                section="episodic_notes",
                writer="seat_agent",
                visibility_scope="seat_private",
                summary="p1 suspects p3",
                render_mode="state_summary",
            ),
        ]

        validate_agent_context_packet(_packet(records))

    def test_fact_record_requires_runtime_writer_and_provenance(self):
        valid = _record(
            "fact_1",
            kind="FactRecord",
            section="board_facts",
            writer="engine",
            visibility_scope="public",
            audience_scope={"seat_ids": []},
            summary="p3 is dead",
            render_mode="control",
            source_provenance={"source_event_ids": ["evt_death"], "generated_by": "runtime"},
        )

        rendered = render_record_summary(valid)

        self.assertEqual(rendered["fact_semantics"], "engine_fact")
        self.assertIn("trust_class", rendered)
        self.assertIn("render_mode", rendered)
        self.assertIn("visibility_scope", rendered)
        self.assertIn("source_provenance", rendered)

        for bad in [
            {**valid, "writer": "seat_agent"},
            {
                **valid,
                "source_provenance": {"generated_by": "runtime"},
            },
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises(AgentContextPacketError):
                    validate_memory_record(bad)

    def test_claim_and_belief_render_as_non_truth(self):
        claim = _record(
            "claim_1",
            kind="ClaimRecord",
            section="public_timeline",
            writer="public_event",
            visibility_scope="public",
            audience_scope={"seat_ids": []},
            summary="p2 claimed p4 is wolf",
            render_mode="quoted_evidence",
        )
        belief = _record(
            "belief_1",
            kind="BeliefRecord",
            section="episodic_notes",
            writer="seat_agent",
            visibility_scope="seat_private",
            summary="p1 suspects p4",
            render_mode="state_summary",
        )

        self.assertEqual(render_record_summary(claim)["fact_semantics"], "claim_only")
        self.assertIn("claimed", render_record_summary(claim)["text"])
        self.assertEqual(render_record_summary(belief)["fact_semantics"], "agent_belief")
        self.assertIn("currently believes", render_record_summary(belief)["text"])

    def test_commitment_and_team_plan_are_non_fact_records(self):
        commitment = _record(
            "commitment_1",
            kind="CommitmentRecord",
            section="commitments",
            writer="seat_agent",
            visibility_scope="public",
            audience_scope={"seat_ids": []},
            summary="p1 promised to vote p3",
            render_mode="state_summary",
        )
        team_plan = _record(
            "team_plan_1",
            kind="TeamPlanRecord",
            section="team_memory",
            writer="team_scaffold",
            visibility_scope="faction_private",
            audience_scope={"team_ids": ["werewolf"], "authorized_seat_ids": ["p1", "p2"]},
            summary="wolves pressure p4",
            render_mode="state_summary",
        )

        self.assertEqual(render_record_summary(commitment)["fact_semantics"], "non_fact")
        self.assertEqual(render_record_summary(team_plan)["fact_semantics"], "non_fact")

    def test_superseded_and_retracted_records_are_preserved(self):
        old = _record(
            "belief_old",
            kind="BeliefRecord",
            section="episodic_notes",
            writer="seat_agent",
            visibility_scope="seat_private",
            summary="p1 suspects p3",
            render_mode="state_summary",
            status="superseded",
        )
        new = _record(
            "belief_new",
            kind="BeliefRecord",
            section="episodic_notes",
            writer="seat_agent",
            visibility_scope="seat_private",
            summary="p1 no longer suspects p3",
            render_mode="state_summary",
            supersedes=["belief_old"],
        )

        selected = select_visible_packet(_packet([old, new]), seat_id="p1")

        self.assertEqual([record["record_id"] for record in selected["records"]], ["belief_old", "belief_new"])

    def test_team_plan_requires_faction_private_authorized_audience(self):
        team_plan = _record(
            "team_plan_1",
            kind="TeamPlanRecord",
            section="team_memory",
            writer="team_scaffold",
            visibility_scope="faction_private",
            audience_scope={"team_ids": ["werewolf"], "authorized_seat_ids": ["p1"]},
            summary="wolves pressure p4",
            render_mode="state_summary",
        )

        validate_memory_record(team_plan)

        for bad in [
            {**team_plan, "visibility_scope": "seat_private"},
            {**team_plan, "audience_scope": {"team_ids": ["werewolf"]}},
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises(AgentContextPacketError):
                    validate_memory_record(bad)

    def test_select_visible_packet_filters_scope_and_reports_budget(self):
        records = [
            _record(
                "public_1",
                kind="ClaimRecord",
                section="public_timeline",
                writer="public_event",
                visibility_scope="public",
                audience_scope={"seat_ids": []},
                summary="p2 claimed villager",
                render_mode="quoted_evidence",
            ),
            _record(
                "private_1",
                kind="BeliefRecord",
                section="episodic_notes",
                writer="seat_agent",
                visibility_scope="seat_private",
                audience_scope={"seat_ids": ["p1"]},
                summary="p1 suspects p2",
                render_mode="state_summary",
            ),
            _record(
                "other_private",
                kind="BeliefRecord",
                section="episodic_notes",
                writer="seat_agent",
                visibility_scope="seat_private",
                audience_scope={"seat_ids": ["p3"]},
                summary="p3 suspects p1",
                render_mode="state_summary",
            ),
            _record(
                "compact_1",
                kind="StaticPlaybookRecord",
                section="retrieved_playbook",
                writer="user_asset",
                visibility_scope="seat_private",
                audience_scope={"seat_ids": ["p1"]},
                trust_class="local_user",
                summary="as seer, reveal after useful chain",
                render_mode="guidance",
                source_provenance={
                    "static_source": "seer_playbook_v1",
                    "generated_by": "playbook_registry",
                },
            ),
        ]
        records[3]["trust_class"] = "local_user"

        selected = select_visible_packet(
            _packet(records),
            seat_id="p1",
            max_records=2,
            compacted_record_ids={"compact_1"},
        )

        self.assertEqual(
            [record["record_id"] for record in selected["records"]],
            ["public_1", "private_1", "compact_1"],
        )
        self.assertEqual(selected["context_budget"]["included_blocks"], ["public_1", "private_1"])
        self.assertEqual(selected["context_budget"]["compacted_blocks"], ["compact_1"])
        self.assertEqual(selected["context_budget"]["dropped_blocks"], ["other_private"])


if __name__ == "__main__":
    unittest.main()

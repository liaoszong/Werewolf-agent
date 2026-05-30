# S4 Consensus Log Runtime Input Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a Phase 2B Consensus Log runtime input path for werewolf night collaboration: a gold fixture, parser / validator, CLI validator, tests, and task/demo documentation updates.

**Architecture:** Follow the D1 Decision Log runtime skeleton pattern, but keep S4 independent from scoring and AI. The new Consensus Log parser validates one game-level file containing multiple consensus entries, each tied to a Game Log `game_id`, werewolf participants, visible event refs, proposals, responses, and one final night kill target. S4 does not feed scoring yet; it only establishes a stable collaboration-input contract that later G1 gameplay and S5 semantic work can consume.

**Tech Stack:** Python standard library only; existing `dataclasses`, `json`, `pathlib`, `unittest`; existing Game Log loader in `src/werewolf_eval/game_log.py`; JSON fixture under `docs/gold-game/`; tree refresh through `node .codex/hooks/tree.mjs --force`.

---

## Context

Current main facts after D2:

- E1 Game Log parser / validator exists in `src/werewolf_eval/game_log.py` and `src/werewolf_eval/validate_game_log.py`.
- D1 Decision Log runtime skeleton exists in `src/werewolf_eval/decision_log.py`, `src/werewolf_eval/validate_decision_log.py`, and `tests/test_decision_log.py`.
- D2 Decision Log scoring integration is merged; Decision Log can be passed into `score_game.py` / `render_demo.py`, but positive `decision_quality_score` still waits for S5.
- S4 is the next low-risk implementation unit after D2. It should validate the werewolf-team collaboration layer but must not change scoring, attribution, or demo rendering.

S4 implements the Consensus Log described in `docs/EVALUATION_RUBRIC.md` B.2 as a runtime input. Because a single game can contain more than one werewolf night, the concrete runtime file uses a game-level wrapper with `consensus_log_id`, `game_id`, `source_label`, and `consensuses: [...]`. Each item in `consensuses` follows the B.2 consensus object fields.

## Global Forbidden Scope

Do not implement any of the following in this S4 PR:

- No AI provider, prompt, model call, mock model, or semantic labeling pipeline.
- No S5 AI semantic labeling research or integration.
- No scoring integration from Consensus Log into `score_game`.
- No changes to `src/werewolf_eval/scoring.py`, `src/werewolf_eval/score_game.py`, `src/werewolf_eval/attribution.py`, or `src/werewolf_eval/render_demo.py`.
- No real AI Agent gameplay engine, round driver, provider adapter, or failure recovery loop.
- No real multi-game Leaderboard.
- No changes to `docs/EVALUATION_RUBRIC.md`.
- No claim that team coordination scoring is complete. S4 only validates Consensus Log input.

## Files Overview

Implementation PR should create or modify exactly these files:

- Create: `docs/gold-game/g001-consensus-log.json`
  - Gold Consensus Log fixture for the two werewolf night kill decisions in `g001`.

- Create: `src/werewolf_eval/consensus_log.py`
  - Dataclasses, parser, loader, validator, and validation error type for Consensus Log runtime input.

- Create: `src/werewolf_eval/validate_consensus_log.py`
  - CLI wrapper that loads Game Log + Consensus Log and prints a deterministic validation summary.

- Create: `tests/test_consensus_log.py`
  - Unit tests for happy path, schema validation, illegal actors, illegal refs, proposal/response constraints, and final target alignment.

- Modify: `docs/TASKS.md`
  - Mark S4 completed after all validation passes.
  - Add S4 UX acceptance row.
  - Add Demo 5 acceptance entry for Consensus Log validation.

- Modify: `.oh-my-harness/tree.md`
  - Refresh after new files are added by running `node .codex/hooks/tree.mjs --force`.

No other files should be modified.

---

### 任务 1：Add S4 Consensus Log fixture

**文件：**
- 创建：`docs/gold-game/g001-consensus-log.json`
- 测试：`tests/test_consensus_log.py`

- [ ] **步骤 1：创建 gold fixture**

创建 `docs/gold-game/g001-consensus-log.json`，内容如下：

```json
{
  "consensus_log_id": "s4_g001_consensus_log",
  "game_id": "g001",
  "source_label": "[人工 gold sample]",
  "consensuses": [
    {
      "consensus_id": "g001_c001",
      "game_id": "g001",
      "round": 1,
      "phase": "night",
      "team": "werewolf",
      "participants": ["p1", "p2"],
      "coordinator": "p1",
      "max_rounds": 3,
      "actual_rounds": 2,
      "status": "accepted_consensus",
      "proposals": [
        {
          "proposal_id": 1,
          "proposer": "p1",
          "proposed_target": "p5",
          "visible_info_refs": ["g001_e001", "g001_e002"],
          "reason_summary": "p5 is an unprotected-looking villager candidate and avoids directly challenging the claimed information holder.",
          "confidence": 0.66,
          "action_round": 1
        },
        {
          "proposal_id": 2,
          "proposer": "p2",
          "proposed_target": "p3",
          "visible_info_refs": ["g001_e001", "g001_e002"],
          "reason_summary": "p3 may become dangerous if allowed to speak, but killing p3 immediately could expose the wolf pair too early.",
          "confidence": 0.58,
          "action_round": 1
        }
      ],
      "responses": [
        {
          "response_id": 1,
          "to_proposal_id": 1,
          "responder": "p2",
          "response_type": "support_with_reason",
          "reason_summary": "p5 is a safer first-night target than p3 because it keeps the daytime framing path open.",
          "visible_info_refs": ["g001_e001", "g001_e002"],
          "action_round": 2
        }
      ],
      "final_decision": {
        "target": "p5",
        "decision_type": "accepted_consensus",
        "primary_proposer": "p1",
        "supporters": ["p1", "p2"],
        "dissenters": [],
        "resolution_round": 2
      }
    },
    {
      "consensus_id": "g001_c002",
      "game_id": "g001",
      "round": 2,
      "phase": "night",
      "team": "werewolf",
      "participants": ["p1", "p2"],
      "coordinator": "p1",
      "max_rounds": 3,
      "actual_rounds": 1,
      "status": "coordinator_tie_break",
      "proposals": [
        {
          "proposal_id": 1,
          "proposer": "p1",
          "proposed_target": "p5",
          "visible_info_refs": ["g001_e022", "g001_e023"],
          "reason_summary": "After p3 is eliminated and revealed as seer, killing p5 keeps pressure away from p1 before final daytime vote.",
          "confidence": 0.7,
          "action_round": 1
        },
        {
          "proposal_id": 2,
          "proposer": "p2",
          "proposed_target": "p6",
          "visible_info_refs": ["g001_e015"],
          "reason_summary": "p6 is a quiet villager who voted for p3 in round 1; eliminating p6 avoids the seer-hunting narrative while keeping pressure diffuse.",
          "confidence": 0.55,
          "action_round": 1
        }
      ],
      "responses": [],
      "final_decision": {
        "target": "p5",
        "decision_type": "coordinator_tie_break",
        "primary_proposer": "p1",
        "supporters": ["p1"],
        "dissenters": ["p2"],
        "resolution_round": 1
      }
    }
  ]
}
```

Rationale:

- `g001_c001.final_decision.target = "p5"` matches Game Log event `g001_e007`, the round 1 werewolf kill.
- `g001_c002.final_decision.target = "p5"` matches Game Log event `g001_e024`, the round 2 werewolf kill.
- Round 2 has both `p1` and `p2` as participants because `g001_e024` (werewolf kill, seq 24) occurs before `g001_e025` (witch poison on `p2`, seq 25); `p2` is still alive and able to participate in the round 2 kill consensus.
- Visible refs only use role-assignment refs for known werewolves and public refs already visible before the relevant final decision.

- [ ] **步骤 2：记录预期 fixture shape**

The fixture must use these top-level keys exactly:

```text
consensus_log_id
game_id
source_label
consensuses
```

Each consensus item must use these keys exactly:

```text
consensus_id
game_id
round
phase
team
participants
coordinator
max_rounds
actual_rounds
status
proposals
responses
final_decision
```

Expected validation summary after later tasks:

```text
validated consensus_log_id=s4_g001_consensus_log game_id=g001 consensuses=2 source_label=[人工 gold sample]
```

- [ ] **步骤 3：提交 fixture only**

```bash
git add docs/gold-game/g001-consensus-log.json
git commit -m "test: add S4 consensus log fixture"
```

Expected result:

```text
[task/s4-consensus-log-runtime-input <sha>] test: add S4 consensus log fixture
 1 file changed
 create mode 100644 docs/gold-game/g001-consensus-log.json
```

---

### 任务 2：Specify Consensus Log parser / validator tests

**文件：**
- 创建：`tests/test_consensus_log.py`
- 读取：`src/werewolf_eval/game_log.py`
- 读取：`docs/gold-game/g001-game-log.json`
- 读取：`docs/gold-game/g001-consensus-log.json`
- 测试：`tests/test_consensus_log.py`

- [ ] **步骤 1：创建 failing tests**

创建 `tests/test_consensus_log.py`，内容如下：

```python
from __future__ import annotations

import json
from pathlib import Path
import unittest

from werewolf_eval.game_log import load_game_log
from werewolf_eval.consensus_log import (
    ConsensusLogValidationError,
    load_consensus_log,
    parse_consensus_log,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class ConsensusLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = load_game_log(ROOT / "docs/gold-game/g001-game-log.json")
        self.raw = load_json("docs/gold-game/g001-consensus-log.json")

    def test_load_consensus_log_accepts_gold_fixture(self) -> None:
        consensus_log = load_consensus_log(ROOT / "docs/gold-game/g001-consensus-log.json", self.game)

        self.assertEqual(consensus_log.consensus_log_id, "s4_g001_consensus_log")
        self.assertEqual(consensus_log.game_id, "g001")
        self.assertEqual(consensus_log.source_label, "[人工 gold sample]")
        self.assertEqual(len(consensus_log.consensuses), 2)
        self.assertEqual(consensus_log.consensus_ids, {"g001_c001", "g001_c002"})
        self.assertEqual(consensus_log.consensuses[0].final_decision.target, "p5")

    def test_rejects_game_id_mismatch(self) -> None:
        raw = dict(self.raw)
        raw["game_id"] = "other_game"

        with self.assertRaisesRegex(ConsensusLogValidationError, "game_id mismatch"):
            parse_consensus_log(raw, self.game)

    def test_rejects_unknown_participant(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["participants"] = ["p1", "p9"]

        with self.assertRaisesRegex(ConsensusLogValidationError, "unknown participant"):
            parse_consensus_log(raw, self.game)

    def test_rejects_non_werewolf_participant(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["participants"] = ["p1", "p3"]

        with self.assertRaisesRegex(ConsensusLogValidationError, "participant must be werewolf"):
            parse_consensus_log(raw, self.game)

    def test_rejects_unknown_visible_info_ref(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["proposals"][0]["visible_info_refs"] = ["missing_event"]

        with self.assertRaisesRegex(ConsensusLogValidationError, "unknown visible_info_refs"):
            parse_consensus_log(raw, self.game)

    def test_rejects_too_many_discussion_rounds(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["actual_rounds"] = 4

        with self.assertRaisesRegex(ConsensusLogValidationError, "actual_rounds must be between 1 and max_rounds"):
            parse_consensus_log(raw, self.game)

    def test_rejects_reason_summary_over_150_chars(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["proposals"][0]["reason_summary"] = "x" * 151

        with self.assertRaisesRegex(ConsensusLogValidationError, "reason_summary exceeds 150 chars"):
            parse_consensus_log(raw, self.game)

    def test_rejects_response_to_unknown_proposal(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["responses"][0]["to_proposal_id"] = 99

        with self.assertRaisesRegex(ConsensusLogValidationError, "unknown to_proposal_id"):
            parse_consensus_log(raw, self.game)

    def test_rejects_final_target_that_does_not_match_werewolf_kill_event(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["final_decision"]["target"] = "p4"

        with self.assertRaisesRegex(ConsensusLogValidationError, "final target does not match werewolf_kill"):
            parse_consensus_log(raw, self.game)

    def test_rejects_invalid_status(self) -> None:
        raw = load_json("docs/gold-game/g001-consensus-log.json")
        raw["consensuses"][0]["status"] = "majority"

        with self.assertRaisesRegex(ConsensusLogValidationError, "invalid status"):
            parse_consensus_log(raw, self.game)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行 tests to confirm missing implementation**

```bash
PYTHONPATH=src python -m unittest tests.test_consensus_log
```

Expected result:

```text
ModuleNotFoundError: No module named 'werewolf_eval.consensus_log'
```

If the failure is not caused by the missing `consensus_log.py` module, stop and inspect whether S4 has already been partially implemented.

- [ ] **步骤 3：提交 failing tests**

```bash
git add tests/test_consensus_log.py
git commit -m "test: specify S4 consensus log validation"
```

Expected result:

```text
[task/s4-consensus-log-runtime-input <sha>] test: specify S4 consensus log validation
 1 file changed
 create mode 100644 tests/test_consensus_log.py
```

---

### 任务 3：Implement Consensus Log parser and validator

**文件：**
- 创建：`src/werewolf_eval/consensus_log.py`
- 测试：`tests/test_consensus_log.py`

- [ ] **步骤 1：创建 parser / validator module**

创建 `src/werewolf_eval/consensus_log.py`，内容如下：

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from werewolf_eval.game_log import GameLog

VALID_SOURCE_LABELS = {"[人工 gold sample]", "[AI 生成]"}
VALID_CONSENSUS_PHASES = {"night"}
VALID_TEAMS = {"werewolf"}
VALID_CONSENSUS_STATUSES = {
    "consensus",
    "accepted_consensus",
    "coordinator_tie_break",
    "forced_random",
}
VALID_RESPONSE_TYPES = {
    "support_with_reason",
    "oppose_with_reason",
    "revise_target",
    "abstain",
}
MAX_REASON_SUMMARY_CHARS = 150


@dataclass(frozen=True)
class ConsensusProposal:
    proposal_id: int
    proposer: str
    proposed_target: str
    visible_info_refs: list[str]
    reason_summary: str
    confidence: float | None


@dataclass(frozen=True)
class ConsensusResponse:
    response_id: int
    to_proposal_id: int
    responder: str
    response_type: str
    reason_summary: str
    visible_info_refs: list[str]


@dataclass(frozen=True)
class FinalConsensusDecision:
    target: str
    decision_type: str
    primary_proposer: str
    supporters: list[str]
    dissenters: list[str]
    resolution_round: int


@dataclass(frozen=True)
class Consensus:
    consensus_id: str
    game_id: str
    round: int
    phase: str
    team: str
    participants: list[str]
    coordinator: str
    max_rounds: int
    actual_rounds: int
    status: str
    proposals: list[ConsensusProposal]
    responses: list[ConsensusResponse]
    final_decision: FinalConsensusDecision


@dataclass(frozen=True)
class ConsensusLog:
    consensus_log_id: str
    game_id: str
    source_label: str
    consensuses: list[Consensus]

    @property
    def consensus_ids(self) -> set[str]:
        return {consensus.consensus_id for consensus in self.consensuses}


class ConsensusLogValidationError(ValueError):
    """Raised when a Consensus Log cannot be accepted as a Phase 2 runtime input."""


def load_consensus_log(path: str | Path, game: GameLog) -> ConsensusLog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("Consensus Log root must be an object")
    return parse_consensus_log(raw, game)


def parse_consensus_log(raw: dict[str, Any], game: GameLog) -> ConsensusLog:
    required_top_level = {"consensus_log_id", "game_id", "source_label", "consensuses"}
    missing = required_top_level - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"missing top-level fields: {sorted(missing)}")

    if not isinstance(raw["consensuses"], list):
        raise ConsensusLogValidationError("consensuses must be a list")

    consensus_log = ConsensusLog(
        consensus_log_id=str(raw["consensus_log_id"]),
        game_id=str(raw["game_id"]),
        source_label=str(raw["source_label"]),
        consensuses=[_parse_consensus(item) for item in raw["consensuses"]],
    )
    validate_consensus_log(consensus_log, game)
    return consensus_log


def validate_consensus_log(consensus_log: ConsensusLog, game: GameLog) -> None:
    if not consensus_log.consensus_log_id:
        raise ConsensusLogValidationError("consensus_log_id must not be empty")

    if consensus_log.game_id != game.game_id:
        raise ConsensusLogValidationError(
            f"game_id mismatch: consensus log {consensus_log.game_id!r} != game {game.game_id!r}"
        )

    if consensus_log.source_label not in VALID_SOURCE_LABELS:
        raise ConsensusLogValidationError(f"invalid source_label: {consensus_log.source_label!r}")

    consensus_ids = [consensus.consensus_id for consensus in consensus_log.consensuses]
    if len(set(consensus_ids)) != len(consensus_ids):
        raise ConsensusLogValidationError("consensus_id values must be unique")

    for consensus in consensus_log.consensuses:
        _validate_consensus(consensus, game)


def _parse_consensus(raw: Any) -> Consensus:
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("consensus entries must be objects")

    required_fields = {
        "consensus_id",
        "game_id",
        "round",
        "phase",
        "team",
        "participants",
        "coordinator",
        "max_rounds",
        "actual_rounds",
        "status",
        "proposals",
        "responses",
        "final_decision",
    }
    missing = required_fields - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"consensus missing fields: {sorted(missing)}")

    participants = raw["participants"]
    proposals = raw["proposals"]
    responses = raw["responses"]
    if not isinstance(participants, list):
        raise ConsensusLogValidationError("participants must be a list")
    if not isinstance(proposals, list):
        raise ConsensusLogValidationError("proposals must be a list")
    if not isinstance(responses, list):
        raise ConsensusLogValidationError("responses must be a list")

    return Consensus(
        consensus_id=str(raw["consensus_id"]),
        game_id=str(raw["game_id"]),
        round=int(raw["round"]),
        phase=str(raw["phase"]),
        team=str(raw["team"]),
        participants=[str(participant) for participant in participants],
        coordinator=str(raw["coordinator"]),
        max_rounds=int(raw["max_rounds"]),
        actual_rounds=int(raw["actual_rounds"]),
        status=str(raw["status"]),
        proposals=[_parse_proposal(item) for item in proposals],
        responses=[_parse_response(item) for item in responses],
        final_decision=_parse_final_decision(raw["final_decision"]),
    )


def _parse_proposal(raw: Any) -> ConsensusProposal:
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("proposal entries must be objects")

    required_fields = {"proposal_id", "proposer", "proposed_target", "visible_info_refs", "reason_summary"}
    missing = required_fields - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"proposal missing fields: {sorted(missing)}")

    visible_info_refs = raw["visible_info_refs"]
    if not isinstance(visible_info_refs, list):
        raise ConsensusLogValidationError("proposal visible_info_refs must be a list")

    confidence = raw.get("confidence")
    if confidence is not None:
        confidence = float(confidence)

    return ConsensusProposal(
        proposal_id=int(raw["proposal_id"]),
        proposer=str(raw["proposer"]),
        proposed_target=str(raw["proposed_target"]),
        visible_info_refs=[str(ref) for ref in visible_info_refs],
        reason_summary=str(raw["reason_summary"]),
        confidence=confidence,
    )


def _parse_response(raw: Any) -> ConsensusResponse:
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("response entries must be objects")

    required_fields = {"response_id", "to_proposal_id", "responder", "response_type", "reason_summary", "visible_info_refs"}
    missing = required_fields - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"response missing fields: {sorted(missing)}")

    visible_info_refs = raw["visible_info_refs"]
    if not isinstance(visible_info_refs, list):
        raise ConsensusLogValidationError("response visible_info_refs must be a list")

    return ConsensusResponse(
        response_id=int(raw["response_id"]),
        to_proposal_id=int(raw["to_proposal_id"]),
        responder=str(raw["responder"]),
        response_type=str(raw["response_type"]),
        reason_summary=str(raw["reason_summary"]),
        visible_info_refs=[str(ref) for ref in visible_info_refs],
    )


def _parse_final_decision(raw: Any) -> FinalConsensusDecision:
    if not isinstance(raw, dict):
        raise ConsensusLogValidationError("final_decision must be an object")

    required_fields = {"target", "decision_type", "primary_proposer", "supporters", "dissenters", "resolution_round"}
    missing = required_fields - set(raw)
    if missing:
        raise ConsensusLogValidationError(f"final_decision missing fields: {sorted(missing)}")

    supporters = raw["supporters"]
    dissenters = raw["dissenters"]
    if not isinstance(supporters, list):
        raise ConsensusLogValidationError("final_decision supporters must be a list")
    if not isinstance(dissenters, list):
        raise ConsensusLogValidationError("final_decision dissenters must be a list")

    return FinalConsensusDecision(
        target=str(raw["target"]),
        decision_type=str(raw["decision_type"]),
        primary_proposer=str(raw["primary_proposer"]),
        supporters=[str(supporter) for supporter in supporters],
        dissenters=[str(dissenter) for dissenter in dissenters],
        resolution_round=int(raw["resolution_round"]),
    )


def _validate_consensus(consensus: Consensus, game: GameLog) -> None:
    if not consensus.consensus_id:
        raise ConsensusLogValidationError("consensus_id must not be empty")

    if consensus.game_id != game.game_id:
        raise ConsensusLogValidationError(
            f"{consensus.consensus_id}: game_id mismatch: {consensus.game_id!r} != {game.game_id!r}"
        )

    if consensus.phase not in VALID_CONSENSUS_PHASES:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid phase {consensus.phase!r}")

    if consensus.team not in VALID_TEAMS:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid team {consensus.team!r}")

    if consensus.status not in VALID_CONSENSUS_STATUSES:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid status {consensus.status!r}")

    if not 1 <= consensus.max_rounds <= 3:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: max_rounds must be between 1 and 3")

    if not 1 <= consensus.actual_rounds <= consensus.max_rounds:
        raise ConsensusLogValidationError(
            f"{consensus.consensus_id}: actual_rounds must be between 1 and max_rounds"
        )

    if not consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: participants must not be empty")

    if len(set(consensus.participants)) != len(consensus.participants):
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: participants must be unique")

    if consensus.coordinator not in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: coordinator must be a participant")

    players = {player.player_id: player for player in game.players}
    for participant in consensus.participants:
        if participant not in players:
            raise ConsensusLogValidationError(f"{consensus.consensus_id}: unknown participant {participant!r}")
        if players[participant].team != "werewolf":
            raise ConsensusLogValidationError(f"{consensus.consensus_id}: participant must be werewolf: {participant!r}")

    proposal_ids = [proposal.proposal_id for proposal in consensus.proposals]
    if len(set(proposal_ids)) != len(proposal_ids):
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: proposal_id values must be unique")

    # Rubric B.2: each wolf may make at most 1 proposal and at most 1 response per round.
    proposer_counts: dict[str, int] = {}
    for proposal in consensus.proposals:
        proposer_counts[proposal.proposer] = proposer_counts.get(proposal.proposer, 0) + 1
    for proposer, count in proposer_counts.items():
        if count > 1:
            raise ConsensusLogValidationError(
                f"{consensus.consensus_id}: participant {proposer} has {count} proposals; max 1 per round"
            )
    responder_counts: dict[str, int] = {}
    for response in consensus.responses:
        responder_counts[response.responder] = responder_counts.get(response.responder, 0) + 1
    for responder, count in responder_counts.items():
        if count > 1:
            raise ConsensusLogValidationError(
                f"{consensus.consensus_id}: participant {responder} has {count} responses; max 1 per round"
            )

    for proposal in consensus.proposals:
        _validate_proposal(consensus, proposal, game)

    for response in consensus.responses:
        _validate_response(consensus, response, set(proposal_ids), game)

    _validate_final_decision(consensus, game)


def _validate_proposal(consensus: Consensus, proposal: ConsensusProposal, game: GameLog) -> None:
    if proposal.proposal_id < 1:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: proposal_id must be >= 1")

    if proposal.proposer not in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: proposer must be a participant")

    if proposal.proposed_target not in game.player_ids:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: unknown proposed_target {proposal.proposed_target!r}")

    if proposal.proposed_target in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: proposed_target must not be a werewolf participant")

    _validate_reason_summary(consensus.consensus_id, proposal.reason_summary)
    _validate_visible_info_refs(consensus.consensus_id, proposal.visible_info_refs, game, consensus.round)

    if proposal.confidence is not None and not 0.0 <= proposal.confidence <= 1.0:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: confidence must be between 0 and 1")


def _validate_response(
    consensus: Consensus,
    response: ConsensusResponse,
    proposal_ids: set[int],
    game: GameLog,
) -> None:
    if response.response_id < 1:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: response_id must be >= 1")

    if response.to_proposal_id not in proposal_ids:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: unknown to_proposal_id {response.to_proposal_id}")

    if response.responder not in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: responder must be a participant")

    if response.response_type not in VALID_RESPONSE_TYPES:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid response_type {response.response_type!r}")

    _validate_reason_summary(consensus.consensus_id, response.reason_summary)
    _validate_visible_info_refs(consensus.consensus_id, response.visible_info_refs, game, consensus.round)


def _validate_final_decision(consensus: Consensus, game: GameLog) -> None:
    decision = consensus.final_decision

    if decision.decision_type not in VALID_CONSENSUS_STATUSES:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: invalid final decision_type {decision.decision_type!r}")

    if decision.decision_type != consensus.status:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: status must match final decision_type")

    if decision.primary_proposer not in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: primary_proposer must be a participant")

    for supporter in decision.supporters:
        if supporter not in consensus.participants:
            raise ConsensusLogValidationError(f"{consensus.consensus_id}: supporter must be a participant")

    for dissenter in decision.dissenters:
        if dissenter not in consensus.participants:
            raise ConsensusLogValidationError(f"{consensus.consensus_id}: dissenter must be a participant")

    if set(decision.supporters) & set(decision.dissenters):
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: supporter cannot also be dissenter")

    if not 1 <= decision.resolution_round <= consensus.actual_rounds:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: resolution_round must be within actual_rounds")

    if decision.target not in game.player_ids:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: unknown final target {decision.target!r}")

    if decision.target in consensus.participants:
        raise ConsensusLogValidationError(f"{consensus.consensus_id}: final target must not be a werewolf participant")

    matching_kill = next(
        (
            event
            for event in game.events
            if event.type == "werewolf_kill"
            and event.round == consensus.round
            and event.phase == consensus.phase
            and event.target == decision.target
        ),
        None,
    )
    if matching_kill is None:
        raise ConsensusLogValidationError(
            f"{consensus.consensus_id}: final target does not match werewolf_kill event for round {consensus.round}"
        )


def _validate_reason_summary(consensus_id: str, reason_summary: str) -> None:
    if not reason_summary:
        raise ConsensusLogValidationError(f"{consensus_id}: reason_summary must not be empty")
    if len(reason_summary) > MAX_REASON_SUMMARY_CHARS:
        raise ConsensusLogValidationError(f"{consensus_id}: reason_summary exceeds 150 chars")


def _validate_visible_info_refs(consensus_id: str, visible_info_refs: list[str], game: GameLog, round: int) -> None:
    unknown_refs = set(visible_info_refs) - game.event_ids
    if unknown_refs:
        raise ConsensusLogValidationError(f"{consensus_id}: unknown visible_info_refs: {sorted(unknown_refs)}")

    for ref in visible_info_refs:
        event = game.event_by_id(ref)
        if event.visibility in {"public", "all", "werewolf_team"}:
            continue
        if event.visibility == "specific_player_ids":
            player = next((p for p in game.players if p.player_id == event.target), None)
            if player is not None and player.team == "werewolf":
                continue
        raise ConsensusLogValidationError(
            f"{consensus_id}: visible_info_ref {ref} has visibility {event.visibility!r}, "
            f"not visible to werewolf team"
        )

    kill_event = next(
        (e for e in game.events if e.type == "werewolf_kill" and e.round == round),
        None,
    )
    if kill_event is not None:
        for ref in visible_info_refs:
            if game.event_by_id(ref).sequence >= kill_event.sequence:
                raise ConsensusLogValidationError(
                    f"{consensus_id}: visible_info_ref {ref} (seq {game.event_by_id(ref).sequence}) "
                    f"is not before werewolf_kill {kill_event.event_id} (seq {kill_event.sequence})"
                )
```

- [ ] **步骤 2：运行 focused Consensus Log tests**

```bash
PYTHONPATH=src python -m unittest tests.test_consensus_log
```

Expected result:

```text
Ran 10 tests

OK
```

- [ ] **步骤 3：提交 parser / validator**

```bash
git add src/werewolf_eval/consensus_log.py tests/test_consensus_log.py
git commit -m "feat: add S4 consensus log validator"
```

Expected result:

```text
[task/s4-consensus-log-runtime-input <sha>] feat: add S4 consensus log validator
 2 files changed
 create mode 100644 src/werewolf_eval/consensus_log.py
```

---

### 任务 4：Add Consensus Log CLI validator

**文件：**
- 创建：`src/werewolf_eval/validate_consensus_log.py`
- 测试：`tests/test_consensus_log.py`

- [ ] **步骤 1：创建 CLI module**

创建 `src/werewolf_eval/validate_consensus_log.py`，内容如下：

```python
from __future__ import annotations

import argparse

from werewolf_eval.consensus_log import ConsensusLogValidationError, load_consensus_log
from werewolf_eval.game_log import GameLogValidationError, load_game_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Consensus Log JSON file.")
    parser.add_argument("path", help="Path to Consensus Log JSON")
    parser.add_argument("game_log_path", help="Path to Game Log JSON")
    args = parser.parse_args()

    try:
        game = load_game_log(args.game_log_path)
        consensus_log = load_consensus_log(args.path, game)
    except (ConsensusLogValidationError, GameLogValidationError, OSError, ValueError) as exc:
        print(f"invalid consensus log: {exc}")
        return 1

    print(
        "validated "
        f"consensus_log_id={consensus_log.consensus_log_id} "
        f"game_id={consensus_log.game_id} "
        f"consensuses={len(consensus_log.consensuses)} "
        f"source_label={consensus_log.source_label}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 2：Run CLI happy path**

```bash
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/gold-game/g001-consensus-log.json docs/gold-game/g001-game-log.json
```

Expected result:

```text
validated consensus_log_id=s4_g001_consensus_log game_id=g001 consensuses=2 source_label=[人工 gold sample]
```

- [ ] **步骤 3：Run full test suite**

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

Expected result:

```text
Ran 45 tests

OK
```

The exact total is expected to be current 35 tests plus 10 S4 tests. If additional tests were added on main after this plan, the total may be higher, but the result must still be `OK`.

- [ ] **步骤 4：提交 CLI**

```bash
git add src/werewolf_eval/validate_consensus_log.py
git commit -m "feat: add S4 consensus log CLI validator"
```

Expected result:

```text
[task/s4-consensus-log-runtime-input <sha>] feat: add S4 consensus log CLI validator
 1 file changed
 create mode 100644 src/werewolf_eval/validate_consensus_log.py
```

---

### 任务 5：Update TASKS acceptance and refresh tree

**文件：**
- 修改：`docs/TASKS.md`
- 修改：`.oh-my-harness/tree.md`
- 测试：`tests/test_consensus_log.py`

- [ ] **步骤 1：Update S4 task status in `docs/TASKS.md`**

Replace the S4 section:

```markdown
### S4：Consensus Log runtime/input

- 状态：`candidate_after_D2`（Phase 2B collaboration input）
- 依赖：E1 / S1；产品优先级上放在 D2 后。
- 目标：验证狼人夜间协商层 Consensus Log 的 parser / validator / fixture / CLI。
- 边界：不做 AI gameplay，不做 S5 语义标注。
```

with:

```markdown
### S4：Consensus Log runtime/input

- 状态：`completed`（Phase 2B collaboration input；Consensus Log parser / validator / fixture / CLI 已实现）
- 产出：`docs/gold-game/g001-consensus-log.json` + `src/werewolf_eval/consensus_log.py` + `src/werewolf_eval/validate_consensus_log.py` + `tests/test_consensus_log.py`。
- 依赖：E1 / S1；产品优先级上放在 D2 后。
- 目标：验证狼人夜间协商层 Consensus Log 的 parser / validator / fixture / CLI。
- 边界：不做 AI gameplay，不做 S5 语义标注，不接 scoring，不宣称 team coordination scoring 完整可用。
```

- [ ] **步骤 2：Add S4 UX acceptance row**

In the UX Acceptance table, add this row after D2:

```markdown
| S4 | Consensus Log CLI 校验摘要 | 同一 Game Log + Consensus Log 能稳定输出 `consensus_log_id`、`game_id`、`consensuses`、`source_label`，并拒绝非法 participant / refs / status / final target |
```

- [ ] **步骤 3：Add Demo 5 acceptance section**

After Demo 4, add:

```markdown
**Demo 5：Phase 2 Consensus Log input validation**

- 状态：`completed`（`docs/gold-game/g001-consensus-log.json`；仅表示 Consensus Log runtime input 可被验证，不表示真实 AI 狼人协商、team coordination scoring 或 Consensus Log scoring 已启用）
- 触发条件：S4 完成。
- 演示内容：运行时读取 Game Log + Consensus Log → 校验狼人夜间协商结构化输入。
- 验收：同一输入稳定输出 `validated consensus_log_id=s4_g001_consensus_log`、`game_id=g001`、`consensuses=2`、`source_label=[人工 gold sample]`；invalid participant / refs / status / final target 由 unit tests 覆盖并拒绝。
```

- [ ] **步骤 4：Refresh tree**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
```

The hook may print no output. After the command, `.oh-my-harness/tree.md` must include these filenames:

```text
g001-consensus-log.json
consensus_log.py
validate_consensus_log.py
test_consensus_log.py
```

- [ ] **步骤 5：Validate docs and runtime commands**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/gold-game/g001-consensus-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
git diff --check
```

Expected result:

```text
validated game_id=g001 players=6 events=38 winner=villager end_round=2
validated consensus_log_id=s4_g001_consensus_log game_id=g001 consensuses=2 source_label=[人工 gold sample]
Ran 45 tests

OK
```

`git diff --check` must produce no output.

- [ ] **步骤 6：提交 docs and tree**

```bash
git add docs/TASKS.md .oh-my-harness/tree.md
git commit -m "docs: mark S4 consensus log input complete"
```

Expected result:

```text
[task/s4-consensus-log-runtime-input <sha>] docs: mark S4 consensus log input complete
 2 files changed
```

---

### 任务 6：Final verification and PR preparation

**文件：**
- 读取：`docs/harness/plans/2026-05-30--s4-consensus-log-runtime-input-plan.md`
- 读取：`docs/TASKS.md`
- 读取：`.oh-my-harness/tree.md`
- 测试：`tests/test_consensus_log.py`

- [ ] **步骤 1：Run final validation commands**

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/gold-game/g001-consensus-log.json docs/gold-game/g001-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --html-out docs/demo/phase2-runtime-demo.html
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
git diff --check main...HEAD
```

Expected result:

```text
validated game_id=g001 players=6 events=38 winner=villager end_round=2
validated decision_log_id=d1_g001_decision_log game_id=g001 decisions=10
decision_log=enabled decision_quality_total=0
rendered_demo_html=docs/demo/phase2-runtime-demo.html
Ran 45 tests

OK
```

The Consensus Log command must also output exactly:

```text
validated consensus_log_id=s4_g001_consensus_log game_id=g001 consensuses=2 source_label=[人工 gold sample]
```

`git diff --check main...HEAD` must produce no output.

- [ ] **步骤 2：Verify changed files are within scope**

Run:

```bash
git diff --name-only main...HEAD
```

Expected result:

```text
.oh-my-harness/tree.md
docs/TASKS.md
docs/gold-game/g001-consensus-log.json
src/werewolf_eval/consensus_log.py
src/werewolf_eval/validate_consensus_log.py
tests/test_consensus_log.py
```

The implementation PR may also include this plan file if the plan and implementation are submitted together:

```text
docs/harness/plans/2026-05-30--s4-consensus-log-runtime-input-plan.md
```

- [ ] **步骤 3：Prepare checkpoint report**

Use `docs/CHECKPOINT_TEMPLATE.md` and report:

```markdown
- 当前分支：task/s4-consensus-log-runtime-input
- Plan：docs/harness/plans/2026-05-30--s4-consensus-log-runtime-input-plan.md
- 新增文件：docs/gold-game/g001-consensus-log.json, src/werewolf_eval/consensus_log.py, src/werewolf_eval/validate_consensus_log.py, tests/test_consensus_log.py
- 修改文件：docs/TASKS.md, .oh-my-harness/tree.md
- 验证：validate_game_log / validate_decision_log / validate_consensus_log / score_game / render_demo / unittest / diff-check 全部通过
- 边界：未调用 AI，未修改 scoring / attribution / render_demo，未实现 G1 / S5 / L1
```

---

## Overall Implementation PR Description Draft

Title:

```text
feat: S4 consensus log runtime input
```

Body:

```markdown
## Summary

Implements S4 Consensus Log runtime/input for Werewolf-agent Phase 2B collaboration input.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-30--s4-consensus-log-runtime-input-plan.md`

## Scope

- Adds `docs/gold-game/g001-consensus-log.json` as an artificial gold Consensus Log fixture for the two werewolf night kill decisions in `g001`.
- Adds `src/werewolf_eval/consensus_log.py` parser / validator.
- Adds `src/werewolf_eval/validate_consensus_log.py` CLI validator.
- Adds `tests/test_consensus_log.py` covering happy path and invalid input rejection.
- Updates `docs/TASKS.md` with S4 completion, UX acceptance, and Demo 5 acceptance.
- Refreshes `.oh-my-harness/tree.md` for new files.

## Boundary

- No AI calls.
- No S5 semantic labeling.
- No scoring integration from Consensus Log.
- No changes to `src/werewolf_eval/scoring.py`, `src/werewolf_eval/score_game.py`, `src/werewolf_eval/attribution.py`, or `src/werewolf_eval/render_demo.py`.
- No G1 real AI Agent gameplay.
- No L1 real multi-game Leaderboard.
- No changes to `docs/EVALUATION_RUBRIC.md`.
- Does not claim team coordination scoring is complete; S4 only validates Consensus Log input.

## Validation

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json
# => validated game_id=g001 players=6 events=38 winner=villager end_round=2

PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json
# => validated decision_log_id=d1_g001_decision_log game_id=g001 decisions=10

PYTHONPATH=src python -m werewolf_eval.validate_consensus_log docs/gold-game/g001-consensus-log.json docs/gold-game/g001-game-log.json
# => validated consensus_log_id=s4_g001_consensus_log game_id=g001 consensuses=2 source_label=[人工 gold sample]

PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json
# => decision_log=enabled decision_quality_total=0

PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --decision-log docs/gold-game/g001-decision-log.json --html-out docs/demo/phase2-runtime-demo.html
# => rendered_demo_html=docs/demo/phase2-runtime-demo.html

PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
# => Ran 45 tests OK

git diff --check main...HEAD
# => clean
```

## Changed files

```text
.oh-my-harness/tree.md
docs/TASKS.md
docs/gold-game/g001-consensus-log.json
src/werewolf_eval/consensus_log.py
src/werewolf_eval/validate_consensus_log.py
tests/test_consensus_log.py
```

Plan file:

```text
docs/harness/plans/2026-05-30--s4-consensus-log-runtime-input-plan.md
```
```

---

## Self-review Checklist

- Specification coverage: S4 fixture, parser, validator, CLI, tests, TASKS acceptance, tree refresh, validation commands, and PR description are covered.
- Placeholder scan: no `TBD`, `TODO`, or `稍后实现` placeholders are used as implementation requirements.
- Type consistency: `ConsensusLog`, `Consensus`, `ConsensusProposal`, `ConsensusResponse`, and `FinalConsensusDecision` are defined before tests and CLI use them.
- Scope control: scoring, attribution, render demo, AI, G1, S5, L1, and `docs/EVALUATION_RUBRIC.md` are explicitly forbidden.

## Execution Option

计划已完成并保存到 `docs/harness/plans/2026-05-30--s4-consensus-log-runtime-input-plan.md`。有一种执行选项：

**1. 内联执行** - 在此会话中继续执行任务，使用检查点进行批量执行。

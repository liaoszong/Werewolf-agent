# G1b Engine Mock Agent Contract Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add the first deterministic game engine and mock-agent action contract so a minimal 6-player Werewolf game can be driven by private observations and structured mock actions, without provider calls or live AI.

**Architecture:** G1b is the step after G1a scripted fresh-log generation. The implementation adds a small state-machine module that owns game phase progression, constructs private `AgentObservation` objects, accepts structured `AgentAction` objects from deterministic mock agents, and emits Game Log plus Decision Log outputs that pass existing validators and evaluator rendering. G1b deliberately does not implement wolf consensus runtime, failure-recovery policy, provider adapters, Web live observer, or human-vs-AI UI; those remain G1c-G1e work.

**Tech Stack:** Python standard library only (`argparse`, `dataclasses`, `json`, `pathlib`, `unittest`, `subprocess`), existing `werewolf_eval` parser / validator / scorer / renderer modules, existing `scripts/dev/validate_brief.py`, existing review packet generator.

---

## Research PR Decision

No Research PR is needed.

Main already records the route decision:

```text
G1a -> G1b -> G1c -> G1d -> G1e
```

G1b is a single implementation unit with clear boundaries:

- deterministic engine state machine;
- private observation contract;
- structured mock agent actions;
- generated Game Log and Decision Log compatibility;
- evaluator pipeline compatibility;
- no provider, no live AI, no Web UI, no wolf consensus runtime.

## Current Main Facts

The current main branch has completed G1a scripted deterministic fresh-log runner. `docs/ROADMAP.md` marks G1b deterministic game engine + mock agent contract as the next G-track implementation candidate. `docs/TASKS.md` records G1b as `next_candidate` with a boundary of no provider, no live AI, and no Web live observer.

## Bound Implementation PR

Future Implementation PR title:

```text
feat: add G1b deterministic engine and mock agent contract
```

Bound plan path:

```text
docs/harness/plans/2026-05-31--g1b-engine-mock-agent-contract-plan.md
```

## G1b Scope Boundary

G1b may generate a fresh Game Log and Decision Log from a deterministic engine-driven mock game.

G1b must not generate or validate a new Consensus Log. Wolf-team consensus runtime is G1c.

G1b must not call a provider, execute prompts, create an API adapter, require secrets, or depend on network behavior.

G1b mock agents are deterministic test doubles. They are not real AI Agents and must not be described as provider-backed gameplay.

## Global Allowed Scope

The Implementation PR may create or modify only these paths:

```text
src/werewolf_eval/game_engine.py
src/werewolf_eval/run_mock_game.py
src/werewolf_eval/decision_log.py
tests/test_game_engine.py
tests/test_decision_log.py
docs/generated-games/g1b-mock-agent-game-log.json
docs/generated-games/g1b-mock-agent-decision-log.json
docs/generated-games/g1b-mock-agent-score-log.json
docs/generated-games/g1b-mock-agent-metrics-summary.json
docs/demo/phase3-g1b-mock-agent-runtime-demo.html
README.md
docs/TASKS.md
docs/ROADMAP.md
.oh-my-harness/tree.md
```

`src/werewolf_eval/decision_log.py` and `tests/test_decision_log.py` may be modified only to add and validate the exact source label:

```text
[deterministic mock agent output]
```

No other parser behavior may be relaxed.

## Global Forbidden Scope

The Implementation PR must not modify:

```text
docs/gold-game/g001-*
docs/generated-games/g1-scripted-*
docs/demo/phase3-g1-scripted-runtime-demo.html
docs/semantic-labeling/**
scripts/research/**
```

The Implementation PR must not introduce:

```text
provider API calls
network calls
SDK or dependency additions
secrets or environment-variable requirements
live AI reasoning
prompt execution
stochastic gameplay
wolf consensus runtime
failure-recovery policy
automatic repair of invalid generated logs
Web live observer
human-vs-AI UI
multi-game Leaderboard
scoring formula changes
semantic label scoring changes
Consensus Log generation for G1b
```

## Files Overview

Create:

- `src/werewolf_eval/game_engine.py`
  - Deterministic G1b state machine, observation/action dataclasses, mock agents, and output conversion helpers.
- `src/werewolf_eval/run_mock_game.py`
  - CLI entrypoint that runs the deterministic mock game and writes Game Log and Decision Log JSON.
- `tests/test_game_engine.py`
  - Unit and CLI tests for private observations, structured actions, deterministic outputs, validators, and evaluator compatibility.
- `docs/generated-games/g1b-mock-agent-game-log.json`
  - Generated Game Log from the deterministic mock-agent game.
- `docs/generated-games/g1b-mock-agent-decision-log.json`
  - Generated Decision Log from structured mock-agent actions.
- `docs/generated-games/g1b-mock-agent-score-log.json`
  - Generated Score Log from the G1b generated Game Log + Decision Log.
- `docs/generated-games/g1b-mock-agent-metrics-summary.json`
  - Generated Metrics Summary from the G1b generated Game Log + Decision Log.
- `docs/demo/phase3-g1b-mock-agent-runtime-demo.html`
  - Static replay demo generated from the G1b outputs.

Modify:

- `src/werewolf_eval/decision_log.py`
  - Add exact source label allowlist entry for deterministic mock-agent output.
- `tests/test_decision_log.py`
  - Add a narrow source-label validation test.
- `README.md`
  - Update current status after G1b implementation.
- `docs/TASKS.md`
  - Mark G1b completed after implementation and leave G1c as next candidate.
- `docs/ROADMAP.md`
  - Update current priority after G1b implementation.
- `.oh-my-harness/tree.md`
  - Refresh after new files are added.

No other files should be modified.

---

### Task 1: Define engine and mock-agent contract tests

**Files:**

- Create: `tests/test_game_engine.py`
- Test: `tests/test_game_engine.py`

- [ ] **Step 1: Create failing contract tests**

Create `tests/test_game_engine.py` with this initial content:

```python
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class GameEngineContractTests(unittest.TestCase):
    def test_private_observation_hides_non_visible_roles(self) -> None:
        from werewolf_eval.game_engine import build_default_config, GameEngine

        engine = GameEngine.from_config(build_default_config(game_id="g1b_mock_001"))

        seer_observation = engine.observation_for("p3")
        self.assertEqual(seer_observation.player_id, "p3")
        self.assertEqual(seer_observation.role, "seer")
        self.assertEqual(seer_observation.team, "villager")
        self.assertEqual(seer_observation.known_roles, {"p3": "seer"})
        self.assertNotIn("p1", seer_observation.known_roles)
        self.assertNotIn("p2", seer_observation.known_roles)

        wolf_observation = engine.observation_for("p1")
        self.assertEqual(wolf_observation.role, "werewolf")
        self.assertEqual(wolf_observation.team, "werewolf")
        self.assertEqual(
            wolf_observation.known_roles,
            {"p1": "werewolf", "p2": "werewolf"},
        )

    def test_mock_agent_returns_structured_action(self) -> None:
        from werewolf_eval.game_engine import AgentAction, MockAgent

        agent = MockAgent(player_id="p3")
        action = agent.decide(
            observation={
                "game_id": "g1b_mock_001",
                "player_id": "p3",
                "role": "seer",
                "team": "villager",
                "phase": "night",
                "round": 1,
                "alive_players": ["p1", "p2", "p3", "p4", "p5", "p6"],
                "public_event_ids": [],
                "private_event_ids": [],
                "known_roles": {"p3": "seer"},
            }
        )

        self.assertIsInstance(action, AgentAction)
        self.assertEqual(action.actor, "p3")
        self.assertEqual(action.action, "seer_check")
        self.assertEqual(action.target, "p1")
        self.assertEqual(action.decision_type, "inference_based")
        self.assertEqual(action.source_label, "[deterministic mock agent output]")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing contract tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine.GameEngineContractTests -v
```

Expected result before implementation:

```text
ModuleNotFoundError: No module named 'werewolf_eval.game_engine'
```

- [ ] **Step 3: Commit task 1**

```bash
git add tests/test_game_engine.py
git commit -m "test: define G1b engine mock agent contract"
```

Expected result:

```text
[branch] test: define G1b engine mock agent contract
```

---

### Task 2: Implement deterministic engine and mock agents

**Files:**

- Create: `src/werewolf_eval/game_engine.py`
- Modify: `tests/test_game_engine.py`
- Test: `tests/test_game_engine.py`

- [ ] **Step 1: Implement `src/werewolf_eval/game_engine.py` public API**

Create `src/werewolf_eval/game_engine.py` with these public constants, dataclasses, and functions:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MOCK_AGENT_SOURCE_LABEL = "[deterministic mock agent output]"


@dataclass(frozen=True)
class EnginePlayer:
    player_id: str
    role: str
    team: str


@dataclass(frozen=True)
class GameConfig:
    game_id: str
    players: list[EnginePlayer]


@dataclass(frozen=True)
class AgentObservation:
    game_id: str
    player_id: str
    role: str
    team: str
    phase: str
    round: int
    alive_players: list[str]
    public_event_ids: list[str]
    private_event_ids: list[str]
    known_roles: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "player_id": self.player_id,
            "role": self.role,
            "team": self.team,
            "phase": self.phase,
            "round": self.round,
            "alive_players": list(self.alive_players),
            "public_event_ids": list(self.public_event_ids),
            "private_event_ids": list(self.private_event_ids),
            "known_roles": dict(self.known_roles),
        }


@dataclass(frozen=True)
class AgentAction:
    actor: str
    action: str
    target: str
    phase: str
    round: int
    reason_summary: str
    decision_type: str
    confidence: float = 1.0
    source_label: str = MOCK_AGENT_SOURCE_LABEL
    visible_info_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EngineOutputs:
    game_log: dict[str, Any]
    decision_log: dict[str, Any]
```

Implement:

```python
def build_default_config(game_id: str = "g1b_mock_001") -> GameConfig:
    return GameConfig(
        game_id=game_id,
        players=[
            EnginePlayer("p1", "werewolf", "werewolf"),
            EnginePlayer("p2", "werewolf", "werewolf"),
            EnginePlayer("p3", "seer", "villager"),
            EnginePlayer("p4", "witch", "villager"),
            EnginePlayer("p5", "villager", "villager"),
            EnginePlayer("p6", "villager", "villager"),
        ],
    )
```

Implement `MockAgent.decide(observation: AgentObservation | dict[str, Any]) -> AgentAction` with this deterministic policy:

```text
p3 seer, night 1 -> seer_check p1
p4 witch, night 1 -> witch_save p5
p3 day 1 -> player_vote p1
p4 day 1 -> player_vote p1
p5 day 1 -> player_vote p1
p6 day 1 -> player_vote p1
p4 day 2 -> player_vote p2
p5 day 2 -> player_vote p2
p6 day 2 -> player_vote p2
```

The method must convert dict observations into `AgentObservation` internally before branching. It must raise `ValueError("no deterministic mock action for <player> <phase> <round>")` when no action exists.

Implement `WolfTeamMockAgent.decide(observation: AgentObservation | dict[str, Any]) -> AgentAction` with this deterministic policy:

```text
night 1 -> werewolf_kill p5
night 2 -> werewolf_kill p3
```

The actor for these actions must be `wolf_team`, and the decision type must be `team_coordinated`.

Implement `GameEngine` with:

```python
class GameEngine:
    @classmethod
    def from_config(cls, config: GameConfig) -> "GameEngine":
        return cls(config)

    def observation_for(self, player_id: str) -> AgentObservation:
        ...

    def run(self) -> EngineOutputs:
        ...
```

The implementation must not use an ellipsis expression. The `observation_for()` method must produce:

- the actor's own role;
- wolf teammate roles only for werewolves;
- no hidden enemy roles for villagers;
- `public_event_ids` from events with visibility `public` or `all`;
- `private_event_ids` visible only to the player role or werewolf team.

The `run()` method must deterministically emit this event sequence:

```text
1 setup role_assignment system -> none
2 night werewolf_kill wolf_team -> p5
3 night seer_check p3 -> p1
4 night witch_save p4 -> p5
5 day player_vote p3 -> p1
6 day player_vote p4 -> p1
7 day player_vote p5 -> p1
8 day player_vote p6 -> p1
9 day player_eliminated system -> p1
10 day role_revealed system -> p1
11 night werewolf_kill wolf_team -> p3
12 night player_died system -> p3
13 day player_vote p4 -> p2
14 day player_vote p5 -> p2
15 day player_vote p6 -> p2
16 day player_eliminated system -> p2
17 day role_revealed system -> p2
18 game_end game_over system -> villager_team
```

The output Game Log must include `game_id = g1b_mock_001`, `source_label = [deterministic mock agent output]`, the six players, the 18 events, and result:

```json
{"winner":"villager","end_round":2,"survivors":["p4","p5","p6"],"end_condition":"all_werewolves_eliminated"}
```

The output Decision Log must include `decision_log_id = g1b_mock_001_decision_log`, `game_id = g1b_mock_001`, `source_label = [deterministic mock agent output]`, and decisions for every mock action listed above.

G1b must not produce `consensus_log` output.

- [ ] **Step 2: Add engine output tests**

Append to `tests/test_game_engine.py`:

```python
class GameEngineOutputTests(unittest.TestCase):
    def test_engine_emits_valid_game_and_decision_logs(self) -> None:
        from werewolf_eval.decision_log import parse_decision_log
        from werewolf_eval.game_engine import build_default_config, GameEngine
        from werewolf_eval.game_log import parse_game_log

        outputs = GameEngine.from_config(build_default_config()).run()
        game = parse_game_log(outputs.game_log)
        decision_log = parse_decision_log(outputs.decision_log, game)

        self.assertEqual(game.game_id, "g1b_mock_001")
        self.assertEqual(outputs.game_log["source_label"], "[deterministic mock agent output]")
        self.assertEqual(decision_log.source_label, "[deterministic mock agent output]")
        self.assertEqual(len(game.events), 18)
        self.assertEqual(len(decision_log.decisions), 11)
        self.assertNotIn("consensus_log", outputs.__dict__)
        self.assertEqual(game.result.winner, "villager")

    def test_engine_is_deterministic(self) -> None:
        from werewolf_eval.game_engine import build_default_config, GameEngine

        first = GameEngine.from_config(build_default_config()).run()
        second = GameEngine.from_config(build_default_config()).run()

        self.assertEqual(first.game_log, second.game_log)
        self.assertEqual(first.decision_log, second.decision_log)
```

- [ ] **Step 3: Add exact source-label validator compatibility**

Modify `src/werewolf_eval/decision_log.py` only by adding the exact source label to `VALID_SOURCE_LABELS`:

```python
VALID_SOURCE_LABELS = {
    "[人工 gold sample]",
    "[AI 生成]",
    "[scripted deterministic output]",
    "[deterministic mock agent output]",
}
```

Modify `tests/test_decision_log.py` by adding a narrow test that copies the existing `g001` Decision Log payload, sets `source_label` to `[deterministic mock agent output]`, and verifies `parse_decision_log()` accepts it. The test must also verify that an unrelated label such as `[freeform mock output]` is rejected.

- [ ] **Step 4: Run targeted tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine tests.test_decision_log -v
```

Expected result:

```text
OK
```

- [ ] **Step 5: Commit task 2**

```bash
git add src/werewolf_eval/game_engine.py src/werewolf_eval/decision_log.py tests/test_game_engine.py tests/test_decision_log.py
git commit -m "feat: add G1b deterministic engine and mock agent contract"
```

Expected result:

```text
[branch] feat: add G1b deterministic engine and mock agent contract
```

---

### Task 3: Add CLI for deterministic mock game output

**Files:**

- Create: `src/werewolf_eval/run_mock_game.py`
- Modify: `tests/test_game_engine.py`
- Test: `tests/test_game_engine.py`

- [ ] **Step 1: Add CLI test**

Append to `tests/test_game_engine.py`:

```python
class GameEngineCliTests(unittest.TestCase):
    def test_run_mock_game_cli_writes_game_and_decision_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "werewolf_eval.run_mock_game",
                    "--game-id",
                    "g1b_mock_001",
                    "--game-log-out",
                    str(out / "game.json"),
                    "--decision-log-out",
                    str(out / "decision.json"),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn("mock_game_id=g1b_mock_001", result.stdout)
            self.assertIn("events=18", result.stdout)
            self.assertIn("decisions=11", result.stdout)
            self.assertIn("consensus=not_generated", result.stdout)

            game = json.loads((out / "game.json").read_text(encoding="utf-8"))
            decision = json.loads((out / "decision.json").read_text(encoding="utf-8"))
            self.assertEqual(game["game_id"], "g1b_mock_001")
            self.assertEqual(game["source_label"], "[deterministic mock agent output]")
            self.assertEqual(decision["source_label"], "[deterministic mock agent output]")
```

- [ ] **Step 2: Run CLI test and confirm failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine.GameEngineCliTests -v
```

Expected result before CLI implementation:

```text
No module named werewolf_eval.run_mock_game
```

- [ ] **Step 3: Implement CLI**

Create `src/werewolf_eval/run_mock_game.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from werewolf_eval.game_engine import GameEngine, build_default_config


def _write_json(path: str, payload: dict) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic G1b mock-agent game.")
    parser.add_argument("--game-id", default="g1b_mock_001")
    parser.add_argument("--game-log-out", required=True)
    parser.add_argument("--decision-log-out", required=True)
    args = parser.parse_args()

    outputs = GameEngine.from_config(build_default_config(game_id=args.game_id)).run()
    _write_json(args.game_log_out, outputs.game_log)
    _write_json(args.decision_log_out, outputs.decision_log)

    print(f"mock_game_id={args.game_id}")
    print(f"events={len(outputs.game_log['events'])}")
    print(f"decisions={len(outputs.decision_log['decisions'])}")
    print("consensus=not_generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Generate canonical G1b outputs**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.run_mock_game --game-id g1b_mock_001 --game-log-out docs/generated-games/g1b-mock-agent-game-log.json --decision-log-out docs/generated-games/g1b-mock-agent-decision-log.json
```

Expected result:

```text
mock_game_id=g1b_mock_001
events=18
decisions=11
consensus=not_generated
```

- [ ] **Step 5: Validate generated logs**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1b-mock-agent-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1b-mock-agent-decision-log.json docs/generated-games/g1b-mock-agent-game-log.json
```

Expected result:

```text
validated game_id=g1b_mock_001
validated decision_log_id=g1b_mock_001_decision_log
```

- [ ] **Step 6: Run CLI tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine.GameEngineCliTests -v
```

Expected result:

```text
OK
```

- [ ] **Step 7: Commit task 3**

```bash
git add src/werewolf_eval/run_mock_game.py tests/test_game_engine.py docs/generated-games/g1b-mock-agent-game-log.json docs/generated-games/g1b-mock-agent-decision-log.json
git commit -m "feat: add G1b mock game CLI"
```

Expected result:

```text
[branch] feat: add G1b mock game CLI
```

---

### Task 4: Connect G1b outputs to evaluator and replay demo

**Files:**

- Modify: `tests/test_game_engine.py`
- Create: `docs/generated-games/g1b-mock-agent-score-log.json`
- Create: `docs/generated-games/g1b-mock-agent-metrics-summary.json`
- Create: `docs/demo/phase3-g1b-mock-agent-runtime-demo.html`
- Test: `tests/test_game_engine.py`

- [ ] **Step 1: Add evaluator pipeline and provenance tests**

Append to `tests/test_game_engine.py`:

```python
class GameEngineEvaluatorPipelineTests(unittest.TestCase):
    def test_g1b_generated_logs_can_be_scored_and_rendered(self) -> None:
        from werewolf_eval.attribution import attribute_game
        from werewolf_eval.decision_log import load_decision_log
        from werewolf_eval.game_log import load_game_log
        from werewolf_eval.render_demo import build_demo_context, render_html
        from werewolf_eval.scoring import score_game, summarize_metrics

        game = load_game_log(ROOT / "docs/generated-games/g1b-mock-agent-game-log.json")
        decision_log = load_decision_log(
            ROOT / "docs/generated-games/g1b-mock-agent-decision-log.json",
            game,
        )
        score_log = score_game(game, decision_log=decision_log)
        metrics = summarize_metrics(game, score_log)
        attribution = attribute_game(game, score_log, metrics)
        html = render_html(build_demo_context(game, score_log, metrics, attribution))

        self.assertEqual(score_log.game_id, "g1b_mock_001")
        self.assertEqual(metrics.game_id, "g1b_mock_001")
        self.assertIn("g1b_mock_001", html)
        self.assertNotIn("https://", html)

    def test_g1b_artifacts_do_not_claim_provider_or_consensus(self) -> None:
        paths = [
            ROOT / "docs/generated-games/g1b-mock-agent-game-log.json",
            ROOT / "docs/generated-games/g1b-mock-agent-decision-log.json",
            ROOT / "docs/generated-games/g1b-mock-agent-score-log.json",
            ROOT / "docs/generated-games/g1b-mock-agent-metrics-summary.json",
            ROOT / "docs/demo/phase3-g1b-mock-agent-runtime-demo.html",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

        self.assertIn("[deterministic mock agent output]", combined)
        for forbidden in [
            "provider-backed",
            "live AI Agent gameplay",
            "human-vs-AI UI",
            "real multi-game Leaderboard",
            "consensus_log_id",
            "g001_",
            "g1_scripted_001",
        ]:
            self.assertNotIn(forbidden, combined)

        self.assertFalse((ROOT / "docs/generated-games/g1b-mock-agent-consensus-log.json").exists())
```

- [ ] **Step 2: Run pipeline test and confirm missing generated artifacts**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine.GameEngineEvaluatorPipelineTests -v
```

Expected result before score / metrics / demo generation:

```text
FileNotFoundError
```

- [ ] **Step 3: Generate score and metrics outputs**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1b-mock-agent-game-log.json --decision-log docs/generated-games/g1b-mock-agent-decision-log.json --score-log-out docs/generated-games/g1b-mock-agent-score-log.json --metrics-out docs/generated-games/g1b-mock-agent-metrics-summary.json
```

Expected result:

```text
scored game_id=g1b_mock_001
score_records=11
winner=villager
game_length=2
wolf_team_outcome_score=5
decision_log=enabled
```

If the CLI prints additional semantic-label status lines, record the exact lines in the PR validation summary.

- [ ] **Step 4: Generate runtime demo HTML**

Run:

```bash
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1b-mock-agent-game-log.json --decision-log docs/generated-games/g1b-mock-agent-decision-log.json --html-out docs/demo/phase3-g1b-mock-agent-runtime-demo.html
```

Expected result:

```text
rendered_demo_html=docs/demo/phase3-g1b-mock-agent-runtime-demo.html
```

- [ ] **Step 5: Run pipeline tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine.GameEngineEvaluatorPipelineTests -v
```

Expected result:

```text
OK
```

- [ ] **Step 6: Commit task 4**

```bash
git add tests/test_game_engine.py docs/generated-games/g1b-mock-agent-score-log.json docs/generated-games/g1b-mock-agent-metrics-summary.json docs/demo/phase3-g1b-mock-agent-runtime-demo.html
git commit -m "feat: connect G1b mock game to evaluator demo"
```

Expected result:

```text
[branch] feat: connect G1b mock game to evaluator demo
```

---

### Task 5: Update route status docs and validation evidence

**Files:**

- Modify: `README.md`
- Modify: `docs/TASKS.md`
- Modify: `docs/ROADMAP.md`
- Modify: `.oh-my-harness/tree.md`
- Test: `tests/test_game_engine.py`

- [ ] **Step 1: Update README current status**

In `README.md`, update current status to say:

```markdown
G1b deterministic game engine + mock agent contract 已完成，可用最小 6 人状态机、private observation 和 structured mock `AgentAction` 生成 Game Log / Decision Log，并通过 evaluator pipeline 生成 `docs/demo/phase3-g1b-mock-agent-runtime-demo.html`。这仍不代表 provider-backed gameplay、live AI Agent gameplay、Web live observer、human-vs-AI UI 或 real multi-game Leaderboard 已完成。
```

- [ ] **Step 2: Update TASKS G1 section**

In `docs/TASKS.md`, update only the G1 section:

```markdown
#### G1b：deterministic game engine + mock agent contract

- 状态：`completed`
- 产出：`src/werewolf_eval/game_engine.py` + `src/werewolf_eval/run_mock_game.py` + `tests/test_game_engine.py` + `docs/generated-games/g1b-mock-agent-game-log.json` + `docs/generated-games/g1b-mock-agent-decision-log.json` + `docs/generated-games/g1b-mock-agent-score-log.json` + `docs/generated-games/g1b-mock-agent-metrics-summary.json` + `docs/demo/phase3-g1b-mock-agent-runtime-demo.html`。
- 作用：建立最小 6 人狼人杀状态机、private observation、structured `AgentAction`、mock agent，并生成可验证 Game Log / Decision Log。
- 边界：不接 provider，不做 live AI，不做 Web live observer，不生成 Consensus Log。
```

Then change G1c status from `future_candidate` to `next_candidate`.

- [ ] **Step 3: Update ROADMAP current priority**

In `docs/ROADMAP.md`:

- add G1b to current completed facts;
- change G1b status to `completed`;
- change G1c status to `next_candidate`;
- change current priority to G1c wolf consensus + failure recovery;
- keep the statement that full G1 real AI Agent gameplay is not complete.

- [ ] **Step 4: Refresh tree**

Run:

```bash
node .codex/hooks/tree.mjs --force
```

Expected result:

```text
.oh-my-harness/tree.md updated
```

If the hook prints a different success line but updates `.oh-my-harness/tree.md`, record the exact output in the PR body.

- [ ] **Step 5: Run documentation route shape check**

Run:

```bash
python - <<'PY'
from pathlib import Path

roadmap = Path("docs/ROADMAP.md").read_text(encoding="utf-8")
tasks = Path("docs/TASKS.md").read_text(encoding="utf-8")
readme = Path("README.md").read_text(encoding="utf-8")

required = [
    "G1b deterministic game engine + mock agent contract 已完成",
    "G1c wolf consensus + failure recovery",
    "full G1 real AI Agent gameplay is not complete",
]
for item in required:
    assert item in roadmap or item in tasks or item in readme, item

for forbidden in [
    "G1 complete",
    "real AI Agent gameplay completed",
    "provider integration completed",
    "human-vs-AI UI completed",
]:
    assert forbidden not in roadmap
    assert forbidden not in tasks
    assert forbidden not in readme

print("g1b route docs: PASS")
PY
```

Expected result:

```text
g1b route docs: PASS
```

- [ ] **Step 6: Commit task 5**

```bash
git add README.md docs/TASKS.md docs/ROADMAP.md .oh-my-harness/tree.md
git commit -m "docs: update G1b mock engine status"
```

Expected result:

```text
[branch] docs: update G1b mock engine status
```

---

## Final Validation Commands

Run all commands before review:

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine tests.test_decision_log -v
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
PYTHONPATH=src python -m werewolf_eval.run_mock_game --game-id g1b_mock_001 --game-log-out docs/generated-games/g1b-mock-agent-game-log.json --decision-log-out docs/generated-games/g1b-mock-agent-decision-log.json
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1b-mock-agent-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1b-mock-agent-decision-log.json docs/generated-games/g1b-mock-agent-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1b-mock-agent-game-log.json --decision-log docs/generated-games/g1b-mock-agent-decision-log.json --score-log-out docs/generated-games/g1b-mock-agent-score-log.json --metrics-out docs/generated-games/g1b-mock-agent-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1b-mock-agent-game-log.json --decision-log docs/generated-games/g1b-mock-agent-decision-log.json --html-out docs/demo/phase3-g1b-mock-agent-runtime-demo.html
PYTHONPATH=src python scripts/dev/validate_brief.py
git diff --check
```

Expected results:

```text
g1b targeted tests: OK
full unittest: OK
run_mock_game: events=18 decisions=11 consensus=not_generated
validate_game_log: validated game_id=g1b_mock_001
validate_decision_log: validated decision_log_id=g1b_mock_001_decision_log
score_game: scored game_id=g1b_mock_001
render_demo: rendered_demo_html=docs/demo/phase3-g1b-mock-agent-runtime-demo.html
validate_brief: ok=true
git diff --check: no output
```

## Acceptance Criteria

- `GameEngine.observation_for()` exposes only allowed private information.
- Mock agents return structured `AgentAction` values.
- `GameEngine.run()` deterministically emits a valid Game Log and Decision Log.
- No G1b Consensus Log is generated.
- Generated Game Log validates with `validate_game_log`.
- Generated Decision Log validates with `validate_decision_log`.
- G1b generated logs feed scoring, metrics, attribution, and static replay demo.
- Generated G1b artifacts use `g1b_mock_001` ids and `[deterministic mock agent output]` source label.
- Generated G1b artifacts do not claim provider-backed gameplay, live AI Agent gameplay, Web live observer, human-vs-AI UI, real multi-game Leaderboard, or consensus runtime.
- Existing G1a generated artifacts remain unchanged.
- README, TASKS, and ROADMAP record G1b completion without claiming full G1 completion.

## Review Packet Requirements

Before requesting Codex implementation review, generate:

```text
.logs/review/latest/review-packet.md
```

The Review Packet must contain at least these machine-generated evidence sections:

1. `git diff --name-only`
2. `git diff --stat`
3. `git diff --check` result
4. changed files allowlist check
5. forbidden patterns check
6. dependency/import diff check
7. test command + exact pass/fail summary
8. key hunk excerpts
9. acceptance checklist with evidence pointer
10. implementer risk notes

The packet must explicitly state whether these risk triggers fired:

```text
changed files > 8
docs/demo/** changed
docs/generated-games/** changed
src/werewolf_eval/decision_log.py changed
src/werewolf_eval/scoring.py changed
provider/network/env/live AI forbidden pattern hits
Consensus Log generated for G1b
```

If the Review Packet exceeds the v1 size limit, it must set `PACKET_TOO_LARGE = YES` and provide Minimal Next Reads with exact file paths and line ranges.

Without the Review Packet, do not request Codex implementation review.

## Codex B档 Risk Points

This implementation may trigger B档 deep review because it adds runtime files, generated artifacts, a demo HTML file, and a parser source-label compatibility change.

Expected B档 focus:

- `src/werewolf_eval/game_engine.py`: deterministic engine, observations, structured actions, no provider behavior.
- `src/werewolf_eval/decision_log.py`: exact source-label allowlist only.
- `tests/test_game_engine.py`: private observation, deterministic output, no consensus output, provenance tests.
- `docs/generated-games/g1b-mock-agent-*.json`: generated ids and source labels.
- `docs/demo/phase3-g1b-mock-agent-runtime-demo.html`: boundary language.
- `README.md`, `docs/TASKS.md`, `docs/ROADMAP.md`: no full-G1 or provider-backed claims.

## Implementation PR Description Draft

Title:

```text
feat: add G1b deterministic engine and mock agent contract
```

Body:

```markdown
## Summary

Add G1b deterministic game engine + mock agent contract.

Bound plan: `docs/harness/plans/2026-05-31--g1b-engine-mock-agent-contract-plan.md`

## Changes

- Add `src/werewolf_eval/game_engine.py` with minimal 6-player state machine, private observations, structured `AgentAction`, and deterministic mock agents.
- Add `src/werewolf_eval/run_mock_game.py` CLI.
- Add G1b generated Game Log / Decision Log / Score Log / Metrics Summary under `docs/generated-games/`.
- Add `docs/demo/phase3-g1b-mock-agent-runtime-demo.html` replay output.
- Add tests for private observations, structured actions, validators, evaluator pipeline, and G1b boundary claims.
- Add exact `[deterministic mock agent output]` source-label compatibility for Decision Log validation.
- Update README / TASKS / ROADMAP to mark G1b complete and G1c as next candidate.

## Boundary

This PR does not implement provider integration, live AI reasoning, prompt execution, network calls, secrets, wolf consensus runtime, failure recovery, Web live observer, human-vs-AI UI, multi-game Leaderboard, scoring formula changes, or Consensus Log generation for G1b.

## Validation

```bash
PYTHONPATH=src python -m unittest tests.test_game_engine tests.test_decision_log -v
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
PYTHONPATH=src python -m werewolf_eval.run_mock_game --game-id g1b_mock_001 --game-log-out docs/generated-games/g1b-mock-agent-game-log.json --decision-log-out docs/generated-games/g1b-mock-agent-decision-log.json
PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/generated-games/g1b-mock-agent-game-log.json
PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/generated-games/g1b-mock-agent-decision-log.json docs/generated-games/g1b-mock-agent-game-log.json
PYTHONPATH=src python -m werewolf_eval.score_game docs/generated-games/g1b-mock-agent-game-log.json --decision-log docs/generated-games/g1b-mock-agent-decision-log.json --score-log-out docs/generated-games/g1b-mock-agent-score-log.json --metrics-out docs/generated-games/g1b-mock-agent-metrics-summary.json
PYTHONPATH=src python -m werewolf_eval.render_demo docs/generated-games/g1b-mock-agent-game-log.json --decision-log docs/generated-games/g1b-mock-agent-decision-log.json --html-out docs/demo/phase3-g1b-mock-agent-runtime-demo.html
PYTHONPATH=src python scripts/dev/validate_brief.py
git diff --check
```

## Review Packet

Generated at:

```text
.logs/review/latest/review-packet.md
```

The packet includes diff evidence, allowlist/forbidden-pattern checks, dependency/import diff check, validation summaries, key hunks, acceptance checklist, and implementer risk notes.
```

## Handoff Prompt for Claude Code

```text
接手当前 Implementation Plan，完成实现 PR。

Plan:
docs/harness/plans/2026-05-31--g1b-engine-mock-agent-contract-plan.md

只实现 G1b deterministic game engine + mock agent contract。
不要实现 provider、live AI、prompt execution、network calls、secrets、wolf consensus runtime、failure recovery、Web live observer、human-vs-AI UI、multi-game Leaderboard 或 Consensus Log generation。

必须按 AGENTS.md 的 Context Budget Gate 执行。
实现完成后必须生成 .logs/review/latest/review-packet.md，否则不要请求 Codex review。
```

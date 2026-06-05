"""P2-A-1 Emergent Werewolf game engine.

A real self-evolving 6-player game: all roles AI-driven (wolf kill, seer check,
witch save/poison/pass, day speech, day vote), with emergent eliminations, win
conditions, and dynamic round count.

This module REUSES the P1 primitives (`AgentObservation`/`AgentAction`/
`EngineOutputs` dataclasses, `ProviderAgent` validation, the wolf-consensus
shape) but has its own game loop. It deliberately does NOT touch
`game_engine.GameEngine` so the scripted g1b/g1c/g1f modes and their tests stay
untouched.

Design: docs/superpowers/specs/2026-06-05-p2-a-1-emergent-engine-design.md
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

from werewolf_eval.game_engine import (
    AgentAction,
    AgentObservation,
    EnginePlayer,
    GameConfig,
    build_default_config,
    build_failure,
)
from werewolf_eval.provider_agent import ProviderActionError
from werewolf_eval.provider_contract import ProviderRequest

# The provider request phase used for free-text speeches. The game_log event is
# still recorded with phase="day"; the distinct request phase only keeps the
# speech provider call from colliding with the day vote at (actor, "day", round).
SPEECH_REQUEST_PHASE = "day_speech"
SPEECH_MAX_CHARS = 200
SPEECH_EMPTY_PLACEHOLDER = "（发言无效）"

WITCH_SAVE = "witch_save"
WITCH_KILL = "witch_kill"
WITCH_PASS = "witch_pass"
WITCH_ACTIONS = (WITCH_SAVE, WITCH_KILL, WITCH_PASS)

FALLBACK_DECISION_TYPE = "default"


class BudgetExhausted(Exception):
    """Raised internally when the per-game request budget is hit; the run is
    then converted to a fail-closed failed outcome (no complete game_log)."""

    def __init__(self, used: int, limit: int) -> None:
        super().__init__(f"budget exhausted: {used}/{limit} requests")
        self.used = used
        self.limit = limit


@dataclass
class EmergentBudget:
    max_requests: int = 80
    max_day_rounds: int = 3
    used: int = 0

    def charge(self) -> None:
        self.used += 1
        if self.used > self.max_requests:
            raise BudgetExhausted(self.used, self.max_requests)


@dataclass(frozen=True)
class GameOutcome:
    """Result of an emergent run. `status` is "completed" (real villager/werewolf
    win, full logs present) or "failed" (round-cap / budget fail-closed: game_log
    is None, failure_audit explains why)."""

    status: str
    game_log: dict[str, Any] | None
    decision_log: dict[str, Any] | None
    consensus_log: dict[str, Any] | None
    failure_audit: dict[str, Any] | None
    end_condition: str

    @property
    def completed(self) -> bool:
        return self.status == "completed"


def build_emergent_config(game_id: str = "p2a1_emergent_001") -> GameConfig:
    """Default 6-player board: p1/p2 wolves, p3 seer, p4 witch, p5/p6 villagers."""
    return build_default_config(game_id=game_id)


class EmergentGameEngine:
    def __init__(
        self,
        config: GameConfig,
        agents: dict[str, Any],
        seed: int = 0,
        source_label: str | None = None,
        budget: EmergentBudget | None = None,
        runtime_events: Any | None = None,
    ) -> None:
        self._config = config
        self._players_by_id: dict[str, EnginePlayer] = {p.player_id: p for p in config.players}
        self._seat_order: list[str] = [p.player_id for p in config.players]
        self._agents = dict(agents)
        self._rng = random.Random(seed)
        self._source_label = source_label or "[deterministic fake provider output]"
        self._budget = budget or EmergentBudget()
        self._runtime_events = runtime_events

        self._events: list[dict[str, Any]] = []
        self._decisions: list[dict[str, Any]] = []
        self._consensus_entries: list[dict[str, Any]] = []
        self._failures: list[dict[str, Any]] = []
        self._seq = 0
        self._d_counter = 0
        self._alive: set[str] = set(self._players_by_id)

    # ---- small helpers -------------------------------------------------

    @property
    def _game_id(self) -> str:
        return self._config.game_id

    def _wolves(self) -> list[str]:
        return [p.player_id for p in self._config.players if p.role == "werewolf"]

    def _alive_in_seat_order(self, exclude: set[str] | None = None) -> list[str]:
        exclude = exclude or set()
        return [pid for pid in self._seat_order if pid in self._alive and pid not in exclude]

    def _public_refs(self) -> list[str]:
        return [e["event_id"] for e in self._events if e["visibility"] in ("public", "all")]

    def _private_refs(self, player_id: str) -> list[str]:
        role = self._players_by_id[player_id].role
        refs: list[str] = []
        for e in self._events:
            v = e["visibility"]
            if v == "all" or v == role or (v == "werewolf_team" and role == "werewolf"):
                refs.append(e["event_id"])
        return refs

    def _emit(
        self,
        phase: str,
        rnd: int,
        etype: str,
        actor: str,
        target: str,
        visibility: str,
        summary: str,
        refs: list[str] | None = None,
    ) -> dict[str, Any]:
        self._seq += 1
        evt = {
            "event_id": f"{self._game_id}_e{self._seq:03d}",
            "sequence": self._seq,
            "round": rnd,
            "phase": phase,
            "type": etype,
            "actor": actor,
            "target": target,
            "visibility": visibility,
            "data": {"summary": summary, "visible_info_refs": refs or []},
        }
        self._events.append(evt)
        if self._runtime_events is not None:
            self._runtime_events.emit(
                "game_event_emitted",
                round=rnd,
                phase=phase,
                actor=actor,
                visibility=visibility,
                payload={"event_id": evt["event_id"], "type": etype},
            )
        return evt

    def _decision(
        self,
        actor: str,
        scope: str,
        phase: str,
        action: str,
        target: str | None,
        dtype: str,
        reason: str,
        refs: list[str] | None = None,
        consensus_id: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        self._d_counter += 1
        self._decisions.append(
            {
                "decision_id": f"{self._game_id}_d{self._d_counter:03d}",
                "actor": actor,
                "decision_scope": scope,
                "consensus_id": consensus_id,
                "phase": phase,
                "action": action,
                "target": target,
                "visible_info_refs": refs or [],
                "reason_summary": reason[:200],
                "decision_type": dtype,
                "confidence": confidence,
                "strategy_tag": None,
            }
        )

    def _record_failure(
        self, rnd: int, phase: str, actor: str, kind: str, reason: str, target: str | None = None
    ) -> None:
        self._failures.append(build_failure(self._game_id, rnd, phase, actor, kind, reason, target))

    def _build_obs(self, player_id: str, phase: str, rnd: int) -> AgentObservation:
        p = self._players_by_id[player_id]
        known_roles = {player_id: p.role}
        if p.role == "werewolf":
            for w in self._wolves():
                known_roles[w] = "werewolf"
        return AgentObservation(
            game_id=self._game_id,
            player_id=player_id,
            role=p.role,
            team=p.team,
            phase=phase,
            round=rnd,
            alive_players=sorted(self._alive),
            public_event_ids=self._public_refs(),
            private_event_ids=self._private_refs(player_id),
            known_roles=known_roles,
        )

    def _charge_and_decide(self, player_id: str, phase: str, rnd: int) -> AgentAction:
        """Charge budget then call the player's ProviderAgent (full validation)."""
        self._budget.charge()
        obs = self._build_obs(player_id, phase, rnd)
        return self._agents[player_id].decide(obs)

    # ---- win condition -------------------------------------------------

    def _win_check(self) -> str | None:
        alive_wolves = [pid for pid in self._alive if self._players_by_id[pid].role == "werewolf"]
        alive_non_wolves = [pid for pid in self._alive if self._players_by_id[pid].role != "werewolf"]
        if not alive_wolves:
            return "villager"
        if len(alive_wolves) >= len(alive_non_wolves):
            return "werewolf"
        return None

    # ---- night sub-phases ---------------------------------------------

    def _resolve_wolf_kill(self, rnd: int) -> str | None:
        wolves = [w for w in self._wolves() if w in self._alive]
        if not wolves:
            return None
        consensus_id = f"{self._game_id}_consensus_r{rnd:02d}"
        proposals: list[tuple[str, str]] = []  # (wolf, target)
        for wolf in wolves:
            try:
                action = self._charge_and_decide(wolf, "night", rnd)
            except BudgetExhausted:
                raise
            except ProviderActionError as exc:
                self._record_failure(rnd, "night", wolf, exc.failure.kind, exc.failure.reason, exc.failure.target)
                continue
            except Exception as exc:  # noqa: BLE001 - defensive
                self._record_failure(rnd, "night", wolf, "agent_error", f"{wolf} raised {type(exc).__name__}: {exc}")
                continue
            valid = (
                action.action == "werewolf_kill"
                and action.target in self._alive
                and self._players_by_id.get(action.target) is not None
                and self._players_by_id[action.target].role != "werewolf"
            )
            if not valid:
                self._record_failure(rnd, "night", wolf, "invalid_action", f"{wolf} proposed invalid kill {action.target}", action.target)
                continue
            proposals.append((wolf, action.target))

        if not proposals:
            # fallback: kill first alive non-wolf by seat order
            candidates = [pid for pid in self._seat_order if pid in self._alive and self._players_by_id[pid].role != "werewolf"]
            if not candidates:
                return None
            target = candidates[0]
            self._consensus_entries.append(self._build_consensus_entry(consensus_id, rnd, wolves, target, wolves[0], [], status="coordinator_tie_break"))
            self._decision(wolves[0], "team", "night", "werewolf_kill", target, FALLBACK_DECISION_TYPE, f"fallback kill {target}", consensus_id=consensus_id)
            self._emit("night", rnd, "werewolf_kill", wolves[0], target, "werewolf_team", f"Wolf team kills {target}.")
            return target

        # tally targets, pick max, seeded tie-break among the top
        counts: dict[str, int] = {}
        for _, t in proposals:
            counts[t] = counts.get(t, 0) + 1
        top = max(counts.values())
        leaders = sorted(t for t, c in counts.items() if c == top)
        if len(leaders) == 1:
            target = leaders[0]
            status = "consensus" if len(set(t for _, t in proposals)) == 1 else "coordinator_tie_break"
        else:
            target = leaders[self._rng.randrange(len(leaders))]
            status = "coordinator_tie_break"
        primary = next(w for w, t in proposals if t == target)
        supporters = [w for w, t in proposals if t == target]
        self._consensus_entries.append(self._build_consensus_entry(consensus_id, rnd, wolves, target, primary, supporters, status=status))
        self._decision(primary, "team", "night", "werewolf_kill", target, "team_coordinated", f"wolf team kills {target}", consensus_id=consensus_id)
        self._emit("night", rnd, "werewolf_kill", primary, target, "werewolf_team", f"Wolf team kills {target}.")
        return target

    def _build_consensus_entry(self, consensus_id, rnd, wolves, target, primary, supporters, status):
        responses = []
        for j, w in enumerate(wolves):
            if w == primary:
                continue
            is_sup = w in supporters
            responses.append(
                {
                    "response_id": j + 1,
                    "to_proposal_id": 1,
                    "responder": w,
                    "response_type": "support_with_reason" if is_sup else "oppose_with_reason",
                    "reason_summary": f"{w} {'supports' if is_sup else 'opposes'} {primary} proposal",
                    "visible_info_refs": [],
                    "action_round": 1,
                }
            )
        dissenters = [w for w in wolves if w != primary and w not in supporters]
        return {
            "consensus_id": consensus_id,
            "game_id": self._game_id,
            "round": rnd,
            "phase": "night",
            "team": "werewolf",
            "participants": list(wolves),
            "coordinator": wolves[0],
            "max_rounds": 1,
            "actual_rounds": 1,
            "status": status,
            "proposals": [
                {
                    "proposal_id": 1,
                    "proposer": primary,
                    "proposed_target": target,
                    "visible_info_refs": self._public_refs(),
                    "reason_summary": f"{primary} proposes {target}",
                    "confidence": 1.0,
                    "action_round": 1,
                }
            ],
            "responses": responses,
            "final_decision": {
                "target": target,
                "decision_type": status,
                "primary_proposer": primary,
                "supporters": supporters,
                "dissenters": dissenters,
                "resolution_round": 1,
            },
        }

    def _resolve_seer(self, rnd: int) -> None:
        seers = [pid for pid in self._alive if self._players_by_id[pid].role == "seer"]
        if not seers:
            return
        seer = seers[0]
        target: str | None = None
        try:
            action = self._charge_and_decide(seer, "night", rnd)
            if action.action == "seer_check" and action.target in self._alive and action.target != seer:
                target = action.target
            else:
                self._record_failure(rnd, "night", seer, "invalid_action", f"{seer} bad seer_check {action.target}", action.target)
        except BudgetExhausted:
            raise
        except ProviderActionError as exc:
            self._record_failure(rnd, "night", seer, exc.failure.kind, exc.failure.reason, exc.failure.target)
        except Exception as exc:  # noqa: BLE001
            self._record_failure(rnd, "night", seer, "agent_error", f"{seer} raised {type(exc).__name__}: {exc}")
        if target is None:
            cands = self._alive_in_seat_order(exclude={seer})
            if not cands:
                return
            target = cands[0]
            dtype = FALLBACK_DECISION_TYPE
        else:
            dtype = "inference_based"
        result = "werewolf" if self._players_by_id[target].role == "werewolf" else "good"
        self._decision(seer, "single", "night", "seer_check", target, dtype, f"seer checks {target}")
        self._emit("night", rnd, "seer_check", seer, target, "seer", f"Seer {seer} checks {target}, result: {result}.")

    def _resolve_witch(self, rnd: int, victim: str | None, save_used: bool, poison_used: bool) -> tuple[bool, str | None, bool, bool]:
        """Returns (saved_victim, poison_target, new_save_used, new_poison_used)."""
        witches = [pid for pid in self._alive if self._players_by_id[pid].role == "witch"]
        if not witches:
            return False, None, save_used, poison_used
        witch = witches[0]
        self._budget.charge()
        provider = self._agents[witch].provider
        obs = self._build_obs(witch, "night", rnd)
        request = ProviderRequest(
            request_id=f"{self._game_id}_r{rnd:02d}_{witch}_witch",
            game_id=self._game_id,
            actor=witch,
            phase="night",
            round=rnd,
            observation=obs.to_dict(),
            allowed_actions=list(WITCH_ACTIONS),
            allowed_targets=sorted(self._alive),
        )
        action_name = WITCH_PASS
        target: str | None = None
        try:
            raw = provider.respond(request).raw_content
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("witch response not a JSON object")
            action_name = parsed.get("action", WITCH_PASS)
            target = parsed.get("target")
        except Exception as exc:  # noqa: BLE001
            self._record_failure(rnd, "night", witch, "parse_failure", f"{witch} witch parse failed: {exc}")
            action_name = WITCH_PASS

        # validate
        if action_name == WITCH_SAVE:
            if save_used or victim is None or target != victim:
                self._record_failure(rnd, "night", witch, "invalid_action", f"{witch} invalid witch_save target={target}", target)
                action_name = WITCH_PASS
        elif action_name == WITCH_KILL:
            if poison_used or target not in self._alive or target == witch:
                self._record_failure(rnd, "night", witch, "invalid_action", f"{witch} invalid witch_kill target={target}", target)
                action_name = WITCH_PASS
        elif action_name != WITCH_PASS:
            self._record_failure(rnd, "night", witch, "invalid_action", f"{witch} unknown witch action {action_name}")
            action_name = WITCH_PASS

        if action_name == WITCH_SAVE:
            self._decision(witch, "single", "night", WITCH_SAVE, victim, "inference_based", f"witch saves {victim}")
            self._emit("night", rnd, WITCH_SAVE, witch, victim, "witch", f"Witch {witch} saves {victim}.")
            return True, None, True, poison_used
        if action_name == WITCH_KILL:
            self._decision(witch, "single", "night", WITCH_KILL, target, "retaliatory", f"witch poisons {target}")
            self._emit("night", rnd, WITCH_KILL, witch, target, "witch", f"Witch {witch} poisons {target}.")
            return False, target, save_used, True
        # pass
        self._decision(witch, "single", "night", WITCH_PASS, "none", FALLBACK_DECISION_TYPE, f"{witch} uses no potion")
        self._emit("night", rnd, WITCH_PASS, witch, "none", "witch", f"Witch {witch} uses no potion.")
        return False, None, save_used, poison_used

    # ---- day sub-phases ------------------------------------------------

    def _resolve_speech(self, player_id: str, rnd: int) -> None:
        self._budget.charge()
        provider = self._agents[player_id].provider
        obs = self._build_obs(player_id, SPEECH_REQUEST_PHASE, rnd)
        request = ProviderRequest(
            request_id=f"{self._game_id}_r{rnd:02d}_{player_id}_speech",
            game_id=self._game_id,
            actor=player_id,
            phase=SPEECH_REQUEST_PHASE,
            round=rnd,
            observation=obs.to_dict(),
            allowed_actions=[],
            allowed_targets=[],
        )
        text = ""
        try:
            text = provider.respond(request).raw_content or ""
        except Exception:  # noqa: BLE001 - speech is non-adjudicating; never abort
            text = ""
        text = text.strip()[:SPEECH_MAX_CHARS]
        if not text:
            text = SPEECH_EMPTY_PLACEHOLDER
        self._emit("day", rnd, "player_speech", player_id, "none", "public", text)

    def _resolve_votes(self, rnd: int) -> str | None:
        refs = self._public_refs()
        tally: dict[str, int] = {}
        for voter in self._alive_in_seat_order():
            target: str | None = None
            try:
                action = self._charge_and_decide(voter, "day", rnd)
                if action.action == "player_vote" and action.target in self._alive and action.target != voter:
                    target = action.target
                else:
                    self._record_failure(rnd, "day", voter, "invalid_action", f"{voter} bad vote {action.target}", action.target)
            except BudgetExhausted:
                raise
            except ProviderActionError as exc:
                self._record_failure(rnd, "day", voter, exc.failure.kind, exc.failure.reason, exc.failure.target)
            except Exception as exc:  # noqa: BLE001
                self._record_failure(rnd, "day", voter, "agent_error", f"{voter} raised {type(exc).__name__}: {exc}")
            if target is None:
                cands = self._alive_in_seat_order(exclude={voter})
                if not cands:
                    continue
                target = cands[0]
                dtype = FALLBACK_DECISION_TYPE
            else:
                dtype = "inference_based"
            tally[target] = tally.get(target, 0) + 1
            self._decision(voter, "single", "day", "player_vote", target, dtype, f"{voter} votes {target}", refs=refs)
            self._emit("day", rnd, "player_vote", voter, target, "public", f"{voter} votes {target}.")

        if not tally:
            return None
        top = max(tally.values())
        leaders = sorted(t for t, c in tally.items() if c == top)
        if len(leaders) == 1:
            return leaders[0]
        return leaders[self._rng.randrange(len(leaders))]

    # ---- main loop -----------------------------------------------------

    def run(self) -> GameOutcome:
        try:
            return self._run_inner()
        except BudgetExhausted as exc:
            return self._failed_outcome("budget_exhausted", str(exc))

    def _failed_outcome(self, end_condition: str, reason: str) -> GameOutcome:
        self._record_failure(0, "game_end", "system", end_condition, reason)
        failure_audit = {
            "game_id": self._game_id,
            "source_label": self._source_label,
            "failures": self._failures,
        }
        return GameOutcome(
            status="failed",
            game_log=None,
            decision_log=None,
            consensus_log=None,
            failure_audit=failure_audit,
            end_condition=end_condition,
        )

    def _run_inner(self) -> GameOutcome:
        game_id = self._game_id
        # setup
        self._emit("setup", 0, "role_assignment", "system", "none", "public", "Roles assigned to all 6 players.")

        save_used = False
        poison_used = False
        winner: str | None = None
        end_condition = ""
        end_round = 0

        for rnd in range(1, self._budget.max_day_rounds + 1):
            end_round = rnd
            # ---- NIGHT ----
            victim = self._resolve_wolf_kill(rnd)
            self._resolve_seer(rnd)
            saved, poison_target, save_used, poison_used = self._resolve_witch(rnd, victim, save_used, poison_used)

            deaths: list[str] = []
            if victim is not None and not saved and victim in self._alive:
                deaths.append(victim)
            if poison_target is not None and poison_target in self._alive and poison_target not in deaths:
                deaths.append(poison_target)
            for pid in deaths:
                self._alive.discard(pid)
                self._emit("night", rnd, "player_died", "system", pid, "all", f"{pid} died during the night.")

            winner = self._win_check()
            if winner is not None:
                end_condition = "all_werewolves_eliminated" if winner == "villager" else "werewolves_reach_parity"
                break

            # ---- DAY ----
            if deaths:
                self._emit("day", rnd, "day_announcement", "system", "none", "public", f"Night fell: {', '.join(deaths)} died.")
            else:
                self._emit("day", rnd, "day_announcement", "system", "none", "public", "A peaceful night: nobody died.")

            for speaker in self._alive_in_seat_order():
                self._resolve_speech(speaker, rnd)

            eliminated = self._resolve_votes(rnd)
            if eliminated is not None:
                self._alive.discard(eliminated)
                role = self._players_by_id[eliminated].role
                self._emit("day", rnd, "player_eliminated", "system", eliminated, "all", f"{eliminated} eliminated by vote.")
                self._emit("day", rnd, "role_revealed", "system", eliminated, "all", f"{eliminated} revealed as {role}.")

            winner = self._win_check()
            if winner is not None:
                end_condition = "all_werewolves_eliminated" if winner == "villager" else "werewolves_reach_parity"
                break

        if winner is None:
            return self._failed_outcome("round_cap", f"no winner within {self._budget.max_day_rounds} day-rounds")

        # game end
        self._emit(
            "game_end",
            end_round,
            "game_over",
            "system",
            "villager_team" if winner == "villager" else "werewolf_team",
            "all",
            f"{'All werewolves eliminated. Villager team wins.' if winner == 'villager' else 'Werewolves reached parity. Werewolf team wins.'}",
        )

        game_log = {
            "game_id": game_id,
            "source_label": self._source_label,
            "players": [{"player_id": p.player_id, "role": p.role, "team": p.team} for p in self._config.players],
            "events": self._events,
            "result": {
                "winner": winner,
                "end_round": end_round,
                "survivors": sorted(self._alive),
                "end_condition": end_condition,
            },
        }
        decision_log = {
            "decision_log_id": f"{game_id}_decision_log",
            "game_id": game_id,
            "source_label": self._source_label,
            "decisions": self._decisions,
        }
        consensus_log = {
            "consensus_log_id": f"{game_id}_consensus_log",
            "game_id": game_id,
            "source_label": self._source_label,
            "consensuses": self._consensus_entries,
        }
        failure_audit = {
            "game_id": game_id,
            "source_label": self._source_label,
            "failures": self._failures,
        }
        return GameOutcome(
            status="completed",
            game_log=game_log,
            decision_log=decision_log,
            consensus_log=consensus_log,
            failure_audit=failure_audit,
            end_condition=end_condition,
        )

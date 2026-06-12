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
from werewolf_eval.runtime_events import build_god_snapshot, build_role_projection_snapshot
from werewolf_eval.provider_agent import ProviderActionError
from werewolf_eval.provider_contract import ProviderRequest, classify_provider_failure_kind
from werewolf_eval.action_runtime import (
    ActionEnvelope,
    ActionValidator,
    DecisionWindow,
    JointSettler,
    NightIntents,
    GuardResolver,
    RngPick,
    RoleAbilityRegistry,
    RuntimeState,
    SeerResolver,
    VoteResolver,
    WolfResolver,
    WolfWindow,
    rules_v1_1,
    rules_v1_2,
)
from werewolf_eval.action_runtime.abilities import TARGET_RULES
from werewolf_eval.invariants.guards import assert_prompt_entitled, assert_death_commit_once
from werewolf_eval.prompt_renderers import get_renderer
from werewolf_eval.prompt_v1 import RenderedObservation, render_observation_text
from werewolf_eval.prompt_v3 import (
    SCRIBE_MAX_OUTPUT_TOKENS,
    parse_scribe_claims,
    render_scribe_input,
)
from werewolf_eval.role_visibility import private_refs_for_role, public_refs

# The provider request phase used for free-text speeches. The game_log event is
# still recorded with phase="day"; the distinct request phase only keeps the
# speech provider call from colliding with the day vote at (actor, "day", round).
SPEECH_REQUEST_PHASE = "day_speech"
# Distinct request phase for the hunter's on-death shot, so its fake-script key
# (actor, phase, round) never collides with the hunter's day-vote key (p6,"day",r).
# The emitted game_log event still uses the real "night"/"day" phase.
HUNTER_SHOT_REQUEST_PHASE = "hunter_shot"
SPEECH_MAX_CHARS = 200
SPEECH_EMPTY_PLACEHOLDER = "（发言无效）"

WITCH_SAVE = "witch_save"
WITCH_POISON = "witch_poison"  # eval-contract vocabulary (scoring/attribution, gold-game g001)
WITCH_PASS = "witch_pass"
WITCH_ACTIONS = (WITCH_SAVE, WITCH_POISON, WITCH_PASS)

FALLBACK_DECISION_TYPE = "default"

# Night abilities dispatched via _RESOLVERS, in their byte-load-bearing order (wolf before
# seer). The witch is deferred (inline) until its RuntimeState potion ledger lands (②b), so it
# is absent here; when it migrates it joins this tuple. Kept as a constant (not derived from
# seat order) so the order can't silently flip on a re-seated board.
#
# WITCH MIGRATION (②b) is BLOCKED on a RuntimeState one-shot potion capability ledger
# (uses_left/consumed_at_event_id) + threading the night victim into _runtime_state(): routing
# the witch through validate_in_state today would accept a 2nd potion -> cross-round divergence.
# Until then the witch stays in _resolve_witch (NOT in _RESOLVERS / this tuple). The one-shot
# guard is pinned by tests/test_witch_potion_one_shot_sentinel.py (antidote + poison), which go
# RED the day a witch swap forgets the ledger.
NIGHT_DISPATCH_ORDER = ("guard_protect", "werewolf_kill", "seer_check")

# Per-request output-token caps (P2-A-2): speeches need more than votes/actions.
SPEECH_MAX_OUTPUT_TOKENS = 250
ACTION_MAX_OUTPUT_TOKENS = 120

# provider_result_kind taxonomy (P2-A-2 gate ②).
LIVE_SUCCESS = "live_success"
INVALID_FALLBACK = "invalid_then_fallback"
TIMEOUT_FALLBACK = "timeout_then_fallback"
ERROR_FALLBACK = "error_then_fallback"
# SYS-B4 scaffold turn kinds (never contribute to live_success_rate).
SCAFFOLD_SUCCESS = "scaffold_success"
SCAFFOLD_FALLBACK = "scaffold_fallback"


def _fallback_kind_for(failure_kind: str) -> str:
    # Transport-class failures (timeout / transport_error / budget_exhausted) keep
    # the existing timeout_then_fallback turn-kind (budget used to arrive as
    # "timeout" pre-B34-10, so this preserves continuity). parse/invalid live
    # results map to invalid_then_fallback; everything else (auth_failed /
    # provider_error / unknown) is an error_then_fallback.
    if failure_kind in ("timeout", "transport_error", "budget_exhausted"):
        return TIMEOUT_FALLBACK
    if failure_kind in ("invalid_action", "parse_failure"):
        return INVALID_FALLBACK
    return ERROR_FALLBACK


def augment_witch_observation(base_text: str, victim: str | None) -> str:
    """R-04 fix: the wolf kill is `werewolf_team`-visible, so the witch's role-filtered
    observation never includes tonight's victim — without it a live witch can never
    satisfy the `target==victim` save rule and is silently pushed toward a wolf win.
    Surface the victim into the WITCH'S OWN prompt only (this is the witch's turn, so
    no game-log event is added and nothing leaks to any other perspective)."""
    if victim is not None:
        return base_text + (
            f"\n今晚 {victim} 被狼人袭击。若用解药救人,witch_save 的 target 必须为 {victim}。"
        )
    return base_text + "\n今晚没有玩家被狼人袭击(无可救目标)。"


# Model-visible inline augmentation (byte-locked via tests/golden_prompts —
# spec 2026-06-10-prompt-versioning §3). Changing this string requires a
# PROMPT_VERSION bump.
HUNTER_SHOT_OBSERVATION_SUFFIX = "\n你已出局,作为猎人可开枪带走一名存活玩家,或选择不开枪。"


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
    provider_turns: list[dict[str, Any]] = field(default_factory=list)

    @property
    def completed(self) -> bool:
        return self.status == "completed"

    @property
    def live_requested_actions(self) -> int:
        return sum(1 for t in self.provider_turns if t.get("live_requested"))

    @property
    def live_success_actions(self) -> int:
        return sum(1 for t in self.provider_turns if t.get("kind") == LIVE_SUCCESS)

    @property
    def live_success_rate(self) -> float:
        """live_success_actions / live_requested_actions (P2-A-2 gate ②).
        1.0 when no live was requested (vacuous; the smoke also checks the
        absolute floor live_success_actions >= 20)."""
        denom = self.live_requested_actions
        return self.live_success_actions / denom if denom else 1.0


def build_emergent_config(game_id: str = "p2a1_emergent_001", seat_roles: dict[str, str] | None = None) -> GameConfig:
    """Default 6-player board: p1/p2 wolves, p3 seer, p4 witch, p5/p6 villagers.
    seat_roles (when given) overrides the per-seat role assignment (multiset preserved
    upstream); None -> the fixed default board (byte-identical to before)."""
    return build_default_config(game_id=game_id, seat_roles=seat_roles)


def build_emergent_hunter_config(game_id: str = "hunter_v11") -> GameConfig:
    """6-player hunter board: p1/p2 wolves, p3 seer, p4 witch, p5 villager, p6 hunter."""
    cfg = build_default_config(game_id=game_id)
    players = list(cfg.players)
    players[5] = EnginePlayer("p6", "hunter", "villager")
    return GameConfig(game_id=game_id, players=players)


class EmergentGameEngine:
    def __init__(
        self,
        config: GameConfig,
        agents: dict[str, Any],
        seed: int = 0,
        source_label: str | None = None,
        budget: EmergentBudget | None = None,
        runtime_events: Any | None = None,
        prompt_version: str = "prompt_v1",
        scaffold_agent: Any | None = None,
    ) -> None:
        self._config = config
        self._players_by_id: dict[str, EnginePlayer] = {p.player_id: p for p in config.players}
        self._seat_order: list[str] = [p.player_id for p in config.players]
        # R-30: the night resolution assumes ONE seer, ONE witch and ONE guard
        # (seers[0]/witches[0]/guards[0]); a board with extras would silently
        # deactivate them. Fail loud at construction instead so an unsupported
        # board can't run a god-view-divergent game.
        for _special in ("seer", "witch", "guard"):
            _count = sum(1 for p in config.players if p.role == _special)
            if _count > 1:
                raise ValueError(
                    f"EmergentGameEngine supports at most one {_special}; got {_count}"
                )
        self._agents = dict(agents)
        self._rng = random.Random(seed)
        self._source_label = source_label or "[deterministic fake provider output]"
        self._budget = budget or EmergentBudget()
        self._runtime_events = runtime_events

        self._events: list[dict[str, Any]] = []
        self._decisions: list[dict[str, Any]] = []
        self._consensus_entries: list[dict[str, Any]] = []
        self._failures: list[dict[str, Any]] = []
        self._provider_turns: list[dict[str, Any]] = []
        self._seq = 0
        self._d_counter = 0
        self._alive: set[str] = set(self._players_by_id)
        self._death_committed: set[str] = set()
        # L4 guard: the guard's previous EFFECTIVE protect target (fallback included,
        # spec §2 patch) — feeds RuntimeState.last_guarded_target (no-consecutive rule).
        self._last_guarded: str | None = None
        # Phase-3 swap: night joint resolution delegates to the Agent Action
        # Runtime's JointSettler, and per-action legality to its registry/validator.
        # The rules version is BOARD-derived: guard boards run rules_v1_2; every
        # other board keeps rules_v1_1. Behavior is identical either way (versioned
        # superset), but the rules CARD prints rules_version into model-visible
        # bytes — a blanket bump would silently rewrite the frozen v2/v3 chains'
        # version line (and the manifest stamp), so guardless boards must not move.
        _board_roles = {p.role for p in config.players}
        _ruleset = rules_v1_2() if "guard" in _board_roles else rules_v1_1()
        self.rules_version = _ruleset.rules_version
        self._registry = RoleAbilityRegistry(_ruleset)
        self._settler = JointSettler(_ruleset)
        self._validator = ActionValidator(self._registry)
        # SYS-B1: runtime-selectable prompt rendering chain (v1 default = legacy
        # bytes). get_renderer fail-louds on unknown versions — no silent fallback.
        self._renderer = get_renderer(prompt_version)
        self.prompt_version = prompt_version
        self._board_card = self._renderer.board_card(
            _ruleset, {p.player_id: p.role for p in config.players}
        )
        # SYS-B4: the scribe is NOT a player. A scaffold-requiring renderer (v3)
        # REQUIRES it (no silent scaffold-less run); other versions ignore it.
        self._scaffold_agent = scaffold_agent
        if self._renderer.requires_scaffold and scaffold_agent is None:
            raise ValueError(f"{prompt_version} requires a scaffold_agent (scribe provider)")
        # Cross-round claim ledger; scribe failures NEVER clear it (spec §3 ②).
        self._claim_ledger: list[dict[str, Any]] = []
        # Registry-driven action dispatch (Phase-3 ②a). Each migrated ability id maps to a
        # driver. Night order is explicit DATA (load-bearing: wolf BEFORE seer — both may draw
        # 0/1 from self._rng). The witch is DEFERRED (inline, ②b) so it is NOT in this map/order.
        self._RESOLVERS = {
            "guard_protect": self._run_guard,
            "werewolf_kill": self._run_wolf_kill,
            "seer_check": self._run_seer,
            "player_vote": self._run_vote_round,
        }

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
        return public_refs(self._events)

    def _private_refs(self, player_id: str) -> list[str]:
        return private_refs_for_role(self._events, self._players_by_id[player_id].role)

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
        self._flush_partial_logs()
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
        self._flush_partial_logs()

    def _record_failure(
        self, rnd: int, phase: str, actor: str, kind: str, reason: str, target: str | None = None
    ) -> None:
        self._failures.append(build_failure(self._game_id, rnd, phase, actor, kind, reason, target))

    # ---- log envelopes (single source of shape) ------------------------

    def _game_log_dict(self, result: dict[str, Any] | None) -> dict[str, Any]:
        """The game-log envelope. ``result=None`` is the in-progress (partial)
        shape used during the live run; the completed run passes the final result.
        Both share this one builder so the partial and the end-of-game log can
        never drift."""
        log: dict[str, Any] = {
            "game_id": self._game_id,
            "source_label": self._source_label,
            "players": [
                {"player_id": p.player_id, "role": p.role, "team": p.team}
                for p in self._config.players
            ],
            "events": self._events,
        }
        if result is not None:
            log["result"] = result
        return log

    def _decision_log_dict(self) -> dict[str, Any]:
        return {
            "decision_log_id": f"{self._game_id}_decision_log",
            "game_id": self._game_id,
            "source_label": self._source_label,
            "decisions": self._decisions,
        }

    # Partial-log filenames mirrored to the spine dir during a live run.
    _PARTIAL_LOG_NAMES = ("game-log.json", "decision-log.json")

    def _flush_partial_logs(self) -> None:
        """Mirror the in-progress game-log + decision-log to the spine dir so the
        live theater's projection can draw pointing lines (event.target) and speech
        bodies (data.summary) / reasons WHILE the game runs, instead of only after
        completion. No-op without a runtime writer (offline unit tests). The
        end-of-game complete log written by the launcher supersedes these."""
        if self._runtime_events is None:
            return
        self._runtime_events.write_partial_log("game-log.json", self._game_log_dict(result=None))
        self._runtime_events.write_partial_log("decision-log.json", self._decision_log_dict())

    def _discard_partial_logs(self) -> None:
        """Fail-closed: remove any partial logs a failed run left on disk."""
        if self._runtime_events is None:
            return
        for name in self._PARTIAL_LOG_NAMES:
            self._runtime_events.remove_partial_log(name)

    def _write_god_snapshot(self, name: str, rnd: int, phase: str) -> None:
        """Write a god-view snapshot to the runtime spine (P2-A-2 mandatory spine
        needs a non-empty snapshots/ dir). No-op without a runtime writer."""
        if self._runtime_events is None:
            return
        players = [{"player_id": p.player_id, "role": p.role, "team": p.team} for p in self._config.players]
        snap = build_god_snapshot(
            run_id=self._game_id, game_id=self._game_id, round=rnd, phase=phase,
            players=players, alive_players=sorted(self._alive),
            public_event_ids=self._public_refs(), private_event_ids=[],
        )
        self._runtime_events.write_snapshot(name, snap, visibility="internal", round=rnd, phase=phase, actor="system")

    def _write_role_snapshot(self, player_id: str) -> None:
        """Write one setup role_projection snapshot for a player.

        role/team/known_roles are static in the current 6-player board, so setup
        is enough for observer projection trust; alive state stays god-snapshot
        authoritative.
        """
        if self._runtime_events is None:
            return
        obs = self._build_obs(player_id, "setup", 0)
        snap = build_role_projection_snapshot(run_id=self._game_id, observation=obs)
        self._runtime_events.write_snapshot(
            f"role_view_{player_id}", snap,
            visibility="internal", round=0, phase="setup", actor=player_id,
        )

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

    def _events_by_id(self) -> dict[str, dict[str, Any]]:
        return {e["event_id"]: e for e in self._events}

    def _render_obs(self, obs: AgentObservation) -> RenderedObservation:
        return self._renderer.render_observation(obs, self._events_by_id())

    def _b1_seat_index(self):
        cached = getattr(self, "_b1_seat_index_cache", None)
        if cached is None:
            from werewolf_eval.invariants.visibility_oracle import seat_index_from_players
            cached = seat_index_from_players(
                [{"player_id": p.player_id, "role": p.role, "team": p.team}
                 for p in self._config.players])
            self._b1_seat_index_cache = cached
        return cached

    def _runtime_state(self, night_victim: str | None = None) -> RuntimeState:
        """Read-model for the Action Runtime registry/validator (Phase-3 swap)."""
        return RuntimeState(
            alive=frozenset(self._alive),
            roles={pid: p.role for pid, p in self._players_by_id.items()},
            night_victim=night_victim,
            last_guarded_target=self._last_guarded,
        )

    def _action_legal(self, actor: str, role: str, phase: str, action: AgentAction) -> bool:
        """Validate a returned action's (action, target) via the registry/validator
        (Phase-3 swap) — byte-equivalent to the prior inline target checks (the
        target is already alive-gated by ProviderAgent.decide, so the discriminator
        is the role-specific target_rule the predicate encodes)."""
        return self._validator.validate_in_state(
            ActionEnvelope.from_legacy(
                actor=actor, role=role, phase=phase, action=action.action,
                target=action.target, reason_summary="", decision_type="", confidence=1.0,
            ),
            self._runtime_state(),
        ).ok

    def _provider_action(
        self, player_id: str, phase: str, rnd: int
    ) -> tuple[AgentAction | None, ProviderActionError | Exception | None, dict[str, Any]]:
        """Charge budget, render ROLE-SAFE observation text, call the player's
        ProviderAgent (full validation), and record one rich provider_turn.
        Returns (action, error, turn): action is None on failure (caller falls
        back). The turn is appended to `self._provider_turns`; the caller may
        downgrade `turn["kind"]` to a fallback kind if it then rejects the live
        action on an engine-level game rule (so live_success_rate stays honest)."""
        self._budget.charge()  # may raise BudgetExhausted -> propagates to run()
        obs = self._build_obs(player_id, phase, rnd)
        rendered = self._render_obs(obs)
        agent = self._agents[player_id]
        # vote request (the only day-phase action path; hunter uses its own
        # site): a scaffold renderer (v3) injects digest + comparison program.
        # Input-side ONLY — the action system prompt / strict-JSON contract is
        # untouched (spec §0). Empty suffix for v1/v2 keeps bytes identical.
        obs_text = rendered.text + self._renderer.action_obs_suffix(phase, self._claim_ledger)
        # C12-01: day-phase action = vote; append _vote so the request_id never
        # collides with the same actor's night action (which shares the bare
        # f"{game_id}_r{rnd:02d}_{actor}" stem). Witch/speech/hunter/scribe already
        # carry their own suffixes; without this, artifacts.collect_provider_trace
        # dedup-by-request_id silently swallowed vote traces for night-acting seats.
        _req_suffix = "_vote" if phase == "day" else ""
        turn: dict[str, Any] = {
            "request_id": f"{self._game_id}_r{rnd:02d}_{player_id}{_req_suffix}",
            "round": rnd,
            "phase": phase,
            "actor": player_id,
            "response_kind": "action",
            "live_requested": True,
            "kind": None,
            "fallback_reason": None,
            "source_label": None,
            "model": getattr(agent.provider, "model", None),
            "token_usage": None,
            "observation_source_event_ids": list(rendered.source_event_ids),
        }
        assert_prompt_entitled(player_id, list(rendered.source_event_ids),
                               self._events_by_id(), self._b1_seat_index())
        try:
            action = agent.decide(
                obs,
                observation_text=obs_text,
                response_kind="action",
                max_output_tokens=ACTION_MAX_OUTPUT_TOKENS,
                prompt_version=self.prompt_version,
                board_card=self._board_card,
            )
        except ProviderActionError as exc:
            turn["kind"] = _fallback_kind_for(exc.failure.kind)
            turn["fallback_reason"] = exc.failure.reason
            self._provider_turns.append(turn)
            return None, exc, turn
        except Exception as exc:  # noqa: BLE001 - defensive; never abort the game
            turn["kind"] = ERROR_FALLBACK
            turn["fallback_reason"] = f"{type(exc).__name__}: {exc}"
            self._provider_turns.append(turn)
            return None, exc, turn
        resp = getattr(agent, "last_response", None)
        turn["kind"] = LIVE_SUCCESS
        if resp is not None:
            turn["source_label"] = resp.source_label
            turn["token_usage"] = dict(resp.token_usage)
        self._provider_turns.append(turn)
        return action, None, turn

    def _downgrade_turn(self, turn: dict[str, Any], reason: str) -> None:
        """A live action was returned but rejected by an engine game rule -> the
        live result was not used, so it must not count toward live_success."""
        turn["kind"] = INVALID_FALLBACK
        turn["fallback_reason"] = reason
        turn["source_label"] = None
        turn["token_usage"] = None

    # ---- pure-resolver bridge helpers ---------------------------------

    def _draw(self, pick: "RngPick") -> str:
        """Perform a resolver's deferred seeded draw against self._rng at the legacy site."""
        if pick.kind == "choice":
            return self._rng.choice(list(pick.over))
        return pick.over[self._rng.randrange(len(pick.over))]

    def _decision_window(self, rnd, actor, role, registry_phase, emit_phase, live_action, refs):
        return DecisionWindow(
            rnd=rnd, actor=actor, role=role, emit_phase=emit_phase, registry_phase=registry_phase,
            alive_seat_order=tuple(self._alive_in_seat_order()),
            roles={pid: p.role for pid, p in self._players_by_id.items()},
            public_refs=tuple(refs), live_action=live_action,
            validator=self._validator, runtime_state=self._runtime_state(),
        )

    def _run_single_turn(self, resolver, actor, role, registry_phase, emit_phase, request_phase, rnd, refs=()):
        """Drive ONE strict-path actor turn (seer / one voter) through a pure resolver.
        Side-effects (provider call, budget, turn dict, err-failure, rng draw, decision, emit)
        stay here; the resolver only decides. Returns the resolved target, or None on skip."""
        action, err, turn = self._provider_action(actor, request_phase, rnd)
        if err is not None:
            if isinstance(err, ProviderActionError):
                self._record_failure(rnd, emit_phase, actor, err.failure.kind, err.failure.reason, err.failure.target)
            else:
                self._record_failure(rnd, emit_phase, actor, "agent_error", f"{actor} raised {type(err).__name__}: {err}")
        window = self._decision_window(rnd, actor, role, registry_phase, emit_phase,
                                       action if err is None else None, refs)
        adj = resolver.adjudicate(window)
        if adj.skip:
            return None  # no-candidates bail. UNREACHABLE in live games (win-check guarantees
                         # >=1 candidate before any turn). A same-turn invalid-action failure/downgrade
                         # would be dropped here; legacy recorded it before bailing. Byte-inert (path dead).
        if adj.failure is not None:
            self._record_failure(rnd, emit_phase, actor, adj.failure.kind, adj.failure.reason, adj.failure.target)
        if adj.downgrade_reason is not None:
            self._downgrade_turn(turn, adj.downgrade_reason)
        target = adj.accepted_target if adj.rng_pick is None else self._draw(adj.rng_pick)
        plan = resolver.render(window, target, adj.decision_type)
        d = plan.decision
        self._decision(d.actor, d.scope, d.phase, d.action, d.target, d.dtype, d.reason,
                       refs=list(d.refs) or None, consensus_id=d.consensus_id)
        e = plan.event
        self._emit(e.phase, rnd, e.etype, e.actor, e.target, e.visibility, e.summary)
        return target

    def _run_seer(self, rnd):
        seers = [pid for pid in self._alive if self._players_by_id[pid].role == "seer"]
        if not seers:
            return None
        return self._run_single_turn(SeerResolver(), seers[0], "seer", "night", "night", "night", rnd)

    def _run_guard(self, rnd):
        guards = [pid for pid in self._alive if self._players_by_id[pid].role == "guard"]
        if not guards:
            return None
        target = self._run_single_turn(GuardResolver(), guards[0], "guard", "night", "night", "night", rnd)
        if target is not None:
            # the ACTUALLY effective protect target (fallback included) drives next
            # night's exclude_last_guarded — spec §2 patch: not the model's raw intent.
            self._last_guarded = target
        return target

    def _run_vote_round(self, rnd):
        refs = self._public_refs()
        tally: dict[str, int] = {}
        for voter in self._alive_in_seat_order():
            role = self._players_by_id[voter].role
            target = self._run_single_turn(VoteResolver(), voter, role, "day_vote", "day", "day", rnd, refs=refs)
            if target is not None:
                tally[target] = tally.get(target, 0) + 1
        if not tally:
            return None
        top = max(tally.values())
        leaders = sorted(t for t, c in tally.items() if c == top)
        if len(leaders) == 1:
            return leaders[0]
        return leaders[self._rng.randrange(len(leaders))]

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

    def _run_wolf_kill(self, rnd: int) -> str | None:
        wolves = [w for w in self._wolves() if w in self._alive]
        if not wolves:
            return None
        consensus_id = f"{self._game_id}_consensus_r{rnd:02d}"
        proposals: list[tuple[str, str]] = []
        for wolf in wolves:
            action, err, turn = self._provider_action(wolf, "night", rnd)
            if err is not None:
                if isinstance(err, ProviderActionError):
                    self._record_failure(rnd, "night", wolf, err.failure.kind, err.failure.reason, err.failure.target)
                else:
                    self._record_failure(rnd, "night", wolf, "agent_error", f"{wolf} raised {type(err).__name__}: {err}")
                continue
            if not self._action_legal(wolf, "werewolf", "night", action):
                self._record_failure(rnd, "night", wolf, "invalid_action", f"{wolf} proposed invalid kill {action.target}", action.target)
                self._downgrade_turn(turn, f"engine rejected kill target {action.target}")
                continue
            proposals.append((wolf, action.target))
        candidates = tuple(pid for pid in self._seat_order
                           if pid in self._alive and self._players_by_id[pid].role != "werewolf")
        ww = WolfWindow(rnd=rnd, wolves=tuple(wolves), proposals=tuple(proposals),
                        candidates=candidates, consensus_id=consensus_id)
        adj = WolfResolver().adjudicate(ww)
        if adj.skip:
            return None
        target = adj.fixed_target if adj.rng_pick is None else self._draw(adj.rng_pick)
        r = WolfResolver().render(ww, target, adj.is_fallback)
        self._consensus_entries.append(
            self._build_consensus_entry(consensus_id, rnd, wolves, target, r.primary, list(r.supporters), status=adj.status))
        self._decision(r.primary, "team", "night", "werewolf_kill", target, adj.decision_type, r.reason, consensus_id=consensus_id)
        self._emit("night", rnd, "werewolf_kill", r.primary, target, "werewolf_team", f"Wolf team kills {target}.")
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

    def _resolve_witch(self, rnd: int, victim: str | None, save_used: bool, poison_used: bool) -> tuple[bool, str | None, bool, bool]:
        """Returns (saved_victim, poison_target, new_save_used, new_poison_used)."""
        witches = [pid for pid in self._alive if self._players_by_id[pid].role == "witch"]
        if not witches:
            return False, None, save_used, poison_used
        witch = witches[0]
        self._budget.charge()  # may raise BudgetExhausted -> propagates to run()
        provider = self._agents[witch].provider
        obs = self._build_obs(witch, "night", rnd)
        rendered = self._render_obs(obs)
        witch_obs_text = augment_witch_observation(rendered.text, victim)
        witch_obs_text += self._renderer.witch_obs_suffix(self._board_card, victim, save_used)
        request = ProviderRequest(
            request_id=f"{self._game_id}_r{rnd:02d}_{witch}_witch",
            game_id=self._game_id,
            actor=witch,
            phase="night",
            round=rnd,
            observation=obs.to_dict(),
            allowed_actions=list(WITCH_ACTIONS),
            allowed_targets=sorted(self._alive),
            observation_text=witch_obs_text,
            response_kind="action",
            max_output_tokens=ACTION_MAX_OUTPUT_TOKENS,
            prompt_version=self.prompt_version,
            board_card=self._board_card,
        )
        turn: dict[str, Any] = {
            "request_id": request.request_id, "round": rnd, "phase": "night", "actor": witch,
            "response_kind": "action", "live_requested": True, "kind": None, "fallback_reason": None,
            "source_label": None, "model": getattr(provider, "model", None), "token_usage": None,
            "observation_source_event_ids": list(rendered.source_event_ids),
        }
        self._provider_turns.append(turn)
        assert_prompt_entitled(witch, list(rendered.source_event_ids),
                               self._events_by_id(), self._b1_seat_index())
        action_name = WITCH_PASS
        target: str | None = None
        try:
            response = provider.respond(request)
        except Exception as exc:  # noqa: BLE001 — transport/respond failure, NOT a parse failure
            # B12-02/03: classify the network/respond exception (transport / budget /
            # auth / provider) instead of lumping it with JSON parse errors. The
            # turn-kind follows _fallback_kind_for so transport != invalid_then_fallback.
            kind = classify_provider_failure_kind(exc)
            self._record_failure(rnd, "night", witch, kind, f"{witch} witch provider error: {exc}")
            turn["kind"] = _fallback_kind_for(kind)
            turn["fallback_reason"] = f"witch provider error: {exc}"
            turn["source_label"] = None
            turn["token_usage"] = None
        else:
            turn["source_label"] = response.source_label
            turn["token_usage"] = dict(response.token_usage)
            try:
                parsed = json.loads(response.raw_content)
                if not isinstance(parsed, dict):
                    raise ValueError("witch response not a JSON object")
            except Exception as exc:  # noqa: BLE001 — JSON parse failure
                self._record_failure(rnd, "night", witch, "parse_failure", f"{witch} witch parse failed: {exc}")
                self._downgrade_turn(turn, f"witch parse failed: {exc}")
            else:
                if "action" not in parsed:
                    # B12-01: a JSON-valid response missing the mandatory action key is a
                    # parse failure (matching ProviderAgent), NOT a silent live pass.
                    self._record_failure(rnd, "night", witch, "parse_failure", f"{witch} witch missing action key")
                    self._downgrade_turn(turn, f"{witch} witch missing action key")
                else:
                    action_name = parsed["action"]
                    target = parsed.get("target")
                    turn["kind"] = LIVE_SUCCESS

        # validate (a parsed-but-illegal potion use is rejected -> fall back to
        # pass AND downgrade the turn: the live result was not used)
        if action_name == WITCH_SAVE:
            if save_used or victim is None or target != victim:
                self._record_failure(rnd, "night", witch, "invalid_action", f"{witch} invalid witch_save target={target}", target)
                self._downgrade_turn(turn, f"invalid witch_save target={target}")
                action_name = WITCH_PASS
        elif action_name == WITCH_POISON:
            if poison_used or target not in self._alive or target == witch:
                self._record_failure(rnd, "night", witch, "invalid_action", f"{witch} invalid witch_poison target={target}", target)
                self._downgrade_turn(turn, f"invalid witch_poison target={target}")
                action_name = WITCH_PASS
        elif action_name != WITCH_PASS:
            self._record_failure(rnd, "night", witch, "invalid_action", f"{witch} unknown witch action {action_name}")
            self._downgrade_turn(turn, f"unknown witch action {action_name}")
            action_name = WITCH_PASS

        if action_name == WITCH_SAVE:
            self._decision(witch, "single", "night", WITCH_SAVE, victim, "inference_based", f"witch saves {victim}")
            self._emit("night", rnd, WITCH_SAVE, witch, victim, "witch", f"Witch {witch} saves {victim}.")
            return True, None, True, poison_used
        if action_name == WITCH_POISON:
            self._decision(witch, "single", "night", WITCH_POISON, target, "retaliatory", f"witch poisons {target}")
            self._emit("night", rnd, WITCH_POISON, witch, target, "witch", f"Witch {witch} poisons {target}.")
            return False, target, save_used, True
        # pass
        self._decision(witch, "single", "night", WITCH_PASS, "none", FALLBACK_DECISION_TYPE, f"{witch} uses no potion")
        self._emit("night", rnd, WITCH_PASS, witch, "none", "witch", f"Witch {witch} uses no potion.")
        return False, None, save_used, poison_used

    # ---- day sub-phases ------------------------------------------------

    def _resolve_speech(self, player_id: str, rnd: int) -> None:
        self._budget.charge()  # may raise BudgetExhausted -> propagates to run()
        provider = self._agents[player_id].provider
        obs = self._build_obs(player_id, SPEECH_REQUEST_PHASE, rnd)
        rendered = self._render_obs(obs)
        # graded guidance: speeches get the DIGEST only (information symmetry),
        # never the comparison program (b1 lesson: don't arm wolf fake-claims).
        # Non-v3 renderers return "" — bytes identical.
        obs_text = rendered.text + self._renderer.speech_obs_suffix(self._claim_ledger)
        request = ProviderRequest(
            request_id=f"{self._game_id}_r{rnd:02d}_{player_id}_speech",
            game_id=self._game_id,
            actor=player_id,
            phase=SPEECH_REQUEST_PHASE,
            round=rnd,
            observation=obs.to_dict(),
            allowed_actions=[],
            allowed_targets=[],
            observation_text=obs_text,
            response_kind="speech",
            max_output_tokens=SPEECH_MAX_OUTPUT_TOKENS,
            prompt_version=self.prompt_version,
            board_card=self._board_card,
        )
        turn: dict[str, Any] = {
            "request_id": request.request_id, "round": rnd, "phase": "day", "actor": player_id,
            "response_kind": "speech", "live_requested": True, "kind": None, "fallback_reason": None,
            "source_label": None, "model": getattr(provider, "model", None), "token_usage": None,
            "observation_source_event_ids": list(rendered.source_event_ids),
        }
        self._provider_turns.append(turn)
        assert_prompt_entitled(player_id, list(rendered.source_event_ids),
                               self._events_by_id(), self._b1_seat_index())
        text = ""
        try:
            response = provider.respond(request)
            text = response.raw_content or ""
            turn["source_label"] = response.source_label
            turn["token_usage"] = dict(response.token_usage)
        except Exception as exc:  # noqa: BLE001 - speech is non-adjudicating; never abort
            text = ""
            turn["fallback_reason"] = f"speech provider error: {exc}"
        text = text.strip()[:SPEECH_MAX_CHARS]
        if not text:
            # empty/whitespace live text -> placeholder; not a live_success turn
            text = SPEECH_EMPTY_PLACEHOLDER
            turn["kind"] = ERROR_FALLBACK if turn["fallback_reason"] else INVALID_FALLBACK
            if turn["kind"] == INVALID_FALLBACK and not turn["fallback_reason"]:
                turn["fallback_reason"] = "empty speech text"
            turn["source_label"] = None
            turn["token_usage"] = None
        else:
            turn["kind"] = LIVE_SUCCESS
        self._emit("day", rnd, "player_speech", player_id, "none", "public", text)

    def _run_scribe(self, rnd: int) -> None:
        """SYS-B4 scheme C: one extraction call per day round, AFTER speeches and
        BEFORE the vote. Budget-charged; recorded as a scaffold turn with
        live_requested=False (never dilutes player live_success_rate). A failed
        round adds nothing — the cross-round ledger is preserved."""
        speeches = [(e["actor"], e["data"]["summary"]) for e in self._events
                    if e["type"] == "player_speech" and e["round"] == rnd]
        if not speeches:
            return
        self._budget.charge()
        provider = self._scaffold_agent.provider
        request = ProviderRequest(
            request_id=f"{self._game_id}_r{rnd:02d}_scribe",
            game_id=self._game_id, actor="scribe", phase="day", round=rnd,
            observation={}, allowed_actions=[], allowed_targets=[],
            observation_text=render_scribe_input(rnd, speeches),
            response_kind="scaffold", max_output_tokens=SCRIBE_MAX_OUTPUT_TOKENS,
            temperature=0.0,                       # extraction task: kill nondeterminism
            prompt_version=self.prompt_version, board_card="",
        )
        turn: dict[str, Any] = {
            "request_id": request.request_id, "round": rnd, "phase": "day", "actor": "scribe",
            "response_kind": "scaffold", "live_requested": False, "kind": None,
            "fallback_reason": None, "source_label": None,
            "model": getattr(provider, "model", None), "token_usage": None,
            "observation_source_event_ids": [],
        }
        self._provider_turns.append(turn)
        claims = None
        try:
            response = provider.respond(request)
            turn["source_label"] = response.source_label
            turn["token_usage"] = dict(response.token_usage)
            claims = parse_scribe_claims(response.raw_content or "")
        except Exception as exc:  # noqa: BLE001 - scaffold is non-adjudicating; never abort
            turn["fallback_reason"] = f"scribe provider error: {exc}"
        if claims is None:
            turn["kind"] = SCAFFOLD_FALLBACK
            if not turn["fallback_reason"]:
                turn["fallback_reason"] = "scribe output unparseable"
            turn["source_label"] = None
            turn["token_usage"] = None
            return                                  # history PRESERVED (spec §3 ②)
        turn["kind"] = SCAFFOLD_SUCCESS
        for c in claims:
            c["round"] = rnd
        self._claim_ledger.extend(claims)

    # ---- death-triggered abilities (hunter v1.1) -----------------------

    def _trigger_on_death(self, dead: str, rnd: int, phase: str) -> None:
        """Fire a dead player's on_death ability (data-driven via the ruleset). For the
        hunter that is a model-driven shot; the shot victim may itself trigger (cascade —
        terminates because each pid is removed from _alive before recursing). No-op for any
        role with no on_death ability, so 4-role games are byte-unchanged."""
        role = self._players_by_id[dead].role
        if not self._registry.on_death_abilities(role):
            return
        target = self._resolve_hunter_shot(dead, rnd, phase)
        if target is not None and target in self._alive:
            self._alive.discard(target)
            assert_death_commit_once(target, self._death_committed)
            self._emit(phase, rnd, "player_died", "system", target, "all",
                       f"{target} was shot by {dead}.")
            self._trigger_on_death(target, rnd, phase)

    def _resolve_hunter_shot(self, hunter: str, rnd: int, phase: str) -> str | None:
        """Ask the hunter's provider for a shot (hunter_shoot) or a pass. Validate via the
        on_death ability's target predicate (exclude_self/alive — NOT the phase-keyed
        validator, which can't see event:on_death abilities); downgrade an illegal shot to a
        pass; charge budget; record a decision + provider_turn; emit the event. Returns the
        shot target, or None for a pass / no valid target. Draws NO self._rng, so it never
        perturbs the seeded RNG order of a 4-role game."""
        self._budget.charge()
        obs = self._build_obs(hunter, phase, rnd)
        rendered = self._render_obs(obs)
        request = ProviderRequest(
            request_id=f"{self._game_id}_r{rnd:02d}_{hunter}_shot",
            game_id=self._game_id, actor=hunter, phase=HUNTER_SHOT_REQUEST_PHASE, round=rnd,
            observation=obs.to_dict(),
            allowed_actions=["hunter_shoot", "hunter_pass"],
            allowed_targets=sorted(self._alive),
            observation_text=rendered.text + HUNTER_SHOT_OBSERVATION_SUFFIX,
            response_kind="action", max_output_tokens=ACTION_MAX_OUTPUT_TOKENS,
            prompt_version=self.prompt_version,
            board_card=self._board_card,
        )
        turn: dict[str, Any] = {
            "request_id": request.request_id, "round": rnd, "phase": phase, "actor": hunter,
            "response_kind": "action", "live_requested": True, "kind": None,
            "fallback_reason": None, "source_label": None,
            "model": getattr(self._agents[hunter].provider, "model", None), "token_usage": None,
            "observation_source_event_ids": list(rendered.source_event_ids),
        }
        self._provider_turns.append(turn)
        assert_prompt_entitled(hunter, list(rendered.source_event_ids),
                               self._events_by_id(), self._b1_seat_index())
        action_name, target = "hunter_pass", None
        try:
            response = self._agents[hunter].provider.respond(request)
        except Exception as exc:  # noqa: BLE001 — transport/respond failure, NOT a parse failure
            # B12-02/03 parity with the witch resolver.
            kind = classify_provider_failure_kind(exc)
            self._record_failure(rnd, phase, hunter, kind, f"{hunter} hunter provider error: {exc}")
            turn["kind"] = _fallback_kind_for(kind)
            turn["fallback_reason"] = f"hunter provider error: {exc}"
            turn["source_label"] = None
            turn["token_usage"] = None
        else:
            turn["source_label"] = response.source_label
            turn["token_usage"] = dict(response.token_usage)
            try:
                parsed = json.loads(response.raw_content)
                if not isinstance(parsed, dict):
                    raise ValueError("hunter response not a JSON object")
            except Exception as exc:  # noqa: BLE001 — JSON parse failure
                self._record_failure(rnd, phase, hunter, "parse_failure", f"{hunter} hunter parse failed: {exc}")
                self._downgrade_turn(turn, f"hunter parse failed: {exc}")
            else:
                if "action" not in parsed:
                    # B12-01: missing mandatory action key is a parse failure, not a silent pass.
                    self._record_failure(rnd, phase, hunter, "parse_failure", f"{hunter} hunter missing action key")
                    self._downgrade_turn(turn, f"{hunter} hunter missing action key")
                else:
                    action_name = parsed["action"]
                    target = parsed.get("target")
                    turn["kind"] = LIVE_SUCCESS

        if action_name == "hunter_shoot":
            ab = next((a for a in self._registry.on_death_abilities("hunter")
                       if a.action_id == "hunter_shoot"), None)
            pred = TARGET_RULES.get(ab.target_rule) if ab else None
            legal = pred is not None and target is not None and pred(self._runtime_state(), hunter, target)
            if not legal:
                self._record_failure(rnd, phase, hunter, "invalid_action", f"{hunter} invalid hunter_shoot {target}", target)
                self._downgrade_turn(turn, f"invalid hunter_shoot {target}")
                action_name, target = "hunter_pass", None
        elif action_name != "hunter_pass":
            # an unknown but parseable action -> flag + downgrade (parity with the witch
            # resolver), so a malformed live response doesn't inflate live_success_rate.
            self._record_failure(rnd, phase, hunter, "invalid_action", f"{hunter} unknown hunter action {action_name}", target)
            self._downgrade_turn(turn, f"unknown hunter action {action_name}")
            action_name, target = "hunter_pass", None

        if action_name == "hunter_shoot" and target is not None:
            self._decision(hunter, "single", phase, "hunter_shoot", target, "retaliatory", f"hunter {hunter} shoots {target}")
            self._emit(phase, rnd, "hunter_shoot", hunter, target, "public", f"Hunter {hunter} shoots {target}.")
            return target
        self._decision(hunter, "single", phase, "hunter_pass", "none", FALLBACK_DECISION_TYPE, f"{hunter} does not shoot")
        self._emit(phase, rnd, "hunter_pass", hunter, "none", "public", f"Hunter {hunter} does not shoot.")
        return None

    # ---- main loop -----------------------------------------------------

    def run(self) -> GameOutcome:
        try:
            return self._run_inner()
        except BudgetExhausted as exc:
            return self._failed_outcome("budget_exhausted", str(exc))

    def _failed_outcome(self, end_condition: str, reason: str) -> GameOutcome:
        # Fail-closed: setup/early events may have mirrored a partial game-log to
        # disk; a failed run must leave NO game log (matches the launcher, which
        # writes only the failure audit on failure).
        self._discard_partial_logs()
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
            provider_turns=self._provider_turns,
        )

    def _run_inner(self) -> GameOutcome:
        game_id = self._game_id
        # setup
        self._emit("setup", 0, "role_assignment", "system", "none", "public", "Roles assigned to all 6 players.")
        self._write_god_snapshot("setup_god_view", 0, "setup")
        for _pid in self._seat_order:
            self._write_role_snapshot(_pid)

        save_used = False
        poison_used = False
        winner: str | None = None
        end_condition = ""
        end_round = 0

        for rnd in range(1, self._budget.max_day_rounds + 1):
            end_round = rnd
            # ---- NIGHT ---- registry-driven dispatch for migrated abilities
            victim = None
            guard_target = None
            for ability_id in NIGHT_DISPATCH_ORDER:
                result = self._RESOLVERS[ability_id](rnd)
                if ability_id == "werewolf_kill":
                    victim = result
                elif ability_id == "guard_protect":
                    guard_target = result
            # witch — DEFERRED inline (BLOCKING: RuntimeState potion ledger pending, ②b)
            saved, poison_target, save_used, poison_used = self._resolve_witch(rnd, victim, save_used, poison_used)

            # Night settlement delegates to the Agent Action Runtime's JointSettler
            # (Phase-3 swap). Byte-identical to the prior inline logic for rules_v1 —
            # proven by tests/test_action_runtime_parity.py and the full suite below.
            deaths: list[str] = list(
                self._settler.resolve_night(
                    NightIntents(wolf_victim=victim, saved=saved,
                                 poison_target=poison_target, guard_target=guard_target),
                    self._runtime_state(),
                ).deaths
            )
            for pid in deaths:
                if pid not in self._alive:   # a hunter shot may have already killed a co-victim
                    continue
                self._alive.discard(pid)
                assert_death_commit_once(pid, self._death_committed)
                self._emit("night", rnd, "player_died", "system", pid, "all", f"{pid} died during the night.")
                self._trigger_on_death(pid, rnd, "night")

            self._write_god_snapshot(f"god_view_r{rnd}_night", rnd, "night")

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

            if self._renderer.requires_scaffold:
                self._run_scribe(rnd)

            eliminated = self._RESOLVERS["player_vote"](rnd)
            if eliminated is not None:
                self._alive.discard(eliminated)
                assert_death_commit_once(eliminated, self._death_committed)
                role = self._players_by_id[eliminated].role
                self._emit("day", rnd, "player_eliminated", "system", eliminated, "all", f"{eliminated} eliminated by vote.")
                self._emit("day", rnd, "role_revealed", "system", eliminated, "all", f"{eliminated} revealed as {role}.")
                self._trigger_on_death(eliminated, rnd, "day")

            self._write_god_snapshot(f"god_view_r{rnd}_day", rnd, "day")

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
        self._write_god_snapshot("final_god_view", end_round, "game_end")

        game_log = self._game_log_dict(
            result={
                "winner": winner,
                "end_round": end_round,
                "survivors": sorted(self._alive),
                "end_condition": end_condition,
            }
        )
        decision_log = self._decision_log_dict()
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
            provider_turns=self._provider_turns,
        )

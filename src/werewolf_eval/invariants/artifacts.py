from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunArtifacts:
    """Unified read view over a finished game — either an in-memory GameOutcome
    or a persisted run_dir. NEVER raises: missing/malformed streams are recorded
    in `gaps` so the checker can report `artifact_gap` instead of crashing."""

    game_id: str
    players: list[dict[str, Any]]
    events: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    provider_turns: list[dict[str, Any]]
    result: dict[str, Any] | None
    gaps: tuple[str, ...] = ()

    @classmethod
    def from_outcome(cls, outcome: Any) -> "RunArtifacts":
        gl = getattr(outcome, "game_log", None) or {}
        dl = getattr(outcome, "decision_log", None) or {}
        turns = list(getattr(outcome, "provider_turns", None) or [])
        gaps: list[str] = []
        if not gl.get("events"):
            gaps.append("game_log.events")
        return cls(
            game_id=str(gl.get("game_id", "")),
            players=list(gl.get("players", [])),
            events=list(gl.get("events", [])),
            decisions=list(dl.get("decisions", [])),
            provider_turns=turns,
            result=gl.get("result"),
            gaps=tuple(gaps),
        )

    @classmethod
    def from_run_dir(cls, run_dir: str | Path) -> "RunArtifacts":
        run_dir = Path(run_dir)

        def _load(name: str) -> Any:
            p = run_dir / name
            if not p.is_file():
                return None
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None

        gl = _load("game-log.json") or {}
        dl = _load("decision-log.json") or {}
        pt = _load("provider-turns.json")
        gaps: list[str] = []
        if not gl.get("events"):
            gaps.append("game-log.json")
        turns: list[dict[str, Any]] = []
        if isinstance(pt, dict) and isinstance(pt.get("turns"), list):
            turns = list(pt["turns"])
        else:
            gaps.append("provider-turns.json")
        return cls(
            game_id=str(gl.get("game_id", "")),
            players=list(gl.get("players", [])),
            events=list(gl.get("events", [])),
            decisions=list(dl.get("decisions", [])),
            provider_turns=turns,
            result=gl.get("result"),
            gaps=tuple(gaps),
        )

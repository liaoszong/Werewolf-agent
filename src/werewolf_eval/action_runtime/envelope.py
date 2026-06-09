from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActionEnvelope:
    """Uniform internal action intent. ``targets`` is 0/1/N; ``params`` carries
    ability-specific extras. ``.target`` projects to the legacy single-target field
    for decision_log / game_log (spec §4.7).

    Byte-parity caveat (Phase 3): the engine writes the literal string ``"none"``
    for no-target rows (witch_pass, speeches, announcements — emergent_engine.py:720),
    whereas ``.target`` returns Python ``None`` for empty ``targets``. The swap-time
    serializer MUST map empty targets back to ``"none"`` (not ``null``) to keep those
    rows byte-identical — the ``.target`` property alone is not sufficient."""

    actor: str
    role: str
    phase: str
    action: str
    targets: list[str]
    params: dict[str, Any]
    reason_summary: str
    decision_type: str
    confidence: float

    @property
    def target(self) -> str | None:
        return self.targets[0] if self.targets else None

    @classmethod
    def from_legacy(
        cls,
        *,
        actor: str,
        role: str,
        phase: str,
        action: str,
        target: str | None,
        reason_summary: str,
        decision_type: str,
        confidence: float,
    ) -> "ActionEnvelope":
        return cls(
            actor=actor,
            role=role,
            phase=phase,
            action=action,
            targets=[] if target in (None, "", "none") else [target],
            params={},
            reason_summary=reason_summary,
            decision_type=decision_type,
            confidence=confidence,
        )

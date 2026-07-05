"""Ablation arm config + paired, per-arm-multiset layout generation."""
from __future__ import annotations
import random
from dataclasses import dataclass

SEATS = ("p1", "p2", "p3", "p4", "p5", "p6")
CANONICAL_MULTISET = ("werewolf", "werewolf", "seer", "witch", "villager", "villager")
# L4 守卫板:6p 保护型结构替换臂(换一个民,spec §1 — NOT a pure addition)
GUARD_MULTISET = ("werewolf", "werewolf", "seer", "witch", "guard", "villager")


@dataclass(frozen=True)
class Arm:
    label: str
    prompt_version: str          # "prompt_v1" (baseline) | "prompt_v2" (b1) — runtime selector
    n_games: int = 45
    seed_base: int = 1000        # GLOBAL-fixed across arms -> paired comparison
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"
    multiset: tuple[str, ...] = CANONICAL_MULTISET  # per-arm board (l4_guard swaps a villager for the guard)
    roleplay_arm: str | None = None  # explicit P3-A roleplay shadow arm id; None keeps baseline off

    def seed_for(self, index: int) -> int:
        return self.seed_base + index


def layout_for(arm: Arm, index: int) -> dict[str, str]:
    """Deterministic per-index shuffled layout. Same index -> same seed -> same RNG
    stream for ALL arms; default-multiset arms stay byte-identical to the historical
    snapshots. A guard-board arm consumes the SAME stream over its own multiset, so
    cross-arm pairing is SEED pairing (boards differ by construction, spec §5)."""
    rng = random.Random(arm.seed_for(index))
    roles = list(arm.multiset)
    rng.shuffle(roles)
    return dict(zip(SEATS, roles))

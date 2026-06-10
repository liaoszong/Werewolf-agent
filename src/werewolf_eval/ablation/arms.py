"""Ablation arm config + paired, canonical-multiset layout generation."""
from __future__ import annotations
import random
from dataclasses import dataclass

SEATS = ("p1", "p2", "p3", "p4", "p5", "p6")
CANONICAL_MULTISET = ("werewolf", "werewolf", "seer", "witch", "villager", "villager")


@dataclass(frozen=True)
class Arm:
    label: str
    prompt_version: str          # "prompt_v1" (baseline) | "prompt_v2" (b1) — runtime selector
    n_games: int = 45
    seed_base: int = 1000        # GLOBAL-fixed across arms -> paired comparison
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"

    def seed_for(self, index: int) -> int:
        return self.seed_base + index


def layout_for(arm: Arm, index: int) -> dict[str, str]:
    """Deterministic per-index shuffled layout. Same index -> same layout for ALL arms
    (depends only on seed, not on the arm), so arms are paired."""
    rng = random.Random(arm.seed_for(index))
    roles = list(CANONICAL_MULTISET)
    rng.shuffle(roles)
    return dict(zip(SEATS, roles))

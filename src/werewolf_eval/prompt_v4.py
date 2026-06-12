"""prompt_v4 (l4_guard_witch_coord): witch antidote-coordination guidance.
Injected into the witch's OWN night action observation only (engine
_resolve_witch), gated on board-has-guard AND victim present AND antidote
unused; every other state renders "" so prompt_v4 stays byte-identical to
prompt_v3 there (spec §5 canaries). NO engine / llm_providers import (they
import US). Spec: docs/superpowers/specs/2026-06-12-l4-guard-witch-coord-arm-design.md.
Visibility hard gate (spec §3): inputs are public board composition plus the
witch's own state — NEVER the guard's actual target or aliveness."""
from __future__ import annotations

from werewolf_eval.prompt_v3 import _board_card_has_guard

WITCH_COORD_GUIDANCE = (
    "【解药协调提示】本局存在守卫。守卫每晚守护一名玩家;若你解药救下的人当晚同时被守卫守护,"
    "该玩家会因「同守同救」规则死亡。你无法知道守卫今晚守了谁。用药前请权衡:该目标是否很可能"
    "正被守卫保护,例如已公开跳出且被全场关注的预言家。信息不足时不要机械地夜1必救;解药整局"
    "仅一瓶,应优先用于你认为\"死亡风险高、且不太可能同时被守卫守护\"的目标。"
)


def render_witch_coord_suffix(board_card: str | None, victim: str | None, save_used: bool) -> str:
    """The ONLY prompt_v4 surface. Three-condition gate (spec §3): all other
    states return "" so the composed witch observation is byte-identical to
    prompt_v3 (spec §5 canaries pin this)."""
    if _board_card_has_guard(board_card) and victim is not None and not save_used:
        return "\n" + WITCH_COORD_GUIDANCE
    return ""

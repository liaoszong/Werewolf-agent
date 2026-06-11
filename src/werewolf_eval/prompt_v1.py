"""prompt_v1 (baseline): the byte-locked v1 observation renderer and speech
contract, moved VERBATIM from emergent_engine.py / llm_providers.py so the
PromptRenderer registry (prompt_renderers.py) can package all versions without
an import cycle (engine/providers import the registry; the registry imports US).
The move is NOT a version bump — bytes stay locked by
tests/golden_prompts/prompt_v1; any byte change still requires the full
versioning flow (see prompt_version.py docstring)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from werewolf_eval.provider_contract import ProviderRequest


@dataclass(frozen=True)
class RenderedObservation:
    """Readable, ROLE-SAFE observation text for a live provider prompt, plus the
    exact event ids it was rendered from (for the visibility-no-feed-leak gate)."""

    text: str
    source_event_ids: list[str]


def render_observation_text(
    obs: Any, events_by_id: dict[str, dict[str, Any]]
) -> RenderedObservation:
    """Render `obs` into readable prompt text. HARD invariant (P2-A-2 gate ①):
    rendered ONLY from `obs.public_event_ids ∪ obs.private_event_ids` and
    `obs.known_roles` — never the global event store or global role map. The
    caller passes `events_by_id`, but this function touches only the ids that
    already appear in `obs`'s role-filtered ref lists, so a hidden event whose id
    is not in those lists can never leak in.
    """
    visible_ids: list[str] = []
    seen: set[str] = set()
    for ref in list(obs.public_event_ids) + list(obs.private_event_ids):
        if ref not in seen:
            seen.add(ref)
            visible_ids.append(ref)

    lines: list[str] = [
        f"你是 {obs.player_id}(身份:{obs.role},阵营:{obs.team})。",
        f"当前:第 {obs.round} 轮 {obs.phase} 阶段。存活玩家:{', '.join(obs.alive_players)}。",
    ]
    # known_roles comes ONLY from the role-filtered observation (self + wolf
    # teammates for a wolf), never a global seat-role index / god snapshot.
    known_others = {pid: role for pid, role in obs.known_roles.items() if pid != obs.player_id}
    if known_others:
        lines.append("你已知的身份:" + ", ".join(f"{pid}={role}" for pid, role in sorted(known_others.items())) + "。")

    source_event_ids: list[str] = []
    event_lines: list[str] = []
    for ref in visible_ids:
        event = events_by_id.get(ref)
        if event is None:
            continue
        summary = event.get("data", {}).get("summary", "")
        if not summary:
            continue
        source_event_ids.append(ref)
        event_lines.append(f"- (r{event.get('round')} {event.get('phase')}) {summary}")
    if event_lines:
        lines.append("你能看到的事件:")
        lines.extend(event_lines)

    return RenderedObservation(text="\n".join(lines), source_event_ids=source_event_ids)


def build_speech_system_prompt(request: ProviderRequest) -> str:
    # Free text, NO JSON, NO allowed_actions[0] (which would IndexError for a
    # speech request with empty allowed_actions).
    return (
        f"你是狼人杀里的 {request.actor}(第 {request.round} 轮,白天发言)。"
        f"请用自然口吻发言,3-5 句或 120-180 字。"
        f"发言应尽量包含:当前局势判断、你怀疑或相信的对象、一个具体理由、本轮投票倾向。"
        f"不要使用固定小标题,不要输出 JSON,直接说话。"
    )

from __future__ import annotations

from typing import Callable

from werewolf_eval.action_runtime.state import RuntimeState

# A death-trigger handler: (state, dead_player) -> NEW deaths to enqueue.
DeathTrigger = Callable[[RuntimeState, str], "list[str]"]


class TriggerSystem:
    """Reactive death-resolution QUEUE (spec §4.10). A batch of deaths is
    processed; each death may enqueue more (lover heartbreak -> hunter shot ->
    wolf-king shot -> ...). Guarantees:

    * **Transitive closure** — keeps processing until the queue drains.
    * **Deterministic ordering** — the next death to resolve is chosen by the
      deterministic ``death_order_key`` (here: ``seat_index``), NEVER a seeded
      shuffle, so a replay can explain "why A fired before B".
    * **Cycle termination** — a `seen` set means each player is processed at most
      once (mutual lovers can't loop forever).

    For ``rules_v1`` no role registers a death trigger, so ``resolve`` just
    returns the input deaths (seat-ordered). The queue is exercised here for
    Phase 3's hunter and the v3 lovers/wolf-king chains.
    """

    def __init__(self, triggers: dict[str, DeathTrigger], seat_order: list[str]) -> None:
        self._triggers = dict(triggers)          # role -> handler
        self._seat_order = list(seat_order)

    def _seat_index(self, pid: str) -> int:
        return self._seat_order.index(pid) if pid in self._seat_order else len(self._seat_order)

    def resolve(self, initial_deaths: list[str], state: RuntimeState) -> list[str]:
        """Return the full ordered list of deaths after the chain settles."""
        processed: list[str] = []
        seen: set[str] = set()
        queue: list[str] = sorted(initial_deaths, key=self._seat_index)
        while queue:
            dead = queue.pop(0)
            if dead in seen:
                continue
            seen.add(dead)
            processed.append(dead)
            handler = self._triggers.get(state.roles.get(dead, ""))
            if handler is None:
                continue
            # Gate on still-alive (mirror the settler) so a buggy handler can't inject
            # a phantom death row; de-dup against already-processed.
            new_deaths = [d for d in handler(state, dead) if d not in seen and d in state.alive]
            queue.extend(new_deaths)
            queue.sort(key=lambda p: (self._seat_index(p), p))   # deterministic (seat, then id)
        return processed

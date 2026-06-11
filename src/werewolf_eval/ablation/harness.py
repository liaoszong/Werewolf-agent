"""Run one ablation arm: N games, fresh provider per game, hard-fail on budget,
live-rate filtering happens in metrics.aggregate."""
from __future__ import annotations
import json, time, traceback
from pathlib import Path

from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game, _deepseek_factory
from werewolf_eval.ablation.arms import Arm, layout_for
from werewolf_eval.ablation.metrics import aggregate

MAX_REQUESTS_PER_GAME = 80   # measured: one game uses ~19-23 requests; ~3x headroom


def _deepseek_factory_builder(arm: Arm, api_key: str):
    # FRESH provider per call -> per-game 80-request budget, never shared across games.
    return _deepseek_factory(api_key=api_key, base_url=arm.base_url, model=arm.model,
                             timeout_seconds=40, max_tokens=256, max_requests=MAX_REQUESTS_PER_GAME)


def run_arm(arm: Arm, out_root: Path, api_key: str | None = None, factory_builder=None) -> dict:
    """factory_builder(arm, api_key) -> ProviderFactory (fresh per game). Defaults to DeepSeek."""
    out_root = Path(out_root)
    arm_dir = out_root / arm.label
    arm_dir.mkdir(parents=True, exist_ok=True)
    index_lines = []
    for i in range(arm.n_games):
        gid = f"{arm.label}_{i:03d}"
        out_dir = arm_dir / gid
        seat_roles = layout_for(arm, i)
        seed = arm.seed_for(i)
        rec = {"game_id": gid, "seed": seed, "seat_roles": seat_roles, "prompt_version": arm.prompt_version}
        t0 = time.time()
        for attempt in range(4):
            try:
                factory = (factory_builder or _deepseek_factory_builder)(arm, api_key)
                run_emergent_deepseek_game(
                    game_id=gid, out_dir=out_dir, provider_factory=factory,
                    model=arm.model, seed=seed,
                    max_requests_per_game=MAX_REQUESTS_PER_GAME, max_day_rounds=3,
                    seat_roles=seat_roles,
                )
                gl = out_dir / "game-log.json"
                rec["status"] = "completed" if gl.exists() else "failed"
                break
            except PermissionError:   # Windows Defender transient lock on atomic rename
                time.sleep(1.5); rec["status"] = "perm_retry"; continue
            except Exception as e:
                rec["status"] = "exception"; rec["error"] = f"{type(e).__name__}: {e}"
                traceback.print_exc(); break
        rec["secs"] = round(time.time() - t0, 1)
        index_lines.append(rec)
        (arm_dir / "_index.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in index_lines), encoding="utf-8")

    run_dirs = [arm_dir / f"{arm.label}_{i:03d}" for i in range(arm.n_games)]
    metrics = aggregate(run_dirs)
    result = {"arm": arm.label, "prompt_version": arm.prompt_version,
              "n_games": arm.n_games, "metrics": metrics}
    (arm_dir / "_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result

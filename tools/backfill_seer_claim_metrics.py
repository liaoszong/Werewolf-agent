# tools/backfill_seer_claim_metrics.py
"""One-shot backfill (L4 spec §8 前置): compute the L4 seer-survival metric family on
EXISTING arm runs (b4/b1) so the l4_guard arm has a paired baseline. Read-only over
.runs; prints one JSON object per arm dir given."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.ablation import metrics

KEYS = ("n_valid", "n_total", "seer_death_rate", "seer_night_death_rate",
        "seer_claim_to_night_survival_rate", "seer_claim_to_night_survival_n",
        "guard_target_seer_rate", "guard_success_rate", "avg_peaceful_nights",
        "wolf_win_rate")


def backfill(arm_dir: Path) -> dict:
    run_dirs = sorted(d for d in arm_dir.iterdir()
                      if d.is_dir() and (d / "game-log.json").exists())
    agg = metrics.aggregate(run_dirs)
    return {"arm_dir": arm_dir.name, **{k: agg.get(k) for k in KEYS}}


def main(argv: list[str]) -> int:
    out = [backfill(Path(p)) for p in argv]
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""CLI: python -m werewolf_eval.ablation run <label> --prompt-version prompt_v1 [--n 45]
         python -m werewolf_eval.ablation compare <armA_dir> <armB_dir>"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from werewolf_eval.ablation.arms import Arm, CANONICAL_MULTISET, GUARD_MULTISET
from werewolf_eval.ablation.harness import run_arm
from werewolf_eval.ablation.metrics import compare

_BOARDS = {"standard": CANONICAL_MULTISET, "guard": GUARD_MULTISET}


def _run(a):
    api_key = os.environ.get(a.api_key_env, "")
    if not api_key:
        print(f"missing {a.api_key_env}", file=sys.stderr); return 1
    arm = Arm(label=a.label, prompt_version=a.prompt_version, n_games=a.n,
              seed_base=a.seed_base, model=a.model, multiset=_BOARDS[a.board])
    res = run_arm(arm, out_root=Path(a.out_root), api_key=api_key)
    print(json.dumps(res["metrics"], ensure_ascii=False, indent=1))
    return 0


def _compare(a):
    A = json.loads((Path(a.arm_a) / "_metrics.json").read_text(encoding="utf-8"))
    B = json.loads((Path(a.arm_b) / "_metrics.json").read_text(encoding="utf-8"))
    A["metrics"]["label"], B["metrics"]["label"] = A["arm"], B["arm"]
    print(f"{'metric':32} {A['arm']:>12} {B['arm']:>12} {'delta':>10}")
    for r in compare(A["metrics"], B["metrics"]):
        d = "" if r["delta"] is None else f"{r['delta']:+.3f}"
        print(f"{r['metric']:32} {str(r['a']):>12} {str(r['b']):>12} {d:>10}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="werewolf_eval.ablation")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.set_defaults(fn=_run)
    r.add_argument("label"); r.add_argument("--prompt-version", dest="prompt_version", default="prompt_v1")
    r.add_argument("--n", type=int, default=45); r.add_argument("--seed-base", dest="seed_base", type=int, default=1000)
    r.add_argument("--model", default="deepseek-v4-flash"); r.add_argument("--out-root", dest="out_root", default=".runs/ablation")
    r.add_argument("--api-key-env", dest="api_key_env", default="DEEPSEEK_API_KEY")
    r.add_argument("--board", choices=sorted(_BOARDS), default="standard")
    c = sub.add_parser("compare"); c.set_defaults(fn=_compare)
    c.add_argument("arm_a"); c.add_argument("arm_b")
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())

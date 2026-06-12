"""Run one ablation arm: N games, fresh provider per game, hard-fail on budget,
live-rate filtering happens in metrics.aggregate."""
from __future__ import annotations
import json, re, time, traceback
from pathlib import Path

from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game, _deepseek_factory
from werewolf_eval.ablation.arms import Arm, layout_for
from werewolf_eval.ablation.metrics import aggregate
from werewolf_eval.prompt_renderers import get_renderer
from werewolf_eval.prompt_version import KNOWN_PROMPT_VERSIONS
from werewolf_eval.invariants.checker import check_run as _check_run

MAX_REQUESTS_PER_GAME = 80   # measured: one game uses ~19-23 requests; ~3x headroom


def _deepseek_factory_builder(arm: Arm, api_key: str):
    # FRESH provider per call -> per-game 80-request budget, never shared across games.
    return _deepseek_factory(api_key=api_key, base_url=arm.base_url, model=arm.model,
                             timeout_seconds=40, max_tokens=256, max_requests=MAX_REQUESTS_PER_GAME)


def _deepseek_scaffold_factory_builder(arm: Arm, api_key: str):
    # Independent scribe provider instance per game (never a seat's instance:
    # seat trace/token accounting must stay clean — spec §3 评审③). Low temp is
    # request-level (the engine stamps temperature=0.0 on scribe requests), so
    # no provider-config change is needed here.
    def build():
        factory = _deepseek_factory(api_key=api_key, base_url=arm.base_url, model=arm.model,
                                    timeout_seconds=40, max_tokens=512, max_requests=MAX_REQUESTS_PER_GAME)
        return factory("scribe")
    return build


def run_arm(arm: Arm, out_root: Path, api_key: str | None = None, factory_builder=None,
            scaffold_factory_builder=None) -> dict:
    """factory_builder(arm, api_key) -> ProviderFactory (fresh per game). Defaults to DeepSeek.
    scaffold_factory_builder(arm, api_key) -> (() -> ProviderAgent); prompt_v3 必需,缺省用 DeepSeek scribe 工厂."""
    if arm.prompt_version not in KNOWN_PROMPT_VERSIONS:
        raise ValueError(
            f"prompt_version {arm.prompt_version!r} is not a known renderer "
            f"(known: {KNOWN_PROMPT_VERSIONS})"
        )
    requires_scaffold = get_renderer(arm.prompt_version).requires_scaffold
    if requires_scaffold and scaffold_factory_builder is None:
        scaffold_factory_builder = _deepseek_scaffold_factory_builder
    out_root = Path(out_root)
    arm_dir = out_root / arm.label
    arm_dir.mkdir(parents=True, exist_ok=True)
    # P1-3: exclusive lock to prevent TOCTOU race if two concurrent run_arm()
    # calls target the same label. open(..., "x") is atomic on POSIX and
    # Windows (NTFS). If the lock file already exists, another process is
    # running this arm — fail loud.
    lock_path = arm_dir / "_run.lock"
    try:
        lock_fd = open(lock_path, "x", encoding="utf-8")
        lock_fd.write(f"pid={__import__('os').getpid()}\n")
        lock_fd.close()
    except FileExistsError:
        raise FileExistsError(
            f"arm_dir {arm_dir} is locked by another process "
            f"(lock file {lock_path} exists). Refusing concurrent run."
        )
    # C12-04: refuse to run into a populated arm_dir. Old-version completed
    # games (status="completed" via gl.exists()) would otherwise silently mix
    # into the new run's aggregate and metrics. A fresh empty dir is fine;
    # any prior game subdir or rollup file is not.
    game_pat = re.compile(re.escape(arm.label) + r"_\d{3}$")
    prior_games = [p for p in arm_dir.iterdir()
                   if p.is_dir() and game_pat.match(p.name)]
    prior_rollup = [arm_dir / f for f in ("_metrics.json", "_index.jsonl")
                    if (arm_dir / f).exists()]
    if prior_games or prior_rollup:
        # P2-3: error message reflects the actual check (prior artifacts, not
        # generic "not empty" which would imply any file is rejected).
        raise FileExistsError(
            f"arm_dir {arm_dir} contains prior ablation artifacts "
            f"({len(prior_games)} game dir(s), "
            f"{len(prior_rollup)} rollup file(s)); "
            f"refusing to mix with prior run. Delete or pick a new label."
        )
    index_lines = []
    # C3-4: per-arm invariants rollup. `check_run` runs after every completed
    # game; hard violations (severity=="error") are counted and bucketed by
    # id. artifact_gap severity is informational and excluded from the hard
    # count (it's reported separately via RunArtifacts.gaps).
    arm_inv_checked = 0
    arm_inv_clean = 0
    arm_inv_total = 0
    arm_inv_by_id: dict[str, int] = {}
    # P1-2: track checker errors separately so the arm-level gate can require
    # n_checker_errors == 0 for a true "clean" verdict. A checker exception
    # means the game was NOT successfully audited, even if n_violations == 0.
    arm_inv_checker_errors = 0
    arm_inv_checker_error_games: list[str] = []
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
                    seat_roles=seat_roles, prompt_version=arm.prompt_version,
                    scaffold_provider_factory=(
                        scaffold_factory_builder(arm, api_key)
                        if requires_scaffold else None),
                )
                gl = out_dir / "game-log.json"
                rec["status"] = "completed" if gl.exists() else "failed"
                # C3-4: run invariants check on completed games. check_run's
                # docstring says "never raises", but we wrap defensively so a
                # checker bug cannot abort the arm.
                if rec["status"] == "completed":
                    try:
                        vs = _check_run(out_dir)
                        hard = [v for v in vs if v.severity == "error"]
                        rec["invariants"] = {
                            "violations": [f"{v.id}: {v.detail}" for v in hard],
                            "n_violations": len(hard),
                            "n_artifact_gaps": sum(
                                1 for v in vs if v.severity == "artifact_gap"),
                        }
                        arm_inv_checked += 1
                        arm_inv_total += len(hard)
                        if not hard:
                            arm_inv_clean += 1
                        for v in hard:
                            arm_inv_by_id[v.id] = arm_inv_by_id.get(v.id, 0) + 1
                    except Exception as e:   # defensive: checker must not abort arm
                        # P1-2: count checker errors separately so the arm-level
                        # gate can require n_checker_errors == 0 for a true
                        # "clean" verdict. This game was NOT successfully audited.
                        arm_inv_checker_errors += 1
                        arm_inv_checker_error_games.append(gid)
                        rec["invariants"] = {
                            "invariants_error": f"{type(e).__name__}: {e}",
                            "violations": [], "n_violations": 0, "n_artifact_gaps": 0,
                        }
                break
            except PermissionError:   # Windows Defender transient lock on atomic rename
                time.sleep(1.5); rec["status"] = "perm_retry"; continue
            except Exception as e:
                rec["status"] = "exception"; rec["error"] = f"{type(e).__name__}: {e}"
                traceback.print_exc(); break
        # P3-3: non-completed games get explicit null invariants so the index
        # schema is uniform (every row has the field). This runs AFTER the
        # retry loop so it applies to all failure modes (exception, failed, etc).
        if rec["status"] != "completed":
            rec["invariants"] = None
        rec["secs"] = round(time.time() - t0, 1)
        index_lines.append(rec)
        (arm_dir / "_index.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in index_lines), encoding="utf-8")

    run_dirs = [arm_dir / f"{arm.label}_{i:03d}" for i in range(arm.n_games)]
    metrics = aggregate(run_dirs)
    result = {"arm": arm.label, "prompt_version": arm.prompt_version,
              "n_games": arm.n_games, "metrics": metrics,
              # C3-4: machine-gate the "0 violations" claim. `n_games_clean`
              # is the count of completed games with zero severity=="error"
              # violations; `violations_by_id` buckets the hard failures so
              # a regression in (say) I4b is instantly visible in the rollup.
              # P1-2: `n_checker_errors` counts games where check_run itself
              # raised — these are NOT audited, so the gate should require
              # n_checker_errors == 0 for a true "clean" verdict.
              "validity": {
                  "invariants": {
                      "n_games_checked": arm_inv_checked,
                      "n_games_clean": arm_inv_clean,
                      "n_violations": arm_inv_total,
                      "violations_by_id": dict(arm_inv_by_id),
                      "n_checker_errors": arm_inv_checker_errors,
                      "checker_error_games": arm_inv_checker_error_games,
                  },
              }}
    (arm_dir / "_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result

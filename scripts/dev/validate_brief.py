from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

DEFAULT_COMMANDS: list[tuple[str, list[str]]] = [
    ("validate_game_log", [sys.executable, "-m", "werewolf_eval.validate_game_log", "docs/gold-game/g001-game-log.json"]),
    ("validate_decision_log", [sys.executable, "-m", "werewolf_eval.validate_decision_log", "docs/gold-game/g001-decision-log.json", "docs/gold-game/g001-game-log.json"]),
    ("validate_consensus_log", [sys.executable, "-m", "werewolf_eval.validate_consensus_log", "docs/gold-game/g001-consensus-log.json", "docs/gold-game/g001-game-log.json"]),
    ("unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]),
]


def _short_text(stdout: str, stderr: str, max_lines: int = 40) -> str:
    combined = (stdout + "\n" + stderr).strip().splitlines()
    return "\n".join(combined[-max_lines:]) + ("\n" if combined else "")


def summarize_completed_process(
    *,
    name: str,
    command: str,
    returncode: int,
    stdout: str,
    stderr: str,
    log_dir: Path,
) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    full_log = log_dir / f"{name}.log"
    short_log = log_dir / f"{name}.short.log"
    full_log.write_text(stdout + stderr, encoding="utf-8")
    short_log.write_text(_short_text(stdout, stderr), encoding="utf-8")
    ok = returncode == 0
    return {
        "name": name,
        "command": command,
        "ok": ok,
        "exit_code": returncode,
        "short_log": str(short_log),
        "full_log": str(full_log),
        "next_read": None if ok else str(short_log),
    }


def run_validation(log_dir: Path) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    for name, argv in DEFAULT_COMMANDS:
        completed = subprocess.run(argv, text=True, capture_output=True, env=env)
        command = "PYTHONPATH=src " + " ".join(argv)
        commands.append(
            summarize_completed_process(
                name=name,
                command=command,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                log_dir=log_dir,
            )
        )
    ok = all(item["ok"] for item in commands)
    next_read = [item["next_read"] for item in commands if item["next_read"]]
    return {"ok": ok, "commands": commands, "next_read": next_read}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Werewolf-agent validation and print a compact JSON summary.")
    parser.add_argument("--log-dir", type=Path, default=Path(".logs/validate/latest"))
    args = parser.parse_args()

    summary = run_validation(args.log_dir)
    args.log_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.log_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

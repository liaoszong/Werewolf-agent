"""Gated MANUAL real-DeepSeek smoke for G3-1 (NOT a default test/CI gate).

Runs ONE live consensus game through the real ``DeepSeekProvider`` and reports a
**text-free** PASS/FAIL: launcher exit 0, runtime spine + artifact bundle present,
``provider-trace.json`` shows >=1 real response with
``source_label="[DeepSeek API output]"``, and no secret marker appears in any
output file.

Boundaries (see the design spec section 7):
* Refuses to run unless ``RUN_DEEPSEEK_LIVE_SMOKE=1``; only then is the key read.
* Reads ``DEEPSEEK_API_KEY`` (override via ``--api-key-env``) once, inside ``main``.
* Never prints the key, the ``Authorization`` header, the raw request, or model text.
* Does NOT assert ``live_api=used`` — that marker is the server wrapper's; a
  launcher-direct smoke bypasses it.

Manual run:
    RUN_DEEPSEEK_LIVE_SMOKE=1 DEEPSEEK_API_KEY=... python scripts/dev/run_deepseek_live_smoke.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Allow standalone execution (python scripts/dev/run_deepseek_live_smoke.py).
_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from werewolf_eval.deepseek_launcher import build_deepseek_launcher  # noqa: E402

DEEPSEEK_SOURCE_LABEL = "[DeepSeek API output]"
_SECRET_MARKERS = ("Authorization", "Bearer ", "api_key", "DEEPSEEK_API_KEY", "sk-")
_SPINE_FILES = ("events.jsonl", "prompt-manifest.json")
_BUNDLE_FILES = (
    "game-log.json", "decision-log.json", "consensus-log.json",
    "provider-trace.json", "failure-audit.json",
)


def _scan_for_secret_markers(run_dir: Path) -> bool:
    """Return True when NO secret marker appears in any output file."""
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(marker in text for marker in _SECRET_MARKERS):
            return False
    return True


def _manifest_model_honest(run_dir: Path, expected_model: str) -> bool:
    """Return True iff prompt-manifest.json records the REAL model for every
    agent (== ``expected_model``, never the legacy ``"unknown"``).  Text-free:
    compares only the configured model string, never raw model output (G3-3)."""
    path = run_dir / "prompt-manifest.json"
    if not path.exists():
        return False
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    agents = manifest.get("agents")
    if not isinstance(agents, list) or not agents:
        return False
    return all(
        isinstance(a, dict) and a.get("model") == expected_model for a in agents
    )


def run_live_smoke(
    *,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    max_requests: int = 32,
    max_tokens: int = 256,
) -> dict:
    """Run one real live game and return a text-free structural result dict.

    No raw model output, no key, no header is included in the result."""
    launcher = build_deepseek_launcher(
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_tokens=max_tokens,
        max_requests=max_requests,
    )
    with TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        exit_code = launcher("g3_live_smoke", run_dir)

        spine_ok = all((run_dir / name).exists() for name in _SPINE_FILES)
        snapshots_ok = (run_dir / "snapshots").is_dir() and any(
            (run_dir / "snapshots").glob("*.json")
        )
        bundle_ok = all((run_dir / name).exists() for name in _BUNDLE_FILES)

        real_responses = 0
        trace_path = run_dir / "provider-trace.json"
        if trace_path.exists():
            try:
                trace = json.loads(trace_path.read_text(encoding="utf-8"))
                real_responses = sum(
                    1 for r in trace.get("responses", [])
                    if r.get("source_label") == DEEPSEEK_SOURCE_LABEL
                )
            except (OSError, json.JSONDecodeError):
                real_responses = 0

        no_secret = _scan_for_secret_markers(run_dir)
        # G3-3: the manifest must record the real model, not the legacy "unknown".
        manifest_model_ok = _manifest_model_honest(run_dir, model)

    checks = {
        "exit_zero": exit_code == 0,
        "spine_present": spine_ok and snapshots_ok,
        "bundle_present": bundle_ok,
        "real_response_present": real_responses >= 1,
        "no_secret_markers": no_secret,
        "manifest_model_honest": manifest_model_ok,
    }
    return {
        "passed": all(checks.values()),
        "exit_code": exit_code,
        "real_response_count": real_responses,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Gated manual DeepSeek live smoke.")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--max-requests", type=int, default=32)
    args = parser.parse_args()

    if os.environ.get("RUN_DEEPSEEK_LIVE_SMOKE") != "1":
        print("smoke=skipped reason=set_RUN_DEEPSEEK_LIVE_SMOKE=1_to_run")
        return 0

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        print(f"smoke=error reason=missing_{args.api_key_env}")
        return 2

    result = run_live_smoke(
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
        max_requests=args.max_requests,
    )
    print(f"smoke={'PASS' if result['passed'] else 'FAIL'}")
    print(f"exit_code={result['exit_code']}")
    print(f"real_response_count={result['real_response_count']}")
    for name, ok in result["checks"].items():
        print(f"check_{name}={ok}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

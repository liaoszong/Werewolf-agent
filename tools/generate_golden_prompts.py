"""Regenerate tests/golden_prompts/<PROMPT_VERSION>/ from the canonical sample set.

Run from repo root:  python tools/generate_golden_prompts.py
Prints the sha256 fingerprint map for the ledger's golden_prompt_hashes field.
Writes bytes directly (no newline translation) — .gitattributes pins LF.
The hash map pastes into docs/generated-games/prompt-version-ledger.json
(golden_prompt_hashes.after). Regenerates BOTH prompt_v1 and prompt_v2 dirs;
old-version dirs are intentionally retained as archived reference anchors.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.prompt_goldens import canonical_prompt_samples, canonical_prompt_samples_v2, canonical_prompt_samples_v3
from werewolf_eval.prompt_version import PROMPT_VERSION


def _write_dir(label: str, samples: list[tuple[str, str]]) -> dict[str, str]:
    out_dir = ROOT / "tests" / "golden_prompts" / label
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for name, text in samples:
        data = text.encode("utf-8")
        (out_dir / f"{name}.txt").write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    return hashes


def main() -> None:
    all_hashes: dict[str, dict[str, str]] = {}
    all_hashes[PROMPT_VERSION] = _write_dir(PROMPT_VERSION, canonical_prompt_samples())
    all_hashes["prompt_v2"] = _write_dir("prompt_v2", canonical_prompt_samples_v2())
    all_hashes["prompt_v3"] = _write_dir("prompt_v3", canonical_prompt_samples_v3())
    print(json.dumps(all_hashes, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

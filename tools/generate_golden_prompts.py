"""Regenerate tests/golden_prompts/<PROMPT_VERSION>/ from the canonical sample set.

Run from repo root:  python tools/generate_golden_prompts.py
Prints the sha256 fingerprint map for the ledger's golden_prompt_hashes field.
Writes bytes directly (no newline translation) — .gitattributes pins LF.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.prompt_goldens import canonical_prompt_samples
from werewolf_eval.prompt_version import PROMPT_VERSION


def main() -> None:
    out_dir = ROOT / "tests" / "golden_prompts" / PROMPT_VERSION
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for name, text in canonical_prompt_samples():
        data = text.encode("utf-8")
        (out_dir / f"{name}.txt").write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    print(json.dumps({PROMPT_VERSION: hashes}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

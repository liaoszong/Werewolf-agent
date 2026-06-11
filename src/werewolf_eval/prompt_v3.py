"""prompt_v3 (SYS-B4 Claim Ledger + Vote Scaffold): pure functions for the scribe
extraction artifact and its injection texts. NO engine / llm_providers import
(the engine and provider layer import US). Spec:
docs/superpowers/specs/2026-06-11-sys-b4-claim-ledger-vote-scaffold-design.md.
Hard constraint (spec §0): input-side scaffold only; the action strict-JSON
contract is untouched — everything here lands in observation_text or the
scribe's OWN scaffold request."""
from __future__ import annotations

import json
from typing import Any

SCRIBE_MAX_OUTPUT_TOKENS = 400

CLAIM_TYPES = ("identity_claim", "check_report", "refutation")
# spec §3: source_quote + uncertain are REQUIRED; confidence optional (unused v1).
_REQUIRED_FIELDS = ("claimant", "claim_type", "source_quote", "uncertain")


def render_scribe_input(rnd: int, speeches: list[tuple[str, str]]) -> str:
    """Scribe user message: THIS round's labeled public speeches, numbered so
    claims can reference their source by index."""
    lines = [f"第 {rnd} 轮白天发言记录(按发言顺序):"]
    for i, (speaker, text) in enumerate(speeches, start=1):
        lines.append(f"{i}. {speaker}: {text}")
    return "\n".join(lines)


def parse_scribe_claims(raw_content: str) -> list[dict[str, Any]] | None:
    """Parse the scribe's JSON. Returns None on malformed response (-> this
    round adds nothing; the cross-round ledger is PRESERVED, spec §3 评审修订②).
    Individually invalid entries are dropped, valid ones kept (extraction, not
    adjudication — a bad entry must not poison the round)."""
    try:
        doc = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("claims"), list):
        return None
    out: list[dict[str, Any]] = []
    for c in doc["claims"]:
        if not isinstance(c, dict):
            continue
        if any(f not in c or c[f] is None for f in _REQUIRED_FIELDS):
            continue
        if c["claim_type"] not in CLAIM_TYPES:
            continue
        out.append({
            "claimant": str(c["claimant"]),
            "claim_type": c["claim_type"],
            "target": c.get("target"),
            "result": c.get("result"),
            "refutes": c.get("refutes"),
            "source": c.get("source"),
            "source_quote": str(c["source_quote"]),
            "uncertain": bool(c["uncertain"]),
        })
    return out

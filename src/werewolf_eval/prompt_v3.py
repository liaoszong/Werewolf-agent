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


_CLAIM_LINE = {
    "identity_claim": lambda c: f"声称自己是 {c.get('result') or '?'}",
    "check_report": lambda c: f"报验 {c.get('target') or '?'} → {c.get('result') or '?'}",
    "refutation": lambda c: f"反驳 {c.get('refutes') or '?'}",
}

VOTE_PROGRAM = (
    "【投票前判断程序】\n"
    "对上面的声称,逐条比较后再决定投票,而不是默认相信或默认怀疑:\n"
    "1. 可验证性:声称内容能否与公开事实(死亡/出局/翻牌/票史)对上?有没有矛盾?\n"
    "2. 对跳关系:若多人声称同一身份,至多一人为真;比较各自报点的具体性与一致性。\n"
    "3. 发言与投票是否一致:声称者过往投票是否符合其声称身份的利益?\n"
    "护栏:不要因为出现对跳就自动否定先声称者;不要因为第一天就声称预言家而自动判定是假冒;"
    "不要默认相信预言家声称——用上面三条比较,选出对你阵营最优的一票。"
)


def render_claim_digest(claims: list[dict[str, Any]]) -> str:
    """【声称账本】 section. Every line carries the verbatim source_quote so an
    extraction error is self-evident (spec §3: 辅助提取,非裁判事实). Empty
    ledger -> "" (sections are omitted entirely, matching the v2 convention)."""
    if not claims:
        return ""
    lines = ["【声称账本】(由系统从公开发言提取,可能不完全,以原文为准)"]
    for c in claims:
        desc = _CLAIM_LINE.get(c["claim_type"], lambda _: c["claim_type"])(c)
        mark = "[不确定]" if c.get("uncertain") else ""
        lines.append(f"- (r{c.get('round')}) {c['claimant']} {desc}{mark}(原文:\"{c['source_quote']}\")")
    return "\n".join(lines)


def render_vote_scaffold(claims: list[dict[str, Any]]) -> str:
    """Vote-request-ONLY injection (spec §4 分级:vote 强 / speech 克制):
    digest + the fixed comparison program. Lands in observation_text — the
    action system prompt / strict-JSON contract is untouched (spec §0)."""
    digest = render_claim_digest(claims)
    if digest:
        return f"{digest}\n{VOTE_PROGRAM}"
    return f"本局到目前为止没有可记录的身份声称。\n{VOTE_PROGRAM}"

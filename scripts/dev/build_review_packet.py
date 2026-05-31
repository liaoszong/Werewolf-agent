#!/usr/bin/env python3
"""Build a bounded Review Packet for Codex A档 review."""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

FORBIDDEN_PATTERNS = [
    "provider",
    "network",
    "env",
    "dependency",
    "live AI",
    "fallback",
    "compatibility",
    "default",
    "silently ignore",
    "optional",
]
FORBIDDEN_RISK_PATTERNS = {"provider", "network", "env", "dependency", "live AI"}
DEPENDENCY_FILES = {
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "poetry.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
}
MAX_PACKET_LINES = 300
MAX_KEY_HUNK_LINES = 120
MAX_FILES_BEFORE_RISK = 8
MAX_CHANGED_LINES_BEFORE_RISK = 500


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def git_diff_name_only(base: str) -> list[str]:
    result = run_git(["diff", "--name-only", base])
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().split("\n") if f]


def git_diff_stat(base: str) -> str:
    return run_git(["diff", "--stat", base]).stdout.strip()


def git_diff_check(base: str) -> str:
    result = run_git(["diff", "--check", base])
    return result.stdout.strip() or "(clean)"


def git_diff_unified(base: str) -> str:
    return run_git(["diff", "--unified=3", base]).stdout


def git_diff_shortstat(base: str) -> str:
    return run_git(["diff", "--shortstat", base]).stdout.strip()


def git_branch_name() -> str:
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def parse_changed_lines(shortstat: str) -> int:
    m = re.search(r"(\d+)\s+insertions?", shortstat)
    insertions = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+deletions?", shortstat)
    deletions = int(m.group(1)) if m else 0
    return insertions + deletions


def check_allowlist(
    changed: list[str], allowlist: list[str]
) -> tuple[str, list[str]]:
    if not allowlist:
        return "MANUAL_REVIEW_REQUIRED", []
    missed = []
    for f in changed:
        if not any(fnmatch.fnmatch(f, pat) for pat in allowlist):
            missed.append(f)
    return ("FAIL", missed) if missed else ("PASS", [])


def scan_forbidden(diff_text: str) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            for pat in FORBIDDEN_PATTERNS:
                if pat.lower() in line.lower():
                    entry = f"{pat}: {line[1:].strip()[:80]}"
                    if entry not in seen:
                        seen.add(entry)
                        hits.append(entry)
    return hits


def dep_manifest_changes(changed: list[str]) -> list[str]:
    return [f for f in changed if Path(f).name in DEPENDENCY_FILES]


def added_imports(diff_text: str) -> list[str]:
    imports: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            stripped = line[1:].strip()
            if re.match(r"^(import\s|from\s+\w+\s+import)", stripped):
                imports.append(stripped)
    return imports


def extract_key_hunks(
    diff_text: str, changed_files: list[str]
) -> tuple[str, bool]:
    blocks = re.split(r"^(?=diff --git )", diff_text, flags=re.MULTILINE)
    blocks = [b.strip() for b in blocks if b.strip()]

    hunks_out: list[str] = []
    total_lines = 0
    truncated = False

    for block in blocks:
        m = re.match(r"diff --git a/(.*?) b/(.*?)$", block, re.MULTILINE)
        if not m:
            continue
        filepath = m.group(1)
        if filepath not in changed_files:
            continue

        hunk_match = re.search(r"(@@ .+? @@.*(?:\n|$))", block)
        if not hunk_match:
            continue

        hunk_start = hunk_match.start()
        hunk_text = block[hunk_start:]

        next_hunk = re.search(r"\n@@ ", hunk_text[len(hunk_match.group()) :])
        if next_hunk:
            hunk_text = hunk_text[: len(hunk_match.group()) + next_hunk.start()]

        hunk_lines = hunk_text.count("\n")
        overhead = 4  # "### filepath\n```diff\n" + "```\n"

        if total_lines + hunk_lines + overhead > MAX_KEY_HUNK_LINES:
            truncated = True
            break

        hunks_out.append(f"### {filepath}\n```diff\n{hunk_text}\n```")
        total_lines += hunk_lines + overhead

    return "\n\n".join(hunks_out), truncated


def detect_risk_triggers(
    changed_files: list[str],
    changed_lines: int,
    packet_too_large: bool,
    forbidden_hits: list[str],
    hunks_truncated: bool,
    allowlist_result: str,
) -> list[str]:
    triggers: list[str] = []

    if len(changed_files) > MAX_FILES_BEFORE_RISK:
        triggers.append(
            f"changed_file_count={len(changed_files)} > {MAX_FILES_BEFORE_RISK}"
        )
    if changed_lines > MAX_CHANGED_LINES_BEFORE_RISK:
        triggers.append(
            f"changed_lines={changed_lines} > {MAX_CHANGED_LINES_BEFORE_RISK}"
        )
    if packet_too_large:
        triggers.append("PACKET_TOO_LARGE=YES")
    if hunks_truncated:
        triggers.append("key_hunks_truncated")
    if allowlist_result != "PASS":
        triggers.append(f"allowlist_check={allowlist_result}")

    for hit in forbidden_hits:
        pat_name = hit.split(":", 1)[0]
        if pat_name in FORBIDDEN_RISK_PATTERNS:
            triggers.append(f"forbidden_pattern_risk={pat_name}")
            break

    for f in changed_files:
        base = Path(f).name
        if "scoring.py" in base:
            triggers.append(f"high_risk_file={f}")
        elif "parser" in base and base.endswith(".py"):
            triggers.append(f"high_risk_file={f}")
        elif "log" in base and base.endswith(".py"):
            triggers.append(f"high_risk_file={f}")
        elif f.startswith("docs/gold-game/"):
            triggers.append(f"high_risk_file={f}")
        elif f.startswith("docs/demo/"):
            triggers.append(f"high_risk_file={f}")
        elif base in DEPENDENCY_FILES:
            triggers.append(f"dependency_manifest={f}")

    return triggers


def run_test_commands(commands: list[str]) -> list[str]:
    summaries: list[str] = []
    for cmd in commands:
        result = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        combined = (result.stdout or "") + (result.stderr or "")
        tail = "\n".join(combined.splitlines()[-10:])
        status = "PASS" if result.returncode == 0 else "FAIL"
        summaries.append(
            f"### `{cmd}`\nExit: {result.returncode} ({status})\n```\n{tail}\n```"
        )
    return summaries


def build_packet(
    base: str,
    branch: str,
    changed_files: list[str],
    diff_stat: str,
    diff_check: str,
    diff_text: str,
    shortstat: str,
    allowlist: list[str],
    test_commands: list[str],
    acceptance_items: list[str],
) -> str:
    sections: list[str] = []

    # Metadata
    sections.append("# Review Packet")
    sections.append("")
    sections.append("## Metadata")
    sections.append(f"- Base: `{base}`")
    sections.append(f"- Branch: `{branch}`")
    sections.append(
        f"- Generated: {datetime.now(timezone.utc).isoformat()}"
    )
    sections.append("")

    # Changed Files
    sections.append("## Changed Files")
    for f in changed_files:
        sections.append(f"- `{f}`")
    if not changed_files:
        sections.append("(no changes)")
    sections.append("")

    # Diff Stat
    sections.append("## Diff Stat")
    sections.append("```")
    sections.append(diff_stat or "(no diff)")
    sections.append("```")
    sections.append("")

    # Diff Check
    sections.append("## Diff Check")
    sections.append("```")
    sections.append(diff_check)
    sections.append("```")
    sections.append("")

    # Allowed Files Check
    allowlist_result, missed = check_allowlist(changed_files, allowlist)
    sections.append("## Allowed Files Check")
    sections.append(f"ALLOWLIST_CHECK = {allowlist_result}")
    if missed:
        for f in missed:
            sections.append(f"- MISSED: `{f}`")
    sections.append("")

    # Forbidden Patterns Check
    forbidden_hits = scan_forbidden(diff_text)
    sections.append("## Forbidden Patterns Check")
    if forbidden_hits:
        sections.append("FORBIDDEN_PATTERN_SCAN = WARN")
        for hit in forbidden_hits:
            sections.append(f"- {hit}")
    else:
        sections.append("FORBIDDEN_PATTERN_SCAN = PASS")
    sections.append("")

    # Dependency / Import Diff
    dep_changes = dep_manifest_changes(changed_files)
    imports = added_imports(diff_text)
    sections.append("## Dependency / Import Diff")
    sections.append("### Dependency manifest changes")
    if dep_changes:
        for f in dep_changes:
            sections.append(f"- `{f}`")
    else:
        sections.append("(none)")
    sections.append("")
    sections.append("### Added imports")
    if imports:
        for imp in imports:
            sections.append(f"- `{imp}`")
    else:
        sections.append("(none)")
    sections.append("")

    # Test Summary
    sections.append("## Test Summary")
    if test_commands:
        summaries = run_test_commands(test_commands)
        for s in summaries:
            sections.append(s)
            sections.append("")
    else:
        sections.append("(no test commands provided)")
        sections.append("")

    # Key Hunks
    sections.append("## Key Hunks")
    hunks_text, hunks_truncated = extract_key_hunks(diff_text, changed_files)
    if hunks_text:
        sections.append(hunks_text)
    else:
        sections.append("(no hunks)")
    if hunks_truncated:
        sections.append("")
        sections.append("**KEY_HUNKS_TRUNCATED = YES**")
    sections.append("")

    # Evidence Map
    sections.append("## Evidence Map")
    sections.append("| Acceptance | Evidence | Status |")
    sections.append("|---|---|---|")
    if acceptance_items:
        for item in acceptance_items:
            sections.append(
                f"| {item} | (manual) | MANUAL_REVIEW_REQUIRED |"
            )
    else:
        sections.append(
            "| (no acceptance items provided) | - | - |"
        )
    sections.append("")

    # Acceptance Checklist
    sections.append("## Acceptance Checklist")
    if acceptance_items:
        for item in acceptance_items:
            sections.append(f"- [ ] {item}")
    else:
        sections.append("(no acceptance items provided)")
    sections.append("")

    # Implementer Risk Notes
    sections.append("## Implementer Risk Notes")
    sections.append("(to be filled by implementer)")
    sections.append("")

    # Pre-compute packet size check
    packet_pre = "\n".join(sections)
    pre_lines = packet_pre.count("\n") + 1
    packet_too_large = pre_lines > MAX_PACKET_LINES

    changed_lines = parse_changed_lines(shortstat)

    triggers = detect_risk_triggers(
        changed_files,
        changed_lines,
        packet_too_large,
        forbidden_hits,
        hunks_truncated,
        allowlist_result,
    )

    # Review Trigger Result
    sections.append("## Review Trigger Result")
    if triggers:
        sections.append("**RISK_TRIGGERS_FIRED**")
        for t in triggers:
            sections.append(f"- {t}")
    else:
        sections.append("(no risk triggers fired)")
    sections.append("")

    sections.append(
        f"PACKET_TOO_LARGE = {'YES' if packet_too_large else 'NO'}"
    )

    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a bounded Review Packet for Codex A档 review."
    )
    parser.add_argument("--base", default="main")
    parser.add_argument(
        "--out", default=".logs/review/latest/review-packet.md"
    )
    parser.add_argument("--allowlist", action="append", default=[])
    parser.add_argument("--test-command", action="append", default=[])
    parser.add_argument("--acceptance", action="append", default=[])
    args = parser.parse_args()

    changed_files = git_diff_name_only(args.base)
    diff_stat = git_diff_stat(args.base)
    diff_check = git_diff_check(args.base)
    diff_text = git_diff_unified(args.base)
    shortstat = git_diff_shortstat(args.base)
    branch = git_branch_name()

    packet = build_packet(
        base=args.base,
        branch=branch,
        changed_files=changed_files,
        diff_stat=diff_stat,
        diff_check=diff_check,
        diff_text=diff_text,
        shortstat=shortstat,
        allowlist=args.allowlist,
        test_commands=args.test_command,
        acceptance_items=args.acceptance,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(packet, encoding="utf-8")

    print(f"wrote {args.out}")
    if "PACKET_TOO_LARGE = YES" in packet:
        print("PACKET_TOO_LARGE = YES")
        print(
            "Suggested action: NEED_DEEP_REVIEW with explicit line ranges"
        )
    else:
        print("PACKET_TOO_LARGE = NO")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

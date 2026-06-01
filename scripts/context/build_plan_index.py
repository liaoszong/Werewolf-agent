from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

TASK_HEADING_RE = re.compile(
    r"^#{2,3}\s+(?:任务|Task)\s+([^：:]+)[：:]\s*(.+?)\s*$",
    re.IGNORECASE,
)
FILE_LINE_RE = re.compile(r"^-\s*(创建|修改|测试|读取)：`([^`]+)`")
COMMAND_FENCE_RE = re.compile(r"^```(?:bash|sh|shell|text)?\s*$")
PATH_RE = re.compile(r"`([^`]+)`")

FILE_BUCKETS = {"创建": "create", "修改": "modify", "测试": "test", "读取": "read"}


def _repo_relative(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _line_ranges(lines: list[str]) -> list[tuple[int, int, str, str]]:
    headings: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines, start=1):
        match = TASK_HEADING_RE.match(line)
        if match:
            headings.append((index, match.group(1).strip(), match.group(2).strip()))
    ranges: list[tuple[int, int, str, str]] = []
    for pos, (start, task_id, title) in enumerate(headings):
        end = headings[pos + 1][0] - 1 if pos + 1 < len(headings) else len(lines)
        ranges.append((start, end, task_id, title))
    return ranges


def _extract_files(section_lines: list[str]) -> dict[str, list[str]]:
    files: dict[str, list[str]] = {"create": [], "modify": [], "test": [], "read": []}
    for line in section_lines:
        match = FILE_LINE_RE.match(line.strip())
        if not match:
            continue
        bucket = FILE_BUCKETS[match.group(1)]
        value = match.group(2).split(":", 1)[0]
        if value not in files[bucket]:
            files[bucket].append(value)
    return files


def _extract_commands(section_lines: list[str]) -> list[str]:
    commands: list[str] = []
    in_fence = False
    current: list[str] = []
    for raw in section_lines:
        line = raw.rstrip("\n")
        if COMMAND_FENCE_RE.match(line.strip()):
            if in_fence:
                command = "\n".join(item for item in current if item.strip())
                if command and (
                    command.startswith("python ")
                    or command.startswith("PYTHONPATH=")
                    or command.startswith("node ")
                    or command.startswith("git ")
                ):
                    commands.append(command)
                current = []
            in_fence = not in_fence
            continue
        if in_fence:
            current.append(line)
    return commands


def _extract_acceptance(section_lines: list[str]) -> list[str]:
    acceptance: list[str] = []
    capture = False
    for raw in section_lines:
        line = raw.rstrip()
        if line.lower().startswith("acceptance") or "预期" in line or "Expected result" in line:
            capture = True
            continue
        if capture and line.startswith("- "):
            acceptance.append(line[2:].strip())
        elif capture and line.startswith("### "):
            capture = False
    return acceptance


def _extract_path_refs(section_lines: list[str]) -> list[str]:
    refs: list[str] = []
    for line in section_lines:
        for value in PATH_RE.findall(line):
            if "/" in value or value.endswith(".md") or value.endswith(".py") or value.endswith(".json"):
                clean = value.split(":", 1)[0]
                if clean not in refs:
                    refs.append(clean)
    return refs


def build_plan_index(plan_path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path.cwd()
    text = plan_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tasks = []
    for start, end, task_id, title in _line_ranges(lines):
        section = lines[start - 1 : end]
        tasks.append(
            {
                "id": task_id,
                "title": title,
                "line_start": start,
                "line_end": end,
                "files": _extract_files(section),
                "commands": _extract_commands(section),
                "acceptance": _extract_acceptance(section),
                "path_refs": _extract_path_refs(section),
            }
        )
    plan_id = plan_path.stem
    return {"plan_id": plan_id, "source_path": _repo_relative(plan_path, root), "task_count": len(tasks), "tasks": tasks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic JSON index for a Werewolf-agent implementation plan.")
    parser.add_argument("plan_path", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    index = build_plan_index(args.plan_path)
    out = args.out or Path("docs/generated-context") / f"{index['plan_id']}.index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.as_posix()} tasks={index['task_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _find_task(index: dict[str, Any], selector: str) -> dict[str, Any]:
    for task in index.get("tasks", []):
        if task.get("id") == selector or task.get("title") == selector:
            return task
    available = ", ".join(f"{task.get('id')}:{task.get('title')}" for task in index.get("tasks", []))
    raise SystemExit(f"task selector not found: {selector}; available={available}")


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- `{item}`" for item in items] if items else ["- none"]


def build_task_context(index: dict[str, Any], task_selector: str, out_path: Path) -> str:
    task = _find_task(index, task_selector)
    files = task.get("files", {})
    lines: list[str] = [
        "# Current Task Context",
        "",
        f"Plan: `{index['plan_id']}`",
        f"Source: `{index['source_path']}`",
        f"Task: `{task['id']}` — {task['title']}",
        f"Original plan lines: {task['line_start']}-{task['line_end']}",
        "",
        "## Files",
        "",
        "### Create",
        *_bullet_lines(files.get("create", [])),
        "",
        "### Modify",
        *_bullet_lines(files.get("modify", [])),
        "",
        "### Test",
        *_bullet_lines(files.get("test", [])),
        "",
        "### Read",
        *_bullet_lines(files.get("read", [])),
        "",
        "## Commands",
        "",
    ]
    commands = task.get("commands", [])
    if commands:
        for command in commands:
            lines.extend(["```bash", command, "```", ""])
    else:
        lines.extend(["- none", ""])
    lines.extend(["## Acceptance Hints", ""])
    for item in task.get("acceptance", []) or ["Use the task-specific expected results in the source plan line range."]:
        lines.append(f"- {item}")
    lines.extend(["", "## Path References", ""])
    lines.extend(_bullet_lines(task.get("path_refs", [])))
    lines.append("")
    text = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Build docs/generated-context/current-task.ctx.md from a plan index.")
    parser.add_argument("index_path", type=Path)
    parser.add_argument("task_selector")
    parser.add_argument("--out", type=Path, default=Path("docs/generated-context/current-task.ctx.md"))
    args = parser.parse_args()

    index = json.loads(args.index_path.read_text(encoding="utf-8"))
    build_task_context(index=index, task_selector=args.task_selector, out_path=args.out)
    print(f"wrote {args.out.as_posix()} task={args.task_selector}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

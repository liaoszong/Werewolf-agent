# S4.x Context Budget Hardening Implementation Plan

> **For agentic workers:** 步骤使用复选框（`- [ ]`）语法进行跟踪。

**Goal:** Add a deterministic context-budget layer that prevents agents from repeatedly reading long plan files and full validation logs during Werewolf-agent implementation work.

**Architecture:** This is workflow infrastructure, not game-domain feature work. The implementation adds two deterministic plan-context scripts, one validation-summary wrapper, tests for the scripts, and a strict AGENTS.md Context Budget Gate so local agents must use the compressed entrypoints before opening long plans or full logs.

**Tech Stack:** Python standard library only (`argparse`, `json`, `os`, `pathlib`, `re`, `subprocess`, `tempfile`, `unittest`), Markdown, existing repository validation commands, existing tree refresh hook `node .codex/hooks/tree.mjs --force`.

---

## Context

S4 implementation exposed a recurring token-cost failure mode:

- Long implementation plans such as `docs/harness/plans/2026-05-30--s4-consensus-log-runtime-input-plan.md` are read repeatedly across implementation, review, and fix loops.
- The same task sections, fixture blocks, and validator commands are re-located mechanically.
- Validation loops print long output while agents usually only need pass/fail, failing command, short reason, and a log pointer.
- Source-code search tools help code exploration, but they do not solve Markdown plan re-reading or validation-log flooding.

This plan implements only the P0 deterministic compression layer. Semble, Repomix, CodeGraph, and codebase-memory MCP are outside this task.

## Research PR Decision

No Research PR is needed.

Reasoning:

- The problem is already observed in S4.
- The boundary is clear and implementation-local.
- The task is a single workflow-infrastructure unit.
- It does not require deciding game-domain scoring, AI behavior, or runtime gameplay semantics.

## Global Forbidden Scope

Do not implement any of the following in this PR:

- No Werewolf game-domain behavior changes.
- No changes to parser, scorer, attribution, render demo, gold fixtures, or runtime CLI behavior except the new validation wrapper.
- No Semble installation or `.sembleignore`.
- No Repomix workflow, generated repo packs, or token-audit reports.
- No CodeGraph or codebase-memory MCP integration.
- No dependency additions.
- No network calls.
- No model calls.
- No generated `docs/generated-context/current-task.ctx.md` committed as a stable source file.
- No validation full logs committed.

## Files Overview

Implementation PR should create or modify exactly these files:

- Create: `scripts/context/build_plan_index.py`
  - Deterministically parses `docs/harness/plans/*.md` into a compact JSON index with plan metadata, task sections, file references, validation commands, acceptance hints, and line ranges.

- Create: `scripts/context/build_task_context.py`
  - Uses the index plus a task selector to generate `docs/generated-context/current-task.ctx.md` as the minimal active-task context.

- Create: `scripts/dev/validate_brief.py`
  - Runs the repository validation chain, writes full logs to `.logs/validate/latest/`, writes `.logs/validate/latest/summary.json`, and prints only the summary JSON.

- Create: `tests/test_context_budget.py`
  - Tests the plan index builder, task context builder, validation summary data shape, and AGENTS / `.gitignore` contracts.

- Modify: `AGENTS.md`
  - Adds a strict Context Budget Gate requiring the generated context and validation summary workflow.

- Modify: `.gitignore`
  - Ensures generated context and validation logs are not accidentally committed while keeping optional README files trackable.

- Modify: `.oh-my-harness/tree.md`
  - Refresh after adding script and test files by running `node .codex/hooks/tree.mjs --force`.

No other files should be modified.

---

### 任务 1：Add plan index builder

**文件：**
- 创建：`scripts/context/build_plan_index.py`
- 创建：`tests/test_context_budget.py`
- 测试：`tests/test_context_budget.py`

- [ ] **步骤 1：创建 failing test skeleton**

Create `tests/test_context_budget.py` with this content. `ROOT` is defined in the initial skeleton so later appended tests can read repository files without `NameError`.

```python
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


MINI_PLAN = """# S4.x Example Implementation Plan

> **For agentic workers:** steps use checkboxes.

**Goal:** Example goal.

**Architecture:** Example architecture.

**Tech Stack:** Python standard library.

---

## Global Forbidden Scope

- No game-domain behavior changes.

### 任务 1：Build context index

**文件：**
- 创建：`scripts/context/build_plan_index.py`
- 修改：`AGENTS.md`
- 测试：`tests/test_context_budget.py`

- [ ] **步骤 1：Run parser**

```bash
python scripts/context/build_plan_index.py docs/harness/plans/2026-05-30--example-plan.md
```

Expected result:

```text
wrote docs/generated-context/2026-05-30--example-plan.index.json tasks=1
```

Acceptance:

- Index contains task id `1`.
- Index contains file reference `scripts/context/build_plan_index.py`.
"""


class PlanIndexBuilderTests(unittest.TestCase):
    def test_build_plan_index_extracts_tasks_files_commands_and_lines(self) -> None:
        from scripts.context.build_plan_index import build_plan_index

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "docs/harness/plans/2026-05-30--example-plan.md"
            plan.parent.mkdir(parents=True)
            plan.write_text(MINI_PLAN, encoding="utf-8")

            index = build_plan_index(plan, repo_root=root)

        self.assertEqual(index["plan_id"], "2026-05-30--example-plan")
        self.assertEqual(index["source_path"], "docs/harness/plans/2026-05-30--example-plan.md")
        self.assertEqual(index["task_count"], 1)
        task = index["tasks"][0]
        self.assertEqual(task["id"], "1")
        self.assertEqual(task["title"], "Build context index")
        self.assertGreaterEqual(task["line_start"], 1)
        self.assertGreaterEqual(task["line_end"], task["line_start"])
        self.assertIn("scripts/context/build_plan_index.py", task["files"]["create"])
        self.assertIn("AGENTS.md", task["files"]["modify"])
        self.assertIn("tests/test_context_budget.py", task["files"]["test"])
        self.assertIn(
            "python scripts/context/build_plan_index.py docs/harness/plans/2026-05-30--example-plan.md",
            task["commands"],
        )
        self.assertTrue(any("task id `1`" in item for item in task["acceptance"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **步骤 2：运行测试确认失败**

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget.PlanIndexBuilderTests -v
```

预期：失败，显示 `ModuleNotFoundError: No module named 'scripts.context.build_plan_index'`，因为脚本尚未创建。

- [ ] **步骤 3：创建 deterministic index builder**

Create `scripts/context/build_plan_index.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

TASK_HEADING_RE = re.compile(r"^###\s+任务\s+([^：:]+)[：:]\s*(.+?)\s*$")
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
    plan_id = plan_path.stem.removesuffix("-plan")
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
```

- [ ] **步骤 4：运行 index builder 测试确认通过**

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget.PlanIndexBuilderTests -v
```

预期：通过，输出包含：

```text
Ran 1 test
OK
```

- [ ] **步骤 5：提交 checkpoint**

```bash
git add scripts/context/build_plan_index.py tests/test_context_budget.py
git commit -m "chore: add plan index builder"
```

预期：提交成功，包含 `scripts/context/build_plan_index.py` 和 `tests/test_context_budget.py`。

---

### 任务 2：Add active task context builder

**文件：**
- 创建：`scripts/context/build_task_context.py`
- 修改：`tests/test_context_budget.py`
- 测试：`tests/test_context_budget.py`

- [ ] **步骤 1：追加 task context failing tests**

Insert this class before the existing `if __name__ == "__main__"` block in `tests/test_context_budget.py`:

```python
class TaskContextBuilderTests(unittest.TestCase):
    def test_build_task_context_writes_minimal_markdown_for_selected_task(self) -> None:
        from scripts.context.build_plan_index import build_plan_index
        from scripts.context.build_task_context import build_task_context

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "docs/harness/plans/2026-05-30--example-plan.md"
            plan.parent.mkdir(parents=True)
            plan.write_text(MINI_PLAN, encoding="utf-8")
            index = build_plan_index(plan, repo_root=root)
            out = root / "docs/generated-context/current-task.ctx.md"

            text = build_task_context(index=index, task_selector="1", out_path=out)
            written = out.read_text(encoding="utf-8")

        self.assertEqual(text, written)
        self.assertIn("# Current Task Context", text)
        self.assertIn("Plan: `2026-05-30--example-plan`", text)
        self.assertIn("Task: `1` — Build context index", text)
        self.assertIn("Original plan lines:", text)
        self.assertIn("scripts/context/build_plan_index.py", text)
        self.assertIn("python scripts/context/build_plan_index.py", text)
```

- [ ] **步骤 2：运行新增测试确认失败**

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget.TaskContextBuilderTests -v
```

预期：失败，显示 `ModuleNotFoundError: No module named 'scripts.context.build_task_context'`，因为脚本尚未创建。

- [ ] **步骤 3：创建 task context builder**

Create `scripts/context/build_task_context.py`:

```python
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
```

- [ ] **步骤 4：运行 task context 测试确认通过**

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget.TaskContextBuilderTests -v
```

预期：通过，输出包含：

```text
Ran 1 test
OK
```

- [ ] **步骤 5：提交 checkpoint**

```bash
git add scripts/context/build_task_context.py tests/test_context_budget.py
git commit -m "chore: add task context builder"
```

预期：提交成功，包含 `scripts/context/build_task_context.py` 和更新后的 `tests/test_context_budget.py`。

---

### 任务 3：Add validation brief wrapper

**文件：**
- 创建：`scripts/dev/validate_brief.py`
- 修改：`tests/test_context_budget.py`
- 测试：`tests/test_context_budget.py`

- [ ] **步骤 1：追加 validation summary failing tests**

Insert this class before the existing `if __name__ == "__main__"` block in `tests/test_context_budget.py`. The `short_log.read_text()` and `full_log.read_text()` assertions stay inside the `TemporaryDirectory` lifetime.

```python
class ValidationBriefTests(unittest.TestCase):
    def test_summarize_completed_process_records_logs_and_next_read(self) -> None:
        from scripts.dev.validate_brief import summarize_completed_process

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            result = summarize_completed_process(
                name="unit_tests",
                command="python -m unittest discover",
                returncode=1,
                stdout="line one\nline two\nline three\n",
                stderr="failure detail\n",
                log_dir=log_dir,
            )

            short_log = log_dir / "unit_tests.short.log"
            full_log = log_dir / "unit_tests.log"
            self.assertFalse(result["ok"])
            self.assertEqual(result["name"], "unit_tests")
            self.assertEqual(result["exit_code"], 1)
            self.assertEqual(result["short_log"], str(short_log))
            self.assertEqual(result["full_log"], str(full_log))
            self.assertEqual(result["next_read"], str(short_log))
            self.assertIn("line three", short_log.read_text(encoding="utf-8"))
            self.assertIn("failure detail", full_log.read_text(encoding="utf-8"))
```

- [ ] **步骤 2：运行新增测试确认失败**

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget.ValidationBriefTests -v
```

预期：失败，显示 `ModuleNotFoundError: No module named 'scripts.dev.validate_brief'`，因为脚本尚未创建。

- [ ] **步骤 3：创建 validation brief wrapper**

Create `scripts/dev/validate_brief.py`:

```python
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
```

- [ ] **步骤 4：运行 validation summary 测试确认通过**

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget.ValidationBriefTests -v
```

预期：通过，输出包含：

```text
Ran 1 test
OK
```

- [ ] **步骤 5：运行完整 brief validation smoke check**

```bash
PYTHONPATH=. python scripts/dev/validate_brief.py
```

预期：当前 main 的 validators 全部可用时，输出 JSON 中包含：

```json
{
  "ok": true,
  "commands": [
```

并生成：

```text
.logs/validate/latest/summary.json
.logs/validate/latest/validate_game_log.log
.logs/validate/latest/validate_decision_log.log
.logs/validate/latest/validate_consensus_log.log
.logs/validate/latest/unit_tests.log
```

- [ ] **步骤 6：提交 checkpoint**

```bash
git add scripts/dev/validate_brief.py tests/test_context_budget.py
git commit -m "chore: add validation brief wrapper"
```

预期：提交成功，包含 `scripts/dev/validate_brief.py` 和更新后的 `tests/test_context_budget.py`。

---

### 任务 4：Add Context Budget Gate and ignore generated artifacts

**文件：**
- 修改：`AGENTS.md`
- 修改：`.gitignore`
- 修改：`tests/test_context_budget.py`
- 测试：`tests/test_context_budget.py`

- [ ] **步骤 1：追加 AGENTS / .gitignore contract tests**

Insert this class before the existing `if __name__ == "__main__"` block in `tests/test_context_budget.py`:

```python
class ContextBudgetGateDocsTests(unittest.TestCase):
    def test_agents_documents_context_budget_gate(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        required = [
            "Context Budget Gate",
            "Do not read long plan files in full",
            "docs/generated-context/current-task.ctx.md",
            "scripts/context/build_plan_index.py",
            "scripts/context/build_task_context.py",
            "scripts/dev/validate_brief.py",
            ".logs/validate/latest/summary.json",
            "Do not use Repomix as the default context entry",
            "Do not introduce Semble, CodeGraph, or codebase-memory MCP unless a later plan explicitly allows it",
        ]
        for item in required:
            self.assertIn(item, text)

    def test_gitignore_excludes_generated_context_and_logs(self) -> None:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        required = [
            "docs/generated-context/*.index.json",
            "docs/generated-context/current-task.ctx.md",
            ".logs/validate/",
        ]
        for item in required:
            self.assertIn(item, text)
```

- [ ] **步骤 2：运行 docs contract test 确认失败**

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget.ContextBudgetGateDocsTests -v
```

预期：失败，因为 `AGENTS.md` 和 `.gitignore` 尚未包含 Context Budget Gate 规则和 generated artifact ignore 规则。

- [ ] **步骤 3：修改 AGENTS.md**

Append this section under `## 工作流` after the tree refresh bullets:

```markdown
### Context Budget Gate

- Do not read long plan files in full.
- For plan tasks, start from `docs/generated-context/current-task.ctx.md`.
- If `docs/generated-context/current-task.ctx.md` is missing or stale, generate it with `scripts/context/build_plan_index.py` and `scripts/context/build_task_context.py`.
- Use `docs/generated-context/<plan>.index.json` to locate exact source plan line ranges.
- Only read original plan line ranges when the generated context is insufficient.
- Run validation through `scripts/dev/validate_brief.py` unless a task-specific plan explicitly requires a narrower command first.
- Read `.logs/validate/latest/summary.json` before reading any validation log.
- Read `.logs/validate/latest/*.short.log` only when `summary.json` lists it in `next_read`.
- Do not read full validation logs unless `summary.json` and the short log are insufficient to identify the failure.
- Do not use Repomix as the default context entry.
- Do not introduce Semble, CodeGraph, or codebase-memory MCP unless a later plan explicitly allows it.
```

- [ ] **步骤 4：修改 .gitignore**

Append this section to `.gitignore`:

```gitignore
# Generated context-budget artifacts
docs/generated-context/*.index.json
docs/generated-context/current-task.ctx.md
.logs/validate/
```

- [ ] **步骤 5：运行 docs contract test 确认通过**

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget.ContextBudgetGateDocsTests -v
```

预期：通过，输出包含：

```text
Ran 2 tests
OK
```

- [ ] **步骤 6：提交 checkpoint**

```bash
git add AGENTS.md .gitignore tests/test_context_budget.py
git commit -m "docs: add context budget gate"
```

预期：提交成功，包含 `AGENTS.md`、`.gitignore` 和测试更新。

---

### 任务 5：Final validation and tree refresh

**文件：**
- 修改：`.oh-my-harness/tree.md`
- 测试：`tests/test_context_budget.py`

- [ ] **步骤 1：运行 context-budget tests**

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget -v
```

预期：全部通过，输出包含：

```text
OK
```

- [ ] **步骤 2：运行 repository validation brief**

```bash
PYTHONPATH=. python scripts/dev/validate_brief.py
```

预期：输出 JSON 中 `ok` 为 `true`，并写入：

```text
.logs/validate/latest/summary.json
```

- [ ] **步骤 3：运行完整 unittest discover**

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -p "test_*.py"
```

预期：所有测试通过，输出包含：

```text
OK
```

- [ ] **步骤 4：刷新 tree**

```bash
node .codex/hooks/tree.mjs --force
```

预期：`.oh-my-harness/tree.md` entries 增加，并包含 filename-only / directory-name + filename 形式的新增文件：

```text
build_plan_index.py
build_task_context.py
validate_brief.py
test_context_budget.py
```

- [ ] **步骤 5：检查 diff 清洁度**

```bash
git diff --check
```

预期：无输出。

- [ ] **步骤 6：检查 changed files 范围**

```bash
git diff --name-only main...HEAD
```

预期只包含：

```text
.gitignore
.oh-my-harness/tree.md
AGENTS.md
scripts/context/build_plan_index.py
scripts/context/build_task_context.py
scripts/dev/validate_brief.py
tests/test_context_budget.py
```

- [ ] **步骤 7：提交 final checkpoint**

```bash
git add .oh-my-harness/tree.md
git commit -m "chore: refresh tree for context budget tooling"
```

预期：提交成功，只更新 `.oh-my-harness/tree.md`。

---

## Implementation PR Description Draft

Title:

```text
chore: add context budget hardening tools
```

Body:

```markdown
## Summary

Adds deterministic context-budget tooling for Werewolf-agent implementation work.

Bound Implementation Plan:

- `docs/harness/plans/2026-05-30--s4x-context-budget-hardening-plan.md`

## Scope

- Adds `scripts/context/build_plan_index.py` to index long Implementation Plans into compact JSON with task line ranges, files, commands, acceptance hints, and path refs.
- Adds `scripts/context/build_task_context.py` to generate `docs/generated-context/current-task.ctx.md` for the selected active task.
- Adds `scripts/dev/validate_brief.py` to run validation commands, write full logs to `.logs/validate/latest/`, and print/read compact `summary.json` first.
- Adds `tests/test_context_budget.py` for the context-budget scripts and AGENTS gate.
- Updates `AGENTS.md` with a strict Context Budget Gate.
- Updates `.gitignore` to prevent generated context and validation logs from being committed.
- Refreshes `.oh-my-harness/tree.md`.

## Boundary

- No game-domain behavior changes.
- No parser/scorer/attribution/render demo changes.
- No gold fixture changes.
- No Semble, Repomix, CodeGraph, or codebase-memory MCP integration.
- No dependency additions.

## Validation

```bash
PYTHONPATH=. python -m unittest tests.test_context_budget -v
PYTHONPATH=. python scripts/dev/validate_brief.py
PYTHONPATH=src:. python -m unittest discover -s tests -p "test_*.py"
node .codex/hooks/tree.mjs --force
git diff --check
git diff --name-only main...HEAD
```

Expected final changed files:

```text
.gitignore
.oh-my-harness/tree.md
AGENTS.md
scripts/context/build_plan_index.py
scripts/context/build_task_context.py
scripts/dev/validate_brief.py
tests/test_context_budget.py
```
```

## Self Review Checklist

- Requirement coverage: plan index builder, current-task context builder, validation brief wrapper, AGENTS gate, generated artifact ignore rules, and tree refresh are each covered by a task.
- Scope control: the follow-up implementation touches workflow tooling and docs only; it does not change Werewolf game-domain behavior.
- Testability: every script has a concrete test path and every task lists exact commands with expected results.
- Dependency control: implementation uses only Python standard library and existing repo commands.
- Tooling deferral control: Semble, Repomix default entry, CodeGraph, and codebase-memory MCP are explicitly out of scope for this task.

## Plan-only PR Validation

For the PR that adds this plan file only, run:

```bash
git diff --name-only main...HEAD
```

Expected result:

```text
docs/harness/plans/2026-05-30--s4x-context-budget-hardening-plan.md
```

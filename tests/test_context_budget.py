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


if __name__ == "__main__":
    unittest.main()

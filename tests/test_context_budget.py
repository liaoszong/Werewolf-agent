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

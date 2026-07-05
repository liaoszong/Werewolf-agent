# AGENTS.md

Telegraph style. Root hard policy only. Read scoped `AGENTS.md` before subtree work. Skills own workflows; this file owns routing, default context, and forbidden-scope rules.

回答优先使用中文。

## Development Mode

单人本地直推 `main`。无强制 PR、无隔离工作树流程、无云端 review、无审查包流程。PR 仅作为可选的外部协作机制，不是默认工作流，也不得在任何文档中被写成硬前置。

## Project Route

- Product direction: client-agnostic live AI Werewolf experiment platform.
- **The current phase is NOT hardcoded here** — read it from `docs/PROJECT_MAP.md` (the sole phase authority). Do not assume an earlier G-track module is the front. Qt/QML, observer server, emergent engine and settlement are IN scope.
- Route authorities (only these):
  - `docs/PROJECT_MAP.md` — phase authority (current/next status).
  - `README.md` — project entry + run instructions.
  - `DESIGN.md` — read only when the task touches UI / QML / visual style.
  - `docs/TASKS.md` — compressed task index only, **not** a route authority.

## Skill Routing

Project runbooks live in `.agents/skills/<name>/SKILL.md`. Read the matching one BEFORE acting on:

- Run tests / stale server / kill process on port: `testing-and-process-control`.
- Any model-visible prompt byte change (system prompts, observation renderers): `guarding-prompt-bytes`.
- Live DeepSeek batches / ablation arms / implausible aggregate metrics: `running-live-games`.
- qt_observer build / QML changes / blank window / screenshot verification: `verifying-qt-observer-ui`.

## Default Context

Default reads should be small and current:

1. User request and this file.
2. `MEMORY.md` — cross-session truth entry; use it to route what to verify next, not as a replacement for canonical docs/code.
3. `README.md`.
4. `docs/PROJECT_MAP.md` — current phase and relevant system-view (SYS-xx) rows.
5. `DESIGN.md` when the task touches UI, visual design, QML styling, or page redesign.
6. `docs/TASKS.md` only when checking a specific task's status/outputs.
7. `docs/superpowers/plans/**` / `docs/superpowers/specs/**` for the active or relevant plan/spec.
8. Exact source/test ranges only when needed.

## Context Budget Gate

- Do not read long plan files in full by default. Prefer the focused task
  context when present: `docs/generated-context/current-task.ctx.md`.
- For plan-scoped context, use `scripts/context/build_plan_index.py` and
  `scripts/context/build_task_context.py`; summarize validation with
  `scripts/dev/validate_brief.py` and `.logs/validate/latest/summary.json`.
- Do not use Repomix as the default context entry.
- Do not introduce Semble, CodeGraph, or codebase-memory MCP unless a later plan explicitly allows it.

## Push Discipline (单人直推纪律)

- 改代码前先看 `git status --short`：工作树脏必须先停下汇报，不默默纳入。
- 推前必须本地全量测试绿，除非明确说明为何不需要。
- 推前报告：`git diff --stat` + `git diff --name-only` + allowlist/forbidden-scope 自检。
- `push to main` 后接受现有 CI（`.github/workflows/tests.yml`）事后检测；CI 是事后检测非合并门。

## Work Boundaries

- Do not modify runtime, scoring, provider, validators, generated fixtures, or tests without the task explicitly allowing it.
- Do not treat historical HTML replay, generated JSON, or gold-game artifacts as current product direction.
- Stable architecture decisions live in `docs/adr/**`.

## Validation

For every change, report:

- `git diff --stat`
- `git diff --name-only`
- Allowlist check against the user request / task.
- Forbidden-scope check confirming no unintended `src/**`, `tests/**`, `clients/**`, `docs/secrets/**`, `docs/adr/**`, `docs/generated-games/**`, `docs/gold-game/**`, `docs/demo/**`, `docs/game-scripts/**`, or `.github/workflows/**` changes.
- Relevant tests or a clear reason tests are unnecessary.

Common local test command on PowerShell:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```

Only run log validators when the change touches log contracts or fixtures.

## Tree

- `.oh-my-harness/tree.md` is navigation only.
- New/delete/rename files: run `node .codex/hooks/tree.mjs --force`.
- Do not hand-edit tree unless the hook is unavailable; if unavailable, explain and use equivalent `git ls-files --cached --others --exclude-standard` output.

## Review

- Code review is optional in single-developer local mode; default to self-validation via the Push Discipline above.
- When review is wanted, read `docs/specs/review-guidelines.md` for reviewer judgment rules.

## Maintenance

- Update `MEMORY.md` after important task closeout; do not store secrets there.
- Only stable facts belong here.
- Keep this file short. Link volatile details to canonical docs instead of copying them.

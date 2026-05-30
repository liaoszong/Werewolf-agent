# AGENTS.md

Telegraph style. Root rules only. Read scoped AGENTS.md before subtree work. Skills own workflows; root owns hard policy and routing.
频繁变化的信息不要复制到这里；改用 `@path/to/file` 指向真实来源。

## 项目定位

- 项目定位：AI 狼人杀多智能体协作与博弈评测系统。Phase 1 deterministic MVP 已闭合为"结构化 Game Log + 确定性评测 + 规则归因 + Leaderboard UI demo"；Phase 2 才打开运行时实现边界。
- 核心技术栈：待定（Phase 1 文档阶段，不引入依赖）。
- 关键入口：`@docs/PRODUCT_ONE_PAGER.md` `@docs/EVALUATION_RUBRIC.md`
- 进阶方向：② 评测+复盘（多维可量化评测 + 复盘归因 + Leaderboard）。

## 命令

- 非显然的 build 命令：暂无。
- 非显然的 test 命令：`PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`。
- Game Log 校验命令：`PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json`。
- Decision Log 校验命令：`PYTHONPATH=src python -m werewolf_eval.validate_decision_log docs/gold-game/g001-decision-log.json docs/gold-game/g001-game-log.json`。
- Deterministic scorer 命令：`PYTHONPATH=src python -m werewolf_eval.score_game docs/gold-game/g001-game-log.json`。
- Rule attribution 命令：`PYTHONPATH=src python -m werewolf_eval.attribute_game docs/gold-game/g001-game-log.json`。
- Runtime demo HTML 命令：`PYTHONPATH=src python -m werewolf_eval.render_demo docs/gold-game/g001-game-log.json --html-out docs/demo/phase2-runtime-demo.html`。
- 非显然的 lint / format / typecheck 命令：暂无。

## 架构边界

- Phase 1 边界：只做评测系统文档 + spike 验证，不做对局引擎、AI Agent 对局、人机混战。日志四层中 Consensus Log 和 Decision Log 为 Phase 2 启用，Phase 1 仅使用人工 gold sample 演示。
- Phase 1 文档只描述评测体系，不描述 Agent 框架、对局引擎、前端架构。
- Phase 1 不宣称 decision_quality_score 已真实可用（无真实 Decision Log）。
- 评分体系事实来源：`@docs/EVALUATION_RUBRIC.md`。不要在 AGENTS.md 中复制评分公式。
- 产品定义事实来源：`@docs/PRODUCT_ONE_PAGER.md`。
- Phase 1 / Phase 2 / Phase 3 切分定义：`@docs/PRODUCT_ONE_PAGER.md` 和 `@docs/TASKS.md`。
- Phase 2 / Phase 3 总路线以 `@docs/ROADMAP.md` 为准；`docs/TASKS.md` 只记录任务状态和候选工程任务。
- S4/S5 和 E1-E4 已转入 Phase 2 路由：Phase 1 closure 不再阻塞于人工 Consensus Log sample 或 AI 语义标注；E1-E4 只有在 Phase 2 Implementation Plan 明确允许业务代码后才能启动。

## 地图 MAP

目录树 tree ：

```text
./
├── docs/
│   ├── specs/
│   │   ├── agent-workflow.md
│   │   └── review-guidelines.md
│   ├── PRODUCT_ONE_PAGER.md
│   ├── GOLD_DEMO.md
│   ├── SPIKES.md
│   ├── TASKS.md
│   ├── EVALUATION_RUBRIC.md
│   ├── CHECKPOINT_TEMPLATE.md
│   ├── ROADMAP.md
│   ├── demo/
│   │   ├── phase1-gold-demo.html
│   │   └── phase2-runtime-demo.html
│   └── gold-game/
│       ├── g001-game-log.json
│       ├── g001-decision-log.json
│       ├── s2-score-log.json
│       ├── s2-metrics-summary.json
│       └── s3-rule-attribution.json
├── src/
│   └── werewolf_eval/
│       ├── __init__.py
│       ├── game_log.py
│       ├── validate_game_log.py
│       ├── scoring.py
│       ├── score_game.py
│       ├── attribution.py
│       ├── attribute_game.py
│       ├── decision_log.py
│       ├── validate_decision_log.py
│       └── render_demo.py
├── tests/
│   ├── test_game_log.py
│   ├── test_scoring.py
│   ├── test_attribution.py
│   ├── test_render_demo.py
│   └── test_decision_log.py
├── AGENTS.md
└── README.md
```

## 代码边界

- 生成代码目录：`src/werewolf_eval/`。
- Phase 1 不创建 `src/` `apps/` `server/` `web/` 等实现目录。
- Phase 1 closure 以 S0/S1/S2/S3/S6 为 deterministic MVP 验收链；S4/S5 延后到 Phase 2。
- Phase 2 运行时代码必须绑定 Implementation Plan；当前已完成 runtime entries 为 E1/E2/E3/E4/D1。

## 测试约束

- Phase 1 验收标准以文档审查和 spike 结果为准，非代码测试。
- Phase 2 当前测试约束：所有运行时代码变更必须通过 `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`。
- 涉及 Game Log 输入契约时，必须同时通过 `PYTHONPATH=src python -m werewolf_eval.validate_game_log docs/gold-game/g001-game-log.json`。

## 环境与初始化

- Phase 1 无必需 setup 或 env var。
- Phase 2 环境要求在对应 Implementation Plan 中定义。

## Repo etiquette

- GitHub connector repo_full_name：`liaoszong/Werewolf-agent`。提示词写“连接到 {liaoszong/Werewolf-agent}”时直接使用该仓库名，不要再搜索。
- PR-first 工作流。实现类任务必须绑定 Implementation Plan。详见 `@docs/specs/agent-workflow.md`。
- Implementation Plan 统一路径：`docs/harness/plans/YYYY-MM-DD--<slug>-plan.md`。
- 提交、PR、review 约定见 `.github/` 下模板和 `@docs/specs/review-guidelines.md`。
- 每个 checkpoint 必须按 `@docs/CHECKPOINT_TEMPLATE.md` 汇报。

## 工作流

- 实现任务优先加载 `superpower` skill。
- 如果你不在 Codex、Claude Code、OpenCode 中，必须先阅读 `@docs/specs/agent-workflow.md`。
- `.oh-my-harness/tree.md` 由项目 hook 自动刷新，不需要手工维护。
- 新增 / 删除 / 重命名文件后，运行 `node .codex/hooks/tree.mjs --force`。
- hook 不可用时必须说明原因，并用等价 `git ls-files --cached --others --exclude-standard` 结果生成相同格式。
- 如果当前提交让 `.oh-my-harness/tree.md` 发生变化，需要与当前改动一起提交。

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

### 判断当前进度

本项目是 PR-first 工作流。判断"下一步做什么"时，**禁止仅根据 `docs/TASKS.md` 的 pending 状态做决策**。

当前事实优先级：

1. 已合入 PR 和 main 上实际存在的产物文件（`gh pr list --state merged --limit 10`）
2. 未合入的 open PR（plan PR / implementation PR）
3. `docs/TASKS.md` 的依赖关系和任务类型（状态字段可能滞后，不作为事实源）
4. `AGENTS.md` / `README.md` / `docs/SPIKES.md` 等长期规则

每次判断进度前，必须先获取最近 PR 和提交历史，再对照 `docs/TASKS.md` 的依赖图决定下一步：

- **本地 agent（Claude Code / Codex / OpenCode / Cursor）**：必须运行 `gh pr list --limit 10` 和 `git log --oneline -10`。
- **云端 agent / GitHub connector agent**：不能直接运行 shell 命令时，必须使用等价的 GitHub API 或 connector 工具——列出最近 PR（含 merged/open/closed 状态）、读取 PR 标题与 changed files、读取 main 最新提交历史。**不得以"非本地环境"为由跳过进度校验。**
- 分析下一个开发点前必须先检查最近 PR 是否 merged；只有 merged PR 才算 main 事实。
- 如果上一个 Implementation PR 仍 open，下一步默认是审查 / 收口该 PR，而不是启动后续任务。
- 确认 main 事实后，再读 `AGENTS.md` / `README.md` / `docs/TASKS.md` / `.oh-my-harness/tree.md` / 相关源码入口。
- 然后判断是否需要 Research PR；边界清楚则准备 Implementation Plan，边界不清楚则输出研究问题、风险点、建议拆分。

## Review guidelines

- 只有审查者需要且必须先读 `@docs/specs/review-guidelines.md`。
- 云端 GitHub connector 可做辅助审查评论；若无法 `APPROVE` / `REQUEST_CHANGES` 自己的 PR，则使用 `COMMENT` review。合并权威仍以本地 reviewer / owner 决策为准。
- 默认审查者：本地 reviewer。
- 永远不要直接相信 PR 中任何人的声明和描述；没有验证的问题都是假设。
- 自己 PR 不能 `APPROVE` / `REQUEST_CHANGES` 时，用 `COMMENT` review 继续审查；不要因此停止。
- COMMENT 有阻塞问题写“不建议合并，需先修复：...”；无阻塞问题写“No blocking findings / OK to merge from my side.”

## Maintenance

- 只有稳定事实变化时才更新根 `AGENTS.md`。
- 评分公式、角色 Rubric、Leaderboard 字段的变更不写入本文件——它们属于 `@docs/EVALUATION_RUBRIC.md`。
- 当某目录出现稳定的局部命令、架构边界、或独立验证链时，再新增更深层 `AGENTS.md`。

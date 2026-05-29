# AGENTS.md

Telegraph style. Root rules only. Read scoped AGENTS.md before subtree work. Skills own workflows; root owns hard policy and routing.
频繁变化的信息不要复制到这里；改用 `@path/to/file` 指向真实来源。

## 项目定位

- 项目定位：AI 狼人杀多智能体协作与博弈评测系统。Phase 1 构建"结构化 Game Log + 确定性评测 + 规则归因 + Leaderboard UI demo"。
- 核心技术栈：待定（Phase 1 文档阶段，不引入依赖）。
- 关键入口：`@docs/PRODUCT_ONE_PAGER.md` `@docs/EVALUATION_RUBRIC.md`
- 进阶方向：② 评测+复盘（多维可量化评测 + 复盘归因 + Leaderboard）。

## 命令

- 非显然的 build 命令：暂无（Phase 1 文档阶段）。
- 非显然的 test 命令：暂无。
- 非显然的 lint / format / typecheck 命令：暂无。

## 架构边界

- Phase 1 边界：只做评测系统文档 + spike 验证，不做对局引擎、AI Agent 对局、人机混战。日志四层中 Consensus Log 和 Decision Log 为 Phase 2 启用，Phase 1 仅使用人工 gold sample 演示。
- Phase 1 文档只描述评测体系，不描述 Agent 框架、对局引擎、前端架构。
- Phase 1 不宣称 decision_quality_score 已真实可用（无真实 Decision Log）。
- 评分体系事实来源：`@docs/EVALUATION_RUBRIC.md`。不要在 AGENTS.md 中复制评分公式。
- 产品定义事实来源：`@docs/PRODUCT_ONE_PAGER.md`。
- Phase 1 / Phase 2 / Phase 3 切分定义：`@docs/PRODUCT_ONE_PAGER.md` 和 `@docs/TASKS.md`。

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
│   └── CHECKPOINT_TEMPLATE.md
├── AGENTS.md
└── README.md
```

## 代码边界

- 生成代码目录：暂无（Phase 1 文档阶段）。
- Phase 1 不创建 `src/` `apps/` `server/` `web/` 等实现目录。
- Phase 2 开始前必须通过所有 Phase 1 spike 验收。

## 测试约束

- Phase 1 验收标准以文档审查和 spike 结果为准，非代码测试。
- Phase 2 引入代码后，测试约束见届时更新的 AGENTS.md。

## 环境与初始化

- Phase 1 无必需 setup 或 env var。
- Phase 2 环境要求在对应 Implementation Plan 中定义。

## Repo etiquette

- PR-first 工作流。实现类任务必须绑定 Implementation Plan。详见 `@docs/specs/agent-workflow.md`。
- 提交、PR、review 约定见 `.github/` 下模板和 `@docs/specs/review-guidelines.md`。
- 每个 checkpoint 必须按 `@docs/CHECKPOINT_TEMPLATE.md` 汇报。

## 工作流

- 实现任务优先加载 `$harness` skill。
- 如果你不在 Codex、Claude Code、OpenCode 中，必须先阅读 `@docs/specs/agent-workflow.md`。
- `.oh-my-harness/tree.md` 由项目 hook 自动刷新，不需要手工维护。
- 如果当前提交让 `.oh-my-harness/tree.md` 发生变化，需要与当前改动一起提交。

### 判断当前进度

本项目是 PR-first 工作流。判断"下一步做什么"时，**禁止仅根据 `docs/TASKS.md` 的 pending 状态做决策**。

当前事实优先级：

1. 已合入 PR 和 main 上实际存在的产物文件（`gh pr list --state merged --limit 10`）
2. 未合入的 open PR（plan PR / implementation PR）
3. `docs/TASKS.md` 的依赖关系和任务类型（状态字段可能滞后，不作为事实源）
4. `AGENTS.md` / `README.md` / `docs/SPIKES.md` 等长期规则

每次判断进度前，必须先运行 `gh pr list --limit 10` 和 `git log --oneline -10`，再对照 `docs/TASKS.md` 的依赖图决定下一步。

## Review guidelines

- 只有审查者需要且必须先读 `@docs/specs/review-guidelines.md`。
- 云端审查支持：否（Phase 1 文档阶段，暂未配置云端审查 bot）。
- 默认审查者：本地 reviewer。
- 永远不要直接相信 PR 中任何人的声明和描述；没有验证的问题都是假设。

## Maintenance

- 只有稳定事实变化时才更新根 `AGENTS.md`。
- 评分公式、角色 Rubric、Leaderboard 字段的变更不写入本文件——它们属于 `@docs/EVALUATION_RUBRIC.md`。
- 当某目录出现稳定的局部命令、架构边界、或独立验证链时，再新增更深层 `AGENTS.md`。

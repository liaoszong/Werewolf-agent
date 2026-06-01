# 项目全局健康检查 v2

日期：2026-06-01

范围：项目全局只读审计 + 本报告写入。这不是 G1c 收口、不是仅 G1d 就绪判定，也不是对先前健康检查报告的决议性通过。已有 `docs/harness/reviews/2026-06-01--g1c-project-healthcheck.md` 和 `docs/harness/reviews/2026-06-01--g1c-project-healthcheck-final.md` 仅作为输入证据使用。

硬性边界（已遵守）：

- 未启动 G1d。
- 未设计或实现 provider adapter。
- 未接入真实 provider 或 live model。
- 未读取 `docs/ai-worklog`。
- 未完整读取历史 plan 文件；仅使用 inventory、generated context、indexes 和定向证据。
- 本次审计未修改业务逻辑代码。

检查时的仓库状态说明：审计开始时工作区已 dirty。已有未提交变更包括 `.oh-my-harness/tree.md`、`docs/TASKS.md`、`docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html`、`docs/generated-games/g1c-wolf-consensus-decision-log.json`、`scripts/dev/build_review_packet.py`、`tests/test_render_demo.py`，以及未跟踪的 G1c 健康检查报告。本报告将上述变更视为当前工作区现实，而非本次审计产生的修改。

## 1. 总体结论

| 维度 | 结论 | 证据基础 |
|---|---|---|
| 项目整体健康度 | WARN | 方向和路线一致，但核心溯源合约仍有 P1 缺口。 |
| G1d 闸门 | PASS | G1d 可以作为 provider adapter research / fake-provider contract 启动，但不能启动 G1e 或真实 provider 工作。 |
| 交付就绪度 | WARN | Demo 可支撑评测进度叙事，但不能支撑最终真实 Agent 声明。 |
| 项目萎缩风险 | MEDIUM | 路线保留了 G1d/G1e/L1，但如果不强制执行扩展检查点，当前产物可能固化为精致 mock / 日志校验器终点。 |
| 评测可信度 | WARN | 当前 G1c 产物通过校验且测试通过，但 Game Log 溯源和 Decision/Consensus 跨日志不变量尚未成为通用校验器保证。 |

底线：项目没有明显偏航，也没有塌缩为静态 demo。但它正处于一个关键节点——下一步必须有意识地打开 provider 边界，同时收紧评测信任合约。将当前 mock 管道视为最终产品将是主要的战略性失败模式。

## 2. 项目应成为什么

当前 canonical 文档将目标定义为一个 AI 狼人杀 Agent 评测、复盘和排行榜系统：

```text
真实或重放的狼人杀对局
→ 结构化 Game Log / Decision Log / Consensus Log
→ 可复现的 Score Log / Metrics Summary
→ 确定性归因 + AI 辅助语义标注
→ 按角色分离的记分卡和真实多局 Leaderboard
```

关键产品意图：

- `README.md` 将系统定位为多 Agent 狼人杀协作 / 对局评测，而非日志生成器。
- `docs/PRODUCT_ONE_PAGER.md` 将核心价值定义为按角色分离的、可量化的多 Agent 评测排行榜。
- `docs/ROADMAP.md` 是最清晰的 canonical 路线文档：Phase 2 评测 runtime、Phase 3 G-track 对局路线、Phase 3+ L-track 真实多局 Leaderboard。
- `docs/EVALUATION_RUBRIC.md` 是评分和日志 schema 的事实来源。

这意味着最终目标不是"G1c 日志修复"、不是"mock 对局 HTML"、也不是"一个确定性场景"。当前实现只有在它充当通往 provider-backed 结构化 Agent 动作和多局评测的桥梁时才是健康的。

## 3. 当前现实

已实现的现状：

- Phase 1 确定性 MVP 存在：gold Game Log、确定性 score/metrics、归因、静态 demo。
- Phase 2 评测 runtime 存在：Game Log parser/validator、scorer、归因、runtime demo HTML。
- Decision Log runtime 输入和确定性 D2 评分已实现。
- Consensus Log parser/validator 存在。
- 已保存 S5 语义标注可接入确定性评分；不执行 live AI 标注。
- G1a scripted deterministic fresh-log runner 存在。
- G1b deterministic game engine + mock agent contract 存在。
- G1c wolf consensus + failure recovery 在当前工作区中存在，包括生成的 Game/Decision/Consensus log、failure audit 产物、score/metrics 和 demo。

当前局限：

- 无 live provider 集成。
- 无 provider-backed 单局 smoke。
- 无真实 AI Agent 自主对局。
- 无人机混战 UI。
- 无真实多局 Leaderboard。
- 无通用 failure-audit 校验器。
- 无将 Decision Log team 条目绑定到 Consensus Log ID 的跨日志校验器。
- Game Log parser 接受缺失或伪造的 `source_label`，因此顶层 Game Log 溯源不是校验器不变量。

## 4. 最终目标差距地图

| 最终目标 | 当前状态 | 差距 | 风险 | 建议检查点 |
|---|---|---|---|---|
| 真实/重放狼人杀对局作为评测输入 | Gold、scripted 和确定性 mock 对局存在 | 尚无 provider-backed 对局；mock 可能被误认为终点 | Medium | G1d fake-provider contract，然后 G1e 单局 smoke |
| 结构化 Game / Decision / Consensus log | Parser 和生成产物存在 | Game Log 溯源未校验；Decision/Consensus 联动仅路径测试 | High | 评测信任硬化检查点 |
| 可复现的 Score Log / Metrics Summary | 确定性 scorer 通过，当前 G1c 评分正常 | 评分路径不要求 Consensus Log 或 Failure Audit 可信 | Medium | provider-backed 评分前的跨日志校验 |
| 确定性归因 + 语义标注 | 归因和已保存 S5 label 存在 | Live 语义标注仍超出范围；已保存 label 不是 provider 能力 | Medium | 保持 S5 已保存 label 边界；待 provider 路线稳定后再做 live 标注 |
| 按角色分离的记分卡和真实 Leaderboard | Demo Leaderboard 行存在 | 主要是单局 + mock baseline 行；无多局样本量现实性 | High | L1 之前的扩展检查点 |
| Agent/provider 扩展路径 | ROADMAP 保留 G1d/G1e/L1 | 尚无 fake-provider contract | Medium | G1d research / fake-provider contract |
| 审计/复盘可信度 | 生成产物和校验器存在 | Failure Audit 无校验器；packet 证据陈旧 | High | Failure-audit schema + packet 重新生成 |

## 5. 文档健康度

文档清单基于 `docs/` 下已跟踪文件构建，按指令排除了 `docs/ai-worklog`。

| 类别 | 文件/区域 | 健康度 | 备注 |
|---|---|---|---|
| Canonical 且一致 | `README.md`、`docs/ROADMAP.md`、`docs/TASKS.md`、`docs/EVALUATION_RUBRIC.md`、`docs/PRODUCT_ONE_PAGER.md` | WARN | 方向一致；source-label 分类法和"明确不做"表有陈旧边缘。 |
| 生成式上下文 | `docs/generated-context/current-task.ctx.md` | PASS | 当前上下文显示 G1c 已完成，G1d 为下一候选。 |
| 生成式上下文索引 | `docs/generated-context/*.index.json` | WARN | G1a 和 S5 索引正常；G1b 和 G1c 索引报告 `task_count=0`，因此 context-budget gate 对这些 plan 不可靠。 |
| Review 产物 | `docs/harness/reviews/2026-06-01--g1c-project-healthcheck*.md`、`.logs/review/latest/review-packet.md` | WARN | 先前报告是有用证据，但最新 packet 仍含陈旧 P1 风险备注和手动验收行。 |
| 历史 plan | `docs/harness/plans/*.md` | 仅作历史 | 仅 inventory/index；不要将其改写为当前真相。 |
| Demo 文档/产物 | `docs/demo/*.html`、`docs/generated-games/*.json`、`docs/gold-game/*.json` | WARN | 当前 G1c demo 在 P1 修复后更清晰；旧 demo 保持历史或阶段范围属性。 |
| 研究/语义标注文档 | `docs/prs/*`、`docs/semantic-labeling/*` | PASS/WARN | 有用的路线记录；非 canonical 路线真相。 |
| 架构文档 | 未发现专用 `docs/ARCHITECTURE*` | WARN | `ROADMAP.md`、`TASKS.md` 和代码结构充当事实上的架构文档。目前可用，但对 provider 扩展偏弱。 |

具体文档发现：

- `README.md` 和 `docs/ROADMAP.md` 正确保留了 G1d、G1e 和 L1；项目未被文档描述为完整真实 AI 对局。
- `docs/TASKS.md` 现在写明 G1c 完成、G1d 为下一候选，但其"明确不做"表仍含 Phase 2 时代的条目，如 `对局引擎 | 真正不做（Phase 2） | active`；在 G1b 之后，如果被解读为全局当前真相，此措辞可能产生误导。
- `docs/PRODUCT_ONE_PAGER.md` 的数据标签表缺少当前 runtime 标签，如 `[scripted deterministic output]`、`[deterministic mock agent output]`、`[semantic research output]`，以及评分复合标签如 `[deterministic][decision-log][semantic-labels]`。
- `.logs/review/latest/review-packet.md` 仍陈旧：仍有 `MANUAL_REVIEW_REQUIRED`、`KEY_HUNKS_TRUNCATED`、`PACKET_TOO_LARGE`、旧的 `consensus_id:null` 备注，以及旧的"not real Consensus Log collection"备注，即便当前工作区证据已与此矛盾。
- 历史 plan 未被当作当前真相。这是正确的。

文档健康度矩阵：

| 状态 | 条目 |
|---|---|
| canonical 且一致 | `README.md`、`docs/ROADMAP.md`、`docs/TASKS.md` 中的当前 G1c 状态、`docs/generated-context/current-task.ctx.md` |
| 陈旧但非阻塞 | `docs/TASKS.md` Phase 2 时代"不做"表、`docs/PRODUCT_ONE_PAGER.md` source-label 表 |
| 误导性且阻塞 | 无（对路线方向而言）；最新 review packet 对 packet-first review 有误导性，但不是 canonical 文档 |
| 仅历史，勿改写 | `docs/harness/plans/*.md`、`docs/gold-game/s*-*.md`、`docs/GOLD_DEMO.md`、`docs/SPIKES.md`、`docs/prs/*.md` |
| 未检查 | `docs/ai-worklog`（按明确指令） |

## 6. 架构与模块边界健康度

检查区域：`src/`、`scripts/`、`tests/`、`docs/generated-games`、`docs/demo`。

当前边界：

- `src/werewolf_eval/game_log.py`：Game Log parser/validator。
- `src/werewolf_eval/decision_log.py`：Decision Log parser/validator。
- `src/werewolf_eval/consensus_log.py`：Consensus Log parser/validator。
- `src/werewolf_eval/scoring.py`：确定性评分、metrics、D2/S5 decision scoring。
- `src/werewolf_eval/attribution.py`：确定性规则归因。
- `src/werewolf_eval/render_demo.py`：HTML 上下文和渲染器。
- `src/werewolf_eval/scripted_game.py` / `run_scripted_game.py`：G1a scripted deterministic 产物。
- `src/werewolf_eval/game_engine.py` / `run_mock_game.py`：G1b/G1c deterministic mock engine 产物。
- `scripts/context/*`：context budget index/context 构建器。
- `scripts/dev/*`：validation 和 review-packet 支持。

评估：

- 当前确定性评测器的模块边界基本清晰。
- 对局引擎仍是确定性且窄的；尚未定义 provider adapter 或 live agent 抽象。
- `game_engine.py` 和 `scoring.py` 正在成为中心化大型模块。这本身不是当前正确性阻塞项，但如果 provider 工作直接落在这些模块上，边界将更难推理。
- `render_demo.py` 消费真实管道产物，不硬编码最终评分，但它拥有大量边界消息；demo 文案仍可能偏离产品真相。
- `scripts/context/build_plan_index.py` 依赖正则匹配 `### 任务 ...` 标题。英文标题的 plan（如 G1b/G1c）当前索引到零个任务，因此 context-budget 架构对实际 plan 语料库不可靠。

模块边界风险：

- 缺少专用架构文档，意味着新贡献者必须从 ROADMAP + TASKS + 代码推断系统边界。
- 存在校验器/生成器自证风险：生成产物由本地代码产出并由本地校验器校验，而外部/provider 形状的坏日志尚未被表征。
- 除非 G1d/G1e 强制外部动作合约，否则 Demo 仍可能将产品叙事拉向"HTML 产物即产品"。

## 7. 评测与溯源可信度

当前 G1c 生成产物健康度：

- Game Log：`game_id=g1c_wolf_consensus`，18 events，winner villager。
- Decision Log：11 decisions，source `[deterministic mock agent output]`。
- Consensus Log：2 consensuses，source `[deterministic mock agent output]`。
- Team decision 现已携带 Consensus Log ID：
  - `g1c_wolf_consensus_d001 → g1c_wolf_consensus_consensus_r01`
  - `g1c_wolf_consensus_d008 → g1c_wolf_consensus_consensus_r02`
- 当前有效 G1c failure audit 有零条目，与有效共识路径一致。

失败模式抽查：

| 模式 | 结果 |
|---|---|
| `g1c_split_wolf_vote` | 18 events, 11 decisions, 2 consensus entries, 1 `wolf_consensus_failure`，无修复动作 |
| `g1c_invalid_wolf_action` | 18 events, 11 decisions, 2 consensus entries, 1 `invalid_action`，无效 `p99` 目标未进入有效 decision |
| `g1c_timeout_parse_failure` | 17 events, 10 decisions, 1 consensus entry, `timeout` + `parse_failure`，第 1 夜无 forced-random kill |

信任发现：

- PASS：无效动作、超时和解析失败在测试中被审计，且未变成合法 Decision Log kill 动作。
- PASS：当前 G1c wolf-team decision 可追溯到当前 Consensus Log ID。
- PASS：Consensus Log 校验器拒绝缺失/重复的 werewolf kill event 共识覆盖。
- WARN：Game Log parser/validator 接受缺失或伪造的顶层 `source_label`；溯源存在于生成的 JSON 中但不被校验。
- WARN：Decision Log parser/validator 接受 team-scope `wolf_team` decision 的 `consensus_id = null`；当前 G1c 输出是正确的，但通用输入合约并非如此。
- WARN：评分路径不消费或要求 Consensus Log / Failure Audit。它可以在共识溯源未经跨校验的情况下对 Game Log + Decision Log 进行评分。
- WARN：Failure Audit 无 parser/validator，因此面向 provider 的失败语义尚不可强制执行。
- WARN：Score Log 的 source label 将 mock-agent 溯源压缩为 `[deterministic][decision-log]`，而 demo 另外重新注入 Game Log 溯源。这在今天对展示可用，但作为审计产物偏弱。

评测信任结论：WARN。当前产物对确定性检查点是可信的；在没有更强溯源和跨日志校验器的情况下，系统对 provider 产出的日志尚不够健壮。

## 8. 测试覆盖与盲区

最新测试结果：

- `python -m unittest discover -s tests -p "test_*.py"`：108 tests OK。
- `python -m pytest -q`：失败，`No module named pytest`。

测试覆盖良好之处：

- Game Log parser 基础：必填字段、序列连续性、actor/target/refs。
- Decision Log parser 基础：actor/target/refs/source label/decision type/confidence。
- Consensus Log parser：participants、visibility、proposal/response 结构、final target、重复/缺失共识覆盖、每轮动作限制。
- G1b mock engine 确定性和生成产物溯源。
- G1c split vote / invalid action / timeout / parse failure 行为。
- 评分确定性结果规则、D2 visibility 检查、S5 已保存 label 路径。
- Render demo source labeling（G1a 和当前 G1c 消息）。
- Context-budget 辅助程序在合成 mini plan 上的行为。
- Review packet 生成器在定向单元测试中的行为。

盲区：

1. 没有测试拒绝缺失或伪造的 Game Log `source_label`。
2. 没有校验器/测试拒绝 team Decision Log 条目缺失或未知 `consensus_id`（当提供 Consensus Log 时）。
3. 没有独立的 Failure Audit parser/validator 测试。
4. 没有测试覆盖 provider 形状的畸形动作载荷，因为 provider/fake-provider contract 尚不存在。
5. Context-budget 测试未覆盖导致零任务索引的实际 G1b/G1c plan 标题格式。
6. Score Log 溯源测试不要求在评分产物 source label 中保留 `[deterministic mock agent output]`。
7. 测试仍以 fixture/scenario 为主；它们证明当前确定性路径，而非广泛的对外日志验收面。

G1d 首个安全检查点前或期间应添加的 Top 5 测试：

1. Game Log validator 拒绝缺失/未知 `source_label`。
2. 跨日志校验器拒绝 team decision 缺失/未知 `consensus_id`（当提供 Consensus Log 时）。
3. Failure Audit validator 拒绝缺失 `kind`、缺失 `repaired_to_valid_action`、未知失败 actor/target，或将已修复无效动作标记为有效的尝试。
4. 使用实际 G1b/G1c 标题风格的 Plan indexer 测试，使 context-budget gate 不会静默产出 `task_count=0`。
5. Fake-provider contract 负面测试：超时、解析失败、无效目标、畸形 JSON、以及禁止修复为有效行为。

`pytest` 缺失应仅记录为环境债务，非项目阻塞项。canonical runner 是 `unittest`，且通过。

## 9. 代码风险扫描

这不是风格审查。发现聚焦于大型正确性风险。

| 风险 | 严重度 | 证据 | 建议 |
|---|---|---|---|
| Game Log 溯源未校验 | P1 | 抽查中 `parse_game_log` 接受缺失/伪造 `source_label` | 在 provider 产出日志前增加 Game Log source-label contract |
| Decision/Consensus 跨日志联动不是校验器合约 | P1 | Team decision 的 `consensus_id = null` 仅用 Decision Log 校验器仍可 parse | 增加跨日志校验命令或用可选 Consensus Log 扩展校验器 |
| Failure Audit 未校验 | P1 | 生成 audit 存在，测试检查它，但无 parser/CLI 校验器 | 在 provider 失败模式前增加 `failure_audit.py` 和 CLI |
| Context plan indexes 对 G1b/G1c 失败 | P1 | G1b/G1c indexes 报告 `task_count=0` | 修复标题 parser 或规范化 plan index 生成 |
| Review packet 陈旧 | P2 | `.logs/review/latest/review-packet.md` 有陈旧 P1 备注和手动证据行 | packet-first review 前重新生成 |
| Score artifact source label 丢失 mock-agent 层 | P2 | G1c score 输出写 `[deterministic][decision-log]` | 决定 score label 应携带来源溯源还是分开的派生标签 |
| Game engine 可能成为 provider 垃圾场 | P2 | `game_engine.py` 已拥有确定性引擎、共识、failure audit 和产物组装 | 将 G1d provider 边界放在单独模块/合约中 |
| 校验器/生成器自证 | P2 | 当前验收主要是生成器产出 + 校验器验证 | 增加对抗性外部 fixtures/fake-provider logs |
| Windows/Linux 命令不匹配风险 | P2 | 文档仍列出 Unix 风格 `PYTHONPATH=src ...`；PowerShell 需 `$env:PYTHONPATH='src'; ...` | 保持校验脚本为 canonical；避免在 Windows 上使用原始 Unix 命令证据 |
| Demo 叙事过度宣称风险 | P2 | Demo 必须保持"not real AI Agent gameplay"边界 | 保留边界测试并增加 provider-route demo 文案测试 |

## 10. Demo 与演示风险

当前 demo 回答：

- 是的，`docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html` 代表来自生成 Game/Decision 产物的真实确定性管道输出。
- 它是确定性 mock-agent 输出，而非真实 LLM agent 输出。
- 它包含当前 source labels，且对 G1c 不再显示"not real Consensus Log collection"。
- 它支撑评测叙事：结构化日志 → score/metrics → attribution/demo。

演示优势：

- 清晰的确定性重放产物。
- Source labels 可见。
- G1c consensus 和 failure recovery 可演示。
- Validator/score/render 命令可重新运行。

演示弱点：

- 评审者可能问："真实 Agent/provider 在哪？"回答：未完成；G1d/G1e 是未来闸门。
- 评审者可能问："坏 provider 日志能被拒绝吗？"回答：Game/Decision/Consensus 部分可以，但 provider 形状的日志和 Failure Audit 需要更强的校验器。
- 评审者可能问："这个 Leaderboard 是真实的吗？"回答：否；当前行是一个确定性对局加 mock baselines。
- 评审者可能问："评分信任 Consensus Log 吗？"回答：不直接；共识校验目前是分开的。

Demo 结论：对检查点演示有用，尚未就绪作为最终产品展示。必须将其定位为确定性评测器 + mock-agent 脚手架。

## 11. 项目萎缩 / 保守性检查

### 是否偏航

否。canonical 路线仍指向评测/复盘/Leaderboard 系统，G1d、G1e 和 L1 被保留。

### 是否越做越小

中等风险。项目做了正确的保守基础工作，但可见产物现在已足够精致，mock 管道可能成为一个舒适的终点。那将是产品萎缩。

### 是否过度 mock

尚未。G1a/G1b/G1c mock 是适当的脚手架。只有当 G1d 不创建具体的 fake-provider 边界且 G1e 持续被推迟而无验收标准时，它们才变得不健康。

### 是否保留扩展路径

是的。ROADMAP 保留：

- provider adapter research / fake-provider contract；
- provider-backed single-game smoke；
- real multi-game Leaderboard；
- 按角色分离的聚合和样本量警告。

需保护的扩展路径：

- provider/fake-provider action contract；
- 批量/重放接口；
- 外部产物溯源；
- 跨日志校验器；
- failure audit contract；
- 最终多局评分聚合。

需避免的萎缩触发器：又一轮仅文档层面的 G1d 通过，不产出 fake-provider contract、负面测试和 G1e 就绪的验收标准。

## 12. Top 10 风险

| 优先级 | 风险 |
|---|---|
| P1 | Game Log 溯源未被校验器强制执行；缺失/伪造 `source_label` 被接受。 |
| P1 | Decision Log team `consensus_id` 未与 Consensus Log 交叉校验。 |
| P1 | Failure Audit 没有独立的 parser/validator。 |
| P1 | Context-budget plan indexes 对实际 G1b/G1c plan 失败，存在全量读取 plan 或使用陈旧上下文的风险。 |
| P1 | G1d 可能变成又一个纯研究循环，没有 fake-provider action contract 和失败语义。 |
| P2 | 最新 review packet 陈旧，不应作为 packet-first 批准证据。 |
| P2 | 产品文档中的 source-label 分类法滞后于 runtime 产物。 |
| P2 | 评分产物压缩溯源；demo 的 source label 比 score 输出更丰富。 |
| P2 | 测试仍以 scenario/fixture 为主，需要外部/对抗性 provider 形状用例。 |
| P2 | 无专用架构文档；provider 工作可能模糊 engine、agent、provider、evaluator 和 demo 的职责边界。 |

## 13. 建议的接下来 3 个检查点

### 检查点 1：评测信任硬化

目的：在 provider 形状的日志进入系统之前，加强评测可信度。

验收：

- Game Log 根据显式分类法校验顶层 `source_label`。
- 跨日志校验器在提供 Consensus Log 时拒绝 team Decision Log 条目缺失/未知 `consensus_id`。
- Failure Audit parser/validator 存在并有负面测试。
- Score/render 路径要求或记录已验证的溯源状态。
- G1b/G1c plan indexes 不再返回 `task_count=0`。

此检查点明确加强评测可信度。

### 检查点 2：G1d Provider Adapter Research / Fake-provider Contract

目的：将路线连接到最终 agent/provider 方向，而不进行 live provider 调用。

验收：

- 定义 provider action request/response contract。
- 定义 fake-provider 行为：成功、超时、解析失败、无效目标、畸形 JSON、拒绝/空输出。
- 定义 secrets/cost/no-CI-live-call 边界。
- 增加使用 fake-provider 输出的测试。
- 产出 G1e 就绪清单，但不运行 G1e。

此检查点明确将项目连接到最终 agent/provider 方向。

### 检查点 3：反萎缩扩展证明

目的：防止项目成为固定的 mock-log demo。

验收：

- 至少用两个 fake-provider 场景变体运行相同的 engine/evaluator 管道。
- 在不改变评测规则的情况下，展示一个有效和一个充满失败的对局。
- 产出可见的产物比较：带有清晰 source labels 的 logs、score/metrics 和 demo 输出。
- 不宣称真实 AI 对局或真实 Leaderboard。
- 找出到 G1e provider-backed single-game smoke 的最小剩余差距。

此检查点明确防止项目萎缩。

现在不要做的事：

- 不在 CI 中进行 live provider 调用。
- G1d contract 被接受前不做 G1e。
- 不从一两局对局实现多局 Leaderboard。
- 不做人机混战 UI。
- 不静默将无效 provider 输出修复为有效 Decision Log / Consensus Log 动作。
- 不批量改写历史 plan。

如果推迟太久将锁定项目为 demo 阶段的事项：

- fake-provider contract；
- provider 形状的负面 fixtures；
- 跨日志校验；
- failure audit 校验；
- source provenance taxonomy；
- 最小多轮/批量评测接口。

## 14. 校验结果

本次审计中新运行的命令：

```text
git status --short
git ls-files
git log --oneline -20
git diff --stat
git diff --check
gh pr list --limit 10 --state all
rg --files -g AGENTS.md
python scripts/dev/validate_brief.py
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests -q
$env:PYTHONPATH='src'; python -m werewolf_eval.validate_game_log docs/generated-games/g1c-wolf-consensus-game-log.json
$env:PYTHONPATH='src'; python -m werewolf_eval.validate_decision_log docs/generated-games/g1c-wolf-consensus-decision-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
$env:PYTHONPATH='src'; python -m werewolf_eval.validate_consensus_log docs/generated-games/g1c-wolf-consensus-consensus-log.json docs/generated-games/g1c-wolf-consensus-game-log.json
$env:PYTHONPATH='src'; python -m werewolf_eval.score_game docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --score-log-out C:\tmp\project-wide-healthcheck-v2-g1c-score-log.json --metrics-out C:\tmp\project-wide-healthcheck-v2-g1c-metrics-summary.json
$env:PYTHONPATH='src'; python -m werewolf_eval.render_demo docs/generated-games/g1c-wolf-consensus-game-log.json --decision-log docs/generated-games/g1c-wolf-consensus-decision-log.json --html-out C:\tmp\project-wide-healthcheck-v2-g1c-demo.html
python -m pytest -q
python scripts/context/build_plan_index.py docs/harness/plans/2026-05-31--g1c-wolf-consensus-failure-recovery-plan.md --out C:\tmp\project-wide-healthcheck-v2-g1c-plan.index.json
```

结果：

- `gh pr list --limit 10 --state all`：最近十个 PR 已合并至 PR #34 G1c plan。
- `git log --oneline -20`：最近提交包括 G1c 实现和溯源修复。
- `git status --short`：审计开始时 dirty；本报告新增一个文件。
- `git diff --stat`：本报告前已有 dirty 状态含 6 个修改文件。
- `git diff --check`：exit 0，`.oh-my-harness/tree.md` 和 `scripts/dev/build_review_packet.py` 有 LF/CRLF warning。
- `unittest`：108 tests OK。
- `compileall`：PASS。
- `validate_brief.py`：`ok: true`，`next_read: []`。
- G1c Game Log validator：PASS，18 events。
- G1c Decision Log validator：PASS，11 decisions。
- G1c Consensus Log validator：PASS，2 consensuses。
- G1c score 命令：PASS，11 score records，`decision_log=enabled`，`semantic_labels=disabled`，`decision_quality_total=0`。
- G1c render 命令：PASS，写入 `C:\tmp\project-wide-healthcheck-v2-g1c-demo.html`。
- `pytest`：FAIL，`No module named pytest`；非阻塞，因为 `unittest` 是 canonical。
- G1c plan index 重新生成：exit 0 但 `tasks=0`；工作流/工具健康度 warning。

定向证明检查：

- Game Log parser 接受了缺失和伪造的 `source_label`：确认信任缺口。
- Decision Log parser 在强制 `consensus_id = null` 后接受了 G1c team decision：确认跨日志信任缺口。
- G1c 失败模式产出了被审计的失败，且未将 invalid/timeout/parse-failure 行为修复为合法的第 1 夜 kill 动作。

## 15. 最终决定

G1d 可以启动，但仅作为一个有边界的 provider adapter research / fake-provider contract 检查点。

G1d 允许范围内的边界：

- Research PR / plan-first。
- Fake-provider contract 和负面 fixtures。
- 超时、解析失败、无效动作、畸形 JSON 和禁止修复语义。
- Secrets、成本、no-CI-live-call 和环境边界。
- 无真实 provider 调用。
- 无 G1e smoke。
- 无多局 Leaderboard。
- 无人机混战 UI。

可在 G1d 启动后推迟：

- 真实 provider-backed 对局执行。
- L1 多局 Leaderboard。
- 完整架构文档，只要 G1d plan 显式分离 provider、engine、evaluator 和 demo 职责。
- 打磨旧历史文档。

不能再推迟太久：

- Game Log source-label 校验。
- Decision/Consensus 跨日志校验。
- Failure Audit validator。
- Fake-provider 负面 fixtures。
- G-track plan 的 Context index 可靠性。

最终项目健康立场：继续，但有意识地扩展。当前确定性脚手架只有在接下来的检查点将其转化为 provider-ready 的评测工具而非更好看的 mock demo 时，才是有用且可信的。

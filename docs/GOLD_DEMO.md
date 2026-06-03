# GOLD_DEMO — Werewolf-agent

> **Phase 1 legacy.** This document describes the completed Phase 1 deterministic MVP / gold demo proof-of-concept. Current product direction is `docs/ROADMAP.md` and `docs/PRODUCT_ONE_PAGER.md`. The HTML gold demo at `docs/demo/phase1-gold-demo.html` is an offline audit artifact, not primary UX.

## 固定输入

一局 6 人狼人杀的结构化 Game Log（JSON）。

对局来源（owner 决策）：优先使用人工编写的虚拟但逻辑自洽的 6 人对局。如能找到版权合适的公开名局，可使用名局。来源在 Spike 0 中最终确定。

角色配置（owner 决策）：Phase 1 固定为 **2 狼人 + 1 预言家 + 1 女巫 + 2 平民**。不包含猎人。

## 固定输出

1. **时间线视图**：按 sequence 排列的完整事件序列。每夜/每天分色块。标注每个事件的 visibility。
2. **状态表**：每轮结束时的存活/死亡/身份揭示状态矩阵。
3. **投票表**：每轮投票的投票人 → 被投票人矩阵，标注投票差。
4. **结果评测指标**：winner、game_length、werewolf/villager survival_rate、margin。
5. **过程评测指标**：每个角色每轮的 outcome_score、rule_integrity_score、投票准确率。每项指标标注计算依据（触发了哪条规则）。
6. **规则归因面板**：关键转折点列表（每项含 rule_id、round、actor、description_template、impact_score、evidence event_ids）。
7. **单局评分卡**：6 角色的三维评分子得分汇总。
8. **Leaderboard UI demo**：一行来自本局的真实评分 + 多行 mock 数据。排序维度可切换。

## 数据标注

所有输出必须明确标注数据来源：

| 数据 | 标注 |
|------|------|
| Game Log 事件 | `[结构化事件]` — 人工从名局整理 |
| 人工编写的 decision_summary | `[人工 gold sample]` |
| 人工编写的 consensus sample | `[人工 gold sample]` |
| 确定性规则计算的指标 | `[deterministic]` |
| 确定性规则归因 | `[deterministic]` |
| Leaderboard 中非本局的行 | `[mock]` |
| 可视化页面中的引导文案 | `[确定性]`（非 AI 生成） |

Phase 1 不使用真实 AI 生成内容，不做真实 Agent 对局。所有 AI 标注能力（矛盾检测、信息泄漏检测、逻辑支撑判断）在 Spike 5 中验证可行性，但 Gold Demo 中不依赖。Decision Log 和 Consensus Log 在 Phase 1 仅以人工 gold sample 形式存在，不宣称已实现真实数据采集。

Phase 1 最小可视化交付为可双击打开的单文件静态 HTML。不依赖后端、不依赖构建工具、不引入 React/Vite。建议路径：`docs/demo/phase1-gold-demo.html`。Phase 1 不要求精美 UI，只要求能展示时间线、状态表、投票表、指标表、单局评分卡、Leaderboard UI demo。

## 3 分钟演示脚本

```
[0:00-0:30] 输入展示
  - 展示结构化 Game Log 摘要
  - 标注：事件总数 X 条，公开事件 Y 条，私有事件 Z 条
  - 6 个角色就座，角色分配可见

[0:30-1:30] 过程评测面板
  - 时间线视图：每轮每天的事件序列
  - 投票表：谁投了谁，投票差
  - 状态表：每轮结束时的存活/死亡/身份揭示
  - 过程指标实时标注
  - 旁白不解释心理，只读数据

[1:30-2:30] 结果评测 + 规则归因
  - 结果评测面板：胜负方、回合数、存活数、分差
  - 归因面板：系统标记的关键转折点（基于规则，不是 AI 分析）
  - 每条归因可展开查看触发的规则和引用的 event_ids
  - 示例："关键转折点 #3：第 2 轮投票，预言家以 1 票之差被处决 → 此后村民投票准确率下降至 0%"

[2:30-3:00] Leaderboard UI demo
  - 当前对局的单局评分
  - Leaderboard 展示多行（1 行真实 + mock 数据）
  - 排序维度可切换
  - 收束语："这就是评测系统的工作方式——不看谁'说得好'，只看数据说了什么"
```

## 人工 gold sample 示例

Phase 1 为对局中每个关键行动手写 decision_summary 和 consensus sample，标注 `[人工 gold sample]`，用于验证评分器的完整链路。这些 sample 不代表真实 AI Agent 行为——仅用于校准评分器和演示数据流。

### Decision Log gold sample（预言家查验）

```jsonc
{
  "decision_id": "g001_n1_seer_check_p2",
  "actor": "p3",
  "phase": "night",
  "action": "check",
  "target": "p2",
  "visible_info_refs": ["event_08", "event_11"],
  "reason_summary": "p2 发言中无依据打包保人，投票跟风，行为可疑，优先查验。",
  "decision_type": "inference_based",
  // [人工 gold sample]
}
```

### Consensus Log gold sample（狼人夜间协商）

```jsonc
{
  "consensus_id": "g001_n1_wolf_consensus",
  "game_id": "g001",
  "round": 1,
  "phase": "night",
  "team": "werewolf",
  "participants": ["p1", "p2"],
  "coordinator": "p1",
  "max_rounds": 3,
  "actual_rounds": 2,
  "status": "accepted_consensus",
  // [人工 gold sample]
  "proposals": [
    {
      "proposal_id": 1,
      "proposer": "p1",
      "proposed_target": "p4",
      "visible_info_refs": ["event_08", "event_14"],
      "reason_summary": "p4 白天发言多次暗示有身份信息，疑似预言家隐藏身份。",
      "confidence": 0.72
    },
    {
      "proposal_id": 2,
      "proposer": "p2",
      "proposed_target": "p6",
      "visible_info_refs": ["event_03"],
      "reason_summary": "p6 发言保守，可能是神职低调。",
      "confidence": 0.55
    }
  ],
  "responses": [
    {
      "response_id": 1,
      "to_proposal_id": 1,
      "responder": "p2",
      "response_type": "support_with_reason",
      "reason_summary": "同意，p4 发言确实异常，杀神优先。",
      "visible_info_refs": ["event_14"]
    },
    {
      "response_id": 2,
      "to_proposal_id": 2,
      "responder": "p1",
      "response_type": "oppose_with_reason",
      "reason_summary": "p6 更可能是平民，杀 p4 风险收益比更高。",
      "visible_info_refs": ["event_03", "event_08"]
    }
  ],
  "final_decision": {
    "target": "p4",
    "decision_type": "accepted_consensus",
    "primary_proposer": "p1",
    "supporters": ["p1", "p2"],
    "dissenters": [],
    "resolution_round": 2
  }
}
```

## 验收标准

1. 两次运行同一 Game Log，所有 deterministic 指标结果**完全一致**。
2. 规则归因产出的每个 turn_point 有明确 rule_id、impact_score 和 evidence event_ids。
3. 非技术用户能在 3 分钟内复述："这局谁赢了、关键转折点是什么、评测系统怎么打分"。
4. 可视化页面中所有 mock / gold / deterministic 数据有清晰标注。
5. Leaderboard UI demo 的排序切换可用、样本量警告可见。

## 失败兜底

- 对局来源：Spike 0 的默认路径是人工编写虚拟对局（逻辑自洽、事件链完整）。名局仅在版权清晰且资料完整时作为备选。
- 可视化技术选型（owner 决策）：Phase 1 使用静态 HTML，不提前选择 React / Vite / 其他前端框架。如复杂度超出预期，先做纯 HTML 无交互版本。
- 如果评分器实现中被发现规则有歧义：回退到 EVALUATION_RUBRIC.md 修正规则，再重跑。

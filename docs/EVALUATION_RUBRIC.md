# EVALUATION_RUBRIC — Werewolf-agent

评分体系唯一事实来源。本文档定义所有评分维度、计算公式、角色 Rubric、AI 裁判边界和 Leaderboard 结构。其他文档引用本文件，不复制评分规则。

**Phase 1 重要限定：**
- 本文档中 Consensus Log 和 Decision Log 为 Phase 2 启用；Phase 1 仅以人工 gold sample 演示，不代表已实现真实数据采集。
- `decision_quality_score` 在 Phase 1 恒为 0（无真实 Decision Log），不宣称已真实可用。
- `team_coordination_score` 权重公式为 Phase 2 draft，Phase 1 仅展示子指标。
- Leaderboard 在 Phase 1 仅做 UI demo（一行真实数据 + mock），不宣称真实排行榜完成。

---

## A. 评分架构

### A.1 三分结构

每个行动评估三个正交维度：

| 维度 | 含义 | 回答的问题 | 谁来判断 |
|------|------|-----------|---------|
| `outcome_score` | 结果贡献分 | 这个行动客观上帮了己方还是敌方？ | 确定性规则（对照终局胜负和身份） |
| `decision_quality_score` | 决策质量分 | 在已知信息约束下，这个决策的质量如何？ | 确定性检查 + AI 辅助语义标注 |
| `rule_integrity_score` | 规则合规分 | 这个行动是否违反了信息隔离或规则约束？ | 确定性规则（对照信息可见性白名单） |

**评分范围：**

| 分数 | 范围 | 说明 |
|------|------|------|
| `outcome_score` | -3 到 +3（整数） | 正 = 有利于己方阵营最终胜利，负 = 有害，0 = 无影响或无法判定 |
| `decision_quality_score` | -2 到 +2（整数） | 正 = 决策有依据且逻辑自洽，负 = 决策与可见信息矛盾或无依据，0 = 正常操作 |
| `rule_integrity_score` | -3 到 0（整数） | 0 = 无违规，负 = 违规。**只能扣分，不能加分** |

### A.2 评分原则

1. **每个行动默认 0 分。** 只在有明确证据时加分或扣分。
2. **结果贡献和决策质量必须分开。** 狼人随机刀中预言家：outcome +3，decision_quality 0。
3. **防止"蒙对了"被高估。** 没有可见信息支撑的正确结果，决策质量不加分。
4. **AI 裁判不能自由打分。** AI 只输出结构化语义标签，分数由确定性规则计算。
5. **跨局聚合分离维度。** 三个分维度独立保存和聚合，不混合为一个数字。
6. **0 分不是"表现差"。** 0 分是基线——正常操作不加不扣。
7. **违规只扣不加。** rule_integrity_score 最高为 0，不可能为正。

### A.3 单局聚合

```
单局 agent 总分 = Σ(outcome_score) + Σ(decision_quality_score) + Σ(rule_integrity_score)
```

三项分开保存。Leaderboard 可按任意维度排序。

### A.4 跨局聚合

```
avg_outcome_score = Σ(各局 outcome_score) / games_played
avg_decision_quality_score = Σ(各局 decision_quality_scores) / total_actions
avg_rule_integrity_score = Σ(各局 rule_integrity_scores) / games_played
avg_total_score = avg_outcome + avg_decision_quality + avg_rule_integrity
```

`decision_quality_score` 按行动数归一化（每局行动数可能不同），另外两个按局数归一化。

---

## B. 日志四层结构

### B.1 Game Log（事实层，不可变）

```jsonc
{
  "game_id": "string",
  "players": [
    { "player_id": "p1", "role": "werewolf", "team": "werewolf" }
  ],
  "events": [
    {
      "event_id": 1,
      "sequence": 1,
      "round": 1,
      "phase": "night",             // night | day | game_end
      "type": "werewolf_kill",      // 事件类型枚举，见 B.5
      "actor": "wolf_team",         // 狼人团队行动时 actor = "wolf_team"
      "target": "p4",
      "data": {},
      "visibility": "werewolf_team" // public | all | werewolf_team | seer | witch | hunter | specific_player_ids
    }
  ],
  "result": {
    "winner": "werewolf",
    "end_round": 3,
    "survivors": ["p1", "p2"],
    "end_condition": "werewolf_majority"
  }
}
```

### B.2 Consensus Log（狼人协商层）

Phase 2 启用。Phase 1 可用人工 gold sample。

```jsonc
{
  "consensus_id": "string",
  "game_id": "string",
  "round": 1,
  "phase": "night",
  "team": "werewolf",
  "participants": ["p1", "p2"],
  "coordinator": "p1",
  "max_rounds": 3,
  "actual_rounds": 2,
  "status": "accepted_consensus",

  "proposals": [
    {
      "proposal_id": 1,
      "proposer": "p1",
      "proposed_target": "p4",
      "visible_info_refs": ["event_id"],
      "reason_summary": "≤150字",
      "confidence": 0.72
    }
  ],

  "responses": [
    {
      "response_id": 1,
      "to_proposal_id": 1,
      "responder": "p2",
      "response_type": "support_with_reason",
      "reason_summary": "≤150字",
      "visible_info_refs": ["event_id"]
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

**`decision_type` 枚举：**

| 值 | 含义 | 说明 |
|----|------|------|
| `consensus` | 双方一开始就一致 | 最优情况 |
| `accepted_consensus` | 一方被说服后接受对方方案 | 正常协作 |
| `coordinator_tie_break` | 僵局后协调者拍板 | 协作失败，双方轻微扣分 |
| `forced_random` | 双方均未有效输出 | 严重失败（AI 故障） |

不使用 `majority`——2 狼局没有多数票概念。

**狼人讨论约束（硬限制）：**
- 最多 3 轮讨论。
- 每轮每个狼人最多 1 条 proposal 或 response。
- 单个 reason_summary ≤ 150 字。
- 最终必须产生唯一 kill target。

**无法达成共识时的降级裁决链：**
1. 双方一致 → target = 共同目标。
2. 一方被说服 → target = 被说服方的最终立场。
3. 双方各持己见 → 采用 coordinator 的方案。
4. 双方均未提案（AI 故障）→ 随机选择非狼人目标。

### B.3 Decision Log（意图层）

Phase 2 启用。Phase 1 可用人工 gold sample。

```jsonc
{
  "decision_id": "string",
  "game_id": "string",
  "actor": "string",
  "decision_scope": "single",      // "single" | "team"
  "consensus_id": "string|null",   // team scope 时关联 Consensus Log
  "phase": "night|day",
  "action": "string",
  "target": "string|null",
  "visible_info_refs": ["event_id"],
  "reason_summary": "≤200字",
  "decision_type": "inference_based|random|retaliatory|team_coordinated|default",
  "confidence": 0.68,              // 可选
  "strategy_tag": "string"         // 可选
}
```

### B.4 Score Log（评价层，可重算）

```jsonc
{
  "score_id": "string",
  "game_id": "string",
  "event_id": "string",
  "decision_id": "string|null",    // Phase 2
  "actor": "string",
  "round": 1,
  "phase": "night",
  "outcome_score": 0,
  "decision_quality_score": 0,     // Phase 1 为 0（无真实 Decision Log）
  "rule_integrity_score": 0,
  "team_coordination_subscore": 0.0, // Phase 2
  "team_shared_scores": {},         // Phase 2
  "rules_triggered": ["rule_id"],
  "computed_at": "ISO8601"
}
```

### B.5 Game Log 事件类型枚举

| type | 说明 | visibility | actor |
|------|------|------------|-------|
| `role_assignment` | 角色分配 | `specific_player_ids` | system |
| `werewolf_kill` | 狼人选杀目标 | `werewolf_team` | `wolf_team` |
| `seer_check` | 预言家查验 | `seer` | seer |
| `witch_save` | 女巫救人 | `witch` | witch |
| `witch_poison` | 女巫毒人 | `witch` | witch |
| `hunter_shoot` | 猎人开枪 | `public` | hunter |
| `player_speech` | 玩家发言 | `public` | speaker |
| `player_vote` | 玩家投票 | `public` | voter |
| `player_eliminated` | 玩家被处决 | `public` | system |
| `player_died` | 玩家非处决死亡 | `public` | system |
| `role_revealed` | 身份揭示 | `public` | system |
| `game_over` | 游戏结束 | `public` | system |
| `contradiction_flag` | 矛盾标记 | `public` | 评分器计算产物 |
| `info_leak_flag` | 信息泄漏标记 | `public` | 评分器计算产物 |

---

## C. 结果评测指标（稳定规则）

结果评测 = 对一局游戏最终结果的量化评分。只依赖 Game Log 的 `result` 和 `events` 终端状态。

| 指标 | 定义 | 计算方式 | 类型 |
|------|------|---------|------|
| `winner` | 胜负方 | `result.winner` | 枚举 |
| `game_length` | 游戏回合数 | `result.end_round` | 整数 |
| `werewolf_survival_rate` | 狼人存活率 | 存活狼人数 / 总狼人数 | 0-1 |
| `villager_survival_rate` | 村民存活率 | 存活村民数 / 总村民数 | 0-1 |
| `margin` | 胜方优势 | 胜方存活人数 - 负方存活人数 | 整数 |
| `werewolf_win_speed` | 狼人获胜速度 | 狼人胜时：剩余人数差 / 回合数 | 浮点数 |
| `villager_win_efficiency` | 村民获胜效率 | 村民胜时：处决狼人数 / 回合数 | 浮点数 |

---

## D. 过程评测指标（稳定规则）

### D.1 通用指标（所有角色）

| 指标 | 定义 | 计算方式 |
|------|------|---------|
| `vote_accuracy` | 投票准确率 | 投给敌对阵营的次数 / 总投票次数（按终局身份判定） |
| `survival_rounds` | 存活轮数 | 角色死亡轮次 |
| `contradiction_count` | 矛盾标记次数 | 评分器标记的 contradiction_flag 总数 |
| `info_leak_count` | 信息泄漏次数 | 评分器标记的 info_leak_flag 总数 |

### D.2 狼队协作指标

| 指标 | 类型 | 定义 | 计算方式 |
|------|------|------|---------|
| `consensus_rate` | 狼队共享 | 达成共识的夜数 / 总夜数 | consensus + accepted_consensus 的夜数 / 总夜数 |
| `leadership_success` | **个人** | 提案被采纳的频率 | 该狼人作为 primary_proposer 的夜数 / 该狼人提出 proposal 的夜数 |
| `follow_quality` | **个人** | 接受对方提案时是否有独立判断 | 高质量跟随（有附加 reason + refs）/ 总跟随次数 |
| `persuasion_success` | **个人** | 成功说服对方的频率 | 提出 oppose 后对方最终接受该狼人方案的比例 |
| `deadlock_count` | 狼队共享 | 僵局次数（未归一化） | `decision_type = "coordinator_tie_break"` 的夜数 |
| `deadlock_rate` | 狼队共享 | 僵局率（归一化） | `deadlock_count` / 总夜数 |
| `kill_quality_total` | 狼队共享 | 击杀质量总分 | Σ(杀神职 × 3 + 杀平民 × 1) |

**owner 决策：狼队协作综合权重暂不确认。** Phase 1 Leaderboard 狼人 tab 优先展示子指标（leadership_success、follow_quality、persuasion_success、deadlock_rate），不合并为单一 team_coordination_score。

`team_coordination_score` 计算公式（**Phase 2 draft 参考，权重待积累 ≥ 10 局真实数据后校准，Phase 1 不使用**）：

```
team_coordination_score = 
  leadership_success × 0.4 +
  follow_quality × 0.3 +
  persuasion_success × 0.3
  - deadlock_rate × 0.5
```

注意上述公式中 `deadlock_rate` 代替了 `deadlock_count`（归一化后不同局之间可比）。此公式仅作为 Phase 2 设计意图的占位，不代表已确认的权重分配。

### D.3 预言家专项指标

| 指标 | 定义 | 计算方式 |
|------|------|---------|
| `check_accuracy` | 查验准确率 | 正确查验数 / 总查验次数（以终局身份为准） |
| `info_conveyed` | 信息传递率 | 查验结果在发言中可追溯提及的次数 / 总查验次数 |
| `check_targeting` | 查验目标选择 | 查验狼人次数 / 总查验次数 |

### D.4 女巫专项指标

| 指标 | 定义 | 计算方式 |
|------|------|---------|
| `save_accuracy` | 救人准确率 | 救的是村民 = 1，救的是狼人 = 0 |
| `poison_accuracy` | 毒人准确率 | 毒的是狼人 = 1，毒的是村民 = 0 |
| `ability_utilization` | 技能使用率 | 使用了所有可用技能 = 1，部分使用 = 0.5，未使用 = 0 |

### D.5 队伍级指标

以下指标使用终局身份做离线评测，不代表玩家当时知道这些身份。属于过程评测指标，不直接等同于胜负能力。

| 指标 | 定义 | 计算方式 |
|------|------|---------|
| `village_vote_cohesion` | 村民阵营投票一致性 | 对每个白天投票阶段：取终局身份为村民阵营的存活投票者。计算 `max(投向同一目标的人数) / 村民阵营投票人数`。对所有白天取平均。若该日村民阵营投票人数为 0，该日不参与平均。 |
| `werewolf_vote_coordination` | 狼人投票协同度 | 对每个白天投票阶段：取存活狼人投票者。若存活狼人数 ≥ 2 且全部投向同一目标，则该日为 1；否则为 0。若存活狼人数 < 2，该日不参与平均。对所有可计算白天取平均。 |
| `turn_point_count` | 关键转折点数量 | 归因规则计算的 turn_points 总数 |

---

## E. 角色评分 Rubric（稳定规则）

每个行动默认 0 分。只在有明确证据时加减分。

### E.1 狼人

**狼队团队行动（夜间 kill）：**

| 行动 | outcome | decision_quality | rule_integrity | 条件 |
|------|---------|-----------------|----------------|------|
| kill 目标为神职（预言家/女巫/猎人） | +3 | — | — | 对照终局身份 |
| kill 目标为平民 | +1 | — | — | 对照终局身份 |
| kill 目标选择有推理支撑 | — | +1 到 +2 | — | AI 判断 refs 逻辑支撑，**仅 proposer 得分** |
| kill 目标为随机/default | — | 0 | — | decision_type = random/default，团队共享 |
| 提出杀同伴（异常行为） | — | — | **-1**（仅 proposer） | 标记异常，非正常评分项 |
| 引用不可见信息 | — | — | **-3**（仅违规者） | deterministic |
| 僵局（coordinator tie-break） | — | **-0.5**（双方都扣） | — | 协作失败 |
| AI 故障（forced_random） | — | **-2**（双方都扣） | — | 严重失败 |

**狼人个人行动（白天投票）：**

| 行动 | outcome | decision_quality | rule_integrity | 条件 |
|------|---------|-----------------|----------------|------|
| 投票处决村民关键角色（预言家/女巫/猎人） | +2 | — | — | 投票结果 + 身份对照 |
| 投票处决平民 | +1 | — | — | — |
| 投票处决狼人同伴 | -2 | — | — | — |
| 投票延续夜间策略（与夜间共识一致） | — | +1 | — | 言行一致 |
| 投票与夜间共识矛盾 | — | -1 | — | 言行矛盾 |
| 投票有逻辑支撑 | — | +1 | — | AI 判断 refs |
| 投票随机 | — | 0 | — | — |
| 成功引导村民投错票 | +2 | +1 | — | 共现分析 |

### E.2 预言家

| 行动 | outcome | decision_quality | rule_integrity | 条件 |
|------|---------|-----------------|----------------|------|
| 查验狼人 | +2 | — | — | 对照终局身份 |
| 查验平民 | 0 | — | — | 信息有价值但不加分 |
| 查验已被查验过的玩家 | — | -1 | — | 浪费查验 |
| 查验目标选择有推理支撑 | — | +1 | — | AI 判断 refs |
| 查验目标随机 | — | 0 | — | — |
| 发言中有效传递查验结果（被后续行动引用） | +2 | +1 | — | 查验结果在发言中可追溯，且后续村民据此行动 |
| 发言中未传递关键查验结果 | -1 | -1 | — | 预言家死亡时仍有未传递的狼人查验 |
| 投票处决狼人 | +2 | — | — | — |
| 投票处决村民关键角色 | -1 | — | — | — |
| 投票处决平民 | -1 | — | — | — |
| 引用不可见信息 | — | — | **-3** | deterministic |
| 谎报查验结果 | — | -1 | — | 战术性撒谎，不违规但降低可信度 |

### E.3 女巫

| 行动 | outcome | decision_quality | rule_integrity | 条件 |
|------|---------|-----------------|----------------|------|
| 救预言家/猎人 | +3 | — | — | 对照终局身份 |
| 救平民 | +1 | — | — | — |
| 救狼人 | -1 | — | — | 无法在当下知道，终局判定 |
| 不救任何人（保留技能） | 0 | — | — | 合理保留 |
| 毒狼人 | +3 | — | — | — |
| 毒预言家/猎人 | -3 | — | — | — |
| 毒平民 | -1 | — | — | — |
| 救/毒决策有推理支撑 | — | +1 | — | AI 判断 refs |
| 救/毒决策随机 | — | 0 | — | — |
| 两夜内同时用掉救和毒且效果差 | — | -1 | — | 策略审视 |
| 引用不可见信息 | — | — | **-3** | deterministic |

### E.4 平民

| 行动 | outcome | decision_quality | rule_integrity | 条件 |
|------|---------|-----------------|----------------|------|
| 投票处决狼人 | +2 | — | — | — |
| 投票处决预言家/女巫/猎人 | -2 | — | — | — |
| 投票处决平民 | -1 | — | — | — |
| 投票有逻辑依据 | — | +1 | — | AI 判断 refs |
| 投票随机/default | — | 0 | — | — |
| 发言提出有效质疑（引出后续关键行动） | — | +1 | — | 因果追踪 |
| 声称自己有特殊身份信息 | — | — | **-2** | 平民不应声称有角色专属信息 |
| 引用不可见信息 | — | — | **-3** | deterministic |

### E.5 猎人（仅当后续对局包含猎人时启用；Phase 1 gold demo 不启用）

| 行动 | outcome | decision_quality | rule_integrity | 条件 |
|------|---------|-----------------|----------------|------|
| 死亡开枪带走狼人 | +3 | — | — | — |
| 死亡开枪带走预言家/女巫 | -3 | — | — | — |
| 死亡开枪带走平民 | -1 | — | — | — |
| 开枪目标有依据 | — | +1 到 +2 | — | AI 判断 refs |
| 开枪随机 | — | 0 | — | — |
| 引用不可见信息 | — | — | **-3** | deterministic |

---

## F. 规则归因（稳定规则）

归因 = **确定性的、可计算的、可复现的**规则引擎。不对自然语言做推理，只对结构化事件做模式匹配。

### F.1 归因规则

**规则 1：关键投票转折点**
```
触发条件：投票差 = 1 票（1 票改变结果），且被处决者身份在终局可判定。
输出："第 X 轮投票为关键转折点，Y 以 Z 票之差被处决，该玩家身份为 [狼人/村民]。"
影响赋值：若被处决者为村民阵营核心角色（预言家/女巫），影响权重 ×2。
```

**规则 2：信息断层归因**
```
触发条件：预言家死亡时，已查验但未在发言中可追溯提及的结果数 > 0。
输出："预言家在第 X 轮死亡，Y 条查验结果未能传递给村民阵营。"
影响赋值：每条未传递的狼人身份查验 +1 影响分。
```

**规则 3：女巫误伤归因**
```
触发条件：女巫毒杀/未救的目标终局身份为村民阵营关键角色。
输出："女巫在第 X 轮的 [毒杀/未救] 决策误伤村民阵营关键角色。"
影响赋值：+2 影响分。
```

**规则 4：投票偏离归因**
```
触发条件：某一轮中，村民阵营玩家投票准确率 < 50%。
输出："第 X 轮投票，村民阵营投票准确率仅 Y%，Z 名村民投给了同阵营玩家。"
影响赋值：偏离率 × 参与投票村民数。
```

**规则 5：伪装成功归因**
```
触发条件：某狼人在第 X 轮被投票但未被处决，且后续存活 ≥ 2 轮。
输出："狼人 Y 在第 X 轮被投票但成功逃脱，此后继续存活 Z 轮。"
影响赋值：+1（对狼人阵营正向）。
```

### F.2 归因输出格式

```jsonc
{
  "turn_points": [
    {
      "rule": "critical_vote",
      "round": 2,
      "actor": "p3",
      "description_template": "第 2 轮投票，预言家 p3 以 1 票之差被处决",
      "impact_score": 2.0,
      "impact_sign": "negative",
      "evidence": ["event_15", "event_17", "event_19"]
    }
  ],
  "top_attribution": "预言家过早死亡导致村民信息断层是村民阵营失败的主要原因"
}
```

`top_attribution` 是按 impact_score 排序后最高项的模板化结论——不是 AI 自由文本。

---

## G. 决策质量判断机制

### G.1 "蒙对了" vs "有依据"

判断依赖 Decision Log 中的 `visible_info_refs` 和 `reason_summary`。

**评分流程：**

```
Step 1 [deterministic]：检查每个 ref 的 visibility 对该角色是否合法。
  → 不合法 → rule_integrity_score 扣分，同时标记"不可信决策"。

Step 2 [deterministic]：检查 refs 是否为空，或 decision_type 是否为 "random"。
  → 是 → decision_quality_score = 0（不扣不加）。

Step 3 [AI 辅助]：语义检查 refs 是否逻辑支撑 reason_summary 中的结论。
  → AI 输出：{ logically_supported: bool, confidence: float }
  → 是 → decision_quality_score 加分。
  → 否 → decision_quality_score = 0 或 -1（逻辑明显矛盾）。

Step 4 [deterministic]：对照 outcome_score。
  → outcome + 且 decision_quality + → "高质量决策"。
  → outcome + 且 decision_quality 0 → "运气好"。
  → outcome - 且 decision_quality + → "好决策坏运气"。
  → outcome - 且 decision_quality - → "双重失败"。
```

### G.2 示例

**狼人随机刀中预言家：**
```
Decision Log: visible_info_refs = [], decision_type = "random"
评分: outcome = +3, decision_quality = 0
→ 可识别为"运气型玩家"
```

**狼人基于推理刀中预言家：**
```
Decision Log: visible_info_refs = ["event_12","event_15","event_18"], reason = "p4 多次暗示有额外信息，疑似预言家隐藏身份"
评分: outcome = +3, decision_quality = +2
→ 可识别为"实力型玩家"
```

---

## H. AI 裁判边界

### H.1 AI 不能做的事

- **不能给分。** 分数永远是确定性规则计算的。
- **不能读完整局后自由裁判。** AI 只读当前决策的 `visible_info_refs` + `reason_summary`，不给全知视角。
- **不能生成长篇解释。** 输出必须是结构化 JSON。
- **不能事后诸葛亮。** AI 不知道游戏结果（不传入 outcome 信息）。

### H.2 AI 可以做的语义标注

| 标注任务 | 输入 | 输出格式 | 用于哪个评分 |
|---------|------|---------|------------|
| 逻辑支撑判断 | refs 的事件内容 + reason_summary | `{ logically_supported: bool, confidence: 0-1 }` | decision_quality_score |
| 矛盾检测 | Agent 多条发言/决策之间 | `{ has_contradiction: bool, evidence_event_ids: [], contradiction_type: "info|logic|goal" }` | rule_integrity_score |
| 信息泄漏检测 | 发言内容 vs 角色可见信息白名单 | `{ has_info_leak: bool, leaked_info_type: "role|action|night_info", evidence: string }` | rule_integrity_score |
| 发言行为分类 | 发言文本 | `{ speech_act_types: ["claim","accusation","defense","question","bluff"] }` | 辅助指标 |

### H.3 AI 输出格式强制约束

```jsonc
{
  "task": "logical_support_check",
  "input_refs": ["event_12", "event_15"],
  "output": {
    // 任务特定的结构化输出，不含自然语言解释段落
  },
  "confidence": 0.72,
  "model": "claude-haiku-4-5",
  "token_count": 340
}
```

### H.4 延后到 Phase 2+ 的 AI 用途

| 用途 | Phase | 原因 |
|------|-------|------|
| 跨局策略风格聚类 | Phase 3 | 需要多局数据 |
| 发言说服力评分 | Phase 3 | 高度主观，需大量校准 |
| 自动发现新型作弊模式 | Phase 3 | 需要对抗样本积累 |
| 自然语言复盘报告 | Phase 3 或不做 | 产品形态待定 |

---

## I. Leaderboard

### I.1 字段

```jsonc
{
  "agent_id": "string",
  "model": "string",
  "agent_version": "string",
  "games_played": 0,
  "role_distribution": {
    "werewolf": 0, "seer": 0, "witch": 0, "villager": 0, "hunter": 0
  },
  "win_rate": 0.0,
  "avg_total_score": 0.0,
  "avg_outcome_score": 0.0,
  "avg_decision_quality_score": 0.0,
  "avg_rule_integrity_score": 0.0,
  "info_leak_rate": 0.0,
  "contradiction_rate": 0.0,
  "role_scores": {
    "werewolf": { "win_rate": 0.0, "avg_total_score": 0.0, "games": 0, "team_coordination_score": 0.0, "leadership_success": 0.0, "follow_quality": 0.0, "persuasion_success": 0.0, "deadlock_rate": 0.0 },
    "seer": { "win_rate": 0.0, "avg_total_score": 0.0, "games": 0 },
    "witch": { "win_rate": 0.0, "avg_total_score": 0.0, "games": 0 },
    "villager": { "win_rate": 0.0, "avg_total_score": 0.0, "games": 0 }
  },
  "confidence_level": "low|medium|high",
  "sample_size_warning": "string|null",
  "last_updated": "datetime"
}
```

### I.2 默认排序

**默认按 `avg_decision_quality_score` 降序排列。**

`avg_decision_quality_score` 是 agent 自身能力的最纯粹度量——衡量"给定可用的信息，决策有多好"。胜率受随机性和队友质量影响太大。

### I.3 可切换排序维度

| 排序维度 | 用途 |
|---------|------|
| `avg_decision_quality_score`（默认） | 决策能力 |
| `win_rate` | 实战结果（需足够样本） |
| `avg_outcome_score` | 结果贡献 |
| `avg_total_score` | 综合评分 |
| `avg_rule_integrity_score` | 规则遵守 |
| `info_leak_rate`（升序） | 信息卫生 |

### I.4 按角色分 tab

**不跨角色混合排名。**

- 总览 tab：按 `avg_decision_quality_score`。
- 狼人 tab：含 leadership_success、follow_quality、persuasion_success、deadlock_rate 子指标列。team_coordination_score 列标注为 Phase 2 draft。
- 预言家 tab。
- 女巫 tab。
- 平民 tab。

每个角色 tab：Agent 必须至少玩过 3 局该角色才能进入该 tab。

### I.5 样本量警告

| 条件 | 展示 |
|------|------|
| `games_played < 5` | 行背景标灰，显示"数据不足，排名无统计意义" |
| `games_played < 10` | 显示"低置信度" |
| 某角色 `games < 5` | 该角色专项分标灰，显示"样本不足" |
| `games_played >= 20` | 显示"统计可信" |

### I.6 Phase 1 限定

**Phase 1 只做 Leaderboard UI demo：**
- 一行来自 Phase 1 名局的真实评分。
- 其余行为 mock 数据，标注 `[mock]`。
- 不宣称真实排行榜完成。
- 不发布公开排名。
- 不做跨模型对比。

---

## J. 文档维护边界

| 规则类型 | 标注 | 修改条件 |
|---------|------|---------|
| 结果评测指标 | 稳定规则 | spike 验证通过后不轻易改 |
| 过程评测指标（D.1/D.3/D.4/D.5） | 稳定规则 | spike 验证通过后不轻易改 |
| 角色 Rubric | 稳定规则 | Phase 2 根据真实 Agent 行为可微调 |
| 归因规则 | 稳定规则 | Phase 2 可根据新发现的模式增加规则 |
| 狼队协作子指标（leadership_success 等） | 稳定规则 | 指标定义稳定，Leaderboard 展示方式可变 |
| 狼队协作综合权重 (team_coordination_score) | **Phase 2 draft** | Phase 2 积累 ≥ 10 局数据后校准，Phase 1 不使用 |
| Consensus Log schema | **Phase 2 draft** | Phase 1 仅人工 gold sample 验证结构，Phase 2 根据真实 AI 交互调整 |
| Decision Log schema | 稳定结构 | Phase 2 启用，字段语义不变 |
| AI 标注准确率阈值 | **Phase 2 draft** | Spike 5 验证后确定 |
| Leaderboard 字段 | 稳定结构 | 字段语义不变，可增加新字段 |
| 事件类型枚举 | 稳定结构 | 可扩展，不删除已有类型 |
| decision_quality_score | **Phase 2 启用** | Phase 1 恒为 0，不宣称真实可用 |

---

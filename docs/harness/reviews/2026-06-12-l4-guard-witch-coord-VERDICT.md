# l4_guard_witch_coord (prompt_v4) — Experiment Verdict

> 2026-06-12,用户裁决。实验:l4_guard_witch_coord 臂(prompt_v4 = v3 + 女巫解药协调提示,
> 守卫板 + rules_v1_2,标准规则不动)45 局 vs l4_guard(prompt_v3)。
> **座位级真配对**(同 multiset 同 seed 流,布局逐座位相同,亲证 game 000)。
> 有效性:**n_valid=41**(1 局 fail-closed 无 game-log + 1 局低 live + 2 局 coverage 门剔除;≥40 线内)。
> **45 局产物 I1-I8c 零违例**;注入覆盖 45/45(每局夜1女巫请求都带协调提示,条件门正确:夜2 不满足即不注入)。
> 快照:`2026-06-12-l4-guard-witch-coord-prompt-v4-metrics.json`(含 per-game 明细 + l4_guard 当前度量代码重算全键对照)。

## Verdict(用户裁决原文口径)

```text
verdict: FAILED_NEGATIVE
infrastructure_result: PASS
injection_result: PASS
behavior_change_result: FAIL
mechanism_result: FAIL
winrate_result: NEAR_MISS_NO_ATTRIBUTABLE_MECHANISM
production_default: DO_NOT_FLIP
canonical_guard_arm: l4_guard_v3
prompt_v4_status: archived_failed_experimental_arm
next: do not iterate witch-coordination prompt
```

**定性(用户原文)**:这不是「差一点」的阴性,而是机制主判据完全没动。注入链有效,行为层没有响应;
女巫只是把提示写进理由里,然后继续机械清药。结论记录为:
**input-side prompt guidance 无法修复女巫夜1必救 / 奶穿内耗。**

## 记分卡(spec §8)

| 判据 | 目标 | l4_guard | v4_coord | 结论 |
|---|---|---|---|---|
| 奶穿 milk_pierce_death_count(主) | 12 → ≤5 | 12 | **12** | ❌ 纹丝不动 |
| 狼胜(主) | ≤65% | 68.2% | **65.9% (27/41)** | ❌ 差 0.85pp;**不归因**(奶穿未降,改善更像 API 非确定/有效局构成/路径噪声) |
| L4 五主判据不回退(原门限) | 仍过 | — | 预死 56.1↓ / 报验后生存 78.8↑ / 验狼跟投 60.0 / 验狼局投预 26.7 / 方向门过 | ✅ 5/5 |
| witch_save_rate 塌陷门 | ≥0.3 | 1.0 | **1.0** | ✅(但 = 零移动,guidance 无任何行为效应) |
| witch_save_night1_share(观察) | 打破机械夜1救 | 1.0 | **1.0** | ❌ 未打破 |
| 幻觉 | ≤5% 不回退 | 2.96%/4.55% | 发言级 1.57% / 机制 0% | ✅ |
| 不变量 | 0 违例 | — | **0/45(I1-I8c)** | ✅ |

**不给 partial/pass 的理由(用户裁决)**:狼胜 65.9% 的改善不能归因到设计目标——奶穿没降、女巫行为没变。

## 机制诊断(本批最有价值的发现)

- **注入链全程工作**:45/45 夜1注入,r≥2 条件门正确(亲证 game 000:r1 带、r2 不带)。
- **行为层零响应**:女巫 reason_summary 反复出现「同守同救风险低/概率低」「守卫应该不会守他」——
  读了提示、把奶穿风险写进推理,然后**每局照样夜1清药**(合理化,不弃药)。
- 奶穿 12 局与 l4_guard 重叠 6 局(006/011/016/022/030/038)、各异 6 局:API 非确定重排了
  哪些局穿,但总数恰好相同。
- 与 B 系列教训同构:prompt 层 guidance 对「机械必救」强先验行为已到边际。

## 收口归因分析(离线,不打 API;cap=4 裁决依据)

| 问题 | l4_guard (30 村败) | v4_coord (27 村败) |
|---|---|---|
| Q1 败局终结轮分布 | r1:6 / r2:21 / r3:3 | r1:6 / r2:21 / **r3:0** |
| Q2 败局触达 max_day_rounds=3 | 3/30 (10%) | **0/27** |
| Q2b fail-closed 触顶局(已剔) | 0 | 1 |
| Q3 cap=4 能多出一个白天的局 | ≈3 | ≈1(且是 fail-closed 局) |
| Q4 奶穿局胜负 | 狼 9 / 村 3;穿在 n1×6 / n2×6 | 狼 9 / 村 3;穿在 n1×6 / n2×6 |
| Q5 夜1刀 p1 | 24/44 (54.5%) | 22/41 (53.7%);p1+p3 合计 ~76% |

**结论:cap=4 没有客户群**——两臂村败 90%+ 在第 1-2 轮就被早期 parity 收割,几乎没有局活到 cap
生效的边界。败局大头由夜1行为(必救/必刀低序号)与位置偏置(L3)解释,不是「差一轮翻盘」。

## 处置(用户裁决)

```text
① 判 FAILED 收口;
④ 协调线到此为止,不再迭代 prompt_v4;
暂缓 ② cap=4 —— 保留 backlog,且本归因显示其前提(败局触顶)不成立,事实性搁置;
不做 ③ 规则变体/夜序信息干预。
```

- **当前最佳结构臂回到 l4_guard(prompt_v3)**:status=ACCEPTABLE_PROGRESS,canonical guard
  structure arm(预言家生存机制已修复;胜率近强通过线、不翻默认)。
- prompt_v4:archived_failed_experimental_arm。代码与 golden/ledger 锁保留(高质量阴性结果的
  可复现档案),不删除、不迭代。`PROMPT_VERSION` 仍 prompt_v1,默认板不动。
- 原始 45 局保留主树 `.runs/ablation/l4_guard_witch_coord/`。
- 实验纪律重申(用户原文):不能把失败的 prompt arm 偷偷变成默认;平台价值 = 可配置、可审计、
  可复现的实验,不为过胜率门随手改规则。
- 残留课题(四臂+本臂未解,另立):女巫毒0(P8)、夜1位置偏置(L3)。下一刀的取舍
  (L3 或其他)等用户下一次裁决;本归因数据指向 L3 的解释力最大。

## 开销

1225+ 请求 / ~1.39M tokens(prompt 1.28M + completion 0.11M)/ ~35 分钟(deepseek-v4-flash,串行)。
v4 注入增量 <1%(只在守卫板女巫夜带刀口且解药未用时注入)。

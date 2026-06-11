# SYS-B4 Claim Ledger + Vote Scaffold (prompt_v3) — Experiment Verdict

> 2026-06-11,用户裁决。实验:b4 臂(prompt_v3)45 局 vs baseline(prompt_v1)/ b1(prompt_v2),配对 seed 1000-1044。
> 有效性:**n_valid=40**(1 局低 live + **4 局被 `scaffold_coverage<0.5` 臂纯度门剔除**——门首战起效);有效局 coverage 均值 0.938;45 局产物全过不变量 I1-I7+I4b(0 违例)。
> 快照:`2026-06-11-b4-prompt-v3-metrics.json`(含 per-game 明细 + scaffold_coverage)。

## Verdict(用户裁决)

| 维度 | 结论 |
|---|---|
| infrastructure | **PASS**(scribe 链路/coverage 门/turns 分列/golden+ledger 全链路) |
| mechanism | **PASS**(声称账本 + 投票脚手架可证地修复了瞄准的失败链) |
| gameplay outcome | **PARTIAL PASS**(失败链砍半;胜率方向门未达) |
| production default | **DO NOT FLIP**(`PROMPT_VERSION` 保持 `prompt_v1`) |
| next | **Layer 4 板子结构**(预言家存活/板子平衡);**不再继续调 B4 prompt** |

## 处置

- **prompt_v3 保留为实验臂 `b4_scaffold`**(arm 可选,golden 字节锁 + ledger 哈希守卫防静默改动);v1 默认、v2 冻结、v3 保留——三链共存。
- 后续 Layer 4 工作在新会话开启(用户安排),其消融对照可直接复用本度量台与三臂快照。

## 判据记分卡(spec §6)

| 判据 | 目标 | b1 | b4 | 结论 |
|---|---|---|---|---|
| 真预言家被投率(主判据) | <30% | 70% (14/20) | **35.3% (6/17)** | 砍半,差 1 局达标 |
| 验狼跟投 | ≥60% | 30% | **52.9%** | 未达,超 baseline(50%) |
| 狼胜(方向门) | ≤65% | 93.3% | **87.5%** | ❌ 仍高于 baseline 77.8% |
| 视觉幻觉发言率 | ≤5% 不回退 | 2.45% | 2.47% | ✅ |
| 机制幻觉局率 | ≤5% 不回退 | 2.2% | 5.0% | ✅(门内) |
| live/解析不退化 | — | — | 正常(coverage 门兜底 4 局) | ✅ |
| 不变量 | 全绿 | — | 0/45 违例 | ✅ |

其他:day2 命中 28.6%→45.5%;herding 0.617(续降=更独立);视觉幻觉局率 11.1%→5%。

## 解读(per-game 明细)

脚手架修好了它瞄准的链:验狼局村庄不再处决自己的预言家(70%→35.3%),day2 决策质量翻身。**瓶颈转移**:预言家 40 局死 33 局(被夜刀 15 + 被票 20),day1 命中仍 32.5%——day1 信息天然太少,预言家一报验即成夜刀首选,2 狼在 3 轮上限内靠 parity 收官。**这不再是"村庄不会用信息"(B4 已修),而是"信息到得太晚 + 预言家存活结构"= Layer 4 课题(守卫类角色/轮数上限/板子规模),prompt 层已到边际。**

开销:1016 请求(含 56 scribe)/ 977K completion tokens / 40 分钟。三臂完整对比表见快照与 `2026-06-11-b1-context-repair-VERDICT.md`。

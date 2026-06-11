# SYS-B1 Context Repair (prompt_v2) — Experiment Verdict

> 2026-06-11,用户裁决。实验:b1 臂(prompt_v2)45 局 vs baseline(prompt_v1)45 局,配对 seed 1000-1044,两臂 n_valid 均 45/45。
> 快照:`2026-06-11-baseline-prompt-v1-metrics.json` / `2026-06-11-b1-prompt-v2-metrics.json`(b1 含 per-game 明细行)。

## Verdict

| 维度 | 结论 |
|---|---|
| infrastructure | **PASS**(度量台 + v1/v2 共存渲染链 + golden/ledger/不变量全链路) |
| hallucination repair | **PASS**(视觉幻觉发言率 12.4%→2.45%,判据 <5% 达成;机制幻觉局率 11.1%→2.2%,无复述膨胀) |
| gameplay outcome | **FAIL / REGRESSED**(狼胜 77.8%→93.3%,+15.6pp 与判据反向;day1 命中 42→31%;验狼跟投 50%→30%) |
| production default | **DO NOT FLIP**(`PROMPT_VERSION` 保持 `prompt_v1`) |
| next | **SYS-B4 Claim Ledger + Vote Scaffold** |

## 处置

- **prompt_v2 冻结为实验臂 `b1_context_repair`**:不允许静默修改(golden 字节锁 + ledger 哈希守卫强制);仅经 `--prompt-version prompt_v2` 显式选用。
- **不跑 v2-lite**(纯规则卡/纯发言子消融):幻觉修复已被证有效,胜率反向已暴露 B4 缺口;继续调 prompt 是局部最优,不解主问题。若 B4 落地前需要公开演示再临时评估。
- 任何 v2 派生版本不得提前翻默认;B4 完成后注册新版本(如 `prompt_v3` / `b4_scaffold`)。

## 根因(per-game 明细,非推测)

预言家验到狼的 20 局中,**14 局 day1 多数票把真预言家自己投出**;预言家被票死 21 局 > 被夜刀 15 局。机制链:speech v2 的判别指令("报验者可能是假冒,用对跳检验,勿默认相信")同时发给全桌——双狼协同悍跳(对跳)更锋利,而村民被要求怀疑却**没有声称区/结构化对跳信息可供分辨**(声称区当时按 spec 裁决刻意砍掉留给 B4),均匀怀疑落在孤证的真预言家上。2 狼协同 > 1 预言家。

**数据印证原诊断:根因层是村庄智能(SYS-B4 脚手架),纯上下文修复(SYS-B1)够不着胜率。**

## B4 硬约束(用户裁决,写入下一份 spec)

```
B4 不改变 action 响应机器契约。
vote / night action 仍然输出既有 strict-JSON。
不得要求模型输出"推理段 + JSON 尾"这种会影响解析链的格式,除非 action_runtime 明确支持并有测试。
脚手架优先放在输入侧:observation_text / structured context / system guidance。
如果确实需要中间推理产物,必须作为独立 scaffold artifact 或 pre-action note,不得混入 action JSON 响应。
```

理由:B1 工程风险可控的关键正是"只动 speech/观察文本/规则卡、不碰 action JSON 契约"。B4 若动 vote action 而不钉死契约,解析失败率会污染 `live_success_rate` 和全部行为指标,届时分不清是模型变笨、脚手架变差还是 JSON 解析坏了。

## 完整对比表

| metric | baseline | b1 | delta |
|---|---|---|---|
| n_valid | 45 | 45 | — |
| wolf_win_rate | 0.778 | 0.933 | +0.156 |
| villager_win_rate | 0.222 | 0.067 | -0.156 |
| day1_hit | 0.422 | 0.311 | -0.111 |
| day2_hit | 0.500 | 0.286 | -0.214 |
| verify_wolf_followed | 0.500 (n=18) | 0.300 (n=20) | -0.200 |
| witch_save_rate | 0.933 | 1.000 | +0.067 |
| witch_poison_rate | 0.000 | 0.000 | 0 |
| herding | 0.719 | 0.678 | -0.041 |
| halluc_visual_speech_rate | 0.124 | 0.025 | -0.099 |
| halluc_visual_game_rate | 0.356 | 0.111 | -0.244 |
| halluc_mechanic_game_rate | 0.111 | 0.022 | -0.089 |
| seer_survives_d1_rate | 0.733 | 0.578 | -0.156 |
| avg_rounds | 2.156 | 2.244 | +0.089 |

开销:b1 996 请求 / 1.14M completion tokens / 57 分钟(baseline 1024 / 779K / 41 分钟;增量主因=规则卡 per-request 前缀 + 更长发言)。

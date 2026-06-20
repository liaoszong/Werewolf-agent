# 设计:质量消融度量台 + SYS-B1 Layer-1 上下文修复

> **类型**:design spec(待用户 review → 再写 implementation plan)
> **来源**:`historical harness review 2026-06-10-live-quality-diagnosis.md`(已 commit `75d8363`)。
> **范围由用户锁定(2026-06-10)**:首份 spec = **可复现消融度量台** + **SYS-B1 Layer-1 上下文修复**(作为第一个干预臂)。**不含** SYS-B4 脚手架、女巫 ②b ledger、候选/座位随机化、板子平衡。
> **目标不是直接平衡胜率**,而是:① 建成可复现实验 harness;② 用最高置信的上下文修复作首个干预臂;③ 验证指标链是否改善。

---

## 1. 目标与非目标

**目标**
1. **消融度量台**:给定一个"实验臂"(arm = 一组 prompt/上下文配置),自动跑 N 局 live、按 `live_success_rate` 过滤、`budget_exhausted` hard fail,产出 §6 诊断指标的聚合,并支持多臂对比。
2. **SYS-B1 Layer-1 上下文修复**:规则卡 + 结构化公共状态 + 发言表态,作为第一个干预臂。
3. **实验协议**:在 harness 上**重打 baseline**(旧 45 局只作 v0 参考),再跑 B1 臂,出 delta。

**非目标(明确排除)**
- SYS-B4 脚手架(投票前结构化推理、狼频道、发言-投票一致性硬约束)。
- 女巫 ②b CapabilityLedger / `allowed_actions` 递减(P9 修复留后)。
- 候选/座位顺序随机化(Layer 3)。
- 板子平衡 / 加角色 / 改回合数(Layer 4)。
- LLM-judge 式发言质量评分(本期用关键词近似,够用即可)。

---

## 2. Part A — 消融度量台

### 2.1 位置与形态
新增模块 `src/werewolf_eval/ablation/`:
- `harness.py` — 跑一个 arm 的 N 局 + 落盘 + 调用 metrics。
- `metrics.py` — **纯函数**:吃一个 run 目录列表,出聚合指标 dict(无副作用、可单测)。
- `arms.py` — arm 配置定义(label、**`prompt_version: "prompt_v1" | "prompt_v2"` 选择器**、模型、局数、seed 基)。`prompt_version` 是**运行时机制**(穿进 runner,照 `seat_roles` 的穿线方式选渲染路径);`PROMPT_VERSION`/ledger 是**记账**(manifest 戳每局实际版本)。两者合用,见 §3.4。
- CLI `python -m werewolf_eval.ablation run <arm> [--n 45] [--model ...]` 与 `compare <armA> <armB>`。
- 产物落 `.runs/ablation/<arm>/<game_id>/`(gitignore),聚合写 `<arm>/_metrics.json`。

> 复用诊断期 `.tmp/diag_*` 的全部经验,但**产品化**:每局新建 provider、live 率过滤、hard fail、确定性 seed。

### 2.2 硬性设计约束(诊断期踩坑固化为契约)
1. **每局新建 provider**:`_deepseek_factory` 的共享 provider 带 64 次预算,跨局复用会耗光 → 后续局静默兜底 RNG。harness **每局新建**。
2. **`budget_exhausted` = hard fail**:任何一局触发预算耗尽 → 该局标记 invalid,不进聚合,并在汇总里显式计数(沿用 P2-A-2 验收口径)。
3. **live 率过滤**:每局算 `live_success_rate`,`< 阈值(默认 0.7)`的局**剔除**且计数。**绝不**把兜底局混进行为指标(诊断期首批 44 局只有 6 局真 live,差点得出全错结论)。
4. **诚实链**:沿用 G3-3 — `source_label == "[DeepSeek API output]"`、manifest 记真实 model、`token_usage>0`。
5. **配对 seed(降方差)**:**所有臂共用同一 seed 序列**,逐局配对(同 `index` → 同布局/洗牌)。seed `= seed_base + index`,`seed_base` **全局固定、非 per-arm** → 做配对比较,45 局/臂小样本下是免费的统计功效。
6. **预算**:单局 `max_requests = 80`(实测一局 ~19–23 次请求,留 ~3× 余量,够 3 回合局);批次**不设总预算上限**(deepseek-v4-flash 极廉,45 局 ~836 次请求 ≪ 用户额度),但每局触发 `budget_exhausted` 仍 hard fail 并计数。
7. **确定性边界**:温度 0.8 + API 本身非确定 → seed **只保证布局/洗牌可复现,不保证对局逐字可复现**;验收时勿据此误判 harness 坏。

### 2.3 指标(metrics.py 输出,全部从 artifacts 只读计算)
| 指标 | 定义 | 诊断 v0 参考 |
|---|---|---|
| `wolf_win_rate` | 狼胜 / 有效局 | 0.78 |
| `villager_win_rate` | 村胜 / 有效局 | 0.22 |
| `day1_hit` | day1 多数票命中狼比例 | 0.51 |
| `day2_hit` | day2 多数票命中狼比例 | 0.39 |
| `verify_wolf_followed` | 预言家夜验到狼的局中,该狼当日被多数票投出的比例 | 0.65(n=17,CI宽) |
| `witch_save_rate` / `witch_poison_rate` | 出现救/毒动作的局比例 | 1.00 / 0.00 |
| `herding` | 每轮最高票占比均值(报告**随机基线**:6投5≈0.43) | 0.72 |
| `hallucination_visual` | 含视觉破绽词(眼神/表情/紧张/躲闪/语气…)的发言比例 + 涉及局比例 | 0.20 / 22 局 |
| `hallucination_mechanic` | 含不存在机制词(警徽/警长/警上/守卫/守夜人)的发言比例 + 涉及局 | 9 局 |
| `positional_kill` | 夜1 狼刀座位分布(诊断 p1=58%) | — |
| `live_rate_mean` / `invalid_games` / `roundcap_fail` | 有效性指标 | 0.92 / — / 0 |
| `avg_rounds` | 平均结束回合 | — |

- 关键词表(visual/mechanic)放 `metrics.py` 常量、**可配置**;承认是近似,文档标注。
- `compare` 输出两臂并排 + delta + 简单显著性提示(小样本只给区间感,不做正式检验)。
- **v0 参考列来源**:= 诊断报告 §2 表,全部由 `.tmp/diag_analyze.py` 计算;其中 `day2_hit=0.39` / `witch_save_rate=1.00` 为补算后已写入报告 §2(非凭空引用)。harness 的 baseline 臂会重新产出这些,v0 仅参考不作正式对照。

### 2.4 测试
- `metrics.py` 纯函数:用 `tests/fixtures/` 里 2-3 个**保存的 run 目录**(从诊断期挑:1 村胜 + 1 狼胜 + 1 含幻觉词)做单测,锁定每个指标的期望值。
- **fixtures 脱敏复查**:真 API 产物入 `tests/fixtures/` 前必须过一遍脱敏(沿用 Plan-A 的 trace 脱敏),确认无 key / 无敏感串——**提交即永久**。
- harness 的跑局逻辑:`fake-deterministic` 模式下跑 2 局冒烟(不碰 key),验证落盘 + 聚合不崩;live 路径不进 CI(opt-in)。

---

## 3. Part B — SYS-B1 Layer-1 上下文修复(首个干预臂)

> 三处改动都在 prompt/上下文构建层,**踩 prompt_v1 字节锁** → 全部走 `PROMPT_VERSION` bump + golden 更新 + ledger 记录(版本化基建的第一个真客户)。

### 3.1 规则卡(rules card)注入每个 prompt —— **数据驱动,不写死**
- **内容必须从数据生成,严禁硬编码"6人=2狼…"**:猎人板 `rules_v1_1` 已存在(`action_runtime/ruleset.py:67`),洗牌局 seat 构成可变。写死会给猎人局发错卡 = **P4 幻觉的镜像错误**(我们亲手塞一张不符本局的规则表)。
- **数据源**:`BoardRuleset(rules_version)` —— 单一来源(`.roles` 给每角色 team + abilities,`.rules_version`)+ `Counter(seat_roles.values())` 给本局构成。卡内容 = 角色清单(谁能做什么:验人=预言家、救/毒=女巫…)+ 构成计数 + 胜负/**parity** 规则 + 显式声明:"纯文字推理局,无任何表情/眼神/语气等视觉信息,**不得据此推断**。"
- **落点(穿线)**:`compose_system` 现在只拿 persona + contract,**`ProviderRequest`/observation 里没有板子构成**。需把"板子摘要"数据线穿进 provider 层(照 `seat_roles` 的穿法:engine 侧从 `BoardRuleset`+`seat_roles` 算出 `board_summary`,放进 `ProviderRequest`,`compose_system` 拼入)。spec-plan 须明确这条穿线。
- 直接打 **P3(看脸幻觉)+ P4(机制幻觉)**。

### 3.2 结构化公共状态摘要(替代裸事件流)—— **首版降级:砍掉"声称区"**
- 落点:`emergent_engine.py:render_observation_text`(及 `_build_obs` 渲染线)。
- 现状:只给"你是谁 + 存活名单 + 可见事件流(无说话人标签、私有信息第三人称混在一坨)"。
- 改为**结构化分区**呈现(全部仍只用该 seat 的可见集):
  - **你的私有信息**(你的角色 + 你的历史动作/验人结果)单列、突出。
  - **公开事实**:死亡名单、出局者(若该变体公开真身则含)。
  - **发言**:**带说话人标签、按顺序**(修早前 40ff0a32 的"无主语一坨→误认"问题)。
  - **投票矩阵**:历史每轮谁投谁。
- **首版明确砍掉"声称区"(谁声称什么角色/报什么验)**:引擎**没有结构化 claim 事件**,claim 只活在自由文本里。三条路:(a) 正则提取 → **假阳性会把错误声称以"结构化权威"形态注入全桌 prompt,比没有更糟**(诊断期正则刚闹过两个假阳性);(b) 让模型发言附结构化 claim → 那是 **B4 脚手架,本期 out**;(c) **降级:不做声称区**。**选 (c)**,声称区列 follow-up(等 B4 的结构化发言)。
- **P5 修复主力不依赖声称区**:靠 §3.1 规则卡的**能力表**(验人=预言家、救/毒=女巫)+ **带标签发言**即可消解"预言家救完人还能验人?"式混乱;降级不伤打击面。
- 直接打 **P5(角色能力归属混乱)**,并为 **P2(信息锚定)** 铺路。

### 3.3 发言 prompt 升级
- 落点:发言 prompt 路径(`llm_providers.py` 发言系统 prompt,现仅 4 句)。
- 要求:对场上**硬信息**(预言家报点 / 验人结果)**明确表态**信 / 不信 + 理由。
- 注意:**不写"相信预言家"**(狼悍跳同样受益),而是给"如何用对跳 / 反验来证伪"的**判别结构**,让村民有分辨力而非新先验。打 **P6**。

### 3.4 不变量约束 + v1/v2 运行时共存(必须守住)
- **v1 渲染器在 v2 落地后必须保留**:`PROMPT_VERSION` bump 的语义是"替换当前版本",但**消融要求 baseline 臂在 B1 合并后永远可跑**(否则下次加 L3 臂就没对照了)。因此:
  - **两套渲染路径(prompt_v1 / prompt_v2)运行时共存**,由 arm 的 `prompt_version` 字段选择(§2.1)。
  - **两套各有 golden 守卫**:v1 路径继续被原 14 golden 锁(防漂移),v2 路径新增自己的 golden。
  - manifest / ledger **戳每局实际用的版本**。
- **I4b 可见性**:结构化摘要**只能**含该 seat 可见集(public_event_ids ∪ private_event_ids)。规则卡 = 公共,合法;**绝不**把他人私有结果作为真值注入。
- 安全网 `src/werewolf_eval/invariants/` 7 不变量 + I4b oracle 跑 arm 产物须**全绿**(改了渲染,必须复跑)。
- 字节锁:v2 走 `PROMPT_VERSION` bump + golden regen + ledger 条目 + 3 CI 守卫绿;**v1 golden 保留不动**。

---

## 4. 实验协议

1. **Arm-0 baseline**:当前 prompt,~45 局,harness 重打(**旧 45 局不作正式对照,仅 v0 参考**)。
2. **Arm-1 b1-context**:3.1–3.3 三处合并为一个干预臂(Layer-1 概念上是一个干预)。
   - 若 Arm-1 显著改善,可后续**子消融**(单独 rules-card / 单独结构化状态 / 单独发言)定位贡献——列为 follow-up,非本期。
3. 每臂 ~45 局,live 率过滤,budget_exhausted hard fail。
4. **成功判据(方向性,非验收硬门槛)**:幻觉率 20%→<5%、验狼跟投 65%→85%、day1 命中 51%→65%+;按乘法模型 → 村胜 40–50%。
5. 建议附跑 3–5 局**强模型(非 flash)**做天花板标定:若强模型村胜也 <30%,说明结构占比更大,Layer-4 要提前。

---

## 5. 组件边界与数据流

```
arms.py (arm 配置)
   │
   ▼
harness.run(arm) ──每局──▶ run_emergent_deepseek_game(每局新建 provider, seed)
   │                              │
   │                         .runs/ablation/<arm>/<gid>/ (artifacts)
   ▼                              │
metrics.aggregate(run_dirs) ◀─────┘  (纯函数, 只读 artifacts, live率过滤)
   │
   ▼
<arm>/_metrics.json  +  compare(armA, armB) 表
```
- **harness** 只管编排与有效性门禁;**metrics** 只管只读统计;两者解耦、各自可单测。
- Part B 改的是引擎/provider 的 prompt 渲染,**不动** harness/metrics 接口。

---

## 6. 风险与未决

1. **结构化公共状态(3.2)是最高风险改动** —— 触碰 observation 渲染,必须保 I4b + 安全网全绿;建议 TDD,先写"渲染来源 ⊆ 可见集"的断言。
2. **关键词幻觉检测是近似**(可能高/低估);本期接受,未来可换 LLM-judge,接缝在 metrics.py。
3. **字节锁流程成本**:v2 prompt 须走 PROMPT_VERSION bump + golden regen,v1 golden 保留;设计内必经路径,非阻塞。
4. **小样本**:45 局/臂,指标含噪(如 verify-wolf-followed CI 宽);配对 seed(§2.2)降方差,但关键结论仍需加大样本或多臂复现。

### 已裁决(2026-06-10 user review)
- **harness 位置 = `src/werewolf_eval/ablation/`**(harness import runner、metrics 进 CI 单测,放包内最顺;tools/ 平添 import/PYTHONPATH 麻烦无收益)。
- **arm 切换 = `prompt_version` flag(机制)+ PROMPT_VERSION/ledger(记账)合用,v1/v2 渲染器运行时共存**(§2.1 + §3.4)。
- **§3.2 声称区首版砍掉**(降级方案 c),列 follow-up。
```


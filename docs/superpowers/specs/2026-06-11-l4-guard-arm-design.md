# Layer 4 守卫臂(l4_guard)设计 — 6p 保护型结构替换实验

> 2026-06-11。承接 SYS-B4 verdict(`docs/harness/reviews/2026-06-11-b4-scaffold-VERDICT.md`):
> prompt 层已到边际,瓶颈转移为「信息到得太晚 + 预言家存活结构」(预言家 40 局死 33:夜刀 15 + 被票 20)。
> 用户裁决:Layer 4 第一臂 = 守卫角色;轮数上限(cap=4)留作第二批,视本臂结果再定;不做板子规模扩张。
> 用户终审口径:ACCEPTED_WITH_SPEC_REQUIREMENTS(8 条硬边界,已全部钉入本 spec)。

## 1. 一句话定义

新增保护型角色 **守卫(guard)**,以 **6p 替换臂**(2狼 + 预言家 + 女巫 + 守卫 + 1民,换掉一个普通村民)跑在
**prompt_v3(b4_scaffold)+ rules_v1_2 + cap=3** 上,45 局配对 seed 消融,验证「保护型结构是否打开预言家生存窗口」。

**解释纪律(用户要求)**:该板子减少了普通村民数量,因此 guard arm 不得被解释为「只增加保护能力」,
必须解释为「6p 保护型结构替换臂」。分析与 verdict 中禁止出现「只多了守卫」式归因。

## 2. 守卫规则细则(标准规则,用户已裁决)

| 规则 | 取值 | 理由 |
|---|---|---|
| 可自守 | ✅ | 守卫不退化为纯辅助 |
| 不可连续两晚守同一人 | ✅(硬验收) | 防「预言家跳验后贴脸永守」退化策略导致实验失真 |
| 守护成功反馈 | ❌ 无 | 不注入额外信息;守卫只能从白天公告(平安夜)间接推断 |
| 必须守人 | ✅(无 guard_pass) | 每夜有明确 intent,便于 JointSettler 与指标统计 |
| 奶穿 | 守+救同一目标 → 死 | 规则表 `guard+save_same_target: death` 已预埋,settler 已消费 |

不可连守的硬验收文本(用户原文):

```text
Guard cannot protect the same target on consecutive guard nights.
Invalid consecutive protect must be rejected by target rule and fall back deterministically.
```

**状态最小化(用户硬边界)**:不可连守状态只属于 guard 的能力状态,用最小 `last_guarded_target`
每局内联状态(女巫 one-shot 内联先例,见 `emergent_engine.py:85-89` 注释)。
**禁止**为它提前实现完整 CapabilityLedger(②b 大工程,本 spec 不认领)。

兜底:guard 决策失败/非法时,确定性兜底从合法目标集(存活 − 上夜所守)中按既有 per-game RNG 规约取目标
(沿用「兜底 RNG 每局新建」纪律,不复用跨局 provider 预算对象)。

## 3. Rules 层 — `rules_v1_2`(append-only superset)

仿照猎人先例(`rules_v1_1`,「加角色=加数据」):

- 新函数 `rules_v1_2()` = `rules_v1_1()` + guard。**`rules_v1_1` 函数一字不动。**
- 角色:`RoleDefinition("guard", "villager", ("guard_protect", "player_vote"))`
- 能力:`AbilityDefinition("guard_protect", "phase:night", "exclude_last_guarded", ARITY_ONE, "guard")`
  - `exclude_last_guarded` 是新 target rule:存活 ∧ ≠ 上一守卫夜所守目标(含义上允许自守)。
  - 该规则依赖每局状态;v1 实现允许由 guard resolver 内联执行合法集计算与校验
    (女巫不进 `validate_in_state` 的同款理由),但 ruleset 数据中必须如实声明规则名,
    且拒绝 + 确定性兜底为硬验收(§2)。
- `all_rulesets()` 追加 `rules_v1_2()`(append-only 契约不变)。
- 夜规则表:`guard+save_same_target: death` 已在 v1 表中,v1_2 继承,无新键。
- JointSettler:**零改动**(`settler.py:46-53` v1.5 guard 路径已实现),只需引擎把
  `guard_target` 穿进 `NightIntents`(字段已预留,`settler.py:16`)。

**默认不翻(用户硬边界)**:

```text
rules_v1_1 不动。
默认板仍走现有规则/构成(2狼+预+女巫+2民,CANONICAL_MULTISET 不变)。
l4_guard arm 显式选择 rules_v1_2 + guard board。
```

引擎 `emergent_engine.py:302` 的 ruleset 引用从 `rules_v1_1()` 升至 `rules_v1_2()`,
合法性同猎人先例:**无 guard 的板子在 v1_2 下行为字节恒等**,由现有
`test_allowed_actions_pinned` + 确定性 canary 扩展钉死(§9 验收)。这不构成默认行为漂移:
默认板不含 guard,不产生任何 guard 路径。

## 4. 引擎接线(最小面)

- `NIGHT_DISPATCH_ORDER`(`emergent_engine.py:90`)→ `("guard_protect", "werewolf_kill", "seer_check")`,
  新增 `_run_guard` resolver(`_run_seer` 同款模式)。守卫先行;结算为 joint,夜序只影响展示与哨兵,
  **女巫看到的夜刀受害者仍为狼队原始目标**(守卫是否挡刀对女巫不可见 → 奶穿可发生,标准规则)。
  SYS-A2 夜序哨兵需同步加 guard 行。
- 夜间结算调用处把 `guard_target` 传入 `NightIntents`(`emergent_engine.py:1145`)。
- 守卫挡刀成功 → `deaths` 为空 → 走现有「A peaceful night」公告路径(`:1168`),**零新渲染逻辑**。
- 已知名单面(用户硬边界,直接入 allowlist,不留到 plan 阶段):
  - `profile_config.ALLOWED_ROLES`(`profile_config.py:53`):加 `"guard"`。**不加 hunter**(它现在就不在,保持)。
  - `observer_visibility._KNOWN_ROLE_TEAMS`(`observer_visibility.py:19`):经 observer_protocol 从
    `known_role_teams()` 联集派生,`all_rulesets()` 追加后自动覆盖 guard;以哨兵断言确认,不手改副本。
- 观察/词汇:guard 中英词汇 i18n(SYS-A2 词汇哨兵 ×6 加行);`guard_protect` 事件
  `visibility="guard"` 私有;R-17 visibility 不变量守卫覆盖新事件类型。

## 5. 板子构成与臂配置

- `arms.py`:`Arm` 增加可选 `multiset` 字段,缺省 = `CANONICAL_MULTISET`(现有臂布局逐字节不变);
  `l4_guard` 臂用 `("werewolf", "werewolf", "seer", "witch", "guard", "villager")`。
- `layout_for` 配对语义:同 index → 同 seed → 同洗牌;guard 臂 multiset 不同,布局与三臂不可能逐座位相同,
  **配对 = seed 配对**(同 RNG 流),verdict 中按此口径解读,不声称座位级配对。
- 臂参数:`label="l4_guard"`, `prompt_version="prompt_v3"`, `n_games=45`, `seed_base=1000`,
  `max_day_rounds=3`(不动),DeepSeek 同 b4(scribe scaffold factory 必带,harness 已强制)。

## 6. Prompt 面 — 只动 v3,v1/v2 零触碰

- 给 `prompt_v3` 补:guard 角色能力说明、claim ledger 词汇(守卫声称/守护宣称)、vote scaffold 能力表 guard 行、
  规则卡板子构成行(guard 板)。
- **v1/v2 字节零触碰**:guard 不进那两条链的板;v1 golden 14 样本 + v2 冻结链 + 现有 v3 golden 全部字节不动,
  只**新增** guard 板 v3 样本入 golden 锁 + ledger 哈希。
- **visibility 硬门(用户硬边界)**:guard 私有信息(守卫身份、守护目标、`guard_protect` 事件)
  不得进入其他 seat 的 claim/vote scaffold。P2-A-2 硬门仍适用:prompt 只能由该 seat 可见事件渲染,
  渲染来源必须是可见事件子集,**喂漏 = 阻断性 bug**。scribe(全知豁免面如有)沿 b4 既有边界,不扩。
- 全程走 `guarding-prompt-bytes` skill;`PROMPT_VERSION` 不翻(默认仍 `prompt_v1`)。

## 7. 指标与不变量

新增指标(度量台扩展,数据源:decision-log + scribe claim ledger 产物 + game-log):

```text
guard_target_seer_rate          守卫守预言家的比例(守卫夜次分母)
guard_success_rate              守护目标正好挡刀的比例(守对率)
seer_claim_to_night_survival_rate  预言家公开报验(claim ledger 检出)后存活到下一天的比例
```

保留既有:预言家被刀数/被票数、平安夜数、真预言家被投率、验狼跟投、herding、幻觉率、coverage。

不变量 I8 拆两分支(用户硬边界,防「非奶穿」写成含糊条件):

```text
I8a: 若 night kill target == guard target,且没有 witch save 造成奶穿,
     则该 target 不产生 player_died / role_revealed 死亡链。
I8b: 若 night kill target == guard target 且 witch save 同时作用于该 target,
     则按奶穿规则死亡。
```

另加守卫自身硬验收:I8c(命名延续):任意两个**连续**守卫夜的 guard_target 不相同(产物级断言)。
I1-I7 + I4b 照常全跑;coverage 门(`scaffold_coverage<0.5` 剔局)沿用。

## 8. 判据(用户裁决口径)

```text
主判据:
- 预言家公开报验后夜间死亡率显著下降
- 预言家总死亡率下降(b4 基准 33/40)
- seer_claim_to_night_survival_rate 上升
- 验狼跟投不低于 b4(52.9%)
- 真预言家 day1 被投率不回退(b4 基准 35.3% 总被投率口径,day1 分量单列)

方向门:
- 狼胜率较 b4 87.5% 显著下降
- ≤65% 为强通过
- ≤75% 且主判据明显改善为可接受进展(不判死,下一步 = cap=4 第二批)

不回退门:
- 视觉/机制幻觉 ≤5%
- live 率与解析不退化
- 不变量(I1-I7、I4b、I8a/b/c)0 违例
```

狼胜 ≤65% **不作为唯一硬失败**:若守卫保住预言家但狼胜仅降至 ~70%,定性为有价值的结构改进,进入 cap=4 批次。

## 9. 测试与验收

- 字节恒等:无 guard 板在 rules_v1_2 下与 v1_1 字节恒等(确定性 canary + `test_allowed_actions_pinned` 扩展)。
- 哨兵:夜序、词汇 ×6、闸门、冷启动(ColdImportTest,A2 循环 import 坑)全部加 guard 行。
- settler 单测:I8a / I8b 两分支显式用例(奶穿规则表读取路径)。
- 连守:拒绝 + 确定性兜底用例;night1(无上夜目标)全存活合法含自守。
- visibility:guard 私有事件不进其他 seat 渲染源(R-17 守卫扩展);scaffold 输入面审计用例。
- golden:v1 14 样本 + v3 现有样本字节不动(CI 守卫);新增 guard 板样本入锁。
- 全量回归:`PYTHONPATH=src python -m unittest discover`(基准 1107 OK)。
- live 验收:45 局,n_valid 口径同 b4(live 率 + coverage 门),快照
  `docs/harness/reviews/2026-06-XX-l4-guard-metrics.json` + verdict 文档。

## 10. Out of scope(硬边界,用户原文)

```text
不扩 7/8/9 人板。
不加入猎人默认板。
不修改 prompt_v1 / prompt_v2。
不翻 PROMPT_VERSION。
不实现完整 CapabilityLedger。
不重构 NightPlan。
不改变 action strict-JSON。
不改 max_day_rounds。
不做 L3 随机化。
```

尤其 NightPlan:A1 的 NightPlan 等第一个夜间新角色「再落地」不等于「本臂必须做完」;
本臂只做 `NIGHT_DISPATCH_ORDER` 最小扩展,夜晚系统大重构 = 越界。

## 11. 风险

| 风险 | 缓解 |
|---|---|
| 守卫太强(永久保护链)→ 实验失真 | 不可连守(硬验收 I8c)+ 奶穿规则保留狼方反制 |
| guard claim 词汇改动误碰 v3 既有字节 | golden 锁 + ledger 哈希守卫;新增样本与既有样本分离 |
| multiset 字段改动破坏既有臂配对 | 缺省值 = CANONICAL_MULTISET,既有臂布局逐字节回归用例 |
| guard 私有信息喂漏进 scaffold | §6 visibility 硬门 + 审计用例,喂漏 = 阻断 |
| 报验检测(claim ledger)误判影响主判据 | 指标定义钉在 scribe claim 产物字段上,verdict 抽样人工校验 |

## 12. 流程

spec(本文)→ plan(`docs/harness/plans/2026-06-XX--l4-guard-arm-plan.md`,独立审)→
worktree 隔离 subagent 执行 → review → 45 局 live(`running-live-games` skill)→ verdict 归档。
消融对照直接复用三臂快照与度量台(b4 verdict 处置条款)。

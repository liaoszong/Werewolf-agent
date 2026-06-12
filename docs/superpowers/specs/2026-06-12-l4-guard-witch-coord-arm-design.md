# 奶穿协调臂(l4_guard_witch_coord)设计 — prompt_v4 女巫保护协调实验

> 2026-06-12。承接 L4 守卫臂 verdict(`docs/harness/reviews/2026-06-11-l4-guard-VERDICT.md`):
> 守卫臂 ACCEPTABLE PROGRESS(主判据 5/5 过,狼胜 87.5→68.2 首次低于 baseline,强通过 65% 差 3.2pp);
> 瓶颈转移为**奶穿 12 次 = 最大保护内耗**(女巫解药使用率 100%,夜1机械必救,频繁与守卫同守同救)。
> 用户裁决:下一臂 = 女巫保护协调,**标准规则不动**(同守同救仍死——改规则会把实验从
> 「优化 AI 决策/结构」变成「改游戏规则补平衡」,后续无法解释)。
> 用户终审口径:ACCEPTED_WITH_SMALL_EDITS(4 条补充约束,已全部钉入本 spec)。

## 1. 一句话定义

新臂 **`l4_guard_witch_coord`** = 守卫板(2狼+预言家+女巫+守卫+1民)+ `rules_v1_2` + **`prompt_v4`**
(= prompt_v3 + 女巫解药协调提示,只在女巫夜间救药决策点注入)+ cap=3,45 局配对 seed 消融,
对照 l4_guard(prompt_v3),验证「女巫侧协调 guidance 能否消掉奶穿内耗、补上 68.2%→65% 的缺口」。

**配对口径升级**:本臂与 l4_guard 同 multiset、同 `seed_base=1000` → `layout_for` 产生
**逐座位相同的布局**(座位级真配对,强于守卫臂 vs b4 的「仅 seed 配对」)。两臂唯一变量 =
prompt_v4 的女巫协调提示,verdict 归因按此口径解读。

## 2. 方案选型(用户裁决)

| 方案 | 裁决 | 理由 |
|---|---|---|
| **A. 渲染器 hook + prompt_v4,女巫夜间 action prompt 专属追加** | ✅ 选 | 只改女巫一个决策点;复刻 B-1 注册表 `action_obs_suffix` 先例;不污染其他 seat;不碰锁定面 |
| B. 写进 v4 规则卡 | ❌ | 全员可见,违反「只改女巫侧」;狼也读到女巫被教导;污染全 seat 字节 |
| C. 改 `augment_witch_observation` 本体 | ❌ | v1 锁定面(`prompt_version.py` docstring 点名),动一字节须翻 `PROMPT_VERSION` |

方案 A 符合 B4 既定硬边界:脚手架优先放输入侧,不改变 action strict-JSON,不把中间推理混进 action 响应。

## 3. prompt_v4 — 渲染器注册表加版本(B-1 接缝)

走 SYS-B1 PromptRenderer 注册表路径(`src/werewolf_eval/prompt_renderers.py`),不是 b4 时代的散点 if:

- 新模块 `prompt_v4.py`:只含锁定的协调提示渲染件(文案 §4)。
- 新适配器 `PromptRendererV4(PromptRendererV3)`,`version="prompt_v4"`,`requires_scaffold=True` 继承
  (v4 臂跑守卫板 + scribe scaffold,同 l4_guard)。
- **基类新增 hook** `witch_obs_suffix(...)`:`PromptRendererV1` 返回 `""`(既有三版字节零影响,
  与 `action_obs_suffix`/`speech_obs_suffix` 同款模式);仅 V4 覆写。
- 引擎接线:`_resolve_witch`(`emergent_engine.py:760` 附近)在 `augment_witch_observation` 之后
  追加 `renderer.witch_obs_suffix(...)`。`_resolve_witch` 已持有 `victim` 与 `save_used`,直接作 hook 参数。
- `KNOWN_PROMPT_VERSIONS` 追加 `"prompt_v4"`(`prompt_version.py` 字面量;注册表哨兵
  `tuple(REGISTRY)==KNOWN` 自动覆盖)。`PROMPT_VERSION` 默认仍 `prompt_v1`,不翻。

**注入条件(用户硬边界,三连)**:

```text
board_has_guard ∧ victim != None ∧ witch_save_available(解药未用)
```

三者缺一即返回 `""`:解药已用过再提示协调没有意义,还可能干扰毒药/pass 决策;
无 victim 时没有救药决策,注入协调提示 = 噪音;非守卫板上「本局存在守卫」是假命题。

**visibility 硬门**:协调提示是**静态文本**,只派生自公开的板构成(board_has_guard)与女巫自身状态
(victim 可见性已由 R-04 `augment_witch_observation` 先例确立;save_used 是女巫私有状态)。
**禁止引用守卫真实守护目标、last_guarded_target 或任何 guard 私有运行时状态**——喂漏 = 阻断性 bug。

## 4. 协调提示文案(钉死,执行时逐字用)

```text
【解药协调提示】本局存在守卫。守卫每晚守护一名玩家;若你解药救下的人当晚同时被守卫守护,该玩家会因「同守同救」规则死亡。你无法知道守卫今晚守了谁。用药前请权衡:该目标是否很可能正被守卫保护,例如已公开跳出且被全场关注的预言家。信息不足时不要机械地夜1必救;解药整局仅一瓶,应优先用于你认为"死亡风险高、且不太可能同时被守卫守护"的目标。
```

文案纪律(用户裁决 §1):核心口径是 **「死亡风险高且不太可能被守卫同时保护」** 的风险权衡,
不用「高价值就救」措辞——高价值目标(如已跳预言家)往往正是守卫高概率守护对象,二者会撞。
guidance 只陈述标准规则下的奶穿风险与用药权衡,**不改奶穿规则,不撒谎**(女巫确实无法知道守卫目标)。
前缀换行符与拼接方式在 plan 阶段按既有 suffix 先例钉进注入单测。

## 5. 字节纪律 — v1/v2/v3 零触碰 + 两类 canary

- v1/v2/v3 golden 全部字节零变化(CI 守卫);新增 `tests/golden_prompts/prompt_v4/` 目录 +
  ledger 条目(`docs/generated-games/prompt-version-ledger.json`),全程走 `guarding-prompt-bytes` skill。
- **canary 1**:非 guard board,prompt_v4 的女巫夜间 observation == prompt_v3 逐字节。
- **canary 2**:guard board 但 `victim is None`,prompt_v4 的女巫夜间 observation == prompt_v3 逐字节。
- (plan 阶段补第三条单测:guard board ∧ victim 非空 ∧ 解药已用 → 同样恒等 v3。)
- 两类 canary 的目的(用户原话):防止 prompt_v4 变成「全局 v3+废话」。

## 6. 指标 — 奶穿计数升一等公民,拆两层

现状:`milk_pierce_deaths=12` 只是 verdict 快照里的手算 detail(`guard_mechanics_detail`),
不在 `ablation/metrics.py` 正式键里。本臂主判据要可机算,升级如下:

```text
milk_pierce_overlap_count   同守同救重叠次数(夜间 guard 生效目标 == witch_save 目标)
milk_pierce_death_count     同守同救且按规则最终死亡次数(主判据用这个)
witch_save_night1_share     解药在夜1使用的占比(观察项,不设门;验证「机械夜1必救」是否被打破)
```

拆 overlap/death 两层的理由(用户裁决 §4):若后续 settler/规则变体或事件链有差异,
能分清是「重叠少了」还是「死亡结算变了」。本轮不改规则,两值应恒等——不等即结算异常,verdict 须解释。
数据源:decision-log + game-log(同 I8b 不变量的判定输入);guard 目标取**实际生效目标**
(含兜底,沿 l4_guard spec §2 口径)。**分母口径:同其余 metrics 键 = n_valid 过滤后集合**
(l4_guard 为 44 局;回算门 §11 的「复现 12」按此口径核对)。

保留既有全键:`witch_save_rate` / `witch_poison_rate` / guard 族 / seer 生存族 / 幻觉 / coverage。

## 7. 臂配置与运行

- 臂参数:`label="l4_guard_witch_coord"`, `prompt_version="prompt_v4"`, `--board guard`,
  `n_games=45`, `seed_base=1000`, `max_day_rounds=3`(不动),DeepSeek 同 l4_guard,scribe 必带。
- 运行命令(T-live,用户触发,走 `running-live-games` skill):

```text
PYTHONPATH=src python -m werewolf_eval.ablation run l4_guard_witch_coord --prompt-version prompt_v4 --board guard --n 45 --seed-base 1000
```

- 预算参考:l4_guard 实跑 1225 请求 / ~108K completion tokens / 50.2 分钟(deepseek 串行)。
- 45 局产物全跑 check_run(I1-I8c 0 违例硬门)→ 快照 + verdict 归档 `docs/harness/reviews/`。

## 8. 判据(用户裁决口径,全部机算)

```text
主判据:
- milk_pierce_death_count:12 → ≤5(45 局总次数口径)
- 狼胜:68.2% → ≤65%
- l4_guard 已过的 5 个主判据不回退,**「不回退」= 仍过原 L4 spec §8 门限**
  (45 局噪声下「不得劣于实测值」过严,单局波动即可翻条;实测值仅作参照列入 verdict 对照表):
  预言家总死亡率下降(L4 实测 56.8%)/ 报验后夜间生存率上升(77.8%)/ 验狼跟投 ≥b4 52.9%
  (实测 64.7%)/ 验狼局投死真预言家不回退 b4 35.3%(实测 23.5%)/
  (方向门)狼胜——本臂已收紧为上行的 ≤65% 主判据与「不高于 l4_guard 实测 68.2%」双显式值,不悬空

塌陷门(用户裁决,量化):
- witch_save_rate ≥ 0.3(45 局中至少 ~14 局用解药;低于此线视为
  guidance 把女巫吓成不用药,臂判不通过)

不回退门:
- 视觉/机制幻觉发言率 ≤5%
- live 率、解析、scaffold coverage 不退化(coverage<0.5 剔局门沿用)
- 不变量 I1-I7、I4b、I8a/b/c 0 违例
```

**分支(用户裁决)**:若奶穿显著下降但狼胜仍 >65% → 下一步跑 cap=4(守卫臂 verdict 已降级为备选的
第二批;注意 avg_rounds 1.98 的既有疑虑仍在,届时另行裁决)。

## 9. 测试与验收

- 注入单测:hook 三条件真值表(8 组合,仅 guard∧victim∧save_available 注入,其余 7 组返回 `""`);
  拼接字节钉死(B-1 注入单测同款)。
- canary 1 / canary 2(§5)+ 解药已用恒等单测。
- golden:v4 新样本入锁(至少含「注入态」与「恒等态」女巫 observation);v1/v2/v3 golden 字节不动。
- 注册表哨兵:`tuple(REGISTRY) == KNOWN_PROMPT_VERSIONS` 自动覆盖 v4。
- visibility 审计:协调提示渲染源不含 guard 私有事件/状态(R-17 思路,静态文本 + 公开派生输入)。
- metrics 单测:overlap/death 两键在构造局上的显式用例(含「重叠但被毒药死亡链混淆」类边界);
  本轮规则不变 → 两键恒等断言可作哨兵。
- 全量回归:`PYTHONPATH=src python -m unittest discover`(当前基线 931c3ae@1187 OK;
  跨会话计数不可比,以执行时主树同 commit 实测为准)。
- live 验收:45 局,n_valid 口径同 l4_guard(live 率 + coverage 门),快照
  `docs/harness/reviews/2026-06-XX-l4-guard-witch-coord-prompt-v4-metrics.json` + verdict 文档。

## 10. Out of scope(硬边界,用户裁决)

```text
不改奶穿规则(同守同救仍死;不走「同守同救=救成功」变体)。
不改守卫结算(settler 零改动)。
不改 action strict-JSON。
不叠 cap=4(留作分支,见 §8)。
不做 L3 随机化。
不加毒药 guidance(P8 女巫毒0 另立课题,混入会污染归因)。
不加守卫侧 guidance(守预言家 17% 留作观察项)。
不修改 prompt_v1 / prompt_v2 / prompt_v3(字节零触碰)。
不翻 PROMPT_VERSION(默认仍 prompt_v1)。
默认板不动(标准 6p;守卫板仍是显式 --board guard 实验臂)。
不动 rules_v1_1 / rules_v1_2(本臂零规则改动)。
```

## 11. 风险

| 风险 | 缓解 |
|---|---|
| guidance 把女巫吓成不用药 → 保护总量下降、狼胜反升 | 塌陷门 witch_save_rate ≥0.3 硬线 + 狼胜方向门兜底 |
| v4 注入误碰 v3 既有字节 | 两类 canary + golden 锁 + ledger 哈希;hook 基类返回 "" 钉单测 |
| 奶穿降了但守卫/女巫保护同目标的「协调」只是双双弃守预言家 | l4_guard 5 主判据不回退门(预言家生存族全在内) |
| milk_pierce 机算与 verdict 手算口径不一致 | 回算 l4_guard 原始局(.runs/ablation/l4_guard/,n_valid=44 口径,§6)须复现 overlap=death=12,作为度量正确性门 |
| **已知接受项**:守卫死后协调提示仍注入(「守卫每晚守护一名玩家」隐含守卫存活),可能压制本来安全的用药 | visibility 硬门(§3)禁止 hook 以 guard_alive 为条件——那正是 guard 私有状态喂漏;此为约束下的必然取舍,塌陷门 witch_save_rate≥0.3 部分兜底;verdict 阶段按已知项解读,不作意外发现 |
| guard 私有状态喂漏进 guidance | §3 visibility 硬门:静态文本 + 仅公开派生输入,审计用例,喂漏=阻断 |

## 12. 流程

spec(本文)→ plan(`docs/harness/plans/2026-06-12--l4-guard-witch-coord-arm-plan.md`,独立审)→
worktree 隔离执行 → review → 45 局 live(用户触发)→ verdict 归档。
对照数据直接复用 `2026-06-11-l4-guard-prompt-v3-metrics.json`(座位级配对,无需回算 b4)。

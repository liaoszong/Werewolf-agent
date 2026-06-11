# 设计:SYS-B4 Claim Ledger + Vote Scaffold

> **类型**:design spec(待用户 review → 再写 implementation plan)
> **来源**:b1 消融实验 verdict(`docs/harness/reviews/2026-06-11-b1-context-repair-VERDICT.md`,merge `ae09d12`)+ 用户裁决(2026-06-11):合并 b1、冻结 v2、不跑 v2-lite、直开 B4。
> **B4 第一版定性(用户裁决)**:**input-side scaffold**,不是 output protocol 改造。

---

## 0. 硬约束(用户裁决原文,任何 plan/实现不得违反)

```
B4 不改变 action 响应机器契约。
vote / night action 仍然输出既有 strict-JSON。
不得要求模型输出"推理段 + JSON 尾"这种会影响解析链的格式,除非 action_runtime 明确支持并有测试。
脚手架优先放在输入侧:observation_text / structured context / system guidance。
如果确实需要中间推理产物,必须作为独立 scaffold artifact 或 pre-action note,不得混入 action JSON 响应。
```

理由:B1 工程风险可控的关键正是只动输入侧。若碰 vote action 输出格式而不钉死契约,解析失败率会污染 `live_success_rate` 与全部行为指标——届时分不清是模型变笨、脚手架变差,还是 JSON 解析坏了。

## 1. 目标:只盯一条失败链

```
预言家验狼并公开报出后,村庄不应在多数情况下把真预言家自己投死。
```

b1 实测基线(per-game 明细):验狼 20 局中 **14 局(70%)day1 多数票投出真预言家**;验狼跟投 30%;狼胜 93.3%。根因:村民被要求判别声称却没有任何结构化声称信息可用,双狼协同悍跳吃掉孤证预言家。

**非目标**:平衡胜率到特定数值(那是 Layer 4)、座位/候选随机化(Layer 3)、女巫毒人策略、action 输出协议改造(B4 第二版若需要,另立 spec)。

## 2. In scope(用户裁决的四件套)

### 2.1 Claim Ledger(声称账本)
- 记录:谁跳了什么身份;谁报了什么验人结果(验谁、报什么);谁反驳/对跳;哪些 claim 互相冲突。
- **每条 claim 带 `source_event_ids`(指向 player_speech 事件),继续过 I4b**:声称只引用公开发言事件,任何 seat 的 scaffold 注入内容来源 ⊆ 该 seat 可见集,`assert_prompt_entitled` 与 artifact 级 oracle 照常全绿。
- **捕获机制 = 本 spec 最大设计决策,见 §3。**

### 2.2 Vote Scaffold(投票前结构化摘要)
- 投票请求(`player_vote`)的 `observation_text` 在现有 v2 结构化分区之上,注入**分层硬事实摘要**,严格区分四类信息:
  1. **你的真实私有结果**(如你是预言家:你的验人记录——引擎真值);
  2. **公开声称**(来自 Claim Ledger:谁声称什么,带原文引用);
  3. **反驳/对跳**(谁质疑谁、对跳关系);
  4. **票史**(已有投票矩阵,v2 已具备)。
- 对"预言家报狼"局面,system guidance 要求**比较 claim 自洽性**(可验证性、与公开事实矛盾点、发言-投票一致性),而不是默认怀疑或默认相信。
- 落点:输入侧——`observation_text` 拼装 + vote 请求的 system guidance;**action strict-JSON 响应原样不动**(§0)。

### 2.3 Anti-coordination guard(反协同误导护栏,prompt 措辞层)
- 不能因为有人对跳就自动否定先跳者;
- 不能因为第一天跳预言家就自动判悍跳;
- 不能写"相信预言家"(b1 已证其镜像"别默认相信"同样会被狼利用);
- 必须给**比较程序**:claim 的可验证性、矛盾点、发言-投票一致性。
- 这是 b1 判别指令的修正版:b1 给了"怀疑的理由",B4 给"分辨的材料 + 比较的程序"。

### 2.4 Action contract guard(契约护栏,验收硬门)
- strict-JSON 不变(§0);
- **解析失败率不得显著上升**:b4 臂的 `live_success_rate` 分布与 invalid/parse 失败计数对照 baseline/b1 不得退化(量化门见 §6)。

## 3. 关键设计决策:claim 怎么捕获(三案,推荐 C)

B1 当时砍声称区的原因必须正面回答:**引擎没有结构化 claim 事件,claim 只活在自由文本里;正则提取的假阳性会以"结构化权威"形态注入全桌 prompt,比没有更糟。**

| 方案 | 机制 | 否决/保留理由 |
|---|---|---|
| A. 正则/规则提取 | 从发言文本模式匹配"我是预言家/我验了X是狼" | **否决**:b1 诊断期正则刚闹过假阳性;中文自由文本的身份声称变体太多,漏报+误报双高 |
| B. 结构化发言输出 | speech 响应改为 JSON{text, claims[]} | **否决(第一版)**:违反 §0 精神——这是 output protocol 改造,speech 解析链(现为自由文本+空文本兜底)引入新失败面 |
| **C. Scribe 摘要调用(推荐)** | 每轮发言阶段结束、投票开始前,**额外 1 次模型调用**("书记员"):输入=本轮全部带标签公开发言(纯公开信息),输出=strict-JSON 的 claim 列表(claimant/claim_type/target/result/refutes/source 发言序号) | **符合 §0 的"独立 scaffold artifact"**;每轮仅 +1 请求(非每座位);claim 自带发言出处,注入时附原文引用,假阳性自暴露;scribe 输入只含公开事件 → I4b 天然干净 |

方案 C 细则:
- **scribe 调用 = 新增 `response_kind="scaffold"`**——它不是 game action:不进 decision-log 的玩家决策、不参与合法性校验,只产出 scaffold artifact,有自己的小解析器 + 降级路径。**这意味着 provider 层需要 additive 改动**(评审修订①):`_system_for` 现仅有 speech/else 两支,scaffold 请求落进 else 会拿到 action 系统提示("You MUST select action from []" 喂给书记员=垃圾约束)。须新增 scaffold 分支 + `build_scribe_system_prompt` 构建器;**additive 字节安全由 golden 守卫验证(v1/v2 渲染逐字节不变)**。
- **claim 字段**(评审修订,GPT#6 + 保留意见):每条 claim 含 `claimant / claim_type / target / result / refutes / source`(发言事件序号)+ **`source_quote`(原文引用,必填)+ `uncertain`(布尔,必填)**;`confidence` 数值**列为可选**——flash 自打分可能引入新噪声,首版不依赖。
- **解析失败降级(评审修订②,语义钉死)**:scribe JSON 解析失败 → **当前轮不新增 claim,历史账本保留**(账本跨轮累积,任何一次失败都**不得清空**已有条目;"为空"只指本轮增量)。该轮 vote scaffold 注入 = 既有账本 + v2 现状(带标签发言+票史),**绝不阻塞对局、绝不计入玩家 live_success_rate**(scribe turn 单独打 kind:`scaffold_success` / `scaffold_fallback`,且 `live_requested=False`,不混入玩家 turn 统计;metrics 的 live 率口径同步排除 scaffold turns——见 §5 风险 2)。
- **scribe 的 provider 归属(评审新发现③)**:**独立 provider 实例**,不挂任何座位(挂座位会污染该座位 trace 与 per-seat token 记账=B5 既定需求,且共享该实例 max_requests 预算)。trace 单列(actor="scribe");**低温(temperature=0 或接近)**——提取任务,压非确定性。预算分列:`player_requests` 与 `scaffold_requests` 两个口径都进 turns 汇总。
- **预算**:每局 +`max_day_rounds`(≤3)次请求,~+15% 请求数。单局 max_requests=80 余量足够(实测 ~22)。
- **claim 注入形态**(vote scaffold 内):每条 claim 必须带"(原文:'…')"引用 + 标注"由系统从公开发言提取,以原文为准"——提取错误自暴露,不以无源权威形态出现。scribe 输出定位=**辅助提取,非裁判事实**(测试钉住:scribe 单测 fixture 断言只提取、不裁决)。

> 备选折衷:若用户认为 +1 调用/轮成本或非确定性不可接受,可降级为 A'(保守正则:只抓高置信模式如"我验了pX,(他/她)是(狼人|好人)",漏报容忍、误报趋零,凡不带可引用原文的不入账)。spec 默认 C,A' 列为 plan 内的降级开关。

## 4. 版本与组合:prompt_v3(`b4_scaffold`)

- **注册新版本 `prompt_v3`**,走与 v2 相同的共存基建:`KNOWN_PROMPT_VERSIONS` 加项、独立 golden 目录、ledger 条目、arm 可选;`PROMPT_VERSION` 默认**继续保持 prompt_v1**(翻默认=拿到 b4 数据后的独立用户决策)。
- **v3 组合 = v2 的 PASS 部分 + B4 脚手架 + 分级 guidance**(评审修订③:**vote 强 / speech 克制**——b1 教训:把判别武器同步发给全桌=教狼悍跳):
  - 保留:规则卡(P3/P4 幻觉修复已验有效)+ 结构化观察(私有/事实/带标签发言/票史);
  - **claim digest 两边注入**(发言与投票请求的 observation_text 都带账本——信息对称);
  - **强比较程序 + §2.3 反协同护栏只进 vote 请求的 guidance**;speech guidance 保持克制(回到接近 v1 的中性发言要求 + 反视觉/反机制声明,不下发判别程序);
  - 投票请求另加 §2.2 分层摘要。
- **prompt_v2 冻结不动**(`b1_context_repair`,golden 字节锁强制);v3 是新链,不修改 v2 的任何函数——复用走 import,分叉走新函数。

## 5. 风险与未决

1. **Scribe 质量未知**:同款 flash 模型做信息提取通常远易于做推理,但首版需在 plan 中加 scribe 单测(固定发言文本 fixture → 期望 claim 集)+ live 抽查。
2. **live 率口径污染(必须在 plan 中显式处理,已代码证实)**:`metrics.live_rate_from_turns` 分母是 `len(turns)` 全量——scribe turns 不排除**必然**稀释 live 率。设计要求:scribe turn 打独立 kind + `live_requested=False`,`metrics.live_rate_from_turns` 与 P2-A-2 的 `live_success_rate` 口径**只统计玩家 turns**(plan 须有钉死测试);对照臂可比性(b4 臂 vs baseline/b1 的 live 率同口径)是 §2.4 验收的前提。
2b. **臂纯度(评审新发现②,与 b1 的 live 率教训同构)**:scribe 整局全失败的局,事实上跑的是"v3 壳 + v2 内容",照常计入 b4 臂聚合会稀释干预效果(同构于当年"44 局只有 6 局真 live 差点得出全错结论")。设计要求:**per-game `scaffold_coverage` = 成功 scribe 轮 / 总 day 轮,进 `_metrics.json` 明细行**;聚合层照 live 率先例设有效性门槛——**coverage < 0.5 的局不进 b4 行为聚合,单独计数(`n_invalid_scaffold`)并必须在报告单列**(阈值默认 0.5,plan 可调但不可取消单列)。
3. **claim 时效**:scribe 每轮跑一次,r2 投票能看到 r1+r2 全部 claim(账本跨轮累积);claim 与后续行为矛盾(如自称预言家却不报新验)留给模型比较,不做引擎裁决。
4. **I4b**:scribe 输入=公开发言(public events);注入的 ledger 内容若进 `observation_text`,其 source_event_ids 须并入渲染来源并过 `assert_prompt_entitled`(全公开,天然过)。artifact 级 oracle 照常全绿是验收硬门。
5. **多预言家声称的边界**:双狼都跳预言家 + 真预言家 = 3 claim 冲突,scribe 只记录不裁决;护栏(§2.3)负责"不许自动判"。

## 6. 实验协议与成功判据

- **Arm:`b4`(prompt_v3),45 局,seed_base=1000(与 baseline/b1 配对);b4 臂留 per-game 明细行(已具备)。**
- 主判据(直接对失败链):
  - **验狼局中"真预言家被 day1 多数票投出"率:70%(14/20)→ <30%**;
  - 验狼跟投:30% → **≥60%**(b1 的 85% 判据按 b1 教训下调为阶段目标);
  - 狼胜:93.3% → **≤65%**(方向性;回到 baseline 之下才算真改善)。
- 守住的判据(不得回退):
  - 视觉幻觉发言率 ≤5%、机制幻觉局率 ≤5%(v2 已达成的不能丢);
  - **live_success_rate / 解析失败计数对照两臂无显著退化(§2.4 契约护栏;玩家 turn 口径)**;
  - 不变量 I1-I7+I4b 全绿。
- **臂纯度与有效性(§5 风险 2b 的聚合规则)**:有效局 = live 率 ≥0.7(玩家 turn 口径)**且** `scaffold_coverage ≥ 0.5`;`n_invalid_lowlive` 与 `n_invalid_scaffold` 分列计数并在对比报告中单列;每局 `scaffold_coverage` 进明细行。狼胜 ≤65% 为**方向门**(双审一致),不作唯一 hard fail——主判据是失败链指标(真预言家被投率)。
- 预算量级:45 局 × (~22+3) 请求 ≈ 1100+ 次,与 b1 同量级;跑前照例报预算过用户门。

## 7. 组件边界(预期落点,plan 阶段细化)

```
emergent_engine(day 流程):发言阶段后 → scribe 调用(方案C,独立 provider 实例、低温)→ ClaimLedger(纯数据,挂引擎状态,跨轮累积)
                                              │
prompt_v3 模块(纯函数,不 import engine):build_scribe_system_prompt + render_claim_digest(ledger) + render_vote_scaffold(obs, ledger, ...)
                                              │
ProviderRequest.observation_text(投票/发言请求,输入侧)──→ provider 层 additive 改动:
    _system_for 新增 scaffold 分支(scribe 系统提示);action strict-JSON 契约不动;
    v1/v2 渲染逐字节不变,由 golden 守卫验证(评审修订①)
```

- metrics.py:新增 `seer_voted_out_in_verify_cases` 指标(数据已在 per-game 明细,聚合即可)+ scribe turn 口径排除 + `scaffold_coverage`/`n_invalid_scaffold`(§5 2b)。
- 复用 v2 基建:golden/ledger/守卫/不变量/消融臂全套照搬。**v3 golden 须锁三类样本(GPT#2)**:① scribe system prompt + 输出 schema 示例;② claim digest 注入文本;③ vote scaffold 完整 prompt——否则 B4 核心脚手架字节裸奔。

## 8. Plan 硬要求(2026-06-11 双审合并清单,plan 以此为验收硬门)

1. live 率只统计玩家 turn(钉死测试:含 scribe turns 的 fixture → live_rate 不被稀释)。
2. scribe 失败归 `scaffold_fallback` kind + `live_requested=False`;**失败不清空历史账本**(钉死测试)。
3. claim 字段:`source_quote` + `uncertain` 必填,`confidence` 可选;scribe=辅助提取非裁判事实(fixture 单测钉住)。
4. budget/turns 汇总分列 `player_requests` 与 `scaffold_requests`。
5. guidance 分级:digest 两边注入,强比较程序只进 vote 请求(golden 锁 speech_v3 与 vote scaffold 两类样本即可证)。
6. v3 golden 三类样本(scribe prompt+schema / claim digest / vote scaffold 完整 prompt)。
7. scribe 独立 provider 实例 + trace 单列(actor="scribe")+ 低温(temperature≈0)。
8. scribe fixture 单测(固定发言文本 → 期望 claim 集,含对跳/反驳/不确定标注用例)。
9. `scaffold_coverage` 进明细行;有效局门槛 = live≥0.7 且 coverage≥0.5;`n_invalid_scaffold` 单列(阈值可调,单列不可取消)。
10. provider 层 additive 改动的字节安全:v1/v2 golden 守卫绿 + `git diff --exit-code` v1/v2 golden 目录。

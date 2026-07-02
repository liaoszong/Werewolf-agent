# 设计:Agent 角色体验与真人参与路线转向

> 类型:route/spec design
> 日期:2026-07-02
> 背景:当前工程已经完成可观战、可审计的 AI-vs-AI 狼人杀闭环,但对局体验偏无聊。用户明确要求把重点拉回"Agent 智能体",参考 SillyTavern 的角色扮演能力和 Claude Code / learn-claude-code 的 agent harness 工程思想,后续加入真人实时参与。

---

## 0. 路线决策

**P3 从"评测 · 复盘 · 排行榜"改为"Agent 角色体验 · 真人参与"。**

旧 P3 不删除,后移为 P4。原因很直接:如果一局本身不好看、不好玩,再精细的评测也只是在评价无聊。当前项目的 P1/P2 地基是可用资产,不是失败资产;问题出在 Agent 层太薄,多数 seat 仍像"带 persona 的 API 调用",而不是能持续扮演、记忆、伪装、协作、追问、转票的狼人杀玩家。

P3 的产品目标:

- AI seat 要像有角色、有记忆、有目标的玩家,而不是同质化发言器。
- 狼人杀好玩的机制要显性出现:拉踩、试探、对跳、背刺、认错、转票、遗言、狼队私密剧本、好人阵营围绕硬信息形成推理链。
- 真人能作为一个角色加入实时局,AI 能回应真人,真人只看到自己角色应看到的信息。
- 所有增强仍保留现有强项:事件溯源、信息隔离、可审计 prompt source、provider trace、结算复盘。

---

## 1. 参考项目怎么转译

### 1.1 SillyTavern:角色扮演层

SillyTavern 的核心价值不是"多模型 API 面板",而是把角色扮演体验拆成可配置资产:Character Card、persona、group chat、World Info/Lorebook、RAG/Data Bank、summary、prompt inspection。对 Werewolf-agent 的启发如下:

| SillyTavern 能力 | 本项目转译 |
|---|---|
| Character Card | `AgentCard`:角色策略、人格、说话风格、风险偏好、社交倾向、常用开局、禁用行为、示例发言。 |
| Persona | `SeatPersona`:座位长期性格,不绑定真实身份,避免洗牌后把"我是狼"写进 seat persona。 |
| Group Chat | 白天发言调度不只固定轮流:允许被点名回应、强制发言、低/高 talkativeness、补充陈述。 |
| World Info / Lorebook | 角色 playbook 与游戏知识库:不同角色的常见打法、对跳处理、狼队伪装策略、女巫药使用偏好。 |
| Data Bank / RAG | 可选外部策略文档或用户自定义角色资料,但注入必须过 visibility 与 token budget。 |
| Summarize | 当前局情景记忆:每轮后提炼"我相信谁/怀疑谁/我承诺过什么/谁和我冲突"。 |
| Prompt Inspector | 面向调试的 Agent prompt/itemization:本次注入了哪些角色卡、记忆、公共事实、私有事实,来源是什么。 |

关键差异:本项目不能照搬开放式聊天。狼人杀是严格信息不对称游戏,所以任何记忆、摘要、RAG、playbook 注入都必须带 `source_event_ids` 或明确的公共来源,并通过 SYS-A4/SYS-C3 防泄漏检查。

### 1.2 Claude Code / learn-claude-code:Agent harness 层

learn-claude-code 的重要观点是:Agent 不是只有模型,而是 model + harness。主循环稳定,能力来自工具、知识、权限、hooks、记忆、压缩、子智能体和队伍协议。

对 Werewolf-agent 的转译:

| Agent harness 机制 | 本项目转译 |
|---|---|
| One loop | 每个 seat 都走统一 `observe -> remember -> plan -> speak/act -> reflect`。 |
| Tool use / handlers | 游戏内工具:查记忆、更新怀疑图、查询 claim ledger、生成投票计划、写私有笔记、狼队私聊。 |
| Permission system | 工具按角色/阶段/可见性开放:预言家能记录验人,狼人能访问狼频道,村民不能读狼队记忆。 |
| Hooks | `BeforeVote` 检查是否考虑过公开 claim; `AfterSpeech` 抽取承诺/指控; `PrePrompt` 做 visibility guard。 |
| Todo / task graph | 局内目标:今天推谁、保护谁、骗谁、下一轮如何解释上一票。 |
| Subagents / teams | 狼队可以有共享剧本;复盘/书记员/claim extractor 是非玩家 scaffold agent,不参与裁判。 |
| Context compact | 对局越长越需要摘要和压缩:保留承诺、矛盾、票史、私有结果,丢弃低价值寒暄。 |
| Memory selection/extraction/consolidation | 每轮先提取局部记忆,再筛选可注入记忆,局后可沉淀为 playbook。 |

这条线的工程结论:不要继续把智能都塞进一个长 prompt。应当把 Agent 能力拆成可测试的 harness 子系统,每个子系统都要有输入、输出、可见性、预算和失败降级。

---

## 2. 当前差距诊断

现有系统已有强地基:

- P1/P2 已有 emergent engine、visibility projection、runtime events、provider trace、prompt manifest、settlement、Qt theater。
- `profile_config` 已有 role prompt + seat persona。
- SYS-B1 已有最小工作记忆:每轮从可见事件重建 `observation_text`。
- SYS-B4 已有早期 scaffold:claim ledger / vote scaffold / scribe provider 的设计与部分实现接缝。

但它们还不足以支撑"好玩":

- seat persona 只是前置文本,不是可演化的角色状态。
- 没有局内情景记忆:AI 不稳定记住自己说过什么、怀疑谁、为何转票。
- 没有私有目标管理:狼人没有持续伪装剧本,好人没有持续调查路线。
- 白天讨论太机械:固定发言、少回应、少追问,缺少真人桌游的拉扯。
- 没有真人 seat:用户只能观战,不能把 AI 当对手或队友。
- 评测指标偏"正确/合法",缺少"好看/有戏/像玩家"指标。

---

## 3. 推荐路线

### 方案 A:Agent-first,再真人 seat(推荐)

先让 AI 对局变得像真人桌游,再把真人接入。顺序:

1. P3-A Agent Card + Memory Spine。
2. P3-B Table-talk / wolf channel / roleplay scaffold。
3. P3-C Human seat。
4. P4 复盘/排行榜。

优点:真人进入时会遇到有记忆、有反应、有个性的 AI,体验上限高。风险:真人功能稍晚。

### 方案 B:Human-first,再补 Agent

先做真人 seat 表单/输入/投票/夜间行动,AI 仍基本维持现状。

优点:很快能"玩家加入"。风险:真人坐进去后发现 AI 还是无聊,产品问题没有被解决。

### 方案 C:SillyTavern-like UI-first

先做角色卡编辑器、角色库、剧场 UI,再补后端 Agent harness。

优点:看起来像路线转向。风险:容易变成配置 UI,但实际对局仍无聊。

**决策:选 A。** P3-A 先建 Agent Card 与记忆骨架,这是后续真人 seat 和复盘的共同地基。

---

## 4. P3-A 设计:Agent Card + Memory Spine

### 4.1 AgentCard schema

`AgentCard` 是可编辑资产,不等于 provider config。建议字段:

- `name`:卡名,例如"冷静逻辑村民","激进悍跳狼","谨慎女巫"。
- `role_affinity`:适配角色,可为通用或特定角色。
- `personality`:稳定性格,只描述风格。
- `speech_style`:句长、攻击性、是否爱反问、是否爱总结票型。
- `risk_profile`:保守/激进/摇摆/爱带队。
- `social_strategy`:结盟、拉踩、跟票、反打、装糊涂等倾向。
- `role_playbook`:按角色加载的策略片段,例如狼人伪装、预言家报验、女巫药使用。
- `memory_policy`:哪些事必须记,哪些事可压缩,局后是否沉淀跨局 playbook。
- `examples`:少量示例发言,帮助风格稳定。
- `tool_permissions`:允许使用的游戏内 scaffold 工具。

约束:

- `SeatPersona` 必须 role-agnostic,不能写真实身份。
- `RolePlaybook` 可以 role-specific,但只在角色确认后按 visibility 注入。
- Card 不能覆盖 action contract;它只能影响上游 context/harness。

### 4.2 AgentContextPacket

新增概念 `AgentContextPacket`,作为 prompt 组装前的结构化上下文。它不是立即要求改代码的字段名,但后续实现应围绕这个边界设计。

建议分区:

1. **Board facts**:公开规则、角色构成、胜负条件。
2. **Self facts**:我的 seat、真实身份、阵营、可用能力、能力剩余。
3. **Private facts**:预言家验人、女巫救毒、狼队成员、狼队夜间计划。
4. **Public timeline**:死亡、出局、发言、投票、公开 claim。
5. **Episodic notes**:我上一轮相信/怀疑谁,我说过什么,谁和我冲突。
6. **Commitments**:我公开承诺过的观点和投票倾向。
7. **Suspicion graph**:对每个玩家的信任/怀疑分数及来源。
8. **Team memory**:狼队共享剧本和私聊结论,只给狼人。
9. **Retrieved playbook**:当前局面触发的策略片段。
10. **Prompt budget report**:哪些区块被注入/压缩/丢弃。

每个可见事实区块必须有来源:

- 来自 event 的必须带 `source_event_ids`。
- 来自 agent 自己的记忆必须带生成时对应的可见来源集合。
- 来自公共规则/playbook 的必须标记为 public static source。

### 4.3 Memory lifecycle

每个 seat 在每个行动窗口走同一条 harness:

```text
visible observation
  -> extract facts / claims / commitments
  -> update private episodic memory
  -> retrieve relevant card + playbook + memories
  -> plan next speech/action
  -> speak or emit ActionEnvelope
  -> post-action reflection: record what I just committed to
```

失败降级:

- 记忆提取失败:保留旧记忆,当前轮不新增。
- 记忆检索失败:退回工作记忆 + board facts。
- scaffold agent 失败:不阻塞裁判,但在 provider-turns/scaffold summary 单列。

### 4.4 First playable arm

第一版不追求全功能,只要让 6 人局明显更有趣:

- 每个 seat 使用不同 AgentCard。
- 预言家能持续围绕验人结果推动议程。
- 狼人能形成并维护伪装剧本,白天发言与投票不要互相打架。
- 村民能记住谁跳了什么、谁投了谁、谁前后矛盾。
- 女巫能记住药使用与夜晚信息,不把无信息当信息。
- 结算能展示至少 3 个"戏剧节点":例如真预言家被反打、狼人成功带票、村民临时转票。

---

## 5. P3-B 设计:桌面博弈脚手架

P3-B 的目标是让白天讨论像桌游,不是报流水账。

核心能力:

- **Discussion windows**:一轮主发言后,允许被点名玩家回应、关键 claim 后追加质询、投票前最后陈述。
- **Talkativeness**:不同 AgentCard 决定主动发言概率和回应欲望。
- **Claim/counterclaim dynamics**:公开 claim ledger 触发回应机会,但不替玩家裁决真假。
- **Wolf channel**:狼人夜间/特定窗口形成共享剧本,例如"p1 悍跳,p2 倒钩"。
- **Consistency hooks**:投票前检查"你的票是否违背你刚才发言";允许违背,但要求给出解释。

边界:

- 不改变裁判真值。
- 不把玩家中间推理写入 action JSON。
- 所有额外发言窗口仍产生事件,并进入 replay/settlement。

---

## 6. P3-C 设计:真人座位

真人 seat 必须是游戏参与者,不是上帝观众。

核心规则:

- 真人只收到自己 seat 的 projection:公开事件 + 自己私有事件。
- 真人发言、投票、夜间行动走同一 action contract。
- UI 需要区分"观战模式"和"参战模式";参战时禁止显示 god-only 证据。
- 超时可配置:跳过、默认 pass、或 AI 接管。
- 断线重连必须从 server 状态恢复,不能从本地 artifact 读 god view。

首版建议:

- 只支持本地单真人 seat。
- 先支持白天发言 + 投票,再支持夜间角色能力。
- AI 对真人发言的响应先走现有事件流 + P3-A memory,不做特殊捷径。

---

## 7. P4 评测后移后的新口径

P4 仍然重要,但指标要升级:

- **Differentiation**:不同 AgentCard 的语言/行为差异是否明显。
- **Memory use**:是否引用自己可见且相关的历史信息。
- **Consistency**:发言、投票、私有目标是否有可解释关系。
- **Drama points**:对跳、反驳、转票、狼队配合、关键误判等节点。
- **Human fun**:真人是否能看懂局势、是否觉得 AI 有反应、是否愿意再玩一局。
- **Classic metrics**:胜率、角色表现、模型成本、live_success_rate 仍保留。

排行榜不只按模型排,还要按 AgentCard、记忆策略、scaffold 组合排。

---

## 8. 验收与安全

### 文档级验收

- `docs/PROJECT_MAP.md` 明确 P3 当前方向为 Agent 角色体验 + 真人参与。
- 旧评测/排行榜路线后移为 P4。
- 系统视图新增/更新 Agent Card、Agent harness、human seat gateway。

### 后续实现验收

- 所有 prompt/context 改动走 prompt versioning 与 golden。
- 所有记忆注入必须通过 I4b/source entitlement。
- scaffold turn 与 player turn 指标分列。
- Human seat e2e 必须证明真人看不到 god/private-for-other-seat 信息。
- 趣味性指标进入 settlement 或 postgame report,不能只看胜负。

---

## 9. 非目标

- 不把项目改成通用 SillyTavern clone。
- 不做开放式无裁判聊天房。
- 不为了"角色扮演"牺牲信息隔离。
- 不让真人 seat 通过客户端读取本地 run artifact。
- 不在 P3-A 同时重做全部 UI。
- 不把评测删掉;只是后移到更有趣的对局之后。

---

## 10. 参考资料

- SillyTavern repository: https://github.com/SillyTavern/SillyTavern
- SillyTavern docs: https://docs.sillytavern.app/
- Character design: https://docs.sillytavern.app/usage/core-concepts/characterdesign/
- Group chats: https://docs.sillytavern.app/usage/core-concepts/groupchats/
- World Info / Lorebooks: https://docs.sillytavern.app/usage/core-concepts/worldinfo/
- Data Bank / RAG: https://docs.sillytavern.app/usage/core-concepts/data-bank/
- Summarize: https://docs.sillytavern.app/extensions/summarize/
- learn-claude-code: https://github.com/shareAI-lab/learn-claude-code
- Claude Code memory: https://docs.anthropic.com/en/docs/claude-code/memory
- Claude Code subagents: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- Claude Code hooks: https://docs.anthropic.com/en/docs/claude-code/hooks

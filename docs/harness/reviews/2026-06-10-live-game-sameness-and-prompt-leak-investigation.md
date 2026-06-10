# 诊断报告:Live 对局高度雷同 + 疑似 Prompt 泄露(2026-06-10)

**触发**:用户连开多局 live(DeepSeek)对局,发现开局几乎一模一样(狼刀 p3 预言家、预言家 p3 验 p1 狼),发言每局措辞不同但重复性极高;并怀疑发言里有 prompt/信息泄露。

**方法**:只读取证。检查最近 3 局 `.runs/g2d_profile_*`(`4fccba3e` / `30c7b142` / `2f2770b6`,均 `execution_mode=live` / `live_api=used`)的 `resolved-profile.json`、`game-log.json`、`provider-trace.json`(24 个真实下发 prompt)、`provider-turns.json`、`failure-audit.json`,并跑离线不变量 `check_run`(`src/werewolf_eval/invariants/checker.py`,7 条 I1/I2/I3/I4b/I5/I6/I7)。未改任何代码。

---

## 结论速览

| 问题 | 结论 | 性质 |
|---|---|---|
| 开局每局雷同 | **真问题**:角色按座位写死(无洗牌)+ 模型对固定布局收敛 + 同角色共用 persona | 设计/增强层,非 bug |
| 发言疑似 prompt 泄露 | **无越权信息泄露**;"早发言者引用晚发言者"=模型幻觉(confabulation),非系统泄露 | 系统正确 |
| 出局即公开真身 | 设计性强信息源(`pX revealed as role` 全场可见),削弱推理难度 | 设计选择,非 bug |
| `check_run` 7 条不变量 | 全部干净(0 error / 0 artifact_gap) | 系统正确 |

**总判**:系统正确性(可见性、不变量、②a 字节重构)没有问题;雷同与"伪泄露"全部落在**对局设计/增强层**(角色随机化、per-seat persona、温度、出局是否公开身份),不在 ②a 范围内。

---

## 发现 1:开局每局雷同 —— 根因(两层,都成立)

### 证据:三局夜 1 动作逐字相同,且全是真模型返回

| run | 狼刀 | 预言家验 | 女巫救 | 夜1 provider 调用 |
|---|---|---|---|---|
| g2d_profile_4fccba3e | p1→p3 | p3→p1 | p4→p3 | p1/p2/p3/p4 全 `live_success` |
| g2d_profile_30c7b142 | p1→p3 | p3→p1 | p4→p3 | 全 `live_success` |
| g2d_profile_2f2770b6 | p1→p3 | p3→p1 | p4→p3 | 全 `live_success` |

`live_success` 证明这些目标是**真模型选的**,不是兜底 RNG 抽签(failure-audit 里夜1无 invalid),所以**与种子无关**。

### 层 A — 角色按座位写死,全库无洗牌(根因)

- `src/werewolf_eval/profile_config.py:62` `DEFAULT_6P_SEAT_ROLES = {p1:werewolf, p2:werewolf, p3:seer, p4:witch, p5:villager, p6:villager}`。
- `:168` `_template_seat_roles` 直接返回该常量;`resolve_profile`(`:307`)按它逐座位解析。
- 全库 `grep shuffle|randomize|random.sample|assign_roles` **零命中** —— 从来没有角色随机化。
- 后果:每一局 `default_6p` 布局完全相同(p1/p2 恒狼、p3 恒预言家、p4 恒女巫)。

### 层 B — 模型对"固定布局 + 零信息夜1"的结构化决策收敛

- 短 JSON 单选(夜间动作)熵极低,模型几乎必落"最小序号目标":预言家验**最低非己**=p1、狼刀**最低非狼**=p3、女巫救当晚被刀者=p3。
- 自由发言要采样大量 token → 措辞每局不同;但目标几乎必落同一个。这正是"动作一模一样、发言变但重复"的机理。
- **"狼总刀预言家、预言家总验到狼"是被结构逼出来的**:布局固定→预言家恒 p3、狼恒 p1/p2;叠加"都挑最小序号"→ 狼的最小非狼目标 p3 恰是预言家座位,预言家的最小非己目标 p1 恰是狼座位。**不是信息泄露**(见发现 2)。

### 层 B 加剧因素 — persona 按角色共享(两狼=克隆)

- `build_default_profile:446` 把 `DEFAULT_ROLE_PROMPTS[role]` 填进每座位 `prompt`;`seat_agents.py:69` 读 `seat["prompt"]` → config;`llm_providers.py:120 compose_system` 拼进 system message(`:171` `request.persona_prompt or self._config.persona_prompt` 走 config 兜底)。
- persona **确实注入了**(resolved-profile 的 `prompt_hash` 非空佐证;两狼 hash 相同),但**按角色共享** —— 两只狼拿到完全相同的狼人 persona,所以 p1/p2 近乎克隆。
- 注:`provider-trace.json` 里逐请求 `persona_prompt` 字段为空,是记录字段冗余(persona 在 agent config 上、compose_system 时拼接),**不代表没送达**。

---

## 发现 2:疑似 Prompt 泄露 —— 实为模型幻觉,系统无泄露

逐项核验 24 个真实下发 prompt 的可见性:

| 检查项 | 结果 |
|---|---|
| 狼的「你已知的身份」行 | 只见队友(p1↔p2),无其他角色 ✅ |
| 村民/女巫/预言家「你已知的身份」 | 空,无任何别家角色 ✅ |
| 女巫夜间 prompt | 只看到"今晚 p3 被狼人袭击",不含狼身份 ✅ |
| 预言家 r2 prompt | 只看到自己 r1 验人结果(Seer p3 checks p1, result: werewolf)✅ |
| 发言顺序 | 每个发言者**只看到座位在它之前**者的发言(p1 看 0、p2 只看 p1、p3 看 p1+p2…),跨轮=完整历史+本轮更早座位;**无未来发言** ✅ |

**用户嗅到的"泄露"**:p2(第 2 个发言)说"p4 刚才的发言带节奏",而 p4 是第 4 个、尚未发言。核验:**p2 的 prompt 里根本没有 p4 的发言(只有 p1 的)**。这是模型 **confabulation(幻觉)** —— 被 p1 发言里点名"p4…急于带节奏"带跑,把假设当成既成事实。**是模型瞎编,不是系统把后面的发言漏给了它。** 属模型质量(增强层),非正确性 bug。

---

## 发现 3:出局/死亡即公开真身(设计性强信息源)

- prompt 里出现 `- (r1 day) p1 revealed as werewolf.` —— 投票出局会向**全场**公开死者真实身份(狼 p2 那句"证实是狼人"即来源于此)。
- 这是个**刻意的公开事件**,不是泄露 bug;但它让神职/狼一死全场就知身份,大幅降低推理难度(正式狼人杀通常不翻牌)。是否保留取决于设计意图。

---

## 系统正确性旁证

- `check_run`(7 条不变量)对最新 live 局:**0 finding,0 artifact_gap**。
- I4b 可见性 oracle(独立于 `_build_obs` 的反循环实现)干净 —— 进一步佐证无可见性泄露。
- 上述全部问题均不触及 ②a 字节重构(引擎结算/可见性逻辑忠实)。

---

## 修复方向(本报告不改代码,仅列选项)

1. **角色洗牌**:每局用变化的种子随机洗牌"座位→角色"(保持 2狼1预言家1女巫2村 多重集),布局每局不同 —— 最直接打破固定开局。需先决定洗牌放哪条启动路径(会改变 profile"每座位绑定特定模型"的语义,或单独做"随机对局"模式)。
2. **对局多样性(增强层)**:per-seat 差异化 persona(两狼不再克隆)+ 调高 `temperature` + 随机化 prompt 里候选玩家顺序(打破"总选最小序号"位置偏置)。
3. **出局/死亡不公开真身**:去掉 `pX revealed as role` 的全场公开,提升推理难度(贴近正式规则)。

> 三者相互独立,可单做或组合。1 治"布局雷同",2 治"动作/发言雷同 + confabulation 倾向",3 治"推理难度过低"。

---

## 复现命令(只读)

```bash
# 离线不变量体检
NO_PROXY='*' PYTHONPATH=src python -c "from werewolf_eval.invariants.checker import check_run; \
  print(check_run('.runs/g2d_profile_2f2770b6'))"
# 角色布局(任意 g2d_profile run)
python -c "import json; print({s['player_id']:s['role'] for s in json.load(open('.runs/g2d_profile_2f2770b6/resolved-profile.json',encoding='utf-8'))['seats']})"
# 逐 prompt 可见性 / 发言顺序扫描:见本次会话脚本(provider-trace.json 的 requests[].observation_text)
```

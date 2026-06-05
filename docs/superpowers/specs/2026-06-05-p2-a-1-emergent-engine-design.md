# P2-A-1 涌现式游戏引擎 — Design Spec

**Status:** draft (for spec review)
**Route:** `docs/PROJECT_MAP.md` → P2(观战式 AI-vs-AI 对局客户端)/ 模块 A(涌现式游戏引擎)/ 工作任务 1。旧临时名 "G4-1"。
**Date:** 2026-06-05
**Depends on (reuses, does not modify):** P1-B provider 契约(`ProviderAgent`/`DeterministicFakeProvider`/`deepseek_provider`)、P1-C 事件骨架(`runtime_events`)、P1-A 日志校验器、`game_engine.py` 的 dataclass 与共识解析模式。

---

## 1. Goal

把写死的剧本对局换成**一局真正自演化的狼人杀**:6 个角色全部 AI 驱动,夜晚行动 → 白天发言 → 真实唱票 → 出局 → 胜负判定,回合数动态。输出沿用现有 `EngineOutputs` 形状,直接喂给现有校验器/渲染器/cockpit。

**Success criteria**
- 一个新的 `EmergentGameEngine.run(seed)`,用 `DeterministicFakeProvider` 离线**确定性**跑完整局;同 seed 两次完全一致。
- 全部六类 AI 决策真实驱动:狼刀(共识)、预言家查验、女巫救/毒/弃权、白天发言、白天投票。
- 胜负与回合数**涌现**(不写死),含村民胜 / 狼人胜 / 回合上限三种收束。
- 任一 AI 非法输出 → 记一条 failure(现有 audit 形状)+ 确定性兜底,对局**必定走完**。
- 旧 `g1b/g1c/g1f` 剧本模式与其测试**一行不改**。
- 真实 DeepSeek 路径**接好**并通过 **1 次**手动冒烟(不进 CI);客户端永不碰 key。

---

## 2. Current state (verified)

- **`GameEngine.run()`(`game_engine.py:482`)是写死两轮剧本。** 预言家结果(`:695` 硬编码 "result: werewolf")、女巫救人(`:714`)、白天投票名单(`day1_voters=[...]` `:724`、`day2_voters` `:812`)、出局与揭示(`:746`/`:834`)、村民获胜(`:846`)全是字符串 emit。唯一真 AI 调用是 `_resolve_wolf_consensus`(`:293`,仅 `g1f_provider_consensus` 模式)。
- **可复用原语齐全:** `ProviderAgent.decide()`(`provider_agent.py:74`)已做完整 JSON / action / target 校验并抛 `ProviderActionError`;`ALLOWED_ACTIONS_BY_ROLE_PHASE`(`:19`)。`DeterministicFakeProvider`(`fake_provider.py:14`,键 `(actor,phase,round)`)。`EnginePlayer`/`GameConfig`/`AgentObservation`/`AgentAction`/`EngineOutputs` dataclass。`runtime_events` 的 `emit`/`write_snapshot`(见 `game_engine.py:506`、`:611`)。
- **关键发现 1:** `game_log.py:163` 仅校验字段**存在**(`event_id/sequence/round/phase/type/actor/target/visibility`),**无 type 枚举** → 新事件类型不破坏校验。
- **关键发现 2:** `player_speech`(发言)**已是约定** — `render_demo.py:41`、`render_provider_replay.py:34` 映射成 "发言",`scoring.py:750` 读取它。发言文本放进事件 `data.summary` 即可被现有渲染器显示。

---

## 3. Architecture

新文件 `src/werewolf_eval/emergent_engine.py`,类 `EmergentGameEngine`。**不动** `game_engine.py` 的旧逻辑(只从中 import 复用 dataclass / 共识模式)。

```
EmergentGameEngine(config, agents, wolf_agent, seed, runtime_events, budget) 
  .run() -> EngineOutputs              # 与 GameEngine 同输出形状

setup:   种子洗牌分配角色 → role_assignment 事件 + god 快照
loop(round r, 1..max_day_rounds≈3):
  ── NIGHT ──
    狼刀   ← 复用 _resolve_wolf_consensus 模式(存活狼真实提案 → 共识/裁定)→ 受害者 victim
    预言家 ← ProviderAgent.decide()  seer_check(存活非自己)→ 私有结果事件(visibility="seer",真角色查验)
    女巫   ← _resolve_witch_action(见 §5.2): witch_save(=victim,一次)/ witch_kill(存活,一次)/ witch_pass
    结算   ← 死亡 = victim(未被救) ∪ 被毒者 → player_died(visibility="all")
    胜负判定(§6)→ 命中即跳出
  ── DAY ──
    公布死讯(public)
    发言   ← 每个存活者 1 次 _resolve_speech(§5.3) → player_speech 事件(data.summary=自然文本)
            可见:本回合公共事件 + 本回合在它之前的发言(滚动累积)
    唱票   ← 每个存活者 ProviderAgent.decide() player_vote(存活目标)→ 计票
            最高票出局;平票 → 种子 RNG 在并列者中裁定 → player_eliminated + role_revealed(all)
    胜负判定(§6)→ 命中即跳出
到回合上限/预算耗尽仍未分胜负 → fail-closed 失败收束(§6,不产出完整 game_log)
end:  game_over(all) + 终局 god 快照
```

**复用映射(谁连到哪)**

| 子步骤 | 复用 | 说明 |
|---|---|---|
| 狼刀共识 | `_resolve_wolf_consensus` 模式 | 存活狼真实提案 → consensus / coordinator_tie_break |
| 预言家查验、白天投票 | `ProviderAgent.decide()` **原样** | 走现有 JSON+action+target 校验 → `ProviderActionError` |
| 女巫救/毒/弃权 | 新 `_resolve_witch_action` | 镜像 failure+fallback 模式,**不改 ProviderAgent**(§5.2) |
| 发言 | 新 `_resolve_speech` | 自然文本(非 JSON),独立轻调用(§5.3) |
| 事件/快照 | `runtime_events.emit/write_snapshot` | 同现有 cockpit 消费的事件流 |
| 输出 | `EngineOutputs`(game/decision/consensus/failure) | 过现有校验器/渲染器 |

---

## 4. Decisions(locked,owner 2026-06-05)

- **(a) 引擎 = 新 `EmergentGameEngine` 模块**,复用原语,旧剧本模式零碰。
- **(b) 健壮性 = 复用校验 + 确定性兜底**:非法输出 → 记 failure + 套合法兜底,对局必走完。
- **(c) "完成" = 先 fake+测试**(完整离线确定性整局 + 全测试绿)为门槛;真实 DeepSeek 接好 + 1 次冒烟(非 CI 整局)。
- **板子:** 6 人默认(p1/p2 狼、p3 预言家、p4 女巫、p5/p6 村民),本切片不做可配人数。
- **发言:** 3–5 句 / 120–180 字,每人每回合 1 次,无跨回合对辩;**prompt 强引导"判断/怀疑/理由/投票倾向"四要素,但不结构化校验、不 JSON、不因缺段判失败,仅长度截断 + 空输出兜底**。结构化摘要留待后续切片。
- **平票:** 种子 RNG 在并列最高票者中裁定(与角色分配共用同一 seeded RNG,确定性)。
- **预算闸(真实路径):** 每发言 `max_output_tokens≈180–250`;夜/投票 `≈80–120`;`max_day_rounds≈3`;每局 `max_requests≈60–80`;超限 fail-closed → `budget_exhausted`。

---

## 5. Data contracts(两处**加法式**扩展 + 一处事件)

### 5.1 player_speech 事件(复用既有约定)
发言发成事件:`type="player_speech"`,`actor=<player>`,`target="none"`,`visibility="public"`,`phase="day"`,`data.summary=<自然发言文本>`。无需改校验器(发现 1),渲染器已映射(发现 2)。

### 5.2 女巫动作 `_resolve_witch_action`(不改 ProviderAgent → 零 g1d/g1f 风险)
女巫的救/毒/弃权比统一动作契约更富,**单独**一个解析器(复用 `ProviderRequest/Response` + 同样的 failure+fallback 纪律),**不**走 `ProviderAgent.decide()`:
- 允许 `witch_save`(target 必须 = 今夜 victim;解药每局一次)/ `witch_kill`(target ∈ 存活;毒药每局一次)/ `witch_pass`(无 target)。
- 非法 / 解析失败 / 越权用药 → 记一条 `ProviderFailure`(kind=`invalid_action`/`parse_failure`)+ **兜底 = witch_pass**。
- (备选:扩 `ALLOWED_ACTIONS_BY_ROLE_PHASE` + 给无 target 动作放行 target 校验;因有 g1f 回归风险,**不推荐**,writing-plans 最终定。)

### 5.3 发言 `_resolve_speech`(自然文本,非 JSON)
- 发 speech-style `ProviderRequest`(为避免与投票在 `(actor,day,round)` 键冲突,请求 `phase="day_speech"`;事件仍记 `phase="day"`)。取 `response.raw_content` 为发言文本。
- 截断到长度上限;空 / 全空白 → 占位 `（发言无效）`;**不解析、不校验结构、不判失败**。
- Fake 脚本新增 `(actor,"day_speech",round)` 条目返回中文发言文本。

### 5.4 投票 / 预言家 / 狼刀
走现有路径,`AgentAction` 原样;`EngineOutputs` 的四个 log 由引擎累积(同现有形状),`is_consensus`/failure_audit 在有狼共识时产出。

---

## 6. 胜负与回合上限
- **村民胜:** 所有狼人死亡 → `result.winner="villager"`、`end_condition="all_werewolves_eliminated"`。
- **狼人胜:** 存活狼数 ≥ 存活非狼数(奇偶屠边) → `result.winner="werewolf"`、`end_condition="werewolves_reach_parity"`。
- **每夜结算后、每次白天出局后**各判一次。6 人板每昼必出 1 人、每夜可死人,故正常局必在 `max_day_rounds` 内收到真实胜负。
- **校验约束(已核对):** `game_log.py:137` 限定 `winner ∈ {villager, werewolf}`。因此**不引入 `inconclusive` winner**(否则破坏共享 P1-A 校验器)。
- **回合上限 / 预算耗尽仍未分胜负 = fail-closed 失败路径**(非游戏结局):**不产出完整 game_log**,改为返回失败结果 + `failure_audit`(kind=`budget_exhausted`/`round_cap`),镜像现有 provider-failure 收束模式(见 `run_fake_provider_game.py:104` 失败分支)。`EmergentGameEngine.run()` 以一个可区分的 `GameOutcome`(completed vs failed)表达,绝不伪造胜负。

---

## 7. 兜底矩阵(每种失败 → 对局仍走完)

| 子步骤 | 失败 | 处理 |
|---|---|---|
| 狼刀 | 提案非法/分裂 | 复用共识裁定:`coordinator_tie_break`,取首个合法提案 |
| 预言家 | `ProviderActionError` | 记 failure;兜底 = 查验座位序首个合法目标(或当夜不获信息) |
| 女巫 | 非法/越权用药 | 记 failure;兜底 = `witch_pass` |
| 发言 | 空/超限/异常 | 占位文本;不记 failure(发言非裁决步) |
| 投票 | `ProviderActionError` | 记 failure;兜底 = 弃权(不计票)或座位序首个合法目标(writing-plans 定) |
| 真实路径 | 预算超限 | fail-closed → `budget_exhausted` 失败收束(不产出完整 game_log,记 failure_audit) |
| 投票/夜晚 | `decision_type` 兜底 | 兜底决策记 `decision_type="default"`(∈ VALID_DECISION_TYPES) |

---

## 8. Testing(strict TDD,fake 默认离线)
- **整局确定性测试:** 固定 seed + `DeterministicFakeProvider` 脚本跑完整局;同 seed 两次输出逐字一致;四个 log 过现有校验器(`validate_game_log/decision_log/consensus_log/failure_audit`)。
- **单元:** 夜晚结算(救/毒/刀叠加)、种子平票裁定可复现、村民胜/狼人胜/回合上限三收束、女巫解药&毒药各一次约束、发言滚动可见性、发言长度截断与空输出兜底、**每类非法输出 → failure+兜底后对局仍走完**、预算超限 fail-closed。
- **回归:** 旧 `tests/test_game_engine.py`(g1b/g1c/g1f)全绿不变。
- **真实路径:** 复用 G3 launcher/`deepseek_provider` 接好 live 通道 + **1 次**手动冒烟(gated,非 CI;env 限制见 memory `werewolf-env-network-test-limits`:用 `docs/secrets/api-keys.md` 代码块里的完整 key,清代理变量)。

---

## 9. Definition of Done
1. `EmergentGameEngine` 离线 fake 跑完整局,同 seed 可复现,四 log 过校验。✅
2. 上述全部单元/整局/回归测试绿(18 新测试 + g1b/g1d 回归)。✅
3. 现有 cockpit 能读这局事件流(沿用 P1-C/P1-D,无需改协议)。✅(事件/可见性形状不变)
4. ~~真实 DeepSeek 通道接好,1 次手动冒烟~~ → **拆出为 P2-A-2**(owner 决定 2026-06-05)。

**实现期发现(2026-06-05):真实 live 涌现对局不是"薄接线",有两个真实前置依赖,故拆出 P2-A-2:**
- (i) **发言 prompt 路径缺失:** `deepseek_provider.py:73` 取 `allowed_actions[0]`,发言(空 allowed_actions)会 IndexError;live 发言需要独立 prompt 方法。
- (ii) **观察需文本化:** provider 把 `observation`(事件 **ID**,如 `p2a1_e017`)直接 dump 给模型(`:81`),LLM 无法据 ID 推理/发言;需把公共事件摘要 + 私有信息渲染进 prompt。
- 二者正是本 spec §11 标注的 live open risk;P2-A-1 以"离线确定性整局 + 全测试绿"为已批准 DoD 门槛收口,live 留给 P2-A-2 单独做(含真实冒烟)。

## 10. Non-goals(本切片不做)
- 漂亮的上帝视角观战 UI(= P2-C,下一切片;本切片用现有 cockpit 看)。
- 多轮交叉对辩、跨回合记忆深化、可配人数/板子、结构化发言摘要。
- 任何排行榜/评测聚合(= P3)。

## 11. Open risks
- 女巫无 target 动作的契约落点(§5.2 单独解析器 vs 扩 ProviderAgent)→ writing-plans 定;推荐单独解析器(零回归风险)。
- 真实路径**输入** token 随公共历史滚动增长是唯一真成本点 → 预算闸 + 紧凑历史控制。
- 投票兜底语义(弃权 vs 默认目标)对胜负可复现性的影响 → writing-plans 锁定并加测试。

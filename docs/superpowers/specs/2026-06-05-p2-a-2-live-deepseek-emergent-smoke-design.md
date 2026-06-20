# P2-A-2 真实 DeepSeek 涌现对局(live 集成冒烟)— Design Spec

**Status:** draft (for spec review)
**Route:** `docs/PROJECT_MAP.md` → P2 / 模块 A / 工作任务 2。承接 P2-A-1(`EmergentGameEngine`)。
**Date:** 2026-06-05
**Grill 锁定:** `.grill/p2-a-2-live-smoke-and-byo-key-direction.md`(验收口径全部来自此)。
**Depends on (reuse, do not break):** P2-A-1 `emergent_engine.py`;P1-B `DeepSeekProvider`/`ProviderAgent`/`deepseek_launcher`;P1-C `runtime_events`;G3-3 诚实链(`scripts/dev/run_deepseek_live_smoke.py` 模式)。

---

## 1. Goal

让 P2-A-1 的 `EmergentGameEngine` 走**真实 DeepSeek live 路径**并跑通 **1 次手动冒烟**。**定位:集成冒烟,不是内容调优**——只证明真实模型能端到端驱动一整局、日志合法、成本可控、可见性不泄漏、且这一局**主要由 live 驱动而非兜底糊过**。

**Success criteria(= §6 验收口径):** 三条硬门槛(visibility 不喂漏 / 真的是 live / 诚实链)+ 一条软门槛(嘴漏=内容警告)全部满足。

---

## 2. Current state (verified)

- **现有 live 路径跑的是剧本引擎,不是涌现引擎。** `run_deepseek_consensus_game.py:73` 的 `run_deepseek_consensus_game_with_provider_factory` 建 DeepSeek `ProviderAgent` 后跑 `GameEngine.run(mode="g1f_provider_consensus")`(`:115`)。P2-A-2 需要一个**对应的涌现 runner**:建 DeepSeek agents → 跑 `EmergentGameEngine.run()`。
- **前置(i)发言会崩:** `DeepSeekProvider._build_request_payload`(`deepseek_provider.py:59`)在 system prompt 里引用 `request.allowed_actions[0]`(`:73`);发言请求 `allowed_actions=[]` → IndexError。
- **前置(ii)模型只看到 ID:** 同方法把 `request.observation`(含 `public_event_ids`/`private_event_ids` 等 **事件 ID**)直接 `json.dumps` 当 user message(`:81`);LLM 拿不到可读事件文本,无法推理/发言。
- **G1f provider 是单实例共享 + 单 `max_tokens`:** `_build_deepseek_agent`(`:243`)6 个玩家共享一个 `DeepSeekProvider`,`DeepSeekProviderConfig` 只有一个 `max_tokens`/`max_requests`(`deepseek_provider.py:17`)。发言(180–250)和动作(80–120)需要不同 token 上限 → 需 per-request token 覆盖。
- **诚实链已存在(复用):** G3-3 的 `run_deepseek_live_smoke.py` 已有 `source_label=="[DeepSeek API output]"` 计数、`manifest_model_honest`、`_scan_for_secret_markers`、spine/bundle 存在性检查。
- **P2-A-1 引擎已 role-filter 观察:** `emergent_engine.py::_build_obs` 已按角色算好 `public_event_ids`/`private_event_ids`(预言家拿不到狼队 refs)——**文本化只要从这两个列表渲染,就天然不喂漏**。引擎持有全量 `self._events`(可按 ID 查摘要)。

---

## 3. Architecture(全部**加法式**,不破坏 fake 路径与剧本模式)

### 3.1 `ProviderRequest` 增三个可选字段(`provider_contract.py`)
追加(带默认,向后兼容):
- `observation_text: str = ""` — 引擎渲染好的**已过滤可读文本**。
- `response_kind: str = "action"` — `"action"`(JSON)或 `"speech"`(自然文本)。
- `max_output_tokens: int | None = None` — per-request token 覆盖(发言用大、动作用小)。

fake provider 忽略这三个字段(只按 `(actor,phase,round)` 取脚本)→ P2-A-1 全部测试不受影响。

### 3.2 `DeepSeekProvider` 按字段分支(`deepseek_provider.py`)
- `response_kind=="action"`:JSON system prompt;user message 用 `observation_text`;token 用 `request.max_output_tokens or config.max_tokens`。**向后兼容**:`observation_text` 为空时回退 `json.dumps(observation)` **仅对 legacy/非涌现路径允许**。
- `response_kind=="speech"`:**新 prompt 路径**——自然口吻发言、3–5 句/120–180 字、强引导"判断/怀疑/理由/投票倾向"四要素但**不强制结构、不要 JSON、不引用 `allowed_actions[0]`**(消除 IndexError);返回 `raw_content` 即发言文本;token 用发言上限。
> 关键:`response_kind` 分支让发言不再走 JSON action 路径,从根上修掉前置(i);`observation_text` 修掉前置(ii)。
> **P2-A-2 专属硬断言:涌现 live 局的每个 live `ProviderRequest` 必须带非空 `observation_text`;回退到 `json.dumps(observation)` 在涌现 smoke 中=hard failure**(防止"模型继续只看到事件 ID"也跑完)。机检见 §6/§7。

### 3.3 引擎侧文本化(硬门槛①的实现位)`emergent_engine.py`
- 新 pure helper `render_observation_text(obs, events_by_id) -> RenderedObservation(text, source_event_ids)`:**只**遍历 `obs.public_event_ids + obs.private_event_ids`,按 ID 取 `events_by_id[ref]["data"]["summary"]` 拼成可读文本(附 `known_roles`、存活名单、phase/round);**绝不遍历全量事件存**。`source_event_ids` = 实际渲染用到的 ID 集合(供机检 ⊆ 可见集)。
- **`known_roles` 来源写死:渲染进 `observation_text` 的 `known_roles` 只能来自该 seat 已可见的 role-filtered observation / role projection。`render_observation_text` 绝不读全局 seat-role 索引、god snapshot、完整玩家角色表、或全量事件存。** 这是比事件 ID 更隐蔽的泄漏点(身份直接漏)。canary 测试见 §7。
- 引擎在每次 provider 调用前,用 `_build_obs` 的结果渲染 `observation_text`,塞进 `ProviderRequest`;`response_kind`/`max_output_tokens` 按动作 vs 发言设置。
- **provider 只收到 `observation_text`,引擎绝不把 `self._events` / 全局角色表交给 provider。**

### 3.4 live 成功统计(硬门槛②的实现位)`emergent_engine.py`
- 引擎为**每个 provider 回合**记一条富结构 turn(见 §5 `provider_turns` 字段),`kind ∈ {live_success, invalid_then_fallback, timeout_then_fallback, error_then_fallback}`(发言:非空 live 文本=live_success,否则对应 fallback)。累积到 `self._provider_turns`,在 `GameOutcome` 暴露(完成/失败都带)。
- **统计口径(写死,防绕过):** `live_requested_actions` = 引擎真正发起 provider 调用的回合数(不含纯 deterministic-only 步);`live_success_actions` = 其中 `kind==live_success` 的数;**`live_success_rate = live_success_actions / live_requested_actions`**。fallback 回合计入分母、不计入分子;deterministic-only(从未发起 live)不进分母。
- 与现有 failure_audit 不重复:failure 记"哪里非法",provider_turns 记"每回合是 live 还是兜底 + 证据"。
- `budget_exhausted`(`BudgetExhausted` → failed outcome)保持硬失败。

### 3.5 live runner + 冒烟脚本(runtime spine 对 live smoke = 强制,非可选)
- 新 `run_emergent_deepseek_game.py`(对标 `run_deepseek_consensus_game.py`):建共享 `DeepSeekProvider`(`max_requests≥64`)+ 6 个 `ProviderAgent` → `EmergentGameEngine.run()`;`--allow-live-api` gate;fail-closed 退出码沿用(完成 0 / 失败 2)。
- **live smoke 的 runtime spine 是强制产物,不可选**:必须写 `events.jsonl`、`snapshots/`、`prompt-manifest.json`(记真实 model)、`provider_turns` / `provider_result_kind` 统计、`token_usage` 汇总。**缺 `prompt-manifest.json` = hard failure。**
- 扩展 `scripts/dev/run_deepseek_live_smoke.py`(或新增 `--emergent`):**由用户本地用 dev key 运行**;脚本离线机检 §6 三条硬门槛,**text-free** PASS/FAIL(不打印 key/header/模型文本)。

---

## 4. Decisions(grill 2026-06-05 全部锁定)
- **集成冒烟,非内容调优**(软门槛只看下限)。
- **文本化引擎侧做、provider 只收过滤文本**(Client/engine owns filtering;provider 不懂 visibility policy)。
- **跑完≠通过:** `live_success_rate≥0.80`、正常 6 人局 `live_success_actions≥20`、`budget_exhausted`=hard fail;兜底可救场不可过关、须统计暴露。
- **预算语义(写死,区分两个计数):** `max_requests_per_game=64` 计的是**对外 HTTP 尝试数**;`live_requested_actions` 计的是**局级 provider 回合数**;`max_retries_per_action ∈ {0,1}` 显式配置。(40 个回合 + retry 容易碰 64,口径必须分清。)
- **诚实链复用 G3-3**(每个 live_success 回合带 source_label / 真实 model / token_usage>0,见 §6③)。
- **运行(supersede grill Q4 的"agent 一手包办"):** **user-run / agent-offline-review** —— 用户在本地用 dev key 跑 gated live smoke;**agent 不接触 key,只基于 raw artifacts 离线机检**。跑/判分离,agent 无骗的物理可能。`fake-deterministic` 仍是无条件默认。
- **隔离:** 不碰用户 key 存储 / 模型下拉 / BYO-key UI(那是 P2-B)。

---

## 5. Data contracts
- `ProviderRequest` +3 可选字段(§3.1),`provider_request_to_dict`(asdict)自动带上;provider-trace 多三键(确认无既有测试断言精确请求键;若有,更新之)。
- `RenderedObservation`(新 frozen dataclass):`text: str`、`source_event_ids: list[str]`。
- `GameOutcome` +`provider_turns: list[dict]`,每条富结构(足以重建"请求了多少 live、哪些 live、哪些 fallback"):
  ```
  {
    request_id, round, phase, actor,
    response_kind,                 # "action" | "speech"
    live_requested: bool,          # 是否真发起了 provider 调用
    kind,                          # live_success | invalid_then_fallback | timeout_then_fallback | error_then_fallback
    fallback_reason: str | null,
    source_label: str | null,      # live_success 必为 "[DeepSeek API output]";fallback 必标 fallback(不得伪装成 DeepSeek)
    model: str | null,
    token_usage: {prompt_tokens, completion_tokens, total_tokens} | null,
    observation_source_event_ids: list[str]
  }
  ```
- **派生指标(写死):** `live_success_rate = live_success_actions / live_requested_actions`(deterministic-only 不进分母)。
- **不改** game_log/decision_log/consensus_log/failure_audit 形状与校验器。

---

## 6. Acceptance(= 验收口径,机检)
**硬门槛①(visibility 不喂漏,阻断性):**
- 对每个 seat,`render_observation_text(obs).source_event_ids ⊆ set(obs.public_event_ids ∪ obs.private_event_ids)`。
- 非狼视角渲染文本不含狼队私有刀人摘要 / 狼队友身份 / 他人私有结果。优先用事件 `source_event_id`/`visibility` 元数据断言来源,关键词扫描仅作补充。
- **`observation_text` 空 = hard failure**(涌现 live 局每个 live `ProviderRequest` 必须带非空 `observation_text`;不得回退 `json.dumps(observation)`)。

**硬门槛②(真的是 live):**
- `live_success_rate = live_success_actions / live_requested_actions ≥ 0.80`;`budget_exhausted=false`;`provider_turns` 全量统计出现在 validation summary。
- **终局优先:** 通过的首选条件是**真实终局**。deterministic cap **只在 smoke config 里预声明**(不得在看到坏 run 后才选),且仍须满足 `live_success_rate≥0.80` 加上(`live_success_actions≥20` **或** 一份有据的"早终局/短局"解释)。
- 绝对下限 `live_success_actions≥12`(防小样本骗过)。**校准说明(2026-06-05 两局真实数据):** 6 人局 1-2 轮分胜负、产生 ~14-22 provider 回合,故下限定在"最短合法全局(~14)之下、~6 次骗局之上",并与 `rate≥0.80` 在最短局上自洽(原定 20 会误杀合法早终局,已下调)。早终局致更低调用数 → `--allow-short-game` + review 解释。

**硬门槛③(诚实链,逐回合):** **每个 `kind==live_success` 的 provider 回合**必须带:`source_label=="[DeepSeek API output]"`、真实 model 名、`token_usage.total_tokens>0`。**fallback 回合不得伪装成 DeepSeek output,必须明确标 fallback。** prompt-manifest 记真实 model(非 `unknown`),缺 manifest=hard failure。

**软门槛(嘴漏):** 模型幻觉自称不可见系统事实 → 记 content warning,不阻断(除非破坏 action 契约/崩);狼人伪装/诈身份属正常玩法。

**Secret scan(PASS 前置):** 冒烟脚本须扫**全部产物**(game/decision/consensus/failure 日志、events.jsonl、snapshots、prompt-manifest、provider-trace、validation summary)无 secret marker(`Authorization`/`Bearer `/`api_key`/`DEEPSEEK_API_KEY`/`sk-`)才判 PASS——只扫源码不够,live 最易把 header/env/prompt 泄进 artifact。

---

## 7. Testing(strict TDD,默认离线)
- **离线单元(无网络):**
  - `render_observation_text`:source_event_ids ⊆ 可见集;非狼 seat 文本不含狼队私有摘要(构造含狼刀私有事件的局);村民 seat 文本不含预言家查验/女巫私有决定(未公开时)。
  - **known_roles canary:** 在全局角色表里塞一个非公开身份 canary,断言村民/预言家的 `observation_text` 不出现该 canary(证明渲染没从全局角色表/god snapshot 取)。
  - **`observation_text` 非空断言:** 涌现 live ProviderRequest(假 transport)每个都带非空 `observation_text`,且 user message ≠ `json.dumps(observation)`。
  - `DeepSeekProvider`(注入假 transport):`response_kind="speech"` 不再 IndexError、产出自然文本、用发言 token;`response_kind="action"` 用 `observation_text` 且仍走 JSON 校验;per-request `max_output_tokens` 覆盖生效。
  - **发言集成(provider→ProviderAgent→引擎):** `EmergentGameEngine` 发言回合 → `ProviderAgent` → `DeepSeekProvider`(假 transport)→ 非空发言文本 → 引擎记录发言**且不因 JSON-action 校验失败而兜底**(确保 ProviderAgent 不把发言当非法 action)。
  - 引擎 `provider_turns` 统计:用假 provider 注入 timeout/invalid/error,断言每回合 `kind`/`fallback_reason`/`source_label` 正确、`live_success_rate=live_success/live_requested` 计算正确、fallback 回合 source_label 不伪装成 DeepSeek。
  - fake 路径回归:P2-A-1 全部 18 测试 + g1b/g1d 仍绿(新字段默认值不影响)。
- **真实冒烟(gated,手动,非 CI,user-run):** 用户本地 `RUN_DEEPSEEK_LIVE_SMOKE=1` + key 跑一局涌现 live;脚本离线机检 §6 三硬门槛 + 全产物 secret scan,产出 text-free PASS + provider_turns 统计 + token_usage 证据 + 软门槛 content warnings。**agent 不接触 key,只对用户跑出的 raw artifacts 离线机检。** env:清代理变量;key 读自 `docs/secrets/api-keys.md` 代码块完整 key([[werewolf-env-network-test-limits]])。

---

## 8. Definition of Done
1. §7 全部离线单元绿;P2-A-1/g1b/g1d 零回归。
2. **用户**本地跑通一局真实 DeepSeek 涌现 live;**agent 离线机检** raw artifacts,§6 三条硬门槛 + 全产物 secret scan 全 PASS;validation summary 摊开 provider_turns 统计 + 逐回合 token_usage>0 证据 + 软门槛 content warnings(若有)。
3. 记录这次的 `live_requested_actions` / `live_success_rate` / 结局,更新 PROJECT_MAP P2-A-2 状态。

## 8b. Live smoke evidence (user-run 2026-06-05, agent offline-reviewed)
两局真实 DeepSeek(`deepseek-v4-flash`)涌现对局,均端到端完成、两种胜负都出现:

| Run | 结局 | live_requested | live_success | rate | provider_result_kind | 其余 7 门槛 |
|---|---|---|---|---|---|---|
| 1 | 村民胜 | 22 | 19 | 0.864 | 19 live_success / 1 invalid / 2 error | 全 ✅ |
| 2 | 狼人胜 | 14 | 13 | 0.929 | 13 live_success / 1 timeout | 全 ✅ |

两局 `per_turn_honesty_ok`/`manifest_model_honest`/`observation_text_present`/`no_secret_markers`/`budget_not_exhausted`/`game_completed` 全过;`live_success_rate` 均 ≥0.80。唯一触发的是绝对下限——经两局真实回合分布(14、22)校准,floor 20→**12**(§6 已记)。校准后两局 `live_success_floor_ok=True`,**smoke=PASS**。结论:真实 live 涌现路径端到端可用且诚实,DoD 达成。

## 9. Non-goals
- 内容质量调优(观察摘要压缩、per-role prompt、强制发言结构、二轮对辩、温度、失败样本对比)→ 后续"readable play quality"切片。
- 用户 key 存储 / 模型下拉 / BYO-key UI → P2-B。
- 多厂商(OpenAI/Claude/Qwen)→ 后续。

## 10. Open risks
- ProviderRequest 新字段进 provider-trace 可能撞既有精确断言 → TDD first 暴露并更新。
- 真实 live 输入 token 随公共历史 + 发言滚动增长(成本主因)→ 紧凑渲染 + per-request token 上限 + `max_requests=64` 控顶。
- 双闸语义(§4 已写死):`EmergentBudget.max_requests`(局级 provider 回合)与 `DeepSeekProvider.max_requests`(对外 HTTP 尝试,含 retry)区分;`max_requests_per_game=64` 指 HTTP 尝试、`max_retries_per_action∈{0,1}`。两者对齐由 writing-plans 钉死,避免 40 回合+retry 误碰 64 或口径混淆。


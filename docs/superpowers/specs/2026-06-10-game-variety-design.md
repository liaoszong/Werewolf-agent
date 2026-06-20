# 对局多样性设计(子集 1/2):per-seat persona + 温度策略(2026-06-10)

**状态**:DESIGN(用户已审 r1,r2 修订:组 4 重写 + 组 1 措辞收紧 + 温度可观测性)
**动机来源**:`historical harness review 2026-06-10-live-game-sameness-and-prompt-leak-investigation.md`。
**范围裁决**:用户定 = 本 spec **只做真·无冲突子集 ② per-seat persona + ③ 温度**。① 角色洗牌经查证落不进无冲突子集(§1.1),另立 spec、排并行 prompt-versioning 线合并后。

---

## 1. 范围

**做(IN)** —— 只碰 `profile_config.py` + `seat_agents.py`,**零避让区**:
- ② **per-seat persona 拼接**:同角色两座位不再克隆。persona = 角色策略(跟角色,来自 `role_defaults[role].prompt`,可被 `seat_overrides[seat].prompt` 覆盖)+ 座位个性(跟座位,role-agnostic,来自新字段 `seat_personas[seat]`),都是 profile 配置输入(非模板)。
- ③ **温度策略**:live/默认 profile 缺省温度 0.8,显式座位温度永远优先。

**不做(OUT)**:① 角色洗牌(deferred §1.1)、候选顺序随机化、出局公开真身、任何 prompt 模板字节(`build_action_system_prompt`/`build_speech_system_prompt`/`compose_system`/`render_observation_text`/`augment_witch_observation`/猎人后缀)。

### 1.1 为何 ① 角色洗牌被排除(查证记录,用户复核为真)
- live 路径 `run_emergent_deepseek_game.py:143` 用 `config=build_emergent_config(game_id)`;`build_emergent_config`(emergent_engine.py:226)= 固定板子 `build_default_config`,**无角色入参**。引擎角色 = 此固定 config;`resolved_seats[].role` 只入 **provider 路由 + artifact 显示**,**不进引擎**。今天一致纯属都等于 DEFAULT_6P 的巧合。
- 故在 profile 层洗 `resolved_seats.role`:不改变实际对局,且使 p1 拿洗后角色的 persona 却被引擎按 DEFAULT_6P 打 → **persona/角色错位 + artifact 与对局不符**,比不洗更糟。
- 真正洗牌须改 `build_emergent_config`(emergent_engine.py,避让区)+ `run_emergent_deepseek_game.py`(run_*.py,避让区)——正是并行线在改的文件。故 ① deferred(届时引擎角色板加 `seat_roles` 入参、runner 传洗后角色、resolved_seats 对齐、seed 落盘)。

---

## 2. 不变量(实现纪律)

1. **向后兼容逐字节(约束 5,措辞收紧)**:**任意旧 profile**(无 `seat_personas`,**不论座位温度是否为 null**)经 `_resolve_seat` / `resolve_profile` / `build_resolved_profile_artifact` 的**现有字段输出逐字段不变**(允许 §5 的 additive 新字段)。`resolve_profile` 签名与行为不变(不新增洗牌入口,不碰 observer)。
2. **persona 拼接在配置层**(`_resolve_seat`),只产出 persona 字符串喂给**未改动**的 `compose_system`。不触碰任何模板字节。
3. **0.8 兜底单点**:温度兜底**只**发生在 `build_seat_agents`(装配层),**绝不**进 `_resolve_seat`/resolve 层——否则破坏不变量 1。组 1 测试以此为靶(见 §6 组 1)。
4. **离线 fake 路径与温度管道零交集(措辞改正)**:fake 对局走 server 的**默认 fake launcher**,**根本不经过** `build_seat_agents`/`ChatProviderConfig`/`DEFAULT_LIVE_TEMPERATURE`(`PROVIDER_REGISTRY` 无 `fake_deterministic`,`build_seat_agents` 对 fake 座位本就 `ValueError`)。故 fake 对局字节不变的成立机理是**管道不相交**(非"fake provider 忽略温度"),由现有 fake-determinism canary 背书。

> 修订记:r1 的不变量 4 误写为"fake provider 忽略温度→对局字节不变";用户查证 `DeterministicFakeProvider` 虽不读温度,但它根本不会被这条管道构造。机理更正为"管道零交集"。

---

## 3. 组件 ② — per-seat persona 拼接(`profile_config.py`)

### 3.1 新 profile 字段
```jsonc
"seat_personas": { "p1": "……", "p2": "……", ... }   // 缺省 = {} = 等于今天
```
**约束 4:`seat_personas` 必须 role-agnostic**——只写性格/语气/表达习惯,**禁止**写角色能力或阵营策略(如"你是狼/夜晚击杀/查验")。理由:① 洗牌将来落地后个性跟座位走,写角色策略会与座位实际角色冲突;② 保持"策略归角色、个性归座位"分层。语义不可机器强校,故在**字段 docstring + validator 校验错误信息 + 本 spec** 三处文档声明 + 评审把关。

### 3.2 `_resolve_seat` 组装(唯一改动点)
```
role_strategy = merged.get("prompt", "")          # 现有解析:role_defaults[role].prompt 被 seat_overrides[seat].prompt 覆盖(不变)
personality   = profile.get("seat_personas", {}).get(seat, "")
prompt = role_strategy if not personality else (
           personality if not role_strategy else f"{role_strategy}\n\n{personality}")
```
- 两只狼(p1/p2,均 werewolf 策略)+ 各自不同 `seat_personas` → persona 不相等 = 不再克隆。
- **向后兼容**:无 `seat_personas` → `prompt = role_strategy` = 今天逐字节相同。
- `validate_profile`(:304 → `_check_resolved_seat`:257)按**拼接后** prompt 校验长度(`PROMPT_MAX_LEN`),即真实下发 persona 长度。

### 3.3 默认 profile 种入(约束 5:与旧 profile parity 分开)
`build_default_profile` 给 6 座位种入**各不相同**的 role-agnostic `seat_personas`(开箱即两狼不克隆,作为规范示例)。**这是"默认 profile 内容变更",与"旧 profile 缺省解析逐字节不变"是两类事,测试分组(§6 组 1 vs 组 5)。** 温度不种进 build_default_profile(见 §4.2,单源于常量,避免 fake 模板记录 live 采样参数)。

### 3.4 落地范围说明(诚实点,含期望管理)
- 本组件交付**机制**(`seat_personas` 字段 + 拼接)+ 默认 profile 种入。**用户已存在的 live deepseek profile 不含 `seat_personas` → 其两狼仍克隆**,直到该 profile 被填入 `seat_personas`(因约束 5 不能在解析层对缺省 profile 自动注入个性——会破坏逐字节兼容)。
- 填充途径:**编辑该 profile 的 JSON**(已验证 Qt `MatchSetupView.qml:60` 对整个 profile 做 JSON 深拷贝、只改已知键、整 dict 回传 → 手填 `seat_personas` 不会被现有客户端剥掉,该途径成立),或从更新后的默认 profile 重新派生;在 Qt 设置页暴露 `seat_personas` 编辑入口属 **UI 跟进(clients/ + observer,范围外)**。
- **期望管理**:调查报告定性洗牌=根因 A、persona=加剧因素。本子集主打"**发言/风格克隆**";**夜 1 动作收敛(最小序号目标)在 ① 角色洗牌落地前可能仍明显**。落地后若观察三局夜 1 仍雷同,属预期(机制未失效),勿误判。

---

## 4. 组件 ③ — 温度策略(`seat_agents.py` + 常量)

### 4.1 政策框定(用户裁定)
- `default_temperature = 0.8` 是 **live/默认 profile 的多样性策略**,**不是** prompt/rendering 策略。
- **显式 `seat.temperature` 永远优先**。
- **离线 fake 确定性绝不依赖温度**(§2 不变量 4 = 管道零交集)。

### 4.2 实现
- 新增命名常量 `DEFAULT_LIVE_TEMPERATURE = 0.8`,定义于 `profile_config.py`(使装配层 `build_seat_agents` 与配置层 `build_resolved_profile_artifact` 共用单源;依赖方向 seat_agents→profile_config,无环——profile_config 不反依赖 seat_agents)。`seat_agents.py` 从 profile_config import 该常量。
- `build_seat_agents(..., default_temperature: float = DEFAULT_LIVE_TEMPERATURE)`:座位 `temperature` 为 `None` → 套 `default_temperature`;非 None → 原样透传(显式优先)。
- 签名默认值生效 → 现有唯一调用方 `deepseek_launcher.py:252`(**非避让区**,调用未传 temperature)自动让 live 局拿到 0.8;fake 路径不经此管道(§2-4)。**无需改 deepseek_launcher。**
- **不**种进 `build_default_profile`(全 fake 模板,种 0.8 零效力且让 fake artifact 记录 live 采样参数=单源张力)。温度政策单源于常量;运行期生效 + 工件可观测由 §5 的 `effective_temperature` 承载。

---

## 5. resolved-profile.json schema 增量(温度可观测性)

**问题(用户指出)**:生效温度 0.8 在所有工件里无痕——`build_resolved_profile_artifact` 记录的是 resolve 层值(null),provider-trace 的 `request.temperature` 也 null(温度在 config 层、`_effective_temperature` 运行时才取)。后果:旧 live 局(API 默认温度)与新 live 局(0.8)工件上不可区分,改 `DEFAULT_LIVE_TEMPERATURE` 无从考古——与 repo 的 manifest-honesty 文化(G3-3/A3)+ 并行线评测可比性有张力。

**解(零避让区,additive)**:`build_resolved_profile_artifact`(profile_config.py 自建)对每座位加 **additive** 字段:
```jsonc
"seats": [ { "player_id":"p1", ..., "temperature": null, "effective_temperature": 0.8 }, ... ]
```
- `temperature` 字段语义**明文声明**:= **显式配置值**(`null` = 未配置,运行期由 `build_seat_agents` 兜底)。
- `effective_temperature` = `seat.temperature if seat.temperature is not None else DEFAULT_LIVE_TEMPERATURE`(从同一常量算,与运行期生效值一致)。
- 其余现有字段保持不变;`prompt_hash` 随拼接后 persona 改变(内容,非结构)。
- **additive 约定**:消费方须容忍未知字段(组 1 措辞已改为"现有字段逐字段相同 + 允许 additive 新字段")。
- 更广的温度可观测(如 provider-trace 落生效温度)挂 §8 deferred(那条路径在避让区)。

---

## 6. 测试策略(分组,约束 5)

**组 1 — 旧 profile 向后兼容 parity(靶向错误兜底)**
- **任意旧 profile**(无 `seat_personas`,**温度 null 与显式两种 case 都测**)→ `_resolve_seat`、`resolve_profile`、`build_resolved_profile_artifact` 的**现有字段**与改前**逐字段相等**(用改前快照或等价断言;additive `effective_temperature` 单列断言,不计入"现有字段"比对)。
- **专门靶住错误实现**:断言温度 null 的旧 profile 经 `_resolve_seat`/`resolve_profile` 解析出的 `temperature` 仍为 `null`(若实施者错把 0.8 兜底做进 `_resolve_seat`,此断言失败)。0.8 只能在 `build_seat_agents` 出现。

**组 2 — per-seat persona 拼接**
- 拼接顺序:策略在前、个性在后,中间 `\n\n`;`role_strategy` 空 → 只剩个性;`personality` 空 → 只剩策略。
- 两座位同 werewolf 策略 + 不同 `seat_personas` → persona 不相等。
- **叠加 case**:`seat_overrides[seat].prompt`(覆盖角色策略)**+** `seat_personas[seat]` 同时存在 → `prompt = 覆盖后的策略 + "\n\n" + 个性`(验证两来源正交叠加)。
- `_check_resolved_seat` 对拼接后超长 prompt 报错(长度按拼接后算)。

**组 3 — validator 接纳新字段**
- `seat_personas` 键 ∈ `DEFAULT_SEAT_IDS`、值为 str、经 `_reject_secret_like_values` 扫描;缺省/空通过;非法键/类型报错;`validate_profile` 的 `allowed_top` 纳入 `seat_personas`;错误信息含 role-agnostic 文档声明。

**组 4 — 温度(重写:fake 无可执行温度路径)**
- **live/可接受 provider 座位**(注册 provider + 注入 transport/credential 或检视 `ChatProviderConfig`):座位温度 `None` → 建出的 provider config `temperature == DEFAULT_LIVE_TEMPERATURE`;显式值 → 不被覆盖。
- **fake 座位现状不变**:`build_seat_agents` 对 `provider="fake_deterministic"` 座位仍抛 `ValueError("no credential ...")`(锁住"fake 不进温度管道"的现状)。
- **fake 路径不引用温度**:断言默认 fake launcher 路径不 import/引用 `DEFAULT_LIVE_TEMPERATURE`;fake 对局字节不变由**现有 fake-determinism canary** 背书(本 spec 不重造)。

**组 5 — 默认 profile 内容(与组 1 分开)**
- `build_default_profile` 含 6 个互不相同的 `seat_personas`(role-agnostic);校验通过;两狼 persona 不相等;**不含** `temperature`(单源于常量)。

---

## 7. 改动文件清单

- `src/werewolf_eval/profile_config.py`:`DEFAULT_LIVE_TEMPERATURE` 常量、`_resolve_seat`(persona 拼接)、`validate_profile`(接纳 + 文档化 `seat_personas`)、`build_default_profile`(种 `seat_personas`)、`build_resolved_profile_artifact`(additive `effective_temperature` + `temperature` 语义注释)。
- `src/werewolf_eval/seat_agents.py`:import `DEFAULT_LIVE_TEMPERATURE`、`build_seat_agents` 的 `default_temperature` 兜底。
- 测试:`tests/test_profile_config.py` / `tests/test_seat_agents.py`(或新增 `tests/test_game_variety.py`)。
- **零避让区文件**。

---

## 8. 显式 deferred

- **① 角色洗牌**:须改引擎角色板(emergent_engine.py + run_emergent_deepseek_game.py,避让区),另立 spec,排并行 prompt-versioning 线合并后。
- **更广温度可观测性**:provider-trace 落生效温度(该路径在避让区);本 spec 仅在 resolved-profile.json 加 `effective_temperature`。
- per-seat persona 在 Qt 客户端的编辑入口(UI 跟进)。
- per-seat persona 的 role-agnostic 语义机器校验(暂文档 + 评审把关)。
- live 路径 `seed=0` 写死(查证副产物,与本设计无关,记录备查)。


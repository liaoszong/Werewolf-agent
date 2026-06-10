# 对局多样性设计(子集 1/2):per-seat persona + 温度策略(2026-06-10)

**状态**:DESIGN(待用户审)
**动机来源**:`docs/harness/reviews/2026-06-10-live-game-sameness-and-prompt-leak-investigation.md`(live 对局雷同的根因:角色按座位写死无洗牌 + 模型对固定布局收敛 + 同角色共用 persona)。
**范围裁决**:用户定 = 本 spec **只做真·无冲突子集 ② per-seat persona + ③ 温度**。① 角色洗牌经查证落不进无冲突子集(见 §1.1),另立 spec、排在并行 prompt-versioning 线合并后。

---

## 1. 范围

**做(IN)** —— 只碰 `profile_config.py` + `seat_agents.py`,**零避让区**:
- ② **per-seat persona 拼接**:同角色两座位不再克隆。persona = 角色策略(跟角色,来自 `role_defaults[role].prompt`)+ 座位个性(跟座位,role-agnostic,来自新字段 `seat_personas[seat]`),都是 profile 配置输入(非模板)。
- ③ **温度策略**:live/默认 profile 缺省温度 0.8,显式座位温度永远优先。

**不做(OUT)**:
- ❌ **① 角色洗牌**(deferred,见 §1.1)。
- ❌ 随机化候选玩家顺序(等 prompt 版本化机制)。
- ❌ 改"出局公开真身"(rules_version bump,排版本化之后)。
- ❌ 改任何 prompt 模板字节:`build_action_system_prompt` / `build_speech_system_prompt` / `compose_system` / `render_observation_text` / `augment_witch_observation` / 猎人后缀(并行线字节锁)。

### 1.1 为何 ① 角色洗牌被排除(查证记录)
- live 路径 `run_emergent_deepseek_game.py:143` 用 `config=build_emergent_config(game_id)`;`build_emergent_config`(emergent_engine.py)= 固定板子 `build_default_config`("p1/p2 狼、p3 预言家、p4 女巫、p5/p6 民"),**无角色入参**。
- 引擎角色 = 这个固定 config;`resolved_seats[].role` 只用于 **provider 路由 + artifact 显示**,**不进引擎**。今天两者一致纯属都等于 DEFAULT_6P 的巧合。
- 故在 profile 层洗 `resolved_seats` 的 role:不改变实际对局,且使 p1 拿到洗后角色的 persona 却被引擎按 DEFAULT_6P 角色打 → **persona/角色错位 + artifact 与对局不符**,比不洗更糟。
- 真正洗牌须改 `build_emergent_config`(emergent_engine.py,避让区)+ `run_emergent_deepseek_game.py`(run_*.py,避让区)——正是并行线在改的文件。故 ① 不属无冲突子集,deferred 到 `docs/superpowers/specs/<later>-role-shuffle-design.md`,在那条线合并后做(届时引擎角色板要加 `seat_roles` 入参、runner 传洗后角色、resolved_seats 对齐、seed 落盘)。

---

## 2. 不变量(实现纪律)

1. **向后兼容逐字节(约束 5)**:无 `seat_personas`、座位温度显式给定时,`_resolve_seat` / `resolve_profile` / `build_resolved_profile_artifact` 输出与今天**逐字段相同**。`resolve_profile` 签名与行为**不变**(不新增洗牌入口,不碰 observer)。
2. **persona 拼接在配置层**(`_resolve_seat`),只产出 persona 字符串,喂给**未改动**的 `compose_system`。不触碰任何模板字节。
3. **parity 线无关**:字节 parity 测试走 `build_emergent_config`(另一路径),不经 `resolve_profile`/`build_seat_agents`,本设计不影响。
4. **离线 fake 确定性不依赖温度(约束:温度政策)**:`fake_deterministic` provider 忽略温度;无论 `default_temperature` 取何值,fake 对局 game-log 逐字节不变(见 §6 测试组 4)。

---

## 3. 组件 ② — per-seat persona 拼接(`profile_config.py`)

### 3.1 新 profile 字段
```jsonc
"seat_personas": { "p1": "……", "p2": "……", ... }   // 缺省 = {} = 等于今天
```
**约束 4:`seat_personas` 必须 role-agnostic**——只写性格/语气/表达习惯(如"谨慎、重逻辑、发言简洁"),**禁止**写角色能力或阵营策略(如"你是狼/夜晚击杀/查验")。理由:① 洗牌将来落地后个性跟座位走,写角色策略会与座位实际角色冲突;② 保持"策略归角色、个性归座位"的干净分层。语义不可机器强校,故在**字段 docstring + validator 校验错误信息 + 本 spec** 三处文档声明,并由评审把关。

### 3.2 `_resolve_seat` 组装(唯一改动点)
```
role_strategy = merged.get("prompt", "")          # 现有解析:role_defaults[role].prompt 被 seat_overrides[seat].prompt 覆盖(不变)
personality   = profile.get("seat_personas", {}).get(seat, "")
prompt = role_strategy if not personality else (
           personality if not role_strategy else f"{role_strategy}\n\n{personality}")
```
- 两只狼(p1/p2,均 werewolf 策略)+ 各自不同 `seat_personas` → persona 不相等 = 不再克隆。
- **向后兼容**:无 `seat_personas` → `prompt = role_strategy` = 今天逐字节相同。
- `validate_profile` 路径(`_check_resolved_seat`)按**拼接后**的 prompt 校验长度(`PROMPT_MAX_LEN`),即真实下发 persona 的长度。

### 3.3 默认 profile 种入(约束 5:与旧 profile parity 分开)
`build_default_profile` 给 6 座位种入**各不相同**的 role-agnostic `seat_personas`(开箱即两狼不克隆,作为规范示例)。**这是"默认 profile 内容变更",与"旧 profile 缺省解析逐字节不变"是两类事,测试分组(§6 组 1 vs 组 5)。**

### 3.4 落地范围说明(重要,诚实)
本组件交付的是**机制**(`seat_personas` 字段 + 拼接)+ 默认 profile 种入。**用户已存在的 live deepseek profile 不含 `seat_personas` → 其两狼仍克隆**,直到该 profile 被填入 `seat_personas`(因约束 5 不能在解析层对缺省 profile 自动注入个性——那会破坏逐字节兼容)。填充途径:编辑该 profile 的 JSON,或从更新后的默认 profile 重新派生;**在 Qt 客户端设置页暴露 `seat_personas` 编辑属 UI 跟进(clients/ + observer,本 spec 范围外)**。

---

## 4. 组件 ③ — 温度策略(`seat_agents.py`)

### 4.1 政策框定(用户裁定)
- `default_temperature = 0.8` 是 **live/默认 profile 的多样性策略**,**不是** prompt/rendering 策略。
- **显式 `seat.temperature` 永远优先**。
- **离线 fake 确定性绝不依赖温度**(§2 不变量 4 / §6 组 4)。

### 4.2 实现
- `seat_agents.py` 新增命名常量 `DEFAULT_LIVE_TEMPERATURE = 0.8`。
- `build_seat_agents(..., default_temperature: float = DEFAULT_LIVE_TEMPERATURE)`:座位 `temperature` 为 `None` → 套 `default_temperature`;非 None → 原样透传(显式优先)。
- 签名默认值生效 → 现有调用方(`deepseek_launcher.py:252`,**非避让区**,调用时未传 temperature)自动让 live 局拿到 0.8;`fake_deterministic` 忽略温度 → fake 对局不变。**无需改 deepseek_launcher。**
- `build_default_profile` 同时把 `role_defaults[*].temperature = 0.8` 种入(使新默认 profile 在 artifact 里显式记录该温度;其他 profile 运行期由 `build_seat_agents` 默认兜底)。

---

## 5. resolved-profile.json schema 增量

仅 `seats[].prompt_hash` 的**内容**会随拼接后的 persona 改变(字段结构不变);默认 profile 的 `seats[].temperature` 记录为 0.8。无新增顶层块。旧记录解析不受影响。

---

## 6. 测试策略(分组,约束 5)

**组 1 — 旧 profile 向后兼容 parity(不得碰)**
- 无 `seat_personas`、座位温度显式 → `_resolve_seat`、`resolve_profile`、`build_resolved_profile_artifact` 输出与改前**逐字段相等**。

**组 2 — per-seat persona 拼接**
- 拼接顺序:策略在前、个性在后,中间 `\n\n`;`role_strategy` 空时只剩个性;`personality` 空时只剩策略。
- 两座位同 werewolf 策略 + 不同 `seat_personas` → persona 不相等。
- `_check_resolved_seat` 对拼接后超长 prompt 报错(长度按拼接后算)。

**组 3 — validator 接纳新字段**
- `seat_personas` 键 ∈ `DEFAULT_SEAT_IDS`、值为 str、非 secret;缺省/空通过;非法键/类型报错;错误信息含 role-agnostic 文档声明。

**组 4 — 温度**
- 座位温度 `None` → 套 `default_temperature`;显式值 → 不被覆盖。
- **fake 确定性(不变量 4)**:对 `fake_deterministic` 座位,`default_temperature` 取 0.0 / 0.8 / 1.0,对局 game-log 逐字节相同。

**组 5 — 默认 profile 内容(与组 1 分开)**
- `build_default_profile` 含 6 个互不相同的 `seat_personas`(role-agnostic)+ `temperature=0.8`;校验通过;两狼 persona 不相等。

---

## 7. 改动文件清单

- `src/werewolf_eval/profile_config.py`:`_resolve_seat`(persona 拼接)、`validate_profile`(接纳 + 文档化 `seat_personas`)、`build_default_profile`(种 `seat_personas` + `temperature=0.8`)。
- `src/werewolf_eval/seat_agents.py`:`DEFAULT_LIVE_TEMPERATURE` + `build_seat_agents` 的 `default_temperature` 兜底。
- 测试:`tests/test_profile_config.py` / `tests/test_seat_agents.py`(或新增 `tests/test_game_variety.py`)。
- **零避让区文件**。

---

## 8. 显式 deferred

- **① 角色洗牌**:须改引擎角色板(emergent_engine.py + run_emergent_deepseek_game.py,避让区),另立 spec,排并行 prompt-versioning 线合并后。
- per-seat persona 在 Qt 客户端的编辑入口(UI 跟进)。
- per-seat persona 的 role-agnostic 语义机器校验(暂文档 + 评审把关)。
- live 路径 `seed=0` 写死(查证副产物,与本设计无关,记录备查)。

# P2 Spec — Observer Server → EmergentGameEngine Bridge

> **类型:** 设计 spec（design-only）。**不含实现。** 本文档只读现有代码、画接口/数据流/迁移/风险/测试,
> 并为后续实现者锁定 allowlist / forbidden scope / acceptance。
> **日期:** 2026-06-06 · **修订:** 2026-06-06 r2(经审查修正 4 处:game_over visibility 误读、live launcher
> budget exit-code、artifact allowlist 表述、/projection 可见性通道)。
> **分支语境:** 与 `p2-d-settlement-screen` 并行起草,**不碰任何在途代码文件**。
> **定位:** P2-C / P2-D 之后的下一段关键路径 —— 让 observer server 的 run-launch 路径从旧 scripted/fake
> runtime,安全接入 P2-A `EmergentGameEngine`,同时继续兼容 Qt observer、visibility projection、
> settlement bundle、fake/live 模式与 review gate。
>
> **状态: 待实现。** 本 slice 的实现被 P2-D 阻塞(改动点 `observer_server.py` 正被 P2-D 占用),
> 故现在只定设计,P2-D 合并、`observer_server.py` 释放后再落地(符合「锁上不锁下」)。

---

## 0. TL;DR(给赶时间的人)

- **Gap 本质:** observer 的两条 launcher(fake 默认 + live opt-in)**今天跑的都是旧 scripted runtime**,
  没有一条接 `EmergentGameEngine`。
- **最小适配缺口(keystone):** **fake 涌现 runner(`run_emergent_game.py`)没有接 `RuntimeEventWriter`**
  → 不产 `events.jsonl`/snapshots/`prompt-manifest.json`,observer 无法流式观战。live 涌现 runner
  (`run_emergent_deepseek_game.py`)**已经**接了 writer,产物已是 observer 形状。
- **最小实现切片:** 新增一个 **fake 涌现 launcher**(把 `RuntimeEventWriter` 接进 `EmergentGameEngine` 的
  fake-script 路径,写全套 artifact,契合 `(run_id, run_dir) -> int` 契约),在 `run_observer_server.py`
  接线层把 fake/live 两个 launcher **替换**为涌现版。**`observer_server.py` / `observer_protocol.py` /
  Qt / 协议常量全部零改动**。
- **协议零改动可行性已核实:** 涌现局**全部 observer-暴露产物** ⊆ `ALLOWED_ARTIFACTS`;`provider-turns.json`
  是 server-local smoke 输入,**故意不经协议暴露**(不入 allowlist,见 §6.3)。涌现引擎发出的事件词汇 ==
  P2-C theater 已渲染的词汇;`ALLOWED_TEMPLATES` 只需复用现有 `default_6p_fake` token(swap-behind)。
- **1 个已知 seam(预存在,非本 slice 引入,见 §5.3/§A):** 涌现只写 god snapshot,不写 role_projection
  snapshot ⇒ `/projection` 的 `role:pN` 视角缺**可信 role snapshot**,其私有事件(seer/witch/狼队)降级为
  `hidden`,role 视角实际等同 public-only。不阻断本 slice,但 acceptance test 必须**固定该降级行为**。

---

## 1. observer server 现在 launch 的是什么 runtime?(问题 1)

**答:两条路径今天跑的都是旧 *scripted* runtime,没有一条是 `EmergentGameEngine`。**

### 1.1 launcher 契约
`RunLauncher = Callable[[str, Path], int]`(`observer_server.py:62`)。约定:
- 入参 `(run_id, run_dir)`;`run_dir` 已由 handler 创建。
- 返回 `int` exit code:`0` → `completed`;非 0 → `failed`,经 `_map_launcher_exit_reason`
  (`observer_server.py:169`)映射为 key-free reason(**`3` → `budget_exhausted`,其余(含 `2`)→
  `provider_failure`**)。**注意:只有 `3` 才是 `budget_exhausted` —— 这条对 §3.2 live launcher 至关重要。**
- 抛异常 → handler 兜底记 `provider_failure` + `failed`(`observer_server.py:465`),绝不外泄原始异常文本。
- launcher 在后台线程同步执行(`_execute_run`/`_launch_run_async`,`observer_server.py:454/475`)。

### 1.2 fake 默认路径(scripted)
`create_observer_server(... launcher=None)` → `default_fake_launcher`(`observer_server.py:67`)
→ `run_g1h_fake_runtime.run_fake_runtime`
→ **`game_engine.GameEngine.from_config(...).run(mode="g1f_provider_consensus")`**(`run_g1h_fake_runtime.py:121`)。
即旧的「确定性剧本/共识」状态机,**不是涌现引擎**。

### 1.3 live opt-in 路径(scripted)
`run_observer_server.resolve_live_launcher`(`run_observer_server.py:36`)→
`deepseek_launcher.build_deepseek_launcher`(`deepseek_launcher.py:82`)→
**`run_deepseek_consensus_game_with_provider_factory`**(`deepseek_launcher.py:111`)。
即旧的「狼人共识」剧本 live 路径,**也不是涌现引擎**。

### 1.4 profile launch 包装层(runtime-agnostic,可复用)
`_handle_profile_launch`(`observer_server.py:499`)在 base launcher 外**包一层** `_profile_launcher`
(`observer_server.py:548`),它在 base 跑完后写 `resolved-profile.json`(含 `execution_mode=fake|live`、
`live_api=used|not_used`)。**这层与 runtime 无关**,无论 base 是 scripted 还是 emergent 都照常工作 ——
swap launcher **不需要动**这一层。

> **结论:** "接入涌现引擎" 不是改 server 路由,而是**替换两个 base launcher 的实现**,使其驱动
> `EmergentGameEngine` 而非 scripted 引擎。server 路由/包装层/协议常量都不需要动。

---

## 2. EmergentGameEngine 现在输出哪些 artifacts / events / logs?(问题 2)

### 2.1 引擎 API(`emergent_engine.py`)
- 构造:`EmergentGameEngine(config=build_emergent_config(game_id=...), agents=..., seed=...,
  source_label=..., budget=EmergentBudget(max_requests=..., max_day_rounds=...), runtime_events=<writer|None>)`
  (`emergent_engine.py:185`,`runtime_events` 形参在 `:192`)。
- 运行:`outcome = engine.run()`(`emergent_engine.py:719`)→ `GameOutcome`,字段(经 runner 用法核实):
  `.status` / `.completed`(bool)/ `.end_condition` / `.game_log` / `.decision_log` / `.consensus_log` /
  `.failure_audit` / `.provider_turns`(list)/ `.live_requested_actions` / `.live_success_actions` /
  `.live_success_rate`。
- **`runtime_events` 是关键开关:** 仅当传入 writer 时,引擎 `_emit`(`emergent_engine.py:237/261`)
  才把每个事件写进 `events.jsonl`,`_maybe_snapshot`(`:311/319`)才写 god snapshot。
  **不传 writer ⇒ 无 events.jsonl、无 snapshots ⇒ observer 无可观战流。**

### 2.2 事件词汇(引擎 `_emit` 实测,`emergent_engine.py:450–808`)
| type | visibility | 备注 |
|---|---|---|
| `role_assignment` | `public` | setup |
| `werewolf_kill` | `werewolf_team` | 夜刀 intent |
| `seer_check` | `seer` | 含查验结果 summary |
| `witch_save` / `witch_kill` / `witch_pass` | `witch` | **见 §8 witch 词汇并行依赖** |
| `player_died` | `all` | 夜间死亡(settlement 死亡判定锚点) |
| `day_announcement` | `public` | 天亮播报 |
| `player_speech` | `public` | `data.summary` = 自然发言文本(P2-C/scoring 都读它) |
| `player_vote` | `public` | 投票 |
| `player_eliminated` | `all` | 放逐死亡(settlement 死亡判定锚点) |
| `role_revealed` | `all` | 放逐翻牌 |
| `game_over` | `all` | **`_emit` 的 `target`=`villager_team`/`werewolf_team`(携带胜方),`visibility`=`all`,全 perspective 可见**(`emergent_engine.py:800-808`) |

> 该词汇集 == P2-C theater 已渲染的事件类型(见 P2-C spec)。**所以 swap 到涌现引擎对 Qt 是低风险的:
> 没有新事件类型要 Qt 适配。**

### 2.3 logs / artifacts(由 *runner*,非引擎本体写盘)
引擎只产出内存中的 outcome + 经 writer 流式写 `events.jsonl`/snapshots。落盘 log 是 runner 职责:
- **live 涌现 runner**(`run_emergent_deepseek_game.py`,已 observer-shaped)写:`events.jsonl`、`snapshots/`、
  `prompt-manifest.json`(**真实 model**)、`game-log.json`、`decision-log.json`、`consensus-log.json`、
  `failure-audit.json`、`provider-trace.json`、`provider-turns.json`。fail-closed 时只写 `failure-audit.json`
  (+ spine)。**所有失败都返回 `2`(`run_emergent_deepseek_game.py:138`)—— 见 §3.2 budget 修正。**
- **fake 涌现 runner**(`run_emergent_game.py`)**只**在传 `--*-out` 时写 4 个 log,**完全不接 writer**
  ⇒ 无 `events.jsonl`/snapshots/manifest/provider-trace。**这就是缺口(§3)。**

> **暴露 vs server-local:** `provider-turns.json` **不在** `ALLOWED_ARTIFACTS`(`observer_protocol.py:31`),
> 也不该进 —— 它是 live smoke 的 server-local 输入(§4.2 / §6.3),不经协议对 client 暴露。

---

## 3. 两者缺的最小 adapter 是什么?(问题 3)

**一句话:fake 涌现路径缺一个「接了 `RuntimeEventWriter` 并写全套 observer artifact」的 launcher。
live 涌现路径几乎不缺(runner 已 observer-shaped),只缺一个把它包成 `(run_id, run_dir)->int`
并 **把 budget 失败码翻成 `3`** 的闭包。**

### 3.1 Adapter A — fake 涌现 launcher(keystone,新代码)
新增 `run_emergent_fake_runtime(*, game_id, out_dir, script="villager_win", seed=0,
max_requests=80, max_day_rounds=3) -> int`(建议落在新模块 `run_emergent_fake_runtime.py`,
或扩 `run_emergent_game.py` 增一个 writer 化入口)。职责 = **照搬 `run_g1h_fake_runtime.run_fake_runtime`
的「writer + 全套落盘」骨架,但把引擎换成 `EmergentGameEngine` + fake-script agents**:

1. `writer = RuntimeEventWriter(run_id=game_id, out_dir=out_dir)`(产 `events.jsonl` + god snapshots)。
2. `agents = build_emergent_fake_agents(SCRIPTS[script]())`(`emergent_fake_script.py`,已存在,
   `run_emergent_game.py:20` 在用)。
3. `engine = EmergentGameEngine(..., source_label=FAKE_PROVIDER_SOURCE_LABEL, runtime_events=writer)`。
4. `outcome = engine.run()`。
5. completed → 写 `game-log.json` / `decision-log.json` / `consensus-log.json` / `failure-audit.json`
   / `provider-trace.json`(fake provider 的 trace,token=0)/ `prompt-manifest.json`(`secrets_redacted=True`,
   `model="none"`)。返回 `0`。
6. 非 completed(round-cap / budget) → **只**写 `failure-audit.json`(+ 已流出的 spine),返回 `2`
   (与现有 fail-closed 契约一致,见 `run_emergent_game.py:67`、`run_g1h_fake_runtime.py:148`)。
   *(fake 路径无真实 budget 概念,返回 `2`/`provider_failure` 足够;budget 翻码只对 live 必要,见 §3.2。)*

`default_emergent_fake_launcher(run_id, run_dir) -> int` = 调 `run_emergent_fake_runtime(game_id=run_id,
out_dir=run_dir)`,契合 `RunLauncher`。

### 3.2 Adapter B — live 涌现 launcher(薄闭包 + **budget exit-code 翻译**,复用现有 runner)
现有 `run_emergent_deepseek_game(*, game_id, out_dir, provider_factory, model, seed,
max_requests_per_game, max_day_rounds) -> int` 已写全套 observer spine + `provider-turns.json`。

> **⚠️ 已修正的坑(审查 P1):** 该 runner **任何失败都固定返回 `2`**(`run_emergent_deepseek_game.py:138`),
> 但 observer **只有 `3` 才映射成 `budget_exhausted`**(`observer_server.py:169`)。若闭包**原样透传** runner 的
> 返回码,budget 耗尽会被错报成 `provider_failure`,run-status reason 退化。复现:`max_requests_per_game=0`
> → `failure-audit.json` 写 `kind=budget_exhausted` / reason "budget exhausted: 1/0 requests",但进程返回 `2`。
> **此外** 旧 `deepseek_launcher._classify_failure` 只匹配字符串 `"budget exceeded"`,与涌现 audit 的
> `"budget exhausted"` **不一致**,**不能原样复用**。

闭包必须**重读 failure audit 把 budget 失败翻成 `3`**:

```text
build_emergent_deepseek_launcher(api_key, base_url, model, ...) -> RunLauncher:
    factory = _deepseek_factory(api_key, base_url, model, ...)   # 复用 run_emergent_deepseek_game._deepseek_factory
    def launcher(run_id, run_dir) -> int:
        code = run_emergent_deepseek_game(game_id=run_id, out_dir=run_dir,
                                          provider_factory=factory, model=model, ...)
        if code == 0:
            return 0
        # 失败:重读 run_dir/failure-audit.json,若为 budget 耗尽 → 3(observer→budget_exhausted)
        if _audit_is_budget_exhausted(run_dir / "failure-audit.json"):
            return 3
        return 2                                                  # 其余 → provider_failure
    return launcher
```
- `_audit_is_budget_exhausted` 读 `failure-audit.json`,匹配**结构化字段**(实现者须确认确切字段:
  `kind == "budget_exhausted"` 或 `end_condition == "budget_exhausted"`),**不要**用 `_classify_failure`
  的 `"budget exceeded"` 子串匹配(词不一致)。读不到/解析失败 → 保守返回 `2`,绝不抛、绝不外泄路径/文本。
- 形状与现有 `deepseek_launcher.build_deepseek_launcher`(`deepseek_launcher.py:82`)同构 —— 实现时
  **新增一个 emergent 版**,不改旧的(旧 scripted 路径保留备用)。

### 3.3 接线 swap(`run_observer_server.py`,非禁止文件)
- fake:`create_observer_server(... launcher=default_emergent_fake_launcher)`(显式传入,替代当前的
  `default_fake_launcher`)。
- live:`resolve_live_launcher` 把 `build_deepseek_launcher` 换成 `build_emergent_deepseek_launcher`。
- 模型默认值注意:当前 live 默认 `--deepseek-model deepseek-chat`(`run_observer_server.py:32`),
  而涌现冒烟用 `deepseek-v4-flash`。实现时统一默认(建议 `deepseek-v4-flash`,与 §4 smoke 校准一致),
  并保持 CLI 可覆盖。

---

## 4. fake-deterministic 与 live DeepSeek 如何继续遵守现有 gate?(问题 4)

**两类 gate 必须都不退化,且彼此独立:**

### 4.1 launch-time gate(server 强制,本 slice 必须保持)
- **Capability gate**(`_check_live_capability`,`observer_server.py:85`):live 且 `live_enabled` 关或
  `live_launcher is None` → 403 `live_api_disabled` / `missing_api_key`,**先于** load/validate,不建 run_dir。
- **Shape gate**(`_check_live_profile_shape`,`observer_server.py:102`):live 要求全座 `provider=deepseek`
  且单一 model,否则 400 `unsupported_live_provider` / `mixed_models`。
- **swap 不触碰这两个 gate**(它们在 handler 里,`observer_server.py` 禁止改)。涌现 live launcher 只是
  base launcher 实现变了,gate 仍在其外层照常执行。
- `fake-deterministic` 仍是**无条件默认**:`DEFAULT_FAKE_MODE="fake"`(`observer_protocol.py:17`),
  fake launcher 永不需要 key。这条**不可因 swap 退化**。
- **budget reason 不退化**:见 §3.2 —— live launcher 必须把 budget 失败翻成 `3`,否则
  `_map_launcher_exit_reason` 给不出 `budget_exhausted`。

### 4.2 post-hoc review gate(用户跑 / agent 离线判,本 slice 必须保持可用)
`emergent_smoke_check.evaluate_emergent_smoke`(`emergent_smoke_check.py:49`)是**离线**判官,读 RAW
artifact 给 text-free verdict,门槛①②③ + secret scan。它依赖:
- `provider-turns.json`(rate / floor / per-turn honesty)— **live 涌现 launcher 已写**(`run_emergent_deepseek_game.py:105`)。
- `prompt-manifest.json` 的真实 model、`provider-trace.json` 的 `observation_text`、全 dir secret scan。
- 校准常量:`MIN_LIVE_SUCCESS_RATE=0.80`、`MIN_LIVE_SUCCESS_ACTIONS=12`(`emergent_smoke_check.py:19`)。

> **关键不变量:** live 涌现 launcher **必须继续写 `provider-turns.json`**(已满足),否则 smoke 退化。
> **运行口径(沿用 P2-A-2):** user-run live / agent-offline-review —— **agent 不接触 key**,只对 raw artifact
> 离线机检。`provider-turns.json` 是 **server-local** smoke 输入,**不**经协议暴露(§6.3),无需改 `ALLOWED_ARTIFACTS`。

---

## 5. visibility projection 如何保证不退化?(问题 5)

> **⚠️ 已修正(审查 P2):** observer 的 `/events`/`/stream` 与 `/projection` 走**两套不同**的可见性实现,
> 不能混为一谈。

### 5.1 通道 A — `/events`、`/stream`(薄过滤)
用 `observer_protocol.event_visible_to_perspective`(`observer_protocol.py:467`)。投影集:
- `god` = 全可见;
- `public` / `role:pN` = `{public, all}`(`PUBLIC_EVENT_VISIBILITIES`);
- `team:werewolf` = `{public, all, werewolf_team}`。

即:`/events` 下 **`role:pN` 看不到任何私有事件**(连本人的 seer/witch 也看不到,因为薄过滤不识别
role-self);**`team:werewolf` 能看到 `werewolf_kill`**;seer/witch 私有事件仅 god 可见。

### 5.2 通道 B — `/projection`(角色信任投影)
server 的 `/projection` **不**走薄过滤,而走 `observer_visibility.build_projection_envelope`
(`observer_server.py:376`)→ `event_visible_in_projection`(`observer_visibility.py:460`):
- `god` = 全可见;`public` = public-like;
- **`role:pN` 的私有事件解锁依赖「可信 role snapshot」**:`seer`/`witch` 事件仅当该 seat 有
  `role_source == "role_projection_snapshot"` 且匹配角色时可见(`observer_visibility.py:488-497`、
  `_trusted_role_for_player:515`);狼队事件需可信 `team == werewolf`(`:499-503`)。
- **`team:werewolf`(kind=="team")无需 snapshot**:`werewolf_team` 可见性事件直接放行(`:506-510`)。

### 5.3 seam(预存在,本 slice 唯一 visibility seam):涌现只写 god snapshot
涌现 `_maybe_snapshot` 只写 god snapshot(`build_god_snapshot`,`emergent_engine.py:31/319`),
**不写 role_projection snapshot**。后果:
- `/projection` 的 **`role:pN` 缺可信 role snapshot ⇒ seer/witch/狼队私有事件全部降级 `hidden`**,
  role 视角**实际等同 public-only**。这是当前真实行为(**非** bug,是 snapshot 缺位的合理降级)。
- `team:werewolf` **不**受影响(无需 snapshot)—— `/events` 与 `/projection` 下都能见 `werewolf_kill`。
- `/snapshots` registry 对非 god perspective 把 god snapshot 标 `hidden`(`build_snapshot_registry`,
  `observer_protocol.py:221`),非 god 看不到逐角色 snapshot。
- **本 slice 立场:** 不修(改引擎写 role snapshot 属引擎范畴,禁止)。**加 acceptance test 固定该降级**,
  并在 PR 描述如实标注"role 私有解锁需后续补 role_projection snapshot"。

### 5.4 不退化判据(swap 后逐 perspective 断言)
对同一局涌现 run:
- **`/events`/`/stream`:** `role:pN` 与 `public` 的 `events` 只含 `{public, all}` 可见性,**绝不**含
  `werewolf_kill`/`seer_check`/`witch_*`;`team:werewolf` **含** `werewolf_kill` 但**不**含 `seer_check`/`witch_*`;
  每个受限 perspective `hidden_count > 0`。
- **`/projection`:** `role:pN`(无 role snapshot)私有事件计入 `hidden`,`event_visibility_reasons` 不出现
  `seer_event`/`witch_event`/`werewolf_team_event`(证明降级生效);`team:werewolf` 的 `werewolf_team_event`
  正常出现;god 全见。
- **跨通道一致性:** 私有 seer/witch 事件在两条通道下对非匹配 perspective 都不泄漏。

---

## 6. settlement bundle 需要哪些稳定输入?(问题 6)

`build_settlement_response(run_dir, run_status, run_id)`(`settlement_bundle.py:212`)是纯文件系统逻辑,
对 runtime 来源**无知**。它要求:

### 6.1 硬输入
- `run_status == "completed"`(否则 `{"available": False, "reason": "not_completed"}`)。
- `run_dir/game-log.json` 存在(否则 `reason: "no_game_log"`)。
- 可选 `run_dir/decision-log.json`(缺 → `missing_decision_log` 降级;坏 → `invalid_decision_log` 降级;
  在 → battle-report 层)。

### 6.2 game-log 的结构契约(curtain 层恒需)
`build_settlement_bundle`(`settlement_bundle.py:129`)读 `game.players`(player_id/role/team)、
`game.result`(winner/end_round/end_condition/survivors)、`game.source_label`、`game.events`
(sequence/round/phase/type/actor/target)。**死亡判定只认 `player_died` / `player_eliminated`**
(`_DEATH_TYPES`,`settlement_bundle.py:31`),**不依赖任何 witch 事件名** —— 故 §8 的 witch 改名
**不影响 settlement**。涌现 `game-log` 已满足此结构(P2-A-2 已用 `score_game`/`attribute_game` 验证过)。

### 6.3 对本 slice 的要求
- **fake 涌现 launcher 必须写 `game-log.json` + `decision-log.json`(+ `consensus-log.json`)到 run_dir**
  (当前 `run_emergent_game.py` 默认**不写**,§3.1 步骤 5 已纳入)。这是 settlement 在 fake 局可用的前提。
- 路由 `/api/runs/{id}/settlement`(`observer_server.py:404`)与 `settlement-bundle.json` 缓存机制**零改动**:
  懒算-or-缓存逻辑对涌现产物同样成立。
- `settlement-bundle.json` 已在 `ALLOWED_ARTIFACTS`(`observer_protocol.py:40`)—— 无需协议改动。
- **artifact 暴露边界(已修正):** observer-暴露产物 = `ALLOWED_ARTIFACTS` 内的集合
  (events/manifest/game-log/decision-log/consensus-log/provider-trace/failure-audit/resolved-profile/
  settlement-bundle)。`provider-turns.json` **不属暴露集**,是 §4.2 的 server-local smoke 输入。**故不要
  写"涌现全部产物 ⊆ ALLOWED_ARTIFACTS";正确表述是"全部 observer-暴露产物 ⊆ ALLOWED_ARTIFACTS"。**

---

## 7. P2-D 合并后,最小实现切片应改哪些文件?(问题 7)

> **前置:** 必须等 `p2-d-settlement-screen` 合并、`observer_server.py` 释放后再开工(避免与 P2-D 冲突)。
> 本 slice **不需要**改 `observer_server.py`,但要在它稳定后再接线,以免基线漂移。

**新增(NEW):**
1. `src/werewolf_eval/run_emergent_fake_runtime.py` — fake 涌现 launcher(Adapter A,§3.1)。
   *(或:在 `run_emergent_game.py` 内新增一个 writer 化入口函数,二选一。)*
2. `tests/test_run_emergent_fake_runtime.py` — Adapter A 的单测(完整产物 / fail-closed)。
3. `tests/test_observer_emergent_bridge.py` — server 级 + 投影 + settlement + **budget exit-code 翻译**的
   集成断言(离线)。

**修改(EDIT,均非禁止文件):**
4. `src/werewolf_eval/deepseek_launcher.py` — 新增 `build_emergent_deepseek_launcher` + budget-audit 翻码
   辅助(Adapter B,§3.2),**保留**旧 `build_deepseek_launcher`/`_classify_failure`。
5. `src/werewolf_eval/run_observer_server.py` — 接线 swap(§3.3):fake 传 `default_emergent_fake_launcher`;
   live 改用 `build_emergent_deepseek_launcher`;统一 model 默认。

**显式不改(本 slice):** `observer_server.py`、`observer_protocol.py`、`clients/qt_observer/**`、
`emergent_engine.py`、`emergent_fake_script.py`、`scoring.py`、`attribution.py`、`settlement_bundle.py`、
`observer_visibility.py`、`game_engine.py`(旧 scripted 保留)。

> **可选(deferred,不在最小切片):** 若要在协议层区分"涌现"与"剧本"模板(新增 `default_6p_emergent`
> token),需改 `observer_protocol.ALLOWED_TEMPLATES` + Qt 模板选择 —— **跨禁止边界**,留作后续。
> 最小切片采用 **swap-behind-existing-template**:复用 `default_6p_fake`,后端换 runtime,前端无感。

---

## 8. witch 词汇并行依赖(与"witch_kill→witch_poison 修复"协调)

引擎用常量 `WITCH_KILL` 发"女巫毒"事件(`emergent_engine.py:625`,summary 已是 "poisons")。并行的
P2-A 正确性修复要把事件 type `witch_kill` 改名为 `witch_poison`。**两点协调:**
- 本 bridge **不得**硬编码 witch 事件 type 名(fake launcher 透传引擎产物即可,不解析 witch type)。
- settlement(§6.2)与本 bridge 的死亡判定都**不依赖** witch type 名,故改名**不冲突**;但若 Qt theater
  或 smoke 对 `witch_kill` 有断言,应由 witch 修复任务统一收口。**合并顺序:** witch 修复先落 →
  本 bridge 后接,避免双写引擎事件常量。

---

## 9. 验收测试分层(问题 9)

| 层 | 范围 | 关键断言 | 环境备注 |
|---|---|---|---|
| **unit** | Adapter A(`run_emergent_fake_runtime`) | completed→写齐 `events.jsonl`/snapshots/`game-log`/`decision-log`/`consensus-log`/`failure-audit`/`provider-trace`/`prompt-manifest`,返回 0;fail-closed→只写 `failure-audit`,返回 2;manifest `secrets_redacted=True`、`model="none"`、`source_label=[fake...]` | 纯离线,本环境可单测 |
| **unit** | Adapter B 闭包(含 **budget 翻码**) | `(run_id, run_dir)` 签名;注入 fake-transport deepseek factory(无网络)→ 走 `run_emergent_deepseek_game` 全产物 + `provider-turns.json`;**budget 耗尽 run(`max_requests=0`)→ 闭包返回 `3`(非 `2`)**;其它失败→`2` | 复用现有 fake-transport seam |
| **protocol** | `observer_protocol` 常量 | **observer-暴露**产物 ⊆ `ALLOWED_ARTIFACTS`;`provider-turns.json` 为 server-local(不暴露/不入 allowlist);**无需新增 artifact/template/perspective** | 只读断言,零协议改动 |
| **observer-server** | 端点行为(用 Adapter A 作 launcher) | POST `/api/runs`(template launch)→ 跑完 →`/events`、`/projection`、`/settlement`、`/artifacts`、`/snapshots` 全部对涌现 run 正确返回;`/settlement` 懒算缓存命中 | **本环境 localhost HTTP 被屏蔽**(见项目 memory)→ 用 handler/`build_settlement_response` 离线驱动,**不**起真 socket |
| **visibility** | 逐 perspective × 两通道 | §5.4 判据全绿:`/events` 薄过滤 + `/projection` role 降级 hidden + `team:werewolf` 双通道见 `werewolf_kill`;§5.3 snapshot 降级被固定 | 离线,喂合成涌现 events(+ 无 role snapshot) |
| **Qt static contract** | `test_qt_observer_static_contract` | **保持现状绿**(无新事件类型/协议字段 → Qt 静态契约不应变) | 不改 Qt;只确认未破 |
| **smoke**(post-hoc) | `evaluate_emergent_smoke` | live 涌现 launcher 产物喂 smoke,门槛①②③+secret scan 全过;**user-run / agent-offline-review**,agent 不碰 key | 用户本地跑 live;agent 只离线判 raw artifact |

---

## 10. 给实现者:allowlist / forbidden scope / acceptance(问题 8 & 10)

### 10.1 明确**不做**(问题 8)
- **BYO-key**(用户自带 key 存储/选择)—— P2-B,见 `p2-b-byo-key-architecture` memory。本 slice live key
  仍走 server-side env(`DEEPSEEK_API_KEY`),沿用现状。
- **多模型 arena / 混合 provider** —— live shape gate 仍要求单一 deepseek model(§4.1),不放宽。
- **Qt 大改** —— 不新增事件类型/协议字段,不动 `clients/qt_observer/**`。
- **评分公式重写** —— 复用 `score_game`/`summarize_metrics`/`attribute_game` 原样。
- **历史库 / 排行榜** —— P3,不碰。
- **新协议 token / 端点 / artifact** —— 最小切片 swap-behind-existing-template,零协议改动。
- **补 role_projection snapshot 修 §5.3 降级** —— 如实记录 + 固定行为,真正修复留后续 slice。

### 10.2 ALLOWLIST(只允许动这些)
`run_emergent_fake_runtime.py`(新)、`deepseek_launcher.py`(加 emergent launcher + budget 翻码,不删旧)、
`run_observer_server.py`(接线 swap)、`tests/test_run_emergent_fake_runtime.py`(新)、
`tests/test_observer_emergent_bridge.py`(新)。可选扩 `run_emergent_game.py`(加 writer 化入口)。

### 10.3 FORBIDDEN SCOPE(绝不动)
`observer_server.py`、`observer_protocol.py`、`observer_visibility.py`、`clients/qt_observer/**`、
`emergent_engine.py`、`emergent_fake_script.py`、`scoring.py`、`attribution.py`、`settlement_bundle.py`、
`game_engine.py`、`PROJECT_MAP.md`、`TASKS.md`(后两者除非 owner 单独授权)。

### 10.4 ACCEPTANCE CRITERIA(实现完成判据)
1. observer 默认 fake launch 跑的是 `EmergentGameEngine`(非 scripted),且产物 = 完整 observer spine
   (events/snapshots/manifest/4-logs/trace)。
2. `/events`、`/stream`、`/projection`、`/snapshots`、`/artifacts`、`/settlement` 对涌现 run 全部正确,
   §9 各层测试绿。
3. visibility 不退化(§5.4 判据全绿);§5.3 snapshot 降级 seam 有 test 固定其当前行为,并在 PR 描述如实
   标注"role 私有解锁未实现、归后续 slice"。
4. live opt-in 路径走涌现引擎并产 `provider-turns.json`,既有 `evaluate_emergent_smoke` 离线判官**零改动**
   仍可判过一局真实 live(user-run);**budget 耗尽的 live run 在 run-status 里报 `budget_exhausted`(非
   `provider_failure`)**。
5. `fake-deterministic` 仍是无条件无 key 默认;capability/shape gate 行为不变。
6. `observer_server.py` / `observer_protocol.py` / `observer_visibility.py` / Qt **git diff 为空**;Qt 静态
   契约测试保持绿。
7. 旧 scripted launcher 代码(`default_fake_launcher` 路径、`build_deepseek_launcher`、`_classify_failure`)
   保留(可回退),不被删除。

---

## 附录 A — 已知 seam / 坑 速查(如实记录,防"假装修好")

| seam | 位置 | 现象 | 本 slice 处置 |
|---|---|---|---|
| A. 仅 god snapshot → `/projection` role 降级 | `emergent_engine.py:319` 只 `build_god_snapshot`;`observer_visibility.py:488-503` role 私有解锁需可信 role snapshot | `/projection` 的 `role:pN` 私有事件全降级 `hidden`(role 视角≈public-only);`team:werewolf` 不受影响 | 不修,加 test 固定降级,归后续 slice |
| B. live runner 失败固定返回 `2` | `run_emergent_deepseek_game.py:138`;`observer_server.py:169` 只有 `3`→`budget_exhausted` | budget 耗尽会错报 `provider_failure` | **本 slice 必修**:Adapter B 重读 audit 把 budget→`3`(§3.2) |
| C. live model 默认不一致 | `run_observer_server.py:32` `deepseek-chat` vs 冒烟 `deepseek-v4-flash` | 接线时易踩 | swap 时统一默认 + CLI 可覆盖 |
| D. witch 词汇并行改名 | `emergent_engine.py:625` `WITCH_KILL` | 并行任务改 `witch_kill→witch_poison` | bridge 不硬编码该名;合并顺序 witch 先、bridge 后 |
| E. `_classify_failure` 词不一致 | `deepseek_launcher._classify_failure` 匹配 `"budget exceeded"` | 涌现 audit 用 `"budget exhausted"`,子串匹配会漏 | Adapter B 用结构化字段判,不复用该子串匹配(§3.2) |

> **已修正的误读(审查 r2):** 早期草稿曾称 `game_over` 的 `visibility` 是 `villager_team`/`werewolf_team`
> 并要求"加 test 固定该错误"。**实测为误读** —— `emergent_engine.py:800-808` 中 `villager_team`/
> `werewolf_team` 是 **`target`** 字段,`visibility` 是 **`all`**,村民胜 `game_over` 全 perspective 正常可见。
> 该条已删除,**不**作为 seam。

## 附录 B — 数据流(swap 后)

```
POST /api/runs (default_6p_fake / fake)
  └─ observer_server handler (不变)
       └─ default_emergent_fake_launcher(run_id, run_dir)          [NEW, Adapter A]
            └─ run_emergent_fake_runtime
                 ├─ RuntimeEventWriter ──> events.jsonl + snapshots/(god)
                 └─ EmergentGameEngine.run() ──> game-log/decision-log/consensus-log/
                                                  failure-audit/provider-trace/prompt-manifest
  ↓ (completed)
GET /events|/stream ──> 薄过滤(observer_protocol.event_visible_to_perspective, 不变)
GET /projection ──────> 信任投影(observer_visibility.build_projection_envelope, 不变;
                         role 私有事件因无 role snapshot 降级 hidden)
GET /settlement ──────> build_settlement_response ──> settlement-bundle.json(懒算缓存, 不变)
                                                        └─ Qt SettlementReport/Spine (P2-D, 不变)

POST /api/runs (profile, live)  [需 --allow-live-api + env key]
  └─ capability+shape gate(不变) ──> build_emergent_deepseek_launcher(...)  [NEW, Adapter B]
       └─ run_emergent_deepseek_game(...)（已 observer-shaped）
            ├─ ... + provider-turns.json ──> evaluate_emergent_smoke（user-run / agent-offline; server-local）
            └─ 失败→重读 failure-audit:budget→exit 3, 其余→exit 2  [budget reason 不退化]
```

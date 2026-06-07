# P2 Spec — Emergent Engine role_projection + mid-game god Snapshots

> **类型:** 设计 spec(design)。**实现随后由 writing-plans 切计划。**
> **日期:** 2026-06-07
> **定位:** PR #56(observer→EmergentGameEngine 桥接)明确划归后续的 seam 修复
> (桥接 spec §5.3 / 附录 A seam A)。让涌现引擎补齐它本就缺失的两类快照产物,使
> observer `/projection` 的 **role:pN 私有观战**(seer/witch/狼队私有事件对本人视角可见)
> 与 **中盘 alive 实时准确** 成立。
> **关键边界:** **只动 `emergent_engine.py` + 测试。observer / protocol / Qt 零改动**——
> 它们早已能消费 `role_projection` 与 god 快照(scripted `GameEngine` 已在产),涌现侧只是没产。

---

## 0. TL;DR

- **缺口:** 涌现引擎只写 `setup_god_view` + `final_god_view` 两张 **god** 快照,**从不写
  `role_projection` 快照**,也不写中盘 god 快照。后果两条:
  1. `/projection role:pN` 缺「可信 role snapshot」⇒ seer/witch/狼队私有事件全降级 `hidden`,
     role 视角≈public-only(私有观战不可用)。
  2. 中盘只有 setup/end 两张 god 快照 ⇒ `build_seat_role_index` 的 `latest_god_alive` 中途取到
     setup(全员存活)⇒「人已死、投影仍认为活着」。
- **修复:** 在 `emergent_engine.py` 补两类快照,**复用** `runtime_events.build_role_projection_snapshot`
  + `RuntimeEventWriter.write_snapshot`(与 `game_engine.py` 完全同一套写法):
  1. **setup 一次性给全 6 座各写一张 `role_view_p{n}`**(`snapshot_type=role_projection`,`visibility=internal`)。
  2. **每回合 night 死亡结算后写 `god_view_r{rnd}_night`、day 放逐结算后写 `god_view_r{rnd}_day`**,
     保留现有 `setup_god_view` + `final_god_view`。
- **零协议改动:** 不新增事件类型 / 协议字段 / artifact / perspective;observer/protocol/Qt diff 必须为空。
- **防泄漏:** `build_role_projection_snapshot` 本身做角色投影(非狼观察者看不到狼角色);god 快照
  `visibility=internal` 对非 god 视角恒 `hidden`;`write_snapshot` 脱敏。无新泄漏面。

---

## 1. 现状(读码确认)

### 1.1 涌现引擎今天写什么快照
`EmergentGameEngine._write_god_snapshot`(`emergent_engine.py`)只在两处被调:
- `_run_inner` setup 后 → `setup_god_view`(round 0, phase "setup");
- 游戏正常结束后 → `final_god_view`(end_round, phase "game_end")。
两张都是 **god** 快照(`build_god_snapshot`,`visibility="internal"`,`private_event_ids=[]`)。
**没有任何 `role_projection` 快照,也没有中盘 god 快照。**

### 1.2 scripted GameEngine 已有的对照写法(直接复用)
`game_engine.py` 早已:
- `build_role_projection_snapshot(run_id=game_id, observation=obs)` + `write_snapshot("obs_<who>_<when>", snap,
  visibility="internal", round=, phase=, actor=)`(见 `game_engine.py` 的 `obs_wolf_n1` / `obs_p3_n1` /
  `obs_p4_n1` / `obs_{vid}_d1` 等)。
- `build_god_snapshot(...)` + `write_snapshot("setup_god_view", ...)`。
本 spec 在涌现侧采用同构写法,**不引入新机制**。

### 1.3 observer 侧如何消费(已就绪,不改)
- `observer_visibility.build_seat_role_index(run_dir)`:扫 `snapshots/*.json`,把每座 **LATEST**
  `role_projection`(按 `_snap_order`)作为可信 role/team/known_roles 来源;`alive` 由 **最新 god 快照**
  的 `alive_players` 定权(deaths 是公开信息)。
- `_snap_order = (round, _PHASE_RANK[phase])`,`_PHASE_RANK = {setup:0, night:1, day:2, vote/voting:3,
  game_end/result:4}`。本设计依赖此排序;**该表已存在,不改。**
- `event_visible_in_projection`:role:pN 仅当 `_trusted_role_for_player` 命中(role_source ==
  `role_projection_snapshot` 且角色匹配)才解锁 seer/witch;狼队事件需可信 team==werewolf。
  `team:werewolf`(kind=="team")不需快照即见 `werewolf_kill`(原本就成立)。
- `snapshot_visible_to_perspective`:god 快照对非 god 视角恒 `False`;`role_projection` 仅对匹配
  role:pN(及 team:werewolf 见 team==werewolf 的)可见 ⇒ **快照文件本身不会跨视角泄漏**。

---

## 2. 设计

### 2.1 role_projection:setup 一次写满 6 座(静态信息)
**职责定义:** `role_projection` 表达的不是「当前状态」,而是「**这个座位从自身视角合法知道哪些
身份/阵营信息**」。在 6 人标准局里这是**开局即定的静态信息**——预言家不会变女巫、狼队关系不变、
村民阵营不变;`known_roles` 在 `_build_obs` 里对狼已含队友、对其他人只含自身。`alive` 不由 role 快照
表达(走 god 权威)。**故每回合刷新 role 快照无 correctness 收益。**

**写法:** 在 `_run_inner` 的 setup 段(`role_assignment` emit + `setup_god_view` 之后),对
`self._seat_order` 的全部 6 座各写一张:

```text
setup_god_view        (already)
role_view_p1
role_view_p2
role_view_p3
role_view_p4
role_view_p5
role_view_p6
```

每张:`obs = self._build_obs(pid, "setup", 0)` → `build_role_projection_snapshot(run_id=self._game_id,
observation=obs)` → `write_snapshot(f"role_view_{pid}", snap, visibility="internal", round=0,
phase="setup", actor=pid)`。`snapshot_type` 由 builder 固定为 `role_projection`。

> setup 时 `public_event_ids` 已含 `role_assignment`,`private_event_ids` 由 `_private_refs(pid)`
> 角色安全给出(此刻多为空)。refs 不影响事件解锁(解锁只看可信 role/team),仅作信息。

### 2.2 中盘 god 快照:每回合 night/day 两个**结算点**各一张
**触发时机是「关键状态结算后」,不是阶段开始时:**
- **night:** 狼刀 / 救 / 毒 / 查验全部处理完、**死亡集合 `deaths` 确定并已从 `self._alive` 移除后**,
  写 `god_view_r{rnd}_night`(round=rnd, phase="night")。
- **day:** 投票 / 平票裁定 / 放逐(`player_eliminated`+`role_revealed`)处理完、**被放逐者已移除后**,
  写 `god_view_r{rnd}_day`(round=rnd, phase="day")。

保留首尾:`setup_god_view`(round 0)与 `final_god_view`(end_round, game_end)。

**早终局规则:** 若某回合**夜间后直接分胜负**(`_win_check` 在 night 段命中、未进 day),**仍要先写
`god_view_r{rnd}_night`,再写 `final_god_view`**。即:无论从哪条 break 路径结束,该回合已发生的
结算点都要落一张 god 快照,保证中盘 replay 与最终状态都完整。day 段命中同理(该回合的
`god_view_r{rnd}_day` 已在放逐后写过)。

**排序正确性:** `_snap_order=(round, phase_rank)`,`night(1) < day(2) < game_end(4)`,且每张 god 快照
带正确的 `alive_players=sorted(self._alive)`(写入时刻的存活集)。`build_seat_role_index` 的
`latest_god_alive` 取最高 `_snap_order` 的 god 快照 ⇒ 中盘任意时点 `/projection` 的 alive 反映到
**最近一次结算**。

### 2.3 复用辅助(实现提示,非硬契约)
建议把 role 快照逻辑收成一个私有辅助(如 `_write_role_snapshot(pid)`),setup 段 6 次调用;
god 中盘快照可直接复用现有 `_write_god_snapshot(name, rnd, phase)`(它已读 `self._alive` 生成
`alive_players`),只是**新增两个调用点**(night 结算后、day 放逐后)。两者在无 `runtime_events`
writer 时均 no-op(沿用现状,离线 CLI / 无 writer 路径不产快照)。

---

## 3. 数据流(修复后)

```
GET /projection role:p3 (seer)
  └─ build_seat_role_index(run_dir)
       ├─ 读 role_view_p3 → role="seer", role_source=role_projection_snapshot   [NEW]
       └─ 读最新 god_view_r{n}_{phase} → latest_god_alive(实时存活)            [NEW]
  └─ event_visible_in_projection(seer_check 事件, "role:p3", seat_index)
       └─ _trusted_role_for_player == "seer" → 解锁,reason="seer_event"        [now unlocked]
  witch/狼队同理(role:p4 见 witch_event;role:p1 见 werewolf_team_event)。
  role:p5(villager)无私有事件可解锁,且看不到他人私有事件(反向不泄漏)。
  team:werewolf 借各狼 role_view 的可信 team 得到狼名单(werewolf_kill 本就可见)。
```

---

## 4. 防泄漏不变量(必须保持)

1. **role 快照内容投影:** `build_role_projection_snapshot` 对**非狼**观察者把 `projected_known_roles`
   里的狼角色抹成 `unknown`;狼保留队友。⇒ 村民的 role_view 不含任何狼身份。
2. **role 快照跨视角门禁:** `snapshot_visible_to_perspective` 仅让 role:本人(及 team:werewolf 见
   team==werewolf)取到对应 role_projection 文件;`role:p5` 取不到 `role_view_p3`。
3. **god 快照内部化:** god 快照 `visibility="internal"`,`snapshot_visible_to_perspective` 对非 god
   视角恒 `False`。中盘多写 god 快照**不**对外暴露逐角色 god 视图。
4. **事件解锁只认可信源:** role:pN 私有事件解锁严格走 `role_source==role_projection_snapshot`;
   god_snapshot 来源**不**解锁私有事件(`observer_visibility` 既有规则,不改)。
5. **脱敏:** `write_snapshot` 对快照做 secret 脱敏(沿用)。
6. **零新增暴露面:** 不新增事件类型 / 协议字段 / artifact / perspective / template。

---

## 5. 验收标准

1. **observer 默认 fake 涌现局(`default_emergent_fake_launcher`)产物中,`role_view_p{n}` 恰好 6 张,
   不随回合增长**;每张 `snapshot_type=role_projection`、`visibility=internal`。
2. **`/projection role:p3` 解锁 `seer_event`、`role:p4` 解锁 `witch_event`、`role:p1` 解锁
   `werewolf_team_event`**;对应 `hidden` 计数较旧行为下降。
3. **`role:p5`(villager)不能因他人 `role_projection` 存在而看到任何 seer/witch/狼私有事件**
   (反向不泄漏)。
4. **`latest_god_alive` 在夜间死亡后、白天放逐后都能收缩**:中盘 `/projection` 的玩家 alive 反映
   最近一次结算(写出 `god_view_r{rnd}_night` / `god_view_r{rnd}_day`)。
5. **早终局完整性:** 夜间直接分胜负的局,`god_view_r{rnd}_night` 与 `final_god_view` 都存在。
6. **`team:werewolf` 借各狼 role_view 得可信狼名单**;且仍只见 `werewolf_kill`,不见 seer/witch。
7. **`god` 视角全见、所有受限视角私有 seer/witch 事件对非匹配方两通道都不泄漏**(沿用桥接 §5.4)。
8. **禁改文件 git diff 为空:** `observer_server.py`、`observer_protocol.py`、`observer_visibility.py`、
   `clients/qt_observer/**`、`game_engine.py`、`emergent_fake_script.py`、`runtime_events.py`、
   `scoring.py`、`attribution.py`、`settlement_bundle.py`。
9. 全套测试绿(本环境 localhost HTTP socket 测试照旧 env-block,与 main 基线一致,非回归)。

---

## 6. 测试分层

| 层 | 范围 | 关键断言 |
|---|---|---|
| **engine unit**(新 `tests/test_emergent_role_projection.py`,离线) | role 快照产物 | setup 后 `snapshots/` 含恰好 6 张 `role_view_p{1..6}`,`snapshot_type=role_projection`;再多回合也仍是 6 张(验收①) |
| **engine unit** | 中盘 god 快照 | 每回合存在 `god_view_r{rnd}_night`(+ 进入白天的回合存在 `god_view_r{rnd}_day`);按 `_snap_order` 取最新 god 快照的 `alive_players` 随死亡/放逐收缩(验收④);夜间早终局局 `god_view_r{rnd}_night`+`final_god_view` 都在(验收⑤) |
| **engine unit** | 防泄漏 | 全 `snapshots/*.json` secret 扫描;非狼座 `role_view` 的 `projected_known_roles` 不含 `werewolf` |
| **projection**(更新 `tests/test_observer_emergent_bridge.py`) | **翻转 seam 测试** | 旧 `test_projection_role_private_events_downgrade_to_hidden`(钉降级)改为:role:p3 出现 `seer_event`、role:p4 出现 `witch_event`、role:p1 出现 `werewolf_team_event`;**保留反向断言** role:p5 不见 seer/witch/狼私有事件(验收②③) |
| **projection** | 中盘 alive | 喂一局涌现 run,断言中盘 `build_seat_role_index` 的 alive 在死亡后收缩(验收④) |
| **protocol / 既有** | 回归 | `test_emergent_engine.py` / `test_run_emergent_fake_runtime.py` 若硬编码快照数量则同步更新;observer 三件套 + Qt diff 空(验收⑧);Qt 静态契约保持绿 |

---

## 7. allowlist / forbidden / 不做

### 7.1 ALLOWLIST(只允许动)
- `src/werewolf_eval/emergent_engine.py`(加 role 快照 + 中盘 god 快照写出)。
- `tests/test_observer_emergent_bridge.py`(翻转 seam 测试 + 中盘 alive)。
- `tests/test_emergent_role_projection.py`(新)。
- 仅在硬编码快照数量冲突时:`tests/test_emergent_engine.py` / `tests/test_run_emergent_fake_runtime.py`(同步)。

### 7.2 FORBIDDEN(绝不动)
`observer_server.py`、`observer_protocol.py`、`observer_visibility.py`、`clients/qt_observer/**`、
`game_engine.py`、`emergent_fake_script.py`、`runtime_events.py`、`scoring.py`、`attribution.py`、
`settlement_bundle.py`、`deepseek_launcher.py`、`run_observer_server.py`、`run_emergent_fake_runtime.py`、
`PROJECT_MAP.md`、`TASKS.md`。

### 7.3 不做(YAGNI)
- 不做 per-round / per-action role 快照刷新(role/team 静态,无收益)。
- 不改 observer / protocol / Qt / scripted 引擎。
- 不新增协议 token / 端点 / artifact / perspective。
- 不动 god 快照之外的 alive 机制;`latest_god_alive` 依赖既有 observer 逻辑。

---

## 附录 — 实现者结论(一句话)

**采用:`role_projection` setup 一次写全 6 座(`role_view_p{n}`,静态身份投影);`god_view` 每回合在
night 结算后、day 放逐后各写一次(早终局仍补该回合 night 张 + final);不改 observer/protocol/Qt。**

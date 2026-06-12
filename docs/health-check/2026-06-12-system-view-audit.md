# 项目体检报告 — System View 全量审计（2026-06-12）

> 基线:main `c00cab9`(+ T-live verdict `cab30b7`),工作树干净。
> 方法:按 `docs/PROJECT_MAP.md` System View 分 6 组并行只读审计(SYS-A1..A3 / A4..A5 / B1..B2 / B3..B4 / C1..C2 / C3),全部发现带文件级证据,其中 2 项经动态复证。审计本身零代码改动。
> 分层口径:P0=潜在 bug/规则错误/信息泄漏/状态不一致/日志结算错误;P1=未来加角色/加 provider/做 P3 时工作量剧增的结构性风险;P2=改进项(不抢主线)。
> 上一次体检:2026-06-08(见本目录 01/02/03)。本报告为独立新审计,编号不延续。

---

## 修复进度更新（2026-06-12 晚，main `8b6d32c`）

第一轮修复已合入 main（四条 codex 分支），全量 **1216 OK（skipped=2，NO_PROXY+PYTHONPATH=src 亲证）**，新增测试逐条复跑通过：

| 条目 | 状态 | commit | 验证 |
|---|---|---|---|
| **A-1**（Blocker，guard game-log 必炸） | ✅ 已修 | `6b1152d` | `VALID_VISIBILITIES` 加 `"guard"`;`test_accepts_guard_visibility` 绿 |
| **A45-4 / A45-6**（P2,顺手并入 A-1） | ✅ 已修 | `6b1152d` | `EVENT_TYPE_REQUIRED_VISIBILITY` 加 `guard_protect→guard`、parity `_VISIBILITIES` 加 `guard` |
| **B34-01**（Blocker,env live 跨局共享 provider） | ✅ 已修 | `f30340b` | `live_launcher` 改无参 per-launch factory（`_materialize_env_live_launcher`）,server 接线改 `env_launcher_factory` |
| **B34-02**（High,坏 key 0% live 报 completed） | ✅ 已修 | `f30340b` | runner 收口读 `live_success_rate`,<0.80 写 `reason=low_live_success_rate` 进 status |
| **C12-01**（High,投票 trace 被夜动作同 ID 吞） | ✅ 已修 | `f2907f9` | day 阶段 request_id 加 `_vote` 后缀（engine+provider_agent 两侧对齐） |
| **C12-02**（High,结算 per-seat token 恒空+测试假绿） | ✅ 已修 | `f2907f9` | `_load_seat_meta` 改读 `provider-turns.json`（自带 actor+token_usage,剔 scribe）;fixture 换真形状 |
| **C3-7**（Medium,e2e artifact_gap 被滤） | ✅ 已修 | `5a5edf7` | `TestZeroArtifactGap` 全 severity 零容忍,villager/werewolf 两脚本绿 |
| **C3-12**（P2,guard sentinel 不调 check_run） | ✅ 已修 | `5a5edf7` | 5 个 guard sentinel 加 `check_run` 错误级零断言 |
| **C3-2**（P1,文本注入负向扫描缺测试） | ⚠️ 部分 | `5a5edf7` | 便宜的负向扫描测试已补（`test_c3_negative_scan.py`:非女巫座位不含 victim 句式/【解药协调提示】）;**中期 spec（注入点登记表+输入可见性声明走带 id 事件通道）仍未做** |

**遗留缺口（本轮修复自身带出）**：B34-01/02 的 src 修复**无专用新增测试**钉死新行为——已由第二轮批次③补齐（见下）。

---

## 修复进度更新（第二轮，四批并行，全合入 main `9f0827f` 并 push）

第二轮按本报告文末「下一轮并行批次」拆四束,跨会话并行,各自隔离 worktree,全部合入 main 并 push（本地==origin/main=`9f0827f`,全量 **1263 OK（skipped=2）亲证**）：

| 批次 | 条目 | 状态 | commit | 验证 |
|---|---|---|---|---|
| **①ablation 护栏** | C3-4 + C12-04 + C12-03 + C12-10/11 | ✅ 已修 | `3523cf1`(PR #60) | `harness` 接 `check_run` 写 `validity.invariants`;aggregate 校 bucket;run_arm 拒非空目录;无 guard 板 milk_pierce 输出 None |
| **②engine 失败分类** | B12-01 + B12-02/03 + B34-10 | ✅ 已修 | `a778e3e` | 单源 `classify_provider_failure_kind`（budget/transport/auth/provider）;内联 witch/hunter 拆网络异常 vs json 解析 + 缺 action 键→parse_failure;4 新 kind 登记 VALID_FAILURE_KINDS;deepseek_launcher 零改动后向兼容 |
| **③B34 收尾 + key repr** | B34-04 + B34-01/02 测试缺口 | ✅ 已修 | `6448419` | `ChatProviderConfig` api_key `repr=False`;补 run_manager 测试钉死 `low_live_success_rate` 闸门 / per-launch factory 两路径 |
| **④score_id 竞态** | C12-05 | ✅ 已修 | `a124ce5`(PR #59) | 删模块级 `_current_score_id_prefix` 全局,改参数传递;并发结算无 A 局前缀污染 B 局 |

---

## 修复进度更新（第三轮收口，2026-06-12，已合 main 并 push `7de827a`）

审计残留 **5~9 全部收口**（规则裁决 + 注入 spec + 幽灵 id fail-loud + provider-agnostic smoke + perspective ADR），隔离 worktree 串行执行 + 独立 code-review（抓出 1 真 HIGH 已修），全量 **1328 OK（skipped=2）亲证**，rebase 到 origin/main 后线性 push（`3a90b90..7de827a`）：

| 条目 | 状态 | commit | 验证 |
|---|---|---|---|
| **A-2**（毒死猎人开枪裁决） | ✅ 已裁决+修 | `ccbe601`(+`7de827a`) | 裁决=毒死不开枪/他因仍开枪;数据驱动 `suppressed_by_cause`;**review 抓守卫挡刀+毒杀死因误判→settler 返回 `death_causes` 权威死因**;pin 测试含守卫板/奶穿对照 |
| **A-3**（女巫自救裁决） | ✅ 已裁决+修 | `ccbe601` | 裁决=仅首夜自救;`_resolve_witch` 加 `self_save_late` 校验→invalid_action+downgrade;pin 双向 |
| **C3-2**（注入通道 spec） | ✅ 收口 | `7493daa` | `docs/specs/text-injection-channels.md`(6 注入点登记+长期 EffectQueue 迁移)+漂移哨兵;原 ⚠️「spec 仍欠」已补 |
| **C3-1**（幽灵 source id） | ✅ 已修 | `71725be` | runtime `DanglingSourceEventError` fail-loud + offline `check_i4b` 产 I4b error;docstring 改如实 |
| **B34-07**（provider-agnostic smoke） | ✅ 已修 | `228f240`(+`7de827a`) | `LIVE_PROVIDER_SOURCE_LABELS`(⊆VALID,assert 守卫)+per-seat `expected_models_by_seat`;DeepSeek 向后兼容;fake/live 混淆负测 |
| **A45-1**（perspective 非鉴权 ADR） | ✅ 已落 | `010cfe8` | `docs/adr/2026-06-12-perspective-not-access-control-boundary.md` 边界声明;P3 多客户端前补鉴权 |

绑定 plan：`docs/harness/plans/2026-06-12--audit-closeout-rules-invariants-docs-smoke-plan.md`。规则裁决条文：`docs/specs/board-rule-rulings.md`。**至此本报告全部条目（含两 Blocker、Top 5、两条规则空洞）收口完毕。**

---

## P0 — 缺陷(Defect)

### A-1 ｜ SYS-A5/A3 ｜ Defect ｜ **Blocker** ｜ ✅ 已修 `6b1152d`

- **证据**:`src/werewolf_eval/game_log.py:11-19` `VALID_VISIBILITIES` 含 `hunter` 不含 `guard`;guard 板每局必产 `visibility="guard"` 的 `guard_protect` 事件(`action_runtime/turn.py:163`)。动态复证:对 `.runs/ablation/l4_guard/l4_guard_000/game-log.json` 跑 `load_game_log` 直接抛 `GameLogValidationError: invalid visibility 'guard'`;内存补丁加 `"guard"` 后 game-log 与 decision-log 双双通过。
- **触发场景**:任何 guard 板完成局进入 `load_game_log` 消费链。`profile_config.ALLOWED_ROLES` 已含 guard——用户从产品面就能开出守卫局。
- **后果**:`score_game` / `attribute_game` / `settlement_bundle`(Qt 结算画面数据源)/ 全部 validate CLI 对守卫局全断。L4 消融没炸只因 `ablation/metrics.py` 绕过 `load_game_log` 直读 JSON——已发布的 l4_guard/v4 verdict 不受影响,但产品结算路径已坏。
- **推荐动作**:修 bug(一行加 `"guard"`)+ 补「守卫局 game-log 过 parse/score 链」测试(`tests/test_guard_sentinels.py` 完全不调 parse/validate,正是漏网原因)。需开 plan(碰 `src/**`+`tests/**`)。

### B34-01 ｜ SYS-B3 ｜ Defect ｜ **Blocker** ｜ ✅ 已修 `f30340b`

- **证据**:`run_observer_server.py:59-69` env launcher 服务器启动构建一次;`run_emergent_deepseek_game.py:216-226` `_deepseek_factory` 在闭包外 `shared = build_provider(...)`,每局每座位复用;`llm_providers.py:236-237` 预算按实例 `_response_history` 计数跨局不清零;`artifacts.py:40-74` trace 按 request_id 去重,上局请求带不同 game_id 前缀不会被滤掉;`observer/run_manager.py:79-80` 路径 3 每次 launch 直接复用 `state.live_launcher`。
- **触发场景**:`launch-theater.py`(产品主入口)带 `DEEPSEEK_API_KEY` env 启动、客户端没填 key 时走路径 3,同一服务器进程连跑第 2 局。
- **后果**:第 2 局开局即预算耗尽 → 全座位 RNG 兜底但局仍报 completed;第 2 局 provider-trace 含第 1 局全部请求/响应;并发局共享实例无锁。这是 2026-06-10 已知坑「provider 预算跨局复用」——ablation/多 provider/BYO-key 三条路径都修了,唯独 env 预建路径漏网。
- **推荐动作**:修 bug——`state.live_launcher` 改为无参 per-launch factory(一处改动);或与 B5 退役 deepseek-only env 兜底合并解决(B34-06 给出完整 6 点残留面,退役差异是显式 403 非静默降级,安全)。

### B34-02 ｜ SYS-B3 ｜ Defect ｜ High ｜ ✅ 已修 `f30340b`（缺专用测试）

- **证据**:`provider_agent.py:170-187` 一切 provider 异常包成 `ProviderFailure(kind="timeout")` 不上抛;引擎 RNG 兜底走完整局 → `completed=True` → exit 0 → `status=completed`;`observer/run_manager.py:245-252` 的 `provider_auth_failed` 分支实际不可达(异常早被吞/sanitize 只剩类名);observer launch 链上无任何 live_success_rate 闸门(ablation 的 ≥0.7 过滤在 metrics,smoke 的门在 `emergent_smoke_check.py:67`,均不在此链)。
- **触发场景**:用户在 Qt 填错/过期 key 开 live 局。
- **后果**:0% live 的全随机对局对用户显示「completed + live」,唯一线索埋在 provider-turns.json;评测数据不过滤会混入假 live 局。
- **推荐动作**:修 bug——runner 收口按 `live_success_rate` 异常低返回独立 exit code 映射新 reason(如 `provider_all_fallback`),或至少把 live_success_rate 写进 status.json 供客户端展示。

### C12-01 ｜ SYS-C1/C2 ｜ Defect ｜ High ｜ ✅ 已修 `f2907f9`

- **证据**:夜动作与白天投票共用 request_id 格式 `f"{game_id}_r{rnd:02d}_{actor}"`(`emergent_engine.py:532`、`provider_agent.py:117`;witch/speech/hunter/scribe 有后缀,投票没有);`artifacts.py:40-53` 按 request_id 去重,注释自称 "ids never collide"。真实局实证:`l4_guard_000` 的 provider-turns r01 有 6 条投票 turn,provider-trace 只剩 p4、p6——4 个有夜动作座位的投票请求+响应整条被夜动作同 ID 吞掉。
- **触发场景**:每一局每个回合,所有夜行动角色的白天投票。
- **后果**:trace 系统性缺失关键角色(预言家/女巫/守卫/狼)投票的原始模型输出;P3-A 逐人复盘「预言家为什么投他」无原始证据;任何 request_id→response join 歧义。
- **推荐动作**:修 bug(投票 request_id 加 `_vote` 后缀,或 dedup 键改 `(request_id, phase)`)。属 artifact 契约变更,走 plan。

### C12-02 ｜ SYS-C1 ｜ Defect ｜ High ｜ ✅ 已修 `f2907f9`

- **证据**:`settlement_bundle.py:304-319` `_load_seat_meta` 读 `trace["responses"][i]["actor"]`,但 `ProviderResponse`(`provider_contract.py:46-53`)没有 actor 字段;真实 artifact 实测 responses keys = `[latency_ms, provider_name, raw_content, request_id, source_label, token_usage]`;对 `l4_guard_000` 实跑该函数,6 座位 token_usage 全空。`tests/test_settlement_response.py:179-181` 手造了带 `"actor"` 的假形状(runtime 从不写)→ 测试绿是假信号。
- **触发场景**:任何 live 局的结算画面/未来排行榜。
- **后果**:R-09 的 per-seat token/成本维度在生产恒为空;B5 成本汇总若复用此函数继承死路。这是 L4 轨已知「provider-trace 真形状」坑的又一处未改到点。
- **推荐动作**:修 bug——改读 provider-turns.json(turns 自带 actor+token_usage,剔除 `actor=="scribe"`,`run_emergent_deepseek_game.py:105` 注释已预告),同步把测试 fixture 换成真实形状。注意 C12-01 也导致投票 turn 的 token 在 trace 里缺失,两者宜同 plan。

### B12-01 ｜ SYS-B2 ｜ Defect ｜ High ｜ ✅ 已修 `a778e3e`（批次②）

- **证据**:女巫/猎人内联解析 `parsed.get("action", WITCH_PASS)`(`emergent_engine.py:805`、`:1006`)——JSON 合法但缺 `action` 键时静默当 pass 且仍记 `LIVE_SUCCESS`(`:807`、`:1008`);正规路径 `ProviderAgent.decide` 同情形判 `parse_failure` 并 raise(`provider_agent.py:249-268`,`tests/test_fake_provider.py:127` 钉死)。同一契约两套标准。
- **触发场景**:模型返回 `{"target":"p5","reason_summary":...}` 漏写 action。
- **后果**:live_success_rate 虚高;「女巫想救但输出畸形」被记成 pass,方向上偏置 witch_save_rate 与奶穿计数,且无 failure 记录可审计。注:已收口的 v4 臂 T-live 裁决(witch_save 1.0→1.0)不被此偏置推翻——救率是满的,偏置未实际显形;但这是未来所有女巫行为指标的系统性暗箱。
- **推荐动作**:修 bug——与 ProviderAgent 对齐,缺键记 parse_failure 并 `_downgrade_turn`。

### 其余 P0 级缺陷(Medium/Low)

| ID | SYS | 级别 | 类型 | 证据与要点 | 触发/后果 | 动作 |
|---|---|---|---|---|---|---|
| A-2 ✅`ccbe601`(+`7de827a`) | A1+A3 | High | Defect(规则空洞) | `emergent_engine.py:1099-1112` 夜死循环对每个死者无差别调 `_trigger_on_death`,deaths 含 poison_target;触发钩子不携带死因 | 毒死的猎人照常开枪,偏离标准规则;无 spec 裁决无测试 | ✅ 裁决=毒死不开枪;settler 返回 death_causes + pin 测试 + `board-rule-rulings.md` |
| A-3 ✅`ccbe601` | A1 | Medium | Defect(规则空洞) | `emergent_engine.py:818-822` witch_save 校验无自我排除/首夜限定 | 女巫任意夜可自救,与常见板规可能不符;无条文无 pin | ✅ 裁决=仅首夜自救;`_resolve_witch` self_save_late 校验 + pin |
| C12-05 ✅`a124ce5`(#59) | C1 | Medium | Defect | `scoring_records.py:533` 模块级全局 `_current_score_id_prefix`;observer 是 ThreadingHTTPServer,并发结算 `score_game` 竞态 | A 局 score_id 带 B 局前缀且被缓存固化(`settlement_bundle.py:385-390`);分值不受影响 | 修 bug(prefix 改参数传递,删全局) |
| B34-03 | B3 | Medium | Defect | `run_emergent_deepseek_game.py:102/111` `total_completion_tokens` 实际汇总 total_tokens | 成本口径虚高约 5-10 倍;B5 会继承错命名;scribe tokens 也计入 | B5 时修名+per-seat 分列 |
| B34-04 ✅`6448419`(批次③) | B3 | Medium | Defect(key 潜伏面) | `llm_providers.py:45-59` `ChatProviderConfig`(含 api_key)frozen dataclass 默认 repr 整 key 打印;`credential_store.py:61-65` 同类已防,这里漏了;`DeepSeekProviderConfig` 同病 | 任何把 config repr 进异常/断言 diff/日志的路径即泄 key;当前 src 无现行序列化点,属潜伏面 | 修 bug(`api_key: str = field(repr=False)` 一处改全家) |
| B12-02/03 + B34-10 ✅`a778e3e`(批次②) | B2/B3 | Medium | Defect | 三连分类失真:女巫/猎人路径把 respond 网络异常与 json 解析同 except,一律记 `parse_failure`+`INVALID_FALLBACK`(`emergent_engine.py:798-814/:1009-1013`);`provider_agent.py:170-187` 把 401/budget/transport 全记 `kind="timeout"`;budget 信号只活在 reason 子串(`deepseek_launcher.py:82-103` 双拼写匹配) | failure-audit/provider-turns 的 by_kind 统计不可信,live 批次诊断无法区分「模型坏」与「网络坏」 | 修 bug(拆分异常分类,增 kind 枚举,保留子串后向兼容) |
| C3-7 ✅`5a5edf7` | C3 | Medium | Defect(测试) | `tests/test_invariants_e2e.py:26` 只取 severity=="error",artifact_gap 被滤;`artifacts.py:64` provider-turns 缺失只记 gap | provider-turns 写盘回归丢失时 I4b 失去全部输入而 e2e 仍绿 | 写测试(`assertEqual(arts.gaps, ())` 或 gap 零容忍) |
| C3-1 ✅`71725be` | C3 | Medium | Defect | 幽灵 source id 双层静默:B1 运行时 `guards.py:21-25` `if ev is None: continue`,I4b 离线 `checker.py:134-136` 同样跳过且不产 violation;B1 docstring 声称的离线兜底不存在 | renderer 引用从未落 game-log 的 event id 时,两层防线对它失明 | ✅ runtime 抛 `DanglingSourceEventError`,offline `check_i4b` 产 I4b error,docstring 改如实 |
| C3-6 | C3 | Low | Defect(latent) | `checker.py:243-260` I8a 豁免只有同目标 save/poison;`_guard_night_rows` 的 died 含夜间猎人枪死(`emergent_engine.py:965` phase=night);rules_v1_2 支持 guard+hunter 同板 | 守卫守住 X、猎人夜枪 X → I8a 误报;当前 `GUARD_MULTISET` 恰无猎人未触发 | 进 backlog,开混板前修(豁免加 hunter_shoot 致死) |

---

## P1 — 结构性风险(Structural Risk)

### A-6 ｜ SYS-A1 ｜ High ——「加狼系角色 = 静默判错胜负」

- **证据**:胜负判定、`_wolves()`、`is_wolf`、狼队 known_roles、狼频道全部用 `role == "werewolf"` 字面量(`emergent_engine.py:664-671/292/459`、`action_runtime/state.py:18-19`、`role_visibility.py:38`、`abilities._alive_non_wolf`);`EnginePlayer.team`/`RoleDefinition.team` 存在但胜负逻辑不消费。
- **触发/后果**:加任何 team=werewolf 但 role≠werewolf 的角色(狼王/白狼王)→ 被算进好人侧,不报错直接判错胜负,狼频道也看不见它。「加角色成本剧增」里最隐蔽的一类。
- **推荐动作**:写 spec(win check/狼频道改 team 驱动,需字节门评估)。任何狼系新角色动工前必须先修;当前无此角色计划,不抢主线。

### A-4 ｜ SYS-A2 ｜ High ——加角色散落名单实测 10 处

- **证据**(逐处核实):
  1. `game_log.py:11` `VALID_VISIBILITIES`(已被 A-1 证明是真炸点);
  2. `profile_config.py:53` `ALLOWED_ROLES` 字面量——且含 guard 不含 hunter(猎人 rules_v1_1 已 ship,产品 profile 却开不了,名单自相矛盾);
  3. 引擎内 5 处:`emergent_engine.py:91` `NIGHT_DISPATCH_ORDER`、`:279` `_RESOLVERS`、`:225` 单特殊角色元组 `("seer","witch","guard")`、`:257` ruleset 选择 if/else、`:198` 手搓 hunter 板;
  4. `provider_agent.py:25` 模块级钉死 `rules_v1_2()`(见 A-5);
  5. `runtime_events.py:53` + `observer_projection.py:36` 两张可见性名单;
  6. `prompt_v2.py:17/20` `ROLE_NAMES_ZH`+`ABILITY_DESCRIPTIONS`(`.get` 兜底吐原始 token,漏加=prompt 静默劣化)、`display_labels.py:15-16`;
  7. `scoring_types.py:137` `KEY_VILLAGER_ROLES` + `scoring_records.py:388/410`(guard 被按普通村民计分);
  8. `invariants/checker.py:94` `CONSUME_TYPES` / `:165` `DEATH_CAUSE_TYPES`;
  9. `profile_config.py:86` `DEFAULT_ROLE_PROMPTS`(guard/hunter 空 persona);
  10. `ablation/metrics.py:14-41` `classify_event` 英文 summary 正则,新角色事件落 `"other"` 静默丢弃。
- **好消息**:PROJECT_MAP 记载的债务 `_KNOWN_ROLE_TEAMS` 一半已还清——`observer_protocol.py:21` 起三处全 derive 自 ruleset `known_role_teams()`。
- **推荐动作**:进 backlog 立「加角色检查单」+ 哨兵测试(对 ruleset 每个角色断言上述表覆盖);`ALLOWED_ROLES` 收不收 hunter 需用户裁决。

### C3-2(合并 A45-5)｜ SYS-C3×B1 ｜ High ——文本注入通道机制性绕过泄漏防线 ｜ ✅ 收口 `7493daa`(测试 `5a5edf7` + spec + 漂移哨兵)

- **证据**:`augment_witch_observation` + `witch_obs_suffix` 注入文本不进 `observation_source_event_ids`(`emergent_engine.py:770-771` vs `:791/:794`),B1 运行时门与 I4b 离线检查对它完全失明;同类通道还有 `speech_obs_suffix`(`:856`)、`action_obs_suffix`(`:530`)、scribe 输入(`:908-918`,source ids 恒空)。结构性根因:可见性 oracle 无法表达「女巫合法知道刀口」(`werewolf_kill` 的 `werewolf_team` 可见性不含女巫),合法信息被迫绕道文本注入,于是防线无法区分合法注入与泄漏注入。spec 要求的「任何记忆注入必须带 source ids 过 I4b」在当前机制下是真空通过。且全 tests 无一条「跑守卫板局、扫描所有非女巫座位 `observation_text`、断言不含 victim 句式/『【解药协调提示】』」的负向测试(grep 证实)。
- **当前内容已核干净**:v4 注入是纯静态文本,输入只有公开板组成+女巫自身状态,不含守卫目标/存活;唯一防线是 golden 字节锁+人审。
- **推荐动作**:先写测试(上述负向扫描,便宜且立刻补防);中期写 spec(注入点登记表+输入可见性声明,长期让合法角色知识走带 id 的事件通道——挂 EffectQueue/ledger 线)。prompt_v4 已归档不迭代,但 v3 的 augment 通道是 canonical 路径,此洞长存。

### B12-04(合并 B34-08)｜ SYS-B1/B3 ｜ Medium-High ——产品 launch 路径恒 prompt_v1,与 guard 板组合成可用性陷阱

- **证据**:`deepseek_launcher.py:216-223/266-274` 两个产品 launcher 均不传 prompt_version(默认 `"prompt_v1"`,`run_emergent_deepseek_game.py:129`);`profile_config.py:301` profile 顶层白名单无 prompt_version;而 `ALLOWED_ROLES` 已放行 guard、`DEFAULT_ROLE_PROMPTS` 对 guard 返回空 persona(`:560` `.get(role, "")`)。
- **触发/后果**:用户在 Qt 配守卫局开 live → v1 渲染:无规则卡、无守卫能力说明、无连守禁令、空 persona——b1/b4 诊断已证 v1 上下文不足,必然大量 invalid 降级+机制幻觉。版本能力只接到 ablation CLI,没接产品面。SYS-B4 scaffold 上产品路径时还需同时开 profile schema、launcher、scribe 凭证选择三处缝。
- **推荐动作**:写 spec(profile/launcher 加 prompt_version 旋钮,B4/B5 进场时做);短期至少对「板含 guard 且版本 v1」加 fail-loud/警告。

### 其余 P1

| ID | SYS | 级别 | 证据与要点 | 触发/后果 | 动作 / 不建议现在做的理由 |
|---|---|---|---|---|---|
| C3-3 | C3 | High | `fuzz.py:8-41`:固定 50 seed 但唯一随机性=victim×seer target,有效形状 ≤9 种;`_ROLES` 固定 4 人无 guard;合成 artifact 直喂 checker,引擎不在环;spec §6 要求的 script-generator 未实现 | 引擎结算/守卫交互组合空间(奶穿×毒×枪×级联)无随机探索,I8a/b/c 在 fuzz 中恒真空 | 写 spec 落 engine-in-loop fuzz(守卫板进 generator);PROJECT_MAP 已自知缺口,按既有路线 |
| C3-4 ✅`3523cf1`(#60) | C3 | Medium | `check_run` 在 src/scripts 零调用点(grep 证实);L4 verdict 的 45 局 0 违例是会话内手工跑的 | 下个 live 批次可能在无人跑 checker 情况下出 verdict | 修接线(ablation runner 每局落盘后调 `check_run` 写进 metrics `validity.invariants`)——便宜,下个 live 批次前值得做 |
| C3-5 | C3 | Medium | `tests/test_action_runtime_parity.py:31-43` 差分 oracle ROSTER 无 guard、`_old_night_deaths` 无 guard 参数;②a 全局 diff-gate 已删(`tests/parity_scripts.py:5-7`) | settler 奶穿分支回归时无第二证人(单测同步改错则漏网) | 写测试(手写守卫公式独立 oracle,枚举 guard×save×poison×alive 全组合);进 backlog |
| B34-07 ✅`228f240`(+`7de827a`) | B3 | Medium | `emergent_smoke_check.py:71-87` honesty gate 逐 turn 比对 `DEEPSEEK_SOURCE_LABEL`,manifest gate 要求全座位同一 expected_model | 加新 provider/混合局后 smoke 验收不可用——加 provider 的真实成本在这里不在 registry(registry 实测只碰 2 文件) | ✅ `LIVE_PROVIDER_SOURCE_LABELS`(⊆VALID,≠fake)+per-seat `expected_models_by_seat`;DeepSeek 兼容;全离线 fixture |
| C12-04 ✅`3523cf1`(#60) | C1 | Medium | `metrics.py:134-161` aggregate 不读 manifest evaluation_bucket;`ablation/__main__.py:24-32` compare 不校验版本/板;`harness.py:50-80` run_arm 不清理已存在 out_dir 且 `status="completed" if gl.exists()` | 同 label 换版本重跑时旧版本完整局混入聚合;跨 bucket 混样不可见 | 修 bug(aggregate 断言 bucket 一致+写入 metrics;run_arm 拒绝非空目录),下个消融臂前做 |
| C12-06 | C1 | Medium | decision 记录(`emergent_engine.py:341-371`)无 request_id;reason_summary 是引擎模板非模型原话;speech 无 decision 记录;启发式 join 又撞 C12-01 | P3-A 逐人决策链(看到了什么→为何投/杀/救)拿不到原始理由,补齐需改引擎=返工点 | 写 spec(decision 加 additive request_id 字段,validator 允许扩展),排 C12-01 修复后、P3 动工前 |
| C12-03 ✅`3523cf1`(#60) | C1 | Medium | `metrics.py:126-127` milk_pierce 对无守卫板 `sum(... or 0)`=0 而非 None;同家族 `guard_target_seer_rate` 却用 `_mean`→None,N/A 约定不一致 | compare 对 guard vs 非 guard 臂打出 `0 vs 12, delta=-12`,「没有奶穿机制」被读成「奶穿为 0 更优」 | 修 bug(board 无 guard 输出 None),与 C12-04 同 plan 顺手 |
| A-5 | A2 | Medium | ruleset 双源:引擎按板选(`emergent_engine.py:257`)vs `provider_agent.py:25` 全局钉 `rules_v1_2()`;今天一致仅靠 append-only superset(`test_allowed_actions_pinned` 守着) | rules_v1_3 改任何共享角色 ability → provider 侧 allowed_actions(模型可见字节)与引擎裁决静默分叉 | 进 backlog(按板角色集合数据驱动推导最小覆盖版本,单一 helper 共用),rules_v1_3 前必修 |
| A45-1 ✅`010cfe8` | A4 | High(远期) | `observer/handler.py:395-420` artifact 端点收 perspective 但不使用;`ALLOWED_ARTIFACTS` 含 provider-trace/decision-log/game-log;trace 含全部私密 observation_text | 当前单机审计威胁模型内 OK;多客户端(每座位一个真实参与方)接入同一 server 时 role:pN 过滤形同虚设 | ✅ ADR `docs/adr/2026-06-12-perspective-not-access-control-boundary.md` 声明非鉴权边界;P3 多客户端前补鉴权分级 |
| A45-7 | A5 | Medium | `observer_enrichment.py:74-114` decision→event reason join 是无 round 贪心匹配(docstring 自认);decision 行无 round 字段 | 同键跨轮重复+任一侧 decision-无-event 时队列错位,「我的理由」标错事件 | 进 backlog(decision row 加 round,join 键升级),P3 复盘前修 |
| A45-3 | A4 | Medium | 引擎侧 `role_visibility.py:38` 对任意 role 泛化匹配 vs observer 侧 `observer_projection.py:274-289` 仅枚举 seer/witch/guard;漏 observer 侧时运行时硬门 `assert_prompt_entitled` 抛 `PromptLeakError` 整局崩 | 加新私有视野角色漏 observer 一侧 → fail-loud 但报错语义是「泄漏」,误导排障 | 写测试(哨兵:枚举 ruleset 全角色×私有事件断言 entitled==True,固化「两侧同步加」) |
| A45-2 | A4 | Medium | `observer_projection.py:36` `ROLE_SPECIFIC_EVENT_VISIBILITIES` 是导出但逻辑死亡的常量,真实现是 if 链(:268-296),无哨兵绑定 | 加新角色时把它加进 frozenset 以为生效,实际 projection 仍 hidden(静默欠分享) | 修 bug(if 链由集合驱动或删常量)+哨兵;与加新角色工作同批 |
| A-7 | A2 | Medium | 女巫注册表外孤岛:药水状态是 `_run_inner` 局部变量(:1076-1094),校验内联与 ruleset 谓词双份(语义当前一致,逐条比对过);有引擎注释+`test_witch_potion_one_shot_sentinel.py` 哨兵,非裸奔 | 女巫今天走 validator 必坏(②b BLOCKING 已记录) | 维持既有 backlog 顺序(②b potion ledger);加角色前别添第四条校验路径 |
| A-8 | A3 | Low | `triggers.py` TriggerSystem 是 orphan(队列式死亡连锁),引擎用自己的 `_trigger_on_death` 递归(:953-967),两套语义并存;ADR 2026-06-09 已记载 | lovers/狼王上场时误接 TriggerSystem 顺序语义不同 | 进 backlog——加多死亡连锁角色时二选一(删或接),别双活 |
| B34-06 | B3 | Medium | deepseek-only env 兜底完整残留面 6 点(`run_observer_server.py:29-80`、`run_manager.py:63-80/105-108/154-157`、`state.py:26-33`、`launch-theater.py:97-139`);路径 2(client deepseek key 单模型)实际不可达=纯死代码 | 退役差异=env-only 用户 launch 从成功变显式 403,安全 | B5 按 6 点一次清干净,顺带消灭 B34-01 与死路径 2 |
| B34-09 | B4 | Medium | PROJECT_MAP:123 宣称 manifest `enabled_scaffolds` 字段「已留」,全仓 grep 仅命中 docs;实际缝=`requires_scaffold`+`scaffold_model` | 按图纸开工 B4 的人找不到字段 | 改 PROJECT_MAP 措辞,或 B4 时真正落字段 |

---

## P2 — 改进项(Improvement,全部不抢当前主线)

| ID | SYS | 要点(证据) | 不建议现在做的理由 / 归属 |
|---|---|---|---|
| A45-4 ✅`6b1152d` | A4 | R-17 防漂移门 `EVENT_TYPE_REQUIRED_VISIBILITY` 缺 `guard_protect`,且测试只跑无守卫板(`tests/test_event_visibility_invariant.py:34-53`);保护现仅靠另两处守卫测试 | 一行映射+一个脚本局,并入 A-1 修复 plan 顺手做 |
| A45-6 ✅`6b1152d` | A4 | `tests/test_visibility_parity.py:39-47/69-74` `_VISIBILITIES` 与 role-on-protocol 锁均漏 `"guard"` | 同上,一行改动并入 |
| C3-12 ✅`5a5edf7` | C3 | 守卫局 sentinel(`test_guard_sentinels.py`)断言结局但不调 `check_run`;I8 唯一执行载体是手写 dict fixture 且 visibility 填 `"internal"` 与真实 `"guard"` 不同 | 一行断言,并入 C3-4 接线 plan |
| A45-8 | A5 | I7 role_revealed 靠英文正则 `revealed as (\w+)`(`checker.py:193`),不匹配时静默空验证 | 等 i18n 触碰该 summary 时一起;或事件 data 带结构化字段 |
| A45-10(=B12-05) | A4/B1 | shown vs legal 目标差:守卫 allowed_targets 含昨晚守护对象、女巫含自己(毒非法)(`provider_agent.py:115`);prompt 措辞「MUST select from」与板卡禁令矛盾;`registry.legal_targets` 存在未用于出题 | 无泄漏,纯 live 质量损耗;模型可见字节变更须走 prompt 版本流程,等下次 prompt 修订一起 |
| C12-07 | C2 | events.jsonl 全有或全无:`_read_events_jsonl_safe` 重试 3 次返回 `[]`,损坏=整局回放静默变空,无错误码;SSE `last_size` 先更新有窄窗 | 回放健壮性,等真实损坏案例或 P3 |
| C12-08/09 | C2 | 无 status.json 历史局永不可结算(`observer_protocol.py:180-192`+`settlement_bundle.py:341`);run_dir TOCTOU 并发双 POST 回 500 非 409 | 边缘场景,无用户报告 |
| C12-10/11 ✅`3523cf1`(#60) | C1 | milk_pierce_*_count 是总数非率(两臂 n_valid 不同时 delta 失真);`classify_event` 关键词分支在 phase 判断之前,英文 `saves` 发言会污染夜类计数 | 下个消融臂的 metrics plan 一起 |
| A-9 | A2 | `scoring_records.py:583-592` guard_protect/hunter_shoot 不在计分 dispatch;救守卫不算关键村民(+1 非 +3) | 依赖 A-1 先修(guard 局进不了 scoring),属 P3 评测口径 |
| A-10 | A3 | 夜死公告顺序固定 victim→poison(`settler.py:55-61`→`emergent_engine.py:1123`),双死之夜顺序泄露刀/毒 | 模型可见字节变更须走版本纪律,收益小 |
| A-11/A-12 | A1 | hunter 枪死者不进 metrics deaths(无 hunter 臂,休眠);`harness.py:63` round_cap=3 长局被剔除的存活性偏差(实测 45/45 completed 未触发) | 开 hunter 臂/出现失败局时再修,verdict 报剔除数即可 |
| B34-05 | B3 | Qt `CredentialStore.cpp:12/27-30/84-97` QSettings 明文存 raw key(Windows=HKCU 注册表);读侧打码正确 | BYO-key 设计已接受 local;DPAPI/QtKeychain 是独立工作项 |
| B34-11 | B3 | observer live 局 engine seed 恒 0(`run_emergent_deepseek_game.py:124`,launcher 不传)→ 平票/兜底 RNG 每局同序,叠加 L3 夜1偏置 | 与 L3 偏置裁决一起处理(run_id 派生 seed,与 role_shuffle 手法一致) |
| B34-12 | B3 | DELETE 失败回显含服务器路径的 OSError(低危,loopback);provider 级预算只数成功响应与引擎级口径不一致(引擎层兜住) | 低危;复用 provider 单体时再收口 |
| B12-06 | B1 | ablation CLI 允许 `--prompt-version prompt_v4 --board standard` 静默空转(v4 在无守卫板恒等 v3) | prompt_v4 已归档不迭代,风险消退;若复活 v4 系列再加 fail-loud |
| B12-07/08/09 | B1 | 两处内联增强(witch augment/hunter suffix)无版本 hook=注册表已知豁口(有文档);golden 组合文本多为相对锁;`ProviderRequest.prompt_version` 默认 v1 无报警 | 测试网当前闭合;等 v5 需求时顺势收进 renderer 方法 |
| C3-8/11 | C3 | B4 candidate-skip 不可观测(建议 debug 计数进 failure_audit,不破字节门);I4a `check_prompt_subset` 生产零调用 | 防线增强,等下一刀(ledger)护栏需求 |
| A45-9/11/12 | A4/A5 | god snapshot `private_event_ids` 恒空(:436);projection docstring 缺 guard_event;consensus-log responses 是合成叙事非真实协商(`:709-758`,`actual_rounds=1` 恒定) | 文档/语义标注类,顺手时做 |
| C3-10 | C3 | 「测试计数跨会话不可比」已解谜:`unittest discover` 收集文件系统非 commit,共享工作树残留 untracked test 文件即计数漂移;loader.errors=0,机制无漏洞 | 把「计数基线须附 `git status --short` 干净证明」写进 testing skill 即可 |
| C3-9 | C3 | CI 真跑全量+golden v1-v4 强制,但触发=push to main(直推授权下 CI 是事后检测非合并门);win32-only 测试 CI 必跳(设计内) | 维持「推前本地全量绿」纪律;可考虑分支保护要求 CI 绿 |

---

## 查过没问题的面(勿重复审)

- **奶穿结算单源单点**:全仓唯一结算点 `JointSettler.resolve_night`(查 ruleset 表),引擎夜结算唯一入口;settler/引擎/sentinel 三层测试覆盖;守卫不挡毒、毒刀同体去重、连守禁止(含 fallback 同排除)、双特殊角色构造期 fail-loud 均有测试。
- **守卫可见性四处接线全对**:引擎泛化(`role_visibility.py:38`)、observer 枚举分支(`observer_projection.py:285-289`)、I4b oracle、I2 动作表(`checker.py:63-64`)——PROJECT_MAP 记载的「私有 tag 只认 seer/witch」债务已对 guard 还清;`test_guard_visibility.py` 断言其余 5 座位 hidden;`last_guarded` 不进任何事件/快照/他人 prompt。
- **key 不进序列化点**:manifest persona 哈希后丢弃;manifest/trace/snapshot 三写盘点全过 `redact_secret_values`;runtime emit 走 `assert_no_secret_patterns`;transport 异常 sanitize 单源 `from None` 断链;credentials API 不回显不记录、loopback+same-origin。
- **prompt 注册表闭合**:`get_renderer` 未知版本 fail-loud,三层调用全过注册表,哨兵钉 `REGISTRY==KNOWN_PROMPT_VERSIONS`;requires_scaffold 单源(引擎/harness/runner 三处 fail-loud);v4 三条件门逻辑正确(8 组合真值表+3 引擎 canary+golden);`_board_card_has_guard` 用 `"- 守卫("` 行标记防子串假阳性;ledger 四版本哈希被测试校验,RULE3 防无意义 bump。
- **ProviderAgent strict-JSON 不吞合法非常规输出**(五字段必填、白名单、全失败 raise+emit;吞的问题只在 B12-01 两个内联站点);ActionEnvelope from_legacy 映射正确。
- **加第 10 家 OpenAI 兼容 provider 实测只碰 2 个文件**(registry 1 条+哨兵更新);凭证白名单/capabilities/profile schema/Qt 下拉全自动跟随;`VALID_SOURCE_LABELS` 已含 OpenAI 兼容与 mixed。
- **provider_result_kind 单点标注**(引擎五站点盖戳,跨 provider 必然一致);兜底 RNG 在 ablation/runner 层每局新建(唯一漏网=B34-01 env 路径);decide 前清 `_last_response`,无串台。
- **trace 形状消费方全部按真形状 `{requests,responses}` 读且按 request_id join**(metrics/smoke/replay 三处)——唯 settlement `_load_seat_meta` 例外(C12-02)。
- **R-09 model/provider 标注在 role_shuffle 下对位正确**(manifest 按 player_id 记,角色单独线穿,settlement 按 player_id join;真实局验证)。
- **observer 拆分后冻结契约仍被盯住**(handler docstring 列冻结面;覆写/直调测试在位;facade 25 名 re-export 平价测试);SSE size-gate 保留;state 锁内读写;BUNDLE_VERSION 不匹配自动重算,partial 不缓存。
- **安全网骨架真实有效**:B1 四站点 try 外(突变测试钉死)、B4 commit 层三站点 raise(与用户裁决一致)、I1-I7 按事件类型工作与板组成无关、I8a/b/c 已注册;milk_pierce 两层定义(death⊆overlap)与 settler 规则逐行核对一致,机器回算与人工 12/12 对齐;新指标在 live率≥0.7 闸之后计算与旧指标同口径。
- **CI 真跑全量 unittest+golden 守卫强制**;无 F: 盘符依赖测试;discover loader.errors=0。

---

## Top 5(按风险排序)

> 收口状态(2026-06-12,见上方三轮进度表):**1~4 全部 ✅**(A-1 `6b1152d`、B34-01/02 `f30340b`、C12-01/02 `f2907f9`);**C3-4 ✅**(`3523cf1`#60);**C3-2 ✅ 收口**(`7493daa`)、**两条规则裁决 A-2/A-3 ✅**(`ccbe601`+`7de827a`)、**C3-1/B34-07/A45-1 ✅**(`71725be`/`228f240`/`010cfe8`,均 `7de827a` push)。**唯余 5(A-6 结构性)= 加狼系角色前置门,无当前角色计划不抢主线。**

1. **A-1(Blocker)**:guard 局 game-log 校验必炸 → 产品结算/评分/validate 链对守卫局全断,已动态复现。修复一行+测试,性价比最高,建议立即开小 plan。
2. **B34-01(Blocker)**:产品主入口 env live 路径跨局共享 provider——预算累计+trace 跨局污染,已知坑在第 4 条路径的漏网。一处改动拆弹,或并入 B5 退役一并解决。
3. **B34-02(High)**:坏 key 的 0% live 局对用户报 completed+live,`provider_auth_failed` 是死代码。直接伤产品可信度与评测数据纯度。
4. **C12-01 + C12-02(High,同一 artifact 面一并修)**:trace 每局每轮系统性吞掉夜行动角色的投票原始输出;结算 per-seat token 恒空且测试假绿。不修则 P3-A 逐人复盘和 B5 成本汇总都建在坏数据上。
5. **A-6(High,结构性)**:胜负/狼频道按 role 字面量非 team——加任何狼系新角色会静默判错胜负。不抢当前主线,但必须作为「加角色前置门」钉进 backlog,连同 A-4 的 10 处散落名单检查单。

紧随其后:**C3-2**(文本注入通道机制性绕过 I4b,先补便宜的负向扫描测试)、**C3-4**(checker 接进 ablation runner,下个 live 批次前做掉,让「0 违例」从手工变机器)。

**两个规则空洞已裁决并收口**(`ccbe601`):毒死的猎人**不开枪**(他因仍开枪,settler 权威死因)、女巫**仅首夜可自救**——条文落 `docs/specs/board-rule-rulings.md`,各补 pin 测试(含守卫板/奶穿对照)。

---

## 下一轮并行批次建议（2026-06-12 晚）——✅ 四束全部完成并合 main+push

下列四束**文件互斥、无共享状态**,已各开隔离 worktree 并行落地,全合入 main `9f0827f` 并 push（详见上方「第二轮」进度表）:

- **批次①｜ablation 护栏硬化**（C3-4 + C12-04 + C12-03）✅ `3523cf1`(#60):`ablation/harness.py` 接 `check_run` 每局落盘后写 `validity.invariants`;`aggregate` 断言 evaluation_bucket 一致并写入 metrics;`run_arm` 拒绝非空 out_dir;`milk_pierce` 对无 guard 板输出 `None` 非 0。文件面=`ablation/{harness,metrics,__main__}.py`。**下个消融臂前做掉**,让「0 违例」从手工跑变机器门。
- **批次②｜engine 失败分类对齐**（B12-01 + B12-02/03 + B34-10）✅ `a778e3e`:女巫/猎人内联缺 `action` 键改记 `parse_failure`+`_downgrade_turn`(与 `ProviderAgent.decide` 对齐);拆分网络异常 vs JSON 解析异常;`provider_agent` 把 401/budget/transport 从一律 `kind="timeout"` 拆成枚举(保留子串后向兼容)。文件面=`emergent_engine.py`+`provider_agent.py`+`deepseek_launcher.py`。修复后 failure-audit/provider-turns 的 by_kind 才可信。
- **批次③｜B34 收尾 + key repr 防泄**(B34 测试缺口 + B34-04)✅ `6448419`:补 `tests/test_observer_run_manager.py` 钉死 `low_live_success_rate` 闸门 / per-launch factory materialize 两条新路径;`ChatProviderConfig`/`DeepSeekProviderConfig` 的 `api_key: str = field(repr=False)` 一处改全家堵潜伏泄漏面。文件面=`tests/`+`llm_providers.py`。轻量。
- **批次④｜score_id 全局态竞态**(C12-05)✅ `a124ce5`(#59):`scoring_records.py` 模块级 `_current_score_id_prefix` 改参数传递删全局,消除 ThreadingHTTPServer 并发结算 A 局前缀污染 B 局缓存。文件面=`scoring_records.py`(+`settlement_bundle.py` join 点)。

四束均碰 `src/**`(+`tests/**`),按 PR-first 须各绑一份 Implementation Plan。批次① 与 ② 价值最高(下个 live/消融批次前的护栏与诊断可信度)。

**先于实现需用户裁决**:A-2(毒死猎人开枪)、A-3(女巫自救/限首夜)两条规则空洞——裁决产出 spec 条文后才能 pin 测试,不宜并入上述机械批次。

---

## 附:审计元数据

- 审计方式:6 个并行只读 subagent,按 System View 分组;主审计员对两个 Blocker 亲手复核证据。
- 动态复证:A-1(load_game_log 对真实 l4_guard 局抛错)、C12-01/02(真实局 artifact 实测)。
- 审计零改动:`git diff` 为空(本报告文件除外)。
- 已知历史项对照:2026-06-08 体检的 11 项确认风险与本次不重叠(D-3/D-4/D-5/E-5 等已在 provider/launcher 机械重构关闭);本次新发现集中在 guard/v4/milk_pierce 新代码面与跨系统接缝。

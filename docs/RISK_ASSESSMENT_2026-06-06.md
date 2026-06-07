# 全项目风险评估

> **G:\Werewolf-agent**(AI-vs-AI 狼人杀评测平台,main==5f41d04,branch `p2-d-settlement-screen` 在飞行中)

**一句话总览:** 项目在可见性安全(visibility hard-gate)与密钥处理上工程质量扎实,但存在一类已被多处确证的"事件词汇 mismatch"(engine 发 `witch_kill`,scoring/render 消费 `witch_poison`),它静默污染了被声明为"评测就绪"的 P3 入口数据,且整个 602 测试套件因为没有跨 engine->scoring 接缝的测试而全绿掩盖了它。

**评估口径:** 纯只读审计(未编辑/写入/创建任何文件)。所有 finding 经过对抗式双视角(double-lens)验证:`confirmed` = 两个视角都认定为真;`likely` = 一个视角认定为真。原始 45 条,confirmed 34、likely 4、rejected 7。

---

## 修复进度(更新 2026-06-07)

> 报告产出后已修复的项。**全套件现真实全绿:`NO_PROXY=127.0.0.1 python -m unittest discover -s tests` → 630 tests OK**(此前 FAILED:failures=1, errors=47 —— 47 个 error 是被强制代理拦截 localhost 所致,设 `NO_PROXY` 即解,非代码问题;详见环境说明)。

**已修复(✅):**
- **batch-6 CI/结构/perf(2026-06-07):**
  - **R-38** 无 CI —— 新增 `.github/workflows/tests.yml`(clean Linux runner 跑全量;localhost 通,observer HTTP 测试真执行)。
  - **R-11** HTTP 安全测试本环境 ERROR —— 由 CI 解决(clean runner 上 socket 测试真跑真验;in-process harness 重构为可选优化)。
  - **R-06** 双 visibility 重复 frozenset —— 收敛为单一来源(observer_visibility 从 observer_protocol import);行为差异(protocol 对 role:pN 故意 under-share = 安全方向)保留,batch-2 守卫测试强制 protocol ⊆ projection。
  - **附录·byte-repro** —— 文档化边界:runtime events.jsonl 是 observability(uuid/wall-clock ts),非可复现 eval 源;顺序由确定性 `seq` 承载,eval/replay 复现由 game-log/decision-log 保证。
  - **附录·SSE perf** —— append-only 文件加 size-gate,空闲 tick 不再重读+重校验整文件。
  - **R-35** legacy runners —— scripted/mock/attribute_game CLI 加 LEGACY docstring 指向 canonical 入口。
- **batch-5 eval/engine/security 清理(2026-06-07):**
  - **R-19** 脱敏过宽 —— runtime_events VALUE 检查收窄到高置信凭证形状(去 bare secret/token/auth),不再毁正常游戏文本。
  - **R-21** per-decision ScoreRecord 丢弃 —— bundle 加性增 `score_records[]`。
  - **R-30** 单 seer/witch 假设 —— 构造期 >1 即报错(不再静默丢角色)。
  - **R-22** attribution F.3 witch_misfire 硬编码 g001 —— 改为按真实 witch_poison 目标计算;F.2/4/5 notes 去 g001;gold fixture 重生成(g001 状态/结构不变)。
  - **R-17** 无 engine 侧 visibility 不变量 —— 守卫测试断言每个私有 event type 携带正确 visibility(seer/witch/werewolf_team)。
  - **R-16** specific_player_ids "死分支" —— 文档化为 gold-replay 兼容(两 engine role_assignment 发 public),非死代码。
  - **R-34** `.logs/review` packet + `.grill` 笔记 跟踪后忽略冲突 —— untrack + `.grill/` 入 .gitignore。
- **batch-4 engine+文档(2026-06-07):**
  - **R-18** 狼 role-projection 快照拷全 event id(seer/witch 元数据泄漏,g1b/mock 路径)—— `_wolf_obs` 改用 `_private_refs_for_role("werewolf")`(all + werewolf_team);回归测试交叉核对夜2狼快照 vs game-log visibility。
  - **R-29** fallback 目标恒为座位 0(系统性替罪)—— 三处 `candidates[0]`/`cands[0]` 改 `self._rng.choice`(seeded,确定性,分散)。
  - **R-25/26/37** 文档路由陈旧 —— AGENTS.md 不再硬编码 G1h、改指 PROJECT_MAP(Qt/observer/emergent in scope);README 修"下一候选 G2d";TASKS/ROADMAP 正文 G4-next 加 inline superseded 标记。
- **batch-3 eval-readiness/清理(2026-06-07):**
  - **R-09** 无 per-seat model/token —— 趁 v1 schema 未冻,`players[]` 加性增 `model`/`provider`(prompt-manifest)+ `token_usage`(provider-trace 按 actor 汇总);`_load_seat_meta()` best-effort。
  - **R-08 余项** —— 缓存命中校验 `bundle_version`(不符则重算,P3 永不读旧 schema)+ 原子写(temp+replace)。
  - **R-12** render label 双份重复 —— 抽 `display_labels.py` 单源,两 renderer import。
  - **R-28** —— 抽取时发现 `day_announcement` + `witch_pass` 发出却无 label(渲染成原始英文)→ 补全;加守卫测试断言所有 engine 发出的 event type 都有 label。
- **batch-2 安全/BYO-key(2026-06-07):**
  - **附录·DeepSeek 异常链带 key(HIGH)** —— `raise ... from exc`→`from None` + 仅暴露异常类名,断开携带 `headers`(Bearer key)的 frame 链;强化回归。
  - **附录·review-packet 脱敏(最高价值未做项)** —— packet 原样嵌 diff hunk 且无 secret 扫描;新增 `redact_secrets()`(窄高置信 sk-/Bearer/Authorization/api_key)写出前过滤整包;端到端测试。
  - **R-06(双 visibility 分歧→leak)守卫** —— 跨模块测试断言高流量 protocol 过滤器 ⊆ 未受信 projection 基线(protocol 可见⟹projection 可见)+ 重复 frozenset 漂移守卫;完全收敛仍为独立 refactor。
- **R-01 / R-03 / R-05 / V-1~V-8** witch 词汇全链 —— PR #43(`witch_kill`→`witch_poison`),`src` 已无 `witch_kill`。
- **R-02** engine→scoring→settlement 无端到端测试 —— `tests/test_engine_to_scoring_e2e.py`(真实引擎输出过 score_game+attribute_game+settlement;含词汇 registry 静态守卫)。
- **R-04** 女巫永远无法救人 —— `augment_witch_observation()` 把当晚 victim 注入女巫自身 prompt。
- **R-07 / R-10 / R-14 / R-27** witch 降级/文档 caveat —— 词汇修复后 moot。
- **R-08(部分)** —— settlement 缓存坏件自愈 + 不缓存降级/部分件(PR #45/#49);余:`bundle_version` 读回校验 + 原子写仍待做。
- **R-13** 空 fix 分支 —— 随 #43 落地。
- **R-15 / R-33** AGENTS.md 缺 Context Budget Gate(唯一真实失败测试)—— 已恢复段落。
- **R-20(部分)** decision_quality 无标志 —— `decision_quality_available` 字段(PR #49,部分降级)。
- **R-23** 五个陈旧分支 —— 已删。
- **R-24** `.runs/` 未 gitignore —— PR #48。
- **附录·持久化(HIGH)** `status.json` 从不写 → 重启后 run 不可结算 —— `write_run_status` 落盘 + `_get_status` 重启 fallback。
- **附录·缓存中毒(MEDIUM)** 降级件被永久缓存 —— PR #45/#49 只缓存完整件。

**仍待修 / 刻意不做:**
- **R-36(8 launcher 无共享脚手架)** —— **刻意 deferred**:跨 8 个 launcher 抽 fail-closed 共享 helper 是大 refactor、破坏风险高、价值低(纯 DRY);报告本身评 low 且建议"裁剪 scripted runner 时一并处理"。守门契约已各自有测试覆盖,不强行返工。
- **R-06 行为层完全收敛** —— **刻意不做**:常量已单一来源;让 /events,/stream 改走 projection 权威会让它们对受信 role:pN **多分享** role-private 事件,即**扩大泄漏面**。当前 protocol 故意 under-share(安全方向),由守卫测试强制 protocol ⊆ projection。单一 visibility 权威留作未来若要修 under-share 时的专项。

---

## 执行摘要

- **最致命(BLOCKER):** witch 毒药动作的事件词汇贯穿整条链路 mismatch(`emergent_engine.py:43/625` 发 `witch_kill`,`scoring.py:120/674/765` 只消费 `witch_poison`)。这不是异常,scorer 静默跳过,导致每一局 emergent/fake-default 游戏的毒药动作得分为 0、`poison_accuracy=0`、attribution F.3 失明,而 settlement bundle 仍以 `degraded=false` 渲染一份"看起来完整"的错误战报。**这正是被 PROJECT_MAP 声称"评测就绪以免 P3 返工"的那份数据。**
- **第二 BLOCKER:** 没有任何测试横跨 engine->scoring/render 接缝(`tests/test_scoring.py:29` 只喂 gold fixture,`tests/test_emergent_engine.py:13` 从不 import `score_game`),所以上面这个确证 bug 在 602 个测试里全绿通过 —— bug 对测试套件完全不可见。
- **修复尚未开始:** 指派修这个词汇 bug 的 `fix/p2-a-witch-poison-vocab` 分支 0 commit,tip 就是 main HEAD —— bug 在包括 `p2-d-settlement-screen` 在内的每个分支上都活着。
- **安全面健康:** 可见性 hard-gate fail-closed(未知 visibility 默认 `internal`=隐藏),密钥从 env 读入闭包、从不 log/trace/commit,fake 模式无需 key。没有 active leak;主要风险是两套并行 visibility 实现(`observer_protocol.py` vs `observer_visibility.py`)漂移 —— 当前是"少分享"(安全方向),但正是未来一改就翻车的那一类。
- **engine 正确性硬伤:** 女巫结构性永远无法合法救人(被杀者身份是 `werewolf_team` 可见,从不进女巫 prompt,但救人要求 `target==victim`)—— 每局 emergent 游戏被静默推向狼人胜。
- **整体判断:** 安全/密钥地基稳;**eval-readiness 与 contract-drift 是当前最大债务**,且因测试盲区而无信号。在 witch 词汇 bug 修复并接入端到端测试前,settlement bundle 不应被当作"评测就绪"。

---

## 风险登记册 (Risk Register)

| ID | 严重度 | 维度 | 标题 | 关键位置 (file:line) | 一句影响 |
|----|--------|------|------|----------------------|----------|
| R-01 | **blocker** | contract-drift | witch 毒药 emit `witch_kill` / consume `witch_poison`(规范根因,全链路) | `emergent_engine.py:43,625` vs `scoring.py:120,674,765` | 每局毒药动作得 0 分,错误数字烘进 P3 入口 artifact |
| R-02 | **blocker** | test-gaps | 无任何测试横跨 engine->scoring/render 接缝 | `tests/test_scoring.py:29`, `tests/test_emergent_engine.py:13` | 确证 bug 对 602 测试全绿不可见 |
| R-03 | high | contract-drift | 毒药 decision.action 也是 `witch_kill`,decision 匹配也断 | `emergent_engine.py:624` vs `scoring.py:176,222` | 只改 event type 不改 decision/whitelist 仍漏 |
| R-04 | high | engine-correctness | 女巫永远无法合法救人(victim 身份不可见,救人要 `target==victim`) | `emergent_engine.py:605,469,228,560` | 救人潜能死,系统性偏向狼人胜 |
| R-05 | high | engine-correctness | 事件词汇 mismatch(engine 视角)→ 毒药未计分、排除出死亡集 | `emergent_engine.py:43,625` vs `scoring.py:120,674,765` | 与 R-01 同根,确认 emit 侧 |
| R-06 | high | visibility-security | 两套 visibility 实现挂不同 endpoint,对 `role:pN` 私有事件判定不一致 | `observer_protocol.py:485` vs `observer_visibility.py:481`; `observer_server.py:343,672,381` | 同座位不同 endpoint 看到不同事件;一改翻成 leak |
| R-07 | high | eval-readiness | 毒药未计分且**不 degrade**(degraded=false + 错误分数) | `emergent_engine.py:625`, `scoring.py:119,674`, `settlement_bundle.py:154` | 静默 eval 污染,排行榜错而无标志 |
| R-08 | high | eval-readiness | cache 无 `bundle_version` 校验,非原子写 | `settlement_bundle.py:233,254,26` | P3 v2 后永久供旧 schema;截断文件致 crash |
| R-09 | high | eval-readiness | 无 per-seat model/source label,无 token usage | `settlement_bundle.py:87`, `emergent_engine.py:366`, `observer_server.py:410` | 异质 AI 对战缺公平/成本维度,P3 需 schema 迁移 |
| R-10 | high | test-gaps | settlement_bundle 测试绕过 witch mismatch(monkeypatch 而非真实喂入) | `tests/test_settlement_bundle.py:38`, `settlement_bundle.py:150` | 团队已知 scorer 误处理却测"周围",保证 P3 返工 |
| R-11 | high | test-gaps | observer-server 安全/非泄漏 HTTP 测试绑真实 socket,本环境 47/95 ERROR | `tests/test_observer_server.py:50,761,375,411` | HTTP 边界 leak/traversal/secret 防线实际未验证 |
| R-12 | high | integration-debt | render_demo / render_provider_replay 重复 label 字典,**两处都硬编码错误 witch 词汇** | `render_demo.py:39`, `render_provider_replay.py:32` | 修一个 renderer 不传播到另一个 |
| R-13 | high | integration-debt | `fix/p2-a-witch-poison-vocab` 分支 0 commit(tip==main) | `.git/refs/heads/fix/p2-a-witch-poison-vocab` | 指派的修复未开始,bug 处处活着 |
| R-14 | high | doc-drift | PROJECT_MAP 标 P2-A-1"完成"+ settlement"评测就绪",与代码矛盾 | `docs/PROJECT_MAP.md:58,52` vs `emergent_engine.py:625`,`scoring.py:674`,`settlement_bundle.py:151` | 新人继承静默计分洞,即 doc 声称要防的返工 |
| R-15 | high | doc-drift | 真实测试失败:AGENTS.md 删了 test 守护的 "Context Budget Gate" 段 | `tests/test_context_budget.py:232`, `AGENTS.md:1` | 套件非绿(非环境因素),侵蚀"测试通过"信号 |
| R-16 | medium | contract-drift | scoring/consensus 分支 `specific_player_ids`,emergent 从不发(死分支) | `scoring.py:194,208`, `consensus_log.py:501` vs `emergent_engine.py:745` | gold-replay 与 emergent 评分行为分叉,P3 混跑会惊 |
| R-17 | medium | visibility-security | 可见性正确性全靠 engine 传对 per-event `visibility`,无 engine 侧不变量强制 | `game_engine.py:506`, `emergent_engine.py:237`, `runtime_events.py:53` | 复制粘贴错 visibility 即泄漏,fail-closed 也救不了 |
| R-18 | medium | visibility-security | 狼 role-projection 快照把全部 event id 拷进 private_event_ids | `game_engine.py:561,660`, `runtime_events.py:504` | g1b 模式下狼获 seer/witch 事件元数据;默认 consensus 不走此分支 |
| R-19 | medium | visibility-security | 密钥脱敏过宽,会破坏合法游戏文本(secret/token/auth 子串) | `runtime_events.py:65,107,129` | 含这些英文词的发言被 `<REDACTED>` 或致 spine crash |
| R-20 | medium | eval-readiness | `decision_quality_score` 恒为 0 且无 not-computed 标志 | `settlement_bundle.py:166`, `scoring.py:385` | P3 排序误判所有 agent 决策质量相等 |
| R-21 | medium | eval-readiness | per-decision ScoreRecord 算出后丢弃 | `settlement_bundle.py:162`, `scoring.py:11` | P3 per-decision 复盘/rubric 审计需 schema 迁移 |
| R-22 | medium | test-gaps | attribution 规则评估 notes 硬编码 gold game,非按事件计算 | `attribution.py:196`, `tests/test_attribution.py:22` | 仅对 g001 验证,F.3 witch_misfire 永不反映真实局 |
| R-23 | medium | integration-debt | 五个已全合并 feature 分支残留为陈旧指针 | `feat/g2d-2-qt-setup-ui` 等 5 个 ref | 无丢失风险,纯认知/操作混淆 |
| R-24 | medium | integration-debt | `.runs/`(含 prompt-manifest/provider-trace)未 gitignore | `.runs/`, `.runs/default_6p_fake_05aaf702/prompt-manifest.json` | `git add .` 可能提交 live 密钥类 artifact(今为 fake,无泄漏) |
| R-25 | medium | doc-drift | README "当前状态" 落后多个模块(称下一候选 G2d) | `README.md:27,31` vs `PROJECT_MAP.md:49` | 给新人错误项目坐标 |
| R-26 | medium | doc-drift | AGENTS.md 路由头 "Current route: G1h" 落后约 8 个模块 | `AGENTS.md:10,11` vs `ROADMAP.md:49` | 根路由文件把 P2 活跃前沿划为 out-of-scope |
| R-27 | medium | doc-drift | P2-D plan/spec 称"词汇 mismatch → degraded"为假,degrade 仅 monkeypatch 测过 | `...p2-d-settlement-screen-plan.md:130,651`, `tests/test_settlement_bundle.py:37,101` | 把虚假信心烘进声明的 P3 入口规范 |
| R-28 | low | contract-drift | engine 发 `day_announcement`/`player_speech`/`game_over` 无 scorer 消费(render-only) | `emergent_engine.py:777,679,803` vs `render_demo.py:35` | `day_announcement` 在中文 UI 渲染成原始英文 token |
| R-29 | low | engine-correctness | 确定性 fallback 目标恒为首个存活座位 → 系统性替罪同一玩家 | `emergent_engine.py:444,541,698` | 高失败 live 局污染投票准确率/存活指标 |
| R-30 | low | engine-correctness | 单 seer/单 witch 假设,多余特殊座位静默失活 | `emergent_engine.py:527,557` | P3 板型变体下额外特殊角色不行动(latent) |
| R-31 | low | eval-readiness | degrade 路径安全确定、可从 artifact 复现(正面项) | `settlement_bundle.py:154,40` | 失败收敛为脱敏码、curtain 完好;残留风险即 R-08 |
| R-32 | low | test-gaps | artifact 测试用 skipTest 当虚假绿色守卫 | `tests/test_fake_provider_game.py:150` | artifact 停产时 skip 而非 fail,隐藏回归 |
| R-33 | low | test-gaps | 一个真实(非 socket)套件失败:context-budget 文档漂移断言 | `tests/test_context_budget.py` | 套件即便忽略网络也非绿(与 R-15 同) |
| R-34 | low | integration-debt | `.logs/` 与 `.grill/` 部分被跟踪,`.logs/review/` 已 ignore — 先跟踪后忽略冲突 | `.logs/review/latest/review-packet.md`, `.grill/...`, `.gitignore:21` | 生成日志/草稿混入 VCS,无功能影响 |
| R-35 | low | integration-debt | scripted/mock 启动器 + `attribute_game.py` CLI 仅测试可达 | `scripted_game.py`, `run_scripted_game.py`, `run_mock_game.py`, `attribute_game.py:16` | 维护成本 + 哪个 runner 是规范不清 |
| R-36 | low | integration-debt | 八个重叠 `run_*_game` 启动器无共享脚手架 | `run_emergent_game.py` 等 8 个 | argparse/日志/fail-closed 复制,可静默分叉 |
| R-37 | low | doc-drift | TASKS.md/ROADMAP.md 正文仍称下一候选为 "G4 evaluation platform"(顶部已有 superseded banner) | `docs/TASKS.md:86`, `docs/ROADMAP.md:278` vs `TASKS.md:3` | 跳过 banner 的读者得到矛盾陈旧下一步 |
| R-38 | low | test-gaps | 无 CI workflow,但 docs 把"测试通过"当验收门槛;套件 in-repo 非绿 | `.github`(无 workflows/), `PROJECT_MAP.md:58`, `AGENTS.md:78` | "全测试绿"是默认未验证声明 |

---

## 分维度详情

### 维度小结一览

- **contract-drift:** engine 层与 scoring/eval 层在 witch-poison 词汇上分歧,是整个确证 bug 类的唯一根因。规范权威是 gold game + rubric(`docs/EVALUATION_RUBRIC.md:222`,`g001-decision-log.json:124`),命名为 `witch_poison`/visibility=`witch`。两个 engine 及离线默认脚本都用 `witch_kill`。其它字段名(actor/target/type/phase/round/visibility)跨层一致,未漂移。
- **engine-correctness:** 夜/日循环在 happy path 上基本健全(确定性 seeded tie-break、双死去重、预算/轮上限 fail-closed),但带几个可达正确性 bug,最严重的是女巫救人死锁。
- **visibility-security:** hard-gate 与密钥处理整体工程扎实、fail-closed。witch 词汇 mismatch 是**计分 bug 非泄漏**(两个 witch 事件都带 visibility=`witch`)。主要问题是 contract-drift:两套 visibility 实现。
- **eval-readiness:** settlement bundle 的 degrade 路径安全确定,但词汇 bug 不触发 degrade,且缺 per-seat model/token、per-decision record、decision_quality not-computed 标志,cache 无版本校验。
- **test-gaps:** 关键接缝无测试;安全 HTTP 测试绑 socket;attribution 过拟合 gold;存在虚假绿色 skip。
- **integration-debt:** 分支多为陈旧但低风险;真正危险的是空的 fix 分支;render label 重复且都编码错词汇;artifact 目录未 ignore。
- **doc-drift:** 三份追踪文档经 superseded banner 调和,但多处 DONE/eval-ready 声明被代码反证;README/AGENTS.md 路由严重陈旧;存在一个真实失败的 doc-test。

---

### contract-drift

**R-01 [blocker, confirmed] witch 毒药 emit `witch_kill` / consume `witch_poison`(规范根因)**
- 证据:`emergent_engine.py:43` `WITCH_KILL = "witch_kill"` → emit 于 `:625`;`provider_agent.py:21` `("witch","night"): ["witch_save","witch_kill"]`;vs `scoring.py:120` 集合仅含 `"witch_poison"`、`:674` `elif event.type == "witch_poison":`。两字符串永不相等。规范权威 `g001-game-log.json`(g001_e025 type=`witch_poison`,见 `EVALUATION_RUBRIC.md:222`)。`game_log.py:134-135` 的 `_validate_event` 不白名单 event type,`witch_kill` 原样通过 —— 无规范化屏障。`run_emergent_game.py:42` 默认 `--script='villager_win'` 使被毒路径成为发布的确定性默认。
- 影响:每个毒药动作静默不计分(无 ScoreRecord、`poison_accuracy=0`、ability_utilization 低估、F.3 witch_misfire 失明),per-player outcome/decision 分数漏掉毒药,错误数字烘进 P3 将回放的 settlement artifact。默认离线 villager-win 脚本正是经此毒药结束游戏,故 bug 在确定性默认路径上就触发。
- **修复建议:** 选 `witch_poison` 为唯一规范 token(它是 gold/rubric 契约),在 emit 侧重命名:`emergent_engine.py:43`、`provider_agent.py:21` 白名单、`emergent_fake_script.py:60` + 测试。新增共享 `EVENT_TYPES/ACTIONS` 模块级 enum 由 engine 与 scoring 共同 import,加一个 round-trip 测试断言每个 `SCORE_RELEVANT_EVENT_TYPES` 成员都可被 engine 产生。
- 置信度:high / confirmed(emit 码 + consume 码 + gold 契约三处实读)。

**R-03 [high, confirmed] 毒药 decision.action 也是 `witch_kill`,decision 匹配也断**
- 证据:engine 同时写 event(type `witch_kill`,`:625`)与 decision(action `witch_kill`,`:624`);`scoring.py:176` `SCORE_RELEVANT_DECISION_ACTIONS = SCORE_RELEVANT_EVENT_TYPES`(仅 witch_poison),`:222` `_decision_matches_event` 要求 `decision.action == event.type`。完全合法的 live 毒药产出自洽的 `witch_kill` decision+event 对,被两个轴都丢弃。
- 影响:确认漂移不只是 emit/consume gap,而是横跨 engine event + engine decision + action whitelist 的完整错误词汇。只改 event type 而不改 decision action 或白名单仍会留下 decision 链接破裂。
- **修复建议:** 对 decision action(`:624`)与 `WITCH_ACTIONS`/`WITCH_KILL` 常量施加同一规范重命名,或在一处解耦用户面动作名与发出的契约 token,确保 `decision.action` 与 `event.type` 都变 `witch_poison`。
- 置信度:high / confirmed。

**R-16 [medium, likely] scoring/consensus 分支 `specific_player_ids` 而 emergent 从不发(死分支)**
- 证据:消费方处理 `specific_player_ids`(`scoring.py:194/208`,`consensus_log.py:501`),gold log 在 role_assignment 用它(`g001-game-log.json:26`),但 `emergent_engine.py:745` 把 role_assignment 发为 `"public"`,`game_engine.py:603` 同样发 `"public"`。无 engine 路径产生 `specific_player_ids`。
- 影响:两者都是 `VALID_VISIBILITIES` 且 gold 路径仍工作,故严重度低;但 gold-replay 评分与 emergent-run 评分在 decision-visibility 检查上行为分叉,该分支对任何 engine 产出 log 是死代码,P3 混跑 gold+emergent 时会惊到。
- **修复建议:** 决定 role_assignment 规范 visibility(gold 用 specific_player_ids),让两个 engine 都发它;或文档化 emergent 用 public 并 guard/移除不可达分支。至少加注释说明两 engine 对同一 event type 发不同 visibility。
- 置信度:high / likely。

**R-28 [low, confirmed] engine 发 `day_announcement`/`player_speech`/`game_over` 无 scorer 消费(render-only)**
- 证据:`emergent_engine.py:777` 发 `"day_announcement"`;`render_demo.py:35-47` 与 `render_provider_replay.py:28-40` 的 TYPE_LABELS 无 `day_announcement` key,`_type_label` 在中文默认 UI 落到原始英文 token。scoring 不消费这些(正确,叙事性)。反证:Qt UI 确实本地化了 day_announcement(`EvidenceConsole.qml:46`、`SpeechTheater.qml:34`)。
- 影响:对计分无害(刻意不裁定);但 `day_announcement` 在否则全中文的 render/replay HTML 里显示为原始英文串,小的 render-词汇 gap。
- **修复建议:** 在 `render_demo.py:35` 和 `render_provider_replay.py:28` 的 TYPE_LABELS 加 `"day_announcement": "夜晚公告"`。可选加测试断言每个 engine-emitted event type 都有 TYPE_LABELS 条目。
- 置信度:high / confirmed。

---

### engine-correctness

**R-04 [high, confirmed] 女巫永远无法合法救人**
- 证据:`:605` `if save_used or victim is None or target != victim:` 拒绝;`:469` 狼刀 emit 为 `"werewolf_team"`;`:228/:233` `_private_refs` 对 role="witch" 只匹配 `v=="all"` 或 `v=="witch"`,从不 werewolf_team。`:570` `allowed_targets=sorted(self._alive)` 给女巫每个存活座位,无窄化信号。`:768` player_died(visibility="all")在 `_resolve_witch` 之后才发,太晚。live provider prompt 仅由 `request.observation_text` 构建(`deepseek_provider.py:66-67`),省略 victim。fake 脚本硬编码 wolf kill=p5 且 witch_save=p5(`emergent_fake_script.py:35-38`),掩盖此 bug。
- 影响:live(DeepSeek)女巫结构上无法得知今晚谁被攻击,但 engine 拒绝任何 `target!=victim` 的救人。结果:每次真实救人尝试被记为 invalid_action 降级为 PASS,救药事实死掉,witch_save 计分(+1/+3)几乎不触发,该救的关键村民(预言家)死亡 —— 静默偏向狼人胜并污染 eval 信号。
- **修复建议:** 女巫调用前把 victim 渲染进其 observation:为该轮发/注入一个 witch 可见的"今晚受害者是 X"info 事件(visibility="witch"),或把 victim 显式传入 `render_observation_text`/ProviderRequest 的 observation_text 与 allowed_targets。保留 `target==victim` 守卫但确保女巫确被告知 victim。加测试:live-style 女巫返回正确 victim 的 witch_save,断言 saved==True。
- 置信度:high / confirmed。

**R-05 [high, confirmed] 事件词汇 mismatch(engine 视角)**
- 证据:与 R-01 同根。`emergent_engine.py:43` vs `scoring.py:120,674,765`。注意:毒药死亡确实施加到 `self._alive`(`:764`)且发 player_died,故游戏 outcome 正确,但毒药"为何/是否好"的计分归因丢失。
- 影响:`_score_witch_poison` 对 emergent 游戏从不被调用,poison-werewolf(+3)/poison-key-villager(-3)/poison-villager(-1)全计 0。这是被命名的 KNOWN BUG CLASS 在 engine emit 侧的确证。
- **修复建议:** 同 R-01,选一个规范 token;加共享 EVENT_TYPES 常量模块 + 测试断言每个 emitted event.type 对裁定类型都在 `scoring.SCORE_RELEVANT_EVENT_TYPES` 中。
- 置信度:high / confirmed。

**R-29 [low, confirmed] 确定性 fallback 目标恒为首个存活座位**
- 证据:`:447` `target = candidates[0]`、`:544` `target = cands[0]`、`:701` `target = cands[0]` 全 index 0,而 `:463/:715` tie-break 用 `self._rng.randrange(len(leaders))`。fallback 投票作为正常 player_vote 事件喂入指标(`:707`),`_vote_accuracy_by_player`(`scoring.py:719`)无 decision_type 排除。
- 影响:provider 失败/超时/非法时所有 fallback 确定性瞄准最低座位序存活玩家,一轮多座位失败时集中替罪单一低座玩家,产生与游戏逻辑无关的人为淘汰偏置;高失败 live 局主导结果并污染投票准确率/存活指标。
- **修复建议:** fallback 目标选择改用 seeded RNG(`self._rng.choice(cands)`)以匹配 tie-break 确定性风格,或分散 fallback;至少文档化"偏向座位 0 是 intended"。经 seed 保持确定性。
- 置信度:medium / confirmed。

**R-30 [low, likely] 单 seer/单 witch 假设**
- 证据:`:527` `seer = seers[0]`、`:557` `witch = witches[0]`,len>1 无处理。`GameConfig` 无角色数校验/无 `__post_init__`(`game_engine.py:36`),`EmergentGameEngine.__init__`(`:184`)无角色多重性不变量检查。
- 影响:若未来 P3 板型含 >1 seer/witch,仅座位序首者行动,其余永不行动/不计预算/不入日志,静默偏离 god-view。今默认板各一,latent,但 engine 自称 emergent/dynamic 且 PROJECT_MAP 要求 eval-ready,值得标。
- **修复建议:** 遍历所有 seer/witch,或在构造时断言各恰一个,使错配板型响亮失败而非静默丢角色。鉴于单特殊设计意图,优先显式不变量检查。
- 置信度:low / likely。

---

### visibility-security

**R-06 [high, confirmed] 两套 visibility 实现挂不同 endpoint,判定不一致**
- 证据:`observer_protocol.py:486` `if perspective.startswith("role:p"): return visibility in PUBLIC_EVENT_VISIBILITIES`(role:pN 仅 public/all)vs `observer_visibility.py:488-503`(trusted 时额外返回 seer/witch/werewolf_team)。`/events`(`observer_server.py:343`)、`/stream` SSE(`:672`)用 protocol 过滤;`/projection`(`:381`)用 visibility envelope。第三个重复 frozenset(`observer_protocol.py:67` vs `observer_visibility.py:22`)与第四个 endpoint 对(`/snapshots`)扩大漂移面。两套测试各自固化分歧(`test_observer_protocol.py:197-205` vs `test_observer_visibility.py:419-451`),无跨模块 parity 测试。
- 影响:同座位因 endpoint 不同看到不同 event 集。protocol 路径当前 under-share(安全方向,非 active leak,seer 连自己 check 结果都看不到),但两个必须一致的安全关键过滤器正是 witch 词汇 bug 体现的漂移模式:未来给 protocol 加 role-private 可见性(为修 under-share)或只给一个 frozenset 加新 token,可在 SSE/events(最高流量 live 面)静默开 leak。
- **修复建议:** 收敛到唯一 visibility 权威。让 `/events`、`/stream`、`/snapshots` 都走 `/projection` 用的 `event_visible_in_projection`/`project_events`(传 seat_index),删 protocol 里重复 frozenset 与 `event_visible_to_perspective`(或改薄 re-export)。加跨模块测试:对每个 (perspective, visibility) 对两函数返回一致决定,任何未来分歧即 CI 失败。
- 置信度:high / confirmed。

**R-17 [medium, confirmed] 可见性正确性全靠 engine 传对 visibility,无 engine 侧不变量**
- 证据:`game_engine.py:506` `def _emit(phase, rnd, etype, actor, target, visibility, summary, refs=None)` —— visibility 是任意参数,与 etype 无绑定;`:695` seer 传字面 `"seer"`、`:658` werewolf_kill 传字面 `"werewolf_team"`,全靠 caller 纪律。`RUNTIME_EVENT_VISIBILITIES`(`runtime_events.py:53`)只允许集合,不绑 type→visibility。
- 影响:整个防泄漏模型靠每个 `_emit` 传对 visibility 串。无任何映射/断言要求某 event type 必须带某 visibility。新增私有 event type 时复制粘贴 `"public"`/`"all"`(产生 witch_kill 的同种人为错)会把它泄漏给所有视角,且 filter 层 fail-closed 默认抓不住(engine 已显式设 public)。这是可见性版的事件词汇类。
- **修复建议:** 引入唯一规范 `EVENT_TYPE_VISIBILITY` 映射(type→required visibility)由两 engine 共享,`_emit` 据 type 派生或断言 visibility,加 validator(扩展 `validate_runtime_event`/game-log validator)拒绝任何私有类 event type 带 public/all visibility,把静默泄漏变硬失败。
- 置信度:medium / confirmed。

**R-18 [medium, confirmed] 狼 role-projection 快照拷全部 event id 进 private_event_ids**
- 证据:`game_engine.py:561` `private_event_ids=[e["event_id"] for e in events]`(_wolf_obs 内)对比 `:578` _player_obs 用 `_private_refs(player_id)`(visibility 过滤)。真正泄漏的是 `:784` obs_wolf_n2(Night 2 构建,此时 Night-1 seer(`:695` visibility "seer")/witch(`:714` visibility "witch")已在 events 列表)。该快照经 `load_snapshot_detail`(`observer_protocol.py:254-273`)原样发给 team:werewolf,gate 是二元 visibility-only 无字段级过滤。`_resolve_wolf_consensus`(`game_engine.py:312-322`)用正确过滤构建 —— 证明作者知道正确规则,是 fix 应镜像的参考实现。
- 影响:g1b/mock 模式(非 consensus else 分支)狼的 snapshot 嵌入全部 event id 含 seer/witch。泄漏的是 event id/计数(元数据),非 summary(summary 在 game-log 另行 gate),故是元数据泄漏(狼得知发生了多少私有 seer/witch 动作及其 id)。默认 observer-server 走 g1f_provider_consensus(`run_g1h_fake_runtime.py:131`),不走此分支,生产当前不受影响 —— 但泄漏快照随代码出货,任何切到 mock 模式即暴露。
- **修复建议:** 用与普通玩家相同的 `_private_refs`/visibility 规则(all + werewolf_team)构建狼 observation 的 private_event_ids,而非 `[e['event_id'] for e in events]`。加测试:狼 role_projection 快照的 private_event_ids 不含任何源事件 visibility 为 seer/witch 的 id。
- 置信度:medium / confirmed。

**R-19 [medium, confirmed] 密钥脱敏过宽,破坏合法游戏文本**
- 证据:`runtime_events.py:65-74` `SECRET_KEY_FRAGMENTS = ("sk-","Bearer ","api-key","api_key","apikey","secret","token","auth")` 被 `redact_secret_values`(`:107` 静默销毁)与 `assert_no_secret_patterns`(`:129` 抛错)用于任意字符串值,非仅 key 名。`profile_config.py:63-76` 刻意收窄 value markers 以避免此问题,runtime_events.py 没有 —— 内部不一致。
- 影响:任何含子串 `secret`/`token`/`auth`(大小写不敏感)的 snapshot/manifest/runtime-event 值被静默替为 `<REDACTED>`,在 payload/refs 内则使 `validate_runtime_event` 抛 RuntimeEventError 中止写入。狼人杀发言如"keep your role secret"、名含"auth"的玩家、提到"token"的理由会被销毁或 crash event spine。数据完整性/eval-readiness 风险(P2-D bundle 消费这些 artifact),非泄漏。
- **修复建议:** 把 runtime_events 的 value 检查对齐 profile_config 更窄的 `_VALUE_SECRET_MARKERS`(sk-、`bearer `、api_key/api-key/apikey、authorization、access_key);宽列表仅用于 key 名检查。在高置信凭证形状上 redact/raise,而非裸英文词。
- 置信度:high / confirmed。

---

### eval-readiness

**R-07 [high, confirmed] 毒药未计分且不 degrade**
- 证据:`emergent_engine.py:625` 发 witch_kill;`scoring.py:119` `SCORE_RELEVANT_EVENT_TYPES` 有 witch_poison 无 witch_kill;`:663` `score_game` 对未知 type `continue` 而不 raise(故不 degrade);`settlement_bundle.py:154-157` 仅异常 degrade,静默跳过的 scorable-family 事件不 degrade。毒药受害者作为 player_died 发出(`:768`)→ 进 board_timeline,使 degraded=false 的 bundle 看起来完整。gold log 用 witch_poison(`g001-game-log.json:376`)解释为何现有计分测试通过并掩盖此分歧。
- 影响:bundle 是 degraded=false 带完整战报,但下毒者无 credit/penalty、poison_accuracy=0;死亡仍在 board_timeline 故看似完整。P3 摄入错误 gold 分数,排行榜错而无标志。settlement 层使计分 bug 成为静默 eval 污染。
- **修复建议:** 在 P2-A 修 engine(发 witch_poison 或别名 + score_game 加路由)。纵深防御:builder 把"scorable-family 事件无 ScoreRecord"标为 degraded code `unscored_action_types`。
- 置信度:high / confirmed。

**R-08 [high, confirmed] cache 无 bundle_version 校验,非原子写**
- 证据:`settlement_bundle.py:233` cache 无条件返回;`:254` 非原子写;`:26` `BUNDLE_VERSION` 命中时从不校验(`:74` 是唯一写点,从不读回);`:236` 未 guard 的 `json.loads`。`observer_server.py:736` ThreadingHTTPServer → 并发首次写可损坏非原子 cache;`:451` catch-all except→500 把截断读 crash 收敛为 HTTP 500。design "Open risks"(`...design.md:447`)已明示 bundle_version 校验/重算未实现。
- 影响:settlement-bundle.json 原样返回,从不比对 cached 与 BUNDLE_VERSION。P3 v2 后已开 run 永久供 v1,P3 读混合 schema 无信号,无报错。非原子写使 crash 留下截断文件让未 guard 的读 crash。
- **修复建议:** 命中时在 try/except 内解析,读 bundle_version,不同/缺失/不可解析则重算+覆盖。原子写(temp + rename)。
- 置信度:high / confirmed。

**R-09 [high, confirmed] 无 per-seat model/source label,无 token usage**
- 证据:`settlement_bundle.py:87` players[] 缺 model/source_label/token;`emergent_engine.py:366` model+token_usage 仅在 provider-turns.json;`observer_server.py:410` builder 从不读 provider-turns.json。数据存在:`run_emergent_deepseek_game.py:62-78` 保留 per-turn actor/model/token_usage;`:108-114` prompt-manifest 带 per-agent model。`GameLog.Player`(`game_log.py:23-26`)只有 player_id/role/team,source_label 是 game-wide 单字段。设计 v1 players[] 契约冻结 + additive-only P3 深化规则(`...design.md:159,178-182,213,333`)是降级依据。
- 影响:仅 game-wide `result.source_label`,无 per-seat、无 token。异质 AI-vs-AI eval 需 per-seat model + cost。数据在 provider-turns.json 但 builder 从不加载,故 P3 model-fairness/cost/which-model-decided 复盘需 schema 迁移 + 新 builder I/O。趁 v1 未冻结现在加。
- **修复建议:** 加 `players[].model` + per-seat token rollup(或 provider_summary),按 actor 聚合 provider_turns。Secret-free。fake 模式从 source_label 取,zero tokens,key 永存在。
- 置信度:high / confirmed。

**R-20 [medium, confirmed] decision_quality_score 恒为 0 且无 not-computed 标志**
- 证据:`settlement_bundle.py:166` 从 aggregate 拷贝,live/emergent 恒 0;`scoring.py:385` D2 无 S5 labels 不赋 >0;真实 decision-log 命中 `:330-347` 的 no-visible_info_refs 分支,把 live decision_quality 钉在 0。`summarize_metrics`(`:850-886`)不传播 `score_log.scoring_boundary`,故 not-computed 原因(`:407-414` 已有"positive decision_quality_score waits for S5")永不到 bundle。
- 影响:因 score_game 无 semantic_label_log 调用,S5 从不触发。无标志区分 not-computed 与 neutral,P3 排序断定所有 agent 决策质量相等。
- **修复建议:** 把 `score_log.scoring_boundary`(或 `decision_quality_computed=False` + reason)拷进 bundle。Additive,既有 key 冻结。
- 置信度:high / confirmed。

**R-21 [medium, likely] per-decision ScoreRecord 算出后丢弃**
- 证据:`settlement_bundle.py:162` 仅拷 aggregate,`ScoreLog.records` 丢弃;`scoring.py:11` ScoreRecord 含 decision_id/action_type/score/rules/evidence。
- 影响:bundle 仅留 per-player 和 + turning_points。per-decision ScoreRecord(action_type/per-action score/rubric id/evidence id/decision_id)算后扔。P3 per-decision 复盘/rubric 审计/decision-to-event 追溯需要它们;后加 = schema 迁移。已算出。
- **修复建议:** 从 `score_log.records` 持久化一个 `score_records` 数组,gate 在 battle-report degrade 之后。
- 置信度:high / likely。

**R-31 [low, confirmed] degrade 路径安全确定、可复现(正面项)**
- 证据:`settlement_bundle.py:154` except→scoring_failed code,从不原始文本/路径/stack;`:40` board_timeline 仅从 game-log,从不 raise。无 wall-clock/uuid/random;按 sequence 排序;仅 seeded engine RNG 冻进上游 game-log。
- 影响:失败收敛为脱敏码,curtain 完好,无泄漏,board_timeline 仍可推导。可复现。残留:非原子/无版本/未 guard 的 cache(=R-08)是唯一通往 P3 的畸形 bundle 路径。
- **修复建议:** degrade 逻辑不改;经 R-08 修健壮性。可选加 byte-identical 确定性自测。
- 置信度:high / confirmed。

---

### test-gaps

**R-02 [blocker, confirmed] 无任何测试横跨 engine->scoring/render 接缝**
- 证据:engine `self._emit("night", rnd, WITCH_KILL, ...)`(`:625`);scoring `elif event.type == "witch_poison":`(`:674`)。`tests/test_scoring.py:29` 仅 load `g001-game-log.json`(用 witch_poison);`tests/test_emergent_engine.py:13` 从不 import score_game;`tests/test_render_demo.py:21` 仅用 gold/generated fixture。`test_p2a2_live_path.py:220` 跑 EmergentGameEngine(含 witch_kill 毒药脚本)却只断言 provider-turn 分类,从不喂 score_game/attribute_game。
- 影响:确证的事件词汇 mismatch 类的唯一实例对整个 602 测试套件不可见。engine 套件验 engine 发 witch_kill;scoring/attribution/render/settlement 套件在 witch_poison fixture 上验行为。两者永不相遇,真实 engine 局每个毒药动作被丢且套件全绿。因 settlement_bundle 是 P3 入口,错误战报数据无信号地传入 eval。
- **修复建议:** 加端到端 golden 测试:跑 EmergentGameEngine 含 witch 毒药脚本(`emergent_fake_script.py:60` 已有),把 outcome.game_log 直接喂 score_game + attribute_game + build_settlement_bundle,断言毒药产生 ScoreRecord 与非零 per-player 影响。再加词汇契约测试:engine 可发 event-type 常量集合 ⊆ scoring/render/settlement 消费的 event types(一个 shared-registry 测试抓整类)。
- 置信度:high / confirmed。

**R-10 [high, confirmed] settlement_bundle 测试绕过 witch mismatch**
- 证据:`tests/test_settlement_bundle.py:38` 注释 "the scorer is lenient and does not naturally raise on the witch-vocabulary mismatch" → 用 monkeypatch 强制 scoring error;`settlement_bundle.py:150` battle-report 仅异常 degrade,静默误计不是异常 → degraded=False + 错误数字。
- 影响:建 P3 入口的团队已知 scorer 误处理 witch 词汇却测"周围"(mock.patch side_effect 假 raise)而非断言正确计分。真实 engine 局以 degraded=False 结算并静默错 outcome_score/mvp_player_id/turning_points。项目规则要求 settlement 评测就绪以免 P3 返工 —— 这保证返工。
- **修复建议:** 加 settlement 测试:从含 witch 毒药的真实 engine 输出建 bundle,断言被毒玩家死亡与女巫动作反映在 core_metrics/turning_points(非仅 curtain 存活)。把"每个裁定动作都产生计分记录"当作 settlement 不变量。
- 置信度:high / confirmed。

**R-11 [high, confirmed] observer-server 安全 HTTP 测试绑 socket,47/95 ERROR**
- 证据:`tests/test_observer_server.py:50` `_start_server` 绑 127.0.0.1 + serve_forever,每个 endpoint 测试用 urlopen;`:761` 非泄漏测试、`:375` 路径遍历、`:411` secret-scan 全 socket-only;运行得 `http.client.RemoteDisconnected`,`Ran 95 tests ... FAILED (errors=47)`。已有 no-socket harness(`:1239 _InProcessHandler`)只覆盖 POST live-gate,不覆盖 GET projection/artifact/traversal/secret。底层 visibility 逻辑离线覆盖好(58 passing),但 route→projection→response 边界未验。
- 影响:本环境实测 47/95 ERROR(文档化的 localhost 屏蔽)。errored 集含安全非泄漏 projection 测试、路径遍历、endpoint secret-scan。任何 localhost 屏蔽/不稳的 CI/host 上这些 ERROR(或 auto-skip 假绿),故 HTTP 边界 leak/traversal/secret 防线实际未验。
- **修复建议:** 把 socket-only 安全测试重构到同文件已有的 in-process handler harness(无 socket dispatch,~`:1240-1682`),使 leak/traversal/secret-scan 断言无 socket 运行。保留 1-2 个真实 socket 冒烟测试用 `skipUnless(localhost reachable)`,网络屏蔽时显式 skip 而非 ERROR。
- 置信度:high / confirmed。

**R-22 [medium, confirmed] attribution 规则评估 notes 硬编码 gold game**
- 证据:`attribution.py:196` F.3.witch_misfire 无条件返回静态 notes(`"p4 saves villager p5 and poisons werewolf p2. No witch misfire ..."`),`:191/:201/:206` F.2/F.4/F.5 同样硬编码;`tests/test_attribution.py:22` 唯一 fixture 是 g001,对 `s3-rule-attribution.json` 检 byte-equality(`:43` 只检 key 不检 value)。`attribute_game.py:17-26` CLI 对任意 game path 跑 → 对任何非 g001 局发静态 F.2-F.5 notes;`docs/generated-games/` 有 5 个非 g001 log 无 attribution 输出与测试。
- 影响:`rule_evaluation_summary` 返回绑 g001 板的固定散文,唯一测试断 byte-equality。故 attribution 仅对它硬编码复现的那一局被验证。F.3 witch_misfire 尤其永不反映真实 engine 局(其本身又带 witch_kill 词汇问题),无测试会注意。这是 gold-game-only 覆盖 gap 的过拟合实例。
- **修复建议:** 在至少一个非 g001 局(engine 产出或 generated-games log)加 attribution 测试,断言 F-rules 从真实事件 trigger/not-trigger,且女巫毒村民时 witch_misfire 可被评估。
- 置信度:high / confirmed。

**R-32 [low, confirmed] artifact 测试用 skipTest 当虚假绿色守卫**
- 证据:`tests/test_fake_provider_game.py:150` `if not html_path.exists(): self.skipTest("demo HTML not yet generated")`(3 个测试,另 `:165/:175`)。
- 影响:FakeProviderGameArtifactTests 在生成的 demo HTML/game-log/decision-log 缺失时静默 skip(计为 pass)。若回归停产这些 artifact,测试 skip 而非 fail,隐藏破坏。当前 artifact 存在故运行,但模式是 latent 虚假绿。
- **修复建议:** 让测试自己拥有生成步骤(生成到 tmp dir 再断言),使缺失成真实失败;或移到 artifact 缺失即失败的 generation-required target。
- 置信度:medium / confirmed。

**R-33 [low, confirmed] 一个真实(非 socket)套件失败:context-budget 文档漂移断言**
- 证据:`test_agents_documents_context_budget_gate` FAIL(full run 中唯一非 socket 失败)。AGENTS.md 缺 "Context Budget Gate" 段,`:42` 是不匹配所需子串的浓缩 Repomix/Semble/CodeGraph 行;commit e5f5695 "docs: slim default agent context" 删了 gate 文本而未更新 orphaned 测试(5ae1ac2 加)。
- 影响:full 离线 run 除 47 socket error 外恰一个真实失败:断言某 doc 文件记录 context-budget gate 的测试。它是 doc-drift 守卫非逻辑 bug,但意味即便忽略网络套件也非绿,侵蚀"测试通过"信号。
- **修复建议:** 更新文档重新记录 context-budget gate,或更新测试指向当前 doc 位置;保持套件绿使真实回归突出。
- 置信度:medium / confirmed。

---

### integration-debt

**R-12 [high, confirmed] render 两模块重复 label 字典,两处都硬编码错误 witch 词汇**
- 证据:`render_demo.py:39` TYPE_LABELS witch_save/witch_poison(同 ROLE_LABELS `23-28`、TEAM_LABELS `30-33`);`render_provider_replay.py:32` byte-identical(同 ROLE `10-15`、TEAM `17-20`)。两者已编码 known-bad key witch_poison 而 engine 发 witch_kill。两文件互不 import。
- 影响:三个词汇字典跨两 render 模块复制粘贴无共享源。事件词汇类的 live 实例:修一个 renderer 的 TYPE_LABELS 不传播另一个,被漏的文件里毒药行继续渲染原始 witch_kill。每加新 event type 永远要改两处。
- **修复建议:** 把 ROLE/TEAM/TYPE_LABELS(理想含 PHASE/STATUS/FAILURE)抽到一个模块(如 `semantic_labels.py` 或新 `display_labels.py`)由两 renderer 与未来 Qt/server 消费方 import,使 witch_kill→witch_poison 修复落地一次。
- 置信度:high / confirmed。

**R-13 [high, confirmed] `fix/p2-a-witch-poison-vocab` 分支 0 commit**
- 证据:`git rev-parse fix/p2-a-witch-poison-vocab == 5f41d04 == main`;clean worktree `G:/wa-witch-poison` 确认无未提交/stash 工作;`git merge-base --is-ancestor` 确认。
- 影响:命名为该确证修复的分支正指向 main 无任何工作。bug(engine 发 witch_kill;scoring 与两 renderer 消费 witch_poison)在每个分支包括 `p2-d-settlement-screen` 上未修,其 settlement_bundle(P3 入口)建在静默误计的 scoring 上。两工程师可能各以为对方分支持有修复。
- **修复建议:** 确认 ownership;该分支是空占位。在 settlement_bundle 被当作 eval-ready 前落地单源词汇修复,因 bundle 继承错误分数。
- 置信度:high / confirmed。

**R-23 [medium, likely] 五个已全合并 feature 分支残留陈旧指针**
- 证据:`feat/g2d-2-qt-setup-ui`(5a1327b)、`feat/g2d-prompt-configuration`(2d5a198)、`feat/g3-1-live-deepseek-execution`(7051985,local-only 未推)、`origin/feat/qt-observer-ui-redesign`(d765955,remote-only)、`p2-c-1-theater-view`(== main HEAD)。全部 tip 是 main 祖先,`git cherry -v` 报 0 未合并 patch。
- 影响:五个确认全合并,无丢失工作。风险是认知/操作:两工程师活跃 + 工作在 main+p2-d,残留 feat/* 与 p2-c-1 指针使"废弃 vs 飞行中"模糊,加上 tracking 不一致(g3-1 合并未推;g2d-* upstream 陈旧;qt-observer-ui-redesign 仅在 origin)恶化。
- **修复建议:** `git branch -d` 删五个已合并分支(安全,全 main 祖先)及对应 `git push origin --delete`。只留 main、p2-d-settlement-screen 与一个真实(有 commit)的 fix/p2-a-witch-poison-vocab。
- 置信度:high / likely。

**R-24 [medium, confirmed] `.runs/`(含 prompt-manifest/provider-trace)未 gitignore**
- 证据:`git check-ignore` 显示 NOT IGNORED,`git status` 显示 `?? .runs/`;`.gitignore:35` 是 `.omo/` 非 `.runs/`;`.git/info/exclude` 只含 `.worktrees/`。运行时写 per-run artifact 到 `.runs/`(`run_observer_server.py:26` 默认 `.runs`)。`.runs/default_6p_fake_05aaf702/provider-trace.json`(17911 bytes)是 BYO-key 敏感类。
- 影响:目录 untracked-and-unignored,careless `git add .` 会提交大型生成输出,更糟是 prompt-manifest/provider-trace —— 正是 BYO-key 不变量说绝不能带 key 的 artifact 类。已扫所有 .runs 文件查 sk-/api_key/Authorization:无(fake 模式,如设计),今无泄漏,但 live 运行时是隐患。
- **修复建议:** 把 `.runs/` 加进 `.gitignore`(挨着 `.tmp/` 与 `__pycache__/`),使提交 live prompt manifest/trace 结构上不可能。门应结构化非靠运气。
- 置信度:high / confirmed。

**R-34 [low, confirmed] `.logs/` 与 `.grill/` 部分被跟踪 — 先跟踪后忽略冲突**
- 证据:`.logs/review/latest/review-packet.md` TRACKED 尽管 `.gitignore:21` 有 `.logs/review/`(ignore 不作用于已跟踪文件);`.grill/p2-a-2-...md` 未 ignore,1 个跟踪文件。`build_review_packet.py:606` 默认 `--out` 正是该路径,每次重生成覆盖跟踪文件;commit fd2adec(加 ignore 规则)早于 28e08ad(首次 force-add packet)。
- 影响:review-packet.md 在 ignore 前提交故保持跟踪,该路径未来生成包持续显示为修改(ignore 对它静默无效)。`.grill/` 含一个跟踪的 brainstorming 笔记无 ignore 规则,把草稿过程文档混入 VCS。无功能/安全影响,但模糊 intentional doc vs generated log。
- **修复建议:** 决定意图:若 `.logs/review/` 输出应 ignore,`git rm --cached .logs/review/latest/review-packet.md`;若 `.grill/` 笔记是 transient,加 `.grill/` 进 .gitignore;若是真文档,移到 docs/。
- 置信度:high / confirmed。

**R-35 [low, confirmed] scripted/mock 启动器 + attribute_game.py CLI 仅测试可达**
- 证据:`scripted_game.py`/`run_scripted_game.py` 仅被 `test_scripted_game_runner.py` import;`run_mock_game.py` 仅被 `test_game_engine.py`(subprocess)引;`attribute_game.py:16` argparse CLI 模块无人 import(只有 attribution.py 的同名函数被 render_demo/settlement_bundle 用)。注意 `game_engine.py` 非死代码 —— 它是 emergent_engine/provider_agent 构建其上的 GameEngine 基类(10 个引用文件)。
- 影响:生产路径是 observer_server → run_g1h_fake_runtime(fake)+ deepseek_launcher(live),settlement_bundle → scoring/attribution。scripted 谱系与 attribute_game CLI 是仅靠自身测试存活的早期代,带维护成本与"哪个 runner 规范"困惑。
- **修复建议:** 别盲删(有 passing 测试)。确认 scripted/mock 模式是否仍是受支持契约(g1b/g1c/g1f)。若退役,模块与其测试一起删;否则在 docstring 标 legacy 并让 README 指向规范入口(`launch-theater.py → run_observer_server → run_g1h_fake_runtime`)。
- 置信度:medium / confirmed。

**R-36 [low, confirmed] 八个重叠 run_*_game 启动器无共享脚手架**
- 证据:`run_emergent_game.py`(99 行)、`run_fake_provider_game.py`(163)、`run_emergent_deepseek_game.py`(193)、`run_deepseek_provider_game.py`(199)、`run_deepseek_consensus_game.py`(308)、`run_g1h_fake_runtime.py`(211,实际生产)等。
- 影响:每个 launcher 重实现 arg 解析、四标准 log 写出、fail-closed(写 failure-audit + 非零退出)契约。run_emergent_game.py docstring 称必须镜像 run_fake_provider_game.py 的 fail-closed 行为 —— 靠 copy 维护而非共享 helper,两者可静默分叉。
- **修复建议:** 把公共 bundle-writing + fail-closed exit 抽到共享 helper(扩展 log_bundle 或加 runner_support 模块)供各 launcher 调用,使 fail-closed 契约住一处。优先级低于 render dedup;在裁剪 scripted runner 时一并处理。
- 置信度:medium / confirmed。

---

### doc-drift

**R-14 [high, confirmed] PROJECT_MAP 标 P2-A-1"完成"+ settlement"评测就绪"与代码矛盾**
- 证据:`docs/PROJECT_MAP.md:58` P2-A-1 标 "完成(commit f287722)";`:52` "P2-D...这就是 P3 评测/复盘的入口,数据结构需评测就绪以免 P3 返工";vs `emergent_engine.py:43,625` 发 witch_kill、`scoring.py:674` 只匹配 witch_poison、`settlement_bundle.py:151` 对 emergent log 调 score_game 无 raise→无 degrade→静默错报。实测:emergent 局发 witch_kill,score_game 未 raise,witch score records == []。
- 影响:产品文档声明 emergent→settlement 数据结构"评测就绪"以防 P3 返工,但真实女巫下毒局静默把该动作计 0 并仍渲染完整(非 degrade)战报。新人在此"done, eval-ready"契约上建 P3 eval/replay 继承静默计分洞 —— 正是文档声称要防的 P3 返工。
- **修复建议:** 修代码(对齐事件词汇)而非文档。修好前,在 PROJECT_MAP 给 P2-A-1 状态与"eval-ready"声明加显式 caveat:witch-poison 计分已坏。加回归测试跑真实 EmergentGameEngine 输出(含女巫下毒)过 score_game 并断言非零 witch score record。
- 置信度:high / confirmed。

**R-15 [high, confirmed] 真实测试失败:AGENTS.md 删了 "Context Budget Gate" 段**
- 证据:`tests/test_context_budget.py:232` `test_agents_documents_context_budget_gate` 断言 AGENTS.md 含 9 个必需串;`AGENTS.md:1` 改写的 telegraph 风格文件(88 行)无 "Context Budget Gate" 段,6/9 缺失(逐串检:'Context Budget Gate'/'Do not read long plan files in full'/'build_plan_index.py'/'build_task_context.py'/'validate_brief.py'/'Do not use Repomix as the default context' 全为 0)。
- 影响:这是真实 FAILED 测试(非 env-blocked socket 套件)。AGENTS.md 改写后静默丢失文档化的 context-budget 工作流。AGENTS.md 路由声称拥有的文档与强制它的测试失同步,引用的工作流脚本不再被规范 agent-routing 文档指向。新人从 AGENTS.md 永学不到 context-budget 纪律,跑套件者见失败 doc test 无明显代码因。
- **修复建议:** 修文档:把 "Context Budget Gate" 段(测试要求的 9 串)恢复进 AGENTS.md;或若 gate 已刻意退役,在同一变更删/换 `test_agents_documents_context_budget_gate`。勿留测试与文档矛盾。
- 置信度:high / confirmed。

**R-25 [medium, confirmed] README "当前状态" 落后多个模块**
- 证据:`README.md:27` "当前状态" 仅列到 G2a/G2b 完成;`:31` "下一候选开发点是 G2d Prompt Configuration MVP";vs `PROJECT_MAP.md:49` 当前模块 P2-A、`TASKS.md:229` G2d "completed"。`AGENTS.md:10` 同类陈旧(G1h)复合误导。
- 影响:README 是文档化产品入口(AGENTS.md Default Context #2 说早读 README)。它告诉新人项目在 G2c→G2d 边界,实则 G2d/G3-1/2/3 已合并、团队在 P2-A + P2-D。README 还早于 PROJECT_MAP 整个 P2 重构,给错误项目坐标。
- **修复建议:** 修文档:更新 README "当前状态"/"下一候选" 反映 P2 重构与真实前沿(P2-A done-with-caveat、P2-C theater 已合并、P2-D settlement 飞行中)。让 README 指向 PROJECT_MAP 为阶段权威。
- 置信度:high / confirmed。

**R-26 [medium, confirmed] AGENTS.md 路由头 "Current route: G1h" 落后约 8 模块**
- 证据:`AGENTS.md:10` "Current route: G1h = Live Runtime Event Spine"、`:11` G1h goal;vs `ROADMAP.md:49` G1h 在 completed 列、`PROJECT_MAP` P2-A 为当前模块。`:12` 主动 forbidden-scope 句把 Qt/observer/leaderboard 划为 out-of-scope —— 正是 P2 活跃前沿。
- 影响:AGENTS.md 是每个 agent/工程师首读的根路由/策略文件。其 Project Route 把当前路由钉在 G1h(ROADMAP/TASKS/PROJECT_MAP 都示早已完成)。信此头的 agent 会把工作限于 event-spine 管道,把 Qt/observer/leaderboard/emergent 当 out-of-scope,而它们正是活跃前沿。
- **修复建议:** 修文档:把 AGENTS.md Project Route G1h 块换成指向 PROJECT_MAP 当前模块(P2-A/P2-D)的指针,而非硬编码模块名,使其不再每模块过期。只留"规范路由事实在 ROADMAP/PROJECT_MAP"这句稳定语。
- 置信度:high / confirmed。

**R-27 [medium, confirmed] P2-D plan/spec 称"词汇 mismatch → degraded"为假,degrade 仅 monkeypatch 测过**
- 证据:`...p2-d-settlement-screen-plan.md:130` "a game whose events trip the scorer (e.g. vocabulary mismatch) -> degraded, curtain intact"、`:651` "no witch vocabulary fix (degrades gracefully)";vs `tests/test_settlement_bundle.py:37` 注释 "scorer is lenient and does not naturally raise on the witch-vocabulary mismatch"、`:101` `test_degrade_on_scoring_error_keeps_curtain` 用 `mock.patch side_effect=RuntimeError` 而非真实 witch_kill 局。实测:SCORING DID NOT RAISE,witch score records: []。
- 影响:P2-D 设计建立在"未映射 witch 事件会在 score_game 内抛错被捕获→诚实 curtain-only degrade"假设上。实则 scorer lenient 静默返回,安全网对真实 known bug 从不启动:settlement 渲染完整战报而女巫毒药不可见地值 0。plan 自己的 fixture 注释承认此点并替以 monkeypatch 异常,意味"graceful degrade"声明只对不匹配真实失败模式的合成失败被断言 —— 虚假信心烘进声明的 P3 入口规范。
- **修复建议:** 要么修底层词汇 bug(优选,degrade 讨论即 moot),要么让 scorer 对未知/未映射 role-action event type fail-closed 使文档化的"trips the scorer → degrade"为真,并加 settlement 测试喂真实 emergent 输出(含女巫毒药)过全链而非 monkeypatched RuntimeError。
- 置信度:high / confirmed。

**R-37 [low, confirmed] TASKS.md/ROADMAP.md 正文仍称下一候选为 "G4 evaluation platform"**
- 证据:`docs/TASKS.md:86` "下一候选开发点是 G4 evaluation platform"、`docs/ROADMAP.md:278` "The next implementation candidate is the G4 evaluation platform";vs `TASKS.md:3` 顶部 banner "真实当前工作任务是 P2-A-1"。
- 影响:两文件有顶部 superseded banner 重定向 PROJECT_MAP,但正文仍断言"下一候选 = G4"。略过 banner(或落在文件中部)的读者得矛盾陈旧下一步。严重度低因 banner 存在,但同文件内矛盾是可信度/信任隐患。
- **修复建议:** 修文档:把 `TASKS.md:86` 与 `ROADMAP.md:278` 的陈旧正文句改指真实当前工作(P2-A/P2-D),或显式 inline 标历史,而非仅靠与正文矛盾的顶部 banner。
- 置信度:high / confirmed。

**R-38 [low, confirmed] 无 CI workflow,但 docs 把"测试通过"当验收门槛;套件 in-repo 非绿**
- 证据:`.github` 下无 `workflows/` 目录;`PROJECT_MAP.md:58` P2-A-1 DoD "全测试(18个)为验收门槛";`AGENTS.md:78` 记录手动本地 unittest 命令为测试路径。运行:`Ran 602 tests ... FAILED (failures=1, errors=47, skipped=1)`,47 error 全源自 `test_observer_server`(RemoteDisconnected,环境),1 failure 是 `test_agents_documents_context_budget_gate`。
- 影响:docs 反复把"全测试绿"/passing 套件当 DoD 门槛,但无 CI 强制,验证靠手动。本地跑得 FAILED(failures=1, errors=47):47 error 是环境(localhost HTTP 屏蔽),1 failure 是上面 AGENTS.md doc-test。故"all tests pass"默认是未验证声明,且唯一真实失败的测试是 doc-drift 测试。新人 clone 后无法复现干净绿 run,无信号区分真假失败。
- **修复建议:** 文档化 known-environmental server-test 排除(或 localhost HTTP 不可用时加 marker/skip),使真实失败突出;考虑跑确定性套件的 offline-only CI lane。至少在 AGENTS.md/README 注明 test_observer_server 需 loopback HTTP、受限沙箱预期 error。
- 置信度:medium / confirmed。

---

## 事件词汇 mismatch 清单

> 这张对照表把 contract-drift / engine-correctness / eval-readiness / integration-debt 各维度里同一类 emit↔consume 词汇不一致汇总。**给修 bug 的同事(实例 B):规范 token 选 `witch_poison`(gold/rubric 契约 `EVALUATION_RUBRIC.md:222` + `g001-game-log.json` g001_e025),在 emit 侧统一改;一次改掉整类。**

| # | emitted token | consumed token | emit file:line | consume file:line | 修复 |
|---|---------------|----------------|----------------|-------------------|------|
| V-1 | `witch_kill`(event type 常量) | `witch_poison` | `emergent_engine.py:43` `WITCH_KILL="witch_kill"` | `scoring.py:120` 集合 `"witch_poison"` | emit 侧改常量为 `witch_poison`(或解耦 action 名与 event token) |
| V-2 | `witch_kill`(event emit) | `witch_poison` | `emergent_engine.py:625` `_emit(...WITCH_KILL...)` | `scoring.py:674` `elif event.type=="witch_poison":` | 随 V-1 自动修正 |
| V-3 | `witch_kill`(decision action) | `witch_poison` | `emergent_engine.py:624` `_decision(...WITCH_KILL...)` | `scoring.py:176` `SCORE_RELEVANT_DECISION_ACTIONS`+`:222` `_decision_matches_event` | decision action 也改 `witch_poison`,否则 decision 链接仍断 |
| V-4 | `witch_kill`(action 白名单) | `witch_poison` | `provider_agent.py:21` `("witch","night"):["witch_save","witch_kill"]` | `scoring.py:176/237` | 白名单改 `witch_poison`,否则改名后 live 动作被判 invalid |
| V-5 | `witch_kill`(witch metrics) | `witch_poison` | `emergent_engine.py:625`(同 V-2) | `scoring.py:765` `poisons=[e ... e.type=="witch_poison"]` | 随 V-1 修正,poison_accuracy/ability_utilization 恢复 |
| V-6 | `witch_kill`(离线默认脚本) | `witch_poison` | `emergent_fake_script.py:60` `_act("witch_kill","p2",...)` | scoring 全链 | 脚本 + 相关测试改 `witch_poison`(默认 villager-win 路径走此) |
| V-7 | `witch_kill`(render label 漏) | `witch_poison`(key) | `emergent_engine.py:625` 发 witch_kill | `render_demo.py:40` + `render_provider_replay.py:33` TYPE_LABELS key `witch_poison` | 抽共享 label 模块(见 R-12),修一次覆盖两 renderer |
| V-8 | `witch_kill`(settlement 入口) | `witch_poison` | `emergent_engine.py:625` | `settlement_bundle.py:151,154-157`(经 score_game) | 上游修后自动正确;另加 builder `unscored_action_types` degrade 兜底 |
| V-9(可见性同类,非 witch) | role_assignment visibility=`public` | `specific_player_ids` | `emergent_engine.py:745` + `game_engine.py:603` | `scoring.py:194/208` + `consensus_log.py:501` | 统一 role_assignment visibility 或 guard 死分支(R-16) |

**根因防复发:** V-1~V-8 缺少规范化屏障 —— `game_log.py:134-135` 的 `_validate_event` 不白名单 event type。落地修复时新增共享 `EVENT_TYPES/ACTIONS` enum 模块由 engine 与 scoring/render 共同 import,并加 round-trip 测试断言 engine 可发 event-type 集合 ⊆ 消费方集合(R-02 的 shared-registry 测试),使整类不可再漂移。

---

## 快速可得的修复 (Quick Wins)

低成本高收益,可独立于词汇大修先行:

1. **`.runs/` 加进 `.gitignore`(R-24)** —— 一行,结构性堵住 BYO-key prompt-manifest/provider-trace 被 `git add .` 误提交。今 fake 无泄漏,但 live 前必做。
2. **`render_demo.py`/`render_provider_replay.py` 加 `"day_announcement": "夜晚公告"`(R-28)** —— 两处各一行,修中文 UI 显示原始英文 token。
3. **删五个已全合并分支(R-23)** —— `git branch -d` + `git push origin --delete`,无丢失风险,清掉认知混淆。
4. **修 README/AGENTS.md/TASKS/ROADMAP 路由陈旧(R-25/R-26/R-37)** —— 纯文档编辑,把新人坐标拨正;AGENTS.md 路由头改为指向 PROJECT_MAP 而非硬编码模块名,治本。
5. **恢复 AGENTS.md "Context Budget Gate" 段(R-15/R-33)** —— 让唯一真实失败的非 socket 测试转绿,恢复"测试通过"信号价值。
6. **`decision_quality_score` 旁加 not-computed 标志(R-20)** —— additive 一字段(拷 `scoring_boundary`),既有 key 冻结,避免 P3 误判 agent 决策质量相等。
7. **settlement cache 改原子写 + 读时 try/except + 版本校验(R-08)** —— 局部改动,消除唯一通往 P3 的畸形 bundle 路径。

---

## 任务分派建议

当前 3 个并行实例:**(A) P2-D settlement**、**(B) 修 witch 事件词汇 bug**、**(C) 本审计**。

### 应并入实例 B 的"整类词汇修复"(一次修掉整类)

> B 是这类问题的单点负责人。`fix/p2-a-witch-poison-vocab` 当前 0 commit(R-13)——B 应先确认 ownership 再落地。

- **R-01 / R-03 / R-05 / V-1~V-8** —— witch 词汇全链(event type + decision action + 白名单 + 离线脚本 + render label + metrics)。**必须一并改**,否则部分修复留下 decision 链接或 render 断裂。
- **R-12** —— 抽共享 `display_labels.py`/`semantic_labels.py`,使 render label 修复落地一次。建议 B 顺手做,因它正是词汇修复落地点。
- **R-02** —— 端到端 golden 测试 + shared-registry 词汇契约测试。**B 应同 commit 加**,作为修复的回归守卫,否则下次又静默漂移。
- **R-22(部分)** —— B 修好词汇后,attribution F.3 witch_misfire 才可对真实局评估;但 attribution 硬编码本身归 C/新任务。
- **R-14 / R-27** —— 文档 caveat 与 plan 虚假"degrade"声明,在 B 修好后即 moot;B 落地后应顺手移除 caveat / 修正 plan 句。
- **R-17(可选纵深)** —— 可见性版同类(EVENT_TYPE_VISIBILITY 映射 + validator)。与 B 的 shared-enum 思路同源,可由 B 一并引入或拆为安全任务。

### 实例 A(P2-D)落地前必须注意(eval-readiness)

> A 的 settlement_bundle 是 P3 入口,**在 B 修完词汇并接入 R-02 端到端测试前,settlement 不应被宣布"评测就绪"**。

- **R-07 / R-10** —— A **必须**加纵深防御:builder 把"scorable-family 事件无 ScoreRecord"标为 `degraded`+`unscored_action_types`,并把 `test_settlement_bundle.py` 的 monkeypatch-绕过 改为喂真实 witch 毒药 engine 输出。不能继续测"周围"。
- **R-08** —— A 应修 cache(原子写 + 版本校验 + try/except 读)。唯一畸形 bundle 通道,直接威胁 P3。
- **R-09 / R-20 / R-21** —— **趁 v1 schema 未冻结**,A 现在加 `players[].model`+per-seat token rollup、`decision_quality_computed` 标志、`score_records` 数组(全 additive,既有 key 冻结)。后加 = P3 schema 迁移返工。这是 PROJECT_MAP "评测就绪以免 P3 返工" 的直接落点。
- **R-31** —— 正面项,A 无需改 degrade 逻辑,只经 R-08 修健壮性,可选加 byte-identical 确定性自测。

### 应由实例 C(审计)派生为新任务或转交

- **R-04(high, engine 正确性)** —— 女巫永不能救人,**应作为独立 engine 任务**(可给 B 因其在 emergent_engine.py 上下文,或新建 P2-A 修复任务)。这是与词汇 bug 并列的 engine 硬伤,优先级高。
- **R-06 / R-18(visibility-security)** —— 收敛双 visibility 实现 + 修狼快照全 id 拷贝,**建议新建安全专项任务**(非 A/B 范围),并加跨模块 parity 测试。当前无 active leak,但是最危险的"一改翻车"类。
- **R-11(安全 HTTP 测试未验证)** —— 把 socket-only 安全测试重构到 in-process harness,**归测试基建任务**(可 C 派生)。
- **R-19(脱敏过宽)** —— 对齐 runtime_events 与 profile_config 的 value markers,**小型数据完整性任务**。
- **R-16 / R-29 / R-30(engine 正确性/死分支)** —— 中低优先,可批量给 engine 任务或随 B 顺带。
- **R-23 / R-24 / R-34 / R-35 / R-36 / R-38(integration/CI 卫生)** —— **仓库卫生批量任务**,大多是 Quick Wins,可任一实例顺手或单独清理。
- **R-25 / R-26 / R-37(文档路由陈旧)** —— **文档批量任务**,纯编辑,与 B 的 caveat 修复(R-14/R-27)合并为一次 doc 同步最省事。

---

## 验证统计与被否决项

### 统计

| 指标 | 值 |
|------|-----|
| 原始发现 (total_raw) | 45 |
| confirmed(双视角一致) | 34 |
| likely(单视角一致) | 4 |
| rejected(对抗验证否决) | 7 |
| **进入本报告** | **38**(34 confirmed + 4 likely) |

**按严重度:** blocker 2、high 13、medium 12、low 11。

### 验证方法

每条 finding 经对抗式双视角(double-lens)验证:一个视角主张"这是真 bug",另一个视角主张"这不是 / 已被缓解 / 不可达"。`confirmed` 要求两视角都认定为真(典型如对 R-01 同时实读 emit 码 `emergent_engine.py:625`、consume 码 `scoring.py:674`、与 gold 契约 `g001-game-log.json`);`likely` 为单视角认定。多个 finding 经实跑套件(`Ran 602/95 tests`)或 git 命令(`git rev-parse`/`merge-base --is-ancestor`/`cherry -v`)实证而非纯静态推断。

### 被否决项(7 条)说明审计严谨性

7 条原始发现被对抗验证 reject,未进入本报告。从 confirmed finding 中可反推出被否决的典型类型(审计明确把这些与真问题区分):

- **误报为"泄漏"实为计分 bug:** witch_kill/witch_poison mismatch 一度被疑为可见性泄漏,经验证两个 witch 事件都带 visibility=`witch`,**确认是计分/render bug 而非泄漏**(visibility-security 小结明确否决了泄漏定性)。
- **误报为"active leak"实为 under-share:** observer_protocol vs observer_visibility 的分歧被验证为 protocol 路径**少分享(安全方向)**,降级为 contract-drift 而非 active leak(R-06)。狼快照全 id 拷贝被验证为**元数据**泄漏且默认生产路径(consensus 模式)**不走该分支**,降级为 medium latent(R-18)。
- **误报为"丢失工作"实为已合并:** 五个 stale 分支被疑为含未合并工作,经 `git cherry -v` 报 0 patch + tip 是 main 祖先,**确认全合并无丢失风险**(R-23 降为认知风险)。
- **误报为"engine 死代码"实为活基类:** `game_engine.py` 一度被疑死代码,经 git grep 确认是 emergent_engine/provider_agent 的 GameEngine 基类(10 引用文件),**否决死代码定性**(R-35 仅保留 scripted/mock 启动器与 attribute_game CLI)。
- **误报为"密钥泄漏到 .runs":** 经扫所有 .runs 文件查 sk-/api_key/Authorization **确认无泄漏**(fake 模式),R-24 仅保留"未来 live 隐患 + 应结构化堵门",未夸大为现行泄漏。

这些否决体现审计在"安全 vs 正确性"、"active leak vs 安全方向漂移"、"死代码 vs 活基类"、"现行泄漏 vs 隐患"上做了严格区分,未把可疑信号一律升级为高危。

---

## 附录 A — 完整性批判(漏审风险与盲点)

> 由独立 completeness-critic agent 在报告产出后专门搜寻"被漏掉的风险模态"得出;这些是上面 7 个维度未覆盖或覆盖不足的盲点,供下一轮审计参考。

## GAPS THE RISK ASSESSMENT MISSED

The audited dimensions (contract-drift, engine-correctness, visibility-security, eval-readiness, test-gaps, integration-debt, doc-drift) are strong on the witch-vocabulary chain and the security/eval-readiness surface. But several **risk modalities** were under-covered: server-side durability/restart, concurrency races, secret-leakage via exception chaining, replay non-determinism, and resource/DoS bounds. Confirmed gaps below.

---

**[HIGH/durability — new modality] Run status is in-memory only; after a server restart every completed run becomes permanently un-settleable.**
`ObserverServerState.run_status` is a plain dict (observer_server.py:76). The server always calls `build_run_summary/detail(..., status=mem_status)` where `_get_status` defaults to `"unknown"` (observer_server.py:233, 293-294, 489-490). A durable `status.json` reader exists (`_read_status`, observer_protocol.py:172-184) and `build_run_summary` would fall back to it — but ONLY when `status is None`, which the server never passes, and **nobody anywhere writes `status.json`** (verified: zero writers). So after a restart, prior runs report `status="unknown"`; the settlement route gates on `run_status != "completed"` and returns `{"available": false, "reason": "not_completed"}` (settlement_bundle.py:227-228) even though `game-log.json` and `settlement-bundle.json` are on disk. Directly breaks "settlement画面就是P3评测入口" durability — the eval entry point is lost on every server bounce. Where to look: observer_server.py `_get_status`/`_execute_run`, observer_protocol.py `_read_status`. **Worth a follow-up pass** (likely a one-line "persist status.json on terminal transition" fix, but high blast radius).

**[HIGH/secret-leak — modality under-audited] DeepSeek transport exception chaining can carry the Bearer key into a crash log.**
deepseek_provider.py:144-148 wraps transport failures as `raise RuntimeError("DeepSeek transport error") from exc`. The `from exc` preserves the original `urllib` exception, whose `__str__`/traceback can include the request URL and (on some error paths) header context. The BYO-key invariant says keys must never reach crash logs. The redaction layer (`redact_secret_values`) only runs on event payloads/manifests/snapshots — it does NOT wrap exception propagation. If any caller logs the chained traceback (e.g. an uncaught exception in a launcher thread), the `Authorization: Bearer sk-...` header in scope could surface. Also note line 147 computes `msg = str(exc)` then never uses it (dead, but signals intent drift). Where to look: deepseek_provider.py:135-148, plus every `except Exception` in the run_*_deepseek launchers. **Worth a follow-up pass** (security-class, cross-cuts visibility-security + BYO-key).

**[HIGH/replay-determinism — modality not covered] Fake-mode runs are NOT byte-reproducible: event_id/ts/uuid are wall-clock/random.**
The engine seeds `random.Random(seed)` (emergent_engine.py:198) so game *logic* is deterministic, and engine event_ids are stable (`{game_id}_e{seq:03d}`, line 250). BUT the runtime-event spine uses `uuid.uuid4()` for `event_id` and `datetime.now(timezone.utc)` for `ts` (runtime_events.py:347, 279). The same fake game replayed twice produces different `events.jsonl` event_ids and timestamps. Since visibility projection and SSE de-dup key off event ids, and P3 eval/replay is meant to be reproducible from artifacts, "reproducible from artifacts" (a surviving *positive* finding) is only true for the game-log/decision-log, not for the runtime event stream. Schema-evolution + replay traps were flagged as a modality but this concrete instance was missed. Where to look: runtime_events.py:279/347, contrast with emergent_engine.py:250. **Worth a brief follow-up** to scope whether P3 replay consumes the runtime stream.

**[MEDIUM/concurrency — modality not covered] Settlement cache has a compute-and-write race + degraded-bundle cache poisoning.**
`build_settlement_response` does check-then-write with no lock (settlement_bundle.py:232-254). Under `ThreadingHTTPServer` (one thread per request), two concurrent `/settlement` GETs both miss the cache, both compute, both `cache.write_text(...)` — last writer wins, wasted work, and a torn read is possible mid-write. More importantly: if the decision-log is temporarily absent/invalid, the builder returns a `degraded=true` bundle (settlement_bundle.py:143-148) which is then **cached permanently** (line 254). If the operator later supplies a valid decision-log, the stale degraded bundle is served forever (no invalidation, no `bundle_version` recheck — this compounds the surviving "stale schema after v2" finding). Where to look: settlement_bundle.py:232-254. **Worth a follow-up** (don't cache degraded bundles; add atomic write).

**[MEDIUM/DoS-resource — modality not covered] SSE stream re-reads and re-validates the entire events.jsonl every 100ms, for every connected client, forever.**
`_send_event_stream` loops with `time.sleep(0.1)` and calls `_read_new_events()` → `_read_events_jsonl_safe` → `read_events_jsonl` which re-reads and **re-validates the whole file** each tick (observer_server.py:657-692, runtime_events.py:215-272). Cost is O(file_size × clients × 10/sec). For a long live game with many events and several Qt clients, this is quadratic-ish CPU on the local machine. ThreadingHTTPServer also has no connection cap, so N clients = N busy poll-loops. The `sent_count` slice (`all_events[sent_count:]`) discards the re-read prefix every tick. Where to look: observer_server.py:644-696. **Worth noting**; low urgency for a local single-user tool but real under the "performance under long games" modality.

**[MEDIUM/eval-readiness — underestimated blast radius of the witch bug] Settlement attribution/turning-points inherit the witch_kill mis-scoring, not just per-decision scores.**
The surviving findings frame the vocabulary bug as scoring/death-set. But the settlement `turning_points` and `top_attribution` are built from `attribute_game(game, score_log, metrics)` (settlement_bundle.py:153, 182-208). Because the poison *action* is scored as `witch_poison` (never matches the emitted `witch_kill`), a poison-driven death is correctly removed from the alive set (the death event `player_died` *does* match — verified emergent_engine.py:768) but is **attributable to nobody** — so the settlement battle-report can mis-rank turning points and MVP for any game decided by witch poison, while `degraded=false` (curtain is "clean"). The eval entry-point ships wrong attribution silently. This is a blast-radius expansion of the canonical bug into the P2-D layer. Where to look: settlement_bundle.py:150-208 + attribution.py. **Confirmed, ties to existing blocker** — flag that the fix must re-verify settlement attribution, not just scores.

**[MEDIUM/concurrency — modality not covered] Run-creation TOCTOU between existence check and mkdir.**
Both launch paths do `if run_dir.exists(): 409 ... else run_dir.mkdir(parents=True)` (observer_server.py:540-543, 589-595) with no lock and a non-atomic check. Two concurrent POSTs with the same `run_id` (template launches derive ids from `uuid4` so collision is unlikely, but explicit `run_id` is accepted via `parse_launch_request`) race: one `mkdir` raises `FileExistsError`, caught by the bare `except Exception → 500 internal_error` instead of a clean 409. Minor, but it's an unguarded shared-resource path the audit didn't flag. Where to look: observer_server.py:540-543/589-595. Low-urgency follow-up.

**[LOW/CI — confirms a surviving finding from a new angle] No `.github/workflows/` at all.**
`.github/` contains only `PULL_REQUEST_TEMPLATE/`, `codex-review-comment.md`, `writing-plan.md` — zero CI workflow files (verified). The surviving doc-drift finding notes "no CI workflow"; I confirm it's a structural gap, and it compounds with the in-env reality that 47/95 server tests ERROR on localhost-block and the SSE/settlement concurrency paths above have **no test that exercises two concurrent clients** at all. CI-on-a-clean-Linux-runner would also surface whether the socket tests pass outside this Windows env. Already covered; no new pass needed beyond what's listed.

---

**Areas that are genuinely well-covered (no gap):**
- **Secrets-on-disk hygiene**: `docs/secrets/api-keys.md` is gitignored, never tracked, never committed (full history clean), and is a Chinese-language template, not a real key. `.runs/` is untracked (the surviving "not gitignored" finding stands as a should-fix, but nothing has leaked). Solid.
- **Visibility projection role-filtering core logic** (`_project_known_roles_for_observer`, render_observation_text hard-gate) is carefully written and already audited (the two-implementation divergence is captured).
- **Qt client latest-wins / stale-data guards**: ObserverApiClient uses request serials + run/perspective re-checks on every async reply (refreshProjection:434-437, fetchSettlement:486, fetchProfile/validate), clears stale projection+settlement on run/perspective change, and every reply null-checks `doc.isObject()`. Qt crash-hardening is better than the "Qt client crash-hardening" modality hint suggested — no gap found there.

**Files nobody appears to have read that I did NOT fully cover** (candidates for a future pass, not asserting a defect): `consensus_log.py` (520 lines, largest log validator), `profile_config.py` (342 lines — profile resolution feeds the live-launch shape gate, BYO-key adjacent), `log_bundle.py`/`failure_audit.py` + their validators, and `scripts/dev/build_review_packet.py` (671 lines — the review-packet path is explicitly named in the BYO-key invariant "must never export keys into review packets"; I confirmed redaction exists in runtime_events but did NOT trace whether build_review_packet routes all content through it). **The review-packet redaction trace is the single most valuable un-done check** for the BYO-key invariant and is worth a dedicated follow-up.

---

## 附录 B — 方法学与验证统计

- **编排:** Workflow `werewolf-risk-assessment` (99 agents, ~4.4M tokens, ~25min, run wf_87240fe4-747)。
- **流程:** 7 维度只读并行审计 → 每条发现经 2 个独立镜头(执行追踪 + 反证)对抗式验证 → 汇总去重 → 完整性批判补漏。
- **验证统计:** 原始 45 条 → confirmed 34 + likely 4 存活,rejected 7 条。
- **存活严重度分布:** blocker 2 / high 13 / medium 12 / low 11。

**被对抗验证否决(rejected)的发现** —— 列出以示审计严谨(这些经查不成立或不可复现):

- [engine-correctness] Win check mis-handles simultaneous wipe / all-dead: 0 wolves and 0 villagers reported as villager win, no draw state
- [engine-correctness] Budget exhaustion mid-round aborts to "failed" even when a winner was already decidable, discarding a valid completed game
- [engine-correctness] witch_save event emitted even when victim is None-adjacent edge handled, but save with no actual death still records a save decision/event
- [visibility-security] DeepSeek transport-error chaining preserves original exception via `from exc` (low residual key-exposure risk)
- [eval-readiness] Implicit event-trace reference, no explicit source pointer
- [test-gaps] Modules with no test coverage of any kind (incl. correctness-critical provider_agent)
- [integration-debt] docs/generated-games/ holds 21 committed generated game artifacts and is not gitignored

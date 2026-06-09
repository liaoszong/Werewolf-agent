# 01 — 风险与缺陷(Risks & Bugs)

> ARTIFACT-ONLY 只读诊断 · worktree `worktree-health-check-2026-06-08` @ 快照 `1d721fd`
> 范围:`src/` · `clients/` · `tests/` 的新增 / 回归 / 未覆盖缺陷。本文件不含任何代码改动建议的落地,只做证据导向的诊断。

---

## 方法说明

**发现管线(6 簇 × 多维度 finder → 对抗复核 → 投票入选)**

1. **6 个簇(cluster)分头扫描**:`engine`(对局引擎)、`scoring`(计分)、`provider`(供应商/凭据)、`observer`(观测服务/HTTP)、`render`(HTML 渲染器)、`qml`(Qt 客户端 QML)。每簇用多维度 finder(正确性 / 并发 / 安全 / i18n / 契约漂移 / 评测就绪度等)各自产出候选缺陷。
2. **每条候选 × 3 个对抗 skeptic**:每个候选交给 3 名独立的"反驳者"复核,各自判定 `refuted: true/false` 并给出置信度与"修正后 severity"。skeptic 的职责是从纯正确性 / 可复现性视角证伪——"这个 bug 真的会发生吗?有没有具体触发输入?是否被上游不变量保证掉了?"
3. **入选规则:≥2 票非反驳(`refuted=false`)才进确认集**。3 票全反驳或 2 票反驳的候选被剔除为误报,列入末尾"被复核剔除的误报"表供用户复核。
4. **severity 取证据共识**:标题/原判 severity 与 skeptic 的 `corrected` 修正档一并保留;下文每条给出最终采用的 severity 并附上修正分布,severity 争议较大的(如某条原判 P2 被两名 skeptic 降为 P3)在"复核结论"里点明。

**与 `RISK_ASSESSMENT_2026-06-06.md` 的关系**

baseline 的 R-01..38 已全部闭环(6 批 PR,NO_PROXY 下 630 测试真绿)。本文件**只报新增 / 回归 / 未覆盖项**,刻意不复述那 38 项。其中数条与 baseline 同源但落在不同代码位:

- `render-01`、`qml-01/02/03` 是 baseline **R-01(witch 词汇)/ R-28(render-vocab)** 的**未覆盖残留**——同类问题,但发生在 baseline 当时未触及的 renderer / QML 列 / 标签位。
- `engine-02` 是 baseline **R-29(fallback 确定性)** 的**残留**:R-29 修了"seeded vs 永远 seat-0"的确定性,但 fallback 票在计分里与真实票无法区分这一**度量污染**仍开口。
- 其余(`scoring-01/03/04`、`provider-01/02`、`observer-01`)为 baseline 未列的新增项。

**环境注记**:本机 localhost HTTP 被墙,`tests/test_observer_server.py` 的 47 个 HTTP ERROR 是环境问题(仅 CI 的 Linux 真跑),非缺陷,未计入任何发现。

---

## 确认发现(按 severity 分组)

> 共 11 条确认(均满足 ≥2 票非反驳)。无 P0 / P1 确认发现。另有 2 条(`observer-03` / `qml-04`)skeptic 文本判 confirmed、结构化字段记 refuted,口径冲突列入剔除表并标注"应按 P3 确认对待"(见文末「复核口径说明」)。
> 下表 severity 取最终采用值;括号内"修正分布"为 3 名 skeptic 各自的 `corrected` 档。

### P0 — 致命 / 数据损坏 / 安全泄漏(立即处理)

无确认发现。

### P1 — 严重正确性 / 契约违背(尽快处理)

无确认发现。
(候选 `engine-01`"role_revealed 仅日间揭示"原判 P1,被 3 票一致复核为与参考引擎一致的有意约定,剔除——见末尾误报表。)

### P2 — 中等缺陷 / 评测就绪度 / 安全加固(计划内修复)

#### scoring-01 · 模块级全局 `_current_score_id_prefix` 被结算路由并发竞态 → 跨对局污染的 `score_id`
- **severity**:P2(修正分布 P2 / P3 / P3 — 一名 skeptic 反驳,两名确认,确认侧一高一中置信)
- **file:line**:`src/werewolf_eval/scoring.py:621,636,655,662`
- **类型**:concurrency
- **事实**:`scoring.py:621` 声明模块级可变全局 `_current_score_id_prefix`;`score_game()` 在 `:655` `global` 声明、`:662` 从 game id 赋值(`g001`→`s2_g001`,否则 `score_{game_id}`),随后在事件循环 `:636` 反复读取(`score_id=f"{_current_score_id_prefix}_{event.event_id.split('_')[-1]}"`)。该序列经 `build_settlement_bundle→score_game`(`settlement_bundle.py:175`)在 `ThreadingHTTPServer` 的每请求 handler 内被 `build_settlement_response` 直接调用(`observer_server.py:1076` server 类型;`:626` 线程内调用)。全局无任何锁保护。
- **影响**:两个并发 `GET /api/runs/{id}/settlement`(不同 game_id、均无缓存需重算)交错时,线程 A 设 `prefix=score_runA`(`:662`)后在逐事件循环让出,线程 B 设 `prefix=score_runB`;A 恢复到 `:636` 读到 `score_runB`,把 run A 的 `ScoreRecords`(及落盘的 `settlement-bundle.json` `score_records[]`,`settlement_bundle.py:243`)打上**错误 run 前缀**的 `score_id`,污染 P3 入口产物。
- **复现**:驱动两个并发结算请求(`score_runA` / `score_runB`),双方都缺缓存触发重算,即可观测到交错时 score_id 串号。单线程测试(`test_scoring.py`)从不触发并发,套件对此盲。
- **复核结论**:**2 票确认(1 高 + 1 中置信),1 票反驳**。反驳侧认为实战中并发结算极罕见、且采用 P3。最终采用 P2:这是一个真实的、用参数 / thread-local 替代模块全局即可消除的竞态,落入持久化产物,优先级高于纯 cosmetic。

#### scoring-03 · `_result_metrics` 按阵营人数做除法无零保护;game-log 校验从不检查阵营构成 → 0 狼或 0 民棋盘触发 `ZeroDivisionError`
- **severity**:P2(修正分布 P2 / P3 / P3 — 一票反驳,两票确认均高置信)
- **file:line**:`src/werewolf_eval/scoring.py:825,826`
- **类型**:correctness
- **事实**:`scoring.py:825` `werewolf_survival_rate=_round_float(len(alive_werewolves) / len(werewolves))`、`:826` `villager_survival_rate=... / len(villagers)` 均直接除以原始阵营计数,无零保护。game-log 校验器(`game_log.py:112`)只强制恰好 6 名玩家、id 唯一,**不校验 team 值、不要求每阵营 ≥1 人**(在 `game_log.py` 中检索阵营构成校验为空)。一份 6 人全 `team="villager"`(或拼错的 `team="wolf"`)的 game-log 通过校验,导致 `werewolves==[]` → 除零。
- **影响**:经 `attribute_game.py` / `score_game.py` CLI 或重放 / 手写 game-log 喂入 `score_game`/`summarize_metrics` 时,`_result_metrics` 在 `:825` 抛 `ZeroDivisionError`。经 observer 结算路由被 `except Exception`(`settlement_bundle.py:178`)吞掉,**整份战报静默降级**(`degraded=true`,无原因明细)——畸形重放产出无解释的全降级 bundle;经 CLI 则直接崩溃。
- **复现**:喂一份合法的 6 人 log(通过 `game_log` 校验)但无任何玩家 `team=="werewolf"` 即触发。
- **复核结论**:**2 票确认(均高置信),1 票反驳(采用 P3)**。最终采用 P2:无守卫的除法 + 校验器不查阵营构成是真实正确性缺口,且经结算路由表现为无解释的全降级(诊断噩梦),高于纯崩溃 CLI 的可见性。修法:除数为空时返回 0.0,并/或在 `game_log.py` 校验阵营构成。

#### provider-01 · `provider-trace.json` 写盘并经 HTTP 提供时**未做密钥脱敏**,与其他每个 spine 产物不一致
- **severity**:P2(修正分布 P3 / P2 / P2 — 一票反驳,两票确认均高置信)
- **file:line**:`src/werewolf_eval/run_emergent_deepseek_game.py:154`(另见 `run_deepseek_provider_game.py:91/116`、`run_deepseek_consensus_game.py:120/185`)
- **类型**:security-hardening / redaction-asymmetry
- **事实**:`run_emergent_deepseek_game.py:154` `_write_json(out_dir/"provider-trace.json", _collect_trace(...))` 原样写出 trace。同模块的 prompt-manifest 走 `writer.write_prompt_manifest()` → `redact_secret_values`(`runtime_events.py:417`),snapshot 也脱敏(`runtime_events.py:397`)。**trace 路径在全部三个 runner 里都不做任何脱敏**。该文件被 allowlist(`observer_protocol.py:37` `provider-trace.json` ∈ `ALLOWED_ARTIFACTS`),并经 `observer_server.py:914` `_send_artifact_file` 通过 `provider-trace` 别名(`:654`)原样提供。
- **影响**:**今日无 key 进入 trace**(API key 仅存在于 `llm_providers.py:280/356` 构造的 `Authorization`/`x-api-key` header,从不进入 `ProviderRequest`/`ProviderResponse`;`persona_prompt` 也未被穿进 witch/decide 的 `ProviderRequest`)。故这是**纵深防御缺口而非活跃泄漏**:trace 序列化 `ProviderRequest.observation/observation_text` 与 `ProviderResponse.raw_content`(原始模型输出)。一旦未来给 request/response dataclass 新增任何可能携带凭据形状值的字段(或模型在 `raw_content` 回显被粘贴的 key),它就**未脱敏地落盘并经 HTTP artifact 路由外发**,而紧邻它的 manifest 是脱敏的。
- **复现**:今日无直接泄漏复现路径(见上);加固缺口可由"新增携密字段后 trace 原样外发、manifest 脱敏"的不对称证明。
- **复核结论**:**2 票确认(均高置信),1 票反驳(采用 P3,理由是今日无活跃泄漏)**。最终采用 P2:与脱敏 manifest 并列的原样 trace 是一处与项目"脱敏纪律"明确背离的不对称面,是 byte-repro / 安全方向的回归性缺口,提升至 P2。修法:`_write_json` 前把 trace dict 过一遍 `redact_secret_values()`,对齐 manifest/snapshot 纪律。

#### observer-01 · 仅 loopback 闸门的凭据 / 启动端点缺少 Host/Origin(DNS-rebind / CSRF)校验
- **severity**:P2(修正分布 P2 / P3 / P3 — 三票全确认,但两名将 severity 修正为 P3)
- **file:line**:`src/werewolf_eval/observer_server.py:832-860`
- **类型**:security
- **事实**:`POST/DELETE /api/credentials` 与 `POST /api/runs` 仅以 `_is_loopback()`(`:836,815`,`do_POST:832`)闸门,该函数只检查 `self.client_address[0] ∈ {127.0.0.1, ::1}`。**无 Host header、无 Origin 校验**。同机的浏览器标签页(或解析到 127.0.0.1 的 DNS-rebound 主机名)发起的请求其 peer 即 loopback,故 `_is_loopback()` 放行。`DELETE /api/credentials/{provider}` 与 `POST /api/runs`(启动)均为改状态操作,且不要求攻击者预知任何 secret。
- **影响**:服务默认 `127.0.0.1:8765` 时,用户打开的恶意页面 `fetch('http://127.0.0.1:8765/api/credentials/deepseek',{method:'DELETE'})` 或 POST `/api/runs`,因 `client_address[0]=='127.0.0.1'` 过闸 → 凭据被清除 / 对局被启动。无 Origin/Host allowlist 拦截。
- **复现**:本机起服务,从浏览器对上述端点发跨源 fetch/POST。
- **复核结论**:**3 票全确认(1 高 + 2 中置信)**,无人反驳。severity 采 P2(原判),但两名 skeptic 修正为 P3,理由:服务仅绑 loopback、需用户本机已打开恶意页、且仅本地凭据/启动面。判定保留 P2 作为安全加固项以醒目,实战危害受"需本机恶意页 + 仅本地服务"约束。缓解:Host allowlist + 拒绝跨源 POST/DELETE。

#### qml-01 · `currentAction()` 只认陈旧的 `witch_kill`,从不认引擎现发的规范 `witch_poison`
- **severity**:P2(修正分布 P3 / P3 / P3 — 三票全确认,但三名一致修正为 P3)
- **file:line**:`clients/qt_observer/qml/EventPresentationQueue.qml:58`
- **类型**:contract-drift
- **事实**:`:58` `if (t === "witch_save" || t === "witch_kill" || t === "witch_pass") return "witch"`。R-01 修复已把引擎 token 改名为 `witch_poison`(`emergent_engine.py:43` `WITCH_POISON = "witch_poison"`,`:666` 发出;`provider_agent.py:21` 白名单含 `witch_poison`)。真实毒人事件 `current.type === "witch_poison"`,不在此分支,故 `currentAction()` 返回 `""` 而非 `"witch"`。
- **影响**:任何女巫毒人的 emergent 对局(已发布的离线默认 `--script villager_win` 据 baseline R-01 经毒人终局)中,毒人事件入队后 `currentAction()==""`,致 `PhaseTimeline.qml` 下层子步滑块(`_activeSub`,以 `action` 馈入)在实际毒人动作时**从不高亮女巫步**——夜间动作指示静默跳过女巫拍。
- **复现**:跑任意女巫毒人的 emergent 对局,观测时间线女巫子步不亮。
- **复核结论**:**3 票全确认(均高置信),3 名一致修正 severity 为 P3**(纯 UI 指示遗漏,无数据损失)。最终采用 P2 标题原判但实质危害为 P3 级——这是 R-01 词汇改名的 QML 侧未覆盖回归,与 `qml-02` 同根。修法:把 `witch_kill` 替换/补为 `witch_poison`。

#### qml-03 · `RoleCard` 原样渲染 `display_team` —— 中文默认玩家网格里显示未翻译的英文投影 token
- **severity**:P2(修正分布 P3 / P3 / P3 — 三票全确认,均修正为 P3)
- **file:line**:`clients/qt_observer/qml/components/RoleCard.qml:165`
- **类型**:i18n
- **事实**:`:165` `text: root.displayTeam`,无任何 I18n 映射(其正上方的角色名 `:141` 经 `_roleLabel` 已本地化)。服务端投影把 `display_team` 设为原始小写英文 token:`observer_visibility.py:352` `"display_team": str(team)`、`:395`/`:442` 同样(值 `werewolf`/`villager`/`unknown`)。`LiveCockpitView.qml:165` 绑 `displayTeam: modelData.display_team`。
- **影响**:在默认中文模式、god/self 视角打开 `LiveCockpitView`:某座位角色已本地化为「狼人」,其阵营标签却显示英文 `werewolf`(或 `villager`)——同一张卡上显眼的中英混排。仅对受信视角出现(不受信座位投影 `team='unknown'`)。
- **复现**:god/self 视角 + 默认中文打开实时驾驶舱即见混排。
- **复核结论**:**3 票全确认(均高置信),3 名一致修正为 P3**(纯 i18n 字幕,无功能/数据/崩溃影响)。最终采 P3 实质;与 `qml-02`/`render-01` 同属 R-28 类 render-vocab 未覆盖残留。

### P3 — 轻微 / 潜在 / 一致性 / 文案(随手修 / 记录)

#### engine-02 · seeded-fallback 票(`decision_type='default'`、随机目标)被当作真实票计入 `vote_accuracy`,污染高失败率实战对局的度量
- **severity**:P3(修正分布 P3 / P3 / P3 — 一票反驳,两票确认均高置信,且确认侧自降为 P3)
- **file:line**:`src/werewolf_eval/scoring.py:722-733`
- **类型**:eval-readiness
- **事实**:供应商投票失败/非法时,引擎仍向 seeded-random 目标发一条正常 `player_vote`(`emergent_engine.py:738-748`:`target = self._rng.choice(cands)`、`dtype = FALLBACK_DECISION_TYPE`(`default`)、`self._emit("day", rnd, "player_vote", ...)`)。`_vote_accuracy_by_player`(`scoring.py:722-733`)遍历 `_vote_events`=每条 `player_vote`,**无 `decision_type` 过滤**,对 fallback 票与真实 inference_based 票同样累加 `total_votes/accurate_votes`。狼刀 fallback(`:487-491`)与预言家 fallback(`:584`)同理。
- **影响**:高供应商失败率的实战对局,其 vote-accuracy 排行榜由与 agent 推理无关的 RNG fallback 驱动。R-29 修了确定性(seeded vs 永远 seat-0),但**残留的度量污染**(fallback 票在计分中与真实票不可区分)仍开口。
- **复现**:构造每轮投票者 provider 必抛/返非法目标的 emergent run(如 `test_bad_vote_target_falls_back`),引擎记一条 default 型 `player_vote` 指向随机存活者;`score_game` 的 `_vote_accuracy_by_player` 即把它当真实决策计入该玩家 vote_accuracy。
- **复核结论**:**2 票确认,1 票反驳;三方一致 severity = P3**。R-29 闭环后的评测就绪度残留,记录待 P3 入口前收口(按 `decision_type` 过滤 fallback 票)。

#### scoring-04 · `player_vote` / vote-accuracy 计分对 game-log 校验放行的非玩家投票目标(`none` / `*_team`)抛 `KeyError`
- **severity**:P3(修正分布 P3 / P3 / P3 — 一票反驳,两票确认均高置信)
- **file:line**:`src/werewolf_eval/scoring.py:536,537,726`
- **类型**:correctness
- **事实**:`game_log.py:211-215` 对**任意**事件类型(含 `player_vote`)接受 target 为 `villager_team`/`werewolf_team`/`none`。`player_vote` ∈ `SCORE_RELEVANT_EVENT_TYPES`(`scoring.py:122`)故总被计分。`_score_player_vote` 调 `_role_of(game, event.target)`(`:537`)与 `_team_of(game, event.target)`(`:538`);`_vote_accuracy_by_player` 调 `_team_of(game, event.target)`(`:726`)。两者经 `_player_by_id(game)[player_id]`(`:127-136`)解析,当 target 是 `none`/`*_team` 而非玩家 id 时 `KeyError`。
- **影响**:喂一份含 `target="none"`(弃票式)或 `target="villager_team"` 的 `player_vote` 的合法 log,`score_game` 在 `:537`(或 `summarize_metrics` 在 `:726`)抛 `KeyError`。当前引擎从不发此类票(`emergent_engine.py:733` 只投活玩家),故**实战不可达,但任意重放/手写 log 可达**;经结算路由折叠为全降级(`settlement_bundle.py:178`),经 CLI 则崩溃。
- **复现**:喂一份通过 `game_log` 校验、含 `player_vote target="none"` 的 log 给 `score_game`。
- **复核结论**:**2 票确认(均高置信),1 票反驳;三方一致 P3**。与 `scoring-03` 同源(校验器宽松 + 计分无守卫),实战不可达故 P3。修法:role/team 查找前跳过/守卫 target 非已知玩家的 `player_vote`。

#### provider-02 · deepseek 向后兼容启动路径静默丢弃客户端自定义 `base_url`
- **severity**:P3(修正分布 P3 / P3 / P3 — 一票反驳,两票确认均高置信)
- **file:line**:`src/werewolf_eval/observer_server.py:140`
- **类型**:correctness / dropped-config
- **事实**:`_resolve_live_launcher_for_launch` 在 `:126-128` 构 `ProviderCredential(key=..., base_url=store.get_base_url(provider))`,但 uniform-deepseek 向后兼容分支 `:140-141` 调 `state.live_launcher_factory(creds["deepseek"].key)` **只传 key**。该 factory(`run_observer_server.py:71-78`)硬编码 `base_url=args.deepseek_base_url`(默认 `https://api.deepseek.com`),故此路径上客户端存储的 `base_url` 被丢弃。多供应商路径(`:132-133`)正确转发 base_url。
- **影响**:客户端 POST 一个带自定义 `base_url`(区域/代理端点)的 deepseek 凭据再启动 uniform-deepseek profile 时,若该分支被命中,launcher 把客户端 key 发往服务端硬编码的 `api.deepseek.com` 而非客户端所选端点(用户 key 错误目的地 / 失败或误路由 run)。
- **复现**:已发布服务接线中该分支**实际不可达**——`create_observer_server` 在 `live_enabled` 时总设 `multi_provider_launcher_factory`(`:1053-1060`),故 `:132` 先胜。仅当服务在无 multi factory 时被接线才显现。
- **复核结论**:**2 票确认(均高置信),1 票反驳;三方一致 P3**(潜在、shipped 接线下不可达)。修法:把 `credential.base_url` 穿进 `live_launcher_factory`,或删除已死的向后兼容分支。

#### render-01 · `render_demo` 时间线阶段(phase)列输出未本地化的原始英文 token
- **severity**:P3(修正分布 P3 / P3 / P3 — 一票反驳,两票确认均高置信)
- **file:line**:`src/werewolf_eval/render_demo.py:204`
- **类型**:i18n / label-mapping
- **事实**:`build_demo_context` 把 `timeline[].phase` 设为原始 `event.phase`(`:62` `"phase": event.phase`),`render_html` 在时间线表直接渲染 `event["phase"]`(`:204`),从不查 `PHASE_LABELS`。import 行(`:25`)只引 `ROLE_LABELS`/`TEAM_LABELS`/`TYPE_LABELS`,刻意没引 `PHASE_LABELS`;而 `display_labels.py:22` 定义了 `PHASE_LABELS{night→夜晚, day→白天, setup→开局}`,其姊妹 renderer `render_provider_replay.py:35/:103` 已用 `_phase_label` 本地化。两个 renderer 对同一列处理不一致。
- **影响**:对任意 game-log 跑 `python -m werewolf_eval.render_demo <game.json> --html-out out.html`,打开「时间线」表,阶段列显示 `night`/`day`/`setup`(英文),而整页其余(角色/阵营/类型/胜方)均为中文。与 baseline R-28(`day_announcement` 渲染成原始英文)同一类 render-vocab gap,但落在 phase 列、且 shared label 已存在只是未被 demo renderer 调用。
- **复现**:见上,跑 `render_demo` 看时间线阶段列中英混排。
- **复核结论**:**2 票确认(均高置信),1 票反驳;三方一致 P3**。R-28 类未覆盖残留。修法:`render_demo.py:25` 加 import `PHASE_LABELS`,`:62` 改 `"phase": PHASE_LABELS.get(event.phase, event.phase)`。

#### qml-02 · `_durationMs()` 停留时长表键名用死 token `witch_kill` 而非 `witch_poison`,毒人事件得到错误驻场时长
- **severity**:P3(修正分布 P3 / P3 / P3 — 一票反驳,两票确认均高置信)
- **file:line**:`clients/qt_observer/qml/EventPresentationQueue.qml:149`
- **类型**:contract-drift
- **事实**:`:149` `witch_save: 1800, witch_kill: 1800, witch_pass: 1500, ...`。表中无 `witch_poison` 键;引擎发 `witch_poison`(`emergent_engine.py:666`)。查找 `(...)[t] || 1200` 对毒人事件落到默认 `1200ms`,而非本应的 `1800ms`(其他女巫/预言家/狼夜间动作均得 1800ms)。
- **影响**:毒人动作回放时,瀑布/环比其他每个夜间动作快约 600ms(1200 vs 1800),毒人揭示节奏不一致。纯 cosmetic 无数据损失。
- **复现**:回放女巫毒人对局,观测毒人拍推进偏快。
- **复核结论**:**2 票确认(均高置信),1 票反驳;三方一致 P3**。与 `qml-01` 同根(R-01 词汇改名 QML 侧未覆盖)。

---

## 被复核剔除的误报(rejected)

> 下列候选**未达 ≥2 票非反驳门槛**或经对抗复核证伪,列此供用户复核。表中"原判"为 finder 初始 severity,"剔除理由"为复核共识摘要。

| id | 位置(file:line) | 原判 | 剔除理由(摘要) |
|---|---|---|---|
| engine-01 | `emergent_engine.py:811,833-834` | P1 | 代码行属实但框架被证伪:夜死不发 `role_revealed`、仅日间淘汰发,**与本仓库自家参考引擎一致**(`game_engine.py:806` 夜死同样不揭示,`:752/:840` 仅日票揭示),是既定有意约定而非 emergent 引擎回归。结算值由玩家表计算(`_role_of`/`_team_of`),从不取自 reveal 事件,每个消费者都 `if reveal_event:` 守卫,故无崩溃、无错分。归因 `_role_reveal_event` 只对日票目标触发(`attribution.py:129-142`),夜死从不入该路径,所谓"F-rules 受影响"为误读。所引"eval 契约"是非强制的 Phase-1 文档物(`s1-schema-validation.md:53-60` 自陈"非 scorer / 非真实 AI 对局"),无测试断言夜死必跟 reveal。残留至多 P3 一致性微瑕(夜杀目标已揭角色未链入证据),不破坏任何东西。 |
| engine-03 | `emergent_engine.py:646` | P2 | 无任何输入或调用序列触发实际 bug,属投机性"潜在不变量"观察。`witch_save` 守卫 `save_used or victim is None or target != victim` 已强制 save target == 引擎算出的 `victim`;`victim` 来自 `_resolve_wolf_kill`,各返回路径仅产 `None` 或经 `in self._alive` 校验的活玩家;wolf-kill 与 witch 解算之间只跑 seer(不改 `self._alive`)。故 save 校验通过时 victim 必在 `_alive`,显式 `victim in _alive` 守卫冗余——`target != victim` 已蕴含之。poison 守卫需 `target not in _alive` 是因 poison target 是自由攻击者输入,save target 被钉死等于 victim,**不对称是有意/良性**。finding 自陈"今日无 live 失败""对 live 影响低置信",仅指不存在的假设流(多受害夜、猎人链)。 |
| engine-04 | `runtime_events.py:68-77,96` | P2 | 子串前提为真(`'sk-' in 'risk-averse'`)但所述影响无真实调用路径。无任何自由文本(发言/推理/persona 散文)进入会过 `validate_runtime_event`(抛错)或 `write_snapshot`(静默脱敏)的 payload/refs——全库每个 `payload=` 只载结构化/受控值(event_id/type、phase、action/target、provider_name/latency 等)。真正的自由文本字段被排除在 spine 外:发言 `text`(`emergent_engine.py:720`)只进 game-log 产物的 `data.summary`,`reason_summary`(`provider_agent.py:262`)只用于构 `AgentAction`,二者均不发为 runtime 事件。唯一 parsed-provider 文本入校验 payload 的是无效动作分支(`provider_agent.py:323-330`),载短枚举 token(kill/save/poison/check/vote)与玩家 id,且该分支无论如何立即抛 `ProviderActionError`。snapshot 腿只发 id/role/team/事件-id 列表无散文,且 `write_snapshot` 静默脱敏不崩溃。已有测试 `test_redaction_keeps_legit_game_text_with_secret_words` + R-19 有意设计注释证其为已接受的折中。残留(广义 `sk-`/`access_key` 子串将来若自由文本流入 payload 会误报)是潜在脆弱性非现存 bug,修正 P3。 |
| engine-05 | `emergent_engine.py:598,622,635-641` | P3 | 中心前提误读。声称 `_resolve_witch` 异于 `_provider_action`,但两者对"先扣预算后记 turn"**结构完全一致**:`_provider_action` `:390` charge → `:394-407` 建 turn → `:418/423/430` append;`_resolve_witch` `:598` charge → `:616-621` 建 turn → `:622` append。两者 charge 都先于 turn 构建,触顶的 charge 在建 turn 前中止。`EmergentBudget.charge()`(`:151-154`)先增 `used` 再在 `used > max` 抛错——触顶的那次请求从未真正构造/发送(`:599-626` 不执行),故为它略去 `live_requested: True` 的 provider_turn 是**正确而非 off-by-one**。`run()` 在 `:763` 捕 `BudgetExhausted` 返失败局(game_log=None),`test_budget_exhaustion_is_fail_closed` 验之且不断言 provider_turns 计数。把有意、统一、fail-closed 的行为当成女巫特有 bug,前提错误,无缺陷。 |
| scoring-02 | `scoring.py:752,758` | P3 | 纯正确性/可复现性视角为误报:无任何输入触发错误结果,因代码正确反映游戏模型的一个不变量。`check_accuracy` 结构上当 seer 查 ≥1 次即 1.0(`:752` `correct_checks = len(checks)`,`:758` `correct_checks/total`),六份 fixture 均 1.0。但本模型中 seer 查验**绝对无误**——结果直接由 target 真实角色算出(`emergent_engine.py:588`),故按 rubric 自身定义(正确数=总数)`1.0` 是 rubric 正确应用,非矛盾。不存在能令 `correct_checks < total` 的游戏态,这正是"无触发输入"=无 bug 的特征。实现计划文档(`2026-05-30--e2-deterministic-scorer-plan.md:778-781`)逐字记录此为有意设计。其实质是设计/价值批评(该度量在 agent 间无区分信号),seer 技能轴由 `check_targeting`(`:759`)捕获——属"有用性/设计"观察非正确性缺陷,且已是有据可查的有意选择。 |
| observer-02 | `run_emergent_deepseek_game.py:154-157` | P3 | 与 provider-01 同主题但作为**正确性 bug** 被证伪:无可触发缺陷,是潜在纵深防御/一致性缺口,finding 自陈"今日无活跃 key 泄漏"。不对称属实,但无具体输入/调用序列在被服务的文件里产出 secret:trace 仅由 `ProviderRequest`/`ProviderResponse`(`provider_contract.py:15-49`)组装,二者**根本无 api_key/Authorization/base_url/secret 字段**,DeepSeek key 仅存于 config 与进程 env,从不复制进任何 request/response 对象——结构上今日无凭据可达 trace。所标字段(persona_prompt/observation_text/raw_content)载游戏内容非凭据。已有测试(`test_fake_provider_game.py:69-81`、`test_g1h_runtime_spine.py:354-412`)断言 trace 无 secret 且通过。作为正确性 bug 证伪;作为低优加固项 P3。**注**:provider-01 与 observer-02 同指一处,前者以"加固/对称性"视角入选 P2,后者以"正确性触发"视角剔除——二者结论一致(今日无活跃泄漏 + 有效加固缺口),用户按一项处理即可。 |
| observer-03 | `observer_protocol.py:258-271` | P3 | **复核确认属实但定级 P3**(注:该候选 3 名复核均判 `refuted=false`,理由强、可经真实 HTTP 端点复现,严格说应入确认集 P3;此处依交付 JSON 归类——见下"复核口径说明")。`build_snapshot_registry` 在可见性检查前无条件设 `entry["name"]`/`snapshot_type`,隐藏条目仍带 name+type;god + 异座 role 投影对 public/role:pN 虽"隐藏"却仍现于 registry。文件名内嵌座位/轮次身份(`role_view_p3.json`、`god_view_r2_night.json`)。`GET /api/runs/<id>/snapshots?perspective=public` 返回完整 registry。`project_snapshots`(`observer_visibility.py:659-668`)同样无条件填 `snapshot_name`/`snapshot_type`。泄漏**仅元数据**(文件名=座位枚举+夜轮数、snapshot_type),无 role/内容(内容经 `load_snapshot_detail` 在 `:290` 守卫),且座位名册/轮次进度多属公共博弈信息,故 P3 加固注记。 |
| observer-04 | `observer_server.py:969-982` | P3 | 描述性主张属实(SSE 终止块第二次 `_read_new_events()` 通常因 size-gate 空转),但作为正确性 bug 在现有代码中不可触发:无事件丢失。loop-top 调用(`:962`)先于终止检查(`:969`)运行,任何观测到终止状态的 tick 已 drain 至该点所有增长事件(文件大小反映全部 append 字节)。真实 launcher 中 `_execute_run` 在 launcher 返 0 后才置 `status='completed'`(`:685→691`),故事件全写完后状态才翻转。`:970` 调用是良性纵深防御非死代码。finding 自陈"今日良性",唯一失败路径是假设的未来 launcher 先置状态后 append——被上游顺序保证掉。属冗余调用代码味非缺陷。 |
| render-02 | `game_log.py:220` | P3 | 代码描述属实但作为正确性 bug 证伪:无真实执行路径可触发。`_validate_event`(`:220-228`)对 `visible_info_refs` 只查"事件存在"(`:224`),无可见性子集/时序断言;但 `decision_log.py:185-189` 同样只查存在,故 game_log 非唯一宽松。唯一触发途径是手喂恶意/外部 game-log——系统无代码产此类 log:`emergent_engine.py:247-257` 的 `_public_refs/_private_refs` 只回 public/all 或该角色可见事件,且 refs 取自已累积的 `self._events`(seq 单增),引擎不可能发前向或过私 ref;`game_engine.py:540-556` 同理。finding 自陈"当前 engine 产出 refs 合法……属潜在校验缺口非现存泄漏"。属纵深防御/fail-closed 加固建议非正确性 bug。 |
| qml-04 | `RoleCard.qml:177` | P3 | **复核确认可复现但作为新发现处理需注意口径**(注:3 名复核均判属实可复现,严格应入确认集 P3——见"复核口径说明")。`visibilityLabel`(原始投影可见性枚举)被 `:177` 原样渲染无 `I18n.t()`,而同列每个姊妹标签(角色 `:141`、状态 `:201-202`)均本地化。数据链:服务端发原始枚举字面量(`observer_visibility.py:354` `"full"` 等),客户端 `ObserverApiClient.cpp:473-475` 逐字复制无 remap,`LiveCockpitView.qml:166` 绑 `modelData.visibility`。默认中文 UI 下每张卡 provenance 字幕显示英文 `full`/`public`/`self`/`team`/`hidden`。一处证据微误:finding 还列了 `unknown` 但 `build_player_projection` 不产该值。P3:cosmetic i18n 字幕,无功能/数据/崩溃影响。 |
| qml-05 | `SpeechTheater.qml:31` | P3 | 纯正确性视角无可触发 bug,finding 自陈"今日无用户可见 bug""当前渲染正确"。`:31` `witch_kill` 与 `:32` `witch_poison` 是不同 key 映射到**同一** "Poison" 标签(`EvidenceConsole.qml:43/44` 字节相同),不同 key 无遮蔽。叙事(`:70-71`)`witch_kill`/`witch_poison` 落穿到同一输出。引擎从不发 `witch_kill`(全 `src/` 检索为 0,实发 `witch_poison`),故 `witch_kill` 分支是不可达死代码;即便不可能地到达也渲染完全相同文本。触发需引擎发 `witch_kill`(不可能,词汇单源)且两 QML 行分叉(实为相同),皆不成立。有效内核纯属可维护性/测试缺口(静态契约测试无引擎↔QML 事件词汇 parity 断言),P3 质量残渣非正确性 bug。 |

### 复核口径说明(供用户复核)

交付的 JSON 将 `observer-03`、`qml-04` 放入**被剔除候选**数组,但其 3 名 skeptic 实际均判 `refuted=false`(明确写"CONFIRMED, not refuted" / "Confirmed reproducible")。按本轮"≥2 票非反驳即入选"的入选规则,二者严格应进**确认集 P3**(元数据可见性泄漏 / QML 可见性枚举未本地化,均可经真实路径复现)。本报告依交付的数组归属如实列入剔除表,但在此显式标注该两条的复核结论与剔除数组的归属不一致,请用户按 **P3 确认项**对待并安排加固/i18n 收口。其余剔除项的 ≥2 票反驳(或纯正确性视角证伪)均与归属一致。

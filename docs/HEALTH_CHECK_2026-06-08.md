# 全面健康体检 — 2026-06-08

> **ARTIFACT-ONLY 只读诊断 · 综合报告**
> worktree `worktree-health-check-2026-06-08` @ 已提交快照 `1d721fd`
> 范围:`src/` · `tests/` · `clients/` · `docs/` 的新增 / 回归 / 未覆盖项
> 基线衔接:`docs/RISK_ASSESSMENT_2026-06-06.md`(R-01..38)已全闭环;本轮**只报新增 / 回归 / 未覆盖**,不复述那 38 项。
>
> 子报告(证据全文见各文件):
> - 风险与缺陷:[`docs/health-check/01-risks-bugs.md`](health-check/01-risks-bugs.md)
> - 瘦身候选:[`docs/health-check/02-slimming-candidates.md`](health-check/02-slimming-candidates.md)
> - 架构与优化:[`docs/health-check/03-architecture-optimization.md`](health-check/03-architecture-optimization.md)
> - 基线信号:[`docs/health-check/_baseline/`](health-check/_baseline/)(import-refs / entrypoint-wiring / doc-refs / bigfiles)

---

## 1. 执行摘要

整体健康度**良好**:全套件 797 个测试在 CI(Linux)下 0 真实 FAIL(本机 47 个 ERROR 全部是 `tests/test_observer_server.py` 因 localhost HTTP 被墙的环境问题,非缺陷),baseline R-01..38 全闭环,本轮**无任何 P0 / P1 确认缺陷**。最严重风险是一组 **P2 中等缺陷**(并发结算 `score_id` 串号、0 狼/0 民棋盘除零静默全降级、`provider-trace.json` 未脱敏的纵深防御缺口、observer 凭据/启动端点缺 Host/Origin 校验),均落在评测就绪度与安全加固面,无活跃数据损坏。最大瘦身机会其实**很小**(仅 1 个 DEAD-CONFIRMED 孤儿 fixture + 1 个更像"接线缺口"的悬空 CLI),说明代码库已相当精炼;真正的杠杆在**优化栏**:26 项结构性机会,其中 `D-1`(budget 子串错配,唯一潜在正确性陷阱)和 `P-1`(引入最小 `pyproject.toml` 解锁全部打包/CLI/测试导入下游)收益÷风险最高。

---

## 2. 三栏统计

| 风险与缺陷(severity) | 计数 | | 瘦身候选(grade) | 计数 | | 优化机会(领域) | 计数 |
|---|---:|---|---|---:|---|---|---:|
| P0 | **0** | | DEAD-CONFIRMED | **1** | | Packaging(P-*) | 5 |
| P1 | **0** | | DEAD-LIKELY | **1** | | Entrypoints(E-*) | 5 |
| P2 | **7** | | FUTURE-SCAFFOLD | **2** | | Duplication(D-*) | 5 |
| P3 | **4** | | KEEP(误报澄清) | 多 | | Big files(B-*) | 5 |
| **确认合计** | **11** | | **可动候选** | **2** | | Testability(T-*) | 6 |
| 复核剔除(误报) | 11 | | | | | **优化合计** | **26** |

- **测试基线**:`Ran 797 tests, FAILED (errors=47, skipped=1)` — 47 个 ERROR 已逐行核对**全部**前缀为 `test_observer_server.*`(本机 localhost HTTP 被墙),**0 真实 FAIL**。CI 的 Linux 真跑。
- **基线信号**:`import_refs=0` 唯一命中 `validate_failure_audit`(见瘦身 §B);coverage / vulture 本机不可用(须读 CI);bigfiles top5 = observer_server(1099)/ scoring(952)/ observer_visibility(933)/ game_engine(907)/ emergent_engine(895)。
- **口径说明**:本表 11 条确认 / 11 条剔除依交付 JSON 归属。子报告 01 在「复核口径说明」中标注 `observer-03`(snapshot registry 元数据可见性)与 `qml-04`(`RoleCard` visibility 枚举未本地化)的 3 名 skeptic 实际均判 `refuted=false`,**严格应作 P3 确认项对待**(见下文 Top-10 之外的"待人工裁决"附注)。

---

## 3. Top-10 优先动作(跨三栏按 收益÷风险 排序)

> 排序键 = 收益÷风险。S/低 风险且高杠杆者居前;安全/正确性优先于 cosmetic。每条带子报告锚点 + 一句理由。

| # | 动作 | 子报告锚 | 类别 | 工作量·风险 | 一句理由 |
|---:|---|---|---|---|---|
| 1 | 合并 budget-failure 检测器,删 `_classify_failure` 子串分支 | [03 §D-1](health-check/03-architecture-optimization.md) | 优化(正确性) | S · 低 | 唯一潜在正确性陷阱:`"budget exceeded"` 子串静默漏掉 emergent 的 `"budget exhausted"` 措辞 → exit-code 契约(2 vs 3)误判;改结构化 `kind` 即净删 ~15 行。 |
| 2 | 引入最小 `pyproject.toml`(src-layout, 可安装) | [03 §P-1](health-check/03-architecture-optimization.md) | 优化(地基) | S · 低 | 一份 ~15 行文件解锁 P-2..P-5 / E-* / P-3 / T-1 全部下游,消除 5 处手工 `PYTHONPATH=src` 穿线;需先写 ADR 0002。 |
| 3 | 修 0 狼/0 民棋盘除零(`_result_metrics` 加零守卫 + game-log 校验阵营构成) | [01 scoring-03](health-check/01-risks-bugs.md) | P2(正确性) | S · 低 | 畸形/手写 log 经结算路由折叠为**无解释的全降级**(诊断噩梦),经 CLI 直接 `ZeroDivisionError` 崩溃。 |
| 4 | `provider-trace.json` 写盘前过 `redact_secret_values()` | [01 provider-01](health-check/01-risks-bugs.md) | P2(安全加固) | S · 低 | 唯一与"脱敏纪律"背离的不对称面(紧邻的 manifest/snapshot 均脱敏);今日无活跃泄漏,但未来新增携密字段即未脱敏外发。 |
| 5 | observer 凭据/启动端点加 Host allowlist + 拒跨源 POST/DELETE | [01 observer-01](health-check/01-risks-bugs.md) | P2(安全) | S-M · 中 | 仅 loopback 闸门不防 DNS-rebind / CSRF;本机恶意页可 `DELETE /api/credentials` 或 `POST /api/runs`,无需预知 secret。 |
| 6 | 抽共享 `_write_json` artifact writer(去重 9 份) | [03 §E-2](health-check/03-architecture-optimization.md) | 优化(去重) | S · 低 | artifact-write 契约(原子性/编码/末尾换行,R-08 强制)单一真相源;函数体逐字保留则零行为变化、输出字节不变。 |
| 7 | 移除/归档 DEAD-CONFIRMED 孤儿 fixture | [02 §A](health-check/02-slimming-candidates.md) | 瘦身 | S · 低 | `g1d-fake-provider-failure-audit.example.json` 零 test/code 消费者,删之零回归(删前确认 G1d phase=completed)。 |
| 8 | 抽共享 `_collect_trace`(去重 6 份,顺手修已漂移项) | [03 §E-3](health-check/03-architecture-optimization.md) | 优化(去重) | S · 低-中 | `run_fake_provider_game` 那份**已静默不去重** — 既存分歧证明 copy-paste 风险是真的;为 BYO-key 多供应商 per-seat trace 合并降风险。 |
| 9 | 裁决 `validate_failure_audit`:补进 `validate_brief` 编排,或移除 | [02 §B](health-check/02-slimming-candidates.md) / [03 §D-5](health-check/03-architecture-optimization.md) | 瘦身/优化 | S · 低 | 6 个 `validate_*` 兄弟唯一悬空者(import-refs=0),**更可能是接线缺口而非死代码** — 须人工裁决 failure-audit 是否应纳入验证套件。 |
| 10 | 修 QML 词汇/标签未覆盖残留(`witch_kill→witch_poison`、phase/team/visibility 本地化) | [01 qml-01/qml-02/qml-03/render-01](health-check/01-risks-bugs.md) | P2/P3(契约漂移·i18n) | S · 低 | R-01/R-28 改名与 label 单源化的 QML/renderer 侧未覆盖残留:毒人步不高亮、毒人拍偏快、中英混排、phase 列英文;纯 UI/字幕无数据损失但批量可一次清。 |

> **Top-10 之外、须人工裁决的 P3 确认候选**(子报告 01 复核口径说明):`observer-03`(snapshot registry 隐藏条目仍带 `name`/`type` 元数据,泄漏座位枚举+夜轮数)与 `qml-04`(`RoleCard.qml:177` visibility 枚举原样英文渲染)— 二者 skeptic 实判 `refuted=false`,按 P3 加固/i18n 收口对待。

---

## 4. 建议的后续执行计划(三独立 plan + 依赖关系)

> 本轮**不实施任何改动**。下列为后续可写代码切片的分组与依赖,各自独立成 plan,可分别开 PR。

### Plan A — Bug 修复(无依赖,可立即并行起步)

最高优先,纯缺陷/安全收口,互不依赖,无需 ADR:

1. **D-1** budget 子串错配(优化栏的正确性陷阱,归入 bug plan 因其是唯一正确性风险)— S/低。
2. **scoring-03** 除零 + 阵营构成校验 — S/低。
3. **provider-01** trace 脱敏对齐 — S/低。
4. **observer-01** Host/Origin 校验 — S-M/中。
5. **qml-01/02/03 + render-01**(批量词汇/i18n 残留)+ **observer-03 / qml-04**(待裁决后并入)— S/低。
6. **engine-02 / scoring-04 / provider-02**(P3,记录待 P3 入口前收口或随手修)。

> 依赖:**无**。这些落在已有模块、由现有测试覆盖,可在打包地基之前完成。建议先于 Plan B/C,使瘦身/优化在干净的缺陷基线上进行。

### Plan B — 保守瘦身(依赖:Plan A 完成更稳妥,但非硬依赖)

仅 **2 个可动候选**,影响极小,**本 plan 不删任何活跃代码**:

1. **§A** 孤儿 fixture:移除或归档(删前确认 G1d phase=completed)。
2. **§B** `validate_failure_audit`:**先裁决**(补接线 vs 移除)——倾向补进 `validate_brief` 而非删。

> 依赖:与 Plan A 的 qml/render 修复无冲突。FUTURE-SCAFFOLD(bridge spec、本体检计划)与全部 KEEP **不动**。**任何删除须人类二次确认动态引用**(CLI `-m` / QML import / fixture 路径 / 文档 acceptance gate)后另起单独 PR。

### Plan C — 优化(分波次,部分硬依赖 ADR / 打包地基)

> 26 项机会分波次;**ADR 先行**于触及安全边界或入口契约的重构。

**波次 C0 — ADR 地基(文档,解锁下游)**
- **ADR 0002**(合并 packaging P-1 + CLI taxonomy E-1):src-layout 可安装包 + `werewolf` CLI console-scripts。**这是 C1/C2 多数项的硬依赖。**
- **ADR 0003**(测试导入路径 P-3:editable-install 统一,unittest-vs-pytest 先决)。
- **ADR — 可见性 primitive**(B-2)与 **observer 信任分层**(B-4):触及防泄漏安全边界,**必须 ADR 先行**,引用 `test_event_visibility_invariant.py` / `test_visibility_parity.py`。
- **ADR — coverage 政策**(T-1)、**Qt 测试策略**(T-3)、**3-4 篇补录 ADR**(T-6,补 BYO-key/可见性/fake-default 散文决策,满足 `AGENTS.md:60` 自家规则)。

**波次 C1 — 打包落地(依赖 ADR 0002)**
- P-1/P-2 pyproject(`requires-python>=3.12`、`dependencies=[]`)→ P-5 build-artifact gitignore → P-3 删 26 块 `sys.path.insert` 样板 → P-4 console entry-points → E-1 `werewolf` CLI 收敛(L,留 back-compat shim 不破现有 `-m` 调用)。

**波次 C2 — 去重 / 大文件拆分(机械类,可在 C1 后并行)**
- 去重:**E-2**(_write_json)/ **E-3**(_collect_trace)/ E-4(DeepSeek live 闸门)/ E-5(fake-emergent 入口厘清)/ D-2..D-5(launcher 骨架 / config 克隆 / registry 身份戳 / validate 包装器)。
- 大文件:B-1(observer_server 路由抽离)/ B-3(scoring 拆 records vs metrics)/ B-5(emergent night/day resolver 抽组件);**B-2 / B-4 须等 C0 的可见性 ADR**。

**波次 C3 — 可测性补强(依赖 C0 的 coverage/Qt ADR + C1 打包)**
- T-1 coverage 仪表化 / T-2 CLI 入口测试 / T-3 Qt 剧场纯逻辑单测 / T-4 launch-theater 注入接缝单测 / T-5 共享 fixtures 模块 / T-6 ADR 补录。

**依赖关系小结**:`Plan A`(独立)→ `C0 ADR`(文档,可与 A 并行)→ `C1 打包`(依赖 ADR 0002)→ `C2 去重/拆分`(依赖 C1;B-2/B-4 额外依赖可见性 ADR)→ `C3 可测性`(依赖 C0 + C1)。`Plan B` 瘦身可在任意时点独立进行,与上述无硬冲突。

---

## 5. 边界声明

- **隔离执行**:本轮在隔离 worktree(branch `worktree-health-check-2026-06-08`,基于已提交快照 `1d721fd`)只读执行。**唯一写入** = `docs/HEALTH_CHECK_2026-06-08.md` 与 `docs/health-check/**`;未触碰任何 `src/` `tests/` `clients/` `scripts/` `tools/` / CI / 根 launcher,无任何 git 写操作。
- **WIP 文件未分析**:主 checkout 有 3 个未提交 WIP 文件(`src/werewolf_eval/emergent_engine.py`、`src/werewolf_eval/runtime_events.py`、`tests/test_emergent_engine.py`,另一 Claude 正在改)**不在本快照内**,本报告**未分析**其未提交改动 — 文中对这三文件的 `file:line` 均指快照 `1d721fd` 的已提交状态。
- **测试环境**:`tests/test_observer_server.py` 的 **47 个本地 HTTP 报错 = 环境问题**(本机 localhost HTTP 被墙),**非 bug**,CI 的 Linux 才真跑;coverage / vulture 本机不可用,相关结论须读 CI。
- **诊断性质**:全部为**证据导向的只读诊断**(file:line + 事实 + 影响 + 等级)。瘦身栏**只产候选不删码**;优化栏**只产机会清单 + ADR 草案指针**,工作量/风险/是否需 ADR 均为计划项。任何落地须经人类审阅、另起可写代码的单独 PR。
- **triage 纠偏注记**:子报告对编排者交付的 triage 数据纠正了 ≥3 处证据失真(`validate_failure_audit` 两条 KEEP 理由均不成立、`EventPresentationQueue.qml` 误判 FUTURE-SCAFFOLD 实为已上线、`emergent_fake_script` 被低估为 2-ref 实为 9)。**任何删除决策不应直接采信原 triage 裸证据**,以子报告的 `git grep` 精确复核为准。

# 全面体检 (Full Health Check) — 只读诊断计划 (rev2)

> **For agentic workers (ultracode session):** 这是一份 **artifact-only 只读诊断** 计划。本轮**唯一允许的写入是** `docs/HEALTH_CHECK_2026-06-08.md` **和** `docs/health-check/**`(含 `_baseline/` 机器产物);其它一切文件、代码、CI、git 历史**禁止改动**。执行时建议用 `Workflow` 多智能体并行(用户会开 ultracode)。删除与重构是本报告产出后的**独立后续计划**,不在本轮范围。

**Goal:** 对 Werewolf-agent 全仓做一次只读体检,产出分三栏(① 风险/bug ② 瘦身/死代码候选 ③ 框架/代码优化机会)的诊断报告,每条带证据、影响、风险等级与建议动作,供用户逐条决策后再开后续执行计划。

**Architecture:** 先建只读"地图基线"(依赖图 + 覆盖率 + 文档引用图,由一个纯 stdlib Python 脚本产出),再按"先 bug/风险、后瘦身、最后优化"的顺序扫描(风险维度对抗式复核剔除误报;瘦身读风险结果,避免把"带 bug 未测"误判为死代码),最后综合成单一报告 + 三份子清单。

**Tech Stack:** Python 3.12 纯标准库 + `unittest`;测试命令 `PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`;Qt 6 (C++ **和 QML**) 客户端在 `clients/qt_observer`。诊断工具(dev-only,临时 pip 装,不写进任何依赖声明):`vulture`、`coverage`。

> **环境说明:** 本仓库 harness 的 shell 是 **bash**(Windows 上的 Git-bash),不是 PowerShell —— `for`/`grep`/`sed`/`xargs` 可用。但 baseline 分析仍统一用 **Python stdlib 脚本**(可复核、确定性、跨平台、避免 coverage 在根目录落 `.coverage`),不用临时 bash 管道。

---

## 仓库真实画像(2026-06-08 侦察,执行时以实际为准)

- **316 tracked 文件**:112 `.py`(51 `src/werewolf_eval/`、53 `tests/test_*.py`、其余 `scripts/`+`tools/`+根 launcher)、**106 `.md`**、38 `.qml`、33 `.json`、5 `.cpp`/3 `.h`、8 `.html`。
- **`src/werewolf_eval/` 51 模块,零外部依赖(纯 stdlib)。** 框架手写。
- **10 个 `run_*` 入口**(死代码头号嫌疑,多为迭代变体):`run_mock_game`、`run_scripted_game`、`run_fake_provider_game`、`run_g1h_fake_runtime`、`run_emergent_game`、`run_emergent_fake_runtime`、`run_deepseek_consensus_game`、`run_deepseek_provider_game`、`run_emergent_deepseek_game`、`run_observer_server`。
- **6 `validate_*` + 对应日志/契约模块**(consensus_log/decision_log/failure_audit/game_log/log_bundle/semantic_labels):查是否整组废弃。
- **CI**:`.github/workflows/tests.yml`(push/PR 跑全套 unittest,`PYTHONPATH: src`)。
- **文档**:`docs/harness` 44、`docs/generated-games` 21、`docs/superpowers` 15、`docs/gold-game` 14、`docs/demo` 8 + 根目录权威文档。
- **已有基线**:`docs/RISK_ASSESSMENT_2026-06-06.md`(R-01..38 全闭环)。**Phase 1 必先读它,不重复已闭环 38 项,只报新增/回归/未覆盖。**
- **stale 生成物**:`docs/generated-context/current-task.ctx.md`(untracked)仍指向旧任务 *G2b Task 6*,与本体检无关 —— preflight 必须忽略它,不要被它带偏当前任务。

## 全程铁律(每个 agent 的 system 约束)

1. **Artifact-only。** 唯一允许写入:`docs/HEALTH_CHECK_2026-06-08.md`、`docs/health-check/**`。禁止 Edit/Write/删除其它任何文件;禁止改 `src/`、`tests/`、`clients/`、`scripts/`、`tools/`、CI、根 launcher、任何 `.py`(baseline 脚本除外,它写在 `docs/health-check/_baseline/`);禁止任何 `git` 写操作(commit/checkout/reset/clean)。
2. **保守。** 瘦身只标"候选",按"三连证明"分级(见 Phase 2)。宁漏报不错报"可删"。
3. **未来/在用代码 ≠ 死代码。** 瘦身判定必须用 **`docs/PROJECT_MAP.md`(阶段权威)+ `docs/TASKS.md` + 已合并 PR(`git log`/`gh pr list`)** 三者共同判断,**不能只守 P2-B-2/B-3 几个子任务名**。P2-A/B/C/D 都在当前阶段语境内;memory 记 P2-B-2/B-3 未做、P3 未开始,凡指向未来阶段的未引用代码标 `FUTURE-SCAFFOLD` 不删。
4. **不重复已闭环风险。** Phase 1 以 `RISK_ASSESSMENT_2026-06-06.md` 为基线。
5. **每条发现给证据。** `file:line` + 一句话事实 + 影响 + 风险等级(P0/P1/P2/P3)+ 建议动作。无证据的"感觉"不写。

## 产出物(执行结束时应存在,且 **仅** 这些路径被改动)

- `docs/HEALTH_CHECK_2026-06-08.md` — 主报告(执行摘要 + 三栏汇总 + Top-10 优先动作 + 后续计划顺序)
- `docs/health-check/01-risks-bugs.md` — 风险/bug(分级,已对抗复核)
- `docs/health-check/02-slimming-candidates.md` — 死代码/孤儿文档候选(三连分级,**仅候选**)
- `docs/health-check/03-architecture-optimization.md` — 框架/代码优化机会(带 ADR 草案指针)
- `docs/health-check/_baseline/` — 机器产物(`baseline.py` 脚本 + import-refs / doc-refs / entrypoint-wiring / bigfiles / coverage.txt / vulture.txt),作为报告附件供复核

---

## Phase 0 — Preflight 边界 + 只读地图基线(串行,最先)

### 0.A Preflight(确认起点干净、绑定正确任务)

- [ ] **0.A.1 工作区基线 + 脏路径快照**:`git log --oneline -10`、`git rev-parse HEAD`,并把执行前已存在的改动快照存盘(postflight 据此做差分,避免误报执行前就脏的文件):
```bash
mkdir -p docs/health-check/_baseline
git status --porcelain | awk '{print $2}' | sort -u > docs/health-check/_baseline/preflight-dirty.txt
cat docs/health-check/_baseline/preflight-dirty.txt   # 预期含: 本 plan 文件 + 任何已有 WIP(如 MatchSetupView.qml)
```
工作树**不要求 clean**(本 plan 文件本身就是未跟踪输入);执行前已有的改动属"pre-existing",不归本轮负责,也不得被本轮 agent 触碰或掩盖。
- [ ] **0.A.2 阶段/PR 权威**:读 `docs/PROJECT_MAP.md`、`docs/TASKS.md`;跑 `gh pr list --limit 20 --state all`(**memory 警告:agent shell 的 GitHub egress 不稳定;若 gh 失败,改用 `git log --oneline -40` + PROJECT_MAP/TASKS 推断已合并工作**,不要因此卡住)。这是 Phase 2 脚手架判定的输入。
- [ ] **0.A.3 忽略 stale context**:确认 `docs/generated-context/current-task.ctx.md` 指向旧任务,**本轮任务以本计划为准,不重建、不绑定它**。
- [ ] **0.A.4 建产物目录**:`mkdir -p docs/health-check/_baseline`。

### 0.B 测试绿基线

- [ ] **0.B.1** 跑全套:
```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -25
```
预期全绿(memory ~796 OK)。**若红先记进 `01-risks-bugs.md` 当 P0。** memory 提示:本机 localhost HTTP 被墙,observer-server 的 HTTP 测试本地会 `RemoteDisconnected`,CI(Linux)才真跑;本地这几条红属环境问题,标注即可不算 bug。

### 0.C 纯 Python baseline 脚本(替代所有 bash 管道)

- [ ] **0.C.1** 把下面脚本写到 `docs/health-check/_baseline/baseline.py`(在允许的写入范围内),然后 `python docs/health-check/_baseline/baseline.py`。它只读源码、只写 `_baseline/` 下的 txt,**不依赖任何第三方库**:

```python
#!/usr/bin/env python3
"""Read-only health-check baseline. Writes only into its own _baseline/ dir."""
import re, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[3]   # repo root
OUT  = pathlib.Path(__file__).resolve().parent
def tracked(*globs):
    out = subprocess.run(["git","ls-files",*globs], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return [ROOT / p for p in out]

# --- import-refs: 每个 src 模块被多少 src/tests/scripts/tools 文件引用 ---
src_mods = [p.stem for p in tracked("src/werewolf_eval/*.py") if p.stem != "__init__"]
scan = tracked("src/werewolf_eval/*.py","tests/*.py","scripts/**/*.py","tools/*.py") + [ROOT/"launch-theater.py"]
texts = {p: p.read_text(encoding="utf-8", errors="ignore") for p in scan if p.exists()}
rows = []
for m in src_mods:
    pat = re.compile(rf"(import\s+\w*\b{m}\b|from\s+\S*\b{m}\b\s+import|werewolf_eval\.{m}\b|[\"']{m}[\"'])")
    refs = sum(1 for p,t in texts.items() if p.stem != m and pat.search(t))
    rows.append((refs, m))
(OUT/"import-refs.txt").write_text(
    "\n".join(f"{r:3d}  {m}" for r,m in sorted(rows)), encoding="utf-8")

# --- entrypoint wiring: 10 个 run_* 被哪些 launcher/doc/test 提到 ---
entry = ["run_mock_game","run_scripted_game","run_fake_provider_game","run_g1h_fake_runtime",
         "run_emergent_game","run_emergent_fake_runtime","run_deepseek_consensus_game",
         "run_deepseek_provider_game","run_emergent_deepseek_game","run_observer_server"]
wire_scan = tracked("*.py","*.bat","*.md","scripts/**/*.py","tools/*.py","tests/*.py","docs/**/*.md")
wtext = {p: p.read_text(encoding="utf-8", errors="ignore") for p in wire_scan if p.exists()}
lines = []
for e in entry:
    hits = [str(p.relative_to(ROOT)) for p,t in wtext.items()
            if p.name != f"{e}.py" and e in t]
    lines.append(f"=== {e} ({len(hits)} refs) ===\n  " + "\n  ".join(hits) if hits
                 else f"=== {e} (0 refs) ===  <-- STRONG DEAD CANDIDATE")
(OUT/"entrypoint-wiring.txt").write_text("\n".join(lines), encoding="utf-8")

# --- doc-refs: 每个 .md 被多少其它 md/py/json 引用(找孤儿文档) ---
mds = tracked("*.md","docs/**/*.md")
allscan = tracked("*.md","docs/**/*.md","*.py","src/**/*.py","tests/*.py","scripts/**/*.py","*.json","docs/**/*.json")
atext = {p: p.read_text(encoding="utf-8", errors="ignore") for p in allscan if p.exists()}
drows = []
for f in mds:
    base = f.name
    refs = sum(1 for p,t in atext.items() if p != f and base in t)
    drows.append((refs, str(f.relative_to(ROOT))))
(OUT/"doc-refs.txt").write_text(
    "\n".join(f"{r:3d}  {f}" for r,f in sorted(drows)), encoding="utf-8")

# --- bigfiles: src 模块行数倒序(职责过载候选) ---
bf = sorted(((len(p.read_text(encoding='utf-8',errors='ignore').splitlines()), p.stem)
             for p in tracked("src/werewolf_eval/*.py")), reverse=True)
(OUT/"bigfiles.txt").write_text(
    "\n".join(f"{n:5d}  {m}" for n,m in bf), encoding="utf-8")
print("baseline written to", OUT)
```

- [ ] **0.C.2 覆盖率**(coverage 文件落 `_baseline/`,**不污染根目录**):
```bash
pip install coverage vulture            # dev-only,不写进任何依赖声明
export COVERAGE_FILE=docs/health-check/_baseline/.coverage
PYTHONPATH=src python -m coverage run -m unittest discover -s tests -p "test_*.py"
python -m coverage report -m > docs/health-check/_baseline/coverage.txt
unset COVERAGE_FILE
vulture src/werewolf_eval --min-confidence 80 > docs/health-check/_baseline/vulture.txt 2>&1 || true
```
> `_baseline/.coverage` 是机器产物,属报告附件;若不希望进 git,在报告里注明可加 `.gitignore`(本轮不改 .gitignore)。

---

## Phase 1 — 风险/bug 扫描(并行 + 对抗复核)【先于瘦身】

**输出 `01-risks-bugs.md`。先读 `docs/RISK_ASSESSMENT_2026-06-06.md`,只报新增/回归/未覆盖项。** 按**模块簇 × 维度**扇出:

1. **引擎核心**:`emergent_engine`、`game_engine`、`scripted_game`、`seat_agents`、`runtime_events`
2. **计分/归因**:`scoring`、`score_game`、`attribution`、`attribute_game`、`decision_log`、`consensus_log`、`failure_audit`、`settlement_bundle`
3. **Provider/凭证(安全敏感)**:`llm_providers`、`provider_*`、`deepseek_provider`、`*_launcher`、`credential_store`、`profile_config`
4. **Observer 服务/可见性(安全敏感)**:`observer_server`、`observer_protocol`、`observer_visibility` + Qt C++ `clients/qt_observer/src/*.cpp`
5. **渲染/标签/日志**:`render_*`、`*_labels`、`game_log`、`log_bundle`、`validate_*`
6. **Qt 观战/结算 UI(QML,P2-C/P2-D 重灾区)**:`clients/qt_observer/qml/**`(`TheaterView`/`SettlementView`/`LiveCockpitView` + `components/*`)—— 查:静态契约(已有 `tests/test_qt_observer_static_contract.py` 作基线)、状态绑定错误、空状态/遮挡/假数据残留、degraded/降级态渲染、i18n 漏译。

维度(每簇都过):正确性 bug、安全(凭证泄漏/路径穿越/可见性不变量/狼人快照泄漏)、错误处理与边界、并发(`threading` 用法)、契约/不变量回归。

- [ ] 每簇派 finder agent,带 `RISK_ASSESSMENT` 基线,产结构化 findings(`file`,`line`,`type`,`severity`,`evidence`,`repro/推理`)。
- [ ] **对抗复核**:每条 finding 派 ≥2 个 skeptic agent,默认 `refuted=true`,要求反驳/确认能否真实复现;多数确认才入最终清单。剔除"看似 bug 实为设计"误报。
- [ ] Qt C++:`CredentialStore`/`ObserverApiClient`/`ObserverSseParser` 做内存/解析边界检查(`tst_observer_sse_parser.cpp` 之外)。
- [ ] 分级 P0(破功能/安全)→P3,输出表。

## Phase 2 — 瘦身/死代码候选(读 Phase 0 baseline + Phase 1 风险结果)

**输出 `02-slimming-candidates.md`,只产候选,不删。** 每候选打"三连证明"等级:

| 等级 | 含义 | 判据 |
|---|---|---|
| `DEAD-CONFIRMED` | 三连全过,可安全删 | import-refs=0 **且** coverage=0/无测试 **且** entrypoint-wiring=0 **且** git log 最后改动久远 **且** 非 `FUTURE-SCAFFOLD` **且** 非 Phase 1 标了未修 bug 的活模块 |
| `DEAD-LIKELY` | 多数证据指向死,一项存疑 | 任一条不满足但其余强 |
| `FUTURE-SCAFFOLD` | 未引用但是未来阶段地基 | 按铁律 #3,PROJECT_MAP+TASKS+PR 指向 P2-B-2/B-3/P3 → **明确不删** |
| `KEEP` | 看似冗余实在用(动态调用/反射/CLI) | 复核发现间接引用 |

- [ ] 候选来源逐项过:`import-refs.txt`(refs=0)∩ `coverage.txt`(0%)∩ `entrypoint-wiring.txt`(0 refs)→ 最强候选;`vulture.txt` 死函数单列;每个候选派 agent 复核动态/字符串引用(`getattr`/`importlib`/配置里的模块名)再定级。
- [ ] **`validate_*`/日志 6 组**整组判断是否已被新链路取代。
- [ ] **孤儿文档**(读 `doc-refs.txt` refs=0):
  - **排除** 权威文档(`PROJECT_MAP`/`ROADMAP`/`README`/`AGENTS`/`RISK_ASSESSMENT`/`TASKS`/`PRODUCT_ONE_PAGER` 等)。
  - **`docs/superpowers/{specs,plans}` 是 tracked 设计/spec 归档,被 `TASKS.md` 引用(如 `TASKS.md:229` → `docs/superpowers/specs/2026-06-04-...`)→ 默认 `KEEP`**,不是 skill cache,不建议 gitignore;只在确认某篇 spec 对应任务已废弃且无引用时才标候选。
  - 真正的历史产物候选重点查:`docs/generated-games`(21)、`docs/gold-game`(14)、`docs/demo`(8)—— 判断是 fixture(被测试/render 引用→KEEP)还是一次性快照。
- [ ] 输出表:`路径 | 等级 | 证据(refs/cov/wiring/last-commit/PR) | 建议动作`。

## Phase 3 — 框架/代码优化机会

**输出 `03-architecture-optimization.md`。** 用 `improve-codebase-architecture` 思路:读 `docs/PROJECT_MAP.md` 领域语言 + `docs/adr`(**只有 1 个 ADR —— ADR 稀薄本身是一条发现**)。聚焦:

- [ ] **无 packaging**:无 `pyproject.toml`/依赖声明/`conftest.py`,靠 `PYTHONPATH=src` 手接 → 评估是否引入 `pyproject.toml`(影响可测性/可装性,既是优化也是风险)。
- [ ] **`run_*` 入口爆炸**(10 个):是否收敛成单一 CLI 子命令。
- [ ] **重复/可复用**:provider 这块 memory 称已 registry 单源 + 复用 OpenAIProvider,核对残留重复;`validate_*` 6 组能否抽象。
- [ ] **大文件/职责过载**:读 `_baseline/bigfiles.txt`,顶部超大模块评估拆分。
- [ ] **可测性**:`coverage.txt` 里零覆盖且非死代码的模块 = 缺测试(列入)。
- [ ] 每条标:收益 / 工作量 / 风险 / 是否需先写 ADR。**不在本轮实施**,只产清单 + ADR 草案指针。

## Phase 4 — 综合报告

- [ ] 汇总三份子报告 → `docs/HEALTH_CHECK_2026-06-08.md`:执行摘要、三栏统计、**Top-10 优先动作**(跨栏按收益/风险比排序)、建议的后续执行计划顺序(bug 修复 → 保守瘦身 → 优化,各自独立成 plan)。
- [ ] **完整性 critic agent**:问"哪个模块簇没扫?哪条 finding 没复核?哪个候选没定级?"补齐。

### Postflight 边界校验(收尾必做)

- [ ] **按 preflight 快照做差分**(不拿空基线比):本轮"新增/变化路径" = 当前脏路径 **减去** `_baseline/preflight-dirty.txt`。这些 net-new 路径**必须全部落在** `docs/HEALTH_CHECK_2026-06-08.md` 或 `docs/health-check/`:
```bash
git status --porcelain | awk '{print $2}' | sort -u > /tmp/postflight-dirty.txt
# 本轮净新增/变化(排除执行前已脏的)
comm -13 docs/health-check/_baseline/preflight-dirty.txt /tmp/postflight-dirty.txt > /tmp/net-new.txt
# 越界 = net-new 中不在 allowlist 内的
grep -vE '^docs/(HEALTH_CHECK_2026-06-08\.md|health-check/)' /tmp/net-new.txt || echo "OK: no out-of-scope changes"
```
任何越界路径 = 违反 artifact-only,在报告顶部红字标注并列出,**不要自行 `git checkout` 掩盖**(交用户处理)。报告中**单独列出** pre-existing dirty 路径(`preflight-dirty.txt`),声明本轮未触碰它们。
- [ ] 确认根目录无新增 `.coverage`、`.pytest_cache` 等游离产物(coverage 已重定向到 `_baseline/`)。

---

## 建议的 Workflow 扇出结构(给 ultracode 执行会话)

```
phase('Phase 0 Preflight+基线') → 1 agent 顺序跑 0.A–0.C(preflight + baseline.py + coverage/vulture)
phase('Phase 1 风险')  → pipeline(6 模块簇,
                           finder(簇×维度) → parallel(≥2 skeptic 对抗复核) )  // 读 RISK 基线
phase('Phase 2 瘦身')  → pipeline(候选, 复核定级)   // 读 _baseline + Phase 1 风险结果
phase('Phase 3 优化')  → parallel(packaging / 入口收敛 / 重复 / 大文件 / 可测性 5 路)
phase('Phase 4 综合')  → 1 synthesis agent + 1 完整性 critic + postflight 校验
```
- finder/skeptic 用 `schema` 强制结构化输出(findings 数组:`file`,`line`,`type`,`severity`,`evidence`,`verdict`)。
- Phase 1 用 `pipeline`(finder 一出就复核,不等其它簇)。Phase 2 依赖 Phase 0 全部产物 + Phase 1 风险结果。
- `agentType: 'code-reviewer'` 适合 Phase 1 finder;`'Explore'` 适合 Phase 0/2 搜索;`improve-codebase-architecture` 思路用在 Phase 3。
- **每个 agent 的 prompt 必须重申铁律 #1(artifact-only 写入范围)**,防止子 agent 越界改源码。
- 规模随"全面"诉求放大:每簇 finder 1、skeptic 2–3。

## 明确不在本轮范围

- ❌ 不删任何代码/文档(连"确认死"的也不删 —— 留给后续保守瘦身计划)。
- ❌ 不做任何重构/优化实施;不改 CI、`.gitignore`、git 历史。
- ❌ 不重建/绑定 `current-task.ctx.md`。
- ✅ 只产报告 + 候选清单 + ADR 草案指针 + baseline 附件,交用户逐条决策。

## 自检(已过)

- 阶段顺序 = baseline → **bug/风险 → 瘦身** → 优化 → 综合,与"先 bug 后瘦身"原则一致 ✅
- Artifact-only 写入 allowlist + preflight(git/PR/stale-context)+ postflight(diff/forbidden-scope)齐备 ✅
- baseline 改纯 Python stdlib 脚本,`COVERAGE_FILE` 重定向、先 `mkdir` ✅
- `docs/superpowers` 按 tracked 设计归档处理(默认 KEEP,非 gitignore)✅
- 脚手架判定用 PROJECT_MAP + TASKS + PR,非只守子任务名 ✅
- QML(Phase 1 簇 6)纳入风险扫描 ✅
- baseline 用 `git ls-files 'src/werewolf_eval/*.py'`(已验证 pathspec `*` 匹配 `/`,不漏)✅

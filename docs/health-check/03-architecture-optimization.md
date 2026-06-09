# 03 — Architecture & Optimization Opportunities

> **本轮不实施任何重构/优化。** 这是 ARTIFACT-ONLY 只读诊断。本文件只产出
> *机会清单 + ADR 草案指针*。没有任何 `src/` `tests/` `clients/` `scripts/`
> `tools/` 改动落地;所有"工作量/风险/是否需先写 ADR"均为**计划项**,留待后续
> 独立的、可写代码的切片去执行。文中给出的 `file:line` 均针对 worktree 快照
> `worktree-health-check-2026-06-08`(基于 `1d721fd`)。
>
> **基线衔接:** `docs/RISK_ASSESSMENT_2026-06-06.md`(R-01..38)已全闭环。本文
> 只报*新增的结构性优化机会*,不复述那 38 项。凡引用到既有风险编号(R-06/R-08/
> R-17/R-35 等)仅作为"该机会与既闭环项的关系",非重复上报。
> **环境注意:** 本机 localhost HTTP 被墙,observer 的 47 个 HTTP 测试错误是环境
> 问题不是 bug,本文不据其下任何结论;coverage 类指标须读 CI(Linux)。

每个领域按下列字段成条:**机会 · 证据(file:line)· 收益 · 工作量 · 风险 ·
是否需先写 ADR(+草案标题)**。工作量记号:S=小(单文件/无代码改动)、
M=中(跨文件、需小重构)、L=大(跨模块、需协调与回归)。

---

## 1. Packaging — 打包 / 可安装性

整个仓库**没有任何 `pyproject.toml` / `setup.py` / `setup.cfg` /
`requirements.txt`**(`git ls-files` 全仓零命中)。`src/werewolf_eval/` 已是干净的
src-layout 包,但从未被声明为可安装,导致 `PYTHONPATH=src` 被手工穿线进 CI、
文档、批处理、launcher 等多处。这是本领域所有机会的共同根因。

### P-1 · 引入最小 `pyproject.toml`(src-layout),让包可安装、停止手工穿 PYTHONPATH

- **机会:** 用一份 ~15 行 PEP 621 `pyproject.toml`(`[build-system]` +
  `[project]` name/version + `[tool.setuptools] package-dir=src`)让
  `pip install -e .` 生效,从此 tests/CI/launcher/下游消费者用同一机制解析
  `werewolf_eval`,不再各自设环境变量。
- **证据:** 仓库无任何打包清单(`git ls-files` 对 pyproject/setup/requirements
  零命中);包根 `src/werewolf_eval/__init__.py:1` 已就绪但从未声明为可安装;
  `PYTHONPATH=src` 至少被手工穿线进 `.github/workflows/tests.yml:23`、
  `AGENTS.md:85`、`live-check.bat:4`、`launch-theater.py:97`、
  `tools/live_check_deepseek.py:57`。
- **收益:** 单一包身份真相源;`pip install -e .` 后所有入口/测试一致解析,消除
  环境 hack;为未来 `python -m build`/wheel(Qt-bundle 分发故事)解锁。
- **工作量:** **S** — 单个新文件,无需改代码(包已是干净 src-layout)。验证:
  `pip install -e . && python -m unittest discover -s tests`。
- **风险:** **低**。加文件本身非破坏性(旧 `PYTHONPATH=src` 仍可用)。真正风险是
  *半迁移*:若加了 pyproject 但 CI/launcher 仍设 `PYTHONPATH=src`,就出现两套
  竞争的导入机制、可能掩盖坏掉的安装。缓解:在**同一改动**里把 pyproject 与
  CI/launcher 切到 editable-install 一并落地,或明确推迟切换并留 TODO。
- **需先写 ADR:** ✅ **是**
  - 草案:**ADR 0002 — Adopt src-layout `pyproject.toml` as the single
    package/import contract (editable install replaces ad-hoc `PYTHONPATH=src`)**

### P-2 · 显式声明 `requires-python` 与运行时依赖策略(目前只有未文档化的 CI pin)

- **机会:** 在 pyproject 写 `requires-python = ">=3.12"` 与显式
  `dependencies = []`,把当前隐含的"纯 stdlib、无需安装"不变量落到纸面。
- **证据:** CI 在 `.github/workflows/tests.yml:20`(`python-version: "3.12"`)
  pin 了 3.12,但**全仓无 `requires-python` 声明**,README/AGENTS/PROJECT_MAP 均无
  Python 版本或依赖说明;对 src/tests/scripts/tools/clients 的 import 扫描显示运行时
  为**纯 stdlib**(json/urllib/http/dataclasses/typing/argparse…),零第三方包 ——
  例如 `llm_providers.py:26` 用 `urllib.request` 而非 `requests`。
- **收益:** 文档化(目前隐含的)"stdlib-only, 无需安装"不变量;防止有人用
  3.10 不兼容语法或随手加 `import requests` 造成静默破坏;告诉后来者门槛是
  "加依赖要刻意",而非"在我机器上能跑"。
- **工作量:** **S** — P-1 那份 pyproject 里两行,无单独文件。发布版本下限前先用
  import 扫描复核 stdlib-only 仍成立。
- **风险:** **低**。唯一隐患是过度 pin(如 `==3.12`),用与 CI 对齐的下限
  `>=3.12`。`dependencies=[]` 今天准确,但成为"加第一个真依赖那天"的维护触点。
- **需先写 ADR:** ❌ 否(并入 P-1 的 ADR 0002)

### P-3 · 统一测试导入路径,退掉 26 个测试文件里重复的 `sys.path.insert` 样板与两套策略并存

- **机会:** editable install(P-1)后,`werewolf_eval` 对每个测试都可导入(与 cwd/
  env 无关),可删掉 26 块样板,并让 ~27 个"仅靠 env"的测试停止成为静默地雷。
- **证据:** 53 个测试文件中 **26 个**重复同一块
  `ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'src'))`
  (如 `tests/test_emergent_engine.py:8-9`、`tests/test_scoring.py:10`、
  `tests/test_game_engine.py:11`);其余 ~27 个(如 `tests/test_observer_server.py`、
  `tests/test_consensus_log.py`)**无 sys.path 行**,纯靠 `AGENTS.md:85` /
  `tests.yml:23` 设的环境 `PYTHONPATH=src` —— 于是套件存在**两套不一致的导入策略**,
  第二组里任一文件单独跑(不设 env)即失败。(本机实测:53 个测试文件,26 个含
  `sys.path.insert`,无 `conftest.py`。)
- **收益:** editable install 后无关 cwd/env 都可导入,26 块样板可删,~27 个 env-only
  测试不再是"单跑即炸"的脚枪;统一、env-无关的测试改善 AI 可导航性,允许贡献者
  直接跑单个文件。
- **工作量:** **M** — 删 26 块是机械活但触及 `tests/`(本轮只读、禁改;须作为独立的
  可写切片)。**注意 runner 是 stdlib `unittest`(`python -m unittest discover`,
  见 `tests.yml:24`/`AGENTS.md:85),不是 pytest** —— 所以加 `conftest.py`
  对 unittest discover **无效**,正解是 editable-install + 删样板。
- **风险:** **中(方向性)**。pytest conftest 对 `unittest discover` 不起作用;选
  conftest 等于隐含改 runner(unittest→pytest),是更大决策。若不先用 install 统一
  导入路径就去搅 26 个文件,收益边际而 churn 大。
- **需先写 ADR:** ✅ **是**
  - 草案:**ADR 0003 — Unify test import path via editable install (delete
    per-file `sys.path.insert`); decide unittest-vs-pytest before adding any
    `conftest.py`**

### P-4 · 把 10 个 `run_*.py` launcher 声明为 console entry-points,而非按文件/路径调模块

- **机会:** pyproject 落地后,用 `[project.scripts]`(如
  `werewolf-observer = werewolf_eval.run_observer_server:main`)给出稳定、env-无关、
  跨 OS 的命令,移除 Windows-only 的 `.bat` PYTHONPATH 包装与 taskkill-by-port 脆弱性。
- **证据:** `src/werewolf_eval/run_*.py` 命中 **10 个**模块(run_emergent_game、
  run_emergent_deepseek_game、run_observer_server、run_emergent_fake_runtime、
  run_deepseek_consensus_game 等),都是事实上的 CLI 入口;今天只能经
  `PYTHONPATH=src` + `python …` 触达(`launch-theater.py:97` 先设 PYTHONPATH 再 shell
  python;`live-check.bat:4` 设 `PYTHONPATH=src`)。无 `[project.scripts]` 映射(因
  无 pyproject)。
- **收益:** `pip install -e .` 后给出稳定、env-无关命令;移除 .bat 包装与 memory 里
  记的 taskkill-by-port 脆弱性;利于未来打包/可分发产物。
- **工作量:** **M** — 需要每个选中的 launcher 暴露干净的 `main()`;部分 `run_*` 模块
  可能在模块级而非 `if __name__`/`main()` 守卫下做工作,需先小重构(逐文件核实,属
  代码改动,本轮范围外)。scripts 表本身 trivial。
- **风险:** **中**。entry-points 假定包已安装;若同时仍用裸路径调 launcher 会漂移。
  部分 `run_*` 可能要先重构成干净 main()。正确性风险低,协调风险中。
- **需先写 ADR:** ❌ 否(依赖 P-1;命名 taxonomy 见 entrypoints 领域 E-1 的 ADR 0002)

### P-5 · 在打包同一改动里补 build-artifact 忽略(egg-info/dist/build/.venv),保持仓库干净

- **机会:** 预先把 `*.egg-info/` `build/` `dist/` `.venv/` 加进 `.gitignore`,防止
  采用打包后误提交 editable-install 元数据与 wheel。
- **证据:** `.gitignore` 当前忽略 `__pycache__/`、`*.pyc`、`.runs/`、`profiles/`、
  `clients/qt_observer/build/` 等,但**无** `*.egg-info/` `dist/` `build/` `.venv/`
  条目(本机实测:`.gitignore` 中 egg/dist/venv 唯一命中是
  `clients/qt_observer/build/:37`)。这些目录尚不存在,正因当前无可安装产物;一旦
  `pip install -e .` 或 `python -m build` 就会出现。
- **收益:** 廉价保险,让打包改动成为净清理而非噪声源;避免常见的首-PR 误提交。
- **工作量:** **S** — 向 `.gitignore` 追加 ~4 行;仅在引入 pyproject 的同一改动里做才有价值。
- **风险:** **低**。纯增量忽略规则;唯一失败模式是漏写某个生成器目录名,易修正。
- **需先写 ADR:** ❌ 否

---

## 2. Entrypoints — 入口拓扑

10 个 `run_*` 各自独立 `main()`+argparse,无 console_scripts,全靠
`python -m werewolf_eval.run_<x>` 调用;它们之间还有大量逐字复制的辅助函数。

### E-1 · 把 10 个 `run_*` 收敛成一个 `werewolf` CLI(argparse 子命令,单一调度面)

- **机会:** 一个 `werewolf <verb>` 面(如 `serve`、`emergent --fake|--live`、
  `fixture mock|scripted`)取代 10 个需记忆的模块名;run-mode 分类(fake/live/legacy/
  observer)从部落知识变为 `--help` 可发现。
- **证据:** `run_mock_game.py:23`、`run_scripted_game.py:21`、
  `run_fake_provider_game.py:55`、`run_emergent_game.py:39`、
  `run_g1h_fake_runtime.py:201`、`run_emergent_fake_runtime.py:175`、
  `run_deepseek_provider_game.py:156`、`run_deepseek_consensus_game.py:260`、
  `run_emergent_deepseek_game.py:207` 各自定义独立 `main()`+`argparse.ArgumentParser`;
  无 pyproject/console_scripts;baseline 列出 10 个不同 `run_*` 引用簇
  (`docs/health-check/_baseline/entrypoint-wiring.txt`)。
- **收益:** 单一 `werewolf <verb>` 面取代 10 个模块名;run-mode taxonomy 经 `--help`
  可发现;AI 只读一个入口文件而非 10 个近似副本;可纯增量地让子命令委托给现有
  `run_*_with_provider_factory` 接缝(`run_deepseek_consensus_game.py:73`、
  `run_emergent_deepseek_game.py:126`),迁移期间保留 shim 让现有 `python -m` 调用不破。
- **工作量:** **L**
- **风险:** **行为性**。测试与 `launch-theater.py:132` / `tools/live_check_deepseek.py:88`
  调 `python -m werewolf_eval.run_observer_server`,4 个测试 subprocess 调
  `python -m werewolf_eval.run_<x>`(`test_deepseek_provider_game.py:76`、
  `test_deepseek_consensus_game.py:138`、`test_fake_provider_game.py:17`、
  `test_run_emergent_game.py:17`)。删旧模块名会破这些调用方,故须保留模块 shim 或
  逐一更新调用点。arg 名漂移(有的用 `--out-dir`,有的用
  `--game-log-out`/`--decision-log-out`)意味着按子命令分 arg 组,而非一个扁平 schema。
- **需先写 ADR:** ✅ **是**
  - 草案:**ADR 0002 — Single `werewolf` CLI with argparse subcommands as canonical
    entrypoint(supersedes ad-hoc `run_*` modules; defines fake/live/legacy/observer
    verb taxonomy and back-compat shim policy)**
  - *注:此 ADR 0002 与 packaging P-1 的 ADR 0002 是同一编号的两个候选。落地时须二选一
    编号或合并叙事 —— 建议把 packaging 契约与 CLI taxonomy 写进同一份 ADR 0002,因为
    `[project.scripts]` 与 `werewolf` CLI 是同一决策的两面。*

### E-2 · 抽出复制 9 份的 `_write_json` artifact writer 为单一共享 helper

- **机会:** 把逐字近似的 `_write_json(path, payload)`(mkdir parents +
  `json.dumps(ensure_ascii=False, indent=2)` + 末尾换行 + utf-8)抽进一个共享模块。
- **证据:** 该函数出现在 `run_mock_game.py:14`、`run_scripted_game.py:14`、
  `run_fake_provider_game.py:20`、`run_emergent_game.py:33`、
  `run_g1h_fake_runtime.py:67`、`run_emergent_fake_runtime.py:48`、
  `run_deepseek_provider_game.py:23`、`run_deepseek_consensus_game.py:30`、
  `run_emergent_deepseek_game.py:39`(**9 份副本**;本机 grep 确认 9 个 run_* 含
  `_write_json`)。
- **收益:** artifact-write 契约(原子性/编码/末尾换行)的单一真相源;RISK_ASSESSMENT
  R-08 已在别处强制原子写,共享 writer 是统一强制的天然落点,而非 9 处可各自漂移;
  消除"哪个 writer 是 canonical"的提问。
- **工作量:** **S** — 机械抽取到如 `werewolf_eval/cli_io.py`;签名已一致(唯一差异是
  `str` vs `str|Path`)。若函数体逐字保留则零行为变化,各入口测试仍过(输出字节不变)。
- **风险:** **低**。
- **需先写 ADR:** ❌ 否

### E-3 · 抽出复制 6 份的 `_collect_trace` provider-trace 汇总(其中一份已静默漂移)

- **机会:** 把"按 request_id 去重 requests/responses、跨 agent 合成 ProviderTrace"统一
  为一个 helper,顺手修掉已存在的不一致。
- **证据:** `_collect_trace` 在 `run_fake_provider_game.py:29`、
  `run_g1h_fake_runtime.py:75`、`run_emergent_fake_runtime.py:53`、
  `run_deepseek_provider_game.py:32`、`run_deepseek_consensus_game.py:39`、
  `run_emergent_deepseek_game.py:82` 各自重写(本机 grep 确认 6 个 run_* 含
  `_collect_trace`)。`run_fake_provider_game.py:29` 那份**不按 request_id 去重**(纯
  extend),其余五份去重 —— **一处已存在的静默分歧,证明 copy-paste 风险是真的**。
- **收益:** 单一 trace-assembly 契约消除已存在的不一致(未去重的 fake 变体),并保证
  未来 trace 消费者看到相同汇总语义;直接为 BYO-key 多供应商路径(`run_emergent_
  deepseek_game.py:82` 是 live 多供应商变体)的 per-seat trace 正确合并降风险。
- **工作量:** **S** — 函数体略有差异(provider_name/source_label 是参数;
  fake_provider_game 还折入一个独立 wolf_agent)。共享 helper 须把 provider_name/
  source_label/agents-iterable 作参数,wolf_agent 放进 agents 列表传入。各文件现有
  trace 断言可覆盖。
- **风险:** **低-中**。
- **需先写 ADR:** ❌ 否

### E-4 · 统一三份 DeepSeek CLI 里三胞胎的 live-API 闸门 + 从环境取 key 前置序

- **机会:** 把"--allow-live-api 闸门 → 从 env 取 key 的缺失检查 → build-factory-and-run"
  这套安全敏感序列从三处折叠为一个被测 helper。
- **证据:** 相同序列复制在 `run_deepseek_provider_game.py:169-195`、
  `run_deepseek_consensus_game.py:274-304`、`run_emergent_deepseek_game.py:222-242`。
  工厂构建器 `_build_deepseek_agent`(`run_deepseek_provider_game.py:137`、
  `run_deepseek_consensus_game.py:243`)与 `_deepseek_factory`
  (`run_emergent_deepseek_game.py:194`)是近似重复的 shared-DeepSeekProvider 构造器。
- **收益:** 把三份"从 env 读一次 key、永不打日志、闸于 `--allow-live-api`"的安全契约
  (正是 RISK_ASSESSMENT 标注的 key 处理模式)收成一处被测 helper;一处审计取代三处;
  未来 provider(BYO-key 多供应商方向)的单一插入点。`deepseek_launcher.py:63` 已为
  server 路径集中了共享-provider 工厂,CLI 副本是掉队者。
- **工作量:** **M** — 这些是 live(联网、带 key)路径;其离线测试注入 `provider_factory`
  接缝,抽出的 helper 须保留它。默认值不同(max-provider-requests 11 vs 12 vs 64;
  consensus 用 `g1f_provider_consensus` 模式),helper 须把 per-CLI 默认作参数,不可写死。
- **风险:** **中**(live 带 key 路径)。
- **需先写 ADR:** ❌ 否

### E-5 · 厘清重叠的 fake-emergent 入口:裸 `run_emergent_game.py` vs 接 spine 的 `run_emergent_fake_runtime.py`

- **机会:** 要么把 `run_emergent_game` 折成 spine runner 的 `--no-spine` 旗标,要么在其
  docstring 标 **LEGACY**(像 `run_mock_game.py:1`/`run_scripted_game.py:1` 已做),
  以免读者误把裸 CLI 当产品路径。
- **证据:** `run_emergent_game.py:39` 与 `run_emergent_fake_runtime.py:175` 都跑
  fake-deterministic emergent game,旗标重叠(`--game-id`/`--script`/`--seed`/
  `--max-requests`/`--max-day-rounds`)。`run_emergent_fake_runtime.py:7-8` docstring 明说
  `run_emergent_game.py` "deliberately does NOT wire the writer",故裸 CLI 出 log 但无
  observer spine,且只被它自己的测试 `test_run_emergent_game.py:17` 引用。产品路径用
  `run_emergent_fake_runtime` 的 `default_emergent_fake_launcher`
  (`run_observer_server.py:16`)。
- **收益:** 移除第二个"哪个 emergent runner 是 canonical"分叉;降低 E-1 收敛目标的导航成本。
- **工作量:** **S** — `run_emergent_game.py` 仅 `test_run_emergent_game.py` 一个调用方;
  docstring-LEGACY 标记零行为;折成旗标也有界。唯一待定是产品意图(是否保留一个无
  spine 的快速 log-only CLI?),那是 PROJECT_MAP 里一行决策注,而非静默删除。
- **风险:** **低**。
- **需先写 ADR:** ❌ 否

---

## 3. Duplication — 重复 / 已漂移项

本领域含**一条潜在正确性陷阱**(D-1,budget 子串错配),应优先处理。

### D-1 · `deepseek_launcher.py` 里两个 budget-failure 检测器分歧 —— `_classify_failure` 对 emergent 路径匹配了**错误的子串**

- **机会:** 把两个 helper 合并为单一的*结构化字段*检测器(`kind=="budget_exhausted"`),
  删掉 `_classify_failure` 的子串分支,把 legacy 单供应商 launcher 指过去。
- **证据:** `deepseek_launcher.py:74-85`(`_classify_failure` 匹配 reason 子串
  **`"budget exceeded"`**,本机实测在 line 83)vs `deepseek_launcher.py:136-154`
  (`_audit_is_budget_exhausted` 匹配结构化 `kind=="budget_exhausted"`,line 152)。
  emergent engine 实际同时发出 `kind="budget_exhausted"`(`emergent_engine.py:764`)
  与 reason 字符串 **`"budget exhausted: N/M requests"`**(`emergent_engine.py:140` ——
  注意是 **exhausted** 不是 **exceeded**)。旧 `llm_providers.py:211` 路径抛
  `"request budget exceeded"`。**本机已逐行核实子串错配真实存在。**
- **收益:** 合并为单一结构化检测器消除一个真实潜伏陷阱:`_classify_failure` 的
  `"budget exceeded"` 子串会**静默漏掉** emergent engine 的 `"budget exhausted"` 措辞,
  于是任何对 emergent audit 复用 `_classify_failure` 都会把 budget-exhausted 误判为
  generic provider_failure(exit 2 而非 3)。一个检测器 = 一处守住 exit-code 契约。
- **工作量:** **S** — 抽出单一 `budget_exhausted_from_audit(path)->bool`(键于结构化
  `kind` 字段),删掉 `_classify_failure` 的子串分支,把 legacy 单供应商 launcher 指过去。
  净删 ~15 行;现有 launcher 测试可覆盖。
- **风险:** **低** — 结构化-kind 检测器是更严格/正确的那个,且已被 3 个 launcher 中的 2 个
  使用;改动只是扩大其使用面。须保证 legacy consensus runner 的 audit 也发出结构化
  kind(合并前核实)。
- **需先写 ADR:** ❌ 否

### D-2 · `deepseek_launcher.py` 三个近似 launcher 构建器重复 run+classify-exit-code 骨架

- **机会:** 抽一个 `_run_and_classify(runner_call) -> int` helper(以及可选的共享
  factory-or-default 解析器),把三条 live 路径锁在 0/2/3 退出码契约上同步。
- **证据:** `deepseek_launcher.py:88-128`(`build_deepseek_launcher`)、`157-201`
  (`build_emergent_deepseek_launcher`)、`204-248`(`build_multi_provider_launcher`)
  共享同一闭包形状(调 runner,`if code==0: return 0`,否则 budget-exhausted→3 /
  其他→2)。emergent 与 multi-provider 变体的尾部逐字相同(195-199 vs 242-246)。
- **收益:** 移除 ~30 行重复,保证三条 live 路径在 observer-facing 退出码契约(0/2/3)上
  同步;今天改退出映射须在 2-3 处手工同步。
- **工作量:** **M** — 把 run 后分类抽成一个 helper;run 前的工厂接线 per-launcher 不同
  (shared DeepSeek vs per-seat seat_agents),只有尾部能整合,整个 builder 不能。
- **风险:** **低-中**(live 入口;须保留各 runner 精确签名/kwargs,只在现有
  multi_provider + emergent launcher 测试下安全)。
- **需先写 ADR:** ❌ 否

### D-3 · `DeepSeekProviderConfig` 逐字段复制 `ChatProviderConfig` —— 仅为向后兼容保留的第二个 config dataclass

- **机会:** 把 `DeepSeekProviderConfig` 折成 `ChatProviderConfig` 之上的薄工厂(或一个
  仅设 deepseek 默认的弃用别名)。
- **证据:** `deepseek_provider.py:27-37`(`DeepSeekProviderConfig`:api_key/base_url/
  model/timeout_seconds/max_tokens/max_requests/persona_prompt/temperature)与
  `llm_providers.py:41-56`(`ChatProviderConfig`)逐字段相同,仅 base_url/model 默认值
  不同。仍在 **4 处**构造:`deepseek_launcher.py:53`、`run_deepseek_consensus_game.py:244`、
  `run_deepseek_provider_game.py:138`、`run_emergent_deepseek_game.py:195`(本机 grep
  确认 1 处定义 + 4 处构造)。
- **收益:** 消除一个 8 字段结构克隆 —— 它每加一个 per-seat 旋钮就要在两个文件改
  (persona_prompt/temperature 已被加了两次,见 `deepseek_provider.py:36-37`);全 provider
  共享单一 config 形状。
- **工作量:** **S-M** — 保留名字 `DeepSeekProviderConfig` 作向后兼容构造器,返回/别名为带
  deepseek 默认的 `ChatProviderConfig`;4 个调用点无需改。现有 deepseek 测试作安全网。
- **风险:** **中** — `deepseek_provider.py` docstring 明确声明 public API
  (`DeepSeekProviderConfig` 名/字段)是该重构的冻结契约;别名须保留任何测试可能断言的
  frozen-dataclass equality/repr。
- **需先写 ADR:** ❌ 否

### D-4 · 单-DeepSeek 路径直接 `DeepSeekProvider()` 构造,绕过 `build_provider` 的 registry 身份戳(并行构造路径)

- **机会:** 把单-DeepSeek 工厂经 `build_provider("deepseek", config)` 路由,让 registry
  成为**所有** live 构造的字面单一真相源。
- **证据:** `run_emergent_deepseek_game.py:199`(`shared = DeepSeekProvider(config)`)与
  `deepseek_launcher.py:66`(`shared_provider = DeepSeekProvider(config)`)直接构造,而
  per-seat 路径 `seat_agents.py:72`(`build_provider(provider_id, config, ...)`)经
  `provider_registry.build_provider`(它从 spec 盖 PROVIDER_NAME/SOURCE_LABEL,
  `provider_registry.py:204-206`)。registry docstring(`provider_registry.py:1-12`)称
  B1/B3 所有 endpoint/auth/base-url 都从这里读。**本机已核实两处直接构造 vs 一处经 registry。**
- **收益:** 让 registry 成为所有 live 构造的字面单一真相源,而非只有 per-seat 路径;移除
  "未来 registry 改动(如 base-url 或 source-label 微调)对单供应商 launcher 静默不生效"
  的风险。今天功能等价(deepseek 类默认已匹配 spec),故是纯整合。
- **工作量:** **S** — 把两处直接 `DeepSeekProvider(config)` 换成 `build_provider("deepseek",
  config)`;唯一耦合是 D-3 的 `DeepSeekProviderConfig→ChatProviderConfig` 形状问题。
- **风险:** **低** — 类默认已等于盖的值,输出 artifact 不变;经 deepseek smoke/replay 测试
  验 provider trace source_label/provider_name 逐字节一致。
- **需先写 ADR:** ❌ 否

### D-5 · 六个 `validate_*` CLI 包装器同构复制(argparse + load_game_log + load_<X> + print summary),错误处理不一致

- **机会:** 抽一个 `_run_validator(loader, summary_fn)` helper(或一张映射 CLI 名→loader+
  summary keys 的声明式表),把错误处理归一,各 CLI 缩成几行。
- **证据:** `validate_game_log.py:8-21`、`validate_decision_log.py:9-22`、
  `validate_consensus_log.py:9-29`、`validate_failure_audit.py:9-21`、
  `validate_log_bundle.py:12-37`、`validate_semantic_labels.py:10-25` 共享同一 6 行骨架。
  **唯有 `validate_consensus_log.py:15-20` 把 load 包在 try/except、返回 exit 1 + 净化消息;
  其余 5 个让 loader 的 ValidationError 作未捕获 traceback 冒泡**(同类失败的 UX/退出行为
  不同)。本机实测:6 个 validate CLI 中只有 `validate_consensus_log.py` 含 try/except。
- **收益:** 小共享 helper 让全部六个对坏文件都打印同样的 `invalid <log>: <err>` + exit 1
  (今天 6 选 5 是 stack trace),并把每模块缩到几行;为文档化的
  `python -m werewolf_eval.validate_*` 家族(`validate_brief.py:12-14` 编排它们)提供一致
  操作体验。
- **工作量:** **S** — 抽一个 helper 供六者 import;各 CLI 经回调保留自己的 arg 名与 summary
  格式。`validate_brief.py` 与 `test_semantic_labels.py`/`test_decision_log.py` 演练该家族。
- **风险:** **低** —— 薄展示包装,无引擎逻辑;风险仅在于 summary 行是非正式契约
  (`validate_brief` 捕获 stdout),故 summary 文本须保持逐字节不变。错误处理归一是**刻意的
  行为变更**(traceback→exit-1),应先确认是否期望。
- **需先写 ADR:** ❌ 否

---

## 4. Big files — 大文件拆分

五个 >890 LOC 模块各混了多重职责。LOC 经本机 `wc -l` 核实:observer_server 1099、
scoring 952、observer_visibility 933、emergent_engine 895、game_engine 907。

### B-1 · 拆 `observer_server.py`(1099 LOC)—— 把 launch/credential/capability 路由处理器从 HTTP transport 层抽离

- **机会:** 把已写成纯 `(state, args)->(status, payload)` 的 credential/capability/
  launcher-resolution 函数移到如 `observer_launch.py` / `observer_credentials.py`,handler
  仅剩路由+分发。
- **证据:** `observer_server.py:1-1099` 单模块装着(a)`BaseHTTPRequestHandler` transport
  (do_GET/do_POST/do_DELETE/_send_json/_send_event_stream,371-989);(b)~9 个纯
  credential/capability/launcher 函数(`_resolve_live_launcher_for_launch` L106、
  `_check_live_capability` L153、`_check_live_profile_shape` L178、`_provider_live_posture`
  L198、`_build_capabilities_payload` L239、`_credentials_post_result` L267、
  `_credentials_delete_result` L293、`_provider_models_result` L303);(c)server 工厂 +
  profile seeding(L996-1078)。
- **收益:** 这些纯函数无 HTTP 耦合,移出后可不经 localhost HTTP 路径(本环境被墙、今天只能
  经 47 个 HTTP-blocked server 测试触达)做单元测试;handler 缩成最 AI-可导航的纯
  路由+分发形状。
- **工作量:** **M**
- **风险:** **中** — observer_server 被 5 模块 import,路由分发顺序敏感(capability gate 须
  先于 validation);移动须保留精确 import 面与调用次序。纯函数抽取机械,但 SSE/线程代码
  须留原处。
- **需先写 ADR:** ❌ 否

### B-2 · 去重 `game_engine.py` 与 `emergent_engine.py` 共享的 observation/visibility ref 构建

- **机会:** 抽单一共享 helper(如 `role_visibility.refs_for_role(events, role)` + observation
  builder),让 role-filtered 可见事件规则成为两引擎的单一真相源。
- **证据:** `game_engine.py:540-592` 定义 `_public_refs`/`_private_refs_for_role`/
  `_private_refs`/`_wolf_obs`/`_player_obs`,`game_engine.py:256-291` 是 `observation_for`;
  `emergent_engine.py:247-376` 用**相同可见性规则**(public|all、role-match、狼用
  werewolf_team)重新实现 `_public_refs`/`_private_refs`/`_build_obs`。狼-consensus 条目形状
  也近似重复:`game_engine._resolve_wolf_consensus`(L293-480)vs
  `emergent_engine._build_consensus_entry`(L512-561)产出相同 proposals/responses/
  final_decision dict。
- **收益:** 单一 role-filtered 可见事件规则真相源;**这正是 P2-A-2 'no feed leak' 硬闸依赖
  的不变量** —— 今天改一个引擎的过滤器可能静默偏离另一个。减 ~120 重复 LOC 与 consensus-
  entry schema 漂移面。
- **工作量:** **M**
- **风险:** **中** — 两引擎 import 重(game_engine 11 refs,emergent_engine 9),scripted
  g1b/g1c/g1f 模式须逐字节不变(gold-game replay)。抽取须行为保持并对确定性 fixtures 复验。
- **需先写 ADR:** ✅ **是**
  - 草案:**ADR — Shared role-visibility/observation primitive as the single source of
    truth for both `GameEngine` and `EmergentGameEngine` event filtering**(应引用强制该不变量
    的 `tests/test_event_visibility_invariant.py` / `test_visibility_parity.py`)

### B-3 · 拆 `scoring.py`(952 LOC)为 score-log 生成 vs metrics-summary,并隔离 g001 gold-game 特判

- **机会:** 拆成 `scoring_records.py` + `scoring_metrics.py`,并把散落的 g001 字面量抬进一张
  小 `gold_game_fixtures` 表。
- **证据:** `scoring.py:1-953` 担两职:Score Log 生成(`_assess_decision` L276、
  `_score_werewolf_kill`/`_seer_check`/`_witch_save`/`_witch_poison`/`_player_vote`
  L427-596、`score_game` L654)与 Metrics Summary 聚合(`_vote_accuracy_by_player` L722、
  `_seer_metrics` L748、`_witch_metrics` L765、`_team_metrics` L786、`_result_metrics` L812、
  `summarize_metrics` L853)。gold-game `g001` 字面量横跨两半硬编码(L461 event id
  `g001_e007`、L599-608 id 前缀、L691-692、L856-859、L899-911 canonical gap 列表)。
- **收益:** scoring 是被 import 最多的模块(12 refs);拆分把 P3-A(eval/replay)将扩展的两个
  关注点分离,把 g001 fixtures 抬进小表移除 ~10 处散落 magic-string 分支,改善各半独立可测性。
- **工作量:** **L**
- **风险:** **低** —— 纯确定性函数,无 I/O/网络;由现有 gold-game 期望输出测试覆盖,行为保持
  拆分可逐字节验证。
- **需先写 ADR:** ❌ 否

### B-4 · 拆 `observer_visibility.py`(933 LOC)—— 把 snapshot-index 信任解析、event/snapshot 投影、game-log/decision-log 富化分层

- **机会:** 拆成 `seat_trust_index.py` / `projection.py` / `projection_envelope.py`,让安全
  关键的信任源解析与 artifact-join 代码解耦。
- **证据:** `observer_visibility.py:1-934` 混三关注点:(1)snapshot 信任源解析
  `build_seat_role_index` L126-313(role/team/alive 出处:role_projection vs god snapshots);
  (2)透视投影 `build_player_projection` L321 / `event_visible_in_projection` L466 /
  `project_events` L545 / `project_snapshots` L586;(3)artifact join+富化
  `_load_game_log_summaries` L742 / `_load_decision_reasons` L772 /
  `build_projection_envelope` L824(贪婪 decision-to-event 匹配 + private reason_summary 门控)。
- **收益:** 信任源解析(非-god 透视可暴露哪些字段)是安全关键核心,与 artifact-join 交织时最
  难读。分层让 R-06/R-17 可见性不变量可被孤立审查,并让 private reason_summary 门(L865)只挨
  着它自己的逻辑。
- **工作量:** **M**
- **风险:** **中** —— 这是防泄漏边界;任何拆分须保留精确可见性决策。5 个 importer。抽取后须
  重跑可见性投影测试。
- **需先写 ADR:** ✅ **是**
  - 草案:**ADR — Layer observer visibility into trust-index, projection, and
    artifact-enrichment modules with the trust boundary as the single audited surface**

### B-5 · 把 `EmergentGameEngine` 的 night/day 子阶段 resolver 抽成可组合单元,缩小引擎

- **机会:** 把各 night/day 子步 resolver 移到子模块,并把 witch 路径经 `_provider_action`
  统一(它今天绕过该函数手工重建 turn dict)。
- **证据:** `emergent_engine.py:454-756` 把 `_resolve_wolf_kill`(L454-510)、
  `_build_consensus_entry`(L512-561)、`_resolve_seer`(L563-590)、`_resolve_witch`
  (L592-671,最大 —— 内联 ProviderRequest 构建 + parse + 三路验证 + 降级)、
  `_resolve_speech`(L675-720)、`_resolve_votes`(L722-756)与 provider-turn 簿记
  (`_provider_action` L381、`_downgrade_turn` L433)和 run loop(L760-895)塞进同一 class。
- **收益:** 各 resolver 是自洽 night/day 步;witch resolver 尤其复制了 `_provider_action`
  已为其他角色封装的 provider-turn dict+parse+downgrade 模式(它在 L616-622 绕过
  `_provider_action` 手工重建 turn dict)。统一 witch 路径经 `_provider_action` 并移 resolver
  到子模块,减少 per-turn 簿记漂移面,让 live-success 计账(P2-A-2 闸②)各角色一致。
- **工作量:** **M**
- **风险:** **中** —— `live_success_rate` / `provider_result_kind` 计账是分级验收闸;把 witch
  路径改为共享 `_provider_action` 须保持 token_usage/source_label/kind 语义不变,否则 smoke-
  gate 统计偏移。须对两次记录的 DeepSeek smoke 运行复验。
- **需先写 ADR:** ❌ 否

---

## 5. Testability — 可测性

### T-1 · 无 coverage 仪表化、无依赖/测试清单 —— 可测性不可度量

- **机会:** 给现有 CI job 加一个(先非阻塞的)coverage 步骤,并加最小
  `[tool.coverage]` / `requirements-dev.txt`,把"哪些模块没测"从手工 grep 变为可执行可追的数字。
- **证据:** `.github/workflows/tests.yml:24` 仅跑
  `python -m unittest discover -s tests -p test_*.py`;仓库根无
  pyproject/requirements/setup.cfg/pytest.ini(本机实测无任何 `*.toml/*.cfg/*.ini`),
  `import coverage` 在两个已装 Python 上都失败,无 `coverage.txt`。
- **收益:** coverage 闸(哪怕 CI 里 `coverage run -m unittest` 作非阻塞报告)把"哪些模块未测"
  变为可强制可追的数字;最小 requirements/pyproject pin 测试工具链让贡献者与 CI 跑同一套。直接
  使下面每个可测性决策可行。
- **工作量:** **S** — 给现有 CI job 加一步 + 最小 `[tool.coverage]` / `requirements-dev.txt`;无源改动。
- **风险:** **低** —— 增量、先非阻塞报告。localhost-blocked observer HTTP 测试会扭曲本地数字,
  coverage 须只读 CI(Linux)。
- **需先写 ADR:** ✅ **是**
  - 草案:**ADR — Test toolchain and coverage policy(stdlib unittest baseline + CI coverage
    report, no pytest dependency)**

### T-2 · 五个 CLI 入口模块零测试覆盖(只测了其库逻辑)

- **机会:** 给每个 CLI 加一个薄 subprocess / `main([...])` 测试,锁 exit code + arg 接线 + 错误消息。
- **证据:** 精确 import-graph 扫描显示这些被**无任何测试**导入:`validate_game_log.py:1`、
  `validate_consensus_log.py:1`、`validate_failure_audit.py:1`、`validate_log_bundle.py:1`、
  `attribute_game.py:1`。同名的测试 grep 命中解析到的是其他模块的库函数(如
  `attribution.attribute_game` 在 `tests/test_attribution.py:11`),非这些 CLI。argparse 解析、
  退出码(校验错误 return 1,如 `validate_consensus_log.py:18-20`)、错误消息格式均未演练。
- **收益:** 这些是 operator-facing、用于把守 log/fixture 契约的工具;其退出码或 arg 接线的回归会
  静默过 CI。薄 subprocess/`main([...])` 测试(本仓已对 `run_g1h_fake_runtime` 经 `-m` 这么做,见
  `tests/test_g1h_runtime_spine.py:211`)廉价锁住契约。
- **工作量:** **S** — 每 CLI 一个小测试:用 fixture 路径调 `main()`,断言 exit code + stdout;或折进
  现有 validate-library 测试文件。
- **风险:** **低**。注意 `attribute_game.py:1` 已被显式标 LEGACY(R-35)"不要扩展" —— 对它正解可能是
  *删除*而非新增测试,投入前先定。
- **需先写 ADR:** ❌ 否

### T-3 · Qt/QML 客户端无行为测试 —— 只有静态存在/secret-scan 契约 —— 而未测逻辑正是易出 bug 的剧场管线

- **机会:** 把剧场 event-presentation queue 的纯函数抽出做单测(Qt 的 `qmltestrunner`/QtQuickTest,
  或把 queue 逻辑抽成可 headless 测试的 plain-JS/Python 模块);静态契约测试保留作守卫。
- **证据:** `tests/test_qt_observer_static_contract.py` 是唯一 Qt 测试;它 grep 必需文件
  (`REQUIRED_QML_VIEWS` ~L33)、必需 objectName、禁用模式
  (`FORBIDDEN_PYTHON_RUNTIME_PATTERNS` L8、`FORBIDDEN_SECRET_PATTERNS` L22),**断言零运行时
  行为**。承载最多 JS 逻辑的 QML 恰是剧场 render 路径:
  `clients/qt_observer/qml/EventPresentationQueue.qml`(280 行,21 logic markers)、
  `components/SpeechTheater.qml`(364 行,15)、`components/SeatRing.qml`(287 行,14)。
  MEMORY.md 的 live-launch 记录把这条管线的 live 渲染 bug('夜晚指向线缺失/延迟、早期发言无正文')
  标为**仍未关闭**。
- **收益:** 剧场 event-presentation queue(发言与夜晚指向线的顺序/时序)是已产生过实报缺陷的逻辑;
  抽出其纯函数做单测(QtQuickTest,或把 queue/timing 逻辑从 QML 抽成可测 plain-JS/Python)能在手工
  启动前抓住这些回归。
- **工作量:** **M** — 需在 CI 加 Qt 测试 harness(QtQuickTest)或把 queue/timing 逻辑从 QML 抽成
  可测纯逻辑;静态契约测试留作守卫。
- **风险:** **中** —— Qt 测试基建给 CI 加复杂度与 Qt 构建依赖;缓解:只测抽出的纯逻辑,不测全 QML 渲染。
- **需先写 ADR:** ✅ **是**
  - 草案:**ADR — Qt observer testing strategy(static contract guard + extracted pure-logic
    unit tests vs full QtQuickTest in CI)**

### T-4 · 根 launcher `launch-theater.py` 无测试,却是最近 bug 最密的编排代码

- **机会:** 给 `_server_is_current()` 与 `_kill_server_on_port()` 的 netstat-PID parse 加注入接缝
  (传入 getter/runner),对 parse + reuse 决策做单测。
- **证据:** `launch-theater.py`(178 行)无测试引用(tests/ 中 grep
  launch-theater/launch_theater 零命中)。它含非平凡决策逻辑 —— `_server_is_current()`(L51)、
  `_kill_server_on_port()` 的 netstat/taskkill parse(L70)、server 复用-vs-重启分支(L116)——
  全用硬编码模块级 `subprocess.run`/HTTP 调用接线(无注入接缝)。MEMORY.md
  (live-launch-e2e-2026-06-08)记录这个 launcher 是 6 个连环 bug 的根,含'launcher 复用陈旧 server'
  与'Preflight startDefaultMatch 覆盖真局'。
- **收益:** `_server_is_current()` 与 `_kill_server_on_port()` 的 netstat-PID parse 是造成过真实事故的
  近-纯字符串/决策逻辑;让它们可注入并单测 parse + reuse 决策本可抓住那 6 个 bug 中的数个。全仓
  缺陷史-对-覆盖比最高。
- **工作量:** **M** — 需小重构加接缝(抽决策函数、注入 subprocess/HTTP callable)后测试才干净;provider
  层已用 `transport=` 注入示范该模式(`llm_providers.py:58`、`tests/test_openai_provider.py:69`)。
- **风险:** **中** —— 重构用户在用的 launcher;但本轮只读,这是计划项。行为保持的抽取把风险控住。
- **需先写 ADR:** ❌ 否

### T-5 · 无共享 test fixtures/conftest —— 797 个测试函数各自造 setup

- **机会:** 抽共享 fixtures 模块(canonical 最小 GameLog、fake transport 工厂、tmp-run 目录 helper)。
- **证据:** `tests/` 含 53 个 `test_*.py`、约 797 个 `def test_` 函数(本机实测 53 文件),但**无
  conftest.py、无共享 helper 模块**(grep `from tests`/`import helpers`/共享-helper import 零命中)。
  Game-log/decision-log fixtures 各文件内联重建(如 scoring fixtures 在 `tests/test_scoring.py`、
  `test_attribution.py`、`test_engine_to_scoring_e2e.py`、`test_settlement_bundle.py` 各自独立造)。
- **收益:** 共享 fixtures 模块减 per-file 样板,让新测试更便宜写(降低补上面各缺口的成本),防止
  fixture 漂移("同一个" game 在 7 个文件里造得略不同)。
- **工作量:** **M** — 把公共 builder 抽进 `tests/_fixtures.py` 或 conftest;增量,从最重复的(GameLog +
  transport)builder 起。**注意:** runner 是 unittest discover,conftest 对发现无作用,须把共享 helper
  作普通可 import 模块(`tests/_fixtures.py`)而非 pytest conftest(与 T-1/P-3 的 runner 取向决策耦合)。
- **风险:** **低** —— 增量;现有内联 fixtures 迁移期间仍可用。过度集中会耦合无关测试,故 fixtures 保持小而显式。
- **需先写 ADR:** ❌ 否

### T-6 · ADR 语料只有一篇 —— 2026-06-03 后的重大架构决策只活在 memory/PROJECT_MAP 散文里,削弱 AI 可导航性与测试理据可追溯

- **机会:** 为可见性不变量、fake-default 测试策略等已做决策补 3-4 篇短 ADR,把它们从散文落到
  `docs/adr/**`(满足项目自己的规则)。
- **证据:** `docs/adr/` 恰好一个文件:`0001-client-agnostic-live-observer-protocol.md`(2026-06-03,
  Accepted)。其后多个 load-bearing 决策无 ADR:BYO-key 'client-owned secret, server-executed call'
  架构及其三条安全不变量(只在 `PROJECT_MAP.md:71-81` 与 MEMORY.md);多个测试强制的可见性投影
  'no-leak' 不变量(`tests/test_event_visibility_invariant.py`、`test_visibility_parity.py`);
  'fake-deterministic default, live behind a gate' 测试策略(`PROJECT_MAP.md:64-68`)。**`AGENTS.md:60`
  本身写着 "Stable architecture decisions live in `docs/adr/**`",故此缺口违反项目自己的规则。**
  本机已核实 `AGENTS.md:60` 该规则与 `docs/adr/` 仅一文件。
- **收益:** 为可见性不变量与 fake-default 测试策略写 ADR,给测试一个可引用的理据(这些守卫为何存在、
  什么绝不可回归),正是让代码库 AI-可导航、防止未来 agent "修好" 一个编码了安全不变量的测试的关键;
  也补上项目文档化的 stable-decisions 政策。
- **工作量:** **S/篇** —— 这些是把已做、已在散文记录的决策蒸馏的文档产物;3-4 篇短 ADR。
- **风险:** **低** —— 仅文档;主风险是 ADR 与代码漂移,故每篇应引用强制它的测试(如 ADR-visibility 引用
  `tests/test_event_visibility_invariant.py`)。
- **需先写 ADR:** ❌ 否(本条本身即 ADR 工作)

---

## 跨领域备注:ADR 0002 编号冲突

本文出现两个候选 **ADR 0002**:packaging P-1(src-layout pyproject 契约)与
entrypoints E-1(`werewolf` CLI taxonomy)。二者是同一打包决策的两面
(`[project.scripts]` 需要 pyproject 才能声明,`werewolf` CLI 又靠 entry-points 暴露)。
落地时**建议合并为单一 ADR 0002**,把"src-layout 可安装包 + console-scripts 暴露的
canonical CLI taxonomy"写进同一份决策,避免编号撞车与决策碎片。后续 ADR 顺延:
ADR 0003 = 测试导入路径(P-3);可见性 primitive(B-2)、observer 信任分层(B-4)、
coverage 政策(T-1)、Qt 测试策略(T-3)各取后续编号。

## 优先级提示(仅排序建议,非本轮实施)

1. **D-1**(budget 子串错配)— 唯一潜在正确性陷阱,S 工作量、低风险,应最先修。
2. **P-1 + E-1 合并的 ADR 0002**(打包 + CLI)— 解锁 P-2..P-5、E-* 与 P-3/T-1 的多数下游。
3. **B-2 / B-4 的可见性 ADR** — 触及安全边界,须 ADR 先行再动代码。
4. 其余(E-2..E-5、D-2..D-5、B-1/B-3/B-5、T-2..T-6)为机械或文档类,可在上述地基后并行。

# Foundation: artifacts 写盘收敛 + 最小 pyproject Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 两个 S 级地基件：(B) 最小 `pyproject.toml` + ADR-0002 让 `werewolf_eval` 成为可安装包（体检 P-1/P-2，Top-10 第 2 位）；(A) 把 9 份逐字/近字重复的 `_write_json` 与 6 份 `_collect_trace` 收敛进新模块 `src/werewolf_eval/artifacts.py`，artifact 输出字节恒等（体检 E-2/E-3）。

**Architecture:** B 是纯增文件（pyproject + ADR），零代码改动，`PYTHONPATH=src` 在过渡期继续受支持（半迁移风险按 P-1 缓解二「明确推迟切换+留 TODO」处理，CI/launcher 切换属 ADR-0003/P-3 后续切片）。A 是搬移不是重写：`write_json` 9 份变体语义完全一致（mkdir parents → `json.dumps(ensure_ascii=False, indent=2)` + 末尾换行 → utf-8），收敛为单一函数；`collect_provider_trace` 按体检 E-3 处方参数化（provider_name/source_label/agents-iterable 作参数、wolf_agent 折入 agents 列表、`dedup` 开关保留 run_fake_provider_game 的无去重漂移现行为，不修，交用户裁决）。

**Tech Stack:** Python 3.12 纯 stdlib；打包后端 hatchling（理由见 Task 1 ADR 正文：editable install 不在源树落 `egg-info`，避免动 allowlist 之外的 `.gitignore`，即体检 P-5 的旁路解）；测试 `unittest`。

**执行环境:** 隔离 worktree `G:\worktree-foundation`，分支 `foundation/artifacts-pyproject`（基于 main `7066b36`，SYS-B4 已合并，A 部分时序约束已解除）。测试命令一律带 `NO_PROXY='*' PYTHONPATH=src`。**不 merge、不 push main**；终态 = worktree 分支 + 合并就绪报告。

---

## 现状盘点（grep 全量核实，2026-06-11）

`_write_json` 在 src 共 11 份；其中 9 份在 run_*.py 系列（允许改），语义恒等：

| 文件 | 行 | 文本变体 |
|---|---|---|
| run_fake_provider_game.py | 20 | `str`，output_path 多行体 |
| run_deepseek_provider_game.py | 24 | 同上（逐字） |
| run_mock_game.py | 14 | 同上（逐字） |
| run_deepseek_consensus_game.py | 33 | 同上（逐字） |
| run_emergent_deepseek_game.py | 40 | `Path/Any` 单行体 |
| run_emergent_fake_runtime.py | 51 | 同上（逐字） |
| run_g1h_fake_runtime.py | 73 | `Path/Any` 多行体 |
| run_scripted_game.py | 14 | `str \| Path` |
| run_emergent_game.py | 33 | `str`，`p` 变量 |

另 2 份在 `attribute_game.py:16` / `score_game.py:21`——**无 mkdir 且不属 run_*.py 系列，禁改边界外，本计划不动，只入报告**。

`_collect_trace` 在 run_*.py 共 6 份，共享同一去重循环核心，差异维度：

| 文件 | 行 | wolf_agent | isinstance 过滤 | getattr/hasattr 护栏 | 去重 | 返回 |
|---|---|---|---|---|---|---|
| run_fake_provider_game.py | 29 | ✓ | ✓ | ✗ | **✗（漂移）** | ProviderTrace |
| run_deepseek_provider_game.py | 33 | ✓ | ✓ | ✗ | ✓ | ProviderTrace |
| run_deepseek_consensus_game.py | 42 | ✗ | ✓ | ✗ | ✓ | ProviderTrace |
| run_g1h_fake_runtime.py | 81 | ✗ | ✓ | hasattr | ✓ | ProviderTrace |
| run_emergent_deepseek_game.py | 83 | ✗ | ✗ | ✗ | ✓ | dict（provider_trace_to_dict） |
| run_emergent_fake_runtime.py | 56 | ✗ | ✗ | getattr | ✓ | dict |

恒等性论证（详细校验在 Task 7-8 落地）：
- 各座位/狼各持独立 provider 实例（`build_default_fake_provider_agent`/`provider_factory` 每调一次建一个），request_id 跨 provider 不碰撞 → 去重是保险带，开关两态对现有数据流产出相同 bytes；漂移是潜伏性差异，按用户裁决保留 `dedup=False`。
- isinstance 过滤补到 emergent 两份：其 agents 为 `dict[str, ProviderAgent]`，全员通过过滤 → 行为恒等。
- `getattr(provider, "requests", [])` 统一护栏：直接属性访问的 4 份其 provider 必有该属性 → 仅差不可达错误路径。
- 迭代顺序保真：canonical 接收已拼好的 iterable，调用点传 `list(agents.values()) + [wolf_agent]` 等，顺序不变。
- `failures` 按引用透传（不复制），别名语义不变。

跨文件引用：`_write_json`/`_collect_trace` 零跨模块 import（grep 全仓核实；`tests/fake_scribe.py` 仅注释提及）。

## 明确不做（边界）

- `attribute_game.py` / `score_game.py` 的 `_write_json`（边界外，且变体无 mkdir，报告中列出）。
- `deepseek_launcher.py` exit-code 映射收敛（后续 plan）；`observer_server.py` 内联 launcher（别的轨道）；统一 argparse/launcher 框架（R-36 裁决不做）；E-1 console-scripts CLI（需独立 ADR）。
- 删 26 处测试 `sys.path.insert` 样板（P-3/ADR-0003，独立后续 PR）。
- 修 run_fake_provider_game 去重漂移（保留现行为，报告交裁决）。
- 改 `.gitignore`（不在 allowlist；hatchling 后端使其不必要）。

---

## B 段（先做）

### Task 1: ADR-0002 — src-layout 可安装包决策

**Files:**
- Create: `docs/adr/0002-src-layout-installable-package.md`

- [ ] **Step 1: 写 ADR**（英文，与 0001 风格一致；内容要点必须含）：
  - Status: Accepted; Date: 2026-06-11.
  - Context: 零打包清单（git ls-files 无 pyproject/setup/requirements），`PYTHONPATH=src` 手工穿线至少 5 处（`tests.yml:23`、`AGENTS.md:85`、`live-check.bat:4`、`launch-theater.py:97`、`tools/live_check_deepseek.py:57`）；引体检 P-1/P-2/P-5。
  - Decision: PEP 621 最小 pyproject；`requires-python = ">=3.12"`（CI pin 对齐）；`dependencies = []` 把「纯 stdlib」不变量落纸面（加第一个真依赖须刻意）；后端选 **hatchling**，理由：editable install 全程在临时目录构建、不在源树落 `*.egg-info`（setuptools 会，落了就要动本计划 allowlist 之外的 `.gitignore`，即 P-5），且 PEP 621 原生、src-layout 仅需两行显式声明；setuptools 作为已记录的备选。
  - Consequences/Transition: `PYTHONPATH=src` 过渡期继续受支持（两机制并存的半迁移风险按 P-1 缓解二处理，留 TODO）；CI/launcher 切 editable install + 删 26 处 `sys.path.insert` = 未来 ADR-0003（P-3）；console-scripts/`werewolf` CLI（E-1）需独立 ADR——本 ADR 拿走 0002 编号，裁决了体检里 P-1 vs E-1 的编号竞争。
- [ ] **Step 2: Commit** `git add docs/adr/0002-src-layout-installable-package.md && git commit -m "docs(adr): ADR-0002 src-layout installable package (health-check P-1/P-2)"`

### Task 2: 最小 pyproject.toml

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: 基线测试**（改前全绿证据）：
  `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`，记录 OK 数。
- [ ] **Step 2: 写 pyproject.toml**：

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "werewolf-eval"
version = "0.1.0"
description = "Client-agnostic live AI Werewolf experiment platform (evaluation core)"
requires-python = ">=3.12"
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["src/werewolf_eval"]
```

- [ ] **Step 3: 验证 editable install**：
  - `pip install -e .`（pip 走环境代理；若 hatchling 拉取失败，先 `pip install hatchling` 重试；再不行回退 setuptools 方案并停下报告——因牵出 .gitignore 越界问题须问用户）。
  - 不带 PYTHONPATH、换 cwd 验证：`cd /tmp && python -c "import werewolf_eval; print(werewolf_eval.__file__)"` → 指向 `G:\worktree-foundation\src\werewolf_eval\__init__.py`。
  - `git status --short` 确认安装未在源树留任何未跟踪产物（hatchling 关键卖点，必须实证）。
- [ ] **Step 4: 改后测试**：同 Step 1 命令，OK 数一致全绿；另跑一次**不带 PYTHONPATH** 的 `NO_PROXY='*' python -m unittest discover -s tests -p "test_*.py"` 证明 install 路径独立可用（env-only 测试组不再必须 env）。
- [ ] **Step 5: Commit** `git add pyproject.toml && git commit -m "build: minimal PEP 621 pyproject (hatchling, src-layout, stdlib-only) per ADR-0002"`

## A 段

### Task 3: 字节恒等基线采集（改代码之前）

6 个可离线确定性 runner，在未改代码的 HEAD 各跑两遍（before1/before2）以界定非确定性噪声（如时间戳字段）；恒等判据 = after 对 before1 的差异 ⊆ before1 对 before2 的噪声集（理想为空集）。

- [ ] **Step 1: 采集脚本（ad-hoc bash，产物入 `.tmp/byteproof/`，不提交）**：

```bash
cd /g/worktree-foundation
capture() {  # $1 = before1|before2|after
  T=.tmp/byteproof/$1; rm -rf $T
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_mock_game \
    --game-log-out $T/mock/game-log.json --decision-log-out $T/mock/decision-log.json \
    --consensus-log-out $T/mock/consensus-log.json --failure-audit-out $T/mock/failure-audit.json
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_scripted_game docs/game-scripts/g1-scripted-game.json \
    --game-log-out $T/scripted/game-log.json --decision-log-out $T/scripted/decision-log.json \
    --consensus-log-out $T/scripted/consensus-log.json
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_fake_provider_game \
    --game-log-out $T/fakeprov/game-log.json --decision-log-out $T/fakeprov/decision-log.json \
    --provider-trace-out $T/fakeprov/provider-trace.json --failure-audit-out $T/fakeprov/failure-audit.json
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_g1h_fake_runtime --out-dir $T/g1h
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --out-dir $T/emfake
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --out-dir $T/emfake-wolf --script $(NO_PROXY='*' PYTHONPATH=src python -c "from werewolf_eval.emergent_fake_script import SCRIPTS; print(sorted(SCRIPTS)[-1])")
  NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_game \
    --game-log-out $T/emergent/game-log.json --decision-log-out $T/emergent/decision-log.json \
    --consensus-log-out $T/emergent/consensus-log.json --failure-audit-out $T/emergent/failure-audit.json
}
capture before1 && capture before2
diff -r .tmp/byteproof/before1 .tmp/byteproof/before2   # 记录噪声文件清单（期望为空）
```

（注：emergent_fake_runtime 的 `--script` 第二档取 SCRIPTS 里另一脚本，覆盖不同分支；若 `emergent_fake_script` 导入名不符，运行时以 `run_emergent_fake_runtime.py` 顶部 import 实名为准修正命令，不改源码。deepseek 三 runner 无法离线跑，其 `_collect_trace`/`_write_json` 恒等性由 Task 4 单测 + 现有 `test_deepseek_provider_game.py`/`test_deepseek_consensus_game.py` 等套件覆盖。）

- [ ] **Step 2: 记录** before1 vs before2 的 diff 输出（空 = 全确定性，恒等判据收紧为「after 与 before1 逐字节相同」）。

### Task 4: TDD — 新模块 artifacts.py

**Files:**
- Create: `src/werewolf_eval/artifacts.py`
- Test: `tests/test_artifacts.py`

- [ ] **Step 1: 写失败测试** `tests/test_artifacts.py`：

```python
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.artifacts import collect_provider_trace, write_json
from werewolf_eval.provider_agent import ProviderAgent


@dataclass(frozen=True)
class _Item:
    request_id: str


class _FakeProvider:
    def __init__(self, requests=(), responses=()):
        self.requests = list(requests)
        self.responses = list(responses)


def _agent(seat, requests=(), responses=()):
    return ProviderAgent(seat, _FakeProvider(requests, responses))


class WriteJsonTests(unittest.TestCase):
    def test_writes_utf8_json_with_trailing_newline_and_parents(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "dir" / "artifact.json"
            write_json(target, {"name": "狼人", "n": 1})
            raw = target.read_bytes()
            self.assertEqual(raw.decode("utf-8"), '{\n  "name": "狼人",\n  "n": 1\n}\n')

    def test_accepts_str_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "a" / "b.json")
            write_json(target, [])
            self.assertEqual(Path(target).read_text(encoding="utf-8"), "[]\n")


class CollectProviderTraceTests(unittest.TestCase):
    def test_dedups_by_request_id_across_agents_preserving_order(self):
        shared = _Item("dup")
        a1 = _agent("p1", requests=[_Item("r1"), shared], responses=[_Item("r1")])
        a2 = _agent("p2", requests=[shared, _Item("r2")], responses=[_Item("r2")])
        trace = collect_provider_trace("g1", [a1, a2], provider_name="x", source_label="[x]")
        self.assertEqual([r.request_id for r in trace.requests], ["r1", "dup", "r2"])
        self.assertEqual([r.request_id for r in trace.responses], ["r1", "r2"])

    def test_dedup_false_preserves_duplicates(self):
        # run_fake_provider_game 历史无去重行为的保真开关(漂移保留,见合并报告)
        shared = _Item("dup")
        a1 = _agent("p1", requests=[shared])
        a2 = _agent("p2", requests=[shared])
        trace = collect_provider_trace(
            "g1", [a1, a2], provider_name="x", source_label="[x]", dedup=False
        )
        self.assertEqual([r.request_id for r in trace.requests], ["dup", "dup"])

    def test_non_provider_agents_filtered_and_missing_attrs_tolerated(self):
        bare = ProviderAgent("p9", object())
        trace = collect_provider_trace(
            "g1",
            [object(), bare, _agent("p1", requests=[_Item("r1")])],
            provider_name="x",
            source_label="[x]",
        )
        self.assertEqual([r.request_id for r in trace.requests], ["r1"])

    def test_metadata_and_failures_passthrough(self):
        failures = []
        trace = collect_provider_trace(
            "g7", [], provider_name="deepseek", source_label="[live]", failures=failures
        )
        self.assertEqual(trace.game_id, "g7")
        self.assertEqual(trace.provider_name, "deepseek")
        self.assertEqual(trace.source_label, "[live]")
        self.assertIs(trace.failures, failures)
        trace2 = collect_provider_trace("g7", [], provider_name="d", source_label="[l]")
        self.assertEqual(trace2.failures, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**：`NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_artifacts -v` → `ModuleNotFoundError: ... artifacts`。
- [ ] **Step 3: 实现** `src/werewolf_eval/artifacts.py`：

```python
"""Shared artifact-write + provider-trace assembly for run_*.py entrypoints.

Single source of truth for two contracts previously copy-pasted across the
run_* launchers (health check 2026-06-08, E-2/E-3):

- write_json: the artifact-write contract (mkdir parents, UTF-8,
  ensure_ascii=False, indent=2, trailing newline) — the natural enforcement
  point for the R-08 write discipline.
- collect_provider_trace: roll up per-seat provider requests/responses into
  one ProviderTrace, de-duplicated by request_id. Each seat wraps its own
  provider instance, so ids never collide across seats and the de-dup is
  belt-and-suspenders; dedup=False preserves the historical
  run_fake_provider_game no-dedup behavior verbatim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from werewolf_eval.provider_agent import ProviderAgent
from werewolf_eval.provider_contract import (
    ProviderFailure,
    ProviderRequest,
    ProviderResponse,
    ProviderTrace,
)


def write_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def collect_provider_trace(
    game_id: str,
    agents: Iterable[Any],
    *,
    provider_name: str,
    source_label: str,
    failures: list[ProviderFailure] | None = None,
    dedup: bool = True,
) -> ProviderTrace:
    seen_req: set[str] = set()
    seen_resp: set[str] = set()
    requests: list[ProviderRequest] = []
    responses: list[ProviderResponse] = []
    for agent in agents:
        if not isinstance(agent, ProviderAgent):
            continue
        provider = agent.provider
        for req in getattr(provider, "requests", []):
            if dedup and req.request_id in seen_req:
                continue
            seen_req.add(req.request_id)
            requests.append(req)
        for resp in getattr(provider, "responses", []):
            if dedup and resp.request_id in seen_resp:
                continue
            seen_resp.add(resp.request_id)
            responses.append(resp)
    return ProviderTrace(
        game_id=game_id,
        provider_name=provider_name,
        source_label=source_label,
        requests=requests,
        responses=responses,
        failures=failures if failures is not None else [],
    )
```

（循环导入安全：artifacts → provider_agent → action_runtime/game_engine/provider_contract，无回边。）

- [ ] **Step 4: 跑测试确认通过**：同 Step 2 命令 → 全 PASS。
- [ ] **Step 5: Commit** `git add src/werewolf_eval/artifacts.py tests/test_artifacts.py && git commit -m "feat(artifacts): shared write_json + collect_provider_trace (health-check E-2/E-3, TDD)"`

### Task 5: 9 个 run_*.py 切换 write_json

**Files:**
- Modify: 盘点表中 9 个 run_*.py（删本地 `_write_json` def，加 `from werewolf_eval.artifacts import write_json`，调用点 `_write_json(` → `write_json(`）

- [ ] **Step 1: 逐文件替换**。模式（以 run_mock_game.py 为例）：删 14-20 行的 def 块；import 区加一行 `from werewolf_eval.artifacts import write_json`（按字母序插入现有 `from werewolf_eval...` 块）；该文件全部 `_write_json(` 调用改 `write_json(`。9 个文件同模式；`run_emergent_deepseek_game.py`/`run_emergent_fake_runtime.py`/`run_g1h_fake_runtime.py` 删 def 时顺带检查 `typing.Any`/`Path` import 是否仍被其他代码使用，未使用则按该文件实际情况清理（不确定就保留，宁可冗余不引入 NameError）。
- [ ] **Step 2: 死引用扫描**：`grep -rn "_write_json" src tests` → 仅剩 `attribute_game.py`/`score_game.py` 2 处（边界外）。
- [ ] **Step 3: 全套件**：`NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"` 全绿，OK 数与基线一致 +（新增 test_artifacts 的条数）。
- [ ] **Step 4: Commit** `git add -u src/werewolf_eval && git commit -m "refactor(run_*): route artifact writes through artifacts.write_json (byte-identical)"`

### Task 6: 6 个 run_*.py 切换 collect_provider_trace

**Files:**
- Modify: `run_fake_provider_game.py` / `run_deepseek_provider_game.py` / `run_deepseek_consensus_game.py` / `run_g1h_fake_runtime.py`（本地 `_collect_trace` 改薄包装，签名与调用点不动）；`run_emergent_deepseek_game.py` / `run_emergent_fake_runtime.py`（删本地 def，单调用点内联）

- [ ] **Step 1: 四个双调用点文件改薄包装**（保留本地名与签名 → 调用点零改动）。run_fake_provider_game.py：

```python
def _collect_trace(
    game_id: str,
    agents: dict[str, object],
    wolf_agent: object,
    failures: list[ProviderFailure],
) -> ProviderTrace:
    # dedup=False: 保留本 runner 历史上不去重的行为(漂移按用户裁决原样保留)
    return collect_provider_trace(
        game_id,
        list(agents.values()) + [wolf_agent],
        provider_name="deterministic_fake_provider",
        source_label=FAKE_PROVIDER_SOURCE_LABEL,
        failures=failures,
        dedup=False,
    )
```

run_deepseek_provider_game.py 同形：`list(agents.values()) + [wolf_agent]`，`provider_name="deepseek"`，`source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL`，无 `dedup=False`。
run_deepseek_consensus_game.py：`agents.values()`（无 wolf_agent），`provider_name="deepseek"`，`source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL`。
run_g1h_fake_runtime.py：`agents.values()`，`provider_name="fake_deterministic"`，`source_label=FAKE_PROVIDER_SOURCE_LABEL`。
四文件各自 import 区加 `collect_provider_trace`（与 Task 5 的 write_json 合并成一行 `from werewolf_eval.artifacts import collect_provider_trace, write_json`）。

- [ ] **Step 2: 两个单调用点文件内联**。run_emergent_fake_runtime.py:134 改为：

```python
    write_json(
        out_dir / "provider-trace.json",
        provider_trace_to_dict(
            collect_provider_trace(
                game_id,
                agents.values(),
                provider_name=_FAKE_PROVIDER_NAME,
                source_label=FAKE_PROVIDER_SOURCE_LABEL,
            )
        ),
    )
```

run_emergent_deepseek_game.py:172-176 的调用改为 `provider_trace_to_dict(collect_provider_trace(game_id, trace_agents.values(), provider_name=provider_name, source_label=effective_label))`（原 `_collect_trace` 接收 dict 取 `.values()`，外层 `provider_trace_to_dict` 原本在 def 内部，现移到调用点；原调用若已包了一层 dict 转换以实际行号上下文为准，保证最终 payload 表达式语义逐项一致）。两文件删本地 `_collect_trace` def。

- [ ] **Step 3: 死引用扫描**：`grep -rn "_collect_trace" src tests` → 仅剩四个薄包装 def 与其调用点 + `fake_scribe.py` 注释。
- [ ] **Step 4: 全套件**：同 Task 5 Step 3，全绿。
- [ ] **Step 5: Commit** `git add -u src/werewolf_eval && git commit -m "refactor(run_*): route trace assembly through artifacts.collect_provider_trace (drift preserved via dedup=False)"`

### Task 7: 字节恒等验证 + tree 钩子

- [ ] **Step 1: after 采集**：`capture after`（Task 3 同一函数），然后 `diff -r .tmp/byteproof/before1 .tmp/byteproof/after`。判据：差异 ⊆ Task 3 记录的噪声集（噪声集为空则必须逐字节相同）。任何超出 → 停，按 systematic-debugging 找根因，不许「顺手修」。
- [ ] **Step 2: 失败路径补测**：`run_fake_provider_game --failure-mode` 取一个合法值（从该文件 main() 的 choices/分支读出）before/after 各跑一次对比，覆盖 `failures` 非空 + 无去重分支的真实出口。
- [ ] **Step 3: tree 钩子**：`node .codex/hooks/tree.mjs --force`（新增了 artifacts.py / test_artifacts.py / pyproject.toml / ADR / 本 plan）。
- [ ] **Step 4: Commit** `git add .oh-my-harness/tree.md docs/harness/plans/2026-06-11--foundation-artifacts-pyproject-plan.md && git commit -m "docs(plan)+chore(tree): foundation plan + tree refresh"`（plan 文件在首个执行 commit 之前或此处入库均可，以实际执行顺序为准）。

### Task 8: Code review + 合并就绪报告

- [ ] **Step 1:** 派独立 code-review subagent（读本 plan + 全部 diff），抓真问题，修复后复跑全套件。
- [ ] **Step 2:** 验证清单（AGENTS.md Validation 节）：`git diff main --stat` / `--name-only`；allowlist 比对（只许：run_*.py 9 个、artifacts.py、tests/test_artifacts.py、pyproject.toml、docs/adr/0002-*.md、本 plan、tree.md）；forbidden-scope 确认零越界。
- [ ] **Step 3:** `git merge-tree $(git merge-base HEAD main) HEAD main` 冲突检查（或 fetch 主树最新 main 后比对）。
- [ ] **Step 4:** 输出合并就绪报告：分支名、commit 列表、全套测试证据（改前/改后、带/不带 PYTHONPATH 四组）、字节恒等证明（噪声集 + diff 结果）、pip install -e 证据、漂移事实陈述（run_fake_provider_game 无去重 + attribute_game/score_game 两份边界外副本，交用户裁决）、不 merge 不 push。

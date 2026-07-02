# Werewolf-agent

**一个可观战、可审计的 AI 对战 AI 狼人杀竞技场。**

开局前配置每个座位由哪个 AI 模型扮演,以上帝视角实时观战整局推理与博弈,结束后查看结算战报——每一次决策、发言、投票背后都有完整可审计的事件日志。

简体中文 | [English](README.md)

---

## 这是什么?

Werewolf-agent 是一个 **client-agnostic 的 AI 狼人杀实时实验平台**。Python 对局引擎驱动 6 人社交推理局,每个座位由一个 AI agent 扮演,并处于严格的信息隔离之下——狼人不知道谁是预言家、预言家的查验结果只有自己可见,并且每个座位的 prompt 可被证明只由它有权看到的事件构建。

对局既可以完全离线运行(确定性 fake provider,默认模式),也可以接入真实 LLM API 实时对战。每局都会产出结构化、可重放的事件流,支撑观战、结算战报、历史回放与评测。

## 核心特性

- **涌现式对局引擎** — 6 人局(2 狼人、1 预言家、1 女巫、2 村民):狼人共识刀人、预言家查验、女巫救/毒、白天发言、投票、处决、胜负裁决。动态回合、无剧本。猎人角色变体已在 action runtime 中实现(`rules_v1_1`)。
- **自带 AI(BYO-key)** — 按座位配置 provider/模型/prompt/温度。内置预设:DeepSeek、OpenAI、Anthropic,以及 9 家 OpenAI 兼容厂商(智谱 GLM、Moonshot、通义千问、MiniMax、SiliconFlow、xAI、Gemini、ModelScope、OpenRouter),并支持完全自定义端点。API key 始终留在本机;只有本地 Python server 会调用供应商接口。
- **Qt 剧场客户端** — 上帝视角实时观战(座位环、发言剧场、证据控制台、播放控制)、对局配置沙盘、剧场内结算覆盖层与滚动战报、历史对局回看与管理。
- **诚实链路** — 事件溯源日志(`events.jsonl`、快照、prompt manifest、provider 调用链、故障审计)、执行真相 HUD(`LIVE_API` vs `SIMULATION`)、可见性投影(上帝/公开/各角色视角),以及在信息泄漏或规则违例时立刻报错的运行时不变量。
- **评测就绪** — 确定性评分、规则归因、带分臂指标的消融实验台、字节锁定的 prompt 版本化与修订台账、差分测试、固定种子的确定性模拟。
- **零依赖后端** — Python 后端只用标准库,跑离线对局无需 `pip install` 任何东西。

## 架构

```text
YAML 运行 profile(每座位 AI / prompt / 角色洗牌)
        │
        ▼
Python 对局引擎 + agent/provider 循环              src/werewolf_eval/
  · 涌现引擎、action runtime(能力系统)
  · provider 注册表(DeepSeek / OpenAI / Anthropic / 9 家预设 / 自定义)
  · 不变量安全网、确定性 fake 模式
        │  事件溯源:events.jsonl · 快照 · prompt manifest · provider 调用链
        ▼
本地 observer server(REST + SSE,client-agnostic 协议)
        │
        ▼
Qt 6 / QML 剧场客户端                              clients/qt_observer/
  · 实时观战 · 对局配置 · 结算战报 · 历史回放
```

observer 协议是硬边界:任何客户端(现在是 Qt,未来可以是 Web)消费同一套 REST/SSE 接口,绝不接触引擎内部实现或 provider 密钥。

## 快速开始

### Windows 桌面安装

普通桌面用户只需要从主仓库 GitHub Releases 下载 `Werewolf-agent-0.2.0-Setup.exe` 并运行一次。其他 release assets 是更新器使用的包和索引,体验者不需要手动选择。程序安装到 `%LOCALAPPDATA%\WerewolfAgent\current\`,对局、profiles、configs、logs、凭证和设置保留在 `%LOCALAPPDATA%\Werewolf-agent\` 或 Windows 用户存储中。

首次公开 Windows 安装包暂未做代码签名。安装前 Windows 可能显示“未知发布者”或 SmartScreen 提示;这是 0.2.0 的已知限制。

安装后可从桌面或开始菜单启动。后续稳定版更新在客户端 Settings -> 关于与更新 中完成:检查更新、查看目标版本和 release notes,在没有 queued/running 对局时点击“下载并重启更新”。

### 环境要求

- **Python 3.12+** — 无需任何第三方包。
- **Qt 6.8+ 与 CMake 3.16+** — 仅构建桌面客户端时需要。

### 一键启动(Windows)

```bat
python launch-theater.py
```

自动启动本地 observer server(如未运行)、构建并打开 Qt 客户端,落在主页视图——从那里发起对局。请按你机器上的 Qt 安装路径修改 `launch-theater.py` 顶部的 `QT_BIN` / `MINGW_BIN` / `CMAKE` 常量。

### 手动启动

```powershell
# 1. 启动 observer server
$env:PYTHONPATH='src'
python -m werewolf_eval.run_observer_server --host 127.0.0.1 --port 8765 --runs-dir .runs --allow-live-api

# 2. 构建 Qt 客户端
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug

# 3. 运行客户端
.\.tmp\qt-observer-build\appqt_observer.exe --observer-base-url http://127.0.0.1:8765
```

### 接入真实 AI 对局

离线确定性模式是无条件默认,不需要任何 key。要跑真实对局:

1. 用 `--allow-live-api` 启动 server(一键启动器已带此参数)。
2. 在 Qt 客户端的设置页填入你的供应商 API key(仅存本地、界面打码显示、绝不写日志或导出)。
3. 在对局配置页解锁 LIVE 模式并发车。`SYS: LIVE_API / SIMULATION` HUD 徽章始终显示实际执行真相。

`live-check.bat` 可端到端跑一局真实 DeepSeek 对局(需要 `DEEPSEEK_API_KEY`,会产生真实 API 费用)。

### 运行测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

约 1000 个测试覆盖引擎、action runtime、observer 协议、provider、评分、不变量,以及 Qt↔Python 静态契约。Qt 侧测试:`ctest --test-dir .tmp/qt-observer-build`。

## 仓库结构

| 路径 | 内容 |
|------|------|
| `src/werewolf_eval/` | Python 后端:涌现引擎、`action_runtime/`(能力系统)、provider 与注册表、observer server、事件/日志 schema 与校验、评分与归因、`invariants/` 安全网、`ablation/` 实验台 |
| `clients/qt_observer/` | Qt 6 / QML 剧场客户端([客户端 README](clients/qt_observer/README.md)) |
| `tests/` | Python 测试套件(80 个文件) |
| `tools/`、`scripts/` | live 验证与开发/冒烟工具 |
| `docs/` | 项目文档——从 [`PROJECT_MAP.md`](docs/PROJECT_MAP.md) 开始读 |
| `launch-theater.py` / `.bat` | server + 客户端一键启动器 |

## 项目状态与路线图

| 阶段 | 范围 | 状态 |
|------|------|------|
| **P1 — 数据与事件地基** | 日志 schema/校验/评分/归因、引擎与 provider 契约、实时事件骨架、observer 协议 + server | ✅ 完成 |
| **P2 — 观战式 AI-vs-AI 对局客户端** | 涌现引擎、BYO-key 多供应商配置、实时剧场 UI、结算战报 | ✅ 完成 |
| **P3 — 评测 · 复盘 · 排行榜** | 结算深化为逐人复盘;每角色 AI 胜率排行榜 | ⏳ 计划中 |

[`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md) 是权威产品地图(阶段视图 + 系统视图)。

## 文档索引

| 文档 | 作用 |
|------|------|
| [PROJECT_MAP](docs/PROJECT_MAP.md) | **权威** — 产品阶段、模块状态、系统视图(SYS-xx) |
| [PRODUCT_ONE_PAGER](docs/PRODUCT_ONE_PAGER.md) | 产品定义:用户、输入、输出、价值 |
| [TASKS](docs/TASKS.md) | 压缩任务索引 |
| [DESIGN](DESIGN.md) | UI / QML 视觉方向 |
| [Specs](docs/superpowers/specs/) | 重要切片的设计规格 |
| [Plans](docs/superpowers/plans/) | 当前实现计划 |
| [ADRs](docs/adr/) | 架构决策(observer 协议、action runtime 编排器) |
| [Qt 客户端 README](clients/qt_observer/README.md) | 剧场客户端的构建、运行与测试 |
| [EVALUATION_RUBRIC](docs/EVALUATION_RUBRIC.md) | 评分体系参考(P3) |

## 项目背景

项目源于一个多智能体系统课题:构建能自主完成信息不对称博弈的狼人杀 AI Agent Team——每个 Agent 按角色拥有独立目标、策略与行动空间,在严格信息隔离约束下推理、发言、决策;系统需要完整对局引擎、结构化全程可观测,以及观战 UI。项目从「评测 + 复盘」方向出发(对结构化日志做确定性评分),逐步生长为上述实时实验平台:先把对局跑起来、把一切看清楚,再在同一套可审计数据之上做评测。

# Werewolf-agent

**一个可参与、可观战、可审计的狼人杀 Agent Theater。**

开局前配置 AI Agent 座位,以上帝视角实时观战整局推理与博弈,结束后查看结算战报——每一次决策、发言、投票背后都有完整可审计的事件日志。AI-vs-AI 是默认实验形态;真人控制座位是当前 P3 方向的一等能力。

简体中文 | [English](README.md)

---

## 这是什么?

Werewolf-agent 是一个 **client-agnostic 的狼人杀 Agent Theater**。Python 对局引擎驱动 6 人社交推理局,所有座位都处于严格的信息隔离之下——狼人不知道谁是预言家、预言家的查验结果只有自己可见,并且每个座位的上下文可被证明只由它有权看到的事件构建。

对局既可以完全离线运行(确定性 fake provider,默认模式),也可以接入真实 LLM API 实时对战。当前默认产品路径是 AI-vs-AI;新路线优先增强角色扮演 Agent,在 P3 接入真人控制座位,并设计 Flutter-first 移动/桌面客户端。每局都会产出结构化、可重放的事件流,支撑观战、结算战报、历史回放与后续评测。

## 核心特性

- **涌现式对局引擎** — 6 人局(2 狼人、1 预言家、1 女巫、2 村民):狼人共识刀人、预言家查验、女巫救/毒、白天发言、投票、处决、胜负裁决。动态回合、无剧本。猎人角色变体已在 action runtime 中实现(`rules_v1_1`)。
- **自带 AI(BYO-key)** — 按座位配置 provider/模型/prompt/温度。内置预设:DeepSeek、OpenAI、Anthropic,以及 9 家 OpenAI 兼容厂商(智谱 GLM、Moonshot、通义千问、MiniMax、SiliconFlow、xAI、Gemini、ModelScope、OpenRouter),并支持完全自定义端点。API key 始终留在本机;只有本地 Python server 会调用供应商接口。
- **当前 Qt 剧场客户端** — 上帝视角实时观战(座位环、发言剧场、证据控制台、播放控制)、对局配置沙盘、剧场内结算覆盖层与滚动战报、历史对局回看与管理。它保留为 legacy 桌面客户端,直到 Flutter-first 跨平台客户端达到基本 parity。
- **Flutter-first 玩家客户端** — 移动优先的 Flutter 客户端已经可以通过 observer/participant 协议加入 profile 绑定的真人座位,提交发言、投票和角色动作,并接入 Android Internal/Production 更新通道。当前默认连接 PaleInk 公网 observer 方便早期真机冒烟,也支持切回本机开发服务。
- **诚实链路** — 事件溯源日志(`events.jsonl`、快照、prompt manifest、provider 调用链、故障审计)、执行真相 HUD(`LIVE_API` vs `SIMULATION`)、可见性投影(上帝/公开/各角色视角),以及在信息泄漏或规则违例时立刻报错的运行时不变量。
- **Agent 优先、玩家优先路线** — P3 当前聚焦角色卡、单局记忆、Agent harness、桌面发言、真人座位,以及 Flutter-first 移动/桌面跨平台客户端;评测、复盘、排行榜后移到 P4。
- **评测地基就绪** — 确定性评分、规则归因、带分臂指标的消融实验台、字节锁定的 prompt 版本化与修订台账、差分测试、固定种子的确定性模拟。
- **零依赖后端** — Python 后端只用标准库,跑离线对局无需 `pip install` 任何东西。

## 架构

```text
YAML 运行 profile(座位控制器 / AI profile / prompt / 角色洗牌)
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
  · legacy 桌面客户端,保留到 Flutter parity
        │
        ▼
Flutter-first 跨平台客户端                         clients/flutter_app/
  · 移动优先真人座位 · 实时房间 · 桌面扩展
  · Android 远程更新通道
  · 复用同一 observer 协议,不直连 provider
```

observer 协议是硬边界:任何客户端(现在是 Qt,下一步是 Flutter)消费同一套 REST/SSE 接口,绝不接触引擎内部实现或 provider 密钥。

## 快速开始

### Windows 桌面安装

普通桌面用户只需要从主仓库 GitHub Releases 下载 `Werewolf-agent-0.2.0-Setup.exe` 并运行一次。其他 release assets 是更新器使用的包和索引,体验者不需要手动选择。程序安装到 `%LOCALAPPDATA%\WerewolfAgent\current\`,对局、profiles、configs、logs、凭证和设置保留在 `%LOCALAPPDATA%\Werewolf-agent\` 或 Windows 用户存储中。

首次公开 Windows 安装包暂未做代码签名。安装前 Windows 可能显示“未知发布者”或 SmartScreen 提示;这是 0.2.0 的已知限制。

安装后可从桌面或开始菜单启动。后续稳定版更新在客户端 Settings -> 关于与更新 中完成:检查更新、查看目标版本和 release notes,在没有 queued/running 对局时点击“下载并重启更新”。

### Android Flutter 客户端

Flutter Android 客户端是移动优先的真人参与入口。它只连接
observer/participant REST+SSE 协议;不读取本地对局 artifact,不调用模型供应商,
也不接触 provider API key。

早期真机包默认连接 PaleInk 公网 observer:

```text
http://api.paleink.cc:8765
```

这个地址目前是 HTTP 开发/冒烟目标。接入 HTTPS 与访问控制前,不要通过它提交真实
provider key。本机开发时,在 App 的 Settings -> Connection 里切换到 Local Dev,
或填写运行 Python observer server 的电脑局域网地址。

Android APK 更新分两个通道:

- Internal manifest: `https://liaoszong.github.io/Werewolf-agent/updates/internal.json`
- Production manifest: `https://liaoszong.github.io/Werewolf-agent/updates/stable.json`

发布流程、签名 secret 配置和已发布 APK 证据见
[`docs/release/android-update-channels.md`](docs/release/android-update-channels.md)。
公网 observer 的 Docker 部署见 [`deploy/README.md`](deploy/README.md)。

### 环境要求

- **Python 3.12+** — 无需任何第三方包。
- **Qt 6.8+ 与 CMake 3.16+** — 仅构建桌面客户端时需要。
- **Flutter stable + Android SDK** — 仅本地构建 Flutter Android 客户端时需要。

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

### Docker 部署 observer server

移动端公网入口可以用 Docker 部署 observer server:

```bash
cd deploy
sudo docker compose up -d --build
curl http://api.paleink.cc:8765/health
```

compose 服务会暴露 `8765` 端口,并把对局数据持久化到 Docker volume
`werewolf_runs`。完整服务器部署、升级和验证命令见
[`deploy/README.md`](deploy/README.md)。当前 HTTP 入口只适合早期测试;提交真实
provider key 前,应先加 HTTPS 和访问控制。

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

Flutter 客户端检查:

```bash
cd clients/flutter_app
flutter pub get
dart analyze
flutter test
```

## 仓库结构

| 路径 | 内容 |
|------|------|
| `src/werewolf_eval/` | Python 后端:涌现引擎、`action_runtime/`(能力系统)、provider 与注册表、observer server、事件/日志 schema 与校验、评分与归因、`invariants/` 安全网、`ablation/` 实验台 |
| `clients/qt_observer/` | 当前 Qt 6 / QML 剧场客户端;作为 legacy 桌面表面保留到跨平台 parity([客户端 README](clients/qt_observer/README.md)) |
| `clients/flutter_app/` | Flutter-first 移动/桌面客户端:真人座位、实时房间、Android 更新检查 |
| `deploy/` | 面向移动端冒烟的公网 observer Docker Compose 部署 |
| `tests/` | Python 测试套件(80 个文件) |
| `tools/`、`scripts/` | live 验证与开发/冒烟工具 |
| `docs/` | 项目文档——从 [`PROJECT_MAP.md`](docs/PROJECT_MAP.md) 开始读 |
| `launch-theater.py` / `.bat` | server + 客户端一键启动器 |

## 项目状态与路线图

| 阶段 | 范围 | 状态 |
|------|------|------|
| **P1 — 数据与事件地基** | 日志 schema/校验/评分/归因、引擎与 provider 契约、实时事件骨架、observer 协议 + server | ✅ 完成 |
| **P2 — 观战式 AI-vs-AI 对局客户端** | 涌现引擎、BYO-key 多供应商配置、实时剧场 UI、结算战报 | ✅ 完成 |
| **P3 — Agent 角色体验 · 真人参与 · 跨平台客户端** | 角色卡、单局记忆、roleplay harness、桌面发言、真人座位、Flutter-first 移动/桌面客户端 | 🚧 当前方向 |
| **P4 — 评测 · 复盘 · 排行榜** | 结算深化为复盘分析;按模型、角色、Agent Card、记忆策略排行 | ⏳ 后移 |

[`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md) 是权威产品地图(阶段视图 + 系统视图)。

## 文档索引

| 文档 | 作用 |
|------|------|
| [PROJECT_MAP](docs/PROJECT_MAP.md) | **权威** — 产品阶段、模块状态、系统视图(SYS-xx) |
| [PRODUCT_ONE_PAGER](docs/PRODUCT_ONE_PAGER.md) | 产品定义:用户、输入、输出、价值 |
| [TASKS](docs/TASKS.md) | 压缩任务索引 |
| [DESIGN](DESIGN.md) | UI 方向:新跨平台表面 + legacy Qt 维护边界 |
| [Specs](docs/superpowers/specs/) | 重要切片的设计规格 |
| [Plans](docs/superpowers/plans/) | 当前实现计划 |
| [ADRs](docs/adr/) | 架构决策(observer 协议、action runtime 编排器) |
| [Qt 客户端 README](clients/qt_observer/README.md) | 剧场客户端的构建、运行与测试 |
| [Android update channels](docs/release/android-update-channels.md) | Flutter Android Internal/Production 更新与发布流程 |
| [Observer Docker deploy](deploy/README.md) | 面向移动端测试的公网 observer 部署 |
| [EVALUATION_RUBRIC](docs/EVALUATION_RUBRIC.md) | 评分体系参考(P4) |

## 项目背景

项目源于一个多智能体系统课题:构建能自主完成信息不对称博弈的狼人杀 AI Agent Team——每个 Agent 按角色拥有独立目标、策略与行动空间,在严格信息隔离约束下推理、发言、决策;系统需要完整对局引擎、结构化全程可观测,以及观战 UI。项目先从「评测 + 复盘」方向生长出可审计运行地基,现在路线转向更强的 Agent 角色体验:角色卡、单局记忆、桌面发言、阵营计划,以及 P3 真人玩家进入同一套可审计对局循环。

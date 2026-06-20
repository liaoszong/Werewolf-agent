# R0: Windows Distribution Baseline — Design Spec

**Status:** Design approved, pending owner review
**Date:** 2026-06-20
**Scope:** P2 完成 → P3 开始前的发行版基础设施

---

## 1. 目标 / 非目标 / Release Scope

### 目标

1. 产出 Windows x64 安装器，用户一键安装即可运行
2. 首次完整安装后形成 `C:\Program Files\Werewolf-agent\` 的程序目录
3. 支持 Qt IFW maintenance tool 在线更新（stable / preview 双通道）
4. 用户数据与程序安装目录彻底隔离（`%LOCALAPPDATA%\Werewolf-agent\`）
5. 升级不丢 runs、saved configs、logs、Windows Credential Manager 凭证
6. 更新不得静默打断正在进行的对局
7. 显式手动触发更新，不实现静默热更新
8. 卸载默认保留全部用户数据

### 非目标

- 代码签名、MSI/MSIX、macOS/Linux 发行版
- GitHub Release 自动发版 CI
- 静默/热更新、后台轮询、系统通知、自动下载
- 应用内 stable ↔ preview 通道切换
- Downgrade / 版本回退
- 多 client 同服、多窗口协调
- 外部 server 连接支持（release host 只管理 owned server）
- 代码签名 / EV 证书

### Release Scope

- R0 初始版本：`0.2.0`
- `0.2.x` = 兼容 bugfix / 小型体验修正
- `0.3.0+` = P3 或后续阶段产物进入发行版

---

## 2. 不变量

### 架构不变量

| I-01 | Qt client 只通过 observer REST/SSE 通信，不直接绑定 Python runtime |
| I-02 | Python server 仍拥有 engine/provider 调用 |
| I-03 | fake deterministic 必须无 key 可运行 |
| I-04 | 真实 API key 不能进入 logs、runs、导出配置、安装包、更新包或错误输出 |
| I-05 | P3 会消费 P2 产生的历史 run artifacts，升级不能误删或静默破坏历史数据 |
| I-06 | Windows Credential Manager 存储边界不可破坏（target: `WerewolfAgent/byokey/<provider>`） |
| I-07 | QSettings 只存非敏感数据（provider index、base_url），raw key 永不进 QSettings |

### 发行版新不变量

| R-01 | 用户可见唯一入口是 `Werewolf-agent.exe`（bootstrapper） |
| R-02 | 所有程序路径基于 bootstrapper 所在安装目录解析，不依赖 cwd、`F:\Qt`、开发环境变量 |
| R-03 | 所有用户可写数据进入 `%LOCALAPPDATA%\Werewolf-agent\`，不写入安装目录 |
| R-04 | 每 Windows 用户一个 release host、一个 owned server、最多一个 Qt client |
| R-05 | 关闭 client 不等于 interrupt active run；interrupt 只能来自用户明确确认的动作 |
| R-06 | 更新由 Qt IFW maintenance tool 执行，应用内不自行下载或替换文件 |

---

## 3. 发行架构

### 进程职责边界

```
┌─────────────────────────────────────────────────────────┐
│ Werewolf-agent.exe  (Python + PyInstaller onedir)       │
│                                                         │
│  · 用户数据目录初始化                                      │
│  · 单实例 mutex + loopback TCP control endpoint           │
│  · Owned observer server 生命周期                         │
│  · Qt client 子进程生命周期                                │
│  · Health 轮询 + owner token 交叉验证                      │
│  · Update request 消费与 maintenance tool 拉起             │
│  · 无密钥诊断日志                                          │
│  · 不包含 game rules / provider / observer server 逻辑     │
└──────┬──────────────────────────────────────────────────┘
       │ spawn
       ▼
┌──────────────────────────────────────────────────────────┐
│ observer-server.exe  (Python + PyInstaller onedir)       │
│                                                          │
│  · werewolf_eval 全量 + observer 子模块                    │
│  · 动态 loopback port bind                                │
│  · 原子写入 server-state.json                              │
│  · 业务逻辑与现有 observer server 一致                      │
└──────┬───────────────────────────────────────────────────┘
       │ HTTP REST/SSE on 127.0.0.1:<dynamic-port>
       ▼
┌──────────────────────────────────────────────────────────┐
│ appqt_observer.exe  (Qt 6 Release + windeployqt tree)    │
│                                                          │
│  · 纯观战客户端，只通过 observer protocol 通信               │
│  · 不接触 Python runtime / engine / provider              │
│  · --observer-base-url 由 host 传入                       │
│  · --release-host-session 用于 update request 绑定        │
│  · CredentialStore 存/取 Windows Credential Manager       │
└──────────────────────────────────────────────────────────┘
```

### Host-Server-Client 启动序列

```
用户启动 Werewolf-agent.exe
│
├─[1] 尝试获取 per-user named mutex "WerewolfAgentHost"
│   └─ 失败 → 连接 control TCP → 发送 open_or_foreground_client → 退出
│
├─[2] 初始化 %LOCALAPPDATA%\Werewolf-agent\
│   ├─ runs/ profiles/ configs/ logs/ runtime-state/
│   └─ 写入初始 host-control.json（原子）
│
├─[3] 检查 runtime-state\server-state.json
│   ├─ 存在 + health 验证 + owner token 匹配 → 接管 orphan server
│   └─ 否则 → 启动新 owned server
│
├─[4] 启动 observer-server.exe（动态 loopback port）
│   ├─ host 传入: --host 127.0.0.1 --port 0 --runs-dir ... --profiles-dir ... --configs-dir ...
│   │             --runtime-state-file <path> --release-owner-token <nonce> --release-version <version>
│   ├─ server bind 后原子写入 server-state.json（server 为唯一写入者）
│   ├─ host 读取 server-state.json 获取实际 port
│   ├─ Health 轮询（最长 30s，间隔 500ms）
│   └─ host 通过 /health 返回的 instance_id + owner_token 交叉验证
│
├─[5] Server 成功 bind 后原子写入 server-state.json
│   └─ host 仅读取验证，不二次覆盖
│
├─[6] 启动 Qt client
│   └─ --observer-base-url http://127.0.0.1:<port>
│      --release-host-session <uuid>
│      --update-request-path <path>
│
└─[7] 等待 client 退出 → 生命周期收口（见 §4）
```

---

## 4. Bootstrapper 状态机

### 正常退出路径

```
client 退出
│
├─ 有 active run（queued / running）
│   → keep server alive
│   → 不 interrupt
│   → host 保持 supervising
│   → 记录 client_exited_with_active_runs marker
│   → 允许通过 host IPC 重新打开 client
│   → 进入 active-run keepalive 模式
│
├─ 无 active run + 有 valid update request
│   → 优雅停止 owned server
│   → 清理本 session runtime-state
│   → 启动 maintenancetool.exe
│   → host 退出
│
└─ 无 active run + 无 update request
    → 优雅停止 owned server
    → 清理本 session runtime-state
    → host 退出
```

### Active-run keepalive → idle cleanup

```
所有 run 进入终态 (completed / failed / interrupted)
│
├─ 进入 30s idle grace period
│   ├─ grace 内收到 open_or_foreground_client → 取消 timer，启动 client
│   ├─ grace 内收到 valid update request → 取消 timer，停止 server，启动 maintenance tool
│   └─ grace 到期无新请求 → 优雅停止 server，host 退出
```

30 秒仅适用于"client 已关闭，之前因 active run 保活，现所有 run 终态"这一场景。
以下情况不进入 30 秒 grace：client 仍在运行、server crashed、有 active run、有 update request 等待消费。

### 异常路径

| 场景 | 行为 |
|---|---|
| **Client crash** | host 检测子进程异常退出；有 active run → server 继续、不 interrupt、不自动重启 client；无 active run → 正常停止 server |
| **Server crash** | host 不自动重启 server；写入 recovery marker；client 显示运行时已停止；下次 host 启动时 server 消费 stale-runtime 信号，将 queued/running → interrupted（reason: `unexpected_server_exit_recovery`）；**host 不直接扫描或修改 run artifact** |
| **Host 被 taskkill** | server 继续运行（非子进程绑定）；下次 host 通过 state + health token 接管 orphan server |
| **Host + server 都消失** | 下次 host 启动走 server-owned interrupted recovery |
| **Stale state file + health 失败** | 清理 state，走 server-owned unfinished-run recovery |
| **外部/开发 server 在端口上** | 不复用、不 kill、不 interrupt、不更新 |

### 禁止行为

- 按旧 pid 直接 taskkill
- 将 pid 作为所有权证明
- host 直接扫描或修改 run artifact
- client 关闭自动等价于 interrupt active run
- 将开发 launcher 的 `_interrupt_active_runs` + `server.terminate` 语义照搬到 release host

---

## 5. 目录布局

### 安装目录（只读/程序文件）

```
C:\Program Files\Werewolf-agent\
├── Werewolf-agent.exe              # bootstrapper（用户唯一入口）
├── _internal\                       # PyInstaller bootstrapper runtime
├── app\                             # Qt client（windeployqt 产物）
│   ├── appqt_observer.exe
│   ├── Qt6Quick.dll
│   ├── Qt6Network.dll
│   ├── ...（所有 Qt DLL + plugins + QML modules）
│   └── qml\
├── runtime\                         # frozen observer server
│   ├── observer-server.exe
│   └── _internal\                   # PyInstaller server runtime
├── maintenancetool.exe              # Qt IFW（安装器创建）
├── maintenance.dat                  # Qt IFW 内部状态
└── components.xml                   # Qt IFW 组件清单（IFW 自动管理）
```

### 用户数据目录（可写，`%LOCALAPPDATA%\Werewolf-agent\`）

```
%LOCALAPPDATA%\Werewolf-agent\
├── runs\                    # --runs-dir
├── profiles\                # 可直接启动的对局配置（<name>.json）
├── configs\                 # 带元数据的用户命名收藏库
├── logs\                    # server stdout/stderr + bootstrapper 日志
│   ├── server.log
│   ├── server.err.log
│   └── bootstrapper.log
├── runtime-state\               # host/server 运行时状态
│   ├── host-control.json        # IPC 发现引导（host 写入）
│   ├── server-state.json        # owned server 状态（server 唯一写入）
│   ├── update-request.json      # 一次性更新请求（client 写入，host 消费）
│   └── unexpected-server-exit.json  # recovery marker（host 写入，server 消费）
└── update-cache\            # Qt IFW 下载缓存（可安全清除）
```

### 目录职责边界

| 目录 | 类型 | 卸载默认 | 删除本地数据 |
|---|---|---|---|
| `runs/` | 对局产物 | 保留 | 删除 |
| `profiles/` | 用户可复用配置 | 保留 | 删除 |
| `configs/` | 用户命名收藏库 | 保留 | 删除 |
| `logs/` | 诊断日志 | 保留 | 删除 |
| `runtime-state/` | 运行时临时状态 | 保留 | 删除 |
| `update-cache/` | IFW 缓存 | 保留 | 删除 |

### runtime-state 文件职责

| 文件 | 写入者 | 读取者 | 删除者 | 说明 |
|---|---|---|---|---|
| `host-control.json` | host（唯一） | 第二实例（启动发现） | host 退出时 | 仅作为 IPC 发现引导，非所有权证明 |
| `server-state.json` | server（唯一） | host（验证+接管） | host（stale 时清理） | host 不二次覆盖 |
| `update-request.json` | Qt client（唯一） | host（唯一消费） | host（消费后立即删除） | 一次性，5min TTL |
| `unexpected-server-exit.json` | host（server crash 时） | server（下次启动） | server（消费后） | recovery marker |

每个文件的约束：

- **owner**：唯一写入者，其他进程不覆盖
- **原子写入**：write-tmp + rename
- **stale 判断**：token/session 不匹配、超时、health 失败
- **删除责任**：明确谁在何时删除
- **不可包含**：API key、run 内容、provider 配置、repository URL

### profiles vs configs

- **profiles**：可直接启动的原始对局 profile。文件名为 `<name>.json`。API: `GET /api/profiles`、`GET /api/profiles/{name}`、`POST /api/profiles/validate`。Schema: `g2d.profile.v1`。
- **configs**：带 display_name / id / created_at / updated_at / import-export 元数据的用户命名收藏库。内部 `profile` 字段即为完整 profile。API: `GET /api/configs`、`GET /api/configs/{id}`、`GET /api/configs/{id}/export`、`POST /api/configs`、`POST /api/configs/import`。Schema version: 1, Kind: `werewolf_agent.match_config`。
- 两者保持独立平级目录，不在 R0 合并或重构语义。

### 不写入用户数据目录的内容

- API key（在 Windows Credential Manager）
- 程序文件
- 安装包
- git 仓库元数据

### 不进入安装包的内容

- `.runs`、profiles、configs、logs
- `.env`、开发密钥
- 测试 artifact、git 元数据
- 构建缓存（`.tmp/`、`__pycache__/`、`build/`）
- synthetic sentinel: `R0_TEST_SECRET_SENTINEL_DO_NOT_SHIP`

---

## 6. 版本号体系

### 单源权威

仓库根目录 `VERSION` 文件，内容为用户可见 release version：

```
0.2.0
```

### 版本推导

| 消费方 | 方式 |
|---|---|
| CMake (`project VERSION`) | `file(READ "${CMAKE_SOURCE_DIR}/../../VERSION" VER)` |
| Python bootstrapper / server | 统一 release metadata helper，从各自 frozen executable 所在 distribution root 的明确 metadata 文件读取。禁止各模块自行猜 `__file__` 层级；具体使用 `sys.executable` 所在目录、`sys._MEIPASS` 或 package resource，由 portable smoke 验证 |
| Qt UI About 显示 | host 启动 client 时传入 `--release-version`，或 server `/api/runtime/capabilities` 扩展 |
| Run artifact `release-manifest.json` | server 在 run 目录创建成功后原子写入（见 §9b） |
| IFW `config.xml` `<Version>` | 构建时从 VERSION 模板替换 |
| IFW `package.xml` `<Version>` | 构建时模板替换 |

### 版本关系

| 概念 | 来源 | 说明 |
|---|---|---|
| `app_version` | VERSION | 统一产品版本 |
| `observer_protocol_version` | 代码常量 | 独立于 app_version，协议契约 |
| `rules_version` | run manifest | 对局规则版本，独立 |
| `prompt_version` | prompt manifest | prompt 字节锁版本，独立 |
| `scoring_version` | `evaluation_versions.py` | 评分公式版本，独立 |
| `PROFILE_SCHEMA_VERSION` | `profile_config.py` | profile 格式版本，独立 |

`app_version` 不与 observer protocol / rules / prompt / scoring / profile schema 版本耦合。

### Stable / Preview 版本规则

| | Stable | Preview |
|---|---|---|
| `VERSION` | `0.2.0` | `0.2.0` |
| Display version | `0.2.0` | `0.2.0 Preview N` |
| IFW component version | `0.2.0` | `0.2.0-N` |
| IFW repository URL | stable repo | preview repo |
| Installer | 只含 stable repo | 只含 preview repo |
| 通道切换 | 不支持 | 不支持 |

构建时参数（channel、preview sequence、git commit、build timestamp）写入 release manifest，不写回 VERSION。

### 版本递增规则

- **patch**（`0.2.0 → 0.2.1`）：兼容 bugfix / 小型体验修正
- **minor**（`0.2.0 → 0.3.0`）：兼容新增功能（如 P3 一组完整可见能力）
- **major**（`0.2.0 → 1.0.0`）：不兼容的用户数据、协议或公开配置契约变化。必须写迁移策略、阻断策略或只读兼容策略，不静默读取错误。

---

## 7. Host-Instance Control RPC

### 协议

纯 Python stdlib loopback TCP，host 绑定 `127.0.0.1` 动态端口（port 0）。

### 端点发现

```json
// %LOCALAPPDATA%\Werewolf-agent\runtime-state\host-control.json
{
  "schema_version": 1,
  "host_session_id": "<uuid>",
  "host_pid": 12345,
  "control_port": 54321,
  "control_token": "<random-64-char-hex-nonce>",
  "release_version": "0.2.0",
  "started_at": "2026-06-20T10:30:00Z"
}
```

- 原子写入
- `control_token` 是本机同用户会话 nonce，不是 observer server 鉴权 token
- 不得打印到日志、UI、crash report 或 run artifact
- Stale state / 连接超时 / token 不匹配 → 走 stale-host recovery，不 kill 对应 pid

### 消息

仅两个 message type：

**Request:**
```json
{"schema_version": 1, "type": "open_or_foreground_client", "host_session_id": "<uuid>", "control_token": "<nonce>"}
```

**Response (success):**
```json
{"schema_version": 1, "ok": true, "action": "foregrounded"}
```
或
```json
{"schema_version": 1, "ok": true, "action": "client_started"}
```

**Response (error):**
```json
{"schema_version": 1, "ok": false, "code": "host_unavailable"}
```

**Ping（仅诊断）:** `{"type": "ping"}` → `{"ok": true, "action": "pong"}`

### 传输约束

- 一连接一 request / 一 response 后关闭
- 单行 UTF-8 JSON，最大 4 KiB
- connect / read / write 超时 2 秒
- 不支持流式、订阅、重连、批量
- 未知 message type → 拒绝
- 不允许将 API key、provider 配置、run 内容、server token、repository URL 写入 IPC payload 或日志

---

## 8. Update Request 契约

### Schema

```json
// %LOCALAPPDATA%\Werewolf-agent\runtime-state\update-request.json
{
  "schema_version": 1,
  "request_id": "<uuid>",
  "host_session_id": "<uuid>",
  "client_pid": 12345,
  "created_at": "2026-06-20T10:30:00Z",
  "release_version": "0.2.0",
  "action": "launch_maintenance_tool"
}
```

### 生命周期

1. Qt client 写入（路径由 `--update-request-path` 传入），原子写入 + 5 分钟 TTL
2. Client 退出
3. Bootstrapper 消费条件（**全部满足**）：
   - host_session_id 匹配当前 session
   - client 正常退出
   - 无 active run
   - owned server 已停止
   - request 未超时（5 分钟）
4. 消费后立即删除
5. 以下情况删除 + 脱敏记录，不启动 maintenance tool：
   - session 不匹配
   - 超时
   - client crash
   - host restart
   - 格式错误
   - 有 active run
   - action 不为 `launch_maintenance_tool`

### 不被包含的内容

request 不存 API key、run 内容、provider 配置、repository URL、长期状态。

---

## 9. Server State 契约

**写入者：observer server（唯一），host 只读取验证。**

Server 通过 `--runtime-state-file` 参数接收 state 文件路径，bind 到动态端口后原子写入。

```json
// %LOCALAPPDATA%\Werewolf-agent\runtime-state\server-state.json
{
  "schema_version": 1,
  "instance_id": "<uuid>",
  "pid": 12346,
  "port": 54322,
  "owner_token": "<random-64-char-hex-nonce>",
  "release_version": "0.2.0",
  "observer_protocol_version": "<version>",
  "data_root": "C:\\Users\\...\\AppData\\Local\\Werewolf-agent",
  "started_at": "2026-06-20T10:30:01Z"
}
```

- Server 唯一写入，host 不二次覆盖
- Host 启动 server 时传入：`--runtime-state-file`、`--release-owner-token`、`--release-version`
- `/health` 返回 `instance_id`、`owner_token`、`release_version`、`protocol_version`
- Host 通过 health endpoint 交叉验证 owner token
- `owner_token` 不得包含 API key
- Stale state + health 失败 → host 清理 state 文件，走 recovery

### 9b. Run-Level Release Manifest

**写入者：observer server，在 run 目录创建成功、run_id 已确定后原子写入。**

```json
// <run_dir>/release-manifest.json
{
  "schema_version": 1,
  "release_version": "0.2.0",
  "channel": "stable",
  "git_commit": "<build commit sha>",
  "build_timestamp": "2026-06-20T10:30:00Z",
  "bootstrapper_version": "0.2.0",
  "server_version": "0.2.0",
  "observer_protocol_version": 1,
  "created_at": "2026-06-20T10:30:05Z"
}
```

- 写入时机：run 目录创建成功后立即写入，与其他 artifact（resolved-profile.json、status.json）同生命周期
- 原子写入；写入失败必须让该 run 创建失败或进入明确失败状态，不能静默缺失
- 不进入 `prompt-manifest.json`，不进入 `evaluation_bucket`
- P3 读取时将其作为发行环境诊断信息，不作为评分/规则/prompt/artifact schema 的替代版本
- `release_version`、`channel`、`git_commit`、`build_timestamp` 由 host 通过 server 启动参数传入

注意与顶层构建产物 `distribution-manifest.json`（见 §11.5）区分：
- `distribution-manifest.json`：构建级，记录 installer / repository / component hash / build metadata
- `<run_dir>/release-manifest.json`：单局运行环境

---

## 10. Qt Client 启动参数

| 参数 | 用途 | 新增/已有 |
|---|---|---|
| `--observer-base-url` | observer server 地址 | 已有 |
| `--open-run` | 打开指定 run | 已有 |
| `--release-version` | About 页显示版本 + update request 绑定 | **新增** |
| `--release-host-session` | 绑定 update request 的 host session | **新增** |
| `--update-request-path` | update request 文件绝对路径 | **新增** |
| `--version` | 输出版本后退出 | **新增** |

Qt client 不接触 `control_token`，不决定 server 是否 owned。

### 协议边界

```
Qt client  ←→  observer server    : REST/SSE（既有，不变）
Qt client  ←→  host bootstrapper  : 无直接 IPC
              host bootstrapper   : 通过 child process lifecycle 获知 client 退出
              host bootstrapper   : 通过 observer API 确认 active run
              Qt client          : 写入 update-request.json（host 消费）
              host bootstrapper   : control TCP 仅用于第二实例发现
```

---

## 11. 打包

### 11.1 Qt Client — Release + windeployqt

```bash
cmake -S clients/qt_observer -B .tmp/qt-observer-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS_RELEASE="-O2 -DNDEBUG"
cmake --build .tmp/qt-observer-release --config Release

windeployqt.exe \
  --release \
  --qmldir clients/qt_observer/qml \
  --compiler-runtime \
  .tmp/qt-observer-release/appqt_observer.exe
```

产物：`app/` 目录含 `appqt_observer.exe` + Qt DLL + QML modules + plugins + MinGW runtime。

### 11.2 Observer Server — PyInstaller onedir

独立 PyInstaller `.spec`，关键配置策略：

```python
# observer-server.spec (概要)
a = Analysis(
    ['src/werewolf_eval/run_observer_server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('VERSION', '.'),                    # 版本单源
    ],
    hiddenimports=[
        'werewolf_eval.observer_server',
        'werewolf_eval.observer.handler',
        'werewolf_eval.observer.state',
        'werewolf_eval.observer.factory',
        'werewolf_eval.observer.run_manager',
        'werewolf_eval.observer.launch',
        'werewolf_eval.observer.sse',
        'werewolf_eval.observer.routes',
        'werewolf_eval.observer.credentials_api',
        'werewolf_eval.observer.security',
        'werewolf_eval.observer_protocol',
        'werewolf_eval.profile_config',
        'werewolf_eval.user_config_library',
        'werewolf_eval.action_runtime',
        'werewolf_eval.action_runtime.ruleset',
        'werewolf_eval.emergent_engine',
        'werewolf_eval.provider_agent',
        'werewolf_eval.provider_registry',
        'werewolf_eval.evaluation_versions',
        'werewolf_eval.deepseek_launcher',
        'werewolf_eval.run_emergent_fake_runtime',
        'werewolf_eval.run_g1h_fake_runtime',
        'werewolf_eval.credential_store',
        'werewolf_eval.invariants',
        # 以及所有被上述模块动态导入的子模块
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'pandas',
        # 排除不相关的 stdlib 测试模块
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
)

pyz = PYZ(a.pure)
exe = EXE(pyz, ...)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, ...)
```

### 11.3 Bootstrapper — PyInstaller onedir

独立 `.spec`，**不包含 `werewolf_eval`**。datas 含 `VERSION`。hiddenimports 仅限 stdlib（`http.server`、`json`、`socket`、`subprocess` 等）。

### 11.4 打包排除规则

以下内容**不得**进入任何 PyInstaller 产物或 installer payload：

- `.runs/`、`profiles/`、`configs/`、`logs/`
- `.env`、`*.key`、`*.pem`、credentials
- 测试目录：`tests/`、`clients/qt_observer/tests/`
- 构建产物：`.tmp/`、`__pycache__/`、`*.pyc`、`build/`、`dist/`
- git 元数据：`.git/`、`.gitignore`、`.gitattributes`
- 开发配置：`.codex/`、`.claude/`、`.oh-my-harness/`、`.agents/`
- 文档（除 VERSION 外）：`docs/`、`README.md`、`AGENTS.md`、`DESIGN.md`
- CI/CD：`.github/`
- 开发启动器：`launch-theater.py`、`launch-theater.bat`
- Synthetic sentinel: `R0_TEST_SECRET_SENTINEL_DO_NOT_SHIP`

### 11.5 Release Artifact 清单

每个 release 产出：

| Artifact | 说明 |
|---|---|
| `Werewolf-agent-0.2.0-stable-installer.exe` | stable hybrid installer |
| `Werewolf-agent-0.2.0-preview-1-installer.exe` | preview hybrid installer（如适用） |
| `stable-repository/` | `repogen` 输出的 stable 在线仓库 |
| `preview-repository/` | `repogen` 输出的 preview 在线仓库 |
| `distribution-manifest.json` | channel、version、git commit、build timestamp、component hashes（构建级清单） |

---

## 12. Qt Installer Framework

### 12.1 组件

单一主组件：`com.werewolfagent.app`

包含 bootstrapper + Qt client deployment tree + frozen observer server runtime。`maintenancetool.exe` 由 IFW 自动生成和管理。

### 12.2 产品元数据

- 产品名 / 安装器标题 / 开始菜单目录：`Werewolf-agent`
- 默认安装目录：`C:\Program Files\Werewolf-agent\`
- 桌面快捷方式：`Werewolf-agent.exe`
- 开始菜单快捷方式：`Werewolf-agent\Werewolf-agent`

### 12.3 config.xml.in（模板）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Installer>
    <Name>Werewolf-agent</Name>
    <Version>${IFW_COMPONENT_VERSION}</Version>
    <Title>Werewolf-agent</Title>
    <Publisher>Werewolf-agent</Publisher>
    <StartMenuDir>Werewolf-agent</StartMenuDir>
    <TargetDir>@ApplicationsDir@/Werewolf-agent</TargetDir>
    <MaintenanceToolName>maintenancetool</MaintenanceToolName>
    <AllowNonAsciiCharacters>true</AllowNonAsciiCharacters>
    <RepositorySettingsPageVisible>false</RepositorySettingsPageVisible>
    <RemoteRepositories>
        <Repository>
            <Url>${REPOSITORY_URL}</Url>
            <Enabled>1</Enabled>
        </Repository>
    </RemoteRepositories>
</Installer>
```

构建时替换：`${IFW_COMPONENT_VERSION}`、`${REPOSITORY_URL}`。仓库中不提交最终带真实 URL 的 config。

### 12.4 package.xml（模板）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package>
    <DisplayName>Werewolf-agent</DisplayName>
    <Description>AI-vs-AI Werewolf live experiment platform</Description>
    <Version>${IFW_COMPONENT_VERSION}</Version>
    <ReleaseDate>${RELEASE_DATE}</ReleaseDate>
    <Name>com.werewolfagent.app</Name>
    <Script>installscript.qs</Script>
    <Licenses>
        <License name="License Agreement" file="license.txt" />
    </Licenses>
</Package>
```

### 12.5 自定义安装脚本

`installscript.qs` 负责：
- 桌面快捷方式创建
- 开始菜单快捷方式创建
- 卸载时默认保留 `%LOCALAPPDATA%\Werewolf-agent\`
- 卸载选项「删除本地数据」= 删除 `%LOCALAPPDATA%\Werewolf-agent\`
- 文案：「删除本地对局、配置、日志与运行时数据」（不称"删除所有数据"）
- 不删除 Windows Credential Manager 凭证
- 不删除 QSettings 非敏感数据

### 12.6 IFW 产品文案

自定义页面文案提供中英文。IFW wizard chrome（Next/Back/Cancel/Install）英文 fallback。本地 IFW 4.11 不含预编译 `ifw_zh_CN.qm`，此限制写入 release known limitations，不为 R0 手写 IFW chrome 中文翻译。

### 12.7 在线仓库

**本地测试（R0 验收）：** `file:///` URI

**正式发布：** GitHub Pages static repository（独立 repo `werewolf-agent-updates`）

```
stable/
  Updates.xml
  com.werewolfagent.app/
    0.2.0/
      com.werewolfagent.app-0.2.0-meta.7z
      com.werewolfagent.app-0.2.0-content.7z
    0.2.1/
      ...
preview/
  Updates.xml
  com.werewolfagent.app/
    0.2.0-1/
      ...
```

URL: `https://<github-user>.github.io/werewolf-agent-updates/stable/`

该 repo 是公网可访问的（GitHub Pages 公开性质），不放源码、开发配置、密钥、runs、logs。

### 12.8 Repository Retention

- 保留当前及上一 minor 版本的全部 patch 版本
- 保证任意仍受支持的已发布版本可更新到当前最新
- 旧版本归档由发布者手动管理
- 控制 Pages 总大小 < 1 GB（每个 component archive ~30-50MB）

### 12.9 版本递增与更新

- IFW `<Version>` 使用数字段格式（`0.2.0`、`0.2.0-1`）
- 新版本号 > 旧版本号 → maintenance tool 发现更新
- 用户确认后 IFW 下载并原子替换安装目录
- 用户数据目录不受影响

### 12.10 更新失败策略

maintenance tool 启动失败、用户取消更新、下载失败或更新中止后：
- 已安装旧版本仍能正常启动
- `runtime-state/` 不留下阻断后续启动的残留
- runs/profiles/configs/Credential Manager 凭证不受影响

---

## 13. 应用内更新入口

### 13.1 UI 位置与内容

`ProviderSettingsView.qml` 底部新增「关于与更新」区域。

第一版内容：
- 产品名：Werewolf-agent
- 当前 release version（从 `GET /api/runtime/capabilities` 获取或 client 启动参数传入）
- 当前 channel（Stable / Preview）
- 简短说明：「通过系统更新工具检查可用更新」
- 主按钮：「检查更新」

### 13.2 状态

| 状态 | 显示 | 按钮 |
|---|---|---|
| 可检查更新 | 正常文本 | 可点击 |
| 有 active run | 「当前有进行中的对局，请等待对局结束后再检查更新」 | 禁用 |
| 正在退出 | 「正在退出并打开更新工具…」 | 禁用 |
| 无法请求 | 「无法启动更新工具，请查看日志」 | 禁用（可选重试） |

不显示应用自己推导的"已是最新版本"或"发现新版本"。

### 13.3 流程

1. 用户点击「检查更新」
2. Qt client 通过 observer API 确认 active run 状态
3. 有 active run → 阻止 + 提示
4. 无 active run → 写入 `update-request.json`（原子）→ client 正常退出
5. Bootstrapper 消费 request → 停止 server → 启动 `maintenancetool.exe`

### 13.4 i18n

所有新增文案接入现有 `I18n.qml` 中英切换。中文为主要文案，英文完整 fallback。

---

## 14. 安全与隐私边界

### 14.1 Key 保护

- API key 仅存 Windows Credential Manager
- 不在 logs、runs、configs、profiles、runtime-state、update-request、host-control、server-state 中出现
- 不在 installer payload、update repository archives、错误输出中出现
- PyInstaller bundle 不包含 key
- QSettings 只存非敏感数据

### 14.2 验证方法

使用 synthetic sentinel `R0_TEST_SECRET_SENTINEL_DO_NOT_SHIP`，验证不出现在：
- Installer payload
- Release payload 的任何文件
- Logs
- runtime-state JSON 文件
- Run artifacts
- Update repository archives
- 错误输出

不使 用真实 API key 做扫描样本。

### 14.3 日志脱敏

- Bootstrapper + server 日志不包含 API key
- Control IPC payload 不记录到日志
- Control token 不记录到日志
- Update request 内容不记录到日志（只记录"request consumed/deleted"事件）
- 错误消息不包含 key、token、repository URL

### 14.4 文件权限

`%LOCALAPPDATA%\Werewolf-agent\runtime-state\` 尽量限制为当前用户访问（Windows ACL）。

---

## 15. 已知限制

| ID | 限制 | 计划 |
|---|---|---|
| L-01 | IFW wizard chrome 英文 fallback，无预编译 `ifw_zh_CN.qm` | 后续版本调查 Qt IFW translations 获取方式 |
| L-02 | 不支持 stable ↔ preview 通道切换 | 后续独立设计任务 |
| L-03 | 不支持 downgrade / 版本回退 | 后续独立设计任务 |
| L-04 | 仅 Windows x64 | 后续按需扩展 |
| L-05 | 仅手动检查更新，无自动/后台检查 | 后续独立设计任务 |
| L-06 | 不连接外部/开发 server | 开发者仍可用 raw client / dev launcher |
| L-07 | 单 client / 单窗口 | 后续独立设计任务 |
| L-08 | 无代码签名 | 后续按需 |

---

## 16. 验收矩阵

### V1: Clean-machine 安装

| # | 测试 | 方法 |
|---|---|---|
| V1.1 | 无 Qt / 无 Python 的干净 Windows 安装成功 | 虚拟机或干净用户账户 |
| V1.2 | 桌面快捷方式指向 `Werewolf-agent.exe` | 安装后检查 |
| V1.3 | 开始菜单入口 `Werewolf-agent` → `Werewolf-agent` | 安装后检查 |
| V1.4 | 安装目录不含 `.runs`、`.env`、git 元数据、build cache、测试数据、synthetic sentinel | `dir /s` + 审计脚本 |
| V1.5 | `%LOCALAPPDATA%\Werewolf-agent\` 首次启动时自动创建 | 首次运行后检查 |
| V1.6 | 卸载默认保留 `%LOCALAPPDATA%\Werewolf-agent\` | 卸载后检查 |
| V1.7 | 卸载勾选「删除本地数据」后清理 `%LOCALAPPDATA%\Werewolf-agent\` | 卸载后检查 |
| V1.8 | 安装器自身不含 secrets、synthetic sentinel | 安装包审计 |
| V1.9 | 卸载「删除本地数据」不删除 Credential Manager 凭证 | 卸载后 `CredReadW` |
| V1.10 | 卸载「删除本地数据」不删除 QSettings 数据 | 卸载后 QSettings 读 |

### V2: Bootstrapper 生命周期

| # | 测试 | 方法 |
|---|---|---|
| V2.1 | host 启动 → server 动态端口 bind → server-state.json 原子写入 | 日志 + 文件验证 |
| V2.2 | host health + owner token 交叉验证通过后启动 client | 日志 |
| V2.3 | client 正常退出、无 active run、无 update request → server 停止 | 端到端 |
| V2.4 | client 正常退出、有 active run → server 继续保活 | 端到端 + 进程检查 |
| V2.5 | 第二次启动（已有 host）→ 前置已有 client 窗口 | 端到端 |
| V2.6 | 第二次启动（client 已关闭、server 仍在）→ 原 host 打开新 client | 端到端 |
| V2.7 | 不产生第二个 host、第二个 client、第二个 server | 进程计数 |
| V2.8 | client 崩溃、有 active run → server 继续、下次启动可恢复 | 模拟 crash |
| V2.9 | server 崩溃 → recovery marker → queued/running → interrupted | 模拟 crash |
| V2.10 | host 被 taskkill、server 仍活着 → 下次 host 接管 | 模拟 |
| V2.11 | client 关闭时 active run 存在 → 提示对局继续在后台运行 | 截图 + 日志 |

### V3: 更新

| # | 测试 | 方法 |
|---|---|---|
| V3.1 | 无 active run → client 退出 → host 启动 maintenance tool | 端到端 |
| V3.2 | 有 active run → 更新被阻止、显示明确提示 | UI 验证 |
| V3.3 | update-request 旧 session / 超时 / 格式错误 → 删除不触发 | 注入异常 request |
| V3.4 | host 重启不消费旧 session 的 valid request | 重启验证 |
| V3.5 | maintenance tool 从 `file://` repo 发现并安装更新 | file repo 端到端 |
| V3.6 | 更新后 `%LOCALAPPDATA%\Werewolf-agent\` 数据完整 | 更新前后对比 |
| V3.7 | 更新失败/取消 → 旧版本正常启动、无残留阻断 | 模拟失败场景 |

### V4: 数据完整性

| # | 测试 | 方法 |
|---|---|---|
| V4.1 | fake deterministic 对局可完整运行 | 对局运行 + artifact 验证 |
| V4.2 | 升级前后 completed/interrupted runs 文件清单 + 关键 artifact SHA-256 一致（不比较 logs、runtime-state、update-cache） | 升级前后对比 |
| V4.3 | 升级前后 profiles/ 内容一致 | 升级前后对比 |
| V4.4 | 升级前后 configs/ 内容一致 | 升级前后对比 |
| V4.5 | Windows Credential Manager 凭证升级后可读取 | `CredReadW` 验证 |
| V4.6 | QSettings 非敏感数据升级后可读取 | QSettings 读验证 |
| V4.7 | P3 消费：升级后 run artifacts 可被 `build_run_detail` 正常读取 | artifact read 验证 |

### V5: Portable Smoke（PyInstaller 专项）

| # | 测试 | 方法 |
|---|---|---|
| V5.1 | frozen server 在无源码仓库环境下正常启动 | 将 frozen runtime 复制到独立临时目录；cwd 设为非仓库目录；确保 `PYTHONPATH` 未指向源码；验证 server、默认 profiles、fake run、observer API 均正常 |
| V5.2 | `werewolf_eval.*` 所有子模块正确导入 | 启动 + 全 capability 检查 |
| V5.3 | observer 子模块全部可发现 | 启动 + API 全覆盖探测 |
| V5.4 | 默认 profile 正确打包（`seed_default_profile` 不报错） | 启动后 GET profiles |
| V5.5 | `--runs-dir` / `--profiles-dir` / `--configs-dir` 接受绝对路径 | 启动参数验证 |
| V5.6 | 所有 package data / 默认 profile / 模块资源在 frozen onedir 中通过验证。若某处使用 `__file__`，必须在 frozen bundle 中真实验证其定位正确 | 代码审计 + runtime |
| V5.7a | 项目业务依赖基线仍为标准库；`pyproject` / requirements / import graph 不新增业务第三方包 | 依赖审计 |
| V5.7b | release venv 允许安装 PyInstaller 及其构建依赖，但 installer payload 不把 release venv、pip cache 或不相关 site-packages 整体带入 | 安装包内容审计 |

### V6: Release Build

| # | 测试 | 方法 |
|---|---|---|
| V6.1 | Qt client Release 构建成功 | CMake Release build |
| V6.2 | `windeployqt` 收集所有必要 DLL、QML 模块、插件 | 干净环境运行 |
| V6.3 | `appqt_observer.exe --observer-base-url` 功能正常 | 参数验证 |
| V6.4 | `observer-server.exe --help` 输出正常 | 参数验证 |
| V6.5 | `Werewolf-agent.exe --version` 输出 `0.2.0` | 参数验证 |
| V6.6 | host/server/client 版本均从 VERSION 推导 | 代码审计 |

### V7: 测试套件

| # | 测试 | 方法 |
|---|---|---|
| V7.1 | Python 全量测试绿 | `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"` |
| V7.2 | Qt C++ 测试绿 | `ctest --test-dir .tmp/qt-observer-build` |
| V7.3 | Qt 静态契约测试绿 | `tests.test_qt_observer_static_contract` |
| V7.4 | Release 构建不引入测试 regression | Debug vs Release 测试对比 |

### V8: Security & Privacy

| # | 测试 | 方法 |
|---|---|---|
| V8.1 | Synthetic sentinel 不在安装包中 | 安装包内容扫描 |
| V8.2 | Synthetic sentinel 不在日志文件中 | 日志内容扫描 |
| V8.3 | Synthetic sentinel 不在 run artifacts 中 | artifact 扫描 |
| V8.4 | Synthetic sentinel 不在 error 输出中 | 故意触发错误 |
| V8.5 | Synthetic sentinel 不在 installer payload 中 | 文件扫描 |
| V8.6 | Synthetic sentinel 不在 update repository archives 中 | 仓库扫描 |
| V8.7 | `update-request.json` 不含 key、run 内容、repository URL | schema 审计 |
| V8.8 | `host-control.json` 不含 key、run 内容 | schema 审计 |
| V8.9 | `server-state.json` 不含 key、run 内容 | schema 审计 |
| V8.10 | control IPC payload 在日志中不出现 | IPC 日志审计 |

### V9: i18n 与 UI

| # | 测试 | 方法 |
|---|---|---|
| V9.1 | 设置页「关于与更新」中文显示正确 | 截图验证 |
| V9.2 | 设置页「关于与更新」英文 fallback 正确 | 切换语言截图 |
| V9.3 | version/channel/更新按钮双语正常 | 截图验证 |
| V9.4 | active run 阻止更新提示中英双语正确 | 截图验证 |
| V9.5 | 自定义 installer 产品文案中英文可用；IFW wizard chrome 英文 fallback 可接受 | installer 截图 |
| V9.6 | 关闭窗口时 active run 提示中英双语正确 | 截图 + 语言切换 |

### V10: Diff 与 Allowlist 合规

| # | 检查 | 标准 |
|---|---|---|
| V10.1 | `git diff --stat` 在预期范围内 | 与 plan 对照 |
| V10.2 | 无 `src/**` 非 R0 改动 | forbidden-scope |
| V10.3 | 无 `tests/**` 非 R0 改动 | forbidden-scope |
| V10.4 | 无 `docs/adr/**`、`docs/secrets/**`、`.github/workflows/**` 改动 | forbidden-scope |
| V10.5 | 新增文件在 allowlist 内 | allowlist |

---

## 17. 文件 Allowlist / Forbidden Scope

### 预期新增/修改文件

```
# 新增
VERSION                                          # 版本单源
src/werewolf_eval/release_host.py                # bootstrapper 主模块
src/werewolf_eval/release_host/                  # host 子模块（control, lifecycle, update）
scripts/release/                                 # 构建脚本
scripts/release/build-qt-release.bat
scripts/release/build-server-frozen.bat
scripts/release/build-bootstrapper-frozen.bat
scripts/release/package-installer.py
scripts/release/repogen-stable.bat
scripts/release/repogen-preview.bat
scripts/release/distribution-manifest.json.in

docs/superpowers/specs/2026-06-20-r0-windows-distribution-baseline.md
docs/superpowers/plans/2026-06-20-r0-implementation-plan.md

# 修改（最小集）
clients/qt_observer/CMakeLists.txt               # VERSION 消费、Release 构建参数
clients/qt_observer/main.cpp                     # --release-host-session、--update-request-path、--version
clients/qt_observer/qml/ProviderSettingsView.qml  # About & Update 区域
clients/qt_observer/qml/I18n.qml                 # 新增文案 key
clients/qt_observer/src/ObserverApiClient.h/.cpp  # 可能的 capabilities 字段扩展
src/werewolf_eval/run_observer_server.py          # --version、动态 port 支持
src/werewolf_eval/observer/factory.py             # --profiles-dir、--configs-dir 显式传入
src/werewolf_eval/observer/state.py               # 若有新增字段
src/werewolf_eval/observer/run_manager.py         # server recovery marker + app_version stamp
README.md                                         # 新增 release 安装说明
docs/PROJECT_MAP.md                               # R0 加入 P2 收尾或新阶段
docs/TASKS.md                                     # R0 task 条目
```

### Forbidden Scope

以下文件/目录不得被 R0 修改（除非 plan 明确允许）：

- `src/werewolf_eval/emergent_engine.py` — 引擎核心
- `src/werewolf_eval/action_runtime/` — 能力系统
- `src/werewolf_eval/provider_*.py` — provider 逻辑
- `src/werewolf_eval/invariants/` — 安全网
- `tests/` — 除非新增 R0 专项测试
- `docs/adr/` — ADR
- `.github/workflows/` — CI
- `DESIGN.md` — UI 设计
- `AGENTS.md` — 项目指令

---

## 18. GitHub Pages Repository 初始化与发布流程

### 首次创建

1. 创建独立 public repo `werewolf-agent-updates`
2. 启用 GitHub Pages（Settings → Pages → Source: `main` branch, `/` root）
3. 初始目录结构：

```
stable/
  Updates.xml          # repogen 生成
  com.werewolfagent.app/
    (empty until first release)
preview/
  Updates.xml
  com.werewolfagent.app/
    (empty until first preview)
```

4. 验证 `https://<user>.github.io/werewolf-agent-updates/stable/Updates.xml` 可访问

### 发布流程（每次 release）

1. 构建全部 release artifacts
2. `repogen` 生成 stable/preview repository
3. 将 repository 内容推送到 `werewolf-agent-updates` repo：
   ```bash
   cp -r stable-repository/* werewolf-agent-updates/stable/
   cd werewolf-agent-updates
   git add .
   git commit -m "Release 0.2.0"
   git push origin main
   ```
4. 验证 maintenance tool 能从新仓库发现更新
5. 执行 retention policy（删除旧版本）

### Retention Policy 执行

- 每次 release 后检查 repository 大小
- 保留当前版本 + 上一 minor 的全部 patch
- 删除不再受支持的旧 component archives
- 更新 `Updates.xml`（repogen 自动处理）

---

## 19. Implementation Plan 输入条件

1. 本 spec 已由 owner 审核通过
2. 独立 release venv 已创建，PyInstaller 已安装（`pip install pyinstaller`）
3. 验证 IFW `binarycreator.exe`、`repogen.exe` 可用
4. 验证 `windeployqt.exe`、`qmlimportscanner.exe` 可用
5. 验证 Qt Release 构建可成功
6. 确认 GitHub Pages update repository 已创建或就绪
7. Python 全量测试当前 main 基线绿
8. Qt 静态契约 + ctest 当前 main 基线绿
9. `VERSION` 文件已创建并提交

---

## 20. 开放项

以下项目由 spec 明确推迟到后续设计任务，不在 R0 实现：

| ID | 项目 |
|---|---|
| O-01 | Stable ↔ preview 通道切换 |
| O-02 | Downgrade / 版本回退 |
| O-03 | 自动更新检查 / 后台轮询 / 系统通知 |
| O-04 | 多 client 同服 / 多窗口协调 |
| O-05 | 外部 server 连接支持（release host 外） |
| O-06 | 代码签名 / EV 证书 |
| O-07 | macOS / Linux 发行版 |
| O-08 | GitHub Release 自动发版 CI |
| O-09 | IFW wizard chrome 中文翻译 |
| O-10 | 完整凭证清理 / 恢复出厂设置 |
| O-11 | Repository base URL 无破坏迁移机制 |

# P2-B-1 Spec — BYO-key Credential Relay + Server-executed DeepSeek Live Call

> **类型:** 设计 spec(design)。实现随后由 writing-plans 切计划。
> **日期:** 2026-06-07
> **定位:** P2-B「开局配置」的第一切片(三切片之一;P2-B-2 动态模型列表、P2-B-3 多供应商留后续)。
> **一句话:** **客户端持有凭证,本地 server 执行调用** —— Qt 收集/本地保存(QSettings, dev-only)用户自己的
> DeepSeek API key,作为**会话凭证**中继给本地 server;server 只在**进程内存**保存,并在 live launch 时把它注入
> server 端的 DeepSeek provider 调用。**Qt 绝不直连 DeepSeek;provider 网络调用只在本地 Python server。**
> 这是对 G3-2/G3-3 的演进(G3-2 明确没有 key UI、只做 live/fake toggle):把 key UI + BYO-key 接到既有 live
> 管线上,**不推翻**它。`fake-deterministic` 仍是无 key 无条件默认。
> **不是 Qt 端到端直连,也不是通用多供应商系统。**

---

## 0. TL;DR

- **现状:** 配置(选 provider/model/strategy/prompt、校验、fake/live arming、profile→真实涌现 live 对局)**已就绪**。
  live 的 key **只来自 server 启动时的 env**(`run_observer_server --api-key-env DEEPSEEK_API_KEY`)。**没有任何
  用户自带 key 的入口。**
- **本切片补:** 让用户在 Qt 里填/存/选自己的 DeepSeek key,作为会话凭证中继到本地 server,server 用它(env 兜底)
  跑 live。**只 deepseek、只静态模型。**
- **三条边界:** ①Qt→本地 server 的 `/api/credentials`(loopback、仅 JSON、限大小、无宽 CORS);②key 只进
  provider 的 Authorization header,**绝不**进任何 artifact / 日志 / 错误响应;③fake 永不需 key。
- **明确不做:** 动态拉模型(P2-B-2)、多供应商抽象(P2-B-3)、OS keychain。本切片 allowlist 只有 `deepseek`。

---

## 1. 现状(读码确认)

- **Qt 配置面:** `MatchSetupView.qml` + `SeatEditorPanel.qml` 已支持逐座位 provider/model/strategy/prompt 编辑、
  profile 校验、`ModeControl` 两步式 fake/live arming、`launchFromProfile(profile, resolvedMode)`。
- **live key 来源:** `run_observer_server.resolve_live_launcher` 在**启动时**读 env key 构建 launcher 一次;
  无 env key → `live_launcher=None` → `_check_live_capability` 返 403 `missing_api_key`。
- **capability 端点:** `GET /api/runtime/capabilities`(`observer_server.py:292`)→ `_build_capabilities_payload`
  → `build_runtime_capabilities(live_enabled, deepseek_available, reason_code, message)`,产
  `g3.runtime_capabilities.v1`:`{schema_version, default_mode:"fake", live_api:{enabled, providers:{deepseek:{available[, reason_code, message]}}}}`。
  **本切片在此结构上演进,不新发明端点/顶层 schema。**
- **provider/model allowlist:** `profile_config.ALLOWED_PROVIDERS = {fake_deterministic, deepseek}`,模型为静态
  frozenset(`deepseek-chat`/`deepseek-reasoner`)。本切片**不动**(动态/多供应商是后续切片)。
- **既有安全地基(#51):** DeepSeek transport 异常链断开(不泄 key)、review-packet `redact_secrets()`、`.runs/`
  gitignored。本切片**复用并扩展**这套脱敏到凭证库 + 端点 + 错误响应。

---

## 2. 架构

```
Qt MatchSetupView「供应商密钥」面板
  └─ 用户输入 deepseek key(打码)
       ├─ CredentialStore.saveCredential("deepseek", raw) → QSettings(dev-only,本地)
       └─ syncCredentialToServer("deepseek") → POST /api/credentials {provider,api_key}
                                                  → server 进程内存凭证库 {deepseek: key}
launch(mode=live) → POST /api/runs(profile + mode;**body 内无 key**)
  └─ server _handle_profile_launch → 用内存 key(env 兜底)构建涌现 deepseek launcher
       └─ 启动时把凭证 COPY 进 provider 配置 → live 涌现对局
            └─ key 仅存在于 provider 的 Authorization header;绝不进 artifact/日志/错误响应
```

**关键不变量:** Qt 只和本地 server 的 `/api/credentials` 打交道;真正的 DeepSeek 网络调用只由 server 的
`DeepSeekProvider` 发起。Qt 的 arming 只是 **UX 门槛**,launch 时 server **再独立校验一次**(安全门槛在 server)。

---

## 3. 组件

### 3.1 Server — 进程内存凭证库(注入式 app state)
- 一个 `CredentialStore` 对象,挂在 `ObserverServerState` 上(**注入式,非模块全局变量**)。持有 `{provider: key}`,
  **只在进程内存**;进程退出即丢。
- observer server 是 `ThreadingHTTPServer` → 凭证库内部加一把简单 `threading.Lock`(set/get/clear 互斥)。
- `__repr__`/debug 输出**红act**(永不打印内部 dict / key);提供 `has(provider)` / `get(provider)` / `set(provider, key)` /
  `clear(provider)`。`get` 是唯一返回明文的方法,仅 launch 接线内部调用。
- **绝不**被序列化进任何 artifact / 响应 / 日志。

### 3.2 Server — `POST /api/credentials` + `DELETE /api/credentials/{provider}`
- **`POST /api/credentials`**:
  - 仅接受 `Content-Type: application/json`;非 JSON → `415`(或 `400`)。
  - body 必须是 `{"provider": "deepseek", "api_key": "<non-empty>"}`;**空 body / 缺字段 / 空 key 一律 `400`**。
  - **provider allowlist 本切片只有 `deepseek`**;`fake`、未知 provider、其它 → `400`(多供应商留 P2-B-3)。
  - 限 body 大小(如 ≤ 8 KiB)防滥用。
  - 成功 → 存内存 → `200 {"stored": ["deepseek"]}`。**响应绝不回显 key。**
  - handler **绝不打印/记录 body**。
- **`DELETE /api/credentials/{provider}`**:删内存该 provider 的 key → `200 {"cleared": "deepseek"}`(provider 不在
  allowlist → `400`;不存在也视作成功幂等)。**清除只走 DELETE**,不接受"空 body POST 清除"(避免解析失败误清除 /
  网页简单 POST 干扰)。
- **loopback only**:端点(连同整个 server)仅绑 `127.0.0.1`;**不开宽泛 CORS**(浏览器跨站简单请求不能干扰本地 server)。

### 3.3 Server — capability gate 拆「server 能力」与「provider 凭证状态」
- `deepseek_available`(喂给 `build_runtime_capabilities`)的判定从「启动时 env key 存在」改为
  **「该 provider 在 server 侧有可用凭证:内存客户端 key **或** env key,任一存在」**。
- `live_api.enabled` = `--allow-live-api`(server 能力,不变);`live_api.providers.deepseek.available` =
  上面的凭证状态;Qt 据此把 `live_available` 理解为 `enabled && deepseek.available`。
- `reason_code` 在不可用时给 `missing_api_key`(沿用既有 launch-time 403 码,镜像一致)。
- **launch 时 server 必再独立校验**(`_check_live_capability` 仍在 handler 内,先于建 run_dir):capabilities 只是
  posture,**不是安全门槛**。

### 3.4 Server — launch 接线(内存 key 优先,env 兜底)
- profile launch(mode=live)时,**按需在 launch 时刻**用「内存 deepseek key ?? env key」构建涌现 deepseek launcher
  (取代"启动时一次性 env launcher")。key 只流进 `DeepSeekProviderConfig`/Authorization(既有路径)。
- **launcher 在启动时把凭证 COPY 进 provider 配置** → 之后清除/改 key **不影响已在跑的 run**(见 §6 清除语义)。
- **resolved-profile.json 绝不含凭证**(现仅写 `execution_mode`/`live_api` 标记);加测试钉死其无 key。

### 3.5 Client — CredentialStore(C++ QObject,QSettings dev-only)
- 暴露给 QML 的 API **仅**:
  - `bool hasCredential(provider)`
  - `string maskedCredential(provider)` —— 如 `sk-••••••••1234`
  - `saveCredential(provider, rawText)` —— 写 QSettings(dev-only)
  - `clearCredential(provider)` —— 删 QSettings + 触发 server DELETE
  - `syncCredentialToServer(provider)` —— POST /api/credentials
- **不暴露** `getRawKey()` 给 QML;**不**把已保存 raw key 反向加载进 QML(TextField 不预填真实 key,只显示
  placeholder,如 `已保存:sk-••••••••1234` 或 `未配置`)。
- QSettings 存储位置/键明确标 **dev-only**(注释 + 文档);`maskedCredential` 只读首尾、中间打码。

### 3.6 Client — MatchSetupView 内联「供应商密钥」面板
- 位置:`ModeControl` 旁。显示当前 profile 的 **live provider(本切片必为 deepseek)** 的凭证状态:
  - 打码 TextField(placeholder,不预填)+ `保存` + `清除`。
  - 状态行:`已配置凭证(本地)` / `使用服务器环境凭证` / `未配置`。
- `保存` → `saveCredential` + `syncCredentialToServer`;`清除` → `clearCredential`。

### 3.7 Client — arming 门控(UX 门槛,非安全门槛)
- live arming 允许条件 = `capabilities.live_api.enabled && capabilities.providers.deepseek.available`。
- **不**硬要求"本地 QSettings 有 key":若用户没填本地 key 但 **server env 有 key**,`deepseek.available` 仍为真 →
  仍可 arm(UI 显示`使用服务器环境凭证`)。即:本地 key **或** env key 任一即可。
- launch(live)前确保本地 key(若有)已 `syncCredentialToServer`;真正 gate 仍是 server 的 launch 校验。

---

## 4. 数据流(端到端)

1. 用户在面板输入 deepseek key → `saveCredential`(QSettings, dev-only) + `syncCredentialToServer` →
   `POST /api/credentials {deepseek, key}` → server 内存库。
2. server `/api/runtime/capabilities` 现报 `providers.deepseek.available=true`(内存有 key)→ Qt 可 arm live。
3. launch(mode=live)→ `POST /api/runs`(profile + mode,**无 key**)→ `_check_live_capability`(再验)→ 用内存 key
   (env 兜底)构建涌现 deepseek launcher → 跑 live。
4. key 仅在 provider Authorization header;artifact/日志/capabilities/错误响应一律无 key。

---

## 5. 安全不变量(本切片的核心)

- **Hard:** key 不入源码、不打日志(端点 body + launcher + 错误路径)、不进 resolved-profile / prompt-manifest /
  provider-trace / events / status / capabilities / review-packet;fake 永不需 key。
- **Architecture:** Qt 不直连 DeepSeek;只 POST 本地 loopback `/api/credentials`;provider 调用只在 server。
- **Storage:** QSettings **dev-only**(明确标注);UI 只显示打码 key;不向 QML 暴露 raw 已存 key。
- **端点硬化:** loopback only、仅 JSON、限 body 大小、无宽 CORS、清除只走 DELETE。

---

## 6. 错误处理 / 清除语义

- **无凭证却 arm/launch live:** capability `providers.deepseek.available=false` + `reason_code=missing_api_key`;
  launch 时 server 403 `missing_api_key` → Qt `resetToFake`(既有)。
- **key 错(DeepSeek 401):** live 失败路径 → run status 统一 **sanitized** 成 `provider_failure` /
  `provider_auth_failed` / `missing_api_key` 之一;**绝不**含 Authorization header、key 前后缀、原始 provider
  response body、原始 request。Qt 错误 label 同样只显示这些规范码。
- **`/api/credentials` 异常:** 非 JSON→415/400;空/缺字段/空 key→400;非 allowlist provider→400;超大 body→413/400。
  **任何错误响应都不回显收到的 key。**
- **清除语义(写死):** `清除` 删 QSettings 本地 key **并** `DELETE` server 内存 key;**不影响已启动的 run**
  —— launcher 启动时已把凭证 COPY 进 provider 配置,在跑的 live 局继续用旧凭证直到结束。

---

## 7. 测试(全离线)

| 层 | 断言 |
|---|---|
| **server: 凭证库** | set/get/clear 只在内存;`__repr__`/str 红act(不含 key);threaded 下 set/get 加锁不崩;**永不落盘** |
| **server: 端点** | `POST` 仅 JSON(非 JSON→415/400)、`{deepseek,key}`→200 `{"stored":["deepseek"]}`(响应无 key)、空/缺/空 key→400、非 allowlist(`fake`/`openai`/未知)→400、超大 body 拒;`DELETE /api/credentials/deepseek`→200 幂等;**handler 不记录 body** |
| **server: capability** | env 无 + 内存有 key → `deepseek.available=true`;两者都无 → false + `reason_code=missing_api_key`;env 有 + 内存无 → true |
| **server: launch 接线** | 注入 fake-transport,断言用的是**内存客户端 key 而非 env**(内存优先);env 兜底(无内存时用 env);**resolved-profile.json / prompt-manifest / provider-trace 全无 key**(secret 扫描) |
| **server: 错误不泄漏** | 模拟 DeepSeek 401/异常 → run status ∈ {`provider_failure`,`provider_auth_failed`,`missing_api_key`},**不含** Authorization/key 片段/原始 response body(扫描) |
| **server: 全产物 secret 扫描** | 一局 live(fake-transport)后全 run_dir + 所有 JSON 响应 secret 扫描:无 `sk-`/`bearer`/`authorization`/`api_key`/真实 key |
| **Qt 静态契约** | key 面板新 objectName(如 `setupCredentialPanel`/`setupCredentialField`/`setupCredentialSave`/`setupCredentialClear`);CredentialStore **不暴露** `getRawKey`;QSettings 标 dev-only;forbidden 泄漏模式 |
| **构建** | qmlcachegen build exit 0;qmllint clean |
| **(可选)截图** | key 面板渲染(打码态)+ arming 状态行 |

> 运行口径沿用 P2-A-2:真实 DeepSeek 由**用户本地** dev key 跑;**agent 不接触真实 key**,只对 fake-transport /
> 离线产物做机检。

---

## 8. allowlist / forbidden / 不做

### 8.1 ALLOWLIST(允许动)
- **Server:** 新增凭证库模块(注入 `ObserverServerState`)、`observer_server.py`(新增 `/api/credentials` POST/DELETE
  路由 + capability 凭证判定 + launch 用内存 key)、`run_observer_server.py`(launch 时建 launcher 而非启动时一次性;
  保留 env 兜底)、`observer_protocol.py`(若 capability 判定需小调;**不**改 schema 顶层形状)。
- **Client:** 新增 `CredentialStore`(C++ QObject)+ 注册;`MatchSetupView.qml`(内联面板 + arming 联动);
  `ObserverApiClient`(若 POST/DELETE credentials 经它走);`CMakeLists.txt`(注册新 C++ 类;若新 QML 文件则进 QML_FILES)。
- **Tests:** 新增 server 凭证/端点/capability/launch/错误脱敏测试;扩 Qt 静态契约。

### 8.2 FORBIDDEN(不动)
`emergent_engine.py`、`game_engine.py`、`scoring.py`、`attribution.py`、`settlement_bundle.py`、
`observer_visibility.py`、`deepseek_provider.py`(其调用契约不变,只是被传入不同 key)、`PROJECT_MAP.md`、`TASKS.md`。

### 8.3 不做(YAGNI / 后续切片)
- 动态模型列表 `/api/providers/{name}/models`(P2-B-2)。
- 多供应商抽象(openai/anthropic…)、放宽 provider allowlist(P2-B-3)。
- OS keychain(QtKeychain 依赖)。
- 改 fake-deterministic 默认(永不需 key)。
- 通用 CORS / 远程多用户(本切片 loopback 单用户)。

---

## 附录 — 实现者结论(一句话)

**P2-B-1 = BYO-key 凭证中继 + server-side DeepSeek live 执行(非 Qt 直连、非通用多供应商):** server 注入式内存
凭证库 + `POST /api/credentials`(仅 JSON、deepseek-only allowlist、不回显)/`DELETE /api/credentials/{provider}`、
capability 拆「server 能力 / provider 凭证状态」、launch 用内存 key(env 兜底,启动即 COPY)、Qt CredentialStore
(QSettings dev-only,不向 QML 暴露 raw key)+ MatchSetupView 内联面板 + arming UX 门槛、全离线 secret 扫描(含错误
响应)。动态模型 / 多供应商 / keychain 留后续切片。

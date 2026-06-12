# Implementation Plan — 批次② engine 失败分类对齐

> 绑定审计:`docs/health-check/2026-06-12-system-view-audit.md` 的 **B12-01 / B12-02/03 / B34-10**。
> 基线:worktree `worktree-b2-engine-failure-classification` @ 本地 main `8b6d32c`(含本轮 A-1/B34/C12/C3 修复)。
> 工作纪律:隔离 worktree、PR-first、TDD(先失败测试)、字节门不涉及(无 prompt 字节变更)。

## 问题(三处同一契约两套标准)

1. **B12-01**:`emergent_engine.py:811/1017` 女巫/猎人内联 `parsed.get("action", PASS)`——JSON 合法 dict 但缺 `action` 键时静默当 pass 且记 `LIVE_SUCCESS`。正规路径 `ProviderAgent.decide` 同情形判 `parse_failure` 并 raise(`provider_agent.py:255-272`,`test_fake_provider.py:127` 钉死)。
2. **B12-02/03**:`emergent_engine.py:814/1019` 女巫/猎人把 `provider.respond()` 网络异常与 `json.loads()` 解析异常同一 `except`,一律记 `parse_failure`+`INVALID_FALLBACK`——「模型坏」与「网络坏」无法区分。
3. **B34-10**:`provider_agent.py:174-191` 把 401/budget/transport **一切** provider 异常包成 `kind="timeout"`;budget 信号只活在 reason 子串。

## 设计(单源分类器 + 已有 turn-kind 映射复用)

### 失败 kind 枚举(新增 4 个结构化 kind)
落 `failure_audit.py:VALID_FAILURE_KINDS`(硬白名单,`emergent_engine.py:612/691` 把 `ProviderFailure.kind` 直接写审计→必须登记):
- `budget_exhausted`(预算耗尽;`deepseek_launcher._failure_is_budget_exhausted` 已认此结构化 kind→launcher 零改动)
- `transport_error`(网络/传输)
- `auth_failed`(API key 未配置/401)
- `provider_error`(其余 provider 侧异常,如空 content)

`timeout` 保留(provider_agent 的显式 `failure_mode=="timeout"` 模拟路径仍用)。

### 单源分类器(`provider_contract.py` 新增,两路径共用,消除「两套标准」)
```python
def classify_provider_failure_kind(exc: Exception) -> str:
    msg = str(exc).lower()
    if "budget exceeded" in msg or "budget exhausted" in msg: return "budget_exhausted"
    if "transport error" in msg: return "transport_error"
    if "api key is not configured" in msg: return "auth_failed"
    return "provider_error"
```
放 `provider_contract`(`ProviderFailure` 同源,provider_agent 与 emergent_engine 都已 import 它,无循环)。匹配 `llm_providers.py` 现有异常文案(`:81` transport / `:234` api key / `:237` budget)。**reason 字符串保留原始 message→子串后向兼容不破。**

### turn-kind 映射扩展(`emergent_engine._fallback_kind_for`)
```python
if failure_kind in ("timeout", "transport_error", "budget_exhausted"): return TIMEOUT_FALLBACK
if failure_kind in ("invalid_action", "parse_failure"):                return INVALID_FALLBACK
return ERROR_FALLBACK   # auth_failed / provider_error / unknown
```
budget 旧路径 `timeout→TIMEOUT_FALLBACK`,新 `budget_exhausted→TIMEOUT_FALLBACK`,turn-kind 连续不变。

### 内联 witch/hunter 重构(B12-01 + B12-02/03)
`respond()` 与 `json.loads()` 拆开:
- `respond()` 抛 → `classify_provider_failure_kind(exc)` 记审计 + `_fallback_kind_for` 设 turn-kind(非 INVALID_FALLBACK)。
- `json.loads`/非 dict → `parse_failure` + INVALID_FALLBACK(现状)。
- 解析成功但 **缺 `action` 键** → `parse_failure` + INVALID_FALLBACK(B12-01,不再静默 LIVE_SUCCESS pass)。

## TDD 任务序列

- **T1**(B34-10):`tests/test_provider_agent_failure_classification.py` 新建——budget/transport/auth/未知四类异常经 `decide` 各产对应 `ProviderFailure.kind`;reason 仍含原 message(子串兼容)。
- **T2**(分类器单测):`tests/test_provider_contract.py` 追加 `classify_provider_failure_kind` 真值表(四分支)。
- **T3**(B12-01 witch):`tests/test_emergent_engine.py`(或新建)——女巫返回 `{"target":"p5"}` 缺 action → turn `invalid_then_fallback` 非 `live_success`,failure-audit 含 `parse_failure`。
- **T4**(B12-01 hunter):同上,猎人缺 action。
- **T5**(B12-02/03):女巫/猎人 `respond()` 抛 transport 异常 → failure-audit kind=`transport_error` 非 `parse_failure`,turn kind=`timeout_then_fallback`。
- **T6**(白名单守卫):`tests/test_failure_audit.py`——四个新 kind 过 `validate_failure_audit` 不抛。
- **T7**(后向兼容回归):确认 `test_deepseek_launcher.py:234-262` 仍绿(手造 timeout+budget 子串 fixture 不受影响)。

每步:写测试→看红(预期原因)→最小实现→看绿→全量。

## 验证
- 全量:`NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"`(目标 ≥1216 OK)。
- `git diff --stat` + name-only + forbidden-scope(只碰 provider_contract/provider_agent/emergent_engine/failure_audit + tests/ + 本 plan;不碰 scoring/ablation/observer/prompt 字节/ROADMAP/TASKS/adr)。
- 无 prompt 模型可见字节变更→字节门不涉及。

## 不做(明确划界)
- 不碰 deepseek_launcher(已后向兼容)。
- 不动 `agent_error` 既有缺登记问题(预存,越界)。
- 不改 ProviderAgent 五字段必填契约(已正确,本批对齐到它)。
- 不引入 `render_provider_replay` 标签(有 `.get` 兜底,非必需)。

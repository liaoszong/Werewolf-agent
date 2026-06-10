# 对局多样性(子集 1/2):per-seat persona + 温度策略 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 让同角色两座位不再克隆(per-seat persona 拼接)+ 给 live/默认 profile 一个 0.8 的多样性温度,**只碰 `profile_config.py` + `seat_agents.py`,零避让区,旧 profile 解析逐字节不变**。

**Architecture:** persona 在配置层 `_resolve_seat` 拼接「角色策略(跟角色)+ 座位个性(跟座位,新字段 `seat_personas`)」,产出的 persona 字符串经现有未改的 `compose_system` 下发;温度兜底 0.8 单点钉在装配层 `build_seat_agents`(显式座位温度优先),并在 `resolved-profile.json` 加 additive `effective_temperature` 留痕。角色洗牌 deferred(须改避让区引擎角色板)。

**Tech Stack:** Python 3.12, stdlib `unittest`。测试命令:`NO_PROXY='*' PYTHONPATH=src python -m unittest tests.<module> -v`。

**Spec:** `docs/superpowers/specs/2026-06-10-game-variety-design.md`(r2)。

**⚠️ 硬约束(每个 commit 前必做)**:`git branch --show-current` 必须是 `feat/game-variety`(共享工作树曾发生错分支 commit)。不改任何 prompt 模板字节;不碰避让区文件(emergent_engine / run_*/ observer_server / llm_providers / fake_provider / scoring / settlement_bundle / runtime_events / observer_protocol)。

---

## File Structure

- **Modify** `src/werewolf_eval/profile_config.py`:
  - 新增常量 `DEFAULT_LIVE_TEMPERATURE = 0.8`(温度政策单源)。
  - 新增常量 `DEFAULT_SEAT_PERSONAS`(默认 profile 的 6 个 role-agnostic 个性)。
  - `_resolve_seat`:persona 拼接(策略 + 个性)。
  - `validate_profile`:`allowed_top` 纳入 `seat_personas` + 校验块。
  - `build_default_profile`:种入 `seat_personas`。
  - `build_resolved_profile_artifact`:additive `effective_temperature` + `temperature` 语义注释。
- **Modify** `src/werewolf_eval/seat_agents.py`:import `DEFAULT_LIVE_TEMPERATURE`;`build_seat_agents` 加 `default_temperature` 兜底。
- **Modify/Create tests**:`tests/test_profile_config.py`、`tests/test_seat_agents.py`(沿用其现有 fixture 风格)。

---

## Task 1: 温度兜底(常量 + `build_seat_agents`)

**Files:**
- Modify: `src/werewolf_eval/profile_config.py`(加常量)
- Modify: `src/werewolf_eval/seat_agents.py:37-74`
- Test: `tests/test_seat_agents.py`

- [ ] **Step 1: 加失败测试**(组 4:live 座位 null→0.8、显式优先、fake 仍报错)

在 `tests/test_seat_agents.py` 的 `BuildSeatAgentsTests` 类内追加(沿用文件顶部已有的 `_seat`/`_multi_shape_transport`/`_creds`/`_request`):

```python
    def test_null_temperature_falls_back_to_default_live_temperature(self):
        from werewolf_eval.profile_config import DEFAULT_LIVE_TEMPERATURE
        seats = [_seat("p1", "deepseek", "deepseek-v4-flash", temperature=None)]
        agents = build_seat_agents(seats, self._creds(), max_requests=64, transport=_multi_shape_transport)
        agents["p1"].provider.respond(_request("p1"))
        self.assertEqual(_CALLS[-1]["payload"]["temperature"], DEFAULT_LIVE_TEMPERATURE)

    def test_explicit_seat_temperature_wins(self):
        seats = [_seat("p1", "deepseek", "deepseek-v4-flash", temperature=0.2)]
        agents = build_seat_agents(seats, self._creds(), max_requests=64, transport=_multi_shape_transport)
        agents["p1"].provider.respond(_request("p1"))
        self.assertEqual(_CALLS[-1]["payload"]["temperature"], 0.2)

    def test_default_temperature_override_param(self):
        seats = [_seat("p1", "deepseek", "deepseek-v4-flash", temperature=None)]
        agents = build_seat_agents(seats, self._creds(), max_requests=64,
                                   default_temperature=0.55, transport=_multi_shape_transport)
        agents["p1"].provider.respond(_request("p1"))
        self.assertEqual(_CALLS[-1]["payload"]["temperature"], 0.55)

    def test_fake_seat_still_raises_no_temperature_pipeline(self):
        # fake 座位本就进不了温度管道:无 credential -> ValueError(锁住现状)
        seats = [_seat("p1", "fake_deterministic", "none", temperature=None)]
        with self.assertRaises(ValueError):
            build_seat_agents(seats, self._creds(), max_requests=64, transport=_multi_shape_transport)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_seat_agents -v`
Expected: FAIL —— `test_null_temperature_falls_back...` 得到 `KeyError: 'temperature'`(payload 无 temperature,因今天为 None 不写)或 ImportError(`DEFAULT_LIVE_TEMPERATURE` 未定义)。

- [ ] **Step 3: 加常量到 `profile_config.py`**

在 `profile_config.py` 的常量区(`PROMPT_MAX_LEN = 8000` 之后)加:

```python
# Live/default-profile diversity policy (NOT a prompt/rendering policy). Explicit per-seat
# temperature always wins; a null seat temperature is filled with this at build_seat_agents
# time. Single source of truth so build_resolved_profile_artifact can record effective_temperature.
DEFAULT_LIVE_TEMPERATURE = 0.8
```

- [ ] **Step 4: 改 `build_seat_agents`**(`seat_agents.py`)

在 import 区加(与现有 import 同组):

```python
from werewolf_eval.profile_config import DEFAULT_LIVE_TEMPERATURE
```

把签名与温度赋值改为(改 `seat_agents.py:37-71` 的相关行):

```python
def build_seat_agents(
    resolved_seats: list[dict],
    credentials: Mapping[str, ProviderCredential],
    *,
    max_requests: int,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    default_max_tokens: int = DEFAULT_MAX_TOKENS,
    default_temperature: float = DEFAULT_LIVE_TEMPERATURE,
    transport=None,
) -> dict[str, ProviderAgent]:
```

并把原 `temperature=seat.get("temperature"),`(`seat_agents.py:70`)改为:

```python
        seat_temperature = seat.get("temperature")
        config = ChatProviderConfig(
            api_key=cred.key,
            base_url=cred.base_url,
            model=seat["model"],
            timeout_seconds=timeout_seconds,
            max_tokens=seat_max_tokens if seat_max_tokens is not None else default_max_tokens,
            max_requests=max_requests,
            persona_prompt=seat.get("prompt") or "",
            temperature=seat_temperature if seat_temperature is not None else default_temperature,
        )
```

> 注:`fake_deterministic` 座位在此函数更早处(`seat_agents.py:57-60` 无 credential)已 `ValueError`,根本到不了温度赋值;`test_fake_seat_still_raises...` 锁住该现状。无需改 `deepseek_launcher`(其 `:252` 调用未传 `default_temperature`,吃签名默认 0.8)。

- [ ] **Step 5: 跑测试确认通过 + 无 import 环**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_seat_agents -v`
Expected: PASS(4 新测试全过;无 `ImportError`,证明 `seat_agents -> profile_config` 单向无环)。

- [ ] **Step 6: Commit**(先 branch-check)

```bash
git branch --show-current   # 必须 feat/game-variety,否则停手
git add src/werewolf_eval/profile_config.py src/werewolf_eval/seat_agents.py tests/test_seat_agents.py
git commit -m "feat(seat-agents): default live temperature 0.8 fallback (explicit seat temp wins; fake unaffected)"
```

---

## Task 2: `_resolve_seat` persona 拼接

**Files:**
- Modify: `src/werewolf_eval/profile_config.py:216-235`(`_resolve_seat`)
- Test: `tests/test_profile_config.py`

- [ ] **Step 1: 加失败测试**(组 2 拼接 + 组 1 `_resolve_seat` parity)

在 `tests/test_profile_config.py` 顶部 import 区把 `_resolve_seat` 加进来:

```python
from werewolf_eval.profile_config import _resolve_seat, resolve_profile
```
(若 `resolve_profile` 已 import 则只加 `_resolve_seat`。)

追加一个测试类(沿用文件已有的 `_valid_profile` helper):

```python
class ResolveSeatPersonaTests(unittest.TestCase):
    def test_no_seat_personas_is_byte_identical_strategy_only(self):
        # 组 1 parity:无 seat_personas、温度 null -> prompt == role_strategy、temperature 仍 null
        p = _valid_profile(role_defaults={
            "werewolf": {"provider": "fake_deterministic", "model": "none", "prompt": "STRAT_W", "strategy": "default"},
            "seer": {"provider": "fake_deterministic", "model": "none", "prompt": "STRAT_S", "strategy": "default"},
            "witch": {"provider": "fake_deterministic", "model": "none", "prompt": "STRAT_X", "strategy": "default"},
            "villager": {"provider": "fake_deterministic", "model": "none", "prompt": "STRAT_V", "strategy": "default"},
        })
        seat = _resolve_seat(p, "p1", "werewolf")
        self.assertEqual(seat["prompt"], "STRAT_W")
        self.assertIsNone(seat["temperature"])  # 兜底绝不在 _resolve_seat 发生

    def test_persona_appended_after_strategy(self):
        p = _valid_profile(
            role_defaults={
                "werewolf": {"provider": "fake_deterministic", "model": "none", "prompt": "STRAT_W", "strategy": "default"},
                "seer": {"provider": "fake_deterministic", "model": "none", "prompt": "S", "strategy": "default"},
                "witch": {"provider": "fake_deterministic", "model": "none", "prompt": "X", "strategy": "default"},
                "villager": {"provider": "fake_deterministic", "model": "none", "prompt": "V", "strategy": "default"},
            },
            seat_personas={"p1": "PERSONA_1"},
        )
        self.assertEqual(_resolve_seat(p, "p1", "werewolf")["prompt"], "STRAT_W\n\nPERSONA_1")

    def test_two_wolves_distinct_persona(self):
        p = _valid_profile(
            role_defaults={
                "werewolf": {"provider": "fake_deterministic", "model": "none", "prompt": "WOLF", "strategy": "default"},
                "seer": {"provider": "fake_deterministic", "model": "none", "prompt": "S", "strategy": "default"},
                "witch": {"provider": "fake_deterministic", "model": "none", "prompt": "X", "strategy": "default"},
                "villager": {"provider": "fake_deterministic", "model": "none", "prompt": "V", "strategy": "default"},
            },
            seat_personas={"p1": "AGGR", "p2": "CALM"},
        )
        self.assertNotEqual(_resolve_seat(p, "p1", "werewolf")["prompt"],
                            _resolve_seat(p, "p2", "werewolf")["prompt"])

    def test_persona_only_when_strategy_empty(self):
        p = _valid_profile(
            role_defaults={
                "werewolf": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
                "seer": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
                "witch": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
                "villager": {"provider": "fake_deterministic", "model": "none", "prompt": "", "strategy": "default"},
            },
            seat_personas={"p1": "ONLY_ME"},
        )
        self.assertEqual(_resolve_seat(p, "p1", "werewolf")["prompt"], "ONLY_ME")

    def test_seat_override_prompt_stacks_with_persona(self):
        # seat_overrides.prompt(覆盖角色策略)+ seat_personas 叠加正交
        p = _valid_profile(
            role_defaults={
                "werewolf": {"provider": "fake_deterministic", "model": "none", "prompt": "ROLE_W", "strategy": "default"},
                "seer": {"provider": "fake_deterministic", "model": "none", "prompt": "S", "strategy": "default"},
                "witch": {"provider": "fake_deterministic", "model": "none", "prompt": "X", "strategy": "default"},
                "villager": {"provider": "fake_deterministic", "model": "none", "prompt": "V", "strategy": "default"},
            },
            seat_overrides={"p1": {"prompt": "OVERRIDE_W"}},
            seat_personas={"p1": "PERSONA_1"},
        )
        self.assertEqual(_resolve_seat(p, "p1", "werewolf")["prompt"], "OVERRIDE_W\n\nPERSONA_1")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config.ResolveSeatPersonaTests -v`
Expected: FAIL —— 拼接测试得到 `STRAT_W`(未拼 persona)而非 `STRAT_W\n\nPERSONA_1`。

- [ ] **Step 3: 改 `_resolve_seat`**(`profile_config.py:216-235`)

把整个 `_resolve_seat` 改为:

```python
def _resolve_seat(profile: dict, seat: str, role: str) -> dict[str, Any]:
    base = dict(profile["role_defaults"][role])
    override = dict(profile.get("seat_overrides", {}).get(seat, {}))
    merged = {**base, **override}
    # persona = 角色策略(跟角色,可被 seat_overrides.prompt 覆盖)+ 座位个性(跟座位,role-agnostic)。
    # 两者都是 profile 配置输入;拼接在配置层,产出的串喂给未改动的 compose_system。
    role_strategy = merged.get("prompt", "")
    personality = profile.get("seat_personas", {}).get(seat, "")
    if not personality:
        prompt = role_strategy
    elif not role_strategy:
        prompt = personality
    else:
        prompt = f"{role_strategy}\n\n{personality}"
    return {
        "player_id": seat,
        "role": role,
        "team": ROLE_TEAMS[role],
        "provider": merged.get("provider"),
        "model": merged.get("model"),
        "prompt": prompt,
        "strategy": merged.get("strategy"),
        "temperature": merged.get("temperature"),
        "max_tokens": merged.get("max_tokens"),
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config.ResolveSeatPersonaTests -v`
Expected: PASS(5 测试全过)。

- [ ] **Step 5: Commit**(先 branch-check)

```bash
git branch --show-current   # feat/game-variety
git add src/werewolf_eval/profile_config.py tests/test_profile_config.py
git commit -m "feat(profile): compose persona = role strategy + per-seat personality (seat_personas); empty -> byte-identical"
```

---

## Task 3: `validate_profile` 接纳 `seat_personas`

**Files:**
- Modify: `src/werewolf_eval/profile_config.py:268`(allowed_top)+ 校验块
- Test: `tests/test_profile_config.py`

- [ ] **Step 1: 加失败测试**(组 3)

追加测试类:

```python
class SeatPersonasValidationTests(unittest.TestCase):
    def test_valid_seat_personas_pass(self):
        validate_profile(_valid_profile(seat_personas={"p1": "谨慎", "p2": "激进"}))  # 不得抛

    def test_empty_and_absent_pass(self):
        validate_profile(_valid_profile(seat_personas={}))
        validate_profile(_valid_profile())  # 无该键

    def test_unknown_seat_id_rejected(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_personas={"p9": "x"}))

    def test_non_string_persona_rejected(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_personas={"p1": 123}))

    def test_non_dict_seat_personas_rejected(self):
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_personas=["p1"]))

    def test_secret_like_persona_value_rejected(self):
        # _reject_secret_like_values 递归扫到新字段
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(seat_personas={"p1": "my api_key=sk-secret"}))
```

> 注:`test_secret_like_persona_value_rejected` 的触发词需匹配 `_VALUE_SECRET_MARKERS`;若 `"api_key="` 不在标记集,改用该集合里确有的标记词(实施时 `grep _VALUE_SECRET_MARKERS src/werewolf_eval/profile_config.py` 取一个真实标记,如包含 `"sk-"` 或 `"secret"` 的规则)。

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config.SeatPersonasValidationTests -v`
Expected: FAIL —— `test_valid_seat_personas_pass` 抛 `unexpected top-level keys: ['seat_personas']`。
> **TDD 注(plan-review 指出)**:`test_secret_like_persona_value_rejected` 会**在实现前就 PASS** —— 因为 `_reject_secret_like_values(profile)`(`:267`)在 `allowed_top` 闸(`:268`)**之前**递归扫全 profile 值,已覆盖 `seat_personas`。这不是 bug;其余 5 个测试照常红。

- [ ] **Step 3: 改 `validate_profile`**(`profile_config.py`)

把 `:268` 的 allowed_top 改为:

```python
    allowed_top = {"schema_version", "name", "template", "role_defaults", "seat_overrides", "seat_personas"}
```

在 `seat_overrides` 校验块整体之后(`profile_config.py` 的 `for seat, fragment in seat_overrides.items(): _check_fragment(...)` 循环体最后一行 `:297` 之后、`counts` 统计 `:298` 之前)插入:

```python
    # seat_personas: per-seat ROLE-AGNOSTIC personality (tone/style only). MUST NOT encode
    # role abilities or team strategy (e.g. "你是狼/夜晚击杀/查验") — those belong to the role
    # contract; a role-coded persona would clash with the seat's actual role once role-shuffle
    # lands. Semantics are doc-enforced (not machine-checkable) here + in the field docstring.
    seat_personas = profile.get("seat_personas", {})
    if not isinstance(seat_personas, dict):
        raise ProfileValidationError("seat_personas must be an object")
    for sp_seat, persona in seat_personas.items():
        if sp_seat not in DEFAULT_SEAT_IDS:
            raise ProfileValidationError(f"unknown seat id in seat_personas: {sp_seat!r}")
        if not isinstance(persona, str):
            raise ProfileValidationError(
                f"seat_personas.{sp_seat} must be a role-agnostic personality string "
                f"(tone/style only; no role ability or team strategy), got {type(persona).__name__}"
            )
        if len(persona) > PROMPT_MAX_LEN:
            raise ProfileValidationError(
                f"seat_personas.{sp_seat} exceeds {PROMPT_MAX_LEN} chars "
                f"(role-agnostic personality; tone/style only)"
            )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config.SeatPersonasValidationTests -v`
Expected: PASS。

- [ ] **Step 5: Commit**(先 branch-check)

```bash
git branch --show-current   # feat/game-variety
git add src/werewolf_eval/profile_config.py tests/test_profile_config.py
git commit -m "feat(profile): validate optional seat_personas (role-agnostic, doc-enforced)"
```

---

## Task 4: `build_resolved_profile_artifact` 加 `effective_temperature`

**Files:**
- Modify: `src/werewolf_eval/profile_config.py:331-346`(seats append)
- Test: `tests/test_profile_config.py`

- [ ] **Step 1: 加失败测试**(effective_temperature additive + 组 1 现有字段 parity)

追加测试类:

```python
class ArtifactEffectiveTemperatureTests(unittest.TestCase):
    def test_effective_temperature_fills_null_from_policy(self):
        from werewolf_eval.profile_config import DEFAULT_LIVE_TEMPERATURE
        art = build_resolved_profile_artifact(_valid_profile(), "run1")
        for seat in art["seats"]:
            self.assertIsNone(seat["temperature"])                       # 显式配置值(null)不变
            self.assertEqual(seat["effective_temperature"], DEFAULT_LIVE_TEMPERATURE)  # additive 留痕

    def test_effective_temperature_uses_explicit_when_set(self):
        p = _valid_profile(seat_overrides={"p1": {"temperature": 0.3}})
        art = build_resolved_profile_artifact(p, "run1")
        by_pid = {s["player_id"]: s for s in art["seats"]}
        self.assertEqual(by_pid["p1"]["temperature"], 0.3)
        self.assertEqual(by_pid["p1"]["effective_temperature"], 0.3)

    def test_existing_fields_unchanged_except_additive(self):
        # 组 1:现有字段集 = 旧字段(去掉 additive effective_temperature)后与既定字段集一致
        art = build_resolved_profile_artifact(_valid_profile(), "run1")
        expected_keys = {"player_id", "role", "team", "provider", "model",
                         "strategy", "temperature", "max_tokens", "prompt_hash",
                         "effective_temperature"}
        self.assertEqual(set(art["seats"][0]), expected_keys)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config.ArtifactEffectiveTemperatureTests -v`
Expected: FAIL —— `KeyError: 'effective_temperature'`。

- [ ] **Step 3: 改 `build_resolved_profile_artifact`**(`profile_config.py`)

把 seats append 的 dict(`:334-345`)改为(加 `effective_temperature` + temperature 语义注释):

```python
        seats.append(
            {
                "player_id": seat_cfg["player_id"],
                "role": seat_cfg["role"],
                "team": seat_cfg["team"],
                "provider": seat_cfg["provider"],
                "model": seat_cfg["model"],
                "strategy": seat_cfg["strategy"],
                # temperature = EXPLICIT configured value (null = unset; filled at build_seat_agents).
                "temperature": seat_cfg.get("temperature"),
                # effective_temperature = additive: what the live run actually samples at
                # (explicit value, else the DEFAULT_LIVE_TEMPERATURE policy). Single-sourced
                # so old(API default) vs new(0.8) live runs are distinguishable in the artifact.
                "effective_temperature": (
                    seat_cfg["temperature"] if seat_cfg.get("temperature") is not None
                    else DEFAULT_LIVE_TEMPERATURE
                ),
                "max_tokens": seat_cfg.get("max_tokens"),
                "prompt_hash": _hash_text(prompt) if prompt else "",
            }
        )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config.ArtifactEffectiveTemperatureTests -v`
Expected: PASS。

- [ ] **Step 5: Commit**(先 branch-check)

```bash
git branch --show-current   # feat/game-variety
git add src/werewolf_eval/profile_config.py tests/test_profile_config.py
git commit -m "feat(profile): record additive seats[].effective_temperature in resolved-profile artifact"
```

---

## Task 5: `build_default_profile` 种入 `seat_personas`

**Files:**
- Modify: `src/werewolf_eval/profile_config.py`(加 `DEFAULT_SEAT_PERSONAS` + `build_default_profile`)
- Test: `tests/test_profile_config.py`

- [ ] **Step 1: 加失败测试**(组 5)

追加测试类:

```python
class DefaultProfileSeatPersonasTests(unittest.TestCase):
    def test_default_has_six_distinct_personas(self):
        p = build_default_profile()
        sp = p["seat_personas"]
        self.assertEqual(set(sp), {"p1", "p2", "p3", "p4", "p5", "p6"})
        self.assertEqual(len(set(sp.values())), 6)  # 互不相同

    def test_default_two_wolves_distinct_resolved_persona(self):
        p = build_default_profile()
        # 默认 6p:p1/p2 = werewolf
        self.assertNotEqual(_resolve_seat(p, "p1", "werewolf")["prompt"],
                            _resolve_seat(p, "p2", "werewolf")["prompt"])

    def test_default_validates_and_has_no_seeded_temperature(self):
        p = build_default_profile()
        validate_profile(p)  # 不得抛
        for frag in p["role_defaults"].values():
            self.assertNotIn("temperature", frag)  # 温度单源于常量,不种进 fake 模板
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config.DefaultProfileSeatPersonasTests -v`
Expected: FAIL —— `KeyError: 'seat_personas'`。

- [ ] **Step 3: 加 `DEFAULT_SEAT_PERSONAS` + 改 `build_default_profile`**

在 `DEFAULT_ROLE_PROMPTS`(`profile_config.py:77` 一带)之后加(全 role-agnostic,只写性格/语气):

```python
# Per-seat ROLE-AGNOSTIC personalities seeded into the default profile so same-role seats
# (e.g. the two wolves) are not clones out of the box. Tone/style ONLY — never role ability
# or team strategy (that lives in the role contract). Users edit per-seat from here.
DEFAULT_SEAT_PERSONAS: dict[str, str] = {
    "p1": "你说话沉稳,偏好用证据和逻辑链推理,不轻易下结论。",
    "p2": "你性格直率、爱挑头表态,常率先抛出怀疑对象并解释理由。",
    "p3": "你谨慎克制,先听后说,擅长复盘别人发言里的前后矛盾。",
    "p4": "你偏感性,善用语气和共情拉拢人心,容易被情绪带动。",
    "p5": "你话不多但一针见血,倾向用一句简短结论收尾。",
    "p6": "你表面松弛爱开玩笑,实则暗中观察并记住每个人的反应。",
}
```

把 `build_default_profile`(`:435-455`)的 `return` 改为带 `seat_personas`:

```python
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "name": name,
        "template": "default_6p_fake",
        "role_defaults": role_defaults,
        "seat_personas": dict(DEFAULT_SEAT_PERSONAS),
    }
```

> 注:不在 `role_defaults` 里种 `temperature`(温度政策单源于 `DEFAULT_LIVE_TEMPERATURE` 常量;fake 模板种 0.8 零效力且会让 fake artifact 记录 live 采样参数)。

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config.DefaultProfileSeatPersonasTests -v`
Expected: PASS。

- [ ] **Step 5: Commit**(先 branch-check)

```bash
git branch --show-current   # feat/game-variety
git add src/werewolf_eval/profile_config.py tests/test_profile_config.py
git commit -m "feat(profile): seed 6 distinct role-agnostic seat_personas into the default profile"
```

---

## Task 6: 全量回归 + fake 确定性背书

**Files:** none(验证)

- [ ] **Step 1: 跑改动模块全测**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config tests.test_seat_agents -v`
Expected: OK。

- [ ] **Step 2: 全量套件(含 fake-determinism canary,组 4 背书)**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | grep -E "^(Ran |OK|FAILED|ERROR)"`
Expected: `OK`(基线 947 + 本计划新增测试;**0 fail**)。全量含 default_6p_fake / run_emergent_fake_runtime 的确定性测试 —— 它们仍绿即证明"fake 对局字节不变、与温度管道零交集"(组 4 的字节背书,不另造)。

- [ ] **Step 3: 静态自检 —— 零避让区 + 零模板字节**

Run:
```bash
git diff --name-only main...HEAD -- src/ | sort
```
Expected: 仅 `src/werewolf_eval/profile_config.py` 与 `src/werewolf_eval/seat_agents.py`(无任何避让区文件)。
再 `git diff main...HEAD -- src/werewolf_eval/llm_providers.py` → **空**(未碰 `compose_system`/`build_*_system_prompt`)。

- [ ] **Step 4:(可选)冒烟:默认 profile 两狼 persona 实拼不同**

Run:
```bash
NO_PROXY='*' PYTHONPATH=src python -c "from werewolf_eval.profile_config import build_default_profile, resolve_profile; s={x['player_id']:x['prompt'] for x in resolve_profile(build_default_profile())}; print('p1==p2 ?', s['p1']==s['p2']); print('p1:', s['p1'][:40]); print('p2:', s['p2'][:40])"
```
Expected: `p1==p2 ? False`(两狼 = 同狼策略 + 不同个性)。

- [ ] **Step 5: Commit**(若无代码改动可跳过;否则先 branch-check)

无新增改动则不提交;Task 1-5 的 commit 即为交付。

---

## Self-Review(writing-plans checklist)

**Spec 覆盖**:② persona → Task 2(_resolve_seat)+ Task 3(validate)+ Task 5(默认种入);③ 温度 → Task 1(兜底)+ Task 4(effective_temperature 可观测);组 1 parity → Task 2/Task 4 内 parity 断言 + Task 6 全量;组 4 重写(fake 报错 + 全量背书)→ Task 1 + Task 6;约束 4(role-agnostic 文档声明)→ Task 3 注释/错误信息;约束 5(默认变更 vs 旧 parity 分组)→ Task 5(组 5)与 Task 2/4(组 1)分离。① 洗牌 deferred 不在本计划。

**Placeholder 扫描**:无 TBD;唯一"实施时确认"点 = Task 3 Step 1 的 secret 触发词(已给出 `grep _VALUE_SECRET_MARKERS` 取真实标记的具体做法,非占位)。

**类型/签名一致**:`DEFAULT_LIVE_TEMPERATURE`(profile_config 定义,seat_agents 与 build_resolved_profile_artifact 共用)、`default_temperature` 参数名、`seat_personas` 字段名、`effective_temperature` 字段名、`_resolve_seat` 签名不变(仍 `(profile, seat, role)`)—— 全计划一致。

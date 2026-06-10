# 角色洗牌(对局多样性子集 2/2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** opt-in 的**每局角色洗牌**——用变化种子洗"座位→角色"(保持 `{2狼,1预,1女,2民}` 多重集),**真正改变引擎角色板**(不是只改 artifact),并让 `resolved_seats`(persona/provider 路由)与引擎角色**同源对齐**;默认关时**逐字节不变**;洗牌种子落盘可复现。

**Architecture:** 单一洗牌源 = `compute_role_shuffle(profile, run_id|shuffle_seed)` → `{enabled, seed, seed_source, seat_roles}`。`resolve_profile_for_run` 用它产出带洗后角色的 `resolved_seats`;launcher 从 `resolved_seats` 抽出 `{seat:role}` 透传给 runner → `build_emergent_config(seat_roles=)` → `build_default_config(seat_roles=)`,使引擎按洗后角色开局。observer 把 `run_id` 提前并改调 `resolve_profile_for_run`。三处(artifact / launcher-resolved_seats / 引擎 config)都由**同一 run_id 种子**派生 → 完全一致。

**Tech Stack:** Python 3.12, stdlib `unittest`。测试命令:`NO_PROXY='*' PYTHONPATH=src python -m unittest tests.<module> -v`。

**前置(执行时)**:在**当前 main**(已含 prompt-versioning + game-variety 合并)上开隔离 worktree `feat/role-shuffle`;**每次 commit 前 `git branch --show-current` 必须是 `feat/role-shuffle`**(共享工作树曾错分支)。先跑全量基线确认绿。

**关键事实(对账当前 main 代码)**:
- 引擎角色来自 `run_emergent_deepseek_game.py:146 build_emergent_config(game_id)` = `emergent_engine.py:232` = `game_engine.py:91 build_default_config`(硬编码 p1/p2 狼、p3 预、p4 女、p5/p6 民)。
- `EmergentGameEngine.__init__`(emergent_engine.py:258-261)有 **R-30 守卫:必须恰好 1 预言家 + 1 女巫**;多重集守恒的洗牌自动满足。
- `resolved_seats[].role` 只入 provider 路由 + artifact;洗它不改对局(子集 1 的查证)——故必须同时洗引擎 config。
- observer launch handler(`observer_server.py:795`):`:831 resolved_seats = resolve_profile(profile)` 在 `:837 run_id = str(plr["run_id"])` **之前**;须把 run_id 提前。
- `build_resolved_profile_artifact`(profile_config.py:366)在 observer `:861` **同步**写盘(launch 前),内部 `:381 for seat_cfg in resolve_profile(profile)`。
- 常量:`ROLE_TEAMS`(profile_config:56)、`DEFAULT_6P_SEAT_ROLES`(:62)、`CANONICAL_DEFAULT_6P_ROLES`(:50)、`DEFAULT_SEAT_IDS`(:70)。

---

## File Structure

- **Modify** `src/werewolf_eval/profile_config.py`:`role_shuffle` 字段校验、`compute_role_shuffle`、`resolve_profile_for_run`、`build_resolved_profile_artifact` 记录洗牌 + 用 for-run 解析。
- **Modify** `src/werewolf_eval/game_engine.py`:`build_default_config(game_id, seat_roles=None)`。
- **Modify** `src/werewolf_eval/emergent_engine.py`:`build_emergent_config(game_id, seat_roles=None)` 透传。
- **Modify** `src/werewolf_eval/run_emergent_deepseek_game.py`:`run_emergent_deepseek_game(..., seat_roles=None)` → 引擎 config。
- **Modify** `src/werewolf_eval/deepseek_launcher.py`:`build_multi_provider_launcher` 闭包内从 `resolved_seats` 抽 `seat_roles` 透传 runner。
- **Modify** `src/werewolf_eval/observer_server.py`:launch handler 提前 `run_id` + 改调 `resolve_profile_for_run`。
- 测试:`tests/test_profile_config.py`、`tests/test_game_engine.py`(或 emergent)、`tests/test_deepseek_launcher.py`、新增 `tests/test_role_shuffle.py`(对齐 + 端到端)。

---

## 不变量(实现纪律)

1. **默认关逐字节**:`role_shuffle` 缺省/`enabled=false` 时,`resolve_profile_for_run==resolve_profile`、`build_default_config(seat_roles=None or 默认map)==build_default_config()`、artifact 现有字段不变、引擎 config 不变 → 字节 parity 套件全绿。
2. **同源对齐**:同一 `run_id`(或显式 `shuffle_seed`)→ artifact 角色 == launcher 喂引擎的 `seat_roles` == 引擎 god-view 角色,逐座位一致。
3. **多重集守恒**:洗的是角色值列表(`rng.shuffle(values)`),`{2狼1预1女2民}` 恒定 → R-30 守卫过。
4. **无静默兜底**:`enabled=true` 且既无 `run_id` 又无 `shuffle_seed` → `resolve_profile_for_run` 抛 `ProfileValidationError`;`resolve_profile`(预览/校验)永不洗、永不抛。
5. **显式优先**:`shuffle_seed` 给定时优先于 `run_id`(测试/复现用)。

---

## Task 1: profile_config — `role_shuffle` 校验 + `compute_role_shuffle` + `resolve_profile_for_run`

**Files:** Modify `src/werewolf_eval/profile_config.py`;Test `tests/test_profile_config.py`

- [ ] **Step 1: 失败测试**

在 `tests/test_profile_config.py` 顶部把新符号加入 import(私有用单独行):
```python
from werewolf_eval.profile_config import compute_role_shuffle, resolve_profile_for_run
```
追加测试类:
```python
class RoleShuffleTests(unittest.TestCase):
    def test_off_returns_default_layout(self):
        info = compute_role_shuffle(_valid_profile(), run_id="r", shuffle_seed=None)
        self.assertFalse(info["enabled"])
        self.assertIsNone(info["seed"])
        self.assertEqual(info["seat_roles"], {"p1":"werewolf","p2":"werewolf","p3":"seer","p4":"witch","p5":"villager","p6":"villager"})

    def test_on_preserves_multiset(self):
        info = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="run_abc", shuffle_seed=None)
        self.assertTrue(info["enabled"])
        self.assertEqual(sorted(info["seat_roles"].values()),
                         sorted(["werewolf","werewolf","seer","witch","villager","villager"]))
        self.assertEqual(info["seed_source"], "run_id")

    def test_explicit_seed_beats_run_id(self):
        a = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="X", shuffle_seed=12345)
        b = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="Y", shuffle_seed=12345)
        self.assertEqual(a["seat_roles"], b["seat_roles"])       # 同 seed 同布局,与 run_id 无关
        self.assertEqual(a["seed_source"], "explicit")

    def test_run_id_deterministic_and_varies(self):
        same1 = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="same", shuffle_seed=None)
        same2 = compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id="same", shuffle_seed=None)
        self.assertEqual(same1["seat_roles"], same2["seat_roles"])  # 同 run_id 可复现
        layouts = {tuple(compute_role_shuffle(_valid_profile(role_shuffle={"enabled": True}), run_id=f"r{i}", shuffle_seed=None)["seat_roles"].items()) for i in range(12)}
        self.assertGreater(len(layouts), 1)                         # 不同 run_id 出现多种布局

    def test_enabled_but_no_seed_raises(self):
        with self.assertRaises(ProfileValidationError):
            resolve_profile_for_run(_valid_profile(role_shuffle={"enabled": True}), run_id=None, shuffle_seed=None)

    def test_for_run_off_equals_resolve_profile(self):
        p = _valid_profile()
        self.assertEqual(resolve_profile_for_run(p, run_id="r"), resolve_profile(p))

    def test_for_run_on_applies_shuffle_roles(self):
        p = _valid_profile(role_shuffle={"enabled": True})
        seats = {s["player_id"]: s["role"] for s in resolve_profile_for_run(p, run_id="run_zzz")}
        self.assertEqual(sorted(seats.values()), sorted(["werewolf","werewolf","seer","witch","villager","villager"]))
        # role_defaults 是按角色的 -> 洗后某座位的 prompt 应等于其新角色的策略
        full = {s["player_id"]: s for s in resolve_profile_for_run(p, run_id="run_zzz")}
        for pid, s in full.items():
            self.assertIn(s["role"], ("werewolf","seer","witch","villager"))

    def test_role_shuffle_field_validates(self):
        validate_profile(_valid_profile(role_shuffle={"enabled": True}))
        validate_profile(_valid_profile(role_shuffle={"enabled": False}))
        validate_profile(_valid_profile())  # 无该键
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(role_shuffle={"enabled": "yes"}))   # 非 bool
        with self.assertRaises(ProfileValidationError):
            validate_profile(_valid_profile(role_shuffle=["x"]))                # 非 object

    def test_for_run_rechecks_shuffled_combos(self):
        # SHOULD-FIX 2:resolve_profile_for_run 对洗后每席补跑 _check_resolved_seat。
        # 超长角色策略 -> 必拒(任一局恰有 1 个 seer 席,会拿到该超长策略)。8001 > PROMPT_MAX_LEN(8000)。
        p = _valid_profile(role_shuffle={"enabled": True})
        p["role_defaults"]["seer"]["prompt"] = "x" * 8001
        with self.assertRaises(ProfileValidationError):
            resolve_profile_for_run(p, shuffle_seed=0)
```

- [ ] **Step 2: 跑 → 失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config.RoleShuffleTests -v`
Expected: FAIL(ImportError:`compute_role_shuffle` / `resolve_profile_for_run` 未定义)。

- [ ] **Step 3: 实现**(`profile_config.py`)

在模块顶部 import 区**必须新增 `import random`**(profile_config 当前有 `import hashlib`,但**没有 `random`**——不加则 `compute_role_shuffle` 运行时 `NameError: name 'random' is not defined`,plan-review B1)。

在 `validate_profile` 的 `allowed_top`(当前 `:297` 一带,game-variety 后含 `seat_personas`)加 `"role_shuffle"`:
```python
    allowed_top = {"schema_version", "name", "template", "role_defaults", "seat_overrides", "seat_personas", "role_shuffle"}
```
在 `seat_personas` 校验块之后(`counts` 统计之前)加 `role_shuffle` 校验:
```python
    role_shuffle = profile.get("role_shuffle", {})
    if not isinstance(role_shuffle, dict):
        raise ProfileValidationError("role_shuffle must be an object")
    if "enabled" in role_shuffle and not isinstance(role_shuffle["enabled"], bool):
        raise ProfileValidationError("role_shuffle.enabled must be a boolean")
```
在 `resolve_profile`(当前 `:356`)之后加两个函数:
```python
def compute_role_shuffle(profile: dict, *, run_id: str | None, shuffle_seed: int | None) -> dict:
    """Single source of the per-run role shuffle. Returns
    {enabled, seed, seed_source, seat_roles}. seat_roles preserves the template's canonical
    multiset; explicit shuffle_seed beats run_id; off -> default (template) layout."""
    base = _template_seat_roles(profile["template"])  # SHOULD-FIX 1: single source per template
    enabled = bool(profile.get("role_shuffle", {}).get("enabled", False))
    if not enabled:
        return {"enabled": False, "seed": None, "seed_source": None, "seat_roles": dict(base)}
    if shuffle_seed is not None:
        seed, seed_source = int(shuffle_seed), "explicit"
    elif run_id is not None:
        seed = int.from_bytes(hashlib.sha256(run_id.encode("utf-8")).digest()[:8], "big")
        seed_source = "run_id"
    else:
        seed, seed_source = None, None
    seat_order = list(base.keys())
    roles = [base[s] for s in seat_order]
    if seed is not None:
        random.Random(seed).shuffle(roles)
    return {"enabled": True, "seed": seed, "seed_source": seed_source,
            "seat_roles": dict(zip(seat_order, roles))}


def resolve_profile_for_run(profile: dict, *, run_id: str | None = None,
                            shuffle_seed: int | None = None) -> list[dict]:
    """Resolve seats for an ACTUAL run, applying role_shuffle. When role_shuffle is
    enabled, a seed (explicit or run_id-derived) is REQUIRED — no silent fallback to the
    default layout. Off -> identical to resolve_profile (byte-parity)."""
    info = compute_role_shuffle(profile, run_id=run_id, shuffle_seed=shuffle_seed)
    if info["enabled"] and info["seed"] is None:
        raise ProfileValidationError(
            "role_shuffle enabled but neither shuffle_seed nor run_id provided"
        )
    seat_roles = info["seat_roles"]
    resolved = [_resolve_seat(profile, seat, seat_roles[seat]) for seat in DEFAULT_SEAT_IDS]
    if info["enabled"]:
        # SHOULD-FIX 2: shuffle produces NEW (seat,role) combos validate_profile never checked
        # (it only validated the default mapping). Re-check each resolved seat — catches e.g. the
        # composed "new-role strategy + seat personality" exceeding PROMPT_MAX_LEN. No silent pass.
        for seat_cfg, seat in zip(resolved, DEFAULT_SEAT_IDS):
            _check_resolved_seat(seat_cfg, seat)
    return resolved
```

- [ ] **Step 4: 跑 → 通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_profile_config -v` → OK。

- [ ] **Step 5: Commit**(branch-check)
```bash
git branch --show-current   # feat/role-shuffle
git add src/werewolf_eval/profile_config.py tests/test_profile_config.py
git commit -m "feat(profile): role_shuffle field + compute_role_shuffle + resolve_profile_for_run (no silent fallback)"
```

---

## Task 2: profile_config — artifact 记录洗牌 + 用 for-run 解析

**Files:** Modify `src/werewolf_eval/profile_config.py:366-410`;Test `tests/test_profile_config.py`

- [ ] **Step 1: 失败测试**
```python
class ArtifactRoleShuffleTests(unittest.TestCase):
    def test_off_no_shuffle_block_and_default_roles(self):
        art = build_resolved_profile_artifact(_valid_profile(), "run1")
        self.assertEqual(art["role_shuffle"], {"enabled": False, "seed": None, "seed_source": None})
        roles = {s["player_id"]: s["role"] for s in art["seats"]}
        self.assertEqual(roles["p1"], "werewolf")  # 默认布局

    def test_on_records_seed_and_shuffled_roles(self):
        art = build_resolved_profile_artifact(_valid_profile(role_shuffle={"enabled": True}), "run_seed_x")
        self.assertTrue(art["role_shuffle"]["enabled"])
        self.assertEqual(art["role_shuffle"]["seed_source"], "run_id")
        self.assertIsInstance(art["role_shuffle"]["seed"], int)
        roles = sorted(s["role"] for s in art["seats"])
        self.assertEqual(roles, sorted(["werewolf","werewolf","seer","witch","villager","villager"]))

    def test_artifact_roles_match_resolve_for_run(self):
        p = _valid_profile(role_shuffle={"enabled": True})
        art = build_resolved_profile_artifact(p, "run_match")
        live = {s["player_id"]: s["role"] for s in resolve_profile_for_run(p, run_id="run_match")}
        self.assertEqual({s["player_id"]: s["role"] for s in art["seats"]}, live)  # 同源一致
```

- [ ] **Step 2: 跑 → 失败**(`KeyError: 'role_shuffle'`)。

- [ ] **Step 3: 实现**(`profile_config.py`)

把 `build_resolved_profile_artifact`(`:366`)签名旁的内部解析从 `resolve_profile(profile)` 改为 for-run,并加顶层 `role_shuffle` 块。改 `:381`:
```python
    info = compute_role_shuffle(profile, run_id=run_id, shuffle_seed=None)
    for seat_cfg in resolve_profile_for_run(profile, run_id=run_id):
```
在返回 dict(`:404-409` 一带,`"run_id": run_id` 同级)加:
```python
        "role_shuffle": {
            "enabled": info["enabled"], "seed": info["seed"], "seed_source": info["seed_source"],
        },
```
> 注:`resolve_profile_for_run(profile, run_id=run_id)` 与 `compute_role_shuffle(...)` 同 run_id → 一致;off 时 info.seed=None、布局默认 → 现有字段逐字节不变(只多一个 additive 顶层块)。

- [ ] **Step 4: 跑 → 通过**;`tests.test_profile_config` 全绿。

- [ ] **Step 5: Commit**(branch-check)
`git commit -m "feat(profile): artifact records role_shuffle{enabled,seed,seed_source} via resolve_profile_for_run"`

---

## Task 3: game_engine — `build_default_config(seat_roles=None)`

**Files:** Modify `src/werewolf_eval/game_engine.py:91-102`;Test `tests/test_game_engine.py`

- [ ] **Step 1: 失败测试**(新增或追加到现有 game_engine 测试)
```python
def test_build_default_config_default_is_unchanged():
    from werewolf_eval.game_engine import build_default_config, EnginePlayer, GameConfig
    cfg = build_default_config("g")
    assert [(p.player_id, p.role, p.team) for p in cfg.players] == [
        ("p1","werewolf","werewolf"),("p2","werewolf","werewolf"),
        ("p3","seer","villager"),("p4","witch","villager"),
        ("p5","villager","villager"),("p6","villager","villager")]

def test_build_default_config_with_seat_roles_shuffled():
    from werewolf_eval.game_engine import build_default_config
    sr = {"p1":"seer","p2":"villager","p3":"werewolf","p4":"witch","p5":"werewolf","p6":"villager"}
    cfg = build_default_config("g", seat_roles=sr)
    got = {p.player_id: (p.role, p.team) for p in cfg.players}
    assert got["p1"] == ("seer","villager")
    assert got["p3"] == ("werewolf","werewolf")
    assert [p.player_id for p in cfg.players] == ["p1","p2","p3","p4","p5","p6"]  # 座位序不变

def test_build_default_config_seat_roles_equal_default_is_identical():
    from werewolf_eval.game_engine import build_default_config
    sr = {"p1":"werewolf","p2":"werewolf","p3":"seer","p4":"witch","p5":"villager","p6":"villager"}
    assert build_default_config("g", seat_roles=sr) == build_default_config("g")
```

- [ ] **Step 2: 跑 → 失败**(`TypeError: unexpected keyword argument 'seat_roles'`)。

- [ ] **Step 3: 实现**(`game_engine.py:91-102`)
```python
_DEFAULT_SEAT_ORDER = ("p1", "p2", "p3", "p4", "p5", "p6")


def build_default_config(game_id: str = "g1b_mock_001", seat_roles: dict[str, str] | None = None) -> GameConfig:
    if seat_roles is None:
        return GameConfig(
            game_id=game_id,
            players=[
                EnginePlayer("p1", "werewolf", "werewolf"),
                EnginePlayer("p2", "werewolf", "werewolf"),
                EnginePlayer("p3", "seer", "villager"),
                EnginePlayer("p4", "witch", "villager"),
                EnginePlayer("p5", "villager", "villager"),
                EnginePlayer("p6", "villager", "villager"),
            ],
        )
    return GameConfig(
        game_id=game_id,
        players=[
            EnginePlayer(pid, seat_roles[pid], "werewolf" if seat_roles[pid] == "werewolf" else "villager")
            for pid in _DEFAULT_SEAT_ORDER
        ],
    )
```
> team 推导 `werewolf->werewolf, else villager` 与 `ROLE_TEAMS` 对 4 个默认角色一致(且 hunter->villager);不 import profile_config(保层级)。`seat_roles==默认` 时逐字段等于硬编码板(frozen dataclass 相等)。

- [ ] **Step 4: 跑 → 通过**。

- [ ] **Step 5: Commit**(branch-check)
`git commit -m "feat(engine): build_default_config accepts optional seat_roles (None -> byte-identical board)"`

---

## Task 4: emergent_engine — `build_emergent_config(seat_roles=None)` 透传

**Files:** Modify `src/werewolf_eval/emergent_engine.py:232-234`;Test `tests/test_emergent_engine.py`

- [ ] **Step 1: 失败测试**
```python
def test_build_emergent_config_passes_seat_roles():
    from werewolf_eval.emergent_engine import build_emergent_config
    sr = {"p1":"seer","p2":"villager","p3":"werewolf","p4":"witch","p5":"werewolf","p6":"villager"}
    cfg = build_emergent_config("g", seat_roles=sr)
    assert {p.player_id: p.role for p in cfg.players}["p1"] == "seer"

def test_build_emergent_config_default_unchanged():
    from werewolf_eval.emergent_engine import build_emergent_config, build_default_config
    assert build_emergent_config("g") == build_default_config("g")
```

- [ ] **Step 2: 跑 → 失败**。

- [ ] **Step 3: 实现**(`emergent_engine.py:232-234`)
```python
def build_emergent_config(game_id: str = "p2a1_emergent_001", seat_roles: dict[str, str] | None = None) -> GameConfig:
    """Default 6-player board: p1/p2 wolves, p3 seer, p4 witch, p5/p6 villagers.
    seat_roles (when given) overrides the per-seat role assignment (multiset preserved
    upstream); None -> the fixed default board (byte-identical to before)."""
    return build_default_config(game_id=game_id, seat_roles=seat_roles)
```

- [ ] **Step 4: 跑 → 通过**;字节 parity 套件(`test_emergent_*`)仍绿(默认路径不变)。

- [ ] **Step 5: Commit**(branch-check)
`git commit -m "feat(engine): build_emergent_config threads optional seat_roles to build_default_config"`

---

## Task 5: run_emergent_deepseek_game — `seat_roles` 参数 → 引擎 config

**Files:** Modify `src/werewolf_eval/run_emergent_deepseek_game.py:128-152`;Test `tests/test_role_shuffle.py`(新建)

- [ ] **Step 1: 失败测试**(端到端用现有 fake agents 驱动 runner,断言引擎按洗后角色开局)

新建 `tests/test_role_shuffle.py`:
```python
from __future__ import annotations
import sys, tempfile, json
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game
from werewolf_eval.emergent_fake_script import build_emergent_fake_agents, build_villager_win_script

def _factory():
    agents = build_emergent_fake_agents(build_villager_win_script())
    return lambda pid: agents[pid]

class RunnerSeatRolesTests(unittest.TestCase):
    def test_runner_accepts_seat_roles_and_engine_plays_them(self):
        sr = {"p1":"seer","p2":"villager","p3":"werewolf","p4":"witch","p5":"werewolf","p6":"villager"}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            run_emergent_deepseek_game(game_id="g", out_dir=out, provider_factory=_factory(),
                                       model="", seat_roles=sr)
            # setup god-view snapshot records the config roles — written UNCONDITIONALLY at
            # engine init (before the main loop), so it exists even if the role-mismatched
            # script later budget-exhausts. final_god_view.json would NOT exist on failure.
            god = json.loads((out / "snapshots" / "setup_god_view.json").read_text(encoding="utf-8"))
            roles = {p["player_id"]: p["role"] for p in god["players"]}
            self.assertEqual(roles["p3"], "werewolf")
            self.assertEqual(roles["p1"], "seer")
```
> 注(plan-review B3):用 **`setup_god_view.json`** 而非 `final_god_view.json` —— 前者在引擎 `__init__`/`_run_inner` 主循环前**无条件**写盘(结构同样是 `players[*].{player_id, role, team}`),后者只在对局正常完成时写。本测试 seat_roles 让 p1=预言家/p3=狼,而 `build_villager_win_script()` 仍按原角色编脚本 → 大量非法动作可能耗尽预算、不出 final 快照;但**只断言"引擎采纳了传入的 seat_roles"**,setup 快照足矣,不依赖结局。R-30 守卫满足(sr 恰好 1 预 1 女)。实施首步可先 `python -c` 打印一次 setup_god_view.json 确认字段名。

- [ ] **Step 2: 跑 → 失败**(`TypeError: unexpected keyword 'seat_roles'`)。

- [ ] **Step 3: 实现**(`run_emergent_deepseek_game.py:128-152`)

签名加 `seat_roles`:
```python
def run_emergent_deepseek_game(
    *,
    game_id: str,
    out_dir: Path,
    provider_factory: ProviderFactory,
    model: str,
    seed: int = 0,
    max_requests_per_game: int = 64,
    max_day_rounds: int = 3,
    source_label: str | None = None,
    seat_roles: dict[str, str] | None = None,
) -> int:
```
把 `:146` 的 config 改为:
```python
        config=build_emergent_config(game_id=game_id, seat_roles=seat_roles),
```

- [ ] **Step 4: 跑 → 通过**。

- [ ] **Step 5: Commit**(branch-check)
`git commit -m "feat(runner): run_emergent_deepseek_game accepts seat_roles -> shuffled engine board"`

---

## Task 6: deepseek_launcher — 从 resolved_seats 抽 seat_roles 透传 runner

**Files:** Modify `src/werewolf_eval/deepseek_launcher.py:250-267`;Test `tests/test_role_shuffle.py`

- [ ] **Step 1: 失败测试**(注入 mock runner 捕获 seat_roles)
```python
from werewolf_eval.deepseek_launcher import build_multi_provider_launcher
from werewolf_eval.seat_agents import ProviderCredential

def _seat(pid, role):
    return {"player_id": pid, "provider": "deepseek", "model": "deepseek-v4-flash",
            "role": role, "team": "werewolf" if role=="werewolf" else "villager",
            "strategy": "default", "prompt": "", "temperature": None, "max_tokens": None}

class LauncherSeatRolesTests(unittest.TestCase):
    def test_launcher_passes_resolved_seat_roles_to_runner(self):
        captured = {}
        def fake_runner(**kw):
            captured.update(kw); return 0
        seats = [_seat("p1","seer"), _seat("p2","villager"), _seat("p3","werewolf"),
                 _seat("p4","witch"), _seat("p5","werewolf"), _seat("p6","villager")]
        launcher = build_multi_provider_launcher(
            resolved_seats=seats, credentials={"deepseek": ProviderCredential(key="sk")},
            transport=lambda *a, **k: {"choices":[{"message":{"content":"{}"}}],"usage":{}},
            runner=fake_runner)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            launcher("rid", Path(d))
        self.assertEqual(captured["seat_roles"],
                         {"p1":"seer","p2":"villager","p3":"werewolf","p4":"witch","p5":"werewolf","p6":"villager"})
```

- [ ] **Step 2: 跑 → 失败**(`KeyError: 'seat_roles'`)。

- [ ] **Step 3: 实现**(`deepseek_launcher.py:250-267`)

在 `_launcher` 闭包里、`runner(...)` 调用处加 `seat_roles`:
```python
    def _launcher(run_id: str, run_dir: Path) -> int:
        rdir = Path(run_dir)
        agents = build_seat_agents(
            resolved_seats, credentials, max_requests=max_requests,
            timeout_seconds=timeout_seconds, default_max_tokens=default_max_tokens, transport=transport,
        )
        seat_roles = {s["player_id"]: s["role"] for s in resolved_seats}
        code = runner(
            game_id=run_id, out_dir=rdir, provider_factory=lambda pid: agents[pid],
            model="", max_requests_per_game=max_requests, max_day_rounds=max_day_rounds,
            seat_roles=seat_roles,
        )
        if code == 0:
            return 0
        if _audit_is_budget_exhausted(rdir / "failure-audit.json"):
            return 3
        return 2
```
> 当洗牌关时 `resolved_seats` 角色=默认 → `seat_roles`=默认 map → `build_default_config(seat_roles=默认)` 字节等于硬编码板(Task 3 已测)→ 关时引擎 config 不变。

- [ ] **Step 4: 跑 → 通过**;`tests.test_role_shuffle` 全绿。

- [ ] **Step 5: Commit**(branch-check)
`git commit -m "feat(launcher): thread resolved seat_roles from resolved_seats into the runner"`

---

## Task 7: observer_server — 提前 run_id + 改调 resolve_profile_for_run

**Files:** Modify `src/werewolf_eval/observer_server.py:829-837`;Test:见 Task 8 端到端(observer 难单测,靠 resolve/launcher/runner 测 + 端到端覆盖)

- [ ] **Step 1: 改 launch handler**(`observer_server.py`)

import 区(`:58` 一带 `build_resolved_profile_artifact` 同处)加 `resolve_profile_for_run`:
```python
from werewolf_eval.profile_config import (
    ...,
    resolve_profile,
    resolve_profile_for_run,
    ...
)
```
把 `:829-837` 的顺序调整为 **run_id 先于 resolve**,并改调 for-run:
```python
        run_id = str(plr["run_id"])
        resolved_seats: list[dict] = []
        if mode == "live":
            resolved_seats = resolve_profile_for_run(profile, run_id=run_id)
            shape_reject = _check_live_profile_shape(resolved_seats)
            if shape_reject is not None:
                self._send_error_json(*shape_reject)
                return
```
删除原 `:837` 处重复的 `run_id = str(plr["run_id"])`(已上移)。`:995` 预览端点 `resolve_profile(body)` **保持不变**(明确不洗)。`:861 build_resolved_profile_artifact(profile, run_id, ...)` 不动(内部已走 for-run,Task 2)。

> shape gate(`_check_live_profile_shape`)只查 provider/credential,与角色无关 → 喂洗后 seats 不受影响。launcher 经 `_resolve_live_launcher_for_launch(state, resolved_seats)` 捕获的就是洗后 seats → 引擎角色对齐。

- [ ] **Step 2: 跑 observer 相关测试 + 全量**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_observer_server -v` → OK(默认 profile 无 role_shuffle → for-run==resolve_profile,行为不变)。

- [ ] **Step 3: Commit**(branch-check)
`git commit -m "feat(observer): hoist run_id + route live launch seats through resolve_profile_for_run"`

---

## Task 7.5: 拒绝 fake + role_shuffle(400)— BLOCKING(spec §1.1 错位防护)

**Files:** Modify `src/werewolf_eval/observer_server.py`(`_handle_profile_launch`);Test `tests/test_observer_server.py`(`LiveDispatchTests`)

**为何(plan-review 漏、用户抓)**:fake launch 也同步写 artifact(`observer_server.py:861`,`execution_mode="fake"`),而 Task 2 让 artifact 走 `resolve_profile_for_run` → 开了 shuffle 的 profile 在 fake 局会记录**洗后角色 + enabled + seed**;但 fake 分支 launcher 是 `state.launcher`(固定板 `run_emergent_fake_runtime`,不接 `seat_roles`,Task 6 只接了 live 的 multi-provider)→ 引擎按默认板跑 → **artifact 说洗了、引擎没洗** = spec §1.1 错位,破坏不变量 2。且全库唯一模板就是 `default_6p_fake`,用户在 Qt 沙盘开 shuffle 后**先 fake 试跑**是最自然操作。fake 脚本按角色编排,洗了只会预算耗尽、功能无意义 → fail-closed 拒绝(符合不变量 4)。

- [ ] **Step 1: 失败测试**(`LiveDispatchTests` 内,沿用 `_dispatch`/`_deepseek_profile`/`responses`)
```python
    def test_fake_mode_with_role_shuffle_is_400(self) -> None:
        prof = _deepseek_profile()
        prof["role_shuffle"] = {"enabled": True}
        body = {"profile": prof, "run_id": "r_fs", "mode": "fake"}
        h, runs = self._dispatch(body, live_enabled=True, live_launcher_set=True)
        self.assertEqual(h.responses[-1][0], 400)
        self.assertEqual(h.responses[-1][1].get("code"), "shuffle_requires_live")
        self.assertFalse((self._run_dir(runs, "r_fs") / "fake.sentinel").exists())  # 未起跑

    def test_mode_omitted_with_role_shuffle_is_400(self) -> None:
        # mode 省略默认 fake -> 同样拒绝
        prof = _deepseek_profile()
        prof["role_shuffle"] = {"enabled": True}
        h, runs = self._dispatch({"profile": prof, "run_id": "r_om"}, live_enabled=True, live_launcher_set=True)
        self.assertEqual(h.responses[-1][0], 400)
        self.assertEqual(h.responses[-1][1].get("code"), "shuffle_requires_live")
```
> 注:`_deepseek_profile()` 是 test_observer_server 模块级 helper;加 `role_shuffle` 键需 Task 1 的 validate 接受(本任务排在 Task 1 之后)。`mode` 省略时 `parse_profile_launch_request` 默认 `"fake"`(见现有 `test_mode_omitted_runs_fake_launcher`)。

- [ ] **Step 2: 跑 → 失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_observer_server.LiveDispatchTests.test_fake_mode_with_role_shuffle_is_400 -v`
Expected: FAIL(当前无此门 → fake+shuffle 继续走、不返回 400 → 断言 `responses[-1][0]==400` 失败)。

- [ ] **Step 3: 实现**(`observer_server.py` `_handle_profile_launch`)

在 `validate_profile(profile)`(`~:816-824`)之后、`if mode == "live":`(Task 7 后的 resolve 块,`~:830`)**之前**插入(`mode` 在 `:798` 已取、`profile` 已取):
```python
        if mode != "live" and profile.get("role_shuffle", {}).get("enabled", False):
            self._send_error_json(
                400, "shuffle_requires_live",
                "role_shuffle requires live mode (multi-provider path); fake mode runs a fixed "
                "board and would mislabel the artifact",
            )
            return
```

- [ ] **Step 4: 跑 → 通过**;`tests.test_observer_server` 全绿(其余 fake/live 路径不受影响:它们的 `_deepseek_profile()` 无 `role_shuffle`)。

- [ ] **Step 5: Commit**(branch-check)
`git commit -m "feat(observer): reject fake-mode launch with role_shuffle.enabled (400) — artifact/engine alignment"`

---

## Task 8: 端到端对齐 + 全量回归

**Files:** Test `tests/test_role_shuffle.py`

- [ ] **Step 1: 对齐测试**(同 run_id → artifact 角色 == 引擎 god-view 角色)
```python
class AlignmentTests(unittest.TestCase):
    def test_artifact_and_engine_roles_agree_under_shuffle(self):
        from werewolf_eval.profile_config import build_resolved_profile_artifact, resolve_profile_for_run
        # 用同一 run_id 跑 for-run(launcher 角色源)+ artifact;断言两者角色一致
        prof = {"schema_version":"g2d.profile.v1","name":"t","template":"default_6p_fake",
                "role_defaults":{r:{"provider":"fake_deterministic","model":"none","prompt":"","strategy":"default"}
                                 for r in ("werewolf","seer","witch","villager")},
                "role_shuffle":{"enabled":True}}
        rid = "run_align_42"
        art_roles = {s["player_id"]: s["role"] for s in build_resolved_profile_artifact(prof, rid)["seats"]}
        live_roles = {s["player_id"]: s["role"] for s in resolve_profile_for_run(prof, run_id=rid)}
        self.assertEqual(art_roles, live_roles)
        self.assertEqual(sorted(art_roles.values()), sorted(["werewolf","werewolf","seer","witch","villager","villager"]))
```

- [ ] **Step 2: 跑 → 通过**。

- [ ] **Step 3: 全量回归(默认关字节不变的总证)**

Run: `NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | grep -E "^(Ran |OK|FAILED|ERROR)"`
Expected: `OK`(基线 + 新测试;0 fail)。字节 parity / determinism 套件全绿即证明**默认关时引擎 config / artifact 现有字段 / resolved_seats 逐字节不变**。

- [ ] **Step 4: 静态自检**

Run: `git diff --name-only main...HEAD -- src/ | sort`
Expected: 仅 `profile_config.py / game_engine.py / emergent_engine.py / run_emergent_deepseek_game.py / deepseek_launcher.py / observer_server.py`。

- [ ] **Step 5:(可选)冒烟:洗牌开时不同 run_id 布局不同**
```bash
NO_PROXY='*' PYTHONPATH=src python -c "from werewolf_eval.profile_config import compute_role_shuffle as c; p={'role_shuffle':{'enabled':True}}; print({rid: c(p,run_id=rid,shuffle_seed=None)['seat_roles']['p3'] for rid in ['a','b','c','d']})"
```
Expected: 不同 run_id 下 p3 角色出现多种(布局确实每局变)。

---

## Self-Review(writing-plans checklist)

**覆盖**:洗牌引擎生效=Task 3/4/5/6(config 链路)+ Task 7(observer 喂洗后 seats);单源(`_template_seat_roles` 基底,SHOULD-FIX 1)/无静默/显式优先/多重集/洗后组合补校验(SHOULD-FIX 2)=Task 1;落盘可复现=Task 2;**fake+shuffle 错位防护(400)=Task 7.5(BLOCKING)**;同源对齐=Task 8;默认关字节不变=每任务 parity 断言 + Task 8 全量。R-30 守卫由多重集守恒满足(Task 1 测)。`seat_overrides.prompt`×shuffle 不兼容=已知限制清单。

**Placeholder 扫描**:唯一"按实际结构调整"点 = Task 5 的 god snapshot 字段名(已说明:断言"引擎角色==seat_roles"不变,字段读取以 `build_god_snapshot` 实际结构为准——实施首步先 `python -c` 打印一次 final_god_view.json 结构再定断言)。

**类型/签名一致**:`compute_role_shuffle(profile,*,run_id,shuffle_seed)->dict{enabled,seed,seed_source,seat_roles}`、`resolve_profile_for_run(profile,*,run_id,shuffle_seed)`、`build_default_config(game_id,seat_roles=None)`、`build_emergent_config(game_id,seat_roles=None)`、`run_emergent_deepseek_game(...,seat_roles=None)`、launcher 抽 `{s['player_id']:s['role']}` —— 全链路一致。

**已知后果/限制(写明,非缺陷)**:
- `role_defaults` 按角色 → 洗牌开时某座位的 provider/model 跟其新角色走(均匀 deepseek profile 无差异;混合模型 profile 会让模型随角色移动)。洗牌是 opt-in、默认关,受控评测(每座位绑模型)保持不洗即不受影响。
- **`seat_overrides[seat].prompt` 与 shuffle 不兼容**(用户指出):它的语义是"该**座位**的角色策略覆盖"——洗牌后它跟座位走、与该座位的**新角色**错位(注:`seat_overrides` 的 provider/model 座位绑定不受影响,那正是混搭场景想要的;只有 `.prompt` 错位)。**洗牌 profile 的策略只放 `role_defaults.prompt`(跟角色)、个性放 `seat_personas`(role-agnostic 跟座位),不要用 `seat_overrides.prompt`。** 这是 game-variety 分层设计的自然推论。(用户的 `deepseek_v4_flash_6p` 无 `seat_overrides`,兼容;若将来加了带 `.prompt` 的 override 再开 shuffle,须先清。)
- **legacy 单供应商 launcher**(`deepseek_launcher.build_emergent_deepseek_launcher`,无 profile/resolved_seats 的旧 env-key 路径)**不支持洗牌**——其 `runner(...)` 不传 `seat_roles`(默认 None=默认板)。P2-B-3 合并后 live 局走 `build_multi_provider_launcher`(本计划 Task 6 覆盖),legacy 路径仅在 `multi_provider_launcher_factory is None` 时触发。属文档化限制(plan-review N1),非 bug。
- **`build_resolved_profile_artifact` 内 `compute_role_shuffle` 与 `resolve_profile_for_run` 各算一次同一洗牌**(plan-review N2):确定性同结果、纯 stdlib 无 IO,刻意保留以求代码简单;若在意可让 artifact 把 `info["seat_roles"]` 透传给一个 `resolve_profile_for_run(..., _seat_roles=...)` 变体,本计划不做。

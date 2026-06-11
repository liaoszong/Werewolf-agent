# 消融度量台(Ablation Metrics Harness)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建成可复现的消融度量台:给定一个实验臂(arm),跑 N 局 live、按 `live_success_rate` 过滤、`budget_exhausted` hard fail,并由纯函数 metrics 产出诊断报告 §6 的全套聚合指标 + 两臂对比。

**Architecture:** 新增包 `src/werewolf_eval/ablation/`,三层解耦:`arms.py`(配置 + 每局布局) → `harness.py`(编排:每局新建 provider、有效性门禁、落盘) → `metrics.py`(纯函数:只读 artifacts 出指标)。CLI 经 `__main__.py` 暴露 `run` / `compare`。复用 `run_emergent_deepseek_game`(已有)。这是 Part A;SYS-B1 上下文修复是后续独立 plan。

**Tech Stack:** Python 3、pytest、`werewolf_eval.run_emergent_deepseek_game`、`DeepSeekProvider`。无新依赖。

---

## 这份 plan 来自的 spec
`docs/superpowers/specs/2026-06-10-quality-ablation-harness-and-b1-context-design.md`(§2 Part A)。本 plan **只做 Part A**(度量台);Part B(B1 上下文)单独成 plan。

## 设计要点(固化诊断期踩坑)
- **每局新建 provider**:共享 `DeepSeekProvider` 的 64 次预算跨局复用会耗光→兜底 RNG。
- **live 率过滤**:`live_success_rate < 0.7` 的局剔除并计数,绝不混进行为指标。
- **`budget_exhausted` hard fail**:任一局触发预算耗尽→标 invalid,不进聚合,计数。
- **配对 seed**:所有臂共用同一 seed 序列(`seed_base + index`,`seed_base` 全局固定),逐局配对。
- **确定性边界**:seed 只保证布局/洗牌可复现,温度 0.8 + API 非确定→对局不逐字复现。

## 文件结构
- Create `src/werewolf_eval/ablation/__init__.py` — 导出 `Arm`, `run_arm`, `aggregate`, `compare`。
- Create `src/werewolf_eval/ablation/arms.py` — `Arm` dataclass + `layout_for(arm, index)` 布局生成。
- Create `src/werewolf_eval/ablation/metrics.py` — 纯函数:`classify_event`, `analyze_game`, `live_rate`, `aggregate`, `compare`。
- Create `src/werewolf_eval/ablation/harness.py` — `run_arm(arm, out_root, api_key) -> dict`。
- Create `src/werewolf_eval/ablation/__main__.py` — CLI `run` / `compare`。
- Create `tests/test_ablation_metrics.py` — metrics 纯函数单测(fixtures)。
- Create `tests/test_ablation_arms.py` — 布局/配对 seed 单测。
- Create `tests/test_ablation_harness_fake.py` — fake 模式冒烟。
- Create `tests/fixtures/ablation/` — 2-3 个**脱敏后**的真 run 目录。

---

### Task 1: `Arm` 配置 + 配对布局

**Files:**
- Create: `src/werewolf_eval/ablation/__init__.py`
- Create: `src/werewolf_eval/ablation/arms.py`
- Test: `tests/test_ablation_arms.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_ablation_arms.py
from werewolf_eval.ablation.arms import Arm, layout_for, CANONICAL_MULTISET

def test_layout_is_canonical_multiset_and_paired_by_index():
    a = Arm(label="baseline", prompt_version="prompt_v1", n_games=4, seed_base=1000)
    b = Arm(label="b1", prompt_version="prompt_v2", n_games=4, seed_base=1000)
    # 同 index → 同布局(配对);多重集恒为 2狼1预1女2民
    for i in range(4):
        la, lb = layout_for(a, i), layout_for(b, i)
        assert la == lb, "paired arms must share layout per index"
        assert sorted(la.values()) == sorted(CANONICAL_MULTISET)
        assert set(la) == {"p1","p2","p3","p4","p5","p6"}

def test_seed_for_index_is_seed_base_plus_index():
    a = Arm(label="x", prompt_version="prompt_v1", n_games=3, seed_base=2000)
    assert [a.seed_for(i) for i in range(3)] == [2000, 2001, 2002]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_arms.py -q`
Expected: FAIL（ModuleNotFoundError: werewolf_eval.ablation.arms）

- [ ] **Step 3: 写最小实现**

```python
# src/werewolf_eval/ablation/__init__.py
from werewolf_eval.ablation.arms import Arm, layout_for
from werewolf_eval.ablation.metrics import aggregate, compare
from werewolf_eval.ablation.harness import run_arm

__all__ = ["Arm", "layout_for", "aggregate", "compare", "run_arm"]
```

```python
# src/werewolf_eval/ablation/arms.py
"""Ablation arm config + paired, canonical-multiset layout generation."""
from __future__ import annotations
import random
from dataclasses import dataclass

SEATS = ("p1", "p2", "p3", "p4", "p5", "p6")
CANONICAL_MULTISET = ("werewolf", "werewolf", "seer", "witch", "villager", "villager")


@dataclass(frozen=True)
class Arm:
    label: str
    prompt_version: str          # "prompt_v1" (baseline) | "prompt_v2" (b1) — runtime selector
    n_games: int = 45
    seed_base: int = 1000        # GLOBAL-fixed across arms -> paired comparison
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"

    def seed_for(self, index: int) -> int:
        return self.seed_base + index


def layout_for(arm: Arm, index: int) -> dict[str, str]:
    """Deterministic per-index shuffled layout. Same index -> same layout for ALL arms
    (depends only on seed, not on the arm), so arms are paired."""
    rng = random.Random(arm.seed_for(index))
    roles = list(CANONICAL_MULTISET)
    rng.shuffle(roles)
    return dict(zip(SEATS, roles))
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_arms.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/ablation/__init__.py src/werewolf_eval/ablation/arms.py tests/test_ablation_arms.py
git commit -m "feat(ablation): Arm config + paired canonical-multiset layout"
```

---

### Task 2: metrics — 事件分类 + 单局分析

**Files:**
- Create: `src/werewolf_eval/ablation/metrics.py`
- Test: `tests/test_ablation_metrics.py`

> artifact 形状(诊断期已确证):`game-log.json` = `{players:[{player_id,role,team}], events:[{round,phase,actor,target,data:{summary}}], result:{winner,end_round}}`;事件 `action` 字段恒 `None`,**类型在 `data.summary` 文本里**。`provider-turns.json` = `{turns:[{kind:"live_success"|...}]}` 或顶层 list。

- [ ] **Step 1: 写失败测试**(用内联构造的最小 game-log dict，不依赖真 fixtures)

```python
# tests/test_ablation_metrics.py
from werewolf_eval.ablation.metrics import classify_event, analyze_game_dict

def _ev(rnd, phase, actor, target, summary):
    return {"round": rnd, "phase": phase, "actor": actor, "target": target, "data": {"summary": summary}}

def test_classify_event_kinds():
    assert classify_event(_ev(1,"night","p4","p1","Wolf team kills p1."))[0] == "kill"
    assert classify_event(_ev(1,"night","p2","p1","Seer p2 checks p1, result: werewolf."))[0] == "check"
    assert classify_event(_ev(1,"night","p3",None,"Witch p3 saves p1."))[0] == "witch_save"
    assert classify_event(_ev(1,"night","p3",None,"Witch p3 uses no potion."))[0] == "witch_pass"
    assert classify_event(_ev(1,"day","p1","p3","p1 votes p3."))[0] == "vote"
    assert classify_event(_ev(1,"day","p1",None,"各位好，我怀疑p3。"))[0] == "speech"

def test_analyze_game_dict_basic():
    gl = {
        "players": [
            {"player_id":"p1","role":"seer","team":"villager"},
            {"player_id":"p2","role":"werewolf","team":"werewolf"},
            {"player_id":"p3","role":"villager","team":"villager"},
            {"player_id":"p4","role":"witch","team":"villager"},
            {"player_id":"p5","role":"werewolf","team":"werewolf"},
            {"player_id":"p6","role":"villager","team":"villager"},
        ],
        "result": {"winner":"villager","end_round":2},
        "events": [
            _ev(1,"night","p2","p1","Wolf team kills p1."),
            _ev(1,"night","p1","p2","Seer p1 checks p2, result: werewolf."),
            _ev(1,"night","p4",None,"Witch p4 saves p1."),
            _ev(1,"day","p1",None,"我验了p2是狼，投p2。他眼神躲闪。"),
            _ev(1,"day","p1","p2","p1 votes p2."),
            _ev(1,"day","p3","p2","p3 votes p2."),
            _ev(1,"day","p4","p2","p4 votes p2."),
            _ev(1,"day","p5","p1","p5 votes p1."),
            _ev(1,"day","p6","p2","p6 votes p2."),
        ],
    }
    g = analyze_game_dict(gl)
    assert g["winner"] == "villager"
    assert g["seer"] == "p1"
    assert g["night1_kill"] == "p1"
    assert g["seer_r1_check"] == ("p2","werewolf")
    assert g["witch_save"] is True and g["witch_poison"] is False
    assert g["d1_majority"] == "p2" and g["d1_majority_is_wolf"] is True
    # seer 验到狼 p2 且当日多数票投出 p2
    assert g["verify_wolf_followed"] is True
    # 视觉幻觉词命中
    assert g["has_visual_halluc"] is True
    # 羊群:5 票中 4 票投 p2(p2 不投票)= 4/5
    assert abs(g["herd_share"] - 0.8) < 1e-9
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py -q`
Expected: FAIL (ImportError)

- [ ] **Step 3: 写实现**

```python
# src/werewolf_eval/ablation/metrics.py
"""Read-only metrics over emergent-game artifacts. Pure functions; no side effects."""
from __future__ import annotations
import json, re, collections
from pathlib import Path

VISUAL_WORDS = ("眼神", "表情", "紧张", "躲闪", "支支吾吾", "语气", "闪躲")
MECHANIC_WORDS = ("警徽", "警长", "警上", "警下", "守卫", "守夜人")
LIVE_RATE_MIN = 0.7


def classify_event(ev: dict):
    """-> (kind, actor, target, extra). kind in {kill,check,witch_save,witch_pass,
    witch_poison,vote,elim,reveal,night_death,speech,other}."""
    s = (ev.get("data") or {}).get("summary", "") or ""
    actor, tgt, ph = ev.get("actor"), ev.get("target"), ev.get("phase")
    m = re.match(r"Wolf team kills (p\d)", s)
    if m: return ("kill", actor, m.group(1), None)
    m = re.match(r"Seer (p\d) checks (p\d), result: (\w+)", s)
    if m: return ("check", m.group(1), m.group(2), m.group(3))
    if "saves" in s:
        m = re.search(r"saves (p\d)", s); return ("witch_save", actor, m.group(1) if m else tgt, None)
    if "no potion" in s: return ("witch_pass", actor, None, None)
    if "poison" in s.lower():
        m = re.search(r"poisons? (p\d)", s); return ("witch_poison", actor, m.group(1) if m else tgt, None)
    m = re.match(r"(p\d) votes (p\d)", s)
    if m: return ("vote", m.group(1), m.group(2), None)
    if "eliminated by vote" in s: return ("elim", "system", tgt, None)
    m = re.search(r"(p\d) revealed as (\w+)", s)
    if m: return ("reveal", m.group(1), None, m.group(2))
    if "died during the night" in s: return ("night_death", "system", tgt, None)
    if ph == "day" and actor and re.match(r"p\d$", str(actor)) and "votes" not in s:
        return ("speech", actor, None, s)
    return ("other", actor, tgt, s)


def analyze_game_dict(gl: dict) -> dict:
    roles = {p["player_id"]: p["role"] for p in gl["players"]}
    wolves = {k for k, v in roles.items() if v == "werewolf"}
    seer = next((k for k, v in roles.items() if v == "seer"), None)
    res = gl.get("result") or {}
    votes = collections.defaultdict(list)   # round -> [(voter,target)]
    speeches = []                            # (round, actor, text)
    kills, checks = {}, {}
    save = poison = False
    deaths = []                              # (round, pid, cause)
    for ev in gl["events"]:
        kind, a, t, extra = classify_event(ev)
        r = ev.get("round")
        if kind == "kill": kills[r] = t
        elif kind == "check": checks[r] = (t, extra)
        elif kind == "witch_save": save = True
        elif kind == "witch_poison": poison = True
        elif kind == "vote": votes[r].append((a, t))
        elif kind == "speech": speeches.append((r, a, extra))
        elif kind == "elim": deaths.append((r, t, "vote"))
        elif kind == "night_death": deaths.append((r, t, "night"))

    def majority(r):
        c = collections.Counter(t for _, t in votes.get(r, []))
        return c.most_common(1)[0] if c else (None, 0)

    d1, d1n = majority(1)
    d1_total = len(votes.get(1, []))
    seer_chk = checks.get(1)
    seer_chk_role = roles.get(seer_chk[0]) if seer_chk else None
    seer_death = next(((r, c) for (r, p, c) in deaths if p == seer), None)
    # verify-wolf-followed: 预言家夜1验到狼 且 当日多数票=该狼
    verify_wolf_followed = None
    if seer_chk and seer_chk[1] == "werewolf":
        verify_wolf_followed = (d1 == seer_chk[0])
    # herd share per round (avg over rounds with votes)
    shares = []
    for r in votes:
        _, n = majority(r)
        tot = len(votes[r])
        if tot: shares.append(n / tot)
    text_all = " ".join(t for _, _, t in speeches)
    return {
        "roles": roles, "seer": seer, "wolves": sorted(wolves),
        "winner": res.get("winner"), "end_round": res.get("end_round"),
        "night1_kill": kills.get(1), "night1_kill_role": roles.get(kills.get(1)),
        "seer_r1_check": seer_chk, "seer_r1_target_role": seer_chk_role,
        "d1_majority": d1, "d1_majority_is_wolf": (d1 in wolves) if d1 else None,
        "d1_total": d1_total,
        "d2_majority_is_wolf": (majority(2)[0] in wolves) if majority(2)[0] else None,
        "verify_wolf_followed": verify_wolf_followed,
        "witch_save": save, "witch_poison": poison,
        "seer_death_cause": seer_death[1] if seer_death else None,
        "seer_survives_d1": not (seer_death and seer_death[0] == 1),
        "herd_share": sum(shares) / len(shares) if shares else None,
        "has_visual_halluc": any(w in text_all for w in VISUAL_WORDS),
        "has_mechanic_halluc": any(w in text_all for w in MECHANIC_WORDS),
        "n_speeches": len(speeches),
        "n_visual_speeches": sum(1 for _, _, t in speeches if any(w in t for w in VISUAL_WORDS)),
        "n_mechanic_speeches": sum(1 for _, _, t in speeches if any(w in t for w in MECHANIC_WORDS)),
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/ablation/metrics.py tests/test_ablation_metrics.py
git commit -m "feat(ablation): event classifier + per-game analyzer (pure)"
```

---

### Task 3: metrics — live_rate 过滤 + 聚合

**Files:**
- Modify: `src/werewolf_eval/ablation/metrics.py`
- Test: `tests/test_ablation_metrics.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_ablation_metrics.py
from werewolf_eval.ablation.metrics import live_rate_from_turns, aggregate_games

def test_live_rate_from_turns():
    assert live_rate_from_turns({"turns":[{"kind":"live_success"}]*9 + [{"kind":"timeout_then_fallback"}]}) == 0.9
    assert live_rate_from_turns({"turns":[]}) == 0.0

def test_aggregate_filters_low_live_and_counts():
    g_win = {"winner":"villager","d1_majority_is_wolf":True,"verify_wolf_followed":True,
             "witch_save":True,"witch_poison":False,"herd_share":0.83,"has_visual_halluc":True,
             "has_mechanic_halluc":False,"n_speeches":6,"n_visual_speeches":2,"n_mechanic_speeches":0,
             "night1_kill":"p1","end_round":2,"seer_survives_d1":True}
    g_loss = dict(g_win); g_loss["winner"]="werewolf"; g_loss["d1_majority_is_wolf"]=False
    agg = aggregate_games([g_win, g_loss])
    assert agg["n_valid"] == 2
    assert agg["wolf_win_rate"] == 0.5
    assert agg["day1_hit"] == 0.5
    assert agg["witch_save_rate"] == 1.0 and agg["witch_poison_rate"] == 0.0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py -q`
Expected: FAIL (ImportError: live_rate_from_turns)

- [ ] **Step 3: 追加实现到 metrics.py**

```python
# 追加到 src/werewolf_eval/ablation/metrics.py

def live_rate_from_turns(turns_doc) -> float:
    turns = turns_doc.get("turns") if isinstance(turns_doc, dict) else turns_doc
    if not turns: return 0.0
    return sum(1 for t in turns if t.get("kind") == "live_success") / len(turns)


def live_rate(run_dir: Path) -> float:
    p = Path(run_dir) / "provider-turns.json"
    if not p.exists(): return 0.0
    return live_rate_from_turns(json.loads(p.read_text(encoding="utf-8")))


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def aggregate_games(games: list[dict]) -> dict:
    """games = analyze_game_dict outputs of VALID (live) games only."""
    n = len(games)
    if n == 0: return {"n_valid": 0}
    def rate(pred): return sum(1 for g in games if pred(g)) / n
    d1 = [g["d1_majority_is_wolf"] for g in games if g["d1_majority_is_wolf"] is not None]
    d2 = [g["d2_majority_is_wolf"] for g in games if g["d2_majority_is_wolf"] is not None]
    vwf = [g["verify_wolf_followed"] for g in games if g["verify_wolf_followed"] is not None]
    tot_sp = sum(g["n_speeches"] for g in games) or 1
    kill_dist = collections.Counter(g["night1_kill"] for g in games if g["night1_kill"])
    return {
        "n_valid": n,
        "wolf_win_rate": rate(lambda g: g["winner"] == "werewolf"),
        "villager_win_rate": rate(lambda g: g["winner"] == "villager"),
        "day1_hit": (sum(d1)/len(d1)) if d1 else None,
        "day2_hit": (sum(d2)/len(d2)) if d2 else None,
        "verify_wolf_followed": (sum(vwf)/len(vwf)) if vwf else None,
        "verify_wolf_followed_n": len(vwf),
        "witch_save_rate": rate(lambda g: g["witch_save"]),
        "witch_poison_rate": rate(lambda g: g["witch_poison"]),
        "herding": _mean([g["herd_share"] for g in games]),
        "halluc_visual_speech_rate": sum(g["n_visual_speeches"] for g in games) / tot_sp,
        "halluc_visual_game_rate": rate(lambda g: g["has_visual_halluc"]),
        "halluc_mechanic_game_rate": rate(lambda g: g["has_mechanic_halluc"]),
        "seer_survives_d1_rate": rate(lambda g: g["seer_survives_d1"]),
        "avg_rounds": _mean([g["end_round"] for g in games]),
        "night1_kill_dist": dict(sorted(kill_dist.items())),
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/ablation/metrics.py tests/test_ablation_metrics.py
git commit -m "feat(ablation): live-rate filter + aggregate metrics"
```

---

### Task 4: metrics — `aggregate(run_dirs)`(读盘 + 过滤 + 聚合)+ fixtures

**Files:**
- Modify: `src/werewolf_eval/ablation/metrics.py`
- Create: `tests/fixtures/ablation/` (2-3 个脱敏 run 目录)
- Test: `tests/test_ablation_metrics.py`

- [ ] **Step 1: 准备脱敏 fixtures**

从诊断期挑 3 局(1 村胜 + 1 狼胜 + 1 含视觉幻觉词),复制其 `game-log.json` + `provider-turns.json` 到 `tests/fixtures/ablation/<gid>/`。**脱敏复查**:逐文件确认无 key、无 `Authorization`、无 base_url 凭证串(provider-trace 不需要,**不要复制 provider-trace.json**,只要 game-log + provider-turns)。命令参考:

```bash
mkdir -p tests/fixtures/ablation
for g in diag_A_seer_p2_3 diag_A_seer_p3_1 diag_A_seer_p1_0; do
  mkdir -p tests/fixtures/ablation/$g
  cp .tmp/diag/$g/game-log.json .tmp/diag/$g/provider-turns.json tests/fixtures/ablation/$g/
done
NO_PROXY='*' python -c "import glob,re;[print('LEAK?',p) for p in glob.glob('tests/fixtures/ablation/**/*.json',recursive=True) if re.search(r'sk-|Authorization|api_key',open(p,encoding='utf-8').read())]"
# 期望:无 LEAK 输出
```

- [ ] **Step 2: 写失败测试**

```python
# 追加到 tests/test_ablation_metrics.py
from pathlib import Path
from werewolf_eval.ablation.metrics import aggregate

FIX = Path(__file__).parent / "fixtures" / "ablation"

def test_aggregate_reads_dirs_and_reports_invalid():
    run_dirs = sorted(p for p in FIX.iterdir() if p.is_dir())
    agg = aggregate(run_dirs)
    assert agg["n_total"] == len(run_dirs)
    assert agg["n_valid"] >= 1            # 这些 fixture 都是真 live
    assert 0.0 <= agg["wolf_win_rate"] <= 1.0
    assert "n_invalid_lowlive" in agg
```

- [ ] **Step 3: 追加实现**

```python
# 追加到 src/werewolf_eval/ablation/metrics.py

def aggregate(run_dirs) -> dict:
    """Read run dirs, drop low-live (RNG) games, aggregate the valid ones."""
    valid, invalid = [], 0
    for d in run_dirs:
        d = Path(d)
        gl_path = d / "game-log.json"
        if not gl_path.exists():
            invalid += 1; continue
        if live_rate(d) < LIVE_RATE_MIN:
            invalid += 1; continue
        gl = json.loads(gl_path.read_text(encoding="utf-8"))
        if not (gl.get("result") or {}).get("winner"):
            invalid += 1; continue
        valid.append(analyze_game_dict(gl))
    out = aggregate_games(valid)
    out["n_total"] = len(list(run_dirs)) if not isinstance(run_dirs, list) else len(run_dirs)
    out["n_invalid_lowlive"] = invalid
    return out
```

> 注意 `run_dirs` 可能是生成器;实现里先 `run_dirs = [Path(d) for d in run_dirs]` 固化一次,再用。修正:

```python
def aggregate(run_dirs) -> dict:
    run_dirs = [Path(d) for d in run_dirs]
    valid, invalid = [], 0
    for d in run_dirs:
        gl_path = d / "game-log.json"
        if not gl_path.exists() or live_rate(d) < LIVE_RATE_MIN:
            invalid += 1; continue
        gl = json.loads(gl_path.read_text(encoding="utf-8"))
        if not (gl.get("result") or {}).get("winner"):
            invalid += 1; continue
        valid.append(analyze_game_dict(gl))
    out = aggregate_games(valid)
    out["n_total"] = len(run_dirs)
    out["n_invalid_lowlive"] = invalid
    return out
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/ablation/metrics.py tests/test_ablation_metrics.py tests/fixtures/ablation/
git commit -m "feat(ablation): aggregate(run_dirs) with live-filter + scrubbed fixtures"
```

---

### Task 5: `compare(armA_agg, armB_agg)`(两臂对比表)

**Files:**
- Modify: `src/werewolf_eval/ablation/metrics.py`
- Test: `tests/test_ablation_metrics.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_ablation_metrics.py
from werewolf_eval.ablation.metrics import compare

def test_compare_emits_deltas():
    a = {"label":"baseline","wolf_win_rate":0.78,"day1_hit":0.51,"halluc_visual_speech_rate":0.20}
    b = {"label":"b1","wolf_win_rate":0.55,"day1_hit":0.66,"halluc_visual_speech_rate":0.04}
    rows = compare(a, b, keys=["wolf_win_rate","day1_hit","halluc_visual_speech_rate"])
    d = {r["metric"]: r for r in rows}
    assert abs(d["wolf_win_rate"]["delta"] - (-0.23)) < 1e-9
    assert d["day1_hit"]["a"] == 0.51 and d["day1_hit"]["b"] == 0.66
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py::test_compare_emits_deltas -q`
Expected: FAIL (ImportError: compare)

- [ ] **Step 3: 追加实现**

```python
# 追加到 src/werewolf_eval/ablation/metrics.py
DEFAULT_COMPARE_KEYS = (
    "n_valid","wolf_win_rate","villager_win_rate","day1_hit","day2_hit",
    "verify_wolf_followed","witch_save_rate","witch_poison_rate","herding",
    "halluc_visual_speech_rate","halluc_visual_game_rate","halluc_mechanic_game_rate",
    "seer_survives_d1_rate","avg_rounds",
)

def compare(a: dict, b: dict, keys=DEFAULT_COMPARE_KEYS) -> list[dict]:
    rows = []
    for k in keys:
        va, vb = a.get(k), b.get(k)
        delta = (vb - va) if isinstance(va, (int, float)) and isinstance(vb, (int, float)) else None
        rows.append({"metric": k, "a": va, "b": vb, "delta": delta})
    return rows
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_metrics.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/ablation/metrics.py tests/test_ablation_metrics.py
git commit -m "feat(ablation): compare(armA, armB) delta table"
```

---

### Task 6: `harness.run_arm`(编排:每局新建 provider + hard fail + 落盘)

**Files:**
- Create: `src/werewolf_eval/ablation/harness.py`
- Test: `tests/test_ablation_harness_fake.py`

> `run_emergent_deepseek_game(*, game_id, out_dir, provider_factory, model, seed, max_requests_per_game, max_day_rounds, seat_roles)` 已存在(`run_emergent_deepseek_game.py:128`);`_deepseek_factory(api_key, base_url, model, timeout_seconds, max_tokens, max_requests)` 同文件。harness 注入 `provider_factory` 抽象,便于 fake 测试。

- [ ] **Step 1: 写失败测试(fake 工厂,不碰网络/key)**

```python
# tests/test_ablation_harness_fake.py
from pathlib import Path
from werewolf_eval.ablation.arms import Arm
from werewolf_eval.ablation.harness import run_arm
from werewolf_eval.run_emergent_fake_runtime import build_fake_factory  # 见 Step 3 注

def test_run_arm_fake_smoke(tmp_path):
    arm = Arm(label="fake_smoke", prompt_version="prompt_v1", n_games=2, seed_base=7)
    result = run_arm(arm, out_root=tmp_path, factory_builder=build_fake_factory)
    assert result["arm"] == "fake_smoke"
    assert result["metrics"]["n_total"] == 2
    # fake 局 live_success_rate=0 -> 全被过滤,n_valid=0,但不崩
    assert "n_valid" in result["metrics"]
    assert (tmp_path / "fake_smoke" / "_metrics.json").exists()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_harness_fake.py -q`
Expected: FAIL（harness 未实现;若 `build_fake_factory` 不存在见 Step 3 注)

- [ ] **Step 3: 写实现**

> **注**:若 `werewolf_eval.run_emergent_fake_runtime` 没有 `build_fake_factory`,则在测试里就地构造一个返回 `ProviderAgent` 包裹现有 fake provider 的工厂(参照 `run_emergent_fake_runtime.py` 里 fake provider 的构造方式),并把 import 改成本地 helper。harness 本身只依赖"传入一个 `factory_builder()` 或 `provider_factory`"的抽象,不绑定具体 provider。

```python
# src/werewolf_eval/ablation/harness.py
"""Run one ablation arm: N games, fresh provider per game, hard-fail on budget,
live-rate filtering happens in metrics.aggregate."""
from __future__ import annotations
import json, time, traceback
from pathlib import Path

from werewolf_eval.run_emergent_deepseek_game import run_emergent_deepseek_game, _deepseek_factory
from werewolf_eval.ablation.arms import Arm, layout_for
from werewolf_eval.ablation.metrics import aggregate

MAX_REQUESTS_PER_GAME = 80   # 实测一局 ~19-23,留 ~3x 余量


def _deepseek_factory_builder(arm: Arm, api_key: str):
    # FRESH provider per call -> per-game 80-request budget, never shared across games.
    return _deepseek_factory(api_key=api_key, base_url=arm.base_url, model=arm.model,
                             timeout_seconds=40, max_tokens=256, max_requests=MAX_REQUESTS_PER_GAME)


def run_arm(arm: Arm, out_root: Path, api_key: str | None = None, factory_builder=None) -> dict:
    """factory_builder(arm, api_key) -> ProviderFactory (fresh per game). Defaults to DeepSeek."""
    out_root = Path(out_root)
    arm_dir = out_root / arm.label
    arm_dir.mkdir(parents=True, exist_ok=True)
    index_lines = []
    for i in range(arm.n_games):
        gid = f"{arm.label}_{i:03d}"
        out_dir = arm_dir / gid
        seat_roles = layout_for(arm, i)
        seed = arm.seed_for(i)
        rec = {"game_id": gid, "seed": seed, "seat_roles": seat_roles, "prompt_version": arm.prompt_version}
        t0 = time.time()
        for attempt in range(4):
            try:
                factory = (factory_builder or _deepseek_factory_builder)(arm, api_key)
                run_emergent_deepseek_game(
                    game_id=gid, out_dir=out_dir, provider_factory=factory,
                    model=arm.model, seed=seed,
                    max_requests_per_game=MAX_REQUESTS_PER_GAME, max_day_rounds=3,
                    seat_roles=seat_roles,
                )
                gl = out_dir / "game-log.json"
                rec["status"] = "completed" if gl.exists() else "failed"
                break
            except PermissionError:   # Windows Defender transient lock on atomic rename
                time.sleep(1.5); rec["status"] = "perm_retry"; continue
            except Exception as e:
                rec["status"] = "exception"; rec["error"] = f"{type(e).__name__}: {e}"
                traceback.print_exc(); break
        rec["secs"] = round(time.time() - t0, 1)
        index_lines.append(rec)
        (arm_dir / "_index.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in index_lines), encoding="utf-8")

    run_dirs = [arm_dir / f"{arm.label}_{i:03d}" for i in range(arm.n_games)]
    metrics = aggregate(run_dirs)
    result = {"arm": arm.label, "prompt_version": arm.prompt_version,
              "n_games": arm.n_games, "metrics": metrics}
    (arm_dir / "_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result
```

- [ ] **Step 4: 跑测试确认通过**

Run: `NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_ablation_harness_fake.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: 提交**

```bash
git add src/werewolf_eval/ablation/harness.py tests/test_ablation_harness_fake.py
git commit -m "feat(ablation): run_arm orchestration (fresh provider/game, hard-fail, fake-testable)"
```

---

### Task 7: CLI `run` / `compare`

**Files:**
- Create: `src/werewolf_eval/ablation/__main__.py`
- Test: 手动(live,opt-in,不进 CI)

- [ ] **Step 1: 写实现**

```python
# src/werewolf_eval/ablation/__main__.py
"""CLI: python -m werewolf_eval.ablation run <label> --prompt-version prompt_v1 [--n 45]
         python -m werewolf_eval.ablation compare <armA_dir> <armB_dir>"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from werewolf_eval.ablation.arms import Arm
from werewolf_eval.ablation.harness import run_arm
from werewolf_eval.ablation.metrics import compare


def _run(a):
    api_key = os.environ.get(a.api_key_env, "")
    if not api_key:
        print(f"missing {a.api_key_env}", file=sys.stderr); return 1
    arm = Arm(label=a.label, prompt_version=a.prompt_version, n_games=a.n,
              seed_base=a.seed_base, model=a.model)
    res = run_arm(arm, out_root=Path(a.out_root), api_key=api_key)
    print(json.dumps(res["metrics"], ensure_ascii=False, indent=1))
    return 0


def _compare(a):
    A = json.loads((Path(a.arm_a) / "_metrics.json").read_text(encoding="utf-8"))
    B = json.loads((Path(a.arm_b) / "_metrics.json").read_text(encoding="utf-8"))
    A["metrics"]["label"], B["metrics"]["label"] = A["arm"], B["arm"]
    print(f"{'metric':32} {A['arm']:>12} {B['arm']:>12} {'delta':>10}")
    for r in compare(A["metrics"], B["metrics"]):
        d = "" if r["delta"] is None else f"{r['delta']:+.3f}"
        print(f"{r['metric']:32} {str(r['a']):>12} {str(r['b']):>12} {d:>10}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="werewolf_eval.ablation")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.set_defaults(fn=_run)
    r.add_argument("label"); r.add_argument("--prompt-version", dest="prompt_version", default="prompt_v1")
    r.add_argument("--n", type=int, default=45); r.add_argument("--seed-base", dest="seed_base", type=int, default=1000)
    r.add_argument("--model", default="deepseek-v4-flash"); r.add_argument("--out-root", dest="out_root", default=".runs/ablation")
    r.add_argument("--api-key-env", dest="api_key_env", default="DEEPSEEK_API_KEY")
    c = sub.add_parser("compare"); c.set_defaults(fn=_compare)
    c.add_argument("arm_a"); c.add_argument("arm_b")
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 冒烟(fake 不可走此 CLI,因 CLI 绑 DeepSeek;此步仅验证 `--help` 不崩)**

Run: `NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.ablation run --help`
Expected: 打印 usage,exit 0

- [ ] **Step 3: 提交**

```bash
git add src/werewolf_eval/ablation/__main__.py
git commit -m "feat(ablation): CLI run/compare"
```

---

### Task 8: 打 baseline(live,opt-in,产出 prompt_v1 基线)

**Files:** 无代码改动;产物落 `.runs/ablation/baseline/`(gitignore)。

- [ ] **Step 1: 跑 baseline 臂(需 `.tmp/deepseek.key`)**

```bash
export DEEPSEEK_API_KEY=$(tr -d '\r\n' < .tmp/deepseek.key)
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.ablation run baseline --prompt-version prompt_v1 --n 45 --seed-base 1000
```

- [ ] **Step 2: 核对有效性**

检查输出 metrics:`n_valid` 应接近 45、`n_invalid_lowlive` 应很小;若 `n_valid` 远低于 45,**停下排查**(provider 预算/网络),不要把退化批当基线。

- [ ] **Step 3: 落基线快照(可选 commit 到 docs)**

```bash
cp .runs/ablation/baseline/_metrics.json docs/harness/reviews/2026-06-10-baseline-prompt-v1-metrics.json
git add docs/harness/reviews/2026-06-10-baseline-prompt-v1-metrics.json
git commit -m "chore(ablation): baseline prompt_v1 metrics snapshot (45 live games)"
```

---

## Self-Review

**1. Spec 覆盖**(对 spec §2 Part A):
- §2.1 模块结构 → Task 1/2/6/7 建齐 arms/metrics/harness/CLI;位置 `src/werewolf_eval/ablation/` ✓。
- §2.2 硬约束:每局新建 provider(Task 6 `_deepseek_factory_builder` 每次新建)✓;budget hard fail(`max_requests=80` + 退化局靠 live 率过滤剔除,Task 3/4)✓;live 率过滤(Task 3/4 `LIVE_RATE_MIN`)✓;配对 seed(Task 1 `seed_base` 全局 + `layout_for` 只依赖 seed)✓;预算/确定性边界(plan 设计要点已述)✓。
- §2.3 指标:胜率/d1·d2命中/验狼跟投/女巫救毒/羊群/视觉幻觉/机制幻觉/位置 kill_dist/有效性/avg_rounds → Task 2/3 全覆盖 ✓。关键词表可配置(常量)✓。v0 来源不在代码内(报告)✓。
- §2.4 测试:metrics 纯函数单测(Task 2/3/5)+ fixtures 脱敏(Task 4)+ fake 冒烟(Task 6)✓。
- baseline 重打(Task 8)✓。
- **未覆盖**:`prompt_version` 在 baseline 臂仅作记账(prompt_v2 渲染路径属 Part B plan),本 plan 的 Arm 已带该字段并穿进 runner 记录,但 **runner 真正消费 `prompt_version` 选择渲染路径 = Part B plan 的事**;本 plan baseline 只用 prompt_v1(现状),无缺口。

**2. 占位符扫描**:无 TBD/TODO;每个 code step 给了完整代码。Task 4 Step 3 给了两版(初版 + 生成器修正版),执行时用**修正版**。Task 6 Step 3 对 `build_fake_factory` 不存在给了明确 fallback(就地造工厂),非占位。

**3. 类型一致性**:`Arm`(label/prompt_version/n_games/seed_base/model/base_url + seed_for) Task 1 定义,Task 6/7 一致使用;`analyze_game_dict`/`aggregate_games`/`aggregate`/`compare`/`live_rate(_from_turns)` 命名跨 Task 2-5 一致;`run_arm(arm,out_root,api_key,factory_builder)` Task 6 定义、Task 7 调用一致。

---

## Execution Handoff
见对话:选 subagent-driven(推荐)或 inline。Part B(SYS-B1 上下文)将在本 plan 跑通 baseline 后单独成 plan。

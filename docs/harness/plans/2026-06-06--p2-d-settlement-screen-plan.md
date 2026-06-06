# P2-D Settlement / Battle-Report Screen (一镜到底 morph + 中轴脊椎联动) — Implementation Plan

> **For agentic workers:** implement task-by-task in order; each task is TDD (write failing test → run → implement → run → commit). Steps use checkbox (`- [ ]`) syntax. **Do NOT start until the spec is approved** — it is (2026-06-06 user review, 4 tightenings merged: failed-run boundary, scoring call-face, sanitized degraded reason, overlay-only).

**Goal:** When a game **completes** (status `completed` + `game-log.json` present), replace P2-C-1's silent "对局结束" pill with a **ceremonial settlement → deep battle report** that arrives via a **one-shot Z-axis morph** (freeze+spotlight → dock the theater ring → unfold the report), never a StackView page swap. The long right-side report and the docked left "live sandbox" sync through a **single source-of-truth `cursorIndex`**. The report data = a **server-computed, eval-ready `settlement-bundle.json`** (curtain layer always available from game-log; battle-report layer from `score_game`+`summarize_metrics`+`attribute_game`, degrading gracefully). The bundle contract is the P3 anti-rework asset: P3 adds fields, never rewrites.

**Architecture:** One new pure-Python module `settlement_bundle.py` (`build_settlement_bundle(game, decision_log) -> dict`) + one additive observer-server read route `GET /api/runs/{id}/settlement` (lazy compute-or-cache `settlement-bundle.json`; added to `ALLOWED_ARTIFACTS`). `ObserverApiClient` gains one read-only `settlementBundle` Q_PROPERTY + one `fetchSettlement(runId)` invokable (same latest-wins guard pattern as `refreshProjection`). Four new QML files (`SettlementView`, `WinnerBanner`, `SettlementSpine`, `SettlementReport`) + one **presentational** MODIFY to `SeatRing` (gains `layoutMode`/`morphProgress`/`boardState` — no bundle/cursor knowledge). `TheaterView` activates the `SettlementView` overlay on `completed`+game-log (never on `failed`). `HistoryView` adds a thin "查看战报" entry = `openRun()` + `navigateCockpit()` + entry mode `report`. Pure-Python bundle tests gate the backend (server routes are localhost-blocked here); the static contract gates the C++/QML surface; Qt build + 4-scenario `grabToImage` verify the UI.

**Tech Stack:** Python stdlib (extends P1-A `scoring`/`attribution`, P1-D `observer_server`), Qt 6.10 Quick/Quick Controls, C++17, QML, CMake. No new third-party deps, no engine changes, no scoring-formula changes, no client local file I/O, no provider secrets.

**Spec:** `docs/superpowers/specs/2026-06-06-p2-d-settlement-screen-design.md` (approved 2026-06-06).

**Branch:** `p2-d-settlement-screen` (base `main`, already created; spec commits `0fa9c0c`+`c4c8789`).

---

## Context Basis (verified — file:line)

- **Eval chain (pure functions, server can import — `src/werewolf_eval`):** `score_game(game: GameLog, decision_log: DecisionLog | None = None, semantic_label_log=None) -> ScoreLog` (`scoring.py:651`) → `summarize_metrics(game: GameLog, score_log: ScoreLog) -> MetricsSummary` (`scoring.py:850`, **explicit — `score_game` does NOT return metrics**) → `attribute_game(game: GameLog, score_log: ScoreLog, metrics: MetricsSummary) -> AttributionResult` (`attribution.py:266`). `ScoreRecord` fields incl. `outcome_score`/`rule_integrity_score`/`decision_quality_score`/`actor`/`scope`/`evidence_event_ids` (`scoring.py:50-58`). `MetricsSummary.result_metrics{winner,game_length,margin,*_survival_rate}` + `score_summary{player_outcome_scores,...}` (`scoring.py:91-102`). `AttributionResult.turn_points[]{turn_point_id,rule_id,round,subject,description_template,impact_score,impact_sign,evidence_event_ids}` + `top_attribution{turn_point_id,description_template}` (`attribution.py:19-78`).
- **GameLog shape (`game_log.py:22-70`):** `Player{player_id,role,team}` (**no `alive` field — derive from death/elim events**); `Event{event_id,sequence,round,phase,type,actor,target,visibility,data}`; `GameResult{winner,end_round,survivors,end_condition}`. Phases = `setup|night|day|game_end` (`:10`; **voting is a day sub-state, not a distinct phase**). Loader: `load_game_log(...)` / `load_decision_log(...)` (used by P2-C plan; verify exact names at impl, `game_log.py:~77`, `decision_log.py:~57`).
- **Failed-run boundary (BLOCK, verified):** `run_g1h_fake_runtime.py:130-148` — on `ProviderActionError` writes ONLY `provider-trace.json`+`failure-audit.json`, `return 2`, **no game-log/decision-log**; `run_deepseek_consensus_game.py:~114` same. `observer_server.py:454-462`: launcher raise → `provider_failure`; ret≠0 → `_map_launcher_exit_reason`; both `status="failed"`; **reason is always a canonical code, never raw exception** (`:448-450`). ⇒ settlement triggers ONLY on `completed`+game-log; `failed` keeps the failure HUD (spec §2.5).
- **Successful run writes both inputs:** `run_g1h_fake_runtime.py:150-151` writes `game-log.json` + `decision-log.json` together on success ⇒ a `completed` run reliably has both.
- **Observer server route pattern (`observer_server.py:391-417`):** under `/api/runs/{run_id}/...` the handler matches `sub_path` lists; `run_dir` is resolved; helpers `_run_detail_with_reason(run_id, run_dir)`, `build_artifact_registry(run_dir)`, `artifact_path(run_dir, name)`, `_send_json(code, obj)`, `_send_error_json(...)`. Run status obtained via run-detail/registry. `ALLOWED_ARTIFACTS` in `observer_protocol.py:31-40`. **Add `sub_path == ["settlement"]` branch + add `settlement-bundle.json` to `ALLOWED_ARTIFACTS`.**
- **C++ client (`ObserverApiClient.h/.cpp`):** `refreshProjection()` does `GET /api/runs/{id}/projection?perspective=` with a **latest-wins** guard (`++m_projectionRequestSerial`; callback bails if serial/runId changed). Mirror this for `fetchSettlement(runId)` → `GET /api/runs/{id}/settlement`. Q_PROPERTY + signal + member + accessor pattern as for `projectionProof`.
- **P2-C-1 theater surface (verified there):** `TheaterView.qml:30-35` `_runOver = currentStatus==="completed"||"failed"` + `eventQueue.atEnd`; **no settlement UI today** (hook point). `SeatRing.qml` = breathing ring, reads `playerItems` + `eventQueue.current` (theater mode — must stay zero-drift). `AppShell.qml` StackView `navigateCockpit()` → TheaterView. `HistoryView.qml:~223` history list (add "查看战报"). `EventPresentationQueue.atEnd`.
- **Design system (`Theme.qml`, P2-C plan §Context):** factions `roleAccent` (werewolf #EF4444 / seer #FBBF24 / witch #A855F7 / villager #60A5FA / hunter #34D399), `statusColor("completed") #60A5FA`, `space/radius/font/size/weight/motion{fast120,base180,slow260}/layout`. Reusable `AppCard/StatusBadge/AppButton/GlowDot/AppBackground/EmptyState/SectionHeader`. `I18n.t(zh,en)` — **English 2nd arg**, zh default.
- **Static contract (`tests/test_qt_observer_static_contract.py`):** `REQUIRED_QML_VIEWS`, `REQUIRED_OBJECT_NAMES`, CMake-registration test, forbidden scans (`events.jsonl`/`snapshots/`/`QFile`/`QDir`/`file://`/`werewolf_eval`/secret markers), `QtObserverProjectionClientTests` (client surface).

**Build/verify (Qt toolchain on F:, runnable here — memory `qt-observer-build-verify`):**
```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer   # exit 0 = QML AOT-valid
ctest --test-dir .tmp/qt-observer-build
```
Pure-Python bundle tests run here. **P2-D adds no server-route tests** (localhost HTTP env-blocked, memory `werewolf-env-network-test-limits`) — the route is a thin wrapper over `build_settlement_bundle`, fully covered by pure tests.

---

## Allowlist

```text
src/werewolf_eval/settlement_bundle.py
src/werewolf_eval/observer_server.py
src/werewolf_eval/observer_protocol.py
clients/qt_observer/src/ObserverApiClient.h
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/qml/SettlementView.qml
clients/qt_observer/qml/components/WinnerBanner.qml
clients/qt_observer/qml/components/SettlementSpine.qml
clients/qt_observer/qml/components/SettlementReport.qml
clients/qt_observer/qml/components/SeatRing.qml          (MODIFY: + layoutMode/morphProgress/boardState; presentational)
clients/qt_observer/qml/TheaterView.qml                  (MODIFY: completed+game-log activates overlay; failed → none)
clients/qt_observer/qml/HistoryView.qml                  (MODIFY: 查看战报 = openRun + navigateCockpit + entry mode)
clients/qt_observer/CMakeLists.txt
clients/qt_observer/README.md
tests/test_settlement_bundle.py
tests/test_qt_observer_static_contract.py
docs/superpowers/specs/2026-06-06-p2-d-settlement-screen-design.md
docs/harness/plans/2026-06-06--p2-d-settlement-screen-plan.md
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

## Forbidden Scope

No engine changes (`emergent_engine.py`/`game_engine.py`/runtime). No scoring-formula / validator / attribution-rule changes (consume them as-is). **No fixing the `witch_kill` vs `witch_poison` vocabulary mismatch** (P2-A; settlement degrades gracefully if it trips scoring). **No wiring emergent engine → observer** (pre-existing gap; consume whatever ran). No `failed`-run settlement / `failed_no_game_log` bundle. No new server **write** endpoint. No per-player full scorecards / process-metrics tables / decision_quality positive scoring UI (P3-A). No per-player behavior/reasoning long-form sections / win-rate curve / AI-review sidebar (P3-A). No history-list deepening / leaderboard (P3-B/C). No `SettlementView` in `AppShell` independent nav (overlay-only). No heavy morph polish (`MultiEffect` blur / spotlight shader / vote-line / poison micro-anim). No client local file I/O (`QFile`/`QDir`/`file://`). No provider secrets, no new deps, no Web/Electron. No route-product docs (root `README.md`, `ROADMAP.md`, `TASKS.md`, `PROJECT_MAP.md` — those are synced separately after merge).

---

## Task 1: Backend `build_settlement_bundle` (pure, the keystone — runs here)

**Files:** `src/werewolf_eval/settlement_bundle.py` (new), `tests/test_settlement_bundle.py` (new)
**Spec:** §5, §6.1, D2/D3. **The keystone gate — pure Python.**

- [ ] **Step 1: Write the failing bundle tests**

Build small synthetic `GameLog`/`DecisionLog` fixtures (reuse `game_log.load_game_log` on an inline dict, or construct dataclasses directly). Cover the contract + degrade + secret-free + determinism.

```python
class TestBuildSettlementBundle(unittest.TestCase):
    """P2-D §5/§6.1: curtain layer always from game-log; battle-report layer from
    score_game+summarize_metrics+attribute_game; degrade with reason CODE (no raw exc)."""

    def test_full_bundle_shape(self):
        bundle = build_settlement_bundle(self._game(), self._decision_log())
        self.assertEqual(bundle["bundle_version"], "p2d.settlement.v1")
        self.assertFalse(bundle["degraded"])
        # curtain layer
        self.assertEqual(bundle["result"]["winner"], "villager")
        self.assertEqual({p["player_id"] for p in bundle["players"]}, {"p1","p2","p3","p4","p5","p6"})
        self.assertTrue(all("role" in p and "alive" in p for p in bundle["players"]))   # reveal
        # board_timeline covers every (round,phase) group, monotonic cursor_index
        bt = bundle["board_timeline"]
        self.assertEqual([n["cursor_index"] for n in bt], list(range(len(bt))))
        self.assertTrue(all("alive_player_ids" in n for n in bt))
        # battle-report layer
        self.assertEqual(bundle["core_metrics"]["mvp_player_id"],
                         max(bundle["players"], key=lambda p: p["outcome_score"])["player_id"])
        self.assertIn("description", bundle["top_attribution"])
        for tp in bundle["turning_points"]:
            self.assertIn("cursor_index", tp)
            self.assertTrue(0 <= tp["cursor_index"] < len(bt))   # anchor resolves into board_timeline

    def test_board_timeline_only_needs_game_log(self):
        bundle = build_settlement_bundle(self._game(), decision_log=None)
        self.assertTrue(len(bundle["board_timeline"]) >= 1)
        self.assertEqual(bundle["board_timeline"][-1]["phase"], "game_end")
        self.assertEqual(set(bundle["board_timeline"][-1]["alive_player_ids"]),
                         set(self._game().result.survivors))   # final alive == survivors

    def test_degrade_on_scoring_error_keeps_curtain(self):
        # a game whose events trip the scorer (e.g. vocabulary mismatch) → degraded, curtain intact
        bundle = build_settlement_bundle(self._broken_for_scoring_game(), self._decision_log())
        self.assertTrue(bundle["degraded"])
        self.assertEqual(bundle["degraded_reason"], "scoring_failed")
        self.assertEqual(bundle["turning_points"], [])
        self.assertIsNone(bundle["top_attribution"])
        self.assertEqual(bundle["core_metrics"], {})
        self.assertEqual(bundle["result"]["winner"], "villager")        # curtain still there
        self.assertTrue(len(bundle["board_timeline"]) >= 1)             # board_timeline still there

    def test_degraded_reason_is_code_not_raw_exception(self):
        bundle = build_settlement_bundle(self._broken_for_scoring_game(), self._decision_log())
        self.assertIn(bundle["degraded_reason"],
                      {"missing_decision_log", "invalid_decision_log", "scoring_failed"})
        blob = json.dumps(bundle, ensure_ascii=False)
        for forbidden in ["Traceback", "File \"", ".py\", line", "/", "\\"]:   # no paths/stack
            self.assertNotIn(forbidden, str(bundle["degraded_reason"] or ""))

    def test_secret_free(self):
        blob = json.dumps(build_settlement_bundle(self._game(), self._decision_log()), ensure_ascii=False)
        for forbidden in ["reason_summary", "prompt", "api_key", "Bearer", "sk-", "C:\\", "/src/"]:
            self.assertNotIn(forbidden, blob)

    def test_deterministic(self):
        a = build_settlement_bundle(self._game(), self._decision_log())
        b = build_settlement_bundle(self._game(), self._decision_log())
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
```

> Fixture notes: `_game()` = a 6-player villager-win arc (night kill → day vote/elim across ≥2 rounds → game_end). `_broken_for_scoring_game()` = a game whose events raise inside `score_game`/`summarize_metrics`/`attribute_game` (e.g. an unmapped witch event type per spec §15) — assert the chain actually raises before relying on it (otherwise force via a monkeypatched scorer). `_decision_log()` = matching decision-log.

- [ ] **Step 2: Run → fail** — `PYTHONPATH=src python -m unittest tests.test_settlement_bundle -v`.

- [ ] **Step 3: Implement `settlement_bundle.py`**

```python
from __future__ import annotations
from werewolf_eval.game_log import GameLog
from werewolf_eval.decision_log import DecisionLog
from werewolf_eval.scoring import score_game, summarize_metrics
from werewolf_eval.attribution import attribute_game

BUNDLE_VERSION = "p2d.settlement.v1"
_DEATH_TYPES = {"player_died", "player_eliminated"}     # remove target/actor from alive set
_PHASE_LABEL = {"setup": "开局", "night": "夜晚", "day": "白天", "game_end": "终局"}

def _board_timeline(game: GameLog) -> list[dict]:
    """One node per (round, phase) group, in sequence order. Only needs game-log.
    alive_player_ids = state AFTER applying this group's deaths; never raises."""
    alive = {p.player_id for p in game.players}
    nodes, cur_key, cur = [], None, None
    for ev in sorted(game.events, key=lambda e: e.sequence):
        key = (ev.round, ev.phase)
        if key != cur_key:
            cur = {"cursor_index": len(nodes), "round": ev.round, "phase": ev.phase,
                   "label": f"第{ev.round}{_PHASE_LABEL.get(ev.phase, ev.phase)}",
                   "changed": [], "highlight": None, "alive_player_ids": None}
            nodes.append(cur); cur_key = key
        if ev.type in _DEATH_TYPES and ev.target in alive:
            alive.discard(ev.target)
            cur["changed"].append({"player_id": ev.target, "change": ev.type})
        if cur["highlight"] is None and ev.target and ev.target != "none":
            cur["highlight"] = {"actor": ev.actor, "target": ev.target, "kind": ev.type}
        cur["alive_player_ids"] = sorted(alive)
    return nodes

def _curtain(game: GameLog, board: list[dict]) -> dict:
    survivors = set(game.result.survivors)
    return {
        "bundle_version": BUNDLE_VERSION,
        "game_id": game.game_id,
        "degraded": False, "degraded_reason": None,
        "result": {"winner": game.result.winner, "end_round": game.result.end_round,
                   "end_condition": game.result.end_condition,
                   "survivors": sorted(survivors),
                   "margin": None, "source_label": game.source_label},
        "players": [{"player_id": p.player_id, "role": p.role, "team": p.team,
                     "alive": p.player_id in survivors,
                     "outcome_score": 0, "rule_integrity_score": 0, "decision_quality_score": 0}
                    for p in game.players],
        "core_metrics": {}, "top_attribution": None, "turning_points": [],
        "board_timeline": board,
    }

def _cursor_for(tp, game: GameLog, board: list[dict]) -> int:
    """Resolve a turn_point → board_timeline index via its evidence event's (round,phase)."""
    rp = None
    for eid in getattr(tp, "evidence_event_ids", []) or []:
        try:
            ev = game.event_by_id(eid); rp = (ev.round, ev.phase); break
        except Exception:
            continue
    if rp is None:
        rp = (getattr(tp, "round", board[-1]["round"]), "day")
    for n in board:
        if (n["round"], n["phase"]) == rp:
            return n["cursor_index"]
    # nearest preceding by round
    cand = [n for n in board if n["round"] <= rp[0]]
    return (cand[-1] if cand else board[-1])["cursor_index"]

def build_settlement_bundle(game: GameLog, decision_log: DecisionLog | None) -> dict:
    board = _board_timeline(game)
    bundle = _curtain(game, board)
    try:
        score_log = score_game(game, decision_log)
        metrics = summarize_metrics(game, score_log)
        attribution = attribute_game(game, score_log, metrics)
    except Exception:                       # reason CODE only — never raw text/path/stack
        bundle["degraded"] = True
        bundle["degraded_reason"] = "scoring_failed"
        return bundle
    # battle-report layer
    outcome = metrics.score_summary.get("player_outcome_scores", {}) if isinstance(metrics.score_summary, dict) else {}
    integ = metrics.score_summary.get("player_rule_integrity_scores", {})
    decq = metrics.score_summary.get("player_decision_quality_scores", {})
    for p in bundle["players"]:
        p["outcome_score"] = outcome.get(p["player_id"], 0)
        p["rule_integrity_score"] = integ.get(p["player_id"], 0)
        p["decision_quality_score"] = decq.get(p["player_id"], 0)
    rm = metrics.result_metrics
    bundle["result"]["margin"] = rm.get("margin")
    mvp = max(bundle["players"], key=lambda p: p["outcome_score"])["player_id"] if bundle["players"] else None
    bundle["core_metrics"] = {"game_length": rm.get("game_length"), "margin": rm.get("margin"),
        "mvp_player_id": mvp, "villager_survival_rate": rm.get("villager_survival_rate"),
        "werewolf_survival_rate": rm.get("werewolf_survival_rate")}
    bundle["top_attribution"] = {"turn_point_id": attribution.top_attribution.turn_point_id,
        "description": attribution.top_attribution.description_template} if attribution.top_attribution else None
    bundle["turning_points"] = [{"turn_point_id": tp.turn_point_id, "round": tp.round,
        "phase": next((n["phase"] for n in board if n["cursor_index"] == _cursor_for(tp, game, board)), "day"),
        "title": (tp.description_template or "")[:40], "description": tp.description_template,
        "impact_score": tp.impact_score, "impact_sign": tp.impact_sign,
        "evidence_event_ids": list(tp.evidence_event_ids or []),
        "cursor_index": _cursor_for(tp, game, board)} for tp in attribution.turn_points]
    return bundle
```

> Adjust attribute access to the real dataclass surfaces (`metrics.score_summary`/`result_metrics` dict vs attribute; `attribution.top_attribution`/`turn_points`) — verify against `scoring.py`/`attribution.py` while implementing; the test pins the output shape. **`degraded_reason` is always a code string; the `missing_decision_log`/`invalid_decision_log` codes are set by the server (Task 2) when it can't load decision-log before calling the builder.**

- [ ] **Step 4: Run → pass + full module + compileall**
```bash
PYTHONPATH=src python -m unittest tests.test_settlement_bundle -v
python -m compileall src/werewolf_eval/settlement_bundle.py
```

- [ ] **Step 5: Commit** — `git commit -m "feat(p2-d): build_settlement_bundle (eval-ready bundle, curtain always, graceful degrade)"`.

---

## Task 2: Observer-server `/settlement` route (lazy compute-or-cache) + ALLOWED_ARTIFACTS

**Files:** `src/werewolf_eval/observer_server.py`, `src/werewolf_eval/observer_protocol.py`
**Spec:** §6.2, D2/D3. No new server-route test (env-blocked); covered by Task 1 + manual `_build_or_load_settlement` helper kept pure.

- [ ] **Step 1: Add artifact name** — append `"settlement-bundle.json"` to `ALLOWED_ARTIFACTS` (`observer_protocol.py:31-40`) so the cache file is fetchable/auditable.

- [ ] **Step 2: Add the route branch** — in `observer_server.py` run-sub-path handler (next to `:404` artifacts branch), add:
```python
                # /api/runs/{run_id}/settlement  (P2-D §6.2)
                if sub_path == ["settlement"]:
                    self._send_json(200, self._settlement_payload(run_id, run_dir))
                    return
```
- [ ] **Step 3: Implement `_settlement_payload`** (thin; the heavy lift is the pure builder + loaders):
```python
    def _settlement_payload(self, run_id: str, run_dir: Path) -> dict:
        detail = self._run_detail_with_reason(run_id, run_dir)
        game_log_path = run_dir / "game-log.json"
        if detail.get("status") != "completed" or not game_log_path.exists():
            return {"available": False,
                    "reason": "no_game_log" if not game_log_path.exists() else "not_completed"}
        cache = run_dir / "settlement-bundle.json"
        if cache.exists():
            return {"available": True, "bundle": json.loads(cache.read_text(encoding="utf-8"))}
        game = load_game_log(game_log_path)
        decision_log = None
        dpath = run_dir / "decision-log.json"
        if dpath.exists():
            try:
                decision_log = load_decision_log(dpath, game)
            except Exception:
                decision_log = None     # invalid → builder proceeds; bundle may degrade
        bundle = build_settlement_bundle(game, decision_log)
        cache.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        return {"available": True, "bundle": bundle}
```
Import `build_settlement_bundle`, `load_game_log`, `load_decision_log` at top. **`failed` runs (no game-log) → `{available: false, reason}`, non-blocking (spec §2.5).** Lazy + cached → idempotent for just-finished and historical runs.

- [ ] **Step 4: Sanity + commit**
```bash
PYTHONPATH=src python -m unittest tests.test_settlement_bundle -v   # builder still green
python -m compileall src/werewolf_eval/observer_server.py src/werewolf_eval/observer_protocol.py
git commit -m "feat(p2-d): GET /api/runs/{id}/settlement (lazy compute-or-cache) + settlement-bundle artifact"
```

---

## Task 3: C++ `settlementBundle` property + `fetchSettlement`

**Files:** `clients/qt_observer/src/ObserverApiClient.h`, `.cpp`, `tests/test_qt_observer_static_contract.py`
**Spec:** §7.6. Mirrors `refreshProjection` (latest-wins guard); no other endpoint.

- [ ] **Step 1: Contract test (test-first)** — in `QtObserverProjectionClientTests`:
```python
    def test_client_exposes_settlement(self) -> None:
        h = (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")
        cpp = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("settlementBundle", h)
        self.assertIn("fetchSettlement", h)
        self.assertIn("/settlement", cpp)
        # stale guard: run change clears the bundle
        start = cpp.find("ObserverApiClient::setCurrentRunId")
        self.assertNotEqual(start, -1)
        self.assertIn("m_settlementBundle", cpp[start:start + 1200])
```
Run → fail.

- [ ] **Step 2: Declarations (`.h`)** — `Q_PROPERTY(QVariantMap settlementBundle READ settlementBundle NOTIFY settlementBundleChanged)`; `Q_INVOKABLE void fetchSettlement(const QString &runId);`; accessor `QVariantMap settlementBundle() const;`; signal `void settlementBundleChanged();`; members `QVariantMap m_settlementBundle; int m_settlementRequestSerial = 0;`.

- [ ] **Step 3: Implement (`.cpp`)** — `fetchSettlement` does `GET {base}/api/runs/{runId}/settlement` with a latest-wins guard (`int serial = ++m_settlementRequestSerial;` captured; on reply bail if `serial != m_settlementRequestSerial || runId != m_currentRunId`). On success parse `{"available":bool,"bundle":{...}}` → `m_settlementBundle = obj.value("available").toBool() ? obj.value("bundle").toObject().toVariantMap() : QVariantMap{}` → `emit settlementBundleChanged()`. In `setCurrentRunId(...)` clear `m_settlementBundle` + notify **before** issuing new requests (stale guard). No new include.

- [ ] **Step 4: Build + contract + commit**
```bash
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
python -m unittest tests.test_qt_observer_static_contract -v
git commit -m "feat(p2-d): expose settlementBundle + fetchSettlement (latest-wins, no new endpoint shape)"
```

---

## Task 4: `SeatRing` MODIFY — `layoutMode`/`morphProgress`/`boardState` (presentational, §14.2)

**Files:** `clients/qt_observer/qml/components/SeatRing.qml`, `tests/test_qt_observer_static_contract.py`
**Spec:** §7.3, §14.2. **Hard constraint: SeatRing stays presentational — no bundle fetch, no cursor ownership, no report knowledge; theater path zero drift.**

- [ ] **Step 1: Contract test (test-first)**
```python
    def test_seatring_layoutmode_presentational(self) -> None:
        c = (QT / "qml/components/SeatRing.qml").read_text(encoding="utf-8")
        self.assertIn("layoutMode", c)
        self.assertIn("morphProgress", c)
        self.assertIn("boardState", c)
        self.assertNotIn("settlementBundle", c)   # SeatRing must NOT read the bundle
        self.assertNotIn("fetchSettlement", c)
        self.assertNotIn("cursorIndex", c)        # does not own/read the cursor
```
Run → fail.

- [ ] **Step 2: Implement** — add `property string layoutMode: "theater"` (`theater`|`docked`), `property real morphProgress: 0` (0=ring,1=docked), `property var boardState: ({})` (docked-mode input from parent). Seat `Repeater` item `x/y` = lerp(ringPos(i), dockPos(i), morphProgress); root `scale`/spacing track `morphProgress`. **docked rendering:** alive/dead from `boardState.alive_player_ids` (a seat is dead if its id ∉ that list), cursor highlight from `boardState.highlight` (actor/target). **theater rendering unchanged** — still reads `current`/`playerItems` (P2-C-1 regression guard). Roles/colors via existing `Theme.roleAccent`.

- [ ] **Step 3: Build + contract + commit** — `git commit -m "feat(p2-d): SeatRing layoutMode (ring↔docked morph, presentational boardState input)"`.

---

## Task 5: `SettlementSpine.qml` (vertical spine scrubber)

**Files:** `clients/qt_observer/qml/components/SettlementSpine.qml` (new), `CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`
**Spec:** §7.4, D6/D9.

- [ ] **Step 1: Register + contract** — add to CMake `QML_FILES` + `REQUIRED_QML_VIEWS`; `"qml/components/SettlementSpine.qml": ["settlementSpine"]`. Assert the spine reads a cursor but does not own it:
```python
    def test_spine_reads_cursor_via_binding(self) -> None:
        c = (QT / "qml/components/SettlementSpine.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "settlementSpine"', c)
        self.assertNotIn("property int cursorIndex", c)   # owned by SettlementView, not here
```
Run → fail.

- [ ] **Step 2: Implement** — `Item { objectName:"settlementSpine"; property var nodes: []; property int activeIndex: 0; signal nodeClicked(int index) }`. Fixed full-height vertical axis; `Repeater` over `nodes` (= `board_timeline`) drawing round-phase dots + labels (`Theme`); a cursor indicator positioned by `activeIndex` (the binding, Observer) animating with `Theme.motion`. Node `TapHandler`/`MouseArea` → `nodeClicked(index)`. **Never writes the cursor itself** — emits an intent the parent handles.

- [ ] **Step 3: Build + contract + commit** — `git commit -m "feat(p2-d): SettlementSpine vertical timeline scrubber"`.

---

## Task 6: `SettlementReport.qml` (scrolling report + scroll-spy + anti-loop guard)

**Files:** `clients/qt_observer/qml/components/SettlementReport.qml` (new), `CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`
**Spec:** §7.5, D5/D6.

- [ ] **Step 1: Register + contract** — `"qml/components/SettlementReport.qml": ["settlementReport"]`. Assert scroll-spy + programmatic-scroll guard exist:
```python
    def test_report_has_scrollspy_and_guard(self) -> None:
        c = (QT / "qml/components/SettlementReport.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "settlementReport"', c)
        self.assertIn("_programmaticScroll", c)        # anti-feedback-loop flag (D6)
        self.assertIn("cursorRequested", c)            # writes cursor via signal to parent only
        self.assertNotIn("property int cursorIndex", c)  # does not own the cursor
```
Run → fail.

- [ ] **Step 2: Implement** — `Item { objectName:"settlementReport"; property var bundle: ({}); property int activeIndex: 0; property bool _programmaticScroll: false; signal cursorRequested(int index) }`. A `Flickable`/`ListView` of sections: winner header (or hosted `WinnerBanner` slot) → `bundle.turning_points` sections (each carrying its `cursor_index`) → `core_metrics` AppCard row → a P3 placeholder section (spec §5; visibly "P3 加挂位"). **scroll-spy:** on `contentY`/visible-index change, if `!_programmaticScroll`, find the top-most visible section and `cursorRequested(section.cursor_index)`. **scroll-to-anchor (driven by parent):** a `function scrollTo(index)` sets `_programmaticScroll=true`, `positionViewAtIndex(...)`, clears the flag on the scroll animation `onStopped`/a one-shot Timer. **degraded:** when `bundle.degraded`, render turning-point/metrics regions as `EmptyState`「战报数据不可用 · 仅显示对局结果」. Long text uses full width (no wrap squeeze).

- [ ] **Step 3: Build + contract + commit** — `git commit -m "feat(p2-d): SettlementReport scrolling battle report + scroll-spy (anti-loop guarded)"`.

---

## Task 7: `WinnerBanner.qml` (freeze-beat ceremony)

**Files:** `clients/qt_observer/qml/components/WinnerBanner.qml` (new), `CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`
**Spec:** §7.2.

- [ ] **Step 1: Register + contract** — `"qml/components/WinnerBanner.qml": ["winnerBanner"]`. Run → fail.
- [ ] **Step 2: Implement** — `Item { objectName:"winnerBanner"; property var result: ({}) }`: faction-colored headline (`result.winner` via `Theme.roleAccent`/`statusColor`), `end_round` + `margin` + `source_label` (honesty chain). Drop-in animation for the freeze beat; shrinkable to a report header in `report` state. `I18n.t(zh,en)`.
- [ ] **Step 3: Build + contract + commit** — `git commit -m "feat(p2-d): WinnerBanner freeze-beat ceremony"`.

---

## Task 8: `SettlementView.qml` (morph 3-beat + single cursor) + TheaterView activation + HistoryView entry

**Files:** `clients/qt_observer/qml/SettlementView.qml` (new), `TheaterView.qml`, `HistoryView.qml`, `CMakeLists.txt`, `README.md`, `tests/test_qt_observer_static_contract.py`
**Spec:** §3.3, §7.1, §7.7, D4/D6/D7. **The composition + morph state machine + single source-of-truth cursor.**

- [ ] **Step 1: Contract updates (test-first)**
  - `"qml/SettlementView.qml"` → `REQUIRED_QML_VIEWS`; `"qml/SettlementView.qml": ["settlementView"]`.
  - Single-cursor + overlay-only assertions:
```python
    def test_settlement_view_owns_cursor_and_is_overlay(self) -> None:
        s = (QT / "qml/SettlementView.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "settlementView"', s)
        self.assertIn("property int cursorIndex", s)     # the ONE writable source of truth
        self.assertIn("fetchSettlement", s)              # owns the fetch (SeatRing must not)
        self.assertIn("boardState", s)                   # resolves board_timeline[cursorIndex] → SeatRing
        # morph states present
        for st in ['"freeze"', '"docking"', '"report"']:
            self.assertIn(st, s)
        a = (QT / "qml/AppShell.qml").read_text(encoding="utf-8")
        self.assertNotIn("SettlementView", a)            # overlay-only: NOT an AppShell nav target (§14.1)
        t = (QT / "qml/TheaterView.qml").read_text(encoding="utf-8")
        self.assertIn("SettlementView", t)               # hosted inside TheaterView
        self.assertIn('currentStatus === "completed"', t)  # failed → not activated (§2.5)
```
  Run → fail.

  - [ ] **Step 2: Create `SettlementView.qml`** — overlay root hosting the morph + cursor:
    - `Item { id: settle; objectName:"settlementView"; property int entryMode: 0 /*0 live-freeze,1 history-report*/; property int cursorIndex: 0 }`. The **only** writable `cursorIndex`.
    - `Component.onCompleted` / on-activate: `ObserverClient.fetchSettlement(ObserverClient.currentRunId)`; bind `readonly property var bundle: ObserverClient.settlementBundle`.
    - **Resolve boardState for SeatRing:** `readonly property var boardState: (bundle.board_timeline && bundle.board_timeline[cursorIndex]) ? bundle.board_timeline[cursorIndex] : ({})` — passed as a prop to the docked `SeatRing` (SeatRing never touches the bundle/cursor, §14.2).
    - **Single-cursor wiring (D6):** `function setCursor(i) { cursorIndex = Math.max(0, Math.min(i, (bundle.board_timeline||[]).length - 1)); report.scrollTo(cursorIndex) }`. `SettlementReport.onCursorRequested: cursorIndex = index` (scroll-spy path — no scrollTo, avoids loop). `SettlementSpine.onNodeClicked: settle.setCursor(index)`. `SettlementSpine.activeIndex: settle.cursorIndex`; `SettlementReport.activeIndex: settle.cursorIndex`; `SeatRing.boardState: settle.boardState`.
    - **Morph state machine (D4/D7):** `state` ∈ `freeze|docking|report`. `entryMode==1` (history) → initial `state:"report"` (no freeze). `entryMode==0` (live) → start `freeze` (WinnerBanner drop + theater ring spotlight), a "查看深度战报" `AppButton` → `state="docking"` → (anim) → `state="report"`. Transitions animate `SeatRing.morphProgress` 0→1 + ring `scale`/dock + spine/report opacity/slide, `Theme.motion` budget. **Blur/glow polish deferred (§9 out-of-scope).**
    - **degraded:** `bundle.degraded` → WinnerBanner + docked sandbox + spine normal; report battle regions show EmptyState (handled in Task 6).
    - Layout: 28% sticky left (docked SeatRing + WinnerBanner-as-header) · center `SettlementSpine` · 72% `SettlementReport`.

- [ ] **Step 3: TheaterView activation (MODIFY)** — when `ObserverClient.currentStatus === "completed"` **and** game-log exists **and** `eventQueue.atEnd`, activate the `SettlementView` overlay (a `Loader`/visible overlay child — **not** `navigateXxx`). `failed` → leave the existing P2-C-1 failure pill/HUD untouched (no settlement). Pass `entryMode: 0`. The theater `SeatRing` is handed to `SettlementView` to drive `layoutMode/morphProgress/boardState` (or `SettlementView` owns its own SeatRing instance in docked mode — implementer's call; keep one ring visible during morph for the one-shot feel).

- [ ] **Step 4: HistoryView entry (MODIFY)** — on a finished run row add an "查看战报"/"View report" `AppButton`: `ObserverClient.openRun(runId); navigateCockpit();` and signal TheaterView to open `SettlementView` with `entryMode: 1` (direct `report`). Thin — reuses `fetchSettlement`; no history-list deepening (P3-B).

- [ ] **Step 5: README non-goal note** — settlement = in-theater overlay battle report; still no Web client / no Python binding / no local artifact reads / no provider secrets. Keep README-contract substrings.

- [ ] **Step 6: Build + contract + commit**
```bash
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
python -m unittest tests.test_qt_observer_static_contract -v
git commit -m "feat(p2-d): SettlementView morph (freeze→dock→report) + single cursor; theater/history entries"
```

---

## Task 9: Build, lint, 4-scenario visual verification

**Files:** none (verification) — fixes land in the relevant task's files.

- [ ] **Step 1: Clean build + ctest + qmllint**
```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
ctest --test-dir .tmp/qt-observer-build --output-on-failure
qmllint -I .tmp/qt-observer-build clients/qt_observer/qml/SettlementView.qml clients/qt_observer/qml/components/SettlementSpine.qml clients/qt_observer/qml/components/SettlementReport.qml clients/qt_observer/qml/components/WinnerBanner.qml clients/qt_observer/qml/components/SeatRing.qml
```
Expected: build exit 0; ctest 100%; qmllint no `Error:` lines (ignore `[unqualified]`/`[missing-property]`).

- [ ] **Step 2: 4-scenario visual capture (grabToImage → PNG → Read) — TEMPORARY, NEVER committed**

Harness seeds a mock `settlementBundle` (real contract shape: ≥3 `board_timeline` nodes across rounds + ≥2 `turning_points` with valid `cursor_index`) on a mock `ObserverClient`; localhost blocked → no real fetch. Behind a `// TEMP VISUAL ONLY` marker; revert before any commit.
1. **morph** — drive `freeze` → `docking` → `report`; capture `p2d_freeze.png` (WinnerBanner + ring spotlight), `p2d_dock.png` (ring scaled/flown into 28% column), `p2d_report.png` (spine + report unfolded).
2. **scroll-sync** — programmatically scroll `SettlementReport` to a turning-point section → capture `p2d_sync.png` showing docked SeatRing alive/dead at that `cursor_index` + spine cursor on that node (and assert no double-jump: setting cursor via spine click does not re-trigger scroll-spy back-write).
3. **history-direct** — `entryMode:1` → capture `p2d_history.png`: initial `report` state, docked sandbox, **no freeze beat**.
4. **degraded** — bundle `degraded:true` → capture `p2d_degraded.png`: WinnerBanner + sandbox normal, battle regions EmptyState.
Save under `G:/Werewolf-agent/.tmp/`. **Read** each PNG; confirm charcoal palette, faction accents, 28/72 + center spine, sticky left full-height (no collapse).

- [ ] **Step 3: Revert harness + prove clean**
```bash
git checkout -- clients/qt_observer/qml/   # revert any TEMP VISUAL edits
git diff --quiet -- clients/qt_observer/qml || { echo "harness edits remain"; exit 1; }
```

- [ ] **Step 4: Full Python suite + compileall**
```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests
```
Expected: `test_settlement_bundle` green; `compileall` 0 failures. Only acceptable failures = documented pre-existing env-blocked server-route tests (`RemoteDisconnected`). **Any new failure = a P2-D regression to fix.**

---

## Task 10: Validation + review packet

**Files:** `.logs/review/latest/review-packet.md`, `.oh-my-harness/tree.md`

- [ ] **Step 1: Hygiene**
```bash
git diff --check main...HEAD
git diff --name-only main...HEAD          # must be within allowlist
git diff main...HEAD -- clients | python -c "import sys,re; d=sys.stdin.read(); add=[l for l in d.splitlines() if l.startswith('+') and not l.startswith('+++')]; bad=[l for l in add if re.search(r'(QFile|QDir|file://|events\.jsonl|snapshots/|sk-[A-Za-z0-9]{16}|Authorization:|Bearer )', l) and all(k not in l.lower() for k in ('forbidden','assertnotin','marker'))]; print('\n'.join(bad)); assert not bad, bad"
```
- [ ] **Step 2: Refresh tree** — `node .codex/hooks/tree.mjs --force` (4 new QML + new py module).
- [ ] **Step 3: Write review packet** (≤300 lines): Metadata (branch `p2-d-settlement-screen`, base `main`), Changed Files, Diff Stat/Check, Allowlist, Forbidden/secret scan, Test Summary (bundle pure tests incl. degrade + secret-free + determinism; static contract OK; Qt build exit 0; ctest; qmllint; 5 visual PNGs; **no new server-route tests**), Key Hunks (board_timeline + cursor resolution + degrade-to-code; settlement route lazy cache; settlementBundle parse + stale clear; SeatRing presentational boardState; single-cursor wiring + anti-loop guard; morph state machine; overlay-only/failed-not-activated), Evidence Map (A1–A12), Acceptance Checklist, Review Trigger Result.
- [ ] **Step 4: Commit** — `git add .logs/review/latest/review-packet.md .oh-my-harness/tree.md && git commit -m "docs(p2-d): review packet + tree refresh"`.

---

## Acceptance Criteria (mirror spec §12)

- **A1.** `completed`+game-log + `eventQueue.atEnd` → auto `freeze` (WinnerBanner + spotlight); **`failed` does NOT activate settlement** (failure HUD stays); "查看深度战报" → `docking`→`report`, **same-view state machine overlay, no StackView swap / no AppShell settlement nav**. *(test_settlement_view_owns_cursor_and_is_overlay; visual)*
- **A2.** `SeatRing.layoutMode` ring↔docked seat-position interpolation; `theater` mode unchanged (P2-C-1 regression); `docked` renders parent-passed `boardState` (SeatRing touches no bundle/cursor). *(test_seatring_layoutmode_presentational; visual morph)*
- **A3.** Single `cursorIndex` source of truth in `SettlementView`; report scroll-spy + spine click both write via signals; sandbox/spine/highlight read by binding; programmatic scroll guarded (no feedback loop / double-jump). *(test_report_has_scrollspy_and_guard; test_spine_reads_cursor_via_binding; visual sync)*
- **A4.** Bundle contract v1 complete (`result/players/core_metrics/top_attribution/turning_points/board_timeline`); `turning_points[*].cursor_index` resolves into `board_timeline`; `mvp_player_id` = max `outcome_score`. *(test_full_bundle_shape)*
- **A5.** Graceful degrade (completed+game-log, scoring chain raises): `degraded=true` + `degraded_reason` ∈ {`missing_decision_log`,`invalid_decision_log`,`scoring_failed`} (**no raw exception/path/stack**); curtain (winner/reveal/survivors/board_timeline) intact, battle regions EmptyState. *(test_degrade_on_scoring_error_keeps_curtain; test_degraded_reason_is_code_not_raw_exception; visual degraded)*
- **A6.** Lazy compute-or-cache: first GET builds + writes `settlement-bundle.json`, second reads cache; deterministic; non-`completed`/no-game-log (incl. `failed`) → `{available:false, reason}`, non-blocking. *(builder determinism test; route audited by code)*
- **A7.** History entry: finished-run "查看战报" → `openRun`+`navigateCockpit` + `entryMode:1` → initial `report`, docked sandbox, no freeze. *(visual history-direct)*
- **A8.** Settlement = god full reveal, no per-seat fog; bundle secret-free (no prompt/provider/path/`reason_summary`). *(test_secret_free)*
- **A9.** C++ `settlementBundle` + `fetchSettlement` exposed (latest-wins); `setCurrentRunId` clears bundle + notifies. *(test_client_exposes_settlement; build)*
- **A10.** Static contract updated + green (4 new files/objectNames + SeatRing mode); build exit 0; ctest green; qmllint clean; 4-scenario visual confirmed.
- **A11.** No engine change; no scoring/validator/attribution change; no new deps; no client file I/O; SSE/`/events`/`/projection` semantics unchanged; only backend additions = 1 builder + 1 route + 1 artifact name. *(hygiene; diff scan)*
- **A12.** P3-deepen contract: bundle existing keys frozen, P3 adds keys only (spec §5 recorded as P3 entry basis). *(spec cross-ref)*

---

## Review Packet Requirements

`.logs/review/latest/review-packet.md` ≤300 lines: Metadata, Changed Files, Diff Stat, Diff Check, Allowlist, Forbidden/secret scan (note safe test markers), Test Summary (bundle pure-test results incl. degrade/secret-free/determinism + Qt build exit code + visual PNG refs + no-new-server-route note), Key Hunks, Evidence Map (A1–A12), Acceptance Checklist, Review Trigger Result.

---

## PR Description Draft

Title: `feat: P2-D settlement / battle-report screen (一镜到底 morph + spine sync)`

```markdown
## Summary
- Game completion now opens a ceremonial settlement → deep battle report via a one-shot Z-axis morph (freeze+spotlight → dock the theater ring → unfold the report) — same-view state machine, never a page swap.
- Server computes an eval-ready settlement-bundle.json on first request (lazy/cached) from game-log + decision-log via score_game+summarize_metrics+attribute_game; curtain layer (winner/reveal/board_timeline) always available, battle-report layer degrades gracefully with a sanitized reason code.
- 28% sticky docked sandbox + center vertical spine + 72% scrolling report, all synced through a single source-of-truth cursorIndex (scroll-spy + spine click write it; sandbox/spine read by binding). SeatRing gains a presentational layoutMode/boardState (no bundle/cursor knowledge).

## Scope / boundaries
- completed-run only; failed runs keep the failure HUD (no game-log → no settlement). Settlement is an in-theater overlay (no AppShell nav). Bundle contract v1 is the P3 anti-rework asset: P3 adds per-player analysis / full metrics / win-rate curve as new fields + new scroll-synced sections.
- No engine change; no scoring-formula change; no emergent→observer wiring; no witch vocabulary fix (degrades gracefully). No heavy morph polish (blur/glow/vote-line) — structural morph only.

## Validation
- PYTHONPATH=src python -m unittest tests.test_settlement_bundle -v   # shape + degrade + secret-free + determinism
- Qt build (F: toolchain) exit 0; tests.test_qt_observer_static_contract OK; ctest; qmllint
- Visual: .tmp/p2d_{freeze,dock,report,sync,history,degraded}.png
- No new server-route tests; route is a thin wrapper over the pure builder.
```

---

## Execution Handoff

Order: (1) backend `build_settlement_bundle` + pure tests [keystone, runs here], (2) observer-server `/settlement` route + artifact name, (3) C++ `settlementBundle`/`fetchSettlement` + stale clear, (4) SeatRing `layoutMode`/`boardState` [presentational], (5) SettlementSpine, (6) SettlementReport [scroll-spy + anti-loop guard], (7) WinnerBanner, (8) SettlementView morph + single cursor + theater/history entries, (9) build/lint/4-scenario visual, (10) packet. Each task commits. **Hard rules:** curtain layer never depends on scoring (board_timeline/result/reveal from game-log only); `degraded_reason` is always a CODE (never raw exception/path/stack); settlement triggers ONLY on `completed`+game-log (never `failed`); `SettlementView` owns the one writable `cursorIndex` and is overlay-only (never AppShell nav); `SeatRing` stays presentational (no bundle/cursor/report knowledge, theater path zero drift); single-cursor anti-loop guard (`_programmaticScroll`) on report scroll-to-anchor; never touch the engine / scoring formula / shared `Theme` tokens; **P2-D adds no server-route tests**; bundle existing keys are frozen for P3.
```

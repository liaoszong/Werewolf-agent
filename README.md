# Werewolf-agent

**A playable, watchable, auditable Werewolf Agent Theater.**

Configure AI agent seats, watch the match unfold live from a god's-eye theater view, then dive into the settlement battle report — every decision, speech, and vote backed by a fully auditable event log. AI-vs-AI is the default experiment mode; human-controlled seats are part of the current P3 direction.

[简体中文](README.zh-CN.md) | English

---

## What is this?

Werewolf-agent is a **client-agnostic live Werewolf Agent Theater**. A Python game engine drives a 6-player social-deduction match under strict information isolation — werewolves don't know the seer, the seer's checks stay private, and each seat's context is provably built only from events that seat is allowed to see.

Matches can run fully offline (deterministic fake provider, the default) or live against real LLM APIs. Today the default product path is AI-vs-AI; the roadmap now promotes richer role-playing agents, human-controlled seats in P3, and a Flutter-first mobile/desktop client. Every run produces a structured, replayable event stream that powers spectating, settlement reports, history replay, and downstream evaluation.

## Highlights

- **Emergent game engine** — 6 players (2 werewolves, 1 seer, 1 witch, 2 villagers): night kills with wolf consensus, seer checks, witch save/poison, day speeches, votes, executions, win adjudication. Dynamic rounds, no scripts. A hunter role variant ships in the action runtime (`rules_v1_1`).
- **Bring your own AI** — per-seat provider/model/prompt/temperature configuration. Built-in presets: DeepSeek, OpenAI, Anthropic, plus 9 OpenAI-compatible vendors (Zhipu GLM, Moonshot, Qwen, MiniMax, SiliconFlow, xAI, Gemini, ModelScope, OpenRouter) and fully custom endpoints. API keys stay on your machine; only the local Python server ever calls a provider.
- **Current Qt theater client** — live god-view spectating (seat ring, speech theater, evidence console, playback controls), match setup sandbox, in-theater settlement overlay with a scrolling battle report, and a history view for replaying or managing past runs. It remains the legacy desktop client until the Flutter-first cross-platform client reaches parity.
- **Mobile-first player client in design** — P3-E defines a Flutter-first cross-platform client for phone-first human participation and desktop expansion, while preserving the existing backend protocol.
- **Honest by construction** — event-sourced logs (`events.jsonl`, snapshots, prompt manifest, provider traces, failure audits), executed-truth HUD (`LIVE_API` vs `SIMULATION`), visibility projections (God / Public / per-Role), and runtime invariants that fail loudly on information leaks or rule violations.
- **Agent-first, player-first roadmap** — P3 now focuses on role cards, game-scoped memory, agent harnesses, table-talk, human seats, and a Flutter-first mobile/desktop client. Evaluation, replay analysis, and leaderboards move downstream to P4.
- **Evaluation-ready foundation** — deterministic scoring, rule attribution, an ablation harness with per-arm metrics, byte-locked prompt versioning with a revision ledger, differential testing, and seeded deterministic simulation.
- **Zero-dependency backend** — the entire Python backend uses only the standard library. No `pip install` required to run an offline match.

## Architecture

```text
YAML run profile (seat controllers / AI profiles / prompts / role shuffle)
        │
        ▼
Python game engine + agent/provider loop          src/werewolf_eval/
  · emergent engine, action runtime (ability system)
  · provider registry (DeepSeek / OpenAI / Anthropic / 9 presets / custom)
  · invariant safety net, deterministic fake mode
        │  event sourcing: events.jsonl · snapshots · prompt manifest · provider trace
        ▼
Local observer server (REST + SSE, client-agnostic protocol)
        │
        ▼
Qt 6 / QML theater client                         clients/qt_observer/
  · live spectating · match setup · settlement report · history replay
  · legacy desktop client until Flutter parity
        │
        ▼
Flutter-first cross-platform client               planned
  · mobile-first human seats · live room · desktop expansion
  · same observer protocol, no direct provider calls
```

The observer protocol is the hard boundary: any client (Qt today, Flutter next) consumes the same REST/SSE surface and never touches engine internals or provider secrets.

## Getting started

### Windows desktop install

For normal desktop use, download `Werewolf-agent-0.2.0-Setup.exe` from the main repository's GitHub Releases and run it once. Other release assets are updater packages and indexes; testers should not choose them manually. The app installs to `%LOCALAPPDATA%\WerewolfAgent\current\`, while runs, profiles, configs, logs, credentials, and settings stay under `%LOCALAPPDATA%\Werewolf-agent\` or the Windows user stores.

The first public Windows installer is not code-signed yet. Windows may show an "Unknown publisher" or SmartScreen warning before installation; this is a known limitation of the 0.2.0 release.

After installation, launch Werewolf-agent from the desktop or Start menu. Future stable updates are handled in the client under Settings -> About & Updates: check for updates, review the target version and release notes, then choose Download and Restart when no match is queued or running.

### Prerequisites

- **Python 3.12+** — no third-party packages needed.
- **Qt 6.8+ and CMake 3.16+** — only for building the desktop client.

### One-click launch (Windows)

```bat
python launch-theater.py
```

Starts the local observer server (if needed), builds/launches the Qt client, and lands on the home view — start a match from there. When this launcher owns the local server process, closing the launcher/client first marks still `queued` or `running` local runs as `interrupted` before shutdown so History can archive and delete them without fabricating a settlement report. If the launcher reuses an already-running external observer server, it leaves that server and its active runs alone. Edit the `QT_BIN` / `MINGW_BIN` / `CMAKE` constants at the top of `launch-theater.py` to match your Qt installation.

### Manual launch

```powershell
# 1. Observer server
$env:PYTHONPATH='src'
python -m werewolf_eval.run_observer_server --host 127.0.0.1 --port 8765 --runs-dir .runs --allow-live-api

# 2. Build the Qt client
cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
cmake --build .tmp/qt-observer-build --config Debug

# 3. Run it
.\.tmp\qt-observer-build\appqt_observer.exe --observer-base-url http://127.0.0.1:8765
```

### Playing with real AI

Offline deterministic mode is the unconditional default and needs no keys. For a live match:

1. Launch the server with `--allow-live-api` (the one-click launcher does this).
2. In the Qt client, add your provider API key in the settings page (stored locally, masked in UI, never logged or exported).
3. Arm LIVE mode in match setup and launch. The `SYS: LIVE_API / SIMULATION` HUD chip always shows the executed truth.

`live-check.bat` runs a one-shot real DeepSeek match end-to-end (needs `DEEPSEEK_API_KEY`; incurs real API cost).

### Running tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

~1,000 tests cover the engine, action runtime, observer protocol, providers, scoring, invariants, and the Qt↔Python static contract. Qt-side tests: `ctest --test-dir .tmp/qt-observer-build`.

## Repository layout

| Path | What lives there |
|------|------------------|
| `src/werewolf_eval/` | Python backend: emergent engine, `action_runtime/` (ability system), providers & registry, observer server, event/log schemas + validators, scoring & attribution, `invariants/` safety net, `ablation/` harness |
| `clients/qt_observer/` | Current Qt 6 / QML theater client; legacy desktop surface until cross-platform parity ([client README](clients/qt_observer/README.md)) |
| `tests/` | Python test suite (80 files) |
| `tools/`, `scripts/` | Live-check and dev/smoke utilities |
| `docs/` | Project docs — start at [`PROJECT_MAP.md`](docs/PROJECT_MAP.md) |
| `launch-theater.py` / `.bat` | One-click server + client launcher |

## Project status & roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| **P1 — Data & event foundation** | Log schemas/validation/scoring/attribution, engine & provider contracts, runtime event spine, observer protocol + server | ✅ Done |
| **P2 — Watchable AI-vs-AI client** | Emergent engine, BYO-key multi-provider setup, live theater UI, settlement report | ✅ Done |
| **P3 — Agent roleplay · Human participation · Cross-platform client** | Agent cards, game-scoped memory, roleplay harness, table-talk, first-class human seats, Flutter-first mobile/desktop client | 🚧 Current direction |
| **P4 — Evaluation · Replay analysis · Leaderboard** | Settlement deepened into replay analysis; rankings by model, role, Agent Card, memory strategy | ⏳ Downstream |

[`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md) is the authoritative product map (phases + system view).

## Documentation

| Doc | Role |
|-----|------|
| [PROJECT_MAP](docs/PROJECT_MAP.md) | **Authority** — product phases, module status, system view (SYS-xx) |
| [PRODUCT_ONE_PAGER](docs/PRODUCT_ONE_PAGER.md) | Product definition: users, inputs, outputs, value |
| [TASKS](docs/TASKS.md) | Compressed task index |
| [DESIGN](DESIGN.md) | UI direction: new cross-platform surfaces + legacy Qt maintenance boundary |
| [Specs](docs/superpowers/specs/) | Design specs for substantial slices |
| [Plans](docs/superpowers/plans/) | Current implementation plans |
| [ADRs](docs/adr/) | Architecture decisions (observer protocol, action runtime orchestrator) |
| [Qt client README](clients/qt_observer/README.md) | Building, running, and testing the theater client |
| [EVALUATION_RUBRIC](docs/EVALUATION_RUBRIC.md) | Scoring system reference (P4) |

## Background

The project originates from a multi-agent systems exercise: build an AI Werewolf agent team that plays a hidden-information game under strict information isolation, with a complete match engine, structured observability, and a spectator UI. It first grew through the *evaluation & replay* direction — deterministic scoring over structured logs — and now pivots toward richer agents: role cards, game-scoped memory, table-talk, team plans, and human-controlled seats in P3 sharing the same auditable game loop.

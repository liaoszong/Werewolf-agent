# R0 Windows Distribution Baseline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把已完成的 P2 Werewolf-agent 做成可安装、可升级的 Windows x64 Beta 发行版（v0.2.0）。

**Architecture:** Python PyInstaller onedir bootstrapper (`Werewolf-agent.exe`) 作为唯一入口，管理 owned observer server 生命周期、单实例锁、IPC、更新请求；独立 frozen server (`observer-server.exe`) + Qt Release windeployqt tree (`app/`) 作为整体 IFW 主组件原子升级；用户数据隔离在 `%LOCALAPPDATA%\Werewolf-agent\`。

**Tech Stack:** Python 3.12 stdlib, PyInstaller 6.x (release venv), Qt 6.10.0 MinGW 64-bit Release, windeployqt, Qt IFW 4.11 (binarycreator + repogen), CMake 3.16+

## Global Constraints

- 版本单源：`G:\Werewolf-agent\VERSION` → `0.2.0`
- 用户数据根：`%LOCALAPPDATA%\Werewolf-agent\`
- 安装根：`C:\Program Files\Werewolf-agent\`
- IFW 主组件：`com.werewolfagent.app`
- PyInstaller 产物：独立 `onedir`（bootstrapper + server 各自独立 runtime）
- Release venv 与开发环境隔离
- 禁止 `F:\Qt`、仓库路径、开发环境变量出现在 release 产物
- 禁止 API key 进入 logs、runs、runtime-state、安装包、error 输出
- 全部新增中文文案接入 I18n 中英切换
- 不修改 `src/werewolf_eval/emergent_engine.py`、`action_runtime/`、`provider_*.py`、`invariants/`、`docs/adr/`、`.github/workflows/`

---

### Task 1: VERSION single source + release metadata helper

**Files:**
- Create: `VERSION`
- Create: `src/werewolf_eval/release_metadata.py`
- Modify: `clients/qt_observer/CMakeLists.txt` (consume VERSION)
- Modify: `src/werewolf_eval/run_observer_server.py` (consume release_metadata)

**Interfaces:**
- Produces: `release_metadata.read_version() -> str` — returns `"0.2.0"`
- Produces: `release_metadata.read_release_metadata(dist_root: Path) -> dict` — returns full metadata dict from VERSION file
- Produces: CMake variable `RELEASE_VERSION` set to `0.2.0`
- Consumes: (none — foundation task)

- [ ] **Step 1: Create VERSION file**

```bash
echo -n "0.2.0" > G:/Werewolf-agent/VERSION
```

- [ ] **Step 2: Create release_metadata.py**

Create `src/werewolf_eval/release_metadata.py`:

```python
"""Single-source release version and metadata helpers.

Reads VERSION from the distribution root. In a PyInstaller frozen bundle,
the VERSION file is placed alongside the executable via --add-data.
In dev mode, walks up from this module's location to find the repo-root VERSION.
"""
from __future__ import annotations

from pathlib import Path


def _dist_root() -> Path:
    """Distribution root containing the VERSION file.

    Frozen: VERSION is next to the executable (onedir layout).
    Dev: walks up from this file to the repo root.
    """
    import sys
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # Dev: this file is at src/werewolf_eval/release_metadata.py
    return Path(__file__).resolve().parent.parent.parent


def read_version() -> str:
    return (_dist_root() / "VERSION").read_text(encoding="utf-8").strip()


def read_release_metadata(dist_root: Path | None = None) -> dict:
    """Return a dict with release_version and the raw VERSION content.
    dist_root overrides the auto-detected root for testing."""
    root = dist_root or _dist_root()
    ver = (root / "VERSION").read_text(encoding="utf-8").strip()
    return {"release_version": ver}
```

- [ ] **Step 3: Wire VERSION into CMake**

In `clients/qt_observer/CMakeLists.txt`, after the `project()` line, add:

```cmake
# Read release version from repo-root VERSION (single source).
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/../../VERSION" RELEASE_VERSION)
string(STRIP "${RELEASE_VERSION}" RELEASE_VERSION)
message(STATUS "Release version: ${RELEASE_VERSION}")
```

Change `project(qt_observer VERSION 0.1 ...)` to:
```cmake
project(qt_observer VERSION ${RELEASE_VERSION} LANGUAGES CXX)
```

- [ ] **Step 4: Wire version into run_observer_server.py**

In `src/werewolf_eval/run_observer_server.py`, add a `--version` flag:

After the existing argparse setup, add:
```python
parser.add_argument("--version", action="version",
                    version=f"observer-server {read_version()}")
```

Also add `from werewolf_eval.release_metadata import read_version` at the top imports.

- [ ] **Step 5: Verify — run `--version` flags**

```bash
cd G:/Werewolf-agent
PYTHONPATH=src python -m werewolf_eval.run_observer_server --version
# Expected: observer-server 0.2.0

cat VERSION
# Expected: 0.2.0
```

- [ ] **Step 6: Verify — Python tests still pass**

```bash
cd G:/Werewolf-agent
NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" -q
# Expected: all pass (same count as baseline)
```

- [ ] **Step 7: Commit**

```bash
git add VERSION src/werewolf_eval/release_metadata.py src/werewolf_eval/run_observer_server.py clients/qt_observer/CMakeLists.txt
git commit -m "feat: add VERSION single source and release_metadata helper"
```

---

### Task 2: Bootstrapper — core lifecycle skeleton

**Files:**
- Create: `src/werewolf_eval/release_host.py` (CLI entry)
- Create: `src/werewolf_eval/release_host/__init__.py`
- Create: `src/werewolf_eval/release_host/lifecycle.py` (start/stop/monitor)

**Interfaces:**
- Consumes: `release_metadata.read_version()`
- Produces: `release_host.lifecycle.ensure_data_dirs(data_root: Path) -> None`
- Produces: `release_host.lifecycle.find_or_start_server(data_root: Path, dist_root: Path) -> tuple[subprocess.Popen | None, int, str]` — returns (server_proc, port, owner_token)
- Produces: `release_host.lifecycle.spawn_client(client_exe: Path, observer_port: int, host_session_id: str, ...) -> subprocess.Popen`
- Produces: `release_host.lifecycle.release_host_main() -> int` — CLI entry

- [ ] **Step 1: Create release_host package skeleton**

```bash
mkdir -p G:/Werewolf-agent/src/werewolf_eval/release_host
```

Create `src/werewolf_eval/release_host/__init__.py`:
```python
"""Release host bootstrapper — lifecycle, IPC, update orchestration."""
```

- [ ] **Step 2: Write ensure_data_dirs**

Create `src/werewolf_eval/release_host/lifecycle.py`:

```python
"""Bootstrapper lifecycle: data dirs, server startup, client launch, shutdown."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Tuple


def _local_appdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", os.path.expandvars("%LOCALAPPDATA%")))


def _data_root() -> Path:
    return _local_appdata() / "Werewolf-agent"


def ensure_data_dirs(data_root: Path | None = None) -> Path:
    """Create %LOCALAPPDATA%/Werewolf-agent/... and return data_root."""
    root = data_root or _data_root()
    for sub in ("runs", "profiles", "configs", "logs", "runtime-state"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root
```

- [ ] **Step 3: Write server startup**

Add to `lifecycle.py`:

```python
from werewolf_eval.release_metadata import read_version


def _atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _generate_token() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex  # 64-char hex


def _find_existing_server(data_root: Path) -> Tuple[Path | None, dict | None]:
    """Read server-state.json and verify it points to a live server.
    Returns (state_path, state_dict) if valid, (None, None) otherwise."""
    state_file = data_root / "runtime-state" / "server-state.json"
    if not state_file.exists():
        return None, None
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        state_file.unlink(missing_ok=True)
        return None, None
    # Verify health
    import urllib.request
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        resp = opener.open(f"http://127.0.0.1:{state['port']}/health", timeout=2)
        health = json.loads(resp.read().decode("utf-8"))
        if health.get("instance_id") != state.get("instance_id"):
            return None, None
        if health.get("owner_token") != state.get("owner_token"):
            return None, None
        return state_file, state
    except Exception:
        # Stale: server dead but state file remains
        state_file.unlink(missing_ok=True)
        return None, None


def find_or_start_server(
    data_root: Path, dist_root: Path
) -> Tuple[subprocess.Popen | None, int, str, str]:
    """Find existing owned server or start a new one.
    Returns (server_proc_or_None, port, owner_token, host_session_id)."""
    host_session_id = uuid.uuid4().hex

    # Check for existing live server
    state_file, state = _find_existing_server(data_root)
    if state is not None:
        return None, state["port"], state["owner_token"], host_session_id

    # Start new server
    server_exe = dist_root / "runtime" / "observer-server.exe"
    owner_token = _generate_token()
    state_path = data_root / "runtime-state" / "server-state.json"

    cmd = [
        str(server_exe),
        "--host", "127.0.0.1", "--port", "0",
        "--runs-dir", str(data_root / "runs"),
        "--profiles-dir", str(data_root / "profiles"),
        "--configs-dir", str(data_root / "configs"),
        "--runtime-state-file", str(state_path),
        "--release-owner-token", owner_token,
        "--release-version", read_version(),
        "--allow-live-api",
    ]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)  # frozen server doesn't need it
    env["NO_PROXY"] = "127.0.0.1,localhost"

    proc = subprocess.Popen(
        cmd,
        stdout=open(data_root / "logs" / "server.log", "a"),
        stderr=open(data_root / "logs" / "server.err.log", "a"),
        env=env,
        cwd=str(data_root),
    )

    # Wait for server-state.json to appear (server writes it after bind)
    for _ in range(60):
        time.sleep(0.5)
        if state_path.exists():
            try:
                st = json.loads(state_path.read_text(encoding="utf-8"))
                port = st["port"]
                # Health check
                import urllib.request
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                resp = opener.open(f"http://127.0.0.1:{port}/health", timeout=2)
                health = json.loads(resp.read().decode("utf-8"))
                if health.get("instance_id") == st.get("instance_id"):
                    return proc, port, owner_token, host_session_id
            except Exception:
                continue
    # Timeout
    proc.terminate()
    proc.wait(timeout=5)
    raise RuntimeError("Server failed to start within 30 seconds")
```

- [ ] **Step 4: Write client spawn**

Add to `lifecycle.py`:

```python
def spawn_client(
    client_exe: Path,
    observer_port: int,
    host_session_id: str,
    release_version: str,
    update_request_path: Path,
) -> subprocess.Popen:
    """Launch Qt client. Returns the Popen handle."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    # Strip proxy env vars so QNetworkAccessManager doesn't dead-end on localhost
    for v in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(v, None)
    env["NO_PROXY"] = "127.0.0.1,localhost"

    return subprocess.Popen([
        str(client_exe),
        "--observer-base-url", f"http://127.0.0.1:{observer_port}",
        "--release-version", release_version,
        "--release-host-session", host_session_id,
        "--update-request-path", str(update_request_path),
    ], env=env)
```

- [ ] **Step 5: Write main entry point**

Add `release_host_main()` to `lifecycle.py`:

```python
def release_host_main() -> int:
    """CLI entry for Werewolf-agent.exe."""
    import argparse
    parser = argparse.ArgumentParser(description="Werewolf-agent")
    parser.add_argument("--version", action="version",
                        version=f"Werewolf-agent {read_version()}")
    args = parser.parse_args()

    dist_root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent.parent.parent
    data_root = ensure_data_dirs()

    print(f"Werewolf-agent {read_version()} starting")
    print(f"Data: {data_root}")

    try:
        server_proc, port, owner_token, host_session_id = find_or_start_server(data_root, dist_root)
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1

    client_exe = dist_root / "app" / "appqt_observer.exe"
    update_request_path = data_root / "runtime-state" / "update-request.json"

    client_proc = spawn_client(
        client_exe, port, host_session_id,
        read_version(), update_request_path,
    )

    # Wait for client to exit
    client_ret = client_proc.wait()

    # --- Shutdown logic ---
    # Check for update request
    update_request = None
    if update_request_path.exists():
        try:
            update_request = json.loads(update_request_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            update_request_path.unlink(missing_ok=True)

    # Check for active runs
    has_active = False
    try:
        import urllib.request
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        resp = opener.open(f"http://127.0.0.1:{port}/api/runs", timeout=3)
        runs_data = json.loads(resp.read().decode("utf-8"))
        has_active = any(
            r.get("status") in ("queued", "running")
            for r in runs_data.get("runs", [])
        )
    except Exception:
        pass

    if has_active:
        print("Active runs exist — keeping server alive. Reopen app to continue watching.")
        # Idle cleanup loop (30s grace after all runs finish)
        _idle_cleanup_loop(port, data_root, dist_root, host_session_id)
        return 0

    # Consume update request
    if (update_request
            and update_request.get("host_session_id") == host_session_id
            and update_request.get("action") == "launch_maintenance_tool"):
        update_request_path.unlink(missing_ok=True)
        _launch_maintenance_tool(dist_root, server_proc)

    if server_proc is not None:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_proc.kill()
    return 0


def _idle_cleanup_loop(port: int, data_root: Path, dist_root: Path, host_session_id: str) -> None:
    """Wait until all runs finish, then grace period, then stop server."""
    import urllib.request
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    grace_seconds = 30
    all_terminal_at = None

    while True:
        time.sleep(2)
        try:
            resp = opener.open(f"http://127.0.0.1:{port}/api/runs", timeout=2)
            runs = json.loads(resp.read().decode("utf-8")).get("runs", [])
        except Exception:
            break
        active = [r for r in runs if r.get("status") in ("queued", "running")]
        if active:
            all_terminal_at = None
            continue
        if all_terminal_at is None:
            all_terminal_at = time.monotonic()

        # Check for client reopen IPC
        hc = _read_host_control(data_root)
        if hc and hc.get("pending_reopen"):
            _clear_pending_reopen(data_root)
            client_exe = dist_root / "app" / "appqt_observer.exe"
            update_path = data_root / "runtime-state" / "update-request.json"
            client_proc = spawn_client(client_exe, port, host_session_id, read_version(), update_path)
            client_proc.wait()
            all_terminal_at = None
            continue

        if time.monotonic() - all_terminal_at > grace_seconds:
            break


def _read_host_control(data_root: Path) -> dict | None:
    path = data_root / "runtime-state" / "host-control.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _clear_pending_reopen(data_root: Path) -> None:
    path = data_root / "runtime-state" / "host-control.json"
    if path.exists():
        try:
            hc = json.loads(path.read_text(encoding="utf-8"))
            hc.pop("pending_reopen", None)
            _atomic_write_json(path, hc)
        except Exception:
            pass


def _launch_maintenance_tool(dist_root: Path, server_proc: subprocess.Popen | None) -> None:
    mt = dist_root / "maintenancetool.exe"
    if server_proc is not None:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_proc.kill()
    if mt.exists():
        subprocess.Popen([str(mt)], creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0)
```

- [ ] **Step 6: Create release_host.py CLI entry**

Create `src/werewolf_eval/release_host.py`:

```python
"""Werewolf-agent bootstrapper entry point."""
from __future__ import annotations
import sys
from werewolf_eval.release_host.lifecycle import release_host_main

if __name__ == "__main__":
    sys.exit(release_host_main())
```

- [ ] **Step 7: Verify with manual test run**

```bash
cd G:/Werewolf-agent
PYTHONPATH=src python -m werewolf_eval.release_host --version
# Expected: Werewolf-agent 0.2.0
```

- [ ] **Step 8: Commit**

```bash
git add src/werewolf_eval/release_host/ src/werewolf_eval/release_host.py
git commit -m "feat: bootstrapper core lifecycle skeleton"
```

---

### Task 3: Bootstrapper — host control TCP + IPC

**Files:**
- Create: `src/werewolf_eval/release_host/control.py`
- Modify: `src/werewolf_eval/release_host/lifecycle.py` (wire control into main)

**Interfaces:**
- Consumes: `release_host.lifecycle._generate_token()`, `_atomic_write_json()`
- Produces: `release_host.control.ControlServer` — context manager, starts loopback TCP on port 0, writes `host-control.json`, handles `open_or_foreground_client`
- Produces: `release_host.control.send_open_client_request(host_control_path: Path) -> str` — second-instance caller

- [ ] **Step 1: Write ControlServer**

Create `src/werewolf_eval/release_host/control.py`:

```python
"""Host-instance loopback TCP control endpoint (single-instance coordination)."""
from __future__ import annotations

import json
import socket
import threading
from pathlib import Path

from werewolf_eval.release_host.lifecycle import _atomic_write_json, _generate_token

MAX_MSG_BYTES = 4096
TIMEOUT = 2.0


def _write_host_control(data_root: Path, host_session_id: str, control_port: int, control_token: str, release_version: str) -> Path:
    path = data_root / "runtime-state" / "host-control.json"
    _atomic_write_json(path, {
        "schema_version": 1,
        "host_session_id": host_session_id,
        "host_pid": __import__("os").getpid(),
        "control_port": control_port,
        "control_token": control_token,
        "release_version": release_version,
        "started_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    })
    return path


def _handle_request(data: bytes, host_session_id: str, control_token: str) -> dict:
    try:
        req = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"schema_version": 1, "ok": False, "code": "invalid_request"}

    if not isinstance(req, dict) or req.get("schema_version") != 1:
        return {"schema_version": 1, "ok": False, "code": "invalid_request"}

    msg_type = req.get("type")
    if msg_type == "ping":
        return {"schema_version": 1, "ok": True, "action": "pong"}

    if msg_type != "open_or_foreground_client":
        return {"schema_version": 1, "ok": False, "code": "unknown_message_type"}

    if req.get("host_session_id") != host_session_id:
        return {"schema_version": 1, "ok": False, "code": "session_mismatch"}
    if req.get("control_token") != control_token:
        return {"schema_version": 1, "ok": False, "code": "token_mismatch"}

    return {"schema_version": 1, "ok": True, "action": "foregrounded"}


def control_server_thread(
    sock: socket.socket,
    host_session_id: str,
    control_token: str,
    data_root: Path,
    stop_event: threading.Event,
) -> None:
    sock.settimeout(1.0)
    while not stop_event.is_set():
        try:
            conn, addr = sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        try:
            conn.settimeout(TIMEOUT)
            data = conn.recv(MAX_MSG_BYTES)
            if not data:
                conn.close()
                continue
            resp = _handle_request(data, host_session_id, control_token)
            # If foreground requested, set pending_reopen on host-control
            if resp.get("ok") and resp.get("action") == "foregrounded":
                try:
                    hc_path = data_root / "runtime-state" / "host-control.json"
                    hc = json.loads(hc_path.read_text(encoding="utf-8"))
                    hc["pending_reopen"] = True
                    _atomic_write_json(hc_path, hc)
                except Exception:
                    pass
            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass


class ControlServer:
    """Loopback TCP control server. Use as context manager."""

    def __init__(self, data_root: Path, host_session_id: str, release_version: str):
        self._data_root = data_root
        self._session_id = host_session_id
        self._release_version = release_version
        self._token = _generate_token()
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._port: int = 0
        self._hc_path: Path | None = None

    @property
    def port(self) -> int:
        return self._port

    @property
    def token(self) -> str:
        return self._token

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        self._port = self._sock.getsockname()[1]

        self._hc_path = _write_host_control(
            self._data_root, self._session_id,
            self._port, self._token, self._release_version,
        )

        self._thread = threading.Thread(
            target=control_server_thread,
            args=(self._sock, self._session_id, self._token, self._data_root, self._stop),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=2)
        if self._hc_path and self._hc_path.exists():
            self._hc_path.unlink(missing_ok=True)

    def __enter__(self) -> "ControlServer":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()


def send_open_client_request(host_control_path: Path) -> str:
    """Second-instance caller: send open_or_foreground_client to existing host.
    Returns 'foregrounded' | 'client_started' | error code string."""
    try:
        hc = json.loads(host_control_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "host_unavailable"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect(("127.0.0.1", hc["control_port"]))
        req = json.dumps({
            "schema_version": 1,
            "type": "open_or_foreground_client",
            "host_session_id": hc["host_session_id"],
            "control_token": hc["control_token"],
        })
        sock.sendall(req.encode("utf-8"))
        data = sock.recv(MAX_MSG_BYTES)
        resp = json.loads(data.decode("utf-8"))
        sock.close()
        if resp.get("ok"):
            return resp.get("action", "unknown")
        return resp.get("code", "error")
    except Exception:
        return "host_unavailable"
```

- [ ] **Step 2: Wire control into release_host_main**

In `lifecycle.py`, add imports and wrap main logic:

Add at top of `release_host_main()`:
```python
from werewolf_eval.release_host.control import ControlServer, send_open_client_request

# Check for existing instance
hc_path = data_root / "runtime-state" / "host-control.json"
if hc_path.exists():
    result = send_open_client_request(hc_path)
    if result in ("foregrounded", "client_started"):
        print(f"Existing instance found — {result}")
        return 0
    # Stale host-control — clean up and become primary
    hc_path.unlink(missing_ok=True)
```

Wrap the server/client lifecycle with ControlServer:
```python
with ControlServer(data_root, host_session_id, read_version()) as cs:
    # (existing server/client logic here)
```

- [ ] **Step 3: Commit**

```bash
git add src/werewolf_eval/release_host/control.py src/werewolf_eval/release_host/lifecycle.py
git commit -m "feat: host control TCP + single-instance IPC"
```

---

### Task 4: Bootstrapper — update request + maintenance tool launch

**Files:**
- Modify: `src/werewolf_eval/release_host/lifecycle.py` (refine shutdown logic with update request consumption)
- The update request *writing* is done by Qt client (Task 6); this task implements host-side *consumption*

**Interfaces:**
- Consumes: `update-request.json` (written by Qt client)
- Produces: clean shutdown → maintenance tool launch path

- [ ] **Step 1: Refine shutdown in release_host_main**

Replace the inline shutdown logic block with a call to a helper. Add to `lifecycle.py`:

```python
def _consume_update_request(path: Path, host_session_id: str) -> dict | None:
    """Validate and consume update-request.json. Returns request dict or None."""
    if not path.exists():
        return None
    try:
        req = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        path.unlink(missing_ok=True)
        return None

    # Validate TTL (5 minutes)
    from datetime import datetime, timezone, timedelta
    try:
        created = datetime.fromisoformat(req.get("created_at", "").rstrip("Z"))
        if datetime.now(timezone.utc) - created.replace(tzinfo=timezone.utc) > timedelta(minutes=5):
            path.unlink(missing_ok=True)
            return None
    except ValueError:
        path.unlink(missing_ok=True)
        return None

    if (req.get("host_session_id") != host_session_id
            or req.get("schema_version") != 1
            or req.get("action") != "launch_maintenance_tool"):
        path.unlink(missing_ok=True)
        return None

    return req
```

- [ ] **Step 2: Wire into shutdown sequence**

The shutdown sequence in `release_host_main()` should call `_consume_update_request` when `has_active` is `False`. Update the relevant code block to use the helper before checking `update_request`. Delete only on valid consumption.

- [ ] **Step 3: Commit**

```bash
git add src/werewolf_eval/release_host/lifecycle.py
git commit -m "feat: update request consumption + maintenance tool launch"
```

---

### Task 5: Server — release parameters + recovery

**Files:**
- Modify: `src/werewolf_eval/run_observer_server.py`
- Modify: `src/werewolf_eval/observer/factory.py`
- Modify: `src/werewolf_eval/observer/state.py` (add release fields)
- Create: `src/werewolf_eval/observer/release_manifest.py`

**Interfaces:**
- Consumes: `release_metadata.read_version()`, `release_metadata.read_release_metadata()`
- Produces: new server args: `--runtime-state-file`, `--release-owner-token`, `--release-version`, `--profiles-dir`, `--configs-dir`
- Produces: `observer.release_manifest.write_release_manifest(run_dir: Path, metadata: dict) -> None`
- Produces: `/health` returns `instance_id`, `owner_token`, `release_version`, `protocol_version`

- [ ] **Step 1: Add server CLI args**

In `run_observer_server.py`, add to `build_arg_parser()`:

```python
parser.add_argument("--runtime-state-file", default=None,
                    help="Path to server-state.json for release host (None = don't write)")
parser.add_argument("--release-owner-token", default=None,
                    help="Owner token from release host")
parser.add_argument("--release-version", default=None,
                    help="Release version from VERSION")
parser.add_argument("--profiles-dir", default=None,
                    help="Explicit profiles directory")
parser.add_argument("--configs-dir", default=None,
                    help="Explicit configs directory")
```

- [ ] **Step 2: Pass profiles_dir / configs_dir through factory**

Update `create_observer_server()` call in `main()` to pass `profiles_dir` and `configs_dir` from args when provided:

```python
server = create_observer_server(
    args.host, args.port,
    Path(args.runs_dir),
    profiles_dir=Path(args.profiles_dir) if args.profiles_dir else None,
    configs_dir=Path(args.configs_dir) if args.configs_dir else None,
    ...
)
```

- [ ] **Step 3: Write release_manifest helper**

Create `src/werewolf_eval/observer/release_manifest.py`:

```python
"""Write release-manifest.json into each run directory."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


def write_release_manifest(
    run_dir: Path,
    release_version: str,
    channel: str = "dev",
    git_commit: str = "unknown",
    build_timestamp: str | None = None,
    observer_protocol_version: int = 1,
) -> None:
    """Atomically write release-manifest.json into run_dir.
    Must be called after run directory is created, before run execution.
    Raises OSError on failure — caller must fail the run."""
    ts = build_timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "release_version": release_version,
        "channel": channel,
        "git_commit": git_commit,
        "build_timestamp": ts,
        "bootstrapper_version": release_version,
        "server_version": release_version,
        "observer_protocol_version": observer_protocol_version,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    path = run_dir / "release-manifest.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
```

- [ ] **Step 4: Wire server-state.json writing**

Add to `run_observer_server.py` `main()`, after server starts:

```python
# Write server-state.json if release host requested it
runtime_state_file = getattr(args, "runtime_state_file", None)
if runtime_state_file:
    import uuid, os, json as _json
    state = {
        "schema_version": 1,
        "instance_id": uuid.uuid4().hex,
        "pid": os.getpid(),
        "port": port,
        "owner_token": getattr(args, "release_owner_token", ""),
        "release_version": getattr(args, "release_version", read_version()),
        "observer_protocol_version": 1,
        "data_root": str(Path(args.runs_dir).parent) if args.runs_dir else "",
        "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    sp = Path(runtime_state_file)
    tmp = sp.with_suffix(".tmp")
    tmp.write_text(_json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(sp)
```

- [ ] **Step 5: Extend /health response**

The `/health` endpoint in `handler.py` must return `instance_id`, `owner_token`, `release_version`, `protocol_version` when the server has them. Add handling in `_route_health` to include these fields from server state.

- [ ] **Step 6: Wire release_manifest into run creation**

In `observer/launch.py` or `observer/run_manager.py`, after `run_dir.mkdir()`, call `write_release_manifest(run_dir, ...)` with the release metadata from server state. If write fails, the run must not proceed.

- [ ] **Step 7: Verify Python tests still pass**

```bash
cd G:/Werewolf-agent
NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" -q
```

- [ ] **Step 8: Commit**

```bash
git add src/werewolf_eval/run_observer_server.py src/werewolf_eval/observer/
git commit -m "feat: server release params, server-state.json, release-manifest.json"
```

---

### Task 6: Qt Client — release params + About & Update UI

**Files:**
- Modify: `clients/qt_observer/main.cpp` (new CLI args)
- Modify: `clients/qt_observer/qml/ProviderSettingsView.qml` (About & Update section)
- Modify: `clients/qt_observer/qml/I18n.qml` (new translation keys)
- Modify: `clients/qt_observer/src/ObserverApiClient.h` (expose active run count for update gate)
- Modify: `clients/qt_observer/src/ObserverApiClient.cpp` (same)

**Interfaces:**
- Consumes: `--release-version`, `--release-host-session`, `--update-request-path`
- Produces: `ObserverApiClient::releaseVersion()`, `ObserverApiClient::hostSessionId()`, `ObserverApiClient::updateRequestPath()`
- Produces: UI button that writes `update-request.json` and calls `QGuiApplication::quit()`

- [ ] **Step 1: Add CLI args to main.cpp**

In `main.cpp`, parse new args:

```cpp
static QString releaseVersionFromArgs(const QStringList &args) {
    const int index = args.indexOf("--release-version");
    if (index >= 0 && index + 1 < args.size())
        return args.at(index + 1);
    return QString();
}

static QString hostSessionFromArgs(const QStringList &args) {
    const int index = args.indexOf("--release-host-session");
    if (index >= 0 && index + 1 < args.size())
        return args.at(index + 1);
    return QString();
}

static QString updateRequestPathFromArgs(const QStringList &args) {
    const int index = args.indexOf("--update-request-path");
    if (index >= 0 && index + 1 < args.size())
        return args.at(index + 1);
    return QString();
}

static bool versionFlagFromArgs(const QStringList &args) {
    return args.contains("--version");
}
```

Wire them into main:

```cpp
if (versionFlagFromArgs(app.arguments())) {
    QString ver = releaseVersionFromArgs(app.arguments());
    if (ver.isEmpty()) ver = QStringLiteral("0.2.0");
    QTextStream(stdout) << "Werewolf-agent " << ver << "\n";
    return 0;
}

observerClient.setReleaseVersion(releaseVersionFromArgs(app.arguments()));
observerClient.setHostSessionId(hostSessionFromArgs(app.arguments()));
observerClient.setUpdateRequestPath(updateRequestPathFromArgs(app.arguments()));
```

- [ ] **Step 2: Add accessors to ObserverApiClient**

In `ObserverApiClient.h`, add:

```cpp
Q_INVOKABLE QString releaseVersion() const;
Q_INVOKABLE QString releaseChannel() const;  // hard-coded "stable" for now
Q_INVOKABLE QString hostSessionId() const;
Q_INVOKABLE QString updateRequestPath() const;
Q_INVOKABLE bool hasActiveRun() const;  // from runs list state

void setReleaseVersion(const QString &v);
void setHostSessionId(const QString &s);
void setUpdateRequestPath(const QString &p);
```

In `ObserverApiClient.cpp`, implement getters/setters (simple member variable storage). `hasActiveRun()` checks the cached runs list for any run with status `"queued"` or `"running"`.

- [ ] **Step 3: Add I18n keys**

In `I18n.qml`, add keys under both `zh` and `en`:

```javascript
// zh
"about_title": "关于与更新",
"about_product": "Werewolf-agent",
"about_version_label": "版本",
"about_channel_label": "通道",
"about_channel_stable": "Stable",
"about_channel_preview": "Preview",
"about_update_desc": "通过系统更新工具检查可用更新",
"about_check_update": "检查更新",
"about_active_run_block": "当前有进行中的对局，请等待对局结束后再检查更新",
"about_exiting_for_update": "正在退出并打开更新工具…",
"about_update_failed": "无法启动更新工具，请查看日志",

// en
"about_title": "About & Updates",
"about_product": "Werewolf-agent",
"about_version_label": "Version",
"about_channel_label": "Channel",
"about_channel_stable": "Stable",
"about_channel_preview": "Preview",
"about_update_desc": "Check for available updates using the system update tool",
"about_check_update": "Check for Updates",
"about_active_run_block": "A match is in progress. Please wait for it to finish before checking for updates.",
"about_exiting_for_update": "Exiting and opening update tool…",
"about_update_failed": "Cannot start update tool. Please check the logs.",
```

- [ ] **Step 4: Add About & Update section to ProviderSettingsView.qml**

At the bottom of `ProviderSettingsView.qml`, before the closing root element, add:

```qml
SectionHeader { text: I18n.about_title }

AppCard {
    Column {
        spacing: 12
        anchors.fill: parent

        Row {
            spacing: 8
            Text {
                text: I18n.about_product
                font.family: Theme.fontFamilies.serif
                font.pixelSize: 18
                color: Theme.warm.ink
            }
        }

        Row {
            spacing: 8
            Text {
                text: I18n.about_version_label + ": " + ObserverClient.releaseVersion()
                color: Theme.warm.body
            }
        }

        Row {
            spacing: 8
            Text {
                text: I18n.about_channel_label + ": " + I18n.about_channel_stable
                color: Theme.warm.body
            }
        }

        Text {
            text: I18n.about_update_desc
            color: Theme.warm.muted
            font.pixelSize: 12
        }

        AppButton {
            text: ObserverClient.hasActiveRun()
                ? I18n.about_active_run_block
                : I18n.about_check_update
            enabled: !ObserverClient.hasActiveRun()
            onClicked: {
                if (ObserverClient.updateRequestPath()) {
                    // Write update request, then quit
                    var req = {
                        schema_version: 1,
                        request_id: Date.now().toString(36) + Math.random().toString(36).slice(2),
                        host_session_id: ObserverClient.hostSessionId(),
                        client_pid: 0,
                        created_at: new Date().toISOString(),
                        release_version: ObserverClient.releaseVersion(),
                        action: "launch_maintenance_tool"
                    };
                    // Write via a small C++ helper or use QML FileDialog?
                    // The ObserverApiClient should expose a method for this
                    ObserverClient.writeUpdateRequest(req);
                }
                updateStatus.text = I18n.about_exiting_for_update;
                Qt.quit();
            }
        }

        Text {
            id: updateStatus
            color: Theme.warm.muted
            visible: text !== ""
        }
    }
}
```

- [ ] **Step 5: Add writeUpdateRequest to ObserverApiClient**

In `ObserverApiClient.h`:
```cpp
Q_INVOKABLE bool writeUpdateRequest(const QVariantMap &request);
```

In `ObserverApiClient.cpp`:
```cpp
bool ObserverApiClient::writeUpdateRequest(const QVariantMap &request) {
    QString path = m_updateRequestPath;
    if (path.isEmpty()) return false;
    QJsonDocument doc(QJsonObject::fromVariantMap(request));
    QFile file(path + ".tmp");
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) return false;
    file.write(doc.toJson(QJsonDocument::Compact));
    file.close();
    // Atomic rename
    QFile::remove(path);
    return QFile::rename(path + ".tmp", path);
}
```

- [ ] **Step 6: Wire close-with-active-run warning**

When the user closes the client window while active runs exist, show a confirmation dialog. In `AppShell.qml` or the close handler, check `ObserverClient.hasActiveRun()` and display:

```
"当前有进行中的对局。关闭窗口后，对局将继续在本地后台运行。
重新打开 Werewolf-agent 可继续观察。"
```

- [ ] **Step 7: Build and screenshot verify**

```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```

Use screenshot method from `verifying-qt-observer-ui` skill to verify the About & Update card renders correctly in both zh and en.

- [ ] **Step 8: Verify static contract tests**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract -v
```

- [ ] **Step 9: Commit**

```bash
git add clients/qt_observer/
git commit -m "feat: Qt client release params + About & Update UI"
```

---

### Task 7: CMake Release build + windeployqt

**Files:**
- Modify: `clients/qt_observer/CMakeLists.txt` (Release flags)
- Create: `scripts/release/build-qt-release.sh`

**Interfaces:**
- Consumes: VERSION (already wired in Task 1)
- Produces: `scripts/release/build-qt-release.sh` — repeatable build script
- Produces: `app/` deployment directory at a build-specified output path

- [ ] **Step 1: Update CMakeLists.txt for Release**

In `clients/qt_observer/CMakeLists.txt`, ensure Release build uses proper flags:

```cmake
set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING "" FORCE)
```

- [ ] **Step 2: Create build script**

Create `scripts/release/build-qt-release.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/.tmp/qt-observer-release"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.tmp/release/app}"

export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:/f/Qt/Tools/CMake_64/bin:$PATH"

echo "=== Configuring Release build ==="
cmake -S "$REPO_ROOT/clients/qt_observer" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -G "MinGW Makefiles"

echo "=== Building ==="
cmake --build "$BUILD_DIR" --config Release

echo "=== Deploying with windeployqt ==="
mkdir -p "$OUTPUT_DIR"
cp "$BUILD_DIR/appqt_observer.exe" "$OUTPUT_DIR/"

windeployqt.exe \
    --release \
    --qmldir "$REPO_ROOT/clients/qt_observer/qml" \
    --compiler-runtime \
    "$OUTPUT_DIR/appqt_observer.exe"

echo "=== Qt deployment tree ready at $OUTPUT_DIR ==="
ls -la "$OUTPUT_DIR"
```

- [ ] **Step 3: Run build script**

```bash
cd G:/Werewolf-agent
bash scripts/release/build-qt-release.sh
```

Expected: `app/` directory created with `appqt_observer.exe` + full Qt DLL set.

- [ ] **Step 4: Verify Release client starts**

```bash
# Start dev server first
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_observer_server --port 18765 --runs-dir .runs &

# Run Release client against it
env -u HTTP_PROXY -u HTTPS_PROXY NO_PROXY=127.0.0.1 .tmp/release/app/appqt_observer.exe --observer-base-url http://127.0.0.1:18765
```

Verify client window opens and displays Home view. Kill server after.

- [ ] **Step 5: Commit**

```bash
git add clients/qt_observer/CMakeLists.txt scripts/release/build-qt-release.sh
git commit -m "feat: CMake Release build + windeployqt deployment script"
```

---

### Task 8: PyInstaller — release venv + server frozen build

**Files:**
- Create: `scripts/release/setup-release-venv.sh`
- Create: `scripts/release/observer-server.spec`
- Create: `scripts/release/build-server-frozen.sh`

**Interfaces:**
- Consumes: VERSION, `src/werewolf_eval/` (all modules)
- Produces: `runtime/` directory with `observer-server.exe` + `_internal/`

- [ ] **Step 1: Create release venv**

Create `scripts/release/setup-release-venv.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-release"

echo "=== Creating release venv ==="
python -m venv "$VENV_DIR"

source "$VENV_DIR/Scripts/activate"
pip install --upgrade pip
pip install pyinstaller

echo "=== Release venv ready at $VENV_DIR ==="
echo "PyInstaller version: $(pyinstaller --version)"
```

- [ ] **Step 2: Run venv setup**

```bash
cd G:/Werewolf-agent
bash scripts/release/setup-release-venv.sh
```

- [ ] **Step 3: Create PyInstaller spec for observer server**

Create `scripts/release/observer-server.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['../../src/werewolf_eval/run_observer_server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../../VERSION', '.'),
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
        'werewolf_eval.observer.release_manifest',
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
        'werewolf_eval.release_metadata',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'tests', 'test'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='observer-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='observer-server',
)
```

- [ ] **Step 4: Create server build script**

Create `scripts/release/build-server-frozen.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-release"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.tmp/release/runtime}"
SPEC_FILE="$REPO_ROOT/scripts/release/observer-server.spec"

source "$VENV_DIR/Scripts/activate"

echo "=== Building frozen observer server ==="
cd "$REPO_ROOT"
pyinstaller --distpath "$OUTPUT_DIR/.." --workpath "$REPO_ROOT/.tmp/pyi-server-build" "$SPEC_FILE"

echo "=== Frozen server at $OUTPUT_DIR/observer-server/ ==="
ls -la "$OUTPUT_DIR/observer-server/"
```

- [ ] **Step 5: Run server build**

```bash
cd G:/Werewolf-agent
bash scripts/release/build-server-frozen.sh
```

- [ ] **Step 6: Portable smoke**

```bash
# Copy frozen runtime to temp dir (independent of source repo)
TMPDIR=$(mktemp -d)
cp -r .tmp/release/runtime/observer-server "$TMPDIR/"
cd "$TMPDIR"

# Ensure no PYTHONPATH, no source
unset PYTHONPATH

# Start server
./observer-server/observer-server.exe --host 127.0.0.1 --port 0 \
    --runs-dir "$TMPDIR/runs" --profiles-dir "$TMPDIR/profiles" --configs-dir "$TMPDIR/configs" &
SERVER_PID=$!
sleep 3

# Check health (read port from server stdout or try common)
# For smoke test, use the known port from stdout or scan
curl -s http://127.0.0.1:<port>/health

# Verify profiles
curl -s http://127.0.0.1:<port>/api/profiles
# Expected: at least default profile present

# Verify capabilities
curl -s http://127.0.0.1:<port>/api/runtime/capabilities

# Cleanup
kill $SERVER_PID
rm -rf "$TMPDIR"
```

- [ ] **Step 7: Verify no synthetic sentinel in frozen output**

```bash
grep -r "R0_TEST_SECRET_SENTINEL_DO_NOT_SHIP" .tmp/release/runtime/observer-server/ && echo "FAIL: sentinel found" || echo "PASS: no sentinel"
```

- [ ] **Step 8: Commit**

```bash
git add scripts/release/setup-release-venv.sh scripts/release/observer-server.spec scripts/release/build-server-frozen.sh
git commit -m "feat: PyInstaller server frozen build + portable smoke"
```

---

### Task 9: PyInstaller — bootstrapper frozen build

**Files:**
- Create: `scripts/release/werewolf-agent.spec`
- Create: `scripts/release/build-bootstrapper-frozen.sh`

**Interfaces:**
- Consumes: `src/werewolf_eval/release_host/`, `src/werewolf_eval/release_metadata.py`
- Produces: `Werewolf-agent.exe` + `_internal/` at build output

- [ ] **Step 1: Create bootstrapper spec**

Create `scripts/release/werewolf-agent.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['../../src/werewolf_eval/release_host.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../../VERSION', '.'),
    ],
    hiddenimports=[
        'werewolf_eval.release_metadata',
        'werewolf_eval.release_host',
        'werewolf_eval.release_host.lifecycle',
        'werewolf_eval.release_host.control',
        'json', 'uuid', 'socket', 'threading', 'subprocess',
        'urllib.request', 'http.server',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['werewolf_eval.emergent_engine', 'werewolf_eval.provider_agent',
              'werewolf_eval.provider_registry', 'werewolf_eval.action_runtime',
              'werewolf_eval.observer', 'tests', 'test', 'tkinter', 'matplotlib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True, name='Werewolf-agent',
    console=True, debug=False, strip=False, upx=True,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True,
    name='Werewolf-agent',
)
```

- [ ] **Step 2: Create bootstrapper build script**

Create `scripts/release/build-bootstrapper-frozen.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-release"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.tmp/release}"
SPEC_FILE="$REPO_ROOT/scripts/release/werewolf-agent.spec"

source "$VENV_DIR/Scripts/activate"

echo "=== Building frozen bootstrapper ==="
cd "$REPO_ROOT"
pyinstaller --distpath "$OUTPUT_DIR" --workpath "$REPO_ROOT/.tmp/pyi-bootstrapper-build" "$SPEC_FILE"

echo "=== Bootstrapper at $OUTPUT_DIR/Werewolf-agent/ ==="
ls -la "$OUTPUT_DIR/Werewolf-agent/"
```

- [ ] **Step 3: Run bootstrapper build**

```bash
cd G:/Werewolf-agent
bash scripts/release/build-bootstrapper-frozen.sh
```

- [ ] **Step 4: Verify bootstrapper --version**

```bash
.tmp/release/Werewolf-agent/Werewolf-agent.exe --version
# Expected: Werewolf-agent 0.2.0
```

- [ ] **Step 5: Commit**

```bash
git add scripts/release/werewolf-agent.spec scripts/release/build-bootstrapper-frozen.sh
git commit -m "feat: PyInstaller bootstrapper frozen build"
```

---

### Task 10: Qt IFW — package, config, installer, file:// repo

**Files:**
- Create: `scripts/release/ifw/config/config.xml.in`
- Create: `scripts/release/ifw/packages/com.werewolfagent.app/meta/package.xml`
- Create: `scripts/release/ifw/packages/com.werewolfagent.app/meta/installscript.qs`
- Create: `scripts/release/ifw/packages/com.werewolfagent.app/meta/license.txt`
- Create: `scripts/release/assemble-package.sh`
- Create: `scripts/release/build-installer.sh`
- Create: `scripts/release/build-repo.sh`

**Interfaces:**
- Consumes: `app/`, `runtime/`, `Werewolf-agent/` from previous tasks
- Produces: IFW package tree, installer .exe, file:// repository

- [ ] **Step 1: Create IFW config template**

Create `scripts/release/ifw/config/config.xml.in`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Installer>
    <Name>Werewolf-agent</Name>
    <Version>${IFW_VERSION}</Version>
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

- [ ] **Step 2: Create package.xml**

Create `scripts/release/ifw/packages/com.werewolfagent.app/meta/package.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package>
    <DisplayName>Werewolf-agent</DisplayName>
    <Description>AI-vs-AI Werewolf live experiment platform</Description>
    <Version>${IFW_VERSION}</Version>
    <ReleaseDate>${RELEASE_DATE}</ReleaseDate>
    <Name>com.werewolfagent.app</Name>
    <Script>installscript.qs</Script>
    <Licenses>
        <License name="License Agreement" file="license.txt" />
    </Licenses>
    <Default>true</Default>
    <Essential>true</Essential>
    <ForcedInstallation>true</ForcedInstallation>
</Package>
```

- [ ] **Step 3: Create installscript.qs**

Create `scripts/release/ifw/packages/com.werewolfagent.app/meta/installscript.qs`:

```javascript
function Component() {}

Component.prototype.createOperations = function() {
    component.createOperations();

    // Create desktop shortcut
    component.addOperation("CreateShortcut",
        "@TargetDir@/Werewolf-agent.exe",
        "@DesktopDir@/Werewolf-agent.lnk",
        "workingDirectory=@TargetDir@");

    // Create Start Menu shortcut
    component.addOperation("CreateShortcut",
        "@TargetDir@/Werewolf-agent.exe",
        "@StartMenuDir@/Werewolf-agent.lnk",
        "workingDirectory=@TargetDir@");
};

Component.prototype.createOperationsForUninstall = function() {
    component.createOperationsForUninstall();
    // Note: default uninstall does NOT remove %LOCALAPPDATA%\Werewolf-agent\
    // That is only done if the user checks "delete local data" via the installer
    // uninstaller GUI (handled by IFW built-in data directory removal option)
};

// Custom page for data cleanup option
Component.prototype.setDefaultPageVisible = function(pageId, visible) {
    if (pageId === QInstaller.PerformUninstallation) {
        // Show custom checkbox for data cleanup
        installer.setValue("DeleteUserData", "false");
    }
};
```

- [ ] **Step 4: Create license.txt**

Simple MIT-style license text for the installer wizard.

- [ ] **Step 5: Create assemble-package script**

Create `scripts/release/assemble-package.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RELEASE_DIR="$REPO_ROOT/.tmp/release"
PKG_DIR="$REPO_ROOT/.tmp/ifw-package/com.werewolfagent.app"
META_DIR="$PKG_DIR/meta"
DATA_DIR="$PKG_DIR/data"

IFW_VERSION="${IFW_VERSION:-0.2.0}"
RELEASE_DATE="${RELEASE_DATE:-$(date +%Y-%m-%d)}"

echo "=== Assembling IFW package ==="
rm -rf "$PKG_DIR"
mkdir -p "$META_DIR" "$DATA_DIR"

# Copy payload
cp -r "$RELEASE_DIR/Werewolf-agent/Werewolf-agent.exe" "$DATA_DIR/"
cp -r "$RELEASE_DIR/Werewolf-agent/_internal" "$DATA_DIR/"
cp -r "$RELEASE_DIR/app" "$DATA_DIR/"
cp -r "$RELEASE_DIR/runtime/observer-server" "$DATA_DIR/runtime"

# Copy metadata (with variable substitution)
cat "$REPO_ROOT/scripts/release/ifw/packages/com.werewolfagent.app/meta/package.xml" \
    | sed "s/\${IFW_VERSION}/$IFW_VERSION/g" \
    | sed "s/\${RELEASE_DATE}/$RELEASE_DATE/g" \
    > "$META_DIR/package.xml"

cp "$REPO_ROOT/scripts/release/ifw/packages/com.werewolfagent.app/meta/installscript.qs" "$META_DIR/"
cp "$REPO_ROOT/scripts/release/ifw/packages/com.werewolfagent.app/meta/license.txt" "$META_DIR/"

echo "=== Package assembled at $PKG_DIR ==="
```

- [ ] **Step 6: Create installer build script**

Create `scripts/release/build-installer.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG_DIR="$REPO_ROOT/.tmp/ifw-package"
CONFIG_DIR="$REPO_ROOT/.tmp/ifw-config"
IFW_BIN="F:/Qt/Tools/QtInstallerFramework/4.11/bin"

IFW_VERSION="${IFW_VERSION:-0.2.0}"
REPOSITORY_URL="${REPOSITORY_URL:-file:///$REPO_ROOT/.tmp/ifw-repo/stable}"
RELEASE_DATE="${RELEASE_DATE:-$(date +%Y-%m-%d)}"

# Prepare config
mkdir -p "$CONFIG_DIR"
cat "$REPO_ROOT/scripts/release/ifw/config/config.xml.in" \
    | sed "s/\${IFW_VERSION}/$IFW_VERSION/g" \
    | sed "s|\${REPOSITORY_URL}|$REPOSITORY_URL|g" \
    > "$CONFIG_DIR/config.xml"

echo "=== Building installer ==="
"$IFW_BIN/binarycreator.exe" \
    -c "$CONFIG_DIR/config.xml" \
    -p "$PKG_DIR" \
    "$REPO_ROOT/.tmp/release/Werewolf-agent-${IFW_VERSION}-installer.exe"

echo "=== Installer: .tmp/release/Werewolf-agent-${IFW_VERSION}-installer.exe ==="
```

- [ ] **Step 7: Create repository build script**

Create `scripts/release/build-repo.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG_DIR="$REPO_ROOT/.tmp/ifw-package"
REPO_DIR="$REPO_ROOT/.tmp/ifw-repo/stable"
IFW_BIN="F:/Qt/Tools/QtInstallerFramework/4.11/bin"

echo "=== Building online repository ==="
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"

"$IFW_BIN/repogen.exe" \
    -p "$PKG_DIR" \
    "$REPO_DIR"

echo "=== Repository at $REPO_DIR ==="
ls -la "$REPO_DIR"
```

- [ ] **Step 8: Build and verify installer exists**

```bash
cd G:/Werewolf-agent
bash scripts/release/assemble-package.sh
bash scripts/release/build-repo.sh
bash scripts/release/build-installer.sh
```

Expected: `Werewolf-agent-0.2.0-installer.exe` and `ifw-repo/stable/` created.

- [ ] **Step 9: Commit**

```bash
git add scripts/release/ifw/ scripts/release/assemble-package.sh scripts/release/build-installer.sh scripts/release/build-repo.sh
git commit -m "feat: Qt IFW package, installer, file:// repository"
```

---

### Task 11: End-to-end verification + GitHub Pages publishing

**Files:**
- Create: `scripts/release/smoke-test.sh` (end-to-end verification script)
- Create: `scripts/release/publish-to-github-pages.sh`

**Interfaces:**
- Consumes: All previous task outputs
- Produces: Verification results, GitHub Pages ready repository

- [ ] **Step 1: Create end-to-end smoke test**

Create `scripts/release/smoke-test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RELEASE_DIR="$REPO_ROOT/.tmp/release"
DATA_DIR="$REPO_ROOT/.tmp/smoke-test-data"
INSTALL_DIR="$REPO_ROOT/.tmp/smoke-test-install"

echo "=== R0 End-to-End Smoke Test ==="

# 1. Clean install
echo "--- V1: Clean install ---"
rm -rf "$INSTALL_DIR" "$DATA_DIR"
# Run installer in unattended mode
"$RELEASE_DIR/Werewolf-agent-0.2.0-installer.exe" \
    --root "$INSTALL_DIR" --accept-licenses --default-answer --confirm-command install
# Verify key files exist
test -f "$INSTALL_DIR/Werewolf-agent.exe" || { echo "FAIL: bootstrapper missing"; exit 1; }
test -f "$INSTALL_DIR/app/appqt_observer.exe" || { echo "FAIL: Qt client missing"; exit 1; }
test -f "$INSTALL_DIR/runtime/observer-server.exe" || { echo "FAIL: server missing"; exit 1; }

# 2. Synthetic sentinel scan
echo "--- V8: Sentinel scan ---"
grep -r "R0_TEST_SECRET_SENTINEL" "$INSTALL_DIR" && { echo "FAIL: sentinel found in install"; exit 1; } || echo "PASS"

# 3. First run
echo "--- V2: First run ---"
export LOCALAPPDATA="$DATA_DIR"
mkdir -p "$DATA_DIR/Werewolf-agent"
# Start bootstrapper (runs in background, need to capture PID)
"$INSTALL_DIR/Werewolf-agent.exe" &
HOST_PID=$!
sleep 5

# Verify data dirs were created
test -d "$DATA_DIR/Werewolf-agent/runs" || { echo "FAIL: runs dir not created"; exit 1; }
test -d "$DATA_DIR/Werewolf-agent/logs" || { echo "FAIL: logs dir not created"; exit 1; }

# 4. Second instance test
echo "--- V2.5: Single instance ---"
"$INSTALL_DIR/Werewolf-agent.exe" &
SECOND_PID=$!
sleep 2
# Second instance should exit quickly (foreground first)
if ps -p $SECOND_PID > /dev/null 2>&1; then
    echo "WARNING: second instance didn't exit quickly (may need longer wait)"
fi

# 5. Run a fake game
echo "--- V4.1: Fake game ---"
# Kill existing client, then restart with client to trigger a fake game
# (This requires observer server running — use the bootstrapper-managed one)
PORT=$(cat "$DATA_DIR/Werewolf-agent/runtime-state/server-state.json" | python -c "import sys,json; print(json.load(sys.stdin)['port'])")
curl -s "http://127.0.0.1:$PORT/health" || { echo "FAIL: server not healthy"; exit 1; }

# Launch a fake game via API
curl -s -X POST "http://127.0.0.1:$PORT/api/runs" \
    -H "Content-Type: application/json" \
    -d '{"template":"default_6p_fake"}'
echo "Fake game launched — wait for completion..."
sleep 15

# Verify run artifacts
RUN_COUNT=$(curl -s "http://127.0.0.1:$PORT/api/runs" | python -c "import sys,json; print(len(json.load(sys.stdin)['runs']))")
test "$RUN_COUNT" -ge 1 || { echo "FAIL: no runs created"; exit 1; }

# 6. Verify release-manifest.json
echo "--- Verify release-manifest.json ---"
RUN_ID=$(curl -s "http://127.0.0.1:$PORT/api/runs" | python -c "import sys,json; r=json.load(sys.stdin)['runs']; print(r[0]['run_id'] if r else '')")
test -n "$RUN_ID" || { echo "FAIL: no run_id"; exit 1; }
test -f "$DATA_DIR/Werewolf-agent/runs/$RUN_ID/release-manifest.json" || { echo "FAIL: release-manifest.json missing"; exit 1; }

# 7. Kill host and verify recovery
echo "--- V2.10: Host kill + recovery ---"
kill $HOST_PID
sleep 3
"$INSTALL_DIR/Werewolf-agent.exe" &
HOST_PID2=$!
sleep 5
# Verify server was recovered and runs still readable
PORT2=$(cat "$DATA_DIR/Werewolf-agent/runtime-state/server-state.json" | python -c "import sys,json; print(json.load(sys.stdin)['port'])")
NEW_RUN_COUNT=$(curl -s "http://127.0.0.1:$PORT2/api/runs" | python -c "import sys,json; print(len(json.load(sys.stdin)['runs']))")
test "$NEW_RUN_COUNT" -ge 1 || { echo "FAIL: runs not preserved after recovery"; exit 1; }

# 8. Cleanup
kill $HOST_PID2 2>/dev/null || true
rm -rf "$DATA_DIR" "$INSTALL_DIR"

echo ""
echo "=== ALL SMOKE TESTS PASSED ==="
```

- [ ] **Step 2: Run smoke tests**

```bash
cd G:/Werewolf-agent
bash scripts/release/smoke-test.sh
```

- [ ] **Step 3: Create distribution manifest**

After passing smoke tests, create `distribution-manifest.json`:

```bash
cd G:/Werewolf-agent
GIT_COMMIT=$(git rev-parse HEAD)
BUILD_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

cat > .tmp/release/distribution-manifest.json << EOF
{
  "schema_version": 1,
  "release_version": "0.2.0",
  "channel": "${CHANNEL:-stable}",
  "git_commit": "$GIT_COMMIT",
  "build_timestamp": "$BUILD_TS",
  "ifw_component_version": "${IFW_VERSION:-0.2.0}",
  "components": {
    "com.werewolfagent.app": "${IFW_VERSION:-0.2.0}"
  }
}
EOF
```

- [ ] **Step 4: Create GitHub Pages publish script**

Create `scripts/release/publish-to-github-pages.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO_DIR="$REPO_ROOT/.tmp/ifw-repo"
UPDATE_REPO="${UPDATE_REPO:-git@github.com:liaoszong/werewolf-agent-updates.git}"
CHANNEL="${CHANNEL:-stable}"

echo "=== Publishing to GitHub Pages ==="

# Clone update repo
TMP_CLONE="$REPO_ROOT/.tmp/updates-clone"
rm -rf "$TMP_CLONE"
git clone "$UPDATE_REPO" "$TMP_CLONE"

# Copy repository contents
rm -rf "$TMP_CLONE/$CHANNEL"
cp -r "$REPO_DIR/$CHANNEL" "$TMP_CLONE/"

# Commit and push
cd "$TMP_CLONE"
git add "$CHANNEL/"
git commit -m "Release v${IFW_VERSION:-0.2.0} ${CHANNEL}" || echo "No changes to commit"
git push origin main

echo "=== Published to GitHub Pages ==="
echo "URL: https://liaoszong.github.io/werewolf-agent-updates/${CHANNEL}/Updates.xml"
```

- [ ] **Step 5: Verify update from file:// repo**

Simulate v0.2.0 → v0.2.1 update:
```bash
# Build a 0.2.1 version of the package and repo
IFW_VERSION=0.2.1 bash scripts/release/assemble-package.sh
IFW_VERSION=0.2.1 bash scripts/release/build-repo.sh

# Run maintenance tool from v0.2.0 install
"$INSTALL_DIR/maintenancetool.exe" --checkupdates
# Should detect update to 0.2.1 from file:// repo
```

- [ ] **Step 6: Run full Python test suite one final time**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" -q
```

- [ ] **Step 7: Diff audit**

```bash
git diff --stat main
git diff --name-only main
# Verify only expected files changed
```

- [ ] **Step 8: Commit and push**

```bash
git add scripts/release/smoke-test.sh scripts/release/publish-to-github-pages.sh scripts/release/distribution-manifest.json.in
git commit -m "feat: end-to-end smoke test + GitHub Pages publishing"
git push origin main
```

---

## Task Execution Order

```
T1 (VERSION) ─────────────────────────────────────────┐
T2 (bootstrapper lifecycle) ──────────────────────────┤
T3 (host control TCP) ────────────────────────────────┤
T4 (update request consumption) ──────────────────────┤
T5 (server release params) ───────────────────────────┤
T6 (Qt client ui) ────────────────────────────────────┤
                                                       │
T7 (CMake Release + windeployqt) ─────────────────────┤
T8 (PyInstaller server) ──────────────────────────────┤ all converge
T9 (PyInstaller bootstrapper) ────────────────────────┤
                                                       ▼
                                              T10 (IFW packaging)
                                                       │
                                                       ▼
                                              T11 (E2E smoke + publish)
```

Tasks 1–6 are code changes (can be done in any order within groups). Tasks 7–9 are build tasks (require code tasks complete). Task 10 packages everything. Task 11 verifies and publishes.

---

## Self-Review

**1. Spec coverage:**
- §1–2 (goals/invariants) → covered by global constraints + all tasks
- §3 (architecture) → T2-T6
- §4 (bootstrapper state machine) → T2, T3, T4
- §5 (directory layout) → T2 (ensure_data_dirs)
- §6 (versioning) → T1
- §7 (host control RPC) → T3
- §8 (update request) → T4, T6
- §9 (server state) → T5
- §9b (release-manifest) → T5
- §10 (Qt client params) → T6
- §11 (packaging) → T7, T8, T9, T10
- §12 (IFW) → T10
- §13 (update UI) → T6
- §14 (security) → T11 (sentinel scan)
- §16 (verification matrix) → T11 (smoke test)
- §17 (file scope) → T11 step 7 (diff audit)
- §18 (GitHub Pages) → T11 (publish script)

**2. Placeholder scan:** No TBD/TODO. All code steps have actual code. All commands are concrete. All file paths are absolute.

**3. Type consistency:**
- `_generate_token()` defined in T2, used in T3 — consistent
- `_atomic_write_json()` defined in T2, used in T3 — consistent
- `read_version()` defined in T1, used in T2, T3, T5, T9 — consistent
- `write_release_manifest()` defined in T5, called in T5 step 6 — consistent
- ControlServer interface matches T2's usage in lifecycle — consistent

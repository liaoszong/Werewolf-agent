"""One-click launcher for the Werewolf Theater.

Starts the local observer server (if not already running), creates a fake match and
waits for it to finish, then opens the Qt client straight into that run's Theater view
(via the client's --open-run flag).  Close the client window to stop the launcher.

Double-click ``launch-theater.bat`` (which runs this), or run ``python launch-theater.py``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"

# Qt 6.10 mingw toolchain on F: (matches this project's build setup).
QT_BIN = r"F:\Qt\6.10.0\mingw_64\bin"
MINGW_BIN = r"F:\Qt\Tools\mingw1310_64\bin"
CMAKE = r"F:\Qt\Tools\CMake_64\bin\cmake.exe"
EXE = os.path.join(ROOT, ".tmp", "qt-observer-build", "appqt_observer.exe")


def _get(path: str, timeout: float = 2.0):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(path: str, body: dict, timeout: float = 10.0):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _healthy() -> bool:
    try:
        _get("/health", timeout=1)
        return True
    except Exception:
        return False


def _server_is_current() -> bool:
    """A reused server is only safe if it matches what THIS launcher starts:
    current backend code AND live enabled. Two failure modes this catches:
      - older code: serves a profile schema WITHOUT ``provider_specs`` (the
        multi-provider preset feature) → client provider list renders empty.
      - started without ``--allow-live-api``: capabilities report
        ``live_api.enabled == False`` → the client's LIVE control is stuck on
        ``live_api_disabled`` and no real-AI game can launch.
    Either → treat as stale and restart."""
    try:
        schema = _get("/api/profiles/schema", timeout=2)
        if not schema.get("provider_specs"):
            return False
        caps = _get("/api/runtime/capabilities", timeout=2)
        return bool(caps.get("live_api", {}).get("enabled"))
    except Exception:
        return False


def _kill_server_on_port(port: int) -> None:
    """Best-effort stop of whatever is LISTENING on ``port`` — a stale observer
    server this launcher did not start (so we have no handle to it). Windows uses
    netstat+taskkill; POSIX falls back to pkill by module name. Failures are
    swallowed: the worst case is the start-below times out with a clear message."""
    try:
        if os.name == "nt":
            out = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True, text=True,
            ).stdout
            pids = set()
            for line in out.splitlines():
                if f":{port} " in line and "LISTENING" in line.upper():
                    pids.add(line.split()[-1])
            for pid in pids:
                if pid.isdigit() and pid != "0":
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "run_observer_server"], capture_output=True)
    except Exception:
        pass


def main() -> None:
    os.chdir(ROOT)
    env = dict(os.environ)
    env["PYTHONPATH"] = "src" + os.pathsep + env.get("PYTHONPATH", "")
    qt_env = dict(env)
    qt_env["PATH"] = QT_BIN + os.pathsep + MINGW_BIN + os.pathsep + qt_env.get("PATH", "")

    # Always (incrementally) rebuild so the latest code is used — fast when up to date.
    cache = os.path.join(".tmp", "qt-observer-build", "CMakeCache.txt")
    if not os.path.exists(cache):
        print("[*] 首次配置构建目录…")
        subprocess.run([CMAKE, "-S", "clients/qt_observer", "-B", ".tmp/qt-observer-build",
                        "-DCMAKE_BUILD_TYPE=Debug"], env=qt_env)
    print("[*] 构建/更新客户端（确保用上最新代码，已是最新则很快）…")
    subprocess.run([CMAKE, "--build", ".tmp/qt-observer-build", "--target", "appqt_observer"],
                   env=qt_env)
    if not os.path.exists(EXE):
        print("!! 客户端构建失败，请检查脚本顶部的 Qt 工具链路径（QT_BIN / CMAKE）。")
        input("按回车退出…")
        return

    server = None
    if _healthy() and not _server_is_current():
        # A leftover server from OLDER backend code answers /health but serves a
        # stale schema (no provider_specs) → the client's provider list is empty.
        # Don't blindly reuse it: stop it so a fresh one (current code) starts.
        print("[!] 检测到陈旧的服务器（缺少 provider_specs 能力），正在停止并重启…")
        _kill_server_on_port(PORT)
        for _ in range(20):          # wait for the port to free up
            if not _healthy():
                break
            time.sleep(0.25)

    if _healthy():
        print("[*] 检测到已在运行的服务器（版本匹配），直接复用。")
    else:
        print("[*] 启动观察者服务器…")
        server = subprocess.Popen(
            [sys.executable, "-m", "werewolf_eval.run_observer_server",
             "--host", "127.0.0.1", "--port", str(PORT), "--runs-dir", ".runs",
             # Enable the live (real-AI) path so the client's LIVE control works.
             # Spending is still gated client-side (two-click arming + BYO-key);
             # the server only needs a client-synced key to actually launch live.
             "--allow-live-api"],
            env=env)
        for _ in range(60):
            if _healthy():
                break
            time.sleep(0.5)
        else:
            print("!! 服务器启动超时。")
            if server:
                server.terminate()
            input("按回车退出…")
            return

    try:
        print("[*] 创建一局 fake 对局…")
        run = _post("/api/runs", {"template": "default_6p_fake", "mode": "fake"})
        run_id = str(run.get("run_id", ""))
        if not run_id:
            print("!! 未能创建对局。")
            return
        print(f"[*] 对局 {run_id} 运行中，等待收口（写出 game-log.json）…")
        status = ""
        for _ in range(80):
            try:
                detail = _get(f"/api/runs/{run_id}", timeout=2)
                status = str(detail.get("status", ""))
                if status in ("completed", "failed"):
                    break
            except Exception:
                pass
            time.sleep(0.4)
        print(f"[*] 对局就绪：{run_id}（{status or '?'}）")
        print("[*] 打开剧场……（关闭客户端窗口即可退出本启动器）")
        subprocess.run([EXE, "--observer-base-url", BASE, "--open-run", run_id], env=qt_env)
    finally:
        if server is not None:
            print("[*] 关闭本启动器启动的服务器。")
            server.terminate()


if __name__ == "__main__":
    main()

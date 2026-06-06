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


def main() -> None:
    os.chdir(ROOT)
    env = dict(os.environ)
    env["PYTHONPATH"] = "src" + os.pathsep + env.get("PYTHONPATH", "")
    qt_env = dict(env)
    qt_env["PATH"] = QT_BIN + os.pathsep + MINGW_BIN + os.pathsep + qt_env.get("PATH", "")

    # Build the client once if it isn't there yet.
    if not os.path.exists(EXE):
        print("[*] 首次构建客户端（较慢，请稍候）…")
        subprocess.run([CMAKE, "--build", ".tmp/qt-observer-build", "--target", "appqt_observer"],
                       env=qt_env)
    if not os.path.exists(EXE):
        print("!! 找不到客户端可执行文件，请先成功构建一次：")
        print("   cmake -S clients/qt_observer -B .tmp/qt-observer-build -DCMAKE_BUILD_TYPE=Debug")
        print("   cmake --build .tmp/qt-observer-build")
        input("按回车退出…")
        return

    server = None
    if _healthy():
        print("[*] 检测到已在运行的服务器，直接复用。")
    else:
        print("[*] 启动观察者服务器…")
        server = subprocess.Popen(
            [sys.executable, "-m", "werewolf_eval.run_observer_server",
             "--host", "127.0.0.1", "--port", str(PORT), "--runs-dir", ".runs"],
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

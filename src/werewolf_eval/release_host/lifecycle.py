"""Bootstrapper lifecycle: data dirs, server startup, client launch, shutdown."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Callable, Tuple

from werewolf_eval.release_metadata import read_version


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
        health_token = health.get("owner_token")
        if health_token is not None and health_token != state.get("owner_token"):
            return None, None
        return state_file, state
    except Exception:
        # Stale: server dead but state file remains
        state_file.unlink(missing_ok=True)
        return None, None


def _observer_server_exe(dist_root: Path) -> Path:
    nested = dist_root / "runtime" / "observer-server" / "observer-server.exe"
    if nested.exists():
        return nested
    return dist_root / "runtime" / "observer-server.exe"


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
    server_exe = _observer_server_exe(dist_root)
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


def spawn_client(
    client_exe: Path,
    observer_port: int,
    host_session_id: str,
    release_version: str,
    update_session_id: str,
    update_session_token: str,
    update_control_port: int,
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
        "--update-session-id", update_session_id,
        "--update-session-token", update_session_token,
        "--update-control-port", str(update_control_port),
    ], env=env)


def _has_active_runs(port: int) -> bool:
    try:
        import urllib.request
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        resp = opener.open(f"http://127.0.0.1:{port}/api/runs", timeout=3)
        runs_data = json.loads(resp.read().decode("utf-8"))
        return any(
            r.get("status") in ("queued", "running")
            for r in runs_data.get("runs", [])
        )
    except Exception:
        return False


def _stop_owned_server(server_proc: subprocess.Popen | None) -> None:
    if server_proc is not None:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_proc.kill()


def _test_update_source_allowed(environ: dict[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return env.get("WEREWOLF_ALLOW_VELOPACK_TEST_SOURCE") == "1"


def release_host_main() -> int:
    """CLI entry for Werewolf-agent.exe."""
    import argparse
    parser = argparse.ArgumentParser(description="Werewolf-agent")
    parser.add_argument("--version", action="version",
                        version=f"Werewolf-agent {read_version()}")
    parser.add_argument("--velopack-test-update-source", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.velopack_test_update_source and not _test_update_source_allowed():
        print("FATAL: Velopack test update source is disabled in this build context", file=sys.stderr)
        return 2

    dist_root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent.parent.parent
    data_root = ensure_data_dirs()

    from werewolf_eval.release_host.control import ControlServer, send_open_client_request
    from werewolf_eval.release_host.update_control import (
        UpdateControlServer,
        VelopackUpdateBackend,
        create_update_source_factory,
        new_update_session,
    )

    # Windows named mutex for single-instance enforcement (R0 M-1)
    if not _acquire_host_mutex():
        # Did not acquire mutex — another instance may exist
        # Fall through to file-guided IPC check
        hc_path = data_root / "runtime-state" / "host-control.json"
        if hc_path.exists():
            result = send_open_client_request(hc_path)
            if result in ("foregrounded", "client_started"):
                print(f"Existing instance found — {result}")
                return 0
            # Stale host-control — clean up and become primary
            hc_path.unlink(missing_ok=True)

    host_session_id = uuid.uuid4().hex

    print(f"Werewolf-agent {read_version()} starting")
    print(f"Data: {data_root}")

    with ControlServer(data_root, host_session_id, read_version()) as cs:
        try:
            server_proc, port, owner_token, _ = find_or_start_server(data_root, dist_root)
        except RuntimeError as exc:
            print(f"FATAL: {exc}", file=sys.stderr)
            return 1

        update_session_id, update_session_token = new_update_session()
        try:
            update_source_factory = create_update_source_factory(
                test_update_source=args.velopack_test_update_source,
            )
            update_backend = VelopackUpdateBackend(update_source_factory)
        except Exception as exc:
            print(f"FATAL: invalid update source: {exc.__class__.__name__}", file=sys.stderr)
            _stop_owned_server(server_proc)
            return 1
        with UpdateControlServer(
            backend=update_backend,
            active_run_checker=lambda: _has_active_runs(port),
            session_id=update_session_id,
            session_token=update_session_token,
        ) as update_control:
            client_exe = dist_root / "app" / "appqt_observer.exe"

            client_proc = spawn_client(
                client_exe, port, host_session_id,
                read_version(),
                update_session_id, update_session_token, update_control.port,
            )

            # Wait for client to exit
            client_proc.wait()

            if update_control.apply_requested:
                _stop_owned_server(server_proc)
                return 0

            # --- Shutdown logic ---
            has_active = _has_active_runs(port)

            if has_active:
                print("Active runs exist — keeping server alive. Reopen app to continue watching.")
                # Idle cleanup loop (30s grace after all runs finish)
                _idle_cleanup_loop(
                    port, data_root, dist_root, host_session_id, cs,
                    update_session_id, update_session_token, update_control.port,
                    lambda: update_control.apply_requested,
                )
                _stop_owned_server(server_proc)
                return 0

        _stop_owned_server(server_proc)
        return 0


def _idle_cleanup_loop(
    port: int,
    data_root: Path,
    dist_root: Path,
    host_session_id: str,
    cs: ControlServer,
    update_session_id: str,
    update_session_token: str,
    update_control_port: int,
    apply_requested: Callable[[], bool],
) -> None:
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

        # Check for reopen signal from control server (in-memory, no JSON race)
        if cs.check_and_clear_pending_reopen():
            client_exe = dist_root / "app" / "appqt_observer.exe"
            client_proc = spawn_client(
                client_exe, port, host_session_id, read_version(),
                update_session_id, update_session_token, update_control_port,
            )
            client_proc.wait()
            if apply_requested():
                break
            all_terminal_at = None
            continue

        if time.monotonic() - all_terminal_at > grace_seconds:
            break


def _acquire_host_mutex() -> bool:
    """Try to acquire the per-user Windows named mutex. Returns True if acquired (first instance)."""
    import ctypes
    mutex_name = f"Global\\WerewolfAgentHost-{os.environ.get('USERNAME', 'default')}"
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, mutex_name)
    if handle == 0:
        return False  # Failed to create — fall back to file-guided approach
    last_error = kernel32.GetLastError()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return False  # Another instance holds the mutex
    import atexit
    atexit.register(kernel32.CloseHandle, handle)
    return True

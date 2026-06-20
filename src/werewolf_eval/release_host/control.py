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

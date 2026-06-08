"""One-shot REAL live-game verifier: 6 seats all DeepSeek.

Runs a genuine live game (real DeepSeek API calls — costs a little money) through
the SAME server path the Qt client uses, then prints an honest report from the
on-disk artifacts (per-seat provider/model, live success count, tokens, winner).

The API key is read ONLY from the DEEPSEEK_API_KEY environment variable and is
sent only to your own localhost server. It is never written to disk or printed.

Usage (run in YOUR terminal, where your key lives):

    # Windows cmd:
    set DEEPSEEK_API_KEY=sk-your-key-here
    set PYTHONPATH=src
    python tools/live_check_deepseek.py

    # bash:
    DEEPSEEK_API_KEY=sk-... PYTHONPATH=src python tools/live_check_deepseek.py

Then paste the printed report back.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

PORT = 8790
BASE = f"http://127.0.0.1:{PORT}"
MODEL = "deepseek-chat"   # a real, validatable DeepSeek model
ROOT = Path(__file__).resolve().parents[1]


def _req(method: str, path: str, body: dict | None = None, timeout: float = 10.0):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _healthy() -> bool:
    try:
        urllib.request.urlopen(BASE + "/health", timeout=1)
        return True
    except Exception:
        return False


def _live_profile() -> dict:
    sys.path.insert(0, str(ROOT / "src"))
    from werewolf_eval.profile_config import PROFILE_SCHEMA_VERSION
    seat = {"provider": "deepseek", "model": MODEL, "prompt": "", "strategy": "default"}
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "name": "live_check_all_deepseek",
        "template": "default_6p_fake",   # template = seat→role map; mode=live is separate
        "role_defaults": {r: dict(seat) for r in ("werewolf", "seer", "witch", "villager")},
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # readable CN output on Windows cmd
    except Exception:
        pass
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("!! DEEPSEEK_API_KEY 没设置。请先在本终端 set DEEPSEEK_API_KEY=你的key 再运行。")
        return 2

    runs_dir = Path(tempfile.mkdtemp(prefix="live_check_runs_"))
    env = dict(os.environ)
    env["PYTHONPATH"] = "src" + os.pathsep + env.get("PYTHONPATH", "")

    if _healthy():
        print(f"!! 端口 {PORT} 已被占用,先停掉它再跑(本脚本要起自己的临时 server)。")
        return 2

    print(f"[*] 启动临时 live server(--allow-live-api, runs-dir={runs_dir})…")
    server = subprocess.Popen(
        [sys.executable, "-m", "werewolf_eval.run_observer_server",
         "--host", "127.0.0.1", "--port", str(PORT),
         "--runs-dir", str(runs_dir), "--allow-live-api"],
        env=env, cwd=str(ROOT),
    )
    try:
        for _ in range(60):
            if _healthy():
                break
            time.sleep(0.5)
        else:
            print("!! server 启动超时。")
            return 1

        # 1) sync the deepseek credential (key from env → localhost only)
        print("[*] 同步 deepseek 凭证到本地 server…")
        st, _ = _req("POST", "/api/credentials", {"provider": "deepseek", "api_key": key})
        if st != 200:
            print(f"!! 凭证写入失败: HTTP {st}")
            return 1

        # 2) sanity: capabilities should now report deepseek available
        _, caps = _req("GET", "/api/runtime/capabilities")
        ds = caps.get("live_api", {}).get("providers", {}).get("deepseek", {})
        print(f"[*] capabilities: deepseek.available = {ds.get('available')}")

        # 3) launch a REAL live game (6 seats all deepseek)
        print(f"[*] 启动真实 live 对局(6 座位全 deepseek / {MODEL})…")
        st, run = _req("POST", "/api/runs", {"profile": _live_profile(), "mode": "live"})
        if st not in (200, 202):
            print(f"!! 启动失败: HTTP {st} -> {run}")
            return 1
        run_id = str(run.get("run_id", ""))
        print(f"[*] run_id = {run_id} — 跑起来了,等待收口(真实 API 调用中)…")

        # 4) poll to completion
        status = ""
        for _ in range(240):  # up to ~4 min
            try:
                _, detail = _req("GET", f"/api/runs/{run_id}", timeout=4)
                status = str(detail.get("status", ""))
                if status in ("completed", "failed"):
                    break
            except Exception:
                pass
            time.sleep(1.0)
        print(f"[*] 对局结束,status = {status or '?'}")

        # 5) honest report from on-disk artifacts
        rd = runs_dir / run_id
        print("\n================ 真实战报 ================")
        print(f"run dir: {rd}")
        gl = rd / "game-log.json"
        if gl.exists():
            g = json.loads(gl.read_text(encoding="utf-8"))
            print(f"source_label : {g.get('source_label')}")
            print(f"winner       : {g.get('winner') or g.get('result') or g.get('outcome')}")
        live_success = 0
        pt = rd / "provider-turns.json"
        if pt.exists():
            p = json.loads(pt.read_text(encoding="utf-8"))
            summary = {k: v for k, v in p.items() if k != "turns"}
            live_success = int(summary.get("live_success_actions", 0))
            print(f"\nlive 汇总    : {json.dumps(summary, ensure_ascii=False)}")
        else:
            print("!! 没找到 provider-turns.json —— 可能根本没走到 live。")

        # per-seat provider/model identity — the authoritative source is the
        # prompt manifest (one row per seat), NOT the per-turn log.
        mf = rd / "prompt-manifest.json"
        if mf.exists():
            agents = json.loads(mf.read_text(encoding="utf-8")).get("agents", [])
            print("\n每座位真实身份(provider / model):")
            for a in sorted(agents, key=lambda x: x.get("player_id", "")):
                print(f"  {a.get('player_id')}: {a.get('provider')} / {a.get('model')}")

        # honest verdict — 'completed' alone does NOT mean live worked: a bad key
        # still completes via deterministic fallback. The real signal is whether
        # any live API call actually succeeded.
        ok = (status == "completed" and live_success > 0)
        print("\n判定: " + (
            f"✅ 真实 live 成功 —— {live_success} 次 DeepSeek 调用真正返回。"
            if ok else
            f"❌ live 未成功(live_success_actions={live_success})。"
            " 对局可能靠确定性兜底跑完了,但没有真实 AI 输出 —— 检查 key 是否有效/有余额。"
        ))
        print("=========================================\n")
        return 0 if ok else 1
    finally:
        server.terminate()
        print("[*] 已关闭临时 server。")


if __name__ == "__main__":
    raise SystemExit(main())

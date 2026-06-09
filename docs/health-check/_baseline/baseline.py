#!/usr/bin/env python3
"""Read-only health-check baseline. Writes only into its own _baseline/ dir."""
import re, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[3]   # repo root
OUT  = pathlib.Path(__file__).resolve().parent
def tracked(*globs):
    out = subprocess.run(["git","ls-files",*globs], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return [ROOT / p for p in out]

# --- import-refs: 每个 src 模块被多少 src/tests/scripts/tools 文件引用 ---
src_mods = [p.stem for p in tracked("src/werewolf_eval/*.py") if p.stem != "__init__"]
scan = tracked("src/werewolf_eval/*.py","tests/*.py","scripts/**/*.py","tools/*.py") + [ROOT/"launch-theater.py"]
texts = {p: p.read_text(encoding="utf-8", errors="ignore") for p in scan if p.exists()}
rows = []
for m in src_mods:
    pat = re.compile(rf"(import\s+\w*\b{m}\b|from\s+\S*\b{m}\b\s+import|werewolf_eval\.{m}\b|[\"']{m}[\"'])")
    refs = sum(1 for p,t in texts.items() if p.stem != m and pat.search(t))
    rows.append((refs, m))
(OUT/"import-refs.txt").write_text(
    "\n".join(f"{r:3d}  {m}" for r,m in sorted(rows)), encoding="utf-8")

# --- entrypoint wiring: 10 个 run_* 被哪些 launcher/doc/test 提到 ---
entry = ["run_mock_game","run_scripted_game","run_fake_provider_game","run_g1h_fake_runtime",
         "run_emergent_game","run_emergent_fake_runtime","run_deepseek_consensus_game",
         "run_deepseek_provider_game","run_emergent_deepseek_game","run_observer_server"]
wire_scan = tracked("*.py","*.bat","*.md","scripts/**/*.py","tools/*.py","tests/*.py","docs/**/*.md")
wtext = {p: p.read_text(encoding="utf-8", errors="ignore") for p in wire_scan if p.exists()}
lines = []
for e in entry:
    hits = [str(p.relative_to(ROOT)) for p,t in wtext.items()
            if p.name != f"{e}.py" and e in t]
    lines.append(f"=== {e} ({len(hits)} refs) ===\n  " + "\n  ".join(hits) if hits
                 else f"=== {e} (0 refs) ===  <-- STRONG DEAD CANDIDATE")
(OUT/"entrypoint-wiring.txt").write_text("\n".join(lines), encoding="utf-8")

# --- doc-refs: 每个 .md 被多少其它 md/py/json 引用(找孤儿文档) ---
mds = tracked("*.md","docs/**/*.md")
allscan = tracked("*.md","docs/**/*.md","*.py","src/**/*.py","tests/*.py","scripts/**/*.py","*.json","docs/**/*.json")
atext = {p: p.read_text(encoding="utf-8", errors="ignore") for p in allscan if p.exists()}
drows = []
for f in mds:
    base = f.name
    refs = sum(1 for p,t in atext.items() if p != f and base in t)
    drows.append((refs, str(f.relative_to(ROOT))))
(OUT/"doc-refs.txt").write_text(
    "\n".join(f"{r:3d}  {f}" for r,f in sorted(drows)), encoding="utf-8")

# --- bigfiles: src 模块行数倒序(职责过载候选) ---
bf = sorted(((len(p.read_text(encoding='utf-8',errors='ignore').splitlines()), p.stem)
             for p in tracked("src/werewolf_eval/*.py")), reverse=True)
(OUT/"bigfiles.txt").write_text(
    "\n".join(f"{n:5d}  {m}" for n,m in bf), encoding="utf-8")
print("baseline written to", OUT)

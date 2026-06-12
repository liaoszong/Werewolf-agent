# B-4 Observer Visibility Layering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `src/werewolf_eval/observer_visibility.py` (~935 LOC, three mixed concerns) into `observer_trust_index.py` / `observer_projection.py` / `observer_enrichment.py` behind a pure facade, byte-identical in behavior, per ADR `docs/adr/2026-06-11-observer-visibility-layering.md`.

**Architecture:** Verbatim function moves only — bodies do not change, only module docstrings and `import` lines. Provenance is *assigned* only in `observer_trust_index`, *consumed* only in `observer_projection`; `observer_enrichment` joins artifacts onto already-filtered events. `observer_visibility.py` becomes a re-export facade so all 7 external reference sites stay zero-change. The SYS-A4 witness sentinel widens to scan the three new modules.

**Tech Stack:** stdlib Python, unittest. Base: worktree `b4-observer-visibility-layering` @ main `03490de` (baseline: 1187 tests OK, skipped=2).

**Invariants (hard, from user + ADR):**
1. No new module may import or even *mention the name of* the engine-side single-source module (B-2). NOTE: the sentinel is a **string scan** for that module's name across witness files — docstrings/comments in the four observer files must refer to it only as "the engine-side single source (B-2 ADR)", never by filename. NOTE: the sentinel TEST's own path contains that module name as a substring — witness docstrings must not name the test file either; say "the witness-boundary sentinel test".
2. Envelope bytes identical pre/post (Task 1 / Task 6 oracle).
3. Zero changes to: `observer/handler.py`, `invariants/visibility_oracle.py`, `tests/test_observer_visibility.py`, `tests/test_visibility_parity.py`, `tests/test_observer_emergent_bridge.py`, `tests/test_emergent_role_projection.py`, `tests/test_role_single_source.py`.
4. Forbidden scope: prompt renderers, `emergent_engine.py`, `game_engine.py`, `scoring.py`, deepseek launcher / live entry (T17 running), `.github/**`, fixtures.

**Allowlist (complete file set this track may touch):**
- Create: `docs/adr/2026-06-11-observer-visibility-layering.md`, `docs/harness/plans/2026-06-11--b4-observer-visibility-layering-plan.md` (this file), `src/werewolf_eval/observer_trust_index.py`, `src/werewolf_eval/observer_projection.py`, `src/werewolf_eval/observer_enrichment.py`
- Modify: `src/werewolf_eval/observer_visibility.py` (→ facade), `tests/test_role_visibility.py` (sentinel witness list only), `src/werewolf_eval/role_visibility.py` (docstring only), `.oh-my-harness/tree.md` (hook regen)

All line numbers below refer to `src/werewolf_eval/observer_visibility.py` at `03490de`.

---

### Task 0: Gate — user approves ADR; commit ADR + plan

- [ ] **Step 1:** User has reviewed the ADR (posted in chat). On approval, flip ADR `Status:` line to `Accepted (user-approved health-check item B-4, 2026-06-11)`.
- [ ] **Step 2:** Pre-commit checks (shared-tree discipline, applies to every commit below):

```bash
git branch --show-current   # must be worktree-b4-observer-visibility-layering
git status --short          # no staged items outside this task
```

- [ ] **Step 3: Commit**

```bash
git add docs/adr/2026-06-11-observer-visibility-layering.md docs/harness/plans/2026-06-11--b4-observer-visibility-layering-plan.md
git commit -m "docs(adr+plan): B-4 observer visibility layering — trust-index / projection / enrichment, trust boundary as single audited surface"
```

### Task 1: Byte oracle — pre-refactor envelope snapshot

**Files:** none committed (everything under `.tmp/b4-oracle/`, gitignored).

- [ ] **Step 1: Generate two deterministic fake run dirs** (events.jsonl has per-run ts/UUIDs — that is fine, the SAME run dirs are reused in Task 6):

```bash
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --game-id b4_oracle_v --out-dir .tmp/b4-oracle/villager_win --script villager_win --seed 0
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.run_emergent_fake_runtime --game-id b4_oracle_w --out-dir .tmp/b4-oracle/werewolf_win --script werewolf_win --seed 0
```

- [ ] **Step 2: Write the oracle script** `.tmp/b4-oracle/snapshot.py`:

```python
"""Dump canonical-JSON projection envelopes for every perspective (B-4 byte gate)."""
import json, sys
from pathlib import Path

from werewolf_eval.observer_visibility import build_projection_envelope
from werewolf_eval.runtime_events import read_events_jsonl

PERSPECTIVES = ["god", "public", "team:werewolf"] + [f"role:p{i}" for i in range(1, 7)]

out_dir = Path(sys.argv[1])  # e.g. .tmp/b4-oracle/pre
out_dir.mkdir(parents=True, exist_ok=True)
for run_dir in [Path(".tmp/b4-oracle/villager_win"), Path(".tmp/b4-oracle/werewolf_win")]:
    events = read_events_jsonl(run_dir / "events.jsonl")
    for p in PERSPECTIVES:
        env = build_projection_envelope(run_dir=run_dir, run_id=run_dir.name, perspective=p, events=events)
        name = f"{run_dir.name}--{p.replace(':', '_')}.json"
        (out_dir / name).write_text(json.dumps(env, sort_keys=True, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote {len(PERSPECTIVES) * 2} envelopes to {out_dir}")
```

(If `read_events_jsonl` has a different signature, mirror exactly how `observer/handler.py` loads events for `/projection` — the oracle must feed `build_projection_envelope` the same way the server does.)

- [ ] **Step 3: Snapshot PRE state:**

```bash
NO_PROXY='*' PYTHONPATH=src python .tmp/b4-oracle/snapshot.py .tmp/b4-oracle/pre
```

Expected: `wrote 18 envelopes to .tmp/b4-oracle/pre`

### Task 2: Extract `observer_trust_index.py` (provenance assignment)

**Files:**
- Create: `src/werewolf_eval/observer_trust_index.py`
- Modify: `src/werewolf_eval/observer_visibility.py`

- [ ] **Step 1: Create the module.** Header:

```python
"""Observer-side trust-source resolution (B-4 layering, ADR 2026-06-11).

The ONLY module that ASSIGNS provenance: which artifact (a player's own
role_projection snapshot vs a god snapshot vs nothing) backs each seat's
role / team / alive / projected_known_roles. Enforcement of these tags lives in
observer_projection; this module imports no sibling visibility module.

Part of the SYS-A4 observer-side witness: must stay independent of the
engine-side single source (B-2 ADR); enforced by the witness-boundary sentinel test.
"""

from __future__ import annotations

import json
from pathlib import Path
```

Then move **verbatim**: `_SNAPSHOTS_DIR = "snapshots"` (L35), the `_PHASE_RANK` block + `_snap_order` (L100-121), `build_seat_role_index` (L123-284), `_find_player_role_in_god_snaps` (L287-297), `_find_player_team_in_god_snaps` (L300-310).

- [ ] **Step 2: Shrink `observer_visibility.py`:** delete the moved lines; add to its imports:

```python
from werewolf_eval.observer_trust_index import (
    _SNAPSHOTS_DIR,
    build_seat_role_index,
)
```

(`_SNAPSHOTS_DIR` is still needed by `project_snapshots` until Task 3 moves it.)

- [ ] **Step 3: Run gate tests**

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_observer_visibility.py tests/test_visibility_parity.py tests/test_role_visibility.py tests/test_role_single_source.py tests/test_emergent_role_projection.py tests/test_observer_emergent_bridge.py -q
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/werewolf_eval/observer_trust_index.py src/werewolf_eval/observer_visibility.py
git commit -m "refactor(b4): extract observer_trust_index — provenance assignment, verbatim move"
```

### Task 3: Extract `observer_projection.py` (provenance enforcement)

**Files:**
- Create: `src/werewolf_eval/observer_projection.py`
- Modify: `src/werewolf_eval/observer_visibility.py`

- [ ] **Step 1: Create the module.** Header:

```python
"""Observer-side perspective projection (B-4 layering, ADR 2026-06-11).

The ONLY module that CONSUMES provenance tags (``role_source`` / ``team_source``
/ ``alive_source`` assigned by observer_trust_index): perspective vocabulary,
player/event/snapshot projection, and the proof section. Auditing "what may a
non-god perspective expose" means reading observer_trust_index + this file.

Part of the SYS-A4 observer-side witness: must stay independent of the
engine-side single source (B-2 ADR); enforced by the witness-boundary sentinel test.
"""

from __future__ import annotations

import json
from pathlib import Path

# R-06: single source of truth for these visibility sets — import them from
# observer_protocol so the /events,/stream filter and the /projection filter can
# never drift apart (the duplicate frozensets were the contract-drift seam).
from werewolf_eval.observer_protocol import (
    KNOWN_ROLE_TEAMS as _KNOWN_ROLE_TEAMS,
    PUBLIC_EVENT_VISIBILITIES as PUBLIC_LIKE_EVENT_VISIBILITIES,
    WEREWOLF_TEAM_EVENT_VISIBILITIES,
)
from werewolf_eval.observer_trust_index import _SNAPSHOTS_DIR
```

Then move **verbatim**: constants + error (L28-33 `CONTRACT_VERSION`, `ROLE_PERSPECTIVE_PREFIX`, `DEFAULT_PLAYER_IDS`, `ROLE_SPECIFIC_EVENT_VISIBILITIES`; L40-41 `VisibilityProjectionError`), perspective helpers (L49-92: `perspective_kind`, `is_werewolf_role`, `infer_player_ids`, `unknown_player`), `build_player_projection` (L318-455), `event_visible_in_projection` (L463-520), `_trusted_role_for_player` / `_trusted_team_for_player` (L523-544), `project_events` (L547-580), `project_snapshots` (L588-695), `_snapshot_visible_to_projection` (L698-729), `_build_detail_endpoint` (L732-736), `_build_proof` (L892-935).

- [ ] **Step 2: Shrink `observer_visibility.py`:** delete moved lines (including the now-unneeded `observer_protocol` import block and the `_SNAPSHOTS_DIR` re-import from Task 2 if nothing left uses it); add:

```python
from werewolf_eval.observer_projection import (
    CONTRACT_VERSION,
    DEFAULT_PLAYER_IDS,
    PUBLIC_LIKE_EVENT_VISIBILITIES,
    ROLE_PERSPECTIVE_PREFIX,
    ROLE_SPECIFIC_EVENT_VISIBILITIES,
    WEREWOLF_TEAM_EVENT_VISIBILITIES,
    VisibilityProjectionError,
    _KNOWN_ROLE_TEAMS,
    _build_proof,
    build_player_projection,
    event_visible_in_projection,
    infer_player_ids,
    is_werewolf_role,
    perspective_kind,
    project_events,
    project_snapshots,
    unknown_player,
)
```

At this point `observer_visibility.py` = facade imports + the three enrichment functions.

- [ ] **Step 3: Run gate tests** (same command as Task 2 Step 3). Expected: all pass — especially `test_role_single_source.py::DerivedCopiesTest` (`observer_visibility._KNOWN_ROLE_TEAMS` identity survives the re-export chain).

- [ ] **Step 4: Commit**

```bash
git add src/werewolf_eval/observer_projection.py src/werewolf_eval/observer_visibility.py
git commit -m "refactor(b4): extract observer_projection — perspective enforcement, sole *_source reader, verbatim move"
```

### Task 4: Extract `observer_enrichment.py`; facade goes pure

**Files:**
- Create: `src/werewolf_eval/observer_enrichment.py`
- Modify: `src/werewolf_eval/observer_visibility.py` (final facade form)

- [ ] **Step 1: Create the module.** Header:

```python
"""Observer-side artifact join + projection envelope (B-4 layering, ADR 2026-06-11).

Joins game-log summaries and decision-log reasons onto ALREADY-FILTERED events
and assembles the /projection envelope. Must never read snapshots or provenance
tags directly; its only perspective-sensitive rule is the private
``reason_summary`` actor gate (god or the deciding player), which is an
actor-identity gate, not provenance.

Part of the SYS-A4 observer-side witness: must stay independent of the
engine-side single source (B-2 ADR); enforced by the witness-boundary sentinel test.
"""

from __future__ import annotations

import json
from pathlib import Path

from werewolf_eval.observer_projection import (
    CONTRACT_VERSION,
    ROLE_PERSPECTIVE_PREFIX,
    _build_proof,
    build_player_projection,
    perspective_kind,
    project_events,
    project_snapshots,
)
from werewolf_eval.observer_trust_index import build_seat_role_index
```

Then move **verbatim**: `_load_game_log_summaries` (L744-771), `_load_decision_reasons` (L774-823), `build_projection_envelope` (L826-889).

- [ ] **Step 2: Rewrite `observer_visibility.py` as the pure facade** (complete file content):

```python
"""G2c observer visibility facade (B-4 layering, ADR 2026-06-11).

Pure re-export surface — zero logic. The implementation is layered into:

* ``observer_trust_index``  — provenance ASSIGNMENT (which artifact backs each
  seat's role/team/alive; the trust source of truth),
* ``observer_projection``   — provenance ENFORCEMENT (what each perspective may
  see; the only reader of ``*_source`` tags),
* ``observer_enrichment``   — artifact join onto already-filtered events + the
  /projection envelope.

Auditing the anti-leak boundary = reading the first two modules. Importers keep
using this facade.

Part of the SYS-A4 observer-side witness: this facade and all three layered
modules must stay independent of the engine-side single source (B-2 ADR);
enforced by the witness-boundary sentinel test.
"""

from __future__ import annotations

from werewolf_eval.observer_enrichment import build_projection_envelope
from werewolf_eval.observer_projection import (
    CONTRACT_VERSION,
    DEFAULT_PLAYER_IDS,
    PUBLIC_LIKE_EVENT_VISIBILITIES,
    ROLE_PERSPECTIVE_PREFIX,
    ROLE_SPECIFIC_EVENT_VISIBILITIES,
    WEREWOLF_TEAM_EVENT_VISIBILITIES,
    VisibilityProjectionError,
    _KNOWN_ROLE_TEAMS,
    build_player_projection,
    event_visible_in_projection,
    infer_player_ids,
    is_werewolf_role,
    perspective_kind,
    project_events,
    project_snapshots,
    unknown_player,
)
from werewolf_eval.observer_trust_index import build_seat_role_index

__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_PLAYER_IDS",
    "PUBLIC_LIKE_EVENT_VISIBILITIES",
    "ROLE_PERSPECTIVE_PREFIX",
    "ROLE_SPECIFIC_EVENT_VISIBILITIES",
    "WEREWOLF_TEAM_EVENT_VISIBILITIES",
    "VisibilityProjectionError",
    "build_player_projection",
    "build_projection_envelope",
    "build_seat_role_index",
    "event_visible_in_projection",
    "infer_player_ids",
    "is_werewolf_role",
    "perspective_kind",
    "project_events",
    "project_snapshots",
    "unknown_player",
]
```

(`_KNOWN_ROLE_TEAMS` is deliberately imported but not in `__all__` — same as today: a private name external test code reaches via attribute access; `assertIs` identity holds because the re-export chain passes the same `observer_protocol.KNOWN_ROLE_TEAMS` object through.)

- [ ] **Step 3: Run gate tests** (same command as Task 2 Step 3), plus cold import:

```bash
NO_PROXY='*' PYTHONPATH=src python -c "import werewolf_eval.observer_visibility, werewolf_eval.observer_trust_index, werewolf_eval.observer_projection, werewolf_eval.observer_enrichment; print('cold import OK')"
```

- [ ] **Step 4: Commit**

```bash
git add src/werewolf_eval/observer_enrichment.py src/werewolf_eval/observer_visibility.py
git commit -m "refactor(b4): extract observer_enrichment; observer_visibility becomes pure facade, importer surface zero-change"
```

### Task 5: Widen the witness sentinel + engine-side docstring

**Files:**
- Modify: `tests/test_role_visibility.py` (witness list only)
- Modify: `src/werewolf_eval/role_visibility.py` (docstring only)

- [ ] **Step 1: Extend the sentinel** in `WitnessBoundarySentinelTest.test_observer_and_oracle_do_not_reference_role_visibility`:

```python
        witnesses = [
            src / "observer_visibility.py",
            src / "observer_trust_index.py",
            src / "observer_projection.py",
            src / "observer_enrichment.py",
            src / "observer_protocol.py",
            *sorted((src / "invariants").glob("*.py")),
        ]
```

- [ ] **Step 2: Update `role_visibility.py` docstring** witness paragraph (L13-16) to:

```
WITNESS BOUNDARY (do not widen): ``observer_visibility.py`` (facade) +
``observer_trust_index.py`` / ``observer_projection.py`` / ``observer_enrichment.py``
(B-4 layering) / ``observer_protocol.py`` and ``invariants/`` are deliberate
INDEPENDENT implementations (SYS-A4 dual witness / safety-net I4b
anti-circularity). They must never import this module —
``tests/test_role_visibility.py`` enforces that with a sentinel.
```

- [ ] **Step 3: Mutation check — prove the widened sentinel bites.** Append a comment containing the engine module's name to `observer_projection.py`, run the sentinel, expect FAIL naming `observer_projection.py`; then revert:

```bash
echo "# role_visibility" >> src/werewolf_eval/observer_projection.py
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_role_visibility.py -q   # expect 1 failed
git checkout -- src/werewolf_eval/observer_projection.py
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_role_visibility.py -q   # expect all pass
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_role_visibility.py src/werewolf_eval/role_visibility.py
git commit -m "test(b4): widen SYS-A4 witness sentinel to the three layered observer modules (mutation-verified)"
```

### Task 6: Byte gate + full suite + tree

- [ ] **Step 1: Snapshot POST state and byte-diff:**

```bash
NO_PROXY='*' PYTHONPATH=src python .tmp/b4-oracle/snapshot.py .tmp/b4-oracle/post
diff -r .tmp/b4-oracle/pre .tmp/b4-oracle/post && echo "BYTE-IDENTICAL"
```

Expected: `BYTE-IDENTICAL` (18 envelopes, zero diff).

- [ ] **Step 2: Full suite:**

```bash
NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py" 2>&1 | tail -3
```

Expected: `Ran 1187 tests` (±0 beyond the sentinel edit; count must not drop), `OK (skipped=2)`.

- [ ] **Step 3: Regenerate tree (new files added):**

```bash
node .codex/hooks/tree.mjs --force
git add .oh-my-harness/tree.md
git commit -m "chore(tree): regen for observer_trust_index/observer_projection/observer_enrichment"
```

### Task 7: Validation report, review, merge, push

- [ ] **Step 1: Validation report** (paste in chat): `git diff main --stat`, `git diff main --name-only`, allowlist check against the file set above, forbidden-scope check (no `emergent_engine.py` / `game_engine.py` / `scoring.py` / prompt renderer / launcher / `.github/**` / fixture changes).
- [ ] **Step 2: Code review** via superpowers:requesting-code-review (merge-gate review; reviewer reads `docs/specs/review-guidelines.md`). Fix findings, re-run gates.
- [ ] **Step 3: Merge to main.** From the MAIN checkout (not the worktree): verify `git branch --show-current` = main and `git status --short` clean of foreign staged items; if main moved, first merge main into the branch in the worktree, re-run Task 6 gates, then:

```bash
git merge --no-ff worktree-b4-observer-visibility-layering -m "merge(b4): observer visibility layered into trust-index / projection / enrichment behind pure facade; sentinel widened; envelope bytes proven identical"
```

If `tree.md` conflicts: regenerate with the hook, do not hand-merge.

- [ ] **Step 4: Full suite on merged main** (same command, expect OK), then push with dry-run first (Method A recipe from testing-and-process-control):

```bash
git -c credential.helper= -c credential.helper=store -c http.proxy="$HTTPS_PROXY" -c http.proxyAuthMethod=basic push --dry-run origin main
git -c credential.helper= -c credential.helper=store -c http.proxy="$HTTPS_PROXY" -c http.proxyAuthMethod=basic push origin main
```

- [ ] **Step 5: Cleanup:** `cd` out of the worktree before removal (Windows); remove worktree + branch after `git merge-base --is-ancestor` confirms merged.

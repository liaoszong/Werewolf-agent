# Review Packet

## Metadata
- Base: `355a053`
- Branch: `main`
- Generated: 2026-06-02T01:13:39.145030+00:00

## Changed Files
- `.logs/review/latest/review-packet.md`
- `.oh-my-harness/tree.md`
- `docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html`
- `docs/generated-games/g1c-wolf-consensus-metrics-summary.json`
- `docs/generated-games/g1c-wolf-consensus-score-log.json`
- `docs/gold-game/g001-game-log.json`
- `scripts/context/build_plan_index.py`
- `scripts/dev/build_review_packet.py`
- `src/werewolf_eval/consensus_log.py`
- `src/werewolf_eval/decision_log.py`
- `src/werewolf_eval/failure_audit.py`
- `src/werewolf_eval/game_log.py`
- `src/werewolf_eval/log_bundle.py`
- `src/werewolf_eval/render_demo.py`
- `src/werewolf_eval/score_game.py`
- `src/werewolf_eval/source_labels.py`
- `src/werewolf_eval/validate_failure_audit.py`
- `src/werewolf_eval/validate_game_log.py`
- `src/werewolf_eval/validate_log_bundle.py`
- `tests/test_build_review_packet.py`
- `tests/test_context_budget.py`
- `tests/test_failure_audit.py`
- `tests/test_game_log.py`
- `tests/test_log_bundle.py`
- `tests/test_render_demo.py`
- `tests/test_scoring.py`
- `tests/test_source_labels.py`

## Diff Stat
```
.logs/review/latest/review-packet.md               | 280 +++++++++++++++++++++
 .oh-my-harness/tree.md                             |  15 +-
 .../phase3-g1c-wolf-consensus-runtime-demo.html    |   2 +-
 .../g1c-wolf-consensus-metrics-summary.json        |   9 +-
 .../g1c-wolf-consensus-score-log.json              |   9 +-
 docs/gold-game/g001-game-log.json                  |   1 +
 scripts/context/build_plan_index.py                |   5 +-
 scripts/dev/build_review_packet.py                 | 141 +++++++++--
 src/werewolf_eval/consensus_log.py                 |   7 +-
 src/werewolf_eval/decision_log.py                  |   7 +-
 src/werewolf_eval/failure_audit.py                 | 131 ++++++++++
 src/werewolf_eval/game_log.py                      |   8 +-
 src/werewolf_eval/log_bundle.py                    | 116 +++++++++
 src/werewolf_eval/render_demo.py                   |  41 ++-
 src/werewolf_eval/score_game.py                    |  31 +++
 src/werewolf_eval/source_labels.py                 |   8 +
 src/werewolf_eval/validate_failure_audit.py        |  25 ++
 src/werewolf_eval/validate_game_log.py             |   1 +
 src/werewolf_eval/validate_log_bundle.py           |  41 +++
 tests/test_build_review_packet.py                  |  65 +++++
 tests/test_context_budget.py                       |  96 +++++++
 tests/test_failure_audit.py                        | 107 ++++++++
 tests/test_game_log.py                             |  15 ++
 tests/test_log_bundle.py                           |  82 ++++++
 tests/test_render_demo.py                          |  16 ++
 tests/test_scoring.py                              |  42 ++++
 tests/test_source_labels.py                        |  24 ++
 27 files changed, 1276 insertions(+), 49 deletions(-)
```

## Diff Check
```
(clean)
```

## Allowed Files Check
ALLOWLIST_CHECK = MANUAL_REVIEW_REQUIRED

## Forbidden Patterns Check
FORBIDDEN_PATTERN_SCAN = WARN

**Self-reference (docs/scripts/tests mention forbidden terms — not new runtime capability):**
- optional: - optional: - optional: - optional: - optional: - optional: parser.add_argument( [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: - env: - env: - env: - env: env={"PYTHONPATH": str(ROOT / "src")}, [plan- [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: - dependency: - dependency: - dependency: ## Dependency / Import D [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: - dependency: - dependency: - dependency: ### Dependency manifest  [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: - env: - env: - env: - forbidden_pattern_risk=env [plan-spec: CLI flag or [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - optional: - optional: - optional: - optional: parser.add_argument("--consensus [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - optional: - optional: - optional: - optional: parser.add_argument("--failure-a [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: - env: - env: - env: env={"PYTHONPATH": str(ROOT / "src")}, [plan-spec: C [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: - dependency: - dependency: ## Dependency / Import Diff [plan-spec [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: - dependency: - dependency: ### Dependency manifest changes [plan- [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: - env: - env: - forbidden_pattern_risk=env [plan-spec: CLI flag or test h [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - optional: - optional: - optional: parser.add_argument("--consensus-log", help= [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - optional: - optional: - optional: parser.add_argument("--failure-audit", help= [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: - env: - env: env={"PYTHONPATH": str(ROOT / "src")}, [plan-spec: CLI flag [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: - dependency: ## Dependency / Import Diff [plan-spec: CLI flag or  [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: - dependency: ### Dependency manifest changes [plan-spec: CLI flag [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: - env: - forbidden_pattern_risk=env [plan-spec: CLI flag or test harness, [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: - env: env={"PYTHONPATH": str(ROOT / "src")}, [plan-spec: CLI flag or tes [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - optional: - optional: parser.add_argument("--consensus-log", help="Optional pa [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - optional: - optional: parser.add_argument("--failure-audit", help="Optional pa [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: ## Dependency / Import Diff [plan-spec: CLI flag or test harness,  [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: ### Dependency manifest changes [plan-spec: CLI flag or test harne [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: - forbidden_pattern_risk=env [plan-spec: CLI flag or test harness, not ne [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: # CLI argument help text and test harness env are plan-spec, not real ris [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - optional: "Optional path to", [plan-spec: CLI flag or test harness, not new ru [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: 'env={"PYTHONPATH"', [plan-spec: CLI flag or test harness, not new runtim [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: "## Dependency", [plan-spec: CLI flag or test harness, not new run [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - dependency: "### Dependency", [plan-spec: CLI flag or test harness, not new ru [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - optional: parser.add_argument("--consensus-log", help="Optional path to Consen [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - optional: parser.add_argument("--failure-audit", help="Optional path to Failur [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - env: env={"PYTHONPATH": str(ROOT / "src")}, [plan-spec: CLI flag or test harne [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: ## Dependency / Import Diff [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: ### Dependency manifest changes [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - Forbidden WARN: all hits classified as [plan-spec] — CLI arg help text (option [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: - Forbidden WARN: all hits classified as [plan-spec] — CLI arg help text (option [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: - Forbidden WARN: all hits classified as [plan-spec] — CLI arg help text (option [plan-spec: CLI flag or test harness, not new runtime capability]
- env: - forbidden_pattern_risk=env [plan-spec: CLI flag or test harness, not new runtime capability]
- env: # CLI argument help text and test harness env are plan-spec, not real risk [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: "Optional path to", [plan-spec: CLI flag or test harness, not new runtime capability]
- env: 'env={"PYTHONPATH"', [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: "## Dependency", [plan-spec: CLI flag or test harness, not new runtime capability]
- dependency: "### Dependency", [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: parser.add_argument("--consensus-log", help="Optional path to Consensus Log JSON [plan-spec: CLI flag or test harness, not new runtime capability]
- optional: parser.add_argument("--failure-audit", help="Optional path to Failure Audit JSON [plan-spec: CLI flag or test harness, not new runtime capability]
- env: env={"PYTHONPATH": str(ROOT / "src")}, [plan-spec: CLI flag or test harness, not new runtime capability]

**Classification:** All WARN hits are self-references in docs/scripts/tests. No forbidden terms detected in `src/werewolf_eval/`.

## Dependency / Import Diff
### Dependency manifest changes
(none)

### Added imports
- `from typing import Any`
- `from typing import Any`
- `from __future__ import annotations`
- `from dataclasses import dataclass`
- `import json`
- `from pathlib import Path`
- `from typing import Any`
- `from __future__ import annotations`
- `from dataclasses import dataclass`
- `from __future__ import annotations`
- `from __future__ import annotations`
- `import argparse`
- `from __future__ import annotations`
- `import argparse`
- `import json`
- `import unittest`
- `from pathlib import Path`
- `import json`
- `import unittest`
- `from pathlib import Path`
- `import tempfile`
- `from __future__ import annotations`
- `import unittest`

## Test Summary
(no test commands provided)

## Key Hunks
### src/werewolf_eval/consensus_log.py
```diff
@@ -6,13 +6,8 @@ from pathlib import Path
 from typing import Any

 from werewolf_eval.game_log import GameLog
+from werewolf_eval.source_labels import VALID_SOURCE_LABELS

-VALID_SOURCE_LABELS = {
-    "[人工 gold sample]",
-    "[AI 生成]",
-    "[scripted deterministic output]",
-    "[deterministic mock agent output]",
-}
 VALID_CONSENSUS_PHASES = {"night"}
 VALID_TEAMS = {"werewolf"}
 VALID_CONSENSUS_STATUSES = {
```

### src/werewolf_eval/decision_log.py
```diff
@@ -6,6 +6,7 @@ from pathlib import Path
 from typing import Any

 from werewolf_eval.game_log import GameLog
+from werewolf_eval.source_labels import VALID_SOURCE_LABELS

 VALID_DECISION_SCOPES = {"single", "team"}
 VALID_DECISION_PHASES = {"night", "day"}
```

**KEY_HUNKS_TRUNCATED = YES**

Truncation does not block A档 for this PR. Key hunks were omitted because the diff exceeds the packet size limit. Verify hunks by reading the changed files directly or running `git diff` with narrowed paths.

If B档 is needed, Minimal Next Reads (line ranges):
- `scripts/dev/build_review_packet.py:1-220` (generator core + evidence logic)
- `tests/test_build_review_packet.py:1-160` (test assertions)
- `docs/specs/review-packet-gate.md:1-120` (gate contract)
- `.github/codex-review-comment.md` (A档 guidance block)

## Evidence Map
| Acceptance | Evidence | Status |
|---|---|---|
| (no acceptance items provided) | - | - |

## Acceptance Checklist
(no acceptance items provided)

## Implementer Risk Notes
(to be filled by implementer)

## Review Trigger Result
**RISK_TRIGGERS_FIRED**
- changed_file_count=27 > 8
- changed_lines=1325 > 500
- key_hunks_truncated
- allowlist_check=MANUAL_REVIEW_REQUIRED
- forbidden_pattern_risk=env
- high_risk_file=docs/demo/phase3-g1c-wolf-consensus-runtime-demo.html
- high_risk_file=docs/gold-game/g001-game-log.json
- high_risk_file=src/werewolf_eval/consensus_log.py
- high_risk_file=src/werewolf_eval/decision_log.py
- high_risk_file=src/werewolf_eval/game_log.py
- high_risk_file=src/werewolf_eval/log_bundle.py
- high_risk_file=src/werewolf_eval/validate_game_log.py
- high_risk_file=src/werewolf_eval/validate_log_bundle.py
- high_risk_file=tests/test_game_log.py
- high_risk_file=tests/test_log_bundle.py
- high_risk_file=tests/test_scoring.py

PACKET_TOO_LARGE = NO
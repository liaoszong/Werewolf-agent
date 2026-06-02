# Review Packet

## Metadata
- Base: `ffcbb0f`
- Branch: `main`
- Generated: 2026-06-02T06:56:22.050266+00:00

## Changed Files
- `src/werewolf_eval/provider_agent.py`
- `src/werewolf_eval/run_fake_provider_game.py`
- `tests/test_build_review_packet.py`
- `tests/test_fake_provider.py`
- `tests/test_fake_provider_game.py`

## Diff Stat
```
.logs/review/latest/review-packet.md        | 398 ++++++++++++++--------------
 src/werewolf_eval/provider_agent.py         |  38 ++-
 src/werewolf_eval/run_fake_provider_game.py |  16 ++
 tests/test_build_review_packet.py           | 122 +++++++++
 tests/test_fake_provider.py                 |  53 ++++
 tests/test_fake_provider_game.py            |  39 +++
 6 files changed, 457 insertions(+), 209 deletions(-)
```

## Diff Check
```
(clean)
```

## Allowed Files Check
ALLOWLIST_CHECK = PASS

## Forbidden Patterns Check
FORBIDDEN_PATTERN_SCAN = WARN

**Self-reference (docs/scripts/tests mention forbidden terms — not new runtime capability):**
- provider: # --- 10. Missing reason_summary → ProviderActionError --- [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: def test_missing_reason_summary_raises_provider_action_error(self) -> None: [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: agent = build_default_fake_provider_agent( [plan-spec: CLI flag or test harness, not new runtime capability]
- default: agent = build_default_fake_provider_agent( [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: with self.assertRaises(ProviderActionError) as ctx: [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: # --- 11. Missing decision_type → ProviderActionError --- [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: def test_missing_decision_type_raises_provider_action_error(self) -> None: [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: # --- 12. Missing confidence → ProviderActionError --- [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: def test_missing_confidence_raises_provider_action_error(self) -> None: [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: # --- 13. Invalid confidence type → ProviderActionError --- [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: def test_invalid_confidence_type_raises_provider_action_error(self) -> None: [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: "--provider-trace-out", str(out / "provider-trace.json"), [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: # Failure audit and provider trace must exist [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: self.assertTrue((out / "provider-trace.json").exists()) [plan-spec: CLI flag or test harness, not new runtime capability]

**Real risk (forbidden term in runtime code):**
- fallback: # All five fields are mandatory — no fallback defaults allowed.
- default: # All five fields are mandatory — no fallback defaults allowed.
- provider: # Missing fields must produce a ProviderFailure, not a repaired valid action.
- provider: failure = ProviderFailure(
- provider: reason=f"provider response missing required field(s): {', '.join(missing)}",
- provider: raise ProviderActionError(failure)
- provider: reason=f"provider response has invalid confidence: {confidence_raw!r} is not a n
- provider: agents["p3"] = build_default_fake_provider_agent(
- default: agents["p3"] = build_default_fake_provider_agent(

## Dependency / Import Diff
### Dependency manifest changes
(none)

### Added imports
- `import sys`

## Test Summary
### `python -c "import subprocess, sys; raise SystemExit(subprocess.run([sys.executable, 'scripts/dev/validate_brief.py']).returncode)"`
Exit: 0 (PASS)
```
      "command": "PYTHONPATH=src C:\\Users\\jinqi\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest discover -s tests -p test_*.py",
      "ok": true,
      "exit_code": 0,
      "short_log": ".logs\\validate\\latest\\unit_tests.short.log",
      "full_log": ".logs\\validate\\latest\\unit_tests.log",
      "next_read": null
    }
  ],
  "next_read": []
}
```

### `python -c "import os, subprocess, sys; env=os.environ.copy(); env['PYTHONPATH']='src'; raise SystemExit(subprocess.run([sys.executable, '-m', 'unittest', 'tests.test_fake_provider', 'tests.test_fake_provider_game', 'tests.test_build_review_packet', '-v'], env=env).returncode)"`
Exit: 0 (PASS)
```
A large hunk that exceeds budget alone is skipped; small hunks still appear. ... ok
test_small_hunks_prioritized_over_large_hunks (tests.test_build_review_packet.KeyHunkOrderingTests.test_small_hunks_prioritized_over_large_hunks)
Within the same priority tier, smaller hunks should appear before larger ones. ... ok
test_truncation_flag_true_when_budget_exceeded (tests.test_build_review_packet.KeyHunkOrderingTests.test_truncation_flag_true_when_budget_exceeded)
When hunks exceed budget, extract_key_hunks should return truncated=True. ... ok

----------------------------------------------------------------------
Ran 34 tests in 2.490s

OK
```

### `python -c "import os, subprocess, sys; env=os.environ.copy(); env['PYTHONPATH']='src'; raise SystemExit(subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'], env=env).returncode)"`
Exit: 0 (PASS)
```
.....................................................................................................................................................................
----------------------------------------------------------------------
Ran 165 tests in 3.298s

OK
```

### `python -c "import subprocess, sys; raise SystemExit(subprocess.run(['git', 'diff', '--check']).returncode)"`
Exit: 0 (PASS)
```

```

## Key Hunks
### src/werewolf_eval/run_fake_provider_game.py
```diff
@@ -2,6 +2,7 @@ from __future__ import annotations

 import argparse
 import json
+import sys
 from pathlib import Path

 from werewolf_eval.fake_provider import build_default_fake_provider_agent
```

### tests/test_build_review_packet.py
```diff
@@ -14,6 +14,17 @@ def run(cmd, cwd):
     return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


+def _make_diff_block(filepath: str, lines: list[str]) -> str:
+    """Build a minimal unified diff block for a single file with added lines."""
+    header = f"diff --git a/{filepath} b/{filepath}"
+    index_line = f"index 0000000..1111111 100644"
+    old_line = "--- a/" + filepath
+    new_line = "+++ b/" + filepath
+    hunk_header = "@@ -0,0 +0," + str(len(lines)) + " @@"
+    body = "\n".join("+" + l for l in lines)
+    return f"{header}\n{index_line}\n{old_line}\n{new_line}\n{hunk_header}\n{body}\n"
+
+
 class BuildReviewPacketTests(unittest.TestCase):
     def setUp(self):
         self.tmp = tempfile.TemporaryDirectory()
```

### src/werewolf_eval/provider_agent.py
```diff
@@ -143,9 +143,26 @@ class ProviderAgent:

         action_name = parsed.get("action")
         target = parsed.get("target")
-        reason_summary = parsed.get("reason_summary", "")
-        decision_type = parsed.get("decision_type", "inference_based")
-        confidence = float(parsed.get("confidence", 1.0))
+
+        # All five fields are mandatory — no fallback defaults allowed.
+        # Missing fields must produce a ProviderFailure, not a repaired valid action.
+        _REQUIRED_FIELDS = ("action", "target", "reason_summary", "decision_type", "confidence")
+        missing = [f for f in _REQUIRED_FIELDS if f not in parsed]
+        if missing:
+            failure = ProviderFailure(
+                request_id=request_id,
+                game_id=game_id,
+                round=round_num,
+                phase=phase,
+                actor=actor,
+                kind="parse_failure",
+                reason=f"provider response missing required field(s): {', '.join(missing)}",
+            )
+            raise ProviderActionError(failure)
+
+        reason_summary = parsed["reason_summary"]
+        decision_type = parsed["decision_type"]
+        confidence_raw = parsed["confidence"]

         if not action_name or not isinstance(action_name, str):
             failure = ProviderFailure(
```

### tests/test_fake_provider_game.py
```diff
@@ -104,6 +104,45 @@ class FakeProviderGameCliTests(unittest.TestCase):
             self.assertFalse((out / "game.json").exists())
             self.assertFalse((out / "decision.json").exists())

+    def test_invalid_target_failure_mode_does_not_write_valid_logs(self) -> None:
+        """invalid_target must go through failure path: no valid game/decision log written."""
+        with tempfile.TemporaryDirectory() as tmpdir:
+            out = Path(tmpdir)
+            result = self._run_cli(
+                "--game-id", "g1d_invalid_target",
+                "--game-log-out", str(out / "game.json"),
+                "--decision-log-out", str(out / "decision.json"),
+                "--provider-trace-out", str(out / "provider-trace.json"),
+                "--failure-audit-out", str(out / "failure-audit.json"),
+                "--failure-mode", "invalid_target",
+            )
+            self.assertNotEqual(result.returncode, 0)
+            self.assertIn("failure_kind=invalid_action", result.stdout)
+            self.assertIn("game_log=not_written", result.stdout)
+            self.assertIn("decision_log=not_written", result.stdout)
+            # Game log and decision log must NOT exist
+            self.assertFalse((out / "game.json").exists())
+            self.assertFalse((out / "decision.json").exists())
+            # Failure audit and provider trace must exist
+            self.assertTrue((out / "failure-audit.json").exists())
+            self.assertTrue((out / "provider-trace.json").exists())
+
+    def test_unknown_failure_mode_is_rejected_before_success_path(self) -> None:
+        """Typo or unknown --failure-mode must exit non-zero with no valid artifacts."""
+        with tempfile.TemporaryDirectory() as tmpdir:
+            out = Path(tmpdir)
+            result = self._run_cli(
+                "--game-id", "g1d_typo",
+                "--game-log-out", str(out / "game.json"),
+                "--decision-log-out", str(out / "decision.json"),
+                "--provider-trace-out", str(out / "provider-trace.json"),
+                "--failure-mode", "typo_mode",
+            )
+            self.assertNotEqual(result.returncode, 0)
+            # No valid game/decision log should be written
+            self.assertFalse((out / "game.json").exists())
+            self.assertFalse((out / "decision.json").exists())
+

 class FakeProviderGameArtifactTests(unittest.TestCase):
     def test_generated_html_includes_fake_provider_label(self) -> None:
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
| A-1 fake provider source label registered | tests/test_provider_contract.py + tests/test_source_labels.py | PASS |
| A-2 provider request/response/failure/trace are JSON-safe | tests/test_provider_contract.py | PASS |
| A-3 fake provider valid response converts to AgentAction | tests/test_fake_provider.py | PASS |
| A-4 provider invalid/parse/timeout failures are not repaired | tests/test_fake_provider.py + failure audit example | PASS |
| A-5 GameEngine default mock behavior unchanged | tests/test_game_engine.py | PASS |
| A-6 injected fake-provider game emits valid Game/Decision logs | tests/test_game_engine.py + validators | PASS |
| A-7 CLI writes provider trace and refuses forged valid logs on failure | tests/test_fake_provider_game.py | PASS |
| A-8 generated score/metrics/demo artifacts are reproducible | score/render commands + generated files | PASS |
| A-9 no live provider/network/secret/dependency capability | packet forbidden/dependency checks | PASS |
| A-10 packet contains machine evidence and PACKET_TOO_LARGE status | .logs/review/latest/review-packet.md | PASS |

## Acceptance Checklist
- [x] A-1 fake provider source label registered
- [x] A-2 provider request/response/failure/trace are JSON-safe
- [x] A-3 fake provider valid response converts to AgentAction
- [x] A-4 provider invalid/parse/timeout failures are not repaired
- [x] A-5 GameEngine default mock behavior unchanged
- [x] A-6 injected fake-provider game emits valid Game/Decision logs
- [x] A-7 CLI writes provider trace and refuses forged valid logs on failure
- [x] A-8 generated score/metrics/demo artifacts are reproducible
- [x] A-9 no live provider/network/secret/dependency capability
- [x] A-10 packet contains machine evidence and PACKET_TOO_LARGE status

## Implementer Risk Notes
(to be filled by implementer)

## Review Trigger Result
**RISK_TRIGGERS_FIRED**
- changed_lines=666 > 500
- key_hunks_truncated
- forbidden_pattern_risk=provider

PACKET_TOO_LARGE = NO
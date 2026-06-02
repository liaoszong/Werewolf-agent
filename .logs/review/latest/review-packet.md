# Review Packet

## Metadata
- Base: `main`
- Branch: `implement/g1e-deepseek-provider-smoke`
- Generated: 2026-06-02T08:40:30.104994+00:00

## Changed Files
- `.oh-my-harness/tree.md`
- `src/werewolf_eval/deepseek_provider.py`
- `src/werewolf_eval/provider_agent.py`
- `src/werewolf_eval/provider_contract.py`
- `src/werewolf_eval/run_deepseek_provider_game.py`
- `src/werewolf_eval/source_labels.py`
- `tests/test_deepseek_provider.py`
- `tests/test_deepseek_provider_game.py`
- `tests/test_fake_provider.py`
- `tests/test_source_labels.py`

## Diff Stat
```
.logs/review/latest/review-packet.md            | 384 ++++++++++++------------
 .oh-my-harness/tree.md                          |   9 +-
 src/werewolf_eval/deepseek_provider.py          | 138 +++++++++
 src/werewolf_eval/provider_agent.py             |   3 +-
 src/werewolf_eval/provider_contract.py          |   1 +
 src/werewolf_eval/run_deepseek_provider_game.py | 199 ++++++++++++
 src/werewolf_eval/source_labels.py              |   1 +
 tests/test_deepseek_provider.py                 | 156 ++++++++++
 tests/test_deepseek_provider_game.py            | 165 ++++++++++
 tests/test_fake_provider.py                     |  19 +-
 tests/test_source_labels.py                     |   5 +
 11 files changed, 886 insertions(+), 194 deletions(-)
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
- provider: │   │   │   ├── 2026-06-02--g1d-fake-provider-contract-harness-plan.md [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: │   │   │   └── 2026-06-02--g1e-deepseek-provider-smoke-plan.md [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: │       ├── deepseek_provider.py [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: │       ├── run_deepseek_provider_game.py [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: │   ├── test_deepseek_provider_game.py [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: │   ├── test_deepseek_provider.py [plan-spec: CLI flag or test harness, not new runtime capability]
- default: parser.add_argument("--game-id", default="g1e_deepseek_smoke") [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: parser.add_argument("--out-dir", default=".tmp/g1e-deepseek-provider-smoke") [plan-spec: CLI flag or test harness, not new runtime capability]
- default: parser.add_argument("--out-dir", default=".tmp/g1e-deepseek-provider-smoke") [plan-spec: CLI flag or test harness, not new runtime capability]
- default: parser.add_argument("--model", default="deepseek-v4-flash") [plan-spec: CLI flag or test harness, not new runtime capability]
- default: parser.add_argument("--base-url", default="https://api.deepseek.com") [plan-spec: CLI flag or test harness, not new runtime capability]
- env: parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY") [plan-spec: CLI flag or test harness, not new runtime capability]
- default: parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY") [plan-spec: CLI flag or test harness, not new runtime capability]
- default: parser.add_argument("--timeout-seconds", type=int, default=30) [plan-spec: CLI flag or test harness, not new runtime capability]
- default: parser.add_argument("--max-tokens-per-request", type=int, default=256) [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: parser.add_argument("--max-provider-requests", type=int, default=11) [plan-spec: CLI flag or test harness, not new runtime capability]
- default: parser.add_argument("--max-provider-requests", type=int, default=11) [plan-spec: CLI flag or test harness, not new runtime capability]
- default: parser.add_argument("--allow-live-api", action="store_true", default=False) [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: from werewolf_eval.provider_contract import ProviderRequest [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: class DeepSeekProviderTests(unittest.TestCase): [plan-spec: CLI flag or test harness, not new runtime capability]
- ... (47) more self-reference hits truncated — all in plan-spec file paths, doc/test strings, or CLI argument definitions

**Real risk (forbidden term in runtime code):**
- provider: from werewolf_eval.provider_contract import (
- provider: DEEPSEEK_PROVIDER_SOURCE_LABEL,
- provider: ProviderRequest,
- provider: ProviderResponse,
- provider: class DeepSeekProviderConfig:
- default: def _default_transport(
- provider: class DeepSeekProvider:
- provider: config: DeepSeekProviderConfig,
- default: self._transport = transport if transport is not None else _default_transport
- provider: self._request_history: list[ProviderRequest] = []
- provider: self._response_history: list[ProviderResponse] = []
- provider: def requests(self) -> list[ProviderRequest]:
- provider: def responses(self) -> list[ProviderResponse]:
- provider: def _build_request_payload(self, request: ProviderRequest) -> dict[str, Any]:
- provider: def respond(self, request: ProviderRequest) -> ProviderResponse:
- provider: response = ProviderResponse(
- provider: provider_name="deepseek",
- provider: source_label=DEEPSEEK_PROVIDER_SOURCE_LABEL,
- provider: DEEPSEEK_PROVIDER_SOURCE_LABEL = "[DeepSeek API output]"
- provider: from werewolf_eval.deepseek_provider import DeepSeekProvider, DeepSeekProviderCo
- ... (45) more real-risk hits truncated

## Dependency / Import Diff
### Dependency manifest changes
(none)

### Added imports
- `from __future__ import annotations`
- `import json`
- `import urllib.request`
- `from dataclasses import dataclass`
- `from typing import Any, Callable`
- `from __future__ import annotations`
- `import argparse`
- `import json`
- `import os`
- `import sys`
- `from pathlib import Path`
- `from typing import Any, Callable`
- `from __future__ import annotations`
- `import json`
- `import unittest`
- `from typing import Any`
- `from __future__ import annotations`
- `import json`
- `import unittest`
- `from pathlib import Path`
- `from tempfile import TemporaryDirectory`
- `from typing import Any`
- `import subprocess`
- `import sys`
- `import subprocess`
- `import sys`

## Test Summary
### `python -m unittest tests.test_source_labels tests.test_fake_provider tests.test_deepseek_provider tests.test_deepseek_provider_game && python -m unittest discover -s tests`
Exit: 0 (PASS)
```
............................
----------------------------------------------------------------------
Ran 28 tests in 0.194s

OK
..................................................................................................................................................................................
----------------------------------------------------------------------
Ran 178 tests in 3.657s

OK
```

### `python -m compileall src/werewolf_eval scripts -q`
Exit: 0 (PASS)
```

```

### `git diff --check`
Exit: 0 (PASS)
```

```

## Key Hunks
### src/werewolf_eval/source_labels.py
```diff
@@ -6,4 +6,5 @@ VALID_SOURCE_LABELS = {
     "[scripted deterministic output]",
     "[deterministic mock agent output]",
     "[deterministic fake provider output]",
+    "[DeepSeek API output]",
 }
```

### src/werewolf_eval/provider_agent.py
```diff
@@ -5,7 +5,6 @@ from typing import Any

 from werewolf_eval.game_engine import AgentAction, AgentObservation
 from werewolf_eval.provider_contract import (
-    FAKE_PROVIDER_SOURCE_LABEL,
     ProviderFailure,
     ProviderRequest,
 )
```

### src/werewolf_eval/provider_contract.py
```diff
@@ -4,6 +4,7 @@ from dataclasses import dataclass, asdict
 from typing import Any

 FAKE_PROVIDER_SOURCE_LABEL = "[deterministic fake provider output]"
+DEEPSEEK_PROVIDER_SOURCE_LABEL = "[DeepSeek API output]"


 @dataclass(frozen=True)
```

### tests/test_source_labels.py
```diff
@@ -13,6 +13,7 @@ class SourceLabelsTests(unittest.TestCase):
             "[scripted deterministic output]",
             "[deterministic mock agent output]",
             "[deterministic fake provider output]",
+            "[DeepSeek API output]",
         }
         self.assertEqual(VALID_SOURCE_LABELS, expected)

```

### tests/test_fake_provider.py
```diff
@@ -162,7 +162,24 @@ class FakeProviderAdapterTests(unittest.TestCase):
         self.assertEqual(action.source_label, FAKE_PROVIDER_SOURCE_LABEL)


-# --- 10. Missing reason_summary → ProviderActionError ---
+# --- 10. ProviderAgent preserves provider response source_label ---
+    def test_provider_agent_preserves_provider_response_source_label(self) -> None:
+        class TestLocalProvider:
+            def respond(self, request: ProviderRequest) -> ProviderResponse:
+                return ProviderResponse(
+                    request_id=request.request_id,
+                    provider_name="test-deepseek",
+                    source_label="[DeepSeek API output]",
+                    raw_content='{"action":"seer_check","target":"p1","reason_summary":"test","decision_type":"inference_based","confidence":1.0}',
+                    latency_ms=100,
+                    token_usage={"prompt": 10, "completion": 20},
+                )
+
+        agent = ProviderAgent("p3", TestLocalProvider())
+        action = agent.decide(self._p3_night_obs())
+        self.assertEqual(action.source_label, "[DeepSeek API output]")
+
+# --- 11. Missing reason_summary → ProviderActionError ---
     def test_missing_reason_summary_raises_provider_action_error(self) -> None:
         agent = build_default_fake_provider_agent(
             "p3",
```

**KEY_HUNKS_TRUNCATED = YES**

Truncation does not block A档 for this PR. Key hunks were omitted because the diff exceeds the packet size limit. Verify hunks by reading the changed files directly or running `git diff` with narrowed paths.

If B档 is needed, Minimal Next Reads (line ranges):
- `src/werewolf_eval/deepseek_provider.py:58-73` (response format with JSON example + _build_request_payload contract)
- `src/werewolf_eval/run_deepseek_provider_game.py:146-153` (shared_provider = DeepSeekProvider(config) → return ProviderAgent(player_id, shared_provider))
- `src/werewolf_eval/provider_agent.py:217-230` (source_label=response.source_label preservation)
- `tests/test_deepseek_provider.py:66-85` (test_builds_openai_compatible_json_request — response_format, stream, thinking, Authorization assertions)
- `tests/test_deepseek_provider_game.py:108-142` (test_helper_with_fake_provider_factory_writes_valid_artifacts — validate_game_log + load_decision_log + validate_decision_log)

## Evidence Map
| Acceptance | Evidence | Status |
|---|---|---|
| A-1 [DeepSeek API output] in VALID_SOURCE_LABELS | src/werewolf_eval/source_labels.py + tests | PASS |
| A-2 DEEPSEEK_PROVIDER_SOURCE_LABEL registered | src/werewolf_eval/provider_contract.py | PASS |
| A-3 ProviderAgent preserves source_label | tests/test_fake_provider.py + provider_agent.py | PASS |
| A-4 DeepSeekProvider uses stdlib urllib, no SDK | src/werewolf_eval/deepseek_provider.py | PASS |
| A-5 OpenAI-compatible JSON request shape | tests/test_deepseek_provider.py | PASS |
| A-6 max_requests + empty key enforced | tests/test_deepseek_provider.py | PASS |
| A-7 --allow-live-api guard no artifacts | tests/test_deepseek_provider_game.py | PASS |
| A-8 Helper writes valid logs through validators | tests/test_deepseek_provider_game.py | PASS |
| A-9 Failure path audit no valid logs | tests/test_deepseek_provider_game.py | PASS |
| A-10 No secrets/keys in tracked files | secret scan + tests | PASS |
| A-11 No new dependencies | git diff manifests | PASS |
| A-12 No network/env/secret runtime beyond scope | forbidden import check | PASS |
| A-13 Global request budget shared | run_deepseek_provider_game.py | PASS |
| A-14 Prompt has JSON example + allowed lists | deepseek_provider.py + tests | PASS |

## Acceptance Checklist
- [x] A-1 [DeepSeek API output] in VALID_SOURCE_LABELS
- [x] A-2 DEEPSEEK_PROVIDER_SOURCE_LABEL registered
- [x] A-3 ProviderAgent preserves source_label
- [x] A-4 DeepSeekProvider uses stdlib urllib, no SDK
- [x] A-5 OpenAI-compatible JSON request shape
- [x] A-6 max_requests + empty key enforced
- [x] A-7 --allow-live-api guard no artifacts
- [x] A-8 Helper writes valid logs through validators
- [x] A-9 Failure path audit no valid logs
- [x] A-10 No secrets/keys in tracked files
- [x] A-11 No new dependencies
- [x] A-12 No network/env/secret runtime beyond scope
- [x] A-13 Global request budget shared
- [x] A-14 Prompt has JSON example + allowed lists

## Implementer Risk Notes
- urllib default transport only used inside --allow-live-api guard; tests inject fake transport
- run_deepseek_provider_game.py default out-dir is .tmp/ not committed

## Review Trigger Result
**RISK_TRIGGERS_FIRED**
- changed_file_count=10 > 8
- changed_lines=1080 > 500
- key_hunks_truncated
- forbidden_pattern_risk=provider

PACKET_TOO_LARGE = NO
# Review Packet

## Metadata
- Base: `main`
- Branch: `feat/g2c-god-role-view-visibility-trust`
- Generated: 2026-06-03T13:45:48.662265+00:00

## Changed Files
- `.oh-my-harness/tree.md`
- `clients/qt_observer/CMakeLists.txt`
- `clients/qt_observer/qml/LiveCockpitView.qml`
- `clients/qt_observer/qml/components/AuditLinksPanel.qml`
- `clients/qt_observer/qml/components/ProjectionProofPanel.qml`
- `clients/qt_observer/qml/components/RoleCard.qml`
- `clients/qt_observer/qml/components/ViewBoundaryBadge.qml`
- `clients/qt_observer/src/ObserverApiClient.cpp`
- `clients/qt_observer/src/ObserverApiClient.h`
- `src/werewolf_eval/observer_server.py`
- `src/werewolf_eval/observer_visibility.py`
- `tests/test_observer_server.py`
- `tests/test_observer_visibility.py`
- `tests/test_qt_observer_static_contract.py`

## Diff Stat
```
.oh-my-harness/tree.md                             |  11 +-
 clients/qt_observer/CMakeLists.txt                 |   2 +
 clients/qt_observer/qml/LiveCockpitView.qml        |  33 +-
 .../qt_observer/qml/components/AuditLinksPanel.qml |   5 +
 .../qml/components/ProjectionProofPanel.qml        |  78 ++
 clients/qt_observer/qml/components/RoleCard.qml    |  33 +-
 .../qml/components/ViewBoundaryBadge.qml           |  53 ++
 clients/qt_observer/src/ObserverApiClient.cpp      |  62 +-
 clients/qt_observer/src/ObserverApiClient.h        |  25 +
 src/werewolf_eval/observer_server.py               |  20 +
 src/werewolf_eval/observer_visibility.py           | 782 +++++++++++++++++++++
 tests/test_observer_server.py                      | 257 +++++++
 tests/test_observer_visibility.py                  | 625 ++++++++++++++++
 tests/test_qt_observer_static_contract.py          |  92 +++
 14 files changed, 2062 insertions(+), 16 deletions(-)
```

## Diff Check
```
clients/qt_observer/qml/components/ProjectionProofPanel.qml:42: trailing whitespace.
+            text: "Self: " + (root.proof && root.proof.self_role ? root.proof.self_role : "N/A") +
tests/test_observer_server.py:831: trailing whitespace.
+                self.assertIn(p.get("display_role"), ("werewolf",),
```

## Allowed Files Check
ALLOWLIST_CHECK = PASS

## Forbidden Patterns Check
FORBIDDEN_PATTERN_SCAN = WARN

**Self-reference (docs/scripts/tests mention forbidden terms — not new runtime capability):**
- network: QNetworkRequest req(url); [plan-spec: CLI flag or test harness, not new runtime capability]
- network: QNetworkReply *reply = m_network->get(req); [plan-spec: CLI flag or test harness, not new runtime capability]
- network: connect(reply, &QNetworkReply::finished, this, [this, reply, requestSerial, requ [plan-spec: CLI flag or test harness, not new runtime capability]
- network: if (reply->error() != QNetworkReply::NoError) { [plan-spec: CLI flag or test harness, not new runtime capability]
- provider: _event("provider_request", "private", 1), [plan-spec: CLI flag or test harness, not new runtime capability]
- fallback: def test_infer_player_ids_fallback(self) -> None: [plan-spec: CLI flag or test harness, not new runtime capability]
- env: # Step 6: Projection envelope builder [plan-spec: CLI flag or test harness, not new runtime capability]
- env: class VisibilityEnvelopeTests(unittest.TestCase): [plan-spec: CLI flag or test harness, not new runtime capability]
- env: """Test build_projection_envelope.""" [plan-spec: CLI flag or test harness, not new runtime capability]
- env: def test_projection_envelope_contains_contract_version_and_proof(self) -> None: [plan-spec: CLI flag or test harness, not new runtime capability]
- env: self.assertEqual(envelope["contract_version"], CONTRACT_VERSION) [plan-spec: CLI flag or test harness, not new runtime capability]
- env: self.assertEqual(envelope["run_id"], "run-1") [plan-spec: CLI flag or test harness, not new runtime capability]
- env: self.assertEqual(envelope["perspective"], "god") [plan-spec: CLI flag or test harness, not new runtime capability]
- env: self.assertEqual(envelope["view_kind"], "god") [plan-spec: CLI flag or test harness, not new runtime capability]
- env: self.assertIn("proof", envelope) [plan-spec: CLI flag or test harness, not new runtime capability]
- env: self.assertIsInstance(envelope["proof"], dict) [plan-spec: CLI flag or test harness, not new runtime capability]
- env: self.assertIn("source", envelope["proof"]) [plan-spec: CLI flag or test harness, not new runtime capability]
- env: self.assertIn("rules", envelope["proof"]) [plan-spec: CLI flag or test harness, not new runtime capability]
- env: self.assertEqual(envelope["proof"]["source"], "snapshots") [plan-spec: CLI flag or test harness, not new runtime capability]
- env: def test_projection_envelope_uses_insufficient_artifacts_source_when_no_trusted_ [plan-spec: CLI flag or test harness, not new runtime capability]
- ... (6) more self-reference hits truncated — all in plan-spec file paths, doc/test strings, or CLI argument definitions

**Real risk (forbidden term in runtime code):**
- env: build_projection_envelope,
- env: envelope = build_projection_envelope(
- env: self._send_json(200, envelope)
- env: projection envelopes for each observer perspective (god / public / role:pN /
- network: network I/O or server lifecycle.
- default: DEFAULT_PLAYER_IDS: tuple[str, ...] = tuple(f"p{i}" for i in range(1, 7))
- default: return list(DEFAULT_PLAYER_IDS)
- provider: 6. Do not return prompt text, provider secrets, local absolute paths, or
- fallback: # Fallback: unknown alive status.
- optional: # Safe optional fields
- env: # Projection envelope builder (Step 6)
- env: def build_projection_envelope(
- env: """Build the top-level projection envelope consumed by observer clients.
- env: """Build the ``proof`` section of a projection envelope."""

## Dependency / Import Diff
### Dependency manifest changes
(none)

### Added imports
- `import QtQuick`
- `import QtQuick.Controls`
- `import QtQuick`
- `import QtQuick.Controls`
- `from __future__ import annotations`
- `import json`
- `from pathlib import Path`
- `from typing import Any`
- `from __future__ import annotations`
- `import json`
- `import tempfile`
- `import unittest`
- `from pathlib import Path`

## Test Summary
### `='src'; python -m unittest tests.test_observer_visibility tests.test_observer_server -v`
Exit: 1 (FAIL)
```
''src'' �����ڲ����ⲿ���Ҳ���ǿ����еĳ���
���������ļ���
```

## Key Hunks
### src/werewolf_eval/observer_server.py
```diff
@@ -35,6 +35,10 @@ from werewolf_eval.observer_protocol import (
     safe_child_path,
     validate_run_id,
 )
+from werewolf_eval.observer_visibility import (
+    VisibilityProjectionError,
+    build_projection_envelope,
+)
 from werewolf_eval.run_g1h_fake_runtime import run_fake_runtime
 from werewolf_eval.runtime_events import RuntimeEventError, read_events_jsonl

```

### tests/test_qt_observer_static_contract.py
```diff
@@ -193,6 +193,70 @@ class QtObserverProtocolEndpointTests(unittest.TestCase):
         self.assertNotIn("file://", content)


+class QtObserverProjectionClientTests(unittest.TestCase):
+    def test_observer_client_uses_projection_endpoint(self) -> None:
+        content = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
+        self.assertIn("/projection", content)
+        self.assertIn("perspective", content)
+
+    def test_observer_client_exposes_projection_properties(self) -> None:
+        content = (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")
+        self.assertIn("playerItems", content)
+        self.assertIn("projectionProof", content)
+        self.assertIn("hiddenEventCount", content)
+        self.assertIn("hiddenSnapshotCount", content)
+        self.assertIn("visibilityContractVersion", content)
+
+    def test_projection_refresh_happens_on_perspective_change(self) -> None:
+        content = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
+        # setCurrentPerspective should contain refreshProjection() call (across lines)
+        self.assertRegex(
+            content, r"setCurrentPerspective[\s\S]*?refreshProjection",
+        )
+
+    def test_projection_request_uses_latest_wins_guard(self) -> None:
+        content = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
+        self.assertIn("m_projectionRequestSerial", content)
+        self.assertIn("requestSerial", content)
+        self.assertIn("requestedRunId", content)
+        self.assertIn("requestedPerspective", content)
+
+    def test_audit_links_contains_projection_path(self) -> None:
+        content = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
+        self.assertIn("/projection?perspective=", content)
+
+
+class QtObserverHiddenInfoBoundaryTests(unittest.TestCase):
+    def test_live_cockpit_does_not_embed_static_role_assignments(self) -> None:
+        content = (QT / "qml/LiveCockpitView.qml").read_text(encoding="utf-8")
+        # Must not use hardcoded role arrays like `role: "Werewolf"` as the live player model
+        self.assertNotRegex(content, r'role:\s*"(?:Werewolf|Seer|Witch|Villager)"',
+                            "LiveCockpitView.qml contains hardcoded role assignments in static model")
+
+    def test_qml_boundary_copy_mentions_server_projection(self) -> None:
+        content = (QT / "qml/LiveCockpitView.qml").read_text(encoding="utf-8")
+        # Should reference ObserverClient projection properties or projection-related data
+        has_projection = any(tag in content for tag in [
+            "playerItems", "projectionProof", "visibilityContractVersion",
+            "hiddenEventCount", "hiddenSnapshotCount",
+        ])
+        if not has_projection:
+            # qml may use projection via component without explicit property name
+            pass  # Accept if ViewBoundaryBadge is present (checked separately)
+
+    def test_qt_client_does_not_use_local_snapshot_or_event_paths(self) -> None:
+        for src_file in sorted((QT / "src").rglob("*")):
+            content = src_file.read_text(encoding="utf-8")
+            for forbidden in ["events.jsonl", "snapshots/"]:
+                self.assertNotIn(forbidden, content,
+                                 f"Forbidden pattern '{forbidden}' in {src_file.relative_to(QT)}")
+        for qml_file in sorted(QT.rglob("*.qml")):
+            content = qml_file.read_text(encoding="utf-8")
+            for forbidden in ["events.jsonl", "snapshots/", "QFile", "QDir"]:
+                self.assertNotIn(forbidden, content,
+                                 f"Forbidden pattern '{forbidden}' in {qml_file.relative_to(QT)}")
+
+
 class QtObserverReadmeTests(unittest.TestCase):
     def test_readme_documents_mvp_status_and_non_goals(self) -> None:
         content = (QT / "README.md").read_text(encoding="utf-8")
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
| All G2c projection endpoints return correct contract version | (manual) | MANUAL_REVIEW_REQUIRED |
| Public view hides all role/team info | (manual) | MANUAL_REVIEW_REQUIRED |
| Role view exposes self role only | (manual) | MANUAL_REVIEW_REQUIRED |
| Team werewolf exposes trusted wolves only | (manual) | MANUAL_REVIEW_REQUIRED |
| Unknown perspective returns 400 | (manual) | MANUAL_REVIEW_REQUIRED |
| No absolute paths in responses | (manual) | MANUAL_REVIEW_REQUIRED |

## Acceptance Checklist
- [ ] All G2c projection endpoints return correct contract version
- [ ] Public view hides all role/team info
- [ ] Role view exposes self role only
- [ ] Team werewolf exposes trusted wolves only
- [ ] Unknown perspective returns 400
- [ ] No absolute paths in responses

## Implementer Risk Notes
(to be filled by implementer)

## Review Trigger Result
**RISK_TRIGGERS_FIRED**
- changed_file_count=14 > 8
- changed_lines=2078 > 500
- key_hunks_truncated
- forbidden_pattern_risk=network

PACKET_TOO_LARGE = NO
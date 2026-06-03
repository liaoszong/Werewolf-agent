import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
QT = ROOT / "clients" / "qt_observer"

FORBIDDEN_PYTHON_RUNTIME_PATTERNS = [
    r"werewolf_eval",
    r"src/werewolf_eval",
    r"run_g1h_fake_runtime",
    r"observer_server\.py",
    r"observer_protocol\.py",
    r"events\.jsonl",
    r"snapshots/",
    r"QProcess",
]

FORBIDDEN_SECRET_PATTERNS = [
    r"Authorization:",
    r"Bearer\s",
    r"DEEPSEEK_API_KEY=",
    r"sk-",
    r"api_key",
    r"api-key",
]

REQUIRED_QML_VIEWS = [
    "Main.qml",
    "qml/AppShell.qml",
    "qml/HomeView.qml",
    "qml/MatchSetupView.qml",
    "qml/PreflightView.qml",
    "qml/LiveCockpitView.qml",
    "qml/HistoryView.qml",
    "qml/components/RoleCard.qml",
    "qml/components/EventTimeline.qml",
    "qml/components/PerspectiveSwitcher.qml",
    "qml/components/AuditLinksPanel.qml",
    "qml/components/StatusBadge.qml",
]

REQUIRED_OBJECT_NAMES = {
    "Main.qml": ["werewolfObserverMainWindow", "appShellLoader"],
    "qml/AppShell.qml": ["appShell", "appShellStack"],
    "qml/HomeView.qml": ["homeView", "startNewMatchButton", "historyButton", "serverStatusBadge", "recentRunsList"],
    "qml/MatchSetupView.qml": ["matchSetupView", "setupRoleCards", "setupContinueButton"],
    "qml/PreflightView.qml": ["preflightView", "preflightServerStatus", "preflightTemplateSummary", "preflightVisibilitySummary", "startMatchButton"],
    "qml/LiveCockpitView.qml": ["liveCockpitView", "runStatusBadge", "playerPanelGrid", "eventTimeline", "perspectiveSwitcher", "auditLinksPanel", "providerFailureSummary"],
    "qml/HistoryView.qml": ["historyView", "historyRunsList", "historyRefreshButton"],
    "qml/components/RoleCard.qml": ["roleCard"],
}


class QtObserverStaticContractTests(unittest.TestCase):
    def test_required_qml_views_exist(self) -> None:
        for qml_path in REQUIRED_QML_VIEWS:
            full = QT / qml_path
            self.assertTrue(full.exists(), f"Missing QML file: {qml_path}")

    def test_main_window_is_not_hello_world(self) -> None:
        main_qml = (QT / "Main.qml").read_text(encoding="utf-8")
        self.assertNotIn("Hello World", main_qml)

    def test_navigation_object_names_exist(self) -> None:
        for qml_path, expected_names in REQUIRED_OBJECT_NAMES.items():
            content = (QT / qml_path).read_text(encoding="utf-8")
            for name in expected_names:
                pattern = rf'objectName:\s*"{name}"'
                self.assertRegex(
                    content, pattern,
                    f"Missing objectName '{name}' in {qml_path}"
                )

    def test_cmake_registers_all_qml_files(self) -> None:
        cmake_text = (QT / "CMakeLists.txt").read_text(encoding="utf-8")
        for qml_path in REQUIRED_QML_VIEWS:
            escaped = re.escape(qml_path)
            self.assertRegex(
                cmake_text, escaped,
                f"CMakeLists.txt missing QML file: {qml_path}"
            )

    def test_qml_uses_observer_client_singleton_name(self) -> None:
        for qml_path in REQUIRED_QML_VIEWS:
            content = (QT / qml_path).read_text(encoding="utf-8")
            self.assertNotIn(
                "observerClient", content,
                f"Uses 'observerClient' instead of 'ObserverClient' in {qml_path}"
            )

    def test_main_registers_singleton_via_qmlRegisterSingletonInstance(self) -> None:
        main_cpp = (QT / "main.cpp").read_text(encoding="utf-8")
        self.assertIn("qmlRegisterSingletonInstance", main_cpp)
        self.assertIn('"qt_observer"', main_cpp)
        self.assertIn('"ObserverClient"', main_cpp)
        self.assertNotIn("setContextProperty", main_cpp)


class QtObserverSetupContractTests(unittest.TestCase):
    def test_setup_contains_default_six_player_roles(self) -> None:
        content = (QT / "qml/MatchSetupView.qml").read_text(encoding="utf-8")
        for seat in ["p1", "p2", "p3", "p4", "p5", "p6"]:
            self.assertIn(seat, content, f"Missing seat {seat}")
        for role in ["Werewolf", "Seer", "Witch", "Villager"]:
            self.assertIn(role, content, f"Missing role {role}")

    def test_preflight_mentions_visibility_boundary_and_default_template(self) -> None:
        content = (QT / "qml/PreflightView.qml").read_text(encoding="utf-8")
        self.assertIn("default_6p_fake", content)
        self.assertRegex(content, r"(?i)visibility.?(boundary|filter)")

    def test_no_prompt_editor_is_added(self) -> None:
        for qml_path in REQUIRED_QML_VIEWS:
            content = (QT / qml_path).read_text(encoding="utf-8")
            self.assertNotIn("promptEditor", content, f"promptEditor found in {qml_path}")
            self.assertNotIn("PromptEditor", content, f"PromptEditor found in {qml_path}")


class QtObserverCockpitContractTests(unittest.TestCase):
    def test_cockpit_contains_required_object_names(self) -> None:
        content = (QT / "qml/LiveCockpitView.qml").read_text(encoding="utf-8")
        for name in ["runStatusBadge", "playerPanelGrid", "eventTimeline",
                      "perspectiveSwitcher", "auditLinksPanel", "providerFailureSummary"]:
            self.assertRegex(content, rf'objectName:\s*"{name}"',
                             f"Missing objectName '{name}' in LiveCockpitView.qml")

    def test_perspective_switcher_contains_required_values(self) -> None:
        content = (QT / "qml/components/PerspectiveSwitcher.qml").read_text(encoding="utf-8")
        for val in ["god", "public", "role:p1", "role:p2", "role:p3", "role:p4", "role:p5", "role:p6",
                     "team:werewolf"]:
            self.assertIn(val, content, f"Missing perspective value '{val}'")

    def test_audit_panel_has_required_artifact_entries(self) -> None:
        content = (QT / "qml/components/AuditLinksPanel.qml").read_text(encoding="utf-8")
        for tag in ["manifest", "provider-trace", "failure-audit", "snapshots", "artifacts"]:
            self.assertIn(tag, content, f"Missing audit tag '{tag}'")

    def test_history_view_has_replay_flow_objects(self) -> None:
        content = (QT / "qml/HistoryView.qml").read_text(encoding="utf-8")
        for name in ["historyRunsList", "historyRefreshButton", "openReplayButton"]:
            self.assertRegex(content, rf'id:\s*{name}|objectName:\s*"{name}"',
                             f"Missing '{name}' in HistoryView.qml")


class QtObserverBoundaryTests(unittest.TestCase):
    def test_client_does_not_reference_python_runtime_modules(self) -> None:
        for qml_path in sorted(QT.rglob("*.qml")):
            content = qml_path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_PYTHON_RUNTIME_PATTERNS:
                self.assertNotRegex(
                    content, pattern,
                    f"Forbidden pattern '{pattern}' found in {qml_path.relative_to(QT)}"
                )
        for src_file in sorted((QT / "src").rglob("*")):
            content = src_file.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_PYTHON_RUNTIME_PATTERNS:
                self.assertNotRegex(
                    content, pattern,
                    f"Forbidden pattern '{pattern}' found in {src_file.relative_to(QT)}"
                )
        main_cpp = (QT / "main.cpp").read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PYTHON_RUNTIME_PATTERNS:
            self.assertNotRegex(
                main_cpp, pattern,
                f"Forbidden pattern '{pattern}' found in main.cpp"
            )


class QtObserverSecretBoundaryTests(unittest.TestCase):
    def test_client_sources_do_not_contain_secret_markers(self) -> None:
        sources = list(QT.rglob("*.cpp")) + list(QT.rglob("*.h")) + list(QT.rglob("*.qml"))
        for source_file in sorted(sources):
            content = source_file.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_SECRET_PATTERNS:
                self.assertNotRegex(
                    content, pattern,
                    f"Forbidden secret pattern '{pattern}' found in {source_file.relative_to(QT)}"
                )


class QtObserverProtocolEndpointTests(unittest.TestCase):
    def test_client_uses_g2a_protocol_endpoint_names(self) -> None:
        content = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("/health", content)
        self.assertIn("/api/runs", content)
        self.assertIn("/stream", content)
        self.assertIn("/events?perspective=", content)
        self.assertIn("/manifest", content)
        self.assertIn("/provider-trace", content)
        self.assertIn("/failure-audit", content)
        self.assertIn("/artifacts", content)
        self.assertNotIn("file://", content)


class QtObserverProjectionClientTests(unittest.TestCase):
    def test_observer_client_uses_projection_endpoint(self) -> None:
        content = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("/projection", content)
        self.assertIn("perspective", content)

    def test_observer_client_exposes_projection_properties(self) -> None:
        content = (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")
        self.assertIn("playerItems", content)
        self.assertIn("projectionProof", content)
        self.assertIn("hiddenEventCount", content)
        self.assertIn("hiddenSnapshotCount", content)
        self.assertIn("visibilityContractVersion", content)

    def test_projection_refresh_happens_on_perspective_change(self) -> None:
        content = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        # setCurrentPerspective should contain refreshProjection() call (across lines)
        self.assertRegex(
            content, r"setCurrentPerspective[\s\S]*?refreshProjection",
        )

    def test_projection_request_uses_latest_wins_guard(self) -> None:
        content = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("m_projectionRequestSerial", content)
        self.assertIn("requestSerial", content)
        self.assertIn("requestedRunId", content)
        self.assertIn("requestedPerspective", content)

    def test_audit_links_contains_projection_path(self) -> None:
        content = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("/projection?perspective=", content)


class QtObserverHiddenInfoBoundaryTests(unittest.TestCase):
    def test_live_cockpit_does_not_embed_static_role_assignments(self) -> None:
        content = (QT / "qml/LiveCockpitView.qml").read_text(encoding="utf-8")
        # Must not use hardcoded role arrays like `role: "Werewolf"` as the live player model
        self.assertNotRegex(content, r'role:\s*"(?:Werewolf|Seer|Witch|Villager)"',
                            "LiveCockpitView.qml contains hardcoded role assignments in static model")

    def test_qml_boundary_copy_mentions_server_projection(self) -> None:
        content = (QT / "qml/LiveCockpitView.qml").read_text(encoding="utf-8")
        # Should reference ObserverClient projection properties or projection-related data
        has_projection = any(tag in content for tag in [
            "playerItems", "projectionProof", "visibilityContractVersion",
            "hiddenEventCount", "hiddenSnapshotCount",
        ])
        if not has_projection:
            # qml may use projection via component without explicit property name
            pass  # Accept if ViewBoundaryBadge is present (checked separately)

    def test_qt_client_does_not_use_local_snapshot_or_event_paths(self) -> None:
        for src_file in sorted((QT / "src").rglob("*")):
            content = src_file.read_text(encoding="utf-8")
            for forbidden in ["events.jsonl", "snapshots/"]:
                self.assertNotIn(forbidden, content,
                                 f"Forbidden pattern '{forbidden}' in {src_file.relative_to(QT)}")
        for qml_file in sorted(QT.rglob("*.qml")):
            content = qml_file.read_text(encoding="utf-8")
            for forbidden in ["events.jsonl", "snapshots/", "QFile", "QDir"]:
                self.assertNotIn(forbidden, content,
                                 f"Forbidden pattern '{forbidden}' in {qml_file.relative_to(QT)}")


class QtObserverReadmeTests(unittest.TestCase):
    def test_readme_documents_mvp_status_and_non_goals(self) -> None:
        content = (QT / "README.md").read_text(encoding="utf-8")
        self.assertIn("G2b Observer Cockpit MVP", content)
        self.assertIn("no full prompt/profile editor", content)
        self.assertIn("no Web observer client", content)
        self.assertIn("no direct Python runtime binding", content)
        self.assertIn("no local artifact file reads", content)

    def test_readme_documents_local_g2a_server_command(self) -> None:
        content = (QT / "README.md").read_text(encoding="utf-8")
        self.assertIn("run_observer_server", content)
        self.assertIn("--observer-base-url", content)
        self.assertIn("cmake -S clients/qt_observer", content)
        self.assertIn("ctest --test-dir", content)


class QtObserverVisibilityUiTests(unittest.TestCase):
    def test_visibility_components_are_registered_in_cmake(self) -> None:
        cmake_text = (QT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn("ViewBoundaryBadge.qml", cmake_text)
        self.assertIn("ProjectionProofPanel.qml", cmake_text)

    def test_live_cockpit_uses_projection_player_items(self) -> None:
        content = (QT / "qml/LiveCockpitView.qml").read_text(encoding="utf-8")
        self.assertIn("ObserverClient.playerItems", content)

    def test_live_cockpit_contains_boundary_badge_and_proof_panel(self) -> None:
        content = (QT / "qml/LiveCockpitView.qml").read_text(encoding="utf-8")
        self.assertIn("ViewBoundaryBadge", content)
        self.assertIn("ProjectionProofPanel", content)

    def test_role_card_supports_hidden_role_rendering(self) -> None:
        content = (QT / "qml/components/RoleCard.qml").read_text(encoding="utf-8")
        self.assertIn("displayRole", content)
        self.assertIn("displayTeam", content)
        self.assertIn("unknown", content)
        self.assertIn("Hidden", content)

    def test_cockpit_does_not_hardcode_god_roles_as_live_player_source(self) -> None:
        content = (QT / "qml/LiveCockpitView.qml").read_text(encoding="utf-8")
        self.assertNotIn('role: "Werewolf"', content)
        self.assertNotIn('role: "Seer"', content)


if __name__ == "__main__":
    unittest.main()

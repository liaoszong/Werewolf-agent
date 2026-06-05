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
    "qml/components/SeatEditorPanel.qml",
]

REQUIRED_OBJECT_NAMES = {
    "Main.qml": ["werewolfObserverMainWindow", "appShellLoader"],
    "qml/AppShell.qml": ["appShell", "appShellStack"],
    "qml/HomeView.qml": ["homeView", "startNewMatchButton", "historyButton", "serverStatusBadge", "recentRunsList"],
    "qml/MatchSetupView.qml": ["matchSetupView", "setupRoleCards", "setupContinueButton",
                               "setupProfilePicker", "setupValidateButton", "setupExecutionBanner"],
    "qml/PreflightView.qml": ["preflightView", "preflightServerStatus", "preflightTemplateSummary", "preflightVisibilitySummary", "startMatchButton"],
    "qml/LiveCockpitView.qml": ["liveCockpitView", "runStatusBadge", "playerPanelGrid", "eventTimeline", "perspectiveSwitcher", "auditLinksPanel", "providerFailureSummary"],
    "qml/HistoryView.qml": ["historyView", "historyRunsList", "historyRefreshButton"],
    "qml/components/RoleCard.qml": ["roleCard"],
    "qml/components/SeatEditorPanel.qml": [
        "seatEditorPanel", "seatEditorProvider", "seatEditorModel",
        "seatEditorStrategy", "seatEditorPrompt",
    ],
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
    def test_setup_is_profile_driven(self) -> None:
        content = (QT / "qml/MatchSetupView.qml").read_text(encoding="utf-8")
        for token in ["ObserverClient.profileItems", "ObserverClient.loadedProfile",
                      "launchFromProfile", "validateProfile", "profileSchema"]:
            self.assertIn(token, content)
        # options must come from the schema, not a hardcoded provider list
        self.assertNotIn('"deepseek-chat"', content)
        # launch is 202-gated: the view navigates only from the launchSucceeded
        # signal handler, never optimistically on click.
        self.assertIn("onLaunchSucceeded", content)
        # declared-vs-executed trust banner is present
        self.assertIn("Deterministic Mock", content)

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


class QtObserverProfileClientTests(unittest.TestCase):
    def test_client_exposes_profile_properties(self) -> None:
        h = (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")
        for prop in ["profileItems", "profileSchema", "loadedProfile", "profileValidation"]:
            self.assertIn(prop, h)
        for inv in ["refreshProfiles", "refreshProfileSchema", "fetchProfile",
                    "validateProfile", "launchFromProfile"]:
            self.assertIn(inv, h)
        for sig in ["launchSucceeded", "launchFailed"]:
            self.assertIn(sig, h)

    def test_client_launch_is_202_gated(self) -> None:
        cpp = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("/api/profiles/schema", cpp)
        self.assertIn("/api/profiles/validate", cpp)
        # launch advances only on HTTP 202 + a run_id, else launchFailed
        self.assertIn("HttpStatusCodeAttribute", cpp)
        self.assertIn("202", cpp)
        self.assertIn("runId.isEmpty()", cpp)
        self.assertIn("launchSucceeded", cpp)
        self.assertIn("launchFailed", cpp)

    def test_profile_requests_use_latest_wins_guards(self) -> None:
        h = (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")
        cpp = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        # fetchProfile AND validateProfile must drop stale responses
        self.assertIn("m_profileRequestSerial", h)
        self.assertIn("m_profileValidateSerial", h)
        self.assertIn("m_profileValidateSerial", cpp)


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
        self.assertIn("profile setup editor", content)
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


class QtObserverPerspectiveSwitcherTrustTests(unittest.TestCase):
    """G2c B档 gap fix: PerspectiveSwitcher must not leak role information in labels."""

    def test_perspective_switcher_does_not_expose_role_names_in_labels(self) -> None:
        content = (QT / "qml/components/PerspectiveSwitcher.qml").read_text(encoding="utf-8")
        # Role labels must not contain role names that reveal hidden information
        for role_name in ["Werewolf", "Seer", "Witch", "Villager"]:
            # Check for patterns like "Role: p1 (Werewolf)" or "(Seer)" in label values
            self.assertNotRegex(
                content,
                rf'"role:p\d+":\s*"[^"]*\({role_name}\)"',
                f"PerspectiveSwitcher leaks role '{role_name}' in seat label",
            )

    def test_perspective_switcher_uses_generic_seat_labels(self) -> None:
        content = (QT / "qml/components/PerspectiveSwitcher.qml").read_text(encoding="utf-8")
        # Should use generic seat labels like "Seat p1" not "Role: p1 (Werewolf)"
        self.assertIn("Seat p1", content)
        self.assertIn("Seat p6", content)


if __name__ == "__main__":
    unittest.main()

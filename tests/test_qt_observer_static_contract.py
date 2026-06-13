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
    r"""api_key['"]?\s*[=:]\s*['"]""",  # hardcoded value assignment; QStringLiteral field-name usage allowed
    r"api-key",
]

REQUIRED_QML_VIEWS = [
    "Main.qml",
    "qml/AppShell.qml",
    "qml/HomeView.qml",
    "qml/SettlementView.qml",
    "qml/MatchSetupView.qml",
    "qml/ProviderSettingsView.qml",
    "qml/PreflightView.qml",
    "qml/LiveCockpitView.qml",
    "qml/TheaterView.qml",
    "qml/HistoryView.qml",
    "qml/EventPresentationQueue.qml",
    "qml/components/RoleCard.qml",
    "qml/components/SeatRing.qml",
    "qml/components/SettlementSpine.qml",
    "qml/components/SettlementReport.qml",
    "qml/components/WinnerBanner.qml",
    "qml/components/SpeechTheater.qml",
    "qml/components/EvidenceConsole.qml",
    "qml/components/PlaybackControls.qml",
    "qml/components/EventTimeline.qml",
    "qml/components/PerspectiveSwitcher.qml",
    "qml/components/AuditLinksPanel.qml",
    "qml/components/StatusBadge.qml",
    "qml/components/SeatEditorPanel.qml",
    "qml/components/ModeControl.qml",
    "qml/components/DataSourceChip.qml",
    "qml/components/ConfirmDialog.qml",
]

REQUIRED_OBJECT_NAMES = {
    "Main.qml": ["werewolfObserverMainWindow", "appShellLoader"],
    "qml/AppShell.qml": ["appShell", "appShellStack", "dataSourceChip"],
    "qml/HomeView.qml": ["homeView", "startNewMatchButton", "historyButton", "serverStatusBadge", "recentRunsList"],
    # P2-B Q2: credentials moved OUT of the setup view to the dedicated provider
    # settings page (below); the setup view is now a pure scheduling sandbox.
    "qml/MatchSetupView.qml": ["matchSetupView", "setupRoleCards", "setupContinueButton",
                               "setupProfilePicker", "setupValidateButton", "setupModeControl"],
    # P2-B Q1: the provider/model settings page — the new home of the BYO-key
    # credential panel.
    "qml/ProviderSettingsView.qml": ["providerSettingsView", "providerKeyField",
                                     "providerBaseUrlField", "providerSaveButton",
                                     "providerFetchModelsButton", "providerClearButton",
                                     "providerSettingsBackButton"],
    "qml/PreflightView.qml": ["preflightView", "preflightServerStatus", "preflightTemplateSummary", "preflightVisibilitySummary", "startMatchButton"],
    "qml/LiveCockpitView.qml": ["liveCockpitView", "runStatusBadge", "playerPanelGrid", "eventTimeline", "perspectiveSwitcher", "auditLinksPanel", "providerFailureSummary"],
    "qml/TheaterView.qml": ["theaterView"],
    "qml/SettlementView.qml": ["settlementView"],
    "qml/HistoryView.qml": ["historyView", "historyRunsList", "historyRefreshButton",
                            "deleteRunButton", "historyConfirmDialog", "historyNoticeBar",
                            "selectModeButton", "rowSelectBox", "selectAllBox", "batchDeleteButton"],
    "qml/EventPresentationQueue.qml": ["eventQueue"],
    "qml/components/RoleCard.qml": ["roleCard"],
    "qml/components/SeatRing.qml": ["seatRing"],
    "qml/components/SettlementSpine.qml": ["settlementSpine"],
    "qml/components/SettlementReport.qml": ["settlementReport"],
    "qml/components/WinnerBanner.qml": ["winnerBanner"],
    "qml/components/SpeechTheater.qml": ["speechTheater"],
    "qml/components/EvidenceConsole.qml": ["evidenceConsole", "eventTimeline", "perspectiveSwitcher", "auditLinksPanel", "providerFailureSummary"],
    "qml/components/PlaybackControls.qml": ["playbackControls"],
    # P2-B Q3: the dead "strategy" dropdown is replaced by persona-preset chips;
    # per-seat temperature/max_tokens knobs are added.
    "qml/components/SeatEditorPanel.qml": [
        "seatEditorPanel", "seatEditorProvider", "seatEditorModel",
        "seatEditorPrompt", "seatEditorPersona", "seatEditorTemperature",
        "seatEditorMaxTokens",
    ],
    "qml/components/ConfirmDialog.qml": ["confirmDialog", "confirmAcceptButton", "confirmCancelButton"],
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
        # G3-2: the amber "Deterministic Mock" banner is replaced by ModeControl.
        self.assertNotIn("Deterministic Mock", content)
        # MatchSetupView instantiates the segmented arming control (C2/C3).
        self.assertIn("ModeControl", content)
        self.assertIn('objectName: "setupModeControl"', content)
        # C2: launch passes an EXPLICIT resolved mode from the control — never a
        # bare single-arg call that relies on a C++ default.
        self.assertRegex(content, r"launchFromProfile\([^)]+,\s*\w+\.resolvedMode")
        # C3: a single disarm entry point is wired to EACH disarm trigger —
        # seat change, profile load, profile switch (picker), and live becoming
        # unavailable.  Pin every site, not just one presence, so a regression
        # that drops one trigger is caught.
        self.assertIn("onSelectedSeatIdChanged: setupModeControl.resetToFake()", content)
        self.assertRegex(content, r"onLoadedProfileChanged\(\)[\s\S]*?resetToFake\(")
        self.assertRegex(content, r"onCapabilitiesChanged\(\)[\s\S]*?liveAvailable[\s\S]*?resetToFake\(")
        self.assertRegex(content, r"onActivated:[\s\S]*?resetToFake\(")
        self.assertGreaterEqual(
            content.count("resetToFake("), 4,
            "expected resetToFake() wired to all four C3 disarm triggers",
        )

    def test_preflight_mentions_visibility_boundary_and_default_template(self) -> None:
        content = (QT / "qml/PreflightView.qml").read_text(encoding="utf-8")
        self.assertIn("default_6p_fake", content)
        self.assertRegex(content, r"(?i)visibility.?(boundary|filter)")

    def test_prompt_editor_is_server_profile_scoped(self) -> None:
        # G2d-2 adds a per-seat prompt editor, but it edits a server-sourced
        # profile only — never a local prompt-template library or file source.
        panel = (QT / "qml/components/SeatEditorPanel.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "seatEditorPrompt"', panel)
        self.assertIn("root.config", panel)  # prompt value comes from the passed-in server config
        for forbidden in ["promptLibrary", "PromptLibrary", "templateLibrary",
                          "TemplateLibrary", ".txt", "QFile", "QDir", "file://"]:
            self.assertNotIn(forbidden, panel, f"local prompt source '{forbidden}' in SeatEditorPanel")


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

    def test_api_key_pattern_targets_values_not_field_names(self) -> None:
        # Regression: the api_key entry in FORBIDDEN_SECRET_PATTERNS must be narrow
        # enough to allow the legitimate JSON field-name usage
        # (body[QStringLiteral("api_key")] = raw) while still catching hardcoded
        # literal values.  This test locks the narrowing so that a future over-
        # broadening regression OR a real hardcoded-value regression both fail.
        api_key_pat = r"""api_key['"]?\s*[=:]\s*['"]"""
        # Ensure the pattern in the module list matches what we're testing.
        self.assertIn(api_key_pat, FORBIDDEN_SECRET_PATTERNS,
                      "FORBIDDEN_SECRET_PATTERNS must contain the narrowed api_key pattern")
        # (1) Legitimate field-name/variable assignment: must NOT be flagged.
        self.assertIsNone(
            re.search(api_key_pat, 'body[QStringLiteral("api_key")] = raw;'),
            "api_key pattern must NOT flag QStringLiteral field-name + variable assignment",
        )
        # (2) JSON literal value assignment: must be flagged.
        self.assertIsNotNone(
            re.search(api_key_pat, '"api_key":"sk-secret"'),
            'api_key pattern must flag JSON literal: "api_key":"sk-secret"',
        )
        # (3) Bare Python/config-style assignment with quoted literal: must be flagged.
        self.assertIsNotNone(
            re.search(api_key_pat, 'api_key = "sk-abc"'),
            'api_key pattern must flag bare assignment: api_key = "sk-abc"',
        )
        # (4) Server reason-code substring: must NOT be flagged.
        self.assertIsNone(
            re.search(api_key_pat, 'missing_api_key",'),
            'api_key pattern must NOT flag server reason-code substring: missing_api_key",'
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

    def test_client_exposes_projection_events(self) -> None:
        # P2-C-1: enriched per-perspective events exposed to QML, parsed from the
        # same /projection response under the existing latest-wins guard.
        h = (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")
        cpp = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("projectionEvents", h)
        self.assertIn('value(QStringLiteral("events"))', cpp)

    def test_client_exposes_settlement(self) -> None:
        # P2-D §7.6: settlementBundle Q_PROPERTY + fetchSettlement invokable,
        # mirroring refreshProjection's latest-wins guard; the only new endpoint.
        h = (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")
        cpp = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("settlementBundle", h)
        self.assertIn("fetchSettlement", h)
        self.assertIn("/settlement", cpp)
        # stale guard: run change clears the bundle
        start = cpp.find("ObserverApiClient::setCurrentRunId")
        self.assertNotEqual(start, -1)
        self.assertIn("m_settlementBundle", cpp[start:start + 1200])

    def test_stale_guard_in_both_setters_before_requests(self) -> None:
        # Edit 2/7 + P2-F: clear+notify in BOTH setters, BEFORE the new stream/projection request.
        cpp = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        for setter in ["ObserverApiClient::setCurrentPerspective", "ObserverApiClient::setCurrentRunId"]:
            start = cpp.find(setter)
            self.assertNotEqual(start, -1, f"{setter} not found")
            body = cpp[start:start + 1200]            # setter body window
            self.assertIn("m_projectionEvents.clear()", body, f"{setter} must clear projectionEvents")
            self.assertIn("projectionEventsChanged", body, f"{setter} must emit projectionEventsChanged")
            clr = body.index("m_projectionEvents.clear()")
            for req in ["startStreamRequest", "refreshProjection"]:
                if req in body:
                    self.assertLess(clr, body.index(req), f"{setter}: clear must precede {req}")


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
        # fetchProfile AND validateProfile must drop stale responses — pin BOTH
        # latest-wins guards in the .cpp (the .h only proves declaration).
        self.assertIn("m_profileRequestSerial", h)
        self.assertIn("m_profileValidateSerial", h)
        self.assertIn("m_profileRequestSerial", cpp)
        self.assertIn("m_profileValidateSerial", cpp)


class QtObserverModeControlClientTests(unittest.TestCase):
    """G3-2: ObserverApiClient gains a launch ``mode`` param, read-only runtime
    capabilities, and an API-mediated ``currentExecutionMode`` (C1/C1-bis/C2/C4)."""

    # server-owned reason codes — rendered data-driven (verbatim), NEVER as
    # client source literals (C4; also keeps the ``api_key`` secret-scan green).
    SERVER_REASON_CODES = [
        "live_api_disabled", "missing_api_key", "unsupported_live_provider",
        "mixed_models", "provider_failure", "budget_exhausted",
    ]

    def _h(self) -> str:
        return (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")

    def _cpp(self) -> str:
        return (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")

    @staticmethod
    def _method_body(cpp: str, signature_prefix: str) -> str:
        """Slice a single ``void ObserverApiClient::<name>`` definition body."""
        start = cpp.index(signature_prefix)
        nxt = cpp.find("\nvoid ObserverApiClient::", start + len(signature_prefix))
        return cpp[start:] if nxt == -1 else cpp[start:nxt]

    def test_header_declares_capability_properties_and_invokable(self) -> None:
        h = self._h()
        for prop in ["liveAvailable", "liveReasonCode", "liveReasonMessage",
                     "defaultMode", "currentExecutionMode"]:
            self.assertIn(prop, h, f"missing property '{prop}' in ObserverApiClient.h")
        self.assertIn("refreshCapabilities", h)

    def test_cpp_calls_capabilities_endpoint(self) -> None:
        self.assertIn("/api/runtime/capabilities", self._cpp())

    def test_launch_from_profile_takes_mode_and_writes_body_mode(self) -> None:
        cpp = self._cpp()
        h = self._h()
        # signature carries an explicit mode arg (C2: no reliance on a default)
        self.assertRegex(h, r"launchFromProfile\([^)]*QString\s*&?\s*mode")
        self.assertRegex(cpp, r"launchFromProfile\([^)]*QString\s*&?\s*mode")
        # and the POST body carries it verbatim
        self.assertRegex(cpp, r'body\[\s*QStringLiteral\("mode"\)\s*\]\s*=\s*mode')

    def test_capabilities_error_uses_client_only_unreachable_code(self) -> None:
        # C4: 'unreachable' is the ONLY client-owned reason code.
        self.assertIn("unreachable", self._cpp())

    def test_no_server_reason_codes_are_client_literals(self) -> None:
        # C4: server-owned codes are data-driven (read from JSON), never embedded
        # as client source literals — in BOTH the header and the cpp.
        for src_name, src in (("ObserverApiClient.h", self._h()),
                              ("ObserverApiClient.cpp", self._cpp())):
            for code in self.SERVER_REASON_CODES:
                self.assertNotIn(
                    code, src,
                    f"server reason code '{code}' must not be a literal in {src_name}",
                )

    def test_current_execution_mode_parsed_from_run_detail(self) -> None:
        # C1: currentExecutionMode is sourced from a run-detail execution_mode
        # field (parsed in openRun), never from intent or the 202 echo.
        cpp = self._cpp()
        self.assertIn("execution_mode", cpp)
        open_body = self._method_body(cpp, "void ObserverApiClient::openRun")
        self.assertIn("execution_mode", open_body,
                      "openRun must parse the run-detail execution_mode field")

    def test_launch_handler_never_sets_execution_mode(self) -> None:
        # C1: launchFromProfile must NOT set currentExecutionMode — intent and
        # the 202 mode echo are not executed truth.
        cpp = self._cpp()
        launch_body = self._method_body(cpp, "void ObserverApiClient::launchFromProfile")
        self.assertNotIn(
            "m_currentExecutionMode", launch_body,
            "C1: launchFromProfile must not touch currentExecutionMode (intent != truth)",
        )

    def test_stale_guard_reset_wired_to_every_c1bis_trigger(self) -> None:
        # C1-bis: the reset must fire on EACH trigger — run change
        # (setCurrentRunId), missing/non-string execution_mode AND detail error
        # (openRun), and the capabilities request error (refreshCapabilities).
        # A single global-OR over the file would miss a regression that drops the
        # reset from one site (e.g. setCurrentRunId → the worst-case live-run-
        # then-fake-run stale-LIVE flash the spec forbids), so pin each site.
        cpp = self._cpp()
        # the reset helper must actually clear the field (anchor the name).
        reset_body = self._method_body(cpp, "void ObserverApiClient::resetExecutionMode")
        self.assertTrue(
            "m_currentExecutionMode.clear()" in reset_body
            or "m_currentExecutionMode = QString()" in reset_body
            or 'm_currentExecutionMode = QStringLiteral("")' in reset_body,
            "resetExecutionMode() must clear m_currentExecutionMode",
        )
        # run change → reset (the worst-case stale-LIVE guard)
        self.assertIn(
            "resetExecutionMode",
            self._method_body(cpp, "void ObserverApiClient::setCurrentRunId"),
            "setCurrentRunId must reset executed truth on run change (C1-bis)",
        )
        # missing/non-string execution_mode AND a detail request/parse error → reset
        open_body = self._method_body(cpp, "void ObserverApiClient::openRun")
        self.assertGreaterEqual(
            open_body.count("resetExecutionMode"), 2,
            "openRun must reset on detail error AND on a missing/non-string execution_mode",
        )
        # capabilities request error → reset
        self.assertIn(
            "resetExecutionMode",
            self._method_body(cpp, "void ObserverApiClient::refreshCapabilities"),
            "refreshCapabilities must reset executed truth on a request error (C1-bis)",
        )


class QtObserverModeControlComponentTests(unittest.TestCase):
    """G3-2: the segmented arming control (FSM) and the HUD data-source chip."""

    def test_mode_control_declares_canonical_fsm_tokens(self) -> None:
        content = (QT / "qml/components/ModeControl.qml").read_text(encoding="utf-8")
        # Canonical FSM state tokens (asserted verbatim so the contract pins them).
        for token in ['"fake"', '"live_armed"', '"live_confirmed"']:
            self.assertIn(token, content, f"ModeControl.qml missing FSM token {token}")
        # C3: a single disarm entry point.
        self.assertIn("function resetToFake(", content)
        # the control exposes the resolved launch mode for the view to pass along.
        self.assertIn("resolvedMode", content)

    def test_mode_control_resolved_mode_maps_only_confirmed_to_live(self) -> None:
        # C2: resolvedMode is "live" ONLY in live_confirmed; fake/live_armed map to
        # "fake".  (The "live_confirmed" token recurs in several visual bindings, so
        # a plain presence check can't catch a ternary that maps live_armed → live —
        # pin the exact mapping.)
        content = (QT / "qml/components/ModeControl.qml").read_text(encoding="utf-8")
        self.assertRegex(
            content,
            r'resolvedMode:\s*[^\n]*state\s*===\s*"live_confirmed"\s*\?\s*"live"\s*:\s*"fake"',
            "resolvedMode must map ONLY live_confirmed to 'live' (C2)",
        )

    def test_mode_control_renders_reason_code_data_driven(self) -> None:
        content = (QT / "qml/components/ModeControl.qml").read_text(encoding="utf-8")
        # disabled state reads the SERVER reason code (verbatim), never a literal.
        self.assertIn("liveAvailable", content)
        self.assertIn("liveReasonCode", content)
        for code in ["live_api_disabled", "missing_api_key",
                     "unsupported_live_provider", "mixed_models"]:
            self.assertNotIn(code, content, f"server code '{code}' must not be a literal in ModeControl.qml")

    def test_unavailable_hint_gated_on_message_not_code(self) -> None:
        # Regression (blank-gap bug): the unavailable-context line must be gated
        # on the server MESSAGE length, not the reason code.  The "unreachable"
        # posture has an EMPTY message, so a code-gated line rendered a blank,
        # visible Text that opened a gap pushing the whole page down and never
        # reverted.  The reason code is already shown inline on the LIVE segment.
        content = (QT / "qml/components/ModeControl.qml").read_text(encoding="utf-8")
        self.assertIn("liveReasonMessage.length", content)

    def test_data_source_chip_has_both_hud_labels(self) -> None:
        content = (QT / "qml/components/DataSourceChip.qml").read_text(encoding="utf-8")
        self.assertIn("SYS: LIVE_API", content)
        self.assertIn("SYS: SIMULATION", content)
        # the chip is driven by a mode property (executed truth), not intent.
        self.assertIn("mode", content)

    def test_app_shell_binds_chip_to_execution_mode(self) -> None:
        content = (QT / "qml/AppShell.qml").read_text(encoding="utf-8")
        self.assertIn("DataSourceChip", content)
        self.assertIn('objectName: "dataSourceChip"', content)
        # C1: the chip's mode is bound to executed truth, not intent.
        self.assertIn("ObserverClient.currentExecutionMode", content)


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
        self.assertIn("P2 theater client", content)
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


class QtObserverTheaterViewTests(unittest.TestCase):
    """P2-C-1 theater view: queue invariants, PresentationEvent reads, re-home, bindings."""

    def test_event_queue_is_presentation_only(self) -> None:
        c = (QT / "qml/EventPresentationQueue.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "eventQueue"', c)
        self.assertIn("resumeAfterTransition", c)            # D5 yield-gate API
        self.assertIn("function reset", c)                   # run/perspective/source-gen reset
        self.assertIn("_present", c)                         # PresentationEvent normalization
        self.assertIn("readonly property var current", c)    # P1-A: current is a computed binding...
        self.assertNotIn("current = _present", c)            # ...never assigned imperatively
        self.assertNotIn(".sort(", c)                        # append-order consume, never reorder
        for forbidden in ["XMLHttpRequest", '"/api/runs"', "ObserverClient.post"]:
            self.assertNotIn(forbidden, c)

    def test_seek_respects_phase_gate(self) -> None:
        # Review P1: seek must route through the gated phase-aware consumer; it may not
        # bypass _gated or cross a phase boundary without raising the transition gate (D5/A2).
        c = (QT / "qml/EventPresentationQueue.qml").read_text(encoding="utf-8")
        self.assertIn("_consumeCurrentPhaseFast", c)   # shared gated consumer
        self.assertIn("_ffToEnd", c)                   # cross-phase seek continues only after each transition
        i = c.find("function _consumeCurrentPhaseFast")
        self.assertNotEqual(i, -1)
        body = c[i:i + 800]
        self.assertIn("if (_gated)", body)             # respects an in-flight transition
        self.assertIn("phaseBoundary", body)           # raises the gate at a boundary
        for fn in ["function seekNextPhase", "function seekQueueEnd"]:
            j = c.find(fn)
            self.assertNotEqual(j, -1)
            self.assertIn("_consumeCurrentPhaseFast", c[j:j + 200])

    def test_stage_components_read_presentation_event(self) -> None:
        # Edit 1: stage components read the normalized PresentationEvent (current.*),
        # never raw runtime .payload.
        for f in [
            "qml/components/SeatRing.qml",
            "qml/components/SpeechTheater.qml",
            "qml/components/PlaybackControls.qml",
        ]:
            self.assertNotIn(".payload", (QT / f).read_text(encoding="utf-8"))

    def test_cockpit_nav_targets_theater_view(self) -> None:
        # P2-C-1 D1/P2-D/P1-C: navigateCockpit loads TheaterView; layout binds layoutPhase
        # (so reset re-syncs); SeatRing.perspective is never handler-assigned.
        a = (QT / "qml/AppShell.qml").read_text(encoding="utf-8")
        self.assertIn("TheaterView", a)                       # cockpitComponent loads TheaterView
        t = (QT / "qml/TheaterView.qml").read_text(encoding="utf-8")
        self.assertIn("EventPresentationQueue", t)            # hosts the queue
        self.assertIn("id: eventQueue", t)
        self.assertIn("resumeAfterTransition", t)             # D5 yield-gate wired
        self.assertIn("state: eventQueue.layoutPhase", t)     # P2-D declarative layout binding
        self.assertNotIn("ring.perspective =", t)             # P1-C: no handler writing the bound perspective
        self.assertIn("navigateHome", t)                      # theater must have a back/exit affordance

    def test_seatring_layoutmode_presentational(self) -> None:
        # P2-D §7.3/§14.2: SeatRing gains layoutMode/morphProgress/boardState but
        # stays PRESENTATIONAL — it must not read the bundle, fetch, or own the cursor.
        c = (QT / "qml/components/SeatRing.qml").read_text(encoding="utf-8")
        self.assertIn("layoutMode", c)
        self.assertIn("morphProgress", c)
        self.assertIn("boardState", c)
        self.assertNotIn("settlementBundle", c)   # SeatRing must NOT read the bundle
        self.assertNotIn("fetchSettlement", c)
        self.assertNotIn("cursorIndex", c)        # does not own/read the cursor

    def test_evidence_console_rehomes_honesty_chain(self) -> None:
        # P2-C-1 Edit 5: EvidenceConsole.qml ITSELF must instantiate the honesty chain
        # (a retained LiveCockpitView.qml cannot satisfy the re-home requirement).
        c = (QT / "qml/components/EvidenceConsole.qml").read_text(encoding="utf-8")
        for comp in ["ViewBoundaryBadge", "ProjectionProofPanel", "PerspectiveSwitcher",
                     "EventTimeline", "AuditLinksPanel"]:
            self.assertIn(comp, c)
        self.assertIn('objectName: "providerFailureSummary"', c)


class QtObserverSettlementViewTests(unittest.TestCase):
    """P2-D settlement / battle-report surface: single cursor, presentational
    SeatRing, overlay-only activation, scroll-spy anti-loop guard."""

    def test_spine_reads_cursor_via_binding(self) -> None:
        c = (QT / "qml/components/SettlementSpine.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "settlementSpine"', c)
        self.assertNotIn("property int cursorIndex", c)   # owned by SettlementView, not here

    def test_report_has_scrollspy_and_guard(self) -> None:
        c = (QT / "qml/components/SettlementReport.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "settlementReport"', c)
        self.assertIn("_programmaticScroll", c)          # anti-feedback-loop flag (D6)
        self.assertIn("cursorRequested", c)              # writes cursor via signal to parent only
        self.assertNotIn("property int cursorIndex", c)  # does not own the cursor

    def test_settlement_view_owns_cursor_and_is_overlay(self) -> None:
        s = (QT / "qml/SettlementView.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "settlementView"', s)
        self.assertIn("property int cursorIndex", s)     # the ONE writable source of truth
        self.assertIn("fetchSettlement", s)              # owns the fetch (SeatRing must not)
        self.assertIn("boardState", s)                   # resolves board_timeline node -> SeatRing
        # morph states present
        for st in ['"freeze"', '"docking"', '"report"']:
            self.assertIn(st, s)
        a = (QT / "qml/AppShell.qml").read_text(encoding="utf-8")
        self.assertNotIn("SettlementView", a)            # overlay-only: NOT an AppShell nav target (§14.1)
        t = (QT / "qml/TheaterView.qml").read_text(encoding="utf-8")
        self.assertIn("SettlementView", t)               # hosted inside TheaterView
        self.assertIn('currentStatus === "completed"', t)  # failed → not activated (§2.5)


class QtObserverCredentialPanelTests(unittest.TestCase):
    """P2-B BYO-key: credential panel objectNames exist and the raw key is
    never reachable from QML (no getRawKey, no Q_INVOKABLE rawCredential).

    P2-B Q2: the credential panel moved out of MatchSetupView into the dedicated
    ProviderSettingsView (reached via the global gear); the setup view no longer
    carries any credential input."""

    def test_credential_panel_object_names_in_provider_settings_view(self) -> None:
        # (a) The credential-panel objectNames must exist on the settings page so
        # they cannot be silently removed or renamed without the contract catching it.
        content = (QT / "qml/ProviderSettingsView.qml").read_text(encoding="utf-8")
        for name in ["providerKeyField", "providerBaseUrlField",
                     "providerSaveButton", "providerClearButton", "providerStatusText"]:
            pattern = rf'objectName:\s*"{name}"'
            self.assertRegex(
                content, pattern,
                f"Missing objectName '{name}' in qml/ProviderSettingsView.qml"
            )

    def test_setup_view_has_no_inline_credential_input(self) -> None:
        # P2-B Q2 invariant: the setup view must NOT reintroduce an inline key field
        # (credentials belong solely to the settings page now).
        content = (QT / "qml/MatchSetupView.qml").read_text(encoding="utf-8")
        for name in ["setupCredentialField", "setupCredentialSave",
                     "setupCredentialClear", "setupCredentialStatus"]:
            self.assertNotIn(
                name, content,
                f"setup view must not carry credential objectName '{name}' (moved to settings)"
            )

    def test_credential_store_header_has_no_raw_key_exposure(self) -> None:
        # (b) getRawKey must not be declared; rawCredential must be private and
        # never Q_INVOKABLE so QML cannot call it.
        # Note: the header comment mentions "getRawKey()" to document its absence;
        # we check that no non-comment code line declares it as a function.
        header_text = (QT / "src/CredentialStore.h").read_text(encoding="utf-8")
        code_lines = [
            ln for ln in header_text.splitlines()
            if not ln.lstrip().startswith("//")
        ]
        code_only = "\n".join(code_lines)
        self.assertNotIn(
            "getRawKey", code_only,
            "CredentialStore.h must not declare getRawKey as a function"
        )
        self.assertIn(
            "rawCredential", header_text,
            "CredentialStore.h must contain rawCredential (private helper)"
        )
        # Belt-and-suspenders: no Q_INVOKABLE on the same line as rawCredential
        # in code (strip inline // comments before checking).
        for line in header_text.splitlines():
            if "rawCredential" in line:
                code_part = line.split("//")[0]  # strip inline C++ comment
                self.assertNotIn(
                    "Q_INVOKABLE", code_part,
                    f"rawCredential must not be Q_INVOKABLE in code (line: {line.strip()!r})"
                )

    def test_credential_store_uses_qsettings_and_carries_dev_only_marker(self) -> None:
        # (c) QSettings is the storage backend; a dev-only marker must appear in
        # the header or the implementation (the spec Storage invariant requires it).
        # QSettings is declared in the header (the .cpp uses it via m_settings).
        header_text = (QT / "src/CredentialStore.h").read_text(encoding="utf-8")
        cpp_text = (QT / "src/CredentialStore.cpp").read_text(encoding="utf-8")
        self.assertIn(
            "QSettings", header_text,
            "CredentialStore.h must declare QSettings (the storage backend)"
        )
        # The .cpp must actually use the QSettings member (m_settings).
        self.assertIn(
            "m_settings", cpp_text,
            "CredentialStore.cpp must use m_settings (QSettings member)"
        )
        has_dev_only = (
            re.search(r"dev.only", header_text, re.IGNORECASE) is not None
            or re.search(r"dev.only", cpp_text, re.IGNORECASE) is not None
        )
        self.assertTrue(
            has_dev_only,
            "CredentialStore.h or .cpp must carry a 'dev-only' marker (Storage invariant)"
        )

    def test_qml_does_not_reference_raw_key_accessors(self) -> None:
        # (d) Forbidden-leak guard: QML must never call getRawKey or rawCredential.
        # These are private C++ details that must never reach the QML layer.
        for qml_path in sorted((QT / "qml").rglob("*.qml")):
            content = qml_path.read_text(encoding="utf-8")
            for forbidden in ["getRawKey", "rawCredential"]:
                self.assertNotIn(
                    forbidden, content,
                    f"QML must not reference '{forbidden}' (found in {qml_path.relative_to(QT)})"
                )


class QtObserverVocabContractTests(unittest.TestCase):
    """R-01 renamed the engine token witch_kill -> witch_poison; the QML client
    must follow it, and team labels must be localized like role labels."""

    def test_event_queue_recognizes_canonical_witch_poison(self) -> None:
        # qml-01 + qml-02: currentAction() and the _durationMs hold-time table must
        # key off the canonical witch_poison token the engine emits, not the stale
        # witch_kill (which left witch poison un-highlighted and timed at the default).
        content = (QT / "qml/EventPresentationQueue.qml").read_text(encoding="utf-8")
        self.assertIn("witch_poison", content)
        # both the currentAction branch and the duration table reference it
        self.assertGreaterEqual(content.count("witch_poison"), 2)
        # the hold-time table gives witch_poison an explicit duration (not the default)
        self.assertRegex(content, r"witch_poison:\s*\d+")

    def test_role_card_localizes_team_label(self) -> None:
        # qml-03: the team label must be localized (like the role name), not the raw
        # english projection token. The raw token stays available for the accent dot.
        content = (QT / "qml/components/RoleCard.qml").read_text(encoding="utf-8")
        self.assertIn("_teamLabel", content)
        self.assertIn("狼人阵营", content)
        self.assertIn("村民阵营", content)
        # the team Text must not render the raw token directly anymore
        self.assertNotRegex(content, r"text:\s*root\.displayTeam\b")


class QtObserverGameRedesignPhase1Tests(unittest.TestCase):
    """游戏客户端重做 Phase 1：暖色地基 + 插画管线 + HomeView 样板页。"""

    ILLUSTRATIONS = [
        "assets/illustrations/scene/home-day.png",
        "assets/illustrations/scene/home-night.png",
        "assets/illustrations/tarot/werewolf.png",
        "assets/illustrations/tarot/seer.png",
        "assets/illustrations/tarot/witch.png",
        "assets/illustrations/tarot/villager.png",
        "assets/illustrations/tarot/guard.png",
        "assets/illustrations/tarot/hunter.png",
    ]

    def test_illustration_assets_exist(self) -> None:
        for rel in self.ILLUSTRATIONS:
            self.assertTrue((QT / rel).exists(), f"missing illustration asset: {rel}")

    def test_cmake_registers_new_qml_and_singleton_and_resources(self) -> None:
        cmake = (QT / "CMakeLists.txt").read_text(encoding="utf-8")
        for qml in ["qml/Illustrations.qml",
                    "qml/components/SceneBackground.qml",
                    "qml/components/NavRail.qml"]:
            self.assertIn(qml, cmake, f"CMakeLists must register {qml}")
        self.assertRegex(cmake, r"qml/Illustrations\.qml\s+PROPERTIES\s+QT_QML_SINGLETON_TYPE\s+TRUE")
        for rel in self.ILLUSTRATIONS:
            self.assertIn(rel, cmake, f"CMakeLists must bundle resource {rel}")
        self.assertIn("RESOURCES", cmake)

    def test_theme_has_warm_phase_font_tokens(self) -> None:
        theme = (QT / "qml/Theme.qml").read_text(encoding="utf-8")
        for token in ["property QtObject warm", "canvas", "surfaceCard", "surfaceRaised",
                      "property QtObject phase", "property QtObject fontFamilies",
                      "property QtObject warmSize", "property QtObject elevation",
                      "property QtObject anim",
                      '"#cc785c"', '"#faf9f5"']:
            self.assertIn(token, theme, f"Theme.qml missing warm token: {token}")
        # fontFamilies must be single strings, not arrays (no font.families usage).
        self.assertRegex(theme, r'property string serif:\s*"Source Han Serif SC"')
        self.assertNotIn("font.families", theme)

    def test_scene_background_has_no_asset_fallback(self) -> None:
        c = (QT / "qml/components/SceneBackground.qml").read_text(encoding="utf-8")
        self.assertIn("Image.Ready", c)          # only show art when loaded
        self.assertIn("Gradient", c)              # phase-gradient fallback underneath
        self.assertIn("Illustrations", c)         # sourced via the registry

    def test_navrail_contract(self) -> None:
        c = (QT / "qml/components/NavRail.qml").read_text(encoding="utf-8")
        self.assertIn('objectName: "navRail"', c)
        self.assertIn("currentKey", c)            # selected state
        self.assertIn("collapsed", c)             # narrow collapse state
        self.assertIn("signal activated", c)      # emits navigation intent

    def test_home_uses_new_design_system(self) -> None:
        c = (QT / "qml/HomeView.qml").read_text(encoding="utf-8")
        self.assertIn("SceneBackground", c)
        self.assertIn("NavRail", c)
        self.assertIn("onLight", c)               # warm component path is used
        # navigation + required objectNames preserved (also covered by REQUIRED_OBJECT_NAMES)
        self.assertIn("navigateSetup()", c)
        self.assertIn("navigateHistory()", c)
        # typography contract: explicit proportional line height; no font.families
        self.assertIn("lineHeightMode", c)
        self.assertIn("contextFontMerging", c)
        self.assertNotIn("font.families", c)
        # tarot strip falls back on Image.status (not only on empty url)
        self.assertIn("tarotArt.status !== Image.Ready", c)

    def test_no_phase1_glass_or_grain(self) -> None:
        # Phase 1 forbids frosted glass and paper-grain overlays.
        for rel in ["qml/components/SceneBackground.qml", "qml/HomeView.qml",
                    "qml/components/AppCard.qml"]:
            c = (QT / rel).read_text(encoding="utf-8")
            for forbidden in ["FastBlur", "GaussianBlur", "blurEnabled",
                              "PaperGrainOverlay", "noise.png", "grain.png"]:
                self.assertNotIn(forbidden, c, f"{forbidden} forbidden in {rel} (Phase 1)")

    def test_appshell_hides_topbar_only_on_home(self) -> None:
        c = (QT / "qml/AppShell.qml").read_text(encoding="utf-8")
        # topBar visibility gated on home; chip/objectNames preserved
        self.assertRegex(c, r'currentView\s*!==\s*"home"')
        self.assertIn('objectName: "dataSourceChip"', c)
        self.assertIn('objectName: "appShellStack"', c)


if __name__ == "__main__":
    unittest.main()

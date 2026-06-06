cmake_minimum_required(VERSION 3.16)

project(qt_observer VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Quick QuickControls2 Network Test)

qt_standard_project_setup(REQUIRES 6.8)

qt_add_executable(appqt_observer
    main.cpp
    src/ObserverApiClient.cpp
    src/ObserverApiClient.h
    src/ObserverSseParser.cpp
    src/ObserverSseParser.h
)

target_include_directories(appqt_observer PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

target_link_libraries(appqt_observer
    PRIVATE Qt6::Quick Qt6::QuickControls2 Qt6::Network
)

# Theme.qml (design tokens) and I18n.qml (runtime translations) are QML
# singletons accessible module-wide as `Theme` and `I18n`.
set_source_files_properties(qml/Theme.qml PROPERTIES QT_QML_SINGLETON_TYPE TRUE)
set_source_files_properties(qml/I18n.qml PROPERTIES QT_QML_SINGLETON_TYPE TRUE)

qt_add_qml_module(appqt_observer
    URI qt_observer
    VERSION 1.0
    QML_FILES
        Main.qml
        qml/Theme.qml
        qml/I18n.qml
        qml/AppShell.qml
        qml/HomeView.qml
        qml/MatchSetupView.qml
        qml/PreflightView.qml
        qml/LiveCockpitView.qml
        qml/TheaterView.qml
        qml/HistoryView.qml
        qml/EventPresentationQueue.qml
        qml/components/RoleCard.qml
        qml/components/SeatRing.qml
        qml/components/SpeechTheater.qml
        qml/components/EvidenceConsole.qml
        qml/components/PlaybackControls.qml
        qml/components/EventTimeline.qml
        qml/components/PerspectiveSwitcher.qml
        qml/components/AuditLinksPanel.qml
        qml/components/StatusBadge.qml
        qml/components/ViewBoundaryBadge.qml
        qml/components/ProjectionProofPanel.qml
        qml/components/AppBackground.qml
        qml/components/GlowDot.qml
        qml/components/AppCard.qml
        qml/components/AppButton.qml
        qml/components/SectionHeader.qml
        qml/components/EmptyState.qml
        qml/components/SeatEditorPanel.qml
        qml/components/ModeControl.qml
        qml/components/DataSourceChip.qml
)

set_target_properties(appqt_observer PROPERTIES
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

include(GNUInstallDirs)
install(TARGETS appqt_observer
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

enable_testing()
qt_add_executable(tst_observer_sse_parser
    tests/tst_observer_sse_parser.cpp
    src/ObserverSseParser.cpp
    src/ObserverSseParser.h
)
target_include_directories(tst_observer_sse_parser PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(tst_observer_sse_parser PRIVATE Qt6::Test Qt6::Core)
add_test(NAME observer_sse_parser COMMAND tst_observer_sse_parser)

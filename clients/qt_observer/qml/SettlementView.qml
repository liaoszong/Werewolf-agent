import QtQuick
import qt_observer
import "components"

// P2-D §7.1 — the settlement / battle-report overlay. Hosted INSIDE TheaterView as
// an overlay (NOT an AppShell nav target, §14.1). A one-shot Z-axis morph state
// machine (freeze -> docking -> report) and the SINGLE writable cursor source of
// truth. The docked SeatRing / spine / report are pure Observers of cursorIndex;
// only scroll-spy (cursorRequested) and spine click (nodeClicked) write it.
Item {
    id: settle
    objectName: "settlementView"

    // entryMode: 0 = live freeze ceremony, 1 = history → straight to report (no freeze).
    property int entryMode: 0
    // The ONE writable cursor source of truth (a board_timeline index, D6).
    property int cursorIndex: 0

    // Emitted by the always-on exit affordance; the host (TheaterView Loader) decides
    // where to navigate (history vs home). The overlay fills the theater and covers
    // its back button, so without this the settlement screen had no way out.
    signal exitRequested()

    // The fetched bundle (settlement-bundle.v1). SeatRing/spine/report never fetch.
    readonly property var bundle: ObserverClient.settlementBundle
    readonly property bool _degraded: bundle && bundle.degraded === true
    readonly property var _board: (bundle && bundle.board_timeline) ? bundle.board_timeline : []
    // Resolve board_timeline[cursorIndex] -> boardState prop for the docked SeatRing
    // (SeatRing is presentational; resolution lives HERE, not in SeatRing, §14.2).
    readonly property var boardState: (_board.length > 0 && cursorIndex >= 0 && cursorIndex < _board.length)
        ? _board[cursorIndex] : ({})

    // Activated on completion (live) or opened from history; owns the fetch.
    Component.onCompleted: {
        if (ObserverClient.currentRunId !== "")
            ObserverClient.fetchSettlement(ObserverClient.currentRunId)
        settle.state = entryMode === 1 ? "report" : "freeze"
    }

    // Single-cursor wiring (D6). setCursor: clamp + drive the report scroll-to-anchor
    // (spine-click path). The report's scroll-spy writes via onCursorRequested WITHOUT
    // calling scrollTo (no feedback loop). All readers bind settle.cursorIndex.
    function setCursor(i) {
        var n = _board.length
        cursorIndex = Math.max(0, Math.min(i, n > 0 ? n - 1 : 0))
        report.scrollTo(cursorIndex)
    }

    // The morph canvas. freeze = dark translucent (theater shows through, tense);
    // docking/report = the OPAQUE warm-beige "明室" workbench. The ColorAnimation
    // is the 暗室→明室 reveal as the ring docks; opaque also kills the old Z-bleed
    // of the theater game-log through the panel (issue #2).
    Rectangle {
        anchors.fill: parent
        color: settle.state === "freeze"
            ? Theme.withAlpha(Theme.color.bgBase, 0.55)
            : Theme.report.canvas
        Behavior on color { ColorAnimation { duration: Theme.motion.slow } }
    }

    // ---------------------------------------------------------------- Layout
    // 28% sticky left (docked sandbox + winner header) · center spine · 72% report.
    // Left column.
    Item {
        id: leftColumn
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: Theme.space.xl
        width: parent.width * 0.28

        // Docked "live sandbox" — the SeatRing morphed from the theater ring. In the
        // freeze beat it fills the stage (morphProgress 0); docking/report dock it.
        // The winner headline lives ONLY in the right report now (was duplicated here,
        // issue #1a) so the left column is a clean head grid.
        SeatRing {
            id: dockedRing
            objectName: "settlementSandbox"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            // Upper ~58% so the 2-row grid stays compact; clean space below.
            height: parent.height * 0.58
            players: ObserverClient.playerItems
            layoutMode: settle.state === "freeze" ? "theater" : "docked"
            morphProgress: settle.state === "freeze" ? 0 : 1
            boardState: settle.boardState        // resolved here, SeatRing reads no bundle/cursor
        }
    }

    // Center spine.
    SettlementSpine {
        id: spine
        anchors.left: leftColumn.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: Theme.space.xl
        anchors.bottomMargin: Theme.space.xl
        anchors.leftMargin: Theme.space.md
        width: Math.max(150, parent.width * 0.12)
        visible: settle.state === "report"
        nodes: settle._board
        activeIndex: settle.cursorIndex                  // pure binding read
        onNodeClicked: function(index) { settle.setCursor(index) }
    }

    // Right report (72%).
    SettlementReport {
        id: report
        anchors.left: spine.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: Theme.space.xl
        anchors.leftMargin: Theme.space.md
        visible: settle.state === "report"
        bundle: settle.bundle
        activeIndex: settle.cursorIndex                  // pure binding read
        // Scroll-spy write path: set cursor WITHOUT scrollTo (avoids the feedback loop).
        onCursorRequested: function(index) { settle.cursorIndex = index }
    }

    // Freeze-beat centerpiece: the WinnerBanner drop + a "查看深度战报" advance button.
    Item {
        id: freezeBeat
        anchors.fill: parent
        visible: settle.state === "freeze"

        WinnerBanner {
            id: freezeBanner
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: -Theme.space.huge
            width: Math.min(parent.width * 0.6, 560)
            result: (settle.bundle && settle.bundle.result) ? settle.bundle.result : ({})
        }

        AppButton {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: freezeBanner.bottom
            anchors.topMargin: Theme.space.xxl
            text: I18n.t("查看深度战报", "View full battle report")
            variant: "primary"
            onClicked: settle.state = "docking"
        }
    }

    // Always-on exit affordance (top-right). The overlay fills the theater and hides
    // its back button, so this is the ONLY way out. Self-styled with report-palette
    // tokens so it stays readable on BOTH the dark freeze canvas and the beige report
    // canvas (the standard ghost AppButton uses dark-UI colors that vanish on beige).
    Rectangle {
        id: exitButton
        objectName: "settlementExitButton"
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Theme.space.lg
        z: 1000
        implicitWidth: exitLabel.implicitWidth + Theme.space.xl * 2
        implicitHeight: 36
        radius: Theme.radius.sm
        color: exitHover.hovered ? Theme.report.canvas : Theme.report.card
        border.width: 1
        border.color: Theme.report.border

        Behavior on color { ColorAnimation { duration: Theme.motion.fast } }

        Text {
            id: exitLabel
            anchors.centerIn: parent
            text: I18n.t("✕ 退出", "✕ Exit")
            color: Theme.report.text
            font.family: Theme.font.family
            font.pixelSize: Theme.size.body
            font.weight: Theme.weight.semibold
        }

        HoverHandler { id: exitHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: settle.exitRequested() }

        Accessible.role: Accessible.Button
        Accessible.name: exitLabel.text
        Accessible.onPressAction: settle.exitRequested()
    }

    // -------------------------------------------------- Morph state machine (D4/D7)
    // freeze: theater ring + banner drop (no docked column / spine / report).
    // docking: ring flies into the 28% column (SeatRing morphProgress 0->1).
    // report: docked sandbox pinned, spine + report unfolded, scroll-sync live.
    states: [
        State { name: "freeze" },
        State { name: "docking" },
        State { name: "report" }
    ]

    // docking auto-advances to report once the dock travel settles.
    Timer {
        id: dockSettle
        interval: Theme.motion.slow
        repeat: false
        onTriggered: if (settle.state === "docking") settle.state = "report"
    }
    onStateChanged: if (state === "docking") dockSettle.restart()
}

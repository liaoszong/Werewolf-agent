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

    // Dim scrim behind the morph so the theater recedes (Z-axis depth feel).
    Rectangle {
        anchors.fill: parent
        color: Theme.withAlpha(Theme.color.bgBase, settle.state === "report" ? 0.96 : 0.55)
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
        SeatRing {
            id: dockedRing
            objectName: "settlementSandbox"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: parent.height * 0.62
            players: ObserverClient.playerItems
            layoutMode: settle.state === "freeze" ? "theater" : "docked"
            morphProgress: settle.state === "freeze" ? 0 : 1
            boardState: settle.boardState        // resolved here, SeatRing reads no bundle/cursor
        }

        // Winner header docked beneath the sandbox (shrunk WinnerBanner).
        WinnerBanner {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: dockedRing.bottom
            anchors.topMargin: Theme.space.lg
            visible: settle.state !== "freeze"
            result: (settle.bundle && settle.bundle.result) ? settle.bundle.result : ({})
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
        width: Math.max(96, parent.width * 0.10)
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

import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// History — recorded and in-progress matches, with a one-click replay flow.
// Dark "Nightfall" surface; behaviour, bindings and navigation unchanged.
Item {
    id: root
    objectName: "historyView"

    Component.onCompleted: ObserverClient.refreshRuns()

    // ---- delete plumbing (spec §4) ----
    property bool _batchActive: false                 // batch controller sets this

    // Unified confirm callback — single and batch both set this before open().
    property var _onDialogConfirm: null

    ConfirmDialog {
        id: confirmDialog
        objectName: "historyConfirmDialog"
        parent: Overlay.overlay
        onConfirmed: {
            var act = root._onDialogConfirm
            root._onDialogConfirm = null
            if (act) act()
        }
        onClosed: Qt.callLater(function() { root._onDialogConfirm = null })
    }

    // ---- batch selection (spec §4) ----
    property bool selecting: false
    property var _selected: ({})                     // run_id -> true
    readonly property int selectedCount: Object.keys(_selected).length
    property var _batchQueue: []
    property int _batchTotal: 0
    property int _batchFailed: 0
    property var _batchErrors: []

    function _toggleSelected(runId, on) {
        var m = _selected
        if (on) m[runId] = true; else delete m[runId]
        _selected = m                                 // reassign to fire bindings
    }
    function _exitSelectMode() { selecting = false; _selected = ({}) }

    function _startBatchDelete() {
        _batchQueue = Object.keys(_selected)
        _batchTotal = _batchQueue.length
        _batchFailed = 0
        _batchErrors = []
        _batchActive = true
        _pumpBatch()
    }
    function _pumpBatch() {
        if (_batchQueue.length === 0) {
            _batchActive = false
            var okCount = _batchTotal - _batchFailed
            noticeBar.show(_batchFailed === 0
                ? I18n.t("已删除 ", "Deleted ") + okCount + I18n.t(" 局", " runs")
                : I18n.t("已删除 ", "Deleted ") + okCount + I18n.t(" 局,", " runs, ")
                  + _batchFailed + I18n.t(" 局失败:", " failed: ") + _batchErrors.join("; "))
            _exitSelectMode()
            ObserverClient.refreshRuns()              // batch refreshes ONCE at the end (spec §4)
            return
        }
        var q = _batchQueue
        var next = q.shift()
        _batchQueue = q
        ObserverClient.deleteRun(next)
    }

    // Transient notice (delete failures / batch summary). Auto-hides.
    Rectangle {
        id: noticeBar
        objectName: "historyNoticeBar"
        property string text: ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.space.xl
        z: 10
        visible: text !== ""
        width: noticeLabel.implicitWidth + Theme.space.lg * 2
        height: noticeLabel.implicitHeight + Theme.space.md * 2
        radius: Theme.radius.md
        color: Theme.withAlpha(Theme.color.surface, 0.96)
        border.width: 1
        border.color: Theme.color.border
        Text {
            id: noticeLabel
            anchors.centerIn: parent
            text: noticeBar.text
            color: Theme.color.text
            font.family: Theme.font.family
            font.pixelSize: Theme.size.caption
        }
        Timer { id: noticeTimer; interval: 5000; onTriggered: noticeBar.text = "" }
        function show(msg) { text = msg; noticeTimer.restart() }
    }

    Connections {
        target: ObserverClient
        function onDeleteRunFinished(runId, ok, error) {
            if (root._batchActive) {
                if (!ok) { root._batchFailed += 1; root._batchErrors.push(runId + ": " + error) }
                root._pumpBatch()                     // sequential: next delete only after this one
                return
            }
            if (ok)
                ObserverClient.refreshRuns()          // SINGLE delete refreshes per-op (spec §4)
            else
                noticeBar.show(I18n.t("删除失败:", "Delete failed: ") + error)
        }
    }

    // Deep night backdrop so the centered content reads as a focused panel.
    Rectangle {
        anchors.fill: parent
        color: Theme.color.bgBase
    }

    // Centered, max-width content region anchored toward the top.
    Item {
        id: content
        anchors.fill: parent
        anchors.topMargin: Theme.space.xxxl
        anchors.bottomMargin: Theme.space.xxl
        anchors.leftMargin: Theme.space.xxl
        anchors.rightMargin: Theme.space.xxl

        Item {
            id: stack
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: Math.min(parent.width, 1000)

            // ---------------------------------------------------------- Header
            Item {
                id: header
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: titleBlock.implicitHeight

                Column {
                    id: titleBlock
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: refreshButton.left
                    anchors.rightMargin: Theme.space.lg
                    spacing: Theme.space.xs

                    Text {
                        text: I18n.t("历史对局", "History")
                        color: Theme.color.text
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.h1
                        font.weight: Theme.weight.bold
                    }

                    Text {
                        text: I18n.t("已记录与进行中的对局", "Recorded and in-progress matches")
                        color: Theme.color.textMuted
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.caption
                    }
                }

                AppButton {
                    id: refreshButton
                    objectName: "historyRefreshButton"
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.t("刷新", "Refresh")
                    variant: "secondary"
                    onClicked: ObserverClient.refreshRuns()
                }
            }

            // ----------------------------------------------------- Runs panel
            AppCard {
                id: runsPanel
                anchors.top: header.bottom
                anchors.topMargin: Theme.space.lg
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: footer.top
                anchors.bottomMargin: Theme.space.lg

                // Count chip + section label header inside the panel.
                Item {
                    id: panelHeader
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: Theme.space.lg
                    height: panelTitle.implicitHeight

                    SectionHeader {
                        id: panelTitle
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        title: I18n.t("对局", "Runs")
                    }

                    // Select-all checkbox — visible when in selection mode,
                    // placed left of the count chip with a small gap.
                    CheckBox {
                        objectName: "selectAllBox"
                        visible: root.selecting
                        anchors.right: countChip.left
                        anchors.rightMargin: Theme.space.sm
                        anchors.verticalCenter: parent.verticalCenter
                        onToggled: {
                            var m = ({})
                            if (checked)
                                for (var i = 0; i < ObserverClient.runItems.length; i++) {
                                    var it = ObserverClient.runItems[i]
                                    var st = it.status || ""
                                    if (st !== "running" && st !== "queued") m[it.run_id] = true
                                }
                            root._selected = m
                        }
                    }

                    // Select / Cancel toggle button, left of count chip.
                    AppButton {
                        id: selectModeButton
                        objectName: "selectModeButton"
                        anchors.right: countChip.left
                        anchors.rightMargin: root.selecting ? Theme.space.xl + 20 : Theme.space.sm
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.selecting ? I18n.t("取消", "Cancel") : I18n.t("选择", "Select")
                        variant: "ghost"
                        visible: ObserverClient.runItems.length > 0
                        onClicked: root.selecting ? root._exitSelectMode() : root.selecting = true
                    }

                    // Count chip — anchored to right edge.
                    Rectangle {
                        id: countChip
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: 22
                        width: countLabel.implicitWidth + Theme.space.md * 2
                        radius: Theme.radius.pill
                        color: Theme.withAlpha(Theme.color.primary, 0.14)
                        border.width: 1
                        border.color: Theme.withAlpha(Theme.color.primary, 0.30)
                        visible: ObserverClient.runItems.length > 0

                        Text {
                            id: countLabel
                            anchors.centerIn: parent
                            text: "" + ObserverClient.runItems.length
                            color: Theme.color.primary
                            font.family: Theme.font.mono
                            font.pixelSize: Theme.size.caption
                            font.weight: Theme.weight.semibold
                        }
                    }
                }

                Rectangle {
                    id: panelDivider
                    anchors.top: panelHeader.bottom
                    anchors.topMargin: Theme.space.md
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 1
                    anchors.rightMargin: 1
                    height: 1
                    color: Theme.color.border
                    visible: ObserverClient.runItems.length > 0
                }

                // The list of runs, or a friendly empty state.
                ListView {
                    id: historyRunsList
                    objectName: "historyRunsList"
                    anchors.top: panelDivider.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.topMargin: Theme.space.sm
                    anchors.bottomMargin: Theme.space.sm
                    model: ObserverClient.runItems
                    clip: true
                    visible: ObserverClient.runItems.length > 0
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }

                    delegate: Item {
                        id: runDelegate
                        width: ListView.view.width
                        height: 52

                        readonly property color _accent: Theme.statusColor(modelData.status || "")

                        Rectangle {
                            id: rowHighlight
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space.lg
                            anchors.rightMargin: Theme.space.lg
                            anchors.topMargin: 2
                            anchors.bottomMargin: 2
                            radius: Theme.radius.md
                            color: rowHover.hovered ? Theme.color.surfaceAlt : "transparent"

                            Behavior on color { ColorAnimation { duration: Theme.motion.fast } }

                            // Per-row selection checkbox at the far left, visible in selection mode.
                            CheckBox {
                                objectName: "rowSelectBox"
                                visible: root.selecting
                                enabled: (modelData.status || "") !== "running"
                                         && (modelData.status || "") !== "queued"
                                anchors.left: parent.left
                                anchors.leftMargin: Theme.space.md
                                anchors.verticalCenter: parent.verticalCenter
                                checked: root._selected[modelData.run_id] === true
                                onToggled: root._toggleSelected(modelData.run_id, checked)
                            }

                            // Status-tinted leading accent bar.
                            Rectangle {
                                anchors.left: parent.left
                                anchors.leftMargin: root.selecting ? 36 : 0
                                anchors.verticalCenter: parent.verticalCenter
                                width: 3
                                height: 22
                                radius: 1.5
                                color: runDelegate._accent
                                opacity: rowHover.hovered ? 1.0 : 0.55

                                Behavior on opacity { NumberAnimation { duration: Theme.motion.fast } }
                                Behavior on anchors.leftMargin { NumberAnimation { duration: Theme.motion.fast } }
                            }

                            // Run id (mono for a precise, trustworthy feel).
                            Text {
                                id: runIdText
                                anchors.left: parent.left
                                anchors.leftMargin: (root.selecting ? 36 : 0) + Theme.space.lg
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.max(120, parent.width
                                    - statusBadge.width - deleteButton.width - reportButton.width - openButton.width - Theme.space.xl * 5
                                    - (root.selecting ? 36 : 0))
                                elide: Text.ElideRight
                                text: modelData.run_id || I18n.t("(未命名对局)", "(unnamed run)")
                                color: Theme.color.text
                                font.family: Theme.font.mono
                                font.pixelSize: Theme.size.small

                                Behavior on anchors.leftMargin { NumberAnimation { duration: Theme.motion.fast } }
                            }

                            StatusBadge {
                                id: statusBadge
                                anchors.right: deleteButton.left
                                anchors.rightMargin: Theme.space.lg
                                anchors.verticalCenter: parent.verticalCenter
                                status: modelData.status || ""
                            }

                            AppButton {
                                id: deleteButton
                                objectName: "deleteRunButton"
                                anchors.right: reportButton.visible ? reportButton.left : openButton.left
                                anchors.rightMargin: Theme.space.sm
                                anchors.verticalCenter: parent.verticalCenter
                                text: I18n.t("删除", "Delete")
                                variant: "ghost"
                                visible: !root.selecting
                                enabled: (modelData.status || "") !== "running"
                                         && (modelData.status || "") !== "queued"
                                onClicked: {
                                    var rid = modelData.run_id
                                    root._onDialogConfirm = function() { ObserverClient.deleteRun(rid) }
                                    confirmDialog.title = I18n.t("删除对局", "Delete run")
                                    confirmDialog.message = I18n.t("确定删除对局 ", "Delete run ")
                                        + modelData.run_id
                                        + I18n.t("?删除后不可恢复。", "? This cannot be undone.")
                                    confirmDialog.open()
                                }
                            }

                            // P2-D §7.7 — thin "查看战报" entry for finished runs. openRun's
                            // forReport=true sets the settlement entry intent synchronously, so
                            // the theater's settlement overlay opens straight to `report`
                            // (history-direct), skipping the live freeze ceremony.
                            AppButton {
                                id: reportButton
                                objectName: "openSettlementButton"
                                anchors.right: openButton.left
                                anchors.rightMargin: Theme.space.sm
                                anchors.verticalCenter: parent.verticalCenter
                                visible: !root.selecting && (modelData.status || "") === "completed"
                                text: I18n.t("查看战报", "View report")
                                variant: "secondary"
                                onClicked: {
                                    ObserverClient.openRun(modelData.run_id, true)
                                    root.StackView.view.parent.navigateCockpit()
                                }
                            }

                            AppButton {
                                id: openButton
                                objectName: "openReplayButton"
                                anchors.right: parent.right
                                anchors.rightMargin: Theme.space.md
                                anchors.verticalCenter: parent.verticalCenter
                                visible: !root.selecting
                                text: I18n.t("打开", "Open")
                                variant: "ghost"
                                onClicked: {
                                    ObserverClient.openRun(modelData.run_id)
                                    root.StackView.view.parent.navigateCockpit()
                                }
                            }

                            HoverHandler {
                                id: rowHover
                            }
                        }
                    }
                }

                EmptyState {
                    anchors.centerIn: parent
                    visible: ObserverClient.runItems.length === 0
                    title: I18n.t("暂无记录", "No runs recorded")
                    subtitle: I18n.t("已完成与进行中的对局将显示在此。", "Completed and in-progress matches will appear here.")
                }
            }

            // ---------------------------------------------------------- Footer
            Item {
                id: footer
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: Math.max(backButton.implicitHeight, batchDeleteButton.implicitHeight)

                AppButton {
                    id: backButton
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.t("返回首页", "Back to Home")
                    variant: "ghost"
                    onClicked: root.StackView.view.parent.navigateHome()
                }

                // Batch delete action — visible in selection mode when ≥1 item selected.
                AppButton {
                    id: batchDeleteButton
                    objectName: "batchDeleteButton"
                    visible: root.selecting && root.selectedCount > 0
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.t("删除所选(", "Delete selected (") + root.selectedCount + ")"
                    variant: "danger"
                    onClicked: {
                        root._onDialogConfirm = root._startBatchDelete
                        confirmDialog.title = I18n.t("批量删除", "Batch delete")
                        confirmDialog.message = I18n.t("确定删除 ", "Delete ") + root.selectedCount
                            + I18n.t(" 局?删除后不可恢复。", " runs? This cannot be undone.")
                        confirmDialog.open()
                    }
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

// Match Archive — UI-only redesign of the history surface.
// Data and actions remain on the existing ObserverClient run list / replay /
// settlement / delete contract.
Item {
    id: root
    objectName: "historyView"

    Component.onCompleted: firstFrameRefreshTimer.restart()

    // When this view is embedded in AppShell's StackView, AppShell draws the
    // warm full-bleed backdrop from a PERSISTENT layer (pageBackdropLayer) so the
    // background Image is not recreated on every push/pop. In that mode the page
    // must NOT paint its own full-screen gradient / archive art / veils, or they
    // would cover the persistent backdrop and re-flash per visit. Standalone /
    // preview usage keeps the default true so the page still has a background.
    property bool embeddedBackdrop: true

    property bool selecting: false
    property var _selected: ({})
    readonly property int selectedCount: Object.keys(_selected).length
    property bool _batchActive: false
    property var _onDialogConfirm: null
    property var _batchQueue: []
    property int _batchTotal: 0
    property int _batchFailed: 0
    property int _batchInFlight: 0
    property var _batchErrors: []
    readonly property int _batchConcurrency: 4
    readonly property int _batchErrorPreviewLimit: 3
    readonly property int _batchCompleted: _batchTotal - _batchQueue.length - _batchInFlight

    Timer {
        id: firstFrameRefreshTimer
        interval: 80
        repeat: false
        onTriggered: {
            if (ObserverClient.runItems.length > 0)
                return
            var shell = root.StackView.view ? root.StackView.view.parent : null
            if (shell && shell._historyRunsPrewarmed)
                return
            if (shell && shell.requestHistoryRunsRefresh)
                shell.requestHistoryRunsRefresh("history-first-frame", 1500)
            else
                ObserverClient.refreshRuns()
        }
    }

    property string activeFilter: "all"          // all | completed | running | interrupted | unknown
    property string searchText: ""
    property string executionFilter: "all"       // all | fake | live | local | unknown
    property string resultFilter: "all"          // all | good | wolf | unknown
    property string timeFilter: "all"            // all | recent | older
    property string selectedRunId: ""
    readonly property int maxSupportedPlayers: 6
    readonly property double recentWindowMs: 7 * 24 * 60 * 60 * 1000

    readonly property var filteredRuns: _filteredRuns()
    readonly property var selectedRun: _findRun(selectedRunId)
    readonly property bool hasSelectedRun: selectedRunId !== ""
                                           && selectedRun
                                           && selectedRun.run_id !== undefined
                                           && selectedRun.run_id !== ""
    readonly property int completedCount: _countStatus("completed")
    readonly property int runningCount: _countStatus("running")
    readonly property int interruptedCount: _countStatus("interrupted")
    readonly property int failedCount: _countStatus("failed")
    readonly property int unknownCount: _countStatus("unknown")

    function _shortRunId(run) {
        var id = run && run.run_id ? "" + run.run_id : root._unknownLabel()
        return _shortRunIdValue(id)
    }

    function _shortRunIdValue(id) {
        id = id !== undefined && id !== null ? "" + id : root._unknownLabel()
        if (id.length <= 24)
            return id
        return id.slice(0, 15) + "..." + id.slice(id.length - 6)
    }

    function _unknownLabel() {
        return I18n.t("未知", "Unknown")
    }

    function _isObject(value) {
        return value !== undefined && value !== null && typeof value === "object"
    }

    function _positiveInt(value) {
        if (value === undefined || value === null || value === "")
            return 0
        var n = Number(value)
        if (isNaN(n) || n <= 0 || n > root.maxSupportedPlayers)
            return 0
        return Math.floor(n)
    }

    function _collectionCount(value) {
        if (!_isObject(value))
            return 0
        if (value.length !== undefined) {
            var n = _positiveInt(value.length)
            if (n > 0)
                return n
        }
        var keys = Object.keys(value)
        return keys.length > 0 && keys.length <= root.maxSupportedPlayers ? keys.length : 0
    }

    function _playerCountFromString(value) {
        if (value === undefined || value === null)
            return 0
        var text = ("" + value).toLowerCase()
        var match = text.match(/(?:^|[^0-9])([1-9][0-9]?)\s*p(?:[^a-z0-9]|$)/)
        if (!match)
            match = text.match(/(?:^|[^0-9])([1-9][0-9]?)\s*(?:player|players|seat|seats)(?:[^a-z0-9]|$)/)
        if (!match)
            match = text.match(/(?:^|[^0-9])([1-9][0-9]?)\s*人/)
        return match ? _positiveInt(match[1]) : 0
    }

    function _extractPlayerCount(run) {
        if (!run)
            return 0

        var countKeys = [
            "player_count", "players_count", "seat_count", "seats_count",
            "participant_count", "num_players", "playerCount", "seatCount"
        ]
        var collectionKeys = ["players", "seats", "seat_ids", "participants"]
        var sources = [run, run.metadata, run.detail, run.snapshot, run.settlement,
                       run.config, run.profile, run.template, run.summary]

        for (var s = 0; s < sources.length; ++s) {
            var source = sources[s]
            if (!_isObject(source))
                continue
            for (var i = 0; i < countKeys.length; ++i) {
                var n = _positiveInt(source[countKeys[i]])
                if (n > 0)
                    return n
            }
            for (var j = 0; j < collectionKeys.length; ++j) {
                var c = _collectionCount(source[collectionKeys[j]])
                if (c > 0)
                    return c
            }
        }

        var strings = [
            run.run_id, run.profile, run.profile_name, run.profile_id, run.template,
            run.template_id, run.script_id, run.mode, run.name, run.title
        ]
        for (var k = 0; k < strings.length; ++k) {
            var parsed = _playerCountFromString(strings[k])
            if (parsed > 0)
                return parsed
        }
        return 0
    }

    function _timestampMs(value) {
        if (value === undefined || value === null || value === "")
            return NaN
        if (typeof value === "number") {
            if (value > 100000000000)
                return value
            if (value > 1000000000)
                return value * 1000
            return NaN
        }

        var text = ("" + value).trim()
        if (text === "")
            return NaN
        if (/^[0-9]{13}$/.test(text))
            return Number(text)
        if (/^[0-9]{10}$/.test(text))
            return Number(text) * 1000

        var ms = Date.parse(text.replace(" ", "T"))
        if (!isNaN(ms))
            return ms

        var match = text.match(/(20[0-9]{2})[-_]?([0-9]{2})[-_]?([0-9]{2})(?:[T_\- ]?([0-9]{2})[:_\-]?([0-9]{2}))?/)
        if (match) {
            var hour = match[4] !== undefined ? Number(match[4]) : 0
            var minute = match[5] !== undefined ? Number(match[5]) : 0
            return new Date(Number(match[1]), Number(match[2]) - 1,
                            Number(match[3]), hour, minute).getTime()
        }
        return NaN
    }

    function _extractRunTimestamp(run) {
        if (!run)
            return NaN

        var keys = [
            "created_at", "createdAt", "started_at", "startedAt", "start_time",
            "startTime", "timestamp", "mtime", "updated_at", "updatedAt",
            "modified_at", "last_modified", "filesystem_mtime", "completed_at",
            "ended_at", "end_time"
        ]
        var sources = [run, run.metadata, run.detail, run.snapshot, run.settlement, run.summary]
        for (var s = 0; s < sources.length; ++s) {
            var source = sources[s]
            if (!_isObject(source))
                continue
            for (var i = 0; i < keys.length; ++i) {
                var ms = _timestampMs(source[keys[i]])
                if (!isNaN(ms))
                    return ms
            }
        }

        var strings = [run.run_id, run.name, run.title]
        for (var j = 0; j < strings.length; ++j) {
            var parsed = _timestampMs(strings[j])
            if (!isNaN(parsed))
                return parsed
        }
        return NaN
    }

    function _pad2(n) {
        return n < 10 ? "0" + n : "" + n
    }

    function _formatHistoryTimestamp(ms) {
        if (isNaN(ms))
            return ""
        var d = new Date(ms)
        return d.getFullYear() + "-" + _pad2(d.getMonth() + 1) + "-"
               + _pad2(d.getDate()) + " " + _pad2(d.getHours()) + ":"
               + _pad2(d.getMinutes())
    }

    function formatHistoryRunTitle(run) {
        var ms = _extractRunTimestamp(run)
        var count = _extractPlayerCount(run)
        if (!isNaN(ms)) {
            var time = _formatHistoryTimestamp(ms)
            if (count > 0)
                return count + I18n.t("人对局 - ", "-player match - ") + time
            return I18n.t("对局 - ", "Match - ") + time
        }
        if (count > 0)
            return count + I18n.t("人对局", "-player match")
        return I18n.t("对局 - ", "Match - ") + _shortRunId(run)
    }

    function _runTitle(run) {
        return formatHistoryRunTitle(run)
    }

    function _statusKey(status) {
        var st = (status === undefined || status === null) ? "" : ("" + status).toLowerCase()
        if (st === "completed")
            return "completed"
        if (st === "running" || st === "queued")
            return "running"
        if (st === "interrupted")
            return "interrupted"
        if (st === "failed")
            return "failed"
        return "unknown"
    }

    function _statusLabel(status) {
        var st = (status === undefined || status === null) ? "" : ("" + status).toLowerCase()
        if (st === "completed")
            return I18n.t("已完成", "Completed")
        if (st === "running")
            return I18n.t("进行中", "Running")
        if (st === "queued")
            return I18n.t("排队中", "Queued")
        if (st === "interrupted")
            return I18n.t("中断", "Interrupted")
        if (st === "failed")
            return I18n.t("失败", "Failed")
        return root._unknownLabel()
    }

    function _statusAccent(status) {
        var st = _statusKey(status)
        if (st === "completed")
            return Theme.warm.success
        if (st === "running")
            return Theme.warm.primary
        if (st === "interrupted")
            return Theme.warm.warning
        if (st === "failed")
            return Theme.color.failed
        return Theme.parchment.mutedInk
    }

    function _canDelete(run) {
        var st = run && run.status ? ("" + run.status).toLowerCase() : ""
        return st !== "running" && st !== "queued"
    }

    function _canViewReport(run) {
        if (!run)
            return false
        return (run.status || "").toLowerCase() === "completed"
               && run.report_available === true
    }

    function _openActionLabel(run) {
        var st = run && run.status ? ("" + run.status).toLowerCase() : ""
        if (st === "running" || st === "queued")
            return I18n.t("继续观察", "Continue")
        return I18n.t("打开", "Open")
    }

    function _executionKey(run) {
        var mode = ""
        if (run) {
            mode = run.execution_mode || run.mode || run.runtime_mode || ""
        }
        mode = ("" + mode).toLowerCase()
        if (mode === "live" || mode === "cloud" || mode === "remote")
            return "live"
        if (mode === "fake" || mode === "simulation" || mode === "simulated")
            return "fake"
        if (mode === "local")
            return "local"
        return "unknown"
    }

    function _executionLabel(run) {
        var key = _executionKey(run)
        if (key === "live")
            return I18n.t("云端执行", "Cloud execution")
        if (key === "fake")
            return I18n.t("模拟", "Simulation")
        if (key === "local")
            return I18n.t("本地执行", "Local execution")
        return root._unknownLabel()
    }

    function _templateLabel(run) {
        if (!run)
            return root._unknownLabel()
        var value = run.profile_name || run.profile || run.template || run.script_id || ""
        return value === "" ? root._unknownLabel() : "" + value
    }

    function _timeLabel(run) {
        if (!run)
            return root._unknownLabel()
        var ms = _extractRunTimestamp(run)
        if (!isNaN(ms))
            return _formatHistoryTimestamp(ms)
        var value = run.created_at || run.started_at || run.start_time
                    || run.timestamp || run.mtime || run.updated_at || ""
        return value === "" ? root._unknownLabel() : "" + value
    }

    function _endTimeLabel(run) {
        if (!run)
            return root._unknownLabel()
        var value = run.ended_at || run.completed_at || run.end_time || ""
        return value === "" ? root._unknownLabel() : "" + value
    }

    function _durationLabel(run) {
        if (!run)
            return root._unknownLabel()
        var value = run.duration || run.duration_text || run.elapsed || ""
        return value === "" ? root._unknownLabel() : "" + value
    }

    function _resultKey(run) {
        if (!run)
            return "unknown"
        var raw = "" + (run.result || run.winner || run.winner_team || run.outcome || "")
        var lower = raw.toLowerCase()
        if (lower.indexOf("wolf") >= 0 || lower.indexOf("werewolf") >= 0)
            return "wolf"
        if (lower.indexOf("good") >= 0 || lower.indexOf("villager") >= 0
                || lower.indexOf("village") >= 0 || lower.indexOf("human") >= 0)
            return "good"
        return "unknown"
    }

    function _resultLabel(run) {
        if (!run)
            return root._unknownLabel()
        var key = _resultKey(run)
        if (key === "wolf")
            return I18n.t("狼人阵营胜利", "Werewolf team victory")
        if (key === "good")
            return I18n.t("好人阵营胜利", "Good team victory")
        var st = (run.status || "").toLowerCase()
        if (st === "running" || st === "queued")
            return I18n.t("对局记录中", "Recording")
        if (st === "interrupted")
            return I18n.t("中断", "Interrupted")
        if (st === "failed")
            return I18n.t("运行失败", "Run failed")
        return root._unknownLabel()
    }

    function _summaryLabel(run) {
        if (!run)
            return I18n.t("暂无摘要", "No summary")
        if (run.summary !== undefined && run.summary !== null && ("" + run.summary) !== "")
            return "" + run.summary
        if (run.reason !== undefined && run.reason !== null && ("" + run.reason) !== "")
            return I18n.t("状态原因：", "Reason: ") + run.reason
        var events = run.event_count !== undefined ? run.event_count : 0
        var snaps = run.snapshot_count !== undefined ? run.snapshot_count : 0
        var st = (run.status || "").toLowerCase()
        if (st === "completed") {
            var reportText = run.report_available === true
                             ? I18n.t("战报可用", "report ready")
                             : I18n.t("战报不可用", "report unavailable")
            return I18n.t("已归档 ", "Archived ") + events + I18n.t(" 条事件 · ", " events · ")
                   + snaps + I18n.t(" 份快照 · ", " snapshots · ") + reportText
        }
        if (st === "running" || st === "queued")
            return I18n.t("正在记录事件流", "Recording the event stream")
        if (st === "interrupted")
            return I18n.t("对局已中断，无复盘报告", "Interrupted, no report")
        return I18n.t("暂无摘要", "No summary")
    }

    function _roleSummary(run) {
        if (!run)
            return I18n.t("暂无角色摘要", "No role summary")
        if (run.role_summary !== undefined && run.role_summary !== null
                && ("" + run.role_summary) !== "")
            return "" + run.role_summary
        var events = run.event_count !== undefined ? run.event_count : 0
        var snaps = run.snapshot_count !== undefined ? run.snapshot_count : 0
        if (events > 0 || snaps > 0)
            return I18n.t("事件 ", "Events ") + events + I18n.t(" · 快照 ", " · snapshots ") + snaps
        return I18n.t("暂无角色摘要", "No role summary")
    }

    function _versionLabel(run) {
        if (!run)
            return root._unknownLabel()
        if (run.version !== undefined && run.version !== null && ("" + run.version) !== "")
            return "" + run.version
        var bucket = run.evaluation_bucket
        if (bucket !== undefined && bucket !== null) {
            if (bucket.comparison_key !== undefined && bucket.comparison_key !== null)
                return "" + bucket.comparison_key
            var parts = []
            if (bucket.rules_version)
                parts.push(bucket.rules_version)
            if (bucket.prompt_version)
                parts.push(bucket.prompt_version)
            if (bucket.scoring_version)
                parts.push(bucket.scoring_version)
            if (parts.length > 0)
                return parts.join(" / ")
        }
        return root._unknownLabel()
    }

    function _matchSearch(run) {
        var q = (root.searchText || "").toLowerCase().trim()
        if (q === "")
            return true
        var hay = [
            run.run_id || "",
            _runTitle(run),
            run.profile || "",
            run.profile_name || "",
            run.template || ""
        ].join(" ").toLowerCase()
        return hay.indexOf(q) >= 0
    }

    function _matchFilters(run) {
        if (!_matchSearch(run))
            return false
        if (root.activeFilter !== "all" && _statusKey(run.status) !== root.activeFilter)
            return false
        if (root.executionFilter !== "all" && _executionKey(run) !== root.executionFilter)
            return false
        if (root.resultFilter !== "all" && _resultKey(run) !== root.resultFilter)
            return false
        if (!root._matchTimeFilter(run))
            return false
        return true
    }

    function _matchTimeFilter(run) {
        if (root.timeFilter === "all")
            return true

        var ms = _extractRunTimestamp(run)
        if (isNaN(ms))
            return root.timeFilter === "older"

        var cutoff = Date.now() - root.recentWindowMs
        if (root.timeFilter === "recent")
            return ms >= cutoff
        if (root.timeFilter === "older")
            return ms < cutoff
        return true
    }

    function _filteredRuns() {
        var out = []
        var runs = ObserverClient.runItems || []
        for (var i = 0; i < runs.length; ++i) {
            if (_matchFilters(runs[i]))
                out.push(runs[i])
        }
        out.sort(function(a, b) {
            var at = _extractRunTimestamp(a)
            var bt = _extractRunTimestamp(b)
            var ah = !isNaN(at)
            var bh = !isNaN(bt)
            if (ah && bh && at !== bt)
                return bt - at
            if (ah !== bh)
                return ah ? -1 : 1

            var ar = a && a.run_id ? "" + a.run_id : ""
            var br = b && b.run_id ? "" + b.run_id : ""
            if (ar < br)
                return -1
            if (ar > br)
                return 1
            return 0
        })
        return out
    }

    function _countStatus(key) {
        var runs = ObserverClient.runItems || []
        var n = 0
        for (var i = 0; i < runs.length; ++i) {
            if (_statusKey(runs[i].status) === key)
                n += 1
        }
        return n
    }

    function _findRun(runId) {
        var runs = ObserverClient.runItems || []
        for (var i = 0; i < runs.length; ++i) {
            if (runs[i].run_id === runId)
                return runs[i]
        }
        return ({})
    }

    function _toggleSelected(runId, on) {
        var m = _selected
        if (on)
            m[runId] = true
        else
            delete m[runId]
        _selected = m
        if (Object.keys(_selected).length === 0)
            selectAllBox.checked = false
    }

    function _selectVisibleRuns(on) {
        var m = ({})
        if (on) {
            var runs = root.filteredRuns
            for (var i = 0; i < runs.length; ++i) {
                if (_canDelete(runs[i]))
                    m[runs[i].run_id] = true
            }
        }
        _selected = m
    }

    function _exitSelectMode() {
        selecting = false
        _selected = ({})
        selectAllBox.checked = false
    }

    function _openRun(run, forReport) {
        if (!run || !run.run_id)
            return
        ObserverClient.openRun(run.run_id, forReport === true)
        root.StackView.view.parent.navigateCockpit()
    }

    function _confirmDelete(run) {
        if (!run || !run.run_id || !_canDelete(run))
            return
        var rid = run.run_id
        root._onDialogConfirm = function() { ObserverClient.deleteRun(rid) }
        confirmDialog.title = I18n.t("删除对局", "Delete run")
        confirmDialog.message = I18n.t("确定删除对局 ", "Delete run ")
                                + rid
                                + I18n.t("?删除后不可恢复。", "? This cannot be undone.")
        confirmDialog.open()
    }

    function _startBatchDelete() {
        if (_batchActive)
            return
        _batchQueue = Object.keys(_selected)
        _batchTotal = _batchQueue.length
        _batchFailed = 0
        _batchInFlight = 0
        _batchErrors = []
        _batchActive = true
        _pumpBatch()
    }

    function _pumpBatch() {
        if (!_batchActive)
            return

        while (_batchInFlight < _batchConcurrency && _batchQueue.length > 0) {
            var q = _batchQueue
            var next = q.shift()
            _batchQueue = q
            _batchInFlight += 1
            ObserverClient.deleteRun(next)
        }

        if (_batchQueue.length === 0 && _batchInFlight === 0)
            _finishBatchDelete()
    }

    function _finishBatchDelete() {
        _batchActive = false
        var okCount = _batchTotal - _batchFailed
        noticeBar.show(_batchFailed === 0
            ? I18n.t("已删除 ", "Deleted ") + okCount + I18n.t(" 局", " runs")
            : I18n.t("已删除 ", "Deleted ") + okCount + I18n.t(" 局，", " runs, ")
              + _batchFailed + I18n.t(" 局失败：", " failed: ") + _formatBatchErrors())
        _exitSelectMode()
        ObserverClient.refreshRuns()
    }

    function _formatBatchErrors() {
        var shown = _batchErrors.slice(0, _batchErrorPreviewLimit)
        var message = shown.join("; ")
        var hidden = _batchErrors.length - shown.length
        if (hidden > 0)
            message += I18n.t("；另有 ", "; plus ") + hidden + I18n.t(" 项", " more")
        return message
    }

    Connections {
        target: ObserverClient
        function onDeleteRunFinished(runId, ok, error) {
            if (root._batchActive) {
                root._batchInFlight = Math.max(0, root._batchInFlight - 1)
                if (!ok) {
                    root._batchFailed += 1
                    root._batchErrors.push(root._shortRunIdValue(runId) + ": " + error)
                }
                root._pumpBatch()
                return
            }
            if (ok) {
                if (root.selectedRunId === runId)
                    root.selectedRunId = ""
                ObserverClient.refreshRuns()
            } else {
                noticeBar.show(I18n.t("删除失败：", "Delete failed: ") + error)
            }
        }
        function onRunItemsChanged() {
            if (root.selectedRunId !== "" && !root._findRun(root.selectedRunId).run_id)
                root.selectedRunId = ""
        }
    }

    ConfirmDialog {
        id: confirmDialog
        objectName: "historyConfirmDialog"
        parent: Overlay.overlay
        onConfirmed: {
            var act = root._onDialogConfirm
            root._onDialogConfirm = null
            if (act)
                act()
        }
        onClosed: Qt.callLater(function() { root._onDialogConfirm = null })
    }

    Rectangle {
        anchors.fill: parent
        visible: root.embeddedBackdrop
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.00; color: Theme.phase.day.bg }
            GradientStop { position: 0.48; color: Theme.warm.canvas }
            GradientStop { position: 1.00; color: Theme.parchment.parchmentStrong }
        }
    }

    Image {
        id: historyArchiveArt
        anchors.fill: parent
        visible: root.embeddedBackdrop
        source: Illustrations.historyArchive
        fillMode: Image.PreserveAspectCrop
        horizontalAlignment: Image.AlignHCenter
        verticalAlignment: Image.AlignVCenter
        asynchronous: true
        cache: true
        sourceSize.width: 1672
        sourceSize.height: 941
        opacity: status === Image.Ready ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.anim.press; easing.type: Easing.OutCubic } }
    }

    Rectangle {
        anchors.fill: parent
        visible: root.embeddedBackdrop
        color: Theme.withAlpha(Theme.warm.canvas, 0.26)
    }

    Rectangle {
        anchors.fill: parent
        visible: root.embeddedBackdrop
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.00; color: Theme.withAlpha(Theme.parchment.highlightCream, 0.24) }
            GradientStop { position: 0.58; color: Theme.withAlpha(Theme.parchment.highlightHoney, 0.08) }
            GradientStop { position: 1.00; color: Theme.withAlpha(Theme.parchment.shadowBrown, 0.18) }
        }
    }

    Rectangle {
        id: noticeBar
        objectName: "historyNoticeBar"
        property string text: ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.space.md
        z: 20
        visible: text !== ""
        width: noticeLabel.implicitWidth + Theme.space.xl * 2
        height: noticeLabel.implicitHeight + Theme.space.md * 2
        radius: Theme.radius.pill
        color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.97)
        border.width: 1
        border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.50)

        Image {
            anchors.fill: parent
            anchors.margins: 1
            source: Illustrations.texParchment
            fillMode: Image.Tile
            opacity: 0.14
        }

        Text {
            id: noticeLabel
            anchors.centerIn: parent
            text: noticeBar.text
            color: Theme.warm.bodyStrong
            font.family: Theme.fontFamilies.sans
            font.contextFontMerging: true
            font.pixelSize: Theme.size.caption
            font.weight: Theme.weight.medium
        }

        Timer {
            id: noticeTimer
            interval: 5000
            onTriggered: noticeBar.text = ""
        }
        function show(msg) {
            text = msg
            noticeTimer.restart()
        }
    }

    Item {
        id: page
        anchors.fill: parent
        anchors.margins: Theme.space.xxl

        readonly property int gap: Theme.space.lg
        readonly property int railWidth: Math.min(232, Math.max(198, Math.round(width * 0.17)))
        readonly property int detailWidth: Math.min(438, Math.max(342, Math.round(width * 0.34)))

        Item {
            id: header
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 116

            Rectangle {
                id: topBackButton
                objectName: "historyBackButton"
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.topMargin: Theme.space.sm
                width: historyBackButtonContent.implicitWidth + Theme.space.lg * 2
                height: 38
                radius: Theme.radius.pill
                color: historyBackHover.hovered ? Theme.withAlpha(Theme.parchment.parchmentSoft, 0.96)
                                                : Theme.withAlpha(Theme.parchment.parchmentSoft, 0.86)
                border.width: 1
                border.color: historyBackHover.hovered ? Theme.withAlpha(Theme.warm.primary, 0.46)
                                                       : Theme.withAlpha(Theme.parchment.goldLine, 0.48)

                Rectangle {
                    anchors.fill: parent
                    anchors.topMargin: 4
                    anchors.leftMargin: 3
                    anchors.rightMargin: -3
                    anchors.bottomMargin: -5
                    radius: parent.radius
                    color: Theme.withAlpha(Theme.parchment.woodShadow, 0.26)
                    z: -1
                }

                Image {
                    anchors.fill: parent
                    anchors.margins: 1
                    source: Illustrations.texParchment
                    fillMode: Image.Tile
                    opacity: 0.14
                }

                Row {
                    id: historyBackButtonContent
                    anchors.centerIn: parent
                    spacing: Theme.space.md
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "‹"
                        color: Theme.warm.primaryActive
                        font.family: Theme.fontFamilies.sans
                        font.contextFontMerging: true
                        font.pixelSize: 24
                        font.weight: Theme.weight.bold
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: I18n.t("返回", "Back")
                        color: Theme.warm.bodyStrong
                        font.family: Theme.fontFamilies.sans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.caption
                        font.weight: Theme.weight.semibold
                    }
                }

                HoverHandler {
                    id: historyBackHover
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler { onTapped: root.StackView.view.parent.navigateHome() }
            }

            Column {
                anchors.left: topBackButton.right
                anchors.top: parent.top
                anchors.topMargin: Theme.space.sm
                anchors.leftMargin: Theme.space.lg
                width: Math.max(300, parent.width - topBackButton.width - headerActions.width - Theme.space.xxl * 2)
                spacing: Theme.space.xs

                Text {
                    text: I18n.t("历史对局", "History")
                    color: Theme.warm.ink
                    font.family: Theme.fontFamilies.serif
                    font.contextFontMerging: true
                    font.pixelSize: 44
                    font.weight: Theme.weight.bold
                }

                Text {
                    width: parent.width
                    text: I18n.t("重温已记录的对局，查看战报，管理本地档案",
                                 "Revisit recorded matches, inspect reports, and manage local archives")
                    color: Theme.warm.body
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.bodyLg
                    elide: Text.ElideRight
                }
            }

            Row {
                id: headerActions
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.topMargin: Theme.space.lg
                spacing: Theme.space.md

                AppButton {
                    id: refreshButton
                    objectName: "historyRefreshButton"
                    onLight: true
                    text: I18n.t("刷新", "Refresh")
                    variant: "secondary"
                    enabled: !root._batchActive
                    onClicked: ObserverClient.refreshRuns()
                }

                AppButton {
                    id: selectModeButton
                    objectName: "selectModeButton"
                    onLight: true
                    text: root.selecting ? I18n.t("取消选择", "Cancel") : I18n.t("批量操作", "Batch actions")
                    variant: root.selecting ? "primary" : "secondary"
                    enabled: ObserverClient.runItems.length > 0 && !root._batchActive
                    onClicked: root.selecting ? root._exitSelectMode() : root.selecting = true
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.selecting
                    text: root._batchActive
                          ? I18n.t("正在删除 ", "Deleting ") + Math.max(0, root._batchCompleted)
                            + "/" + root._batchTotal
                          : I18n.t("已选择 ", "Selected ") + root.selectedCount + I18n.t(" 项", " items")
                    color: Theme.warm.bodyStrong
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                    font.weight: Theme.weight.semibold
                }

                AppButton {
                    id: batchDeleteButton
                    objectName: "batchDeleteButton"
                    onLight: true
                    visible: root.selecting
                    enabled: root.selectedCount > 0 && !root._batchActive
                    text: I18n.t("批量删除", "Batch delete")
                    variant: "danger"
                    onClicked: {
                        root._onDialogConfirm = root._startBatchDelete
                        confirmDialog.title = I18n.t("批量删除", "Batch delete")
                        confirmDialog.message = I18n.t("确定删除 ", "Delete ") + root.selectedCount
                                                + I18n.t(" 局?删除后不可恢复。失败项会保留在列表中。", " runs? This cannot be undone. Failed items stay in the list.")
                        confirmDialog.open()
                    }
                }
            }
        }

        Rectangle {
            id: filterRail
            anchors.left: parent.left
            anchors.top: header.bottom
            anchors.bottom: parent.bottom
            width: page.railWidth
            radius: 18
            color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.88)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.48)

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 10
                anchors.leftMargin: 5
                anchors.rightMargin: -5
                anchors.bottomMargin: -8
                radius: parent.radius
                color: Theme.withAlpha(Theme.parchment.woodShadow, 0.30)
                z: -1
            }

            Image {
                anchors.fill: parent
                anchors.margins: 2
                source: Illustrations.texParchment
                fillMode: Image.Tile
                opacity: 0.16
            }

            Column {
                anchors.fill: parent
                anchors.margins: Theme.space.lg
                spacing: Theme.space.md

                Text {
                    text: I18n.t("档案筛选", "Archive Filter")
                    color: Theme.warm.ink
                    font.family: Theme.fontFamilies.serif
                    font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.titleLg
                    font.weight: Theme.weight.semibold
                }

                Column {
                    width: parent.width
                    spacing: Theme.space.xs

                    Repeater {
                        model: [
                            { key: "all", label: I18n.t("全部", "All"), count: ObserverClient.runItems.length },
                            { key: "completed", label: I18n.t("已完成", "Completed"), count: root.completedCount },
                            { key: "running", label: I18n.t("进行中", "Running"), count: root.runningCount },
                            { key: "interrupted", label: I18n.t("中断", "Interrupted"), count: root.interruptedCount },
                            { key: "failed", label: I18n.t("失败", "Failed"), count: root.failedCount },
                            { key: "unknown", label: root._unknownLabel(), count: root.unknownCount }
                        ]
                        delegate: Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 38
                            radius: Theme.radius.md
                            readonly property bool selected: root.activeFilter === modelData.key
                            color: selected ? Theme.withAlpha(Theme.warm.primary, 0.82)
                                            : (filterHover.hovered ? Theme.withAlpha(Theme.warm.ink, 0.04) : "transparent")
                            border.width: selected ? 1 : 0
                            border.color: Theme.withAlpha(Theme.warm.primaryActive, 0.36)

                            Row {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: Theme.space.md
                                anchors.rightMargin: Theme.space.sm
                                spacing: Theme.space.sm

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "□"
                                    color: parent.parent.selected ? Theme.warm.textOnPrimary : Theme.warm.primaryActive
                                    font.family: Theme.fontFamilies.sans
                                    font.pixelSize: Theme.size.caption
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - countPill.width - Theme.space.xl * 2
                                    text: modelData.label
                                    color: parent.parent.selected ? Theme.warm.textOnPrimary : Theme.warm.bodyStrong
                                    font.family: Theme.fontFamilies.sans
                                    font.contextFontMerging: true
                                    font.pixelSize: Theme.size.body
                                    font.weight: Theme.weight.semibold
                                    elide: Text.ElideRight
                                }
                                Rectangle {
                                    id: countPill
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: countText.implicitWidth + Theme.space.md
                                    height: 22
                                    radius: Theme.radius.pill
                                    color: parent.parent.selected
                                           ? Theme.withAlpha(Theme.warm.textOnPrimary, 0.16)
                                           : Theme.withAlpha(Theme.parchment.goldLine, 0.13)
                                    border.width: 1
                                    border.color: parent.parent.selected
                                                  ? Theme.withAlpha(Theme.warm.textOnPrimary, 0.24)
                                                  : Theme.withAlpha(Theme.parchment.goldLine, 0.25)
                                    Text {
                                        id: countText
                                        anchors.centerIn: parent
                                        text: "" + modelData.count
                                        color: countPill.parent.parent.selected ? Theme.warm.textOnPrimary : Theme.warm.muted
                                        font.family: Theme.fontFamilies.sans
                                        font.pixelSize: Theme.size.micro
                                        font.weight: Theme.weight.bold
                                    }
                                }
                            }

                            HoverHandler {
                                id: filterHover
                                cursorShape: Qt.PointingHandCursor
                            }
                            TapHandler { onTapped: root.activeFilter = modelData.key }
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.35)
                }

                TextField {
                    id: searchField
                    width: parent.width
                    height: 40
                    text: root.searchText
                    placeholderText: I18n.t("搜索对局名 / Run ID", "Search match name / Run ID")
                    placeholderTextColor: Theme.warm.mutedSoft
                    color: Theme.warm.ink
                    selectedTextColor: Theme.warm.textOnPrimary
                    selectionColor: Theme.warm.primary
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                    leftPadding: Theme.space.md
                    rightPadding: Theme.space.xxl
                    onTextEdited: root.searchText = text
                    background: Rectangle {
                        radius: Theme.radius.md
                        color: Theme.withAlpha(Theme.parchment.parchment, 0.76)
                        border.width: 1
                        border.color: searchField.activeFocus
                                      ? Theme.withAlpha(Theme.warm.primary, 0.55)
                                      : Theme.withAlpha(Theme.parchment.goldLineSoft, 0.42)
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.space.md
                        anchors.verticalCenter: parent.verticalCenter
                        text: "⌕"
                        color: Theme.warm.muted
                        font.family: Theme.fontFamilies.sans
                        font.pixelSize: Theme.size.body
                    }
                }

                Text {
                    text: I18n.t("进阶筛选", "Advanced filters")
                    color: Theme.warm.bodyStrong
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.caption
                    font.weight: Theme.weight.semibold
                }

                Column {
                    width: parent.width
                    spacing: Theme.space.sm

                    ParchmentComboBox {
                        id: executionModeCombo
                        objectName: "historyExecutionModeCombo"
                        width: parent.width
                        compact: true
                        model: [
                            I18n.t("全部模式", "All modes"),
                            I18n.t("模拟", "Simulation"),
                            I18n.t("云端执行", "Cloud execution"),
                            I18n.t("本地执行", "Local execution"),
                            root._unknownLabel()
                        ]
                        onActivated: function(index) {
                            root.executionFilter = ["all", "fake", "live", "local", "unknown"][index]
                        }
                    }

                    ParchmentComboBox {
                        id: resultCombo
                        objectName: "historyResultCombo"
                        width: parent.width
                        compact: true
                        model: [
                            I18n.t("全部结果", "All results"),
                            I18n.t("好人阵营", "Good team"),
                            I18n.t("狼人阵营", "Werewolf team"),
                            root._unknownLabel()
                        ]
                        onActivated: function(index) {
                            root.resultFilter = ["all", "good", "wolf", "unknown"][index]
                        }
                    }

                    ParchmentComboBox {
                        id: timeCombo
                        objectName: "historyTimeCombo"
                        width: parent.width
                        compact: true
                        model: [
                            I18n.t("全部时间", "All time"),
                            I18n.t("最近 7 天", "Last 7 days"),
                            I18n.t("更早/未知", "Older / unknown")
                        ]
                        onActivated: function(index) {
                            root.timeFilter = ["all", "recent", "older"][index]
                        }
                    }
                }

                Item { width: 1; height: Math.max(0, parent.height - y - 48) }

                Text {
                    width: parent.width
                    text: I18n.t("筛选仅作用于已载入的本地档案。", "Filters apply to loaded local archives only.")
                    color: Theme.warm.muted
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.micro
                    wrapMode: Text.WordWrap
                    lineHeightMode: Text.ProportionalHeight
                    lineHeight: 1.25
                }
            }
        }

        Rectangle {
            id: listPanel
            anchors.left: filterRail.right
            anchors.leftMargin: page.gap
            anchors.top: header.bottom
            anchors.bottom: parent.bottom
            width: Math.max(430, page.width - page.railWidth - page.detailWidth - page.gap * 2)
            radius: 18
            color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.90)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.44)

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 12
                anchors.leftMargin: 5
                anchors.rightMargin: -5
                anchors.bottomMargin: -9
                radius: parent.radius
                color: Theme.withAlpha(Theme.parchment.woodShadow, 0.28)
                z: -1
            }

            Image {
                anchors.fill: parent
                anchors.margins: 2
                source: Illustrations.texParchment
                fillMode: Image.Tile
                opacity: 0.13
            }

            Item {
                id: listHeader
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space.lg
                height: 44

                Row {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Theme.space.md

                    CheckBox {
                        id: selectAllBox
                        objectName: "selectAllBox"
                        visible: root.selecting
                        enabled: root.filteredRuns.length > 0
                        width: visible ? 24 : 0
                        height: 24
                        text: ""
                        indicator: Rectangle {
                            x: 3
                            y: 3
                            width: 18
                            height: 18
                            radius: 5
                            color: selectAllBox.checked ? Theme.warm.primary : Theme.withAlpha(Theme.parchment.parchment, 0.72)
                            border.width: 1
                            border.color: selectAllBox.checked ? Theme.warm.primaryActive : Theme.withAlpha(Theme.parchment.goldLine, 0.48)
                            Text {
                                anchors.centerIn: parent
                                visible: selectAllBox.checked
                                text: "✓"
                                color: Theme.warm.textOnPrimary
                                font.family: Theme.fontFamilies.sans
                                font.pixelSize: Theme.size.caption
                                font.weight: Theme.weight.bold
                            }
                        }
                        contentItem: Item {}
                        onToggled: root._selectVisibleRuns(checked)
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1
                        Text {
                            text: I18n.t("对局档案", "Match Archive")
                            color: Theme.warm.ink
                            font.family: Theme.fontFamilies.serif
                            font.contextFontMerging: true
                            font.pixelSize: Theme.warmSize.titleLg
                            font.weight: Theme.weight.semibold
                        }
                        Text {
                            text: I18n.t("共 ", "Showing ") + root.filteredRuns.length
                                  + I18n.t(" 个对局", " matches")
                            color: Theme.warm.muted
                            font.family: Theme.fontFamilies.sans
                            font.contextFontMerging: true
                            font.pixelSize: Theme.size.caption
                        }
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: localChipText.implicitWidth + Theme.space.lg
                    height: 28
                    radius: Theme.radius.pill
                    color: Theme.withAlpha(Theme.parchment.goldLine, 0.13)
                    border.width: 1
                    border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.32)
                    Text {
                        id: localChipText
                        anchors.centerIn: parent
                        text: I18n.t("按时间排序（最新）", "Newest first")
                        color: Theme.warm.muted
                        font.family: Theme.fontFamilies.sans
                        font.contextFontMerging: true
                        font.pixelSize: Theme.size.micro
                        font.weight: Theme.weight.bold
                    }
                }
            }

            Rectangle {
                anchors.top: listHeader.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: Theme.space.lg
                anchors.rightMargin: Theme.space.lg
                height: 1
                color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.34)
            }

            ListView {
                id: historyRunsList
                objectName: "historyRunsList"
                anchors.top: listHeader.bottom
                anchors.topMargin: Theme.space.md
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: Theme.space.md
                anchors.rightMargin: Theme.space.sm
                anchors.bottomMargin: Theme.space.md
                model: root.filteredRuns
                clip: true
                visible: root.filteredRuns.length > 0
                spacing: Theme.space.sm
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    width: 9
                    contentItem: Rectangle {
                        implicitWidth: 7
                        radius: 4
                        color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.58)
                    }
                    background: Rectangle {
                        radius: 4
                        color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.38)
                    }
                }

                delegate: Item {
                    id: runDelegate
                    required property var modelData
                    width: historyRunsList.width - Theme.space.sm
                    height: 112

                    readonly property bool selected: root.selectedRunId === modelData.run_id
                    readonly property color accent: root._statusAccent(modelData.status)

                    Rectangle {
                        anchors.fill: card
                        anchors.topMargin: 8
                        anchors.leftMargin: 4
                        anchors.rightMargin: -4
                        anchors.bottomMargin: -5
                        radius: 16
                        color: Theme.withAlpha(Theme.parchment.woodShadow, runDelegate.selected ? 0.34 : 0.22)
                    }

                    Rectangle {
                        id: card
                        anchors.fill: parent
                        anchors.leftMargin: Theme.space.xs
                        anchors.rightMargin: Theme.space.md
                        radius: 16
                        color: runCardHover.hovered || runDelegate.selected
                               ? Theme.withAlpha(Theme.parchment.parchment, 0.94)
                               : Theme.withAlpha(Theme.parchment.parchmentSoft, 0.86)
                        border.width: runDelegate.selected ? 2 : 1
                        border.color: runDelegate.selected
                                      ? Theme.withAlpha(Theme.warm.primary, 0.82)
                                      : Theme.withAlpha(Theme.parchment.goldLine, 0.38)

                        Image {
                            anchors.fill: parent
                            anchors.margins: 2
                            source: Illustrations.texParchment
                            fillMode: Image.Tile
                            opacity: 0.14
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: runDelegate.selected ? 5 : 3
                            radius: 3
                            color: runDelegate.selected ? Theme.warm.primary : runDelegate.accent
                            opacity: runDelegate.selected ? 1.0 : 0.65
                        }

                        CheckBox {
                            id: rowSelectBox
                            objectName: "rowSelectBox"
                            visible: root.selecting
                            enabled: root._canDelete(modelData)
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.space.md
                            anchors.verticalCenter: parent.verticalCenter
                            width: visible ? 24 : 0
                            height: 24
                            text: ""
                            checked: root._selected[modelData.run_id] === true
                            indicator: Rectangle {
                                x: 3
                                y: 3
                                width: 18
                                height: 18
                                radius: 5
                                color: rowSelectBox.checked ? Theme.warm.primary
                                                            : Theme.withAlpha(Theme.parchment.parchment, 0.76)
                                border.width: 1
                                border.color: rowSelectBox.checked ? Theme.warm.primaryActive
                                                                   : Theme.withAlpha(Theme.parchment.goldLine, 0.48)
                                opacity: rowSelectBox.enabled ? 1.0 : 0.45
                                Text {
                                    anchors.centerIn: parent
                                    visible: rowSelectBox.checked
                                    text: "✓"
                                    color: Theme.warm.textOnPrimary
                                    font.family: Theme.fontFamilies.sans
                                    font.pixelSize: Theme.size.caption
                                    font.weight: Theme.weight.bold
                                }
                            }
                            contentItem: Item {}
                            onToggled: root._toggleSelected(modelData.run_id, checked)
                        }

                        Rectangle {
                            id: dossierSeal
                            anchors.left: parent.left
                            anchors.leftMargin: root.selecting ? 48 : 20
                            anchors.verticalCenter: parent.verticalCenter
                            width: 70
                            height: 70
                            radius: 35
                            color: Theme.withAlpha(runDelegate.accent, 0.15)
                            border.width: 1
                            border.color: Theme.withAlpha(runDelegate.accent, 0.52)

                            Rectangle {
                                anchors.centerIn: parent
                                width: 54
                                height: 54
                                radius: 27
                                color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.72)
                                border.width: 1
                                border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.35)
                                Text {
                                    anchors.centerIn: parent
                                    text: root._statusKey(modelData.status) === "running"
                                          ? "月" : (root._statusKey(modelData.status) === "interrupted" ? "断" : "档")
                                    color: runDelegate.accent
                                    font.family: Theme.fontFamilies.serif
                                    font.contextFontMerging: true
                                    font.pixelSize: 22
                                    font.weight: Theme.weight.bold
                                }
                            }

                            Behavior on anchors.leftMargin { NumberAnimation { duration: Theme.motion.fast; easing.type: Easing.OutCubic } }
                        }

                        Column {
                            id: cardText
                            anchors.left: dossierSeal.right
                            anchors.leftMargin: Theme.space.md
                            anchors.right: cardActions.left
                            anchors.rightMargin: Theme.space.md
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Theme.space.xs

                            Row {
                                width: parent.width
                                spacing: Theme.space.sm
                                Text {
                                    width: parent.width - statusChip.width - Theme.space.sm
                                    text: root._runTitle(modelData)
                                    color: Theme.warm.ink
                                    font.family: Theme.fontFamilies.serif
                                    font.contextFontMerging: true
                                    font.pixelSize: Theme.warmSize.titleMd
                                    font.weight: Theme.weight.semibold
                                    elide: Text.ElideRight
                                }
                                Rectangle {
                                    id: statusChip
                                    width: statusChipText.implicitWidth + Theme.space.md * 2
                                    height: 24
                                    radius: Theme.radius.pill
                                    color: Theme.withAlpha(runDelegate.accent, 0.14)
                                    border.width: 1
                                    border.color: Theme.withAlpha(runDelegate.accent, 0.46)
                                    Text {
                                        id: statusChipText
                                        anchors.centerIn: parent
                                        text: root._statusLabel(modelData.status)
                                        color: Qt.darker(runDelegate.accent, 1.25)
                                        font.family: Theme.fontFamilies.sans
                                        font.contextFontMerging: true
                                        font.pixelSize: Theme.size.micro
                                        font.weight: Theme.weight.bold
                                    }
                                }
                            }

                            Text {
                                width: parent.width
                                text: I18n.t("对局 ID: ", "Run ID: ") + root._shortRunId(modelData)
                                color: Theme.warm.muted
                                font.family: Theme.fontFamilies.mono
                                font.pixelSize: Theme.size.caption
                                elide: Text.ElideRight
                            }

                            Text {
                                width: parent.width
                                text: root._templateLabel(modelData) + " · "
                                      + root._executionLabel(modelData) + " · "
                                      + root._timeLabel(modelData)
                                color: Theme.warm.body
                                font.family: Theme.fontFamilies.sans
                                font.contextFontMerging: true
                                font.pixelSize: Theme.size.caption
                                elide: Text.ElideRight
                            }

                            Row {
                                width: parent.width
                                spacing: Theme.space.lg
                                Text {
                                    text: root._resultLabel(modelData)
                                    color: Theme.warm.bodyStrong
                                    font.family: Theme.fontFamilies.sans
                                    font.contextFontMerging: true
                                    font.pixelSize: Theme.size.caption
                                    font.weight: Theme.weight.semibold
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: root._summaryLabel(modelData)
                                    color: Theme.warm.muted
                                    font.family: Theme.fontFamilies.sans
                                    font.contextFontMerging: true
                                    font.pixelSize: Theme.size.micro
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Row {
                            id: cardActions
                            anchors.right: parent.right
                            anchors.rightMargin: Theme.space.md
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Theme.space.xs
                            visible: !root.selecting

                            AppButton {
                                id: reportButton
                                objectName: "openSettlementButton"
                                onLight: true
                                width: visible ? (enabled ? 92 : 104) : 0
                                height: 34
                                visible: (modelData.status || "") === "completed"
                                enabled: root._canViewReport(modelData)
                                text: enabled ? I18n.t("查看战报", "View report")
                                              : I18n.t("战报不可用", "No report")
                                variant: "secondary"
                                onClicked: root._openRun(modelData, true)
                            }

                            AppButton {
                                id: openButton
                                objectName: "openReplayButton"
                                onLight: true
                                width: {
                                    var key = root._statusKey(modelData.status)
                                    return key === "running" || key === "queued" ? 92 : 66
                                }
                                height: 34
                                text: root._openActionLabel(modelData)
                                variant: "primary"
                                onClicked: root._openRun(modelData, false)
                            }

                            AppButton {
                                id: deleteButton
                                objectName: "deleteRunButton"
                                onLight: true
                                width: 66
                                height: 34
                                enabled: root._canDelete(modelData)
                                text: I18n.t("删除", "Delete")
                                variant: "danger"
                                onClicked: root._confirmDelete(modelData)
                            }
                        }

                        HoverHandler {
                            id: runCardHover
                            cursorShape: Qt.PointingHandCursor
                        }
                        TapHandler {
                            onTapped: root.selectedRunId = modelData.run_id
                        }
                    }
                }
            }

            EmptyState {
                anchors.centerIn: parent
                visible: root.filteredRuns.length === 0
                onLight: true
                title: ObserverClient.runItems.length === 0
                       ? I18n.t("暂无记录", "No runs recorded")
                       : I18n.t("没有匹配的档案", "No matching archives")
                subtitle: ObserverClient.runItems.length === 0
                          ? I18n.t("已完成与进行中的对局将显示在此。", "Completed and in-progress matches will appear here.")
                          : I18n.t("调整筛选或搜索词后再试。", "Try a different filter or search term.")
            }
        }

        Rectangle {
            id: detailPanel
            anchors.left: listPanel.right
            anchors.leftMargin: page.gap
            anchors.top: header.bottom
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            radius: 22
            color: Theme.withAlpha(Theme.parchment.parchmentSoft, 0.91)
            border.width: 1
            border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.52)

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 14
                anchors.leftMargin: 6
                anchors.rightMargin: -6
                anchors.bottomMargin: -10
                radius: parent.radius
                color: Theme.withAlpha(Theme.parchment.woodShadow, 0.32)
                z: -1
            }

            Image {
                anchors.fill: parent
                anchors.margins: 2
                source: Illustrations.texParchment
                fillMode: Image.Tile
                opacity: 0.17
            }

            Column {
                visible: !root.hasSelectedRun
                anchors.centerIn: parent
                width: Math.min(300, parent.width - Theme.space.xxl * 2)
                spacing: Theme.space.md

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 74
                    height: 74
                    radius: 37
                    color: Theme.withAlpha(Theme.parchment.goldLine, 0.12)
                    border.width: 1
                    border.color: Theme.withAlpha(Theme.parchment.goldLine, 0.36)
                    Text {
                        anchors.centerIn: parent
                        text: "档"
                        color: Theme.warm.muted
                        font.family: Theme.fontFamilies.serif
                        font.contextFontMerging: true
                        font.pixelSize: 30
                        font.weight: Theme.weight.bold
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: I18n.t("请选择一局对局", "No match selected")
                    color: Theme.warm.ink
                    font.family: Theme.fontFamilies.serif
                    font.contextFontMerging: true
                    font.pixelSize: Theme.warmSize.titleLg
                    font.weight: Theme.weight.semibold
                    horizontalAlignment: Text.AlignHCenter
                }

                Text {
                    width: parent.width
                    text: I18n.t("选择一局对局以查看详情、战报或回放。",
                                 "Choose a match to inspect details, reports, or replay.")
                    color: Theme.warm.body
                    font.family: Theme.fontFamilies.sans
                    font.contextFontMerging: true
                    font.pixelSize: Theme.size.body
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    lineHeightMode: Text.ProportionalHeight
                    lineHeight: 1.35
                }
            }

            Flickable {
                id: detailFlick
                visible: root.hasSelectedRun
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: detailActions.top
                anchors.margins: Theme.space.xl
                anchors.bottomMargin: Theme.space.md
                clip: true
                contentWidth: width
                contentHeight: detailColumn.implicitHeight
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    width: 8
                    contentItem: Rectangle {
                        implicitWidth: 6
                        radius: 3
                        color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.52)
                    }
                    background: Rectangle {
                        radius: 3
                        color: Theme.withAlpha(Theme.parchment.parchmentStrong, 0.34)
                    }
                }

                Column {
                    id: detailColumn
                    width: detailFlick.width - Theme.space.sm
                    spacing: Theme.space.md

                    Row {
                        width: parent.width
                        spacing: Theme.space.md

                        Rectangle {
                            width: 86
                            height: 86
                            radius: 43
                            color: Theme.withAlpha(root._statusAccent(root.selectedRun.status), 0.16)
                            border.width: 1
                            border.color: Theme.withAlpha(root._statusAccent(root.selectedRun.status), 0.56)
                            Text {
                                anchors.centerIn: parent
                                text: "档"
                                color: root._statusAccent(root.selectedRun.status)
                                font.family: Theme.fontFamilies.serif
                                font.contextFontMerging: true
                                font.pixelSize: 30
                                font.weight: Theme.weight.bold
                            }
                        }

                        Column {
                            width: parent.width - 86 - Theme.space.md
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Theme.space.xs

                            Row {
                                width: parent.width
                                spacing: Theme.space.sm
                                Text {
                                    width: parent.width - detailStatusChip.width - Theme.space.sm
                                    text: root._runTitle(root.selectedRun)
                                    color: Theme.warm.ink
                                    font.family: Theme.fontFamilies.serif
                                    font.contextFontMerging: true
                                    font.pixelSize: Theme.warmSize.titleLg
                                    font.weight: Theme.weight.bold
                                    elide: Text.ElideRight
                                }
                                Rectangle {
                                    id: detailStatusChip
                                    width: detailStatusText.implicitWidth + Theme.space.md * 2
                                    height: 25
                                    radius: Theme.radius.pill
                                    color: Theme.withAlpha(root._statusAccent(root.selectedRun.status), 0.14)
                                    border.width: 1
                                    border.color: Theme.withAlpha(root._statusAccent(root.selectedRun.status), 0.48)
                                    Text {
                                        id: detailStatusText
                                        anchors.centerIn: parent
                                        text: root._statusLabel(root.selectedRun.status)
                                        color: Qt.darker(root._statusAccent(root.selectedRun.status), 1.25)
                                        font.family: Theme.fontFamilies.sans
                                        font.contextFontMerging: true
                                        font.pixelSize: Theme.size.micro
                                        font.weight: Theme.weight.bold
                                    }
                                }
                            }

                            Text {
                                width: parent.width
                                text: I18n.t("对局 ID: ", "Run ID: ")
                                      + (root.selectedRun.run_id || root._unknownLabel())
                                color: Theme.warm.muted
                                font.family: Theme.fontFamilies.mono
                                font.pixelSize: Theme.size.caption
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.36)
                    }

                    Rectangle {
                        width: parent.width
                        height: detailGrid.implicitHeight + Theme.space.lg * 2
                        radius: 16
                        color: Theme.withAlpha(Theme.parchment.parchment, 0.62)
                        border.width: 1
                        border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.38)

                        Grid {
                            id: detailGrid
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.space.lg
                            columns: 2
                            rowSpacing: Theme.space.md
                            columnSpacing: Theme.space.lg

                            Repeater {
                                model: [
                                    { label: I18n.t("对局类型", "Match type"), value: root._templateLabel(root.selectedRun) },
                                    { label: I18n.t("执行模式", "Execution mode"), value: root._executionLabel(root.selectedRun) },
                                    { label: I18n.t("创建时间", "Created"), value: root._timeLabel(root.selectedRun) },
                                    { label: I18n.t("结束时间", "Finished"), value: root._endTimeLabel(root.selectedRun) },
                                    { label: I18n.t("总时长", "Duration"), value: root._durationLabel(root.selectedRun) },
                                    { label: I18n.t("当前版本", "Version"), value: root._versionLabel(root.selectedRun) }
                                ]
                                delegate: Column {
                                    required property var modelData
                                    width: (detailGrid.width - Theme.space.lg) / 2
                                    spacing: 2
                                    Text {
                                        width: parent.width
                                        text: modelData.label
                                        color: Theme.warm.muted
                                        font.family: Theme.fontFamilies.sans
                                        font.contextFontMerging: true
                                        font.pixelSize: Theme.size.micro
                                        font.weight: Theme.weight.bold
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        width: parent.width
                                        text: "" + modelData.value
                                        color: Theme.warm.bodyStrong
                                        font.family: Theme.fontFamilies.sans
                                        font.contextFontMerging: true
                                        font.pixelSize: Theme.size.caption
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 82
                        radius: 16
                        color: Theme.withAlpha(Theme.parchment.terracottaWash, 0.40)
                        border.width: 1
                        border.color: Theme.withAlpha(Theme.warm.primary, 0.28)

                        Column {
                            anchors.fill: parent
                            anchors.margins: Theme.space.lg
                            spacing: Theme.space.xs
                            Text {
                                text: I18n.t("对局结果", "Match result")
                                color: Theme.warm.muted
                                font.family: Theme.fontFamilies.sans
                                font.contextFontMerging: true
                                font.pixelSize: Theme.size.micro
                                font.weight: Theme.weight.bold
                            }
                            Text {
                                width: parent.width
                                text: root._resultLabel(root.selectedRun)
                                color: Theme.warm.primaryActive
                                font.family: Theme.fontFamilies.serif
                                font.contextFontMerging: true
                                font.pixelSize: Theme.warmSize.titleMd
                                font.weight: Theme.weight.bold
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 92
                        radius: 16
                        color: Theme.withAlpha(Theme.parchment.parchment, 0.60)
                        border.width: 1
                        border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.38)
                        Column {
                            anchors.fill: parent
                            anchors.margins: Theme.space.lg
                            spacing: Theme.space.xs
                            Text {
                                text: I18n.t("角色配置 / 阵营摘要", "Role setup / team summary")
                                color: Theme.warm.ink
                                font.family: Theme.fontFamilies.serif
                                font.contextFontMerging: true
                                font.pixelSize: Theme.warmSize.titleMd
                                font.weight: Theme.weight.semibold
                            }
                            Text {
                                width: parent.width
                                text: root._roleSummary(root.selectedRun)
                                color: Theme.warm.body
                                font.family: Theme.fontFamilies.sans
                                font.contextFontMerging: true
                                font.pixelSize: Theme.size.caption
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 124
                        radius: 16
                        color: Theme.withAlpha(Theme.parchment.parchment, 0.60)
                        border.width: 1
                        border.color: Theme.withAlpha(Theme.parchment.goldLineSoft, 0.38)
                        Column {
                            anchors.fill: parent
                            anchors.margins: Theme.space.lg
                            spacing: Theme.space.xs
                            Text {
                                text: I18n.t("精彩摘要 / 最近日志", "Highlights / recent notes")
                                color: Theme.warm.ink
                                font.family: Theme.fontFamilies.serif
                                font.contextFontMerging: true
                                font.pixelSize: Theme.warmSize.titleMd
                                font.weight: Theme.weight.semibold
                            }
                            Text {
                                width: parent.width
                                text: root._summaryLabel(root.selectedRun)
                                color: Theme.warm.body
                                font.family: Theme.fontFamilies.sans
                                font.contextFontMerging: true
                                font.pixelSize: Theme.size.caption
                                wrapMode: Text.WordWrap
                                lineHeightMode: Text.ProportionalHeight
                                lineHeight: 1.35
                            }
                        }
                    }
                }
            }

            Row {
                id: detailActions
                visible: root.hasSelectedRun
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: Theme.space.xl
                spacing: Theme.space.sm

                AppButton {
                    onLight: true
                    width: (parent.width - Theme.space.sm * 2) / 3
                    text: root._openActionLabel(root.selectedRun)
                    variant: "primary"
                    onClicked: root._openRun(root.selectedRun, false)
                }

                AppButton {
                    onLight: true
                    width: (parent.width - Theme.space.sm * 2) / 3
                    text: root._canViewReport(root.selectedRun)
                          ? I18n.t("查看战报", "View report")
                          : I18n.t("战报不可用", "No report")
                    variant: "secondary"
                    enabled: root.hasSelectedRun && root._canViewReport(root.selectedRun)
                    onClicked: root._openRun(root.selectedRun, true)
                }

                AppButton {
                    onLight: true
                    width: (parent.width - Theme.space.sm * 2) / 3
                    text: I18n.t("删除", "Delete")
                    variant: "danger"
                    enabled: root.hasSelectedRun && root._canDelete(root.selectedRun)
                    onClicked: root._confirmDelete(root.selectedRun)
                }
            }
        }

    }
}

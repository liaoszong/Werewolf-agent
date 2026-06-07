import QtQuick
import QtQuick.Controls
import qt_observer

// P2-D §7.5 — the right-hand (72%) scrolling battle report. A ListView of sections:
//   winner header (hosts WinnerBanner) -> turning_points sections (each carries its
//   cursor_index anchor) -> core_metrics card -> a P3 加挂位 placeholder.
//
// Single-cursor wiring (D6): this view never OWNS the cursor. It only:
//   - WRITES via cursorRequested(index) from scroll-spy (top-most visible section),
//   - is DRIVEN by the parent via scrollTo(index) (sets _programmaticScroll to mute
//     the spy during the programmatic jump, clearing it on the scroll's settle).
// degraded bundle -> battle regions render EmptyState「战报数据不可用 · 仅显示对局结果」.
Item {
    id: root
    objectName: "settlementReport"

    property var bundle: ({})
    property int activeIndex: 0
    signal cursorRequested(int index)

    // Anti-feedback-loop flag (D6): true while a parent-driven scrollTo() animation
    // is running so the scroll-spy does NOT write the cursor back (no double-jump).
    property bool _programmaticScroll: false

    readonly property bool _degraded: bundle && bundle.degraded === true
    readonly property var _turningPoints: (bundle && bundle.turning_points) ? bundle.turning_points : []
    readonly property var _metrics: (bundle && bundle.core_metrics) ? bundle.core_metrics : ({})
    // Partial degrade (product decision B): result metrics are present but the
    // decision-quality axis is unavailable (no/unusable decision-log).
    readonly property bool _dqUnavailable: bundle && bundle.degraded !== true
        && bundle.decision_quality_available === false

    // Section model: a flat list the ListView renders. Each entry carries the kind
    // and (for turning-point sections) the cursor_index anchor used by the spy.
    function _sections() {
        var out = []
        out.push({ kind: "winner", cursor_index: 0 })
        if (!_degraded) {
            for (var i = 0; i < _turningPoints.length; i++) {
                var tp = _turningPoints[i]
                out.push({ kind: "turning_point", tp: tp,
                           cursor_index: (tp && tp.cursor_index !== undefined) ? tp.cursor_index : 0 })
            }
            out.push({ kind: "metrics", cursor_index: 0 })
        } else {
            out.push({ kind: "degraded", cursor_index: 0 })
        }
        out.push({ kind: "p3_placeholder", cursor_index: 0 })
        return out
    }

    // Parent-driven scroll-to-anchor (spine click path). Guards the spy, jumps, then
    // releases the guard once the flick settles (one-shot Timer fallback).
    function scrollTo(index) {
        // The spine emits a board_timeline node index, but only turning-point sections
        // have anchors. Most nodes (quiet nights, setup) have no turning point, so an
        // exact match fails for the majority of clicks. Fall back to the NEAREST
        // preceding turning point; if the node precedes them all, scroll to the top
        // (winner header). Every spine click now lands somewhere meaningful (D6 fix).
        var secs = list.model
        var target = -1
        var bestSection = -1
        var bestCursor = -1
        for (var i = 0; i < secs.length; i++) {
            if (secs[i].kind !== "turning_point")
                continue
            if (secs[i].cursor_index === index) {
                target = i
                break
            }
            if (secs[i].cursor_index <= index && secs[i].cursor_index > bestCursor) {
                bestCursor = secs[i].cursor_index
                bestSection = i
            }
        }
        if (target < 0)
            target = bestSection >= 0 ? bestSection : 0   // nearest preceding TP, else winner
        root._programmaticScroll = true
        list.positionViewAtIndex(target, ListView.Beginning)
        guardReleaseTimer.restart()
    }

    Timer {
        id: guardReleaseTimer
        interval: Theme.motion.slow
        repeat: false
        onTriggered: root._programmaticScroll = false
    }

    ListView {
        id: list
        anchors.fill: parent
        clip: true
        spacing: Theme.space.lg
        boundsBehavior: Flickable.StopAtBounds
        model: root._sections()

        // Scroll-spy: on a user-driven scroll, find the top-most visible section and
        // request its cursor. Muted while a parent-driven scrollTo() is animating (D6).
        onContentYChanged: {
            if (root._programmaticScroll)
                return
            var idx = indexAt(width / 2, contentY + 1)
            if (idx < 0)
                return
            var sec = model[idx]
            if (sec && sec.kind === "turning_point")
                root.cursorRequested(sec.cursor_index)
        }

        delegate: Item {
            id: section
            width: ListView.view ? ListView.view.width : 0
            implicitHeight: body.implicitHeight + Theme.space.lg
            readonly property var sec: modelData

            Column {
                id: body
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: Theme.space.md

                // ----- winner header (freeze-beat banner, shrunk to a report header)
                WinnerBanner {
                    visible: section.sec.kind === "winner"
                    width: parent.width
                    light: true                       // on the warm-beige report canvas
                    result: (root.bundle && root.bundle.result) ? root.bundle.result : ({})
                }

                // ----- turning-point section (anchored by its cursor_index)
                // Light card, hairline border, with a coral left accent bar — the
                // turning point is THE thing to spot, so it gets the single accent.
                Rectangle {
                    visible: section.sec.kind === "turning_point"
                    width: parent.width
                    implicitHeight: tpCol.implicitHeight + Theme.space.lg * 2
                    radius: Theme.radius.lg
                    color: Theme.report.card
                    border.width: 1
                    border.color: Theme.report.border

                    Rectangle {   // coral accent bar
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.margins: 1
                        width: 4
                        radius: 2
                        color: Theme.report.accent
                    }

                    Column {
                        id: tpCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.leftMargin: Theme.space.lg + Theme.space.sm
                        anchors.rightMargin: Theme.space.lg
                        anchors.topMargin: Theme.space.lg
                        spacing: Theme.space.sm

                        Text {
                            width: parent.width
                            text: (section.sec.tp && section.sec.tp.title) ? section.sec.tp.title : ""
                            color: Theme.report.text
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.h2
                            font.weight: Theme.weight.semibold
                            wrapMode: Text.WordWrap
                        }
                        Text {
                            width: parent.width
                            text: (section.sec.tp && section.sec.tp.description) ? section.sec.tp.description : ""
                            color: Theme.report.textSecondary
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.body
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                // ----- core metrics — a COMPACT horizontal stat board (issue #1b):
                // 对局天数 [2] | 胜负差 [3] | MVP [p3] in one short row. Big value on
                // top, muted label below; hairline dividers between. Low height frees
                // the space below for the P3 long-text analysis.
                Rectangle {
                    visible: section.sec.kind === "metrics"
                    width: parent.width
                    implicitHeight: metricsCol.implicitHeight + Theme.space.lg * 2
                    radius: Theme.radius.lg
                    color: Theme.report.card
                    border.width: 1
                    border.color: Theme.report.border

                  Column {
                    id: metricsCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: Theme.space.lg
                    anchors.rightMargin: Theme.space.lg
                    spacing: Theme.space.md

                    Row {
                        id: statRow
                        anchors.left: parent.left
                        anchors.right: parent.right

                        readonly property int cellW: (width - 2) / 3   // 3 cells, 2 hairline dividers

                        component Stat: Column {
                            property string statValue: "—"
                            property string statLabel: ""
                            width: statRow.cellW
                            spacing: Theme.space.xs
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: parent.statValue
                                color: Theme.report.text
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.h1
                                font.weight: Theme.weight.bold
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: parent.statLabel
                                color: Theme.report.textMuted
                                font.family: Theme.font.family
                                font.pixelSize: Theme.size.caption
                            }
                        }
                        component Divider: Rectangle {
                            width: 1
                            height: Theme.size.h1 + Theme.size.caption + Theme.space.xs
                            color: Theme.report.border
                        }

                        Stat {
                            statValue: root._metrics.game_length !== undefined ? ("" + root._metrics.game_length) : "—"
                            statLabel: I18n.t("对局天数", "Days")
                        }
                        Divider {}
                        Stat {
                            statValue: (root._metrics.margin !== undefined && root._metrics.margin !== null) ? ("" + root._metrics.margin) : "—"
                            statLabel: I18n.t("胜负差", "Margin")
                        }
                        Divider {}
                        Stat {
                            statValue: root._metrics.mvp_player_id ? ("" + root._metrics.mvp_player_id) : "—"
                            statLabel: "MVP"
                        }
                    }

                    // Partial-degrade note (product decision B): result metrics shown,
                    // but the decision-quality axis is unavailable without a decision-log.
                    Text {
                        visible: root._dqUnavailable
                        anchors.left: parent.left
                        anchors.right: parent.right
                        text: I18n.t("决策质量分不可用 · 缺少决策日志",
                                     "Decision-quality scores unavailable · no decision log")
                        color: Theme.report.textMuted
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.caption
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                  }
                }

                // ----- degraded: battle regions unavailable
                Rectangle {
                    visible: section.sec.kind === "degraded"
                    width: parent.width
                    implicitHeight: 160
                    radius: Theme.radius.lg
                    color: Theme.report.card
                    border.width: 1
                    border.color: Theme.report.border

                    Column {
                        anchors.centerIn: parent
                        spacing: Theme.space.sm
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: I18n.t("战报数据不可用", "Battle report unavailable")
                            color: Theme.report.textSecondary
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.body
                            font.weight: Theme.weight.medium
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: I18n.t("仅显示对局结果", "Showing the match result only")
                            color: Theme.report.textMuted
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.caption
                        }
                    }
                }

                // ----- P3 加挂位 (per-player analysis / metrics / win-rate curve land here)
                Item {
                    visible: section.sec.kind === "p3_placeholder"
                    width: parent.width
                    implicitHeight: p3Text.implicitHeight + Theme.space.xl

                    Text {
                        id: p3Text
                        anchors.centerIn: parent
                        text: I18n.t("P3 加挂位 · 逐人复盘 / 全过程指标", "P3 slot · per-player review / full metrics")
                        color: Theme.report.textMuted
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.caption
                    }
                }
            }
        }

        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
    }
}

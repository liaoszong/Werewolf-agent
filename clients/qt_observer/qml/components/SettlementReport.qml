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
        var target = -1
        var secs = list.model
        for (var i = 0; i < secs.length; i++) {
            if (secs[i].kind === "turning_point" && secs[i].cursor_index === index) {
                target = i
                break
            }
        }
        if (target < 0)
            return
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
                    result: (root.bundle && root.bundle.result) ? root.bundle.result : ({})
                }

                // ----- turning-point section (anchored by its cursor_index)
                AppCard {
                    visible: section.sec.kind === "turning_point"
                    width: parent.width
                    implicitHeight: tpCol.implicitHeight + Theme.space.lg * 2

                    Column {
                        id: tpCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.space.lg
                        spacing: Theme.space.sm

                        Text {
                            width: parent.width
                            text: (section.sec.tp && section.sec.tp.title) ? section.sec.tp.title : ""
                            color: Theme.color.text
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.h2
                            font.weight: Theme.weight.semibold
                            wrapMode: Text.WordWrap
                        }
                        Text {
                            width: parent.width
                            text: (section.sec.tp && section.sec.tp.description) ? section.sec.tp.description : ""
                            color: Theme.color.textSecondary
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.body
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                // ----- core metrics card row
                AppCard {
                    visible: section.sec.kind === "metrics"
                    width: parent.width
                    implicitHeight: metricsCol.implicitHeight + Theme.space.lg * 2

                    Column {
                        id: metricsCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.space.lg
                        spacing: Theme.space.sm

                        SectionHeader { title: I18n.t("核心指标", "Core metrics") }

                        Text {
                            text: I18n.t("对局天数", "Game length") + ": "
                                  + (root._metrics.game_length !== undefined ? root._metrics.game_length : "—")
                            color: Theme.color.textSecondary
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.small
                        }
                        Text {
                            text: I18n.t("胜负差", "Margin") + ": "
                                  + (root._metrics.margin !== undefined && root._metrics.margin !== null ? root._metrics.margin : "—")
                            color: Theme.color.textSecondary
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.small
                        }
                        Text {
                            text: "MVP: " + (root._metrics.mvp_player_id ? root._metrics.mvp_player_id : "—")
                            color: Theme.color.textSecondary
                            font.family: Theme.font.family
                            font.pixelSize: Theme.size.small
                        }
                    }
                }

                // ----- degraded: battle regions unavailable
                AppCard {
                    visible: section.sec.kind === "degraded"
                    width: parent.width
                    implicitHeight: 160

                    EmptyState {
                        anchors.centerIn: parent
                        title: I18n.t("战报数据不可用", "Battle report unavailable")
                        subtitle: I18n.t("仅显示对局结果", "Showing the match result only")
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
                        color: Theme.color.textMuted
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.caption
                    }
                }
            }
        }

        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
    }
}

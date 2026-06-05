import QtQuick
import qt_observer

// G3-2 segmented live/fake arming control — INTENT (not executed truth).
//
// Two-click arming FSM (canonical):
//   fake → (click LIVE API, available) → live_armed
//   live_armed → (click ARM LIVE) → live_confirmed
//   any of {DETERMINISTIC, profile/seat change, live→unavailable} → fake
//
// The FSM is the inherited string `state` property holding exactly the literal
// tokens "fake" | "live_armed" | "live_confirmed".  resetToFake() is the SINGLE
// disarm entry point (C3) — the parent calls it on profile/seat change and when
// live becomes unavailable; the FSM state is never mutated externally.
// The view launches with `resolvedMode` — "live" ONLY in live_confirmed (C2).
Item {
    id: root

    state: "fake"

    // The resolved launch mode — "live" ONLY when fully confirmed; else "fake".
    readonly property string resolvedMode: root.state === "live_confirmed" ? "live" : "fake"

    // Posture comes from the read-only capabilities endpoint (server-supplied);
    // the reason code/message are rendered verbatim (data-driven), never literals.
    readonly property bool liveAvailable: ObserverClient.liveAvailable
    readonly property string liveReasonCode: ObserverClient.liveReasonCode
    readonly property string liveReasonMessage: ObserverClient.liveReasonMessage

    implicitWidth: 380
    implicitHeight: col.implicitHeight

    // C3: the ONE disarm entry point.
    function resetToFake() { root.state = "fake" }

    Column {
        id: col
        width: parent.width
        spacing: Theme.space.sm

        // ---- Segmented [ DETERMINISTIC | LIVE API ] ----
        Row {
            spacing: Theme.space.xs

            // DETERMINISTIC — the safe, unconditional default.
            Rectangle {
                id: segFake
                width: 150; height: 34
                radius: Theme.radius.sm
                color: root.state === "fake" ? Theme.color.surfaceAlt : Theme.color.surfaceInset
                border.width: 1
                border.color: root.state === "fake" ? Theme.color.borderStrong : Theme.color.border
                Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                Text {
                    anchors.centerIn: parent
                    text: I18n.t("模拟（免费）", "SIMULATION (FREE)")
                    color: root.state === "fake" ? Theme.color.text : Theme.color.textMuted
                    font.family: Theme.font.family
                    font.pixelSize: Theme.size.micro
                    font.weight: Theme.weight.semibold
                    font.letterSpacing: 1
                }
                TapHandler { onTapped: root.resetToFake() }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }

            // LIVE API — disabled + "UNAVAIL · <reason_code>" when unavailable.
            Rectangle {
                id: segLive
                width: 218; height: 34
                radius: Theme.radius.sm
                readonly property bool engaged: root.state === "live_armed" || root.state === "live_confirmed"
                opacity: root.liveAvailable ? 1.0 : 0.55
                color: segLive.engaged ? Theme.color.surfaceAlt : Theme.color.surfaceInset
                border.width: 1
                border.color: segLive.engaged ? Theme.color.borderStrong : Theme.color.border
                Behavior on color { ColorAnimation { duration: Theme.motion.fast } }
                Row {
                    anchors.centerIn: parent
                    spacing: Theme.space.xs
                    GlowDot {
                        anchors.verticalCenter: parent.verticalCenter
                        diameter: 7
                        color: root.state === "live_confirmed" ? Theme.color.text : Theme.color.textMuted
                        pulse: root.state === "live_confirmed"
                        visible: segLive.engaged
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        // Available → "LIVE API"; unavailable → "UNAVAIL · <reason_code>".
                        // The <reason_code> is server-supplied (verbatim), so it is a
                        // property reference here, never a client source literal (C4).
                        text: root.liveAvailable
                              ? I18n.t("真实AI（计费）", "LIVE AI (BILLED)")
                              : I18n.t("不可用 · ", "UNAVAILABLE · ") + root.liveReasonCode
                        color: segLive.engaged ? Theme.color.text : Theme.color.textMuted
                        font.family: Theme.font.family
                        font.pixelSize: Theme.size.micro
                        font.weight: Theme.weight.semibold
                        font.letterSpacing: 1
                    }
                }
                // First click (from fake, available) arms — never confirms.
                TapHandler {
                    enabled: root.liveAvailable
                    onTapped: if (root.state === "fake") root.state = "live_armed"
                }
                HoverHandler { enabled: root.liveAvailable; cursorShape: Qt.PointingHandCursor }
            }
        }

        // ---- Two-click arming confirm (only while armed/confirmed) ----
        Rectangle {
            id: armRow
            width: 218; height: 30
            visible: root.state === "live_armed" || root.state === "live_confirmed"
            readonly property bool confirmed: root.state === "live_confirmed"
            radius: Theme.radius.sm
            color: armRow.confirmed ? Theme.withAlpha(Theme.color.text, 0.12) : "transparent"
            border.width: 1
            border.color: armRow.confirmed ? Theme.color.borderStrong : Theme.color.border
            Text {
                anchors.centerIn: parent
                text: armRow.confirmed
                      ? I18n.t("真实AI已启用", "LIVE AI ENGAGED")
                      : I18n.t("确认使用真实AI（计费）", "CONFIRM LIVE AI (BILLED)")
                color: Theme.color.text
                font.family: Theme.font.family
                font.pixelSize: Theme.size.micro
                font.weight: Theme.weight.semibold
                font.letterSpacing: 1
            }
            // Second, deliberate click confirms billed live.
            TapHandler {
                enabled: root.liveAvailable && root.state === "live_armed"
                onTapped: root.state = "live_confirmed"
            }
            HoverHandler { enabled: root.state === "live_armed"; cursorShape: Qt.PointingHandCursor }
        }

        // ---- Unavailable context — the server message, verbatim ----
        // Gated on the MESSAGE (not the code): the reason code is already shown
        // inline on the LIVE segment ("UNAVAIL · <code>"), and the "unreachable"
        // posture has no server message — so this must NOT render an empty line
        // (which previously opened a blank gap that pushed the page down).
        Text {
            width: parent.width
            visible: !root.liveAvailable && root.liveReasonMessage.length > 0
            text: root.liveReasonMessage
            wrapMode: Text.WordWrap
            color: Theme.color.textMuted
            font.family: Theme.font.family
            font.pixelSize: Theme.size.micro
        }
    }
}

import QtQuick
import qt_observer
import "."

// P2-C-1 thin playback remote for the EventPresentationQueue. Play/Pause, speed
// (1x/2x/4x/Instant), skip-to-next-phase and skip-to-queue-end. NO scrub bar — the queue
// only ever consumes already-received events; live never fast-forwards the future.
// Reads queue state (playing/waiting/speed/instant), never raw runtime fields.
Row {
    id: root
    objectName: "playbackControls"

    property var queue: null
    spacing: Theme.space.sm

    AppButton {
        text: (root.queue && root.queue.playing) ? I18n.t("暂停", "Pause") : I18n.t("播放", "Play")
        variant: "secondary"
        onClicked: {
            if (!root.queue)
                return
            if (root.queue.playing)
                root.queue.pause()
            else
                root.queue.play()
        }
    }

    Row {
        spacing: 2
        Repeater {
            model: [ { label: "1x", v: 1 }, { label: "2x", v: 2 }, { label: "4x", v: 4 } ]
            delegate: AppButton {
                text: modelData.label
                variant: (root.queue && !root.queue.instant && root.queue.speed === modelData.v) ? "secondary" : "ghost"
                onClicked: if (root.queue) root.queue.setSpeed(modelData.v)
            }
        }
        AppButton {
            text: I18n.t("瞬时", "Instant")
            variant: (root.queue && root.queue.instant) ? "secondary" : "ghost"
            onClicked: if (root.queue) root.queue.setInstant()
        }
    }

    AppButton {
        text: I18n.t("下一阶段", "Next phase")
        variant: "ghost"
        onClicked: if (root.queue) root.queue.seekNextPhase()
    }
    AppButton {
        text: I18n.t("跳到最新", "Jump to latest")
        variant: "ghost"
        onClicked: if (root.queue) root.queue.seekQueueEnd()
    }

    Row {
        spacing: Theme.space.xs
        visible: root.queue && root.queue.waiting
        GlowDot {
            anchors.verticalCenter: parent.verticalCenter
            diameter: 7
            pulse: true
            color: Theme.color.info
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: I18n.t("AI 思考中…", "AI thinking…")
            color: Theme.color.textMuted
            font.family: Theme.font.mono
            font.pixelSize: Theme.size.micro
        }
    }
}

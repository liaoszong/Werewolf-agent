import QtQuick
import QtQuick.Controls
import qt_observer
import "."

// Per-seat editor for provider / model / strategy / prompt.  Driven entirely
// by the `schema` (server /api/profiles/schema) and `config` (effective seat
// config) passed in by MatchSetupView; holds no state of its own beyond the
// controls.  AppCard is a plain Rectangle (no `padding` property), so the
// content Column is inset with explicit margins.
AppCard {
    id: root
    objectName: "seatEditorPanel"

    // { player_id, role, team }
    property var seat: ({})
    // { provider, model, strategy, prompt }
    property var config: ({})
    // ObserverClient.profileSchema
    property var schema: ({})

    signal edited(string field, string value)

    // Suppress the emit that fires while the controls bind to initial values /
    // when `config` rebinds on seat switch.  MatchSetupView.applyEdit also
    // no-ops unchanged values, so a stale prompt can never reach the backend.
    property bool _ready: false
    Component.onCompleted: _ready = true

    readonly property var providerList: schema && schema.providers ? schema.providers : []
    readonly property var modelList: (schema && schema.models && config && config.provider
                                      && schema.models[config.provider]) ? schema.models[config.provider] : []
    readonly property var strategyList: schema && schema.strategies ? schema.strategies : []
    readonly property int promptMax: schema && schema.prompt_max_len ? schema.prompt_max_len : 8000

    Column {
        id: content
        x: Theme.space.lg
        y: Theme.space.lg
        width: parent.width - 2 * Theme.space.lg
        spacing: Theme.space.md

        SectionHeader {
            title: I18n.t("座位", "Seat") + " " + (root.seat.player_id || "")
            caption: (root.seat.role || "") + (root.seat.team ? " · " + root.seat.team : "")
        }

        // Provider
        Column {
            width: parent.width
            spacing: Theme.space.xs
            Text {
                text: I18n.t("供应方", "Provider")
                color: Theme.color.textSecondary
                font.family: Theme.font.family; font.pixelSize: Theme.size.caption
            }
            ComboBox {
                id: providerBox
                objectName: "seatEditorProvider"
                width: parent.width
                model: root.providerList
                currentIndex: Math.max(0, root.providerList.indexOf(root.config.provider))
                onActivated: root.edited("provider", root.providerList[currentIndex])
            }
        }

        // Model (dependent on provider)
        Column {
            width: parent.width
            spacing: Theme.space.xs
            Text {
                text: I18n.t("模型", "Model")
                color: Theme.color.textSecondary
                font.family: Theme.font.family; font.pixelSize: Theme.size.caption
            }
            ComboBox {
                id: modelBox
                objectName: "seatEditorModel"
                width: parent.width
                model: root.modelList
                currentIndex: Math.max(0, root.modelList.indexOf(root.config.model))
                onActivated: root.edited("model", root.modelList[currentIndex])
            }
        }

        // Strategy
        Column {
            width: parent.width
            spacing: Theme.space.xs
            Text {
                text: I18n.t("策略", "Strategy")
                color: Theme.color.textSecondary
                font.family: Theme.font.family; font.pixelSize: Theme.size.caption
            }
            ComboBox {
                id: strategyBox
                objectName: "seatEditorStrategy"
                width: parent.width
                model: root.strategyList
                currentIndex: Math.max(0, root.strategyList.indexOf(root.config.strategy))
                onActivated: root.edited("strategy", root.strategyList[currentIndex])
            }
        }

        // Prompt + length counter
        Column {
            width: parent.width
            spacing: Theme.space.xs
            Item {
                width: parent.width
                height: promptLabel.implicitHeight
                Text {
                    id: promptLabel
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: I18n.t("提示词", "Prompt")
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                }
                Text {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: promptArea.text.length + " / " + root.promptMax
                    color: promptArea.text.length > root.promptMax ? Theme.color.danger : Theme.color.textMuted
                    font.family: Theme.font.mono; font.pixelSize: Theme.size.micro
                }
            }
            ScrollView {
                width: parent.width
                height: 120
                TextArea {
                    id: promptArea
                    objectName: "seatEditorPrompt"
                    text: root.config.prompt || ""
                    wrapMode: TextArea.Wrap
                    color: Theme.color.text
                    background: Rectangle {
                        color: Theme.color.surfaceInset
                        border.width: 1; border.color: Theme.color.border
                        radius: Theme.radius.sm
                    }
                    // Real-time sync so every edit clears the stale verdict.
                    onTextChanged: if (root._ready) root.edited("prompt", text)
                }
            }
        }
    }
}

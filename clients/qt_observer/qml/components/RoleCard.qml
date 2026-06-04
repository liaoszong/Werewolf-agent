import QtQuick
import qt_observer

// Seat / role tile for the Werewolf Observer "Nightfall" board.
// Faction-aware accents respect the visibility boundary: an "unknown" role
// renders strictly as "Hidden" (initials become "?") — never guessed.
Item {
    id: root
    objectName: "roleCard"

    property string seatId: ""
    property string roleName: ""
    property string displayRole: ""
    property string displayTeam: ""
    property string visibilityLabel: ""
    property string aiLabel: ""
    property string statusText: ""
    property string accentText: ""
    property bool selected: false

    width: 140
    height: 160

    // Effective role: prefer the explicitly revealed displayRole, else fall back.
    readonly property string _role: root.displayRole !== "" ? root.displayRole : root.roleName
    readonly property bool _hidden: root._role === "unknown"
    readonly property bool _dead: root.statusText === "Dead"
    readonly property color _accent: Theme.roleAccent(root._role)

    // Localized role name; an "unknown" role always renders as the hidden label.
    function _roleLabel(r) {
        if (r === "unknown")
            return I18n.t("隐藏", "Hidden")
        switch (("" + r).toLowerCase()) {
        case "werewolf": return I18n.t("狼人", "Werewolf")
        case "seer": return I18n.t("预言家", "Seer")
        case "witch": return I18n.t("女巫", "Witch")
        case "villager": return I18n.t("村民", "Villager")
        default: return Theme.humanizeRole(r)
        }
    }

    opacity: root._dead ? 0.55 : 1.0
    Behavior on opacity { NumberAnimation { duration: Theme.motion.base } }

    // ---------------------------------------------------------------- Surface
    Rectangle {
        id: surface
        anchors.fill: parent
        radius: Theme.radius.lg
        color: Theme.color.surface
        border.width: root.selected ? 2 : 1
        border.color: root.selected ? Theme.color.primary : Theme.color.border

        Behavior on border.color { ColorAnimation { duration: Theme.motion.fast } }

        // Faint top hairline highlight for depth (matches AppCard).
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 1
            height: 1
            color: Theme.color.hairline
        }

        // Faction accent stripe (low-key, premium) — omitted for hidden roles to
        // respect the visibility boundary (a hidden card reveals no faction).
        Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 1
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: Theme.radius.lg
            anchors.bottomMargin: Theme.radius.lg
            width: 3
            radius: 1.5
            color: root._accent
            visible: !root._hidden
        }
    }

    // ---------------------------------------------------------------- Content
    Column {
        anchors.centerIn: parent
        width: parent.width - Theme.space.md * 2
        spacing: Theme.space.sm

        // Seat id — mono for a precise, technical feel.
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.seatId
            font.family: Theme.font.mono
            font.pixelSize: Theme.size.caption
            color: Theme.color.textMuted
            elide: Text.ElideRight
        }

        // Avatar — tinted disc ringed with the faction accent.
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 52
            height: 52
            radius: width / 2
            color: Theme.roleTint(root._role)
            border.width: 2
            border.color: root._accent

            Text {
                anchors.centerIn: parent
                text: root._hidden ? "?" : (I18n.lang === "zh" ? root._roleLabel(root._role).charAt(0) : root._role.substring(0, 2))
                font.family: Theme.font.family
                font.pixelSize: root._hidden ? 18 : (I18n.lang === "zh" ? 22 : 16)
                font.weight: Theme.weight.bold
                color: root._accent
            }
        }

        // Role name — "Hidden" when the role is not revealed.
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root._roleLabel(root._role)
            font.family: Theme.font.family
            font.pixelSize: Theme.size.small
            font.weight: Theme.weight.semibold
            color: root._accent
            elide: Text.ElideRight
        }

        // Team — dot + label, only when provided.
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.space.xs
            visible: root.displayTeam !== ""

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 7
                height: 7
                radius: width / 2
                color: Theme.teamAccent(root.displayTeam)
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.displayTeam
                font.family: Theme.font.family
                font.pixelSize: Theme.size.micro
                color: Theme.color.textSecondary
            }
        }

        // Visibility provenance (e.g. who can see this) — info accent.
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.visibilityLabel
            visible: text !== ""
            font.family: Theme.font.family
            font.pixelSize: Theme.size.micro
            color: Theme.color.info
            elide: Text.ElideRight
        }

        // AI / agent label.
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.aiLabel
            visible: text !== ""
            font.family: Theme.font.family
            font.pixelSize: Theme.size.micro
            color: Theme.color.textMuted
            elide: Text.ElideRight
        }

        // Life status — green alive, red dead, muted otherwise.
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.statusText === "Alive" ? I18n.t("存活", "Alive")
                 : (root.statusText === "Dead" ? I18n.t("出局", "Dead") : root.statusText)
            visible: text !== ""
            font.family: Theme.font.family
            font.pixelSize: Theme.size.micro
            font.weight: Theme.weight.medium
            color: root.statusText === "Alive" ? Theme.color.success
                 : (root.statusText === "Dead" ? Theme.color.danger : Theme.color.textMuted)
        }
    }
}

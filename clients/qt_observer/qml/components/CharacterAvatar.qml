import QtQuick
import qt_observer

// 单座动物头像:圆形肖像(Illustrations.avatar)+ 阵营色环 + 名牌 + 存活/发言/出局态。
// 纯表现,状态经属性。资产缺失 → 角色名首字 + 色环 fallback(永不白屏)。
Item {
    id: root
    objectName: "characterAvatar"

    property string roleKey: ""          // "" → fallback
    property string seatLabel: ""
    property string roleLabel: ""
    property color accent: Theme.warm.hairline
    property bool alive: true
    property bool speaking: false
    property real diameter: 84

    readonly property url _art: Illustrations.avatar(roleKey)
    readonly property bool _hasArt: String(_art) !== "" && portrait.status === Image.Ready

    implicitWidth: diameter
    implicitHeight: diameter + 22

    Rectangle {                          // 发言光晕(珊瑚)
        anchors.horizontalCenter: medallion.horizontalCenter
        anchors.verticalCenter: medallion.verticalCenter
        visible: root.speaking && root.alive
        width: root.diameter + 14; height: width; radius: width / 2
        color: "transparent"; border.width: 4
        border.color: Theme.withAlpha(Theme.warm.primary, 0.45)
    }

    Rectangle {                          // 圆形徽章
        id: medallion
        width: root.diameter; height: root.diameter; radius: width / 2
        anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter
        color: Theme.warm.surfaceCard
        border.width: root.speaking ? 4 : 3
        border.color: root.speaking ? Theme.warm.primary : root.accent
        clip: true
        opacity: root.alive ? 1.0 : 0.55

        Image {
            id: portrait
            anchors.fill: parent
            source: root._art
            fillMode: Image.PreserveAspectCrop
            verticalAlignment: Image.AlignTop
            asynchronous: true
            cache: true
            sourceSize.width: Math.max(1, Math.ceil(width * 2))
            sourceSize.height: Math.max(1, Math.ceil(height * 2))
            visible: root._hasArt
            // 出局去色需 MultiEffect(真机);offscreen 不渲染,截图按彩色判读 alive 态
        }
        Text {                           // fallback:角色名首字
            anchors.centerIn: parent
            visible: !root._hasArt
            text: (root.roleLabel || root.seatLabel || "?").substring(0, 1)
            color: Theme.warm.ink
            font.family: Theme.fontFamilies.serif
            font.contextFontMerging: true
            font.pixelSize: root.diameter * 0.42
            font.weight: Theme.weight.bold
        }
        Rectangle {                      // 出局斜杠
            visible: !root.alive
            anchors.centerIn: parent
            width: parent.width * 1.1; height: 3; radius: 1.5; rotation: -45
            color: Theme.warm.error; opacity: 0.85
        }
    }

    Rectangle {                          // 出局 / OUT 角标
        visible: !root.alive
        anchors.horizontalCenter: medallion.horizontalCenter
        anchors.verticalCenter: medallion.bottom
        width: outText.implicitWidth + Theme.space.sm; height: outText.implicitHeight + 3
        radius: Theme.radius.sm; color: Theme.withAlpha(Theme.warm.error, 0.92)
        Text {
            id: outText; anchors.centerIn: parent
            text: I18n.t("出局", "OUT")
            color: "#ffffff"
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro; font.weight: Theme.weight.bold
        }
    }

    Rectangle {                          // 名牌
        anchors.top: medallion.bottom
        anchors.topMargin: root.alive ? 4 : 13
        anchors.horizontalCenter: medallion.horizontalCenter
        width: plate.implicitWidth + Theme.space.sm; height: plate.implicitHeight + 2
        radius: Theme.radius.sm; color: Theme.withAlpha(Theme.warm.surfaceRaised, 0.82)
        Text {
            id: plate; anchors.centerIn: parent
            text: root.seatLabel + (root.roleLabel ? " · " + root.roleLabel : "")
            color: root.alive ? Theme.warm.ink : Theme.warm.muted
            font.family: Theme.fontFamilies.sans; font.contextFontMerging: true
            font.pixelSize: Theme.size.micro
        }
    }
}

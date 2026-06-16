pragma Singleton
import QtQuick

// Single-source registry of bundled illustration assets (game client redesign).
// Logical name -> resource URL, resolved relative to this module file so callers
// never hardcode qrc paths. A missing file surfaces as Image.Error at load time;
// every consumer MUST provide a no-asset fallback (see SceneBackground et al.).
QtObject {
    id: assets

    readonly property url homeSceneDay: Qt.resolvedUrl("../assets/illustrations/scene/home-day.png")
    readonly property url homeSceneNight: Qt.resolvedUrl("../assets/illustrations/scene/home-night.png")

    readonly property url tableDay: Qt.resolvedUrl("../assets/illustrations/scene/table-day.png")
    readonly property url tableNight: Qt.resolvedUrl("../assets/illustrations/scene/table-night.png")
    readonly property url setupRoom: Qt.resolvedUrl("../assets/illustrations/scene/setup-room.png")

    // Material-system texture: subtle paper-grain overlay (renders in screenshots,
    // unlike GPU shadow effects). The header-weave / night-vignette / warm-glow
    // overlays and the ornamental band/tray frames were all retired with the
    // full-bleed watercolor board — lighting is baked into the table art and the HUD
    // floats as parchment cards.
    readonly property url texParchment: Qt.resolvedUrl("../assets/textures/parchment.png")

    readonly property var _avatar: ({
        "werewolf": Qt.resolvedUrl("../assets/illustrations/avatars/werewolf.png"),
        "seer":     Qt.resolvedUrl("../assets/illustrations/avatars/seer.png"),
        "witch":    Qt.resolvedUrl("../assets/illustrations/avatars/witch.png"),
        "villager": Qt.resolvedUrl("../assets/illustrations/avatars/villager.png"),
        "guard":    Qt.resolvedUrl("../assets/illustrations/avatars/guard.png"),
        "hunter":   Qt.resolvedUrl("../assets/illustrations/avatars/hunter.png")
    })

    readonly property var _tarot: ({
        "werewolf": Qt.resolvedUrl("../assets/illustrations/tarot/werewolf.png"),
        "seer":     Qt.resolvedUrl("../assets/illustrations/tarot/seer.png"),
        "witch":    Qt.resolvedUrl("../assets/illustrations/tarot/witch.png"),
        "villager": Qt.resolvedUrl("../assets/illustrations/tarot/villager.png"),
        "guard":    Qt.resolvedUrl("../assets/illustrations/tarot/guard.png"),
        "hunter":   Qt.resolvedUrl("../assets/illustrations/tarot/hunter.png")
    })

    // Returns "" for an unknown role so the caller renders its fallback.
    function tarot(roleKey) {
        var k = ("" + roleKey).toLowerCase();
        return _tarot[k] !== undefined ? _tarot[k] : "";
    }

    function homeScene(phaseName) {
        return ("" + phaseName).toLowerCase() === "night" ? homeSceneNight : homeSceneDay;
    }

    function table(phaseName) {
        return ("" + phaseName).toLowerCase() === "night" ? tableNight : tableDay;
    }

    // Returns "" for an unknown role so the caller renders its fallback.
    function avatar(roleKey) {
        var k = ("" + roleKey).toLowerCase();
        return _avatar[k] !== undefined ? _avatar[k] : "";
    }
}

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

    // Material-system textures (subtle overlays; render in screenshots, unlike GPU
    // shadow effects). parchment = paper grain; headerWeave = cloth grain.
    // (Night vignette / warm-glow overlays and the ornamental band/tray frames were
    // retired with the full-bleed watercolor board — lighting is now baked into the
    // table art and the HUD floats as parchment cards, no header/tray plaques.)
    readonly property url texParchment: Qt.resolvedUrl("../assets/textures/parchment.png")
    readonly property url texHeaderWeave: Qt.resolvedUrl("../assets/textures/header-weave.png")

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

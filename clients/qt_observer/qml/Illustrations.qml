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
}

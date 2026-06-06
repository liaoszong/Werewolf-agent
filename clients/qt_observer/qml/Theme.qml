pragma Singleton
import QtQuick

// Werewolf Observer — "Nightfall" design tokens.
// Single source of truth for color, spacing, radius, typography and motion.
// Access from any QML file in the module via:  import qt_observer  ->  Theme.color.bg
QtObject {
    id: theme

    // ---------------------------------------------------------------- Color
    readonly property QtObject color: QtObject {
        // Backgrounds — matte charcoal / zinc, neutral (no blue or purple cast)
        readonly property color bgBase: "#09090B"   // zinc-950
        readonly property color bg: "#18181B"        // zinc-900 (app background)
        readonly property color bgRaised: "#1C1C1F"

        // Surfaces (cards / panels) — quietly raised on the charcoal base
        readonly property color surface: "#27272A"   // zinc-800
        readonly property color surfaceAlt: "#323238" // hover / raised
        readonly property color surfaceInset: "#161618" // wells / list backgrounds

        // Borders / dividers — crisp 1px "hard-cut" lines (no glow, no shadow)
        readonly property color border: "#3F3F46"     // zinc-700
        readonly property color borderStrong: "#52525B" // zinc-600
        readonly property color hairline: Qt.rgba(1, 1, 1, 0.04)

        // Text — brightened slate ramp for legibility on the near-black stage.
        // Each tier stays >= 4.5:1 against the charcoal surfaces; the faintest tier
        // (textMuted) is deliberately lifted off "死黑" so it survives cheap panels.
        readonly property color text: "#F8FAFC"          // slate-50  (primary content)
        readonly property color textSecondary: "#CBD5E1" // slate-300 (names, labels)
        readonly property color textMuted: "#94A3B8"     // slate-400 (timestamps, tags)
        readonly property color textDisabled: "#64748B"  // slate-500 (floor — disabled only)

        // Brand / primary action — moonlight silver (light surface, dark label)
        readonly property color primary: "#FFFFFF"
        readonly property color primaryHover: "#E4E4E7"  // dims slightly on hover
        readonly property color primaryPressed: "#D4D4D8"
        readonly property color primaryText: "#18181B"   // dark text ON the light button

        // Factions / roles — shown as low-opacity tints + accents, never solid fills
        readonly property color werewolf: "#EF4444" // blood red
        readonly property color seer: "#FBBF24"     // prophetic gold
        readonly property color witch: "#A855F7"    // arcane violet
        readonly property color villager: "#60A5FA" // calm blue
        readonly property color unknown: "#71717A"  // hidden / zinc

        // Teams
        readonly property color teamWolf: "#EF4444"
        readonly property color teamGood: "#60A5FA"

        // Status / semantic (functional accents only)
        readonly property color success: "#34D399"
        readonly property color danger: "#EF4444"
        readonly property color warning: "#F59E0B"
        readonly property color info: "#A1A1AA"   // chrome accents stay neutral / monochrome
        readonly property color completed: "#60A5FA"
        readonly property color running: "#34D399"
    }

    // -------------------------------------------------------------- Spacing
    // 8px rhythm (4px for fine adjustments)
    readonly property QtObject space: QtObject {
        readonly property int xs: 4
        readonly property int sm: 8
        readonly property int md: 12
        readonly property int lg: 16
        readonly property int xl: 20
        readonly property int xxl: 24
        readonly property int xxxl: 32
        readonly property int huge: 48
    }

    // --------------------------------------------------------------- Radius
    readonly property QtObject radius: QtObject {
        readonly property int sm: 6
        readonly property int md: 8
        readonly property int lg: 12
        readonly property int xl: 16
        readonly property int pill: 999
    }

    // ----------------------------------------------------------- Typography
    readonly property QtObject font: QtObject {
        readonly property string family: "Segoe UI"
        readonly property string display: "Segoe UI"
        readonly property string mono: "Consolas"
    }
    readonly property QtObject size: QtObject {
        readonly property int display: 34
        readonly property int h1: 24
        readonly property int h2: 17
        readonly property int body: 14
        readonly property int small: 13
        readonly property int caption: 12
        readonly property int micro: 11
    }
    readonly property QtObject weight: QtObject {
        readonly property int regular: Font.Normal
        readonly property int medium: Font.Medium
        readonly property int semibold: Font.DemiBold
        readonly property int bold: Font.Bold
    }

    // ----------------------------------------------------------------- Motion
    readonly property QtObject motion: QtObject {
        readonly property int fast: 120
        readonly property int base: 180
        readonly property int slow: 260
    }

    // ----------------------------------------------------------------- Layout
    // A single app-wide gutter keeps every page (and the top bar) on one grid.
    readonly property QtObject layout: QtObject {
        readonly property int pageMargin: 40
        readonly property int contentMax: 1040
        readonly property int actionBarHeight: 72
    }

    // ---------------------------------------------------------------- Helpers
    function roleKey(role) {
        if (role === undefined || role === null)
            return "unknown";
        return ("" + role).toLowerCase();
    }

    function roleAccent(role) {
        switch (roleKey(role)) {
        case "werewolf":
        case "wolf":
            return theme.color.werewolf;
        case "seer":
            return theme.color.seer;
        case "witch":
            return theme.color.witch;
        case "villager":
            return theme.color.villager;
        default:
            return theme.color.unknown;
        }
    }

    function roleTint(role) {
        var c = roleAccent(role);
        return Qt.rgba(c.r, c.g, c.b, 0.10);
    }

    function roleBorder(role) {
        var c = roleAccent(role);
        return Qt.rgba(c.r, c.g, c.b, 0.30);
    }

    function teamAccent(team) {
        var t = (team === undefined || team === null) ? "" : ("" + team).toLowerCase();
        if (t.indexOf("wolf") >= 0)
            return theme.color.teamWolf;
        if (t === "" || t === "unknown")
            return theme.color.unknown;
        return theme.color.teamGood;
    }

    function statusColor(status) {
        switch (("" + status).toLowerCase()) {
        case "running":
            return theme.color.running;
        case "completed":
            return theme.color.completed;
        case "failed":
            return theme.color.danger;
        case "queued":
            return theme.color.warning;
        case "connected":
            return theme.color.success;
        case "disconnected":
            return theme.color.danger;
        default:
            return theme.color.unknown;
        }
    }

    function statusTint(status) {
        var c = statusColor(status);
        return Qt.rgba(c.r, c.g, c.b, 0.16);
    }

    function withAlpha(c, a) {
        return Qt.rgba(c.r, c.g, c.b, a);
    }

    // "default_6p_fake" -> "6-Player Match · Test Template"
    function humanizeTemplate(t) {
        var s = "" + t;
        if (s === "default_6p_fake")
            return "6-Player Match · Test Template";
        return s.replace(/_/g, " ").replace(/\b\w/g, function (m) {
            return m.toUpperCase();
        });
    }

    // Role display respecting the visibility boundary ("unknown" -> "Hidden")
    function humanizeRole(role) {
        var k = roleKey(role);
        if (k === "unknown" || k === "")
            return "Hidden";
        var s = "" + role;
        return s.charAt(0).toUpperCase() + s.slice(1);
    }
}

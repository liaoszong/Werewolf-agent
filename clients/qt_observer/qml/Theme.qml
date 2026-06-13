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

    // -------------------------------------------- Settlement "明室" (P2-D)
    // A warm-beige LIGHT canvas for the deep battle report. The theater stays dark;
    // the one-shot morph crosses from the dark stage INTO this light workbench —
    // the psychological shift from 局中人 (tense, dark) to 复盘者 (calm, bright).
    // Coral is the single accent; rainbow faction colors are dropped here. High
    // density via hairline dividers + soft shadow instead of heavy borders.
    readonly property QtObject report: QtObject {
        readonly property color canvas: "#F5F0E6"   // warm beige page
        readonly property color card: "#FFFFFF"      // card surface
        readonly property color cardAlt: "#FBF7F0"   // subtle alt / inset / dead seat
        readonly property color border: Qt.rgba(0, 0, 0, 0.10)        // hairline divider
        readonly property color borderStrong: Qt.rgba(0, 0, 0, 0.16)
        readonly property color text: "#2A2622"       // warm near-black (primary)
        readonly property color textSecondary: "#5C554C"
        readonly property color textMuted: "#8A8175"
        readonly property color accent: "#E8624A"     // coral — bars, active fill, emphasis
        readonly property color accentGlow: "#FF7A5C" // brighter coral for the breathing glow
        readonly property color shadow: Qt.rgba(0, 0, 0, 0.12)
        // Light-canvas faction tints (deeper than the dark-stage reds/blues so the
        // winner headline keeps its meaning while staying legible on beige).
        readonly property color winVillager: "#2563EB"
        readonly property color winWerewolf: "#DC2626"
    }

    // ---------------------------------------------- Warm "Claude" palette (game client)
    // ADDITIVE — the dark tokens above keep their values so un-migrated pages do
    // not regress. Warm-surfaced pages (Home first) read from `warm` / `phase`.
    readonly property QtObject warm: QtObject {
        readonly property color canvas: "#faf9f5"
        readonly property color surfaceSoft: "#f5f0e8"
        readonly property color surfaceCard: "#efe9de"
        readonly property color surfaceCreamStrong: "#e8e0d2"
        readonly property color surfaceRaised: "#fffefb"
        readonly property color surfaceDark: "#181715"
        readonly property color surfaceDarkElevated: "#252320"
        readonly property color hairline: "#e6dfd8"
        readonly property color hairlineSoft: "#ebe6df"
        readonly property color ink: "#141413"
        readonly property color body: "#3d3d3a"
        readonly property color bodyStrong: "#252523"
        readonly property color muted: "#6c6a64"
        readonly property color mutedSoft: "#8e8b82"
        readonly property color primary: "#cc785c"
        readonly property color primaryActive: "#a9583e"
        readonly property color primaryDisabled: "#e6dfd8"
        // NOTE: token names must NOT start with "on"+Capital — QML parses those as
        // signal handlers (onPrimary -> "onPrimary" handler). Use textOn* instead.
        readonly property color textOnPrimary: "#ffffff"
        readonly property color textOnDark: "#faf9f5"
        readonly property color textOnDarkSoft: "#a09d96"
        readonly property color accentAmber: "#e8a55a"
        readonly property color accentTeal: "#5db8a6"
        readonly property color success: "#5db872"
        readonly property color warning: "#d4a017"
        readonly property color error: "#c64545"
    }

    // Day / night phase surfaces (extracted from the home-scene illustrations).
    readonly property QtObject phase: QtObject {
        readonly property QtObject day: QtObject {
            readonly property color bg: "#f3e8d2"
            readonly property color ambient: "#e8c078"
            readonly property color sky: "#afc9e0"
        }
        readonly property QtObject night: QtObject {
            readonly property color bg: "#2a3a55"
            readonly property color sky: "#20304f"
            readonly property color glow: "#e8a85a"
        }
    }

    // System-stack-first font families (NO bundled fonts in Phase 1; see spec §3.4).
    // Single string per role; warm Text uses font.family + font.contextFontMerging
    // = true so a missing CJK glyph in (e.g.) "Inter" is merged from the system CJK
    // font at render time. No multi-family arrays, no unverified font features, no subsetting.
    readonly property QtObject fontFamilies: QtObject {
        readonly property string serif: "Source Han Serif SC"
        readonly property string sans:  "Inter"
        readonly property string mono:  "JetBrains Mono"
    }

    // Larger warm type scale (additive; existing `size` untouched).
    readonly property QtObject warmSize: QtObject {
        readonly property int displayXl: 48
        readonly property int displayLg: 36
        readonly property int displayMd: 28
        readonly property int titleLg: 22
        readonly property int titleMd: 18
        readonly property int bodyLg: 16
    }

    // Restrained damped motion for warm UI (Phase 1). Components reference these
    // instead of literal durations/easing so the feel stays consistent.
    //   color/hover -> Easing.OutCubic ; press/scale -> Easing.OutQuad
    readonly property QtObject anim: QtObject {
        readonly property int color: 140        // hover / colour cross-fade (120–160)
        readonly property int press: 100        // press / scale (80–120)
        readonly property real pressScale: 0.98
    }

    // Soft warm elevation (consumed by AppCard onLight via QtQuick.Effects MultiEffect).
    readonly property QtObject elevation: QtObject {
        readonly property color shadowColor: Qt.rgba(50 / 255, 38 / 255, 24 / 255, 0.18)
        readonly property real blur: 0.9
        readonly property real verticalOffset: 10
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

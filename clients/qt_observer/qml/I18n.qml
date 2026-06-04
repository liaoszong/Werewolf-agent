pragma Singleton
import QtQuick

// Lightweight runtime i18n for the Werewolf Observer.
// Default language is Chinese; the top-bar toggle flips `lang` to English.
//
// Usage (from any file in the module):  import qt_observer
//     text: I18n.t("中文", "English")
//
// Because t() reads `lang`, every `text: I18n.t(...)` binding re-evaluates
// live when the language is switched — no reload required.
QtObject {
    id: i18n

    // "zh" | "en"
    property string lang: "zh"

    function t(zh, en) {
        return lang === "zh" ? zh : en
    }
}

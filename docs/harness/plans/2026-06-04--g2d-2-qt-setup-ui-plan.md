# G2d-2 Qt Profile Setup UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Qt cockpit's `MatchSetupView` into a profile-driven setup editor that loads an existing server-side profile, edits per-seat provider/model/strategy/prompt in a master-detail layout, validates server-side, and launches a fake run — advancing to Preflight only after `POST /api/runs` returns `202`.

**Architecture:** One read-only backend endpoint (`GET /api/profiles/schema`) feeds the dropdown allowlists; `ObserverApiClient` gains profile fetch/validate/launch methods (latest-wins guards, 202-gated launch); a new `SeatEditorPanel.qml` holds the per-seat editor; `MatchSetupView.qml` becomes master-detail. The contract test is the test-first gate; Qt build + visual `grabToImage` verify the UI.

**Tech Stack:** Python stdlib (extends G2d-1 `profile_config`/observer server), Qt 6.10 Quick/Quick Controls, C++17, QML, CMake. No new third-party deps, no live providers, no local file I/O in the client.

**Spec:** `docs/superpowers/specs/2026-06-04-g2d-2-qt-setup-ui-design.md` (approved, tweaks merged).

---

## Context Basis (verified)

- `clients/qt_observer/src/ObserverApiClient.cpp`: `get(path)` (:68), `post(path, body)` (:75), `startDefaultMatch()` (:135) — finished-lambda pattern: check `reply->error()`, parse `QJsonDocument`, set state, emit. `refreshProjection()` (:347) uses a `quint64 m_projectionRequestSerial` latest-wins guard.
- `clients/qt_observer/CMakeLists.txt:34` `QML_FILES` list (ends with `qml/components/EmptyState.qml`).
- `clients/qt_observer/qml/AppShell.qml`: `navigateHome()` (:174), `navigatePreflight()` (:184). Views reach them via `root.StackView.view.parent.navigateX()`.
- `tests/test_qt_observer_static_contract.py`: required-files list (:32), required-objectNames map (:47, MatchSetupView → `matchSetupView`,`setupRoleCards`,`setupContinueButton`), forbidden-pattern scan (`events.jsonl`,`snapshots/`,`QFile`,`QDir`,`file://`) (:255), `test_setup_contains_default_six_player_roles` (:101), `QtObserverReadmeTests` asserting `clients/qt_observer/README.md` has `"no full prompt/profile editor"` (:264).
- G2d-1 `profile_config.py` constants: `ALLOWED_PROVIDERS`, `ALLOWED_MODELS`, `ALLOWED_STRATEGIES`, `ALLOWED_ROLES`, `ROLE_TEAMS`, `DEFAULT_6P_SEAT_ROLES`, `DEFAULT_SEAT_IDS`, `PROMPT_MAX_LEN`.

**Build/verify (Qt toolchain on F:):**
```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer   # exit 0 = QML valid
ctest --test-dir .tmp/qt-observer-build
```

---

## Allowlist

```text
src/werewolf_eval/profile_config.py
src/werewolf_eval/observer_server.py
src/werewolf_eval/observer_protocol.py
clients/qt_observer/src/ObserverApiClient.h
clients/qt_observer/src/ObserverApiClient.cpp
clients/qt_observer/qml/components/SeatEditorPanel.qml
clients/qt_observer/qml/MatchSetupView.qml
clients/qt_observer/CMakeLists.txt
clients/qt_observer/README.md
tests/test_profile_config.py
tests/test_observer_protocol.py
tests/test_observer_server.py
tests/test_qt_observer_static_contract.py
docs/superpowers/specs/2026-06-04-g2d-2-qt-setup-ui-design.md
docs/harness/plans/2026-06-04--g2d-2-qt-setup-ui-plan.md
.logs/review/latest/review-packet.md
.oh-my-harness/tree.md
```

## Forbidden Scope

No game engine / fake runtime / scoring / provider changes; no route-product docs (`README.md` root, `ROADMAP.md`, `TASKS.md`, `PRODUCT_ONE_PAGER.md`); no new server **write** endpoint (only the read-only `/api/profiles/schema`); no client local file I/O (`QFile`/`QDir`/`file://`); no live providers/secrets; no new third-party deps; no Web/Electron.

---

## Task 1: Backend read-only profile schema

**Files:** `src/werewolf_eval/profile_config.py`, `src/werewolf_eval/observer_server.py`, `tests/test_profile_config.py`, `tests/test_observer_server.py`

- [ ] **Step 1: Write the failing schema test**

Append to `tests/test_profile_config.py` (add `build_profile_schema` to the import block):

```python
class ProfileSchemaTests(unittest.TestCase):
    def test_schema_shape(self):
        s = build_profile_schema()
        self.assertEqual(s["schema_version"], PROFILE_SCHEMA_VERSION)
        self.assertEqual(set(s["providers"]), {"fake_deterministic", "deepseek"})
        self.assertEqual(s["models"]["deepseek"], ["deepseek-chat", "deepseek-reasoner"])
        self.assertEqual(s["models"]["fake_deterministic"], ["none"])
        self.assertIn("default", s["strategies"])
        self.assertEqual(s["seat_roles"]["p1"], "werewolf")
        self.assertEqual(s["seat_roles"]["p3"], "seer")
        self.assertEqual(s["seat_ids"], ["p1", "p2", "p3", "p4", "p5", "p6"])
        self.assertEqual(s["prompt_max_len"], 8000)
        self.assertNotIn("templates", s)
        # sorted + leak-free
        self.assertEqual(s["providers"], sorted(s["providers"]))
        blob = json.dumps(s)
        self.assertNotIn(":\\", blob)
```

- [ ] **Step 2: Run → fail**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_profile_config -v
```
Expected: ImportError for `build_profile_schema`.

- [ ] **Step 3: Implement `build_profile_schema`**

Append to `src/werewolf_eval/profile_config.py`:

```python
def build_profile_schema() -> dict:
    """Return read-only UI metadata (dropdown options + seat layout) derived
    from the validation constants.  No profile-name list (that comes from
    GET /api/profiles), no secrets, no paths."""
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "providers": sorted(ALLOWED_PROVIDERS),
        "models": {p: sorted(ALLOWED_MODELS[p]) for p in sorted(ALLOWED_MODELS)},
        "strategies": sorted(ALLOWED_STRATEGIES),
        "roles": sorted(ALLOWED_ROLES),
        "role_teams": dict(ROLE_TEAMS),
        "seat_roles": dict(DEFAULT_6P_SEAT_ROLES),
        "seat_ids": list(DEFAULT_SEAT_IDS),
        "prompt_max_len": PROMPT_MAX_LEN,
    }
```

- [ ] **Step 4: Run → pass**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_profile_config -v
```
Expected: `OK`.

- [ ] **Step 5: Add the `GET /api/profiles/schema` endpoint**

In `src/werewolf_eval/observer_server.py`, import `build_profile_schema` (add to the existing `from werewolf_eval.profile_config import (...)` block). In `do_GET`, add **before** the `if segments == ["api", "profiles"]:` block:

```python
                if segments == ["api", "profiles", "schema"]:
                    self._send_json(200, build_profile_schema())
                    return
```

> Order matters: the 2-segment `["api","profiles"]` and 3-segment `["api","profiles",name]` checks must not shadow `["api","profiles","schema"]`. Placing this 3-segment exact match first is safe; the `{name}` branch (`len==3 and segments[:2]==["api","profiles"]`) would otherwise treat `schema` as a profile name. Guard the name branch with `and segments[2] != "schema"`.

Update the name branch:
```python
                if len(segments) == 3 and segments[:2] == ["api", "profiles"] and segments[2] != "schema":
```

- [ ] **Step 6: Add a server test (env-documented)**

Append to `tests/test_observer_server.py` `ObserverServerProfileTests`:

```python
    def test_schema_endpoint(self) -> None:
        s = _request_json(self._base_url, "/api/profiles/schema")
        self.assertEqual(s["seat_roles"]["p1"], "werewolf")
        self.assertIn("deepseek", s["providers"])
        self.assertNotIn("templates", s)
```

- [ ] **Step 7: Run focused tests + commit**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_profile_config tests.test_observer_protocol -v
```
Expected: `OK` (server test env-blocked like the others — document if run). Commit:
```powershell
git add src/werewolf_eval/profile_config.py src/werewolf_eval/observer_server.py tests/test_profile_config.py tests/test_observer_server.py
git commit -m "feat(g2d-2): add read-only GET /api/profiles/schema"
```

---

## Task 2: ObserverApiClient profile methods

**Files:** `clients/qt_observer/src/ObserverApiClient.h`, `clients/qt_observer/src/ObserverApiClient.cpp`, `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Extend the static contract test (test-first)**

In `tests/test_qt_observer_static_contract.py`, add to the client-contract class (the one reading `ObserverApiClient.h/.cpp` — mirror the existing G2c projection assertions):

```python
class QtObserverProfileClientTests(unittest.TestCase):
    def test_client_exposes_profile_properties(self) -> None:
        h = (QT / "src/ObserverApiClient.h").read_text(encoding="utf-8")
        for prop in ["profileItems", "profileSchema", "loadedProfile", "profileValidation"]:
            self.assertIn(prop, h)
        for inv in ["refreshProfiles", "refreshProfileSchema", "fetchProfile",
                    "validateProfile", "launchFromProfile"]:
            self.assertIn(inv, h)
        for sig in ["launchSucceeded", "launchFailed"]:
            self.assertIn(sig, h)

    def test_client_launch_is_202_gated(self) -> None:
        cpp = (QT / "src/ObserverApiClient.cpp").read_text(encoding="utf-8")
        self.assertIn("/api/profiles/schema", cpp)
        self.assertIn("/api/profiles/validate", cpp)
        self.assertIn("launchSucceeded", cpp)
        self.assertIn("202", cpp)  # launch advances only on 202
```

Run → fail:
```powershell
python -m unittest tests.test_qt_observer_static_contract -v
```

- [ ] **Step 2: Add declarations to `ObserverApiClient.h`**

After the G2c projection `Q_PROPERTY` lines (before `public:`), add:
```cpp
    // G2d-2 profile setup properties
    Q_PROPERTY(QVariantList profileItems READ profileItems NOTIFY profileItemsChanged)
    Q_PROPERTY(QVariantMap profileSchema READ profileSchema NOTIFY profileSchemaChanged)
    Q_PROPERTY(QVariantMap loadedProfile READ loadedProfile NOTIFY loadedProfileChanged)
    Q_PROPERTY(QVariantMap profileValidation READ profileValidation NOTIFY profileValidationChanged)
```
In the accessors section:
```cpp
    QVariantList profileItems() const;
    QVariantMap profileSchema() const;
    QVariantMap loadedProfile() const;
    QVariantMap profileValidation() const;
```
In `public slots:`:
```cpp
    Q_INVOKABLE void refreshProfiles();
    Q_INVOKABLE void refreshProfileSchema();
    Q_INVOKABLE void fetchProfile(const QString &name);
    Q_INVOKABLE void validateProfile(const QVariantMap &profile);
    Q_INVOKABLE void launchFromProfile(const QVariantMap &profile);
```
In `signals:`:
```cpp
    void profileItemsChanged();
    void profileSchemaChanged();
    void loadedProfileChanged();
    void profileValidationChanged();
    void launchSucceeded();
    void launchFailed();
```
In the private members:
```cpp
    QVariantList m_profileItems;
    QVariantMap m_profileSchema;
    QVariantMap m_loadedProfile;
    QVariantMap m_profileValidation;
    quint64 m_profileRequestSerial = 0;
```
Add `#include <QJsonArray>` if not present (it is used by existing code).

- [ ] **Step 3: Implement in `ObserverApiClient.cpp`**

Add accessors (near the other accessors) and methods (near `refreshProjection`):

```cpp
QVariantList ObserverApiClient::profileItems() const { return m_profileItems; }
QVariantMap ObserverApiClient::profileSchema() const { return m_profileSchema; }
QVariantMap ObserverApiClient::loadedProfile() const { return m_loadedProfile; }
QVariantMap ObserverApiClient::profileValidation() const { return m_profileValidation; }

void ObserverApiClient::refreshProfiles()
{
    QNetworkReply *reply = get(QStringLiteral("/api/profiles"));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) { setError(reply->errorString()); return; }
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) { setError(QStringLiteral("Invalid profiles response")); return; }
        QVariantList items;
        for (const QJsonValue &v : doc.object().value(QStringLiteral("profiles")).toArray())
            items.append(v.toObject().toVariantMap());
        m_profileItems = items;
        emit profileItemsChanged();
    });
}

void ObserverApiClient::refreshProfileSchema()
{
    QNetworkReply *reply = get(QStringLiteral("/api/profiles/schema"));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) { setError(reply->errorString()); return; }
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) { setError(QStringLiteral("Invalid schema response")); return; }
        m_profileSchema = doc.object().toVariantMap();
        emit profileSchemaChanged();
    });
}

void ObserverApiClient::fetchProfile(const QString &name)
{
    const quint64 serial = ++m_profileRequestSerial;
    QNetworkReply *reply = get(QStringLiteral("/api/profiles/") + name);
    connect(reply, &QNetworkReply::finished, this, [this, reply, serial]() {
        reply->deleteLater();
        if (serial != m_profileRequestSerial) return;  // latest-wins
        if (reply->error() != QNetworkReply::NoError) { setError(reply->errorString()); return; }
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) { setError(QStringLiteral("Invalid profile response")); return; }
        m_loadedProfile = doc.object().toVariantMap();
        emit loadedProfileChanged();
    });
}

void ObserverApiClient::validateProfile(const QVariantMap &profile)
{
    QJsonObject body = QJsonObject::fromVariantMap(profile);
    QNetworkReply *reply = post(QStringLiteral("/api/profiles/validate"),
                                QJsonDocument(body).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) { setError(QStringLiteral("Invalid validate response")); return; }
        m_profileValidation = doc.object().toVariantMap();
        emit profileValidationChanged();
    });
}

void ObserverApiClient::launchFromProfile(const QVariantMap &profile)
{
    QJsonObject body;
    body[QStringLiteral("profile")] = QJsonObject::fromVariantMap(profile);
    QNetworkReply *reply = post(QStringLiteral("/api/runs"),
                                QJsonDocument(body).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        const int httpStatus =
            reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        const QJsonObject obj = doc.isObject() ? doc.object() : QJsonObject();
        const QString runId = obj.value(QStringLiteral("run_id")).toString();
        // Advance ONLY on 202 with a run_id; never optimistically.
        if (httpStatus != 202 || runId.isEmpty()) {
            const QString msg = obj.value(QStringLiteral("message")).toString();
            setError(msg.isEmpty() ? QStringLiteral("Launch failed (%1)").arg(httpStatus) : msg);
            emit launchFailed();
            return;
        }
        m_currentRunId = runId;
        m_currentStatus = obj.value(QStringLiteral("status")).toString();
        emit currentRunChanged();
        emit currentStatusChanged();
        refreshAuditLinks();
        emit launchSucceeded();
    });
}
```

Add `#include <QJsonObject>`/`<QJsonArray>`/`<QJsonDocument>` if not already included (existing methods use them).

- [ ] **Step 4: Build + contract test + commit**

```powershell
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
python -m unittest tests.test_qt_observer_static_contract -v
```
Expected: build exit 0; contract tests `OK`. Commit:
```powershell
git add clients/qt_observer/src/ObserverApiClient.h clients/qt_observer/src/ObserverApiClient.cpp tests/test_qt_observer_static_contract.py
git commit -m "feat(g2d-2): add profile fetch/validate/launch to ObserverApiClient"
```

---

## Task 3: SeatEditorPanel.qml component

**Files:** `clients/qt_observer/qml/components/SeatEditorPanel.qml` (new), `clients/qt_observer/CMakeLists.txt`, `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Register + contract test (test-first)**

In `CMakeLists.txt` `QML_FILES`, after `qml/components/EmptyState.qml`, add `qml/components/SeatEditorPanel.qml`.

In `tests/test_qt_observer_static_contract.py`, add `"qml/components/SeatEditorPanel.qml"` to the required-files list (:32) and an objectNames entry:
```python
    "qml/components/SeatEditorPanel.qml": [
        "seatEditorPanel", "seatEditorProvider", "seatEditorModel",
        "seatEditorStrategy", "seatEditorPrompt",
    ],
```
Run → fail (file missing).

- [ ] **Step 2: Create `SeatEditorPanel.qml`**

```qml
import QtQuick
import QtQuick.Controls
import qt_observer
import "."

AppCard {
    id: root
    objectName: "seatEditorPanel"

    // { player_id, role, team }
    property var seat: ({})
    // { provider, model, strategy, prompt }
    property var config: ({})
    // ObserverClient.profileSchema
    property var schema: ({})

    signal edited(string field, var value)

    readonly property var providerList: schema && schema.providers ? schema.providers : []
    readonly property var modelList: (schema && schema.models && config && config.provider
                                      && schema.models[config.provider]) ? schema.models[config.provider] : []
    readonly property var strategyList: schema && schema.strategies ? schema.strategies : []
    readonly property int promptMax: schema && schema.prompt_max_len ? schema.prompt_max_len : 8000

    padding: Theme.space.lg

    Column {
        width: parent.width
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
            Row {
                width: parent.width
                Text {
                    text: I18n.t("提示词", "Prompt")
                    color: Theme.color.textSecondary
                    font.family: Theme.font.family; font.pixelSize: Theme.size.caption
                }
                Item { width: parent.width - 2 * implicitWidth; height: 1 }
                Text {
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
                    onEditingFinished: root.edited("prompt", text)
                }
            }
        }
    }
}
```

> Uses `AppCard` as the root (a registered component); `import "."` resolves sibling components. Quick Controls `ComboBox`/`TextArea` are available (Quick Controls is already a dependency).

- [ ] **Step 3: Build + contract test + commit**

```powershell
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
python -m unittest tests.test_qt_observer_static_contract -v
```
Expected: build exit 0; contract `OK`. Commit:
```powershell
git add clients/qt_observer/qml/components/SeatEditorPanel.qml clients/qt_observer/CMakeLists.txt tests/test_qt_observer_static_contract.py
git commit -m "feat(g2d-2): add SeatEditorPanel.qml (per-seat provider/model/strategy/prompt)"
```

---

## Task 4: MatchSetupView master-detail rewrite

**Files:** `clients/qt_observer/qml/MatchSetupView.qml`, `clients/qt_observer/README.md`, `tests/test_qt_observer_static_contract.py`

- [ ] **Step 1: Update the contract assertions (test-first)**

In `tests/test_qt_observer_static_contract.py`:
- Replace `test_setup_contains_default_six_player_roles` body with profile-driven checks:
```python
    def test_setup_is_profile_driven(self) -> None:
        content = (QT / "qml/MatchSetupView.qml").read_text(encoding="utf-8")
        for token in ["ObserverClient.profileItems", "ObserverClient.loadedProfile",
                      "launchFromProfile", "validateProfile", "profileSchema"]:
            self.assertIn(token, content)
        # options must come from the schema, not a hardcoded provider list
        self.assertNotIn('"deepseek-chat"', content)
        # launch is 202-gated via launchSucceeded, not optimistic navigation
        self.assertIn("launchSucceeded", content)
```
- Add `setupProfilePicker`, `setupValidateButton` to MatchSetupView's required objectNames (keep `matchSetupView`, `setupRoleCards`, `setupContinueButton`).
- In `QtObserverReadmeTests.test_readme_documents_mvp_status_and_non_goals`, replace `self.assertIn("no full prompt/profile editor", content)` with `self.assertIn("profile setup editor", content)`.

Run → fail.

- [ ] **Step 2: Rewrite `MatchSetupView.qml`**

Replace the whole file with the profile-driven master-detail version:

```qml
import QtQuick
import QtQuick.Controls
import qt_observer
import "components"

Item {
    id: root
    objectName: "matchSetupView"

    property string selectedSeatId: ""
    property var editedProfile: ({})
    property int profileRevision: 0

    readonly property var seatRoles: ObserverClient.profileSchema && ObserverClient.profileSchema.seat_roles
                                      ? ObserverClient.profileSchema.seat_roles : ({})
    readonly property var roleTeams: ObserverClient.profileSchema && ObserverClient.profileSchema.role_teams
                                     ? ObserverClient.profileSchema.role_teams : ({})
    readonly property var seatIds: ObserverClient.profileSchema && ObserverClient.profileSchema.seat_ids
                                   ? ObserverClient.profileSchema.seat_ids : ["p1","p2","p3","p4","p5","p6"]
    readonly property bool launchEnabled: ObserverClient.profileValidation
        && ObserverClient.profileValidation.valid === true
        && root._validatedRevision === root.profileRevision
    property int _validatedRevision: -1

    Component.onCompleted: {
        ObserverClient.refreshProfileSchema()
        ObserverClient.refreshProfiles()
    }

    // Load the first profile once the list arrives.
    Connections {
        target: ObserverClient
        function onProfileItemsChanged() {
            if (root.editedProfile.name === undefined && ObserverClient.profileItems.length > 0)
                ObserverClient.fetchProfile(ObserverClient.profileItems[0].name)
        }
        function onLoadedProfileChanged() {
            root.editedProfile = JSON.parse(JSON.stringify(ObserverClient.loadedProfile))
            if (!root.editedProfile.seat_overrides) root.editedProfile.seat_overrides = ({})
            root.profileRevision++
            root._validatedRevision = -1
            if (!root.selectedSeatId && root.seatIds.length > 0) root.selectedSeatId = root.seatIds[0]
        }
        function onLaunchSucceeded() { root.StackView.view.parent.navigatePreflight() }
    }

    // Field-level effective config for a seat.
    function effective(seatId) {
        var role = root.seatRoles[seatId] || ""
        var def = (root.editedProfile.role_defaults && root.editedProfile.role_defaults[role]) || {}
        var ov = (root.editedProfile.seat_overrides && root.editedProfile.seat_overrides[seatId]) || {}
        return {
            player_id: seatId, role: role, team: root.roleTeams[role] || "",
            provider: ov.provider !== undefined ? ov.provider : def.provider,
            model: ov.model !== undefined ? ov.model : def.model,
            strategy: ov.strategy !== undefined ? ov.strategy : def.strategy,
            prompt: ov.prompt !== undefined ? ov.prompt : (def.prompt || "")
        }
    }

    // Materialize a full coherent override fragment on edit.
    function applyEdit(seatId, field, value) {
        var eff = effective(seatId)
        var frag = { provider: eff.provider, model: eff.model, strategy: eff.strategy, prompt: eff.prompt }
        frag[field] = value
        if (field === "provider") {
            var models = (ObserverClient.profileSchema.models || {})[value] || []
            frag.model = models.length > 0 ? models[0] : frag.model
        }
        var ep = JSON.parse(JSON.stringify(root.editedProfile))
        if (!ep.seat_overrides) ep.seat_overrides = ({})
        ep.seat_overrides[seatId] = frag
        root.editedProfile = ep
        root.profileRevision++          // any edit invalidates a prior verdict
    }

    Rectangle { anchors.fill: parent; color: Theme.color.bgBase }

    // -------------------------------------------------------------- Header row
    Column {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: Theme.space.xxxl
        anchors.leftMargin: Theme.layout.pageMargin
        anchors.rightMargin: Theme.layout.pageMargin
        spacing: Theme.space.md

        Text {
            text: I18n.t("对局配置", "Match Setup")
            color: Theme.color.text
            font.family: Theme.font.display; font.pixelSize: Theme.size.h1; font.weight: Theme.weight.bold
        }

        Row {
            spacing: Theme.space.md
            ComboBox {
                id: profilePicker
                objectName: "setupProfilePicker"
                width: 280
                model: ObserverClient.profileItems
                textRole: "name"
                onActivated: {
                    root.editedProfile = ({})
                    root.selectedSeatId = ""
                    ObserverClient.fetchProfile(ObserverClient.profileItems[currentIndex].name)
                }
            }
            AppButton {
                id: validateButton
                objectName: "setupValidateButton"
                text: I18n.t("校验", "Validate")
                variant: "secondary"
                onClicked: {
                    root._validatedRevision = root.profileRevision
                    ObserverClient.validateProfile(root.editedProfile)
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: ObserverClient.profileValidation && ObserverClient.profileValidation.errors
                         && ObserverClient.profileValidation.errors.length > 0
                text: visible ? ObserverClient.profileValidation.errors[0] : ""
                color: Theme.color.danger
                font.family: Theme.font.family; font.pixelSize: Theme.size.caption
            }
        }
    }

    EmptyState {
        anchors.centerIn: parent
        visible: ObserverClient.profileItems.length === 0
        // caption guidance for an empty profiles dir
        property string note: I18n.t("没有可用档案 — 在服务器 profiles/ 目录放入 JSON。",
                                      "No profiles — drop a JSON into the server's profiles/ dir.")
    }

    // ----------------------------------------------------- Master (seat grid)
    Flickable {
        id: master
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.bottom: actionBar.top
        anchors.topMargin: Theme.space.xl
        anchors.leftMargin: Theme.layout.pageMargin
        width: root.cardWidth * 2 + Theme.space.lg
        contentHeight: setupRoleCards.height
        clip: true
        visible: ObserverClient.profileItems.length > 0

        Grid {
            id: setupRoleCards
            objectName: "setupRoleCards"
            columns: 2
            spacing: Theme.space.lg
            Repeater {
                model: root.seatIds
                delegate: RoleCard {
                    property var eff: root.effective(modelData)
                    seatId: modelData
                    roleName: eff.role
                    displayRole: eff.role
                    width: 168
                    height: 150
                    MouseArea { anchors.fill: parent; onClicked: root.selectedSeatId = modelData }
                }
            }
        }
    }
    readonly property int cardWidth: 168

    // ----------------------------------------------------- Detail (seat editor)
    SeatEditorPanel {
        id: detail
        anchors.top: header.bottom
        anchors.right: parent.right
        anchors.bottom: actionBar.top
        anchors.left: master.right
        anchors.topMargin: Theme.space.xl
        anchors.rightMargin: Theme.layout.pageMargin
        anchors.leftMargin: Theme.space.xl
        anchors.bottomMargin: Theme.space.lg
        visible: root.selectedSeatId !== "" && ObserverClient.profileItems.length > 0
        seat: root.selectedSeatId ? root.effective(root.selectedSeatId) : ({})
        config: root.selectedSeatId ? root.effective(root.selectedSeatId) : ({})
        schema: ObserverClient.profileSchema
        onEdited: function(field, value) { root.applyEdit(root.selectedSeatId, field, value) }
    }

    // ------------------------------------------------------ Bottom action bar
    Rectangle {
        id: actionBar
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: Theme.layout.actionBarHeight
        color: Theme.color.surface
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 1; color: Theme.color.border }

        AppButton {
            text: I18n.t("返回", "Back")
            variant: "ghost"
            anchors.left: parent.left; anchors.leftMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.StackView.view.parent.navigateHome()
        }
        AppButton {
            id: setupContinueButton
            objectName: "setupContinueButton"
            text: I18n.t("启动", "Launch")
            variant: "primary"
            width: 200
            enabled: root.launchEnabled
            anchors.right: parent.right; anchors.rightMargin: Theme.layout.pageMargin
            anchors.verticalCenter: parent.verticalCenter
            // Advances to Preflight only via onLaunchSucceeded (202 + currentRunId).
            onClicked: ObserverClient.launchFromProfile(root.editedProfile)
        }
    }
}
```

> Notes: the view root `Item` is sized by StackView (no `anchors.fill`). The `setupContinueButton` objectName is kept (label 启动/Launch). `enabled: root.launchEnabled` ties Launch to a fresh passing Validate (profileRevision). Navigation happens only on `onLaunchSucceeded`.

- [ ] **Step 3: Update `clients/qt_observer/README.md` non-goals**

Replace the line containing `no full prompt/profile editor` with one that says a **profile setup editor** now exists, e.g.:
```text
- G2d-2 adds a profile setup editor (select/edit/validate/launch a server-side profile); still no Web observer client, no direct Python runtime binding, no local artifact file reads, no provider secrets.
```
Keep the other non-goal lines (`no Web observer client`, `no direct Python runtime binding`, `no local artifact file reads`) so their contract assertions stay green.

- [ ] **Step 4: Build + contract test + commit**

```powershell
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
python -m unittest tests.test_qt_observer_static_contract -v
```
Expected: build exit 0; contract `OK`. Commit:
```powershell
git add clients/qt_observer/qml/MatchSetupView.qml clients/qt_observer/README.md tests/test_qt_observer_static_contract.py
git commit -m "feat(g2d-2): profile-driven master-detail MatchSetupView with 202-gated launch"
```

---

## Task 5: Build, lint, visual verification

**Files:** none (verification) — fixes committed to the relevant Task file if needed.

- [ ] **Step 1: Clean build**

```powershell
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```
Expected: exit 0 (qmlcachegen AOT-compiles all QML).

- [ ] **Step 2: Static contract + ctest + qmllint**

```powershell
python -m unittest tests.test_qt_observer_static_contract -v
ctest --test-dir .tmp/qt-observer-build --output-on-failure
qmllint -I .tmp/qt-observer-build clients/qt_observer/qml/MatchSetupView.qml clients/qt_observer/qml/components/SeatEditorPanel.qml
```
Expected: contract `OK`; ctest `100%`; qmllint no `Error:` lines (ignore `[unqualified]`/`[missing-property]`).

- [ ] **Step 3: Visual capture (grabToImage → PNG → Read)**

Temporarily add to `AppShell.qml` a timer that navigates to setup, loads a profile, selects a seat, and grabs:
```qml
Timer {
    interval: 1500; running: true; repeat: false
    onTriggered: { navigateSetup(); grabTimer.start() }
}
Timer { id: grabTimer; interval: 1500; running: false
    onTriggered: stackView.grabToImage(function(r){ r.saveToFile("G:/Werewolf-agent/.tmp/g2d2_setup.png"); Qt.quit() }) }
```
Run the app pointed at a live G2a server with a profile in `profiles/`, then **Read** `.tmp/g2d2_setup.png` to confirm: profile picker, seat grid (left), seat editor (right) with provider/model/strategy dropdowns + prompt area + counter, action bar with disabled Launch until validated. **Remove the temp timers afterward.**

- [ ] **Step 4: Full Python suite + compileall**

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
python -m compileall src tests
```
Expected: only the documented pre-existing `test_context_budget` failure + env-blocked server tests; compileall `0 failures`.

- [ ] **Step 5: Commit any fixes**

```powershell
git add -A clients/qt_observer tests
git commit -m "test(g2d-2): build/contract/visual verification fixes" --allow-empty
```

---

## Task 6: Validation commands + review packet

**Files:** `.logs/review/latest/review-packet.md`, `.oh-my-harness/tree.md`

- [ ] **Step 1: Hygiene checks**

```powershell
git diff --check main...HEAD
git diff --name-only main...HEAD
git diff main...HEAD -- src clients tests | python -c "import sys,re; d=sys.stdin.read(); add=[l for l in d.splitlines() if l.startswith('+') and not l.startswith('+++')]; bad=[l for l in add if re.search(r'(QFile|QDir|file://|requests|httpx|openai|anthropic|sk-[A-Za-z0-9]{16}|Authorization:|Bearer )', l) and all(k not in l.lower() for k in ('marker','reject','frag','assertnotin','forbidden'))]; print('\n'.join(bad)); assert not bad, bad"
```
Expected: no whitespace errors; changed files within allowlist; no forbidden client patterns.

- [ ] **Step 2: Refresh tree**

```powershell
node .codex/hooks/tree.mjs --force
```
Expected: tree includes `SeatEditorPanel.qml`.

- [ ] **Step 3: Write review packet**

Create `.logs/review/latest/review-packet.md` (≤300 lines): Metadata (branch `feat/g2d-2-qt-setup-ui`, base `main`), Changed Files, Diff Stat, Diff Check, Allowlist, Forbidden/secret-scan, Test Summary (profile_config schema test OK; static contract OK; Qt build exit 0; ctest; qmllint; visual PNG referenced; server tests env-noted; pre-existing failure noted), Key Hunks (schema endpoint, client methods incl. 202 gate, SeatEditorPanel, MatchSetupView), Evidence Map (A1–A8), Acceptance Checklist, Review Trigger Result.

- [ ] **Step 4: Commit**

```powershell
git add .logs/review/latest/review-packet.md .oh-my-harness/tree.md
git commit -m "docs(g2d-2): review packet + tree refresh"
```

---

## Acceptance Criteria

- **A1.** `GET /api/profiles/schema` returns providers/models/strategies/roles/role_teams/seat_roles/seat_ids/prompt_max_len from constants; no `templates`, no secrets/paths. *(ProfileSchemaTests)*
- **A2.** `ObserverApiClient` exposes `profileItems`/`profileSchema`/`loadedProfile`/`profileValidation` + the 5 invokables + `launchSucceeded`/`launchFailed`; `fetchProfile` latest-wins; `launchFromProfile` advances only on 202. *(QtObserverProfileClientTests; build)*
- **A3.** `SeatEditorPanel.qml` edits provider/model(dependent)/strategy/prompt(counter), registered in CMake, required objectNames present. *(static contract; build)*
- **A4.** `MatchSetupView.qml` profile-driven master-detail (picker + seat grid + editor + validate); no static role array; options from `profileSchema`; Launch enabled only when valid for the current `profileRevision`. *(test_setup_is_profile_driven; build)*
- **A5.** Launch advances to Preflight only after 202 + `currentRunId` (`onLaunchSucceeded`); failure stays + shows error. *(cpp 202 gate; QML onLaunchSucceeded)*
- **A6.** Static-contract test updated + green (new components/objectNames, README non-goal updated, forbidden patterns absent); Qt build exit 0; ctest green; qmllint clean.
- **A7.** Visual capture confirms the master-detail editor renders per the design system. *(.tmp/g2d2_setup.png)*
- **A8.** No save endpoint, no client file I/O, no live providers, no new deps, no engine/route-product-doc changes. *(hygiene checks)*

---

## Review Packet Requirements

`.logs/review/latest/review-packet.md` ≤ 300 lines: Metadata, Changed Files, Diff Stat, Diff Check, Allowlist, Forbidden/secret-scan (list any safe test markers), Test Summary (with Qt build exit code + visual PNG reference + env/pre-existing notes), Key Hunks, Evidence Map (A1–A8), Acceptance Checklist, Review Trigger Result.

---

## PR Description Draft

Title: `feat: add G2d-2 Qt profile setup UI`

```markdown
## Summary
- Adds read-only GET /api/profiles/schema (dropdown allowlists from profile_config).
- ObserverApiClient: profileItems/profileSchema/loadedProfile/profileValidation + refresh/fetch/validate/launch; launch advances only on HTTP 202.
- New SeatEditorPanel.qml (provider/model/strategy/prompt); MatchSetupView becomes profile-driven master-detail with profileRevision-bound Validate→Launch.

## Scope
- Qt UI + one read-only endpoint. No save endpoint, no client file I/O, no live providers, no new deps.

## Validation
- python -m unittest tests.test_profile_config tests.test_observer_protocol -v
- Qt build (F: toolchain) exit 0; tests.test_qt_observer_static_contract OK; ctest; qmllint
- Visual: .tmp/g2d2_setup.png (master-detail editor)
- Server endpoint test authored; env-blocked like other server tests (documented).
```

---

## Execution Handoff

Order: (1) backend schema endpoint, (2) client profile methods, (3) SeatEditorPanel, (4) MatchSetupView master-detail + README + contract updates, (5) build/lint/visual, (6) packet. Each task commits. Do not add a save endpoint, client file I/O, live providers, or route-product-doc changes.

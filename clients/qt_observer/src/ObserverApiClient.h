#pragma once

#include <QObject>
#include <QJsonDocument>
#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QVariantMap>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QTimer>

class ObserverSseParser;

class ObserverApiClient : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString baseUrl READ baseUrl WRITE setBaseUrl NOTIFY baseUrlChanged)
    Q_PROPERTY(bool connected READ connected NOTIFY connectedChanged)
    Q_PROPERTY(QString currentRunId READ currentRunId NOTIFY currentRunChanged)
    Q_PROPERTY(QString currentStatus READ currentStatus NOTIFY currentStatusChanged)
    Q_PROPERTY(QString currentPerspective READ currentPerspective WRITE setCurrentPerspective NOTIFY currentPerspectiveChanged)
    Q_PROPERTY(QVariantList runItems READ runItems NOTIFY runItemsChanged)
    Q_PROPERTY(QVariantList eventItems READ eventItems NOTIFY eventItemsChanged)
    Q_PROPERTY(QVariantList auditItems READ auditItems NOTIFY auditItemsChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    // G2c projection properties
    Q_PROPERTY(QVariantList playerItems READ playerItems NOTIFY playerItemsChanged)
    Q_PROPERTY(QVariantMap projectionProof READ projectionProof NOTIFY projectionProofChanged)
    Q_PROPERTY(int hiddenEventCount READ hiddenEventCount NOTIFY projectionChanged)
    Q_PROPERTY(int hiddenSnapshotCount READ hiddenSnapshotCount NOTIFY projectionChanged)
    Q_PROPERTY(QString visibilityContractVersion READ visibilityContractVersion NOTIFY projectionChanged)
    // P2-C-1: per-perspective enriched projection events (data.summary + target)
    Q_PROPERTY(QVariantList projectionEvents READ projectionEvents NOTIFY projectionEventsChanged)
    // P2-D: eval-ready settlement bundle (read-only; fetched lazily on game completion).
    Q_PROPERTY(QVariantMap settlementBundle READ settlementBundle NOTIFY settlementBundleChanged)
    // P2-D: 0 = live freeze ceremony, 1 = history → straight to report. Set
    // SYNCHRONOUSLY by openRun(forReport) so it is reliable when the theater mounts
    // (currentStatus is async and was racy as the freeze/report discriminator).
    Q_PROPERTY(int settlementEntry READ settlementEntry NOTIFY settlementEntryChanged)
    // P2-B (Q1): per-provider live model lists keyed by provider id (deepseek/
    // openai/anthropic/openai_compatible). Populated by fetchProviderModels via the
    // loopback GET /api/providers/{provider}/models endpoint. Never carries a key.
    Q_PROPERTY(QVariantMap providerModels READ providerModels NOTIFY providerModelsChanged)
    // G2d-2 profile setup properties
    Q_PROPERTY(QVariantList profileItems READ profileItems NOTIFY profileItemsChanged)
    Q_PROPERTY(QVariantMap profileSchema READ profileSchema NOTIFY profileSchemaChanged)
    Q_PROPERTY(QVariantMap loadedProfile READ loadedProfile NOTIFY loadedProfileChanged)
    Q_PROPERTY(QVariantMap profileValidation READ profileValidation NOTIFY profileValidationChanged)
    // G3-2 live/fake toggle: read-only capability posture (intent) + executed
    // truth.  liveReasonCode/liveReasonMessage are server-supplied and rendered
    // verbatim; the ONLY client-owned code is "unreachable".  currentExecutionMode
    // is set ONLY from run-detail execution_mode (C1) and reset to "" on run
    // change / missing field / request error (C1-bis).
    Q_PROPERTY(bool liveAvailable READ liveAvailable NOTIFY capabilitiesChanged)
    Q_PROPERTY(QString liveReasonCode READ liveReasonCode NOTIFY capabilitiesChanged)
    Q_PROPERTY(QString liveReasonMessage READ liveReasonMessage NOTIFY capabilitiesChanged)
    Q_PROPERTY(QString defaultMode READ defaultMode NOTIFY capabilitiesChanged)
    Q_PROPERTY(QString currentExecutionMode READ currentExecutionMode NOTIFY currentExecutionModeChanged)
    // Startup convenience: a run id to auto-open into the cockpit (CLI --open-run).
    Q_PROPERTY(QString initialRunId READ initialRunId CONSTANT)

public:
    explicit ObserverApiClient(QObject *parent = nullptr);
    ~ObserverApiClient() override;

    QString baseUrl() const;
    void setBaseUrl(const QString &url);

    bool connected() const;
    QString currentRunId() const;
    QString currentStatus() const;
    QString currentPerspective() const;
    void setCurrentPerspective(const QString &perspective);

    QVariantList runItems() const;
    QVariantList eventItems() const;
    QVariantList auditItems() const;
    QString lastError() const;
    // G2c projection accessors
    QVariantList playerItems() const;
    QVariantMap projectionProof() const;
    int hiddenEventCount() const;
    int hiddenSnapshotCount() const;
    QString visibilityContractVersion() const;
    QVariantList projectionEvents() const;
    // P2-D settlement accessor
    QVariantMap settlementBundle() const;
    int settlementEntry() const;
    // P2-B (Q1) provider model-list accessor
    QVariantMap providerModels() const;
    // G2d-2 profile setup accessors
    QVariantList profileItems() const;
    QVariantMap profileSchema() const;
    QVariantMap loadedProfile() const;
    QVariantMap profileValidation() const;
    // G3-2 capability + executed-truth accessors
    bool liveAvailable() const;
    QString liveReasonCode() const;
    QString liveReasonMessage() const;
    QString defaultMode() const;
    QString currentExecutionMode() const;
    QString initialRunId() const;
    void setInitialRunId(const QString &id);

public slots:
    Q_INVOKABLE void checkHealth();
    Q_INVOKABLE void refreshRuns();
    Q_INVOKABLE void startDefaultMatch();
    // forReport=true (history "查看战报") makes the settlement overlay skip the freeze
    // ceremony and open straight to the report; default false = live freeze ceremony.
    Q_INVOKABLE void openRun(const QString &runId, bool forReport = false);
    Q_INVOKABLE void deleteRun(const QString &runId);
    Q_INVOKABLE void interruptRun(const QString &runId);
    Q_INVOKABLE void connectStream();
    Q_INVOKABLE void disconnectStream();
    Q_INVOKABLE void refreshAuditLinks();
    Q_INVOKABLE void refreshProjection();
    // P2-D: lazily fetch the settlement bundle for a completed run (latest-wins).
    Q_INVOKABLE void fetchSettlement(const QString &runId);
    // G2d-2 profile setup invokables
    Q_INVOKABLE void refreshProfiles();
    Q_INVOKABLE void refreshProfileSchema();
    Q_INVOKABLE void fetchProfile(const QString &name);
    Q_INVOKABLE void validateProfile(const QVariantMap &profile);
    Q_INVOKABLE void fetchConfig(const QString &configId);
    Q_INVOKABLE void saveConfig(const QString &displayName, const QVariantMap &profile);
    Q_INVOKABLE void importConfigFromFile(const QString &fileUrl);
    Q_INVOKABLE void exportConfigToFile(const QString &configId, const QString &fileUrl);
    Q_INVOKABLE void exportProfileToFile(const QString &displayName, const QVariantMap &profile, const QString &fileUrl);
    // C2: QML always passes an explicit mode ("fake"|"live") — no C++ default arg.
    Q_INVOKABLE void launchFromProfile(const QVariantMap &profile, const QString &mode);
    // G3-2 read-only live posture (no key, no provider call).
    Q_INVOKABLE void refreshCapabilities();
    // P2-B (Q1): fetch the live model list for a configured provider via the
    // loopback GET /api/providers/{provider}/models. On success updates
    // providerModels[provider] and emits providerModelsFetched(provider); on
    // failure emits providerModelsFailed with the key-free, server-supplied code
    // (read from the JSON envelope and rendered data-driven by QML — server
    // reason codes are never enumerated as client literals here).
    Q_INVOKABLE void fetchProviderModels(const QString &provider);
    // Drop a provider's cached (validated) model list — call when its credential
    // changes so a re-entered, not-yet-validated key no longer reads as validated.
    Q_INVOKABLE void invalidateProviderModels(const QString &provider);

signals:
    void baseUrlChanged();
    void connectedChanged();
    void currentRunChanged();
    void currentStatusChanged();
    void currentPerspectiveChanged();
    void runItemsChanged();
    void eventItemsChanged();
    void auditItemsChanged();
    void lastErrorChanged();
    // G2c projection signals
    void playerItemsChanged();
    void projectionProofChanged();
    void projectionChanged();
    void projectionEventsChanged();
    // P2-D settlement signals
    void settlementBundleChanged();
    void settlementEntryChanged();
    // G2d-2 profile setup signals
    void profileItemsChanged();
    void profileSchemaChanged();
    void loadedProfileChanged();
    void profileValidationChanged();
    void launchSucceeded();
    void launchFailed();
    void configLoaded(const QString &configId);
    void configSaved(const QString &configId);
    void configImported(const QString &configId);
    void configExported(const QString &filePath);
    void configActionFailed(const QString &message);
    // G3-2 capability + executed-truth signals
    void capabilitiesChanged();
    void currentExecutionModeChanged();
    // P2-B (Q1) provider model-list signals
    void providerModelsChanged();                                              // property NOTIFY (provider-agnostic)
    void providerModelsFetched(const QString &provider);                       // a fetch for THIS provider succeeded
    void providerModelsFailed(const QString &provider, const QString &reason); // reason is key-free
    void deleteRunFinished(const QString &runId, bool ok, const QString &error);
    void interruptRunFinished(const QString &runId, bool ok, const QString &error);

private slots:
    void onStreamReadyRead();
    void onStreamFinished();
    void onStreamError(QNetworkReply::NetworkError error);

private:
    QNetworkReply *get(const QString &path);
    QNetworkReply *post(const QString &path, const QByteArray &body);
    void setError(const QString &msg);
    void setConfigActionError(const QString &msg);
    QString localPathFromFileUrl(const QString &fileUrl) const;
    bool writeJsonDocumentToFile(const QJsonDocument &doc, const QString &fileUrl, QString *error) const;
    void startStreamRequest(bool clearEvents = true);
    void stopStream();
    bool shouldReconnectStream() const;
    void scheduleStreamReconnect();
    // C1-bis: a run change must never inherit the prior run's executed truth.
    void setCurrentRunId(const QString &runId);
    void resetExecutionMode();

    QString m_baseUrl;
    bool m_connected;
    QString m_currentRunId;
    QString m_currentStatus;
    QString m_currentPerspective;
    QVariantList m_runItems;
    QVariantList m_eventItems;
    QVariantList m_auditItems;
    QString m_lastError;
    // G2c projection state
    QVariantList m_playerItems;
    QVariantMap m_projectionProof;
    int m_hiddenEventCount = 0;
    int m_hiddenSnapshotCount = 0;
    QString m_visibilityContractVersion;
    quint64 m_projectionRequestSerial = 0;
    QVariantList m_projectionEvents;
    // P2-D settlement state
    QVariantMap m_settlementBundle;
    int m_settlementRequestSerial = 0;
    int m_settlementEntry = 0;   // 0 = freeze ceremony, 1 = history → report-direct
    // P2-B (Q1) provider model lists, keyed by provider id
    QVariantMap m_providerModels;
    // G2d-2 profile setup state
    QVariantList m_profileItems;
    QVariantMap m_profileSchema;
    QVariantMap m_loadedProfile;
    QVariantMap m_profileValidation;
    quint64 m_profileRequestSerial = 0;
    quint64 m_profileValidateSerial = 0;
    // G3-2 live capability posture + executed truth
    bool m_liveAvailable = false;
    QString m_liveReasonCode;
    QString m_liveReasonMessage;
    QString m_defaultMode = QStringLiteral("fake");
    QString m_currentExecutionMode;
    QString m_initialRunId;
    QString m_pendingOpenRunId;   // last openRun target; stale async replies are dropped

    QNetworkAccessManager *m_network;
    QNetworkReply *m_streamReply;
    bool m_streamDesired = false;
    int m_streamReconnectAttempts = 0;
    QTimer m_streamReconnectTimer;
    ObserverSseParser *m_sseParser;
};

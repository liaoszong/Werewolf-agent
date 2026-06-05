#pragma once

#include <QObject>
#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QVariantMap>
#include <QNetworkAccessManager>
#include <QNetworkReply>

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

public slots:
    Q_INVOKABLE void checkHealth();
    Q_INVOKABLE void refreshRuns();
    Q_INVOKABLE void startDefaultMatch();
    Q_INVOKABLE void openRun(const QString &runId);
    Q_INVOKABLE void connectStream();
    Q_INVOKABLE void disconnectStream();
    Q_INVOKABLE void refreshAuditLinks();
    Q_INVOKABLE void refreshProjection();
    // G2d-2 profile setup invokables
    Q_INVOKABLE void refreshProfiles();
    Q_INVOKABLE void refreshProfileSchema();
    Q_INVOKABLE void fetchProfile(const QString &name);
    Q_INVOKABLE void validateProfile(const QVariantMap &profile);
    // C2: QML always passes an explicit mode ("fake"|"live") — no C++ default arg.
    Q_INVOKABLE void launchFromProfile(const QVariantMap &profile, const QString &mode);
    // G3-2 read-only live posture (no key, no provider call).
    Q_INVOKABLE void refreshCapabilities();

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
    // G2d-2 profile setup signals
    void profileItemsChanged();
    void profileSchemaChanged();
    void loadedProfileChanged();
    void profileValidationChanged();
    void launchSucceeded();
    void launchFailed();
    // G3-2 capability + executed-truth signals
    void capabilitiesChanged();
    void currentExecutionModeChanged();

private slots:
    void onStreamReadyRead();
    void onStreamFinished();
    void onStreamError(QNetworkReply::NetworkError error);

private:
    QNetworkReply *get(const QString &path);
    QNetworkReply *post(const QString &path, const QByteArray &body);
    void setError(const QString &msg);
    void startStreamRequest();
    void stopStream();
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

    QNetworkAccessManager *m_network;
    QNetworkReply *m_streamReply;
    ObserverSseParser *m_sseParser;
};

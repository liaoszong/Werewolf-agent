#pragma once

#include <QObject>
#include <QString>
#include <QStringList>
#include <QVariantList>
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

public slots:
    Q_INVOKABLE void checkHealth();
    Q_INVOKABLE void refreshRuns();
    Q_INVOKABLE void startDefaultMatch();
    Q_INVOKABLE void openRun(const QString &runId);
    Q_INVOKABLE void connectStream();
    Q_INVOKABLE void disconnectStream();
    Q_INVOKABLE void refreshAuditLinks();

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

    QString m_baseUrl;
    bool m_connected;
    QString m_currentRunId;
    QString m_currentStatus;
    QString m_currentPerspective;
    QVariantList m_runItems;
    QVariantList m_eventItems;
    QVariantList m_auditItems;
    QString m_lastError;

    QNetworkAccessManager *m_network;
    QNetworkReply *m_streamReply;
    ObserverSseParser *m_sseParser;
};

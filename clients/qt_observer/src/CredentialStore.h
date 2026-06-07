#pragma once
#include <QObject>
#include <QString>
#include <QSettings>
#include <QNetworkAccessManager>

// P2-B-1: client-side BYO-key store. Persists the user's API key via QSettings
// (DEV-ONLY: plaintext on disk; marked dev-only per the spec Storage invariant)
// and relays it to the LOCAL server as a session credential. QML sees only
// masked/presence accessors — never the raw saved key (no getRawKey()).
//
// Registration: qmlRegisterSingletonInstance (mirrors ObserverApiClient pattern).
class CredentialStore : public QObject {
    Q_OBJECT
public:
    explicit CredentialStore(QObject *parent = nullptr);

    Q_INVOKABLE bool hasCredential(const QString &provider) const;
    Q_INVOKABLE QString maskedCredential(const QString &provider) const; // "sk-••••1234" or ""
    Q_INVOKABLE void saveCredential(const QString &provider, const QString &rawText);
    Q_INVOKABLE void clearCredential(const QString &provider);           // QSettings + server DELETE
    Q_INVOKABLE void syncCredentialToServer(const QString &provider);    // POST /api/credentials

    void setBaseUrl(const QString &baseUrl); // wired from main.cpp like ObserverApiClient

signals:
    void credentialChanged(const QString &provider);
    void syncSucceeded(const QString &provider);
    void syncFailed(const QString &provider, const QString &reason); // reason is key-free

private:
    static QString mask(const QString &raw);
    QString rawCredential(const QString &provider) const; // PRIVATE — never Q_INVOKABLE

    QSettings m_settings;
    QString m_baseUrl;
    QNetworkAccessManager *m_network;
};

#pragma once
#include <QObject>
#include <QHash>
#include <QString>
#include <QStringList>
#include <QSettings>
#include <QNetworkAccessManager>

// P2-B-1: client-side BYO-key store. Raw API keys are session-memory-only:
// they live in this process, are relayed to the LOCAL server as session
// credentials, and are never persisted through QSettings. QML sees only
// masked/presence accessors — never the raw key (no getRawKey()).
//
// P2-B (Q1): multi-provider — each provider stores an optional non-secret
// base_url via QSettings (custom OpenAI-compatible endpoints require one). The
// base_url is NOT a secret and IS exposed to QML (baseUrlFor) so the settings
// form can pre-fill; the key never is. The server-side contract
// (POST /api/credentials) accepts an optional base_url and requires it for
// openai_compatible.
//
// Registration: qmlRegisterSingletonInstance (mirrors ObserverApiClient pattern).
class CredentialStore : public QObject {
    Q_OBJECT
public:
    explicit CredentialStore(QObject *parent = nullptr);

    Q_INVOKABLE bool hasCredential(const QString &provider) const;
    Q_INVOKABLE QString maskedCredential(const QString &provider) const; // masked prefix + bullets + suffix, or ""
    Q_INVOKABLE QString baseUrlFor(const QString &provider) const;       // stored base_url ("" if none) — NOT secret
    Q_INVOKABLE QStringList configuredProviders() const;                 // providers with a session key
    // baseUrl defaults to "" so the legacy 2-arg call (DeepSeek) stays valid; a
    // blank baseUrl clears any stored custom endpoint for the provider.
    Q_INVOKABLE void saveCredential(const QString &provider, const QString &rawText, const QString &baseUrl = QString());
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

    QHash<QString, QString> m_credentials;
    QSettings m_settings;
    QString m_baseUrl;
    QNetworkAccessManager *m_network;
};

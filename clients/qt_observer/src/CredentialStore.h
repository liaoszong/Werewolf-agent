#pragma once
#include <QObject>
#include <QHash>
#include <QString>
#include <QStringList>
#include <QSettings>
#include <QNetworkAccessManager>

// TF-1: client-side BYO-key store with OS-backed persistence.
//
// Raw API keys MUST NOT be persisted to QSettings, files, logs or HTTP responses.
// On Windows the raw key is persisted through the Windows Credential Manager
// (CRED_TYPE_GENERIC / CRED_PERSIST_LOCAL_MACHINE) under a stable target name;
// on other platforms it is session-memory-only (no plaintext QSettings fallback)
// until an equivalent system credential vault is wired in.
//
// `m_credentials` is a process-level cache populated at construction from the
// OS vault; QSettings keeps only NON-secret state: the per-provider base_url
// (`byobase/<provider>`) and a provider-ID index (`credential/providers`). The
// raw key is never read from QSettings on the normal path. A legacy plaintext
// `byokey/<provider>` entry is migrated ONCE into the OS vault and then removed
// only after the vault write succeeds.
//
// P2-B (Q1): multi-provider — each provider stores an optional non-secret
// base_url via QSettings (custom OpenAI-compatible endpoints require one). The
// base_url is NOT a secret and IS exposed to QML (baseUrlFor) so the settings
// form can pre-fill; the key never is. The server-side contract
// (POST /api/credentials) accepts an optional base_url and requires it for
// openai_compatible.
//
// QML sees only masked/presence accessors — never the raw key (no getRawKey(),
// rawCredential is private and never Q_INVOKABLE).
//
// Registration: qmlRegisterSingletonInstance (mirrors ObserverApiClient pattern).
class CredentialStore : public QObject {
    Q_OBJECT
public:
    explicit CredentialStore(QObject *parent = nullptr);

    Q_INVOKABLE bool hasCredential(const QString &provider) const;
    Q_INVOKABLE QString maskedCredential(const QString &provider) const; // masked prefix + bullets + suffix, or ""
    Q_INVOKABLE QString baseUrlFor(const QString &provider) const;       // stored base_url ("" if none) — NOT secret
    Q_INVOKABLE QStringList configuredProviders() const;                 // providers with a loaded/saved key
    // baseUrl defaults to "" so the legacy 2-arg call (DeepSeek) stays valid; a
    // blank baseUrl clears any stored custom endpoint for the provider.
    // Returns whether the credential was persisted (false on empty key or a
    // vault write failure); QML may ignore the return value.
    Q_INVOKABLE bool saveCredential(const QString &provider, const QString &rawText, const QString &baseUrl = QString());
    Q_INVOKABLE void clearCredential(const QString &provider);           // vault + cache + QSettings + server DELETE
    Q_INVOKABLE void syncCredentialToServer(const QString &provider);    // POST /api/credentials

    void setBaseUrl(const QString &baseUrl); // wired from main.cpp like ObserverApiClient

signals:
    void credentialChanged(const QString &provider);
    void syncSucceeded(const QString &provider);
    void syncFailed(const QString &provider, const QString &reason); // reason is key-free

private:
    static QString mask(const QString &raw);
    QString rawCredential(const QString &provider) const; // PRIVATE — never Q_INVOKABLE

    // ---- OS-vault helpers (no-op outside Windows) -------------------------
    // Target name is stable: "WerewolfAgent/byokey/<provider>". The raw key is
    // stored only inside the CredentialBlob; it never appears in TargetName /
    // UserName / Comment / error text. Returns false on a vault failure; the
    // key-free status is reported via the bool, never via a thrown string.
    static QString credentialTarget(const QString &provider);
#ifdef Q_OS_WIN
    static bool writePersistentCredential(const QString &provider, const QString &rawKey);
    static bool readPersistentCredential(const QString &provider, QString *outKey);
    static bool deletePersistentCredential(const QString &provider);
#else
    // Non-Windows: no OS vault wired in this slice. Session-memory-only; never
    // a plaintext QSettings fallback (see the ADR). These return failure so the
    // cache is the only source and no plaintext is written.
    static bool writePersistentCredential(const QString &, const QString &) { return false; }
    static bool readPersistentCredential(const QString &, QString *) { return false; }
    static bool deletePersistentCredential(const QString &) { return true; }
#endif

    // ---- provider-ID index (non-secret) -----------------------------------
    QStringList providerIndex() const;
    void setProviderIndex(const QStringList &providers);

    QHash<QString, QString> m_credentials;
    QSettings m_settings;
    QString m_baseUrl;
    QNetworkAccessManager *m_network;
};

#include "CredentialStore.h"

#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaEnum>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>
#include <QVarLengthArray>
#include <cstring>

#ifdef Q_OS_WIN
#include <windows.h>
#include <wincred.h>
#endif

// ---------------------------------------------------------------------------
// Non-secret QSettings key layout (raw API keys NEVER land here on the normal
// path — only the legacy `byokey/<provider>` migration reads them once).
// ---------------------------------------------------------------------------
static const QString kLegacyKeyPrefix = QStringLiteral("byokey/");
static const QString kBaseKeyPrefix = QStringLiteral("byobase/");
static const QString kProviderIndexKey = QStringLiteral("credential/providers");
static const QString kVaultNamespace = QStringLiteral("WerewolfAgent/byokey/");

CredentialStore::CredentialStore(QObject *parent)
    : QObject(parent)
    , m_settings(QStringLiteral("WerewolfAgent"), QStringLiteral("CredentialStore"))
    , m_baseUrl(QStringLiteral("http://127.0.0.1:8765"))
    , m_network(new QNetworkAccessManager(this))
{
    // 1) Load provider IDs known to be configured. This is a NON-secret index;
    //    presence here is not proof of a key — we verify each one against the
    //    OS vault and drop any stale entry whose credential is gone.
    QStringList known = providerIndex();
    QStringList liveProviders;

    for (const QString &provider : known) {
        if (provider.isEmpty())
            continue;
        QString cached;
        if (readPersistentCredential(provider, &cached) && !cached.isEmpty()) {
            m_credentials.insert(provider, cached);
            liveProviders.append(provider);
        }
    }

    // 2) Migrate legacy plaintext `byokey/<provider>` entries into the OS vault.
    //    The raw value is read ONLY here, used only for this write, and the
    //    legacy entry is removed ONLY after the vault write succeeds — so a
    //    vault failure never silently drops a user's key.
    const QStringList allKeys = m_settings.allKeys();
    for (const QString &key : allKeys) {
        if (!key.startsWith(kLegacyKeyPrefix))
            continue;
        const QString provider = key.mid(kLegacyKeyPrefix.length());
        if (provider.isEmpty())
            continue;
        // Legacy migration read (restricted, this branch only). The value is
        // never logged, never echoed, and is dropped from scope right after use.
        const QString legacyRaw = m_settings.value(key).toString();
        if (legacyRaw.isEmpty()) {
            // Nothing useful to migrate; remove the empty placeholder.
            m_settings.remove(key);
            continue;
        }
        if (writePersistentCredential(provider, legacyRaw)) {
            m_credentials.insert(provider, legacyRaw);
            if (!liveProviders.contains(provider))
                liveProviders.append(provider);
            m_settings.remove(key);
        }
        // On vault-write failure: keep the legacy entry so the next launch can
        // retry. Do NOT log the key, a prefix/suffix, its length, or any value.
    }

    // 3) Reconcile the index to actually-live providers so we never advertise a
    //    key that does not exist in the vault.
    setProviderIndex(liveProviders);
}

void CredentialStore::setBaseUrl(const QString &baseUrl)
{
    m_baseUrl = baseUrl;
}

// ---------------------------------------------------------------------------
// Private helpers — OS vault
// ---------------------------------------------------------------------------

QString CredentialStore::credentialTarget(const QString &provider)
{
    return kVaultNamespace + provider;
}

#ifdef Q_OS_WIN

// Writes `rawKey` into the Windows Credential Manager as a generic, local-
// machine persisted credential. Returns true on success. The raw key is held
// only inside the CredentialBlob and a short-lived byte buffer that is cleared
// best-effort before returning.
bool CredentialStore::writePersistentCredential(const QString &provider, const QString &rawKey)
{
    const std::wstring target = credentialTarget(provider).toStdWString();

    QByteArray blobBytes = rawKey.toUtf8();
    // Copy into a writable buffer so we can zero it after the call.
    QVarLengthArray<unsigned char, 256> blob(blobBytes.size());
    if (!blob.isEmpty())
        std::memcpy(blob.data(), blobBytes.constData(), static_cast<size_t>(blob.size()));

    // Clear the UTF-8 QByteArray copy as soon as we no longer need it.
    if (!blobBytes.isEmpty())
        std::memset(blobBytes.data(), 0,
                    static_cast<size_t>(blobBytes.size()));

    CREDENTIALW cred;
    std::memset(&cred, 0, sizeof(cred));
    cred.Flags = 0;
    cred.Type = CRED_TYPE_GENERIC;
    cred.TargetName = const_cast<LPWSTR>(target.c_str());
    cred.Persist = CRED_PERSIST_LOCAL_MACHINE;
    cred.UserName = nullptr;   // never put any key-derived data here
    cred.Comment = nullptr;    // never put any key-derived data here
    cred.CredentialBlob = blob.isEmpty() ? nullptr : blob.data();
    cred.CredentialBlobSize = static_cast<DWORD>(blob.size());

    const BOOL ok = ::CredWriteW(&cred, 0);

    // Best-effort clear of the transient blob regardless of outcome.
    if (!blob.isEmpty())
        std::memset(blob.data(), 0, static_cast<size_t>(blob.size()));

    return ok != FALSE;
}

bool CredentialStore::readPersistentCredential(const QString &provider, QString *outKey)
{
    if (outKey)
        outKey->clear();
    const std::wstring target = credentialTarget(provider).toStdWString();

    PCREDENTIALW raw = nullptr;
    const BOOL ok = ::CredReadW(target.c_str(), CRED_TYPE_GENERIC, 0, &raw);
    if (!ok) {
        const DWORD err = ::GetLastError();
        // ERROR_NOT_FOUND => not configured yet; not an error.
        if (err == ERROR_NOT_FOUND)
            return false;
        // Any other failure is reported as a miss; no key-derived text is
        // surfaced, and GetLastError() is never decoded into a request string.
        return false;
    }

    QString key;
    if (raw->CredentialBlob && raw->CredentialBlobSize > 0) {
        const int byteLen = static_cast<int>(raw->CredentialBlobSize);
        key = QString::fromUtf8(reinterpret_cast<const char *>(raw->CredentialBlob),
                                byteLen);
    }

    ::CredFree(raw);

    if (outKey)
        *outKey = key;
    // Clear the local copy of the key as soon as it has been handed out.
    key.clear();
    return true;
}

bool CredentialStore::deletePersistentCredential(const QString &provider)
{
    const std::wstring target = credentialTarget(provider).toStdWString();
    const BOOL ok = ::CredDeleteW(target.c_str(), CRED_TYPE_GENERIC, 0);
    if (!ok) {
        const DWORD err = ::GetLastError();
        // Idempotent: a missing credential is a successful delete.
        if (err == ERROR_NOT_FOUND)
            return true;
        return false;
    }
    return true;
}

#endif // Q_OS_WIN

// ---------------------------------------------------------------------------
// Private helpers — provider index (non-secret)
// ---------------------------------------------------------------------------

QStringList CredentialStore::providerIndex() const
{
    return m_settings.value(kProviderIndexKey).toStringList();
}

void CredentialStore::setProviderIndex(const QStringList &providers)
{
    QStringList sorted = providers;
    sorted.removeAll(QString());
    sorted.removeDuplicates();
    sorted.sort();
    m_settings.setValue(kProviderIndexKey, sorted);
}

// ---------------------------------------------------------------------------
// Private helpers — masking / reads
// ---------------------------------------------------------------------------

QString CredentialStore::rawCredential(const QString &provider) const
{
    return m_credentials.value(provider);
}

// base_url is NOT a secret — persisted under a separate prefix and readable by
// QML (the masking rules apply only to the key).
QString CredentialStore::baseUrlFor(const QString &provider) const
{
    return m_settings.value(kBaseKeyPrefix + provider).toString();
}

QStringList CredentialStore::configuredProviders() const
{
    QStringList providers;
    const QStringList keys = m_credentials.keys();
    for (const QString &provider : keys) {
        if (!provider.isEmpty() && !m_credentials.value(provider).isEmpty())
            providers.append(provider);
    }
    providers.sort();
    return providers;
}

// static
QString CredentialStore::mask(const QString &raw)
{
    if (raw.isEmpty())
        return QString();
    if (raw.length() <= 7)
        return QStringLiteral("••••");
    return raw.left(3) + QStringLiteral("••••") + raw.right(4);
}

// ---------------------------------------------------------------------------
// Q_INVOKABLE — presence / masked view (no raw key exposed to QML)
// ---------------------------------------------------------------------------

bool CredentialStore::hasCredential(const QString &provider) const
{
    return !rawCredential(provider).isEmpty();
}

QString CredentialStore::maskedCredential(const QString &provider) const
{
    return mask(rawCredential(provider));
}

// ---------------------------------------------------------------------------
// Q_INVOKABLE — mutations
// ---------------------------------------------------------------------------

bool CredentialStore::saveCredential(const QString &provider, const QString &rawText, const QString &baseUrl)
{
    if (rawText.trimmed().isEmpty())
        return false;

#ifdef Q_OS_WIN
    // Persist to the OS vault FIRST. Only on success do we update the in-memory
    // cache and the provider-ID index, so a vault failure leaves no half-state.
    if (!writePersistentCredential(provider, rawText))
        return false;
#endif

    m_credentials.insert(provider, rawText);

#ifdef Q_OS_WIN
    // Reconcile the non-secret provider-ID index.
    QStringList idx = providerIndex();
    if (!idx.contains(provider)) {
        idx.append(provider);
        setProviderIndex(idx);
    }
#endif

    // A blank base_url clears any stored custom endpoint (the server then falls
    // back to the provider's registry default). Non-blank values are trimmed.
    const QString trimmedBase = baseUrl.trimmed();
    if (trimmedBase.isEmpty())
        m_settings.remove(kBaseKeyPrefix + provider);
    else
        m_settings.setValue(kBaseKeyPrefix + provider, trimmedBase);

    emit credentialChanged(provider);
    return true;
}

void CredentialStore::clearCredential(const QString &provider)
{
    // Remove the OS-vault credential (idempotent). Best-effort: even on failure
    // we clear the in-memory cache and QSettings so the UI reflects the clear.
    deletePersistentCredential(provider);

    m_credentials.remove(provider);
    // Remove the now-empty provider from the non-secret index.
    QStringList idx = providerIndex();
    if (idx.removeAll(provider) > 0)
        setProviderIndex(idx);
    m_settings.remove(kLegacyKeyPrefix + provider); // clean any leftover legacy entry
    m_settings.remove(kBaseKeyPrefix + provider);
    emit credentialChanged(provider);

    // Best-effort DELETE to the local server — ignore response, clean up reply.
    QNetworkRequest req(QUrl(m_baseUrl + QStringLiteral("/api/credentials/")
        + QString::fromUtf8(QUrl::toPercentEncoding(provider))));
    QNetworkReply *reply = m_network->deleteResource(req);
    connect(reply, &QNetworkReply::finished, reply, &QNetworkReply::deleteLater);
}

void CredentialStore::syncCredentialToServer(const QString &provider)
{
    const QString raw = rawCredential(provider);
    if (raw.isEmpty()) {
        emit syncFailed(provider, QStringLiteral("no_local_key"));
        return;
    }

    // Build JSON body — key is in the body, never in the URL or headers.
    QJsonObject body;
    body[QStringLiteral("provider")] = provider;
    body[QStringLiteral("api_key")] = raw;
    // base_url is optional (omitted = server uses the provider's registry default).
    // It is required server-side only for openai_compatible; the settings form
    // enforces that before saving, so a stored value reaches the server here.
    const QString baseUrl = baseUrlFor(provider);
    if (!baseUrl.isEmpty())
        body[QStringLiteral("base_url")] = baseUrl;
    const QByteArray bodyBytes = QJsonDocument(body).toJson(QJsonDocument::Compact);

    QNetworkRequest req(QUrl(m_baseUrl + QStringLiteral("/api/credentials")));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));

    QNetworkReply *reply = m_network->post(req, bodyBytes);
    connect(reply, &QNetworkReply::finished, this, [this, reply, provider]() {
        const int status =
            reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        if (status >= 200 && status < 300) {
            emit syncSucceeded(provider);
        } else {
            // Reason is key-free: derived from HTTP status or QNetworkReply error enum only.
            // Never include response body or the key.
            QString reason;
            if (status > 0) {
                reason = QStringLiteral("http_") + QString::number(status);
            } else {
                // QNetworkReply::NetworkError enum value name (numeric fallback).
                const QMetaEnum me =
                    QMetaEnum::fromType<QNetworkReply::NetworkError>();
                const char *name = me.valueToKey(static_cast<int>(reply->error()));
                reason = name ? QString::fromLatin1(name)
                              : QStringLiteral("network_error_") +
                                    QString::number(static_cast<int>(reply->error()));
            }
            emit syncFailed(provider, reason);
        }
        reply->deleteLater();
    });
}

#include "CredentialStore.h"

#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaEnum>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>

CredentialStore::CredentialStore(QObject *parent)
    : QObject(parent)
    , m_settings(QStringLiteral("WerewolfAgent"), QStringLiteral("CredentialStore"))
    , m_baseUrl(QStringLiteral("http://127.0.0.1:8765"))
    , m_network(new QNetworkAccessManager(this))
{
    const QString legacyKeyPrefix = QStringLiteral("byokey/");
    const QStringList keys = m_settings.allKeys();
    for (const QString &key : keys) {
        if (key.startsWith(legacyKeyPrefix))
            m_settings.remove(key);
    }
}

void CredentialStore::setBaseUrl(const QString &baseUrl)
{
    m_baseUrl = baseUrl;
}

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

QString CredentialStore::rawCredential(const QString &provider) const
{
    return m_credentials.value(provider);
}

// base_url is NOT a secret — persisted under a separate prefix and readable by
// QML (the masking rules apply only to the key).
QString CredentialStore::baseUrlFor(const QString &provider) const
{
    return m_settings.value(QStringLiteral("byobase/") + provider).toString();
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

void CredentialStore::saveCredential(const QString &provider, const QString &rawText, const QString &baseUrl)
{
    if (rawText.trimmed().isEmpty())
        return;
    m_credentials.insert(provider, rawText);
    // A blank base_url clears any stored custom endpoint (the server then falls
    // back to the provider's registry default). Non-blank values are trimmed.
    const QString trimmedBase = baseUrl.trimmed();
    if (trimmedBase.isEmpty())
        m_settings.remove(QStringLiteral("byobase/") + provider);
    else
        m_settings.setValue(QStringLiteral("byobase/") + provider, trimmedBase);
    emit credentialChanged(provider);
}

void CredentialStore::clearCredential(const QString &provider)
{
    m_credentials.remove(provider);
    m_settings.remove(QStringLiteral("byokey/") + provider);
    m_settings.remove(QStringLiteral("byobase/") + provider);
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

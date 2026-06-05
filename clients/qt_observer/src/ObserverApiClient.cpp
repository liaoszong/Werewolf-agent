#include "ObserverApiClient.h"
#include "ObserverSseParser.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>
#include <QUrlQuery>

ObserverApiClient::ObserverApiClient(QObject *parent)
    : QObject(parent)
    , m_connected(false)
    , m_currentPerspective(QStringLiteral("god"))
    , m_network(new QNetworkAccessManager(this))
    , m_streamReply(nullptr)
    , m_sseParser(new ObserverSseParser)
{
    m_baseUrl = QStringLiteral("http://127.0.0.1:8765");
}

ObserverApiClient::~ObserverApiClient()
{
    stopStream();
    delete m_sseParser;
}

QString ObserverApiClient::baseUrl() const { return m_baseUrl; }

void ObserverApiClient::setBaseUrl(const QString &url)
{
    if (m_baseUrl != url) {
        m_baseUrl = url;
        emit baseUrlChanged();
    }
}

bool ObserverApiClient::connected() const { return m_connected; }
QString ObserverApiClient::currentRunId() const { return m_currentRunId; }
QString ObserverApiClient::currentStatus() const { return m_currentStatus; }
QString ObserverApiClient::currentPerspective() const { return m_currentPerspective; }

void ObserverApiClient::setCurrentPerspective(const QString &perspective)
{
    if (m_currentPerspective != perspective) {
        m_currentPerspective = perspective;
        emit currentPerspectiveChanged();
        if (m_connected && !m_currentRunId.isEmpty()) {
            startStreamRequest();
            refreshProjection();
        }
    }
}

QVariantList ObserverApiClient::runItems() const { return m_runItems; }
QVariantList ObserverApiClient::eventItems() const { return m_eventItems; }
QVariantList ObserverApiClient::auditItems() const { return m_auditItems; }
QString ObserverApiClient::lastError() const { return m_lastError; }

// G2c projection getters
QVariantList ObserverApiClient::playerItems() const { return m_playerItems; }
QVariantMap ObserverApiClient::projectionProof() const { return m_projectionProof; }
int ObserverApiClient::hiddenEventCount() const { return m_hiddenEventCount; }
int ObserverApiClient::hiddenSnapshotCount() const { return m_hiddenSnapshotCount; }
QString ObserverApiClient::visibilityContractVersion() const { return m_visibilityContractVersion; }

// G2d-2 profile setup getters
QVariantList ObserverApiClient::profileItems() const { return m_profileItems; }
QVariantMap ObserverApiClient::profileSchema() const { return m_profileSchema; }
QVariantMap ObserverApiClient::loadedProfile() const { return m_loadedProfile; }
QVariantMap ObserverApiClient::profileValidation() const { return m_profileValidation; }

QNetworkReply *ObserverApiClient::get(const QString &path)
{
    QNetworkRequest req(QUrl(m_baseUrl + path));
    req.setRawHeader("Accept", "application/json");
    return m_network->get(req);
}

QNetworkReply *ObserverApiClient::post(const QString &path, const QByteArray &body)
{
    QNetworkRequest req(QUrl(m_baseUrl + path));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setRawHeader("Accept", "application/json");
    return m_network->post(req, body);
}

void ObserverApiClient::setError(const QString &msg)
{
    m_lastError = msg;
    emit lastErrorChanged();
}

void ObserverApiClient::checkHealth()
{
    QNetworkReply *reply = get(QStringLiteral("/health"));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            setError(reply->errorString());
            return;
        }
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) {
            setError(QStringLiteral("Invalid health response"));
            return;
        }
        QJsonObject obj = doc.object();
        bool ok = obj.value(QStringLiteral("status")).toString() == QStringLiteral("ok");
        if (m_connected != ok) {
            m_connected = ok;
            emit connectedChanged();
        }
    });
}

void ObserverApiClient::refreshRuns()
{
    QNetworkReply *reply = get(QStringLiteral("/api/runs"));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            setError(reply->errorString());
            return;
        }
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) {
            setError(QStringLiteral("Invalid runs response"));
            return;
        }
        QJsonArray runs = doc.object().value(QStringLiteral("runs")).toArray();
        QVariantList items;
        for (const QJsonValue &v : runs)
            items.append(v.toObject().toVariantMap());
        m_runItems = items;
        emit runItemsChanged();
    });
}

void ObserverApiClient::startDefaultMatch()
{
    QJsonObject body;
    body[QStringLiteral("template")] = QStringLiteral("default_6p_fake");
    body[QStringLiteral("mode")] = QStringLiteral("fake");

    QNetworkReply *reply = post(QStringLiteral("/api/runs"),
                                QJsonDocument(body).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            setError(reply->errorString());
            return;
        }
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) {
            setError(QStringLiteral("Invalid start response"));
            return;
        }
        QJsonObject obj = doc.object();
        QString runId = obj.value(QStringLiteral("run_id")).toString();
        QString status = obj.value(QStringLiteral("status")).toString();

        if (runId.isEmpty()) {
            setError(QStringLiteral("No run_id in response"));
            return;
        }

        m_currentRunId = runId;
        m_currentStatus = status;
        emit currentRunChanged();
        emit currentStatusChanged();
        refreshAuditLinks();
        refreshProjection();
        connectStream();
    });
}

void ObserverApiClient::openRun(const QString &runId)
{
    QNetworkReply *reply = get(QStringLiteral("/api/runs/") + runId);
    connect(reply, &QNetworkReply::finished, this, [this, runId, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            setError(reply->errorString());
            return;
        }
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) {
            setError(QStringLiteral("Invalid run detail response"));
            return;
        }
        QJsonObject obj = doc.object();
        m_currentRunId = runId;
        m_currentStatus = obj.value(QStringLiteral("status")).toString();
        emit currentRunChanged();
        emit currentStatusChanged();
        refreshAuditLinks();
        refreshProjection();

        QNetworkReply *eventsReply = get(
            QStringLiteral("/api/runs/") + runId + QStringLiteral("/events?perspective=") + m_currentPerspective);
        connect(eventsReply, &QNetworkReply::finished, this, [this, eventsReply]() {
            eventsReply->deleteLater();
            if (eventsReply->error() != QNetworkReply::NoError) {
                setError(eventsReply->errorString());
                return;
            }
            QJsonDocument doc = QJsonDocument::fromJson(eventsReply->readAll());
            if (!doc.isObject()) {
                setError(QStringLiteral("Invalid events response"));
                return;
            }
            QJsonArray events = doc.object().value(QStringLiteral("events")).toArray();
            QVariantList items;
            for (const QJsonValue &v : events)
                items.append(v.toObject().toVariantMap());
            m_eventItems = items;
            emit eventItemsChanged();
        });
    });
}

void ObserverApiClient::connectStream()
{
    if (m_currentRunId.isEmpty())
        return;
    startStreamRequest();
}

void ObserverApiClient::disconnectStream()
{
    stopStream();
}

void ObserverApiClient::startStreamRequest()
{
    stopStream();

    m_sseParser->reset();
    m_eventItems.clear();
    emit eventItemsChanged();

    QUrl url(m_baseUrl + QStringLiteral("/api/runs/") + m_currentRunId + QStringLiteral("/stream"));
    QUrlQuery query;
    query.addQueryItem(QStringLiteral("perspective"), m_currentPerspective);
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setRawHeader("Accept", "text/event-stream");

    m_streamReply = m_network->get(req);
    connect(m_streamReply, &QNetworkReply::readyRead, this, &ObserverApiClient::onStreamReadyRead);
    connect(m_streamReply, &QNetworkReply::finished, this, &ObserverApiClient::onStreamFinished);
    connect(m_streamReply, &QNetworkReply::errorOccurred, this, &ObserverApiClient::onStreamError);
}

void ObserverApiClient::stopStream()
{
    if (m_streamReply) {
        m_streamReply->abort();
        m_streamReply->deleteLater();
        m_streamReply = nullptr;
    }
    if (m_connected) {
        m_connected = false;
        emit connectedChanged();
    }
}

void ObserverApiClient::onStreamReadyRead()
{
    if (!m_streamReply)
        return;

    if (!m_connected) {
        m_connected = true;
        emit connectedChanged();
    }

    QByteArray chunk = m_streamReply->readAll();
    QList<ObserverSseMessage> messages = m_sseParser->feed(chunk);

    for (const ObserverSseMessage &msg : messages) {
        if (msg.eventName == QStringLiteral("run_status")) {
            QString status = msg.data.value(QStringLiteral("status")).toString();
            if (!status.isEmpty() && m_currentStatus != status) {
                m_currentStatus = status;
                emit currentStatusChanged();
            }
        }

        QVariantMap item = msg.data.toVariantMap();
        item[QStringLiteral("_eventType")] = msg.eventName;
        m_eventItems.append(item);
    }

    if (!messages.isEmpty())
        emit eventItemsChanged();
}

void ObserverApiClient::onStreamFinished()
{
    if (m_streamReply) {
        m_streamReply->deleteLater();
        m_streamReply = nullptr;
    }
    m_connected = false;
    emit connectedChanged();
}

void ObserverApiClient::onStreamError(QNetworkReply::NetworkError error)
{
    Q_UNUSED(error)
    if (m_streamReply) {
        setError(m_streamReply->errorString());
        m_streamReply->deleteLater();
        m_streamReply = nullptr;
    }
    m_connected = false;
    emit connectedChanged();
}

void ObserverApiClient::refreshAuditLinks()
{
    if (m_currentRunId.isEmpty())
        return;

    QStringList aliases = {
        QStringLiteral("/manifest"),
        QStringLiteral("/provider-trace"),
        QStringLiteral("/failure-audit"),
        QStringLiteral("/snapshots?perspective=") + m_currentPerspective,
        QStringLiteral("/projection?perspective=") + m_currentPerspective,
        QStringLiteral("/artifacts"),
    };

    QVariantList auditList;

    for (const QString &alias : aliases) {
        QString path = QStringLiteral("/api/runs/") + m_currentRunId + alias;
        QUrl url(m_baseUrl + path);
        QVariantMap item;
        item[QStringLiteral("url")] = url.toString();
        item[QStringLiteral("path")] = path;
        auditList.append(item);
    }

    m_auditItems = auditList;
    emit auditItemsChanged();
}

void ObserverApiClient::refreshProjection()
{
    if (m_currentRunId.isEmpty())
        return;

    const quint64 requestSerial = ++m_projectionRequestSerial;
    const QString requestedRunId = m_currentRunId;
    const QString requestedPerspective = m_currentPerspective;

    QUrl url(m_baseUrl + QStringLiteral("/api/runs/") + requestedRunId + QStringLiteral("/projection"));
    QUrlQuery query;
    query.addQueryItem(QStringLiteral("perspective"), requestedPerspective);
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setRawHeader("Accept", "application/json");
    QNetworkReply *reply = m_network->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply, requestSerial, requestedRunId, requestedPerspective]() {
        reply->deleteLater();
        if (requestSerial != m_projectionRequestSerial || requestedRunId != m_currentRunId || requestedPerspective != m_currentPerspective)
            return;
        if (reply->error() != QNetworkReply::NoError) {
            setError(reply->errorString());
            return;
        }
        QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (!doc.isObject()) {
            setError(QStringLiteral("Invalid projection response"));
            return;
        }
        QJsonObject obj = doc.object();
        m_visibilityContractVersion = obj.value(QStringLiteral("contract_version")).toString();
        m_hiddenEventCount = obj.value(QStringLiteral("hidden_event_count")).toInt();
        m_hiddenSnapshotCount = obj.value(QStringLiteral("hidden_snapshot_count")).toInt();

        QVariantList players;
        for (const QJsonValue &v : obj.value(QStringLiteral("players")).toArray())
            players.append(v.toObject().toVariantMap());
        m_playerItems = players;
        m_projectionProof = obj.value(QStringLiteral("proof")).toObject().toVariantMap();

        emit playerItemsChanged();
        emit projectionProofChanged();
        emit projectionChanged();
    });
}

// ---------------------------------------------------------------------------
// G2d-2 profile setup methods
// ---------------------------------------------------------------------------

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
    const QString encoded = QString::fromUtf8(QUrl::toPercentEncoding(name));
    QNetworkReply *reply = get(QStringLiteral("/api/profiles/") + encoded);
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
    const quint64 serial = ++m_profileValidateSerial;   // latest-wins
    QJsonObject body = QJsonObject::fromVariantMap(profile);
    QNetworkReply *reply = post(QStringLiteral("/api/profiles/validate"),
                                QJsonDocument(body).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply, serial]() {
        reply->deleteLater();
        if (serial != m_profileValidateSerial) return;  // a newer validate superseded this
        if (reply->error() != QNetworkReply::NoError) { setError(reply->errorString()); return; }
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
        // Explicit network-error path first (httpStatus may be 0 on transport error).
        if (reply->error() != QNetworkReply::NoError) {
            // 4xx bodies still carry a JSON {code,message}; surface that if present.
            const QJsonDocument edoc = QJsonDocument::fromJson(reply->readAll());
            const QString emsg = edoc.isObject()
                ? edoc.object().value(QStringLiteral("message")).toString() : QString();
            setError(emsg.isEmpty() ? reply->errorString() : emsg);
            emit launchFailed();
            return;
        }
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

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
        if (m_connected && !m_currentRunId.isEmpty())
            startStreamRequest();
    }
}

QVariantList ObserverApiClient::runItems() const { return m_runItems; }
QVariantList ObserverApiClient::eventItems() const { return m_eventItems; }
QVariantList ObserverApiClient::auditItems() const { return m_auditItems; }
QString ObserverApiClient::lastError() const { return m_lastError; }

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

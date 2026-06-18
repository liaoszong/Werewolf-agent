#include "ObserverApiClient.h"

#include <QByteArray>
#include <QHash>
#include <QHostAddress>
#include <QObject>
#include <QSignalSpy>
#include <QString>
#include <QStringList>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTest>
#include <QVariantList>
#include <QVariantMap>

class ReplaySseServer : public QObject {
    Q_OBJECT
public:
    explicit ReplaySseServer(QObject *parent = nullptr)
        : QObject(parent)
    {
        connect(&m_server, &QTcpServer::newConnection, this, &ReplaySseServer::acceptConnection);
    }

    bool listen()
    {
        return m_server.listen(QHostAddress::LocalHost, 0);
    }

    QString baseUrl() const
    {
        return QStringLiteral("http://127.0.0.1:%1").arg(m_server.serverPort());
    }

    int streamRequests() const { return m_streamRequests; }

private:
    void acceptConnection()
    {
        while (QTcpSocket *socket = m_server.nextPendingConnection()) {
            m_buffers.insert(socket, QByteArray());
            connect(socket, &QTcpSocket::readyRead, this, [this, socket]() { readRequest(socket); });
            connect(socket, &QObject::destroyed, this, [this, socket]() { m_buffers.remove(socket); });
        }
    }

    void readRequest(QTcpSocket *socket)
    {
        QByteArray buffer = m_buffers.value(socket);
        buffer.append(socket->readAll());
        m_buffers[socket] = buffer;
        if (!buffer.contains("\r\n\r\n"))
            return;

        const QByteArray firstLine = buffer.left(buffer.indexOf("\r\n"));
        const QList<QByteArray> parts = firstLine.split(' ');
        const QString path = parts.size() >= 2 ? QString::fromUtf8(parts[1]) : QString();
        m_buffers.remove(socket);

        if (path == QStringLiteral("/api/runs/run1")) {
            writeJson(socket, QByteArrayLiteral("{\"run_id\":\"run1\",\"status\":\"running\",\"execution_mode\":\"fake\"}"));
        } else if (path.startsWith(QStringLiteral("/api/runs/run1/events"))) {
            writeJson(socket, QByteArrayLiteral("{\"events\":[]}"));
        } else if (path.startsWith(QStringLiteral("/api/runs/run1/projection"))) {
            writeJson(socket, QByteArrayLiteral("{\"contract_version\":\"test\",\"hidden_event_count\":0,\"hidden_snapshot_count\":0,\"players\":[],\"proof\":{},\"events\":[]}"));
        } else if (path.startsWith(QStringLiteral("/api/runs/run1/stream"))) {
            writeStream(socket);
        } else {
            writeResponse(socket, QByteArrayLiteral("404 Not Found"), QByteArrayLiteral("application/json"), QByteArrayLiteral("{}"));
        }
    }

    static QByteArray runtimeEvent(const char *eventId)
    {
        return QByteArrayLiteral("event: runtime_event\n")
            + "data: {\"kind\":\"phase_started\",\"visibility\":\"public\",\"payload\":{\"event_id\":\""
            + eventId
            + "\"}}\n\n";
    }

    static QByteArray runStatus()
    {
        return QByteArrayLiteral("event: run_status\n"
                                 "data: {\"run_id\":\"run1\",\"status\":\"running\"}\n\n");
    }

    void writeStream(QTcpSocket *socket)
    {
        ++m_streamRequests;
        QByteArray body = runStatus() + runtimeEvent("e1") + runtimeEvent("e2");
        if (m_streamRequests >= 3)
            body += runtimeEvent("e3");
        writeResponse(socket, QByteArrayLiteral("200 OK"), QByteArrayLiteral("text/event-stream"), body);
    }

    static void writeJson(QTcpSocket *socket, const QByteArray &body)
    {
        writeResponse(socket, QByteArrayLiteral("200 OK"), QByteArrayLiteral("application/json"), body);
    }

    static void writeResponse(QTcpSocket *socket, const QByteArray &status, const QByteArray &contentType, const QByteArray &body)
    {
        QByteArray response = "HTTP/1.1 " + status + "\r\n"
            + "Content-Type: " + contentType + "\r\n"
            + "Content-Length: " + QByteArray::number(body.size()) + "\r\n"
            + "Connection: close\r\n\r\n"
            + body;
        socket->write(response);
        socket->flush();
        socket->disconnectFromHost();
    }

    QTcpServer m_server;
    QHash<QTcpSocket *, QByteArray> m_buffers;
    int m_streamRequests = 0;
};

class ObserverApiClientTests : public QObject {
    Q_OBJECT
private slots:
    void reconnectReplayDoesNotDuplicateEventItems();
};

static QStringList eventIds(const QVariantList &items)
{
    QStringList ids;
    for (const QVariant &itemValue : items) {
        const QVariantMap item = itemValue.toMap();
        QString id = item.value(QStringLiteral("event_id")).toString();
        if (id.isEmpty())
            id = item.value(QStringLiteral("payload")).toMap().value(QStringLiteral("event_id")).toString();
        if (!id.isEmpty())
            ids.append(id);
    }
    return ids;
}

void ObserverApiClientTests::reconnectReplayDoesNotDuplicateEventItems()
{
    ReplaySseServer server;
    QVERIFY(server.listen());

    ObserverApiClient client;
    client.setBaseUrl(server.baseUrl());
    QSignalSpy eventItemsChanged(&client, &ObserverApiClient::eventItemsChanged);

    client.openRun(QStringLiteral("run1"), false);
    QTRY_COMPARE_WITH_TIMEOUT(client.currentRunId(), QStringLiteral("run1"), 1000);
    QTRY_COMPARE_WITH_TIMEOUT(client.currentStatus(), QStringLiteral("running"), 1000);

    client.connectStream();
    QTRY_COMPARE_WITH_TIMEOUT(eventIds(client.eventItems()), QStringList({QStringLiteral("e1"), QStringLiteral("e2")}), 1500);
    const int signalsAfterFirstStream = eventItemsChanged.count();

    QTRY_VERIFY_WITH_TIMEOUT(server.streamRequests() >= 2, 2500);
    QTest::qWait(200);
    QCOMPARE(eventIds(client.eventItems()), QStringList({QStringLiteral("e1"), QStringLiteral("e2")}));
    QCOMPARE(eventItemsChanged.count(), signalsAfterFirstStream);

    QTRY_COMPARE_WITH_TIMEOUT(eventIds(client.eventItems()), QStringList({QStringLiteral("e1"), QStringLiteral("e2"), QStringLiteral("e3")}), 2500);
    QCOMPARE(eventItemsChanged.count(), signalsAfterFirstStream + 1);

    client.disconnectStream();
    const int streamsAfterDisconnect = server.streamRequests();
    QTest::qWait(1300);
    QCOMPARE(server.streamRequests(), streamsAfterDisconnect);
}

QTEST_MAIN(ObserverApiClientTests)
#include "tst_observer_api_client.moc"

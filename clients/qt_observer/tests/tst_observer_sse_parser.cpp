#include "ObserverSseParser.h"

#include <QByteArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QList>
#include <QObject>
#include <QString>
#include <QTest>

class ObserverSseParserTests : public QObject {
    Q_OBJECT
private slots:
    void parsesRuntimeEventFrame();
    void parsesRunStatusFrame();
    void buffersIncompleteFrameAcrossChunks();
    void ignoresUnknownLinesWithoutCrashing();
    void ignoresMultilineDataFramesInMvp();
};

void ObserverSseParserTests::parsesRuntimeEventFrame()
{
    ObserverSseParser parser;
    QByteArray frame =
        "event: runtime_event\n"
        "data: {\"kind\":\"game_started\",\"visibility\":\"public\"}\n"
        "\n";

    QList<ObserverSseMessage> msgs = parser.feed(frame);
    QCOMPARE(msgs.size(), 1);
    QCOMPARE(msgs[0].eventName, QStringLiteral("runtime_event"));
    QCOMPARE(msgs[0].data.value(QStringLiteral("kind")).toString(), QStringLiteral("game_started"));
    QCOMPARE(msgs[0].data.value(QStringLiteral("visibility")).toString(), QStringLiteral("public"));
}

void ObserverSseParserTests::parsesRunStatusFrame()
{
    ObserverSseParser parser;
    QByteArray frame =
        "event: run_status\n"
        "data: {\"run_id\":\"my_run\",\"status\":\"completed\"}\n"
        "\n";

    QList<ObserverSseMessage> msgs = parser.feed(frame);
    QCOMPARE(msgs.size(), 1);
    QCOMPARE(msgs[0].eventName, QStringLiteral("run_status"));
    QCOMPARE(msgs[0].data.value(QStringLiteral("run_id")).toString(), QStringLiteral("my_run"));
    QCOMPARE(msgs[0].data.value(QStringLiteral("status")).toString(), QStringLiteral("completed"));
}

void ObserverSseParserTests::buffersIncompleteFrameAcrossChunks()
{
    ObserverSseParser parser;

    QByteArray chunk1 = "event: run_status\ndata: {\"run_id\":\"abc\",";
    QList<ObserverSseMessage> msgs1 = parser.feed(chunk1);
    QVERIFY(msgs1.isEmpty());

    QByteArray chunk2 = "\"status\":\"running\"}\n\n";
    QList<ObserverSseMessage> msgs2 = parser.feed(chunk2);
    QCOMPARE(msgs2.size(), 1);
    QCOMPARE(msgs2[0].eventName, QStringLiteral("run_status"));
    QCOMPARE(msgs2[0].data.value(QStringLiteral("run_id")).toString(), QStringLiteral("abc"));
    QCOMPARE(msgs2[0].data.value(QStringLiteral("status")).toString(), QStringLiteral("running"));
}

void ObserverSseParserTests::ignoresUnknownLinesWithoutCrashing()
{
    ObserverSseParser parser;
    QByteArray frame =
        "id: 42\n"
        "event: runtime_event\n"
        "retry: 3000\n"
        "data: {\"kind\":\"round_started\",\"round\":1}\n"
        ": this is a comment\n"
        "\n";

    QList<ObserverSseMessage> msgs = parser.feed(frame);
    QCOMPARE(msgs.size(), 1);
    QCOMPARE(msgs[0].eventName, QStringLiteral("runtime_event"));
    QCOMPARE(msgs[0].data.value(QStringLiteral("kind")).toString(), QStringLiteral("round_started"));
    QCOMPARE(msgs[0].data.value(QStringLiteral("round")).toInt(), 1);
}

void ObserverSseParserTests::ignoresMultilineDataFramesInMvp()
{
    ObserverSseParser parser;
    QByteArray frame =
        "event: runtime_event\n"
        "data: {\"kind\":\"phase_started\",\"phase\":\"night\"}\n"
        "data: {\"extra\":\"ignored\"}\n"
        "\n";

    QList<ObserverSseMessage> msgs = parser.feed(frame);
    QCOMPARE(msgs.size(), 1);
    QCOMPARE(msgs[0].eventName, QStringLiteral("runtime_event"));
    QCOMPARE(msgs[0].data.value(QStringLiteral("kind")).toString(), QStringLiteral("phase_started"));
    QCOMPARE(msgs[0].data.value(QStringLiteral("phase")).toString(), QStringLiteral("night"));
    QVERIFY(!msgs[0].data.contains(QStringLiteral("extra")));
}

QTEST_MAIN(ObserverSseParserTests)
#include "tst_observer_sse_parser.moc"

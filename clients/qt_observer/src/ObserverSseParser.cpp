#include "ObserverSseParser.h"

#include <QByteArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QList>
#include <QString>

QList<ObserverSseMessage> ObserverSseParser::feed(const QByteArray &chunk)
{
    QList<ObserverSseMessage> messages;
    m_buffer.append(chunk);

    while (true) {
        int idx = m_buffer.indexOf("\n\n");
        if (idx < 0)
            break;

        QByteArray frameBytes = m_buffer.left(idx);
        m_buffer.remove(0, idx + 2);

        if (frameBytes.isEmpty())
            continue;

        QString eventName;
        QString dataLine;

        QList<QByteArray> lines = frameBytes.split('\n');
        for (const QByteArray &line : lines) {
            QString lineStr = QString::fromUtf8(line);
            if (lineStr.startsWith(QStringLiteral("event: "))) {
                eventName = lineStr.mid(7).trimmed();
            } else if (lineStr.startsWith(QStringLiteral("data: "))) {
                if (dataLine.isEmpty()) {
                    dataLine = lineStr.mid(6).trimmed();
                }
            }
        }

        if (eventName.isEmpty() || dataLine.isEmpty())
            continue;

        if (eventName != QStringLiteral("runtime_event") && eventName != QStringLiteral("run_status"))
            continue;

        QJsonParseError parseError;
        QJsonDocument doc = QJsonDocument::fromJson(dataLine.toUtf8(), &parseError);
        if (parseError.error != QJsonParseError::NoError || !doc.isObject())
            continue;

        ObserverSseMessage msg;
        msg.eventName = eventName;
        msg.data = doc.object();
        messages.append(msg);
    }

    return messages;
}

void ObserverSseParser::reset()
{
    m_buffer.clear();
}

#pragma once

#include <QByteArray>
#include <QJsonObject>
#include <QList>
#include <QString>

struct ObserverSseMessage {
    QString eventName;
    QJsonObject data;
};

class ObserverSseParser {
public:
    QList<ObserverSseMessage> feed(const QByteArray &chunk);
    void reset();

private:
    QByteArray m_buffer;
};

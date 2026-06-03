#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlEngine>
#include "ObserverApiClient.h"

static QString observerBaseUrlFromArgs(const QStringList &args)
{
    const int index = args.indexOf("--observer-base-url");
    if (index >= 0 && index + 1 < args.size()) {
        return args.at(index + 1);
    }
    return QStringLiteral("http://127.0.0.1:8765");
}

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);

    ObserverApiClient observerClient;
    observerClient.setBaseUrl(observerBaseUrlFromArgs(app.arguments()));
    qmlRegisterSingletonInstance("qt_observer", 1, 0, "ObserverClient", &observerClient);

    QQmlApplicationEngine engine;
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, []() { QCoreApplication::exit(-1); }, Qt::QueuedConnection);
    engine.loadFromModule("qt_observer", "Main");

    return app.exec();
}

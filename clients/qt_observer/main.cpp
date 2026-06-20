#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlEngine>
#include <QQuickStyle>
#include <QTextStream>
#include "ObserverApiClient.h"
#include "CredentialStore.h"

static QString observerBaseUrlFromArgs(const QStringList &args)
{
    const int index = args.indexOf("--observer-base-url");
    if (index >= 0 && index + 1 < args.size()) {
        return args.at(index + 1);
    }
    return QStringLiteral("http://127.0.0.1:8765");
}

static QString openRunFromArgs(const QStringList &args)
{
    const int index = args.indexOf("--open-run");
    if (index >= 0 && index + 1 < args.size()) {
        return args.at(index + 1);
    }
    return QString();
}

static QString releaseVersionFromArgs(const QStringList &args)
{
    const int index = args.indexOf("--release-version");
    if (index >= 0 && index + 1 < args.size())
        return args.at(index + 1);
    return QString();
}

static QString hostSessionFromArgs(const QStringList &args)
{
    const int index = args.indexOf("--release-host-session");
    if (index >= 0 && index + 1 < args.size())
        return args.at(index + 1);
    return QString();
}

static QString updateRequestPathFromArgs(const QStringList &args)
{
    const int index = args.indexOf("--update-request-path");
    if (index >= 0 && index + 1 < args.size())
        return args.at(index + 1);
    return QString();
}

static bool versionFlagFromArgs(const QStringList &args)
{
    return args.contains("--version");
}

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);

    // Use the fully customizable Basic style so the dark theme controls render
    // identically across platforms (native styles ignore custom backgrounds).
    QQuickStyle::setStyle(QStringLiteral("Basic"));

    ObserverApiClient observerClient;
    observerClient.setBaseUrl(observerBaseUrlFromArgs(app.arguments()));
    observerClient.setInitialRunId(openRunFromArgs(app.arguments()));
    observerClient.setReleaseVersion(releaseVersionFromArgs(app.arguments()));
    observerClient.setHostSessionId(hostSessionFromArgs(app.arguments()));
    observerClient.setUpdateRequestPath(updateRequestPathFromArgs(app.arguments()));

    if (versionFlagFromArgs(app.arguments())) {
        QString ver = releaseVersionFromArgs(app.arguments());
        if (ver.isEmpty()) ver = QStringLiteral("0.2.0");
        QTextStream(stdout) << "Werewolf-agent " << ver << "\n";
        return 0;
    }

    qmlRegisterSingletonInstance("qt_observer", 1, 0, "ObserverClient", &observerClient);

    CredentialStore credentialStore;
    credentialStore.setBaseUrl(observerBaseUrlFromArgs(app.arguments()));
    qmlRegisterSingletonInstance("qt_observer", 1, 0, "CredentialStore", &credentialStore);

    QQmlApplicationEngine engine;
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, []() { QCoreApplication::exit(-1); }, Qt::QueuedConnection);
    engine.loadFromModule("qt_observer", "Main");

    return app.exec();
}

// SPDX-License-Identifier: Apache-2.0
#include <QFile>
#include <QGuiApplication>
#include <QJsonDocument>
#include <QQmlApplicationEngine>
#include <QQmlContext>

int main(int argc, char* argv[]) {
    QGuiApplication app(argc, argv);
    app.setApplicationName("FreeFlight");
    app.setOrganizationName("Dockpipe Industries Inc.");
    QFile content(":/content.json");
    if (!content.open(QIODevice::ReadOnly)) return 1;
    QJsonParseError error;
    const auto pages = QJsonDocument::fromJson(content.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !pages.isArray()) return 1;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("sitePages", pages.toVariant());
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, [] { QCoreApplication::exit(1); }, Qt::QueuedConnection);
    engine.loadFromModule("FreeFlight.Site", "Main");
    return app.exec();
}

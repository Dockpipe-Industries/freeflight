// SPDX-License-Identifier: Apache-2.0
#include "site-config.h"
#include <QFile>
#include <QFontDatabase>
#include <QGuiApplication>
#include <QJsonDocument>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
class SiteBridge : public QObject {
    Q_OBJECT
public:
    Q_INVOKABLE int themeMode() const {
#ifdef __EMSCRIPTEN__
        return EM_ASM_INT({try {return "system light dark".split(" ").indexOf(localStorage.getItem('freeflight-theme') || 'system');}catch{return 0;}});
#else
        return 0;
#endif
    }
    Q_INVOKABLE bool systemDark() const {
#ifdef __EMSCRIPTEN__
        return EM_ASM_INT({return matchMedia('(prefers-color-scheme: dark)').matches;});
#else
        return false;
#endif
    }
    Q_INVOKABLE void setTheme(int mode) {
#ifdef __EMSCRIPTEN__
        EM_ASM({window.freeflightTheme?.("system light dark".split(" ")[$0]);}, mode);
#endif
    }
    Q_INVOKABLE void documents(const QString& id = QStringLiteral("README.md")) {
#ifdef __EMSCRIPTEN__
        const auto value = id.toUtf8();
        EM_ASM({window.freeflightDocs?.open(UTF8ToString($0));}, value.constData());
#endif
    }
};
int main(int argc, char* argv[]) {
    QGuiApplication app(argc, argv);
    const auto fontId = QFontDatabase::addApplicationFont(":/fonts/InterVariable.ttf");
    const auto families = QFontDatabase::applicationFontFamilies(fontId);
    if (!families.isEmpty()) {
        app.setFont(QFont(families.first()));
    }
    QFontDatabase::addApplicationFont(":/fonts/DejaVuSansMono.ttf");
    QQuickStyle::setStyle("Basic");
    app.setApplicationName("FreeFlight");
    app.setOrganizationName("Dockpipe Industries Inc.");
    QFile content(":/content.json");
    if (!content.open(QIODevice::ReadOnly)) return 1;
    QJsonParseError error;
    const auto pages = QJsonDocument::fromJson(content.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !pages.isArray()) return 1;
    QQmlApplicationEngine engine;
    SiteBridge bridge;
    engine.rootContext()->setContextProperty("siteBridge", &bridge);
    engine.rootContext()->setContextProperty("sitePages", pages.toVariant());
    engine.rootContext()->setContextProperty("companyUrl", QStringLiteral(FREEFLIGHT_COMPANY_URL));
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, [] { QCoreApplication::exit(1); }, Qt::QueuedConnection);
    engine.loadFromModule("FreeFlight.Site", "Main");
    return app.exec();
}
#include "main.moc"

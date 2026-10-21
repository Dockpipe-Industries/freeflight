// SPDX-License-Identifier: Apache-2.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true; width: 1280; height: 900
    title: "FreeFlight — Code intelligence. No subscriptions. No nonsense."
    property int selectedPage: 0
    property int themeMode: Math.max(0, siteBridge.themeMode())
    readonly property bool dark: themeMode === 2 || (themeMode === 0 && siteBridge.systemDark())
    readonly property bool compact: width < 760
    readonly property color ink: dark ? "#edf4ff" : "#152c49"
    readonly property color bodyInk: dark ? "#afc2dc" : "#47617e"
    readonly property color accent: dark ? "#9cc7ff" : "#195cb5"
    readonly property color surface: dark ? "#14263d" : "#ffffff"
    readonly property color line: dark ? "#30445f" : "#d2dfed"
    color: dark ? "#0c1b2e" : "#f1f7fd"
    font.family: "sans-serif"; font.pixelSize: 14
    palette.windowText: ink; palette.text: ink; palette.buttonText: ink
    palette.button: surface; palette.base: surface; palette.highlight: accent
    palette.highlightedText: dark ? "#0c1b2e" : "#ffffff"
    onThemeModeChanged: siteBridge.setTheme(themeMode)

    component Action: Button {
        property bool primary: false
        implicitHeight: 44
        leftPadding: 18; rightPadding: 18
        contentItem: Text { text: parent.text; color: parent.primary ? "#ffffff" : window.ink; font.pixelSize: 14; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { radius: 7; color: parent.primary ? (parent.down ? "#174c96" : "#2165c5") : (parent.hovered ? window.surface : "transparent"); border.width: parent.primary ? 0 : 1; border.color: parent.activeFocus ? window.accent : window.line }
    }
    function navigate(index) {
        if (index === 2) { siteBridge.documents(); return }
        if (index === 3) { siteBridge.documents("docs/capabilities.md"); return }
        if (index === 4) { siteBridge.documents("docs/README.md"); return }
        if (index === 5) { siteBridge.documents("docs/development.md"); return }
        selectedPage = index; contentScroll.contentItem.contentY = 0
    }
    header: Rectangle {
        height: window.compact ? 136 : 88; color: window.color
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: window.line }
        ColumnLayout {
            width: Math.min(1180, parent.width - (window.compact ? 36 : 96))
            anchors.centerIn: parent; spacing: 12
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                Rectangle { width: 34; height: 34; radius: 9; color: "#2165c5"; Text { anchors.centerIn: parent; text: "↗"; color: "white"; font.pixelSize: 28 } }
                Label { text: "FreeFlight"; color: window.ink; font.pixelSize: 24; font.weight: Font.DemiBold }
                Item { Layout.fillWidth: true }
                RowLayout {
                    visible: !window.compact; spacing: 4
                    Repeater { model: ["Overview", "Install", "Docs", "Languages"]
                        Button { required property string modelData; required property int index; text: modelData; flat: true; background: Rectangle { radius: 6; color: window.selectedPage === parent.index ? window.surface : "transparent"; border.width: window.selectedPage === parent.index ? 1 : 0; border.color: window.line } onClicked: window.navigate(index) }
                    }
                }
                ComboBox { id: theme; Accessible.name: "Color theme"; model: ["System", "Light", "Dark"]; currentIndex: window.themeMode; onActivated: window.themeMode = currentIndex; implicitWidth: 100; implicitHeight: 38 }
            }
            RowLayout {
                visible: window.compact; Layout.fillWidth: true; spacing: 0
                Repeater { model: ["Overview", "Install", "Docs", "Languages"]
                    Button { required property string modelData; required property int index; Layout.fillWidth: true; text: modelData; font.pixelSize: 12; leftPadding: 4; rightPadding: 4; flat: true; onClicked: window.navigate(index) }
                }
            }
        }
    }
    ScrollView {
        id: contentScroll; anchors.fill: parent; clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: Math.min(1180, contentScroll.availableWidth - (window.compact ? 40 : 96)); x: (contentScroll.availableWidth - width) / 2; spacing: 0
            Item { Layout.preferredHeight: window.compact ? 36 : 64 }
            ColumnLayout {
                visible: window.selectedPage === 0; Layout.fillWidth: true; spacing: 0
                GridLayout {
                    Layout.fillWidth: true; columns: window.width < 1050 ? 1 : 2; columnSpacing: 54; rowSpacing: 34
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.preferredWidth: 600; spacing: 22
                        Label { text: "LOCAL CODE INTELLIGENCE"; color: window.accent; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 1.6 }
                        Label { Layout.fillWidth: true; text: "Code intelligence.\nNo subscriptions.\nNo nonsense."; color: window.ink; font.pixelSize: window.compact ? 40 : 57; font.weight: Font.DemiBold; font.letterSpacing: -2; lineHeight: 1.06; wrapMode: Text.WordWrap }
                        Label { Layout.fillWidth: true; Layout.maximumWidth: 500; text: "Give your AI tools a semantic view of your code. One local MCP server brings C#, TypeScript and JavaScript into your workflow."; color: window.bodyInk; font.pixelSize: 17; lineHeight: 1.4; wrapMode: Text.WordWrap }
                        Flow { Layout.fillWidth: true; spacing: 10
                            Action { text: "Get FreeFlight  →"; primary: true; onClicked: window.navigate(1) }
                            Action { text: "Read the docs"; onClicked: siteBridge.documents() }
                        }
                        Label { Layout.fillWidth: true; text: "Open source · Apache-2.0 · Developer preview"; color: window.bodyInk; font.pixelSize: 12; wrapMode: Text.WordWrap }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredWidth: 460; implicitHeight: 350; radius: 12; color: "#101e32"; border.color: "#354c6b"
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 24; spacing: 16
                            RowLayout { Layout.fillWidth: true; Label { text: "YOUR MCP WORKFLOW"; color: "#a6bcdc"; font.pixelSize: 10; font.letterSpacing: 1.5 } Item { Layout.fillWidth: true } Label { text: "●  ●  ●"; color: "#6483ac"; font.pixelSize: 10 } }
                            Rectangle { Layout.fillWidth: true; height: 1; color: "#354c6b" }
                            Label { text: "01  Ask about your code"; color: "#9cc7ff"; font.pixelSize: 13 }
                            Label { Layout.fillWidth: true; text: '“Where is this symbol defined?”'; color: "#edf4ff"; font.pixelSize: 18; wrapMode: Text.WordWrap }
                            Label { text: "02  Resolve with language services"; color: "#9cc7ff"; font.pixelSize: 13 }
                            Label { Layout.fillWidth: true; text: "MCP client → FreeFlight\n                         Roslyn / TypeScript"; color: "#c0d0e6"; font.family: "monospace"; font.pixelSize: 13; lineHeight: 1.6; wrapMode: Text.WordWrap }
                            Label { text: "03  Get structured results"; color: "#9cc7ff"; font.pixelSize: 13 }
                            Label { Layout.fillWidth: true; text: "Definitions · References · Diagnostics\nEdit previews — your files stay yours."; color: "#c0d0e6"; font.pixelSize: 13; lineHeight: 1.5; wrapMode: Text.WordWrap }
                        }
                    }
                }
                Item { Layout.preferredHeight: window.compact ? 40 : 60 }
                Rectangle { Layout.fillWidth: true; height: 1; color: window.line }
                GridLayout {
                    Layout.fillWidth: true; Layout.topMargin: 28; Layout.bottomMargin: 32; columns: window.compact ? 1 : 3; columnSpacing: 38; rowSpacing: 28
                    Repeater { model: [
                        {number:"01",title:"One local connection",body:"A native C++23 server coordinates the language workers behind a single stdio MCP endpoint."},
                        {number:"02",title:"Semantics, not guesswork",body:"Established Roslyn and TypeScript services provide navigation and diagnostics. See the documented scope for each language."},
                        {number:"03",title:"Control stays with you",body:"Workspace access is explicit. Refactoring returns previews; FreeFlight does not write changes to your source files."}]
                        ColumnLayout { required property var modelData; Layout.fillWidth: true; Layout.preferredWidth: 330; Layout.alignment: Qt.AlignTop; spacing: 10
                            Label { text: modelData.number; color: window.accent; font.family: "monospace"; font.pixelSize: 12 }
                            Label { Layout.fillWidth: true; text: modelData.title; color: window.ink; font.pixelSize: 17; font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
                            Label { Layout.fillWidth: true; text: modelData.body; color: window.bodyInk; font.pixelSize: 14; lineHeight: 1.45; wrapMode: Text.WordWrap }
                        }
                    }
                }
            }
            ColumnLayout {
                visible: window.selectedPage === 1; Layout.fillWidth: true; spacing: 24
                Label { text: "INSTALL FREEFLIGHT"; color: window.accent; font.pixelSize: 11; font.letterSpacing: 1.5 }
                Label { Layout.fillWidth: true; text: "Your tools. Your workflow."; color: window.ink; font.pixelSize: window.compact ? 36 : 50; font.letterSpacing: -1.5; wrapMode: Text.WordWrap }
                Label { Layout.fillWidth: true; Layout.maximumWidth: 700; text: "Download a complete native bundle, verify its checksum, and connect your MCP client. The language workers are included."; color: window.bodyInk; font.pixelSize: 17; lineHeight: 1.4; wrapMode: Text.WordWrap }
                GridLayout {
                    Layout.fillWidth: true; columns: window.compact ? 1 : 3; columnSpacing: 18; rowSpacing: 16
                    Repeater { model: [{name:"Linux", detail:"x64 and ARM64"},{name:"macOS",detail:"Apple silicon / ARM64"},{name:"Windows",detail:"x64"}]
                        Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredWidth: 330; implicitHeight: 160; radius: 10; color: window.surface; border.color: window.line
                            ColumnLayout { anchors.fill: parent; anchors.margins: 24; spacing: 12
                                Label { text: modelData.name; color: window.ink; font.pixelSize: 22; font.weight: Font.DemiBold }
                                Label { text: modelData.detail; color: window.bodyInk; font.pixelSize: 14 }
                                Label { text: "Native archive + MCPB"; color: window.accent; font.pixelSize: 12 }
                            }
                        }
                    }
                }
                Flow { Layout.fillWidth: true; spacing: 12
                    Action { text: "Browse release downloads  ↗"; primary: true; onClicked: Qt.openUrlExternally("https://github.com/Dockpipe-Industries/freeflight/releases") }
                    Action { text: "Installation and platform guide"; onClicked: siteBridge.documents("docs/distribution.md") }
                }
                Label { Layout.fillWidth: true; Layout.maximumWidth: 850; text: "Developer preview. Match the artifact to your platform and read its qualification notes. Code signing and notarization are not currently provided."; color: window.bodyInk; font.pixelSize: 13; lineHeight: 1.5; wrapMode: Text.WordWrap }
                Rectangle { Layout.fillWidth: true; height: 1; color: window.line }
                Label { text: "Connect once. Choose your workspace."; color: window.ink; font.pixelSize: 24; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Label { Layout.fillWidth: true; Layout.maximumWidth: 850; text: "The client launches the native server over stdio. Configure only the roots you intend to expose. Trusted C# project loading can execute repository build logic and requires a compatible installed SDK; read the trust guide before enabling it."; color: window.bodyInk; font.pixelSize: 16; lineHeight: 1.5; wrapMode: Text.WordWrap }
                Action { text: "Read the configuration guide  →"; onClicked: siteBridge.documents("docs/README.md") }
                Item { Layout.preferredHeight: 28 }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: window.line }
            Flow {
                Layout.fillWidth: true; Layout.topMargin: 22; Layout.bottomMargin: 28; spacing: 18
                Label { text: "A project by Dockpipe Industries Inc."; color: window.bodyInk; font.pixelSize: 12; height: 36; verticalAlignment: Text.AlignVCenter }
                Button { text: "Company ↗"; flat: true; onClicked: Qt.openUrlExternally(companyUrl) }
                Button { text: "GitHub ↗"; flat: true; onClicked: Qt.openUrlExternally("https://github.com/Dockpipe-Industries/freeflight") }
                Button { text: "MCP setup"; flat: true; onClicked: window.navigate(4) }
                Button { text: "Contribute"; flat: true; onClicked: window.navigate(5) }
            }
        }
    }
}

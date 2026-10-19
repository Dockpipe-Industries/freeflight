// SPDX-License-Identifier: Apache-2.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1180
    height: 820
    title: "FreeFlight — " + sitePages[selectedPage].title
    color: "#101716"
    property int selectedPage: 0
    readonly property color ink: "#f2f6ef"
    readonly property color accent: "#c3ef88"
    readonly property bool compact: width < 720
    palette.window: color
    palette.windowText: ink
    palette.text: ink
    palette.button: "#182220"
    palette.buttonText: ink
    palette.highlight: accent
    palette.highlightedText: "#101716"
    font.family: "sans-serif"
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: header.implicitHeight + 32
            color: "#182220"
            ColumnLayout {
                id: header
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "↗ FreeFlight"; color: window.accent; font.pixelSize: 26; font.bold: true; Accessible.name: "FreeFlight" }
                    Item { Layout.fillWidth: true }
                    Button { text: "Company ↗"; onClicked: Qt.openUrlExternally("https://github.com/Dockpipe-Industries") }
                    Button { text: "GitHub ↗"; onClicked: Qt.openUrlExternally("https://github.com/Dockpipe-Industries/freeflight") }
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: 6
                    Repeater {
                        model: sitePages
                        Button {
                            required property var modelData
                            required property int index
                            text: modelData.title
                            highlighted: window.selectedPage === index
                            Accessible.name: modelData.title
                            onClicked: { window.selectedPage = index; contentScroll.contentItem.contentY = 0 }
                        }
                    }
                }
            }
        }
        ScrollView {
            id: contentScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: contentScroll.availableWidth
                spacing: 24
                Label {
                    Layout.fillWidth: true
                    Layout.leftMargin: window.compact ? 20 : 64
                    Layout.rightMargin: window.compact ? 20 : 64
                    Layout.topMargin: 32
                    text: "INDEPENDENT · OPEN SOURCE · DEVELOPMENT PREVIEW"
                    color: window.accent
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Text {
                    id: contentText
                    Layout.fillWidth: true
                    Layout.leftMargin: window.compact ? 20 : 64
                    Layout.rightMargin: window.compact ? 20 : 64
                    text: sitePages[window.selectedPage].html
                    textFormat: Text.RichText
                    color: window.ink
                    linkColor: window.accent
                    font.pixelSize: window.compact ? 15 : 17
                    wrapMode: Text.WordWrap
                    Accessible.role: Accessible.StaticText
                    Accessible.name: sitePages[window.selectedPage].title
                    onLinkActivated: function(url) {
                        if (url.charAt(0) === "#") {
                            for (let i = 0; i < sitePages.length; ++i)
                                if (sitePages[i].id === url.substring(1)) { window.selectedPage = i; return }
                        } else if (url.indexOf("https://github.com/") === 0) {
                            Qt.openUrlExternally(url)
                        }
                    }
                }
                Label {
                    Layout.fillWidth: true
                    Layout.margins: 24
                    color: "#aebdb7"
                    text: "A project by Dockpipe Industries Inc. · Independent of Glider and TGlider."
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}

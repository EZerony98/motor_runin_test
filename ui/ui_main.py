# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpacerItem, QStatusBar, QVBoxLayout,
    QWidget)

from ui.tray_entry_widget import TrayEntryWidget

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1280, 820)
        MainWindow.setMinimumSize(QSize(1024, 720))
        MainWindow.setStyleSheet(u"QMainWindow, QWidget {\n"
"    background: #f3f5f7;\n"
"    color: #263442;\n"
"    font-family: \"Microsoft YaHei\", \"PingFang SC\", sans-serif;\n"
"    font-size: 14px;\n"
"}\n"
"QWidget#centralwidget {\n"
"    background: #f3f5f7;\n"
"}\n"
"QFrame#testPanel, QFrame#logPanel {\n"
"    background: white;\n"
"    border: 1px solid #d8dee5;\n"
"    border-radius: 12px;\n"
"}\n"
"QLabel#logoLabel {\n"
"    background: transparent;\n"
"    border: none;\n"
"    padding: 0;\n"
"}\n"
"QLabel#titleLabel {\n"
"    color: #202d3a;\n"
"    font-size: 28px;\n"
"    font-weight: 700;\n"
"}\n"
"QLabel#subtitleLabel {\n"
"    color: #6b7f93;\n"
"    font-size: 14px;\n"
"    font-weight: 500;\n"
"    letter-spacing: 0.6px;\n"
"}\n"
"QLabel#testTitle, QLabel#logTitle {\n"
"    color: #33404d;\n"
"    font-size: 16px;\n"
"    font-weight: 700;\n"
"}\n"
"QLabel#plcConnectionLabel {\n"
"    min-height: 30px;\n"
"    padding: 0 14px;\n"
"    border: 1px solid #cbd5e1;\n"
"    border-radius: 15px;\n"
"    background: #eef2f6;\n"
""
                        "    color: #8a94a3;\n"
"    font-weight: 600;\n"
"}\n"
"QLabel#plcAddressLabel {\n"
"    color: #627d98;\n"
"    font-size: 12px;\n"
"}\n"
"QPushButton {\n"
"    min-height: 34px;\n"
"    padding: 0 18px;\n"
"    border: 1px solid #b9c4ce;\n"
"    border-radius: 5px;\n"
"    background: white;\n"
"}\n"
"QPushButton:hover {\n"
"    background: #fff1f3;\n"
"    border-color: #d41432;\n"
"}\n"
"QPushButton#submitButton {\n"
"    color: white;\n"
"    border-color: #d41432;\n"
"    background: #d41432;\n"
"    font-weight: 600;\n"
"}\n"
"QPushButton#submitButton:hover {\n"
"    background: #b80f29;\n"
"}\n"
"QLineEdit {\n"
"    min-height: 36px;\n"
"    padding: 0 10px;\n"
"    border: 1px solid #b9c4ce;\n"
"    border-radius: 5px;\n"
"    background: white;\n"
"    selection-background-color: #d41432;\n"
"}\n"
"QLineEdit:focus {\n"
"    border: 2px solid #d41432;\n"
"}\n"
"QLineEdit[traySnInput=\"true\"] {\n"
"    background: #ffffff;\n"
"    font-family: Menlo, Consolas, monospace;\n"
"    font-size: 13px;\n"
" "
                        "   font-weight: 600;\n"
"}\n"
"QLineEdit#trayIdEdit {\n"
"    background: #eef2f6;\n"
"    color: #334e68;\n"
"    font-weight: 600;\n"
"}\n"
"QPlainTextEdit {\n"
"    border: 1px solid #dce2e8;\n"
"    border-radius: 6px;\n"
"    background: #fbfcfd;\n"
"    font-family: Menlo, Consolas, monospace;\n"
"    font-size: 12px;\n"
"}")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.rootLayout = QVBoxLayout(self.centralwidget)
        self.rootLayout.setSpacing(12)
        self.rootLayout.setObjectName(u"rootLayout")
        self.rootLayout.setContentsMargins(20, 16, 20, 14)
        self.headerLayout = QHBoxLayout()
        self.headerLayout.setSpacing(22)
        self.headerLayout.setObjectName(u"headerLayout")
        self.logoLabel = QLabel(self.centralwidget)
        self.logoLabel.setObjectName(u"logoLabel")
        self.logoLabel.setMinimumSize(QSize(250, 76))
        self.logoLabel.setMaximumSize(QSize(250, 76))
        self.logoLabel.setAlignment(Qt.AlignCenter)

        self.headerLayout.addWidget(self.logoLabel)

        self.titleLayout = QVBoxLayout()
        self.titleLayout.setSpacing(5)
        self.titleLayout.setObjectName(u"titleLayout")
        self.titleLayout.setAlignment(Qt.AlignVCenter)
        self.titleLabel = QLabel(self.centralwidget)
        self.titleLabel.setObjectName(u"titleLabel")
        self.titleLabel.setMinimumSize(QSize(0, 36))

        self.titleLayout.addWidget(self.titleLabel)

        self.subtitleLabel = QLabel(self.centralwidget)
        self.subtitleLabel.setObjectName(u"subtitleLabel")

        self.titleLayout.addWidget(self.subtitleLabel)


        self.headerLayout.addLayout(self.titleLayout)

        self.headerSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.headerLayout.addItem(self.headerSpacer)

        self.plcStatusLayout = QVBoxLayout()
        self.plcStatusLayout.setSpacing(2)
        self.plcStatusLayout.setObjectName(u"plcStatusLayout")
        self.plcConnectionLabel = QLabel(self.centralwidget)
        self.plcConnectionLabel.setObjectName(u"plcConnectionLabel")
        self.plcConnectionLabel.setAlignment(Qt.AlignCenter)

        self.plcStatusLayout.addWidget(self.plcConnectionLabel)

        self.plcAddressLabel = QLabel(self.centralwidget)
        self.plcAddressLabel.setObjectName(u"plcAddressLabel")
        self.plcAddressLabel.setAlignment(Qt.AlignCenter)

        self.plcStatusLayout.addWidget(self.plcAddressLabel)


        self.headerLayout.addLayout(self.plcStatusLayout)


        self.rootLayout.addLayout(self.headerLayout)

        self.testPanel = QFrame(self.centralwidget)
        self.testPanel.setObjectName(u"testPanel")
        self.testPanelLayout = QVBoxLayout(self.testPanel)
        self.testPanelLayout.setObjectName(u"testPanelLayout")
        self.testPanelLayout.setContentsMargins(18, 14, 18, 16)
        self.testHeadingLayout = QHBoxLayout()
        self.testHeadingLayout.setObjectName(u"testHeadingLayout")
        self.testTitle = QLabel(self.testPanel)
        self.testTitle.setObjectName(u"testTitle")

        self.testHeadingLayout.addWidget(self.testTitle)

        self.testHeadingSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.testHeadingLayout.addItem(self.testHeadingSpacer)

        self.testStateLabel = QLabel(self.testPanel)
        self.testStateLabel.setObjectName(u"testStateLabel")
        self.testStateLabel.setStyleSheet(u"color: #627d98;")

        self.testHeadingLayout.addWidget(self.testStateLabel)


        self.testPanelLayout.addLayout(self.testHeadingLayout)

        self.trayInfoLayout = QHBoxLayout()
        self.trayInfoLayout.setObjectName(u"trayInfoLayout")
        self.trayIdLabel = QLabel(self.testPanel)
        self.trayIdLabel.setObjectName(u"trayIdLabel")

        self.trayInfoLayout.addWidget(self.trayIdLabel)

        self.trayIdEdit = QLineEdit(self.testPanel)
        self.trayIdEdit.setObjectName(u"trayIdEdit")
        self.trayIdEdit.setMinimumSize(QSize(210, 0))
        self.trayIdEdit.setReadOnly(True)

        self.trayInfoLayout.addWidget(self.trayIdEdit)

        self.trayInfoSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.trayInfoLayout.addItem(self.trayInfoSpacer)

        self.scanHintLabel = QLabel(self.testPanel)
        self.scanHintLabel.setObjectName(u"scanHintLabel")
        self.scanHintLabel.setStyleSheet(u"color: #627d98;")

        self.trayInfoLayout.addWidget(self.scanHintLabel)


        self.testPanelLayout.addLayout(self.trayInfoLayout)

        self.trayEntryWidget = TrayEntryWidget(self.testPanel)
        self.trayEntryWidget.setObjectName(u"trayEntryWidget")
        self.trayEntryWidget.setMinimumSize(QSize(0, 330))

        self.testPanelLayout.addWidget(self.trayEntryWidget)

        self.controlLayout = QHBoxLayout()
        self.controlLayout.setObjectName(u"controlLayout")
        self.fillButton = QPushButton(self.testPanel)
        self.fillButton.setObjectName(u"fillButton")

        self.controlLayout.addWidget(self.fillButton)

        self.clearButton = QPushButton(self.testPanel)
        self.clearButton.setObjectName(u"clearButton")

        self.controlLayout.addWidget(self.clearButton)

        self.controlSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.controlLayout.addItem(self.controlSpacer)

        self.submitButton = QPushButton(self.testPanel)
        self.submitButton.setObjectName(u"submitButton")

        self.controlLayout.addWidget(self.submitButton)


        self.testPanelLayout.addLayout(self.controlLayout)


        self.rootLayout.addWidget(self.testPanel)

        self.logPanel = QFrame(self.centralwidget)
        self.logPanel.setObjectName(u"logPanel")
        self.logPanel.setMaximumSize(QSize(16777215, 145))
        self.logPanelLayout = QVBoxLayout(self.logPanel)
        self.logPanelLayout.setObjectName(u"logPanelLayout")
        self.logPanelLayout.setContentsMargins(18, 10, 18, 10)
        self.logTitle = QLabel(self.logPanel)
        self.logTitle.setObjectName(u"logTitle")

        self.logPanelLayout.addWidget(self.logTitle)

        self.logOutput = QPlainTextEdit(self.logPanel)
        self.logOutput.setObjectName(u"logOutput")
        self.logOutput.setMinimumSize(QSize(0, 68))
        self.logOutput.setMaximumSize(QSize(16777215, 78))
        self.logOutput.setReadOnly(True)

        self.logPanelLayout.addWidget(self.logOutput)


        self.rootLayout.addWidget(self.logPanel)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"\u7535\u673a\u8dd1\u5408\u6d4b\u8bd5\u7cfb\u7edf", None))
        self.logoLabel.setText("")
        self.titleLabel.setText(QCoreApplication.translate("MainWindow", u"\u7535\u673a\u8dd1\u5408\u6d4b\u8bd5\u7cfb\u7edf", None))
        self.subtitleLabel.setText(QCoreApplication.translate("MainWindow", u"Motor Run-in Test Station", None))
        self.plcConnectionLabel.setText(QCoreApplication.translate("MainWindow", u"\u25cf PLC \u672a\u8fde\u63a5", None))
        self.plcAddressLabel.setText(QCoreApplication.translate("MainWindow", u"192.168.250.1:9600", None))
        self.testTitle.setText(QCoreApplication.translate("MainWindow", u"\u6258\u76d8\u4e0a\u6599\u4e0e SN \u5f55\u5165", None))
        self.testStateLabel.setText(QCoreApplication.translate("MainWindow", u"\u5f53\u524d\u72b6\u6001\uff1a\u7b49\u5f85\u6258\u76d8", None))
        self.trayIdLabel.setText(QCoreApplication.translate("MainWindow", u"\u6258\u76d8\u7f16\u53f7", None))
        self.trayIdEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u7b49\u5f85 PLC \u8bfb\u53d6 RFID", None))
        self.scanHintLabel.setText(QCoreApplication.translate("MainWindow", u"\u626b\u7801\u540e\u6309\u56de\u8f66\u81ea\u52a8\u8fdb\u5165\u4e0b\u4e00\u4f4d\u7f6e", None))
        self.fillButton.setText(QCoreApplication.translate("MainWindow", u"\u987a\u5e8f\u8865\u9f50", None))
        self.clearButton.setText(QCoreApplication.translate("MainWindow", u"\u6e05\u7a7a SN", None))
        self.submitButton.setText(QCoreApplication.translate("MainWindow", u"\u5199\u5165 PLC", None))
        self.logTitle.setText(QCoreApplication.translate("MainWindow", u"\u8fd0\u884c\u65e5\u5fd7", None))
        self.logOutput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u7cfb\u7edf\u65e5\u5fd7\u5c06\u5728\u8fd9\u91cc\u663e\u793a\u2026\u2026", None))
    # retranslateUi

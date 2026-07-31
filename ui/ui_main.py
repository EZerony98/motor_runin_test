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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QPlainTextEdit,
    QPushButton, QSizePolicy, QSpacerItem, QStatusBar,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1180, 760)
        MainWindow.setMinimumSize(QSize(960, 640))
        MainWindow.setStyleSheet(u"QMainWindow, QWidget {\n"
"    background: #f4f6f8;\n"
"    color: #1f2937;\n"
"    font-family: \"Microsoft YaHei\", \"PingFang SC\", sans-serif;\n"
"    font-size: 14px;\n"
"}\n"
"QFrame#testPanel, QFrame#logPanel {\n"
"    background: white;\n"
"    border: 1px solid #dce2e8;\n"
"    border-radius: 8px;\n"
"}\n"
"QLabel#titleLabel {\n"
"    color: #102a43;\n"
"    font-size: 24px;\n"
"    font-weight: 600;\n"
"}\n"
"QLabel#testTitle, QLabel#logTitle {\n"
"    color: #334e68;\n"
"    font-size: 16px;\n"
"    font-weight: 600;\n"
"}\n"
"QLabel#plcConnectionLabel {\n"
"    min-height: 30px;\n"
"    padding: 0 14px;\n"
"    border: 1px solid #cbd5e1;\n"
"    border-radius: 15px;\n"
"    background: #eef2f6;\n"
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
""
                        "QPushButton:hover {\n"
"    background: #edf4fb;\n"
"}\n"
"QPushButton#submitButton {\n"
"    color: white;\n"
"    border-color: #1769aa;\n"
"    background: #1769aa;\n"
"    font-weight: 600;\n"
"}\n"
"QPushButton#submitButton:hover {\n"
"    background: #12568c;\n"
"}\n"
"QLineEdit {\n"
"    min-height: 36px;\n"
"    padding: 0 10px;\n"
"    border: 1px solid #b9c4ce;\n"
"    border-radius: 5px;\n"
"    background: white;\n"
"    selection-background-color: #1769aa;\n"
"}\n"
"QLineEdit:focus {\n"
"    border: 2px solid #1769aa;\n"
"}\n"
"QLineEdit#trayIdEdit {\n"
"    background: #eef2f6;\n"
"    color: #334e68;\n"
"    font-weight: 600;\n"
"}\n"
"QPlainTextEdit {\n"
"    border: 1px solid #dce2e8;\n"
"    border-radius: 5px;\n"
"    background: #fbfcfd;\n"
"    font-family: Menlo, Consolas, monospace;\n"
"    font-size: 12px;\n"
"}")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.rootLayout = QVBoxLayout(self.centralwidget)
        self.rootLayout.setSpacing(16)
        self.rootLayout.setObjectName(u"rootLayout")
        self.rootLayout.setContentsMargins(24, 20, 24, 20)
        self.headerLayout = QHBoxLayout()
        self.headerLayout.setObjectName(u"headerLayout")
        self.titleLayout = QVBoxLayout()
        self.titleLayout.setSpacing(2)
        self.titleLayout.setObjectName(u"titleLayout")
        self.titleLabel = QLabel(self.centralwidget)
        self.titleLabel.setObjectName(u"titleLabel")

        self.titleLayout.addWidget(self.titleLabel)

        self.subtitleLabel = QLabel(self.centralwidget)
        self.subtitleLabel.setObjectName(u"subtitleLabel")
        self.subtitleLabel.setStyleSheet(u"color: #627d98;")

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

        self.serialNumberGrid = QGridLayout()
        self.serialNumberGrid.setObjectName(u"serialNumberGrid")
        self.serialNumberGrid.setHorizontalSpacing(14)
        self.serialNumberGrid.setVerticalSpacing(8)
        self.snLabel1 = QLabel(self.testPanel)
        self.snLabel1.setObjectName(u"snLabel1")
        self.snLabel1.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel1, 0, 0, 1, 1)

        self.snLabel2 = QLabel(self.testPanel)
        self.snLabel2.setObjectName(u"snLabel2")
        self.snLabel2.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel2, 0, 1, 1, 1)

        self.snLabel3 = QLabel(self.testPanel)
        self.snLabel3.setObjectName(u"snLabel3")
        self.snLabel3.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel3, 0, 2, 1, 1)

        self.snLabel4 = QLabel(self.testPanel)
        self.snLabel4.setObjectName(u"snLabel4")
        self.snLabel4.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel4, 0, 3, 1, 1)

        self.snLabel5 = QLabel(self.testPanel)
        self.snLabel5.setObjectName(u"snLabel5")
        self.snLabel5.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel5, 0, 4, 1, 1)

        self.snInput1 = QLineEdit(self.testPanel)
        self.snInput1.setObjectName(u"snInput1")
        self.snInput1.setMaxLength(64)
        self.snInput1.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput1, 1, 0, 1, 1)

        self.snInput2 = QLineEdit(self.testPanel)
        self.snInput2.setObjectName(u"snInput2")
        self.snInput2.setMaxLength(64)
        self.snInput2.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput2, 1, 1, 1, 1)

        self.snInput3 = QLineEdit(self.testPanel)
        self.snInput3.setObjectName(u"snInput3")
        self.snInput3.setMaxLength(64)
        self.snInput3.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput3, 1, 2, 1, 1)

        self.snInput4 = QLineEdit(self.testPanel)
        self.snInput4.setObjectName(u"snInput4")
        self.snInput4.setMaxLength(64)
        self.snInput4.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput4, 1, 3, 1, 1)

        self.snInput5 = QLineEdit(self.testPanel)
        self.snInput5.setObjectName(u"snInput5")
        self.snInput5.setMaxLength(64)
        self.snInput5.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput5, 1, 4, 1, 1)

        self.snLabel6 = QLabel(self.testPanel)
        self.snLabel6.setObjectName(u"snLabel6")
        self.snLabel6.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel6, 2, 0, 1, 1)

        self.snLabel7 = QLabel(self.testPanel)
        self.snLabel7.setObjectName(u"snLabel7")
        self.snLabel7.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel7, 2, 1, 1, 1)

        self.snLabel8 = QLabel(self.testPanel)
        self.snLabel8.setObjectName(u"snLabel8")
        self.snLabel8.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel8, 2, 2, 1, 1)

        self.snLabel9 = QLabel(self.testPanel)
        self.snLabel9.setObjectName(u"snLabel9")
        self.snLabel9.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel9, 2, 3, 1, 1)

        self.snLabel10 = QLabel(self.testPanel)
        self.snLabel10.setObjectName(u"snLabel10")
        self.snLabel10.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snLabel10, 2, 4, 1, 1)

        self.snInput6 = QLineEdit(self.testPanel)
        self.snInput6.setObjectName(u"snInput6")
        self.snInput6.setMaxLength(64)
        self.snInput6.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput6, 3, 0, 1, 1)

        self.snInput7 = QLineEdit(self.testPanel)
        self.snInput7.setObjectName(u"snInput7")
        self.snInput7.setMaxLength(64)
        self.snInput7.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput7, 3, 1, 1, 1)

        self.snInput8 = QLineEdit(self.testPanel)
        self.snInput8.setObjectName(u"snInput8")
        self.snInput8.setMaxLength(64)
        self.snInput8.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput8, 3, 2, 1, 1)

        self.snInput9 = QLineEdit(self.testPanel)
        self.snInput9.setObjectName(u"snInput9")
        self.snInput9.setMaxLength(64)
        self.snInput9.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput9, 3, 3, 1, 1)

        self.snInput10 = QLineEdit(self.testPanel)
        self.snInput10.setObjectName(u"snInput10")
        self.snInput10.setMaxLength(64)
        self.snInput10.setAlignment(Qt.AlignCenter)

        self.serialNumberGrid.addWidget(self.snInput10, 3, 4, 1, 1)


        self.testPanelLayout.addLayout(self.serialNumberGrid)

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
        self.logPanelLayout = QVBoxLayout(self.logPanel)
        self.logPanelLayout.setObjectName(u"logPanelLayout")
        self.logPanelLayout.setContentsMargins(18, 14, 18, 16)
        self.logTitle = QLabel(self.logPanel)
        self.logTitle.setObjectName(u"logTitle")

        self.logPanelLayout.addWidget(self.logTitle)

        self.logOutput = QPlainTextEdit(self.logPanel)
        self.logOutput.setObjectName(u"logOutput")
        self.logOutput.setMinimumSize(QSize(0, 110))
        self.logOutput.setReadOnly(True)

        self.logPanelLayout.addWidget(self.logOutput)


        self.rootLayout.addWidget(self.logPanel)

        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
        QWidget.setTabOrder(self.snInput1, self.snInput2)
        QWidget.setTabOrder(self.snInput2, self.snInput3)
        QWidget.setTabOrder(self.snInput3, self.snInput4)
        QWidget.setTabOrder(self.snInput4, self.snInput5)
        QWidget.setTabOrder(self.snInput5, self.snInput6)
        QWidget.setTabOrder(self.snInput6, self.snInput7)
        QWidget.setTabOrder(self.snInput7, self.snInput8)
        QWidget.setTabOrder(self.snInput8, self.snInput9)
        QWidget.setTabOrder(self.snInput9, self.snInput10)
        QWidget.setTabOrder(self.snInput10, self.fillButton)
        QWidget.setTabOrder(self.fillButton, self.clearButton)
        QWidget.setTabOrder(self.clearButton, self.submitButton)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"\u7535\u673a\u8dd1\u5408\u6d4b\u8bd5\u7cfb\u7edf", None))
        self.titleLabel.setText(QCoreApplication.translate("MainWindow", u"\u7535\u673a\u8dd1\u5408\u6d4b\u8bd5\u7cfb\u7edf", None))
        self.subtitleLabel.setText(QCoreApplication.translate("MainWindow", u"Motor Run-in Test Station", None))
        self.plcConnectionLabel.setText(QCoreApplication.translate("MainWindow", u"\u25cf PLC \u672a\u8fde\u63a5", None))
        self.plcAddressLabel.setText(QCoreApplication.translate("MainWindow", u"192.168.250.1:9600", None))
        self.testTitle.setText(QCoreApplication.translate("MainWindow", u"\u6258\u76d8\u4e0a\u6599\u4e0e SN \u5f55\u5165", None))
        self.testStateLabel.setText(QCoreApplication.translate("MainWindow", u"\u5f53\u524d\u72b6\u6001\uff1a\u7b49\u5f85\u6258\u76d8", None))
        self.trayIdLabel.setText(QCoreApplication.translate("MainWindow", u"\u6258\u76d8\u7f16\u53f7", None))
        self.trayIdEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u7b49\u5f85 PLC \u8bfb\u53d6 RFID", None))
        self.scanHintLabel.setText(QCoreApplication.translate("MainWindow", u"\u626b\u7801\u540e\u6309\u56de\u8f66\u81ea\u52a8\u8fdb\u5165\u4e0b\u4e00\u4f4d\u7f6e", None))
        self.snLabel1.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 1", None))
        self.snLabel2.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 2", None))
        self.snLabel3.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 3", None))
        self.snLabel4.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 4", None))
        self.snLabel5.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 5", None))
        self.snInput1.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 1", None))
        self.snInput2.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 2", None))
        self.snInput3.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 3", None))
        self.snInput4.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 4", None))
        self.snInput5.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 5", None))
        self.snLabel6.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 6", None))
        self.snLabel7.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 7", None))
        self.snLabel8.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 8", None))
        self.snLabel9.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 9", None))
        self.snLabel10.setText(QCoreApplication.translate("MainWindow", u"\u4f4d\u7f6e 10", None))
        self.snInput6.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 6", None))
        self.snInput7.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 7", None))
        self.snInput8.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 8", None))
        self.snInput9.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 9", None))
        self.snInput10.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u626b\u63cf SN 10", None))
        self.fillButton.setText(QCoreApplication.translate("MainWindow", u"\u987a\u5e8f\u8865\u9f50", None))
        self.clearButton.setText(QCoreApplication.translate("MainWindow", u"\u6e05\u7a7a SN", None))
        self.submitButton.setText(QCoreApplication.translate("MainWindow", u"\u5199\u5165 PLC", None))
        self.logTitle.setText(QCoreApplication.translate("MainWindow", u"\u8fd0\u884c\u65e5\u5fd7", None))
        self.logOutput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u7cfb\u7edf\u65e5\u5fd7\u5c06\u5728\u8fd9\u91cc\u663e\u793a\u2026\u2026", None))
    # retranslateUi

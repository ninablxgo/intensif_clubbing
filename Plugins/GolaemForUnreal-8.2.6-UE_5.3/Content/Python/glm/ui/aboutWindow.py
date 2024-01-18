#**************************************************************************
#*                                                                        *
#*  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
#*                                                                        *
#**************************************************************************

import os
import webbrowser
import datetime
from glm.Qtpy.Qt import QtCore, QtGui, QtWidgets


#**********************************************************************
#
# SimCacheLibWindow
#
#**********************************************************************
class AboutWindow(QtWidgets.QMainWindow):
    #------------------------------------------------------------------
    # Constructor
    #------------------------------------------------------------------
    def __init__(self, wrapper=None, golaemVersion="", licenseText="", productName=""):
        self.wrapper = wrapper
        parent = self.wrapper.getParentWindow()
        super(AboutWindow, self).__init__(parent)

        # Data Members
        self.golaemVersion = golaemVersion
        licenseTextSplit = licenseText.split(';')
        self.isLicenseValid = licenseTextSplit[0]
        self.licenseText = ""
        if len(licenseTextSplit) > 1:
            self.licenseText = licenseTextSplit[1]
        self.productName = productName
        self.defaultPosAndSize = [[50, 50],[400, 160]]

        # Init
        self.initUI()


    #******************************************************************
    # UI Accessors
    #******************************************************************

    #------------------------------------------------------------------
    # UI
    #------------------------------------------------------------------
    def initUI(self):
        # Window properties
        iconsDir = self.wrapper.getIconsDir()
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("About " + self.productName + " " + self.golaemVersion)
        self.setObjectName('glmAboutWnd')
        self.restorePosAndSize()
        self.setWindowIcon(QtGui.QIcon(os.path.join(iconsDir, "glmDefaultIcon.png").replace("\\", "/")))

        # Central Widget
        mainWidget = QtWidgets.QWidget(self)
        mainLayout = QtWidgets.QGridLayout()
        mainLayout.setHorizontalSpacing(0)
        mainLayout.setVerticalSpacing(0)
        mainWidget.setLayout(mainLayout)
        #mainWidget.setStyleSheet(self.wrapper.getStyleSheet())
        self.setCentralWidget(mainWidget)

        # upperLayout
        upperLayout = QtWidgets.QGridLayout()
        mainLayout.addLayout(upperLayout, 0, 0)

        # Icon
        iconLabel = QtWidgets.QLabel(self)
        iconPixmap = QtGui.QPixmap(os.path.join(iconsDir, "glmAbout.png").replace("\\", "/"))
        iconLabel.setPixmap(iconPixmap)
        upperLayout.addWidget(iconLabel, 0, 0)

        currentYear = datetime.datetime.now().year

        # Label
        aboutText = "<b>" + self.productName + " " + self.golaemVersion + '</b><br>'
        aboutText += '<br>'
        aboutText += '&#169; 2011-' + str(currentYear) + ' Golaem SA - France.<br>'
        aboutText += 'All rights reserved.<br>'
        aboutText += '<br>'
        if self.isLicenseValid == "1":
            aboutText += "<font color='#008300'>" + self.licenseText + '</font><br>'
        else:
            aboutText += "<font color='#ea7b09'>" + self.licenseText + '</font><br>'
        aboutText += '<br>'

        aboutLabel = QtWidgets.QLabel(aboutText, self)
        aboutLabel.setFixedWidth(300)
        upperLayout.addWidget(aboutLabel, 0, 1)

        #button layout
        buttonsLayout = QtWidgets.QGridLayout()
        mainLayout.addLayout(buttonsLayout, 1, 0)

        #buttons
        buttonOK = QtWidgets.QPushButton('OK', self)
        buttonOK.clicked.connect(self.close)
        buttonRN = QtWidgets.QPushButton('Support Request', self)
        buttonRN.clicked.connect(lambda: webbrowser.open('http://support.golaem.com'))
        buttonNV = QtWidgets.QPushButton('Release Notes', self)
        buttonNV.clicked.connect(lambda: webbrowser.open('http://releasenotes.golaem.com'))
        buttonsLayout.addWidget(buttonOK, 0, 0)
        buttonsLayout.addWidget(buttonRN, 0, 1)
        buttonsLayout.addWidget(buttonNV, 0, 2)


    #******************************************************************
    # Accessors
    #******************************************************************

    #------------------------------------------------------------------
    # restorePosAndSize
    #------------------------------------------------------------------
    def restorePosAndSize(self):
        posAndSize = self.wrapper.loadWindowPrefs(self.objectName(), self.defaultPosAndSize)
        self.move(QtCore.QPoint(posAndSize[0][0], posAndSize[0][1]))
        # force size
        self.setFixedSize(posAndSize[1][0], posAndSize[1][1])

    #------------------------------------------------------------------
    # savePosAndSize
    #------------------------------------------------------------------
    def savePosAndSize(self):
        posAndSize = []
        posAndSize.append([self.pos().x(), self.pos().y()])
        posAndSize.append([self.width(), self.height()])
        self.wrapper.saveWindowPrefs(self.objectName(), posAndSize)

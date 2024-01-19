#**************************************************************************
#*                                                                        *
#*  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
#*                                                                        *
#**************************************************************************

import os
from glm.Qtpy.Qt import QtCore, QtWidgets


#**********************************************************************
#
# WindowWrapper
# Default wrapper for golaem window tools
#
#**********************************************************************
class WindowWrapper(object):
    #******************************************************************
    # File
    #******************************************************************

    #------------------------------------------------------------------
    # invokes a file browser
    # return an array of string
    # fileMode 0 Any file, whether it exists or not, 1 A single existing file, 2 for write-segmented (no paths), 3 The name of a directory
    #------------------------------------------------------------------
    def browseFiles(self, caption, fileFilters, fileType, fileMode):
        browserMode = QtWidgets.QFileDialog.ExistingFile
        if fileMode == 0:
            browserMode = QtWidgets.QFileDialog.AnyFile
        elif fileMode == 3:
            browserMode = QtWidgets.QFileDialog.Directory

        dialog = QtWidgets.QFileDialog()
        dialog.setWindowTitle(caption)
        dialog.setFileMode(browserMode)
        dialog.setNameFilter(';;'.join(fileFilters))
        fileNames = None
        if dialog.exec_() and len(dialog.selectedFiles()):
            fileNames = dialog.selectedFiles()
        return fileNames

    #******************************************************************
    # Prefs
    #******************************************************************

    #------------------------------------------------------------------
    # loads and returns the window prefs
    #------------------------------------------------------------------
    def loadWindowPrefs(self, windowsName, defaultValues):
        return defaultValues

    #------------------------------------------------------------------
    # save the window prefs
    #------------------------------------------------------------------
    def saveWindowPrefs(self, windowsName, values):
        pass

    #------------------------------------------------------------------
    # get a string global var value
    #------------------------------------------------------------------
    def getStrOptionVar(self, optionVarGrp, optionVar):
        settings = QtCore.QSettings('Golaem', optionVarGrp)
        return str(settings.value(optionVar, ''))

    #------------------------------------------------------------------
    # set a string global var value
    #------------------------------------------------------------------
    def setStrOptionVar(self, optionVarGrp, optionVar, value):
        settings = QtCore.QSettings('Golaem', optionVarGrp)
        settings.setValue(optionVar, value)

    #******************************************************************
    # Select
    #******************************************************************

    #------------------------------------------------------------------
    # selects a node
    #------------------------------------------------------------------
    def selectNode(self, nodeToSelect):
        pass

    #------------------------------------------------------------------
    # returns all selected objects of type
    #------------------------------------------------------------------
    def getSelectedObjectsOfType(self, objectType):
        return []

    #------------------------------------------------------------------
    # returns all objects of type
    #------------------------------------------------------------------
    def getObjectsOfType(self, objectType):
        return []

    #******************************************************************
    # UI
    #******************************************************************

    #------------------------------------------------------------------
    # returns the parent window
    #------------------------------------------------------------------
    def getParentWindow(self):
        return None

    #------------------------------------------------------------------
    # log a message (level : info / warning / error)
    #------------------------------------------------------------------
    def log(self, logLevel, message):
        pass

    #------------------------------------------------------------------
    # returns the directory with the icons
    #------------------------------------------------------------------
    def getIconsDir(self):
        thisDirectory = os.path.dirname(os.path.realpath(__file__))
        return (thisDirectory + '/../../../icons/')

    #------------------------------------------------------------------
    # creates a callback which is called when the parent app exits
    #------------------------------------------------------------------
    def addExitCallback(self, callback):
        return None

    #------------------------------------------------------------------
    # deletes an exit callback which is called when the parent app exits
    #------------------------------------------------------------------
    def removeExitCallback(self, callbackId):
        pass

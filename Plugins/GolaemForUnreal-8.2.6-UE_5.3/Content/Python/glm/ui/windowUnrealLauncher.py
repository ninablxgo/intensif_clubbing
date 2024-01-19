from __future__ import absolute_import
# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
# *                                                                        *
# **************************************************************************

from ..simCacheLib import simCacheLibWindow as scl
from ..simCacheLib import simCacheLibWindowUnrealWrapper as sclw
from ..layout import layoutEditorUtils
from ..layout import layoutEditorWrapper
from . import aboutWindow as abt
from ..Qtpy.Qt import QtCore, QtWidgets
from . import windowUnrealWrapper as wrapper
import unreal
import sys
import os

usingDevkit = True
try:
    from ..devkit import *
except:
    usingDevkit = False

# **********************************************************************
#
# Launchers
#
# **********************************************************************

glmSimCacheLibWindowUIs = []
# ------------------------------------------------------------------
# SimCacheLibWindowMain
# ------------------------------------------------------------------
def SimCacheLibWindowMain():
    global glmSimCacheLibWindowUIs
    application = None
    libUI = None
    if not QtWidgets.QApplication.instance():
        application = QtWidgets.QApplication(sys.argv)
        unreal.log("Created QApplication instance: {0}".format(application))
    if len(glmSimCacheLibWindowUIs):
        libUI = glmSimCacheLibWindowUIs[0]
    else:
        libUI = scl.SimCacheLibWindow(sclw.SimCacheLibWindowUnrealWrapper())
        glmSimCacheLibWindowUIs.append(libUI)
    libUI.show()
    libUI.setWindowState(libUI.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
    libUI.activateWindow()
    return libUI


# ------------------------------------------------------------------
# AboutWindowMain
# ------------------------------------------------------------------
def AboutWindowMain(golaemVersion="", licenseInfo=""):
    application = None
    abtUI = None
    if not QtWidgets.QApplication.instance():
        application = QtWidgets.QApplication(sys.argv)
        unreal.log("Created QApplication instance: {0}".format(application))
    unrealWrapper = wrapper.WindowUnrealWrapper()
    abtUI = abt.AboutWindow(wrapper=unrealWrapper, golaemVersion=golaemVersion, licenseText=licenseInfo, productName="Golaem for Unreal")
    abtUI.show()
    abtUI.setWindowState(abtUI.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
    abtUI.activateWindow()
    return abtUI


# ------------------------------------------------------------------
# LayoutEditorWindowMain
# ------------------------------------------------------------------
def LayoutEditorWindowMain(golaemUEDir=""):
    application = None
    layoutEditor = None
    if not QtWidgets.QApplication.instance():
        application = QtWidgets.QApplication(sys.argv)
        unreal.log("Created QApplication instance: {0}".format(application))

    layoutIconsDir = os.path.join(golaemUEDir, "Resources", "Icons", "layoutToolv7").replace("\\", "/")
    layoutWrapper = layoutEditorWrapper.getTheLayoutEditorWrapperInstance()
    layoutWrapper._iconsDir = layoutIconsDir
    layoutEditor = layoutEditorUtils.getTheLayoutEditorInstance(wrapper=layoutWrapper)
    layoutEditor.show()
    layoutEditor.setWindowState(
        layoutEditor.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive
    )
    layoutEditor.activateWindow()
    return layoutEditor


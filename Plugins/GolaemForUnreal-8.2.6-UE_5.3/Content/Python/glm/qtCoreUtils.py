# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A.  All Rights Reserved.                       *
# *                                                                        *
# **************************************************************************

# **************************************************************************
#! \file Qt Core Utils
#  \brief Golaem qt functions with no dependencies from Maya!!
# **************************************************************************

# DO NOT ADD ANY MAYA DEPENDENCY HERE

from builtins import str
from glm.Qtpy.Qt import QtWidgets

import xml.etree.ElementTree as xml

import os
import tempfile
import sys

pyside2uicAvailable = True
try:
    import pyside2uic
except:
    pyside2uicAvailable = False

# DO NOT ADD ANY MAYA DEPENDENCY HERE


# ------------------------------------------------------------------
# Pyside lacks the "loadUiType" command, so we have to convert the ui file to py code in-memory first
# and then execute it in a special frame to retrieve the form_class.
# http://tech-artists.org/forum/showthread.php?3035-PySide-in-Maya-2013
# Maya 2022: modified to use uic executable instead of pysideuic which is no longer available
# ------------------------------------------------------------------
def loadUiType(uiFile):
    parsed = xml.parse(uiFile)
    widget_class = parsed.find("widget").get("class")
    form_class = parsed.find("class").text

    with open(uiFile, "r") as f:
        # print("loadUiType in")
        outFile = os.path.join(tempfile.gettempdir(), "ui_" + os.path.splitext(os.path.basename(uiFile))[0] + ".py").replace("\\", "/")
        uicPath = os.path.join(os.path.dirname(sys.executable), "uic").replace("\\", "/")
        if pyside2uicAvailable:
            with open(outFile, "w") as uicFile:
                pyside2uic.compileUi(uiFile, uicFile)
        else:
            os.system('"' + uicPath + '"' + " -g python " + uiFile + " -o " + outFile)
        with open(outFile, "r") as uicFile:
            variables = {}
            exec(uicFile.read(), variables)

            # Fetch the base_class and form class based on their type in the xml from designer
            # print(form_class + " - " + widget_class)
            form_class = variables["Ui_%s" % form_class]
            base_class = eval("QtWidgets.%s" % widget_class)
    return form_class, base_class


# ------------------------------------------------------------------
# Get existing QApplication instance
# ------------------------------------------------------------------
def getQappInstance():
    newInstance = False
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication([])
        newInstance = True
    return (app, newInstance)
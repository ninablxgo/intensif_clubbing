# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
# *                                                                        *
# **************************************************************************

from glm.simCacheLib import SimCacheLibWindow

from builtins import map
from builtins import bytes
from builtins import str
from builtins import range
from glm.Qtpy.Qt import QtCore, QtGui, QtWidgets
from functools import partial
from glm.simCacheLib import simCacheLib
from glm.simCacheLib.simCacheLibWindowMayaWrapper import SimCacheLibWindowMayaWrapper

import sys
import os
import fnmatch
import base64

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# **********************************************************************
#
# SimCacheLibWindow
#
# **********************************************************************
class SimCacheLibWindowMaya(MayaQWidgetDockableMixin, SimCacheLibWindow):
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(self, wrapper=SimCacheLibWindowMayaWrapper()):
        self.wrapper = wrapper
        parent = self.wrapper.getParentWindow()
        MayaQWidgetDockableMixin.__init__(self, parent=parent)
        SimCacheLibWindow.__init__(self, parent=parent, wrapper = wrapper)

    def show(self):
        MayaQWidgetDockableMixin.show(self, dockable=True) # if dockable False, the window disappear behind maya when lsoing focus under linux
        self.activateWindow()
        self.raise_()
        if self.isMinimized():
            self.showNormal()
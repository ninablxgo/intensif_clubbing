from __future__ import absolute_import

# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
# *                                                                        *
# **************************************************************************

from builtins import bytes
from glm.simCacheLib import simCacheLibWindow as scl
from glm.simCacheLib import simCacheLibWindowWrapper as sclw
from glm.devkit import *
from glm.Qtpy.Qt import QtWidgets
from glm import qtCoreUtils as qtcUtils

initGolaemProduct("Standalone", "")
initGolaem()

app, newInstance = qtcUtils.getQappInstance()

if app:
    scl.main(sclw.SimCacheLibWindowWrapper())
    if newInstance:
        app.exec_()

from __future__ import print_function

# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
# *                                                                        *
# **************************************************************************

from builtins import range
import os
import random

from glm.Nodz import nodz_utils

from glm.Qtpy.Qt import QtCore, QtWidgets
import glm.layout.layoutEditorUtils as layoutUtils
import glm.layout.layoutEditorWrapper as layoutWrapper
from glm import qtCoreUtils as qtcUtils

usingDevkit = True
try:
    from glm.devkit import *
except:
    usingDevkit = False


def main():
    app, newInstance = qtcUtils.getQappInstance()

    # get and display main windows
    if usingDevkit:
        currentDir = os.path.dirname(os.path.realpath(__file__))
        licDir = os.path.join(currentDir, os.pardir, os.pardir, os.pardir, "plug-ins").replace("\\", "/")
        initGolaemProduct("Standalone", licDir)
        initGolaem()
    layoutEditor = layoutUtils.getTheLayoutEditorInstance(wrapper=layoutWrapper.getTheLayoutEditorWrapperInstance())
    layoutEditor.show()
    layoutEditor.loadWindowPrefs()
    # just for test purposes (the wrapper won't do much without a cache proxy):
    layoutEditor.wrapper.getVectorFieldsList()
    layoutEditor.wrapper.getPaintedZonesList()

    # If trying to debug the attributes UI, use these lines to use a DEBUG node definition containing everyt possible type of attribute (combining base types and possible flags)
    debugAttributes = False
    if debugAttributes:
        layoutEditor.layoutNodesList = None
        layoutEditor.layoutNodesDefinition = list()
        layoutNodesDefinitionFile = nodz_utils._loadConfig(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "golaem_layoutNodes_DEBUG_definition.json")
        )
        layoutEditor.layoutNodesDefinition = layoutNodesDefinitionFile["GolaemLayoutNodes"]
        layoutEditor.initEditor(layoutWrapper.getTheLayoutEditorWrapperInstance())

    # add action on key to save the model from the current file
    def on_keyPressed(key):
        # if key==QtCore.Qt.Key_M:  #'m' to save the data model as a .json file
        #     filePath = QtWidgets.QFileDialog.getSaveFileName(None, 'Save Layout File', os.path.dirname(os.path.realpath(__file__)), "JSON files (*.json)")
        #     if(filePath[0]!=''):
        #         layoutEditor.saveGolaemLayoutNodeDefinition(filePath[0])

        if key == QtCore.Qt.Key_G:
            print("Test editLayoutParameter")
            value = random.random() * 3
            layoutEditor.wrapper.openCacheProxy(layoutEditor.getLayoutNameForCurrentTab(), True)
            layoutEditor.wrapper.editLayoutParameter(layoutEditor.getLayoutNameForCurrentTab(), "defaultGroundAdaptationMode", 3, value)

        if key == QtCore.Qt.Key_W:
            print("Test addOrEditLayoutTransformation")
            pivot = [[random.random(), random.random(), random.random()]]
            rotate = [[random.random(), random.random(), random.random()]]
            frame = random.random() * 100
            layoutEditor.wrapper.openCacheProxy(layoutEditor.getLayoutNameForCurrentTab(), True)
            layoutEditor.wrapper.addOrEditLayoutTransformation(
                layoutEditor.getLayoutNameForCurrentTab(), "1001, 2001, 3001-5001, et(0), cf(1)", "Rotate", "pivot", pivot, None, 1
            )
            layoutEditor.wrapper.addOrEditLayoutTransformation(
                layoutEditor.getLayoutNameForCurrentTab(), "1001, 2001, 3001-5001, et(0), cf(1)", "Rotate", "rotate", rotate, frame, 0
            )

        if key == QtCore.Qt.Key_S:
            print("Test cache status")
            # global status
            cacheSize = 1024
            cachedPercentUsed = random.random()
            globalStatus = [cachedPercentUsed * cacheSize, cacheSize]
            # frame range
            cacheFrameRange = [2, 10]
            # nodes status
            nodesStatus = []
            nodesStatusCount = int(random.random() * 10)
            for iNode in range(nodesStatusCount):
                nodeFrames = []
                for iFrame in range(cacheFrameRange[0], cacheFrameRange[1]):
                    if random.random() > 0.5:
                        nodeFrames.append(iFrame)
                currentNodeCacheStatus = [iNode, nodeFrames]
                nodesStatus.append(currentNodeCacheStatus)

            # global status is a multi array
            cacheStatus = [globalStatus, cacheFrameRange, nodesStatus]

            layoutEditor.wrapper.setCacheStatus(layoutEditor.getLayoutNameForCurrentTab(), cacheStatus)

        if key == QtCore.Qt.Key_T:
            print("Test setHighlightedLayoutNodesIDs")
            layoutEditor.wrapper.openCacheProxy(layoutEditor.getLayoutNameForCurrentTab(), True)
            layoutEditor.wrapper.setHighlightedLayoutNodesIDs(
                layoutEditor.getLayoutNameForCurrentTab(), [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
            )

        if key == QtCore.Qt.Key_P:
            print("Test editLayoutPostureNode")
            keyFramesCount = int(random.random() * 5)
            keyFrames = []
            keyValues = []
            for i in range(keyFramesCount):
                keyFrames.append(random.random() * 100)
                keyValues.append([random.random(), random.random(), random.random()])

            transformLabel = "localOri"
            if random.randint(0, 100) > 50:
                transformLabel = "localPos"

            layoutEditor.wrapper.openCacheProxy(layoutEditor.getLayoutNameForCurrentTab(), True)
            layoutEditor.wrapper.editLayoutPostureNode(
                layoutEditor.getLayoutNameForCurrentTab(), 0, random.randint(0, 10), "boneName", transformLabel, keyFrames, keyValues, 0, 6
            )

        if key == QtCore.Qt.Key_K:
            print("Test editLayoutNodeAttribute")
            frameCount = int(random.random() * 10)
            keyFrames = list()
            keyValues = list()
            for _iKey in range(frameCount):
                keyFrames.append(random.random() * 100)
                keyValues.append([random.random(), random.random(), random.random()])
            layoutEditor.wrapper.openCacheProxy(layoutEditor.getLayoutNameForCurrentTab(), True)
            layoutEditor.wrapper.editLayoutNodeAttribute(layoutEditor.getLayoutNameForCurrentTab(), 1, "translate", keyFrames, keyValues)
            layoutEditor.wrapper.editLayoutNodeAttribute(layoutEditor.getLayoutNameForCurrentTab(), 1, "rotate", keyFrames, keyValues)
            layoutEditor.wrapper.editLayoutNodeAttribute(layoutEditor.getLayoutNameForCurrentTab(), 1, "vectorField", [], keyValues)

        if key == QtCore.Qt.Key_V:
            print("Test vector fields refresh")
            layoutEditor.wrapper.openCacheProxy(layoutEditor.getLayoutNameForCurrentTab(), True)
            layoutEditor.wrapper.updateCacheProxyTabVectorField(layoutEditor.getLayoutNameForCurrentTab(), "FakeVectorField")

        if key == QtCore.Qt.Key_Z:
            print("Test painted zone refresh")
            layoutEditor.wrapper.openCacheProxy(layoutEditor.getLayoutNameForCurrentTab(), True)
            layoutEditor.wrapper.updateCacheProxyTabPaintedZone(layoutEditor.getLayoutNameForCurrentTab(), "FakePaintedZone")

        if key == QtCore.Qt.Key_N:
            layoutEditor.wrapper.openCacheProxy(layoutEditor.getLayoutNameForCurrentTab(), True)
            layoutEditor.wrapper.updateCacheProxyTabPoptool("New", "FakePopTool")

    layoutEditor.signal_KeyPressed.connect(on_keyPressed)

    if app:
        mainWidget = app.activeWindow()
        if newInstance:
            # command line stand alone test... run our own event loop
            app.exec_()
        if usingDevkit:
            finishGolaem()
            finishGolaemProduct()

    layoutEditor.saveWindowPrefs()

main()

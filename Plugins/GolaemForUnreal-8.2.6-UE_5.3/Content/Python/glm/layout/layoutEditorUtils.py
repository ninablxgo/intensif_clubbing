from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
# *                                                                        *
# **************************************************************************

from builtins import str
from builtins import bytes
from builtins import range
from past.utils import old_div
from builtins import object
import os
import sys
import json
import copy
import math
import base64

import glm.golaemUtils

import glm.Qtpy.Qt
from glm.Qtpy.Qt import QtGui, QtCore, QtWidgets, Qt
from glm.Nodz import nodz_main, nodz_utils

from glm.qtUtils import QtBreadcrumbWidget

usingDevkit = True
try:
    from glm.devkit import *
except:
    errorMsg = "WARNING : Could not locate the Golaem python devkit, will fallback to autonomous, PLE tagged management. Please set your PYTHONPATH to include your Golaem install ./scripts folder"
    if sys.platform.startswith("win"):
        errorMsg += ", and PATH to include the ./bin folder."
    else:
        errorMsg += ", and LD_LIBRARY_PATH to include the ./lib folder."
    print(errorMsg)
    usingDevkit = False

import glm.layout.layoutAttributeEditor as layoutAttributeEditor
from glm.layout.layoutAttributeEditor import GlmAttributeFlags, GlmTransformType, GlmValueType
import fnmatch

if Qt.IsPyQt5 or Qt.IsPyQt4:
    signalObject = "PyQt_PyObject"
else:
    signalObject = "PyObject"


######################################################################
# Layout Editor Singelton
######################################################################


def getTheLayoutEditorInstance(parentWindow=None, wrapper=None):
    """
    Returns the instance singleton
    """
    global layoutEditorInstance
    try:
        layoutEditorInstance
    except NameError:
        layoutEditorInstance = LayoutEditor(parentWindow, wrapper)
        layoutEditorInstance.loadWindowPrefs()

    return layoutEditorInstance


######################################################################
# Node library
######################################################################
class LayoutNodesListWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super(LayoutNodesListWidget, self).__init__(parent)

        self.setDragEnabled(True)
        self.setViewMode(QtWidgets.QListView.IconMode)
        self.setIconSize(QtCore.QSize(32, 32))
        self.setFlow(QtWidgets.QListView.LeftToRight)
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setWrapping(True)

    def startDrag(self, supportedActions):
        item = self.currentItem()

        mimeData = QtCore.QMimeData()
        nodeText = str(item.data(5))  # setting directly text or tooltip is OK in standalone, but has an issue in Maya
        # nodeNameByteArray = QtCore.QByteArray(nodeText) #glm.Qtpy.Qt. prefix tested and does not work either
        nodeNameByteArray = QtCore.QByteArray(bytes(nodeText, encoding="utf8"))  # glm.Qtpy.Qt. prefix tested and does not work either
        mimeData.setData("glm/LayoutNode", nodeNameByteArray)

        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        drag.exec_(QtCore.Qt.MoveAction)


class LayoutUndoRedoState(object):
    def __init__(self):
        # identifier of nodz instance to work on (ref)
        self.editedGroupId = None
        self.layoutData = None
        self.runtimeChanges = True

        self.dirtyLayoutNodeId = None
        self.dirtyAssetsRepartition = False  # same in both ways


######################################################################
# QtBreadcrumbWidget
######################################################################
class QtBreadcrumbWidget(QtWidgets.QToolBar):
    def __init__(self, parent=None):
        super(QtBreadcrumbWidget, self).__init__(parent)
        self.setFixedHeight(24)
        self.setStyleSheet("QToolBar { border: 0px }")

    def clear(self):
        for action in self.actions():
            self.removeAction(action)
            # action._remove()

    def addItem(self, label, itemData):
        action = self.addAction(label)
        action.setData(itemData)

    def updateContainerHierarchy(self, theNodz, layoutName):
        self.clear()
        # self.addItem('test', None)
        if theNodz is not None:
            currentNodz = theNodz
            allParentNodz = list()
            while "parentNodz" in currentNodz.scene().userData:
                currentNodz = currentNodz.scene().userData["parentNodz"]
                allParentNodz.insert(0, currentNodz)

            # all nodes are groups/containers in this loop
            groupName = ""
            for levelNodz in allParentNodz:
                parentNodzUserData = levelNodz.scene().userData
                if "groupId" in parentNodzUserData:
                    groupNodeId = levelNodz.scene().userData["groupId"]
                    groupNode = levelNodz.scene().userData["groupNode"]
                    groupName = "{} (ID:{})".format(groupNode.userData["name"], groupNodeId)
                else:
                    groupName = layoutName
                self.addItem(groupName, levelNodz)
                self.addWidget(QtWidgets.QLabel(">"))

            groupNodeId = theNodz.scene().userData["groupId"]
            groupNode = theNodz.scene().userData["groupNode"]
            groupName = "{} (ID:{})".format(groupNode.userData["name"], groupNodeId)

            self.addItem(groupName, theNodz)

    def updatePos(self):
        if self.parentWidget() is not None:
            parentGeom = self.parentWidget().geometry()
            breadcrumbPos = parentGeom.topLeft()
            breadcrumbPos.setX(breadcrumbPos.x() + 3)
            breadcrumbPos.setY(breadcrumbPos.y() + 2)
            self.move(breadcrumbPos)
            self.setFixedWidth(parentGeom.width() - 6)

    def paintEvent(self, paintEvent):
        self.updatePos()
        super(QtBreadcrumbWidget, self).paintEvent(paintEvent)


######################################################################
# LayoutGraphicViewWidget contains * nodz of a single proxy and a breadcrumb
######################################################################
class LayoutGraphicViewWidget(QtWidgets.QWidget):

    signal_breadcrumbGoneBack = QtCore.Signal(signalObject)

    def __init__(self, parent=None):
        super(LayoutGraphicViewWidget, self).__init__(parent)

        self.breadcrumbWidget = QtBreadcrumbWidget(
            self
        )  # for some reasons, the breadcrumb needs to be parented to tab widget and not this view Widget (else not displayed)
        self.breadcrumbWidget.actionTriggered.connect(self.on_breadcrumbClicked)
        self.breadcrumbWidget.hide()

        self.mainNodz = None
        self.childrenNodz = dict()

        self.openViaOpenAction = False

        self.editedNodz = None  # nodz scene parent
        self.layoutName = ""
        self.isModified = False
        self.displayName = ""

        self.PLELabel = None
        # self.nodzList = dict()

        self.maxUndoStackDepth = 20
        self.undoStack = list()  # of LayoutUndoRedoState
        self.redoStack = list()  # of LayoutUndoRedoState

    def setEditEnabled(self, editEnabled):
        if self.mainNodz is not None:
            self.mainNodz.editEnabled = editEnabled
        for childNodz in list(self.childrenNodz.values()):
            if childNodz is not None:
                childNodz.editEnabled = editEnabled

    def displayPLEIconOnCurrentTab(self, iconPath, visible):
        if not visible and self.PLELabel is not None:
            self.PLELabel.setPixmap(None)
            self.PLELabel.hide()
        elif visible and (self.PLELabel is None or not self.PLELabel.isVisible()):
            if iconPath is not None:
                myPix = QtGui.QPixmap(iconPath)
                if self.PLELabel is None:
                    self.PLELabel = QtWidgets.QLabel(self)
                self.PLELabel.setPixmap(myPix)
                # self.PLELabel.setFixedSize(32,32)
                # self.PLELabel.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft)
                self.PLELabel.setGeometry(5, 25, 32, 32)
                self.PLELabel.setToolTip("This file is a PLE file")
                self.PLELabel.show()

    def updateBreadcrumb(self):
        if self.editedNodz is not None and "parentNodz" in self.editedNodz.scene().userData:
            self.breadcrumbWidget.updateContainerHierarchy(self.editedNodz, self.layoutName)
            self.breadcrumbWidget.setVisible(True)
        else:
            self.breadcrumbWidget.setVisible(False)

    def on_breadcrumbClicked(self, action):
        self.signal_breadcrumbGoneBack.emit(action.data())


class CustomEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Wheel:
            return True
        else:
            # standard event processing
            return QtCore.QObject.eventFilter(self, obj, event)


######################################################################
# Editor
######################################################################


class LayoutEditor(QtWidgets.QMainWindow):
    """
    The Golaem Layout Editor that allows to edit a golaem simulation cache Layout (*.gscl)
    """

    # signals
    signal_KeyPressed = QtCore.Signal(signalObject)  # raised when a key is pressed in a tab
    signal_NodeSelected = QtCore.Signal(signalObject, signalObject)  # raised when a node is selected
    signal_LayoutGraphChanged = QtCore.Signal(signalObject, bool)  # raised when the graph layout changes (clear/load)
    signal_LayoutRootChanged = QtCore.Signal(signalObject, signalObject)  # raised when the root node was changed in the graph. Provides the node name in parameter
    signal_RigOrPostureCreate = QtCore.Signal(signalObject, int)  # raised when a contextual action is called on a Rig or Posture node
    signal_blindDataParametersCreate = QtCore.Signal(signalObject, int)  # raised when a contextual action is called on a BlindData node
    signal_TrajectoriesMeshExport = QtCore.Signal(signalObject, int)  # raised when a contextual action is called on an Edit Trajectory node
    signal_TrajectoriesSrcExport = QtCore.Signal(signalObject, int)  # raised when a contextual action is called on an Edit Trajectory node
    signal_TrajectoriesDstExport = QtCore.Signal(signalObject, int)  # raised when a contextual action is called on an Edit Trajectory node
    signal_TrajectoriesSrcImport = QtCore.Signal(signalObject, int)  # raised when a contextual action is called on an Edit Trajectory node
    signal_TrajectoriesDstImport = QtCore.Signal(signalObject, int)  # raised when a contextual action is called on an Edit Trajectory node
    signal_KeyframedLocatorsCreate = QtCore.Signal(signalObject, int)  # raised when a contextual action is called to create locator on node's keyframed attributes
    signal_KeyframedLocatorsDelete = QtCore.Signal(signalObject, int)  # raised when a contextual action is called to delete locator on node's keyframed attributes
    signal_LayoutNodeChanged = QtCore.Signal(signalObject, signalObject)  # raised when a node was changed in the graph (edited/enabled/disabled). Provides the node name in parameter
    signal_LayoutParameterChanged = QtCore.Signal(signalObject)  # raised when a parameter in the layout was changed
    signal_LayoutSnapToPoptoolDropDownChanged = QtCore.Signal(signalObject, signalObject, signalObject)  # raised when a dropdown changes value (snapTo, etc)
    signal_LayoutSnapToSlotsUpdate = QtCore.Signal(signalObject, signalObject, signalObject)
    signal_LayoutVectorFieldDropDownChanged = QtCore.Signal(signalObject, signalObject)  # raised when a dropdown changes value (snapTo, etc)
    signal_LayoutVectorFieldUpdate = QtCore.Signal(signalObject, signalObject)
    signal_LayoutPaintedZoneDropDownChanged = QtCore.Signal(signalObject, signalObject)  # raised when a dropdown changes value (snapTo, etc)
    signal_LayoutPaintedZoneUpdate = QtCore.Signal(signalObject, signalObject)
    signal_LayoutEditTrajectoryMeshUpdate = QtCore.Signal(signalObject, signalObject, int)
    # signal_LayoutColorChannelDropDownChanged = QtCore.Signal(signalObject, signalObject) #raised when a dropdown changes value (snapTo, etc)
    signal_LayoutNodePreEdited = QtCore.Signal(signalObject, signalObject)  # raised when a node was edited
    signal_LayoutNodeCreated = QtCore.Signal(signalObject, signalObject)  # raised when a node was created by the user
    signal_LayoutGraphLoaded = QtCore.Signal(int, signalObject)  # raised when the current layout is loaded from a file
    signal_LayoutGraphSaved = QtCore.Signal(int, signalObject)  # raised when the current layout is saved in a file
    signal_LayoutCacheSizeChanged = QtCore.Signal(signalObject, int)  # raised when the user change the cache size
    signal_LayoutEndCompoundInteraction = QtCore.Signal(signalObject)

    def __init__(self, parent=None, wrapper=None):  # TODO: put config files path here
        super(LayoutEditor, self).__init__(parent=parent)

        if usingDevkit:
            initGolaem()

        # flag 2 is generated for snapToTarget / poptool list
        # flag 4 _uiOperationModeComboBox
        self.operationModeList = ["Add", "Set"]
        # flag 8 _uiGroundAdaptationModeComboBox
        self.groundAdaptationModeList = ["None", "Snap Height", "Snap Height And Ori", "With IK"]
        # flag 16384 _uiOnOffComboBox
        self.onOffList = ["Off", "On"]
        # flag 524288 _uiColorChannelComboBox
        self.colorChannelList = ["Red Channel", "Green Channel", "Blue Channel", "Alpha Channel", "RGB Vector"]
        # flag _uiRotateOrderComboBox
        self.rotateOrderList = ["XYZ", "YZX", "ZXY", "XZY", "YXZ", "ZYX"]

        self.layoutNodesDefinition = None
        self.layoutNodesList = None
        self.layoutNodesIconList = None
        self.layoutNodesTooltipList = None
        self.layoutNodesDockWidget = None
        self.layoutSearchDockWidget = None
        self.layoutSearchTypeComboBox = None  # to get back the type of search
        self.layoutSearchLineEdit = None
        self.layoutCacheStatusDockWidget = None
        self.layoutCacheStatusLabel = None
        self.layoutCacheCacheSizeSpinBox = None

        # attribute editor widget
        self.layoutAttributeEditorDockWidget = None
        self.layoutAttributeEditorDockMainWidget = None
        self.layoutEmptyAttributeEditorWidget = None
        self.layoutActiveAttributeEditorWidget = None
        self.toggleSyncSelectionAction = None

        self.centralWidget = None
        self.editorTabWidget = None
        self.emptyTabWidget = None
        self.layoutViewTabWidgets = (
            list()
        )  # list of the view widget hold the nodz instance for each tab. The index of the tab is index of the nodz in nodzInstances. 'Et Vice Et Versa'.
        self.poptools = ["Manual Entry"]
        self.entityTypes = ["All"]
        self.nodesToCopyOriginNodz = None
        self.nodesToCopy = list()
        self.vectorFields = ["None"]  # list of all vector fields names in the scene
        self.paintedZones = ["None"]  # list of all painted zones names in the scene
        self.bonesNames = ["None"]  # list of bones for the current active UI

        self.attributeEditorPos = None
        self.attributeEditorHeight = None

        self.blockUndoRedoSignals = False

        self.blockRootForward = False

        self.syncSelection = True  # true to sync nodes selection with the main DCC

        self.maxTablesDisplayCount = 50

        self.wrapper = None
        self.PLEIconPath = None

        self.initEditor(wrapper)

    def __del__(self):
        self.finishGolaem()

    def finishGolaem(self):
        if usingDevkit:
            finishGolaem()

    def loadWindowPrefs(self):
        # load window prefs:
        if self.wrapper is not None:
            self.wrapper.loadWindowPref(self.objectName(), self)

    def saveWindowPrefs(self):
        # save window prefs:
        if self.wrapper is not None:
            self.wrapper.saveWindowPref(self.objectName(), self)

    def initEditor(self, editorWrapper):
        self.wrapper = editorWrapper

        # init layout nodes definition
        if self.layoutNodesDefinition is None:
            self.layoutNodesDefinition = list()
            layoutNodesDefinitionFile = nodz_utils._loadConfig(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), "golaem_layoutNodes_definition.json")
            )
            self.layoutNodesDefinition = layoutNodesDefinitionFile["GolaemLayoutNodes"]

        if self.layoutNodesList is None:
            # extract the node list:
            self.layoutNodesList = list()
            self.layoutNodesTooltipList = list()
            glmLayoutNodesListTypesIndices = list()
            self.layoutNodesList.append("Notes")  # Notes node
            self.layoutNodesTooltipList.append("Annotate the Layout Graph")
            glmLayoutNodesListTypesIndices.append(-2)  # -2 to make sure it will always be displayed first
            self.layoutNodesList.append("EntitySelector")  # the basic node to select entities
            self.layoutNodesTooltipList.append("Define a selection or a selection filter")
            glmLayoutNodesListTypesIndices.append(-1)  # -1 to make sure it will always be displayed second
            for GolaemlayoutNode in self.layoutNodesDefinition:
                nodeTypeIndex = GolaemlayoutNode["type"]
                if nodeTypeIndex != layoutAttributeEditor.GlmTransformType.Note:
                    self.layoutNodesList.append(GolaemlayoutNode["type_name"])
                    self.layoutNodesTooltipList.append(GolaemlayoutNode["tooltip"])
                    glmLayoutNodesListTypesIndices.append(nodeTypeIndex)

        # extract icons and tooltips
        self.iconsDir = ""
        if self.wrapper is not None:
            self.iconsDir = self.wrapper.getIconsDir()
            if self.layoutNodesList is not None:
                self.layoutNodesIconList = list()
                for aNode in self.layoutNodesList:
                    # icon
                    iconPath = os.path.join(self.iconsDir, aNode + ".png").replace("\\", "/")
                    if os.path.isfile(iconPath):
                        self.layoutNodesIconList.append(QtGui.QIcon(iconPath))
                    else:
                        print(iconPath + " does not exist")
                        self.layoutNodesIconList.append(None)  # to avoid shifting
                    # tooltip


        # init editorMainWindow
        if self.toggleSyncSelectionAction is None:
            self.setWindowTitle("Golaem Layout Editor")
            self.setObjectName("GolaemLayoutEditor")
            self.setWindowIcon(
                QtGui.QIcon(os.path.join(self.iconsDir, os.pardir, "buttonSimulationCacheLayout.png").replace("\\", "/"))
            )
            self.resize(800, 500)
            self.installEventFilter(
                self
            )  # catch children key event filter not processed yet, forward to layout attribute editor input processing

            # Toolbar
            toolBar = QtWidgets.QToolBar("Golaem Toolbar", self)
            toolBar.setObjectName("GolaemLayoutEditorToolbar")
            toolBar.setMovable(0)
            toolBar.setFloatable(0)

            # statusBar text is settable via the wrapper
            self.statusBar = QtWidgets.QStatusBar(self)
            self.setStatusBar(self.statusBar)

            # New / Save / Save As buttons
            newAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, os.pardir, "editors", "new.png").replace("\\", "/")),
                "New Layout",
                self,
            )
            newAction.triggered.connect(self.on_newAction)
            toolBar.addAction(newAction)
            openAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, os.pardir, "editors", "open.png").replace("\\", "/")),
                "Open Layout",
                self,
            )
            openAction.triggered.connect(self.on_openAction)
            toolBar.addAction(openAction)
            saveAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, os.pardir, "editors", "save.png").replace("\\", "/")),
                "Save Layout",
                self,
            )
            saveAction.triggered.connect(self.on_saveAction)
            toolBar.addAction(saveAction)
            saveAsAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, os.pardir, "editors", "saveAs.png").replace("\\", "/")),
                "Save As Layout",
                self,
            )
            saveAsAction.triggered.connect(self.on_saveAsAction)
            toolBar.addAction(saveAsAction)

            toolBar.addSeparator()

            clearAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, os.pardir, "editors", "delete.png").replace("\\", "/")),
                "Clear Layout",
                self,
            )
            clearAction.triggered.connect(self.on_clearAction)
            toolBar.addAction(clearAction)

            toolBar.addSeparator()

            configureAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, os.pardir, "buttonCrowdSettings.png").replace("\\", "/")),
                "Configure...",
                self,
            )
            configureAction.triggered.connect(self.on_configureAction)
            toolBar.addAction(configureAction)

            toolBar.addSeparator()

            # Toggle maya entities selection
            self.toggleSyncSelectionAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, "editorSyncSelection.png").replace("\\", "/")),
                "Toggle synchronize Selection",
                self,
            )
            self.toggleSyncSelectionAction.triggered.connect(self.onToggleSyncSelection)
            self.toggleSyncSelectionAction.setCheckable(True)
            self.toggleSyncSelectionAction.setChecked(self.syncSelection)
            toolBar.addAction(self.toggleSyncSelectionAction)

            toolBar.addSeparator()

            # Frame all / visible / 1:1
            frameAllAction = QtWidgets.QAction(QtGui.QIcon(os.path.join(self.iconsDir, "editorFrameAll.png").replace("\\", "/")), "Frame all", self)
            frameAllAction.triggered.connect(self.onFrameAllAction)
            toolBar.addAction(frameAllAction)
            frameSelAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, "editorFrameSelection.png").replace("\\", "/")),
                "Frame selection",
                self,
            )
            frameSelAction.triggered.connect(self.onFrameSelectedAction)
            toolBar.addAction(frameSelAction)
            realSizeAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, "editorRealSize.png").replace("\\", "/")),
                "Display the real size",
                self,
            )
            realSizeAction.triggered.connect(self.onRealSizeAction)
            toolBar.addAction(realSizeAction)

            toolBar.addSeparator()

            entityInspectorAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, "editorEntityInspector.png").replace("\\", "/")),
                "Open the Entity Inspector",
                self,
            )
            entityInspectorAction.triggered.connect(self.onEntityInspectorAction)
            toolBar.addAction(entityInspectorAction)

            toolBar.addSeparator()

            # "Toggle Layout Nodes Library visibility"
            toggleSearchAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, "editorSearch.png").replace("\\", "/")),
                "Toggle Search Field Visibility",
                self,
            )
            toggleSearchAction.triggered.connect(self.onToggleSearchVisibility)
            toolBar.addAction(toggleSearchAction)
            toggleLibraryAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, "editorPrimaryLibrary.png").replace("\\", "/")),
                "Toggle Layout Nodes Library Visibility",
                self,
            )
            toggleLibraryAction.triggered.connect(self.onToggleLibraryVisibility)
            toolBar.addAction(toggleLibraryAction)
            toggleStatusAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, "editorSecondaryLibrary.png").replace("\\", "/")),
                "Toggle Layout Cache Status Visibility",
                self,
            )
            toggleStatusAction.triggered.connect(self.onToggleStatusVisibility)
            toolBar.addAction(toggleStatusAction)
            toggleAttributesAction = QtWidgets.QAction(
                QtGui.QIcon(os.path.join(self.iconsDir, "editorAttribute.png").replace("\\", "/")),
                "Toggle Layout Attribute Editor",
                self,
            )
            toggleAttributesAction.triggered.connect(self.onToggleAttributesVisibility)
            toolBar.addAction(toggleAttributesAction)

            self.PLEIconPath = os.path.join(self.iconsDir, "GolaemPLELicense.png").replace("\\", "/")
            isPLE = True
            if usingDevkit:
                isPLE = usingGolaemPLELicense()
            if isPLE:
                toolBar.addSeparator()
                PLEAction = QtWidgets.QAction(
                    QtGui.QIcon(self.PLEIconPath),
                    "You are using a Personal Learning license, beware that files saved with the editor will be contaminated by PLE.",
                    self,
                )
                toolBar.addAction(PLEAction)

            toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
            self.addToolBar(toolBar)

        if self.layoutSearchDockWidget is None:
            self.layoutSearchDockWidget = QtWidgets.QDockWidget("Layout Search Dock Widget", self)
            self.layoutSearchDockWidget.setWindowTitle("Search Entities and Nodes")
            self.layoutSearchDockWidget.setObjectName("GolaemLayoutSearchWidget")

            innerWidget = QtWidgets.QWidget(self.layoutSearchDockWidget)

            # set a horizontal layout, a line edit & a QComboBox dropdown to search entities or nodes
            hLayout = QtWidgets.QHBoxLayout()
            hLayout.setContentsMargins(3, 3, 3, 3)

            self.layoutSearchTypeComboBox = QtWidgets.QComboBox(self.layoutSearchDockWidget)
            self.layoutSearchTypeComboBox.addItem("Entity IDs")
            self.layoutSearchTypeComboBox.addItem("Node Names")
            hLayout.addWidget(self.layoutSearchTypeComboBox)

            self.layoutSearchLineEdit = QtWidgets.QLineEdit(self.layoutSearchDockWidget)
            self.layoutSearchLineEdit.returnPressed.connect(self.onSearchItems)
            # self.layoutSearchLineEdit.setFixedHeight(32)
            # self.layoutSearchLineEdit.setMinimumWidth(32)

            hLayout.addWidget(self.layoutSearchLineEdit)

            innerWidget.setLayout(hLayout)
            # innerWidget.setMaximumHeight(63)
            innerWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
            self.layoutSearchDockWidget.setWidget(innerWidget)
            self.layoutSearchDockWidget.setLayout(hLayout)
            self.layoutSearchDockWidget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.layoutSearchDockWidget)

        if self.layoutAttributeEditorDockWidget is None:
            # build a parent widget that can toggle between [Select a node for edition] and the editor for the selected node
            self.layoutAttributeEditorDockWidget = QtWidgets.QDockWidget("Node Attribute Editor", self)
            self.layoutAttributeEditorDockWidget.setWindowTitle("Attribute Editor")
            self.layoutAttributeEditorDockWidget.setObjectName("GolaemLayoutAttributeEditor")

            self.layoutAttributeEditorDockMainWidget = QtWidgets.QWidget()
            self.layoutAttributeEditorDockMainWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Expanding)
            attributeEditorMainLayout = QtWidgets.QVBoxLayout()
            attributeEditorMainLayout.setContentsMargins(0, 0, 0, 0)
            self.layoutAttributeEditorDockMainWidget.setLayout(attributeEditorMainLayout)

            # need a single widget as main one, to avoid switching widget via setWidget, and killing the needed constant width while editing (avoid moving nodes at select)
            self.layoutAttributeEditorDockWidget.setWidget(self.layoutAttributeEditorDockMainWidget)

            # now add the empty widget displaying the message to the main widget of this dock
            self.layoutEmptyAttributeEditorWidget = QtWidgets.QWidget(self.layoutAttributeEditorDockMainWidget)
            emptyAttributeEditorLayout = QtWidgets.QVBoxLayout()
            emptyAttributeEditorLabel = QtWidgets.QLabel("<center>Select a Node to edit it</center>", self.layoutAttributeEditorDockMainWidget)
            emptyAttributeEditorLabel.setWordWrap(True)
            emptyAttributeEditorLabel.setMinimumWidth(20)
            emptyAttributeEditorLabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            emptyAttributeEditorLayout.addWidget(emptyAttributeEditorLabel)

            self.layoutEmptyAttributeEditorWidget.setLayout(emptyAttributeEditorLayout)
            self.layoutEmptyAttributeEditorWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

            self.layoutAttributeEditorDockMainWidget.layout().addWidget(self.layoutEmptyAttributeEditorWidget)

            self.layoutAttributeEditorDockMainWidget.setMinimumWidth(284)
            self.layoutAttributeEditorDockMainWidget.setMaximumWidth(999)
            self.layoutAttributeEditorDockWidget.setMinimumWidth(284)
            self.layoutAttributeEditorDockWidget.setMaximumWidth(999)

            # self.layoutAttributeEditorDockWidget.setWidget(self.layoutEmptyAttributeEditorWidget)
            # We want to ignore content dynamic resize, or it will mess up node position when clicking on it
            # self.layoutAttributeEditorDockWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Expanding)
            # self.layoutAttributeEditorDockWidget.setMinimumWidth(355) # will be set to 50 at first show, but need to be shown first to retain the 355 as opening width
            # self.layoutAttributeEditorDockWidget.setMaximumWidth(481)
            self.layoutAttributeEditorDockWidget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.layoutAttributeEditorDockWidget)

        if self.layoutNodesDockWidget is None:
            self.layoutNodesDockWidget = QtWidgets.QDockWidget("Layout Nodes Dock Widget", self)
            self.layoutNodesDockWidget.setWindowTitle("Layout Nodes Library")
            self.layoutNodesDockWidget.setObjectName("GolaemLayoutNodesLibrary")

            layoutNodesLibraryWidget = LayoutNodesListWidget(self.layoutNodesDockWidget)  # QtWidgets.QListWidget
            vLayout = QtWidgets.QVBoxLayout()
            vLayout.setContentsMargins(3, 3, 3, 3)
            layoutNodesLibraryWidget.setLayout(vLayout)
            layoutNodesLibraryWidget.setMinimumHeight(38)
            layoutNodesLibraryWidget.setMinimumWidth(38)

            layoutNodesLibraryWidget.itemDoubleClicked.connect(self.libraryNodeItemDoubleClicked)

            # set a Maximum height according to current window size ?
            # maximum height is set here and set again when showing
            # layoutNodesLibraryWidget.setMaximumHeight(38)

            # layoutNodesLibraryWidget.setSize(36, layoutNodesLibraryWidget.width())
            # vLayout.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
            # layoutNodesLibraryWidget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
            # self.layoutNodesDockWidget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

            for aNode in self.layoutNodesList:
                # iconPath = os.path.join(self.iconsDir, aNode + ".png").replace("\\", "/")
                # indentation fix
                moveListItem = QtWidgets.QListWidgetItem()
                moveListItem.setData(5, aNode)
                moveListItem.setSizeHint(QtCore.QSize(32, 32))
                nodeIndex = self.layoutNodesList.index(aNode)
                if self.layoutNodesIconList is not None:
                    icon = self.layoutNodesIconList[nodeIndex]
                    if icon is not None:
                        moveListItem.setIcon(icon)
                # tooltip
                toolTip = aNode + ': ' + self.layoutNodesTooltipList[nodeIndex]
                moveListItem.setToolTip(toolTip)
                layoutNodesLibraryWidget.addItem(moveListItem)

            self.layoutNodesDockWidget.setWidget(layoutNodesLibraryWidget)
            self.layoutNodesDockWidget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.layoutNodesDockWidget)

        if self.layoutCacheStatusDockWidget is None:
            self.layoutCacheStatusDockWidget = QtWidgets.QDockWidget("Layout Cache Status Dock Widget", self)
            self.layoutCacheStatusDockWidget.setWindowTitle("Layout Cache Status")
            self.layoutCacheStatusDockWidget.setObjectName("GolaemLayoutCacheStatus")

            innerWidget = QtWidgets.QWidget(self.layoutCacheStatusDockWidget)

            hLayout = QtWidgets.QHBoxLayout()
            hLayout.setContentsMargins(3, 3, 3, 3)

            # content widget(s)
            self.layoutCacheStatusLabel = QtWidgets.QLabel()
            self.layoutCacheStatusLabel.setText("Cache usage: 0MB (0%). Total: ")
            hLayout.addWidget(self.layoutCacheStatusLabel)

            self.layoutCacheCacheSizeSpinBox = QtWidgets.QSpinBox()
            self.layoutCacheCacheSizeSpinBox.setRange(0, 32768)
            self.layoutCacheCacheSizeSpinBox.setValue(1024)  # default cache size: 1Go
            self.layoutCacheCacheSizeSpinBox.setSuffix("MB")
            self.layoutCacheCacheSizeSpinBox.editingFinished.connect(self.onCacheSizeChanged)
            hLayout.addWidget(self.layoutCacheCacheSizeSpinBox)

            innerWidget.setLayout(hLayout)
            # innerWidget.setMaximumHeight(63)
            innerWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
            self.layoutCacheStatusDockWidget.setWidget(innerWidget)
            self.layoutCacheStatusDockWidget.setLayout(hLayout)
            self.layoutCacheStatusDockWidget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.layoutCacheStatusDockWidget)

        # central widget
        if self.centralWidget is None:
            self.centralWidget = QtWidgets.QWidget(self)
            centralLayout = QtWidgets.QVBoxLayout()
            centralLayout.setContentsMargins(0, 0, 0, 0)
        # tab widget
        if self.editorTabWidget is None:
            self.editorTabWidget = QtWidgets.QTabWidget(self)

            self.editorTabWidget.tabBar().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.editorTabWidget.tabBar().customContextMenuRequested.connect(self.on_customContextMenuRequested)

            self.editorTabWidget.setTabsClosable(True)
            # self.editorTabWidget.currentChanged.connect(self.on_tabChanged)
            self.editorTabWidget.tabCloseRequested.connect(self.on_tabCloseRequested)
            self.editorTabWidget.hide()
            # self.setCentralWidget(self.editorTabWidget)
            if self.emptyTabWidget is None:
                self.emptyTabWidget = QtWidgets.QWidget(self)
                emptyTabLayout = QtWidgets.QVBoxLayout()
                emptyTabLabel = QtWidgets.QLabel(
                    "<center>Select a Simulation Cache Proxy Node, load a Layout File <br>or create a new Layout to get the party started</center>",
                    self,
                )
                emptyTabLayout.addWidget(emptyTabLabel)
                self.emptyTabWidget.setLayout(emptyTabLayout)
                self.emptyTabWidget.show()
            centralLayout.addWidget(self.editorTabWidget)
            centralLayout.addWidget(self.emptyTabWidget)
            self.centralWidget.setLayout(centralLayout)
            self.centralWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.setCentralWidget(self.centralWidget)

        # connect 'set as modified' signals
        self.signal_LayoutGraphChanged.connect(self.on_setModified)
        self.signal_LayoutNodeChanged.connect(self.on_setModified)
        self.signal_LayoutParameterChanged.connect(self.on_setModified)
        self.signal_LayoutRootChanged.connect(self.on_setModified)
        self.signal_LayoutNodeCreated.connect(self.on_setModified)

        # connect 'unset as modified' signals
        self.signal_LayoutGraphLoaded.connect(self.on_clearModified)
        self.signal_LayoutGraphSaved.connect(self.on_clearModified)

        # connect the wrapper
        if self.wrapper is not None:
            self.wrapper.setLayoutEditor(self)

    def keyReleaseEvent(self, event):
        """
        Clear the key from the pressed key list.

        """
        # when switching from editedNodz while maintaining control, the key is never released by the nodz, let's do this here
        # print('releasing key {} in LayoutEditor'.format(event.key()))
        currentNodz = self.getCurrentNodz()
        if currentNodz is not None:
            currentNodz.keyReleaseEvent(event)

    def libraryNodeItemDoubleClicked(self, item):
        # print ("Item has been double clicked : {}".format(item.toolTip()))
        currentTabName = self.getCurrentTabName()
        selectedEntitiesIds = self.wrapper.getSelectedEntities(currentTabName)
        if currentTabName != "":
            self.addOrEditLayoutTransformation(
                currentTabName,
                selectedEntitiesIds,
                item.data(5),
                parameterName=None,
                parameterValue=None,
                frame=None,
                mode=0,
            )

    def eventFilter(self, widget, event):
        if event.type() == QtCore.QEvent.KeyPress:
            return self.on_keyPressed(event.key())
        return QtWidgets.QWidget.eventFilter(self, widget, event)

    def onDockResized(self, nodzInst):
        print("Dock resized")

    def show(self):
        super(LayoutEditor,self).show()
        self.activateWindow()
        self.raise_()
        # self.layoutNodesDockWidget.widget().setMaximumHeight(9999) # does work on standalone, but not in Maya
        if self.isMinimized():
            self.showNormal()

    def hide(self):
        self.saveWindowPrefs()  # save prefs each time we hide the editor
        super(LayoutEditor,self).hide()

    def setStatusMessage(self, text):
        self.statusBar.showMessage(text)

    def setCacheStatus(self, cacheProxyName, cacheStatus):
        prevBlockSignalsStatus = self.signalsBlocked()
        self.blockSignals(True)

        # cacheStatus is a multi array:
        # [
        #     [cacheMemoryGlobalUsage, cacheMemoryGlobalSize],
        #     [cacheFirstFrame, cacheLastFrame],
        #     [
        #         [nodeID, [nodeFramesInCache, ...],
        #         [nodeID, [nodeFramesInCache, ...],
        #         [nodeID, [nodeFramesInCache, ...]
        #     ]
        # ]

        # global status
        globalStatus = cacheStatus[0]
        percentUsed = 100
        if globalStatus[1] > 0:
            percentUsed = int(old_div(100 * globalStatus[0], globalStatus[1]))
        self.layoutCacheStatusLabel.setText("Cache usage: {}MB ({}%). Total: ".format(globalStatus[0], percentUsed))
        self.layoutCacheCacheSizeSpinBox.setValue(globalStatus[1])

        # per node status
        cacheFrameRange = cacheStatus[1]
        nodesStatus = cacheStatus[2]
        if len(cacheProxyName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                    # iterate on scene nodes
                    for node in nodzInst.scene().nodes:
                        currentNodeInst = nodzInst.scene().nodes[node]
                        currentNodeID = currentNodeInst.userData["ID"]
                        currentNodeAttributes = []
                        if "attributes" in currentNodeInst.userData:
                            currentNodeAttributes = currentNodeInst.userData["attributes"]

                        # find the status for the current node...
                        nodeFrames = []
                        for nodeStatus in nodesStatus:
                            if nodeStatus[0] == currentNodeID:
                                nodeFrames = nodeStatus[1]
                        nodeCacheStatus = "{} cached frames [".format(len(nodeFrames))
                        charCount = 8  # config
                        framesPerChar = old_div((cacheFrameRange[1] - cacheFrameRange[0] + float(1)), charCount)
                        for iStatusCharacter in range(charCount):
                            # find if there are frames in this range
                            foundAtLeastOneFrame = False
                            startFrame = int(math.floor(cacheFrameRange[0] + int(iStatusCharacter * framesPerChar)))
                            endFrame = int(math.ceil(cacheFrameRange[0] + int((iStatusCharacter + 1) * framesPerChar)))
                            for iFrameInRange in range(startFrame, endFrame):
                                if iFrameInRange in nodeFrames:
                                    foundAtLeastOneFrame = True
                                    break
                            if foundAtLeastOneFrame:
                                nodeCacheStatus = "{}-".format(nodeCacheStatus)
                            else:
                                nodeCacheStatus = "{} ".format(nodeCacheStatus)
                        nodeCacheStatus = "{}]".format(nodeCacheStatus)

                        cacheStatusAttributeIndex = 1
                        for currentAttr in currentNodeAttributes:  # 1 attribute for the name, then 1 for each attribute
                            doIncrement = True
                            if "flags" in currentAttr:
                                attributeFlags = currentAttr["flags"]
                                if (attributeFlags is not None) and (attributeFlags & GlmAttributeFlags._uiHidden):
                                    doIncrement = False
                            if doIncrement:
                                cacheStatusAttributeIndex = cacheStatusAttributeIndex + 1

                        if "entities" in currentNodeInst.userData:
                            cacheStatusAttributeIndex = cacheStatusAttributeIndex + 4  # selector has 4 attributes
                        elif currentNodeInst.userData["type"] == layoutAttributeEditor.GlmTransformType.Group:
                            cacheStatusAttributeIndex -= 2  # group hides its rootId and childrenNodeIds attributes
                        if len(currentNodeInst.attrs) <= cacheStatusAttributeIndex:
                            if len(nodeFrames) > 0:  # adding a cache status attribute ONLY once there is at least 1 frame in cache for this node
                                nodzInst.createAttribute(
                                    node=currentNodeInst,
                                    name=nodeCacheStatus,
                                    index=cacheStatusAttributeIndex,
                                    preset="attr_preset_LayoutCacheStatus",
                                    plug=False,
                                    socket=False,
                                    dataType=str,
                                )
                        elif currentNodeInst.attrs[cacheStatusAttributeIndex] != nodeCacheStatus:
                            nodzInst.editAttribute(node=currentNodeInst, index=cacheStatusAttributeIndex, newName=nodeCacheStatus)

        self.blockSignals(prevBlockSignalsStatus)

    def focusSelection(self):
        currentNodz = self.getCurrentNodz()
        if currentNodz is not None:
            currentNodz._focus()

    def on_dragEvent(self, dragNDropEvent, nodzInst):
        if dragNDropEvent.mimeData().hasFormat("glm/LayoutNode"):
            nodzInst.dragAccept = True
        else:
            nodzInst.dragAccept = False

    def on_dragMoveEvent(self, dragNDropEvent, nodzInst):
        if dragNDropEvent.mimeData().hasFormat("glm/LayoutNode"):
            nodzInst.dragMoveAccept = True

            # almost copy paste from nodz
            nodzInst.currentHoveredLink = None
            eventPos = dragNDropEvent.pos()
            eventPosF = nodzInst.mapToScene(eventPos)
            mbb = nodz_utils._createPointerBoundingBox(pointerPos=eventPosF.toPoint(), bbSize=nodzInst.config["mouse_bounding_box"])
            hoveredItems = nodzInst.scene().items(mbb)
            lowestDistance2 = 10000000000
            for hoveredItem in hoveredItems:
                if isinstance(hoveredItem, nodz_main.ConnectionItem):
                    # Check that link accepts plug-nodeSocket and nodePlug-socket connections
                    # use theNodeSocket to test accepts, as plugs must be empty / not at max connection
                    fromScenePos = eventPosF
                    toScenePos = hoveredItem.center()
                    deltaPos = toScenePos - fromScenePos
                    distance2 = deltaPos.x() * deltaPos.x() + deltaPos.y() * deltaPos.y()
                    if nodzInst.currentHoveredLink is None or distance2 < lowestDistance2:
                        lowestDistance2 = distance2
                        nodzInst.currentHoveredLink = hoveredItem

            nodzInst.currentHoveredNodeForDrop = None
            mbb = nodz_utils._createPointerBoundingBox(pointerPos=eventPosF.toPoint(), bbSize=nodzInst.config["mouse_bounding_box"])
            hoveredItems = nodzInst.scene().items(mbb)
            lowestDistance2 = 10000000000
            for hoveredItem in hoveredItems:
                if isinstance(hoveredItem, nodz_main.NodeItem) and hoveredItem.acceptNodeDrop:
                    fromScenePos = eventPosF
                    toScenePos = hoveredItem.center()
                    deltaPos = toScenePos - fromScenePos
                    distance2 = deltaPos.x() * deltaPos.x() + deltaPos.y() * deltaPos.y()
                    if nodzInst.currentHoveredNodeForDrop is None or distance2 < lowestDistance2:
                        lowestDistance2 = distance2
                        nodzInst.currentHoveredNodeForDrop = hoveredItem

            nodzInst.scene().updateScene()

        else:
            nodzInst.dragMoveAccept = False

    def on_dropEvent(self, dragNDropEvent, nodzInst):
        if dragNDropEvent.mimeData().hasFormat("glm/LayoutNode"):
            # self.wrapper.layoutPreDo(self.getLayoutNameForCurrentTab())
            # create a node where the item was dropped
            position = dragNDropEvent.pos()
            positionF = nodzInst.mapToScene(position.x(), position.y())
            nodeTypeName = dragNDropEvent.mimeData().data("glm/LayoutNode").data().decode("utf-8")
            createdNode = self.GolaemLayoutNodeCreator(nodzInst, nodeTypeName, positionF)
            nodzInst.dropAccept = True
            # self.wrapper.layoutPostDo(self.getLayoutNameForCurrentTab())

            runtimeChanges = False

            if nodzInst.currentHoveredLink is not None:
                fromNode = nodzInst.currentHoveredLink.plugNode
                fromAttr = nodzInst.currentHoveredLink.plugAttr
                toNode = nodzInst.currentHoveredLink.socketNode
                toAttr = nodzInst.currentHoveredLink.socketAttr

                theNodePlugAttr = iter(createdNode.plugs.values()).next().attribute
                theNodeSocketAttr = iter(createdNode.sockets.values()).next().attribute

                removedConnections = list()
                addedConnections = list()

                # pack the layout update call in a single call
                nodzInst.signal_StartCompoundInteraction.emit(nodzInst)
                removedConnections.append(nodz_main.ConnectionInfo(nodzInst.currentHoveredLink))
                nodzInst.currentHoveredLink._remove()

                addedConnections.append(nodz_main.ConnectionInfo(nodzInst.createConnection(fromNode, fromAttr, createdNode.name, theNodeSocketAttr)))
                addedConnections.append(nodz_main.ConnectionInfo(nodzInst.createConnection(createdNode.name, theNodePlugAttr, toNode, toAttr)))

                nodzInst.signal_EndCompoundInteraction.emit(nodzInst, True)

                nodzInst.signal_UndoRedoConnectNodes.emit(nodzInst, removedConnections, addedConnections)
                runtimeChanges = True

            if nodzInst.currentHoveredNodeForDrop is not None:
                nodzInst.selectedNodes = list()
                nodzInst.selectedNodes.append(createdNode.name)
                nodzInst.signal_dropOnNode.emit(nodzInst, nodzInst.currentHoveredNodeForDrop.name)  # can get back selection from nodzInst

            # most of the time dropped nodes are not in flow, except if on a hovered link
            self.stackUndo(self.getCurrentTabIndex(), None, False, runtimeChanges)  # added nodes are detected by propagation

        else:
            nodzInst.dropAccept = False

    def clearUndoStack(self, tabIndex):
        if self.blockUndoRedoSignals:
            return

        if tabIndex < 0 or tabIndex > len(self.layoutViewTabWidgets):
            print("Error: no tab selected")
            return

        tabWidget = self.layoutViewTabWidgets[tabIndex]
        tabWidget.undoStack = list()
        tabWidget.redoStack = list()

    def stackUndo(self, tabIndex, dirtyNodeId=None, dirtyAssets=False, runtimeChanges=True):
        if self.blockUndoRedoSignals:
            return

        if tabIndex < 0 or tabIndex > len(self.layoutViewTabWidgets):
            print("Error: no tab selected")
            return

        tabWidget = self.layoutViewTabWidgets[tabIndex]

        newState = LayoutUndoRedoState()
        newState.layoutData = copy.deepcopy(
            self.buildGolaemLayoutFile(tabWidget.mainNodz, tabIndex))

        newState.editedGroupId = None
        newState.runtimeChanges = runtimeChanges

        newState.dirtyLayoutNodeId = dirtyNodeId
        newState.dirtyAssetsRepartition = dirtyAssets  # same in both ways

        if "groupId" in tabWidget.editedNodz.scene().userData:
            newState.editedGroupId = tabWidget.editedNodz.scene().userData["groupId"]

        # in case we are editing the same node, stack it over the previous edition (or addOrEdit will stack all along translate / rotate / scale)
        # we only keep more recent state in that case
        # would be even better to check if the edited attribute is the same, but would not work for rotate 3 params or scale 2 params
        # last undo stack is never deleted as it is the loaded file base state
        undoStackLength = len(tabWidget.undoStack)
        if (
            undoStackLength > 1
            and dirtyNodeId is not None
            and tabWidget.undoStack[undoStackLength - 1].dirtyLayoutNodeId == newState.dirtyLayoutNodeId
        ):
            prevRuntimeChanges = tabWidget.undoStack[undoStackLength - 1].runtimeChanges
            tabWidget.undoStack[undoStackLength - 1] = newState
            tabWidget.undoStack[undoStackLength - 1].runtimeChanges = (
                prevRuntimeChanges or runtimeChanges
            )  # if stacking several things that change and don't change, change must be taken into account (ex : modify attribute value then move)
        else:
            if len(tabWidget.undoStack) > tabWidget.maxUndoStackDepth:
                tabWidget.undoStack.pop(0)  # make room for a fresher undo
            tabWidget.undoStack.append(newState)

        # if we have an edit, clear the redo stack
        del tabWidget.redoStack[:]

    def undo(self, tabIndex):

        if tabIndex < 0 or tabIndex > len(self.layoutViewTabWidgets):
            print("Error: no tab selected")
            return

        tabWidget = self.layoutViewTabWidgets[tabIndex]

        if len(tabWidget.undoStack) <= 1:
            print("Warning : Nothing left to be undone (max undo depth reached)")
            return

        thisState = tabWidget.undoStack[len(tabWidget.undoStack) - 1]
        tabWidget.undoStack.pop()
        tabWidget.redoStack.append(thisState)

        prevState = tabWidget.undoStack[len(tabWidget.undoStack) - 1]

        filePath = ""
        if "currentFilePath" in tabWidget.mainNodz.scene().userData.keys():
            filePath = tabWidget.mainNodz.scene().userData["currentFilePath"]

        self.blockUndoRedoSignals = True
        self.clearTab(tabIndex)  # reset the tab before loading a nodz. block signals to avoid sending an empty layout before right one
        self.loadGolaemLayoutData(tabIndex, copy.deepcopy(prevState.layoutData), False, False)

        # should keep current filepath between undo/redo
        if filePath != "":
            tabWidget.mainNodz.scene().userData["currentFilePath"] = filePath

        # find the editedGroupId
        newEditedNodz = tabWidget.mainNodz
        for childNodz in tabWidget.childrenNodz.items():
            if childNodz[0] == prevState.editedGroupId:
                newEditedNodz = childNodz[1]

        self.blockUndoRedoSignals = False

        self.editorTabWidget.setCurrentIndex(tabIndex)
        self.setEditedNodz(newEditedNodz)

        if prevState.runtimeChanges:
            # when undoing, what changes is what has changed from prev to current, stored in this
            if thisState.dirtyLayoutNodeId is None:
                self.signal_LayoutGraphChanged.emit(self, prevState.dirtyAssetsRepartition)
            else:
                # find dirty node by Id in current (modified) nodz (node edition includes name, name is unsage to keep)
                dirtyNodeName = None
                for node in newEditedNodz.scene().nodes:
                    nodeInst = newEditedNodz.scene().nodes[node]
                    if nodeInst.userData["ID"] == thisState.dirtyLayoutNodeId:
                        dirtyNodeName = nodeInst.name
                        break
                if dirtyNodeName is not None:
                    self.signal_LayoutNodeChanged.emit(self, dirtyNodeName)
                else:
                    # fallback to layout graph changed with dirty asset info
                    self.signal_LayoutGraphChanged.emit(self, prevState.dirtyAssetsRepartition)

    def redo(self, tabIndex):

        if tabIndex < 0 or tabIndex > len(self.layoutViewTabWidgets):
            print("Error: no tab selected")
            return

        tabWidget = self.layoutViewTabWidgets[tabIndex]

        if len(tabWidget.redoStack) == 0:
            print("Warning :  Nothing left to be redone")
            return

        stateToRedo = tabWidget.redoStack[len(tabWidget.redoStack) - 1]
        tabWidget.redoStack.pop()

        filePath = ""
        if "currentFilePath" in tabWidget.mainNodz.scene().userData.keys():
            filePath = tabWidget.mainNodz.scene().userData["currentFilePath"]

        self.blockUndoRedoSignals = True
        self.clearTab(tabIndex)  # reset the tab before loading a nodz
        self.loadGolaemLayoutData(tabIndex, copy.deepcopy(stateToRedo.layoutData), False, False)

        # should keep current filepath between undo/redo
        if filePath != "":
            tabWidget.mainNodz.scene().userData["currentFilePath"] = filePath

        # find the editedGroupId
        newEditedNodz = tabWidget.mainNodz
        for childNodz in tabWidget.childrenNodz.items():
            if childNodz[0] == stateToRedo.editedGroupId:
                newEditedNodz = childNodz[1]

        self.blockUndoRedoSignals = False

        tabWidget.undoStack.append(stateToRedo)

        self.editorTabWidget.setCurrentIndex(tabIndex)
        self.setEditedNodz(newEditedNodz)

        if stateToRedo.runtimeChanges:
            if stateToRedo.dirtyLayoutNodeId is None:
                self.signal_LayoutGraphChanged.emit(self, stateToRedo.dirtyAssetsRepartition)
            else:
                # find dirty node by Id in current (modified) nodz (node edition includes name, name is unsage to keep)
                dirtyNodeName = None
                for node in newEditedNodz.scene().nodes:
                    nodeInst = newEditedNodz.scene().nodes[node]
                    if nodeInst.userData["ID"] == stateToRedo.dirtyLayoutNodeId:
                        dirtyNodeName = nodeInst.name
                        break
                if dirtyNodeName is not None:
                    self.signal_LayoutNodeChanged.emit(self, dirtyNodeName)
                else:
                    # fallback to layout graph changed with dirty asset info
                    self.signal_LayoutGraphChanged.emit(self, stateToRedo.dirtyAssetsRepartition)

    def undoRedoDeleteSelectedNodes(self, nodzInstance, deletedNodesUserDataList):
        self.stackUndo(self.getNodzTabIndex(nodzInstance))

    def undoRedoEditNode(self, nodzInstance, nodeUserDataBefore, nodeUserDataAfter):
        doRecomputeAssets = False
        if "type" in nodeUserDataBefore and nodeUserDataBefore["type"] in [
            GlmTransformType.SetMeshAssets,
            GlmTransformType.SetRenderingType,
            GlmTransformType.AddRemoveMeshAssets,
        ]:
            doRecomputeAssets = True
        self.stackUndo(self.getNodzTabIndex(nodzInstance), nodeUserDataBefore["ID"], doRecomputeAssets)

    def undoRedoAddNode(self, nodzInstance, nodeUserData):
        self.stackUndo(self.getNodzTabIndex(nodzInstance))

    def undoRedoMoveNodes(self, nodzInstance, nodeList, fromPosList, toPosList):
        self.stackUndo(self.getNodzTabIndex(nodzInstance), None, False, False)

    def undoRedoConnectNodes(self, nodzInstance, removedConnections, newConnections):
        self.stackUndo(self.getNodzTabIndex(nodzInstance))

    def createNodz(self, parentTabWidget):
        # init nodz
        newNodzInstance = nodz_main.Nodz(parentTabWidget)

        # QtBehaviorGraphicViewWidget * graphicsView = new QtBehaviorGraphicViewWidget(this);
        # graphicsView->createGraphicScene();
        # graphicsView->setObjectName(QString::fromUtf8("behaviorGraphicsView"));
        # graphicsView->setCompleterModel(_completerModel);
        # graphicsView->setFocus(Qt::MouseFocusReason);

        # inspired from QtAbstractGraphicViewWidget
        newNodzInstance.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        newNodzInstance.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        newNodzInstance.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        newNodzInstance.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        newNodzInstance.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # newNodzInstance.setDragMode(QtWidgets.QGraphicsView.NoDrag)

        newNodzInstance.allowLoop = False
        newNodzInstance.loadConfig(os.path.join(os.path.dirname(os.path.realpath(__file__)), "golaem_layoutNodz_config.json"))
        newNodzInstance.initialize()

        # init scene user data
        newNodzInstance.scene().userData = dict()
        newNodzInstance.scene().userData["nextNodeId"] = 0
        newNodzInstance.scene().userData["rootTransformId"] = -1
        newNodzInstance.scene().userData["licenseHashKey"] = 0

        # ndoe creation context menu
        newNodzInstance.initNodeCreationHelper(self.layoutNodesList, self.GolaemLayoutNodeCreator, QtCore.Qt.Key_Tab)

        # connect to nodz signals
        newNodzInstance.signal_NodePreDeleted.connect(self.on_nodePreDeleted)
        newNodzInstance.signal_NodeDeleted.connect(self.on_nodeDeleted)
        newNodzInstance.signal_NodeSelected.connect(self.on_nodeSelected)
        # newNodzInstance.signal_NodeMoved.connect(self.on_nodeMoved)
        newNodzInstance.signal_NodeDoubleClicked.connect(self.on_nodeDoubleClick)

        newNodzInstance.signal_SceneDoubleClicked.connect(self.on_sceneDoubleClick)
        # newNodzInstance.signal_NodeRightClicked.connect(self.on_nodeRightClick)

        newNodzInstance.signal_NodeContextMenuEvent.connect(self.on_nodeContextMenu)
        newNodzInstance.signal_ViewContextMenuEvent.connect(self.on_viewContextMenu)

        newNodzInstance.signal_SocketConnected.connect(self.on_connected)
        newNodzInstance.signal_SocketDisconnected.connect(self.on_disconnected)
        newNodzInstance.signal_KeyPressed.connect(self.on_keyPressed)

        newNodzInstance.setEnableDrop(True)
        newNodzInstance.signal_dragEvent.connect(self.on_dragEvent)
        newNodzInstance.signal_dragMoveEvent.connect(self.on_dragMoveEvent)
        newNodzInstance.signal_dropEvent.connect(self.on_dropEvent)

        # all this signals have nodz instance as first param
        # newNodzInstance.signal_UndoRedoModifySelection.connect(self.undoRedoModifySelection)
        newNodzInstance.signal_UndoRedoDeleteSelectedNodes.connect(self.undoRedoDeleteSelectedNodes)
        # newNodzInstance.signal_UndoRedoEditNodeName.connect(self.undoRedoEditNodeName) # node
        newNodzInstance.signal_UndoRedoAddNode.connect(self.undoRedoAddNode)  # node
        newNodzInstance.signal_UndoRedoMoveNodes.connect(self.undoRedoMoveNodes)  # node list, fromPos list, toPos list
        newNodzInstance.signal_UndoRedoConnectNodes.connect(
            self.undoRedoConnectNodes
        )  # list of removed connection (potentially due to addition), list of new connections

        newNodzInstance.signal_StartCompoundInteraction.connect(
            self.startCompoundInteraction
        )  # list of removed connection (potentially due to addition), list of new connections
        newNodzInstance.signal_EndCompoundInteraction.connect(
            self.endCompoundInteraction
        )  # list of removed connection (potentially due to addition), list of new connections

        newNodzInstance.signal_dropOnNode.connect(self.dropOnGroup)

        return newNodzInstance

    def newTab(self, tabName=None):
        # newTab is only called for main Nodz, groups tab are created via double click

        newLayoutGraphicViewWidget = LayoutGraphicViewWidget(self.editorTabWidget)
        newLayoutGraphicViewWidget.signal_breadcrumbGoneBack.connect(self.setEditedNodz)

        newNodzInstance = self.createNodz(newLayoutGraphicViewWidget)
        newLayoutGraphicViewWidget.mainNodz = newNodzInstance
        newLayoutGraphicViewWidget.editedNodz = newNodzInstance
        newLayoutGraphicViewWidget.editedNodz.setVisible(True)

        vLayout = QtWidgets.QVBoxLayout()
        vLayout.addWidget(newNodzInstance)
        newLayoutGraphicViewWidget.setLayout(vLayout)
        newLayoutGraphicViewWidget.layout().setContentsMargins(0, 0, 0, 0)

        if tabName is None:
            tabName = "New"

        # Add the tab and save the nodz data at the correct place
        newTabIndex = self.editorTabWidget.addTab(newLayoutGraphicViewWidget, tabName)
        # newTabIndex = self.editorTabWidget.addTab(newLayoutGraphicViewWidget.breadcrumbWidget, "New")
        self.layoutViewTabWidgets.append(newLayoutGraphicViewWidget)
        self.editorTabWidget.setCurrentIndex(newTabIndex)

        newLayoutGraphicViewWidget.layoutName = tabName
        newLayoutGraphicViewWidget.displayName = tabName
        newLayoutGraphicViewWidget.updateBreadcrumb()
        newNodzInstance.stackUnder(newLayoutGraphicViewWidget.breadcrumbWidget)

        # hide empty label
        self.emptyTabWidget.hide()
        self.editorTabWidget.show()

        self.clearTab(newTabIndex)

        # isPLE = True
        # createReturnList = createGolaemLayout()
        # layoutData = json.loads(createReturnList[0]) # [0] json string content
        # self.loadGolaemLayoutData(newTabIndex, layoutData)  # should not change anything

        # newLayoutGraphicViewWidget.displayPLEIconOnCurrentTab(self.PLEIconPath, isPLE)

        return newNodzInstance

    def isCurrentTabOpenViaOpenAction(self):
        currentTabIndex = self.getCurrentTabIndex()
        if currentTabIndex != -1:
            return self.layoutViewTabWidgets[currentTabIndex].openViaOpenAction
        return False

    def getCurrentNodz(self):
        if self.editorTabWidget.count() > 0:
            currentTabIndex = self.editorTabWidget.currentIndex()
            return self.layoutViewTabWidgets[currentTabIndex].editedNodz
        return None

    def isMainNodz(self, theNodz):
        return theNodz is not None and "groupId" not in theNodz.scene().userData

    def getNodzMainNodz(self, theNodz):
        if theNodz is not None and "mainNodz" in theNodz.scene().userData:
            return theNodz.scene().userData["mainNodz"]
        return theNodz

    def getNodeNodz(self, tabIndex, nodeName):
        thisTabMainNodz = self.layoutViewTabWidgets[tabIndex].mainNodz
        if nodeName in list(thisTabMainNodz.scene().nodes.keys()):
            return thisTabMainNodz
        for childNodz in list(self.layoutViewTabWidgets[tabIndex].childrenNodz.values()):
            if nodeName in list(childNodz.scene().nodes.keys()):
                return childNodz
        return None

    def getCurrentMainNodz(self):
        if self.editorTabWidget.count() > 0:
            currentTabIndex = self.editorTabWidget.currentIndex()
            # check if there is a parent 'mainNodz'
            return self.layoutViewTabWidgets[currentTabIndex].mainNodz
        return None

    def isNodzInTabWidget(self, tabIndex, theNodz):
        if self.layoutViewTabWidgets[tabIndex].mainNodz == theNodz:
            return True

        for childNodz in list(self.layoutViewTabWidgets[tabIndex].childrenNodz.values()):
            if childNodz == theNodz:
                return True
        return False

    def getNodzTabIndex(self, theNodz):
        if self.editorTabWidget.count() > 0:
            for tabIndex in range(0, self.editorTabWidget.count()):
                if self.isNodzInTabWidget(tabIndex, theNodz):
                    return tabIndex
        return -1

    def getCurrentTabIndex(self):
        if self.editorTabWidget.count() > 0:
            return self.editorTabWidget.currentIndex()
        return -1

    def getCurrentTabWidget(self):
        if self.editorTabWidget.count() > 0:
            return self.layoutViewTabWidgets[self.editorTabWidget.currentIndex()]
        return None

    def getCurrentTabName(self):
        if self.editorTabWidget.count() > 0:
            currentTabIndex = self.editorTabWidget.currentIndex()
            return self.getLayoutNameForTab(currentTabIndex)
        return ""

    def getLayoutNameForTab(self, tabIndex, withModifiedMarker=False):
        if tabIndex != -1:
            if withModifiedMarker and self.layoutViewTabWidgets[tabIndex].isModified:
                return "{} *".format(self.layoutViewTabWidgets[tabIndex].layoutName)
            else:
                return self.layoutViewTabWidgets[tabIndex].layoutName
        return ""

    def getCurrentTabDisplayName(self):
        if self.editorTabWidget.count() > 0:
            currentTabIndex = self.editorTabWidget.currentIndex()
            return self.getLayoutDisplayNameForTab(currentTabIndex)
        return ""

    def getLayoutDisplayNameForTab(self, tabIndex, withModifiedMarker=False):
        if tabIndex != -1:
            if withModifiedMarker and self.layoutViewTabWidgets[tabIndex].isModified:
                return "{} *".format(self.layoutViewTabWidgets[tabIndex].displayName)
            else:
                return self.layoutViewTabWidgets[tabIndex].displayName
        return ""

    def getLayoutNameForCurrentTab(self, withModifiedMarker=False):
        tabIndex = self.getCurrentTabIndex()
        return self.getLayoutNameForTab(tabIndex, withModifiedMarker)

    def getNodeItemFromId(self, nodzInstance, nodeId):
        for node in nodzInstance.scene().nodes:
            nodeInst = nodzInstance.scene().nodes[node]
            if nodeInst.userData["ID"] == nodeId:
                return nodeInst
        return None

    def keyPressEvent(self, event):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            return

        if event.key() == QtCore.Qt.Key_Tab:
            currentNodz.nodeCreationPopup.popup()
        elif event.key() == QtCore.Qt.Key_Escape:
            currentNodz.nodeCreationPopup.popdown()

    def onToggleSyncSelection(self):
        self.syncSelection = not self.syncSelection
        statusMsg = "Sync selection with the DCC is now "
        if self.syncSelection:
            statusMsg = statusMsg + "on"
        else:
            statusMsg = statusMsg + "off"
        self.setStatusMessage(statusMsg)
        self.toggleSyncSelectionAction.setChecked(self.syncSelection)

    def onFrameAllAction(self):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            return
        itemsArea = currentNodz.scene().itemsBoundingRect()
        currentNodz.fitInView(itemsArea, QtCore.Qt.KeepAspectRatio)

    def onFrameSelectedAction(self):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            return
        currentNodz._focus()

    def onRealSizeAction(self):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            return
        currentNodz._resetScale()

    def onEntityInspectorAction(self):
        self.wrapper.openEntityInspector()

    def onToggleAttributesVisibility(self):
        if self.layoutAttributeEditorDockWidget is not None:
            wasVisible = self.layoutAttributeEditorDockWidget.isVisible()
            self.layoutAttributeEditorDockWidget.setVisible(not wasVisible)

    def onToggleLibraryVisibility(self):
        if self.layoutNodesDockWidget is not None:
            wasVisible = self.layoutNodesDockWidget.isVisible()
            self.layoutNodesDockWidget.setVisible(not wasVisible)

    def onToggleSearchVisibility(self):
        if self.layoutSearchDockWidget is not None:
            wasVisible = self.layoutSearchDockWidget.isVisible()
            self.layoutSearchDockWidget.setVisible(not wasVisible)

    def onToggleStatusVisibility(self):
        if self.layoutCacheStatusDockWidget is not None:
            wasVisible = self.layoutCacheStatusDockWidget.isVisible()
            self.layoutCacheStatusDockWidget.setVisible(not wasVisible)

    def onSearchItems(self):
        # get search item type :
        value = self.layoutSearchLineEdit.text()
        if value is not None:
            if self.layoutSearchTypeComboBox.currentIndex() == 0:
                # Entities
                self.wrapper.selectEntityListFromString(value)
            else:
                currentNodz = self.getCurrentNodz()
                if currentNodz is not None:
                    # possibleNodes = list()
                    nodes = currentNodz.scene().nodes
                    resultNodeList = fnmatch.filter(list(nodes.keys()), value)

                    currentNodz.scene().clearSelection()
                    for resultNodeName in resultNodeList:
                        nodes[resultNodeName].setSelected(True)

    def onCacheSizeChanged(self):
        newValue = self.layoutCacheCacheSizeSpinBox.value()
        self.signal_LayoutCacheSizeChanged.emit(self, newValue)

    ######################################################################
    # File handling
    ######################################################################
    def loadGolaemLayoutData(self, tabIndex, layoutInfo, focus=True, autoLayout=False):

        if tabIndex < 0 or tabIndex > len(self.layoutViewTabWidgets):
            print("Error: no tab selected")
            return

        # self.preModifyScene()
        prevBlockSignalsStatus = self.signalsBlocked()
        self.blockSignals(True)
        # layoutFileVersion = -1
        hasNodes = False
        hasConnections = False

        # clean children group nodz before clear graph
        thisTabWidget = self.layoutViewTabWidgets[tabIndex]

        mainNodz = thisTabWidget.mainNodz

        self.blockRootForward = True

        # either block root id connection or save and restore it. Preferred way is to block connectRootId signal
        # groupRootId = childNodz.scene().userData['rootTransformId']

        # prepare scene
        for item in layoutInfo.items():
            # if item[0] == 'layoutFileVersion':
            #     layoutFileVersion = item[1]
            if item[0] == "nodes":
                hasNodes = True
            elif item[0] == "connections":
                hasConnections = True
            elif item[0] == "parameters":
                #see if there is a specific display name
                for parameter in layoutInfo["parameters"]:
                    attributeName = None
                    attributeValue = None
                    for parameterItem in parameter.items():
                        if parameterItem[0] == "name":
                            attributeName = parameterItem[1]
                        elif parameterItem[0] == "values":
                            attributeValue = parameterItem[1]
                    if attributeName == "displayName":
                        displayName = attributeValue[0]
                        if(len(displayName)>0):
                            thisTabWidget.displayName = displayName
                mainNodz.scene().userData[item[0]] = item[1]  # make sure the parameters are still saved in the nodz userdata
            else:
                mainNodz.scene().userData[item[0]] = item[1]  # pass trough all other values in file, including 'rootTransformId'

        nodeIdToGroupNodz = dict()  # if nodeId not in array, it is in main, else in specified nodz
        groupsNodzRootId = dict()  # group Nodz to its root node Id
        groupsRootNodePerNodz = dict()  # if nodeId not in nodeIdToGroupNodz array, it is in main, else in specified nodz
        # groupNodzToParentNodz=dict() # get parent of a group Nodz

        # On this pass, we just prepare the children Nodz and the node list
        if hasNodes:
            for node in layoutInfo["nodes"]:
                # find groups, create relative nodz
                # node have all user data, including children nodeId
                # name = None
                nodeType = None
                attributes = None
                nodeId = None
                for item in node.items():
                    # if item[0] == "name":
                    #     nodeName = item[1]
                    if item[0] == "ID":
                        nodeId = item[1]
                    elif item[0] == "type":
                        nodeType = item[1]
                    elif item[0] == "attributes":
                        attributes = item[1]

                if nodeType == layoutAttributeEditor.GlmTransformType.Group and nodeId is not None:

                    # create the group Nodz and associate it with this node Id
                    thisGroupNodz = self.createNodz(thisTabWidget)
                    thisGroupNodz.stackUnder(thisTabWidget.breadcrumbWidget)
                    thisTabWidget.childrenNodz[nodeId] = thisGroupNodz
                    thisGroupNodz.scene().userData["groupId"] = nodeId  # store groupId
                    thisGroupNodz.scene().userData["mainNodz"] = mainNodz  # store mainNodz for nextNodeId retrieval

                    if attributes is not None:

                        groupChildrenIds = list()

                        # create the group Nodz
                        for attribute in attributes:
                            attributeName = None
                            attributeValue = None
                            for attributeItem in attribute.items():
                                if attributeItem[0] == "name":
                                    attributeName = attributeItem[1]
                                elif attributeItem[0] == "values":
                                    attributeValue = attributeItem[1]

                            if attributeName == "childrenNodeIds":
                                if attributeValue is None or len(attributeValue) == 0:
                                    continue
                                groupChildrenIds = attributeValue[0]
                                for childNodeId in groupChildrenIds:
                                    nodeIdToGroupNodz[childNodeId] = thisGroupNodz

                            if attributeName == "rootNodeId":
                                if attributeValue is None or len(attributeValue) == 0:
                                    continue
                                # cannot set root yet as nodes are not created, cannot write 'rootTransformId' userData or it will prevent root node refresh
                                groupsNodzRootId[thisGroupNodz] = attributeValue[0][0]

        # created nodes
        nodzNodes = dict()
        # nodzTypes=dict()
        if hasNodes:
            for node in layoutInfo["nodes"]:
                nodeId = mainNodz.scene().userData["nextNodeId"]
                nodeName = ""
                # nodeActive = 1
                position = [0, 0]
                # selectorEntities = None
                operatorType = None
                # operatorTypeName = ''
                # attributes = None
                for item in node.items():
                    if item[0] == "name":
                        nodeName = item[1]
                    elif item[0] == "ID":
                        nodeId = item[1]
                        if nodeId >= mainNodz.scene().userData["nextNodeId"]:
                            mainNodz.scene().userData["nextNodeId"] = nodeId + 1
                    elif item[0] == "GUI_pos":
                        position = item[1]
                    elif item[0] == "type":
                        operatorType = item[1]

                nodeDisplayName = "{} (ID:{})".format(nodeName, nodeId)

                nodeContainer = None
                if nodeId in nodeIdToGroupNodz and nodeIdToGroupNodz[nodeId] is not None:
                    nodeContainer = nodeIdToGroupNodz[nodeId]  # groupNodz
                    nodzNode = nodeContainer.createNode(nodeDisplayName, "node_default", position=QtCore.QPointF(position[0], position[1]))
                    # force real pos as createNode removes nodeCenter
                    nodzNode.setPos(QtCore.QPointF(position[0], position[1]))
                    if nodeId == groupsNodzRootId[nodeContainer]:
                        groupsRootNodePerNodz[nodeContainer] = nodzNode
                else:
                    nodeContainer = mainNodz
                    nodzNode = mainNodz.createNode(nodeDisplayName, "node_default", position=QtCore.QPointF(position[0], position[1]))
                    # force real pos as createNode removes nodeCenter
                    nodzNode.setPos(QtCore.QPointF(position[0], position[1]))

                if operatorType == GlmTransformType.Group:
                    thisTabWidget.childrenNodz[nodeId].scene().userData["parentNodz"] = nodeContainer
                    thisTabWidget.childrenNodz[nodeId].scene().userData["groupNode"] = nodzNode
                    nodzNode.acceptNodeDrop = True  # group accepts nodeDrop, it will get it back by signal

                nodzNode.userData = node  # save all info (node + attributes) in user data
                self.createOrRefreshNodeAttributes(nodzNode, nodeContainer)  # will refresh the display from the node userData

                nodzNodes[nodeId] = nodzNode  # .name
                # nodzTypes[nodeId] = operatorTypeName

        # once nodes have been created, set root ids :
        for groupNodz in thisTabWidget.childrenNodz.items():
            groupNodz[1]._resetScale()  # force 1:1 display
            itemsArea = groupNodz[1].scene().itemsBoundingRect()
            groupNodz[1].centerOn(itemsArea.left() + old_div(itemsArea.width(), 2), itemsArea.top() + old_div(itemsArea.height(), 2))
            # restore previous pos if any
            # if ('matrix' in groupNodz[1].scene().userData):
            #     groupNodz[1].setMatrix(currentNodz.scene().userData['matrix'])
            # fit in view does some wierd zoom, too zoomed out
            # groupNodz[1].fitInView(itemsArea, QtCore.Qt.KeepAspectRatio) # avoid opening a layout / group out of its content scope

            if groupNodz[1] in groupsRootNodePerNodz:
                rootNodeInst = groupsRootNodePerNodz[groupNodz[1]]
                self.setRootNode(groupNodz[1], rootNodeInst)
                self.createOrRefreshNodeAttributes(rootNodeInst, groupNodz[1])
                # self.signal_LayoutRootChanged.emit(self, rootNodeInst.name)

        # connect nodes
        if hasConnections:
            for connection in layoutInfo["connections"]:
                srcId = connection[0]
                dstId = connection[1]
                if srcId in nodzNodes and dstId in nodzNodes:
                    # build the connections in the srcId relative nodz view
                    if srcId in nodeIdToGroupNodz and nodeIdToGroupNodz[srcId] is not None:
                        nodeIdToGroupNodz[srcId].createConnection(
                            nodzNodes[srcId].name,
                            nodzNodes[srcId].attrs[0],
                            nodzNodes[dstId].name,
                            nodzNodes[dstId].attrs[0],
                        )
                    else:
                        mainNodz.createConnection(
                            nodzNodes[srcId].name,
                            nodzNodes[srcId].attrs[0],
                            nodzNodes[dstId].name,
                            nodzNodes[dstId].attrs[0],
                        )
                else:
                    print("unable to connect node ID {} to {} : at least one of the nodes does not exist".format(srcId, dstId))

        # layout graph and focus
        if autoLayout:
            mainNodz.autoLayoutGraph()
        if focus:
            mainNodz._focus()

        self.blockRootForward = False

        self.blockSignals(prevBlockSignalsStatus)

        for childNodz in thisTabWidget.childrenNodz.items():
            childNodz[1].hide()

        # self.postModifyScene()
        return True

    def loadGolaemLayoutFile(self, filePath, focus=True, autoLayout=False):
        success = True
        currentNodz = self.getCurrentMainNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            return False

        correctedFilePath = filePath
        if usingDevkit:
            correctedFilePath = replaceEnvVars(glm.golaemUtils.convertStringForDevkit(filePath))

        if not os.path.isfile(correctedFilePath):
            print("Error: file '{}' does not exist".format(filePath))
            return False

        layoutInfo = dict()
        isPLE = True
        if usingDevkit:
            openReturnList = openGolaemLayout(glm.golaemUtils.convertStringForDevkit(correctedFilePath))
            if openReturnList is not None and isinstance(openReturnList, list) and len(openReturnList) == 2:
                layoutInfo = json.loads(openReturnList[0])
                isPLE = openReturnList[1]
                if layoutInfo is None:
                    return False
            else:
                print(
                    "Could not open Layout file {}. Possible cause is a license issue, or Golaem devkit library _devkit.pyd is not in python path.".format(
                        str(correctedFilePath)
                    )
                )
                return False
        else:
            # load Golaem Layout JSON file - forced PLE Mode
            with open(correctedFilePath, "r") as myfile:
                fileString = myfile.read()
                layoutInfo = json.loads(fileString)

        layoutFileVersion = -1

        # prepare scene
        for item in layoutInfo.items():
            if item[0] == "layoutFileVersion":
                layoutFileVersion = item[1]

        if layoutFileVersion < 1:
            if layoutFileVersion == 0:
                print("Layout file '{}' is an older file version. It can't be displayed in the layout editor.".format(filePath))
            else:
                print("Layout file '{}' is an unkown file version. It can't be displayed in the layout editor.".format(filePath))
            return False

        self.clearTab(self.getCurrentTabIndex())  # reset the tab before loading a nodz
        success = self.loadGolaemLayoutData(self.getCurrentTabIndex(), layoutInfo, focus, autoLayout)
        self.getCurrentTabWidget().displayPLEIconOnCurrentTab(self.PLEIconPath, isPLE)

        # remember path for next time we load or save a file...
        settings = QtCore.QSettings("Golaem", "LayoutEditorWindow")
        baseDir = str(os.path.dirname(correctedFilePath))
        settings.setValue("LastFiles", baseDir)

        currentNodz._resetScale()  # force 1:1 display
        itemsArea = currentNodz.scene().itemsBoundingRect()
        itemsArea = currentNodz.scene().itemsBoundingRect()
        currentNodz.centerOn(itemsArea.left() + old_div(itemsArea.width(), 2), itemsArea.top() + old_div(itemsArea.height(), 2))

        # restore previous pos if any
        # if ('matrix' in currentNodz.scene().userData):
        #     currentNodz.setMatrix(currentNodz.scene().userData['matrix'])

        # could also use fitInView for main nodz, does not work for inner groups
        # currentNodz.fitInView(itemsArea, QtCore.Qt.KeepAspectRatio) # avoid opening a layout / group out of its content scope

        # self.signal_LayoutGraphChanged.emit(self, True)
        self.signal_LayoutGraphLoaded.emit(self.getCurrentTabIndex(), filePath)
        return success

    def refreshGroupNodeUserData(self, theNodz, thisTabWidget, groupNodeInst):
        # refresh the groupNode userdata (root and children attributes) from the group nodz, if the groupNodeInst is of type group
        if "type" in groupNodeInst.userData and groupNodeInst.userData["type"] == GlmTransformType.Group:
            groupId = groupNodeInst.userData["ID"]

            # fill root id from its nodz
            childNodz = thisTabWidget.childrenNodz[groupId]
            groupRootId = childNodz.scene().userData["rootTransformId"]
            groupChildNodes = list()

            for node in childNodz.scene().nodes:
                # handle node, attributes are stores in userData, so will be saved as well
                childgroupNodeInst = childNodz.scene().nodes[node]
                groupChildNodes.append(childgroupNodeInst.userData["ID"])

            attributeIndex = 1  # skip name in nodz, userData does not have it
            for attribute in groupNodeInst.userData["attributes"]:
                attributeName = None
                attributeValue = None
                # attributeFrames = None
                for attributeItem in attribute.items():
                    if attributeItem[0] == "name":
                        attributeName = attributeItem[1]
                    elif attributeItem[0] == "values":
                        attributeValue = attributeItem[1]
                    # elif attributeItem[0] == "frames":
                    #     attributeFrames = attributeItem[1]

                # rootNodeId and childrenNodeIds are not displayed
                if attributeName == "rootNodeId":
                    attributeValue[0][0] = groupRootId
                if attributeName == "childrenNodeIds":
                    attributeValue[0] = groupChildNodes

                attributeIndex += 1

    def recursiveBuildGolaemLayoutFile(self, currentNodz, thisTabWidget, layoutInfo):

        for node in currentNodz.scene().nodes:
            # handle node, attributes are stores in userData, so will be saved as well
            nodeInst = currentNodz.scene().nodes[node]
            self.refreshGroupNodeUserData(currentNodz, thisTabWidget, nodeInst)
            currentNodeJSON = nodeInst.userData
            currentNodeJSON["GUI_pos"] = [nodeInst.pos().x(), nodeInst.pos().y()]
            layoutInfo["nodes"].append(currentNodeJSON)

            # handle connections by checking all nodes' plugs (plugMaxConnections is 1)
            for plug in nodeInst.plugs:
                plugInst = nodeInst.plugs[plug]
                for connection in plugInst.connections:
                    if connection.plugNode is not None and connection.socketNode is not None:
                        srcNode = connection.plugNode
                        srcNodeInst = currentNodz.scene().nodes[srcNode]
                        srcId = srcNodeInst.userData["ID"]
                        dstNode = connection.socketNode
                        dstNodeInst = currentNodz.scene().nodes[dstNode]
                        dstId = dstNodeInst.userData["ID"]
                        layoutInfo["connections"].append([srcId, dstId])

            # handle children groups
            nodeId = currentNodeJSON["ID"]
            if nodeId is not None and nodeId in list(thisTabWidget.childrenNodz.keys()):
                self.recursiveBuildGolaemLayoutFile(thisTabWidget.childrenNodz[nodeId], thisTabWidget, layoutInfo)

    def buildGolaemLayoutFile(self, theMainNodz, tabIndex):
        if theMainNodz is None:
            print("Error: no tab selected")
            return
        
        # assemble data in structure compatible with our JSON format
        layoutInfo = theMainNodz.scene().userData  # contain the rootTransformId and licenseHashKey if they exists
        if layoutInfo is None:
            layoutInfo = dict()
        layoutInfo["layoutFileVersion"] = 1
        #save the display name if it's different than the tab id name
        if self.editorTabWidget.count() > 0:
            tabName = self.getLayoutNameForTab(tabIndex, False)
            displayName = self.getLayoutDisplayNameForTab(tabIndex, False)
            if displayName!=tabName:
                if "parameters" not in layoutInfo:
                    layoutInfo["parameters"] = list()
                alreadyHasDisplayNameParamater = False
                for parameter in layoutInfo["parameters"]:
                    for parameterItem in parameter.items():
                        if parameterItem[0] == "name":
                            if parameterItem[1] == "displayName":
                                parameter["values"] = [displayName]
                                alreadyHasDisplayNameParamater = True
                                break
                if not alreadyHasDisplayNameParamater:
                    displayNameParameter = dict()
                    displayNameParameter["name"] = "displayName"
                    displayNameParameter["values"] = [displayName]
                    displayNameParameter["type"] = 1
                    displayNameParameter["frames"] = list()
                    displayNameParameter["flags"] = 0
                    layoutInfo["parameters"].append(displayNameParameter)

        layoutInfo["nodes"] = list()
        layoutInfo["groups"] = list()
        layoutInfo["connections"] = list()

        # add information about the inner groups in the layout info
        thisTabWidget = self.layoutViewTabWidgets[self.getNodzTabIndex(theMainNodz)]
        self.recursiveBuildGolaemLayoutFile(theMainNodz, thisTabWidget, layoutInfo)

        return layoutInfo

    def saveGolaemLayoutFile(self, theNodz, tabIndex, filePath):

        if theNodz is None:
            print("Error: no tab selected")
            return

        mainNodz = theNodz
        # when calling save from a child tab, we need to save the main one
        if theNodz.scene().userData is not None and "mainNodz" in theNodz.scene().userData:
            mainNodz = theNodz.scene().userData["mainNodz"]

        layoutInfo = self.buildGolaemLayoutFile(mainNodz, tabIndex)
        layoutJSon = json.dumps(layoutInfo, sort_keys=False, indent=2, ensure_ascii=False)

        # save file
        correctedFilePath = filePath
        if usingDevkit:
            correctedFilePath = replaceEnvVars(glm.golaemUtils.convertStringForDevkit(filePath))
        if usingDevkit:
            saveGolaemLayout(
                glm.golaemUtils.convertStringForDevkit(correctedFilePath),
                glm.golaemUtils.convertStringForDevkit(layoutJSon),
            )
        else:
            f = open(correctedFilePath, "w")
            f.write(json.dumps(layoutInfo, sort_keys=False, indent=2, ensure_ascii=False))
            f.close()
        print("Saved Golaem Layout File in {}".format(correctedFilePath))

        # remember path for next time we load or save a file...
        settings = QtCore.QSettings("Golaem", "LayoutEditorWindow")
        baseDir = str(os.path.dirname(correctedFilePath))
        settings.setValue("LastFiles", baseDir)

        self.signal_LayoutGraphSaved.emit(tabIndex, filePath)

    def saveGolaemLayoutNodeDefinition(self, filePath):
        currentNodz = self.getCurrentMainNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            return

        # assemble data in structure compatible wiith our JSON format
        layoutInfo = dict()
        layoutInfo["GolaemLayoutNodes"] = list()

        for node in currentNodz.scene().nodes:
            # handle node, attributes are stores in userData, so will be saved as well
            nodeInst = currentNodz.scene().nodes[node]
            currentNodeJSON = nodeInst.userData
            # take only node that have type / type_name
            if ("type" in currentNodeJSON) and ("type_name" in currentNodeJSON):
                golaemNodeDefinition = dict()
                golaemNodeDefinition["type"] = currentNodeJSON["type"]
                golaemNodeDefinition["type_name"] = currentNodeJSON["type_name"]
                golaemNodeDefinition["attributes"] = currentNodeJSON[
                    "attributes"
                ]  # copy all attributes: values and frames will be used as the default values
                # store
                layoutInfo["GolaemLayoutNodes"].append(golaemNodeDefinition)

        # save file
        f = open(filePath, "w")
        f.write(json.dumps(layoutInfo, sort_keys=False, indent=2, ensure_ascii=False))
        f.close()
        print("Saved Golaem Layout Nodes Defintion in {}".format(filePath))

    ######################################################################
    # Utils
    ######################################################################

    def getRootNode(self, currentNodz):
        if "rootTransformId" in currentNodz.scene().userData:
            rootId = currentNodz.scene().userData["rootTransformId"]
            return self.getNodeItemFromId(currentNodz, rootId)
        return None

    def setRootNode(self, currentNodz, nodeInst, enableToggle=False):
        newRootID = nodeInst.userData["ID"]
        previousRootId = None
        if "rootTransformId" in currentNodz.scene().userData:
            previousRootId = currentNodz.scene().userData["rootTransformId"]

        if previousRootId is not None and previousRootId == newRootID:
            if enableToggle:
                currentNodz.scene().userData["rootTransformId"] = -1
            else:
                return
        else:
            currentNodz.scene().userData["rootTransformId"] = newRootID

        self.createOrRefreshNodeAttributes(nodeInst, currentNodz)  # refresh new root
        if previousRootId is not None:
            nodeInst = self.getNodeItemFromId(currentNodz, previousRootId)
            if nodeInst is not None:
                self.createOrRefreshNodeAttributes(nodeInst, currentNodz)  # refresh old root

    def findEditedEntities(self, nodeName):
        editedEntitiesExpression = str()
        nodeInst = self.getCurrentNodz().scene().nodes[nodeName]
        if "entities" in nodeInst.userData:  # this does not handle duplicates & snapTo, this is a fallback if no wrapper
            editedEntitiesExpression = nodeInst.userData["entities"]
        else:  # find all previous nodes
            for socket in nodeInst.sockets:
                socketInst = nodeInst.sockets[socket]
                for connection in socketInst.connections:
                    if connection.plugNode is not None:
                        srcNodeName = connection.plugNode
                        if len(editedEntitiesExpression) > 0:
                            editedEntitiesExpression = "{}, {}".format(editedEntitiesExpression, self.findEditedEntities(srcNodeName))
                        else:
                            editedEntitiesExpression = self.findEditedEntities(srcNodeName)
        # old layout files might return a list instead of a string
        if type(editedEntitiesExpression) == type(list()):
            print("Selection is from an old file format, converting into string: {}".format(editedEntitiesExpression))
            editedEntitiesExpression = str(editedEntitiesExpression)
            editedEntitiesExpression = editedEntitiesExpression.strip("[")
            editedEntitiesExpression = editedEntitiesExpression.strip("]")
        return editedEntitiesExpression

    def getStringRect(self, str, font):
        metrics = QtGui.QFontMetrics(font)
        lines = str.split("\n")
        textRect = QtCore.QRect()
        for line in lines:
            textRect.setWidth(max(textRect.width(), metrics.width(line)))
            textRect.setHeight(textRect.height() + metrics.lineSpacing())
        return textRect

    def checkNodeAttributes(self, nodzNode, printFullNode=False):
        # currentNodz = self.getCurrentNodz()
        # if currentNodz is None:
        #     print("Error: no tab selected")
        #     return None

        # print if asked
        if printFullNode:
            print("Node dump:\n{}".format(nodzNode.userData))

        # check all attributes
        nodeName = None
        nodeId = None
        attributes = None
        for item in nodzNode.userData.items():
            if item[0] == "name":
                nodeName = item[1]
            elif item[0] == "ID":
                nodeId = item[1]
            elif item[0] == "attributes":
                attributes = item[1]

        if attributes is not None:
            for attribute in attributes:
                attributeName = None
                attributeValue = None
                attributeFrames = None
                for attributeItem in attribute.items():
                    if attributeItem[0] == "name":
                        attributeName = attributeItem[1]
                    elif attributeItem[0] == "values":
                        attributeValue = attributeItem[1]
                    elif attributeItem[0] == "frames":
                        attributeFrames = attributeItem[1]

                if attributeName is None:
                    print("Error: [GolaemLayoutEditor]: an attribute as no name in the node {}".format(nodeName))
                    return False
                if attributeValue is None:
                    print(
                        "Error: [GolaemLayoutEditor]: Invalid attribute. {} in node {} (ID {}) has no values".format(attributeName, nodeName, nodeId)
                    )
                    return False
                if type(attributeValue) != type(list()):
                    print(
                        'Error: [GolaemLayoutEditor]: Invalid attribute. {} in node {} (ID {}) is a "{}" type'.format(
                            attributeName, nodeName, nodeId, type(attributeValue)
                        )
                    )
                    return False
                if len(attributeValue) == 0:
                    print(
                        "Error: [GolaemLayoutEditor]: Invalid attribute. {} in node {} (ID {}) has a list of 0 values".format(
                            attributeName, nodeName, nodeId
                        )
                    )
                    return False
                if attributeFrames is not None:
                    if len(attributeFrames) > 0:
                        if len(attributeFrames) != len(attributeValue):
                            print(
                                "Error: [GolaemLayoutEditor]: Invalid attribute. {} in node {} (ID {}) has a {} keyframes, but {} keyvalues".format(
                                    attributeName, nodeName, nodeId, len(attributeFrames), len(attributeValue)
                                )
                            )
                            return False

        return True

    def refreshAttributeEditor(self, modifiedNodeInst):
        editedNodeInst = self.getEditedNode()
        if modifiedNodeInst is not None and modifiedNodeInst == editedNodeInst:
            # force refresh of the attribute editor, the data has been modified from outside
            currentNodz = self.getCurrentNodz()
            self.setEditedNode(currentNodz, None)
            self.setEditedNode(currentNodz, editedNodeInst)

    def createOrRefreshNodeAttributes(self, nodzNode, nodeContainer=None):

        self.checkNodeAttributes(nodzNode)

        currentNodz = nodeContainer
        if currentNodz is None:
            currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            return

        # scene info
        rootNodeId = None
        if currentNodz.scene().userData is not None:
            for item in currentNodz.scene().userData.items():
                if item[0] == "rootTransformId":
                    rootNodeId = item[1]

        # get default values
        nodeId = -1
        nodeName = ""
        nodeActive = 1
        # position = [0,0]
        selectorEntities = None
        filterInput = False
        percent = 100
        randomSeed = 0
        operatorType = None
        operatorTypeName = ""
        attributes = None
        connectionAttributeDisplayName = " "
        for item in nodzNode.userData.items():
            if item[0] == "name":
                nodeName = item[1]
            elif item[0] == "ID":
                nodeId = item[1]
            elif item[0] == "active":
                nodeActive = item[1]
            # elif item[0] == "GUI_pos":
            #     position = item[1]
            elif item[0] == "entities":
                selectorEntities = item[1]
                connectionAttributeDisplayName = "Entity Selector"
            elif item[0] == "filterInput":
                filterInput = item[1] == 1
            elif item[0] == "percent":
                percent = item[1]
            elif item[0] == "randomSeed":
                randomSeed = item[1]
            elif item[0] == "type":
                operatorType = item[1]
            elif item[0] == "type_name":
                operatorTypeName = item[1]
                connectionAttributeDisplayName = operatorTypeName
            elif item[0] == "attributes":
                attributes = item[1]
        nodeDisplayName = "{} (ID:{})".format(nodeName, nodeId)

        #################
        # update node name
        if ("name" in nodzNode.userData) and ("ID" in nodzNode.userData):
            if nodzNode.name != nodeDisplayName:
                currentNodz.editNode(node=nodzNode, newName=nodeDisplayName)

        ###################################
        # update icon based on Type
        if self.layoutNodesList is not None and self.layoutNodesIconList is not None:
            try:
                if operatorTypeName != "":
                    iconIndex = self.layoutNodesList.index(operatorTypeName)
                else:
                    iconIndex = self.layoutNodesList.index("EntitySelector")
                nodzNode.icon = self.layoutNodesIconList[iconIndex]  # can be None if icon failed to load
            except:
                nodzNode.icon = None

        ###################################
        # update node preset (active status)

        # get preset according to the type of the node
        nodePresetName = None
        attributeConnectionPresetName = None
        if selectorEntities is not None:
            if filterInput:
                nodePresetName = "node_preset_LayoutSelectorFilterNode"
                attributeConnectionPresetName = "attr_preset_LayoutSelectorFilterConnection"
            else:
                nodePresetName = "node_preset_LayoutSelectorNode"
                attributeConnectionPresetName = "attr_preset_LayoutSelectorConnection"
        elif operatorType is not None:
            nodePresetName = "node_preset_LayoutOperatorNode"
            attributeConnectionPresetName = "attr_preset_LayoutOperatorConnection"
        # override node preset for duplicate nodes
        if operatorType == GlmTransformType.Duplicate or operatorType == GlmTransformType.SnapTo:  # duplicate and snap to have specific presets
            nodePresetName = "node_preset_LayoutOperatorNode"
            attributeConnectionPresetName = "attr_preset_LayoutSelectorConnection"
        elif operatorType == GlmTransformType.Note:  # Notes
            nodePresetName = "node_preset_notes"
            attributeConnectionPresetName = "attr_preset_notes"
        elif operatorType == GlmTransformType.Group:  # Group
            nodzNode.acceptNodeDrop = True
            nodePresetName = "node_preset_group"
            attributeConnectionPresetName = "attr_preset_group"
        # override node preset for root
        if nodeId == rootNodeId:
            nodePresetName = "node_preset_root"

        # active node ?
        if nodeActive == 0 and operatorType != GlmTransformType.Note:  # Notes have no inactive state
            if nodePresetName is not None:
                nodePresetName = "{}_inactive".format(nodePresetName)

        if nodePresetName is None:
            nodePresetName = "node_default"
        if attributeConnectionPresetName is None:
            attributeConnectionPresetName = "attr_default"

        nodzNode.nodePreset = nodePresetName
        nodzNode._createStyle(currentNodz.config)
        attributeIndex = 0

        ###################################
        # Notes
        if operatorType == GlmTransformType.Note:
            # find content and display it instead of type and everything
            if attributes != None:
                # if not nodePresetName in nodzInst.config:
                #     baseConfig = dict(
                #                 border_sel=[255, 155, 0, 255],
                #                 bg=[80, 160, 80, 255],
                #                 border=[50, 50, 50, 255],
                #                 text=[230, 230, 230, 255]
                #     )
                #     nodzInst.config[nodePresetName] = baseConfig

                noteContent = ""
                fontSize = 14
                bgColor = currentNodz.config[nodePresetName]["bg"]
                textColor = currentNodz.config[nodePresetName]["text"]
                minWidth = 200
                minHeight = 200
                for attribute in attributes:
                    attributeName = None
                    attributeValue = None
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                        elif attributeItem[0] == "values":
                            attributeValue = attributeItem[1]

                    if attributeName == "content":
                        noteContent = attributeValue
                    elif attributeName == "minWidth":
                        minWidth = attributeValue[0][0]
                    elif attributeName == "minHeight":
                        minHeight = attributeValue[0][0]
                    elif attributeName == "bgColor":
                        bgColor = attributeValue[0][0]
                    elif attributeName == "textColor":
                        textColor = attributeValue[0][0]
                    elif attributeName == "fontSize":
                        fontSize = attributeValue[0][0]

                nodzNode.baseZValue = -1  # Notes are behind everything
                # nodzNode.setZValue(-1)

                # store the preset for this spcific node (color may change from preset). If name has changed, store at new key
                baseConfig = dict(border_sel=bgColor, bg=bgColor, border=bgColor, text=textColor)
                currentNodz.config[nodeDisplayName] = baseConfig

                # override node colors
                bgQColor = QtGui.QColor(bgColor[0], bgColor[1], bgColor[2], bgColor[3])
                # bgQColor.setRgbF(bgColor[0], bgColor[1], bgColor[2], bgColor[3])
                textQColor = QtGui.QColor(textColor[0], textColor[1], textColor[2], textColor[3])
                # textQColor.setRgbF(
                nodzNode._brush.setColor(bgQColor)
                nodzNode._textPen.setColor(textQColor)
                nodzNode._attrVAlign = QtCore.Qt.AlignTop
                # override font size
                nodzNode._attrTextFont = QtGui.QFont(currentNodz.config["attr_font"], fontSize, QtGui.QFont.Normal)

                # handle the attribute's value
                if len(nodzNode.attrs) <= attributeIndex:
                    currentNodz.createAttribute(
                        node=nodzNode,
                        name=noteContent[0],
                        index=attributeIndex,
                        preset=nodeDisplayName,
                        plug=False,
                        socket=False,
                        dataType=str,
                        plugMaxConnections=-1,
                        socketMaxConnections=-1,
                    )
                elif nodzNode.attrs[attributeIndex] != noteContent[0]:
                    currentNodz.editAttribute(node=nodzNode, index=attributeIndex, newName=noteContent[0])

                # In case NodeDisplayName changed, use the new preset in place
                nodzNode.attrsData[noteContent[0]]["preset"] = nodeDisplayName

                # compute the needed text's width and height
                minWidth = max(nodzNode.baseWidth, minWidth)
                minHeight = max(nodzNode.attrHeight, minHeight)
                if noteContent is not None:
                    textRect = self.getStringRect(noteContent[0], nodzNode._attrTextFont)
                    minWidth = max(minWidth, textRect.width() + 28)
                    minHeight = max(minHeight, textRect.height())  # getStringRect() line spacing will return an height even for empty string
                nodzNode.baseWidth = minWidth
                nodzNode.attrHeight = minHeight

        ###################################
        # any other node attributes
        elif operatorType == GlmTransformType.Group:
            ###################################
            # update node connections attribute
            attributeDisplayName = " "

            if len(nodzNode.attrs) <= attributeIndex:
                currentNodz.createAttribute(
                    node=nodzNode,
                    name=connectionAttributeDisplayName,
                    index=attributeIndex,
                    preset=attributeConnectionPresetName,
                    plug=True,
                    socket=True,
                    dataType=str,
                    plugMaxConnections=-1,
                    socketMaxConnections=-1,
                )
            attributeIndex += 1
        else:

            ###################################
            # update node connections attribute
            attributeDisplayName = " "

            if len(nodzNode.attrs) <= attributeIndex:
                currentNodz.createAttribute(
                    node=nodzNode,
                    name=connectionAttributeDisplayName,
                    index=attributeIndex,
                    preset=attributeConnectionPresetName,
                    plug=True,
                    socket=True,
                    dataType=str,
                    plugMaxConnections=-1,
                    socketMaxConnections=-1,
                )
            attributeIndex += 1

            ###################################
            # entities selection
            if selectorEntities is not None:
                attributeDisplayName = "entities: {}".format(selectorEntities)
                if len(nodzNode.attrs) <= attributeIndex:
                    currentNodz.createAttribute(
                        node=nodzNode,
                        name=attributeDisplayName,
                        index=attributeIndex,
                        preset="attr_default",
                        plug=False,
                        socket=False,
                        dataType=str,
                    )
                elif nodzNode.attrs[attributeIndex] != attributeDisplayName:
                    currentNodz.editAttribute(node=nodzNode, index=attributeIndex, newName=attributeDisplayName)
                attributeIndex += 1

                attributeDisplayName = "filterInput: {}".format(filterInput)
                if len(nodzNode.attrs) <= attributeIndex:
                    currentNodz.createAttribute(
                        node=nodzNode,
                        name=attributeDisplayName,
                        index=attributeIndex,
                        preset="attr_default",
                        plug=False,
                        socket=False,
                        dataType=str,
                    )
                elif nodzNode.attrs[attributeIndex] != attributeDisplayName:
                    currentNodz.editAttribute(node=nodzNode, index=attributeIndex, newName=attributeDisplayName)
                attributeIndex += 1

                attributeDisplayName = "percent: {}".format(percent)
                if len(nodzNode.attrs) <= attributeIndex:
                    currentNodz.createAttribute(
                        node=nodzNode,
                        name=attributeDisplayName,
                        index=attributeIndex,
                        preset="attr_default",
                        plug=False,
                        socket=False,
                        dataType=str,
                    )
                elif nodzNode.attrs[attributeIndex] != attributeDisplayName:
                    currentNodz.editAttribute(node=nodzNode, index=attributeIndex, newName=attributeDisplayName)
                attributeIndex += 1

                attributeDisplayName = "randomSeed: {}".format(randomSeed)
                if len(nodzNode.attrs) <= attributeIndex:
                    currentNodz.createAttribute(
                        node=nodzNode,
                        name=attributeDisplayName,
                        index=attributeIndex,
                        preset="attr_default",
                        plug=False,
                        socket=False,
                        dataType=str,
                    )
                elif nodzNode.attrs[attributeIndex] != attributeDisplayName:
                    currentNodz.editAttribute(node=nodzNode, index=attributeIndex, newName=attributeDisplayName)
                attributeIndex += 1

            ###################################
            # attributes
            if attributes is not None:
                for attribute in attributes:
                    attributeName = None
                    attributeValue = None
                    attributeFrames = None
                    attributeFlags = GlmAttributeFlags._none
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                        elif attributeItem[0] == "values":
                            attributeValue = attributeItem[1]
                        elif attributeItem[0] == "frames":
                            attributeFrames = attributeItem[1]
                        elif attributeItem[0] == "flags":
                            attributeFlags = attributeItem[1]

                    # dismiss attributes that are marked is hidden
                    if (attributeFlags is not None) and (attributeFlags & GlmAttributeFlags._uiHidden):
                        continue

                    if (attributeName is not None) and (attributeValue is not None):
                        # flag _uiOperationModeComboBox
                        if attributeFlags == GlmAttributeFlags._uiOperationModeComboBox:
                            mode = attributeValue[0][0]  # [0][0] for first frame, first value
                            if mode < len(self.operationModeList):
                                attributeValue = self.operationModeList[mode]
                        # flag _uiGroundAdaptationModeComboBox
                        elif attributeFlags == GlmAttributeFlags._uiGroundAdaptationModeComboBox:
                            mode = attributeValue[0][0]  # [0][0] for first frame, first value
                            if mode < len(self.groundAdaptationModeList):
                                attributeValue = self.groundAdaptationModeList[mode]
                        # flag _uiOnOffComboBox
                        elif attributeFlags == GlmAttributeFlags._uiOnOffComboBox:
                            mode = attributeValue[0][0]  # [0][0] for first frame, first value
                            if mode < len(self.onOffList):
                                attributeValue = self.onOffList[mode]
                        # flag _uiColorChannelComboBox
                        elif attributeFlags == GlmAttributeFlags._uiColorChannelComboBox:
                            mode = attributeValue[0][0]  # [0][0] for first frame, first value
                            if mode < len(self.colorChannelList):
                                attributeValue = self.colorChannelList[mode]
                        # flag _uiRotateOrderComboBox
                        elif attributeFlags == GlmAttributeFlags._uiRotateOrderComboBox:
                            mode = attributeValue[0][0]  # [0][0] for first frame, first value
                            if mode < len(self.rotateOrderList):
                                attributeValue = self.rotateOrderList[mode]
                        # flag _uiImage
                        elif attributeFlags == GlmAttributeFlags._uiImage:
                            value = attributeValue[0]  # [0] for first frame (use all char values)
                            if value is not None and len(value) > 0:
                                image = QtGui.QImage.fromData(bytes(base64.b64decode(value)))
                                attributeValue = "{}x{} image".format(image.width(), image.height())
                            else:
                                attributeValue = "empty image"
                        else:  # other types: remove keyframes delimiters
                            attributeValue = str(attributeValue)[1:-1]
                        # add the key frame count
                        if attributeFrames is not None and len(attributeFrames) > 0:
                            attributeDisplayName = "{} ({} keys): {}".format(attributeName, len(attributeFrames), attributeFrames)
                        else:
                            attributeDisplayName = "{}: {}".format(attributeName, attributeValue)
                        if len(nodzNode.attrs) <= attributeIndex:
                            currentNodz.createAttribute(
                                node=nodzNode,
                                name=attributeDisplayName,
                                index=attributeIndex,
                                preset="attr_default",
                                plug=False,
                                socket=False,
                                dataType=str,
                            )
                        elif nodzNode.attrs[attributeIndex] != attributeDisplayName:
                            currentNodz.editAttribute(node=nodzNode, index=attributeIndex, newName=attributeDisplayName)
                        attributeIndex += 1

        nodzNode.update()

    def GolaemLayoutNodeCreator(self, nodzInst, nodeTypeName, pos, forcedNodeId=None):
        nodeTypeFound = False
        nodzNode = None

        mainNodz = nodzInst  # potentially groupNodz here if in group, get main nodz for per-main nodz shared nextNodeId
        if mainNodz.scene().userData is not None and "mainNodz" in mainNodz.scene().userData:
            mainNodz = nodzInst.scene().userData["mainNodz"]

        if nodeTypeName == "EntitySelector":
            nodeTypeFound = True
            # create selector Nodz node
            nodeName = "Selector"
            if forcedNodeId is not None:
                nodeId = forcedNodeId
            else:
                nodeId = mainNodz.scene().userData["nextNodeId"]
                mainNodz.scene().userData["nextNodeId"] += 1
            nodeDisplayName = "{} (ID:{})".format(nodeName, nodeId)
            nodzNode = nodzInst.createNode(
                name=nodeDisplayName, preset="node_default", position=pos
            )  # node preset will be refreshed with the createOrRefreshNodeAttributes
            nodzNode.userData = dict()
            nodzNode.userData["name"] = nodeName
            nodzNode.userData["ID"] = nodeId
            nodzNode.userData["active"] = 1
            nodzNode.userData["entities"] = str()
            nodzNode.userData["filterInput"] = 0
            nodzNode.userData["GUI_pos"] = [nodzNode.pos().x(), nodzNode.pos().y()]
            nodzNode.userData["percent"] = 100
            nodzNode.userData["randomSeed"] = 0
        else:
            for nodeDefinition in self.layoutNodesDefinition:
                if "type_name" in nodeDefinition:
                    nodeDefinitionTypeName = nodeDefinition["type_name"]
                    nodeTypeIsTheCurrentNode = False
                    if nodeTypeName == nodeDefinitionTypeName:
                        nodeTypeIsTheCurrentNode = True

                    if nodeTypeIsTheCurrentNode:
                        nodeTypeFound = True
                        # prepare node name
                        if forcedNodeId is not None:
                            nodeId = forcedNodeId  # case of transfering the same node to a child group nodz
                        else:
                            nodeId = mainNodz.scene().userData["nextNodeId"]
                            mainNodz.scene().userData["nextNodeId"] += 1
                        nodeName = nodeTypeName

                        # create Nodz node
                        nodeDisplayName = "{} (ID:{})".format(nodeName, nodeId)
                        nodzNode = nodzInst.createNode(
                            name=nodeDisplayName, preset="node_default", position=pos
                        )  # node preset will be refreshed with the createOrRefreshNodeAttributes
                        nodzNode.userData = copy.deepcopy(nodeDefinition)  # default values
                        if "name" not in nodzNode.userData:
                            nodzNode.userData["name"] = nodeName
                        nodzNode.userData["ID"] = nodeId
                        nodzNode.userData["active"] = 1
                        nodzNode.userData["GUI_pos"] = [nodzNode.pos().x(), nodzNode.pos().y()]

                        if "type" in nodzNode.userData and nodzNode.userData["type"] == GlmTransformType.Group:  # Group
                            tabIndex = self.getNodzTabIndex(nodzInst)
                            thisTabWidget = self.layoutViewTabWidgets[tabIndex]
                            nodzNode.acceptNodeDrop = True  # group accepts nodeDrop, it will get it back by signal

                            # if we force Id, we move nodes. we can keep the matching node Id -> child group nodz
                            if forcedNodeId is None:
                                # create the group Nodz and associated it with this node Id
                                thisGroupNodz = self.createNodz(thisTabWidget)
                                thisGroupNodz.stackUnder(thisTabWidget.breadcrumbWidget)
                                thisTabWidget.childrenNodz[nodeId] = thisGroupNodz
                                thisGroupNodz.scene().userData["groupId"] = nodeId  # store groupId
                                thisGroupNodz.scene().userData["mainNodz"] = mainNodz  # store mainNodz for nextNodeId retrieval
                                thisGroupNodz.scene().userData["parentNodz"] = nodzInst
                                thisGroupNodz.scene().userData["groupNode"] = nodzNode
                        break

        if not nodeTypeFound:
            print("{} is not a recognized node type. Known types are: {}".format(nodeTypeName, self.layoutNodesList))
        else:
            # set Root Id if we have created the first node of the graph, or if the current root node does not exist (deleted)
            rootNodeInst = self.getRootNode(nodzInst)
            if (
                rootNodeInst is None and nodzNode is not None
            ):  # was len(nodzInst.scene().nodes) == 1 and nodzNode is not None, changed to set root if root node was deleted
                # cannot call setRootNode, as the node does not really exist yet in scene. createOrRefreshNodeAttributes is called after, it will update the only node OK
                nodzInst.scene().userData["rootTransformId"] = nodzNode.userData["ID"]

            # refresh node display (from the user data)
            self.signal_LayoutNodeCreated.emit(self, nodzNode)
            self.createOrRefreshNodeAttributes(nodzNode, nodzInst)

        return nodzNode

    def addOrEditLayoutTransformation(
        self,
        cacheProxyName,
        entitiesIDsExpression,
        transformationNodeTypeName,
        parameterName,
        parameterValue,
        frame,
        mode,
    ):
        """
        Add a layout transformation node and the corresponding selection node with the given value

        :type  cacheProxyName: str.
        :param cacheProxyName: Name of the tab widget in which adding a tansform

        :type  entitiesIDsExpression: str.
        :param entitiesIDsExpression: list of entities, presented as a selection string (example: 1001,2001-4001,et(2),cf(1) )

        :type  transformationNodeTypeName: str.
        :param transformationNodeTypeName: Exact name of the transform type, as present in the node definition (example: Translate)

        :type  parameterName: str.
        :param parameterName: Exact name of the paramater to edit (example: translate)

        :type  parameterValue: list.
        :param parameterValue: Value for the parameter, presented as a list (example: [1.1] for a float, or [[1.1, 2.2, 3.3]] for a vector)

        :type  frame: float
        :param frame: frame for the given parameter value

        :type  mode: integer
        :param mode: Mode for adding the value: 0 to set the value, 1 to add to the current value, 2 to mult with the current value

        """
        # self.preModifyScene()
        prevBlockSignalsStatus = self.signalsBlocked()
        self.blockSignals(True)

        editedNodeInst = None
        editedNodz = None
        editedTabIndex = 0

        modifiedOperator = None

        if len(cacheProxyName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    editedTabIndex = tabIndex
                    # set ourselves in root of tab when addding transformation
                    self.setEditedNodz(self.layoutViewTabWidgets[tabIndex].mainNodz)
                    editedNodz = self.layoutViewTabWidgets[tabIndex].editedNodz
                    if editedNodz is not None and editedNodz.editEnabled:
                        nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                        nodePositionOffset = QtCore.QPointF(200, 9)
                        sceneSize = nodzInst.parentWidget().frameSize()
                        newNodePos = nodzInst.mapToScene(
                            old_div(sceneSize.width(), 2), old_div(sceneSize.height(), 2)
                        )  # center of the current view by default
                        # get current root position
                        previousNodeInst = None
                        if "rootTransformId" in nodzInst.scene().userData:
                            previousRootId = nodzInst.scene().userData["rootTransformId"]
                            previousNodeInst = self.getNodeItemFromId(nodzInst, previousRootId)
                            if previousNodeInst is not None:
                                newNodePos = previousNodeInst.pos() + (1.5 * nodePositionOffset)

                        isNote = transformationNodeTypeName == "Notes"
                        isSelector = transformationNodeTypeName == "EntitySelector"
                        prevIsGroup = (
                            previousNodeInst is not None
                            and "type" in previousNodeInst.userData
                            and previousNodeInst.userData["type"] == GlmTransformType.Group
                        )
                        hasSelector = False

                        if not isNote and entitiesIDsExpression is not None and len(entitiesIDsExpression) > 0:
                            # we add a selector now, reused or this one.
                            hasSelector = True

                            # check if the current selection is OK or if a new selector node should be added
                            editedEntitiesExpressionsList = list()
                            if previousNodeInst is not None:
                                editedEntitiesExpressions = self.wrapper.getNodeOutSelection(previousNodeInst)
                                if editedEntitiesExpressions is not None:
                                    editedEntitiesExpressionsList = editedEntitiesExpressions.split(",")
                                    for expressionIndex in range(len(editedEntitiesExpressionsList)):
                                        editedEntitiesExpressionsList[expressionIndex] = editedEntitiesExpressionsList[expressionIndex].strip(" ")

                            entitiesIDsExpressionsList = entitiesIDsExpression.split(",")
                            for expressionIndex in range(len(entitiesIDsExpressionsList)):
                                entitiesIDsExpressionsList[expressionIndex] = entitiesIDsExpressionsList[expressionIndex].strip(" ")
                            # if previous is a group, add a selector to lock the input, as the group input may change
                            if (prevIsGroup or len(editedEntitiesExpressionsList) != len(entitiesIDsExpressionsList)) or (
                                len(set(entitiesIDsExpressionsList).intersection(editedEntitiesExpressionsList)) != len(entitiesIDsExpressionsList)
                            ):
                                # add the selector node
                                selectorNodzNode = self.GolaemLayoutNodeCreator(nodzInst, "EntitySelector", newNodePos)
                                if entitiesIDsExpression is not None:
                                    # this replace raw IDs by the output of node syntax 'o(nodeId, duplicateIndex)'
                                    selectorNodzNode.userData["entities"] = self.wrapper.replaceDuplicatesInSelection(
                                        cacheProxyName, entitiesIDsExpression
                                    )
                                    self.createOrRefreshNodeAttributes(selectorNodzNode)
                                # connect
                                if previousNodeInst is not None:
                                    nodzInst.createConnection(
                                        previousNodeInst.name,
                                        previousNodeInst.attrs[0],
                                        selectorNodzNode.name,
                                        selectorNodzNode.attrs[0],
                                    )
                                previousNodeInst = selectorNodzNode
                                newNodePos = newNodePos + nodePositionOffset
                        # else, no selection : only stack the operator after the root

                        # if we have no selection, and node is not Note or EntitySelector + no previous selector, we don't authorize continuing
                        # we must also exit if we have a selector as node to make and we did it
                        if (isSelector and hasSelector) or (
                            previousNodeInst is None and not (isNote or isSelector)
                        ):  # no selection, we can't add an operator on nothing
                            break

                        # shall we create a new node if attribute value is different ?
                        if (previousNodeInst is None) or (
                            (previousNodeInst.attrs[0] != transformationNodeTypeName) or (previousNodeInst.attrs[0] == "Duplicate")
                        ):  # or (previousNodeInst.attrs[0] == "Duplicate") : #the transform type is always set in the attribute at index 0

                            # add the transformation node
                            operatorNodzNode = None
                            try:
                                operatorNodzNode = self.GolaemLayoutNodeCreator(nodzInst, transformationNodeTypeName, newNodePos)
                            except Exception as e:
                                print("-----{} was not recognized as a valid layout node (exception: {})".format(transformationNodeTypeName, e))

                            if operatorNodzNode is not None:  # can happen if requesting a addOrEdit on a wrong type
                                # connect
                                if previousNodeInst is not None:
                                    nodzInst.createConnection(
                                        previousNodeInst.name,
                                        previousNodeInst.attrs[0],
                                        operatorNodzNode.name,
                                        operatorNodzNode.attrs[0],
                                    )
                                # set as new root
                                self.setRootNode(nodzInst, operatorNodzNode)

                                # focus on the newly added node
                                nodzInst.centerOn(operatorNodzNode)
                                previousNodeInst = operatorNodzNode

                        modifiedOperator = previousNodeInst

                        editedNodeInst = previousNodeInst
                        if not isSelector and editedNodeInst is not None and "attributes" in editedNodeInst.userData:  # case of selector drop
                            for currentAttribute in editedNodeInst.userData["attributes"]:
                                if currentAttribute["name"] == parameterName:
                                    currentAttributeFrames = currentAttribute["frames"]
                                    currentAttributeValues = currentAttribute["values"]

                                    # find the correct frame index
                                    frameIndex = 0
                                    if len(currentAttributeFrames) > 0 and frame is not None:  # only adding frames on already keyframed attributes
                                        createNewKeyFrameValue = True
                                        newFrameIndex = -1
                                        for currentAttributeFrameIndex in range(len(currentAttributeFrames)):
                                            if currentAttributeFrames[currentAttributeFrameIndex] == frame:
                                                newFrameIndex = currentAttributeFrameIndex  # use this index, no need to create a new one
                                                createNewKeyFrameValue = False
                                                break
                                            elif currentAttributeFrames[currentAttributeFrameIndex] > frame:
                                                newFrameIndex = (
                                                    currentAttributeFrameIndex  # use this index, but create a new frame AND a new frame value
                                                )
                                                createNewKeyFrameValue = True
                                                break

                                        if newFrameIndex < 0:  # key frame is at the end
                                            createNewKeyFrameValue = True
                                            newFrameIndex = len(currentAttributeFrames)
                                        frameIndex = newFrameIndex

                                        if createNewKeyFrameValue:
                                            currentAttributeFrames.insert(frameIndex, frame)
                                            currentAttributeValues.insert(frameIndex, [])

                                    # now set the correct value(s)
                                    for valueIndex in range(len(parameterValue)):
                                        if currentAttribute["type"] in [
                                            GlmValueType.GTV_int32,
                                            GlmValueType.GTV_uint32,
                                            GlmValueType.GTV_int64,
                                            GlmValueType.GTV_float,
                                        ]:  # single types attributes
                                            # make sure there are at least the same count of values in the current parameters
                                            while len(currentAttributeValues[frameIndex]) < len(parameterValue):
                                                currentAttributeValues[frameIndex].append(0)
                                            # now set/add/mult
                                            if mode == 0:  # set
                                                currentAttributeValues[frameIndex][valueIndex] = parameterValue[valueIndex]
                                            elif mode == 1:  # add
                                                currentAttributeValues[frameIndex][valueIndex] += parameterValue[valueIndex]
                                            elif mode == 2:  # mult
                                                currentAttributeValues[frameIndex][valueIndex] *= parameterValue[valueIndex]
                                        elif currentAttribute["type"] == GlmValueType.GTV_char:
                                            # only set is supported for char attr
                                            currentAttributeValues[valueIndex] = parameterValue[valueIndex]
                                        elif currentAttribute["type"] == GlmValueType.GTV_vec3:  # 6: vec3
                                            # make sure there are at least the same count of values in the current parameters
                                            while len(currentAttributeValues[frameIndex]) < len(parameterValue):
                                                currentAttributeValues[frameIndex].append([0.0, 0.0, 0.0])
                                            # now set/add/mult
                                            if mode == 0:  # set
                                                currentAttributeValues[frameIndex][valueIndex][0] = parameterValue[valueIndex][0]
                                                currentAttributeValues[frameIndex][valueIndex][1] = parameterValue[valueIndex][1]
                                                currentAttributeValues[frameIndex][valueIndex][2] = parameterValue[valueIndex][2]
                                            elif mode == 1:  # add
                                                currentAttributeValues[frameIndex][valueIndex][0] += parameterValue[valueIndex][0]
                                                currentAttributeValues[frameIndex][valueIndex][1] += parameterValue[valueIndex][1]
                                                currentAttributeValues[frameIndex][valueIndex][2] += parameterValue[valueIndex][2]
                                            elif mode == 2:  # mult
                                                currentAttributeValues[frameIndex][valueIndex][0] *= parameterValue[valueIndex][0]
                                                currentAttributeValues[frameIndex][valueIndex][1] *= parameterValue[valueIndex][1]
                                                currentAttributeValues[frameIndex][valueIndex][2] *= parameterValue[valueIndex][2]
                                        elif currentAttribute["type"] == GlmValueType.GTV_vec4:  # 7: vec4
                                            # make sure there are at least the same count of values in the current parameters
                                            while len(currentAttributeValues[frameIndex]) < len(parameterValue):
                                                currentAttributeValues[frameIndex].append([0.0, 0.0, 0.0, 0.0])
                                            # now set/add/mult
                                            if mode == 0:  # set
                                                currentAttributeValues[frameIndex][valueIndex][0] = parameterValue[valueIndex][0]
                                                currentAttributeValues[frameIndex][valueIndex][1] = parameterValue[valueIndex][1]
                                                currentAttributeValues[frameIndex][valueIndex][2] = parameterValue[valueIndex][2]
                                                currentAttributeValues[frameIndex][valueIndex][3] = parameterValue[valueIndex][3]
                                            elif mode == 1:  # add
                                                currentAttributeValues[frameIndex][valueIndex][0] += parameterValue[valueIndex][0]
                                                currentAttributeValues[frameIndex][valueIndex][1] += parameterValue[valueIndex][1]
                                                currentAttributeValues[frameIndex][valueIndex][2] += parameterValue[valueIndex][2]
                                                currentAttributeValues[frameIndex][valueIndex][3] += parameterValue[valueIndex][3]
                                            elif mode == 2:  # mult
                                                currentAttributeValues[frameIndex][valueIndex][0] *= parameterValue[valueIndex][0]
                                                currentAttributeValues[frameIndex][valueIndex][1] *= parameterValue[valueIndex][1]
                                                currentAttributeValues[frameIndex][valueIndex][2] *= parameterValue[valueIndex][2]
                                                currentAttributeValues[frameIndex][valueIndex][3] *= parameterValue[valueIndex][3]
                                    self.createOrRefreshNodeAttributes(editedNodeInst)
                                    self.refreshAttributeEditor(editedNodeInst)
                                    break

        self.blockSignals(prevBlockSignalsStatus)
        # # addOrEdit being called by user, we should never be in a state where prevBlockSignalsStatus is True.
        # # that happened on internal crashes, which have been fixed (bad node type created was crashing the callstack)
        # # We may force a False to have "auto recovery" behavior, but that is sooo unsafe not to detect something wrong at this point
        # # this is the former behavior
        # self.blockSignals(False)

        # self.postModifyScene()

        if editedNodeInst is not None and editedNodz is not None and editedNodz.editEnabled:

            # find the edited node Id
            nodeID = editedNodeInst.userData["ID"]
            doRecomputeAssets = False
            if "type" in editedNodeInst.userData and editedNodeInst.userData["type"] in [
                GlmTransformType.SetMeshAssets,
                GlmTransformType.SetRenderingType,
                GlmTransformType.AddRemoveMeshAssets,
            ]:
                doRecomputeAssets = True

            self.stackUndo(editedTabIndex, nodeID, doRecomputeAssets)
            self.signal_LayoutNodeChanged.emit(self, editedNodeInst.name)
            if editedNodeInst.name not in editedNodz.selectedNodes:
                editedNodz.scene().clearSelection()
                editedNodeInst.setSelected(True)
                editedNodz._returnSelection()

        return modifiedOperator

    def updateSnapToValues(self, node, poptoolName, entityTypeName):
        self.snapToPosValues = None  # nothing done if it stays at None
        self.snapToOriValues = None  # nothing done if it stays at None

        # update
        self.signal_LayoutSnapToSlotsUpdate.emit(self, poptoolName, entityTypeName)

        if not (
            self.snapToPosValues is not None
            and self.snapToOriValues is not None
            and len(self.snapToPosValues) != 0
            and len(self.snapToOriValues) != 0
        ):
            print("got bad values from signal_LayoutSnapToSlotsUpdate")

        if (
            self.snapToPosValues is not None
            and self.snapToOriValues is not None
            and len(self.snapToPosValues) != 0
            and len(self.snapToOriValues) != 0
        ):

            # update current node userdata attributes
            prevBlockSignalsStatus = self.signalsBlocked()
            self.blockSignals(True)
            if "attributes" in node.userData:
                for attribute in node.userData["attributes"]:
                    attributeName = ""
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]

                    if attributeName == "snapToPos":
                        attribute["values"] = self.snapToPosValues
                    if attributeName == "snapToOri":
                        attribute["values"] = self.snapToOriValues
            self.blockSignals(prevBlockSignalsStatus)

            self.createOrRefreshNodeAttributes(node)

            self.signal_LayoutNodeChanged.emit(self, node.name)

    def updatePoptool(self, cacheProxyName, poptoolName):
        somethingChanged = 0
        if len(cacheProxyName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                    # find the correct layout node (by ID)
                    for node in nodzInst.scene().nodes:
                        currentNodeInst = nodzInst.scene().nodes[node]
                        if "type" in currentNodeInst.userData:
                            if currentNodeInst.userData["type"] == GlmTransformType.SnapTo:  # update snapTo if same poptool
                                # look desired attributes
                                if "attributes" in currentNodeInst.userData:
                                    for currentAttribute in currentNodeInst.userData["attributes"]:
                                        if "name" in currentAttribute and currentAttribute["name"] == "snapToTarget":
                                            if "values" in currentAttribute and currentAttribute["values"][0] == poptoolName:
                                                entityTypeName = None
                                                for otherAttribute in currentNodeInst.userData["attributes"]:
                                                    if (
                                                        "name" in otherAttribute
                                                        and otherAttribute["name"] == "entityType"
                                                        and "values" in otherAttribute
                                                    ):
                                                        if len(otherAttribute["values"]) > 0:
                                                            entityTypeName = otherAttribute["values"][0]
                                                            break
                                                # force update of slots
                                                self.updateSnapToValues(currentNodeInst, poptoolName, entityTypeName)
                                                somethingChanged = 1
        return somethingChanged

    def updateVectorFields(self, cacheProxyName, vectorFieldName):
        somethingChanged = 0
        if len(cacheProxyName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                    # find the correct layout node (by ID)
                    for node in nodzInst.scene().nodes:
                        currentNodeInst = nodzInst.scene().nodes[node]
                        if "type" in currentNodeInst.userData:
                            if (
                                currentNodeInst.userData["type"] == GlmTransformType.TrajectoryVectorField
                            ):  # update TrajectoryVectorField if same vector field
                                # look desired attributes
                                if "attributes" in currentNodeInst.userData:
                                    for currentAttribute in currentNodeInst.userData["attributes"]:
                                        if "name" in currentAttribute and currentAttribute["name"] == "target":
                                            if "values" in currentAttribute and currentAttribute["values"][0] == vectorFieldName:
                                                # force update of map
                                                self.updateVectorFieldValues(currentNodeInst, vectorFieldName)
                                                somethingChanged = 1
        return somethingChanged

    def updateVectorFieldValues(self, node, vectorFieldName):
        self.vectorFieldMap = None  # nothing done if it stays at None
        self.vectorFieldGeometry = None

        # update
        self.signal_LayoutVectorFieldUpdate.emit(self, vectorFieldName)

        nodeWasRefresh = False

        # vector field map
        if not (self.vectorFieldMap is not None and len(self.vectorFieldMap) != 0):
            print("got bad values from signal_LayoutVectorFieldUpdate")
        else:
            # update current node userdata attributes
            prevBlockSignalsStatus = self.signalsBlocked()
            self.blockSignals(True)
            if "attributes" in node.userData:
                for attribute in node.userData["attributes"]:
                    attributeName = ""
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                    if attributeName == "map":
                        attribute["values"] = list()
                        attribute["values"].append(self.vectorFieldMap)
                        nodeWasRefresh = True
            self.blockSignals(prevBlockSignalsStatus)

        # vector field geometry
        if not (self.vectorFieldGeometry is not None and len(self.vectorFieldGeometry) >= 3):
            print("got bad values from signal_LayoutVectorFieldUpdate")
        else:
            # update current node userdata attributes
            prevBlockSignalsStatus = self.signalsBlocked()
            self.blockSignals(True)
            if "attributes" in node.userData:
                for attribute in node.userData["attributes"]:
                    attributeName = ""
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                    if attributeName == "geoVertices":
                        attribute["values"] = list()
                        attribute["values"].append(self.vectorFieldGeometry[0])
                        nodeWasRefresh = True
                    elif attributeName == "geoNormals":
                        attribute["values"] = list()
                        attribute["values"].append(self.vectorFieldGeometry[1])
                        nodeWasRefresh = True
                    elif attributeName == "geoUVs":
                        attribute["values"] = list()
                        attribute["values"].append(self.vectorFieldGeometry[2])
                        nodeWasRefresh = True
                    elif attributeName == "geoTriangles":
                        attribute["values"] = list()
                        attribute["values"].append(self.vectorFieldGeometry[3])
                        nodeWasRefresh = True
            self.blockSignals(prevBlockSignalsStatus)
            nodeWasRefresh = True

        if nodeWasRefresh:
            self.createOrRefreshNodeAttributes(node)
            # update attribute editor if the node is edited
            self.refreshAttributeEditor(node)
            self.signal_LayoutNodeChanged.emit(self, node.name)

    def updatePaintedZones(self, cacheProxyName, paintedZoneName):
        somethingChanged = 0
        if len(cacheProxyName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                    # find the correct layout node (by ID)
                    for node in nodzInst.scene().nodes:
                        currentNodeInst = nodzInst.scene().nodes[node]
                        if "type" in currentNodeInst.userData:
                            if (
                                currentNodeInst.userData["type"] == GlmTransformType.SetShaderAttribute
                                or currentNodeInst.userData["type"] == GlmTransformType.SetAttribute
                            ):  # update SetShaderAttribute if same paitned zone
                                # look desired attributes
                                if "attributes" in currentNodeInst.userData:
                                    for currentAttribute in currentNodeInst.userData["attributes"]:
                                        if "name" in currentAttribute and currentAttribute["name"] == "target":
                                            if "values" in currentAttribute and currentAttribute["values"][0] == paintedZoneName:
                                                # force update of map
                                                self.updatePaintedZoneValues(currentNodeInst, paintedZoneName)
                                                somethingChanged = 1
        return somethingChanged

    def updatePaintedZoneValues(self, node, paintedZoneName):
        self.paintedZoneMap = None  # nothing done if it stays at None
        self.paintedZoneGeometry = None

        # update
        self.signal_LayoutPaintedZoneUpdate.emit(self, paintedZoneName)

        nodeWasRefresh = False

        # vector field map
        if not (self.paintedZoneMap is not None and len(self.paintedZoneMap) != 0):
            print("got bad values from signal_LayoutPaintedZoneUpdate")
        else:
            # update current node userdata attributes
            prevBlockSignalsStatus = self.signalsBlocked()
            self.blockSignals(True)
            if "attributes" in node.userData:
                for attribute in node.userData["attributes"]:
                    attributeName = ""
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                    if attributeName == "map":
                        attribute["values"] = list()
                        attribute["values"].append(self.paintedZoneMap)
                        nodeWasRefresh = True
            self.blockSignals(prevBlockSignalsStatus)

        # vector field geometry
        if not (self.paintedZoneGeometry is not None and len(self.paintedZoneGeometry) >= 3):
            print("got bad values from signal_LayoutPaintedZoneUpdate")
        else:
            # update current node userdata attributes
            prevBlockSignalsStatus = self.signalsBlocked()
            self.blockSignals(True)
            if "attributes" in node.userData:
                for attribute in node.userData["attributes"]:
                    attributeName = ""
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                    if attributeName == "geoVertices":
                        attribute["values"] = list()
                        attribute["values"].append(self.paintedZoneGeometry[0])
                        nodeWasRefresh = True
                    elif attributeName == "geoNormals":
                        attribute["values"] = list()
                        attribute["values"].append(self.paintedZoneGeometry[1])
                        nodeWasRefresh = True
                    elif attributeName == "geoUVs":
                        attribute["values"] = list()
                        attribute["values"].append(self.paintedZoneGeometry[2])
                        nodeWasRefresh = True
                    elif attributeName == "geoTriangles":
                        attribute["values"] = list()
                        attribute["values"].append(self.paintedZoneGeometry[3])
                        nodeWasRefresh = True
            self.blockSignals(prevBlockSignalsStatus)
            nodeWasRefresh = True

        if nodeWasRefresh:
            self.createOrRefreshNodeAttributes(node)
            # update attribute editor if the node is edited
            self.refreshAttributeEditor(node)
            self.signal_LayoutNodeChanged.emit(self, node.name)

    def updateTrajectoryValues(self, node, currentTabName, layoutNodeID):
        self.meshVertices = None  # nothing done if it stays at None

        # update
        self.signal_LayoutEditTrajectoryMeshUpdate.emit(self, currentTabName, layoutNodeID)

        if not (self.meshVertices is not None and len(self.meshVertices) != 0):
            print("got bad values from signal_LayoutEditTrajectoryMeshUpdate")

        if self.meshVertices is not None and len(self.meshVertices) != 0:

            # update current node userdata attributes
            prevBlockSignalsStatus = self.signalsBlocked()
            self.blockSignals(True)
            if "attributes" in node.userData:
                for attribute in node.userData["attributes"]:
                    attributeName = ""
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]

                    if attributeName == "dstMesh":
                        attribute["values"] = [self.meshVertices]
            self.blockSignals(prevBlockSignalsStatus)

            self.createOrRefreshNodeAttributes(node)

            self.signal_LayoutNodeChanged.emit(self, node.name)

    def updateAllTrajectories(self, currentTabName):
        somethingChanged = 0
        if len(currentTabName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == currentTabName:
                    nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                    # find the correct layout node (by ID)
                    for node in nodzInst.scene().nodes:
                        currentNodeInst = nodzInst.scene().nodes[node]
                        if "type" in currentNodeInst.userData:
                            if currentNodeInst.userData["type"] == GlmTransformType.EditTrajectory:  # update EditTrajectory
                                # force update of vertices
                                self.updateTrajectoryValues(currentNodeInst, currentTabName, currentNodeInst.userData["ID"])

        return somethingChanged

    def editLayoutParameter(self, cacheProxyName, parameterName, parameterType, parameterValue):
        prevBlockSignalsStatus = self.signalsBlocked()
        self.blockSignals(True)

        nodeEdited = False

        if len(cacheProxyName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                    if nodzInst is not None and nodzInst.editEnabled:

                        if not "parameters" in nodzInst.scene().userData:
                            nodzInst.scene().userData["parameters"] = []

                        for currentAttribute in nodzInst.scene().userData["parameters"]:
                            if currentAttribute["name"] == parameterName:
                                # now replace the keyFrames and keyValues of the attribute
                                currentAttribute["type"] = parameterType
                                currentAttribute["frames"] = []
                                currentAttribute["values"] = [[parameterValue]]
                                nodeEdited = True
                        if not nodeEdited:
                            # add the attribute
                            currentAttribute = dict()
                            currentAttribute["name"] = parameterName
                            currentAttribute["type"] = parameterType
                            currentAttribute["frames"] = []
                            currentAttribute["values"] = [[parameterValue]]
                            nodzInst.scene().userData["parameters"].append(currentAttribute)

                            nodeEdited = True

        self.blockSignals(prevBlockSignalsStatus)
        if nodeEdited:
            self.signal_LayoutParameterChanged.emit(self)

    def editLayoutNodeAttribute(self, cacheProxyName, nodeID, attributeName, keyFrames, keyValues, createIfAbsent=True, newType=0, newFlags=0, refreshAttributeEditor=True):
        prevBlockSignalsStatus = self.signalsBlocked()
        self.blockSignals(True)

        editedNodeInst = None

        if len(cacheProxyName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                    if nodzInst is not None and nodzInst.editEnabled:
                        # find the correct layout node (by ID)
                        currentNodeInst = self.getNodeItemFromId(nodzInst, nodeID)
                        if currentNodeInst is not None:
                            # look desired attributes
                            if "attributes" in currentNodeInst.userData:
                                for currentAttribute in currentNodeInst.userData["attributes"]:
                                    if currentAttribute["name"] == attributeName:
                                        # now replace the keyFrames and keyValues of the attribute
                                        currentAttribute["frames"] = keyFrames
                                        currentAttribute["values"] = keyValues
                                        editedNodeInst = currentNodeInst
                                if editedNodeInst is None:
                                    if createIfAbsent:
                                        # add the attribute
                                        currentAttribute = dict()
                                        currentAttribute["name"] = attributeName
                                        currentAttribute["type"] = newType
                                        currentAttribute["flags"] = newFlags
                                        currentAttribute["frames"] = keyFrames
                                        currentAttribute["values"] = keyValues
                                        currentNodeInst.userData["attributes"].append(currentAttribute)
                                        editedNodeInst = currentNodeInst
                                    else:
                                        print("Did not find attribute {} in Node Id {}".format(attributeName, nodeID))

                                # refresh display
                                # self.checkNodeAttributes(currentNodeInst)
                                self.createOrRefreshNodeAttributes(currentNodeInst)
                                if(refreshAttributeEditor):
                                    self.refreshAttributeEditor(editedNodeInst)
                                break

        self.blockSignals(prevBlockSignalsStatus)

        if editedNodeInst != None:
            self.signal_LayoutNodeChanged.emit(self, editedNodeInst.name)

    def editLayoutPostureNodeAttribute(
        self,
        attribute,
        attributeName,
        keyFrames,
        keyValues,
        valueIndex,
        valuesCount,
        valueType,
        overrideExistingKeyframes,
    ):
        # create attribute if not existing
        if attribute is None:
            attribute = dict()
            attribute["name"] = attributeName
            attribute["flags"] = GlmAttributeFlags._uiKeyframable
            attribute["type"] = valueType
            # frames
            attribute["frames"] = list()
            # values
            attribute["values"] = list()  # that's the list of keyframes
        elif overrideExistingKeyframes:
            attribute["frames"] = list()
            attribute["values"] = list()

        # create the correct amount of keyframes
        if keyFrames is not None:
            for keyIndex in range(len(keyFrames)):
                keyFrame = keyFrames[keyIndex]
                keyValue = keyValues[keyIndex]
                # find the correct keyframe position
                keyFrameIndex = -1
                for existingKeyFrameIndices in range(len(attribute["frames"])):
                    if keyFrame == attribute["frames"][existingKeyFrameIndices]:
                        keyFrameIndex = existingKeyFrameIndices
                        break
                    elif keyFrame < attribute["frames"][existingKeyFrameIndices]:
                        keyFrameIndex = existingKeyFrameIndices
                        attribute["frames"].insert(keyFrameIndex, keyFrame)
                        attribute["values"].insert(keyFrameIndex, list())
                        break
                if keyFrameIndex < 0:  # the keyframe is > to all values in the current list
                    keyFrameIndex = len(attribute["frames"])
                    attribute["frames"].append(keyFrame)
                    while len(attribute["values"]) < len(attribute["frames"]):
                        attribute["values"].append(list())
                # append at the correct bone position
                while len(attribute["values"][keyFrameIndex]) <= valueIndex:
                    if (
                        valueType == GlmValueType.GTV_int32
                        or valueType == GlmValueType.GTV_uint32
                        or valueType == GlmValueType.GTV_int64
                        or valueType == GlmValueType.GTV_float
                    ):
                        attribute["values"][keyFrameIndex].append(0)  # default value
                    elif valueType == GlmValueType.GTV_vec3:
                        attribute["values"][keyFrameIndex].append([0, 0, 0])  # default value
                    elif valueType == GlmValueType.GTV_vec4:
                        attribute["values"][keyFrameIndex].append([0, 0, 0, 0])  # default value
                attribute["values"][keyFrameIndex][valueIndex] = keyValue

        # make sure the list of keys is of correct size...
        while len(attribute["values"]) < max(1, len(keyFrames)):
            attribute["values"].append(list())
        # make sure the list of values for each key is of correct size...
        for attributeKeyValues in attribute["values"]:
            while len(attributeKeyValues) < valuesCount:
                if (
                    valueType == GlmValueType.GTV_int32
                    or valueType == GlmValueType.GTV_uint32
                    or valueType == GlmValueType.GTV_int64
                    or valueType == GlmValueType.GTV_float
                ):
                    attributeKeyValues["values"][keyFrameIndex].append(0)  # default value
                elif valueType == GlmValueType.GTV_vec3:
                    attributeKeyValues["values"][keyFrameIndex].append([0, 0, 0])  # default value
                elif valueType == GlmValueType.GTV_vec4:
                    attributeKeyValues["values"][keyFrameIndex].append([0, 0, 0, 0])  # default value
        return attribute

    def editLayoutPostureNode(
        self,
        cacheProxyName,
        nodeID,
        boneIndex,
        boneLabel,
        transformLabel,
        transformKeyFrames,
        transformValues,
        valueType,
        operationMode,
        overrideExistingKeyframes=False,
    ):
        """
        Edit the existing layout posture node

        :type  cacheProxyName: str.
        :param cacheProxyName: Name of the tab widget in which adding a tansform

        :type  nodeID: int.
        :param nodeID: ID of the layout node to edit

        :type  boneIndex: int.
        :param boneIndex: bone index for which adding a transform

        :type  boneLabel: str.
        :param boneLabel: bone label to use in the attribute name (only for display purposes)

        :type  transformLabel: str.
        :param transformLabel: transform to edit (only "localOri" or "localPos" are handled for now)

        :type  transformKeyFrames: list.
        :param transformKeyFrames: new keyframes for the bone/transform

        :type  transformValues: list.
        :param transformValues: new key values for the bone/transform

        :type  operationMode: str.
        :param operationMode: operation mode of the node: 0 to add, 1 to set
        """
        prevBlockSignalsStatus = self.signalsBlocked()
        self.blockSignals(True)

        foundTab = False
        editedNodeInst = None

        # find the correct tab widget
        if len(cacheProxyName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    foundTab = True
                    nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                    if nodzInst is not None and nodzInst.editEnabled:
                        currentNodeInst = self.getNodeItemFromId(nodzInst, nodeID)
                        if currentNodeInst is not None:
                            editedNodeInst = currentNodeInst
                            # print("layoutEditor editLayoutPostureNode: found node")
                            transformAttributeName = "{}-{}-{}".format(boneLabel, boneIndex, transformLabel)
                            operationModeAttribute = None
                            # boneIndexAttribute = None
                            transformAttribute = None
                            # look desired attributes
                            for currentAttribute in currentNodeInst.userData["attributes"]:
                                if currentAttribute["name"] == "operationMode":
                                    operationModeAttribute = currentAttribute
                                elif currentAttribute["name"] == transformAttributeName:
                                    transformAttribute = currentAttribute
                            # create missing attribute(s), or update the existing one
                            # operationMode
                            if operationModeAttribute is None:
                                operationModeAttribute = dict()
                                operationModeAttribute["name"] = "operationMode"
                                operationModeAttribute["frames"] = list()
                                operationModeAttribute["type"] = GlmValueType.GTV_uint32
                                operationModeAttribute["values"] = list()  # that's the list of keyframes
                                operationModeAttribute["values"].append(list())  # append first keyframe
                                operationModeAttribute["values"][0].append(operationMode)
                                currentNodeInst.userData["attributes"].append(operationModeAttribute)
                            else:
                                doIt = True
                                for item in operationModeAttribute.items():
                                    if item[0] == "type":
                                        if item[1] != GlmValueType.GTV_uint32:
                                            doIt = False
                                            print(
                                                'Error in LayoutEditor::editLayoutPostureNode: the existing "operationMode" attribute is not a uint32 type'
                                            )
                                if doIt:
                                    operationModeAttribute["values"] = list()  # that's the list of keyframes
                                    operationModeAttribute["values"].append(list())  # append first keyframe
                                    operationModeAttribute["values"][0].append(operationMode)

                            # handle transform
                            newTransformAttribute = self.editLayoutPostureNodeAttribute(
                                transformAttribute,
                                transformAttributeName,
                                transformKeyFrames,
                                transformValues,
                                0,
                                1,
                                valueType,
                                overrideExistingKeyframes,
                            )
                            if transformAttribute is None:
                                currentNodeInst.userData["attributes"].append(newTransformAttribute)

                            # refresh display
                            # print("layoutEditor editLayoutPostureNode: refresh node {}".format(currentNodeInst.userData['ID']))
                            # self.checkNodeAttributes(currentNodeInst)
                            self.createOrRefreshNodeAttributes(currentNodeInst)
                            self.refreshAttributeEditor(currentNodeInst)
                            break

        if not foundTab:
            print("Error in LayoutEditor::editLayoutPostureNode: could not find the tab named {}".format(cacheProxyName))
        elif editedNodeInst is None:
            print("Error in LayoutEditor::editLayoutPostureNode: could not find the node ID {} in the tab named {}".format(nodeID, cacheProxyName))

        self.blockSignals(prevBlockSignalsStatus)

        if editedNodeInst != None:
            self.signal_LayoutNodeChanged.emit(self, editedNodeInst.name)

    def setHighlightedLayoutNodesIDs(self, cacheProxyName, layoutNodeIDsList):
        """
        Set highlight on a set of given layout nodes

        :type  cacheProxyName: str.
        :param cacheProxyName: Name of the tab widget in which adding a tansform

        :type  layoutNodeIDsList: list.
        :param layoutNodeIDsList: list of layout nodes, presented as a list (example: [0,16,81] )
        """
        prevBlockSignalsStatus = self.signalsBlocked()
        self.blockSignals(True)

        if len(cacheProxyName) > 0:
            for tabIndex in range(self.editorTabWidget.count()):
                tabName = self.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    nodzInst = self.layoutViewTabWidgets[tabIndex].editedNodz
                    # iterate on scene nodes
                    for node in nodzInst.scene().nodes:
                        currentNodeInst = nodzInst.scene().nodes[node]
                        currentNodeID = currentNodeInst.userData["ID"]
                        highlightCurrentNode = False

                        # iterate on nodes to highlight
                        for layoutNodeIdToHighlight in layoutNodeIDsList:
                            if currentNodeID == layoutNodeIdToHighlight:
                                highlightCurrentNode = True
                                break

                        # find base attribute preset name
                        isNote = False
                        baseAttributePresetName = "attr_preset_LayoutOperatorConnection"
                        selectorEntities = False
                        isSelectorFilter = False
                        for item in currentNodeInst.userData.items():
                            if item[0] == "entities":
                                selectorEntities = item[1]
                            elif item[0] == "filterInput":
                                isSelectorFilter = item[1] == 1
                            elif item[0] == "type":
                                operatorType = item[1]
                                if (
                                    operatorType == GlmTransformType.Duplicate or operatorType == GlmTransformType.SnapTo
                                ):  # duplicate and snap to have specific presets
                                    baseAttributePresetName = "attr_preset_LayoutSelectorConnection"
                                    break
                                elif operatorType == GlmTransformType.Note:
                                    isNote = True
                                    break

                        if isSelectorFilter:
                            baseAttributePresetName = "attr_preset_LayoutSelectorConnection"
                        elif selectorEntities:
                            baseAttributePresetName = "attr_preset_LayoutSelectorFilterConnection"

                        # note is static regarding presets
                        if not isNote:
                            attributePresetName = baseAttributePresetName
                            if highlightCurrentNode:
                                attributePresetName = attributePresetName + "_highlight"

                            # print("Set style on node {} : {}".format(node, attributePresetName))
                            typeAttributeName = currentNodeInst.attrs[0]
                            currentNodeInst.attrsData[typeAttributeName]["preset"] = attributePresetName
                            currentNodeInst.update()

                    break  # don't iterate on other tabs

        self.blockSignals(prevBlockSignalsStatus)

    def setSelectedNodeIDs(self, initTabName, selectedNodeIds):
        currentTabName = self.getCurrentTabName()

        # Only operate layoutEditor selection if in current view ?
        if currentTabName != initTabName:
            return

        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            return

        prevBlockSignalsStatus = self.signalsBlocked()
        self.blockSignals(True)
        currentNodz.scene().clearSelection()
        layoutNodes = currentNodz.scene().nodes
        for nodeId in selectedNodeIds:
            if nodeId in list(layoutNodes.keys()):
                currentNodz.selectedNodes.append(layoutNodes[nodeId])
                layoutNodes[nodeId].setSelected(True)

        self.blockSignals(prevBlockSignalsStatus)
        currentNodz.scene().update()

    def copySelectedNodesAt(self, nodesToCopy, fromNodz, positionF, destNodz=None, moveNodesMode=False, copyRoot=False):
        toNodz = self.getCurrentNodz()
        if destNodz is not None:
            toNodz = destNodz

        if toNodz is None:
            print("Error: no tab selected")
            return

        # self.preModifyScene()

        modelNodeIdToPastedNodeId = dict()
        modelNodeIdToNode = dict()
        pasteNodeIdToNode = dict()

        modelGroupNodeIds = list()

        barycenter = QtCore.QPointF(0, 0)
        baryCount = 0

        if fromNodz is None:
            return

        for nodeToCopy in nodesToCopy:
            if not nodeToCopy in fromNodz.scene().nodes:
                print("Did not find {} node to copy".format(nodeToCopy))
                continue

            modelNode = fromNodz.scene().nodes[nodeToCopy]
            if modelNode is None:
                continue

            barycenter += (
                QtCore.QPointF(modelNode.pos().x(), modelNode.pos().y()) + modelNode.nodeCenter
            )  # QtCore.QPointF(modelNode.userData['GUI_pos'][0], modelNode.userData['GUI_pos'][1]) + modelNode.nodeCenter
            baryCount += 1

        barycenter = old_div(barycenter, baryCount)

        for nodeToCopy in nodesToCopy:
            if not nodeToCopy in fromNodz.scene().nodes:
                continue

            modelNode = fromNodz.scene().nodes[nodeToCopy]

            if modelNode is None:
                continue

            # positionF = QtCore.QPointF
            if "type_name" in modelNode.userData:
                nodeTypeName = modelNode.userData["type_name"]
            else:
                nodeTypeName = "EntitySelector"

            positionOffsetF = QtCore.QPointF(modelNode.pos().x(), modelNode.pos().y()) + modelNode.nodeCenter - barycenter
            if moveNodesMode:
                createdNode = self.GolaemLayoutNodeCreator(toNodz, nodeTypeName, positionOffsetF + positionF, modelNode.userData["ID"])
            else:
                createdNode = self.GolaemLayoutNodeCreator(toNodz, nodeTypeName, positionOffsetF + positionF)

            # Copy attribute values
            createdNode.baseZValue = copy.deepcopy(modelNode.baseZValue)
            createdNode.setZValue(modelNode.zValue())

            createdNode.attrs = copy.deepcopy(modelNode.attrs)
            createdNode.attrsData = copy.deepcopy(modelNode.attrsData)
            createdNode.attrCount = copy.deepcopy(modelNode.attrCount)

            # in user data keep pos, ID to default ones, type and type_name are also already set
            createdNode.userData["active"] = copy.deepcopy(modelNode.userData["active"])
            createdNode.userData["name"] = copy.deepcopy(modelNode.userData["name"])

            # for operators
            if "attributes" in createdNode.userData:
                createdNode.userData["attributes"] = copy.deepcopy(modelNode.userData["attributes"])

            # for selectors
            if "entities" in createdNode.userData:
                createdNode.userData["entities"] = copy.deepcopy(modelNode.userData["entities"])
            if "filterInput" in createdNode.userData:
                createdNode.userData["filterInput"] = copy.deepcopy(modelNode.userData["filterInput"])
            if "percent" in createdNode.userData:
                createdNode.userData["percent"] = copy.deepcopy(modelNode.userData["percent"])
            if "randomSeed" in createdNode.userData:
                createdNode.userData["randomSeed"] = copy.deepcopy(modelNode.userData["randomSeed"])

            modelNodeId = modelNode.userData["ID"]
            createdNodeId = createdNode.userData["ID"]

            modelNodeIdToPastedNodeId[modelNodeId] = createdNodeId
            modelNodeIdToNode[modelNodeId] = modelNode
            pasteNodeIdToNode[createdNodeId] = createdNode

            if nodeTypeName == "Group":
                modelGroupNodeIds.append(modelNodeId)

            self.createOrRefreshNodeAttributes(createdNode)

            # patch the position, as the node is placed centered before adding attributes
            createdNode.setPos(positionOffsetF + positionF - createdNode.nodeCenter)
            createdNode.update()

        # In a second loop, recreate connections between copied nodes
        for entryKey in modelNodeIdToNode:
            modelNode = modelNodeIdToNode[entryKey]
            pastedNodeId = modelNodeIdToPastedNodeId[entryKey]
            pastedNode = pasteNodeIdToNode[pastedNodeId]

            if modelNode.sockets:
                for socket in list(modelNode.sockets.values()):
                    for connection in socket.connections:
                        otherNodeId = fromNodz.scene().nodes[connection.plugNode].userData["ID"]
                        if otherNodeId in modelNodeIdToPastedNodeId:
                            # both nodes exist in pasted group, create a connection between pasted nodes
                            sourceNode = pasteNodeIdToNode[modelNodeIdToPastedNodeId[otherNodeId]].name
                            sourceAttr = copy.deepcopy(connection.plugAttr)
                            destNode = pastedNode.name
                            destAttr = copy.deepcopy(connection.socketAttr)
                            # print("Connecting {}.{} to {}.{}".format(sourceNode, sourceAttr, destNode ,destAttr))
                            toNodz.createConnection(sourceNode, sourceAttr, destNode, destAttr)

            # if connections are inner to group : both plug and socket exists in the group, no need to double the links by processing plugs after sockets !

            # if modelNode.plugs:
            #     for plug in modelNode.plugs.values():
            #         for connection in plug.connections:
            #             otherNodeId = fromNodz.scene().nodes[connection.socketNode].userData['ID']
            #             if otherNodeId in modelNodeIdToPastedNodeId:
            #                 # both nodes exist in pasted group, create a connection between pasted nodes
            #                 sourceNode = pastedNode.name
            #                 sourceAttr = copy.deepcopy(connection.plugAttr)
            #                 destNode = pasteNodeIdToNode[ modelNodeIdToPastedNodeId[ otherNodeId ] ].name
            #                 destAttr = copy.deepcopy(connection.socketAttr)
            #                 #print("Connecting {}.{} to {}.{}".format(sourceNode, sourceAttr, destNode ,destAttr))
            #                 toNodz.createConnection(sourceNode, sourceAttr, destNode, destAttr)

        # finally, recursively call groups to be copied too if we do'nt just "displace" the groups
        thisTabWidget = self.layoutViewTabWidgets[self.getCurrentTabIndex()]

        if copyRoot:
            # copy nodes to child group / Nodz
            destGroupRootId = None
            if toNodz.scene().userData is not None:
                # for item in groupNodz.scene().userData.items():
                if "rootTransformId" in toNodz.scene().userData:
                    destGroupRootId = toNodz.scene().userData["rootTransformId"]

            if (
                destGroupRootId is None or destGroupRootId == -1 or self.getNodeItemFromId(toNodz, destGroupRootId) is None
            ):  # if no current group, create/copy root
                copiedGroupRootNode = None

                # find a suitable root : either a copied one or the first node met with only & maximum count of input connection
                if "rootTransformId" in fromNodz.scene().userData:
                    modelGroupRootId = fromNodz.scene().userData["rootTransformId"]
                    if modelGroupRootId in modelNodeIdToPastedNodeId:
                        copiedGroupRootId = modelNodeIdToPastedNodeId[modelGroupRootId]
                        copiedGroupRootNode = pasteNodeIdToNode[copiedGroupRootId]
                    else:
                        # iterate on copied nodes, find the one with most inputs and no outputs
                        maxInput = 0
                        for pastedNode in pasteNodeIdToNode.items():
                            skipNode = False
                            for plugItem in pastedNode[1].plugs.items():
                                if len(plugItem[1].connected_slots) > 0:
                                    skipNode = True

                            if not skipNode:
                                for socketItem in pastedNode[1].sockets.items():
                                    socketConnectionCount = len(socketItem[1].connected_slots)
                                    if socketConnectionCount > maxInput:
                                        # our current best candidate to be the new root
                                        maxInput = socketConnectionCount
                                        copiedGroupRootNode = pastedNode[1]
                if copiedGroupRootNode is not None:
                    self.setRootNode(toNodz, copiedGroupRootNode)
                    self.createOrRefreshNodeAttributes(copiedGroupRootNode, toNodz)

        for modelGroupNodeId in modelGroupNodeIds:
            if not moveNodesMode:
                copiedGroupNodeId = modelNodeIdToPastedNodeId[modelGroupNodeId]

                modelTabIndex = self.getNodzTabIndex(fromNodz)
                modelTabWidget = self.layoutViewTabWidgets[modelTabIndex]
                modelGroupNodz = modelTabWidget.childrenNodz[modelGroupNodeId]
                copiedGroupNodz = thisTabWidget.childrenNodz[copiedGroupNodeId]

                self.copySelectedNodesAt(list(modelGroupNodz.scene().nodes.keys()), modelGroupNodz, positionF, copiedGroupNodz, False, True)

            else:
                # patch parentNodz with correct new value
                copiedGroupNodeId = modelNodeIdToPastedNodeId[modelGroupNodeId]
                copiedGroupNodz = thisTabWidget.childrenNodz[copiedGroupNodeId]
                copiedGroupNodz.scene().userData["parentNodz"] = destNodz

        if moveNodesMode:
            # actually remove nodes
            for nodeToCopy in nodesToCopy:
                # note that group Nodz have been TRANSFERED in that case
                fromNodz.scene().nodes[nodeToCopy]._remove()

    ######################################################################
    # Slots
    ######################################################################

    def startCompoundInteraction(self, nodzInst):
        self.wrapper.blockSignalsFromLayoutEditor = True
        self.wrapper.compoundDirtyAssetRepartition = False
        self.wrapper.compoundDirtyLayoutNodeIDs = list()

    def endCompoundInteraction(self, nodzInst, somethingChanged):
        self.wrapper.blockSignalsFromLayoutEditor = False
        if somethingChanged:
            self.signal_LayoutEndCompoundInteraction.emit(self)

    def dropOnGroup(self, nodzInst, groupNodeName):
        # must move selection to group :
        if groupNodeName in nodzInst.scene().nodes:
            groupNodeItem = nodzInst.scene().nodes[groupNodeName]
            nodeId = groupNodeItem.userData["ID"]
            # get group nodz from group Id and tab widget
            tabWidget = self.getCurrentTabWidget()
            if tabWidget is not None and nodeId in tabWidget.childrenNodz:
                self.on_groupSelectedNodes(nodzInst.selectedNodes, tabWidget.childrenNodz[nodeId])

    # Main windows
    def on_show(self):
        self.show()

    def on_hide(self):
        self.hide()

    def on_keyPressed(self, key):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None or not currentNodz.editEnabled:
            return True

        # set a single selected node as root
        if (
            key == QtCore.Qt.Key_V
            and (not (QtCore.Qt.Key_Control in currentNodz.pressedKeys))
            and len(currentNodz.selectedNodes) == 1
            and currentNodz.editEnabled
        ):
            singleSelectedNode = currentNodz.scene().nodes[currentNodz.selectedNodes[0]]
            if (
                "type" not in singleSelectedNode.userData or singleSelectedNode.userData["type"] != GlmTransformType.Note
            ):  # Notes have no right click menu
                self.setRootNode(currentNodz, singleSelectedNode, enableToggle=True)
                self.signal_LayoutRootChanged.emit(self, currentNodz.selectedNodes[0])

        if key == QtCore.Qt.Key_G and QtCore.Qt.Key_Control in currentNodz.pressedKeys :
            self.on_groupSelectedNodes(currentNodz.selectedNodes)

        if key == QtCore.Qt.Key_Z and QtCore.Qt.Key_Control in currentNodz.pressedKeys:
            # print("Test Undo()")
            self.undo(self.getCurrentTabIndex())

        if key == QtCore.Qt.Key_Y and QtCore.Qt.Key_Control in currentNodz.pressedKeys:
            # print("Test Redo()")
            self.redo(self.getCurrentTabIndex())

        # print('key pressed : ', key)
        if key == QtCore.Qt.Key_L:  #'l' for layout selection
            currentNodz.autoLayoutGraph(currentNodz.selectedNodes)
        # if key==QtCore.Qt.Key_O:  #'o' to open a .gscl file
        #     self.on_openAction()
        if (
            key == QtCore.Qt.Key_S and QtCore.Qt.Key_Control in currentNodz.pressedKeys
        ):  #'s' to save a .gscl file --> s is already 'snap to grid' when a node is selected
            # need to empty the pressedKeys arrays, cause saveAction will call back other stuff and lose layout focus.
            # We will not have the key release events while losing focus
            currentNodz.pressedKeys = []
            self.on_saveAction()
            return True

        if key == QtCore.Qt.Key_D and QtCore.Qt.Key_Control in currentNodz.pressedKeys:
            # we create a duplicate node on Control+D pressed, based on current selection :
            currentTabName = self.getCurrentTabName()
            selectedEntitiesIds = self.wrapper.getSelectedEntities(currentTabName)
            if currentTabName != "" and selectedEntitiesIds is not None and len(selectedEntitiesIds) > 0:
                self.addOrEditLayoutTransformation(
                    currentTabName,
                    selectedEntitiesIds,
                    "Duplicate",
                    parameterName=None,
                    parameterValue=None,
                    frame=None,
                    mode=0,
                )

        # copy with ctrl C OR copy for duplicate with ctrl D
        if (
            key == QtCore.Qt.Key_C and QtCore.Qt.Key_Control in currentNodz.pressedKeys
        ):  # or (key==QtCore.Qt.Key_D and QtCore.Qt.Key_Control in currentNodz.pressedKeys): # duplicate with ctrl D
            self.nodesToCopy[:] = []
            if currentNodz.selectedNodes is not None:
                self.nodesToCopyOriginNodz = self.getCurrentNodz()
                for selectedNode in currentNodz.selectedNodes:
                    self.nodesToCopy.append(selectedNode)
                print("Copying {}".format(str(self.nodesToCopy)))

        # paste with ctrl V OR paste for duplicate with ctrl D (Ctrl D does copy paste at once)
        if (
            key == QtCore.Qt.Key_V and QtCore.Qt.Key_Control in currentNodz.pressedKeys
        ):  # or (key==QtCore.Qt.Key_D and QtCore.Qt.Key_Control in currentNodz.pressedKeys):
            if self.nodesToCopyOriginNodz is not None and len(self.nodesToCopy) > 0:

                mouseViewPos = currentNodz.mapFromGlobal(QtGui.QCursor.pos())

                pastePos = currentNodz.mapToScene(mouseViewPos)
                # ToDo : ideally would get the cursor position but this will do the trick for now
                self.copySelectedNodesAt(self.nodesToCopy, self.nodesToCopyOriginNodz, pastePos)
                self.stackUndo(self.getCurrentTabIndex())

        self.signal_KeyPressed.emit(key)
        return True

    def on_newAction(self):
        self.newTab()
        self.stackUndo(self.getCurrentTabIndex())
        self.layoutViewTabWidgets[self.getCurrentTabIndex()].openViaOpenAction = True
        self.signal_LayoutGraphChanged.emit(self, True)

    def clearTab(self, tabIndex):
        if tabIndex == -1:
            print("Error: no tab selected")
            return
        tabWidget = self.layoutViewTabWidgets[tabIndex]
        mainNodz = tabWidget.mainNodz
        mainNodz.clearGraph()
        mainNodz.scene().userData = dict()
        mainNodz.scene().userData["nextNodeId"] = 0
        mainNodz.scene().userData["rootTransformId"] = -1
        mainNodz.scene().userData["licenseHashKey"] = 0
        # keep currentFilePath to be able to save on top of a previous gscl
        # if 'currentFilePath' in currentNodz.scene().userData:
        #     del currentNodz.scene().userData['currentFilePath']

        for childNodz in tabWidget.childrenNodz.items():
            childNodz[1].scene().userData = dict()
            childNodz[1].clearGraph()

        tabWidget.childrenNodz = dict()
        self.setEditedNodz(mainNodz)

        isPLE = True
        if usingDevkit:
            createReturnList = createGolaemLayout()
            if createReturnList is not None and isinstance(createReturnList, list) and len(createReturnList) == 2:
                layoutData = json.loads(createReturnList[0])
                isPLE = createReturnList[1]
                self.loadGolaemLayoutData(tabIndex, layoutData)  # should not change anything
            else:
                print("Could not create a new Layout. Possible cause is a license issue, or Golaem devkit library _devkit.pyd is not in python path.")
        tabWidget.displayPLEIconOnCurrentTab(self.PLEIconPath, isPLE)

    def on_clearAction(self):
        tabIndex = self.getCurrentTabIndex()
        if tabIndex == -1:
            print("Error: no tab selected")
            return

        # message box
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        msgBox.setWindowTitle("Delete all Layout Nodes")
        msgBox.setText("You are about to remove all Golaem Layout Nodes from the current tab. Are you sure that's what you'd like to do?")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        msgBoxPressed = msgBox.exec_()
        if msgBoxPressed == QtWidgets.QMessageBox.Cancel:
            return

        self.clearTab(tabIndex)
        self.stackUndo(tabIndex)
        # keep currentFilePath to be able to save on top of a previous gscl
        # if 'currentFilePath' in currentNodz.scene().userData:
        #     del currentNodz.scene().userData['currentFilePath']

        self.signal_LayoutGraphChanged.emit(self, True)

    def openLayoutFile(self, filePath):
        # check if an opened tab has this filePath as currentFilePath,
        selectTabIndex = -1
        for aTabIndex in range(self.editorTabWidget.count()):
            tabWidget = self.layoutViewTabWidgets[aTabIndex]
            mainNodz = tabWidget.mainNodz
            if "currentFilePath" in mainNodz.scene().userData:
                aTabFilePath = mainNodz.scene().userData["currentFilePath"]
                if aTabFilePath == filePath:
                    selectTabIndex = aTabIndex
                    break

        if selectTabIndex != -1:
            self.editorTabWidget.setCurrentIndex(selectTabIndex)
        else:
            # if currentNodz is None: -> always open a new tab when opening a gscl
            currentNodz = self.newTab(os.path.basename(filePath))
            self.layoutViewTabWidgets[self.getCurrentTabIndex()].openViaOpenAction = True
            if filePath is not None and filePath != "":
                self.loadGolaemLayoutFile(filePath, focus=True, autoLayout=False)
                # currentNodz.editEnabled = False # for test purpose
                currentNodz.scene().userData["currentFilePath"] = filePath
            else:
                # there was no signal emitted from newTab, send one now
                self.signal_LayoutGraphChanged.emit(self, True)
            self.stackUndo(self.getCurrentTabIndex())

        return self.layoutViewTabWidgets[self.getCurrentTabIndex()]

    def on_openAction(self):
        filePath = self.wrapper.openLayoutFile()
        if filePath is not None and len(filePath) > 0:
            self.openLayoutFile(filePath)

    def on_saveAction(self):
        currentNodz = self.getCurrentMainNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            return

        filePath = ""
        if "currentFilePath" in currentNodz.scene().userData:
            filePath = currentNodz.scene().userData["currentFilePath"]
        else:
            tabName = self.getLayoutNameForTab(self.editorTabWidget.currentIndex())
            qtSaveFiles = self.wrapper.openLayoutFile(True, tabName)
            filePath = qtSaveFiles
            currentNodz.scene().userData["currentFilePath"] = filePath
        if len(filePath) > 0:
            self.saveGolaemLayoutFile(currentNodz, self.getCurrentTabIndex(), filePath)

    def on_saveAsAction(self):
        currentNodz = self.getCurrentMainNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            return

        tabName = self.getLayoutNameForTab(self.editorTabWidget.currentIndex())
        filePath = self.wrapper.openLayoutFile(True, tabName)
        if len(filePath) > 0:
            self.saveGolaemLayoutFile(currentNodz, self.getCurrentTabIndex(), filePath)
            currentNodz.scene().userData["currentFilePath"] = filePath

    # # Widgets
    # def on_tabChanged(self, tabIndex):
    #     self.layoutViewTabWidgets[tabIndex].updateBreadcrumb()

    def on_configureAction(self):
        configuration = LayoutEditorConfiguration(self)

        # set current values...
        configuration.maxTablesDisplayCount = self.maxTablesDisplayCount

        configuration.initUI()
        retValue = configuration.exec_()

        # set back new values...
        if retValue == 1:
            self.maxTablesDisplayCount = configuration.maxTablesDisplayCount

    # Widgets
    def on_setModified(self):
        tabIndex = self.getCurrentTabIndex()
        if tabIndex >= 0:
            self.layoutViewTabWidgets[tabIndex].isModified = True
            # refresh tab name
            # tabName = self.getLayoutNameForTab(tabIndex, True)
            tabDisplayName = self.getLayoutDisplayNameForTab(tabIndex, True)
            self.editorTabWidget.setTabText(tabIndex, tabDisplayName)

    def on_clearModified(self, tabIndex, filePath):
        if tabIndex >= 0:
            self.layoutViewTabWidgets[tabIndex].isModified = False
            # refresh tab name
            #tabName = self.getLayoutNameForTab(tabIndex, True)
            tabDisplayName = self.getLayoutDisplayNameForTab(tabIndex, True)
            self.editorTabWidget.setTabText(tabIndex, tabDisplayName)

    def on_tabCloseRequested(self, tabIndex):
        if self.layoutActiveAttributeEditorWidget is not None:
            deletingNodz = self.layoutActiveAttributeEditorWidget.parent
            if (deletingNodz is self.layoutViewTabWidgets[tabIndex].mainNodz) or (deletingNodz in self.layoutViewTabWidgets[tabIndex].childrenNodz):
                self.setEditedNode(None, None)  # close attribute editor when we close parent main nodz

        # remove reference in viewWidgets or it would unsync tab and nodzInstances
        del self.layoutViewTabWidgets[tabIndex]
        self.editorTabWidget.removeTab(tabIndex)
        if self.editorTabWidget.count() == 0:
            self.editorTabWidget.hide()
            self.emptyTabWidget.show()

    def on_customContextMenuRequested(self):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            event.accept()
            return

        # prepare the menu action
        menu = QtWidgets.QMenu()
        renameAction = menu.addAction("Rename tab")
        action = menu.exec_(QtGui.QCursor().pos())
        if action == renameAction:
            renameDialog = SetDisplayNameDialog(self)
            renameDialog.displayName = self.getCurrentTabDisplayName()
            renameDialog.initUI()
            retValue = renameDialog.exec_()

            # set back new values...
            if retValue == 1:
                self.getCurrentTabWidget().displayName = renameDialog.displayName
                self.on_setModified()


    # Nodes
    def on_nodeCreated(self, nodeName):
        print(("node created : ", nodeName))

    def on_nodePreDeleted(self, deletedNodeNameList):
        # print('node deleted : ', nodeName)

        # if a deleted node was root, set previous one as root
        rootId = -1
        currentNodz = self.getCurrentNodz()
        if currentNodz is not None:
            rootId = currentNodz.scene().userData["rootTransformId"]
            for nodeName in deletedNodeNameList:
                if rootId == currentNodz.scene().nodes[nodeName].userData["ID"]:
                    foundANewRoot = None
                    previousNodes = list()
                    nextPreviousNodes = list()
                    previousNodes.append(currentNodz.scene().nodes[nodeName])

                    # find incoming connections node until we have a node not deleted, then set it as new root.
                    while foundANewRoot is None and len(previousNodes) > 0:
                        for previousNode in previousNodes:
                            if previousNode.name not in deletedNodeNameList:
                                foundANewRoot = previousNode
                                self.setRootNode(currentNodz, previousNode)
                                break
                            else:
                                # add node predecessors to nextPreviousNodes
                                if len(previousNode.sockets) > 0:
                                    for socketItem in previousNode.sockets.items():
                                        if len(socketItem[1].connected_slots) > 0:
                                            for otherPlugItem in socketItem[1].connected_slots:
                                                nextPreviousNodes.append(otherPlugItem.parentItem())

                        previousNodes = nextPreviousNodes
                        nextPreviousNodes = []
                    break

    def on_nodeDeleted(self, deletedNodeNameList):
        # print 'node deleted : ', nodeName
        self.signal_LayoutGraphChanged.emit(self, False)
        # manage group children here

    def on_nodeEdited(self, nodeName, newName):
        print("node edited : {0}, new name : {1}".format(nodeName, newName))

    def on_nodeSelected(self, nodesName):
        # print('node selected : ', nodesName)
        if not self.wrapper.statusBarHandledByWrapper():
            self.setStatusMessage(str(nodesName))
        # else wrapper will set status bar itself
        self.signal_NodeSelected.emit(self, nodesName)

        # # edit if not group
        # nodeType = None
        # if 'type_name' in nodeInst.userData:
        #     nodeType = nodeInst.userData['type_name']
        # else:
        #     nodeType = 'EntitySelector'

        # if (nodeType is None or nodeType != "Group"):
        currentNodz = self.getCurrentNodz()
        if len(nodesName) == 1:
            self.signal_LayoutNodePreEdited.emit(self, nodesName[0])
            self.setEditedNode(currentNodz, currentNodz.scene().nodes[nodesName[0]])
        else:
            self.setEditedNode(currentNodz, None)

    def on_nodeMoved(self, nodeName, nodePos):
        print("node {0} moved to {1}".format(nodeName, nodePos))

    def on_viewContextMenu(self, event):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            return

        # prepare the menu action
        menu = QtWidgets.QMenu()
        renameAction = menu.addAction("Rename tab")
        pasteAction = None
        if len(self.nodesToCopy) > 0:
            pasteAction = menu.addAction("Paste {}".format(str(self.nodesToCopy)))
        else:
            pasteAction = menu.addAction("Paste")
            pasteAction.setEnabled(False)
        action = menu.exec_(QtGui.QCursor().pos())
        if action == pasteAction:
            if self.nodesToCopyOriginNodz is not None and len(self.nodesToCopy):
                position = event.pos()
                positionF = currentNodz.mapToScene(position.x(), position.y())
                self.copySelectedNodesAt(self.nodesToCopy, self.nodesToCopyOriginNodz, positionF)
                self.stackUndo(self.getCurrentTabIndex())
        if action == renameAction:
            renameDialog = SetDisplayNameDialog(self)
            renameDialog.displayName = self.getCurrentTabDisplayName()
            renameDialog.initUI()
            retValue = renameDialog.exec_()

            # set back new values...
            if retValue == 1:
                self.getCurrentTabWidget().displayName = renameDialog.displayName
                self.on_setModified()

    def on_nodeContextMenu(self, event, nodeName):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            return

        # get current status
        nodeInst = currentNodz.scene().nodes[nodeName]
        nodeActive = nodeInst.userData["active"]

        isNote = False
        isGroup = False
        if "type" in nodeInst.userData:
            isNote = nodeInst.userData["type"] == GlmTransformType.Note  # Notes have no right click menu
            isGroup = nodeInst.userData["type"] == GlmTransformType.Group  # Group have rename option as context menu (double click opens the group)

        # prepare the menu action
        menu = QtWidgets.QMenu()
        setRootNodeAction = None
        enabelDisableAction = None
        if not isNote:
            if nodeInst is self.getRootNode(currentNodz):
                setRootNodeAction = menu.addAction("Unset Root [V]")
            else:
                setRootNodeAction = menu.addAction("Set as Root [V]")
            enabelDisableAction = None
            if nodeActive:
                enabelDisableAction = menu.addAction("Disable")
            else:
                enabelDisableAction = menu.addAction("Enable")
        # editAction = menu.addAction("Edit")
        copyAction = menu.addAction("Copy")
        groupAction = menu.addAction("Group")
        ungroupAction = None
        if isGroup:
            ungroupAction = menu.addAction("Ungroup")

        createRigOrPostureAction = False
        createBlindDataParametersAction = False
        exportTrajectoriesMeshAction = False
        exportSrcTrajectoriesAction = False
        exportDstTrajectoriesAction = False
        importSrcTrajectoriesAction = False
        importDstTrajectoriesAction = False
        createLocatorForKeyframedAttributes = False
        deleteLocatorForKeyframedAttributes = False
        if "type" in nodeInst.userData:
            if nodeInst.userData["type"] == GlmTransformType.Posture:  # Create Rig option
                menu.addSeparator()
                createRigOrPostureAction = menu.addAction("Create Posture Node")
            elif nodeInst.userData["type"] == GlmTransformType.Rig:  # Create Rig option
                menu.addSeparator()
                createRigOrPostureAction = menu.addAction("Create Rig Node")
            elif nodeInst.userData["type"] == GlmTransformType.BlindData:  # Create blind data attributes option
                menu.addSeparator()
                createBlindDataParametersAction = menu.addAction("Create Parameters for all Blind Data")
                createLocatorForKeyframedAttributes = menu.addAction("Create Locators For Keyframed Attributes")
                deleteLocatorForKeyframedAttributes = menu.addAction("Delete Locators For Keyframed Attributes")
            elif nodeInst.userData["type"] == GlmTransformType.EditTrajectory:  # Create EditTrajectory option
                menu.addSeparator()
                exportTrajectoriesMeshAction = menu.addAction("Export trajectories as source/destination mesh")
                exportSrcTrajectoriesAction = menu.addAction("Export source mesh")
                exportDstTrajectoriesAction = menu.addAction("Export destination mesh")
                importSrcTrajectoriesAction = menu.addAction("Import selection as source mesh/curve")
                importDstTrajectoriesAction = menu.addAction("Import selection as destination mesh/curve")
            else:
                if not isNote:
                    menu.addSeparator()
                    createLocatorForKeyframedAttributes = menu.addAction("Create Locators For Keyframed Attributes")
                    deleteLocatorForKeyframedAttributes = menu.addAction("Delete Locators For Keyframed Attributes")

        # fetch action
        action = menu.exec_(QtGui.QCursor().pos())
        if action is not None:  # protect against escaping when some nodes could be grouped / ungrouped but action is not in this node menu
            if action == setRootNodeAction:
                self.setRootNode(currentNodz, nodeInst, enableToggle=True)
                self.signal_LayoutRootChanged.emit(self, nodeInst.name)
            elif action == enabelDisableAction:
                # current node
                nodeInst.userData["active"] = not nodeActive
                self.createOrRefreshNodeAttributes(nodeInst)
                self.signal_LayoutNodeChanged.emit(self, nodeInst.name)
                # all selected nodes
                if currentNodz.selectedNodes is not None:
                    for selectedNode in currentNodz.selectedNodes:
                        nodeInst = currentNodz.scene().nodes[selectedNode]
                        nodeInst.userData["active"] = not nodeActive
                        self.createOrRefreshNodeAttributes(nodeInst)
                        self.signal_LayoutNodeChanged.emit(self, nodeInst.name)
            elif action == copyAction:
                self.nodesToCopy[:] = []
                self.nodesToCopyOriginNodz = currentNodz
                if currentNodz.selectedNodes is not None:
                    for selectedNode in currentNodz.selectedNodes:
                        self.nodesToCopy.append(selectedNode)
                    print("Copying {}".format(str(self.nodesToCopy)))
            elif action == groupAction:
                nodesToGroup = list()
                if currentNodz.selectedNodes is not None:
                    for selectedNode in currentNodz.selectedNodes:
                        nodesToGroup.append(selectedNode)
                if nodeInst.name not in currentNodz.selectedNodes:
                    nodesToGroup.append(nodeInst.name)

                self.on_groupSelectedNodes(nodesToGroup)  # preserve connections when grouping "in flow" nodes
            elif action == ungroupAction:
                nodesToUngroup = list()
                if currentNodz.selectedNodes is not None:
                    for selectedNode in currentNodz.selectedNodes:
                        nodesToUngroup.append(selectedNode)
                if nodeInst.name not in currentNodz.selectedNodes:
                    nodesToUngroup.append(nodeInst.name)
                self.on_ungroupSelectedNodes(nodesToUngroup)
            # elif action == editAction:
            #     self.on_nodeDoubleClick(nodeName, isGroup)
            elif action == createRigOrPostureAction:
                self.signal_RigOrPostureCreate.emit(self, nodeInst.userData["ID"])
            elif action == createBlindDataParametersAction:
                self.signal_blindDataParametersCreate.emit(self, nodeInst.userData["ID"])
            elif action == exportTrajectoriesMeshAction:
                self.signal_TrajectoriesMeshExport.emit(self, nodeInst.userData["ID"])
            elif action == exportSrcTrajectoriesAction:
                self.signal_TrajectoriesSrcExport.emit(self, nodeInst.userData["ID"])
            elif action == exportDstTrajectoriesAction:
                self.signal_TrajectoriesDstExport.emit(self, nodeInst.userData["ID"])
            elif action == importSrcTrajectoriesAction:
                self.signal_TrajectoriesSrcImport.emit(self, nodeInst.userData["ID"])
            elif action == importDstTrajectoriesAction:
                self.signal_TrajectoriesDstImport.emit(self, nodeInst.userData["ID"])
            elif action == createLocatorForKeyframedAttributes:
                self.signal_KeyframedLocatorsCreate.emit(self, nodeInst.userData["ID"])
            elif action == deleteLocatorForKeyframedAttributes:
                self.signal_KeyframedLocatorsDelete.emit(self, nodeInst.userData["ID"])

    def on_ungroupSelectedNodes(self, selectedNodes):
        currentNodz = self.getCurrentNodz()
        # selectedNodes = currentNodz.selectedNodes

        # if root is in selection, group becomes the root node of the current Nodz
        if selectedNodes is not None and len(selectedNodes) > 0:

            self.startCompoundInteraction(currentNodz)

            # nodePrePosList = list()
            # nodePostPosList = list()

            # # Mean selected nodes pos to create new group
            # currentNodzRootId = currentNodz.scene().userData['rootTransformId']
            for selectedNode in selectedNodes:
                selectedNodeInst = currentNodz.scene().nodes[selectedNode]

                isGroup = selectedNodeInst.userData["type"] == GlmTransformType.Group
                if isGroup:
                    # ungroup all child nodz, the current group node becomes the anchor position
                    if "ID" in selectedNodeInst.userData:
                        groupId = selectedNodeInst.userData["ID"]

                        # get the current groupStorage
                        layoutTabWidget = self.layoutViewTabWidgets[self.getCurrentTabIndex()]

                        # get the Nodz from the group storage
                        if layoutTabWidget is not None and groupId in layoutTabWidget.childrenNodz:

                            childGroupNodz = layoutTabWidget.childrenNodz[groupId]

                            groupInputPlugNodeInsts = list()
                            groupOutputSocketNodeInsts = list()

                            # get connections,
                            if len(selectedNodeInst.sockets) > 0:
                                for socketItem in selectedNodeInst.sockets.items():
                                    if len(socketItem[1].connected_slots) > 0:
                                        for otherPlugItem in socketItem[1].connected_slots:
                                            otherNodeInst = otherPlugItem.parentItem()
                                            groupInputPlugNodeInsts.append(otherNodeInst)

                            if len(selectedNodeInst.plugs) > 0:
                                for plugItem in selectedNodeInst.plugs.items():
                                    if len(plugItem[1].connected_slots) > 0:
                                        for otherSocketItem in plugItem[1].connected_slots:
                                            otherNodeInst = otherSocketItem.parentItem()
                                            groupOutputSocketNodeInsts.append(otherNodeInst)

                            groupNodePos = selectedNodeInst.pos() + selectedNodeInst.nodeCenter

                            # save root name before copy / move
                            childGroupRootNodeName = ""
                            childGroupRootNodeInst = self.getRootNode(childGroupNodz)
                            if childGroupRootNodeName is not None:
                                childGroupRootNodeName = childGroupRootNodeInst.name

                            inputLessGroupChildrenNodes = list()
                            for groupNode in childGroupNodz.scene().nodes:
                                childGroupNodeInst = childGroupNodz.scene().nodes[groupNode]

                                hasInputs = False
                                if len(childGroupNodeInst.sockets) > 0:
                                    for socketItem in childGroupNodeInst.sockets.items():
                                        if len(socketItem[1].connected_slots) > 0:
                                            for otherPlugItem in socketItem[1].connected_slots:
                                                hasInputs = True

                                if not hasInputs:
                                    if ("type" not in childGroupNodeInst.userData) or (childGroupNodeInst.userData["type"] != GlmTransformType.Note):
                                        inputLessGroupChildrenNodes.append(childGroupNodeInst.name)

                            copyRootNode = False
                            moveMode = True
                            self.copySelectedNodesAt(
                                list(childGroupNodz.scene().nodes.keys()),
                                childGroupNodz,
                                groupNodePos,
                                currentNodz,
                                moveMode,
                                copyRootNode,
                            )  # will copy root only if not already set

                            # makes connections : must add group input connection(s) to all group children nodes "input less"
                            for inputLessGroupChildNodeName in inputLessGroupChildrenNodes:
                                for groupInputPlugNodeInst in groupInputPlugNodeInsts:
                                    currentNodz.createConnection(
                                        groupInputPlugNodeInst.name,
                                        groupInputPlugNodeInst.attrs[0],
                                        inputLessGroupChildNodeName,
                                        currentNodz.scene().nodes[inputLessGroupChildNodeName].attrs[0],
                                    )

                            # makes connections : must connect group root to groupNode output
                            if childGroupRootNodeName is not None:
                                ungroupedFinalNodeInst = currentNodz.scene().nodes[childGroupRootNodeName]

                                # create connections from former group root node to groupOutputSocketNode/Attr
                                for groupOutputSocketNodeInst in groupOutputSocketNodeInsts:
                                    currentNodz.createConnection(
                                        ungroupedFinalNodeInst.name,
                                        ungroupedFinalNodeInst.attrs[0],
                                        groupOutputSocketNodeInst.name,
                                        groupOutputSocketNodeInst.attrs[0],
                                    )

                            # former group root becomes root if the group was root of its own nodz
                            if self.getRootNode(currentNodz) == selectedNodeInst and childGroupRootNodeName != "":
                                self.setRootNode(currentNodz, currentNodz.scene().nodes[childGroupRootNodeName])

                            # Finally delete group node
                            selectedNodeInst._remove()

            self.stackUndo(self.getCurrentTabIndex())

            # self.signal_LayoutGraphChanged.emit(self, True)
            self.signal_LayoutGraphChanged.emit(self, False)  # we don't need to recomputeAssets when grouping, do we ?

            self.endCompoundInteraction(currentNodz, True)

            # self.refreshGroupNodeUserData(currentNodz, thisGroupStorage, groupNode)

    def isInRootFlow(self, aNodeInst, aNodz):
        rootNodeInst = self.getRootNode(aNodz)
        if aNodeInst is rootNodeInst:
            return True

        parsedNodes = list()
        nodesInstToProcess = list()
        nextNodesInstToProcess = list()

        nodesInstToProcess.append(aNodeInst)

        while len(nodesInstToProcess) > 0:
            del nextNodesInstToProcess[:]  # or nextNodesInstToProcess = list()
            # for all next nodes, if root : True, else continue stacking nodes
            for nodeInstToProcess in nodesInstToProcess:
                if nodeInstToProcess not in parsedNodes:
                    parsedNodes.append(nodeInstToProcess)

                    if len(nodeInstToProcess.plugs) > 0:
                        for plugItem in nodeInstToProcess.plugs.items():
                            if len(plugItem[1].connected_slots) > 0:
                                for otherSocketItem in plugItem[1].connected_slots:
                                    if otherSocketItem.parentItem() is rootNodeInst:
                                        return True
                                    else:
                                        nextNodesInstToProcess.append(otherSocketItem.parentItem())

            nodesInstToProcess = nextNodesInstToProcess[:]

        return False

    def on_groupSelectedNodes(self, selectedNodes, destinationGroupNodz=None):
        #  destinationGroupNodz is meant to be used for drag n drop node on groups, but this requires modifying Nodz deeply to make nodes conditionnaly accept drag and emit signals
        currentNodz = self.getCurrentNodz()
        # selectedNodes = currentNodz.selectedNodes

        # if root is in selection, group becomes the root node of the current Nodz
        rootInSelection = False
        if selectedNodes is not None and len(selectedNodes) > 0:

            self.startCompoundInteraction(currentNodz)

            # Mean selected nodes pos to create new group
            currentNodzRootId = currentNodz.scene().userData["rootTransformId"]
            posX = 0
            posY = 0
            for selectedNode in selectedNodes:
                selectedNodeInst = currentNodz.scene().nodes[selectedNode]

                posX += selectedNodeInst.pos().x() + selectedNodeInst.nodeCenter.x()
                posY += selectedNodeInst.pos().y() + selectedNodeInst.nodeCenter.y()
                rootInSelection = rootInSelection or selectedNodeInst.userData["ID"] == currentNodzRootId

            posX /= len(selectedNodes)
            posY /= len(selectedNodes)
            nodePos = QtCore.QPointF(posX, posY)

            # # get the main parent Nodz
            # mainNodz = currentNodz
            # if currentNodz.scene().userData is not None and 'mainNodz' in currentNodz.scene().userData:
            #     mainNodz = currentNodz.scene().userData['mainNodz']

            # create a child group / Nodz in this Nodz
            # keep same Id as we will delete the nodes in this nodz
            if destinationGroupNodz is None:
                # groupNodeId = mainNodz.scene().userData['nextNodeId']
                # mainNodz.scene().userData['nextNodeId'] += 1
                groupNode = self.GolaemLayoutNodeCreator(currentNodz, "Group", nodePos)
                groupNodeId = groupNode.userData["ID"]

                thisTabWidget = self.layoutViewTabWidgets[self.getCurrentTabIndex()]
                groupNodz = thisTabWidget.childrenNodz[groupNodeId]
            else:
                groupNodeId = destinationGroupNodz.scene().userData["groupId"]
                groupNode = destinationGroupNodz.scene().userData["groupNode"]
                groupNodz = destinationGroupNodz

            # connect group to input output if only one input and one output
            groupSrcNodeNames = list()
            groupDestNodeNames = list()
            groupRootNodeNames = list()

            # candidates to "first" node giving their socket to the group, must have non 0, only "outside selection" previous connections
            # candidates to "last" node giving their sockets to the group and becomre root, must have only "outside selection" next connections (can be 0)
            # if there is more than one candidate, can't apply automatic plugging
            if destinationGroupNodz is None:  # do not forward connection if grouping via drop / "out of flow"
                for selectedNode in selectedNodes:
                    selectedNodeInst = currentNodz.scene().nodes[selectedNode]

                    # skip notes type (no connections could be considered as root)
                    if "type" in selectedNodeInst.userData and selectedNodeInst.userData["type"] == GlmTransformType.Note:
                        continue

                    # get connections,
                    if len(selectedNodeInst.sockets) > 0:
                        for socketItem in selectedNodeInst.sockets.items():
                            if len(socketItem[1].connected_slots) > 0:
                                for otherPlugItem in socketItem[1].connected_slots:
                                    if not (
                                        otherPlugItem.parentItem().name in selectedNodes
                                    ):  # a connection to this node from not inside the selection : we need to replug it to the group
                                        groupSrcNodeNames.append(otherPlugItem.parentItem().name)

                    if len(selectedNodeInst.plugs) > 0:
                        for plugItem in selectedNodeInst.plugs.items():
                            if len(plugItem[1].connected_slots) > 0:
                                for otherSocketItem in plugItem[1].connected_slots:
                                    if not (otherSocketItem.parentItem().name in selectedNodes):
                                        groupDestNodeNames.append(otherSocketItem.parentItem().name)
                                        if self.isInRootFlow(otherSocketItem.parentItem(), currentNodz):
                                            groupRootNodeNames.append(selectedNode)

                for groupSrcNodeName in groupSrcNodeNames:
                    previousNodeInst = currentNodz.scene().nodes[groupSrcNodeName]
                    currentNodz.createConnection(previousNodeInst.name, previousNodeInst.attrs[0], groupNode.name, groupNode.attrs[0])

                # if (outputCandidateCount == 1 and groupDestNodeName != ''):
                for groupDestNodeName in groupDestNodeNames:
                    nextNodeInst = currentNodz.scene().nodes[groupDestNodeName]
                    currentNodz.createConnection(groupNode.name, groupNode.attrs[0], nextNodeInst.name, nextNodeInst.attrs[0])

            copyRootNode = True
            moveMode = True
            self.copySelectedNodesAt(selectedNodes, currentNodz, nodePos, groupNodz, moveMode, copyRootNode)  # will copy root only if not already set

            if len(groupRootNodeNames) == 1:
                # if (outputCandidateCount == 1):
                # set root id in child group Nodz
                if groupRootNodeNames[0] in groupNodz.scene().nodes:
                    groupRootNodeInstance = groupNodz.scene().nodes[groupRootNodeNames[0]]
                    self.setRootNode(groupNodz, groupRootNodeInstance)
                    self.createOrRefreshNodeAttributes(groupRootNodeInstance, groupNodz)
            elif len(groupRootNodeNames) > 1:
                # add a merge node to connect all nodes active in group and connected to external nodes
                posX = 0
                posY = 0
                for groupRootNodeName in groupRootNodeNames:
                    groupRootNodeInst = groupNodz.scene().nodes[groupRootNodeName]
                    posX += groupRootNodeInst.pos().x()
                    posY += groupRootNodeInst.pos().y()
                posX /= len(groupRootNodeNames)
                posY /= len(groupRootNodeNames)
                groupMergeNode = self.GolaemLayoutNodeCreator(groupNodz, "Merge", QtCore.QPointF(posX + 200, posY))
                groupMergeNode.setPos(groupMergeNode.pos() + groupMergeNode.nodeCenter)  # add the node center as we are relying on top left corner a
                for groupRootNodeName in groupRootNodeNames:
                    groupRootNodeInst = groupNodz.scene().nodes[groupRootNodeName]
                    groupNodz.createConnection(groupRootNodeInst.name, groupRootNodeInst.attrs[0], groupMergeNode.name, groupMergeNode.attrs[0])
                self.setRootNode(groupNodz, groupMergeNode)
                self.createOrRefreshNodeAttributes(groupMergeNode, groupNodz)

            # if destination is None, we group "in flow" : if one of gruoped nodes were root, the group become root
            if destinationGroupNodz is None:
                if rootInSelection and destinationGroupNodz is None:
                    self.setRootNode(currentNodz, groupNode)
                    self.createOrRefreshNodeAttributes(groupNode, currentNodz)
            # if we move nodes to a group by drag n drop, set the group as root only if no other node has taken this job after the move
            # "disconnect forward root back" rule prevail
            else:
                if self.getRootNode(currentNodz) is None:
                    self.setRootNode(currentNodz, groupNode)

            self.stackUndo(self.getCurrentTabIndex())

            # self.signal_LayoutGraphChanged.emit(self, True)
            self.signal_LayoutGraphChanged.emit(self, False)  # we don't need to recomputeAssets when grouping, do we ?

            self.endCompoundInteraction(currentNodz, True)

    def setEditedNodz(self, editedNodz):
        # create the tab
        tabIndex = self.getCurrentTabIndex()
        currentViewWidget = self.layoutViewTabWidgets[tabIndex]
        if currentViewWidget.editedNodz != editedNodz:
            if currentViewWidget.editedNodz is not None:
                currentViewWidget.editedNodz.setVisible(False)
                currentViewWidget.layout().removeWidget(currentViewWidget.editedNodz)
            
            # forward pressed keys to new nodz
            editedNodz.pressedKeys = currentViewWidget.editedNodz.pressedKeys
            currentViewWidget.editedNodz.pressedKeys = []
            currentViewWidget.editedNodz = editedNodz
            tabName = ""
            if "groupNode" in editedNodz.scene().userData:
                groupNode = editedNodz.scene().userData["groupNode"]
                tabName = "{} (ID:{})".format(groupNode.userData["name"], groupNode.userData["ID"])
            else:
                tabName = self.layoutViewTabWidgets[tabIndex].layoutName

            self.editorTabWidget.setTabText(tabIndex, tabName)
            currentViewWidget.editedNodz.setVisible(True)
            currentViewWidget.layout().addWidget(currentViewWidget.editedNodz)
            currentViewWidget.editedNodz.setFocus()

        self.layoutViewTabWidgets[tabIndex].updateBreadcrumb()

    def getEditedNode(self):
        if self.layoutActiveAttributeEditorWidget is not None:
            return self.layoutActiveAttributeEditorWidget.node
        return None

    def setEditedNode(self, currentNodz, nodeInst):
        if self.layoutActiveAttributeEditorWidget is not None:
            self.layoutAttributeEditorDockMainWidget.layout().removeWidget(self.layoutActiveAttributeEditorWidget)
            self.layoutActiveAttributeEditorWidget.deleteLater()
            self.layoutActiveAttributeEditorWidget = None
        if nodeInst is not None:
            self.layoutEmptyAttributeEditorWidget.hide()
            self.layoutActiveAttributeEditorWidget = layoutAttributeEditor.LayoutAttributeEditor(
                currentNodz, self, nodeInst, currentNodz.editEnabled
            )  # parent currentNodz
            self.layoutActiveAttributeEditorWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.layoutAttributeEditorDockMainWidget.layout().addWidget(self.layoutActiveAttributeEditorWidget)
            self.layoutAttributeEditorDockWidget.setWindowTitle(self.layoutActiveAttributeEditorWidget.windowsTitle)
        else:
            self.layoutEmptyAttributeEditorWidget.show()
            self.layoutAttributeEditorDockWidget.setWindowTitle("Attribute Editor")

    def on_sceneDoubleClick(self):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            return

        if QtCore.Qt.Key_Control in currentNodz.pressedKeys:
            # go up one level of group
            if "parentNodz" in currentNodz.scene().userData:
                parentNodz = currentNodz.scene().userData["parentNodz"]
                if parentNodz is not None:
                    self.setEditedNodz(parentNodz)

    def on_nodeDoubleClick(self, nodeName, forceEdit=False):
        currentNodz = self.getCurrentNodz()
        if currentNodz is None:
            print("Error: no tab selected")
            return

        # print('double click on node {0}'.format(nodeName))
        nodeInst = currentNodz.scene().nodes[nodeName]

        nodeTypeIndex = None
        if "type" in nodeInst.userData:
            nodeTypeIndex = nodeInst.userData["type"]

        # group
        if nodeTypeIndex is not None and nodeTypeIndex == layoutAttributeEditor.GlmTransformType.Group and not forceEdit:
            if "ID" in nodeInst.userData:
                groupId = nodeInst.userData["ID"]

                # # get the main parent Nodz
                # mainNodz = currentNodz
                # if currentNodz.scene().userData is not None and 'mainNodz' in currentNodz.scene().userData:
                #     mainNodz = currentNodz.scene().userData['mainNodz']

                # get the current groupStorage
                layoutTabWidget = self.layoutViewTabWidgets[self.getCurrentTabIndex()]

                # get the Nodz from the group storage
                if layoutTabWidget is not None and groupId in layoutTabWidget.childrenNodz:
                    self.setEditedNodz(layoutTabWidget.childrenNodz[groupId])
                    # self.resetUndoStack()

    # Attrs
    def on_attrCreated(self, nodeName, attrId):
        print("attr created : {0} at index : {1}".format(nodeName, attrId))

    def on_attrDeleted(self, nodeName, attrId):
        print("attr Deleted : {0} at old index : {1}".format(nodeName, attrId))

    def on_attrEdited(self, nodeName, oldId, newId):
        print("attr Edited : {0} at old index : {1}, new index : {2}".format(nodeName, oldId, newId))

    # Connections
    def on_connected(self, srcNodeName, srcPlugName, destNodeName, dstSocketName):
        # print('connected src: "{0}" at "{1}" to dst: "{2}" at "{3}"'.format(srcNodeName, srcPlugName, destNodeName, dstSocketName))

        # find nodz for node named srcNodeName
        editedNodz = self.sender()
        # editedNodz = self.getNodzForNode()

        if not self.blockRootForward:
            rootID = editedNodz.scene().userData["rootTransformId"]
            if editedNodz.scene().nodes[srcNodeName].userData["ID"] == rootID:
                self.setRootNode(editedNodz, editedNodz.scene().nodes[destNodeName])
                # editedNodz.scene().userData['rootTransformId'] = editedNodz.scene().nodes[destNodeName].userData['ID']
                # self.createOrRefreshNodeAttributes(editedNodz.scene().nodes[srcNodeName])
                # self.createOrRefreshNodeAttributes(editedNodz.scene().nodes[destNodeName])

        self.signal_LayoutNodeChanged.emit(self, destNodeName)

    def on_disconnected(self, srcNodeName, srcPlugName, destNodeName, dstSocketName):
        # print('disconnected src: "{0}" at "{1}" from dst: "{2}" at "{3}"'.format(srcNodeName, srcPlugName, destNodeName, dstSocketName))
        self.signal_LayoutNodeChanged.emit(self, destNodeName)


######################################################################
# LayoutEditorConfiguration
######################################################################
class LayoutEditorConfiguration(QtWidgets.QDialog):

    # ------------------------------------------------------------------
    def __init__(self, parentWidget):
        super(LayoutEditorConfiguration, self).__init__(parentWidget)
        self.setModal(True)
        # parameters
        self.maxTablesDisplayCount = 50

    # ------------------------------------------------------------------
    def initUI(self):
        # layout
        self.contentLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.contentLayout)

        # Draw frequency
        self.maxTablesDisplayCountLayout = QtWidgets.QHBoxLayout()
        self.contentLayout.addLayout(self.maxTablesDisplayCountLayout)

        self.maxTablesDisplayCountLayout.addWidget(QtWidgets.QLabel("Max values to display in tables", self))

        maxTablesDisplayCountSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        maxTablesDisplayCountSlider.setMaximumWidth(200)
        maxTablesDisplayCountSlider.setRange(1, 200)
        maxTablesDisplayCountSlider.setValue(self.maxTablesDisplayCount)
        maxTablesDisplayCountSlider.valueChanged.connect(self.onMaxTablesDisplayCountChanged)
        self.maxTablesDisplayCountLayout.addWidget(maxTablesDisplayCountSlider)

        self.maxTablesDisplayCountLineEdit = QtWidgets.QLineEdit("{}".format(self.maxTablesDisplayCount), self)
        self.maxTablesDisplayCountLineEdit.setReadOnly(True)
        self.maxTablesDisplayCountLineEdit.setMaximumWidth(40)
        self.maxTablesDisplayCountLayout.addWidget(self.maxTablesDisplayCountLineEdit)

        self.maxTablesDisplayCountLayout.addStretch()

        # stretch between main UI and ok/cancel
        self.contentLayout.addStretch()

        # OK and Cancel buttons
        self.okCancelButtonsLayout = QtWidgets.QHBoxLayout()
        self.contentLayout.addLayout(self.okCancelButtonsLayout)

        self.okCancelButtonsLayout.addStretch()

        cancelButton = QtWidgets.QPushButton(self)
        cancelButton.setText("Cancel")
        cancelButton.released.connect(self.reject)
        self.okCancelButtonsLayout.addWidget(cancelButton)

        okButton = QtWidgets.QPushButton(self)
        okButton.setText("OK")
        okButton.released.connect(self.accept)
        self.okCancelButtonsLayout.addWidget(okButton)

    # ------------------------------------------------------------------
    def onMaxTablesDisplayCountChanged(self, value):
        self.maxTablesDisplayCount = value
        self.maxTablesDisplayCountLineEdit.setText("{}".format(self.maxTablesDisplayCount))


######################################################################
# SetDisplayNameDialog
######################################################################
class SetDisplayNameDialog(QtWidgets.QDialog):

    # ------------------------------------------------------------------
    def __init__(self, parentWidget):
        super(SetDisplayNameDialog, self).__init__(parentWidget)
        self.setModal(True)
        # parameters
        self.displayName = ""

    # ------------------------------------------------------------------
    def initUI(self):
        # layout
        self.contentLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.contentLayout)

        # Draw frequency
        self.displayNameLayout = QtWidgets.QHBoxLayout()
        self.contentLayout.addLayout(self.displayNameLayout)

        self.displayNameLineEdit = QtWidgets.QLineEdit("{}".format(self.displayName), self)
        self.displayNameLineEdit.setReadOnly(False)
        self.displayNameLineEdit.textChanged.connect(self.onDisplayNameChanged)
        self.displayNameLayout.addWidget(self.displayNameLineEdit)

        # stretch between main UI and ok/cancel
        self.contentLayout.addStretch()

        # OK and Cancel buttons
        self.okCancelButtonsLayout = QtWidgets.QHBoxLayout()
        self.contentLayout.addLayout(self.okCancelButtonsLayout)

        self.okCancelButtonsLayout.addStretch()

        okButton = QtWidgets.QPushButton(self)
        okButton.setText("OK")
        okButton.released.connect(self.accept)
        self.okCancelButtonsLayout.addWidget(okButton)

        cancelButton = QtWidgets.QPushButton(self)
        cancelButton.setText("Cancel")
        cancelButton.released.connect(self.reject)
        self.okCancelButtonsLayout.addWidget(cancelButton)

    # ------------------------------------------------------------------
    def onDisplayNameChanged(self, value):
        self.displayName = value



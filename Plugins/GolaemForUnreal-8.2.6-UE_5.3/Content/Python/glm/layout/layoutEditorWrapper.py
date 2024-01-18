from __future__ import print_function
from __future__ import absolute_import
#**************************************************************************
#*                                                                        *
#*  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
#*                                                                        *
#**************************************************************************

from builtins import str
from builtins import range
import os
import json
import ast
# import ntpath

from glm.Qtpy.Qt import QtCore, QtWidgets
from glm.layout import layoutEditorUtils as layoutUtils
import glm.layout.layoutAttributeEditor as layoutAttributeEditor
usingMaya = True
try:
    import maya.cmds as cmds
    import maya.mel as mel
    import maya.OpenMaya as om
    cmds.about(version=True)  # call an actual command to filter call from mayapy
    import glm.mayaUtils as mutils
    import glm.crowdUtils as cutils
except:
    usingMaya = False

usingUnreal = True
try:
    import unreal
except:
    usingUnreal = False    

######################################################################
# Wrapper Singleton
######################################################################

def getTheLayoutEditorWrapperInstance(createIfNone=True, delete=False):
    """
    Returns the instance singleton
    """
    global layoutEditorWrapperInstance
    try:
        layoutEditorWrapperInstance
        if delete:
            if(layoutEditorWrapperInstance is not None):
                layoutEditorWrapperInstance.__del__()
                del layoutEditorWrapperInstance
            else:
                print("layoutEditorWrapperInstance is None")
            return None
    except NameError:
        if delete:
            print("layoutEditorWrapperInstance is already destroyed")
            return None
        else:
            if(createIfNone):
                layoutEditorWrapperInstance = LayoutEditorWrapper()
            else:
                return None
    return layoutEditorWrapperInstance

######################################################################
# Wrapper
######################################################################

class LayoutEditorWrapper(QtCore.QObject):
    """
    The Golaem Layout Editor that allows to edit a golaem simulation cache Layout (*.gscl)
    """
    layoutEditor = None
    blockSignalsToLayoutEditor = False
    blockSignalsFromLayoutEditor = False
    blockUpdateTrajectoryField = False
    blockUpdatePaintedZone = False
    blockJSonUpload = False

    def __init__(self):
        super(LayoutEditorWrapper, self).__init__()
        self._iconsDir = ""
        # set default icons dir
        if(usingMaya):
            self._iconsDir = os.path.join(cutils.getGolaemIconsDir(), 'layoutToolv7')
        elif (usingUnreal):
            thisDirectory = os.path.dirname(os.path.realpath(__file__))
            self._iconsDir = os.path.join(thisDirectory, os.pardir, os.pardir, os.pardir, os.pardir, "Resources", "icons", "layoutToolv7").replace('\\', '/')
        else:
            thisDirectory = os.path.dirname(os.path.realpath(__file__))
            self._iconsDir = os.path.join(thisDirectory, os.pardir, os.pardir, os.pardir, "icons", "layoutToolv7").replace('\\', '/')

        self.compoundDirtyAssetRepartition = False
        self.compountDirtyLayoutNodeIDs = list()

        self.cacheProxyPoptoolsChanged = 0
        self.cacheProxyVectorFieldsChanged=0
        self.cacheProxyPaintedZonesChanged = 0

    ###################################################################
    ###################### LAYOUT EDITOR TO MAYA ######################
    ###################################################################

    def setLayoutEditor(self, layoutEditorInstance):
        if self.layoutEditor != layoutEditorInstance:
            if self.layoutEditor is not None:
                #make sure signals don't stay connected with another layout editor...
                self.layoutEditor.signal_NodeSelected.disconnect(self.on_nodeSelected)
                self.layoutEditor.signal_LayoutGraphChanged.disconnect(self.on_layoutGraphChanged)
                self.layoutEditor.signal_LayoutNodeChanged.disconnect(self.on_layoutNodeChanged)
                self.layoutEditor.signal_LayoutParameterChanged.disconnect(self.on_layoutParameterChanged)
                self.layoutEditor.signal_LayoutRootChanged.disconnect(self.on_layoutRootChanged)
                self.layoutEditor.signal_RigOrPostureCreate.disconnect(self.on_rigOrPostureCreate)
                self.layoutEditor.signal_blindDataParametersCreate.disconnect(self.on_blindDataParametersCreate)
                self.layoutEditor.signal_TrajectoriesMeshExport.disconnect(self.on_trajectoriesMeshExport)
                self.layoutEditor.signal_TrajectoriesSrcExport.disconnect(self.on_trajectoriesSrcExport)
                self.layoutEditor.signal_TrajectoriesDstExport.disconnect(self.on_trajectoriesDstExport)
                self.layoutEditor.signal_TrajectoriesSrcImport.disconnect(self.on_trajectoriesSrcImport)
                self.layoutEditor.signal_TrajectoriesDstImport.disconnect(self.on_trajectoriesDstImport)
                self.layoutEditor.signal_KeyframedLocatorsCreate.disconnect(self.on_keyframedLocatorsCreate)
                self.layoutEditor.signal_KeyframedLocatorsDelete.disconnect(self.on_keyframedLocatorsDelete)
                self.layoutEditor.signal_LayoutNodePreEdited.disconnect(self.on_layoutNodePreEdited)
                self.layoutEditor.signal_LayoutNodeCreated.disconnect(self.on_layoutNodeCreated)
                self.layoutEditor.signal_LayoutGraphLoaded.disconnect(self.on_layoutGraphSetFilePath)
                self.layoutEditor.signal_LayoutGraphSaved.disconnect(self.on_layoutGraphSetFilePath)
                self.layoutEditor.signal_LayoutSnapToPoptoolDropDownChanged.disconnect(self.on_layoutSnapToPoptoolComboBoxEdited)
                self.layoutEditor.signal_LayoutSnapToSlotsUpdate.disconnect(self.on_layoutSnapToSlotsUpdate)
                self.layoutEditor.signal_LayoutVectorFieldDropDownChanged.disconnect(self.on_layoutVectorFieldComboBoxEdited)
                self.layoutEditor.signal_LayoutVectorFieldUpdate.disconnect(self.on_layoutVectorFieldUpdate)
                self.layoutEditor.signal_LayoutPaintedZoneDropDownChanged.disconnect(self.on_layoutPaintedZoneComboBoxEdited)
                self.layoutEditor.signal_LayoutPaintedZoneUpdate.disconnect(self.on_layoutPaintedZoneUpdate)
                self.layoutEditor.signal_LayoutEditTrajectoryMeshUpdate.disconnect(self.on_layoutEditTrajectoryMeshUpdate)
                self.layoutEditor.signal_LayoutCacheSizeChanged.disconnect(self.on_layoutCacheSizeChanged)
                self.layoutEditor.signal_LayoutEndCompoundInteraction.disconnect(self.on_endCompoundInteraction)

            self.layoutEditor = layoutEditorInstance

            self.layoutEditor.poptools = list() #self.getPopulationToolList()
            self.layoutEditor.entityTypes = list() #self.getEntityTypeList()
            self.layoutEditor.entityTypeIds = list() #self.getEntityTypeList()
            self.layoutEditor.renderingTypes = list() #self.getRenderingTypeList()
            self.layoutEditor.selectedCharacterMeshAssets = list() # self.getSelectedCharacterMeshAssetList()
            self.layoutEditor.selectedEntityMeshAssets = list() #self.getSelectedEntityMeshAssetList()
            self.layoutEditor.vectorFields = list()  #self.getPopulationToolList()
            self.layoutEditor.paintedZones = list() #self.getPopulationToolList()
            

            #connect the layout editor signals
            self.layoutEditor.signal_NodeSelected.connect(self.on_nodeSelected)
            self.layoutEditor.signal_LayoutGraphChanged.connect(self.on_layoutGraphChanged)
            self.layoutEditor.signal_LayoutNodeChanged.connect(self.on_layoutNodeChanged)
            self.layoutEditor.signal_LayoutEndCompoundInteraction.connect(self.on_endCompoundInteraction)
            self.layoutEditor.signal_LayoutParameterChanged.connect(self.on_layoutParameterChanged)
            self.layoutEditor.signal_LayoutRootChanged.connect(self.on_layoutRootChanged)
            self.layoutEditor.signal_RigOrPostureCreate.connect(self.on_rigOrPostureCreate)
            self.layoutEditor.signal_blindDataParametersCreate.connect(self.on_blindDataParametersCreate)
            self.layoutEditor.signal_TrajectoriesMeshExport.connect(self.on_trajectoriesMeshExport)
            self.layoutEditor.signal_TrajectoriesSrcExport.connect(self.on_trajectoriesSrcExport)
            self.layoutEditor.signal_TrajectoriesDstExport.connect(self.on_trajectoriesDstExport)
            self.layoutEditor.signal_TrajectoriesSrcImport.connect(self.on_trajectoriesSrcImport)
            self.layoutEditor.signal_TrajectoriesDstImport.connect(self.on_trajectoriesDstImport)
            self.layoutEditor.signal_KeyframedLocatorsCreate.connect(self.on_keyframedLocatorsCreate)
            self.layoutEditor.signal_KeyframedLocatorsDelete.connect(self.on_keyframedLocatorsDelete)
            self.layoutEditor.signal_LayoutNodePreEdited.connect(self.on_layoutNodePreEdited)
            self.layoutEditor.signal_LayoutNodeCreated.connect(self.on_layoutNodeCreated)
            self.layoutEditor.signal_LayoutGraphLoaded.connect(self.on_layoutGraphSetFilePath)
            self.layoutEditor.signal_LayoutGraphSaved.connect(self.on_layoutGraphSetFilePath)
            self.layoutEditor.signal_LayoutSnapToPoptoolDropDownChanged.connect(self.on_layoutSnapToPoptoolComboBoxEdited)
            self.layoutEditor.signal_LayoutSnapToSlotsUpdate.connect(self.on_layoutSnapToSlotsUpdate)
            self.layoutEditor.signal_LayoutVectorFieldDropDownChanged.connect(self.on_layoutVectorFieldComboBoxEdited)
            self.layoutEditor.signal_LayoutVectorFieldUpdate.connect(self.on_layoutVectorFieldUpdate)
            self.layoutEditor.signal_LayoutPaintedZoneDropDownChanged.connect(self.on_layoutPaintedZoneComboBoxEdited)
            self.layoutEditor.signal_LayoutPaintedZoneUpdate.connect(self.on_layoutPaintedZoneUpdate)
            self.layoutEditor.signal_LayoutEditTrajectoryMeshUpdate.connect(self.on_layoutEditTrajectoryMeshUpdate)
            self.layoutEditor.signal_LayoutCacheSizeChanged.connect(self.on_layoutCacheSizeChanged)

            self.compoundDirtyAssetRepartition = False
            self.compoundDirtyLayoutNodeIDs = list()

            self.cacheProxyPoptoolsChanged = 0
            self.cacheProxyVectorFieldsChanged = 0
            self.cacheProxyPaintedZonesChanged = 0

    def selectEntityListFromString(self, entityListString):
        if not self.blockSignalsFromLayoutEditor:
            if self.layoutEditor is None:
                return

            currentTabName = self.layoutEditor.getLayoutNameForCurrentTab()
            if len(currentTabName)==0:
                return

            #self.blockSignalsFromLayoutEditor = True

            if(usingMaya):
                cmds.glmLayoutTool(cacheProxy=currentTabName, selectEntities=entityListString)
            # else:
            # nothing

            #self.blockSignalsFromLayoutEditor = False
            return self.layoutEditor.poptools

    def openEntityInspector(self):
        if(usingMaya):
            mel.eval('glmEntityInspectorCmd();')
        else:
            print('Open the Entity Inspector is not available outside of Maya yet')

    def getPopulationToolList(self):
        if(usingMaya):
            self.layoutEditor.poptools = [u"Manual Entry"]
            populationTools = mutils.getObjectsOfType("PopulationToolLocator")
            if populationTools is not None:
                for populationTool in populationTools:
                    self.layoutEditor.poptools.append(populationTool)
        else:
            self.layoutEditor.poptools = [u"Manual Entry"]
            # self.layoutEditor.poptools.append(u"FakePopTool") #for testing purpose

        return self.layoutEditor.poptools

    def getEntityTypeList(self):
        if self.layoutEditor is None:
            return

        if(usingMaya):
            self.layoutEditor.entityTypes = [u"All"]
            self.layoutEditor.entityTypeIds = [-1]
            entityTypes = mutils.getObjectsOfType("CrowdEntityTypeNode")
            for entityType in entityTypes:
                self.layoutEditor.entityTypes.append(entityType)
                self.layoutEditor.entityTypeIds.append(cmds.getAttr('{}.entityTypeId'.format(entityType)))
        else:
            self.layoutEditor.entityTypes = [u"All"]
            # self.layoutEditor.entityTypes.append(u"FakeEntityType1") #for testing purpose
            # self.layoutEditor.entityTypes.append(u"FakeEntityType2") #for testing purpose

            self.layoutEditor.entityTypeIds = [-1]
            # self.layoutEditor.entityTypeIds.append(1)
            # self.layoutEditor.entityTypeIds.append(2)

    def createRigOrPostureNode(self, nodeId):
        if self.layoutEditor is None or self.blockSignalsFromLayoutEditor:
            return
        currentTabName = self.layoutEditor.getCurrentTabName()
        if len(currentTabName) == 0:
            return
        if (usingMaya):
            prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            self.blockSignalsToLayoutEditor = True
            cmds.glmLayoutTool(cacheProxy=currentTabName, createRigOrPostureNode=True, requestSourceNode=nodeId)
            self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
        else:
            print('Creating a Rig or Posture Node outside of Maya is not available yet for node ' + str(nodeId))

    def createBlindDataParameters(self, nodeId):
        if self.layoutEditor is None:
            return
        currentTabName = self.layoutEditor.getCurrentTabName()
        if len(currentTabName) == 0:
            return
        blindDataNamesList=None
        if(usingMaya):
            blindDataNamesList = cmds.glmLayoutTool(cacheProxy=currentTabName, getAvailableBlindDataNames=True, requestSourceNode=nodeId)
        else:
            print('Creating a Rig or Posture Node outside of Maya is not available yet for node ' + str(nodeId))
        if blindDataNamesList is not None:

            self.layoutEditor.startCompoundInteraction(self.layoutEditor.getCurrentNodz())

            hideFlag = layoutUtils.GlmAttributeFlags._none
            for blindDataindex in range(len(blindDataNamesList)):
                if blindDataindex>5:
                    hideFlag = layoutUtils.GlmAttributeFlags._uiHidden
                #create the blind data attribute
                cacheProxyName = currentTabName
                attributeName = "{}-{}-blindData".format(blindDataNamesList[blindDataindex], blindDataindex)
                attributeType = 5 #float
                attributeFlags = layoutAttributeEditor.GlmAttributeFlags._uiKeyframable
                self.layoutEditor.editLayoutNodeAttribute(cacheProxyName, nodeId, attributeName, [], [[0]], True, attributeType, attributeFlags+hideFlag, False)
                #create the corresponding noise attributes
                attributeName = "{}-{}-blindDataFramesNoise".format(blindDataNamesList[blindDataindex], blindDataindex)
                self.layoutEditor.editLayoutNodeAttribute(cacheProxyName, nodeId, attributeName, [], [[0]], True, attributeType, layoutUtils.GlmAttributeFlags._uiHidden, False)

                attributeName = "{}-{}-blindDataNoise".format(blindDataNamesList[blindDataindex], blindDataindex)
                self.layoutEditor.editLayoutNodeAttribute(cacheProxyName, nodeId, attributeName, [], [[0]], True, attributeType, layoutUtils.GlmAttributeFlags._uiHidden, (blindDataindex>=len(blindDataNamesList)-1))

            self.layoutEditor.endCompoundInteraction(self.layoutEditor.getCurrentNodz(), True)

    def exportTrajectories(self, nodeId):
        if self.layoutEditor is None or self.blockSignalsFromLayoutEditor:
            return
        currentTabName = self.layoutEditor.getCurrentTabName()
        if len(currentTabName) == 0:
            return
        if (usingMaya):
            #prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            #self.blockSignalsToLayoutEditor = True
            cmds.glmLayoutTool(cacheProxy=currentTabName, exportTrajectoriesMeshMode=1, requestSourceNode=nodeId)
            #self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
        else:
            print('Creating a trajectory mesh outside of Maya is not available yet for node ' + str(nodeId))

    def exportSrcTrajectories(self, nodeId):
        if self.layoutEditor is None or self.blockSignalsFromLayoutEditor:
            return
        currentTabName = self.layoutEditor.getCurrentTabName()
        if len(currentTabName) == 0:
            return
        if (usingMaya):
            #prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            #self.blockSignalsToLayoutEditor = True
            cmds.glmLayoutTool(cacheProxy=currentTabName, exportTrajectoriesMeshMode=2, requestSourceNode=nodeId)
            #self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
        else:
            print('Creating a trajectory mesh outside of Maya is not available yet for node ' + str(nodeId))

    def exportDstTrajectories(self, nodeId):
        if self.layoutEditor is None or self.blockSignalsFromLayoutEditor:
            return
        currentTabName = self.layoutEditor.getCurrentTabName()
        if len(currentTabName) == 0:
            return
        if (usingMaya):
            #prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            #self.blockSignalsToLayoutEditor = True
            cmds.glmLayoutTool(cacheProxy=currentTabName, exportTrajectoriesMeshMode=3, requestSourceNode=nodeId)
            #self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
        else:
            print('Creating a trajectory mesh outside of Maya is not available yet for node ' + str(nodeId))

    def importSrcTrajectories(self, nodeId):
        if self.layoutEditor is None or self.blockSignalsFromLayoutEditor:
            return
        currentTabName = self.layoutEditor.getCurrentTabName()
        if len(currentTabName) == 0:
            return
        if (usingMaya):
            #prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            #self.blockSignalsToLayoutEditor = True
            allVertices=[]
            sList = om.MSelectionList()
            om.MGlobal.getActiveSelectionList( sList )
            pathDg = om.MDagPath()
            for iObject in range(sList.length()):
                sList.getDagPath(iObject, pathDg)
                pathDg.extendToShape()
                objectName = pathDg.partialPathName()
                objectType = cmds.objectType(objectName)
                if(objectType == "mesh"):
                    mItVtx = om.MItMeshVertex(pathDg)
                    while not mItVtx.isDone():
                        point = om.MPoint()
                        point = mItVtx.position(om.MSpace.kWorld)
                        allVertices.append([point.x, point.y, point.z])
                        mItVtx.next()
                    self.editLayoutNodeAttribute(currentTabName, nodeId, "trajectoryMode", [], [[0]])
                elif(objectType == "nurbsCurve"):
                    mItVtx = om.MItCurveCV(pathDg)
                    while not mItVtx.isDone():
                        point = om.MPoint()
                        point = mItVtx.position(om.MSpace.kWorld)
                        allVertices.append([point.x, point.y, point.z])
                        mItVtx.next()
                    self.editLayoutNodeAttribute(currentTabName, nodeId, "trajectoryMode", [], [[1]])
                    trajectoryDegree = cmds.getAttr('{}.degree'.format(objectName))
                    self.editLayoutNodeAttribute(currentTabName, nodeId, "srcTrajectoryDegree", [], [[trajectoryDegree]])

            self.editLayoutNodeAttribute(currentTabName, nodeId, "srcMesh", [], [allVertices])
            #self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
        else:
            print('Creating a trajectory mesh outside of Maya is not available yet for node ' + str(nodeId))

    def importDstTrajectories(self, nodeId):
        if self.layoutEditor is None or self.blockSignalsFromLayoutEditor:
            return
        currentTabName = self.layoutEditor.getCurrentTabName()
        if len(currentTabName) == 0:
            return
        if (usingMaya):
            #prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            #self.blockSignalsToLayoutEditor = True
            allVertices=[]
            sList = om.MSelectionList()
            om.MGlobal.getActiveSelectionList( sList )
            pathDg = om.MDagPath()
            for iObject in range(sList.length()):
                sList.getDagPath(iObject, pathDg)
                pathDg.extendToShape()
                objectName = pathDg.partialPathName()
                objectType = cmds.objectType(objectName)
                if(objectType == "mesh"):
                    mItVtx = om.MItMeshVertex(pathDg)
                    while not mItVtx.isDone():
                        point = om.MPoint()
                        point = mItVtx.position(om.MSpace.kWorld)
                        allVertices.append([point.x, point.y, point.z])
                        mItVtx.next()
                    self.editLayoutNodeAttribute(currentTabName, nodeId, "trajectoryMode", [], [[0]])
                elif(objectType == "nurbsCurve"):
                    mItVtx = om.MItCurveCV(pathDg)
                    while not mItVtx.isDone():
                        point = om.MPoint()
                        point = mItVtx.position(om.MSpace.kWorld)
                        allVertices.append([point.x, point.y, point.z])
                        mItVtx.next()
                    self.editLayoutNodeAttribute(currentTabName, nodeId, "trajectoryMode", [], [[1]])
                    trajectoryDegree = cmds.getAttr('{}.degree'.format(objectName))
                    self.editLayoutNodeAttribute(currentTabName, nodeId, "dstTrajectoryDegree", [], [[trajectoryDegree]])
            self.editLayoutNodeAttribute(currentTabName, nodeId, "dstMesh", [], [allVertices])

            # connect the mesh to the cache proxy node for automatic updates
            cacheProxyName=currentTabName
            currentTabNameSplitted = currentTabName.split(' ')
            if(len(currentTabNameSplitted)>1):
                cacheProxyName=currentTabNameSplitted[0]
            objectName = pathDg.partialPathName()
            cmds.connectAttr("{}.controlPoints[0]".format(objectName), "{}.layoutTrajectoryNodesAttributes[{}]".format(cacheProxyName, nodeId), force=True)

            #self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
        else:
            print('Creating a trajectory mesh outside of Maya is not available yet for node ' + str(nodeId))

    def createLocatorsForKeyframedAttributes(self, nodeId):
        if self.layoutEditor is None or self.blockSignalsFromLayoutEditor:
            return
        currentTabName = self.layoutEditor.getCurrentTabName()
        if len(currentTabName) == 0:
            return
        if (usingMaya):
            prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            self.blockSignalsToLayoutEditor = True
            cmds.glmLayoutTool(cacheProxy=currentTabName, createLocatorsForKeyframedAttrs=True, requestSourceNode=nodeId)
            self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
        else:
            print('Creating locators outside of Maya is not available yet for node ' + str(nodeId))

    def deleteLocatorsForKeyframedAttributes(self, nodeId):
        if self.layoutEditor is None or self.blockSignalsFromLayoutEditor:
            return
        currentTabName = self.layoutEditor.getCurrentTabName()
        if len(currentTabName) == 0:
            return
        if (usingMaya):
            prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            self.blockSignalsToLayoutEditor = True
            cmds.glmLayoutTool(cacheProxy=currentTabName, deleteLocatorsForKeyframedAttrs=True, requestSourceNode=nodeId)
            self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
        else:
            print('Deleting locators outside of Maya is not available yet for node ' + str(nodeId))

    def getRenderingTypeList(self, nodeName):
        if self.layoutEditor is None:
            return
        currentTabName = self.layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        if(usingMaya):
            renderingTypeList = cmds.glmLayoutTool(cacheProxy=currentTabName, getRenderingTypes=True, requestSourceNode=nodeName)
        else:
            renderingTypeList = [] #u"Fake Rendering Type From Wrapper", u"Another fake Rendering Type From Wrapper"]

        return renderingTypeList

    def getSelectedEntityMeshAssetList(self):
        if self.layoutEditor is None:
            return
        currentTabName = self.layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        selectedEntityMeshAssetList = None
        if(usingMaya):
            selectedEntityMeshAssetList = cmds.glmLayoutTool(cacheProxy=currentTabName, getSelectedEntityMeshAssets=True)
            # ToDo get possible RenderingType for selected entities, or display nothing ?
            # returns empty list if there is several character files selected
        else:
            selectedEntityMeshAssetList = []

        return selectedEntityMeshAssetList

    def getVectorFieldsList(self):
        if self.layoutEditor is None:
            return []

        if(usingMaya):
            self.layoutEditor.vectorFields = [u"Manual Entry"]
            vectorFields = mutils.getObjectsOfType("VectorFieldLocator")
            if vectorFields is not None:
                for vectorField in vectorFields:
                    self.layoutEditor.vectorFields.append(vectorField)
        else:
            self.layoutEditor.vectorFields = [u"Manual Entry"]
            # self.layoutEditor.vectorFields.append(u"FakeVectorField") #for testing purpose

        return self.layoutEditor.vectorFields

    def getPaintedZonesList(self):
        if self.layoutEditor is None:
            return []

        if(usingMaya):
            self.layoutEditor.paintedZones = [u"Manual Entry"]
            paintedZones = mutils.getObjectsOfType("PaintedZoneLocator")
            if paintedZones is not None:
                for paintedZone in paintedZones:
                    self.layoutEditor.paintedZones.append(paintedZone)
        else:
            self.layoutEditor.paintedZones = [u"Manual Entry"]
            # self.layoutEditor.paintedZones.append(u"FakePaintedZone") #for testing purpose

        return self.layoutEditor.paintedZones

    def statusBarHandledByWrapper(self):
        return usingMaya

    def getSelectedCharacterMeshAssetList(self, nodeName):
        if self.layoutEditor is None:
            return
        currentTabName = self.layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        if(usingMaya):
            meshAssetList = cmds.glmLayoutTool(cacheProxy=currentTabName, getAvailableMeshAssets=True, requestSourceNode=nodeName)
            # ToDo get possible RenderingType for selected entities, or display nothing ?
            # returns empty list if there is several character files selected
            #  = [u"Fake Mesh Asset Type From Maya", u"Another Mesh Asset Type From Maya"]
        else:
            meshAssetList = [] #u"Fake Mesh Asset Type From Wrapper", u"Another Mesh Asset Type From Wrapper"]

        return meshAssetList

    def getSelectedCharacterBonesNamesList(self, nodeName):
        if self.layoutEditor is None:
            return
        currentTabName = self.layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        if(usingMaya):
            bonesNamesList = cmds.glmLayoutTool(cacheProxy=currentTabName, getAvailableBonesNames=True, requestSourceNode=nodeName)
        else:
            bonesNamesList = []#u"Fake Bone Name From Wrapper", u"Another Fake Bone Name From Wrapper"]

        return bonesNamesList

    def openLayoutFile(self, isSaveDialog = False, saveTabName = ''):
        if usingMaya:
            if (isSaveDialog):
                filePath = mutils.fileBrowser('Save Golaem Layout File for Tab ' + saveTabName, ';;'.join(['Golaem Layout files (*.gscl)']), 'SimulationExport', 0) # 0 : Any file, whether it exists or not.
            else:
                filePath = mutils.fileBrowser('Open Golaem Layout File', ';;'.join(['Golaem Layout files (*.gscl)']), 'SimulationExport', 1) # 1 : a single existing file
        else:
            settings = QtCore.QSettings('Golaem', 'LayoutEditorWindow')
            baseDir = str(settings.value('LastFiles', os.path.dirname(os.path.realpath(__file__)))) #default to current file path

            if (isSaveDialog):
                filePath = QtWidgets.QFileDialog.getSaveFileName(None, 'Save Golaem Layout File for Tab ' + saveTabName, baseDir, "Golaem Layout files (*.gscl)")
            else:
                filePath = QtWidgets.QFileDialog.getOpenFileName(None, 'Open Golaem Layout File', baseDir, "Golaem Layout files (*.gscl)")

        if (filePath is not None and len(filePath)>0):
            return filePath[0]
        return ''

    def openDirectory(self, fileType, captionTitle):
        if usingMaya:
            fileDirs = mutils.fileBrowser(captionTitle, '', fileType, 3) # 1 : directory
        else:
            settings = QtCore.QSettings('Golaem', fileType)
            baseDir = str(settings.value('LastFiles', os.path.dirname(os.path.realpath(__file__)))) #default to current file path

            fileDirs = QtWidgets.QFileDialog.getExistingDirectory(None, captionTitle, baseDir)

        if (fileDirs is not None and len(fileDirs)>0):
            return fileDirs[0]
        return ''

    def loadWindowPref(self, name, aWindow):
        if (usingMaya):
            windowGeometryName = "{}_geometry".format(name)
            windowStateName = "{}_state".format(name)

            readState = cmds.optionVar(q=windowStateName) or ''
            readStateByteArrayHex = QtCore.QByteArray()
            readStateByteArrayHex = QtCore.QByteArray.fromRawData(readState.encode())
            readStateByteArray = QtCore.QByteArray.fromHex(readStateByteArrayHex)
            readStateByteArray = QtCore.QByteArray.fromHex(readState.encode())
            aWindow.restoreState(readStateByteArray)

            readGeometry = cmds.optionVar(q=windowGeometryName) or ''
            readGeometryByteArrayHex = QtCore.QByteArray()
            readGeometryByteArrayHex = QtCore.QByteArray.fromRawData(readGeometry.encode())
            readGeometryByteArray = QtCore.QByteArray.fromHex(readGeometryByteArrayHex)
            aWindow.restoreGeometry(readGeometryByteArray)

        else:
            settings = QtCore.QSettings('Golaem', 'LayoutEditor')
            settingValue = settings.value("{}_geometry".format(name))
            if (settingValue is not None):
                aWindow.restoreGeometry(settingValue)
            settingState = settings.value("{}_state".format(name))
            if (settingState is not None):
                aWindow.restoreState(settingState)

    def saveWindowPref(self, name, aWindow):
        if (usingMaya):

            windowGeometryName = "{}_geometry".format(name)
            windowStateName = "{}_state".format(name)

            # saving
            saveGeometryByteArray = aWindow.saveGeometry()
            saveGeometryByteArrayHex = saveGeometryByteArray.toHex()
            cmds.optionVar(sv=(windowGeometryName, saveGeometryByteArrayHex.data()))

            saveStateByteArray = aWindow.saveState()
            saveStateByteArrayHex = saveStateByteArray.toHex()
            cmds.optionVar(sv=(windowStateName, saveStateByteArrayHex.data()))
            cmds.savePrefs()
        else:
            settings = QtCore.QSettings('Golaem', 'LayoutEditor')
            settings.setValue("{}_geometry".format(name), aWindow.saveGeometry())
            settings.setValue("{}_state".format(name), aWindow.saveState())

    def setStatusMessage(self, text):
        if not self.blockSignalsToLayoutEditor:
            if self.layoutEditor is None:
                return
            self.blockSignalsFromLayoutEditor = True

            if self.layoutEditor is not None:
                self.layoutEditor.setStatusMessage(text)

            self.blockSignalsFromLayoutEditor = False

    def setCacheStatus(self, cacheProxyName, cacheStatus):
        if self.layoutEditor is not None:
            self.layoutEditor.setCacheStatus(cacheProxyName, cacheStatus)

    #------------------------------------------------------------------
    # returns the directory with the icons
    #------------------------------------------------------------------
    def getIconsDir(self):
        return self._iconsDir

    def updateAllCacheProxyPopTools(self):
        if self.layoutEditor is None:
            return

        #find all cache proxies
        cacheProxies = []
        for tabIndex in range(self.layoutEditor.editorTabWidget.count()):
            cacheProxyName = self.layoutEditor.getLayoutNameForTab(tabIndex)
            cacheProxies.append(cacheProxyName)
        #find all pop tools
        popTools = self.getPopulationToolList()
        #update all possible combinations
        for cacheProxy in cacheProxies:
            for popTool in popTools:
                self.updateCacheProxyTabPoptool(cacheProxy, popTool)

    def getNodeOutSelection(self, nodeInst):
        if (usingMaya):
            cacheProxyName = self.layoutEditor.getCurrentTabName()
            return cmds.glmLayoutTool(cacheProxy=cacheProxyName, requestSourceNode=nodeInst.userData['ID'] , getOutSelection=True)
        elif self.layoutEditor is not None:
            return self.layoutEditor.findEditedEntities(nodeInst.name)

    def getPoptoolSlots(self, anObject, poptoolName, entityTypeName):
        self.getEntityTypeList()
        anObject.snapToPosValues = None
        anObject.snapToOriValues = None
        if(usingMaya):
            if self.layoutEditor is not None:
                # if it has snapToPos and snapToOri, update with values from command
                isPoptool = cmds.objExists(poptoolName)
                if isPoptool and entityTypeName in self.layoutEditor.entityTypes: # else probably manual entry, let data as is
                    anObject.snapToPosValues = list() # nothing done if it stays at None
                    anObject.snapToOriValues = list() # nothing done if it stays at None

                    # get the type to filter result :
                    slotEntityTypes = list()
                    slotEntityTypes.append(cmds.getAttr(poptoolName+".entityTypes"))

                    snapToPosValues = list()
                    snapToPosValues.append(cmds.getAttr(poptoolName+".particles"))

                    snapToOriValues = list()
                    snapToOriValues.append(cmds.getAttr(poptoolName+".eulerOrientation"))

                    typeIndex = self.layoutEditor.entityTypes.index(entityTypeName)

                    if (typeIndex >= len(self.layoutEditor.entityTypeIds)):
                        return

                    typeId = self.layoutEditor.entityTypeIds[typeIndex]

                    # filter type and invalid lifespan
                    anObject.snapToPosValues.append(list())
                    anObject.snapToOriValues.append(list())
                    for i in range (len(slotEntityTypes[0])):
                        if (typeId == -1 or slotEntityTypes[0][i] == typeId):
                            anObject.snapToPosValues[0].append(list(snapToPosValues[0][i]))
                            anObject.snapToOriValues[0].append(list(snapToOriValues[0][i]))

        else:  # for testing purposes
            anObject.snapToPosValues = list() # nothing done if it stays at None
            anObject.snapToOriValues = list() # nothing done if it stays at None

            # if poptoolName == u'FakePopTool':
            #     anObject.snapToPosValues = list() # nothing done if it stays at None
            #     anObject.snapToOriValues = list() # nothing done if it stays at None

            #     anObject.snapToPosValues.append([[7,7,7],[8,8,8],[9,9,9]])
            #     anObject.snapToOriValues.append([[3,3,3],[4,4,4],[5,5,5]])

    def getVectorFieldNormalMap(self, anObject, vectorFieldName):
        anObject.vectorFieldMap = None

        if(usingMaya):
            isVectorField = cmds.objExists(vectorFieldName)
            if isVectorField: # else probably manual entry, let data as is
                vectorFieldMapPng = cmds.glmRenderPaintSurface(paintLocator=vectorFieldName, clear=False, refreshMesh=False, getMap=True)
                if vectorFieldMapPng is not None:
                    anObject.vectorFieldMap = vectorFieldMapPng

        else: # for testing purposes
            print("wrapper is getting the VectorFieldNormalMap '{}'. No maya.".format(vectorFieldName))
            # if vectorFieldName == 'FakeVectorField':
            #     anObject.vectorFieldMap = "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEAAgMAAAAhHED1AAAADFBMVEV//wAAfwD/fwB/AADMl8o6AAAAW0lEQVR4Ae3MMQ0AIBAAMUxiEpMg4QamT1oBXWUHgUAgEAgEAoFAIBAIBAKBQCAQCAQCgUAgEAgE44MTbhAIBAKBQCAQCAQCgUAgEAgEAoFAIBAIBAKBQCD4DR6nRwxhYxyG8gAAAABJRU5ErkJggg=="

    def getVectorFieldGeometry(self, anObject, vectorFieldName):
        anObject.vectorFieldGeometry = None

        if(usingMaya):
            isVectorField = cmds.objExists(vectorFieldName)
            if isVectorField: # else probably manual entry, let data as is
                vectorFieldGeometryString = cmds.glmRenderPaintSurface(paintLocator=vectorFieldName, clear=False, refreshMesh=False, getGeometry=True)
                anObject.vectorFieldGeometry = ast.literal_eval(vectorFieldGeometryString)

        else: # for testing purposes
            print("wrapper is getting the VectorFieldNormalMap '{}'. No maya.".format(vectorFieldName))
            # if vectorFieldName == 'FakeVectorField':
            #     vertices = [[-12,0,-12], [-12,0,12], [12,0,12], [12,0,-12]]
            #     normals =  [[0,1,0], [0,1,0], [0,1,0], [0,1,0]]
            #     UVs = [-1,-1,-1,1,1,1,1,-1]
            #     indices = [0,1,2,2,3,0]
            #     geometry = list()
            #     geometry.append(vertices)
            #     geometry.append(normals)
            #     geometry.append(UVs)
            #     geometry.append(indices)
            #     anObject.vectorFieldGeometry = geometry

    def getPaintedZoneNormalMap(self, anObject, paintedZoneName):
        anObject.paintedZoneMap = None

        if(usingMaya):
            isPaintedZone = cmds.objExists(paintedZoneName)
            if isPaintedZone: # else probably manual entry, let data as is
                paintedZoneMapPng = cmds.glmRenderPaintSurface(paintLocator=paintedZoneName, clear=False, refreshMesh=False, getMap=True)
                if paintedZoneMapPng is not None:
                    anObject.paintedZoneMap = paintedZoneMapPng

        else: # for testing purposes
            print("wrapper is getting the PaintedZoneNormalMap '{}'. No maya.".format(paintedZoneName))
            # if paintedZoneName == 'FakePaintedZone':
            #     anObject.paintedZoneMap = "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEAAgMAAAAhHED1AAAADFBMVEV//wAAfwD/fwB/AADMl8o6AAAAW0lEQVR4Ae3MMQ0AIBAAMUxiEpMg4QamT1oBXWUHgUAgEAgEAoFAIBAIBAKBQCAQCAQCgUAgEAgE44MTbhAIBAKBQCAQCAQCgUAgEAgEAoFAIBAIBAKBQCD4DR6nRwxhYxyG8gAAAABJRU5ErkJggg=="

    def getPaintedZoneGeometry(self, anObject, paintedZoneName):
        anObject.paintedZoneGeometry = None

        if(usingMaya):
            isPaintedZone = cmds.objExists(paintedZoneName)
            if isPaintedZone: # else probably manual entry, let data as is
                paintedZoneGeometryString = cmds.glmRenderPaintSurface(paintLocator=paintedZoneName, clear=False, refreshMesh=False, getGeometry=True)
                anObject.paintedZoneGeometry = ast.literal_eval(paintedZoneGeometryString)

        else: # for testing purposes
            print("wrapper is getting the PaintedZoneNormalMap '{}'. No maya.".format(paintedZoneName))            

    def getMeshVertices(self, anObject, objectName):
        anObject.meshVertices = None

        if(usingMaya):
            isMesh = cmds.objExists(objectName)
            if isMesh: # else probably manual entry, let data as is
                anObject.meshVertices=[]

                sList = om.MSelectionList()
                sList.add(objectName)
                pathDg = om.MDagPath()
                sList.getDagPath(0, pathDg)
                pathDg.extendToShape()
                objectName = pathDg.partialPathName()
                objectType = cmds.objectType(objectName)
                if(objectType == "mesh"):
                    mItVtx = om.MItMeshVertex(pathDg)
                    while not mItVtx.isDone():
                        point = om.MPoint()
                        point = mItVtx.position(om.MSpace.kWorld)
                        anObject.meshVertices.append([point.x, point.y, point.z])
                        mItVtx.next()
                elif(objectType == "nurbsCurve"):
                    mItVtx = om.MItCurveCV(pathDg)
                    while not mItVtx.isDone():
                        point = om.MPoint()
                        point = mItVtx.position(om.MSpace.kWorld)
                        anObject.meshVertices.append([point.x, point.y, point.z])
                        mItVtx.next()

        else: # for testing purposes
            print("wrapper is getting the vertices from mesh '{}'. No maya.".format(objectName))
            # if vectorFieldName == 'FakeVectorField':
            #     vertices = [[-12,0,-12], [-12,0,12], [12,0,12], [12,0,-12]]
            #     normals =  [[0,1,0], [0,1,0], [0,1,0], [0,1,0]]
            #     UVs = [-1,-1,-1,1,1,1,1,-1]
            #     indices = [0,1,2,2,3,0]
            #     geometry = list()
            #     geometry.append(vertices)
            #     geometry.append(normals)
            #     geometry.append(UVs)
            #     geometry.append(indices)
            #     anObject.vectorFieldGeometry = geometry

    def getSelectedEntities(self, cacheProxyName):
        result = ""
        if(usingMaya):
            tempResult = cmds.glmLayoutTool(cacheProxy=cacheProxyName, getSelectedEntities=True)
            if tempResult: # check against None value
                result = tempResult
        if (usingUnreal):
            editorLevelLib = unreal.EditorLevelLibrary()
            editorWorld = editorLevelLib.get_editor_world()
            cacheNameElements = cacheProxyName.split(' ')  # cacheElement[0] = proxy name, [1] is index
            myGolaemCache = editorLevelLib.get_actor_reference('PersistentLevel.{}'.format(cacheNameElements[0]))
            if (myGolaemCache is not None):
                result = myGolaemCache.get_selected_entities()

        return result # 1001,2001,3001

    def replaceDuplicatesInSelection(self, cacheProxyName, selectionExpression):
        result = selectionExpression
        if (usingMaya):
            tempResult = cmds.glmLayoutTool(cacheProxy=cacheProxyName, replaceDuplicateInString=selectionExpression)
            if tempResult: # check against None value
                result = tempResult
        return result

    @QtCore.Slot(object, object)
    def on_nodeSelected(self, layoutEditor, nodesName):
        currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        if not self.blockSignalsFromLayoutEditor:

            if(usingMaya and layoutEditor.syncSelection):
                cmds.select(clear=True)

            #select nodes directly (by layout node ID)
            theNodz = self.layoutEditor.getCurrentNodz()
            selectedNodesIDs = list()
            for nodeName in nodesName:
                if nodeName in theNodz.scene().nodes:
                    currentNode = theNodz.scene().nodes[nodeName]
                    selectedNodesIDs.append(currentNode.userData["ID"])

            if(usingMaya):
                if (layoutEditor.syncSelection):
                    prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
                    self.blockSignalsToLayoutEditor = True
                    cmds.glmLayoutTool(cacheProxy=currentTabName, selectLayoutNodes=str(selectedNodesIDs))
                    self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
            else:
                print('Selected layout nodes(s) : {}.'.format(selectedNodesIDs))

    @QtCore.Slot(object)
    def on_endCompoundInteraction(self, layoutEditor):
        currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        if (not layoutEditor.isCurrentTabOpenViaOpenAction()):
        # if not self.blockSignalsFromLayoutEditor: # cannot be as caller set it false just before signal

            #JSON that describes the full graph (same as when saving a file)
            layoutInfo = layoutEditor.buildGolaemLayoutFile(
                layoutEditor.getCurrentMainNodz(), layoutEditor.getCurrentTabIndex())
            layoutJSON = json.dumps(layoutInfo,
                            sort_keys = False,
                            indent = 2,
                            ensure_ascii=False)

            prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            self.blockSignalsToLayoutEditor = True
            self.sendLayoutInternal(currentTabName, layoutJSON, self.compoundDirtyLayoutNodeIDs, self.compoundDirtyAssetRepartition)
            self.compoundDirtyLayoutNodeIDs = list()
            self.compoundDirtyAssetRepartition = False
            self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

    @QtCore.Slot(object, bool)
    def on_layoutGraphChanged(self, layoutEditor, doRefreshAssets):
        currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        if self.blockJSonUpload: # called back Maya -> reloadCacheProxy -> clearTab : no need to send back again the json
            return

        # update items even if filtered
        if self.blockSignalsFromLayoutEditor:
            self.compoundDirtyAssetRepartition = self.compoundDirtyAssetRepartition or doRefreshAssets
        else:
            #JSON that describes the full graph (same as when saving a file)
            layoutInfo = layoutEditor.buildGolaemLayoutFile(
                layoutEditor.getCurrentMainNodz(), layoutEditor.getCurrentTabIndex())
            layoutJSON = json.dumps(layoutInfo,
                            sort_keys = False,
                            indent = 2,
                            ensure_ascii=False)

            if (not layoutEditor.isCurrentTabOpenViaOpenAction()):
                prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
                self.blockSignalsToLayoutEditor = True
                self.sendLayoutInternal(currentTabName, layoutJSON, [], doRefreshAssets)
                self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

    @QtCore.Slot(object, str)
    def on_layoutNodeChanged(self, layoutEditor, nodeName):
        currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        #does it need to refresh CAA as well ? only if node is a MeshAsset / Rendering Type ("SimulationCacheSetMeshAssets")
        doRecomputeAssets = False
        nodeID = -1
        # find the nodz containing the node
        theNodz = self.layoutEditor.getNodeNodz(layoutEditor.getCurrentTabIndex(), nodeName)
        if(theNodz is not None):
            node = theNodz.scene().nodes[nodeName]
            nodeID = node.userData['ID']
            if('type' in node.userData):
                currentNodeType = node.userData['type']
                if currentNodeType in [layoutUtils.GlmTransformType.SetMeshAssets, layoutUtils.GlmTransformType.SetRenderingType, layoutUtils.GlmTransformType.AddRemoveMeshAssets]:
                    doRecomputeAssets = True

        if self.blockSignalsFromLayoutEditor:
            # update items even if filtered
            self.compoundDirtyAssetRepartition = self.compoundDirtyAssetRepartition or doRecomputeAssets
            if (nodeID != -1 and nodeID not in self.compoundDirtyLayoutNodeIDs):
                self.compoundDirtyLayoutNodeIDs.append(nodeID)
        else:

            #JSON that describes the full graph (same as when saving a file)
            layoutInfo = layoutEditor.buildGolaemLayoutFile(
                layoutEditor.getCurrentMainNodz(), layoutEditor.getCurrentTabIndex())
            layoutJSON = json.dumps(layoutInfo,
                            sort_keys = False,
                            indent = 2,
                            ensure_ascii=False)

            if (not layoutEditor.isCurrentTabOpenViaOpenAction()):
                dirtyNodeList = list()
                dirtyNodeList.append(nodeID)
                #dirtyNodeList
                prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor  # sometimes calls are done from inside a blocking operation (updateTrajectoryField cascade to this)
                self.blockSignalsToLayoutEditor = True
                self.sendLayoutInternal(currentTabName, layoutJSON, [nodeID], doRecomputeAssets)
                self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

    @QtCore.Slot(object)
    def on_layoutParameterChanged(self, layoutEditor):
        currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        if not self.blockSignalsFromLayoutEditor:

            #JSON that describes the full graph (same as when saving a file)
            layoutInfo = layoutEditor.buildGolaemLayoutFile(
                layoutEditor.getCurrentMainNodz(), layoutEditor.getCurrentTabIndex())
            layoutJSON = json.dumps(layoutInfo,
                            sort_keys = False,
                            indent = 2,
                            ensure_ascii=False)

            #does it need to refresh CAA as well ? only if node is a type 7 ("SimulationCacheSetMeshAssets")
            doRecomputeAssets = True
            theNodz = self.layoutEditor.getCurrentNodz()
            rootNodeID = theNodz.scene().userData['rootTransformId']

            if (not layoutEditor.isCurrentTabOpenViaOpenAction()):
                prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
                self.blockSignalsToLayoutEditor = True
                self.sendLayoutInternal(currentTabName, layoutJSON, [rootNodeID], doRecomputeAssets)
                self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

    @QtCore.Slot(object, str)
    def on_layoutRootChanged(self, layoutEditor, nodeName):
        currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        if not self.blockSignalsFromLayoutEditor:

            #JSON that describes the full graph (same as when saving a file)
            layoutInfo = layoutEditor.buildGolaemLayoutFile(
                layoutEditor.getCurrentMainNodz(), layoutEditor.getCurrentTabIndex())
            layoutJSON = json.dumps(layoutInfo,
                            sort_keys = False,
                            indent = 2,
                            ensure_ascii=False)

            #does it need to refresh CAA as well ? only if node is a type 7 ("SimulationCacheSetMeshAssets")
            doRecomputeAssets = False # will be computed in clearCachePropagation
            nodeID = -1
            theNodz = self.layoutEditor.getCurrentNodz()
            if theNodz.scene().userData['rootTransformId'] != -1 and nodeName in theNodz.scene().nodes:
                node = theNodz.scene().nodes[nodeName]
                nodeID = node.userData['ID']

            if (not layoutEditor.isCurrentTabOpenViaOpenAction()):
                prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
                self.blockSignalsToLayoutEditor = True
                self.sendLayoutInternal(currentTabName, layoutJSON, [nodeID], doRecomputeAssets)
                self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

            #When the root node changed, the currently selected node might become an executed node while it wasn 't one before. We need to refresh the curently selected entities in case...
            self.on_nodeSelected(layoutEditor, theNodz.selectedNodes)

    @QtCore.Slot(object, int)
    def on_rigOrPostureCreate(self, layoutEditor, nodeId):
        self.createRigOrPostureNode(nodeId)

    @QtCore.Slot(object, int)
    def on_blindDataParametersCreate(self, layoutEditor, nodeId):
        self.createBlindDataParameters(nodeId)

    @QtCore.Slot(object, int)
    def on_trajectoriesMeshExport(self, layoutEditor, nodeId):
        self.exportTrajectories(nodeId)

    @QtCore.Slot(object, int)
    def on_trajectoriesSrcExport(self, layoutEditor, nodeId):
        self.exportSrcTrajectories(nodeId)

    @QtCore.Slot(object, int)
    def on_trajectoriesDstExport(self, layoutEditor, nodeId):
        self.exportDstTrajectories(nodeId)

    @QtCore.Slot(object, int)
    def on_trajectoriesSrcImport(self, layoutEditor, nodeId):
        self.importSrcTrajectories(nodeId)

    @QtCore.Slot(object, int)
    def on_trajectoriesDstImport(self, layoutEditor, nodeId):
        self.importDstTrajectories(nodeId)

    @QtCore.Slot(object, int)
    def on_keyframedLocatorsCreate(self, layoutEditor, nodeId):
        self.createLocatorsForKeyframedAttributes(nodeId)

    @QtCore.Slot(object, int)
    def on_keyframedLocatorsDelete(self, layoutEditor, nodeId):
        self.deleteLocatorsForKeyframedAttributes(nodeId)

    @QtCore.Slot(object, str, str)
    def on_layoutSnapToSlotsUpdate(self, layoutEditor, selectedPoptoolName, entityTypeName):
        self.getPoptoolSlots(layoutEditor, selectedPoptoolName, entityTypeName)

    @QtCore.Slot(object, str, str)
    def on_layoutSnapToPoptoolComboBoxEdited(self, layoutAttributeEditor, selectedPoptoolName, entityTypeName):
        self.getPoptoolSlots(layoutAttributeEditor, selectedPoptoolName, entityTypeName)
        if (layoutAttributeEditor.snapToPosValues is not None and layoutAttributeEditor.snapToOriValues is not None):
            layoutAttributeEditor.setSnapToAttributesUI()

    @QtCore.Slot(object, str)
    def on_layoutVectorFieldComboBoxEdited(self, layoutAttributeEditor, selectedVectorFieldName):
        #update normal map
        self.getVectorFieldNormalMap(layoutAttributeEditor, selectedVectorFieldName)
        if (layoutAttributeEditor.vectorFieldMap is not None):
            layoutAttributeEditor.setVectorFieldNormalMapUI()
        #update geometry
        self.getVectorFieldGeometry(layoutAttributeEditor, selectedVectorFieldName)
        if (layoutAttributeEditor.vectorFieldGeometry is not None):
            layoutAttributeEditor.setVectorFieldGeometryUI()

    @QtCore.Slot(object, str)
    def on_layoutVectorFieldUpdate(self, layoutEditor, vectorFieldName):
        #update normal map
        self.getVectorFieldNormalMap(layoutEditor, vectorFieldName)
        #update geometry
        self.getVectorFieldGeometry(layoutEditor, vectorFieldName)

    @QtCore.Slot(object, str)
    def on_layoutPaintedZoneComboBoxEdited(self, layoutAttributeEditor, selectedPaintedZoneName):
        #update normal map
        self.getPaintedZoneNormalMap(layoutAttributeEditor, selectedPaintedZoneName)
        if (layoutAttributeEditor.paintedZoneMap is not None):
            layoutAttributeEditor.setPaintedZoneNormalMapUI()
        #update geometry
        self.getPaintedZoneGeometry(layoutAttributeEditor, selectedPaintedZoneName)
        if (layoutAttributeEditor.paintedZoneGeometry is not None):
            layoutAttributeEditor.setPaintedZoneGeometryUI()

    @QtCore.Slot(object, str)
    def on_layoutPaintedZoneUpdate(self, layoutEditor, paintedZoneName):
        #update normal map
        self.getPaintedZoneNormalMap(layoutEditor, paintedZoneName)
        #update geometry
        self.getPaintedZoneGeometry(layoutEditor, paintedZoneName)
        
    @QtCore.Slot(object, str)
    def on_layoutEditTrajectoryMeshUpdate(self, layoutEditor, currentTabName, layoutNodeID):
        #find the mesh name from the connection to the cache proxy
        cacheProxyName=currentTabName
        currentTabNameSplitted = currentTabName.split(' ')
        if(len(currentTabNameSplitted)>1):
            cacheProxyName=currentTabNameSplitted[0]

        inputMeshes = cmds.listConnections("{}.layoutTrajectoryNodesAttributes[{}]".format(cacheProxyName,layoutNodeID))
        if(inputMeshes is not None):
            if(len(inputMeshes)>0):
                self.getMeshVertices(layoutEditor, inputMeshes[0])

    @QtCore.Slot(object, str)
    def on_layoutNodePreEdited(self, layoutEditor, nodesName):
        currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName) == 0:
            return

        usePoptools = False
        useEntityTypes = False
        useRenderingType = False
        # useSelectedEntityMeshAssets = False
        useCharacterMeshAssets = False
        useBonesNames = False
        useVectorFields = False
        usePaintedZones = False

        theNodz = self.layoutEditor.getCurrentNodz()
        if(nodesName in theNodz.scene().nodes):
            node = theNodz.scene().nodes[nodesName]
            if 'attributes' in node.userData:
                for currentAttribute in node.userData['attributes']:
                    if ('type' in currentAttribute):
                        #attributeType = currentAttribute['type']
                        attributeFlags = layoutUtils.GlmAttributeFlags._none
                        if 'flags' in currentAttribute:
                            attributeFlags = currentAttribute['flags']

                        usePoptools = usePoptools or (attributeFlags & layoutUtils.GlmAttributeFlags._uiSnapToTargetComboBox != 0)
                        useEntityTypes = useEntityTypes or (attributeFlags & layoutUtils.GlmAttributeFlags._uiSnapToTargetComboBox != 0)
                        useRenderingType = useRenderingType or (attributeFlags & layoutUtils.GlmAttributeFlags._uiRenderingTypeDropDown != 0)
                        # useSelectedEntityMeshAssets = useSelectedEntityMeshAssets or (attributeFlags & layoutUtils.GlmAttributeFlags._uiPickSelectedEntityMeshAssets != 0)
                        useCharacterMeshAssets = useCharacterMeshAssets or (attributeFlags & layoutUtils.GlmAttributeFlags._uiSelectedCharMeshAssetComboBox != 0)
                        useBonesNames = useBonesNames or (attributeFlags & layoutUtils.GlmAttributeFlags._uiBoneNamesComboBox != 0)
                        useVectorFields = useVectorFields or (attributeFlags & layoutUtils.GlmAttributeFlags._uiVectorFieldTargetComboBox != 0)
                        usePaintedZones = usePaintedZones or (attributeFlags & layoutUtils.GlmAttributeFlags._uiPaintedZoneTargetComboBox != 0)

            if (useRenderingType):
                self.layoutEditor.renderingTypes = self.getRenderingTypeList(node.userData["ID"])
            if (useCharacterMeshAssets):
                self.layoutEditor.selectedCharacterMeshAssets = self.getSelectedCharacterMeshAssetList(node.userData["ID"])
            if(useBonesNames):
                self.layoutEditor.bonesNames = self.getSelectedCharacterBonesNamesList(node.userData["ID"])

        if (usePoptools):
            self.getPopulationToolList()
        if (useEntityTypes):
            self.getEntityTypeList()
        # if (useSelectedEntityMeshAssets):
        #     self.layoutEditor.selectedEntityMeshAssets = self.getSelectedEntityMeshAssetList() : this is contextual, it is now postponed to when the user pick it
        if (useVectorFields):
            self.getVectorFieldsList()
        if (usePaintedZones):
            self.getPaintedZonesList()            

    @QtCore.Slot(object, object)
    def on_layoutNodeCreated(self, layoutEditor, nodzNode):
        currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return

        if not self.blockSignalsFromLayoutEditor:

            if(usingMaya):
                if 'entities' in nodzNode.userData:
                    # self.blockSignalsToLayoutEditor = True # getSelectedEntities should not impact updates / refreshes or callback anything
                    selectedEntitiesIds = self.getSelectedEntities(cacheProxyName=currentTabName)
                    selectedEntitiesWithReplacedDuplicates = self.replaceDuplicatesInSelection(cacheProxyName=currentTabName, selectionExpression=selectedEntitiesIds)
                    # self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor
                    nodzNode.userData['entities'] = selectedEntitiesWithReplacedDuplicates
            else:
                print('Layout node created. Created node: {} with ID {}'.format(nodzNode.userData['name'], nodzNode.userData['ID']))

    @QtCore.Slot(int, str)
    def on_layoutGraphSetFilePath(self, tabIndex, filePath):
        # currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        # if len(currentTabName)==0:
        #     return
        # if(usingMaya):
        #     cacheNameElements = tabName.split(' ') # cacheElement[0] = proxy name, [1] is index
        #     isCacheProxy = cmds.objExists(cacheNameElements[0])
        #     if not isCacheProxy:
        #         return
        if not self.blockSignalsFromLayoutEditor:
            prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            self.blockSignalsToLayoutEditor = True  # the graph is already loaded here, no need to reload it !
            tabName = self.layoutEditor.getLayoutNameForTab(tabIndex)
            if (usingMaya):
                cacheNameElements = tabName.split(' ')  # cacheElement[0] = proxy name, [1] is index
                isCacheProxy = cmds.objExists(cacheNameElements[0])
                if isCacheProxy:
                    cmds.setAttr('{}.layoutFiles[{}].path'.format(cacheNameElements[0], cacheNameElements[1]), filePath, type="string")  #will load the json in Maya as well, no need to transmit the layoutJSON
            elif (usingUnreal):
                # find object of relative name
                cacheNameElements = tabName.split(' ')  # cacheElement[0] = proxy name, [1] is index
                cacheProxyArray = unreal.EditorFilterLibrary.by_id_name(unreal.EditorLevelLibrary.get_all_level_actors(), cacheNameElements[0], unreal.EditorScriptingStringMatchType.EXACT_MATCH)
                if len(cacheProxyArray) > 0:
                    # if exists, check if layout file path is empty
                    currentLayoutFile = cacheProxyArray[0].get_editor_property('LayoutFile')
                    # if empty, set enabled true
                    if (len(currentLayoutFile) == 0):
                        cacheProxyArray[0].set_editor_property('bEnableLayout', True)
                    # set value
                    cacheProxyArray[0].set_editor_property('LayoutFile', filePath)                    
            else:
                print('Layout file for {} is now: {}'.format(tabName, filePath))
            self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

    @QtCore.Slot(object, int)
    def on_layoutCacheSizeChanged(self, layoutEditor, newValue):
        currentTabName = layoutEditor.getLayoutNameForCurrentTab()
        if len(currentTabName)==0:
            return
        if(usingMaya):
            cacheNameElements = currentTabName.split(' ') # cacheElement[0] = proxy name, [1] is index
            isCacheProxy = cmds.objExists(cacheNameElements[0])
            if not isCacheProxy:
                return

        if not self.blockSignalsFromLayoutEditor:
            prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
            self.blockSignalsToLayoutEditor = True

            cacheNameElements = currentTabName.split(' ') # cacheElement[0] = proxy name, [1] is index
            if (usingMaya):
                cmds.setAttr('{}.memoryBudget'.format(cacheNameElements[0]), newValue)
            else:
                print('Layout cache size for {} is now: {}'.format(currentTabName, newValue))

            self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

    ###################################################################
    ###################### MAYA TO LAYOUT EDITOR ######################
    ###################################################################

    def openMayaCacheProxiesInNewTabs(self):
        if not self.blockSignalsToLayoutEditor:
            if(usingMaya):
                cacheProxies = mutils.getObjectsOfType("SimulationCacheProxy")
                for cacheProxy in cacheProxies:
                    layoutFilesIndices = cmds.getAttr('{}.layoutFiles'.format(cacheProxy), multiIndices=True) # return valid indices
                    if layoutFilesIndices is not None and len(layoutFilesIndices) > 0:
                        for alayoutFileIndex in range(0, len(layoutFilesIndices)):
                            layoutFileIndex = layoutFilesIndices[alayoutFileIndex]
                            self.openCacheProxy("{} {}".format(cacheProxy, layoutFileIndex), False) # False: We don't want to change currentIndex of tabWidget
                    else:
                        # must add a layoutFile entry and open it
                        cmds.glmLayoutTool(cacheProxy=cacheProxy, focusEdited=True)

    def updateAllCacheProxyTabPoptools(self, cacheProxyName):
        poptools = self.getPopulationToolList()
        if poptools is not None:
            for poptool in poptools:
                self.updateCacheProxyTabPoptool(cacheProxyName, poptool)

    def updateCacheProxyTabPoptool(self, cacheProxyName, poptoolName):
        if self.layoutEditor is None:
            return

        # update poptool list to be sure it is up to date
        # self.getPopulationToolList()
        # self.openCacheProxy(cacheProxyName)
        self.cacheProxyPoptoolsChanged = self.layoutEditor.updatePoptool(cacheProxyName, poptoolName) # iterate on snapTo nodes using this poptool, if found force update their value

    def areCacheProxyPoptoolsChanged(self):
        return self.cacheProxyPoptoolsChanged

    def updateAllCacheProxyTabVectorFields(self, cacheProxyName):
        vectorFields = self.getVectorFieldsList()
        if vectorFields is not None:
            for vectorField in vectorFields:
                self.updateCacheProxyTabVectorField(cacheProxyName, vectorField)

    def updateCacheProxyTabVectorField(self, cacheProxyName, vectorFieldName):
        if self.layoutEditor is None:
            return

        if not self.blockUpdateTrajectoryField:
            self.blockUpdateTrajectoryField = True

        self.cacheProxyVectorFieldsChanged = False

        # update poptool list to be sure it is up to date
        # self.getVectorFieldsList()
        # self.openCacheProxy(cacheProxyName)
        self.cacheProxyVectorFieldsChanged = self.layoutEditor.updateVectorFields(cacheProxyName, vectorFieldName) # iterate on snapTo nodes using this poptool, if found force update their value

        self.blockUpdateTrajectoryField = False

    def areCacheProxyVectorFieldsChanged(self):
        return self.cacheProxyVectorFieldsChanged

    def updateAllCacheProxyTabPaintedZones(self, cacheProxyName):
        paintedZones = self.getPaintedZonesList()
        if paintedZones is not None:
            for paintedZone in paintedZones:
                self.updateCacheProxyTabPaintedZone(cacheProxyName, paintedZone)
    
    def updateCacheProxyTabPaintedZone(self, cacheProxyName, paintedZoneName):
        if self.layoutEditor is None:
            return

        if not self.blockUpdatePaintedZone:
            self.blockUpdatePaintedZone = True

        self.cacheProxyPaintedZonesChanged = False

        # update poptool list to be sure it is up to date
        # self.getPaintedZonesList()
        # self.openCacheProxy(cacheProxyName)
        self.cacheProxyPaintedZonesChanged = self.layoutEditor.updatePaintedZones(cacheProxyName, paintedZoneName) # iterate on snapTo nodes using this poptool, if found force update their value

        self.blockUpdatePaintedZone = False

    def areCacheProxyPaintedZonesChanged(self):
        return self.cacheProxyPaintedZonesChanged

    def updateAllCacheProxyTrajectories(self, cacheProxyName):
        if self.layoutEditor is None:
            return

        #self.cacheProxyPoptoolsChanged = self.layoutEditor.updatePoptool(cacheProxyName, poptoolName) # iterate on snapTo nodes using this poptool, if found force update their value
        self.layoutEditor.updateAllTrajectories(cacheProxyName) # iterate on editTrajectory nodes, if found force update their value

    def lockCacheProxy(self, cacheProxyNameAndIndex, editEnabled):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return

        self.blockSignalsFromLayoutEditor = True
        if len(cacheProxyNameAndIndex) > 0:
            #move to the correct tab, or create a new one if none exist with the desired name
            for tabIndex in range(self.layoutEditor.editorTabWidget.count()):
                tabName = self.layoutEditor.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyNameAndIndex:
                    self.layoutEditor.setEditedNode(None, None) # reset the attribute editor
                    self.layoutEditor.layoutViewTabWidgets[tabIndex].setEditEnabled(editEnabled)
                    # self.layoutEditor.editorTabWidget.setEditEnabled(editEnabled)
                    break
        self.blockSignalsFromLayoutEditor = False

    def reloadCacheProxy(self, cacheProxyNameAndIndex, editEnabled):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return

        # we block signals TO layout editor : we want to be able to request everything that need to be requested at load : poptools, entityTypes, etc
        prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
        self.blockSignalsToLayoutEditor = True
        if len(cacheProxyNameAndIndex) > 0:
            #move to the correct tab, or create a new one if none exist with the desired name
            foundTab = False
            for tabIndex in range(self.layoutEditor.editorTabWidget.count()):
                tabName = self.layoutEditor.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyNameAndIndex:
                    self.layoutEditor.editorTabWidget.setCurrentIndex(tabIndex) #need to force focus to be able to reload the layout in the correct tab
                    foundTab = True
                    break
            if not foundTab:
                #self.blockSignalsFromLayoutEditor = True  # block layoutGraphChanged event, we are sending another one when loaded below, else we will send an empty graph in the mean time
                self.layoutEditor.newTab(cacheProxyNameAndIndex)
                #self.blockSignalsFromLayoutEditor = False  # reopen communication to load the layout and get poptools / entities / etc
            #now force reload the file in the current tab
            if(usingMaya):
                cacheNameElements = cacheProxyNameAndIndex.split(' ') # cacheElement[0] = proxy name, [1] is index
                filePath = cmds.getAttr('{}.layoutFiles[{}].path'.format(cacheNameElements[0], cacheNameElements[1]))
                if (filePath is not None and filePath != ''):
                    self.blockJSonUpload = True
                    self.layoutEditor.loadGolaemLayoutFile(filePath, focus=True, autoLayout=False)
                    self.layoutEditor.getCurrentMainNodz().scene().userData['currentFilePath'] = filePath
                    self.blockJSonUpload = False
                else:
                    self.layoutEditor.signal_LayoutGraphChanged.emit(self.layoutEditor, True)
                self.layoutEditor.getCurrentTabWidget().setEditEnabled(editEnabled)
                self.layoutEditor.setEditedNode(None, None) # reset the attribute editor
                # self.layoutEditor.editorTabWidget.setEditEnabled(editEnabled)
            else:
                self.layoutEditor.signal_LayoutGraphChanged.emit(self.layoutEditor, True)

            # we have reloaded a complete layout, reset the undo stacks
            self.layoutEditor.clearUndoStack(self.layoutEditor.getCurrentTabIndex())
            self.layoutEditor.stackUndo(self.layoutEditor.getCurrentTabIndex()) # this will become the base, never deleted undo state
        self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

    def openCacheProxy(self, cacheProxyNameAndIndex, focus=True):
        if self.layoutEditor is None  or self.blockSignalsToLayoutEditor:
            return

        # we block signals TO layout editor : we want to be able to request everything from layoutEditor->Maya that need to be requested at load
        #such as poptools, entityTypes, etc
        if len(cacheProxyNameAndIndex) > 0:
            #move to the correct tab, or create a new one if none exist with the desired name
            foundTab = False
            for tabIndex in range(self.layoutEditor.editorTabWidget.count()):
                tabName = self.layoutEditor.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyNameAndIndex:
                    if (focus):
                        self.layoutEditor.editorTabWidget.setCurrentIndex(tabIndex)
                    foundTab = True
            if not foundTab:
                # self.blockSignalsFromLayoutEditor = True  # block layoutGraphChanged event, we are sending another one when loaded below, else we will send an empty graph in the mean time
                self.layoutEditor.newTab(cacheProxyNameAndIndex)
                # self.blockSignalsFromLayoutEditor = False  # reopen communication to load the layout and get poptools / entities / etc

                if (usingMaya):
                    cacheNameElements = cacheProxyNameAndIndex.split(' ')  # cacheElement[0] = proxy name, [1] is index
                    fileLocked = cmds.getAttr('{}.layoutFiles[{}].locked'.format(cacheNameElements[0], cacheNameElements[1]))
                    filePath = cmds.getAttr('{}.layoutFiles[{}].path'.format(cacheNameElements[0], cacheNameElements[1]))
                    if (fileLocked is not None and filePath is not None and filePath != ''):
                        #self.blockSignalsToLayoutEditor = True # but block in case of loops
                        self.layoutEditor.loadGolaemLayoutFile(filePath, focus=True, autoLayout=False)
                        #self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor # but block in case of loops
                        self.layoutEditor.getCurrentMainNodz().scene().userData['currentFilePath'] = filePath
                        self.layoutEditor.getCurrentTabWidget().setEditEnabled(not fileLocked)
                    else:
                        self.layoutEditor.signal_LayoutGraphChanged.emit(self.layoutEditor, True)
                    self.layoutEditor.setEditedNode(None, None)  # reset the attribute editor
                else:
                    self.layoutEditor.signal_LayoutGraphChanged.emit(self.layoutEditor, True)

                self.layoutEditor.clearUndoStack(self.layoutEditor.getCurrentTabIndex())
                self.layoutEditor.stackUndo(self.layoutEditor.getCurrentTabIndex())

                
    # def path_leaf(self, path):
    #     head, tail = ntpath.split(path)
    #     return tail or ntpath.basename(head)
        
    # meant for alternative dcc who loads layout files from their gscl file configuration setting
    def openLayoutFileFromPath(self, filePath, newTabName, focus=True):
        if self.layoutEditor is None  or self.blockSignalsToLayoutEditor:
            return

        # we block signals TO layout editor : we want to be able to request everything from layoutEditor->Maya that need to be requested at load
        #such as poptools, entityTypes, etc
        if len(filePath) > 0:
            #move to the correct tab, or create a new one if none exist with the desired name
            foundTab = False
            for tabIndex in range(self.layoutEditor.editorTabWidget.count()):
                tabFilePath = self.layoutEditor.layoutViewTabWidgets[tabIndex].mainNodz.scene().userData['currentFilePath']
                if tabFilePath == filePath:
                    # update the tab name, in case we reloaded a cache instead of that file
                    currentTabText = self.layoutEditor.editorTabWidget.tabText(tabIndex)
                    if (currentTabText != newTabName):
                        self.renameCacheProxyTab(currentTabText, newTabName)

                    if (focus):
                        self.layoutEditor.editorTabWidget.setCurrentIndex(tabIndex)
                        
                    foundTab = True
            if not foundTab:
                # parse file name 
                # filename = self.path_leaf(filePath)
                # self.blockSignalsFromLayoutEditor = True  # block layoutGraphChanged event, we are sending another one when loaded below, else we will send an empty graph in the mean time
                self.layoutEditor.newTab(newTabName)
                self.layoutEditor.loadGolaemLayoutFile(filePath, focus=True, autoLayout=False)
                self.layoutEditor.getCurrentMainNodz().scene().userData['currentFilePath'] = filePath
                self.layoutEditor.getCurrentTabWidget().setEditEnabled(True)
                self.layoutEditor.setEditedNode(None, None)  # reset the attribute editor

                self.layoutEditor.clearUndoStack(self.layoutEditor.getCurrentTabIndex())
                self.layoutEditor.stackUndo(self.layoutEditor.getCurrentTabIndex())

    def renameCacheProxyTab(self, oldCacheProxyName, newCacheProxyName):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return

        if len(oldCacheProxyName)>0:
            for tabIndex in range(self.layoutEditor.editorTabWidget.count()):
                cacheProxyName = self.layoutEditor.getLayoutNameForTab(tabIndex)
                if cacheProxyName == oldCacheProxyName:
                    thisTabViewWidget = self.layoutEditor.layoutViewTabWidgets[tabIndex]
                    thisTabViewWidget.layoutName = newCacheProxyName
                    thisTabViewWidget.updateBreadcrumb()
                    if (self.layoutEditor.isMainNodz(thisTabViewWidget.editedNodz)):
                        self.layoutEditor.editorTabWidget.setTabText(tabIndex, self.layoutEditor.getLayoutNameForTab(tabIndex))
                break

    def saveCacheProxyTab(self, cacheProxyName):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return

        # do not block signals to make sure the file path is written properly in the cache proxy node
        # self.blockSignalsFromLayoutEditor = True
        if len(cacheProxyName) > 0:
            for tabIndex in range(self.layoutEditor.editorTabWidget.count()):
                tabName = self.layoutEditor.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    theNodz = self.layoutEditor.layoutViewTabWidgets[tabIndex].mainNodz
                    self.saveCacheProxyNodz(theNodz, tabIndex)
                    break
        # self.blockSignalsFromLayoutEditor = False

    def saveCacheProxyNodz(self, theNodz, tabIndex):
        if theNodz is None:
            print("Error: no tab selected")
            return

        if self.layoutEditor is None:
            return

        filePath = ''

        if 'currentFilePath' in theNodz.scene().userData:
            filePath = theNodz.scene().userData['currentFilePath']
        if 'currentFilePath' not in theNodz.scene().userData or len(filePath) == 0:
            tabName = self.layoutEditor.getLayoutNameForTab(tabIndex) # was  .editorTabWidget.tabText(
            filePath = self.openLayoutFile(True, tabName)
            theNodz.scene().userData['currentFilePath'] = filePath
        if(len(filePath)>0):
            self.layoutEditor.saveGolaemLayoutFile(theNodz, tabIndex, filePath)

    def closeCacheProxyTab(self, cacheProxyName="", saveBeforeClose=False):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return

        # do not block signals to make sure the file path is written properly in the cache proxy node
        # self.blockSignalsFromLayoutEditor = True

        if len(cacheProxyName)>0:
            if self.layoutEditor is not None:
                for tabIndex in range(self.layoutEditor.editorTabWidget.count()):
                    tabName = self.layoutEditor.getLayoutNameForTab(tabIndex)
                    if tabName == cacheProxyName:
                        if saveBeforeClose:
                            theNodz = self.layoutViewTabWidgets[tabIndex].mainNodz
                            self.saveCacheProxyNodz(theNodz, tabIndex)
                        self.layoutEditor.on_tabCloseRequested(tabIndex)
                        break

        # self.blockSignalsFromLayoutEditor = False

    def addOrEditLayoutTransformation(self, cacheProxyName, entitiesIDsList, transformationNodeTypeName, parameterName, parameterValue, frame, mode):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return None

        self.openCacheProxy(cacheProxyName)

        # block signals TO layout in case the layout need a list of poptool or such things
        self.blockSignalsFromLayoutEditor = True
        nodeInst = self.layoutEditor.addOrEditLayoutTransformation(cacheProxyName, entitiesIDsList, transformationNodeTypeName, parameterName, parameterValue, frame, mode)
        self.blockSignalsFromLayoutEditor = False
        return nodeInst

    def sendLayoutUnreal(self, cacheProxyName, layoutJSON, dirtyNodeIds, doRefreshAssets):
        if (usingUnreal):
            editorLevelLib = unreal.EditorLevelLibrary()            
            editorWorld = editorLevelLib.get_editor_world()
            cacheNameElements = cacheProxyName.split(' ')  # cacheElement[0] = proxy name, [1] is index
            myGolaemCache = editorLevelLib.get_actor_reference('PersistentLevel.{}'.format(cacheNameElements[0]))
            if (myGolaemCache is not None):
                myGolaemCache.reload_layout(int(cacheNameElements[1]), layoutJSON, dirtyNodeIds, doRefreshAssets)

    def sendLayoutInternal(self, cacheProxyName, layoutJSON, dirtyNodeIds, doRefreshAssets):
        if (usingMaya):
            cmds.glmLayoutTool(cacheProxy=cacheProxyName, layoutJSON=layoutJSON, dirtyLayoutNodeID=dirtyNodeIds, dirtyAssetsRepartition=doRefreshAssets)
        elif (usingUnreal):
            self.sendLayoutUnreal(cacheProxyName, layoutJSON, dirtyNodeIds, doRefreshAssets)
        else:
            print('sendLayout: Call a glmLayoutTool that refresh the display.')

    # called in crowd code after addOrEditTransformation to avoid sending layout several times
    def sendLayout(self, cacheProxyName, doRefreshAssets):
        if len(cacheProxyName)>0 and  self.layoutEditor is not None:
            for tabIndex in range(self.layoutEditor.editorTabWidget.count()):
                tabName = self.layoutEditor.getLayoutNameForTab(tabIndex)
                if tabName == cacheProxyName:
                    # self.blockSignalsToLayoutEditor = True
                    layoutInfo = self.layoutEditor.buildGolaemLayoutFile(
                        self.layoutEditor.layoutViewTabWidgets[tabIndex].mainNodz, tabIndex)
                    layoutJSON = json.dumps(layoutInfo,
                                    sort_keys = False,
                                    indent = 2,
                                    ensure_ascii=False)
                    if (not self.layoutEditor.isCurrentTabOpenViaOpenAction()):
                        self.sendLayoutInternal(cacheProxyName, layoutJSON, self.compoundDirtyLayoutNodeIDs, doRefreshAssets)
                        self.compoundDirtyLayoutNodeIDs = list()
                    # self.blockSignalsToLayoutEditor = True
                    break

    def editLayoutParameter(self, cacheProxyName, parameterName, parameterType, parameterValue):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return

        self.openCacheProxy(cacheProxyName)

        # block signals TO layout in case the layout need a list of poptool or such things
        self.blockSignalsFromLayoutEditor = True
        self.layoutEditor.editLayoutParameter(cacheProxyName, parameterName, parameterType, parameterValue)
        self.blockSignalsFromLayoutEditor = False

    def editLayoutNodeAttribute(self, cacheProxyName, nodeID, attributeName, keyFrames, keyValues):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return

        self.openCacheProxy(cacheProxyName)

        # block signals TO layout in case the layout need a list of poptool or such things
        prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
        self.blockSignalsToLayoutEditor = True
        self.layoutEditor.editLayoutNodeAttribute(cacheProxyName, nodeID, attributeName, keyFrames, keyValues, True)
        self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

    def editLayoutPostureNode(self, cacheProxyName, nodeID, boneIndex, boneLabel, transformLabel, transformKeyFrames, transformValues, valueType, operationMode, overrideExistingKeyframes=False):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return

        self.openCacheProxy(cacheProxyName)

        # block signals TO layout in case the layout need a list of poptool or such things
        prevBlockSignalsToLayoutEditor = self.blockSignalsToLayoutEditor
        self.blockSignalsToLayoutEditor = True
        self.layoutEditor.editLayoutPostureNode(cacheProxyName, nodeID, boneIndex, boneLabel, transformLabel, transformKeyFrames, transformValues, valueType, operationMode, overrideExistingKeyframes)
        self.blockSignalsToLayoutEditor = prevBlockSignalsToLayoutEditor

    def setHighlightedLayoutNodesIDs(self, cacheProxyName, layoutNodeIDsList):
        if self.layoutEditor is None or self.blockSignalsToLayoutEditor:
            return

        self.openCacheProxy(cacheProxyName)
        self.layoutEditor.setHighlightedLayoutNodesIDs(cacheProxyName, layoutNodeIDsList)

from __future__ import print_function
#**************************************************************************
#*                                                                        *
#*  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
#*                                                                        *
#**************************************************************************

import os
import copy
from glm.Qtpy.Qt import QtCore

usingMaya = True
try:
    import maya.cmds as cmds
    import glm.layout.layoutEditorMaya as layoutEditorMaya
    layoutEditorForAPI = layoutEditorMaya.getTheLayoutEditorMayaInstance()
except:
    import glm.layout.layoutEditorUtils as layoutEditorUtils
    layoutEditorForAPI = layoutEditorUtils.getTheLayoutEditorInstance()

def openLayoutFile(filePath):
    return layoutEditorForAPI.openLayoutFile(filePath)

def listLayoutParameters(layoutFileHandle, parameterNameList):
    if (layoutFileHandle is None):
        print("Error : layoutFileHandle is None")
        return False
    mainNodz = layoutFileHandle.mainNodz
    for layoutParam in mainNodz.scene().userData.items():
        parameterNameList.append(layoutParam[0])
    return True

def getLayoutParameter(layoutFileHandle, parameterName):
    if (layoutFileHandle is None):
        print("Error : layoutFileHandle is None")
        return False

    mainNodz = layoutFileHandle.mainNodz
    if parameterName in mainNodz.scene().userData:
        return mainNodz.scene().userData[parameterName]
    else:
        print("Layout Parameter not found :{}".format(parameterName))
        return None

def setLayoutParameter(layoutFileHandle, parameterName, parameterValue):
    if (layoutFileHandle is None):
        print("Error : layoutFileHandle is None")
        return False

    mainNodz = layoutFileHandle.mainNodz
    if parameterName in mainNodz.scene().userData:
        mainNodz.scene().userData[parameterName] = parameterValue
        return True
    else:
        return False

def getRootId(layoutFileHandle,  groupNodeId=None):
    if (layoutFileHandle is None):
        print("Error : layoutFileHandle is None")
        return False

    graphNodz = layoutFileHandle.mainNodz
    if (groupNodeId is not None):
        if (groupNodeId in layoutFileHandle.childrenNodz):
            graphNodz = layoutFileHandle.childrenNodz[groupNodeId]
        else:
            print("Error - getRootId() did not find groupNodeId {}".format(groupNodeId))
            return False

    if 'rootTransformId' in graphNodz.scene().userData:
        return graphNodz.scene().userData['rootTransformId']
    else:
        print("Error: rootTransformId not found in graph parameters")
        return (-1)

def getNodzFromNode(layoutFileHandle, requestedNodeInst):
    """
    INTERNAL USE ONLY
    """
    if (layoutFileHandle is None):
        print("Error : layoutFileHandle is None")
        return False

    # find back main Nodz
    mainNodz = layoutFileHandle.mainNodz
    for node in mainNodz.scene().nodes:
        #handle node, attributes are stores in userData, so will be saved as well
        nodeInst = mainNodz.scene().nodes[node]
        if (requestedNodeInst == nodeInst):
            return mainNodz
    for childrenNodz in layoutFileHandle.childrenNodz.items():
        currentNodz = childrenNodz[1]
        for node in currentNodz.scene().nodes:
            #handle node, attributes are stores in userData, so will be saved as well
            nodeInst = currentNodz.scene().nodes[node]
            if (requestedNodeInst == nodeInst):
                return currentNodz
    print("Error : getNodzFromNode() - requestedNodeInst is not found in all Nodz graphs")
    return None
    
def getNodzFromGroupId(layoutFileHandle, groupNodeId=None):
    """
    INTERNAL USE ONLY
    """
    if groupNodeId is None:
        return layoutFileHandle.mainNodz
    else:
        for childrenNodz in layoutFileHandle.childrenNodz.items():
            if (childrenNodz[1].scene().userData['groupId'] == groupNodeId):
                return childrenNodz[1]
        return None

def getNodeParameter(nodeInst, parameterName):
    """
    INTERNAL USE ONLY
    """
    if nodeInst is not None:
        for item in nodeInst.userData.items():
            if item[0] == parameterName:
                return item[1]
    if nodeInst is None:
        print("getNodeParameter Error: nodeInst is None")
    return None

def setNodeParameter(nodeInst, parameterName, parameterValue):
    """
    INTERNAL USE ONLY
    """
    if nodeInst is not None:
        for item in nodeInst.userData.items():
            if item[0] == parameterName:
                nodeInst.userData[parameterName] = parameterValue
                return True
    print("Error : nodeInst is None or parameter {} is not found".format(parameterName))
    return False

def getNodeById(layoutFileHandle,  nodeID):
    """
    getNodeById() works on current tab index, for batch we work on a single tab
    """
    if (layoutFileHandle is None):
        print("Error : layoutFileHandle is None")
        return False

    # find back main Nodz
    mainNodz = layoutFileHandle.mainNodz

    # look for node ID in main Nodz
    for node in mainNodz.scene().nodes:
        currentNodeInst = mainNodz.scene().nodes[node]
        if currentNodeInst.userData['ID'] == nodeID:
            return currentNodeInst

    # look for node ID in chidlren Nodz
    for childNodz in layoutFileHandle.childrenNodz.items():
        for node in childNodz[1].scene().nodes:
            currentNodeInst = childNodz[1].scene().nodes[node]
            if currentNodeInst.userData['ID'] == nodeID:
                return currentNodeInst

    print("Error : nodeID {} not found in all nodz graph".format(nodeID))
    return None

def setRootId(layoutFileHandle, rootNodeId, groupNodeId=None):
    if layoutFileHandle is None:
        print("Error : layoutFileHandle is None")
        return False

    rootNodeInst = getNodeById(layoutFileHandle, rootNodeId)
    if (rootNodeInst is None):
        return False
   
    containerNodz = getNodzFromNode(layoutFileHandle, rootNodeInst)
    if (containerNodz is None):
        return False

    layoutEditorForAPI.setRootNode(containerNodz, rootNodeInst)
    return True

def listNodeIds(layoutFileHandle):
    nodeId = getRootId(layoutFileHandle)
    allNodeIds = list()
    nodesToProcess = list()
    nodesToProcess.append(nodeId)

    while(len(nodesToProcess)):
        nodeId = nodesToProcess.pop(0)
        nodeInst = getNodeById(layoutFileHandle, nodeId)
        allNodeIds.append(nodeId)
        #print(getNodeName(nodeInst))
        # if group, get inside nodes
        if (getNodeTypeName(nodeInst) is not None):
            if (getNodeTypeName(nodeInst) == 'Group'):
                inNodeId = getRootId(layoutFileHandle , nodeId)
                nodesToProcess.append(inNodeId)
        # also get previous 
        inConnections = list()
        listIncomingConnections(layoutFileHandle, nodeInst, inConnections)
        nodesToProcess = nodesToProcess + inConnections
    return allNodeIds

def listNodeAttributes(operatorNode, attributeNameList):
    if (operatorNode is not None):
        attributes = None
        for item in operatorNode.userData.items():
            if item[0] == 'attributes':
                attributes = item[1]
        if attributes is not None:
            # create the group Nodz
            for attribute in attributes:
                nodeAttributeName = None
                for attributeItem in attribute.items():
                    if attributeItem[0] == "name":
                        nodeAttributeName = attributeItem[1]
                attributeNameList.append(nodeAttributeName)
            return True
    print("Error : operatorNode is None")        
    return False

def getNodeAttribute(operatorNode, attributeName, keyFrames, keyValues):
    if (operatorNode is not None):
        attributes = None
        for item in operatorNode.userData.items():
            if item[0] == 'attributes':
                attributes = item[1]
        if attributes is not None:
            # create the group Nodz
            for attribute in attributes:
                nodeAttributeName = None
                nodeAttributeValue = None
                nodeAttributeFrame = None
                for attributeItem in attribute.items():
                    if attributeItem[0] == "name":
                        nodeAttributeName = attributeItem[1]
                    elif attributeItem[0] == "values":
                        nodeAttributeValue = attributeItem[1]
                    elif attributeItem[0] == "frames":
                        nodeAttributeFrame = attributeItem[1]

                if (nodeAttributeName == attributeName):
                    keyValues[:] = nodeAttributeValue
                    keyFrames[:] = nodeAttributeFrame
                    return True
    print("Error : operatorNode is None or attribute {} is not found".format(attributeName))
    return False

def setNodeAttribute(operatorNode, attributeName, keyFrames, keyValues):
    if (operatorNode is not None):
        attributes = None
        for item in operatorNode.userData.items():
            if item[0] == 'attributes':
                attributes = item[1]
        if attributes is not None:
            # create the group Nodz
            for attribute in attributes:
                nodeAttributeName = None
                for attributeItem in attribute.items():
                    if attributeItem[0] == "name":
                        nodeAttributeName = attributeItem[1]

                if (nodeAttributeName == attributeName):
                    attribute["frames"] = keyFrames
                    attribute["values"] = keyValues
                    return True
    print("Error : operatorNode is None or attribute {} is not found".format(attributeName))
    return False

def setAllNodesAttribute(fileHandle, attributeName, keyFrames, keyValues):
    allNodeIds = listNodeIds(fileHandle)
    for nodeId in allNodeIds:
        nodeInst = getNodeById(fileHandle, nodeId)
        if (getNodeTypeName(nodeInst) is not None):
            attrList = list()
            if (listNodeAttributes(nodeInst, attrList)):
                if (attributeName in attrList):
                    setNodeAttribute(nodeInst, attributeName, keyFrames, keyValues)

def listNodeParameters(nodeInst, parameterNameList):
    if (nodeInst is not None):
        for item in nodeInst.userData.items():
            if item[0] != "nodes" and item[0] != "connections":
                parameterNameList.append(item[0])

### parameters GETTERS

def getNodeID(nodeInst):
    return getNodeParameter(nodeInst, "ID")

def getNodeActive(nodeInst):
    return getNodeParameter(nodeInst, "active")

def getNodeName(nodeInst):
    return getNodeParameter(nodeInst, "name")

def getNodeTypeName(nodeInst):
    return getNodeParameter(nodeInst, "type_name")

def getNodeType(nodeInst):
    return getNodeParameter(nodeInst, "type")

def getNodePos(nodeInst):
    return getNodeParameter(nodeInst, "GUI_pos")

def getNodeEntities(nodeInst):
    return getNodeParameter(nodeInst, "entities")

### parameters SETTERS

def setNodeActive(nodeInst, active):
    return setNodeParameter(nodeInst, "active", active)

def setNodeName(nodeInst, name):
    return setNodeParameter(nodeInst, "name", name)

def setNodePos(nodeInst, pos):
    return setNodeParameter(nodeInst, "GUI_pos", pos)

def setNodeEntities(nodeInst, entities):
    return setNodeParameter(nodeInst, "entities", entities)

### END

def listIncomingConnections(layoutFileHandle, nodeInst, incomingNodeIds):
    if nodeInst is None:
        print("Error: nodeInst is None")
        return
    currentNodz = getNodzFromNode(layoutFileHandle, nodeInst)
    if (currentNodz is None):
        print("Error: cannot find nodz parent of this node")
        return
    for socket in nodeInst.sockets:
        socketInst = nodeInst.sockets[socket]
        for connection in socketInst.connections:
            if (connection.plugNode is not None and connection.socketNode is not None):
                srcNodeName  = connection.plugNode
                srcNodeInst = currentNodz.scene().nodes[srcNodeName]
                srcId = srcNodeInst.userData['ID']
                incomingNodeIds.append(srcId)

def listOutgoingConnections(layoutFileHandle, nodeInst, outgoingNodeIds):
    if nodeInst is None:
        print("Error: nodeInst is None")
        return
    currentNodz = getNodzFromNode(layoutFileHandle, nodeInst)
    if (currentNodz is None):
        print("Error: cannot find nodz parent of this node")
        return
    for plug in nodeInst.plugs:
        plugInst = nodeInst.plugs[plug]
        for connection in plugInst.connections:
            if (connection.plugNode is not None and connection.socketNode is not None):
                dstNodeName = connection.socketNode
                dstNodeInst = currentNodz.scene().nodes[dstNodeName]
                dstId = dstNodeInst.userData['ID']
                outgoingNodeIds.append(dstId)

def connect(layoutFileHandle, fromNodeId, toNodeId):
    if (layoutEditorForAPI is None or layoutEditorForAPI.getCurrentMainNodz() is None):
        print("Error : LayoutEditorAPI need to open a Layout before requesting data")
        return

    fromNode = getNodeById(layoutFileHandle, fromNodeId)
    toNode = getNodeById(layoutFileHandle, toNodeId)

    if (fromNode == None or toNode == None):
        print("Error : fromNodeID or toNodeId do not exist")
        return False
    
    fromNodz = getNodzFromNode(layoutFileHandle, fromNode)
    toNodz = getNodzFromNode(layoutFileHandle, fromNode)

    if (fromNodz == None or fromNodz != toNodz):
        print("Error : fromNodeID and toNodeId do not belong to same group / graph")
        return False

    fromNodz.createConnection(fromNode.name, fromNode.attrs[0], toNode.name, toNode.attrs[0])
    return True
            
def disconnect(layoutFileHandle, fromNodeId, toNodeId):
    if (layoutEditorForAPI is None or layoutEditorForAPI.getCurrentMainNodz() is None):
        print("Error : LayoutEditorAPI need to open a Layout before requesting data")
        return

    # must find a matching connection and remove it :
    fromNode = getNodeById(layoutFileHandle, fromNodeId)
    if (fromNode is None):
        print("Error : fromNodeID or toNodeId do not exist")
        return

    currentNodz = getNodzFromNode(layoutFileHandle, fromNode)
    if (currentNodz is None):
        print("Error : fromNodeID and toNodeId do not belong to same group / graph")
        return

    # list all from node out going connections :
    for plug in fromNode.plugs:
        plugInst = fromNode.plugs[plug]
        for connection in plugInst.connections:
            if (connection.plugNode is not None and connection.socketNode is not None):
                dstNodeName = connection.socketNode
                dstNodeInst = currentNodz.scene().nodes[dstNodeName]
                dstId = dstNodeInst.userData['ID']
                if (dstId == toNodeId):
                    connection._remove()
                    return True

    print("Error : did not find a connection matching from {} to {}".format(fromNodeId, toNodeId))
    return False

def createOperator(layoutFileHandle, operatorTypeName, insertAfterNode=None, parentGroupNodeId=None):
    if (layoutFileHandle is None):
        print("Error : layoutFileHandle is None")
        return None

    editedNodz = getNodzFromGroupId(layoutFileHandle, parentGroupNodeId)
    # rootId = getRootId(parentGroupNodeId)  # for default if insertAfterId is None
    pos = [0, 0]
    operatorPos = QtCore.QPointF(pos[0], pos[1])
    if (insertAfterNode is not None):
        if (getNodzFromNode(layoutFileHandle, insertAfterNode) != editedNodz):
            print("insertAfterId does not exist, or is not in same group")
            return None
        else:
            pos = getNodeParameter(insertAfterNode, "GUI_pos")
            nodePositionOffset = QtCore.QPointF(200, 9)
            operatorPos = QtCore.QPointF(pos[0], pos[1]) + 1.5 * nodePositionOffset # hard offset after linked node
    
    createdNode = layoutEditorForAPI.GolaemLayoutNodeCreator(
        editedNodz, operatorTypeName, operatorPos)
    if (createdNode is not None):
        if(insertAfterNode is not None):
            # connect insertAfter to currentNode            
            createdNodeId = getNodeParameter(createdNode, "ID")
            insertAfterId = getNodeParameter(insertAfterNode, "ID")
            connect(layoutFileHandle, insertAfterId, createdNodeId)         
        
            # link previous node with current. if previous was root, set current as root
            rootId = getRootId(layoutFileHandle, parentGroupNodeId)
            if (insertAfterId == rootId):
                setRootId(layoutFileHandle, createdNode)

    return createdNode
    
def createSelector(layoutFileHandle, entities, insertAfterId=None, parentGroupNodeId=None):
    createdSelector = createOperator(layoutFileHandle, "EntitySelector", insertAfterId, parentGroupNodeId)
    if (createdSelector is not None):
        setNodeParameter(createdSelector, "entities", entities)
    return createdSelector

def deleteNode(nodeToDelete):
    if nodeToDelete is not None:
        nodeToDelete._remove()
        return True
    return False

def saveLayoutFile(layoutFileHandle, newPath = None):
    if (layoutFileHandle is None):
        print("Error : layoutFileHandle is None")
        return None

    currentNodz = layoutEditorForAPI.getCurrentMainNodz()
    if (newPath is not None):
        currentNodz.scene().userData['currentFilePath'] = newPath
    filePath = currentNodz.scene().userData['currentFilePath']
    if (len(filePath) > 0):
        layoutEditorForAPI.saveGolaemLayoutFile(currentNodz, 0, filePath)
    layoutEditorForAPI.on_tabCloseRequested(
        layoutEditorForAPI.getCurrentTabIndex())

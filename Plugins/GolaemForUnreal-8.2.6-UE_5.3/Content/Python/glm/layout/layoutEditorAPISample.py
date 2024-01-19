from __future__ import print_function

# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
# *                                                                        *
# **************************************************************************

from builtins import range
import os
import copy
import traceback
from glm.Qtpy.Qt import QtWidgets

from glm.layout.layout import *

###############################################################################
# Put user batch commands after this lines, or after importing this file
###############################################################################


# example
def processLayoutFiles(filePaths):
    errorCode = 0
    try:
        for filePath in filePaths:
            print("processing file {}".format(filePath))
            fileHandle = openLayoutFile(filePath)
            if fileHandle is not None:

                # get current Root Node Id for main graph
                rootId = getRootId(fileHandle)
                print("rootId={}".format(rootId))

                # get current Root Node from Id (to be able to link next nodes)
                previousRootNode = getNodeById(fileHandle, rootId)

                # list all layout parameters
                layoutParameters = list()
                listLayoutParameters(fileHandle, layoutParameters)
                for i in range(0, len(layoutParameters)):
                    layoutParameterValue = getLayoutParameter(fileHandle, layoutParameters[i])
                    print("layout parameter {}: {}={}".format(i, layoutParameters[i], layoutParameterValue))

                # create a selector, linked after root and automatically set as root instead
                scaleSelectorNode = createSelector(fileHandle, "char(0)", previousRootNode)

                # create a Scale operator, linked after selector and automatically set as root instead (case sensitive ! operator type names are uppercase for first letter)
                scaleOperatorNode = createOperator(fileHandle, "Scale", scaleSelectorNode)

                # list all scale node parameters
                scaleNodeParameters = list()
                print("scale ID: {}".format(getNodeID(scaleOperatorNode)))
                print("scale name: {}".format(getNodeName(scaleOperatorNode)))
                print("scale type: {}".format(getNodeType(scaleOperatorNode)))
                print("scale type_name: {}".format(getNodeTypeName(scaleOperatorNode)))
                print("scale GUI_pos: {}".format(getNodePos(scaleOperatorNode)))
                print("scale active: {}".format(getNodeActive(scaleOperatorNode)))
                print("scale ID: {}".format(getNodeID(scaleOperatorNode)))
                print("scale selector entities: {}".format(getNodeEntities(scaleSelectorNode)))

                # test bad taget
                print("scale bad entities: {}".format(getNodeEntities(scaleOperatorNode)))
                print("scale bad type_name: {}".format(getNodeTypeName(scaleSelectorNode)))

                # listNodeParameters(
                #     scaleOperatorNode, scaleNodeParameters)
                # for i in range(0, len(scaleNodeParameters)):
                #     print("scale node parameters list {} : {}".format(
                #         i, scaleNodeParameters[i]))

                # list all scale node attributes
                scaleNodeAttributes = list()
                listNodeAttributes(scaleOperatorNode, scaleNodeAttributes)
                for i in range(0, len(scaleNodeAttributes)):
                    print("scale node attribute list {} : {}".format(i, scaleNodeAttributes[i]))

                # modify scale value of Scale operator (case sensitive ! operator type names are uppercase for first letter)
                setNodeAttribute(scaleOperatorNode, "scale", [], [[[2, 2, 2]]])

                # modify pivot value of Scale operator
                setNodeAttribute(scaleOperatorNode, "pivot", [], [[[10, 0.5, 0]]])

                # create a new group after scale operator
                groupOperatorNode = createOperator(fileHandle, "Group", scaleOperatorNode)

                # get group ID to be able to parent nodes to it
                groupOperatorId = getNodeParameter(groupOperatorNode, "ID")

                # create a translate selector, placed into the created group, not chained to any node yet (first of the group)
                translateSelectorNode = createSelector(fileHandle, "2001", None, groupOperatorId)

                # create a Translate operator chained after its selector
                translateOperatorNode = createOperator(fileHandle, "Translate", translateSelectorNode, groupOperatorId)

                # set the translate attribute of the Translate operator
                setNodeAttribute(translateOperatorNode, "translate", [], [[[10, 0, 0]]])

                # get translate selector and operator IDs to play with connections
                translateSelectorId = getNodeParameter(translateSelectorNode, "ID")
                translateOperatorId = getNodeParameter(translateOperatorNode, "ID")

                # disconnect translate operator from its selector
                disconnect(fileHandle, translateSelectorId, translateOperatorId)

                # disable the translate operator
                setNodeParameter(translateOperatorNode, "active", 0)

                # create a selector in group, chained after translate operator
                killSelectorNode = createSelector(fileHandle, "1001", translateOperatorNode, groupOperatorId)

                # get kill ID to play with its connections
                killSelectorId = getNodeParameter(killSelectorNode, "ID")

                # create a kill operator in group, chained after kill selector
                killOperatorNode = createOperator(fileHandle, "Kill", killSelectorNode, groupOperatorId)

                # get kill ID to play with its connections
                killOperatorId = getNodeParameter(killOperatorNode, "ID")

                # connect translate selector to kill selector
                connect(fileHandle, translateSelectorId, killSelectorId)

                # set the group root ID to the kill operator
                setRootId(fileHandle, killOperatorId, groupOperatorId)

                # list incoming connections to the group node
                incomingConnectionsList = list()
                listIncomingConnections(fileHandle, groupOperatorNode, incomingConnectionsList)

                # list outgoing connections to the group node
                outgoingConnectionsList = list()
                listOutgoingConnections(fileHandle, groupOperatorNode, outgoingConnectionsList)

                # outside of the group, link group to a frameOffset (selector and operator)
                frameOffsetSelectorNode = createSelector(fileHandle, "*", groupOperatorNode)
                frameOffsetOperatorNode = createOperator(fileHandle, "FrameOffset", frameOffsetSelectorNode)
                setNodeAttribute(frameOffsetOperatorNode, "frameOffsetNoise", [], [[5.0]])
                setNodeAttribute(frameOffsetOperatorNode, "randomSeed", [], [[123456]])

                # list incoming connections to the group node
                incomingConnectionsList = []
                listIncomingConnections(fileHandle, groupOperatorNode, incomingConnectionsList)

                # list outgoing connections to the group node
                outgoingConnectionsList = []
                listOutgoingConnections(fileHandle, groupOperatorNode, outgoingConnectionsList)

                # delete last set node
                deleteNode(frameOffsetOperatorNode)

                # We have deleted the current root node of the main graph, need to set it to the previous node
                frameOffsetSelectorId = getNodeParameter(frameOffsetSelectorNode, "ID")
                setRootId(fileHandle, frameOffsetSelectorId)

                currentFilePath = getLayoutParameter(fileHandle, "currentFilePath")
                currentFilePathModified = "{}_modified.gscl".format(currentFilePath)

                saveLayoutFile(fileHandle, currentFilePathModified)
    except:
        traceback.print_exc()
        errorCode = 1
    return errorCode

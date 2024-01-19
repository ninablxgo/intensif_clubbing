from __future__ import print_function

# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A.  All Rights Reserved.                       *
# *                                                                        *
# **************************************************************************

# **************************************************************************
#! \file QT Utils
#  \brief QT related functions
# **************************************************************************

from future import standard_library

standard_library.install_aliases()
from builtins import range
from glm.Qtpy.Qt import QtWidgets, QtCompat
from pydoc import locate

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


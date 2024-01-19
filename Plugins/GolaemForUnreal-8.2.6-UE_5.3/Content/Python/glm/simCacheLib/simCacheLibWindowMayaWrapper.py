#**************************************************************************
#*                                                                        *
#*  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
#*                                                                        *
#**************************************************************************

from glm import simCacheUtils as scutils
from glm.ui import windowMayaWrapper


#**********************************************************************
#
# SimCacheLibWindowWrapper
# Maya wrapper for SimCacheLibWindow
#
#**********************************************************************
class SimCacheLibWindowMayaWrapper(windowMayaWrapper.WindowMayaWrapper):
    #******************************************************************
    # Specific
    #******************************************************************

    #------------------------------------------------------------------
    # Returns the app stylesheet
    #------------------------------------------------------------------
    def getStyleSheet(self):
        return 'QWidget#itemLibList { background-color: #444444 ; } QWidget#itemLib { background-color: #333333 ; border: 1px solid #343434 ; padding: 3px ; } QWidget#itemLib:hover { background-color: #597b9b ; }'

    #------------------------------------------------------------------
    # Updates the item snapshot and returns it
    #------------------------------------------------------------------
    def updateItemSnapshot(self, item):
        return scutils.updateItemSnapshot(item)

    #------------------------------------------------------------------
    # Create a sim cache proxy node, fills it from item and returns it
    #------------------------------------------------------------------
    def createSimCacheProxyFromItem(self, lib, itemIdx):
        item = lib.getLibItemAt(itemIdx)
        return scutils.createSimCacheProxyFromItem(item)

    #------------------------------------------------------------------
    # Create a sim cache proxy node, fills it from item and returns it
    #------------------------------------------------------------------
    def createSimCacheProxiesFromItem(self, lib, itemIdx):
        item = lib.getLibItemAt(itemIdx)
        return scutils.createSimCacheProxiesFromItem(item)

    #------------------------------------------------------------------
    # Updates a sim cache lib from a set of nodes and returns it
    #------------------------------------------------------------------
    def fillSimCacheLibFromProxies(self, lib, nodes):
        return scutils.fillSimCacheLibFromProxies(lib, nodes)

    #------------------------------------------------------------------
    # Return true if a button is available is this interface
    #------------------------------------------------------------------
    def isButtonAvailable(self, buttonName):
        return True

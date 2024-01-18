#**************************************************************************
#*                                                                        *
#*  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
#*                                                                        *
#**************************************************************************

from glm.ui import windowWrapper


#**********************************************************************
#
# SimCacheLibWindowWrapper
# Default wrapper for SimCacheLibWindow
#
#**********************************************************************
class SimCacheLibWindowWrapper(windowWrapper.WindowWrapper):
    #******************************************************************
    # Specific
    #******************************************************************

    #------------------------------------------------------------------
    # Returns the app stylesheet
    #------------------------------------------------------------------
    def getStyleSheet(self):
        return 'QWidget#itemLib { padding: 3px ; } QWidget#itemLib:hover { background-color: #597b9b ; }'

    #------------------------------------------------------------------
    # Updates the item snapshot and returns it
    #------------------------------------------------------------------
    def updateItemSnapshot(self, item):
        return item

    #------------------------------------------------------------------
    # Create a sim cache proxy node, fills it from item and returns it
    #------------------------------------------------------------------
    def createSimCacheProxyFromItem(self, lib, itemIdx):
        return ''

    #------------------------------------------------------------------
    # Create a sim cache proxy node, fills it from item and returns it
    #------------------------------------------------------------------
    def createSimCacheProxiesFromItem(self, lib, itemIdx):
        return []

    #------------------------------------------------------------------
    # Updates a sim cache lib from a set of nodes and returns it
    #------------------------------------------------------------------
    def fillSimCacheLibFromProxies(self, lib, nodes):
        return lib

    #------------------------------------------------------------------
    # Return true if a button is available is this interface
    #------------------------------------------------------------------
    def isButtonAvailable(self, buttonName):
        return True

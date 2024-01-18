# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
# *                                                                        *
# **************************************************************************

from builtins import str
from builtins import object
from glm import golaemUtils as gutils
from glm import callbackUtils as cbUtils
from glm import jsonUtils as jutils
import os
import sys
import base64

usingDevkit = True
try:
    import glm.devkit as devkit
except:
    usingDevkit = False

# **********************************************************************
#
# SimCacheLib
#
# **********************************************************************
class SimCacheLib(object):
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(self, libFile=""):
        # version
        # v1 first batch of data
        # v2 addition of itemName
        # v3 addition of nodeName
        self.libFileVersion = 3
        # Data Members
        self.items = []
        self.libFile = str(libFile)
        self.libFileDirty = False

    # ------------------------------------------------------------------
    # readLibFile
    # ------------------------------------------------------------------
    def readLibFile(self, libFile):
        if os.path.exists(libFile) is False:
            return
        fileDesc = open(libFile)
        fileContent = fileDesc.read()
        fileDesc.close()
        # parse content
        sc = SimCacheLib()
        sc = jutils.glmJsonLoad(fileContent, globals())
        self.items = sc.items
        self.libFile = str(libFile)
        # update if libFileVersion is different
        self.updateOnVersionChange()
        #callback
        cbUtils.executeUserCallback('sclReadLibFile', self.libFile)

    # ------------------------------------------------------------------
    # importLibFile
    # ------------------------------------------------------------------
    def importLibFile(self, libFile):
        fileDesc = open(libFile)
        fileContent = fileDesc.read()
        fileDesc.close()
        # parse content
        sc = SimCacheLib()
        sc = jutils.glmJsonLoad(fileContent, globals())
        # update if libFileVersion is different
        sc.updateOnVersionChange()
        self.items.extend(sc.items)
        self.libFileDirty = True
        #callback
        cbUtils.executeUserCallback('sclImportLibFile', (libFile + ';' + self.libFile))

    # ------------------------------------------------------------------
    # writeLibFile
    # ------------------------------------------------------------------
    def writeLibFile(self, libFile):
        fileContent = u""
        fileContent = jutils.glmJsonDump(self)
        fileDesc = open(libFile, "w")
        fileDesc.write(fileContent)
        fileDesc.close()
        self.libFile = str(libFile)
        self.libFileDirty = False
        #callback
        cbUtils.executeUserCallback('sclWriteLibFile', self.libFile)

    # ------------------------------------------------------------------
    # addLibItem
    # ------------------------------------------------------------------
    def addLibItem(self, item):
        if item.isInitialized() is True:
            self.items.append(item)
            self.libFileDirty = True
            #callback
            cbUtils.executeUserCallback('sclAddLibItem', (self.libFile + ';' + str(item.itemName)))

    # ------------------------------------------------------------------
    # removeLibItem
    # ------------------------------------------------------------------
    def removeLibItem(self, idItem):
        if idItem < len(self.items):
            itemName = self.items[idItem].itemName
            del self.items[idItem]
            self.libFileDirty = True
            #callback
            cbUtils.executeUserCallback('sclRemoveLibItem', (self.libFile + ';' + str(itemName)))

    # ------------------------------------------------------------------
    # getLibItemCount
    # ------------------------------------------------------------------
    def getLibItemCount(self):
        return len(self.items)

    # ------------------------------------------------------------------
    # getLibItemAt
    # ------------------------------------------------------------------
    def getLibItemAt(self, idItem):
        if idItem < len(self.items):
            return self.items[idItem]
        return None

    # ------------------------------------------------------------------
    # setLibItemAt
    # ------------------------------------------------------------------
    def setLibItemAt(self, idItem, item):
        if idItem < len(self.items):
            self.items[idItem] = item
            self.libFileDirty = True

    # ------------------------------------------------------------------
    # moveLibItemUp
    # ------------------------------------------------------------------
    def moveLibItemUp(self, idItem):
        newIdItem = max(0, idItem - 1)
        self.items[idItem], self.items[newIdItem] = self.items[newIdItem], self.items[idItem]
        self.libFileDirty = True

    # ------------------------------------------------------------------
    # moveLibItemDown
    # ------------------------------------------------------------------
    def moveLibItemDown(self, idItem):
        newIdItem = min(len(self.items) - 1, idItem + 1)
        self.items[idItem], self.items[newIdItem] = self.items[newIdItem], self.items[idItem]
        self.libFileDirty = True

    # ------------------------------------------------------------------
    # clear
    # ------------------------------------------------------------------
    def clear(self):
        del self.items[:]
        self.libFileDirty = True
        #callback
        cbUtils.executeUserCallback('sclClearLibItems', self.libFile)

    # ------------------------------------------------------------------
    # update on version change
    # ------------------------------------------------------------------
    def updateOnVersionChange(self):
        # v1 -> v2, addition of itemName in items, default it with cacheName values
        for item in self.items:
            if not item.itemName:
                item.itemName = item.cacheName
            if not item.nodeName:
                item.nodeName = ''


# **********************************************************************
#
# SimCacheLibItem
#
# **********************************************************************
class SimCacheLibItem(object):
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(self):
        self.itemName = u""
        self.nodeName = u""
        self.crowdFields = []
        self.cacheName = u""
        self.cacheDir = u""
        self.characterFiles = u""
        self.enableLayout = True
        self.layoutFile = u""
        self.sourceTerrain = u""
        self.destTerrain = u""
        self.image = u""
        self.nbEntities = 0
        self.startFrame = -1
        self.endFrame = 0
        self.tags = []

    # ------------------------------------------------------------------
    # Set the image
    # ------------------------------------------------------------------
    def setImage(self, imageFile):
        self.image = self.imageToString(imageFile)

    # ------------------------------------------------------------------
    # Returns true if initialized
    # ------------------------------------------------------------------
    def isInitialized(self):
        return self.nbEntities != 0

    # ------------------------------------------------------------------
    # Returns true if is in the filter
    # ------------------------------------------------------------------
    def isInFilter(self, filter):
        return (
            self.itemName.find(filter) != -1
            or self.nodeName.find(filter) != -1
            or self.cacheName.find(filter) != -1
            or any(filter in tag for tag in self.tags)
        )

    # ------------------------------------------------------------------
    # Returns true if their relative simulation file exist or not
    # ------------------------------------------------------------------
    def simCacheFilesExist(self):
        return self.firstSimCacheFilesExist() and self.characterFilesExist()

    def replaceEnvVars(self, sourcePath, startStr = '%', endStr= '%'):
        replacedPath = str(sourcePath)
        startPos = 0
        endPos = 0
        increment = 1
        currentDepth = 0
        for iPos in range(0, len(sourcePath)):
            increment = 1
            if replacedPath.startswith(startStr, iPos):
                if startStr != endStr or currentDepth == 0:
                    if currentDepth == 0:
                        startPos = iPos
                    increment = len(startStr)
                    currentDepth += 1
                    continue
			
            if replacedPath.startswith( endStr, iPos):
                currentDepth -= 1
                if currentDepth == 0:
                    endPos = iPos
                    stringToProcess = replacedPath[startPos + len(startStr) : endPos - startPos - len(startStr)]
                    stringToProcess = self.replaceEnvVars(stringToProcess, startStr, endStr)
                    varValue = os.getenv(stringToProcess)
                    replacedPath = replacedPath[0:startPos] + varValue + self.replaceEnvVars(replacedPath[endPos + len(endStr):], startStr, endStr)
                    break
                increment = len(endStr)
        return replacedPath

    def dirmap(self, sourcePath, mapFrom, mapTo):
        mappedPath = str(sourcePath)
        if mapFrom[0] == '^':
            # the rest of the string must be matched at the beginning
            mapFromRest = mapFrom[1:]
            if mappedPath.startswith(mapFromRest):
                mappedPath = mapTo + mappedPath[len(mapFromRest):]
        else:
            mappedPath = mappedPath.replace(mapFrom, mapTo)
        return mappedPath
    
    def correctPath(self, pathname):
        correctedPath = self.replaceEnvVars(pathname)
        return correctedPath.replace(os.path.sep, '/') # always work with /

    def findDirMapFile(self, filePath, dirmapRules):
        dirmappedFilePath = self.replaceEnvVars(filePath)
        fileExists = os.path.exists(dirmappedFilePath)
        iRule = 0
        while not fileExists and (iRule  + 1) < len(dirmapRules):
            dirmappedFilePath = self.dirmap(filePath, dirmapRules[iRule], dirmapRules[iRule + 1])
            fileExists = os.path.exists(dirmappedFilePath)
            iRule += 2

        if fileExists:
            correctedFilePath = self.correctPath(dirmappedFilePath)
        else:
            correctedFilePath = filePath
        return correctedFilePath

    # ------------------------------------------------------------------
    # Returns true if the first simulation cache frame exist
    # ------------------------------------------------------------------    
    def firstSimCacheFilesExist(self):
        dirMapEnv = os.getenv("GLM_DIRMAP")
        dirMapRules = str(dirMapEnv).split(';')
        dirMappedCacheDir = self.findDirMapFile(self.cacheDir, dirMapRules) # do not replace data in library without user awareness
        for crowdField in self.crowdFields:
            filePath = gutils.getSimulationCachePath(
                gutils.getExportedFilePrefix(dirMappedCacheDir, self.cacheName, crowdField), self.startFrame + 1
            )
            if os.path.isfile(filePath) is not True:
                return False
        return True

    # ------------------------------------------------------------------
    # Returns true if the first simulation cache frame exist
    # ------------------------------------------------------------------
    def characterFilesExist(self):
        dirMapEnv = os.getenv("GLM_DIRMAP")
        dirMapRules = str(dirMapEnv).split(';')
        for characterFile in self.characterFiles.split(";"):
            characterFile = self.findDirMapFile(characterFile, dirMapRules)
            # if usingDevkit:
            #     devkit.replaceEnvVars(gutils.convertStringForDevkit(characterFile))
            if os.path.isfile(characterFile) is not True:
                return False
        return True

    # ------------------------------------------------------------------
    # Nb Frames
    # ------------------------------------------------------------------
    def getNbFrames(self):
        return self.endFrame - self.startFrame + 1


    # ------------------------------------------------------------------
    # Open an image file and returns a string out of it
    # ------------------------------------------------------------------
    def imageToString(self, imagePath):
        with open(imagePath, "rb") as f:
            data = f.read()
            return base64.b64encode(data)


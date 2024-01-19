# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
# *                                                                        *
# **************************************************************************

from builtins import map
from builtins import bytes
from builtins import str
from builtins import range
from glm.Qtpy.Qt import QtCore, QtGui, QtWidgets
from glm import qtCoreUtils as qtcUtils
from functools import partial
from glm.simCacheLib import simCacheLib
import glm.simCacheLib.simCacheLibWindowWrapper as wrapper
import sys
import os
import fnmatch
import base64


# **********************************************************************
#
# SimCacheLibWindow
#
# **********************************************************************
class SimCacheLibWindow(QtWidgets.QMainWindow):
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(self, wrapper=wrapper.SimCacheLibWindowWrapper()):
        self.wrapper = wrapper
        parent = self.wrapper.getParentWindow()
        super(SimCacheLibWindow, self).__init__(parent)

        # Data Members
        self.tabWidget = QtWidgets.QTabWidget(self)
        self.footerLabel = QtWidgets.QLabel(self)
        self.libs = []
        self.imageSize = [200, 150]
        self.itemSize = [187, 252]
        self.nbItemPerLine = 4
        self.defaultPosAndSize = [[50, 50], [860, 600]]
        self.editItemWin = SimCacheLibEditWindow(self)

        # Init
        self.initUI()

    # ******************************************************************
    # UI Accessors
    # ******************************************************************

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def initUI(self):

        # Window properties
        iconsDir = self.wrapper.getIconsDir()
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Golaem Simulation Cache Library")
        self.setObjectName("glmSimulationCacheLibraryWnd")
        self.installEventFilter(self)
        self.restorePosAndSize()
        self.setWindowIcon(QtGui.QIcon(os.path.join(iconsDir, "buttonSimulationCacheLibrary.png").replace("\\", "/")))

        # Central Widget
        mainWidget = QtWidgets.QWidget(self)
        mainLayout = QtWidgets.QGridLayout()
        mainLayout.setHorizontalSpacing(0)
        mainLayout.setVerticalSpacing(0)
        mainWidget.setLayout(mainLayout)
        mainWidget.setStyleSheet(self.wrapper.getStyleSheet())
        self.setCentralWidget(mainWidget)

        # Menu Bar
        separatorWidget = QtWidgets.QLabel(self)
        separatorImage = QtGui.QPixmap(os.path.join(iconsDir, "editors", "smallSeparator.png").replace("\\", "/"))
        separatorWidget.setPixmap(separatorImage)

        rowIndex = 0
        menuBarLayout = QtWidgets.QGridLayout()
        mainLayout.addLayout(menuBarLayout, 0, 0)
        menuBarLayout.setHorizontalSpacing(0)
        menuBarLayout.setVerticalSpacing(0)
        if self.wrapper.isButtonAvailable("Create Library File"):
            menuBarLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "editors", "new.png").replace("\\", "/"), "Create Library File", 20, True, self.createNewTab, None
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Open Library File"):
            menuBarLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "editors", "open.png").replace("\\", "/"), "Open Library File", 20, True, self.openInNewTab, ""
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Import Library File"):
            menuBarLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "editors", "import.png").replace("\\", "/"), "Import Library File", 20, True, self.importInCurrentTab, ""
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Import All Library Files of a Directory"):
            menuBarLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "editors", "importDir.png").replace("\\", "/"),
                    "Import All Library Files of a Directory",
                    20,
                    True,
                    self.importDirInCurrentTab,
                    "",
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Save Library File"):
            menuBarLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "editors", "save.png").replace("\\", "/"), "Save Library File", 20, True, self.saveCurrentTab, None
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Save Library File As..."):
            menuBarLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "editors", "saveAs.png").replace("\\", "/"),
                    "Save Library File As...",
                    20,
                    True,
                    self.saveCurrentTabAs,
                    None,
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Refresh Library File"):
            menuBarLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "editors", "refresh.png").replace("\\", "/"),
                    "Refresh Library File",
                    20,
                    True,
                    self.refreshCurrentTab,
                    None,
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        menuBarLayout.addWidget(separatorWidget, 0, rowIndex)
        rowIndex += 1
        if self.wrapper.isButtonAvailable("Import from selected / scene Simulation Cache Proxy"):
            menuBarLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "libraryTool", "cacheImport.png").replace("\\", "/"),
                    "Import from selected / scene Simulation Cache Proxy",
                    20,
                    True,
                    self.addItemInCurrentTab,
                    None,
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        # menuBarLayout.addItem(QtWidgets.QSpacerItem(1000, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum), 0, rowIndex)
        menuBarLayout.setColumnStretch(rowIndex, 5000)
        rowIndex += 1
        menuBarLayout.addWidget(QtWidgets.QLabel("Filter: ", self), 0, rowIndex)
        rowIndex += 1
        filterLine = SimCacheLibFilterLineEdit(self)
        filterLine.setFixedWidth(150)
        menuBarLayout.addWidget(filterLine, 0, rowIndex)

        # Footer Bar
        footerBarLayout = QtWidgets.QGridLayout()
        mainLayout.addLayout(footerBarLayout, 2, 0)
        footerBarLayout.addWidget(self.footerLabel)

        # Tab
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.tabClosedEvent)
        self.tabWidget.currentChanged.connect(self.tabChangedEvent)
        mainLayout.addWidget(self.tabWidget, 1, 0)

        # Lib
        libFiles = self.getLastOpenedLibFiles()
        if len(libFiles):
            for libFile in libFiles:
                self.openInNewTab(libFile)
        else:
            self.createNewTab()

        # Callbacks
        self.callbackID = self.wrapper.addExitCallback(self.closeParentEvent)

    # ******************************************************************
    # Events
    # ******************************************************************

    # ------------------------------------------------------------------
    # Event Filter
    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):
        # Close event, do we need to save
        if event.type() == QtCore.QEvent.Close:
            event.accept() if self.closeWindowEvent() is True else event.ignore()
            return True
        elif event.type() == QtCore.QEvent.Show:
            event.accept()
            self.refreshAllTabs()
            return True
        return False

    # ------------------------------------------------------------------
    # Tab changed event
    # ------------------------------------------------------------------
    def tabChangedEvent(self, tabIndex):
        if tabIndex != -1 and len(self.libs) > tabIndex:
            self.updateFooterBar(tabIndex)

    # ------------------------------------------------------------------
    # Tab changed event
    # ------------------------------------------------------------------
    def tabClosedEvent(self, tabIndex):
        if tabIndex != -1:
            self.closeTab(tabIndex)

    # ------------------------------------------------------------------
    # Close Event
    # ------------------------------------------------------------------
    def closeWindowEvent(self):
        dirtyLib = False
        for lib in self.libs:
            dirtyLib |= lib.libFileDirty

        if dirtyLib is True:
            saveReminder = QtWidgets.QMessageBox.question(
                self,
                "Save Simulation Cache Library File",
                "Save dirty Simulation Cache Library files?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
            )
            if saveReminder == QtWidgets.QMessageBox.Save:
                self.saveAllTabs()
            elif saveReminder == QtWidgets.QMessageBox.Cancel:
                return False

        self.savePosAndSize()
        self.setLastOpenedLibFiles()
        self.editItemWin.close()
        return True

    # ------------------------------------------------------------------
    # Close Maya Event
    # ------------------------------------------------------------------
    def closeParentEvent(*args):
        event = QtCore.QEvent(QtCore.QEvent.Type.Close)
        args[0].eventFilter("", event)
        args[0].wrapper.removeExitCallback(args[0].callbackID)

    # ******************************************************************
    # Accessors
    # ******************************************************************

    # ------------------------------------------------------------------
    # Return the main QLayout
    # ------------------------------------------------------------------
    def getMainLayout(self):
        return self.centralWidget().layout()

    def getCentralWidget(self):
        return self.centralWidget()

    def getTabWidget(self):
        return self.tabWidget

    def getTabWidgetIndex(self):
        return self.getTabWidget().currentIndex()

    def getListWidget(self, tabIndex):
        return self.getTabWidget().widget(tabIndex)

    # ******************************************************************
    # Menu Commands
    # ******************************************************************

    # ------------------------------------------------------------------
    # Create New Tab
    # ------------------------------------------------------------------
    def createNewTab(self, fileToOpen=""):
        tabIndex = self.addTab()
        lib = simCacheLib.SimCacheLib(fileToOpen)
        self.libs.insert(tabIndex, lib)
        return tabIndex

    # ------------------------------------------------------------------
    # Open a Lib Files in a New Tab
    # ------------------------------------------------------------------
    def openInNewTab(self, libFile):
        filesToOpen = []
        if libFile == "":
            files = self.wrapper.browseFiles("Open Golaem Simulation Cache Library File", ["Golaem Library Files (*.gscb)"], "SimulationLibrary", 4)
            if files is not None:
                filesToOpen.extend(files)
        else:
            filesToOpen.append(libFile)

        for fileToOpen in filesToOpen:
            if os.path.isfile(fileToOpen) is False:
                self.wrapper.log("warning", "Golaem Simulation Cache Library File '" + fileToOpen + "' does not exist.")
            else:
                tabIndex = self.getTabIndexOfLibFile(fileToOpen)
                if tabIndex == -1:
                    tabIndex = self.createNewTab(fileToOpen)
                else:
                    self.getTabWidget().setCurrentIndex(tabIndex)
                self.refreshTab(tabIndex)

    # ------------------------------------------------------------------
    # Refresh the Current Tab
    # ------------------------------------------------------------------
    def refreshCurrentTab(self):
        self.refreshTab(self.getTabWidgetIndex())

    # ------------------------------------------------------------------
    # Save abb tabs
    # ------------------------------------------------------------------
    def refreshAllTabs(self):
        tabCount = self.getTabWidget().count()
        for iTab in range(tabCount):
            self.refreshTab(iTab)

    # ------------------------------------------------------------------
    # Open a Lib File in a specific tab
    # ------------------------------------------------------------------
    def refreshTab(self, tabIndex):
        if tabIndex != -1:
            if os.path.exists(self.libs[tabIndex].libFile):
                self.libs[tabIndex].readLibFile(self.libs[tabIndex].libFile)
                self.refreshLibWidget(tabIndex)

    # ------------------------------------------------------------------
    # Import a Lib File in the Current Tab
    # ------------------------------------------------------------------
    def importInCurrentTab(self, libFile):
        filesToImport = []
        if not libFile:
            files = self.wrapper.browseFiles("Import Golaem Simulation Cache Library File", ["Golaem Library Files (*.gscb)"], "SimulationLibrary", 4)
            if files is not None:
                filesToImport.extend(files)
        else:
            filesToImport.append(libFile)

        for fileToImport in filesToImport:
            if os.path.isfile(fileToImport) is False:
                self.wrapper.log("warning", "Golaem Simulation Cache Library File '" + fileToImport + "' does not exist.")
            else:
                tabIndex = self.getTabWidgetIndex()
                if tabIndex != -1:
                    self.libs[tabIndex].importLibFile(fileToImport)
                    self.refreshLibWidget(tabIndex)
                else:
                    self.openInNewTab(fileToImport)

    # ------------------------------------------------------------------
    # Import a Lib File in the Current Tab
    # ------------------------------------------------------------------
    def importDirInCurrentTab(self, directory):
        directoriesToImport = []
        if not directory:
            directories = self.wrapper.browseFiles(
                "Import All Golaem Simulation Cache Library Files", ["Golaem Library Files (*.gscb)"], "SimulationLibrary", 3
            )
            if directories is not None:
                directoriesToImport.extend(directories)
        else:
            directoriesToImport.append(directory)

        filesToImport = []
        for directoryToImport in directoriesToImport:
            # recursively search gscb files in this directory
            for root, directories, filenames in os.walk(directoryToImport):
                for filename in fnmatch.filter(filenames, "*.gscb"):
                    filesToImport.append(os.path.join(root, filename))

        for fileToImport in filesToImport:
            self.importInCurrentTab(fileToImport)

    # ------------------------------------------------------------------
    # Save the Current Tab
    # ------------------------------------------------------------------
    def saveCurrentTab(self):
        self.saveTab(self.getTabWidgetIndex())

    # ------------------------------------------------------------------
    # Save abb tabs
    # ------------------------------------------------------------------
    def saveAllTabs(self):
        tabCount = self.getTabWidget().count()
        for iTab in range(tabCount):
            self.saveTab(iTab)

    # ------------------------------------------------------------------
    # Save the Current Tab
    # ------------------------------------------------------------------
    def saveTab(self, tabIndex):
        if tabIndex != -1:
            if self.libs[tabIndex].libFile != "":
                self.libs[tabIndex].writeLibFile(self.libs[tabIndex].libFile)
                self.updateTabName(tabIndex)
                self.updateFooterBar(tabIndex)
            else:
                self.saveTabAs(tabIndex, "")

    # ------------------------------------------------------------------
    # Save the Current Tab as
    # ------------------------------------------------------------------
    def saveCurrentTabAs(self):
        self.saveTabAs(self.getTabWidgetIndex(), "")

    # ------------------------------------------------------------------
    # Save the Current Tab
    # ------------------------------------------------------------------
    def saveTabAs(self, tabIndex, libFile):
        if tabIndex != -1:
            libFileToSave = ""
            if libFile == "":
                files = self.wrapper.browseFiles(
                    "Save Golaem Simulation Cache Library File", ["Golaem Library Files (*.gscb)"], "SimulationLibrary", 0
                )
                if files is not None:
                    libFileToSave = files[0]
            else:
                libFileToSave = libFile
            if libFileToSave != "":
                self.libs[tabIndex].writeLibFile(libFileToSave)
                self.updateTabName(tabIndex)
                self.updateFooterBar(tabIndex)

    # ------------------------------------------------------------------
    # Close the Current Tab
    # ------------------------------------------------------------------
    def closeCurrentTab(self):
        self.closeTab(self.getTabWidgetIndex())

        # ------------------------------------------------------------------

    # Close the Current Tab
    # ------------------------------------------------------------------
    def closeAllTabs(self):
        tabCount = self.getTabWidget().count()
        for iTab in range(tabCount):
            self.closeTab(iTab)

    # ------------------------------------------------------------------
    # Close a Lib File
    # ------------------------------------------------------------------
    def closeTab(self, tabIndex):
        if tabIndex != -1:
            if self.libs[tabIndex].libFileDirty is True:
                quit_msg = "Save lib file '" + self.libs[tabIndex].libFile + "'?"
                saveReminder = QtWidgets.QMessageBox.question(
                    self, "Save Lib File", quit_msg, QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel
                )
                if saveReminder == QtWidgets.QMessageBox.Save:
                    self.saveTab(tabIndex)
                elif saveReminder == QtWidgets.QMessageBox.Discard:
                    pass
                else:  # Cancel
                    return
            del self.libs[tabIndex]
            self.removeTab(tabIndex)

    # ------------------------------------------------------------------
    # Add a new lib item in the Current Tab
    # ------------------------------------------------------------------
    def addItemInCurrentTab(self):
        self.addItemInTab(self.getTabWidgetIndex())

    # ------------------------------------------------------------------
    # Add a new lib item in the Current Tab
    # ------------------------------------------------------------------
    def addItemInTab(self, tabIndex):
        if tabIndex == -1:
            tabIndex = self.createNewTab()
        # get selected node
        nodes = self.wrapper.getSelectedObjectsOfType("SimulationCacheProxy")
        if len(nodes) == 0:
            nodes = self.wrapper.getObjectsOfType("SimulationCacheProxy")
        self.libs[tabIndex] = self.wrapper.fillSimCacheLibFromProxies(self.libs[tabIndex], nodes)
        self.refreshLibWidget(tabIndex)

    # ******************************************************************
    # Utils
    # ******************************************************************

    # ------------------------------------------------------------------
    # Return the id
    # ------------------------------------------------------------------
    def getTabIndexOfLibFile(self, libFile):
        tabIndex = -1
        for iLib in range(len(self.libs)):
            if self.libs[iLib].libFile == libFile:
                tabIndex = iLib
                break
        return tabIndex

    # ------------------------------------------------------------------
    # Add a new tab
    # ------------------------------------------------------------------
    def addTab(self, label="untitled"):
        listWidget = QtWidgets.QListWidget(self)
        listWidget.setObjectName("itemLibList")
        listWidget.setDragEnabled(False)
        listWidget.setViewMode(QtWidgets.QListView.IconMode)
        listWidget.setFlow(QtWidgets.QListView.LeftToRight)
        listWidget.setResizeMode(QtWidgets.QListView.Adjust)
        listWidget.setWrapping(True)
        listWidget.setViewportMargins(5, 5, 5, 5)

        tabIndex = self.getTabWidgetIndex()
        newTabIndex = self.getTabWidget().insertTab(tabIndex + 1, listWidget, label)
        self.getTabWidget().setCurrentIndex(newTabIndex)
        return newTabIndex

    # ------------------------------------------------------------------
    # Remove a tab
    # ------------------------------------------------------------------
    def removeTab(self, tabIndex):
        listWidget = self.getTabWidget().widget(tabIndex)
        listWidget.deleteLater()
        self.getTabWidget().removeTab(tabIndex)

    # ******************************************************************
    # Item Button Commands
    # ******************************************************************

    # ------------------------------------------------------------------
    # Open the item editor
    # ------------------------------------------------------------------
    def openEditLibItemWindow(self, idLibItem):
        tabIndex = self.getTabWidgetIndex()
        item = self.libs[tabIndex].getLibItemAt(idLibItem)
        if item is not None:
            self.editItemWin.loadLibItem(idLibItem, item)
            self.editItemWin.show()

    # ------------------------------------------------------------------
    # Delete a lib item
    # ------------------------------------------------------------------
    def deleteLibItem(self, idLibItem):
        tabIndex = self.getTabWidgetIndex()
        self.libs[tabIndex].removeLibItem(idLibItem)
        self.refreshLibWidget(tabIndex)

    # ------------------------------------------------------------------
    # editLibItem
    # ------------------------------------------------------------------
    def editLibItem(self, idLibItem, item):
        tabIndex = self.getTabWidgetIndex()
        if self.libs[tabIndex].getLibItemAt(idLibItem) is not None:
            self.libs[tabIndex].setLibItemAt(idLibItem, item)
            self.refreshLibWidget(tabIndex)

    # ------------------------------------------------------------------
    # updateSnapshot
    # ------------------------------------------------------------------
    def updateSnapshot(self, idLibItem):
        tabIndex = self.getTabWidgetIndex()
        item = self.libs[tabIndex].getLibItemAt(idLibItem)
        if item is not None:
            item = self.wrapper.updateItemSnapshot(item)
            self.libs[tabIndex].setLibItemAt(idLibItem, item)
            self.refreshLibWidget(tabIndex)

    # ------------------------------------------------------------------
    # createCacheProxyFromLibItem
    # ------------------------------------------------------------------
    def createCacheProxyFromLibItem(self, idLibItem):
        tabIndex = self.getTabWidgetIndex()
        item = self.libs[tabIndex].getLibItemAt(idLibItem)
        if item is not None:
            node = self.wrapper.createSimCacheProxyFromItem(self.libs[tabIndex], idLibItem)
            if node != "":
                self.wrapper.selectNode(node)

    # ------------------------------------------------------------------
    # createCacheProxiesFromLibItem
    # ------------------------------------------------------------------
    def createCacheProxiesFromLibItem(self, idLibItem):
        tabIndex = self.getTabWidgetIndex()
        item = self.libs[tabIndex].getLibItemAt(idLibItem)
        if item is not None:
            nodes = self.wrapper.createSimCacheProxiesFromItem(self.libs[tabIndex], idLibItem)
            if len(nodes):
                self.wrapper.selectNode(nodes[len(nodes)-1])

    # ******************************************************************
    # GUI
    # ******************************************************************

    # ------------------------------------------------------------------
    # refreshLibWidgets
    # ------------------------------------------------------------------
    def refreshLibWidgets(self, filter=""):
        tabCount = self.getTabWidget().count()
        for iTab in range(tabCount):
            self.refreshLibWidget(iTab, filter)

    # ------------------------------------------------------------------
    # refreshTabWidget
    # ------------------------------------------------------------------
    def refreshLibWidget(self, tabIndex, filter=""):
        # Clean current widget if existing
        self.deleteLibWidget(tabIndex)

        # Layout items
        listWidget = self.getListWidget(tabIndex)
        nbItems = self.libs[tabIndex].getLibItemCount()
        iFilteredItem = 0
        for iItem in range(0, nbItems):
            item = self.libs[tabIndex].getLibItemAt(iItem)
            if item.isInFilter(filter) is True:
                itemName = "item" + str(iItem)
                libItem = self.createLibItemWidget(item, iFilteredItem, item.simCacheFilesExist())
                itemWidget = QtWidgets.QListWidgetItem(itemName)
                itemWidget.setSizeHint(QtCore.QSize(self.itemSize[0] + 13, 270))
                listWidget.addItem(itemWidget)
                listWidget.setItemWidget(itemWidget, libItem)
                iFilteredItem += 1

        # Update tab name
        self.updateTabName(tabIndex)
        self.updateFooterBar(tabIndex)

    # ------------------------------------------------------------------
    # deleteLibWidget
    # ------------------------------------------------------------------
    def deleteLibWidget(self, tabIndex):
        libWidget = self.getListWidget(tabIndex)
        libWidget.clear()

    # ------------------------------------------------------------------
    # createLibItemLayout
    # ------------------------------------------------------------------
    def createLibItemWidget(self, libItem, idLibItem, isEnabled):
        itemLayout = QtWidgets.QGridLayout()
        itemLayout.setContentsMargins(0, 0, 0, 0)

        itemWidget = QtWidgets.QFrame(self)
        itemWidget.setObjectName("itemLib")
        itemWidget.setLayout(itemLayout)
        itemWidget.setMinimumSize(self.itemSize[0], self.itemSize[1])
        itemWidget.setMaximumSize(self.itemSize[0], self.itemSize[1])

        # Tool tip
        toolTipStr = self.createTooltipOfAnItem(libItem)
        # Image
        captureLabel = SimCacheLibImageWidget(idLibItem, self)
        captureLabel.setToolTip(toolTipStr)
        if len(libItem.image):
            captureLabel.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(bytes(base64.b64decode(libItem.image)))))
        else:
            pixmap = QtGui.QPixmap(self.imageSize[0], self.imageSize[1])
            pixmap.fill(QtGui.QColor(80, 80, 80))
            captureLabel.setPixmap(pixmap)
        captureLabel.setEnabled(isEnabled)
        itemLayout.addWidget(captureLabel, 0, 0)
        # Cache Name
        nameLabel = QtWidgets.QLabel("<b><font size=4>" + libItem.itemName + "</font></b>", self)
        nameLabel.setToolTip(toolTipStr)
        itemLayout.addWidget(nameLabel, 1, 0)
        # Info
        infoLabel = QtWidgets.QLabel(
            "<i>"
            + str(libItem.nbEntities)
            + " entities - "
            + str(libItem.getNbFrames())
            + " frames ("
            + str(libItem.startFrame)
            + "-"
            + str(libItem.endFrame)
            + ")</i><br />Layout Name: "
            + str(libItem.layoutFile),
            self,
        )
        infoLabel.setToolTip(toolTipStr)
        itemLayout.addWidget(infoLabel, 2, 0)
        # Tags
        tagsLabel = QtWidgets.QLabel("Tags: " + ", ".join(libItem.tags), self)
        tagsLabel.setToolTip(toolTipStr)
        itemLayout.addWidget(tagsLabel, 3, 0)
        # Buttons
        iconsDir = self.wrapper.getIconsDir()
        rowIndex = 0
        buttonLayout = QtWidgets.QGridLayout()
        buttonLayout.setHorizontalSpacing(0)
        buttonLayout.setVerticalSpacing(0)
        if self.wrapper.isButtonAvailable("Import Simulation Cache in Scene"):
            buttonLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "libraryTool", "cacheExport.png").replace("\\", "/"),
                    "Import Simulation Cache in Scene",
                    20,
                    isEnabled,
                    self.createCacheProxyFromLibItem,
                    idLibItem,
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Import Simulation Cache in Scene as Multiple Proxies"):
            buttonLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "libraryTool", "cachesExport.png").replace("\\", "/"),
                    "Import Simulation Cache in Scene as Multiple Proxies",
                    20,
                    isEnabled,
                    self.createCacheProxiesFromLibItem,
                    idLibItem,
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Edit Item Attributes"):
            buttonLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "libraryTool", "itemEdit.png").replace("\\", "/"),
                    "Edit Item Attributes",
                    20,
                    True,
                    self.openEditLibItemWindow,
                    idLibItem,
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Update Thumbnail from Viewport"):
            buttonLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "libraryTool", "snapshot.png").replace("\\", "/"),
                    "Update Thumbnail from Viewport",
                    20,
                    True,
                    self.updateSnapshot,
                    idLibItem,
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        if self.wrapper.isButtonAvailable("Delete From Library"):
            buttonLayout.addWidget(
                self.createPushButton(
                    os.path.join(iconsDir, "editors", "delete.png").replace("\\", "/"), "Delete From Library", 20, True, self.deleteLibItem, idLibItem
                ),
                0,
                rowIndex,
            )
            rowIndex += 1
        buttonLayout.addItem(QtWidgets.QSpacerItem(100, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum), 0, rowIndex)
        itemLayout.addLayout(buttonLayout, 4, 0)
        return itemWidget

    # ------------------------------------------------------------------
    # create a button
    # ------------------------------------------------------------------
    def createPushButton(self, iconPath, toolTip, size, isEnabled, command, commandArg):
        icon = QtGui.QIcon(iconPath)
        iconSize = QtCore.QSize(size, size)
        button = QtWidgets.QPushButton(self)
        button.setIcon(icon)
        button.setIconSize(iconSize)
        button.setFlat(True)
        button.setFixedSize(iconSize + QtCore.QSize(8, 8))
        button.setMinimumSize(iconSize + QtCore.QSize(8, 8))
        button.setContentsMargins(4, 4, 4, 4)
        button.setToolTip(toolTip)
        button.setEnabled(isEnabled)
        if commandArg is not None:
            button.clicked.connect(partial(command, commandArg))
        else:
            button.clicked.connect(command)
        return button

    # ------------------------------------------------------------------
    # create tooltip of an item
    # ------------------------------------------------------------------
    def createTooltipOfAnItem(self, item):
        return (
            item.itemName
            + "\n"
            + " - Node Name: "
            + item.nodeName
            + "\n"
            + " - CrowdFields: "
            + ", ".join(item.crowdFields)
            + "\n"
            + " - Cache Name: "
            + item.cacheName
            + "\n"
            + " - Cache Dir: "
            + item.cacheDir
            + "\n"
            + " - Character Files: "
            + item.characterFiles
            + "\n"
            + " - Nb Entities: "
            + str(item.nbEntities)
            + "\n"
            + " - Start Frame: "
            + str(item.startFrame)
            + "\n"
            + " - End Frame: "
            + str(item.endFrame)
            + "\n"
            + " - Enable Layout: "
            + str(item.enableLayout)
            + "\n"
            + " - Layout File: "
            + str(item.layoutFile)
            + "\n"
            + " - Source Terrain: "
            + str(item.sourceTerrain)
            + "\n"
            + " - Destination Terrain: "
            + str(item.destTerrain)
        )

    # ------------------------------------------------------------------
    # update the footer bar
    # ------------------------------------------------------------------
    def updateFooterBar(self, tabIndex):
        filePath = "untitled"
        if self.libs[tabIndex].libFile != "":
            filePath = self.libs[tabIndex].libFile
        if self.libs[tabIndex].libFileDirty is True:
            filePath += "*"
        self.footerLabel.setText("Library File: <i>" + filePath + "</i>")  # TODO

    # ------------------------------------------------------------------
    # update the tab bar
    # ------------------------------------------------------------------
    def updateTabName(self, tabIndex):
        fileName = "untitled"
        if self.libs[tabIndex].libFile != "":
            fileName = os.path.splitext(os.path.basename(self.libs[tabIndex].libFile))[0]
            self.getTabWidget().setTabToolTip(tabIndex, self.libs[tabIndex].libFile)
        if self.libs[tabIndex].libFileDirty is True:
            fileName += "*"
        self.getTabWidget().setTabText(tabIndex, fileName)

    # ------------------------------------------------------------------
    # restorePosAndSize
    # ------------------------------------------------------------------
    def restorePosAndSize(self):
        posAndSize = self.wrapper.loadWindowPrefs(self.objectName(), self.defaultPosAndSize)
        self.move(QtCore.QPoint(posAndSize[0][0], posAndSize[0][1]))
        self.resize(posAndSize[1][0], posAndSize[1][1])

        # force width depending on element numbers
        # self.setFixedWidth((self.itemSize[0] + 23) * self.nbItemPerLine)

    # ------------------------------------------------------------------
    # savePosAndSize
    # ------------------------------------------------------------------
    def savePosAndSize(self):
        posAndSize = []
        posAndSize.append([self.pos().x(), self.pos().y()])
        posAndSize.append([self.width(), self.height()])
        self.wrapper.saveWindowPrefs(self.objectName(), posAndSize)

    # ------------------------------------------------------------------
    # getLastOpenedLibFiles
    # ------------------------------------------------------------------
    def getLastOpenedLibFiles(self):
        libFiles = []
        optionVar = self.wrapper.getStrOptionVar("SimCacheLibWindow", self.objectName() + "LastFiles")
        if optionVar != "0" and optionVar != "":  # if var does not exist
            libFiles.extend(optionVar.split(";"))
        return libFiles

    # ------------------------------------------------------------------
    # setLastOpenedLibFiles
    # ------------------------------------------------------------------
    def setLastOpenedLibFiles(self):
        libFiles = []
        for lib in self.libs:
            if lib.libFile != "":
                libFiles.append(lib.libFile)
        self.wrapper.setStrOptionVar("SimCacheLibWindow", self.objectName() + "LastFiles", ";".join(libFiles))


# **********************************************************************
#
# SimCacheLibImageWidget
#
# **********************************************************************
class SimCacheLibImageWidget(QtWidgets.QLabel):
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(self, idLibItem, simCacheLibGUI, parent=None):
        super(SimCacheLibImageWidget, self).__init__(parent)
        self.idLibraryItem = idLibItem
        self.simCacheLibGUI = simCacheLibGUI

        # events
        self.installEventFilter(self)
        # self.mousePressEvent = self.mousePressEvent

    # ------------------------------------------------------------------
    # eventFilter
    # ------------------------------------------------------------------
    def eventFilter(self, object, event):
        if self.isEnabled():
            if event.type() == QtCore.QEvent.MouseButtonPress:
                self.simCacheLibGUI.createCacheProxyFromLibItem(self.idLibraryItem)
                return True

            elif event.type() == QtCore.QEvent.Enter:
                QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                return True

            elif event.type() == QtCore.QEvent.Leave:
                QtWidgets.QApplication.restoreOverrideCursor()
                return True

        return False


# **********************************************************************
#
# SimCacheLibFilterWidget
#
# **********************************************************************
class SimCacheLibFilterLineEdit(QtWidgets.QLineEdit):
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(self, simCacheLibGUI, parent=None):
        super(SimCacheLibFilterLineEdit, self).__init__(parent)
        self.simCacheLibGUI = simCacheLibGUI

        # events
        # self.keyPressed = self.keyPressed

    # ------------------------------------------------------------------
    # eventFilter
    # ------------------------------------------------------------------
    def keyPressEvent(self, event):
        super(SimCacheLibFilterLineEdit, self).keyPressEvent(event)
        filterText = self.text()
        self.simCacheLibGUI.refreshLibWidgets(filterText)


# **********************************************************************
#
# SimCacheLibEditWindow
#
# **********************************************************************
class SimCacheLibEditWindow(QtWidgets.QMainWindow):
    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------
    def __init__(self, parent=None):
        super(SimCacheLibEditWindow, self).__init__(parent)

        # Data Members
        self.libItem = simCacheLib.SimCacheLibItem()
        self.itemNameLineEdit = QtWidgets.QLineEdit(self)
        self.nodeNameLineEdit = QtWidgets.QLineEdit(self)
        self.crowdFieldsLineEdit = QtWidgets.QLineEdit(self)
        self.cacheNameLineEdit = QtWidgets.QLineEdit(self)
        self.cacheDirLineEdit = QtWidgets.QLineEdit(self)
        self.characterFilesLineEdit = QtWidgets.QLineEdit(self)
        self.tagsLineEdit = QtWidgets.QLineEdit(self)
        self.startFrameLineEdit = QtWidgets.QDoubleSpinBox(self)
        self.startFrameLineEdit.setDecimals(0)
        self.startFrameLineEdit.setRange(-sys.float_info.max, sys.float_info.max)
        self.endFrameLineEdit = QtWidgets.QDoubleSpinBox(self)
        self.endFrameLineEdit.setDecimals(0)
        self.endFrameLineEdit.setRange(-sys.float_info.max, sys.float_info.max)
        self.enableLayoutCheckbox = QtWidgets.QCheckBox(self)
        self.layoutFileLineEdit = QtWidgets.QLineEdit(self)
        self.sourceTerrainLineEdit = QtWidgets.QLineEdit(self)
        self.destTerrainLineEdit = QtWidgets.QLineEdit(self)

        # Init
        self.initUI()

    # ******************************************************************
    # UI Accessors
    # ******************************************************************

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def initUI(self):

        # Window properties
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Edit Simulation Cache Library Item")
        self.setObjectName("glmSimulationCacheLibraryEditWnd")
        self.restorePosAndSize()

        # Central Widget
        mainWidget = QtWidgets.QWidget()
        self.setCentralWidget(mainWidget)
        mainLayout = QtWidgets.QGridLayout()
        mainLayout.setHorizontalSpacing(2)
        mainLayout.setVerticalSpacing(2)
        mainWidget.setLayout(mainLayout)

        # UI elements
        formLayout = QtWidgets.QGridLayout()
        formLayout.addWidget(QtWidgets.QLabel("Item Name: "), 0, 0)
        formLayout.addWidget(self.itemNameLineEdit, 0, 1)
        formLayout.addWidget(QtWidgets.QLabel("Node Name: "), 1, 0)
        formLayout.addWidget(self.nodeNameLineEdit, 1, 1)
        formLayout.addWidget(QtWidgets.QLabel("CrowdFields: "), 2, 0)
        formLayout.addWidget(self.crowdFieldsLineEdit, 2, 1)
        formLayout.addWidget(QtWidgets.QLabel("Cache Name: "), 3, 0)
        formLayout.addWidget(self.cacheNameLineEdit, 3, 1)
        formLayout.addWidget(QtWidgets.QLabel("Cache Directory: "), 4, 0)
        formLayout.addWidget(self.cacheDirLineEdit, 4, 1)
        formLayout.addWidget(QtWidgets.QLabel("Character Files: "), 5, 0)
        formLayout.addWidget(self.characterFilesLineEdit, 5, 1)
        formLayout.addWidget(QtWidgets.QLabel("Tags: "), 6, 0)
        formLayout.addWidget(self.tagsLineEdit, 6, 1)

        formLayout.addWidget(QtWidgets.QLabel("Start Frame:"), 7, 0)
        formLayout.addWidget(self.startFrameLineEdit, 7, 1)
        formLayout.addWidget(QtWidgets.QLabel("End Frame:"), 8, 0)
        formLayout.addWidget(self.endFrameLineEdit, 8, 1)

        formLayout.addWidget(QtWidgets.QLabel("Enable Layout:"), 9, 0)
        formLayout.addWidget(self.enableLayoutCheckbox, 9, 1)
        formLayout.addWidget(QtWidgets.QLabel("Layout File:"), 10, 0)
        formLayout.addWidget(self.layoutFileLineEdit, 10, 1)

        formLayout.addWidget(QtWidgets.QLabel("Source Terrain:"), 11, 0)
        formLayout.addWidget(self.sourceTerrainLineEdit, 11, 1)
        formLayout.addWidget(QtWidgets.QLabel("Dest Terrain:"), 12, 0)
        formLayout.addWidget(self.destTerrainLineEdit, 12, 1)
        mainLayout.addLayout(formLayout, 0, 0)

        # Buttons
        buttonLayout = QtWidgets.QGridLayout()
        okButton = QtWidgets.QPushButton("OK", self)
        applyButton = QtWidgets.QPushButton("Apply", self)
        cancelButton = QtWidgets.QPushButton("Cancel", self)
        buttonLayout.addWidget(okButton, 0, 0)
        buttonLayout.addWidget(applyButton, 0, 1)
        buttonLayout.addWidget(cancelButton, 0, 2)
        mainLayout.addLayout(buttonLayout, 1, 0)

        okButton.clicked.connect(self.applyAndClose)
        applyButton.clicked.connect(self.apply)
        cancelButton.clicked.connect(self.close)

    # ------------------------------------------------------------------
    # restorePosAndSize
    # ------------------------------------------------------------------
    def restorePosAndSize(self):
        winPos = QtCore.QPoint(100, 100)
        if self.parent() is not None:
            winPos += self.parent().pos()
        self.move(winPos)

    # ------------------------------------------------------------------
    # override
    # ------------------------------------------------------------------
    def show(self):
        if self.isVisible() is False:
            self.restorePosAndSize()
        super(SimCacheLibEditWindow, self).show()

    # ******************************************************************
    # Item Accessors
    # ******************************************************************

    # ------------------------------------------------------------------
    # apply
    # ------------------------------------------------------------------
    def apply(self):
        if self.parent() is not None:
            self.saveLibItem()
            self.parent().editLibItem(self.idLibItem, self.libItem)

    # ------------------------------------------------------------------
    # apply
    # ------------------------------------------------------------------
    def applyAndClose(self):
        self.apply()
        self.close()

    # ------------------------------------------------------------------
    # loadLibItem
    # ------------------------------------------------------------------
    def loadLibItem(self, idLibItem, libItem):
        if libItem.isInitialized() is True:
            self.libItem = libItem
            self.idLibItem = idLibItem
            self.itemNameLineEdit.setText(self.libItem.itemName)
            self.nodeNameLineEdit.setText(self.libItem.nodeName)
            self.crowdFieldsLineEdit.setText(";".join(self.libItem.crowdFields))
            self.cacheNameLineEdit.setText(self.libItem.cacheName)
            self.cacheDirLineEdit.setText(self.libItem.cacheDir)
            self.characterFilesLineEdit.setText(self.libItem.characterFiles)
            self.enableLayoutCheckbox.setCheckState(QtCore.Qt.Checked if self.libItem.enableLayout is True else QtCore.Qt.Unchecked)
            self.layoutFileLineEdit.setText(self.libItem.layoutFile)
            self.sourceTerrainLineEdit.setText(self.libItem.sourceTerrain)
            self.destTerrainLineEdit.setText(self.libItem.destTerrain)
            self.startFrameLineEdit.setValue(float(self.libItem.startFrame))
            self.endFrameLineEdit.setValue(float(self.libItem.endFrame))
            self.tagsLineEdit.setText(", ".join(self.libItem.tags))
            self.displayMissingFiles()

    # ------------------------------------------------------------------
    # saveLibItem
    # ------------------------------------------------------------------
    def saveLibItem(self):
        if self.libItem.isInitialized() is True:
            self.libItem.itemName = self.itemNameLineEdit.text()
            self.libItem.nodeName = self.nodeNameLineEdit.text()
            self.libItem.crowdFields = list(map(str.strip, str(self.crowdFieldsLineEdit.text()).split(";")))
            self.libItem.cacheName = self.cacheNameLineEdit.text()
            self.libItem.cacheDir = self.cacheDirLineEdit.text()
            self.libItem.characterFiles = self.characterFilesLineEdit.text()
            self.libItem.enableLayout = True if self.enableLayoutCheckbox.checkState() == QtCore.Qt.Checked else False
            self.libItem.layoutFile = self.layoutFileLineEdit.text()
            self.libItem.sourceTerrain = self.sourceTerrainLineEdit.text()
            self.libItem.destTerrain = self.destTerrainLineEdit.text()
            self.libItem.startFrame = int(self.startFrameLineEdit.value())
            self.libItem.endFrame = int(self.endFrameLineEdit.value())
            self.libItem.tags = list(map(str.strip, str(self.tagsLineEdit.text()).split(",")))
            self.displayMissingFiles()

    # ------------------------------------------------------------------
    # displayMissingFiles
    # ------------------------------------------------------------------
    def displayMissingFiles(self):
        # first cache file per crowdField
        stylesheet = "color: rgb(255, 147, 0);"
        if self.libItem.firstSimCacheFilesExist() is False:
            stylesheet = "color: rgb(255, 147, 0);"
        else:
            stylesheet = ""
        self.crowdFieldsLineEdit.setStyleSheet(stylesheet)
        self.cacheNameLineEdit.setStyleSheet(stylesheet)
        self.cacheDirLineEdit.setStyleSheet(stylesheet)
        self.startFrameLineEdit.setStyleSheet(stylesheet)

        # character files
        if self.libItem.characterFilesExist() is False:
            stylesheet = "color: rgb(255, 147, 0);"
        else:
            stylesheet = ""
        self.characterFilesLineEdit.setStyleSheet(stylesheet)


# **********************************************************************
#
# Launchers
#
# **********************************************************************
glmSimCacheLibWindowUIs = []

def main(wrapper=wrapper.SimCacheLibWindowWrapper()):
    global glmSimCacheLibWindowUIs
    if len(glmSimCacheLibWindowUIs):
        ui = glmSimCacheLibWindowUIs[0]
    else:
        ui = SimCacheLibWindow(wrapper)
        glmSimCacheLibWindowUIs.append(ui)
    ui.show()
    ui.setWindowState(ui.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
    ui.activateWindow()
    return ui


def testStandalone(wrapper=wrapper.SimCacheLibWindowWrapper()):
    app, newInstance = qtcUtils.getQappInstance()
    main(wrapper)
    if newInstance:
        app.exec_()

if __name__ == "__main__":
    testStandalone()

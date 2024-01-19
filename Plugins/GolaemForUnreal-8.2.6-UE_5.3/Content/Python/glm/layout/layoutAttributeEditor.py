from __future__ import print_function
#**************************************************************************
#*                                                                        *
#*  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
#*                                                                        *
#**************************************************************************

from builtins import map
from builtins import str
from builtins import bytes
from builtins import range
from builtins import object
import copy
import os
import webbrowser
import base64
from glm.Qtpy.Qt import QtGui, QtCore, QtWidgets

# import fnmatch

######################################################################
# Enums
######################################################################
class GlmAttributeFlags(object): #2**0 is an operator notation for math.pow(2, 0)
    _none = 0                                # 0 attribute flags default to 0
    _uiEnableAddRemove = 2**0                # 1 Allow add remove on this attribute
    _uiSnapToTargetComboBox = 2**1           # 2 SnapToTarget combo box
    _uiOperationModeComboBox = 2**2          # 4 Operation Mode combo box (Add/Set)
    _uiGroundAdaptationModeComboBox = 2**3   # 8 Ground adaptation mode combo box (None/Snap Height/Snap Height And Ori/With IK)
    _uiKeyframable = 2**4                    # 16 Keyframable attribute (will display )
    _uiColorWheel = 2**5                     # 32 specific color ui for GTV_Vec4 values
    _uiTextEdit = 2**6                       # 64 specific multi line string ui for GTV_Char values
    _uiRenderingTypeDropDown = 2**7          # 128 display as a RenderingType list dropDown, use wrapper for list
    _uiAddRemoveMeshAssetDialog = 2**8       # 256 add a button to add/remove MeshAssets to an mesh indices integer list, use wrapper for list
    _uiPickSelectedEntityMeshAssets = 2**9   # 512 add a button to pick currently selected entity mesh asset indices in attribute
    _uiSelectedCharMeshAssetComboBox = 2**10 # 1024 currently selected character all mesh asset indices combo box
    _uiSnapToEntityTypeComboBox = 2**11      # 2048 entityType combo box
    _uiVectorFieldTargetComboBox = 2**12     # 4096 VectorField target combobox
    _uiImage = 2**13                         # 8192 the attribute is encoding an image
    _uiOnOffComboBox = 2**14                 # 16384 On/Off combo box
    _uiBoneNamesComboBox = 2 ** 15           # 32768 display as a bone list combobox, use the wrapper to populate the list
    _uiHidden = 2 ** 16                      # 65536 hidden in the nodz UI
    _uiPerformanceWarning = 2 ** 17          # 131 072 shows a performance warning icon
    _uiPaintedZoneTargetComboBox = 2 ** 18   # 262 144 paintedZone target combobox (to get shaderAttribute value)
    _uiColorChannelComboBox = 2 ** 19        # 524 288 color channel selector : Vector / R Channel / G Channel / B Channel / A Channel
    _uiRotateOrderComboBox = 2 ** 20         # 1 048 576 rotate order combo box
class GlmTransformType(object):
    Noop = 0
    Rotate = 1
    Scale = 2
    Translate = 3
    Duplicate = 4
    Kill = 5
    Unkill = 6
    SetMeshAssets = 7
    Expand = 8
    FrameOffset = 9
    FrameWarp = 10
    ScaleRange = 11
    SnapTo = 12
    SetShaderAttribute = 13
    ReplaceShader = 14
    GroundAdaptation = 15
    Posture = 16
    Rig = 17
    Note = 18
    SetRenderingType = 19
    AddRemoveMeshAssets = 20
    TrajectoryVectorField = 21
    Group = 22
    FaceTo = 23
    LookAt = 24
    SetFrame = 25
    SetGeometryFile = 26
    BlindData = 27
    SetAttribute = 28
    MirrorGeometry = 29
    ReplaceLODDistances = 30
    EditTrajectory = 31
    OpsCount = 32 #allows to count the number of transforms types

class GlmValueType(object):
    GTV_none = 0
    GTV_char = 1    # Golaem Typed Values: char
    GTV_int32 = 2   # Golaem Typed Values: int32_t
    GTV_uint32 = 3  # Golaem Typed Values: uint32_t
    GTV_int64 = 4   # Golaem Typed Values: int64_t
    GTV_float = 5   # Golaem Typed Values: float
    GTV_vec3 = 6    # Golaem Typed Values: float[3]
    GTV_vec4 = 7    # Golaem Typed Values: float[4]

class EatWheelEventIfNoFocusFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Wheel:
            return True
        else:
            # standard event processing
            return QtCore.QObject.eventFilter(self, obj, event)

class LayoutAttributeEditor(QtWidgets.QWidget):
    """
    The GUI that allows to edit a Node that represent a Layout node in the Golaem Layout Editor
    """
    def __init__(self, parent, layoutEditor, node, editEnabled):
        """
        Initialize the widget.
        """
        super(LayoutAttributeEditor, self).__init__(parent)
        self.layoutEditor = layoutEditor
        self.node = node
        self.parent = parent
        self.nodeData = copy.deepcopy(node.userData)  # copy node user data for edition purpose
        self.preEditNodeUserData = copy.deepcopy(node.userData)  # save pre edit status

        self.wheelEater = EatWheelEventIfNoFocusFilter(self)
        self.baseWidget = None

        """
        Build or refresh the main widget.
        """
        self.windowsTitle = '{}:Selector - Attribute Editor'.format(self.node.name)
        # minimumWidth = 220
        # self.maximumHeight = 700
        self.tableMaximumHeight = 300
        self.tableMinimumWidth = 175

        nodeName = None
        nodeActive = None
        attributes = None
        selectorEntities = None
        isSelectorFilter = False
        filterPercent = 100
        filterSeed = 0
        operatorType = None
        for item in self.nodeData.items():
            if item[0] == "name":
                nodeName = item[1]
            # elif item[0] == "ID":
            #     nodeId = item[1]
            elif item[0] == "active":
                nodeActive = item[1]
            elif item[0] == 'entities':
                selectorEntities = item[1]
            elif item[0] == 'filterInput':
                isSelectorFilter = item[1] == 1
            elif item[0] == 'percent':
                filterPercent = item[1]
            elif item[0] == 'randomSeed':
                filterSeed = item[1]
            elif item[0] == 'type':
                operatorType = item[1]
            elif item[0] == 'type_name':
                self.windowsTitle = '{}: {} - Attribute Editor'.format(self.node.name, item[1])
            elif item[0] == 'attributes':
                attributes = item[1]

        #add controls
        mainLayout = QtWidgets.QVBoxLayout()

        #add node name and active status controls
        nodeNameLayout = QtWidgets.QHBoxLayout()
        nodeNameLabel = QtWidgets.QLabel(self)
        nodeNameLabel.setText('Name: ')
        nodeNameLayout.addWidget(nodeNameLabel)
        nodeNameLineEdit = QtWidgets.QLineEdit(self)
        if nodeName is not None:
            nodeNameLineEdit.setText(nodeName)
        # nodeNameLineEdit.setFixedWidth(270)
        nodeNameLineEdit.setMinimumWidth(50)
        nodeNameLineEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        nodeNameLayout.addWidget(nodeNameLineEdit)
        # nodeNameLayout.addStretch(0)
        mainLayout.addLayout(nodeNameLayout)
        #connect signal
        nodeNameLineEdit.textEdited.connect(self.onNameChanged)
        nodeNameLineEdit.editingFinished.connect(self.onEditingFinished)

        if operatorType != GlmTransformType.Note: # not notes
            nodeActiveCheckBox = QtWidgets.QCheckBox(self)
            nodeActiveCheckBox.setText('Active')
            if nodeActive!=None:
                nodeActiveCheckBox.setChecked(nodeActive)
            mainLayout.addWidget(nodeActiveCheckBox)
            #connect signal
            nodeActiveCheckBox.stateChanged.connect(self.onActiveChanged)

        #add entities controls
        if selectorEntities is not None:
            entitiesGroupBoxLayout = QtWidgets.QVBoxLayout()

            #make sure entity selection is a type string (it used to be a list, might still be in old files)
            if(type(selectorEntities)==type(list())):
                print("Selection is from an old file format, converting into string: {}".format(selectorEntities))
                selectorEntities=str(selectorEntities)
                selectorEntities = selectorEntities.strip('[')
                selectorEntities = selectorEntities.strip(']')

            entitiesValue = QtWidgets.QLineEdit(self)
            entitiesValue.setMinimumWidth(50)
            entitiesValue.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
            entitiesValue.setText(selectorEntities)
            entitiesGroupBoxLayout.addWidget(entitiesValue)

            # buttons
            entitiesButtonsWidget = QtWidgets.QWidget(self)
            entitiesButtonsLayout = QtWidgets.QHBoxLayout()
            setSelectionButton = QtWidgets.QToolButton(self)
            setSelectionButton.setText('Set')
            entitiesButtonsLayout.addWidget(setSelectionButton)
            addSelectionButton = QtWidgets.QToolButton(self)
            addSelectionButton.setText('Add')
            entitiesButtonsLayout.addWidget(addSelectionButton)
            remSelectionButton = QtWidgets.QToolButton(self)
            remSelectionButton.setText('Remove')
            entitiesButtonsLayout.addWidget(remSelectionButton)
            clrSelectionButton = QtWidgets.QToolButton(self)
            clrSelectionButton.setText('Clear')
            entitiesButtonsLayout.addWidget(clrSelectionButton)
            entitiesButtonsLayout.addStretch()
            entitiesButtonsWidget.setLayout(entitiesButtonsLayout)
            entitiesGroupBoxLayout.addWidget(entitiesButtonsWidget)

            filterCheckBox = QtWidgets.QCheckBox("Selection Filter", self)
            filterCheckBox.setChecked(isSelectorFilter)
            entitiesGroupBoxLayout.addWidget(filterCheckBox)

            entitiesGroupBox = QtWidgets.QGroupBox("Entities", self)
            entitiesGroupBox.setLayout(entitiesGroupBoxLayout)
            entitiesGroupBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
            entitiesGroupBox.updateGeometry()

            mainLayout.addWidget(entitiesGroupBox)

            percentBoxVLayout = QtWidgets.QVBoxLayout()

            percentBoxLayout = QtWidgets.QHBoxLayout()
            self.percentValue = QtWidgets.QSpinBox(self)
            self.percentValue.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            self.percentValue.setRange(0, 100)
            self.percentValue.setValue(filterPercent)
            percentBoxLayout.addWidget(self.percentValue)
            self.percentSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
            self.percentSlider.setMinimum(0)
            self.percentSlider.setMaximum(100)
            self.percentSlider.setValue(filterPercent)
            self.percentSlider.setTracking(False)
            percentBoxLayout.addWidget(self.percentSlider)
            percentBoxVLayout.addLayout(percentBoxLayout)
            randomSeedLayout = QtWidgets.QHBoxLayout()

            randomSeedLabel = QtWidgets.QLabel(self)
            randomSeedLabel.setText('Random Seed : ')
            randomSeedLayout.addWidget(randomSeedLabel)

            randomSeedValue = QtWidgets.QSpinBox(self)
            randomSeedValue.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            randomSeedValue.setRange(0, 2147483647)
            randomSeedValue.setValue(filterSeed)
            randomSeedLayout.addWidget(randomSeedValue)
            percentBoxVLayout.addLayout(randomSeedLayout)

            percentBox = QtWidgets.QGroupBox("Kept Percent", self)
            percentBox.setLayout(percentBoxVLayout)
            # percentBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
            # percentBox.updateGeometry()

            mainLayout.addWidget(percentBox)

            #connect signal
            setSelectionButton.clicked.connect(self.onSetSelectedEntitiesClicked)
            addSelectionButton.clicked.connect(self.onAddSelectedEntitiesClicked)
            remSelectionButton.clicked.connect(self.onRemoveSelectedEntitiesClicked)
            clrSelectionButton.clicked.connect(self.onClearSelectedEntitiesClicked)
            entitiesValue.textEdited.connect(self.onSelectedEntitiesValueChanged)
            entitiesValue.editingFinished.connect(self.onEditingFinished)

            filterCheckBox.stateChanged.connect(self.onFilterInputStateChanged)
            # self.percentValue.valueChanged.connect(self.onPercentValueChanged)
            self.percentValue.editingFinished.connect(self.onPercentValueEditingFinished)
            self.percentSlider.valueChanged.connect(self.onPercentSliderChanged)
            # randomSeedValue.valueChanged.connect(self.onRandomSeedValueChanged)
            randomSeedValue.editingFinished.connect(self.onRandomSeedValueEditingFinished)

        #add attributes controls
        if attributes!=None and operatorType != GlmTransformType.Group:
            attributeIndex = 0
            for attribute in attributes:

                attributeName = "Error: attribute has no name..."
                attributeFrames = None
                attributeValues = None
                attributeType = GlmValueType.GTV_none
                attributeFlags = GlmAttributeFlags._none  #_none
                for attributeItem in attribute.items():
                    if attributeItem[0] == 'name':
                        attributeName = attributeItem[1]
                    elif attributeItem[0] == 'frames':
                        attributeFrames = attributeItem[1]
                    elif attributeItem[0] == 'values':
                        attributeValues = attributeItem[1]
                    elif attributeItem[0] == 'type':
                        attributeType = attributeItem[1]
                    elif attributeItem[0] == 'flags':
                        attributeFlags = attributeItem[1]

                attributeGroupBoxLayout = QtWidgets.QVBoxLayout()

                valuesLayout = QtWidgets.QVBoxLayout()
                # snapToTarget / poptool Combo Box
                if attributeFlags&GlmAttributeFlags._uiSnapToTargetComboBox:
                    if attributeType != GlmValueType.GTV_char:
                        print(("ERROR: Attribute {} has the SnapToTargetComboBox flag but the type is not GTV_char", attributeName))
                    else:
                        valueDropDown = QtWidgets.QComboBox(self)
                        if len(self.layoutEditor.poptools) > 0:
                            for poptool in self.layoutEditor.poptools:
                                valueDropDown.addItem(poptool)
                                if (poptool == attributeValues[0]):
                                    valueDropDown.setCurrentIndex(valueDropDown.count()-1)

                        valueDropDown.currentIndexChanged.connect(self.onSnapToPoptoolComboBoxChanged)
                        valueDropDown.installEventFilter(self.wheelEater)
                        valuesLayout.addWidget(valueDropDown)
                # snaptToEntity ComboBox
                elif attributeFlags&GlmAttributeFlags._uiSnapToEntityTypeComboBox:
                    if attributeType != GlmValueType.GTV_char:
                        print(("ERROR: Attribute {} has the EntityTypeComboBox flag but the type is not GTV_char", attributeName))
                    else:
                        valueDropDown = QtWidgets.QComboBox(self)
                        if len(self.layoutEditor.entityTypes) > 0:
                            for entityType in self.layoutEditor.entityTypes:
                                valueDropDown.addItem(entityType)
                                if (entityType == attributeValues[0]):
                                    valueDropDown.setCurrentIndex(valueDropDown.count()-1)
                        valueDropDown.currentIndexChanged.connect(self.onSnapToEntityTypeComboBoxChanged)
                        valueDropDown.installEventFilter(self.wheelEater)
                        valuesLayout.addWidget(valueDropDown)
                # vectorField target Combo Box
                elif attributeFlags&GlmAttributeFlags._uiVectorFieldTargetComboBox:
                    if attributeType != GlmValueType.GTV_char:
                        print(("ERROR: Attribute {} has the VectorFieldTargetComboBox flag but the type is not GTV_char", attributeName))
                    else:
                        valueDropDown = QtWidgets.QComboBox(self)
                        if len(self.layoutEditor.vectorFields) > 0:
                            for vectorField in self.layoutEditor.vectorFields:
                                valueDropDown.addItem(vectorField)
                                if (vectorField == attributeValues[0]):
                                    valueDropDown.setCurrentIndex(valueDropDown.count()-1)

                        valueDropDown.currentIndexChanged.connect(self.onVectorFieldComboBoxChanged)
                        valueDropDown.installEventFilter(self.wheelEater)
                        valuesLayout.addWidget(valueDropDown)
                # paintedZone target Combo Box
                elif attributeFlags&GlmAttributeFlags._uiPaintedZoneTargetComboBox:
                    if attributeType != GlmValueType.GTV_char:
                        print(("ERROR: Attribute {} has the PaintedZoneTargetComboBox flag but the type is not GTV_char", attributeName))
                    else:
                        valueDropDown = QtWidgets.QComboBox(self)
                        if len(self.layoutEditor.paintedZones) > 0:
                            for paintedZone in self.layoutEditor.paintedZones:
                                valueDropDown.addItem(paintedZone)
                                if (paintedZone == attributeValues[0]):
                                    valueDropDown.setCurrentIndex(valueDropDown.count()-1)

                        valueDropDown.currentIndexChanged.connect(self.onPaintedZoneComboBoxChanged)
                        valueDropDown.installEventFilter(self.wheelEater)
                        valuesLayout.addWidget(valueDropDown)
                # bonesNames combo box
                elif attributeFlags&GlmAttributeFlags._uiBoneNamesComboBox:
                    if attributeType != GlmValueType.GTV_char:
                        print(("ERROR: Attribute {} has the BoneNamesComboBox flag but the type is not GTV_char", attributeName))
                    else:
                        valueDropDown = QtWidgets.QComboBox(self)
                        if self.layoutEditor.bonesNames is not None:
                            for boneName in self.layoutEditor.bonesNames:
                                valueDropDown.addItem(boneName)
                                if (boneName == attributeValues[0]):
                                    valueDropDown.setCurrentIndex(valueDropDown.count()-1)
                        if(valueDropDown.count()==0):
                            valueDropDown.addItem(attributeValues[0])
                            valueDropDown.setCurrentIndex(valueDropDown.count()-1)

                        valueDropDown.currentIndexChanged.connect(self.onTextEnumComboBoxChanged)
                        valueDropDown.installEventFilter(self.wheelEater)
                        valuesLayout.addWidget(valueDropDown)
                else:
                    # is keyframable ?
                    showUseKeyframesButton = attributeFlags&GlmAttributeFlags._uiKeyframable
                    if showUseKeyframesButton:
                        # use keyframes checkbox
                        useKeyframesCheckbox = QtWidgets.QCheckBox(self)
                        useKeyframesCheckbox.setText('Use Keyframes')
                        useKeyframesCheckbox.setChecked(len(attributeFrames)>0)  #true if already using keyframes, false otherwize
                        useKeyframesCheckbox.toggled.connect(self.onUseKeyframesCheckboxClicked)
                        valuesLayout.addWidget(useKeyframesCheckbox)

                    showRenderingTypeButton = attributeFlags&GlmAttributeFlags._uiRenderingTypeDropDown

                    #attributes
                    if (not showRenderingTypeButton):
                        # we need horizontal & vertical layouts with spacers to avoid blank space on small tables
                        # tableVLayout = QtWidgets.QVBoxLayout(self)
                        tableHLayout = QtWidgets.QHBoxLayout()

                        valuesTableWidget = QtWidgets.QTableWidget(self)
                        self.refreshAttributesTableWidget(valuesTableWidget, attribute)
                        valuesTableWidget.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
                        self.resizeTableToContent(valuesTableWidget)

                        tableHLayout.addWidget(valuesTableWidget)
                        tableHLayout.addStretch(1)
                        # tableVLayout.addLayout(tableHLayout)
                        # tableVLayout.addStretch(1)
                        # valuesLayout.addWidget(valuesTableWidget)

                        valuesLayout.addLayout(tableHLayout)

                    # is multi-values ?
                    showPlusMinusButtons = attributeFlags&GlmAttributeFlags._uiEnableAddRemove
                    if attributeType == GlmValueType.GTV_char:    # no multi-values for GTV_char
                        if showPlusMinusButtons:
                            print("Error on attribute '{}' defintion: GTV_char type attributes can't use the multi-values flag".format(attributeName))
                        showPlusMinusButtons = False
                    showPlusMinusButtons = showPlusMinusButtons or showUseKeyframesButton   #when an attribute is keyframable, the +/- buttons are used to add a keyframe

                    #raw of buttons before the attributes
                    if (showPlusMinusButtons): # _enableAddRemove
                        plusClearGroupBoxLayout = QtWidgets.QHBoxLayout()
                        # + button
                        valueAddButton = QtWidgets.QToolButton(self)
                        valueAddButton.setText('+')
                        valueAddButton.released.connect(self.onAddValueButtonClicked)
                        plusClearGroupBoxLayout.addWidget(valueAddButton)
                        # clear button
                        valueClearButton = QtWidgets.QPushButton(self)
                        valueClearButton.setText('Clear')
                        valueClearButton.setAutoDefault(False)
                        valueClearButton.setDefault(False)
                        valueClearButton.released.connect(self.onClearValueButtonClicked)
                        plusClearGroupBoxLayout.addWidget(valueClearButton)

                        # # entry count information
                        # too hard to keep updated as a first try, will do it later
                        # if (len(attributeValues) > 0):
                        #     entryCountLabel = QtWidgets.QLabel()
                        #     if (len(attributeValues[0]) == 1):
                        #         entryCountLabel.setText('(1 Entry)')
                        #     else:
                        #         entryCountLabel.setText('({} Entries)'.format(len(attributeValues[0])))
                        #     plusClearGroupBoxLayout.addWidget(entryCountLabel)

                        #
                        plusClearGroupBoxLayout.addStretch(0)
                        valuesLayout.addLayout(plusClearGroupBoxLayout)
                        # when not using keyframes but the button is available, disable the + and clear buttons
                        if showUseKeyframesButton and len(attributeFrames)==0:
                            valueAddButton.hide()
                            valueClearButton.hide()

                    showMeshAddRemoveDialog = attributeFlags&GlmAttributeFlags._uiAddRemoveMeshAssetDialog
                    if showMeshAddRemoveDialog:
                        showAddRemoveDialogButton = QtWidgets.QPushButton(self)
                        showAddRemoveDialogButton.setText('Add / Remove')
                        showAddRemoveDialogButton.released.connect(self.onAddRemoveMeshAssetButtonClicked)
                        valuesLayout.addWidget(showAddRemoveDialogButton)

                    showPickSelectedEntityMeshAssets = attributeFlags&GlmAttributeFlags._uiPickSelectedEntityMeshAssets
                    if showPickSelectedEntityMeshAssets:
                        pickselectedMeshAssetButton = QtWidgets.QPushButton(self)
                        pickselectedMeshAssetButton.setText('Pick From Selected Entity')
                        pickselectedMeshAssetButton.released.connect(self.onPickSelectedEntityMeshAssetClicked)
                        valuesLayout.addWidget(pickselectedMeshAssetButton)

                    if showRenderingTypeButton:
                        rtDropDown = QtWidgets.QComboBox(self)
                        if self.layoutEditor.renderingTypes is not None:
                            for renderingType in self.layoutEditor.renderingTypes:
                                rtDropDown.addItem(renderingType)
                        else:
                            for outOfRangeItem in range(0, 256):
                                rtDropDown.addItem("Value {} out of range".format(outOfRangeItem))

                        if (attributeValues[0][0] > rtDropDown.count()) :
                            for outOfRangeItem in range(rtDropDown.count(), attributeValues[0][0] + 1):
                                rtDropDown.addItem("Value {} out of range".format(outOfRangeItem))
                        rtDropDown.setCurrentIndex(attributeValues[0][0])
                        rtDropDown.installEventFilter(self.wheelEater)
                        rtDropDown.currentIndexChanged.connect(self.onEnumComboBoxChanged)
                        valuesLayout.addWidget(rtDropDown)

                #minimumWidth = max(minimumWidth, minimumAttributeWidth)
                attributeGroupBoxLayout.addLayout(valuesLayout)

                #warning flag ?
                if attributeFlags&GlmAttributeFlags._uiPerformanceWarning:
                    attributeWarningText = "Performances warning"
                    attributeWarningUrl = "www.golaem.com/content/doc/golaem-crowd-documentation/layout-editor-performances#{}{}".format(nodeName,attributeName)

                    lineLayout = QtWidgets.QHBoxLayout()
                    #lineLayout.addStretch(1)
                    # Icon
                    iconLabel = QtWidgets.QLabel(self)
                    iconPixmap = QtGui.QPixmap(os.path.join(self.layoutEditor.iconsDir, os.pardir, "warning_icon.png").replace("\\", "/"))
                    iconLabel.setPixmap(iconPixmap)
                    lineLayout.addWidget(iconLabel)
                    # hyperlink
                    warningElement = QtWidgets.QLabel(self)
                    warningElement.setText("<a href=\"{}\">{}</a>".format(attributeWarningUrl, attributeWarningText))
                    warningElement.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
                    warningElement.setOpenExternalLinks(True)
                    lineLayout.addWidget(warningElement)

                    lineLayout.addStretch(1)

                    attributeGroupBoxLayout.addLayout(lineLayout)
                    
                #finalize the groupbox
                attributeGroupBox = QtWidgets.QGroupBox(attributeName, self)
                attributeGroupBox.setObjectName(attributeName)
                attributeGroupBox.setLayout(attributeGroupBoxLayout)
                # attributeGroupBox.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
                attributeGroupBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)

                #shared attribute index for all this groupBox
                attributeGroupBox.setProperty('attributeIndex', attributeIndex)

                mainLayout.addWidget(attributeGroupBox)

                attributeIndex+=1

        #buttons OK/Cancel
        # buttonLayout = QtWidgets.QHBoxLayout()
        # buttonLayout.addStretch(0)

        # buttonOK = QtWidgets.QPushButton()
        # buttonOK.setText('OK')
        # buttonOK.setAutoDefault(True)
        # buttonOK.setDefault(True)
        # buttonOK.released.connect(self.onOkButtonClicked)
        # buttonLayout.addWidget(buttonOK)

        # buttonCancel = QtWidgets.QPushButton()
        # buttonCancel.setText('Cancel')
        # buttonCancel.released.connect(self.onCancelButtonClicked)
        # buttonLayout.addWidget(buttonCancel)

        mainLayout.addStretch(0)
        # mainLayout.addLayout(buttonLayout)

        self.baseWidget = QtWidgets.QWidget(self)
        self.baseWidget.setLayout(mainLayout)
        self.baseWidget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.baseWidget.setEnabled(editEnabled)

        scrollArea = QtWidgets.QScrollArea(self)
        scrollArea.setWidget(self.baseWidget)
        scrollArea.setWidgetResizable(True)
        # scrollArea.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)

        baseLayout = self.parent.layout()
        if baseLayout is not None:
            baseLayout = self.parent.layout()
            baseLayout.takeAt(0)
        else:
            baseLayout = QtWidgets.QVBoxLayout(self.parent)
        baseLayout.addWidget(scrollArea)

        self.setLayout(baseLayout)
        # attributeEditorWidth = self.baseWidget.sizeHint().width() + 60
        # self.setFixedWidth(attributeEditorWidth)
        # self.setMinimumWidth(300)
        # self.setWindowTitle(windowsTitle)

        # attributeEditorHeight = self.baseWidget.sizeHint().height() + 30
        # # if (attributeEditorHeight > self.maximumHeight):
        # #     attributeEditorHeight = self.maximumHeight
        # self.setMinimumHeight(attributeEditorHeight)
        # self.setMaximumHeight(self.maximumHeight)

        if (self.layoutEditor.attributeEditorPos is not None):
            self.move(self.layoutEditor.attributeEditorPos)

    def refreshAttributesTableWidget(self, valuesTableWidget, attribute):

        # get attribute info
        attributeFrames = None
        attributeValues = None
        attributeType = GlmValueType.GTV_none
        attributeFlags = GlmAttributeFlags._none
        for attributeItem in attribute.items():
            if attributeItem[0] == 'frames':
                attributeFrames = attributeItem[1]
            elif attributeItem[0] == 'values':
                attributeValues = attributeItem[1]
            elif attributeItem[0] == 'type':
                attributeType = attributeItem[1]
            elif attributeItem[0] == 'flags':
                attributeFlags = attributeItem[1]

        # add 'Frame' column ?
        addFrameToTable = False
        if (attributeFrames is not None and len(attributeFrames) > 0 and attributeValues is not None):
            addFrameToTable = True
            #make sure arrays are the same size
            while(len(attributeValues)<len(attributeFrames) ):
                attributeValues.append(attributeValues[-1]) # [-1] = last item
            while(len(attributeFrames)<len(attributeValues) ):
                attributeFrames.append(attributeFrames[-1]) # [-1] = last item

        # is '-' button ?
        showPlusMinusButtons = attributeFlags&GlmAttributeFlags._uiEnableAddRemove
        if attributeType == GlmValueType.GTV_char:    # no multi-values for GTV_char
            showPlusMinusButtons = False
        showPlusMinusButtons = showPlusMinusButtons or addFrameToTable   #when an attribute is keyframable, the +/- buttons are used to add a keyframe

        # count columns
        tableColumnCount = 0
        if addFrameToTable:
            tableColumnCount += 1

        if showPlusMinusButtons:
            tableColumnCount += 1

        #when using frames, the attributes to show are the first of each keyframe, while when not using keyframes, it's the whole list of attributes at frame0
        attributeCount = len(attributeValues)
        if not addFrameToTable:
            if attributeType == GlmValueType.GTV_char:
                attributeCount=1
            else:
                attributeCount = len(attributeValues[0])

        # GTV_char + all single values int or float
        if attributeType in [GlmValueType.GTV_char, GlmValueType.GTV_int32, GlmValueType.GTV_uint32, GlmValueType.GTV_int64, GlmValueType.GTV_float]:
            tableColumnCount += 1
        elif attributeType == GlmValueType.GTV_vec3:    # GTV_vec3
            tableColumnCount += 3
        elif attributeType == GlmValueType.GTV_vec4:    # GTV_vec4
            if attributeFlags&GlmAttributeFlags._uiColorWheel:
                tableColumnCount += 1
            else:
                tableColumnCount += 4

        valuesTableWidget.clear()
        valuesTableWidget.setObjectName("ValuesTable")
        valuesTableWidget.setProperty('addFrameToTable', addFrameToTable)
        valuesTableWidget.setProperty('showPlusMinusButtons', showPlusMinusButtons)
        valuesTableWidget.setColumnCount(tableColumnCount)
        valuesTableWidget.setRowCount(min(self.layoutEditor.maxTablesDisplayCount,attributeCount))

        #add rows
        valuesTableWidget.blockSignals(True)
        for iFrame in range(min(self.layoutEditor.maxTablesDisplayCount,len(attributeValues))):
            if attributeType == GlmValueType.GTV_char:  # GTV_char have 1 widget for all char values
                value = attributeValues[iFrame]
                frame = -1
                if(addFrameToTable):
                    frame = attributeFrames[iFrame]
                testColumnIndex = 0
                if addFrameToTable:
                    testColumnIndex = 1
                valuesTableWidget.setColumnWidth(testColumnIndex, self.tableMinimumWidth)
                self.setTableRowWidgets(valuesTableWidget, attributeType, attributeFlags, addFrameToTable, showPlusMinusButtons, iFrame, value, frame)
            else:   # other types have 1 widget per value
                for iValue in range(min(self.layoutEditor.maxTablesDisplayCount,len(attributeValues[iFrame]))):
                    value = attributeValues[iFrame][iValue]
                    frame = -1
                    if(addFrameToTable):
                        frame = attributeFrames[iFrame]
                    self.setTableRowWidgets(valuesTableWidget, attributeType, attributeFlags, addFrameToTable, showPlusMinusButtons, iFrame+iValue, value, frame)
        valuesTableWidget.blockSignals(False)

        # add frame number if requested
        iColumn = 0
        tableHeader = []
        if (addFrameToTable):
            tableHeader.append("Frames")
            iColumn += 1

        # then add value(s)
        if attributeType in [GlmValueType.GTV_char, GlmValueType.GTV_int32, GlmValueType.GTV_uint32, GlmValueType.GTV_int64, GlmValueType.GTV_float]:
            tableHeader.append("Value")
            iColumn += 1
        elif attributeType == GlmValueType.GTV_vec3:
            tableHeader.append("X")
            tableHeader.append("Y")
            tableHeader.append("Z")
            iColumn += 3
        elif attributeType == GlmValueType.GTV_vec4:
            if attributeFlags&GlmAttributeFlags._uiColorWheel:
                tableHeader.append("Color")
                iColumn += 1
            else:
                tableHeader.append("X")
                tableHeader.append("Y")
                tableHeader.append("Z")
                tableHeader.append("W")
                iColumn += 4

        # then add - button if requested
        if (showPlusMinusButtons): # _enableAddRemove
            valuesTableWidget.setColumnWidth(iColumn, 22)
            tableHeader.append("") # no header for the minus button

        if (len(tableHeader) == 1 or (len(tableHeader) == 2 and showPlusMinusButtons)):
            valuesTableWidget.horizontalHeader().setHidden(True)
        else:
            valuesTableWidget.setHorizontalHeaderLabels(tableHeader)
            valuesTableWidget.horizontalHeader().setHidden(False)
        valuesTableWidget.verticalHeader().setHidden(True)

    def setSnapToAttributesUI(self):
        if (self.snapToPosValues is None or self.snapToOriValues is None):
            return

        attributes = None
        nodeData = self.nodeData

        snapToPosAttributeBox = self.findChild(QtWidgets.QGroupBox, u'snapToPos')
        snapToOriAttributeBox = self.findChild(QtWidgets.QGroupBox, u'snapToOri')

        if (snapToPosAttributeBox is None or snapToOriAttributeBox is None):
            return

        snapToPosTableWidget = self.getTableFromAttributeBox(snapToPosAttributeBox)
        snapToOriTableWidget = self.getTableFromAttributeBox(snapToOriAttributeBox)

        if (snapToPosTableWidget is None or snapToOriTableWidget is None):
            return

        for item in nodeData.items():
            attributes = None
            if item[0] == 'attributes':
                attributes = item[1]

            if attributes!=None:
                for attribute in attributes:
                    attributeName = None
                    attributeValue = None
                    attributeType = None
                    attributeFlags = None
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                        elif attributeItem[0] == "type":
                            attributeType = attributeItem[1]
                        elif attributeItem[0] == "values":
                            attributeValue = attributeItem[1]
                        if attributeItem[0] == "flags":
                            attributeFlags = attributeItem[1]

                    if (attributeName!=None) and (attributeValue!=None):
                        if (attributeName == "snapToPos"):
                            attribute["values"] = self.snapToPosValues
                            self.setSnapToTableValues(snapToPosTableWidget, self.snapToPosValues, attributeType, attributeFlags)
                        if (attributeName == "snapToOri"):
                            attribute["values"] = self.snapToOriValues
                            self.setSnapToTableValues(snapToOriTableWidget, self.snapToOriValues, attributeType, attributeFlags)

        self.resizeTableToContent(snapToPosTableWidget)
        self.resizeTableToContent(snapToOriTableWidget)

    def setVectorFieldNormalMapUI(self):
        if (self.vectorFieldMap is None):
            return

        vectorFieldMapAttributeBox = self.findChild(QtWidgets.QGroupBox, 'map')
        if (vectorFieldMapAttributeBox is None):
            return

        vectorFieldMapTableWidget = self.getTableFromAttributeBox(vectorFieldMapAttributeBox)
        if (vectorFieldMapTableWidget is None):
            return

        for item in self.nodeData.items():
            attributes = None
            if item[0] == 'attributes':
                attributes = item[1]

            if attributes is not None:
                for attribute in attributes:
                    attributeName = None
                    attributeValue = None
                    # attributeType = None
                    # attributeFlags = None
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                        # elif attributeItem[0] == "type":
                        #     attributeType = attributeItem[1]
                        elif attributeItem[0] == "values":
                            attributeValue = attributeItem[1]
                        # elif attributeItem[0] == "flags":
                        #     attributeFlags = attributeItem[1]

                    if (attributeName!=None) and (attributeValue!=None):
                        if (attributeName == "map"):
                            attribute["values"] = list()
                            attribute["values"].append(self.vectorFieldMap)
                            iRow = 0
                            iColumn = 0
                            valueTableElement = vectorFieldMapTableWidget.cellWidget(iRow, iColumn)
                            if (valueTableElement is None):
                                # Image display
                                valueTableElement = QtWidgets.QLabel(self)
                                valueTableElement.setFixedHeight(150) # cell widget height
                                vectorFieldMapTableWidget.setRowHeight(iRow, 150) # table height
                                valueTableElement.setMinimumWidth(self.tableMinimumWidth)
                                vectorFieldMapTableWidget.setCellWidget(iRow, iColumn, valueTableElement)

                            valueTableElement.blockSignals(True)
                            try:
                                imagePixmap = QtGui.QPixmap.fromImage(QtGui.QImage.fromData(bytes(base64.b64decode(self.vectorFieldMap))))
                                pixampRect = imagePixmap.rect()
                                if(pixampRect.height()>1024):
                                    pixampRect.setHeight(1024)
                                if(pixampRect.width()>1024):
                                    pixampRect.setWidth(1024)
                                vectorFieldMapTableWidget.setRowHeight(iRow, pixampRect.height()) # table height
                                vectorFieldMapTableWidget.setColumnWidth(iColumn, pixampRect.width())  # table width
                                valueTableElement.setMinimumWidth(pixampRect.width()) # mandatory before loading the pixmap or it will be cropped
                                valueTableElement.setMinimumHeight(pixampRect.height()) # mandatory before loading the pixmap or it will be cropped
                                valueTableElement.setFrameRect(pixampRect)
                                valueTableElement.setPixmap(imagePixmap)
                            except:
                                print("Error: invalid image")
                            valueTableElement.blockSignals(False)

        self.resizeTableToContent(vectorFieldMapTableWidget)  # mandatory or the map table widget won't be resized accordingly

    def setVectorFieldGeometryUI(self):
        if (self.vectorFieldGeometry is None):
            return

        vectorFieldGeometryVerticesAttributeBox = self.findChild(QtWidgets.QGroupBox, 'geoVertices')
        vectorFieldGeometryNormalsAttributeBox = self.findChild(QtWidgets.QGroupBox, 'geoNormals')
        vectorFieldGeometryUVsAttributeBox = self.findChild(QtWidgets.QGroupBox, 'geoUVs')
        vectorFieldGeometryTrianglesAttributeBox = self.findChild(QtWidgets.QGroupBox, 'geoTriangles')
        if ((vectorFieldGeometryVerticesAttributeBox is None) or (vectorFieldGeometryNormalsAttributeBox is None) or (vectorFieldGeometryUVsAttributeBox is None) or (vectorFieldGeometryTrianglesAttributeBox is None)):
            return

        vectorFieldGeometryVerticesTableWidget = self.getTableFromAttributeBox(vectorFieldGeometryVerticesAttributeBox)
        vectorFieldGeometryNormalsTableWidget = self.getTableFromAttributeBox(vectorFieldGeometryNormalsAttributeBox)
        vectorFieldGeometryUVsTableWidget = self.getTableFromAttributeBox(vectorFieldGeometryUVsAttributeBox)
        vectorFieldGeometryTrianglesTableWidget = self.getTableFromAttributeBox(vectorFieldGeometryTrianglesAttributeBox)
        if((vectorFieldGeometryVerticesTableWidget is None) or(vectorFieldGeometryNormalsAttributeBox is None) or (vectorFieldGeometryUVsAttributeBox is None) or(vectorFieldGeometryTrianglesTableWidget is None)):
            return

        for item in self.nodeData.viewitems():
            attributes = None
            if item[0] == 'attributes':
                attributes = item[1]

            if attributes!=None:
                for attribute in attributes:
                    attributeName = None
                    attributeValue = None
                    #attributeType = None
                    #attributeFlags = None
                    for attributeItem in attribute.viewitems():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                        # elif attributeItem[0] == "type":
                        #     attributeType = attributeItem[1]
                        elif attributeItem[0] == "values":
                            attributeValue = attributeItem[1]
                        # elif attributeItem[0] == "flags":
                        #     attributeFlags = attributeItem[1]

                    if (attributeName!=None) and (attributeValue!=None):
                        if (attributeName == "geoVertices"):
                            attribute["values"] = list()
                            attribute["values"].append(self.vectorFieldGeometry[0])
                            # iRow = 0
                            # iColumn = 0
                            # valueTableElement = vectorFieldGeometryTableWidget.cellWidget(iRow, iColumn)
                            # valueTableElement.setText(self.vectorFieldGeometry)
                        elif (attributeName == "geoNormals"):
                            attribute["values"] = list()
                            attribute["values"].append(self.vectorFieldGeometry[1])
                        elif (attributeName == "geoUVs"):
                            attribute["values"] = list()
                            attribute["values"].append(self.vectorFieldGeometry[2])
                        elif (attributeName == "geoTriangles"):
                            attribute["values"] = list()
                            attribute["values"].append(self.vectorFieldGeometry[3])

        self.resizeTableToContent(vectorFieldGeometryVerticesTableWidget)  # mandatory or the map table widget won't be resized accordingly
        self.resizeTableToContent(vectorFieldGeometryNormalsTableWidget) # mandatory or the map table widget won't be resized accordingly
        self.resizeTableToContent(vectorFieldGeometryUVsTableWidget)  # mandatory or the map table widget won't be resized accordingly
        self.resizeTableToContent(vectorFieldGeometryTrianglesTableWidget) # mandatory or the map table widget won't be resized accordingly

    def setPaintedZoneNormalMapUI(self):
        if (self.paintedZoneMap is None):
            return

        paintedZoneMapAttributeBox = self.findChild(QtWidgets.QGroupBox, 'map')
        if (paintedZoneMapAttributeBox is None):
            return

        paintedZoneMapTableWidget = self.getTableFromAttributeBox(paintedZoneMapAttributeBox)
        if (paintedZoneMapTableWidget is None):
            return

        for item in self.nodeData.items():
            attributes = None
            if item[0] == 'attributes':
                attributes = item[1]

            if attributes is not None:
                for attribute in attributes:
                    attributeName = None
                    attributeValue = None
                    # attributeType = None
                    # attributeFlags = None
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                        # elif attributeItem[0] == "type":
                        #     attributeType = attributeItem[1]
                        elif attributeItem[0] == "values":
                            attributeValue = attributeItem[1]
                        # elif attributeItem[0] == "flags":
                        #     attributeFlags = attributeItem[1]

                    if (attributeName!=None) and (attributeValue!=None):
                        if (attributeName == "map"):
                            attribute["values"] = list()
                            attribute["values"].append(self.paintedZoneMap)
                            iRow = 0
                            iColumn = 0
                            valueTableElement = paintedZoneMapTableWidget.cellWidget(iRow, iColumn)
                            if (valueTableElement is None):
                                # Image display
                                valueTableElement = QtWidgets.QLabel(self)
                                valueTableElement.setFixedHeight(150) # cell widget height
                                paintedZoneMapTableWidget.setRowHeight(iRow, 150) # table height
                                valueTableElement.setMinimumWidth(self.tableMinimumWidth)
                                paintedZoneMapTableWidget.setCellWidget(iRow, iColumn, valueTableElement)

                            valueTableElement.blockSignals(True)
                            try:
                                imagePixmap = QtGui.QPixmap.fromImage(QtGui.QImage.fromData(bytes(base64.b64decode(self.paintedZoneMap))))
                                pixampRect = imagePixmap.rect()
                                if(pixampRect.height()>1024):
                                    pixampRect.setHeight(1024)
                                if(pixampRect.width()>1024):
                                    pixampRect.setWidth(1024)
                                paintedZoneMapTableWidget.setRowHeight(iRow, pixampRect.height()) # table height
                                paintedZoneMapTableWidget.setColumnWidth(iColumn, pixampRect.width())  # table width
                                valueTableElement.setMinimumWidth(pixampRect.width()) # mandatory before loading the pixmap or it will be cropped
                                valueTableElement.setMinimumHeight(pixampRect.height()) # mandatory before loading the pixmap or it will be cropped
                                valueTableElement.setFrameRect(pixampRect)
                                valueTableElement.setPixmap(imagePixmap)
                            except:
                                print("Error: invalid image")
                            valueTableElement.blockSignals(False)

        self.resizeTableToContent(paintedZoneMapTableWidget)  # mandatory or the map table widget won't be resized accordingly        

    def setPaintedZoneGeometryUI(self):
        if (self.paintedZoneGeometry is None):
            return

        paintedZoneGeometryVerticesAttributeBox = self.findChild(QtWidgets.QGroupBox, 'geoVertices')
        paintedZoneGeometryNormalsAttributeBox = self.findChild(QtWidgets.QGroupBox, 'geoNormals')
        paintedZoneGeometryUVsAttributeBox = self.findChild(QtWidgets.QGroupBox, 'geoUVs')
        paintedZoneGeometryTrianglesAttributeBox = self.findChild(QtWidgets.QGroupBox, 'geoTriangles')
        if ((paintedZoneGeometryVerticesAttributeBox is None) or (paintedZoneGeometryNormalsAttributeBox is None) or (paintedZoneGeometryUVsAttributeBox is None) or (paintedZoneGeometryTrianglesAttributeBox is None)):
            return

        paintedZoneGeometryVerticesTableWidget = self.getTableFromAttributeBox(paintedZoneGeometryVerticesAttributeBox)
        paintedZoneGeometryNormalsTableWidget = self.getTableFromAttributeBox(paintedZoneGeometryNormalsAttributeBox)
        paintedZoneGeometryUVsTableWidget = self.getTableFromAttributeBox(paintedZoneGeometryUVsAttributeBox)
        paintedZoneGeometryTrianglesTableWidget = self.getTableFromAttributeBox(paintedZoneGeometryTrianglesAttributeBox)
        if((paintedZoneGeometryVerticesTableWidget is None) or(paintedZoneGeometryNormalsAttributeBox is None) or (paintedZoneGeometryUVsAttributeBox is None) or(paintedZoneGeometryTrianglesTableWidget is None)):
            return

        for item in self.nodeData.items():
            attributes = None
            if item[0] == 'attributes':
                attributes = item[1]

            if attributes!=None:
                for attribute in attributes:
                    attributeName = None
                    attributeValue = None
                    #attributeType = None
                    #attributeFlags = None
                    for attributeItem in attribute.items():
                        if attributeItem[0] == "name":
                            attributeName = attributeItem[1]
                        # elif attributeItem[0] == "type":
                        #     attributeType = attributeItem[1]
                        elif attributeItem[0] == "values":
                            attributeValue = attributeItem[1]
                        # elif attributeItem[0] == "flags":
                        #     attributeFlags = attributeItem[1]

                    if (attributeName!=None) and (attributeValue!=None):
                        if (attributeName == "geoVertices"):
                            attribute["values"] = list()
                            attribute["values"].append(self.paintedZoneGeometry[0])
                            # iRow = 0
                            # iColumn = 0
                            # valueTableElement = paintedZoneGeometryTableWidget.cellWidget(iRow, iColumn)
                            # valueTableElement.setText(self.paintedZoneGeometry)
                        elif (attributeName == "geoNormals"):
                            attribute["values"] = list()
                            attribute["values"].append(self.paintedZoneGeometry[1])
                        elif (attributeName == "geoUVs"):
                            attribute["values"] = list()
                            attribute["values"].append(self.paintedZoneGeometry[2])
                        elif (attributeName == "geoTriangles"):
                            attribute["values"] = list()
                            attribute["values"].append(self.paintedZoneGeometry[3])

        self.resizeTableToContent(paintedZoneGeometryVerticesTableWidget)  # mandatory or the map table widget won't be resized accordingly
        self.resizeTableToContent(paintedZoneGeometryNormalsTableWidget) # mandatory or the map table widget won't be resized accordingly
        self.resizeTableToContent(paintedZoneGeometryUVsTableWidget)  # mandatory or the map table widget won't be resized accordingly
        self.resizeTableToContent(paintedZoneGeometryTrianglesTableWidget) # mandatory or the map table widget won't be resized accordingly


    def getTableFromAttributeBox(self, attributeBox):
        # find child goes recursively in children
        tableWidget = attributeBox.findChild(QtWidgets.QTableWidget, u'ValuesTable')
        return tableWidget

    def resizeTableToContent(self, tableWidget):
        tableWidth = tableWidget.horizontalHeader().length()
        if (tableWidget.verticalHeaderItem(0) is not None):
            tableWidth += tableWidget.verticalHeader().width()

        tableHeight = tableWidget.verticalHeader().length()
        if (tableWidget.horizontalHeaderItem(0) is not None):
            tableHeight += tableWidget.horizontalHeader().height()
        tableWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        rowCount = tableWidget.rowCount()
        if rowCount > 1 or tableWidget.horizontalHeaderItem(0) is not None:
            tableHeight += 2 * tableWidget.frameWidth()  # looks like we need to count 2 frame width to be correct

        columnCount = tableWidget.columnCount()
        if (columnCount > 1):
            tableWidth += 2*tableWidget.frameWidth() # looks like we need to count 2 frame width to be correct

        if (tableHeight > self.tableMaximumHeight and tableWidget.rowCount() > 1): # if rowcount is 1, we allow images table of 1024
            tableHeight = self.tableMaximumHeight
            tableWidth += tableWidget.verticalScrollBar().sizeHint().width()  # scroll bar size

        tableWidget.setFixedSize(tableWidth, tableHeight)

        tableWidget.updateGeometry()
        tableWidget.hide()
        tableWidget.show() # need to force display to get right sizeHint


    def setSnapToTableValues(self, tableWidget, values, attributeType, attributeFlags):
        tableWidget.blockSignals(True)
        # first we must resize columns to the right type and add minus buttons :
        rowCount = min(self.layoutEditor.maxTablesDisplayCount, len(values[0]))
        tableWidget.setRowCount(rowCount)

        for iRow in range(rowCount):
            self.setTableRowWidgets(tableWidget, attributeType, attributeFlags, False, True,  iRow, values[0][iRow], -1)  # addFrameToTable always false, show plus minus always true for snapTo

        self.resizeTableToContent(tableWidget)

        tableWidget.blockSignals(False)

    def setTableRowWidgets(self, valuesTableWidget, attributeType, attributeFlags, addFrameToTable, showPlusMinusButtons, iRow, value, frame):
        useComboBox = False
        comboBoxList = None
        if attributeFlags&GlmAttributeFlags._uiSelectedCharMeshAssetComboBox:
            useComboBox = True
            comboBoxList = self.layoutEditor.selectedCharacterMeshAssets

        if attributeFlags&GlmAttributeFlags._uiOperationModeComboBox:
            useComboBox = True
            comboBoxList = self.layoutEditor.operationModeList

        if attributeFlags&GlmAttributeFlags._uiGroundAdaptationModeComboBox:
            useComboBox = True
            comboBoxList = self.layoutEditor.groundAdaptationModeList

        if attributeFlags&GlmAttributeFlags._uiOnOffComboBox:
            useComboBox = True
            comboBoxList = self.layoutEditor.onOffList

        if attributeFlags&GlmAttributeFlags._uiColorChannelComboBox:
            useComboBox = True
            comboBoxList = self.layoutEditor.colorChannelList

        if attributeFlags&GlmAttributeFlags._uiRotateOrderComboBox:
            useComboBox = True
            comboBoxList = self.layoutEditor.rotateOrderList

        isAnImage = False
        if attributeFlags&GlmAttributeFlags._uiImage:
            isAnImage = True

        # add frame number if requested
        iColumn = 0
        if (addFrameToTable):
            frameTableElement = valuesTableWidget.cellWidget(iRow, iColumn)
            if (frameTableElement is None):
                frameTableElement = QtWidgets.QDoubleSpinBox(self)
                frameTableElement.setButtonSymbols(
                    QtWidgets.QAbstractSpinBox.NoButtons)
                frameTableElement.setRange(-10000, 10000)
                valuesTableWidget.setCellWidget(iRow, iColumn, frameTableElement)
                valuesTableWidget.setColumnWidth(iColumn, 68)
                frameTableElement.installEventFilter(self.wheelEater)
                frameTableElement.valueChanged.connect(self.onTableValueChanged)
                frameTableElement.editingFinished.connect(self.onEditingFinished)
            frameTableElement.blockSignals(True)
            frameTableElement.setValue(frame)
            frameTableElement.blockSignals(False)
            iColumn += 1

        # then add value(s)
        if attributeType == GlmValueType.GTV_char and isAnImage:
            valueTableElement = valuesTableWidget.cellWidget(iRow, iColumn)
            if (valueTableElement is None):
                # Image display
                valueTableElement = QtWidgets.QLabel(self)
                valueTableElement.setFixedHeight(150) # cell widget height
                valuesTableWidget.setRowHeight(iRow, 150) # table height
                valueTableElement.setMinimumWidth(self.tableMinimumWidth)
                valuesTableWidget.setCellWidget(iRow, iColumn, valueTableElement)

            valueTableElement.blockSignals(True)
            try:
                imagePixmap = QtGui.QPixmap.fromImage(QtGui.QImage.fromData(bytes(base64.b64decode(value))))
                pixampRect = imagePixmap.rect()
                if(pixampRect.height()>1024):
                    pixampRect.setHeight(1024)
                if(pixampRect.width()>1024):
                    pixampRect.setWidth(1024)
                valuesTableWidget.setRowHeight(iRow, pixampRect.height()) # table height
                valuesTableWidget.setColumnWidth(iColumn, pixampRect.width()) # table width
                valueTableElement.setMinimumWidth(pixampRect.width()) # mandatory before loading the pixmap or it will be cropped
                valueTableElement.setMinimumHeight(pixampRect.height()) # mandatory before loading the pixmap or it will be cropped
                valueTableElement.setFrameRect(pixampRect)
                valueTableElement.setPixmap(imagePixmap)
            except:
                print("Error: invalid image")
            valueTableElement.blockSignals(False)

            iColumn += 1
        elif attributeType == GlmValueType.GTV_char:    # GTV_char, // Golaem Typed Values: char
            valueTableElement = valuesTableWidget.cellWidget(iRow, iColumn)
            if (valueTableElement is None):
                if attributeFlags&GlmAttributeFlags._uiTextEdit:
                    # Text Edit
                    # make table row higher
                    valuesTableWidget.row
                    valueTableElement = QtWidgets.QTextEdit(self)
                    valueTableElement.setFixedHeight(150) # cell widget height
                    valuesTableWidget.setRowHeight(iRow, 150) # table height
                    valueTableElement.ensureCursorVisible()
                    valueTableElement.textChanged.connect(self.onTableStringValueChanged)
                    valueTableElement.focusOutEvent = self.onEditingFinished
                else:
                    # Line Edit
                    valueTableElement = QtWidgets.QLineEdit(self)
                    valueTableElement.textEdited.connect(self.onTableStringValueChanged)
                    valueTableElement.focusOutEvent = self.onEditingFinished
                valueTableElement.setMinimumWidth(self.tableMinimumWidth)
                valuesTableWidget.setCellWidget(iRow, iColumn, valueTableElement)

            valueTableElement.blockSignals(True)
            valueTableElement.setText(value)
            valueTableElement.blockSignals(False)
            iColumn += 1
        elif attributeType == GlmValueType.GTV_uint32 and useComboBox:
            valueTableElement = valuesTableWidget.cellWidget(iRow, iColumn)
            if (valueTableElement is None):
                # displays a combo box per cell, with "out of range value x" displayed if not in range
                valueTableElement = QtWidgets.QComboBox(self)
                comboBoxListLen = 0
                if comboBoxList is not None:
                    comboBoxListLen = len(comboBoxList)
                if comboBoxListLen > 0:
                    for comboValue in comboBoxList:
                        valueTableElement.addItem(comboValue)
                else:
                    # if no list is found, complete with 0-255 possible value range
                    for iOutOfRangeValue in range(0,255):
                        valueTableElement.addItem("Value {} out of range".format(iOutOfRangeValue))

                if value >= comboBoxListLen: # complete out of range value to be able to conserve the attribute original value
                    for iOutOfRangeValue in range(comboBoxListLen, value+1):
                        valueTableElement.addItem("Value {} out of range".format(iOutOfRangeValue))
                valueTableElement.setMinimumWidth(self.tableMinimumWidth)
                # valueTableElement.setFixedWidth(300)
                valuesTableWidget.setCellWidget(iRow, iColumn, valueTableElement)
                valueTableElement.installEventFilter(self.wheelEater)
                valueTableElement.currentIndexChanged.connect(self.onTableComboBoxValueChanged)
                valuesTableWidget.setColumnWidth(iColumn, self.tableMinimumWidth)  # ici nico
            valueTableElement.blockSignals(True)
            valueTableElement.setCurrentIndex(value)
            valueTableElement.blockSignals(False)
            iColumn += 1
        elif attributeType in [ GlmValueType.GTV_int32,  GlmValueType.GTV_uint32,  GlmValueType.GTV_int64]:    #all integer types
            valueTableElement = valuesTableWidget.cellWidget(iRow, iColumn)
            if (valueTableElement is None):
                valueTableElement = QtWidgets.QSpinBox(self)
                valueTableElement.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                if (attributeType == GlmValueType.GTV_int32):
                    valueTableElement.setRange(-2147483647, 2147483647)
                elif (attributeType == GlmValueType.GTV_uint32):
                    valueTableElement.setRange(0, 2147483647)
                elif (attributeType == GlmValueType.GTV_int64):
                    valueTableElement.setRange(-2147483647, 2147483647)
                # valueTableElement.setMinimumWidth(68)
                valuesTableWidget.setCellWidget(iRow, iColumn, valueTableElement)
                valuesTableWidget.setColumnWidth(iColumn, 68)
                valueTableElement.valueChanged.connect(self.onTableValueChanged)
                valueTableElement.editingFinished.connect(self.onEditingFinished)
                valueTableElement.installEventFilter(self.wheelEater)
            valueTableElement.blockSignals(True)
            valueTableElement.setValue(value)
            valueTableElement.blockSignals(False)
            iColumn += 1
        elif attributeType == GlmValueType.GTV_float:
            valueTableElement = valuesTableWidget.cellWidget(iRow, iColumn)
            if (valueTableElement is None):
                valueTableElement = QtWidgets.QDoubleSpinBox(self)
                valueTableElement.setButtonSymbols(
                    QtWidgets.QAbstractSpinBox.NoButtons)
                valueTableElement.setRange(-3.4e+38,3.4e+38)
                # valueTableElement.setMinimumWidth(68)
                valuesTableWidget.setCellWidget(iRow, iColumn, valueTableElement)
                valueTableElement.installEventFilter(self.wheelEater)
                valuesTableWidget.setColumnWidth(iColumn, 68)
                valueTableElement.valueChanged.connect(self.onTableValueChanged)
                valueTableElement.editingFinished.connect(self.onEditingFinished)
            valueTableElement.blockSignals(True)
            valueTableElement.setValue(value)
            valueTableElement.blockSignals(False)
            iColumn += 1
        elif attributeType == GlmValueType.GTV_vec3:
            for iSubElement in range(3):
                valueTableElement = valuesTableWidget.cellWidget(iRow, iColumn)
                if (valueTableElement is None):
                    valueTableElement = QtWidgets.QDoubleSpinBox(self)
                    valueTableElement.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                    valueTableElement.setRange(-3.4e+38,3.4e+38)
                    # valueTableElement.setMinimumWidth(68)
                    valuesTableWidget.setCellWidget(iRow, iColumn, valueTableElement)
                    valueTableElement.installEventFilter(self.wheelEater)
                    valuesTableWidget.setColumnWidth(iColumn, 68)
                    valueTableElement.valueChanged.connect(self.onTableValueChanged)
                    valueTableElement.editingFinished.connect(self.onEditingFinished)
                valueTableElement.blockSignals(True)
                valueTableElement.setValue(value[iSubElement])
                valueTableElement.blockSignals(False)
                iColumn += 1
        elif attributeType == GlmValueType.GTV_vec4:
            # color wheel : color rectangle + onPressEvent
            if attributeFlags&GlmAttributeFlags._uiColorWheel:
                valueTableElement = valuesTableWidget.cellWidget(iRow, iColumn)
                if (valueTableElement is None):
                    valueTableElement = QtWidgets.QPushButton(self)
                    valueTableElement.setText("")
                    valueTableElement.setAutoFillBackground(True)
                    valueTableElement.setFlat(True)
                    valueTableElement.setAutoDefault(False)
                    valueTableElement.setDefault(False)
                    valuesTableWidget.setCellWidget(iRow, iColumn, valueTableElement)
                    valuesTableWidget.setColumnWidth(iColumn, 68)
                    valueTableElement.update()
                    # valueTableElement.valueChanged.connect(self.onTableValueChanged)
                    valueTableElement.released.connect(self.onColorPressed)
                valueTableElement.blockSignals(True)
                palette = valueTableElement.palette()
                currentColor = QtGui.QColor(value[0], value[1], value[2], value[3])
                palette.setColor(QtGui.QPalette.Window, currentColor)
                palette.setColor(QtGui.QPalette.Button, currentColor)
                valueTableElement.setPalette(palette)
                valueTableElement.blockSignals(False)
                iColumn += 1
            else:
                for iSubElement in range(4):
                    valueTableElement = valuesTableWidget.cellWidget(iRow, iColumn)
                    if (valueTableElement is None):
                        valueTableElement = QtWidgets.QDoubleSpinBox(self)
                        valueTableElement.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                        valueTableElement.setRange(-3.4e+38,3.4e+38)
                        valuesTableWidget.setColumnWidth(iColumn, 68)
                        valuesTableWidget.setCellWidget(iRow, iColumn, valueTableElement)
                        valueTableElement.installEventFilter(self.wheelEater)
                        valueTableElement.valueChanged.connect(self.onTableValueChanged)
                        valueTableElement.editingFinished.connect(self.onEditingFinished)
                    valueTableElement.blockSignals(True)
                    valueTableElement.setValue(value[iSubElement])
                    valueTableElement.blockSignals(False)
                    iColumn += 1

        # then add - button if requested
        if (showPlusMinusButtons): # _enableAddRemove
                minusButtonElement = valuesTableWidget.cellWidget(iRow, iColumn)
                if (minusButtonElement is None):
                    minusButtonElement = QtWidgets.QToolButton(self)
                    minusButtonElement.setText('-')
                    minusButtonElement.released.connect(self.onRemoveValueButtonClicked)
                    minusButtonElement.setMinimumWidth(20)
                    minusButtonElement.setMaximumHeight(20)
                    minusButtonElement.setMaximumWidth(20)
                    valuesTableWidget.setCellWidget(iRow, iColumn, minusButtonElement)

    # https://stackoverflow.com/questions/8766633/how-to-determine-the-correct-size-of-a-qtablewidget
    # replaced by horizontal header  and verticla header length + width or height of the other
    # def getQTableWidgetSize(self, tableWidget, maxHeight):
    #     w = 4
    #     if (not tableWidget.verticalHeader().isHidden()):
    #         w += tableWidget.verticalHeader().sizeHint().width() + 2
    #     columnCount = tableWidget.columnCount()
    #     for i in range(columnCount) :
    #         w += tableWidget.columnWidth(i)

    #     h = 4
    #     if (not tableWidget.horizontalHeader().isHidden()):
    #         h += tableWidget.horizontalHeader().sizeHint().height() + 2
    #     rowCount = tableWidget.rowCount()
    #     for i in range(rowCount):
    #         h += tableWidget.rowHeight(i)

    #     if (h > maxHeight):
    #         #we will have a slider, add its space
    #         h = maxHeight
    #         w += 15  # allocate 20 pixels for vertical slider

    #     return QtCore.QSize(w, h)

    def getThisOrParentProperty(self, aWidget, propertyName):
        currentWidget = aWidget
        while (currentWidget is not None):
            propertyValue = currentWidget.property(propertyName)
            if (propertyValue is not None):
                return propertyValue

            # poll all parents layout
            thisLayout = currentWidget.layout()
            previousLayout = 0
            while (thisLayout is not None and previousLayout != thisLayout ):
                propertyValue = thisLayout.property(propertyName)
                if (propertyValue is not None):
                    return propertyValue
                previousLayout = thisLayout
                thisLayout = thisLayout.layout()

            currentWidget = currentWidget.parentWidget()
        return None

    def addTableRow(self, attributeType, attributeFlags, tableWidget, value, frame):
        hasFrame = tableWidget.property("addFrameToTable")
        showPlusMinusButtons = tableWidget.property('showPlusMinusButtons')

        iRow = tableWidget.rowCount()
        # values have been added, now add UI :
        # add the line
        tableWidget.insertRow(iRow)
        self.setTableRowWidgets(tableWidget, attributeType, attributeFlags, hasFrame, showPlusMinusButtons, iRow, value, frame)

        vHeader = tableWidget.verticalHeader()
        tableHeight = min(self.tableMaximumHeight, vHeader.length())
        tableWidget.setFixedHeight(tableHeight)
        # tableWidget.setMaximumHeight(tableHeight)


        # size = self.getQTableWidgetSize(tableWidget, self.tableMaximumHeight)
        # tableWidget.setFixedSize(size) # table geometry will be update as a whole after all lines additions


    # add action on key to save the model from the current file
    def onEditingFinished(self, event=None):
        self.dataEdited()

    def onNameChanged(self, value):
        if 'name' not in self.nodeData:
            self.nodeData.append('name')
        self.nodeData['name'] = value

    def onActiveChanged(self, value):
        if 'active' not in self.nodeData:
            self.nodeData.append('active')
        self.nodeData['active'] = value
        self.dataEdited()

    def onSelectedEntitiesValueChanged(self, value):
        if 'entities' in self.nodeData:
            self.nodeData['entities'] = value

    def onFilterInputStateChanged(self):
        if 'filterInput' in self.nodeData:
            if self.sender().isChecked():
                self.nodeData['filterInput'] = 1
            else:
                self.nodeData['filterInput'] = 0
            self.dataEdited()

    def onPercentValueEditingFinished(self):
        if 'percent' in self.nodeData:
            self.nodeData['percent'] = self.percentValue.value()  # self.sender().value()
            self.percentSlider.setValue(self.percentValue.value())
            self.dataEdited()

    def onPercentSliderChanged(self, value):
        if 'percent' in self.nodeData:
            self.nodeData['percent'] = self.percentSlider.value()  # self.sender().value()
            self.percentValue.setValue(self.percentSlider.value())
            self.dataEdited()

    def onRandomSeedValueEditingFinished(self):
        if 'randomSeed' in self.nodeData:
            self.nodeData['randomSeed'] = self.sender().value()
            self.dataEdited()

    def dataEdited(self):
        postEditUserData = copy.deepcopy(self.nodeData)
        if (self.preEditNodeUserData != postEditUserData):
            #copy edited values into node
            self.node.userData = copy.deepcopy(self.nodeData)

            #update node display
            self.layoutEditor.createOrRefreshNodeAttributes(self.node)
            self.layoutEditor.undoRedoEditNode(self.parent, self.preEditNodeUserData, postEditUserData)
            self.layoutEditor.signal_LayoutNodeChanged.emit(self.layoutEditor, self.node.name)

            # prepare for next edition
            self.preEditNodeUserData = copy.deepcopy(self.nodeData)

    # def onOkButtonClicked(self):
    #     postEditUserData = copy.deepcopy(self.nodeData)
    #     if (self.preEditNodeUserData != postEditUserData):
    #         #copy edited values into node
    #         self.node.userData = copy.deepcopy(self.nodeData)
    #         #update node display
    #         self.layoutEditor.createOrRefreshNodeAttributes(self.node)
    #         self.layoutEditor.undoRedoEditNode(self.parent, self.preEditNodeUserData, postEditUserData)
    #         self.layoutEditor.signal_LayoutNodeChanged.emit(self.layoutEditor, self.node.name)
    #     self.accept()

    # def onCancelButtonClicked(self):
    #     self.reject()

    # Entity Selector Functions
    def findCacheProxyNameFromNode(self):
        cacheProxyName = ''
        layoutEditor = self.layoutEditor
        currentNodzInst = self.node.scene().views()[0]
        for tabIndex in range(layoutEditor.editorTabWidget.count()):
            tabNodzInst = layoutEditor.layoutViewTabWidgets[tabIndex].editedNodz
            if currentNodzInst == tabNodzInst:
                cacheProxyName = layoutEditor.getLayoutNameForTab(tabIndex)
                break
        return cacheProxyName

    def findEntitiesTextFieldInSelectorFromButton(self):
        entitiesGroupBox = self.sender().parent().parent()
        entitiesTextField = None
        for childIndex in range(len(entitiesGroupBox.children())):
            if(isinstance(entitiesGroupBox.children()[childIndex], QtWidgets.QLineEdit)):
                entitiesTextField = entitiesGroupBox.children()[childIndex]
                break
        return entitiesTextField

    def updateEntitiesFromArrayValues(self, textField, values):
        values = list(map(str.strip, values))  # trim spaces
        values = list(set(values))       # remove duplicates if required
        values = [_f for _f in values if _f]    # remove empty strings
        valueStr = ','.join(values)
        self.nodeData['entities'] = valueStr
        self.dataEdited()
        textField.setText(valueStr)

    def onSetSelectedEntitiesClicked(self):
        entitiesTextField = self.findEntitiesTextFieldInSelectorFromButton()
        if entitiesTextField is not None:
            self.updateEntitiesFromArrayValues(entitiesTextField, str(self.layoutEditor.wrapper.getSelectedEntities(self.findCacheProxyNameFromNode())).split(','))

    def onAddSelectedEntitiesClicked(self):
        entitiesTextField = self.findEntitiesTextFieldInSelectorFromButton()
        if entitiesTextField is not None:
            vpSelectedEntities = str(self.layoutEditor.wrapper.getSelectedEntities(self.findCacheProxyNameFromNode())).split(',')
            nodeSelectedEntities = str(entitiesTextField.text()).split(',')
            self.updateEntitiesFromArrayValues(entitiesTextField, vpSelectedEntities + nodeSelectedEntities)

    def onRemoveSelectedEntitiesClicked(self):
        entitiesTextField = self.findEntitiesTextFieldInSelectorFromButton()
        if entitiesTextField is not None:
            vpSelectedEntities = list(map(str.strip, str(self.layoutEditor.wrapper.getSelectedEntities(self.findCacheProxyNameFromNode())).split(',')))
            nodeSelectedEntities = list(map(str.strip, str(entitiesTextField.text()).split(',')))
            finalSelectedEntities = [x for x in nodeSelectedEntities if x not in vpSelectedEntities]
            self.updateEntitiesFromArrayValues(entitiesTextField, finalSelectedEntities)

    def onClearSelectedEntitiesClicked(self):
        entitiesTextField = self.findEntitiesTextFieldInSelectorFromButton()
        if entitiesTextField is not None:
            self.updateEntitiesFromArrayValues(entitiesTextField, [])

    # Others
    def onPickSelectedEntityMeshAssetClicked(self):
        pickMeshAssetsButton = self.sender()
        valueGroupBox = pickMeshAssetsButton.parent()
        # find the table widget
        tableWidget = None
        for childIndex in range(len(valueGroupBox.children())):
            if(type(valueGroupBox.children()[childIndex])==type(QtWidgets.QTableWidget())):
                tableWidget=valueGroupBox.children()[childIndex]
                break
        if tableWidget is None:
            return

        attributeIndex = self.getThisOrParentProperty(pickMeshAssetsButton,'attributeIndex')

        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']
            if len(attributes)>attributeIndex:
                if ('type' in attributes[attributeIndex]):
                    # attributeType = attributes[attributeIndex]['type']
                    # attributeFlags = GlmAttributeFlags._none
                    # if 'flags' in attributes[attributeIndex]:
                    #     attributeFlags = attributes[attributeIndex]['flags']
                    attributeValues = attributes[attributeIndex]['values']    #create if it does not exist ?
                    # attributeFrames = attributes[attributeIndex]['frames']    #create if it does not exist ?

                    newMeshAssetList = list()
                    selectedEntityMeshAssets = []
                    if self.layoutEditor.wrapper is not None:
                        selectedEntityMeshAssets = self.layoutEditor.wrapper.getSelectedEntityMeshAssetList()
                    if selectedEntityMeshAssets is not None and len(selectedEntityMeshAssets) > 0:
                        for entityMeshAssetIndex in selectedEntityMeshAssets:
                            newMeshAssetList.append(entityMeshAssetIndex)
                        attributeValues[0] = newMeshAssetList #should call the table value changed event as we did not block the events
                        self.refreshAttributesTableWidget(tableWidget, attributes[attributeIndex])
                    # else:
                    #     print("Pick Mesh Assets error : select an entity to pick mesh assets from.")

        self.resizeTableToContent(tableWidget)
        self.dataEdited()

    def onAddRemoveMeshAssetButtonClicked(self):
        showDialogButton = self.sender()
        valueGroupBox = showDialogButton.parent()
         #find the table widget
        tableWidget = None
        for childIndex in range(len(valueGroupBox.children())):
            if(type(valueGroupBox.children()[childIndex])==type(QtWidgets.QTableWidget())):
                tableWidget=valueGroupBox.children()[childIndex]
                break
        if tableWidget is None:
            return

        attributeIndex = self.getThisOrParentProperty(showDialogButton,'attributeIndex')

        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']
            if len(attributes)>attributeIndex:
                if ('type' in attributes[attributeIndex]):
                    # attributeType = attributes[attributeIndex]['type']
                    # attributeFlags = GlmAttributeFlags._none
                    # if 'flags' in attributes[attributeIndex]:
                    #     attributeFlags = attributes[attributeIndex]['flags']
                    attributeValues = attributes[attributeIndex]['values']    # create if it does not exist ?
                    # attributeFrames = attributes[attributeIndex]['frames']    #create if it does not exist ?

                    meshAssetSearchLabel = QtWidgets.QLabel(self)
                    meshAssetSearchLabel.setText('Search: ')
                    meshAssetLineEdit = QtWidgets.QLineEdit(self)
                    meshAssetLineEdit.textChanged.connect(self.onSearchLineEditChanged)

                    # OK we have a value table, let s pop up the dialog and select indices
                    meshAssetChoiceDlg = QtWidgets.QDialog(self)
                    meshAssetChoiceDlg.setWindowTitle('Add / Remove Mesh Assets')
                    #meshAssetChoiceDlg.layoutAttributeEditor = self

                    meshAssetsListWidget = QtWidgets.QListWidget(self)
                    if (self.layoutEditor.selectedCharacterMeshAssets is not None and len(self.layoutEditor.selectedCharacterMeshAssets) > 0):
                        for meshAsset in self.layoutEditor.selectedCharacterMeshAssets:
                            meshAssetsListWidget.addItem(meshAsset)

                    maxValue = -1
                    currentSelectionList = attributeValues[0]  # all meshAsset indices values at first frame
                    for iCurrentSel in currentSelectionList:
                        maxValue = max(maxValue, iCurrentSel)

                    if (maxValue > -1):
                        for iOutOfRangeAsset in range(len(self.layoutEditor.selectedCharacterMeshAssets), maxValue + 1):
                            meshAssetsListWidget.addItem("Value {} out of range".format(iOutOfRangeAsset))

                    meshAssetsListWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

                    for i in currentSelectionList:
                        meshAssetsListWidget.item(i).setSelected(True)

                    okCancelButtons = QtWidgets.QDialogButtonBox(self)
                    okCancelButtons.orientation = QtCore.Qt.Horizontal
                    okCancelButtons.setStandardButtons(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
                    okCancelButtons.accepted.connect(meshAssetChoiceDlg.accept)
                    okCancelButtons.rejected.connect(meshAssetChoiceDlg.reject)
                    # meshAssetChoiceDlg.connect(okCancelButtons, QtCore.SIGNAL("accepted()"), meshAssetChoiceDlg, QtCore.SLOT("accept()"))
                    # meshAssetChoiceDlg.connect(okCancelButtons, QtCore.SIGNAL("rejected()"), meshAssetChoiceDlg, QtCore.SLOT("reject()"))

                    searchLayout = QtWidgets.QHBoxLayout()
                    searchWidget = QtWidgets.QWidget(self)
                    searchWidget.setLayout(searchLayout)
                    searchLayout.addWidget(meshAssetSearchLabel)
                    searchLayout.addWidget(meshAssetLineEdit)

                    vertLayout = QtWidgets.QVBoxLayout()
                    vertLayout.addWidget(searchWidget)
                    vertLayout.addWidget(meshAssetsListWidget)
                    vertLayout.addWidget(okCancelButtons)

                    meshAssetChoiceDlg.setLayout(vertLayout)
                    if meshAssetChoiceDlg.exec_() == QtWidgets.QDialog.Accepted:
                        newMeshAssetList = list()
                        for selectedItem in meshAssetsListWidget.selectedItems():
                            newMeshAssetList.append((meshAssetsListWidget.row(selectedItem)))
                        attributeValues[0] = newMeshAssetList #should call the table value changed event as we did not block the events
                        self.refreshAttributesTableWidget(tableWidget, attributes[attributeIndex])
        self.resizeTableToContent(tableWidget)
        self.dataEdited()

    def onSearchLineEditChanged(self, value=None):
        widgetEdited = self.sender()  # QLineEdit, QTextEdit
        tableWidget = widgetEdited.parent().parent()  # QDialog
        for childIndex in range(len(tableWidget.children())):
            if(type(tableWidget.children()[childIndex]) == type(QtWidgets.QListWidget())):
                self.updateMeshAssetsListFromSearch(tableWidget.children()[childIndex], value)

    def updateMeshAssetsListFromSearch(self, listWidget, searchValue):
        for iItem in range(listWidget.count()):
            listWidget.item(iItem).setHidden(searchValue is not None and (listWidget.item(iItem).text().lower().find(searchValue.lower()) == -1))

    def onClearValueButtonClicked(self):
        valueAddButton = self.sender()
        valueGroupBox = valueAddButton.parent()
        #find the table widget
        tableWidget = None
        for childIndex in range(len(valueGroupBox.children())):
            if(type(valueGroupBox.children()[childIndex])==type(QtWidgets.QTableWidget())):
                tableWidget=valueGroupBox.children()[childIndex]
                break
        if tableWidget is None:
            return
        attributeIndex = self.getThisOrParentProperty(valueAddButton,'attributeIndex')
        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']
            if len(attributes)>attributeIndex:
                # get attribute info
                if ('frames' in attributes[attributeIndex] and 'values' in attributes[attributeIndex]):
                    attributeFrames = attributes[attributeIndex]['frames']
                    attributeValues = attributes[attributeIndex]['values']
                    #clear all the frames except 1 (if it's not a keyframed attribute, it already has 0 frames)
                    while(len(attributeFrames)>1):
                        attributeFrames.pop()   # a pop in a while rather than = [] because the '=' won't really delete the list, just affect another
                    #clear all the values except 1
                    while(len(attributeValues)>1):  #keep 1 value in the frames list
                        attributeValues.pop()
                    if(len(attributeValues)>0):
                        if ('type' in attributes[attributeIndex]):
                            valueType = attributes[attributeIndex]['type']
                            if valueType != GlmValueType.GTV_char:
                                valuesCountToKeep=len(attributeFrames)
                                while(len(attributeValues[0])>valuesCountToKeep):
                                    attributeValues[0].pop()
                    tableWidget.setRowCount(len(attributeFrames))  # view
        self.resizeTableToContent(tableWidget)
        self.dataEdited()

    def onUseKeyframesCheckboxClicked(self, checked):
        valueAddButton = self.sender()
        valueGroupBox = valueAddButton.parent()
        #find the needed widgets
        tableWidget = None
        valueAddButton = None
        valueClearButton = None
        for childIndex in range(len(valueGroupBox.children())):
            if(type(valueGroupBox.children()[childIndex])==type(QtWidgets.QTableWidget())):
                tableWidget=valueGroupBox.children()[childIndex]
            elif(type(valueGroupBox.children()[childIndex])==type(QtWidgets.QToolButton())):
                valueAddButton=valueGroupBox.children()[childIndex]
            elif(type(valueGroupBox.children()[childIndex])==type(QtWidgets.QPushButton())):
                valueClearButton=valueGroupBox.children()[childIndex]
        if tableWidget is None:
            return
        attributeIndex = self.getThisOrParentProperty(valueAddButton,'attributeIndex')

        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']
            if len(attributes)>attributeIndex:
                attribute = attributes[attributeIndex]

                # get attribute info
                attributeFrames = None
                attributeValues = None
                for attributeItem in attribute.items():
                    if attributeItem[0] == 'frames':
                        attributeFrames = attributeItem[1]
                    elif attributeItem[0] == 'values':
                        attributeValues = attributeItem[1]
                if attributeFrames!=None and attributeValues!=None:
                    if(checked):
                        #make sure arrays are the same size
                        while(len(attributeValues)<len(attributeFrames) ):
                            attributeValues.append(attributeValues[-1]) # [-1] = last item
                        while(len(attributeFrames)<len(attributeValues) ):
                            if(len(attributeFrames)>0):
                                attributeFrames.append(attributeFrames[-1]) # [-1] = last item
                            else:
                                attributeFrames.append(0)
                    else:
                        #clear the attributeFrames
                        while(len(attributeFrames)>0):
                            attributeFrames.pop()
                        while(len(attributeValues)>1):  #we alsway need to keep at least one value
                            attributeValues.pop()

                if(checked):
                    if valueAddButton is not None:
                        valueAddButton.show()
                    if valueClearButton is not None:
                        valueClearButton.show()
                else:
                    if valueAddButton is not None:
                        valueAddButton.hide()
                    if valueClearButton is not None:
                        valueClearButton.hide()

                self.refreshAttributesTableWidget(tableWidget, attribute)
        self.resizeTableToContent(tableWidget)
        self.dataEdited()

    def onAddValueButtonClicked(self):

        valueAddButton = self.sender()
        valueGroupBox = valueAddButton.parent()
        #find the table widget
        tableWidget = None
        for childIndex in range(len(valueGroupBox.children())):
            if(type(valueGroupBox.children()[childIndex])==type(QtWidgets.QTableWidget())):
                tableWidget=valueGroupBox.children()[childIndex]
                break
        if tableWidget is None:
            return
        attributeIndex = self.getThisOrParentProperty(valueAddButton,'attributeIndex')

        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']
            if len(attributes)>attributeIndex:
                if ('type' in attributes[attributeIndex]):
                    attributeType = attributes[attributeIndex]['type']
                    attributeFlags = GlmAttributeFlags._none
                    if 'flags' in attributes[attributeIndex]:
                        attributeFlags = attributes[attributeIndex]['flags']
                    attributeValues = attributes[attributeIndex]['values']    #create if it does not exist ?
                    attributeFrames = attributes[attributeIndex]['frames']    #create if it does not exist ?
                    #default value to add
                    valueToAdd = None
                    if attributeType == GlmValueType.GTV_char:
                        print("Attribute type error : char attribute type  should never have + button")
                    elif attributeType in [GlmValueType.GTV_int32, GlmValueType.GTV_uint32, GlmValueType.GTV_int64]:
                        valueToAdd = 0
                    elif attributeType == GlmValueType.GTV_float:
                        valueToAdd = 0.0
                    elif attributeType == GlmValueType.GTV_vec3:
                        valueToAdd = [0.0, 0.0, 0.0]
                    elif attributeType == GlmValueType.GTV_vec4:
                        valueToAdd = [0.0, 0.0, 0.0, 0.0]
                    else:    #unknown or 0 (#GTV_none)
                        print("Attribute type error : unkown type")

                    #is added differently if the widget has frames or not
                    hasFrames = tableWidget.property("addFrameToTable")
                    if(hasFrames):
                        nextFrameIndex = 0
                        if(len(attributeFrames)>0):
                            nextFrameIndex = attributeFrames[-1]+1
                        attributeFrames.append(nextFrameIndex)
                        while(len(attributeValues)<len(attributeFrames) ):
                            attributeValues.append(list())
                            attributeValues[-1].append(valueToAdd) # [-1] = last item

                        self.addTableRow(attributeType, attributeFlags, tableWidget, attributeValues[-1][0], attributeFrames[-1])
                    else:
                        attributeValues[0].append(valueToAdd)    #attributeValues's size is always at least 1, so index 0 is always valid
                        self.addTableRow(attributeType, attributeFlags, tableWidget, attributeValues[0][-1], -1)    #no frame, so set to -1

        self.resizeTableToContent(tableWidget)
        self.dataEdited()

    def onRemoveValueButtonClicked(self):
        valueRemoveButton = self.sender()
        tableWidget = valueRemoveButton.parent().parent()

        attributeIndex = self.getThisOrParentProperty(valueRemoveButton,'attributeIndex')
        # valueIndex = self.getThisOrParentProperty(valueRemoveButton,'valueIndex')

        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']
            if len(attributes)>attributeIndex:
                if ('frames' in attributes[attributeIndex] and 'values' in attributes[attributeIndex]):
                    attributeFrames = attributes[attributeIndex]['frames']
                    attributeValues = attributes[attributeIndex]['values']
                    if (len(attributeFrames) != 0 and tableWidget.rowCount() == 1):
                        print("A keyframe array cannot have 0 value, can't delete.")
                        return # can't delete a single row when using keyframes, we need at least one value

                    if(len(attributeFrames) == 0 and len(attributeValues)>0):
                        attributeValues = attributeValues[0]   #when not using keyframes, were using multi-values on keyframe value 0

                    # find row giving frame, find column givin subValueIndex
                    iColumn = tableWidget.columnCount() - 1 # button is last of columns
                    for iRow in range(tableWidget.rowCount()):
                        if (tableWidget.cellWidget(iRow, iColumn) == valueRemoveButton):
                            valueIndex = iRow
                            if (len(attributeFrames))>valueIndex:
                                attributeFrames.pop(valueIndex)
                            if (len(attributeValues))>valueIndex:
                                attributeValues.pop(valueIndex)
                            #update node display
                            tableWidget.removeRow(valueIndex)

        self.resizeTableToContent(tableWidget)
        self.dataEdited()

    def onEnumComboBoxChanged(self, selectedIndex):
        widgetEdited = self.sender() #QComboBox
        widgetEdited.blockSignals(True)
        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']
            # swap first with current
            if len(attributes)>attributeIndex:
                if 'values' in attributes[attributeIndex]:
                    # view is uptodate, update attribute value
                    attributes[attributeIndex]['values'][0][0] = widgetEdited.currentIndex()    #[0][0] for first frame, first value
        widgetEdited.blockSignals(False)
        self.dataEdited()

    def onTextEnumComboBoxChanged(self, selectedIndex):
        widgetEdited = self.sender() #QComboBox
        widgetEdited.blockSignals(True)
        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']
            # swap first with current
            if len(attributes)>attributeIndex:
                if 'values' in attributes[attributeIndex]:
                    selectedItem = widgetEdited.itemText(selectedIndex)
                    # update value
                    attributes[attributeIndex]['values'][0] = selectedItem
        widgetEdited.blockSignals(False)
        self.dataEdited()

    def onSnapToPoptoolComboBoxChanged(self, selectedIndex):
        widgetEdited = self.sender() #QComboBox
        widgetEdited.blockSignals(True)
        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        done=False
        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']

            entityTypeName = ''
            for attribute in attributes:
                if 'name' in attribute and attribute['name'] == 'entityType' and 'values' in attribute:
                    entityTypeName = attribute['values'][0]
                    break

            # swap first with current
            if len(attributes)>attributeIndex:
                if 'values' in attributes[attributeIndex]:
                    selectedItem = widgetEdited.itemText(selectedIndex)

                    # update value
                    attributes[attributeIndex]['values'][0] = selectedItem
                    done = True
        widgetEdited.blockSignals(False)
        if (done):
            self.layoutEditor.signal_LayoutSnapToPoptoolDropDownChanged.emit(self, widgetEdited.itemText(selectedIndex), entityTypeName)
            self.dataEdited()

    def onSnapToEntityTypeComboBoxChanged(self, selectedIndex):
        widgetEdited = self.sender() #QComboBox
        widgetEdited.blockSignals(True)
        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        done=False
        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']

            poptoolName = ''
            for attribute in attributes:
               if 'name' in attribute and attribute['name'] == 'snapToTarget' and 'values' in attribute:
                    poptoolName = attribute['values'][0]
                    break

            # swap first with current
            if len(attributes)>attributeIndex:
                if 'values' in attributes[attributeIndex]:
                    selectedItem = widgetEdited.itemText(selectedIndex)

                    # update value
                    attributes[attributeIndex]['values'][0] = selectedItem
                    done = True
        widgetEdited.blockSignals(False)
        if (done):
            self.layoutEditor.signal_LayoutSnapToPoptoolDropDownChanged.emit(self, poptoolName, widgetEdited.itemText(selectedIndex))
            self.dataEdited()

    def onVectorFieldComboBoxChanged(self, selectedIndex):
        widgetEdited = self.sender() #QComboBox
        widgetEdited.blockSignals(True)
        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        done=False
        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']

            # swap first with current
            if len(attributes)>attributeIndex:
                if 'values' in attributes[attributeIndex]:
                    selectedItem = widgetEdited.itemText(selectedIndex)

                    # update value
                    attributes[attributeIndex]['values'][0] = selectedItem
                    done = True
        widgetEdited.blockSignals(False)
        if (done):
            self.layoutEditor.signal_LayoutVectorFieldDropDownChanged.emit(self, widgetEdited.itemText(selectedIndex))
            self.dataEdited()

    def onPaintedZoneComboBoxChanged(self, selectedIndex):
        widgetEdited = self.sender() #QComboBox
        widgetEdited.blockSignals(True)
        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        done=False
        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']

            # swap first with current
            if len(attributes)>attributeIndex:
                if 'values' in attributes[attributeIndex]:
                    selectedItem = widgetEdited.itemText(selectedIndex)

                    # update value
                    attributes[attributeIndex]['values'][0] = selectedItem
                    done = True
        widgetEdited.blockSignals(False)
        if (done):
            self.layoutEditor.signal_LayoutPaintedZoneDropDownChanged.emit(self, widgetEdited.itemText(selectedIndex))
            self.dataEdited()            

    def onColorChannelComboBoxChanged(self, selectedIndex):
        widgetEdited = self.sender() #QComboBox
        widgetEdited.blockSignals(True)
        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        done=False
        if 'attributes' in self.nodeData:
            attributes = self.nodeData['attributes']

            # swap first with current
            if len(attributes)>attributeIndex:
                if 'values' in attributes[attributeIndex]:
                    selectedItem = widgetEdited.itemText(selectedIndex)

                    # update value
                    attributes[attributeIndex]['values'][0] = selectedItem
                    done = True
        widgetEdited.blockSignals(False)
        if (done):
            # self.layoutEditor.signal_LayoutColorChannelDropDownChanged.emit(self, widgetEdited.itemText(selectedIndex))
            self.dataEdited()            

    def onColorPressed(self):
        # need the value from the current table widget
        # self is layoutAttributeEditor
        pushButton = self.sender()
        currentColor = pushButton.palette().color(QtGui.QPalette.Button)
        self.color_chooser = QtWidgets.QColorDialog(currentColor, self)
        if self.color_chooser.exec_() == QtWidgets.QColorDialog.Accepted:
            newColor = self.color_chooser.currentColor()
            palette = pushButton.palette()
            palette.setColor(QtGui.QPalette.Window, newColor)
            palette.setColor(QtGui.QPalette.Button, newColor)
            pushButton.setPalette(palette)
            self.onTableValueChanged(newColor)
            self.dataEdited()

    def onTableStringValueChanged(self, value = None):
        widgetEdited = self.sender() #QLineEdit, QTextEdit
        tableWidget = widgetEdited.parent().parent() #QTableWidget

        plainTextValue = value # QLineEdit case
        if (plainTextValue is None):
            plainTextValue = widgetEdited.toPlainText() # QTextEdit case

        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        frameIndex = -1

        done=False
        # find row giving frame, find column giving subValueIndex
        for iRow in range(tableWidget.rowCount()):
            for iColumn in range(tableWidget.columnCount()):
                if (tableWidget.cellWidget(iRow, iColumn) == widgetEdited):
                    valueIndex = iRow
                    columnIndex = iColumn
                    hasFrame = tableWidget.property("addFrameToTable")
                    #save value in self.nodeData
                    if 'attributes' in self.nodeData:
                        attributes = self.nodeData['attributes']
                        if len(attributes)>attributeIndex:
                            if (hasFrame and columnIndex == 0):
                                frameIndex = iRow
                                if 'frames' in attributes[attributeIndex]:
                                    frames = attributes[attributeIndex]['frames']
                                    if len(frames)>valueIndex:
                                        frames[valueIndex] = plainTextValue
                                        done=True
                            elif hasFrame:
                                frameIndex = iRow
                                valueIndex = 0
                                # subValueIndex = iColumn-1
                            else:
                                frameIndex = 0
                                valueIndex = iRow
                                # subValueIndex = iColumn
                            if not done:
                                # if has values
                                if 'values' in attributes[attributeIndex]:
                                    values = attributes[attributeIndex]['values']
                                    if len(values)>frameIndex:
                                        values[frameIndex] = plainTextValue
                                        done=True
        if(not done):
            print('Error: value {} for attribute {}, at frame index {} could not be saved...'.format(value, attributeIndex, frameIndex))
        # else:
        #     self.dataEdited()
        # else:
        #     print 'New value for attribute {}, at frame index {} is {}'.format(attributeIndex, frameIndex, value)

    def onTableComboBoxValueChanged(self, selectedIndex):
        widgetEdited = self.sender() #QComboBox
        tableWidget = widgetEdited.parent().parent() #QTableWidget

        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        frameIndex = -1

        done=False
        # find row giving frame, find column giving subValueIndex
        for iRow in range(tableWidget.rowCount()):
            for iColumn in range(tableWidget.columnCount()):
                if (tableWidget.cellWidget(iRow, iColumn) == widgetEdited):
                    valueIndex = iRow
                    columnIndex = iColumn
                    hasFrame = tableWidget.property("addFrameToTable")
                    #save value in self.nodeData
                    if 'attributes' in self.nodeData:
                        attributes = self.nodeData['attributes']
                        if len(attributes)>attributeIndex:
                            if (hasFrame and columnIndex == 0):
                                frameIndex = iRow
                                if 'frames' in attributes[attributeIndex]:
                                    frames = attributes[attributeIndex]['frames']
                                    if len(frames)>valueIndex:
                                        frames[valueIndex] = selectedIndex
                                        done=True
                            elif hasFrame:
                                frameIndex = iRow
                                valueIndex = 0
                                subValueIndex = iColumn-1
                            else:
                                frameIndex = 0
                                valueIndex = iRow
                                subValueIndex = iColumn
                            if not done:
                                # if has values
                                if 'values' in attributes[attributeIndex]:
                                    values = attributes[attributeIndex]['values']

                                    # attributeFlags = GlmAttributeFlags._none
                                    # if 'flags' in attributes[attributeIndex]:
                                    #     attributeFlags = attributes[attributeIndex]['flags']

                                    if len(values)>frameIndex:
                                        # if values is an array
                                        if len(values[frameIndex])>valueIndex:
                                                if isinstance(values[frameIndex][valueIndex], list):
                                                    if len(values[frameIndex][valueIndex])>subValueIndex:
                                                        values[frameIndex][valueIndex][subValueIndex] = selectedIndex
                                                        done=True
                                                else:
                                                    values[frameIndex][valueIndex] = selectedIndex
                                                    done=True
        if(not done):
            print('Error: value {} for attribute {}, at frame index {} could not be saved...'.format(selectedIndex, attributeIndex, frameIndex))
        else:
            self.dataEdited()
        # else:
        #     print 'New value for attribute {}, at frame index {} is {}'.format(attributeIndex, frameIndex, value)

    def onTableValueChanged(self, value):
        widgetEdited = self.sender() #QSpinBox  /QDoubleSpinBox
        tableWidget = widgetEdited.parent().parent() #QTableWidget

        attributeIndex = self.getThisOrParentProperty(widgetEdited,'attributeIndex')
        frameIndex = -1

        done=False
        # find row giving frame, find column giving subValueIndex
        for iRow in range(tableWidget.rowCount()):
            for iColumn in range(tableWidget.columnCount()):
                if (tableWidget.cellWidget(iRow, iColumn) == widgetEdited):
                    valueIndex = iRow
                    columnIndex = iColumn
                    hasFrame = tableWidget.property("addFrameToTable")
                    #save value in self.nodeData
                    if 'attributes' in self.nodeData:
                        attributes = self.nodeData['attributes']
                        if len(attributes)>attributeIndex:
                            if (hasFrame and columnIndex == 0):
                                frameIndex = iRow
                                if 'frames' in attributes[attributeIndex]:
                                    frames = attributes[attributeIndex]['frames']
                                    if len(frames)>valueIndex:
                                        frames[valueIndex] = value
                                        done=True
                            elif hasFrame:
                                frameIndex = iRow
                                valueIndex = 0
                                subValueIndex = iColumn-1
                            else:
                                frameIndex = 0
                                valueIndex = iRow
                                subValueIndex = iColumn
                            if not done:
                                # if has values
                                if 'values' in attributes[attributeIndex]:
                                    values = attributes[attributeIndex]['values']

                                    attributeFlags = GlmAttributeFlags._none
                                    if 'flags' in attributes[attributeIndex]:
                                        attributeFlags = attributes[attributeIndex]['flags']

                                    if len(values)>frameIndex:
                                        # if values is an array
                                        if len(values[frameIndex])>valueIndex:
                                            if attributeFlags&GlmAttributeFlags._uiColorWheel:
                                                # color button case
                                                values[frameIndex][valueIndex][0] = value.red()
                                                values[frameIndex][valueIndex][1] = value.green()
                                                values[frameIndex][valueIndex][2] = value.blue()
                                                values[frameIndex][valueIndex][3] = value.alpha()
                                                done=True
                                            else:
                                                if isinstance(values[frameIndex][valueIndex], list):
                                                    if len(values[frameIndex][valueIndex])>subValueIndex:
                                                        values[frameIndex][valueIndex][subValueIndex] = value
                                                        done=True
                                                else:
                                                    values[frameIndex][valueIndex] = value
                                                    done=True
        if(not done):
            print('Error: value {} for attribute {}, at frame index {} could not be saved...'.format(value, attributeIndex, frameIndex))
        # else:
        #     self.dataEdited()
        # else:
        #     print 'New value for attribute {}, at frame index {} is {}'.format(attributeIndex, frameIndex, value)

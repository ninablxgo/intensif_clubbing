from glm.layout.layoutEditorUtils import LayoutEditor
from glm.layout import layoutEditorWrapper
import glm.mayaUtils as mutils

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

######################################################################
# getTheLayoutEditorMayaInstance
######################################################################
def getTheLayoutEditorMayaInstance(delete=False):
    """
    Returns the instance singleton
    """
    global layoutEditorInstance
    try:
        layoutEditorInstance
        if delete:
            if(layoutEditorInstance is not None):
                print("Trying to delete the LayoutEditor")
                layoutEditorInstance.__del__()
                del layoutEditorInstance
                print("Trying to delete the LayoutEditorWrapper")
                layoutEditorWrapper.getTheLayoutEditorWrapperInstance(False, False)
            else:
                print("LayoutEditor is None")
            return None
    except NameError:
        if delete:
            print("LayoutEditor is already destroyed")
            return None
        else:
            mayaMainWindow = mutils.getMayaWindow()
            wrapper = layoutEditorWrapper.getTheLayoutEditorWrapperInstance(True)
            layoutEditorInstance = LayoutEditorMaya(mayaMainWindow, wrapper)
            layoutEditorInstance.loadWindowPrefs()

    return layoutEditorInstance

######################################################################
# LayoutEditorMaya
######################################################################
class LayoutEditorMaya(MayaQWidgetDockableMixin, LayoutEditor):
    """
    The Golaem Layout Profiler that allows to analysis golaem simulation performances
    """
    # ------------------------------------------------------------------
    def __init__(self, parent=None, wrapper = layoutEditorWrapper.getTheLayoutEditorWrapperInstance(True)):
        super(LayoutEditorMaya, self).__init__(parent=parent, wrapper=wrapper)
    
    # ------------------------------------------------------------------
    def __del__(self):
        print("LayoutEditorMaya destructor")
        super(LayoutEditorMaya, self).__del__()

    # ------------------------------------------------------------------
    def show(self):
        MayaQWidgetDockableMixin.show(self, dockable=True) # if dockable False, the window disappear behind maya when lsoing focus under linux
        self.activateWindow()
        self.raise_()
        if self.isMinimized():
            self.showNormal()

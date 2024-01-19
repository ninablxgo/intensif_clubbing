from __future__ import absolute_import
#**************************************************************************
#*                                                                        *
#*  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
#*                                                                        *
#**************************************************************************

#**************************************************************************
#! \file Callback Utils
#  \brief callback related functions
#**************************************************************************

#**************************************************************************
#! @name Golaem Callback Utils
#**************************************************************************
#@{
# global storage for node creation user callbacks
glmUserCallbacks = {}

#------------------------------------------------------------
#! Allows an user to register a user callback
#! callbackName the name of the callback
#------------------------------------------------------------
def registerUserCallback(callbackName, function):
    global glmUserCallbacks
    glmUserCallbacks[callbackName] = function

#------------------------------------------------------------
#! Allows an user to deregister a user callback
#! callbackName the name of the callback
#------------------------------------------------------------
def deregisterUserCallback(callbackName):
    global glmUserCallbacks
    if callbackName in glmUserCallbacks:
        del glmUserCallbacks[callbackName]

#------------------------------------------------------------
#! Checks if a functionNameUserCallback function exists and if yes, calls it
#! nodeName the name of the node created
#------------------------------------------------------------
def executeUserCallback(functionName, attribute):
    callbackName = (functionName + 'UserCallback')
    global glmUserCallbacks
    if callbackName in glmUserCallbacks:
        try:
            glmUserCallbacks[callbackName](attribute)
        except:
            return False
#@}

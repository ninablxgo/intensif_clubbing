#**************************************************************************
#*                                                                        *
#*  Copyright (C) Golaem S.A. - All Rights Reserved.                      *
#*                                                                        *
#**************************************************************************

#**************************************************************************
#! \file String Utils
#  \brief String related functions
#**************************************************************************

import re

#**************************************************************************
#! @name Utils
#**************************************************************************
#@{
#------------------------------------------------------------
#! Replace all characters from dict with values
#------------------------------------------------------------
def translateFromDict(str, dict):
    for key in dict:
        str = str.replace(key, dict[key])
    return str

#------------------------------------------------------------
#! Cut oversize string
#------------------------------------------------------------
def cutOversizeStringWithEndEllipsis(oversizeString, maxSize ):
    return (oversizeString[:maxSize] + '...') if len(oversizeString) > maxSize else oversizeString

#------------------------------------------------------------
#! Cut oversize string
#------------------------------------------------------------
def cutOversizeStringWithBeginEllipsis(oversizeString, maxSize ):
    return ('...' + oversizeString[len(oversizeString) - maxSize:]) if len(oversizeString) > maxSize else oversizeString

#------------------------------------------------------------
#! Cut oversize string
#------------------------------------------------------------
def alphanumerize(string):
    return re.sub(r'\W+', '', string)
#@}

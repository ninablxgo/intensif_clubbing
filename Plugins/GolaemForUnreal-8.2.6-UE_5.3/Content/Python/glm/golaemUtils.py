# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A.  All Rights Reserved.                       *
# *                                                                        *
# **************************************************************************

# **************************************************************************
#! \file Golaem Utils
#  \brief Golaem functions with no dependencies from Maya!!
# **************************************************************************

# DO NOT ADD ANY MAYA DEPENDENCY HERE
from builtins import str
from builtins import range
import re
import sys
from glm import stringUtils as stutils
# DO NOT ADD ANY MAYA DEPENDENCY HERE

usingDevkit = True
try:
    import glm.devkit as devkit
except:
    usingDevkit = False

# ------------------------------------------------------------
def convertStringForDevkit(value):
    if sys.version_info.major >= 3:
        return str(value)
    return value.encode()


# **************************************************************************
#! @name File Utils
# **************************************************************************
# @{
# ------------------------------------------------------------
#! Return the file path prefix of an exported file (same as getExportedFilePath but without the frame and the extension)
#! \note: ends with a "."
# ------------------------------------------------------------
def getExportedFilePrefix(directory, cacheName, crowdField):
    if usingDevkit:
        directory = devkit.replaceEnvVars(convertStringForDevkit(directory))
    return directory + "/" + cacheName + "." + convertToValidName(crowdField) + "."


# ------------------------------------------------------------
#! Return the simulation cache file path
# ------------------------------------------------------------
def getSimulationCachePath(cachePrefix, frame):
    return cachePrefix + str(frame) + ".gscf"


# ------------------------------------------------------------
#! Convert a str (such as a nodeName) to a a valid str for file naming
#  \str str to convert
# ------------------------------------------------------------
def convertToValidName(str):
    validStr = list(str)

    # check first letter and replace it if a number
    if (len(validStr) and validStr[0].isdigit()):
        validStr[0] = stutils.translateFromDict(validStr[0], {'0':'a','1':'b','2':'c','3':'d','4':'e','5':'f','6':'g','7':'h','8':'i','9':'j'})
    
    # replace special characters with _ or __
    expr = re.compile("[a-zA-Z0-9|@]")
    for iS in range(1, len(validStr)):
        if expr.match(validStr[iS]) is None:
            if validStr[iS] == ":":
                validStr.insert(iS + 1, "_")
            validStr[iS] = "_"
    return "".join(validStr)
# @}

# **************************************************************************
# *                                                                        *
# *  Copyright (C) Golaem S.A.  All Rights Reserved.                       *
# *                                                                        *
# **************************************************************************

# **************************************************************************
#! \file JSON Utils
#  \brief JSON related functions
# **************************************************************************

from builtins import str, bytes
import json
import sys

if sys.version_info.major == 3:
    unicode = str

# **************************************************************************
#! @name Read / Write
# **************************************************************************
# @{
# ------------------------------------------------------------
#! Parses a python object from a JSON string. Every Object which should be loaded needs a constuctor that doesn't need any Arguments.
#! Arguments: The JSON string; the module which contains the class, the parsed object is instance of.
# ------------------------------------------------------------
def glmJsonLoad(jsonString, module):
    def _load(d, module):
        if isinstance(d, list):
            l = []
            for item in d:
                l.append(_load(item, module))
            return l
        # object
        elif isinstance(d, dict) and "type" in d:
            t = d["type"]
            try:
                o = module[t]()
            except KeyError as e:
                raise ClassNotFoundError("Class '%s' not found in the given module!" % t)
            except TypeError as e:
                raise TypeError("Make sure there is an constuctor that doesn't take any arguments (class: %s)" % t)
            for key in d:
                if key != "type":
                    setattr(o, key, _load(d[key], module))
            return o
        # dict
        elif isinstance(d, dict):
            rd = {}
            for key in d:
                rd[key] = _load(d[key], module)
            return rd
        else:
            return d

    d = json.loads(jsonString)
    return _load(d, module)


# ------------------------------------------------------------
#! Dumps a python object to a JSON string. Argument: Python object
# ------------------------------------------------------------
def glmJsonDump(obj):
    def _dump(obj, path):
        if isinstance(obj, list):
            l = []
            i = 0
            for item in obj:
                # print('dumping list item {}'.format(i))
                l.append(_dump(item, path + "/[" + str(i) + "]"))
                i += 1
            return l
        # dict
        elif isinstance(obj, dict):
            rd = {}
            for key in obj:
                # print('dumping dict key {}'.format(key))
                rd[key] = _dump(obj[key], path + "/" + key)
            return rd
        elif (
            isinstance(obj, str)
            or isinstance(obj, unicode)
            or isinstance(obj, int)
            or isinstance(obj, float)
            or isinstance(obj, complex)
            or isinstance(obj, bool)
            or type(obj).__name__ == "NoneType"
        ):
            return obj
        elif isinstance(obj, bytes):
            return obj.decode()
        else:
            d = {}
            d["type"] = obj.__class__.__name__
            for key in obj.__dict__:
                # print('dumping class key {}'.format(key))
                d[key] = _dump(obj.__dict__[key], path + "/" + key)
            return d

    return json.dumps(_dump(obj, "/"), sort_keys=True, indent=4, separators=(",", ": "))


# ------------------------------------------------------------
#! DClassNotFoundError
# ------------------------------------------------------------
class ClassNotFoundError(Exception):
    """docstring for ClassNotFoundError"""

    def __init__(self, msg):
        super(ClassNotFoundError, self).__init__(msg)


# @}


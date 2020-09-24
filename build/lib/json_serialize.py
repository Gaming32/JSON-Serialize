"""Create JSON serialized representations of Python objects

Functions:

    convert_to_data(obj:object) -> Union[Dict, FALLBACK]
    convert_to_obj(data:Dict, allow_mode_repr:bool) -> object
    load(file) -> object
    loads(string) -> object
    dump(object, file)
    dumps(object) -> str
    set_version_error_level(level:int)
    version_check(version:int, min_version:int) -> bool

Misc variables:

    __version__
    __author__
    VERSION
    MIN_VERSION
    type_settings
    FALLBACK
    Set:
        used to keep track of serialized objects in the _reached argument

Descriptors:

    serialization_settings(serialization_mode=MODE_YES,
        serialization_function:Union[None, Callable[[object, Set], Mapping]]=None,
        deserialization_function:Union[None, Callable[[dict, bool, Set], None]]=None)"""

import builtins
import sys
import json, uuid, warnings, typing

class VersionError(ValueError):
    """Raised when an incompatible version is detected and the version error level is 2"""
class VersionWarning(Warning):
    """Warned when an incompatible version is detected and the version error level is 1"""

__version__ = '1.0.2'
__author__ = 'Gaming32'

VERSION = 1
MIN_VERSION = 1
_MIN_DES_VER = 1
_VER_ERROR_LVL = 1

Set = typing.List[typing.Tuple[int, typing.Any]]
JsonSupported = typing.Union[dict, list, str, int, float, bool, None]

def set_version_error_level(level:int=1):
    """Set the version error level. This value is used when an an incompatible version is detected

Possible Values:

    0: Do nothing
    1: Warn VersionWarning
    2: Raise VersionError"""
    global _VER_ERROR_LVL
    _VER_ERROR_LVL = level

MODE_YES = 'yes'
MODE_NO = 'no'
MODE_FALLBACK = 'fallback'
MODE_REPR = 'repr'
MODE_FUNCTION = 'function'
_MODE_UUID = 'uuid'
class FALLBACK:
    """This class is returned by itself when convert_to_data doesn't detect any object attributes"""

def _serialize_list(obj, _reached):
    return [convert_to_data(x, _reached) for x in obj]
def _deserialize_list(value, allow_mode_repr, _reached):
    return [convert_to_obj(x, allow_mode_repr, _reached) for x in value]
def _serialize_dict(obj, _reached):
    return {k: convert_to_data(x, _reached) for (k, x) in obj.items()}
def _deserialize_dict(value, allow_mode_repr, _reached):
    return {k: convert_to_obj(x, allow_mode_repr, _reached) for (k, x) in value.items()}
def _serialize_tuple(obj, *args):
    return _serialize_list(list(obj), *args)
def _deserialize_tuple(*args):
    return tuple(_deserialize_list(*args))
def _serialize_set(obj, *args):
    return _serialize_list(list(obj), *args)
def _deserialize_set(*args):
    return set(_deserialize_list(*args))

type_settings = {
    'str': [MODE_FALLBACK, None, None],
    'int': [MODE_FALLBACK, None, None],
    'float': [MODE_FALLBACK, None, None],
    'list': [MODE_FUNCTION, _serialize_list, _deserialize_list],
    'tuple': [MODE_FUNCTION, _serialize_tuple, _deserialize_tuple],
    'set': [MODE_FUNCTION, _serialize_set, _deserialize_set],
    'dict': [MODE_FUNCTION, _serialize_dict, _deserialize_dict],
    'bool': [MODE_FALLBACK, None, None],
    'NoneType': [MODE_FALLBACK, None, None],
}

builtins.NoneType = type(None)

def serialization_settings(serialization_mode=MODE_YES,
    serialization_function:typing.Union[None, typing.Callable[[object, Set], JsonSupported]]=None,
    deserialization_function:typing.Union[None, typing.Callable[[JsonSupported, bool, Set], object]]=None):
    """Descriptor that gives the specified type an entry in type_settings

Arguments:

    serialization_mode : Any of the MODE_* constants
        The method to use to serialize (and possibly deserialize the type)
        Possibilites:
            MODE_YES:
                serialize the type
            MODE_NO:
                don't serialize the type, always deserializes as None
            MODE_FALLBACK:
                fallback to the JSON module types, the types can be found at https://docs.python.org/3/library/json.html#json.JSONDecoder
            MODE_REPR:
                serializes with repr(obj), deserializes with eval(data)
            MODE_FUNCTION:
                uses serialization_function to serialize, uses deserialization_function to deserialize
    serialization_function : Union[None, Callable[[object, Set], JsonSupported]]
        callable that accepts (object, Set) and returns the serialized data
    deserialization_function : Union[None, Callable[[JsonSupported, bool, Set], None]]
        callable that accepts (JsonSupported, bool, Set) and returns the deserialized object"""
    def descriptor(cls):
        type_settings[cls.__name__] = [serialization_mode, serialization_function, deserialization_function]
        return cls
    return descriptor

def _in_set_obj(set:Set, obj):
    for (uuid_, item) in set:
        if item is obj:
            return uuid_, item
    return None
def _in_set_uuid(set:Set, uuid_):
    for (this_uuid, item) in set:
        if this_uuid == uuid_:
            return uuid_, item
    return None
def _set_add_obj(set:Set, obj):
    uuid_ = uuid.uuid1().int
    _set_add_uuid(set, uuid_, obj)
    return uuid_
def _set_add_uuid(set:Set, uuid_, obj):
    set.append((uuid_, obj))

def version_check(version, min_version):
    if version > VERSION:
        if MIN_VERSION >= min_version:
            return True
        else:
            return False
    else:
        if version >= MIN_VERSION:
            return True
        else:
            return False

def convert_to_data(obj:object, _reached=None) -> typing.Union[typing.Dict, FALLBACK]:
    if _reached is None:
        _reached = list()

    data = {}
    data['version'] = VERSION
    data['min_version'] = _MIN_DES_VER

    data['module'] = obj.__class__.__module__
    data['type'] = obj.__class__.__name__
    data['attrs'] = {}

    in_set = _in_set_obj(_reached, obj)
    if in_set is not None:
        uuid_, item = in_set
        data['mode'] = _MODE_UUID
        data['uuid'] = uuid_
        data['force_use_uuid'] = True
        return data

    uuid_ = _set_add_obj(_reached, obj)
    data['uuid'] = uuid_

    if type(obj).__name__ not in type_settings:
        serialization_setting = MODE_YES
    else:
        serialization_setting = type_settings[type(obj).__name__][0]
        serialization_function = type_settings[type(obj).__name__][1]

    if hasattr(obj.__class__, '__slots__'):
        attrs = obj.__class__.__slots__
    elif hasattr(obj, '__dict__'):
        attrs = list(obj.__dict__)
    else:
        if serialization_setting == MODE_FALLBACK:
            data['value'] = obj
            attrs = []
        elif serialization_setting == MODE_FUNCTION:
            data['value'] = serialization_function(obj, _reached)
            attrs = []
        else:
            return FALLBACK

    for attr in attrs:
        obj_attr = getattr(obj, attr)
        data['attrs'][attr] = {}
        location = data['attrs'][attr]
        location['value'] = {}

        in_set = _in_set_obj(_reached, obj_attr)
        if in_set is not None:
            uuid_, item = in_set
            location['mode'] = _MODE_UUID
            location['uuid'] = uuid_
            continue

        if type(obj_attr).__name__ not in type_settings:
            serialization_setting = MODE_YES
        else:
            serialization_setting = type_settings[type(obj_attr).__name__][0]
            serialization_function = type_settings[type(obj_attr).__name__][1]

        uuid_ = _set_add_obj(_reached, obj_attr)
        location['uuid'] = uuid_
        location['mode'] = serialization_setting

        if serialization_setting == MODE_YES:
            location['value'] = convert_to_data(obj_attr, _reached)
            if location['value'] is FALLBACK:
                location['mode'] = MODE_NO
                location['value'] = {}
        elif serialization_setting == MODE_NO:
            continue
        elif serialization_setting == MODE_FALLBACK:
            location['value'] = obj_attr
        elif serialization_setting == MODE_REPR:
            location['value'] = repr(obj_attr)
        elif serialization_setting == MODE_FUNCTION:
            location['value'] = serialization_function(obj_attr, _reached)
            location['class'] = type(obj_attr).__name__
        else:
            raise ValueError('Unknown serialization mode "%s"' % serialization_setting)
    return data

def convert_to_obj(data:typing.Dict, allow_mode_repr:bool=True, _reached=None) -> object:
    if not version_check(data['version'], data['min_version']):
        message = 'data version %i incompatable with data version %i' % (data['version'], VERSION)
        if _VER_ERROR_LVL == 2:
            raise VersionError(message)
        elif _VER_ERROR_LVL == 1:
            warnings.warn(VersionWarning(message))

    if 'force_use_uuid' in data:
        in_set = _in_set_uuid(_reached, data['uuid'])
        if in_set is not None:
            return in_set[1]
        else:
            raise IndexError('No object with uuid "%i"' % data['uuid'])

    if _reached is None:
        _reached = list()

    obj_type = getattr(__import__(data['module']), data['type'])

    if data['type'] not in type_settings:
        serialization_setting = MODE_YES
    else:
        serialization_setting = type_settings[data['type']][0]
        deserialization_function = type_settings[data['type']][2]

    obj = obj_type.__new__(obj_type)
    _set_add_uuid(_reached, data['uuid'], obj)

    if serialization_setting == MODE_FALLBACK:
        return data['value']
    elif serialization_setting == MODE_FUNCTION:
        return deserialization_function(data['value'], allow_mode_repr, _reached)

    for (name, attrdata) in data['attrs'].items():
        mode = attrdata['mode']
        value = attrdata['value']
        uuid_ = attrdata['uuid']

        if mode == MODE_YES:
            obj_attr = convert_to_obj(value, _reached)
        elif mode == MODE_NO:
            obj_attr = None
        elif mode == MODE_FALLBACK:
            obj_attr = value
        elif mode == MODE_REPR:
            if allow_mode_repr:
                obj_attr = eval(value)
            else:
                raise ValueError('MODE_REPR is not allowed; was attempting to deserialize "%s"' % value)
        elif mode == MODE_FUNCTION:
            obj_attr = type_settings[attrdata['class']][2](value, allow_mode_repr, _reached)
        elif mode == _MODE_UUID:
            in_set = _in_set_uuid(_reached, uuid_)
            if in_set is not None:
                uuid_, obj_attr = in_set
            else:
                raise IndexError('No object with uuid "%i"' % uuid_)
        else:
            raise ValueError('Unknown serialization mode "%s"' % mode)
        setattr(obj, name, obj_attr)
        _set_add_uuid(_reached, uuid_, obj_attr)
    return obj

def dump(obj, *jargs, **jkwargs):
    data = convert_to_data(obj)
    return json.dump(data, *jargs, **jkwargs)

def dumps(obj, *jargs, **jkwargs):
    data = convert_to_data(obj)
    return json.dumps(data, *jargs, **jkwargs)

def load(*jargs, allow_mode_repr=True, **jkwargs) -> object:
    data = json.load(*jargs, **jkwargs)
    return convert_to_obj(data)

def load(*jargs, allow_mode_repr=True, **jkwargs):
    data = json.load(*jargs, **jkwargs)
    return convert_to_obj(data)

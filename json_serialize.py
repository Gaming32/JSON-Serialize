import sys
import json, uuid

MODE_YES = 'yes'
MODE_NO = 'no'
MODE_FALLBACK = 'fallback'
MODE_REPR = 'repr'
MODE_FUNCTION = 'function'
_MODE_IID = 'iid'
class FALLBACK: pass

def _serialize_list(obj, _reached):
    return [convert_to_data(x, _reached) for x in obj]
def _deserialize_list(value, allow_mode_repr, _reached):
    return [convert_to_obj(x, allow_mode_repr, _reached) for x in value]
def _serialize_dict(obj, _reached):
    return {k: convert_to_data(x, _reached) for (k, x) in obj.items()}
def _deserialize_dict(value, allow_mode_repr, _reached):
    return {k: convert_to_obj(x, allow_mode_repr, _reached) for (k, x) in value.items()}

type_settings = {
    'str': [MODE_FALLBACK, None, None],
    'int': [MODE_FALLBACK, None, None],
    'float': [MODE_FALLBACK, None, None],
    'list': [MODE_FUNCTION, _serialize_list, _deserialize_list],
    'dict': [MODE_FUNCTION, _serialize_dict, _deserialize_dict],
    'NoneType': [MODE_FALLBACK, None, None],
}

def serialization_settings(serialization_mode=MODE_YES, serialization_function=None, deserialization_function=None):
    def descriptor(cls):
        type_settings[cls.__name__] = [serialization_mode, serialization_function, deserialization_function]
        return cls
    return descriptor

def _in_set_obj(set, obj):
    for (iid, item) in set:
        if item is obj:
            return iid, item
    return None
def _in_set_iid(set, iid):
    for (this_iid, item) in set:
        if this_iid == iid:
            return iid, item
    return None
def _set_add_obj(set, obj):
    iid = uuid.uuid1().int
    _set_add_iid(set, iid, obj)
    return iid
def _set_add_iid(set, iid, obj):
    set.append((iid, obj))

def convert_to_data(obj, _reached=None):
    if _reached is None:
        _reached = list()

    data = {}
    data['module'] = obj.__class__.__module__
    data['type'] = obj.__class__.__name__
    data['attrs'] = {}
    
    in_set = _in_set_obj(_reached, obj)
    if in_set is not None:
        iid, item = in_set
        data['mode'] = _MODE_IID
        data['iid'] = iid
        data['force_use_iid'] = True
        return data

    iid = _set_add_obj(_reached, obj)
    data['iid'] = iid

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
            iid, item = in_set
            location['mode'] = _MODE_IID
            location['iid'] = iid
            continue

        if type(obj_attr).__name__ not in type_settings:
            serialization_setting = MODE_YES
        else:
            serialization_setting = type_settings[type(obj_attr).__name__][0]
            serialization_function = type_settings[type(obj_attr).__name__][1]

        iid = _set_add_obj(_reached, obj_attr)
        location['iid'] = iid
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

def convert_to_obj(data, allow_mode_repr=True, _reached=None):
    if 'force_use_iid' in data:
        in_set = _in_set_iid(_reached, data['iid'])
        if in_set is not None:
            return in_set[1]
        else:
            raise IndexError('No object with iid "%i"' % data['iid'])

    if _reached is None:
        _reached = list()

    obj_type = getattr(__import__(data['module']), data['type'])

    if data['type'] not in type_settings:
        serialization_setting = MODE_YES
    else:
        serialization_setting = type_settings[data['type']][0]
        deserialization_function = type_settings[data['type']][2]

    obj = obj_type.__new__(obj_type)
    _set_add_iid(_reached, data['iid'], obj)

    if serialization_setting == MODE_FALLBACK:
        return data['value']
    elif serialization_setting == MODE_FUNCTION:
        return deserialization_function(data['value'], allow_mode_repr, _reached)

    for (name, attrdata) in data['attrs'].items():
        mode = attrdata['mode']
        value = attrdata['value']
        iid = attrdata['iid']

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
        elif mode == _MODE_IID:
            in_set = _in_set_iid(_reached, iid)
            if in_set is not None:
                iid, obj_attr = in_set
            else:
                raise IndexError('No object with iid "%i"' % iid)
        else:
            raise ValueError('Unknown serialization mode "%s"' % mode)
        setattr(obj, name, obj_attr)
        _set_add_iid(_reached, iid, obj_attr)
    return obj

def dump(obj, *jargs, **jkwargs):
    data = convert_to_data(obj)
    return json.dump(data, *jargs, **jkwargs)

def dumps(obj, *jargs, **jkwargs):
    data = convert_to_data(obj)
    return json.dumps(data, *jargs, **jkwargs)

def load(*jargs, **jkwargs):
    data = json.load(*jargs, **jkwargs)
    return convert_to_obj(data)

def load(*jargs, **jkwargs):
    data = json.load(*jargs, **jkwargs)
    return convert_to_obj(data)
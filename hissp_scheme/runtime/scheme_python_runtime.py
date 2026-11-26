"""Runtime helpers for the `(scheme python)` interop library.

This module deliberately deals with Python-native containers and attributes.
Scheme data ownership stays elsewhere: `(scheme base)` owns Pair/vector
operations and `(srfi 69)` owns hash-table operations.
"""

from __future__ import annotations

import builtins

import hissp

from scheme_pairs import cons, list_to_py, py_to_list
from hissp_scheme.runtime.srfi69_runtime import hash_table_q, hash_table_set_bang


_MISSING = object()


def _python_name(name):
    """Normalize a Scheme symbol/string into a Python attribute name."""

    if not isinstance(name, str):
        raise TypeError("Python attribute names must be strings or symbols")
    return hissp.demunge(name).replace("-", "_")


def dict_q(obj):
    return isinstance(obj, dict)


def make_dict(*items):
    if len(items) % 2:
        raise ValueError("make-dict requires key/value pairs")
    result = {}
    for index in range(0, len(items), 2):
        result[items[index]] = items[index + 1]
    return result


def make_dict_from_list(items):
    return make_dict(*list_to_py(items)[0])


def _require_dict(obj, procedure):
    if not dict_q(obj):
        raise TypeError(f"{procedure} expected a Python dict")
    return obj


def dict_ref(dictionary, key):
    return _require_dict(dictionary, "dict-ref")[key]


def dict_ref_default(dictionary, key, default):
    return _require_dict(dictionary, "dict-ref/default").get(key, default)


def dict_set_bang(dictionary, key, value):
    _require_dict(dictionary, "dict-set!")[key] = value
    return None


def dict_delete_bang(dictionary, key):
    _require_dict(dictionary, "dict-delete!").pop(key, None)
    return None


def dict_exists_q(dictionary, key):
    return key in _require_dict(dictionary, "dict-exists?")


def dict_keys(dictionary):
    return py_to_list(_require_dict(dictionary, "dict-keys").keys())


def dict_values(dictionary):
    return py_to_list(_require_dict(dictionary, "dict-values").values())


def dict_items(dictionary):
    return py_to_list(
        cons(key, value)
        for key, value in _require_dict(dictionary, "dict-items").items()
    )


def dict_copy(dictionary):
    return dict(_require_dict(dictionary, "dict-copy"))


def dict_update_bang(dictionary, other):
    _require_dict(dictionary, "dict-update!").update(
        _require_dict(other, "dict-update!")
    )
    return dictionary


def dict_to_hash_table(dictionary, hash_table):
    for key, value in _require_dict(dictionary, "dict->hash-table").items():
        hash_table_set_bang(hash_table, key, value)
    return hash_table


def hash_table_to_dict(hash_table):
    if not hash_table_q(hash_table):
        raise TypeError("hash-table->dict expected an SRFI-69 hash table")
    return {key: value for key, value in hash_table._entries.values()}


def tuple_q(obj):
    return isinstance(obj, tuple)


def make_tuple(*items):
    return tuple(items)


def _require_tuple(obj, procedure):
    if not tuple_q(obj):
        raise TypeError(f"{procedure} expected a Python tuple")
    return obj


def tuple_ref(value, index):
    return _require_tuple(value, "tuple-ref")[index]


def tuple_length(value):
    return len(_require_tuple(value, "tuple-length"))


def tuple_to_list(value):
    return py_to_list(_require_tuple(value, "tuple->list"))


def list_to_tuple(value):
    return tuple(list_to_py(value)[0])


def tuple_to_vector(value):
    return builtins.list(_require_tuple(value, "tuple->vector"))


def vector_to_tuple(value):
    if not isinstance(value, list):
        raise TypeError("vector->tuple expected a Scheme vector/Python list")
    return tuple(value)


def python_list_to_list(value):
    if not isinstance(value, list):
        raise TypeError("python-list->list expected a Python list")
    return py_to_list(value)


def list_to_python_list(value):
    return builtins.list(list_to_py(value)[0])


def python_list_to_vector(value):
    if not isinstance(value, list):
        raise TypeError("python-list->vector expected a Python list")
    return builtins.list(value)


def vector_to_python_list(value):
    if not isinstance(value, list):
        raise TypeError("vector->python-list expected a Scheme vector/Python list")
    return builtins.list(value)


def item_ref(obj, key):
    return obj[key]


def item_set_bang(obj, key, value):
    obj[key] = value
    return None


def item_delete_bang(obj, key):
    del obj[key]
    return None


def object_q(obj):
    return hasattr(obj, "__class__")


def attribute_ref(obj, name):
    return getattr(obj, _python_name(name))


def attribute_ref_default(obj, name, default):
    return getattr(obj, _python_name(name), default)


def attribute_set_bang(obj, name, value):
    setattr(obj, _python_name(name), value)
    return None


def attribute_delete_bang(obj, name):
    if hasattr(obj, _python_name(name)):
        delattr(obj, _python_name(name))
    return None


def attribute_exists_q(obj, name):
    return hasattr(obj, _python_name(name))


def class_q(obj):
    return isinstance(obj, type)


def object_class(obj):
    return type(obj)


def class_name(cls):
    if not class_q(cls):
        raise TypeError("class-name expected a Python class")
    return cls.__name__


def is_a_q(obj, cls):
    if not class_q(cls):
        raise TypeError("is-a? expected a Python class")
    return isinstance(obj, cls)


def subclass_q(subclass, superclass):
    if not class_q(subclass) or not class_q(superclass):
        raise TypeError("subclass? expected Python classes")
    return issubclass(subclass, superclass)


def make_object(cls, *args):
    if not class_q(cls):
        raise TypeError("make-object expected a Python class")
    return cls(*args)


def make_object_from_list(cls, args):
    return make_object(cls, *list_to_py(args)[0])


def method_ref(obj, name):
    method = getattr(obj, _python_name(name))
    if not callable(method):
        raise TypeError(f"{_python_name(name)} is not callable")
    return method


def call_method(obj, name, *args):
    return method_ref(obj, name)(*args)


def call_method_from_list(obj, name, args):
    return call_method(obj, name, *list_to_py(args)[0])


__all__ = [
    "dict_q",
    "make_dict",
    "make_dict_from_list",
    "dict_ref",
    "dict_ref_default",
    "dict_set_bang",
    "dict_delete_bang",
    "dict_exists_q",
    "dict_keys",
    "dict_values",
    "dict_items",
    "dict_copy",
    "dict_update_bang",
    "dict_to_hash_table",
    "hash_table_to_dict",
    "tuple_q",
    "make_tuple",
    "tuple_ref",
    "tuple_length",
    "tuple_to_list",
    "list_to_tuple",
    "tuple_to_vector",
    "vector_to_tuple",
    "python_list_to_list",
    "list_to_python_list",
    "python_list_to_vector",
    "vector_to_python_list",
    "item_ref",
    "item_set_bang",
    "item_delete_bang",
    "object_q",
    "attribute_ref",
    "attribute_ref_default",
    "attribute_set_bang",
    "attribute_delete_bang",
    "attribute_exists_q",
    "class_q",
    "object_class",
    "class_name",
    "is_a_q",
    "subclass_q",
    "make_object",
    "make_object_from_list",
    "method_ref",
    "call_method",
    "call_method_from_list",
]

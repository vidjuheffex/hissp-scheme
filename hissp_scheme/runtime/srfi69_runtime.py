"""Runtime substrate for `(srfi 69)` hash tables.

SRFI-69 hash tables are mutable maps with configurable equivalence and hash
functions. Python's `dict` gives us the right storage primitive, but a thin key
wrapper is required so Scheme-level equivalence predicates can participate in
lookup instead of always using Python's native equality.
"""

from __future__ import annotations

import builtins
import operator
from dataclasses import dataclass
from typing import Any, Callable

from scheme_pairs import car, cdr, cons, list_to_py, pair_q, py_to_list


_MISSING = object()
_DEFAULT_BOUND = 2**31 - 1


def _bounded(value: int, bound: int | None) -> int:
    if bound is None:
        return value
    return value % bound


def _structural_hashable(value):
    """Convert common Scheme/Python aggregate data to hashable structure."""

    if pair_q(value):
        items, tail = list_to_py(value, require_proper=False)
        if tail == ():
            return tuple(_structural_hashable(item) for item in items)
        return (
            "dotted-list",
            tuple(_structural_hashable(item) for item in items),
            _structural_hashable(tail),
        )
    if isinstance(value, list):
        return tuple(_structural_hashable(item) for item in value)
    if isinstance(value, dict):
        return tuple(
            sorted(
                (_structural_hashable(key), _structural_hashable(item))
                for key, item in value.items()
            )
        )
    return value


def hash_value(obj, bound=None):
    """Generic SRFI-69 `hash` implementation."""

    try:
        value = builtins.hash(_structural_hashable(obj))
    except TypeError:
        value = builtins.hash(repr(obj))
    return _bounded(value, bound)


def string_hash(value, bound=None):
    if not isinstance(value, str):
        raise TypeError("string-hash expected a string")
    return _bounded(builtins.hash(value), bound)


def string_ci_hash(value, bound=None):
    if not isinstance(value, str):
        raise TypeError("string-ci-hash expected a string")
    return _bounded(builtins.hash(value.casefold()), bound)


def hash_by_identity(obj, bound=None):
    return _bounded(id(obj), bound)


@dataclass(frozen=True)
class _WrappedKey:
    table: "HashTable"
    key: Any

    def __hash__(self):
        return int(self.table.hash_function(self.key))

    def __eq__(self, other):
        if not isinstance(other, _WrappedKey) or self.table is not other.table:
            return False
        return bool(self.table.equivalence_function(self.key, other.key))


class HashTable:
    """A mutable SRFI-69 hash table backed by Python `dict`."""

    def __init__(
        self,
        equivalence_function: Callable[[Any, Any], bool] = operator.eq,
        hash_function: Callable[[Any], int] = hash_value,
    ):
        self.equivalence_function = equivalence_function
        self.hash_function = hash_function
        self._entries: dict[_WrappedKey, tuple[Any, Any]] = {}

    def _wrapped(self, key):
        return _WrappedKey(self, key)


def make_hash_table(equivalence_function=operator.eq, hash_function=hash_value):
    return HashTable(equivalence_function, hash_function)


def hash_table_q(obj):
    return isinstance(obj, HashTable)


def _require_hash_table(hash_table, procedure):
    if not hash_table_q(hash_table):
        raise TypeError(f"{procedure} expected a hash table")
    return hash_table


def _call_missing_thunk(thunk, procedure):
    if not callable(thunk):
        raise TypeError(f"{procedure} expected a missing-key thunk")
    return thunk()


def hash_table_equivalence_function(hash_table):
    return _require_hash_table(
        hash_table, "hash-table-equivalence-function"
    ).equivalence_function


def hash_table_hash_function(hash_table):
    return _require_hash_table(hash_table, "hash-table-hash-function").hash_function


def hash_table_ref(hash_table, key, thunk=_MISSING):
    hash_table = _require_hash_table(hash_table, "hash-table-ref")
    entry = hash_table._entries.get(hash_table._wrapped(key), _MISSING)
    if entry is not _MISSING:
        return entry[1]
    if thunk is not _MISSING:
        return _call_missing_thunk(thunk, "hash-table-ref")
    raise KeyError(key)


def hash_table_ref_default(hash_table, key, default):
    return hash_table_ref(hash_table, key, lambda: default)


def hash_table_set_bang(hash_table, key, value):
    hash_table = _require_hash_table(hash_table, "hash-table-set!")
    hash_table._entries[hash_table._wrapped(key)] = (key, value)
    return None


def hash_table_delete_bang(hash_table, key):
    hash_table = _require_hash_table(hash_table, "hash-table-delete!")
    hash_table._entries.pop(hash_table._wrapped(key), None)
    return None


def hash_table_exists_q(hash_table, key):
    hash_table = _require_hash_table(hash_table, "hash-table-exists?")
    return hash_table._wrapped(key) in hash_table._entries


def hash_table_update_bang(hash_table, key, function, thunk=_MISSING):
    value = hash_table_ref(hash_table, key, thunk)
    hash_table_set_bang(hash_table, key, function(value))
    return None


def hash_table_update_bang_default(hash_table, key, function, default):
    return hash_table_update_bang(hash_table, key, function, lambda: default)


def hash_table_size(hash_table):
    return len(_require_hash_table(hash_table, "hash-table-size")._entries)


def hash_table_walk(hash_table, procedure):
    hash_table = _require_hash_table(hash_table, "hash-table-walk")
    for key, value in builtins.list(hash_table._entries.values()):
        procedure(key, value)
    return None


def hash_table_fold(hash_table, function, init_value):
    result = init_value
    for key, value in builtins.list(
        _require_hash_table(hash_table, "hash-table-fold")._entries.values()
    ):
        result = function(key, value, result)
    return result


def hash_table_keys(hash_table):
    return py_to_list(
        key
        for key, _ in _require_hash_table(hash_table, "hash-table-keys")._entries.values()
    )


def hash_table_values(hash_table):
    return py_to_list(
        value
        for _, value in _require_hash_table(
            hash_table, "hash-table-values"
        )._entries.values()
    )


def hash_table_to_alist(hash_table):
    return py_to_list(
        cons(key, value)
        for key, value in _require_hash_table(
            hash_table, "hash-table->alist"
        )._entries.values()
    )


def hash_table_copy(hash_table):
    hash_table = _require_hash_table(hash_table, "hash-table-copy")
    result = make_hash_table(
        hash_table.equivalence_function,
        hash_table.hash_function,
    )
    for key, value in hash_table._entries.values():
        hash_table_set_bang(result, key, value)
    return result


def hash_table_merge_bang(hash_table1, hash_table2):
    hash_table1 = _require_hash_table(hash_table1, "hash-table-merge!")
    hash_table2 = _require_hash_table(hash_table2, "hash-table-merge!")
    for key, value in hash_table2._entries.values():
        hash_table_set_bang(hash_table1, key, value)
    return hash_table1


def alist_to_hash_table(alist, equivalence_function=operator.eq, hash_function=hash_value):
    result = make_hash_table(equivalence_function, hash_function)
    for association in list_to_py(alist)[0]:
        key = car(association)
        if not hash_table_exists_q(result, key):
            hash_table_set_bang(result, key, cdr(association))
    return result


__all__ = [
    "make_hash_table",
    "hash_table_q",
    "alist_to_hash_table",
    "hash_table_equivalence_function",
    "hash_table_hash_function",
    "hash_table_ref",
    "hash_table_ref_default",
    "hash_table_set_bang",
    "hash_table_delete_bang",
    "hash_table_exists_q",
    "hash_table_update_bang",
    "hash_table_update_bang_default",
    "hash_table_size",
    "hash_table_keys",
    "hash_table_values",
    "hash_table_walk",
    "hash_table_fold",
    "hash_table_to_alist",
    "hash_table_copy",
    "hash_table_merge_bang",
    "hash_value",
    "string_hash",
    "string_ci_hash",
    "hash_by_identity",
]

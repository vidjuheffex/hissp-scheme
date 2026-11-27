"""Runtime substrate for `(srfi 132)` sort libraries.

Sorting is delegated to Python's `sorted`/`list.sort` (Timsort), which is
stable, so the plain and `stable` SRFI-132 variants share one implementation.
Timsort only ever compares with `<`, which matches SRFI-132's contract of a
single strict "less than" procedure. Scheme truth is "anything but #f", so
comparator results are tested with `is not False`.
"""

from __future__ import annotations

from scheme_pairs import list_to_py, pair_q, py_to_list, vector_q


class _Key:
    __slots__ = ("value", "less")

    def __init__(self, value, less):
        self.value = value
        self.less = less

    def __lt__(self, other):
        return self.less(self.value, other.value) is not False


def _less_q(less, left, right):
    return less(left, right) is not False


def _sorted(less, items):
    return [key.value for key in sorted(_Key(item, less) for item in items)]


def _require_procedure(value, procedure):
    if not callable(value):
        raise TypeError(f"{procedure} expected a procedure, got {value!r}")
    return value


def _require_vector(value, procedure):
    if not vector_q(value):
        raise TypeError(f"{procedure} expected a vector, got {value!r}")
    return value


def _list_items(value, procedure):
    try:
        return list_to_py(value)[0]
    except TypeError as error:
        raise TypeError(f"{procedure}: {error}") from None


def _list_pairs(value, procedure):
    _list_items(value, procedure)
    pairs = []
    while pair_q(value):
        pairs.append(value)
        value = value.cdr
    return pairs


def _relink(pairs):
    for pair, following in zip(pairs, pairs[1:]):
        pair.cdr = following
    if not pairs:
        return ()
    pairs[-1].cdr = ()
    return pairs[0]


def _range(vector, start, end, procedure):
    length = len(vector)
    stop = length if end is None else end
    if not (
        isinstance(start, int)
        and isinstance(stop, int)
        and 0 <= start <= stop <= length
    ):
        raise IndexError(
            f"{procedure}: invalid range [{start}, {end}) for vector of length {length}"
        )
    return start, stop


def _merge(less, left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if _less_q(less, right[j], left[i]):
            result.append(right[j])
            j += 1
        else:
            result.append(left[i])
            i += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


def _delete_neighbor_dups(same, items):
    result = []
    for item in items:
        if not result or same(result[-1], item) is False:
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Sortedness predicates
# ---------------------------------------------------------------------------


def _items_sorted_q(less, items):
    return not any(
        _less_q(less, items[index + 1], items[index]) for index in range(len(items) - 1)
    )


def list_sorted_q(less, lis):
    _require_procedure(less, "list-sorted?")
    return _items_sorted_q(less, _list_items(lis, "list-sorted?"))


def vector_sorted_q(less, vector, start=0, end=None):
    _require_procedure(less, "vector-sorted?")
    _require_vector(vector, "vector-sorted?")
    start, end = _range(vector, start, end, "vector-sorted?")
    return _items_sorted_q(less, vector[start:end])


# ---------------------------------------------------------------------------
# General sort procedures
# ---------------------------------------------------------------------------


def list_sort(less, lis):
    _require_procedure(less, "list-sort")
    return py_to_list(_sorted(less, _list_items(lis, "list-sort")))


def list_sort_bang(less, lis):
    _require_procedure(less, "list-sort!")
    pairs = _list_pairs(lis, "list-sort!")
    for pair, item in zip(pairs, _sorted(less, [pair.car for pair in pairs])):
        pair.car = item
    return lis


def vector_sort(less, vector, start=0, end=None):
    _require_procedure(less, "vector-sort")
    _require_vector(vector, "vector-sort")
    start, end = _range(vector, start, end, "vector-sort")
    return _sorted(less, vector[start:end])


def vector_sort_bang(vector, less, start=0, end=None):
    _require_procedure(less, "vector-sort!")
    _require_vector(vector, "vector-sort!")
    start, end = _range(vector, start, end, "vector-sort!")
    vector[start:end] = _sorted(less, vector[start:end])
    return None


# ---------------------------------------------------------------------------
# Merge procedures
# ---------------------------------------------------------------------------


def list_merge(less, lis1, lis2):
    _require_procedure(less, "list-merge")
    return py_to_list(
        _merge(
            less,
            _list_items(lis1, "list-merge"),
            _list_items(lis2, "list-merge"),
        )
    )


def list_merge_bang(less, lis1, lis2):
    _require_procedure(less, "list-merge!")
    left = _list_pairs(lis1, "list-merge!")
    right = _list_pairs(lis2, "list-merge!")
    pairs = _merge(
        lambda a, b: less(a.car, b.car),
        left,
        right,
    )
    return _relink(pairs)


def vector_merge(less, vector1, vector2, start1=0, end1=None, start2=0, end2=None):
    _require_procedure(less, "vector-merge")
    _require_vector(vector1, "vector-merge")
    _require_vector(vector2, "vector-merge")
    start1, end1 = _range(vector1, start1, end1, "vector-merge")
    start2, end2 = _range(vector2, start2, end2, "vector-merge")
    return _merge(less, vector1[start1:end1], vector2[start2:end2])


def vector_merge_bang(
    less, to, vector1, vector2, start=0, start1=0, end1=None, start2=0, end2=None
):
    _require_procedure(less, "vector-merge!")
    _require_vector(to, "vector-merge!")
    _require_vector(vector1, "vector-merge!")
    _require_vector(vector2, "vector-merge!")
    start1, end1 = _range(vector1, start1, end1, "vector-merge!")
    start2, end2 = _range(vector2, start2, end2, "vector-merge!")
    merged = _merge(less, vector1[start1:end1], vector2[start2:end2])
    if not (isinstance(start, int) and 0 <= start and start + len(merged) <= len(to)):
        raise IndexError(
            f"vector-merge!: {len(merged)} elements do not fit at index {start} "
            f"of a vector of length {len(to)}"
        )
    to[start : start + len(merged)] = merged
    return None


# ---------------------------------------------------------------------------
# Deleting duplicate neighbors
# ---------------------------------------------------------------------------


def list_delete_neighbor_dups(same, lis):
    _require_procedure(same, "list-delete-neighbor-dups")
    return py_to_list(
        _delete_neighbor_dups(same, _list_items(lis, "list-delete-neighbor-dups"))
    )


def list_delete_neighbor_dups_bang(same, lis):
    _require_procedure(same, "list-delete-neighbor-dups!")
    kept = []
    for pair in _list_pairs(lis, "list-delete-neighbor-dups!"):
        if not kept or same(kept[-1].car, pair.car) is False:
            kept.append(pair)
    return _relink(kept)


def vector_delete_neighbor_dups(same, vector, start=0, end=None):
    _require_procedure(same, "vector-delete-neighbor-dups")
    _require_vector(vector, "vector-delete-neighbor-dups")
    start, end = _range(vector, start, end, "vector-delete-neighbor-dups")
    return _delete_neighbor_dups(same, vector[start:end])


def vector_delete_neighbor_dups_bang(same, vector, start=0, end=None):
    _require_procedure(same, "vector-delete-neighbor-dups!")
    _require_vector(vector, "vector-delete-neighbor-dups!")
    start, end = _range(vector, start, end, "vector-delete-neighbor-dups!")
    kept = _delete_neighbor_dups(same, vector[start:end])
    vector[start : start + len(kept)] = kept
    return start + len(kept)


# ---------------------------------------------------------------------------
# Finding the median and selection
# ---------------------------------------------------------------------------


def _median(items, knil, mean):
    if not items:
        return knil
    middle = len(items) // 2
    if len(items) % 2:
        return items[middle]
    return mean(items[middle - 1], items[middle])


def vector_find_median(less, vector, knil, mean):
    _require_procedure(less, "vector-find-median")
    _require_vector(vector, "vector-find-median")
    return _median(_sorted(less, vector), knil, mean)


def vector_find_median_bang(less, vector, knil, mean):
    _require_procedure(less, "vector-find-median!")
    _require_vector(vector, "vector-find-median!")
    vector[:] = _sorted(less, vector)
    return _median(vector, knil, mean)


def _require_rank(k, start, end, procedure):
    if not (isinstance(k, int) and 0 <= k < end - start):
        raise IndexError(
            f"{procedure}: k={k!r} is outside the {end - start} selected elements"
        )


def vector_select_bang(less, vector, k, start=0, end=None):
    _require_procedure(less, "vector-select!")
    _require_vector(vector, "vector-select!")
    start, end = _range(vector, start, end, "vector-select!")
    _require_rank(k, start, end, "vector-select!")
    vector[start:end] = _sorted(less, vector[start:end])
    return vector[start + k]


def vector_separate_bang(less, vector, k, start=0, end=None):
    _require_procedure(less, "vector-separate!")
    _require_vector(vector, "vector-separate!")
    start, end = _range(vector, start, end, "vector-separate!")
    if not (isinstance(k, int) and 0 <= k <= end - start):
        raise IndexError(
            f"vector-separate!: k={k!r} is outside the {end - start} selected elements"
        )
    vector[start:end] = _sorted(less, vector[start:end])
    return None


__all__ = [
    "list_sorted_q",
    "vector_sorted_q",
    "list_sort",
    "list_sort_bang",
    "vector_sort",
    "vector_sort_bang",
    "list_merge",
    "list_merge_bang",
    "vector_merge",
    "vector_merge_bang",
    "list_delete_neighbor_dups",
    "list_delete_neighbor_dups_bang",
    "vector_delete_neighbor_dups",
    "vector_delete_neighbor_dups_bang",
    "vector_find_median",
    "vector_find_median_bang",
    "vector_select_bang",
    "vector_separate_bang",
]

"""Runtime substrate for `(srfi 1)` list procedures.

Lists are chains of `scheme_pairs.Pair` ending in `()`. Procedures that take
several lists stop at the end of the shortest one, so a circular list may be
mixed with finite ones. Scheme truth is "anything but #f", so predicate results
are tested with `is not False`.

SRFI-1 allows, but does not require, the linear-update (`!`) procedures to
reuse their arguments' storage; here they are the pure procedures.
"""

from __future__ import annotations

import builtins

from scheme_pairs import Pair, py_to_list, scheme_append

from hissp_scheme.runtime.base_runtime import equal_q
from hissp_scheme.runtime.control_runtime import values


def _items(lis):
    items = []
    while lis.__class__ is Pair:
        items.append(lis.car)
        lis = lis.cdr
    return items


def _rows(lists):
    """Yield the cars of `lists` in lock step until the shortest one ends."""

    lists = builtins.list(lists)
    while all(lis.__class__ is Pair for lis in lists):
        yield [lis.car for lis in lists]
        lists = [lis.cdr for lis in lists]


def _pairs(lists):
    """Yield the successive sublists of `lists` in lock step."""

    lists = builtins.list(lists)
    while all(lis.__class__ is Pair for lis in lists):
        following = [lis.cdr for lis in lists]
        yield lists
        lists = following


def _require_count(k, procedure):
    if not (isinstance(k, int) and not isinstance(k, bool) and k >= 0):
        raise TypeError(f"{procedure} expected a non-negative exact integer, got {k!r}")
    return k


def _member_q(same, x, lis):
    while lis.__class__ is Pair:
        if same(x, lis.car) is not False:
            return True
        lis = lis.cdr
    return False


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------


def xcons(d, a):
    return Pair(a, d)


def cons_star(first, *rest):
    if not rest:
        return first
    return py_to_list((first, *rest[:-1]), rest[-1])


def list_tabulate(n, init_proc):
    _require_count(n, "list-tabulate")
    return py_to_list([init_proc(i) for i in range(n)])


def circular_list(elt, *elts):
    head = py_to_list((elt, *elts))
    last = head
    while last.cdr.__class__ is Pair:
        last = last.cdr
    last.cdr = head
    return head


def iota(count, start=0, step=1):
    _require_count(count, "iota")
    return py_to_list([start + i * step for i in range(count)])


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


def _classify(x):
    """Return 'proper', 'dotted', or 'circular' for any object."""

    slow = fast = x
    while True:
        if fast.__class__ is not Pair:
            return "proper" if fast == () else "dotted"
        fast = fast.cdr
        if fast.__class__ is not Pair:
            return "proper" if fast == () else "dotted"
        fast = fast.cdr
        slow = slow.cdr
        if fast is slow:
            return "circular"


def proper_list_q(x):
    return _classify(x) == "proper"


def circular_list_q(x):
    return _classify(x) == "circular"


def dotted_list_q(x):
    return _classify(x) == "dotted"


def not_pair_q(x):
    return x.__class__ is not Pair


def null_list_q(lis):
    if lis.__class__ is Pair:
        return False
    if lis == ():
        return True
    raise TypeError(f"null-list? expected a list, got {lis!r}")


def list_eq(same, *lists):
    for left, right in zip(lists, lists[1:]):
        if left is right:
            continue
        while left.__class__ is Pair and right.__class__ is Pair:
            if same(left.car, right.car) is False:
                return False
            left, right = left.cdr, right.cdr
        if left.__class__ is Pair or right.__class__ is Pair:
            return False
    return True


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


def _nth(index, name):
    def selector(lis):
        value = lis
        for _ in range(index):
            if value.__class__ is not Pair:
                break
            value = value.cdr
        if value.__class__ is not Pair:
            raise TypeError(f"{name} expected a list of at least {index + 1} elements")
        return value.car

    selector.__name__ = name
    return selector


first = _nth(0, "first")
second = _nth(1, "second")
third = _nth(2, "third")
fourth = _nth(3, "fourth")
fifth = _nth(4, "fifth")
sixth = _nth(5, "sixth")
seventh = _nth(6, "seventh")
eighth = _nth(7, "eighth")
ninth = _nth(8, "ninth")
tenth = _nth(9, "tenth")


def car_plus_cdr(pair):
    if pair.__class__ is not Pair:
        raise TypeError(f"car+cdr expected a pair, got {pair!r}")
    return values(pair.car, pair.cdr)


def _split(x, i, procedure):
    _require_count(i, procedure)
    prefix = []
    for _ in range(i):
        if x.__class__ is not Pair:
            raise TypeError(f"{procedure}: list has fewer than {i} elements")
        prefix.append(x.car)
        x = x.cdr
    return prefix, x


def take(x, i):
    return py_to_list(_split(x, i, "take")[0])


def drop(x, i):
    return _split(x, i, "drop")[1]


def take_right(flist, i):
    lead = drop(flist, i)
    lag = flist
    while lead.__class__ is Pair:
        lead, lag = lead.cdr, lag.cdr
    return lag


def drop_right(flist, i):
    lead = drop(flist, i)
    lag = flist
    kept = []
    while lead.__class__ is Pair:
        kept.append(lag.car)
        lead, lag = lead.cdr, lag.cdr
    return py_to_list(kept)


def split_at(x, i):
    prefix, rest = _split(x, i, "split-at")
    return values(py_to_list(prefix), rest)


def last_pair(lis):
    if lis.__class__ is not Pair:
        raise TypeError(f"last-pair expected a pair, got {lis!r}")
    while lis.cdr.__class__ is Pair:
        lis = lis.cdr
    return lis


def last(pair):
    return last_pair(pair).car


# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------


def length_plus(x):
    if _classify(x) == "circular":
        return False
    count = 0
    while x.__class__ is Pair:
        count += 1
        x = x.cdr
    return count


def concatenate(lists):
    return scheme_append(*_items(lists))


def append_reverse(rev_head, tail):
    while rev_head.__class__ is Pair:
        tail = Pair(rev_head.car, tail)
        rev_head = rev_head.cdr
    return tail


def zip_lists(clist1, *clists):
    return py_to_list([py_to_list(row) for row in _rows((clist1, *clists))])


def _unzip_columns(lis, width):
    columns = [[] for _ in range(width)]
    for row in _items(lis):
        for column in columns:
            column.append(row.car)
            row = row.cdr
    return [py_to_list(column) for column in columns]


def unzip1(lis):
    return _unzip_columns(lis, 1)[0]


def unzip2(lis):
    return values(*_unzip_columns(lis, 2))


def unzip3(lis):
    return values(*_unzip_columns(lis, 3))


def unzip4(lis):
    return values(*_unzip_columns(lis, 4))


def unzip5(lis):
    return values(*_unzip_columns(lis, 5))


def count(pred, clist1, *clists):
    return sum(1 for row in _rows((clist1, *clists)) if pred(*row) is not False)


# ---------------------------------------------------------------------------
# Fold, unfold, and map
# ---------------------------------------------------------------------------


def fold(kons, knil, clist1, *clists):
    acc = knil
    for row in _rows((clist1, *clists)):
        acc = kons(*row, acc)
    return acc


def fold_right(kons, knil, clist1, *clists):
    acc = knil
    for row in reversed(builtins.list(_rows((clist1, *clists)))):
        acc = kons(*row, acc)
    return acc


def pair_fold(kons, knil, clist1, *clists):
    acc = knil
    for sublists in _pairs((clist1, *clists)):
        acc = kons(*sublists, acc)
    return acc


def pair_fold_right(kons, knil, clist1, *clists):
    acc = knil
    for sublists in reversed(builtins.list(_pairs((clist1, *clists)))):
        acc = kons(*sublists, acc)
    return acc


def reduce(f, ridentity, lis):
    if lis.__class__ is not Pair:
        return ridentity
    return fold(f, lis.car, lis.cdr)


def reduce_right(f, ridentity, lis):
    items = _items(lis)
    if not items:
        return ridentity
    acc = items[-1]
    for item in reversed(items[:-1]):
        acc = f(item, acc)
    return acc


def unfold(stop, mapper, successor, seed, tail_gen=None):
    items = []
    while stop(seed) is False:
        items.append(mapper(seed))
        seed = successor(seed)
    return py_to_list(items, () if tail_gen is None else tail_gen(seed))


def unfold_right(stop, mapper, successor, seed, tail=()):
    result = tail
    while stop(seed) is False:
        result = Pair(mapper(seed), result)
        seed = successor(seed)
    return result


def append_map(f, clist1, *clists):
    results = [f(*row) for row in _rows((clist1, *clists))]
    return scheme_append(*results)


def pair_for_each(f, clist1, *clists):
    for sublists in _pairs((clist1, *clists)):
        f(*sublists)
    return False


def filter_map(f, clist1, *clists):
    results = (f(*row) for row in _rows((clist1, *clists)))
    return py_to_list([result for result in results if result is not False])


# ---------------------------------------------------------------------------
# Filtering and partitioning
# ---------------------------------------------------------------------------


def filter_list(pred, lis):
    return py_to_list([item for item in _items(lis) if pred(item) is not False])


def remove(pred, lis):
    return py_to_list([item for item in _items(lis) if pred(item) is False])


def partition(pred, lis):
    kept, dropped = [], []
    for item in _items(lis):
        (kept if pred(item) is not False else dropped).append(item)
    return values(py_to_list(kept), py_to_list(dropped))


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------


def find_tail(pred, clist):
    while clist.__class__ is Pair:
        if pred(clist.car) is not False:
            return clist
        clist = clist.cdr
    return False


def find(pred, clist):
    while clist.__class__ is Pair:
        if pred(clist.car) is not False:
            return clist.car
        clist = clist.cdr
    return False


def any_of(pred, clist1, *clists):
    for row in _rows((clist1, *clists)):
        result = pred(*row)
        if result is not False:
            return result
    return False


def every(pred, clist1, *clists):
    result = True
    for row in _rows((clist1, *clists)):
        result = pred(*row)
        if result is False:
            return False
    return result


def list_index(pred, clist1, *clists):
    for index, row in enumerate(_rows((clist1, *clists))):
        if pred(*row) is not False:
            return index
    return False


def _span(pred, clist):
    prefix = []
    while clist.__class__ is Pair and pred(clist.car) is not False:
        prefix.append(clist.car)
        clist = clist.cdr
    return prefix, clist


def take_while(pred, clist):
    return py_to_list(_span(pred, clist)[0])


def drop_while(pred, clist):
    return _span(pred, clist)[1]


def span(pred, clist):
    prefix, rest = _span(pred, clist)
    return values(py_to_list(prefix), rest)


def break_span(pred, clist):
    prefix, rest = _span(lambda item: pred(item) is False, clist)
    return values(py_to_list(prefix), rest)


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


def delete(x, lis, same=equal_q):
    return py_to_list([item for item in _items(lis) if same(x, item) is False])


def delete_duplicates(lis, same=equal_q):
    kept = []
    for item in _items(lis):
        if all(same(earlier, item) is False for earlier in kept):
            kept.append(item)
    return py_to_list(kept)


# ---------------------------------------------------------------------------
# Association lists
# ---------------------------------------------------------------------------


def alist_cons(key, datum, alist):
    return Pair(Pair(key, datum), alist)


def alist_copy(alist):
    return py_to_list([Pair(entry.car, entry.cdr) for entry in _items(alist)])


def alist_delete(key, alist, same=equal_q):
    return py_to_list(
        [entry for entry in _items(alist) if same(key, entry.car) is False]
    )


# ---------------------------------------------------------------------------
# Lists as sets
# ---------------------------------------------------------------------------


def lset_le(same, *lists):
    return all(
        all(_member_q(same, x, right) for x in _items(left))
        for left, right in zip(lists, lists[1:])
    )


def lset_eq(same, *lists):
    return all(
        all(_member_q(same, x, right) for x in _items(left))
        and all(_member_q(lambda a, b: same(b, a), y, left) for y in _items(right))
        for left, right in zip(lists, lists[1:])
    )


def lset_adjoin(same, lis, *elts):
    for elt in elts:
        if not _member_q(lambda a, b: same(b, a), elt, lis):
            lis = Pair(elt, lis)
    return lis


def lset_union(same, *lists):
    result = ()
    for lis in lists:
        if result == ():
            result = lis
        elif lis is not result:
            for elt in _items(lis):
                if not _member_q(lambda a, b: same(b, a), elt, result):
                    result = Pair(elt, result)
    return result


def lset_intersection(same, list1, *lists):
    return py_to_list(
        [
            x
            for x in _items(list1)
            if all(_member_q(same, x, lis) for lis in lists if lis is not list1)
        ]
    )


def lset_difference(same, list1, *lists):
    return py_to_list(
        [x for x in _items(list1) if not any(_member_q(same, x, lis) for lis in lists)]
    )


def _diff_and_intersection(same, list1, lists):
    diff, both = [], []
    for x in _items(list1):
        (both if any(_member_q(same, x, lis) for lis in lists) else diff).append(x)
    return diff, both


def lset_diff_plus_intersection(same, list1, *lists):
    diff, both = _diff_and_intersection(same, list1, lists)
    return values(py_to_list(diff), py_to_list(both))


def lset_xor(same, *lists):
    result = ()
    for lis in lists:
        diff, both = _diff_and_intersection(same, result, (lis,))
        if not diff:
            result = lset_difference(same, lis, result)
        elif not both:
            result = scheme_append(lis, result)
        else:
            both = py_to_list(both)
            acc = py_to_list(diff)
            for elt in _items(lis):
                if not _member_q(same, elt, both):
                    acc = Pair(elt, acc)
            result = acc
    return result

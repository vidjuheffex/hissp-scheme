"""Variadic Scheme arithmetic and numeric comparison.

This module doesn't depend on the pair runtime, so the bootstrap prelude can
bind `+`, `<`, and friends to these procedures in every module, including the
core libraries that define pairs. A module that re-runs its prelude (as a
hot-reloaded library does) therefore never sees different arithmetic.
"""

from __future__ import annotations

import math
from fractions import Fraction

from hissp_scheme.runtime.numeric_syntax import _normalize

_EXACT_TYPES = (int, Fraction)

_NO_ARGUMENT = object()


def add(first=0, second=0, *rest):
    result = first + second
    for value in rest:
        result = result + value
    return _normalize(result) if result.__class__ is Fraction else result


def sub(first, second=_NO_ARGUMENT, *rest):
    if second is _NO_ARGUMENT:
        result = -first
    else:
        result = first - second
        for value in rest:
            result = result - value
    return _normalize(result) if result.__class__ is Fraction else result


def mul(first=1, second=1, *rest):
    result = first * second
    for value in rest:
        result = result * value
    return _normalize(result) if result.__class__ is Fraction else result


def _divide(first, second):
    if first.__class__ is int and second.__class__ is int:
        if second == 0:
            raise ZeroDivisionError("/: division by exact zero")
        if first % second == 0:
            return first // second
        return _normalize(Fraction(first, second))
    if isinstance(first, _EXACT_TYPES) and isinstance(second, _EXACT_TYPES):
        if second == 0:
            raise ZeroDivisionError("/: division by exact zero")
        return _normalize(Fraction(first) / Fraction(second))
    try:
        return first / second
    except ZeroDivisionError:
        if isinstance(first, complex) or isinstance(second, complex):
            raise
        numerator = float(first)
        if numerator == 0 or math.isnan(numerator):
            return math.nan
        return math.copysign(math.inf, numerator) * math.copysign(1.0, second)


def div(first, *rest):
    if not rest:
        return _divide(1, first)
    result = first
    for value in rest:
        result = _divide(result, value)
    return result


def _chain(compare, first, second, rest):
    if not compare(first, second):
        return False
    previous = second
    for value in rest:
        if not compare(previous, value):
            return False
        previous = value
    return True


def num_eq(first, second, *rest):
    if not rest:
        return first == second
    return _chain(lambda a, b: a == b, first, second, rest)


def num_lt(first, second, *rest):
    if not rest:
        return first < second
    return _chain(lambda a, b: a < b, first, second, rest)


def num_gt(first, second, *rest):
    if not rest:
        return first > second
    return _chain(lambda a, b: a > b, first, second, rest)


def num_le(first, second, *rest):
    if not rest:
        return first <= second
    return _chain(lambda a, b: a <= b, first, second, rest)


def num_ge(first, second, *rest):
    if not rest:
        return first >= second
    return _chain(lambda a, b: a >= b, first, second, rest)

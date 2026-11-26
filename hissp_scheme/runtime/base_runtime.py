"""Runtime support for `(scheme base)`: equivalence, numbers, and lists.

Numbers use Python's types: `int` and `fractions.Fraction` are exact,
`float` and `complex` are inexact. Exact results that are whole numbers are
always normalized to `int`. Python's `bool` is a subclass of `int`, but it is
not a Scheme number.

Arithmetic stays generic over Python's operators, so `(+ "a" "b")` still
concatenates, which library code relies on for strings and tuples.
"""

from __future__ import annotations

import cmath
import math
from fractions import Fraction

from scheme_pairs import Pair, py_to_list

from hissp_scheme.runtime import control_runtime
from hissp_scheme.runtime.numeric_syntax import (
    _normalize,
    exact,
    string_to_number,
)
from hissp_scheme.runtime.symbols import Symbol

_EXACT_TYPES = (int, Fraction)
_NUMBER_TYPES = (int, Fraction, float, complex)


# Equivalence


def number_q(value):
    return isinstance(value, _NUMBER_TYPES) and value.__class__ is not bool


def exact_q(value):
    _check_number(value, "exact?")
    return isinstance(value, _EXACT_TYPES)


def eq_q(first, second):
    if first is second:
        return True
    # Small integers and characters are immediate values in most Schemes.
    if first.__class__ is second.__class__ and first.__class__ in (int, str):
        return first == second
    return False


def eqv_q(first, second):
    if first is second:
        return True
    first_type = first.__class__
    second_type = second.__class__
    if first_type is bool or second_type is bool:
        return False
    if isinstance(first, _NUMBER_TYPES) and isinstance(second, _NUMBER_TYPES):
        return (
            isinstance(first, _EXACT_TYPES) == isinstance(second, _EXACT_TYPES)
            and first == second
        )
    if first_type is str and second_type is str:
        return first == second
    return False


def equal_q(first, second):
    while True:
        if eqv_q(first, second):
            return True
        if first.__class__ is Pair and second.__class__ is Pair:
            if not equal_q(first.car, second.car):
                return False
            first, second = first.cdr, second.cdr
            continue
        if first.__class__ is list and second.__class__ is list:
            return len(first) == len(second) and all(
                equal_q(a, b) for a, b in zip(first, second)
            )
        if isinstance(first, (Symbol, Pair, bool)) or isinstance(
            second, (Symbol, Pair, bool)
        ):
            return False
        if number_q(first) or number_q(second):
            return False
        # Bytevectors and other Python values compare structurally.
        return first.__class__ is second.__class__ and first == second


# Numbers


def _check_number(value, who):
    if not number_q(value):
        raise TypeError(f"{who}: not a number: {value!r}")


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
        return Fraction(first, second)
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


def complex_q(value):
    return number_q(value)


def real_q(value):
    return number_q(value) and not isinstance(value, complex)


def rational_q(value):
    if isinstance(value, float):
        return math.isfinite(value)
    return number_q(value) and isinstance(value, _EXACT_TYPES)


def integer_q(value):
    if not number_q(value):
        return False
    if value.__class__ is int:
        return True
    if isinstance(value, float):
        return value.is_integer()
    return False


def inexact_q(value):
    _check_number(value, "inexact?")
    return not isinstance(value, _EXACT_TYPES)


def exact_integer_q(value):
    return value.__class__ is int


def nan_q(value):
    if isinstance(value, complex):
        return cmath.isnan(value)
    return isinstance(value, float) and math.isnan(value)


def infinite_q(value):
    if isinstance(value, complex):
        return cmath.isinf(value)
    return isinstance(value, float) and math.isinf(value)


def finite_q(value):
    if isinstance(value, complex):
        return cmath.isfinite(value)
    if isinstance(value, float):
        return math.isfinite(value)
    _check_number(value, "finite?")
    return True


def zero_q(value):
    _check_number(value, "zero?")
    return value == 0


def positive_q(value):
    return value > 0


def negative_q(value):
    return value < 0


def odd_q(value):
    return value % 2 == 1


def even_q(value):
    return value % 2 == 0


def _contagion(result, values):
    if any(isinstance(value, float) for value in values):
        return float(result)
    return result


def max_(first, *rest):
    values = (first, *rest)
    return _contagion(max(values), values)


def min_(first, *rest):
    values = (first, *rest)
    return _contagion(min(values), values)


def abs_(value):
    return abs(value)


def _inexact_like(result, *operands):
    if any(isinstance(value, float) for value in operands):
        return float(result)
    return result


def _check_integer(value, who):
    if not integer_q(value):
        raise TypeError(f"{who}: not an integer: {value!r}")


def floor_quotient(n, m):
    _check_integer(n, "floor-quotient")
    _check_integer(m, "floor-quotient")
    return _inexact_like(int(n) // int(m), n, m)


def floor_remainder(n, m):
    _check_integer(n, "floor-remainder")
    _check_integer(m, "floor-remainder")
    return _inexact_like(int(n) % int(m), n, m)


def floor_slash(n, m):
    return control_runtime.values(floor_quotient(n, m), floor_remainder(n, m))


def truncate_quotient(n, m):
    _check_integer(n, "truncate-quotient")
    _check_integer(m, "truncate-quotient")
    n_int, m_int = int(n), int(m)
    quotient = abs(n_int) // abs(m_int)
    if (n_int < 0) != (m_int < 0):
        quotient = -quotient
    return _inexact_like(quotient, n, m)


def truncate_remainder(n, m):
    quotient = truncate_quotient(n, m)
    return _inexact_like(int(n) - int(m) * int(quotient), n, m)


def truncate_slash(n, m):
    return control_runtime.values(truncate_quotient(n, m), truncate_remainder(n, m))


def gcd(*args):
    for value in args:
        _check_integer(value, "gcd")
    return _inexact_like(math.gcd(*(int(value) for value in args)), *args)


def lcm(*args):
    for value in args:
        _check_integer(value, "lcm")
    return _inexact_like(abs(math.lcm(*(int(value) for value in args))), *args)


def numerator(value):
    if isinstance(value, float):
        return float(Fraction(value).numerator)
    return Fraction(value).numerator


def denominator(value):
    if isinstance(value, float):
        return float(Fraction(value).denominator)
    return Fraction(value).denominator


def _rounder(function):
    def round_number(value):
        if isinstance(value, float):
            if not math.isfinite(value):
                return value
            return float(function(value))
        return function(value)

    return round_number


floor = _rounder(math.floor)
ceiling = _rounder(math.ceil)
truncate = _rounder(math.trunc)
round_ = _rounder(round)


def inexact(value):
    _check_number(value, "inexact")
    if isinstance(value, complex):
        return value
    return float(value)


def square(value):
    return mul(value, value)


def _exact_sqrt(value):
    if value.__class__ is int:
        root = math.isqrt(value)
        return root if root * root == value else None
    numerator_root = _exact_sqrt(value.numerator)
    denominator_root = _exact_sqrt(value.denominator)
    if numerator_root is None or denominator_root is None:
        return None
    return Fraction(numerator_root, denominator_root)


def sqrt(value):
    if isinstance(value, _EXACT_TYPES) and value >= 0:
        root = _exact_sqrt(value)
        if root is not None:
            return root
    if isinstance(value, complex) or value < 0:
        result = cmath.sqrt(value)
        if isinstance(value, _EXACT_TYPES) and result.real == 0:
            root = _exact_sqrt(-value)
            if root is not None:
                return complex(0, root)
        return result
    return math.sqrt(value)


def exact_integer_sqrt(value):
    if value.__class__ is not int or value < 0:
        raise ValueError(
            f"exact-integer-sqrt: not a non-negative exact integer: {value!r}"
        )
    root = math.isqrt(value)
    return control_runtime.values(root, value - root * root)


def expt(base, exponent):
    if exponent.__class__ is int and isinstance(base, _EXACT_TYPES):
        if exponent < 0 and base == 0:
            raise ZeroDivisionError("expt: zero to a negative power")
        return _normalize(Fraction(base) ** exponent)
    result = base**exponent
    return _normalize(result) if result.__class__ is Fraction else result


def exp(value):
    return cmath.exp(value) if isinstance(value, complex) else math.exp(value)


def _real_or_complex(real_function, complex_function):
    def function(value):
        if isinstance(value, complex):
            return complex_function(value)
        try:
            return real_function(value)
        except ValueError:
            return complex_function(value)

    function.__name__ = real_function.__name__
    return function


sin = _real_or_complex(math.sin, cmath.sin)
cos = _real_or_complex(math.cos, cmath.cos)
tan = _real_or_complex(math.tan, cmath.tan)
asin = _real_or_complex(math.asin, cmath.asin)
acos = _real_or_complex(math.acos, cmath.acos)


def atan(y, x=None):
    if x is None:
        return cmath.atan(y) if isinstance(y, complex) else math.atan(y)
    return math.atan2(y, x)


def log(value, base=None):
    if base is None:
        if isinstance(value, complex) or value < 0:
            return cmath.log(value)
        return math.log(value)
    return log(value) / log(base)


_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _int_to_string(value, radix):
    if radix == 10:
        return str(value)
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    value = abs(value)
    digits = []
    while value:
        value, digit = divmod(value, radix)
        digits.append(_DIGITS[digit])
    return sign + "".join(reversed(digits))


def number_to_string(value, radix=10):
    _check_number(value, "number->string")
    if value.__class__ is int:
        return _int_to_string(value, radix)
    if isinstance(value, Fraction):
        return (
            f"{_int_to_string(value.numerator, radix)}"
            f"/{_int_to_string(value.denominator, radix)}"
        )
    if radix != 10:
        raise ValueError("number->string: inexact numbers only support radix 10")
    if isinstance(value, float):
        if math.isnan(value):
            return "+nan.0"
        if math.isinf(value):
            return "+inf.0" if value > 0 else "-inf.0"
        return repr(value)
    return repr(value)


# Lists


def list_q(value):
    seen = set()
    while value.__class__ is Pair:
        if id(value) in seen:
            return False
        seen.add(id(value))
        value = value.cdr
    return value == ()


def make_list(count, fill=False):
    return py_to_list([fill] * count)


def list_tail(values, k):
    for _ in range(k):
        values = values.cdr
    return values


def list_set_bang(values, k, value):
    list_tail(values, k).car = value


def list_copy(values):
    if values.__class__ is not Pair:
        return values
    items = []
    while values.__class__ is Pair:
        items.append(values.car)
        values = values.cdr
    result = values
    for item in reversed(items):
        result = Pair(item, result)
    return result


def _member(value, values, same):
    while values.__class__ is Pair:
        if same(value, values.car):
            return values
        values = values.cdr
    return False


def memq(value, values):
    return _member(value, values, eq_q)


def memv(value, values):
    return _member(value, values, eqv_q)


def member(value, values, same=None):
    return _member(value, values, equal_q if same is None else same)


def _assoc(key, alist, same):
    while alist.__class__ is Pair:
        entry = alist.car
        if same(key, entry.car):
            return entry
        alist = alist.cdr
    return False


def assq(key, alist):
    return _assoc(key, alist, eq_q)


def assv(key, alist):
    return _assoc(key, alist, eqv_q)


def assoc(key, alist, same=None):
    return _assoc(key, alist, equal_q if same is None else same)


def _cars(lists):
    for values in lists:
        if values.__class__ is not Pair:
            return None
    return [values.car for values in lists]


def map_(procedure, values, *more):
    results = []
    if not more:
        while values.__class__ is Pair:
            results.append(procedure(values.car))
            values = values.cdr
        return py_to_list(results)
    lists = [values, *more]
    while (cars := _cars(lists)) is not None:
        results.append(procedure(*cars))
        lists = [values.cdr for values in lists]
    return py_to_list(results)


def for_each(procedure, values, *more):
    if not more:
        while values.__class__ is Pair:
            procedure(values.car)
            values = values.cdr
        return None
    lists = [values, *more]
    while (cars := _cars(lists)) is not None:
        procedure(*cars)
        lists = [values.cdr for values in lists]
    return None


def vector_map(procedure, vector, *more):
    return [procedure(*items) for items in zip(vector, *more)]


def vector_for_each(procedure, vector, *more):
    for items in zip(vector, *more):
        procedure(*items)


def case_match_q(key, labels):
    return any(eqv_q(key, label) for label in labels)

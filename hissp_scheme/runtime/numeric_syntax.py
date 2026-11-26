"""Scheme number syntax, shared by `string->number` and the reader."""

from __future__ import annotations

import math
import re
from fractions import Fraction

_EXACT_TYPES = (int, Fraction)
_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


class Rational(Fraction):
    """Exact non-integer rational.

    Arithmetic on a `Rational` returns an `int` when the result is whole, so
    exact integers are always `int`. That lets compiled code use Python's own
    operators (see `hissp_scheme.macro.primitives`) without normalizing
    results afterward.
    """

    __slots__ = ()


def _normalizing(method):
    def operation(self, *args):
        result = method(self, *args)
        if isinstance(result, Fraction):
            if result.denominator == 1:
                return result.numerator
            if result.__class__ is not Rational:
                return Rational._from_coprime_ints(result.numerator, result.denominator)
        return result

    operation.__name__ = method.__name__
    return operation


for _name in (
    "__add__", "__radd__", "__sub__", "__rsub__", "__mul__", "__rmul__",
    "__truediv__", "__rtruediv__", "__mod__", "__rmod__", "__pow__", "__rpow__",
    "__neg__", "__pos__", "__abs__",
):
    setattr(Rational, _name, _normalizing(getattr(Fraction, _name)))
del _name


def _normalize(value):
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return value.numerator
        if value.__class__ is not Rational:
            return Rational._from_coprime_ints(value.numerator, value.denominator)
    return value


def exact(value):
    if isinstance(value, _EXACT_TYPES) and value.__class__ is not bool:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"exact: no exact representation of {value!r}")
        return _normalize(Fraction(value))
    raise TypeError(f"exact: not a real number: {value!r}")


_RADIX_PREFIXES = {"b": 2, "o": 8, "d": 10, "x": 16}
_SPECIAL_FLOATS = {
    "+inf.0": math.inf,
    "-inf.0": -math.inf,
    "+nan.0": math.nan,
    "-nan.0": math.nan,
}
_DECIMAL = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?\Z")


def _parse_real(text, radix):
    if text in _SPECIAL_FLOATS:
        return _SPECIAL_FLOATS[text]
    if "/" in text:
        numerator_text, _, denominator_text = text.partition("/")
        numerator_value = _parse_integer(numerator_text, radix)
        denominator_value = _parse_integer(denominator_text, radix)
        if (
            numerator_value is None
            or denominator_value is None
            or denominator_text[:1] in "+-"
            or denominator_value == 0
        ):
            return None
        return _normalize(Fraction(numerator_value, denominator_value))
    integer = _parse_integer(text, radix)
    if integer is not None:
        return integer
    if radix == 10 and _DECIMAL.match(text):
        return float(text)
    return None


def _parse_integer(text, radix):
    body = text[1:] if text[:1] in "+-" else text
    if not body or any(char not in _DIGITS[:radix] for char in body):
        return None
    return int(text, radix)


def string_to_number(text, radix=10):
    text = text.lower()
    exactness = None
    while len(text) >= 2 and text[0] == "#":
        prefix = text[1]
        if prefix in _RADIX_PREFIXES:
            radix = _RADIX_PREFIXES[prefix]
        elif prefix in "ei" and exactness is None:
            exactness = prefix
        else:
            return False
        text = text[2:]
    value = _parse_real(text, radix)
    if value is None:
        return False
    if exactness == "e":
        return exact(value)
    if exactness == "i":
        return float(value)
    return value


def number_literal(token):
    """Number for a reader token that Hissp would read as a symbol, or None.

    Hissp already reads Python-style numbers. This covers the Scheme-only
    spellings: rationals (`1/2`), `+inf.0`/`-inf.0`/`+nan.0`, and `#x`/`#b`/
    `#o`/`#d`/`#e`/`#i` prefixes.
    """

    if not token or token[0] not in "+-.#0123456789":
        return None
    lowered = token.lower()
    if not ("/" in lowered or lowered.endswith(("inf.0", "nan.0")) or lowered[0] == "#"):
        return None
    value = string_to_number(token)
    return None if value is False else value

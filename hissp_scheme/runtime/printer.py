"""R7RS external representations for `write`, `display`, and REPL output."""

from __future__ import annotations

import math
from fractions import Fraction

from hissp_scheme.runtime.symbols import Symbol

_STRING_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\t": "\\t",
    "\r": "\\r",
    "\a": "\\a",
    "\b": "\\b",
    "\0": "\\x0;",
}


def _write_string_literal(value):
    return '"' + "".join(_STRING_ESCAPES.get(char, char) for char in value) + '"'


def _number(value):
    if isinstance(value, Fraction):
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, float):
        if math.isnan(value):
            return "+nan.0"
        if math.isinf(value):
            return "+inf.0" if value > 0 else "-inf.0"
    return repr(value)


def _is_pair(value):
    return type(value).__name__ == "Pair" and hasattr(value, "car")


def _render(value, display, seen):
    if value is True:
        return "#t"
    if value is False:
        return "#f"
    if isinstance(value, Symbol):
        return value.name
    if type(value) is str:
        return value if display else _write_string_literal(value)
    if isinstance(value, (int, float, Fraction)):
        return _number(value)
    if value == ():
        return "()"
    if _is_pair(value):
        return _render_pair(value, display, seen)
    if type(value) is bytearray:
        return "#u8(" + " ".join(str(byte) for byte in value) + ")"
    if type(value) is list:
        if id(value) in seen:
            return "#(...)"
        seen.add(id(value))
        try:
            return "#(" + " ".join(_render(item, display, seen) for item in value) + ")"
        finally:
            seen.discard(id(value))
    return repr(value)


def _render_pair(value, display, seen):
    parts = []
    visited = set()
    while _is_pair(value):
        if id(value) in visited or id(value) in seen:
            parts.append("...")
            return "(" + " ".join(parts) + ")"
        visited.add(id(value))
        seen.add(id(value))
        parts.append(_render(value.car, display, seen))
        value = value.cdr
    for pair_id in visited:
        seen.discard(pair_id)
    if value == ():
        return "(" + " ".join(parts) + ")"
    return "(" + " ".join(parts) + " . " + _render(value, display, seen) + ")"


def write_string(value):
    """Return the `write` representation of `value`."""

    return _render(value, False, set())


def display_string(value):
    """Return the `display` representation of `value`."""

    return _render(value, True, set())

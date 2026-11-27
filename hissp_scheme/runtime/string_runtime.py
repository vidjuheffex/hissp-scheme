"""Strings and characters for `(scheme base)` and `(scheme char)`.

Strings are Python `str`, which is immutable, so the mutating procedures
(`string-set!`, `string-copy!`, `string-fill!`) raise `TypeError`. A character
is a one-character `str`. Symbols are a `str` subclass (see `symbols`), so
`string?` checks the exact type.
"""

from __future__ import annotations

from scheme_pairs import Pair, py_to_list


def string_q(value):
    return value.__class__ is str


def char_q(value):
    return value.__class__ is str and len(value) == 1


def _check_string(value, who):
    if value.__class__ is not str:
        raise TypeError(f"{who} expected a string, got {value!r}")
    return value


def _check_char(value, who):
    if not char_q(value):
        raise TypeError(f"{who} expected a character, got {value!r}")
    return value


def _immutable(who):
    raise TypeError(f"{who} cannot mutate Python-backed immutable strings")


def _py_list(values, who):
    items = []
    while values.__class__ is Pair:
        items.append(values.car)
        values = values.cdr
    if values != ():
        raise TypeError(f"{who} expected a proper list")
    return items


# Strings


def make_string(count, char="\0"):
    return _check_char(char, "make-string") * count


def string(*chars):
    return "".join(_check_char(char, "string") for char in chars)


def string_length(value):
    return len(_check_string(value, "string-length"))


def string_ref(value, index):
    return _check_string(value, "string-ref")[index]


def string_set_bang(value, index, char):
    _immutable("string-set!")


def string_copy_bang(to, at, source, start=0, end=None):
    _immutable("string-copy!")


def string_fill_bang(value, fill, start=0, end=None):
    _immutable("string-fill!")


def substring(value, start, end):
    return _check_string(value, "substring")[start:end]


def string_copy(value, start=0, end=None):
    return _check_string(value, "string-copy")[start:end]


def string_append(*strings):
    return "".join(_check_string(value, "string-append") for value in strings)


def string_to_list(value, start=0, end=None):
    return py_to_list(list(_check_string(value, "string->list")[start:end]))


def list_to_string(chars):
    return "".join(_check_char(char, "list->string") for char in _py_list(chars, "list->string"))


def string_to_vector(value, start=0, end=None):
    return list(_check_string(value, "string->vector")[start:end])


def vector_to_string(vector, start=0, end=None):
    return "".join(_check_char(char, "vector->string") for char in vector[start:end])


def string_map(procedure, value, *more):
    strings = [_check_string(item, "string-map") for item in (value, *more)]
    return "".join(
        _check_char(procedure(*chars), "string-map") for chars in zip(*strings)
    )


def string_for_each(procedure, value, *more):
    strings = [_check_string(item, "string-for-each") for item in (value, *more)]
    for chars in zip(*strings):
        procedure(*chars)


def _comparison(name, compare, key=None):
    def compare_strings(first, second, *rest):
        values = [_check_string(item, name) for item in (first, second, *rest)]
        if key is not None:
            values = [key(item) for item in values]
        return all(compare(a, b) for a, b in zip(values, values[1:]))

    compare_strings.__name__ = name
    return compare_strings


def _char_comparison(name, compare, key=None):
    def compare_chars(first, second, *rest):
        values = [_check_char(item, name) for item in (first, second, *rest)]
        if key is not None:
            values = [key(item) for item in values]
        return all(compare(a, b) for a, b in zip(values, values[1:]))

    compare_chars.__name__ = name
    return compare_chars


def _eq(a, b):
    return a == b


def _lt(a, b):
    return a < b


def _gt(a, b):
    return a > b


def _le(a, b):
    return a <= b


def _ge(a, b):
    return a >= b


string_eq_q = _comparison("string=?", _eq)
string_lt_q = _comparison("string<?", _lt)
string_gt_q = _comparison("string>?", _gt)
string_le_q = _comparison("string<=?", _le)
string_ge_q = _comparison("string>=?", _ge)

# Characters


def char_to_integer(char):
    return ord(_check_char(char, "char->integer"))


def integer_to_char(code):
    return chr(code)


char_eq_q = _char_comparison("char=?", _eq)
char_lt_q = _char_comparison("char<?", _lt)
char_gt_q = _char_comparison("char>?", _gt)
char_le_q = _char_comparison("char<=?", _le)
char_ge_q = _char_comparison("char>=?", _ge)

# `(scheme char)`


def char_alphabetic_q(char):
    return _check_char(char, "char-alphabetic?").isalpha()


def char_numeric_q(char):
    return _check_char(char, "char-numeric?").isdecimal()


def char_whitespace_q(char):
    return _check_char(char, "char-whitespace?").isspace()


def char_upper_case_q(char):
    return _check_char(char, "char-upper-case?").isupper()


def char_lower_case_q(char):
    return _check_char(char, "char-lower-case?").islower()


def digit_value(char):
    char = _check_char(char, "digit-value")
    return int(char) if char.isdecimal() else False


def _single_char(result, original):
    # Case mappings like "ß" -> "SS" aren't single characters; R7RS char
    # procedures return the character unchanged then.
    return result if len(result) == 1 else original


def char_upcase(char):
    return _single_char(_check_char(char, "char-upcase").upper(), char)


def char_downcase(char):
    return _single_char(_check_char(char, "char-downcase").lower(), char)


def char_foldcase(char):
    return _single_char(_check_char(char, "char-foldcase").casefold(), char)


def string_upcase(value):
    return _check_string(value, "string-upcase").upper()


def string_downcase(value):
    return _check_string(value, "string-downcase").lower()


def string_foldcase(value):
    return _check_string(value, "string-foldcase").casefold()


char_ci_eq_q = _char_comparison("char-ci=?", _eq, str.casefold)
char_ci_lt_q = _char_comparison("char-ci<?", _lt, str.casefold)
char_ci_gt_q = _char_comparison("char-ci>?", _gt, str.casefold)
char_ci_le_q = _char_comparison("char-ci<=?", _le, str.casefold)
char_ci_ge_q = _char_comparison("char-ci>=?", _ge, str.casefold)

string_ci_eq_q = _comparison("string-ci=?", _eq, str.casefold)
string_ci_lt_q = _comparison("string-ci<?", _lt, str.casefold)
string_ci_gt_q = _comparison("string-ci>?", _gt, str.casefold)
string_ci_le_q = _comparison("string-ci<=?", _le, str.casefold)
string_ci_ge_q = _comparison("string-ci>=?", _ge, str.casefold)

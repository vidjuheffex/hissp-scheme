"""Scheme symbols.

A `Symbol` is an interned `str` subclass whose value is the munged Hissp
spelling (`'list->vector` is `Symbol("listQzH_QzGT_vector")`), without the
keyword prefix that Scheme source adds to Python keywords. Being a `str`
keeps symbols usable as Hissp forms, so Scheme-written macro helpers can still
build and compare code with quoted symbols. Scheme-level predicates and
equivalence (`symbol?`, `string?`, `eqv?`, `equal?`) and the printer treat
symbols and strings as distinct types.
"""

from __future__ import annotations

import threading

import hissp

from hissp_scheme import names

_table: dict[str, "Symbol"] = {}
_lock = threading.Lock()


class Symbol(str):
    __slots__ = ()

    @property
    def name(self):
        """Scheme source spelling of this symbol."""

        return hissp.demunge(str(self))

    def __repr__(self):
        return self.name

    def __reduce__(self):
        return (intern, (str(self),))


def intern(munged_name):
    """Return the unique symbol for a munged Hissp spelling."""

    symbol = _table.get(munged_name)
    if symbol is None:
        with _lock:
            symbol = _table.setdefault(munged_name, Symbol(munged_name))
    return symbol


def symbol_q(obj):
    return isinstance(obj, Symbol)


def symbol_to_string(symbol):
    if not isinstance(symbol, Symbol):
        raise TypeError(f"symbol->string expected a symbol, got {symbol!r}")
    return symbol.name


def string_to_symbol(string):
    if not isinstance(string, str):
        raise TypeError(f"string->symbol expected a string, got {string!r}")
    return intern(hissp.munge(string))


def symbol_eq_q(first, *rest):
    for symbol in (first, *rest):
        if not isinstance(symbol, Symbol):
            raise TypeError(f"symbol=? expected symbols, got {symbol!r}")
    return all(symbol is first for symbol in rest)


def from_form(form):
    """Symbol for a munged reader symbol, undoing Scheme-only reader renames."""

    form = names.restore_keyword(form)
    if form == "schemeQzH_lambda":
        form = "lambda"
    return intern(form)

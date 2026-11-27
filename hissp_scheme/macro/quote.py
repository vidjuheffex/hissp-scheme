"""Scheme `quote`.

In Scheme source the reader turns `'datum` into `(QUOTE datum)`, a macro form
rather than Hissp's `quote` special form. The macro builds the runtime value
when the form is compiled, which happens after `syntax-rules` has substituted
pattern variables into templates such as `'x`.

Quoted symbols become interned `Symbol` objects, lists become `Pair` chains,
string literals stay strings, and `#t`/`#f` become booleans.
"""

from __future__ import annotations

from types import SimpleNamespace

from hissp_scheme.runtime.symbols import from_form

QUOTE = "hissp_scheme.macro.quote.._macro_.quote"

_BOOLEANS = {"QzHASH_t": True, "QzHASH_f": False}


def is_string_literal_form(value):
    return (
        isinstance(value, str)
        and len(value) >= 2
        and value[0] == "("
        and value[1] in "'\""
    )


def list_form(items, tail=()):
    """Form building a list of the `items` forms ending in `tail`."""

    if not items:
        return tail
    if tail == ():
        return ("scheme_pairs..scheme_list", *items)
    return ("scheme_pairs..list_star", *items, tail)


def symbol_form(symbol):
    """Form evaluating to the interned symbol for a reader symbol."""

    return (
        "hissp_scheme.runtime.symbols..intern",
        f"({str(from_form(symbol))!r})",
    )


def datum_form(datum):
    """Form evaluating to the Scheme value of reader data `datum`."""

    if isinstance(datum, tuple):
        if not datum:
            return ()
        if len(datum) == 2 and datum[0] == QUOTE:
            datum = ("quote", datum[1])
        if len(datum) >= 3 and datum[-2] == ".":
            items, tail = datum[:-2], datum_form(datum[-1])
        elif "." in datum:
            raise SyntaxError("dot may only appear before the final tail in quoted lists")
        else:
            items, tail = datum, ()
        return list_form(tuple(datum_form(item) for item in items), tail)

    if datum is Ellipsis:
        return symbol_form("...")
    if isinstance(datum, str):
        if is_string_literal_form(datum):
            return datum
        if datum in _BOOLEANS:
            return _BOOLEANS[datum]
        return symbol_form(datum)
    return datum


def quote(datum):
    return datum_form(datum)


_macro_ = SimpleNamespace(quote=quote)

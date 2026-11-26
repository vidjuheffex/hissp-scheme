"""Scheme identifier spelling.

Hissp munges Scheme names like `list->vector` into Python identifiers, but it
leaves Python keywords alone, and `return(x)` isn't valid Python. Scheme source
renames keyword identifiers with a prefix instead. A few keywords stay as they
are because they name Scheme syntax (`if`, `lambda`, ...) or Python constants.
"""

from __future__ import annotations

import keyword

import hissp

KEYWORD_PREFIX = "_Qzkw_"

# Keywords that stay unrenamed: macro names, `cond`/`case` `else`, and Python
# constants used in library code.
UNRENAMED_KEYWORDS = frozenset(
    {"if", "lambda", "import", "raise", "and", "or", "else", "True", "False", "None"}
)


def rename_keyword(symbol: str) -> str:
    """Rename an already-munged symbol if it's a Python keyword."""

    if keyword.iskeyword(symbol) and symbol not in UNRENAMED_KEYWORDS:
        return KEYWORD_PREFIX + symbol
    return symbol


def restore_keyword(symbol: str) -> str:
    if symbol.startswith(KEYWORD_PREFIX):
        return symbol[len(KEYWORD_PREFIX) :]
    return symbol


def munge(name: str) -> str:
    """Scheme source spelling to the Python identifier used for the binding."""

    return rename_keyword(hissp.munge(name))


def demunge(symbol: str) -> str:
    """Python identifier for a Scheme binding back to its source spelling."""

    return hissp.demunge(restore_keyword(symbol))

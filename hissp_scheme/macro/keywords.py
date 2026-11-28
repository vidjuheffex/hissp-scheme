"""Transformers for SRFI-177 keyword arguments (`(srfi 177)`).

They build Hissp's keyword-argument call syntax and keyword-only formals,
which Scheme has no spelling for.
"""

from __future__ import annotations

from hissp_scheme import names

_HISSP = "hissp.macros.._macro_."


def _python_name(symbol):
    if not isinstance(symbol, str):
        raise SyntaxError("keyword names must be symbols")
    return names.demunge(symbol).replace("-", "_")


def _keyword_mapping_form(spec):
    if isinstance(spec, tuple) and len(spec) == 2 and spec[0] == "QzSTAR_QzSTAR_":
        return spec[1]
    if not isinstance(spec, tuple):
        raise SyntaxError(
            "call/kw keyword arguments must be a final list: "
            "(name value ...) or (** mapping)"
        )
    if len(spec) % 2:
        raise SyntaxError("call/kw keyword argument list must contain name/value pairs")
    items = []
    seen = set()
    for symbol, value in zip(spec[::2], spec[1::2]):
        name = _python_name(symbol)
        if name in seen:
            raise SyntaxError(f"duplicate call/kw keyword: {names.demunge(symbol)}")
        seen.add(name)
        items += [f"({name!r})", value]
    return (f"{_HISSP}QzPCENT_", *items)


def _keyword_formals(formals):
    if not isinstance(formals, tuple):
        raise SyntaxError("lambda/kw formals must be a list")
    positional, keywords = formals, ()
    if formals and isinstance(formals[-1], tuple):
        positional, keywords = formals[:-1], formals[-1]
    for formal in positional + keywords:
        if not isinstance(formal, str):
            raise SyntaxError("lambda/kw formals and keywords must be symbols")
    if not keywords:
        return positional
    return (*positional, "*", *(f"{name}=False" for name in keywords))


def call_kw_form(function, *args):
    # (call/kw dumps payload (indent 2 sort-keys #t))
    # (call/kw dumps payload (** options))
    if not args:
        raise SyntaxError("call/kw requires a final keyword argument list")
    *positional, keywords = args
    return (function, *positional, ":", ":**", _keyword_mapping_form(keywords))


def lambda_kw_form(formals, *body):
    return (f"{_HISSP}fun", "lambdaQzSOL_kw", _keyword_formals(formals), *body)


def define_kw_form(head, *body):
    if not (isinstance(head, tuple) and head):
        raise SyntaxError("define/kw requires a function head")
    return (f"{_HISSP}defun", head[0], _keyword_formals(head[1:]), *body)

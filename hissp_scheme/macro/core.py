"""The core syntax of `(scheme base)`.

`scheme_base.sld` imports these with `(import hissp_scheme.macro.core)` and
re-exports them. They're Python because they build Hissp code directly, and
because the tail-call marker in `tail` recognizes them by identity.

A top-level `define` of a name that's bound to a macro removes the macro from
that module, so the definition shadows it as in R7RS. Locals that share a
macro's name are handled by `syntax_rules.assigned_locals`.
"""

from __future__ import annotations

from types import SimpleNamespace

from hissp.compiler import ENV

from hissp_scheme.macro import syntax_rules
from hissp_scheme.macro.quote import QUOTE
from hissp_scheme.macro.tail import (
    do_form,
    let_form,
    let_star_form,
    letrec_form,
    named_let_form,
    procedure_form,
)

_HISSP = "hissp.macros.._macro_."

# Imported values: none. Imported macros: Scheme spelling -> `_macro_` name.
__scheme_exports__ = {}
__scheme_macros__ = {
    "define": "define",
    "scheme-lambda": "schemeQzH_lambda",
    "set!": "setQzBANG_",
    "begin": "begin",
    "let": "let",
    "let*": "letQzSTAR_",
    "letrec": "letrec",
    "letrec*": "letrecQzSTAR_",
    "do": "do",
    "define-syntax": "defineQzH_syntax",
    "let-syntax": "letQzH_syntax",
    "letrec-syntax": "letrecQzH_syntax",
    "case": "case",
}


def forget_macro(env, name):
    """Remove the macro `name` from the module `env`, if it has one."""

    namespace = env.get("_macro_")
    if namespace is not None and name in vars(namespace):
        delattr(namespace, name)
        return True
    return False


def define(head, *body):
    if isinstance(head, tuple):
        if not head:
            raise SyntaxError("function-style define requires a name")
        name = head[0]
        form = (f"{_HISSP}define", name, procedure_form(name, head[1:], body))
    else:
        if len(body) != 1:
            raise SyntaxError("value-style define requires exactly one value")
        name = head
        form = (f"{_HISSP}define", name, body[0])
    # Forget the macro now, so the rest of this module compiles calls to the
    # new definition, and again when the module runs, so a module importing
    # this one's exports gets the procedure.
    if not forget_macro(ENV.get(), name):
        return form
    return (
        f"{_HISSP}progn",
        form,
        ("hissp_scheme.macro.core..forget_macro", ("builtins..globals",), ("quote", name)),
    )


def scheme_lambda(formals, *body):
    return procedure_form(None, formals, body)


def set_bang(target, value):
    # Locals that are `set!` somewhere in their scope live in cells (see
    # `box_assigned_locals`), and `set!` forms written in that scope are
    # rewritten before this macro runs. A macro can still hand this form an
    # already-rewritten cell reference. Everything else is a global.
    cell = syntax_rules.cell_name_from_ref_form(target)
    if cell:
        return ("hissp_scheme.macro.syntax_rules..cell_set", cell, value)
    return (f"{_HISSP}setQzAT_", target, value)


def begin(*body):
    # Definitions in a top-level `begin` are globals. (A `begin` directly in a
    # body is spliced by the body expander.)
    expanded = syntax_rules.expand_sequence(
        body, syntax_rules.syntax_rules_stable_identifiers()
    )
    return (f"{_HISSP}progn", *expanded)


def let(bindings, *body):
    if isinstance(bindings, str):
        if not body:
            raise SyntaxError("named let requires bindings")
        return named_let_form(bindings, body[0], body[1:])
    return let_form(bindings, body)


def let_star(bindings, *body):
    return let_star_form(bindings, body)


def letrec(bindings, *body):
    return letrec_form(bindings, body, "letrec")


def letrec_star(bindings, *body):
    return letrec_form(bindings, body, "letrec*")


def do(specs, exit_clause, *commands):
    return do_form(specs, exit_clause, commands)


def define_syntax(name, transformer):
    if not (
        isinstance(transformer, tuple)
        and transformer
        and transformer[0] in ("syntaxQzH_rules", "syntaxQzH_case")
    ):
        raise SyntaxError(
            "define-syntax supports syntax-rules and syntax-case transformers"
        )
    return (
        "builtins..setattr",
        "_macro_",
        ("quote", name),
        (
            "hissp_scheme.macro.syntax_rules..make_transformer_from_form",
            ("quote", name),
            ("quote", transformer),
            ("hissp_scheme.macro.syntax_rules..syntax_rules_stable_identifiers",),
            ("builtins..globals",),
        ),
    )


def let_syntax(bindings, *body):
    return syntax_rules.expand_let_syntax(
        bindings, body, syntax_rules.syntax_rules_stable_identifiers()
    )


def letrec_syntax(bindings, *body):
    return syntax_rules.expand_letrec_syntax(
        bindings, body, syntax_rules.syntax_rules_stable_identifiers()
    )


def case(key, *clauses):
    # Labels are datums, compared with `eqv?`. The key is evaluated once.
    key_name = f"_Qzcase_key_{id(clauses)}"
    return ("let", ((key_name, key),), _case_dispatch(key_name, clauses))


def _case_dispatch(key_name, clauses):
    if not clauses:
        return False
    clause, *remaining = clauses
    if not (isinstance(clause, tuple) and clause):
        raise SyntaxError("case clauses must be non-empty lists")
    labels, *body = clause
    if labels == "else":
        return ("begin", *body)
    if not isinstance(labels, tuple):
        raise SyntaxError("case datum labels must be a list")
    return (
        "if",
        (
            "hissp_scheme.runtime.base_runtime..case_match_q",
            key_name,
            (f"{_HISSP}QzAT_", *((QUOTE, label) for label in labels)),
        ),
        ("begin", *body),
        _case_dispatch(key_name, remaining),
    )


def _named(function, name):
    function.__name__ = name
    function.__qualname__ = f"_macro_.{name}"
    return function


_macro_ = SimpleNamespace(
    **{
        name: _named(function, name)
        for name, function in {
            "define": define,
            "schemeQzH_lambda": scheme_lambda,
            "setQzBANG_": set_bang,
            "begin": begin,
            "let": let,
            "letQzSTAR_": let_star,
            "letrec": letrec,
            "letrecQzSTAR_": letrec_star,
            "do": do,
            "defineQzH_syntax": define_syntax,
            "letQzH_syntax": let_syntax,
            "letrecQzH_syntax": letrec_syntax,
            "case": case,
        }.items()
    }
)

"""Tail-position marking and procedure construction for `(scheme base)`.

`procedure_form` builds the Hissp form for a Scheme procedure: the compiled
lambda body is wrapped by `control_runtime.make_procedure`, and the last body
form is wrapped in the `tail` macro defined here.

`tail` runs lazily, when Hissp compiles that form, so it sees the macros that
are in scope at that point. It pushes itself through forms whose own tail
position is still the procedure's tail position (`if`, `begin`, `let`, and any
Scheme macro after one expansion step), and rewrites a plain application
`(f arg ...)` into `(<TailCall> f arg ...)`. Everything else is left alone.
"""

from __future__ import annotations

import itertools
import sys
from contextvars import ContextVar
from types import SimpleNamespace

from hissp.compiler import Compiler, ENV, macroexpand1

from hissp_scheme.runtime import control_runtime
from hissp_scheme.macro.inline import compile_subform, fresh_let_name, sequence_form
from hissp_scheme.macro.syntax_rules import (
    _formal_names,
    assigned_locals,
    box_assigned_locals,
    expand_body_definitions,
    rename_locals,
    syntax_rules_stable_identifiers,
)
from hissp_scheme.runtime.scheme_bootstrap_runtime import (
    IMPORTED_VALUES,
    scheme_body,
    scheme_formals,
)

TAIL = "hissp_scheme.macro.tail.._macro_.tail"

# Bound once around each procedure so tail calls use a closure variable instead
# of a module lookup through `__import__` on every call.
TAIL_CALL = control_runtime.TAIL_CALL_NAME

_gensym_counter = itertools.count(1)

_IF = {
    ("scheme_bootstrap", "_macro_.if"),
}
_IF_ELSE = {
    ("hissp.macros", "_macro_.ifQzH_else"),
}
_CORE = "hissp_scheme.macro.core"
_SEQUENCE = {
    (_CORE, "_macro_.begin"),
    ("scheme_bootstrap", "_macro_.begin"),
    ("hissp.macros", "_macro_.progn"),
}
_LET = {
    (_CORE, "_macro_.let"),
    ("scheme_bootstrap", "_macro_.let"),
    ("hissp.macros", "_macro_.let"),
}
# Scheme-level macros whose expansion is still Scheme code with the same tail
# position. Anything not listed is treated as opaque.
_EXPAND = {
    (_CORE, f"_macro_.{name}")
    for name in (
        "letQzSTAR_",
        "letrec",
        "letrecQzSTAR_",
        "do",
        "letQzH_syntax",
        "letrecQzH_syntax",
        "case",
    )
}
_TRANSFORMER_MODULE = "hissp_scheme.macro.syntax_rules"


def _macro_key(macro):
    return (getattr(macro, "__module__", None), getattr(macro, "__qualname__", None))


def _is_control(item):
    return isinstance(item, str) and item.startswith(":")


def _lookup_macro(head):
    try:
        return Compiler.get_macro(head, ENV.get())
    except Exception:
        return None


# Procedure parameters in scope while a procedure body compiles. Parameters
# are the only locals that keep their source names: `let` variables are
# renamed, and internal definitions and `set!` targets live in cells.
_LOCALS: ContextVar[frozenset] = ContextVar("scheme_locals", default=frozenset())

_MISSING = object()


def _global_value(head):
    """Compile-time value of a global or qualified name, or `_MISSING`."""

    if ".." in head:
        module_name, _, attribute_path = head.partition("..")
        value = sys.modules.get(module_name, _MISSING)
        for attribute in attribute_path.split("."):
            if value is _MISSING:
                break
            value = getattr(value, attribute, _MISSING)
        return value
    if not head.isidentifier() or head in _LOCALS.get():
        return _MISSING
    # Only trust a bare name bound by a Scheme `import`. Python's builtins
    # provide names like `filter` that a later Scheme definition may take over.
    env = ENV.get(None) or {}
    value = env.get(head, _MISSING)
    if (
        value is _MISSING
        or env.get(IMPORTED_VALUES, {}).get(head, _MISSING) is not value
    ):
        return _MISSING
    return value


def _calls_python_directly(head):
    # A call to a Python function (a builtin, a pairs primitive, a class)
    # can't continue a chain of Scheme tail calls, so it needn't go through
    # the trampoline. Unknown or local callees still get a proper tail call.
    value = _global_value(head)
    return (
        value is not _MISSING
        and callable(value)
        and not control_runtime.is_scheme_procedure(value)
    )


def mark_tail(form):
    """Return `form` rewritten for tail position inside a procedure body."""

    if not isinstance(form, tuple) or not form:
        return form

    head = form[0]
    if head in ("quote", "lambda"):
        return form

    if isinstance(head, str):
        if head.startswith(".") or head.startswith(":") or head.startswith("("):
            return form
        macro = _lookup_macro(head)
        if macro is not None:
            return _mark_macro_tail(form, macro)

    if any(_is_control(item) for item in form[1:]):
        return form
    if not isinstance(head, (str, tuple)):
        return form
    if isinstance(head, str) and _calls_python_directly(head):
        return form
    return (TAIL_CALL, *form)


def _wrap(form):
    return (TAIL, form)


def _mark_macro_tail(form, macro):
    key = _macro_key(macro)

    if key in _IF or key in _IF_ELSE:
        if len(form) != 4:
            return form
        return (form[0], form[1], _wrap(form[2]), _wrap(form[3]))

    if key in _SEQUENCE:
        if len(form) < 2:
            return form
        return (*form[:-1], _wrap(form[-1]))

    if key in _LET:
        if len(form) < 3:
            return form
        if key[0] == _CORE and isinstance(form[1], str):
            return mark_tail(macroexpand1(form))
        return (*form[:-1], _wrap(form[-1]))

    if key in _EXPAND or key[0] == _TRANSFORMER_MODULE:
        return mark_tail(macroexpand1(form))

    return form


def tail(form):
    return mark_tail(form)


def scope(formal_names, form):
    """Compile `form` with `formal_names` added to the parameters in scope."""

    token = _LOCALS.set(_LOCALS.get() | frozenset(formal_names))
    try:
        return compile_subform(form)
    finally:
        _LOCALS.reset(token)


SCOPE = "hissp_scheme.macro.tail.._macro_.scope"

_macro_ = SimpleNamespace(tail=tail, scope=scope)


# ---------------------------------------------------------------------------
# Procedure construction
# ---------------------------------------------------------------------------


def procedure_body(formals, body):
    """Expand a Scheme body into the Hissp body of a procedure's raw lambda."""

    expanded = expand_body_definitions(body, syntax_rules_stable_identifiers())
    boxed = box_assigned_locals(_formal_names(formals), expanded)
    if boxed:
        boxed = (*boxed[:-1], _wrap(boxed[-1]))
    return scheme_body(formals, boxed)


def procedure_form(name, formals, body):
    """Hissp form evaluating to a Scheme procedure.

    `name` is the munged Python name for `define`, or `None` for `lambda`.
    """

    raw = (
        "hissp.macros.._macro_.fun",
        name if name is not None else "lambda",
        scheme_formals(formals),
        *procedure_body(formals, body),
    )
    return (
        "hissp.macros.._macro_.let",
        (TAIL_CALL, "hissp_scheme.runtime.control_runtime..TailCall"),
        (
            "hissp_scheme.runtime.control_runtime..compiled_procedure",
            # A procedure's own name counts as local in its body, since the
            # global may still hold an imported value it's replacing.
            (SCOPE, tuple(sorted(_formal_names(formals) | {name} - {None})), raw),
        ),
    )


def let_form(bindings, body):
    """Hissp form for a plain (not named) Scheme `let`.

    Usually the result is an inline `:=` expression (see `inline`). Names that
    are `set!` stay on the Hissp `let` path with cells, since an assignment
    expression in a nested lambda would bind that lambda's variable instead.
    """

    _check_bindings(bindings, "let")
    names = [name for name, _ in bindings]
    expanded = expand_body_definitions(body, syntax_rules_stable_identifiers())
    if assigned_locals(names, expanded):
        return (
            "hissp.macros.._macro_.let",
            tuple(itertools.chain.from_iterable(bindings)),
            *box_assigned_locals(names, expanded),
        )
    renames = {name: fresh_let_name(name) for name in names}
    renamed = tuple(rename_locals(form, renames) for form in expanded)
    return sequence_form([(renames[name], value) for name, value in bindings], renamed)


# ---------------------------------------------------------------------------
# Derived binding forms
# ---------------------------------------------------------------------------
#
# Expansions use bare Scheme spellings (`let`, `define`, `schemeQzH_lambda`):
# the body rewriters in `syntax_rules` recognize binding forms by spelling.


def _check_bindings(bindings, form_name):
    if not isinstance(bindings, tuple):
        raise SyntaxError(f"{form_name} bindings must be a list")
    for binding in bindings:
        if not (
            isinstance(binding, tuple)
            and len(binding) == 2
            and isinstance(binding[0], str)
        ):
            raise SyntaxError(f"{form_name} bindings must be (name value) pairs")
    return bindings


def letrec_form(bindings, body, form_name="letrec"):
    # Internal defines already give letrec* semantics through cells, and
    # evaluating letrec inits left to right is a valid letrec order.
    _check_bindings(bindings, form_name)
    return (
        "let",
        (),
        *(("define", name, value) for name, value in bindings),
        *body,
    )


def named_let_form(tag, bindings, body):
    _check_bindings(bindings, "named let")
    names = tuple(name for name, _ in bindings)
    inits = tuple(value for _, value in bindings)
    return (
        ("letrec", ((tag, ("schemeQzH_lambda", names, *body)),), tag),
        *inits,
    )


def let_star_form(bindings, body):
    _check_bindings(bindings, "let*")
    if not bindings:
        return ("let", (), *body)
    form = ("let", (bindings[-1],), *body)
    for binding in reversed(bindings[:-1]):
        form = ("let", (binding,), form)
    return form


_CONTROL = "hissp_scheme.runtime.control_runtime.."


def guard_form(spec, *body):
    # (guard (var clause ...) body ...)
    if not (isinstance(spec, tuple) and spec and isinstance(spec[0], str)):
        raise SyntaxError("guard requires (variable clause ...) before its body")
    variable, *clauses = spec
    last = clauses[-1] if clauses else None
    if not (isinstance(last, tuple) and last and last[0] == "else"):
        clauses.append(("else", f"{_CONTROL}GUARD_NO_MATCH"))
    return (
        f"{_CONTROL}guard_",
        ("schemeQzH_lambda", (variable,), ("cond", *clauses)),
        ("schemeQzH_lambda", (), *body),
    )


def parameterize_form(bindings, *body):
    _check_bindings_shape(bindings, "parameterize")
    return (
        f"{_CONTROL}parameterize_",
        ("schemeQzH_lambda", (), *body),
        *((f"{_CONTROL}binding", parameter, value) for parameter, value in bindings),
    )


def raise_form(obj):
    return (f"{_CONTROL}raise_", obj)


def _check_bindings_shape(bindings, form_name):
    if not isinstance(bindings, tuple) or not all(
        isinstance(binding, tuple) and len(binding) == 2 for binding in bindings
    ):
        raise SyntaxError(f"{form_name} bindings must be (parameter value) pairs")


def do_form(specs, exit_clause, commands):
    if not isinstance(specs, tuple):
        raise SyntaxError("do variable specs must be a list")
    if not (isinstance(exit_clause, tuple) and exit_clause):
        raise SyntaxError("do requires a (test expression ...) clause")
    bindings = []
    steps = []
    for spec in specs:
        if not (
            isinstance(spec, tuple) and len(spec) in (2, 3) and isinstance(spec[0], str)
        ):
            raise SyntaxError("do variable specs must be (variable init [step])")
        bindings.append((spec[0], spec[1]))
        steps.append(spec[2] if len(spec) == 3 else spec[0])
    loop = f"_Qzdo_loop_{next(_gensym_counter)}"
    test, *results = exit_clause
    finish = ("begin", *results) if results else False
    again = (loop, *steps)
    if commands:
        again = ("begin", *commands, again)
    return ("let", loop, tuple(bindings), ("if", test, finish, again))

"""Compile calls to arithmetic, comparison, and vector access to Python code.

`(scheme base)` binds `+`, `<`, `vector-ref`, and friends to procedures, and
also exports a macro under each name. The macro turns a call with the expected
number of arguments, such as `(+ a b c)` or `(vector-ref v i)`, into the
Python expression it would compute (`a + b + c`, `v[i]`):

- the module-level binding at compile time is still base's (the bootstrap
  prelude binds the same procedures), so a module that defines its own `+`
  keeps calling it;
- a local variable named `+` lives in a cell (see `box_assigned_locals`), so
  local references compile to `cell[0]` and never reach this macro.

Exact rationals are `numeric_syntax.Rational`, whose operators already return
`int` for whole results, so plain Python operators give Scheme results.

The inline vector accessors skip the procedures' vector check, so they also
index other Python sequences, and negative indices count from the end.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from hissp.compiler import ENV

import scheme_pairs

from hissp_scheme import names
from hissp_scheme.runtime import arithmetic
from hissp_scheme.macro.inline import compile_subform

# Munged Scheme name -> (kind, Python operator or template, base procedure).
# `fold` operators take two or more arguments, left to right, and `-` is also
# negation. `chain` comparisons take two or more. `template` calls take exactly
# as many arguments as the template has slots.
PRIMITIVES = {
    "QzPLUS_": ("fold", "+", arithmetic.add),
    "QzH_": ("fold", "-", arithmetic.sub),
    "QzSTAR_": ("fold", "*", arithmetic.mul),
    "QzEQ_": ("chain", "==", arithmetic.num_eq),
    "QzLT_": ("chain", "<", arithmetic.num_lt),
    "QzGT_": ("chain", ">", arithmetic.num_gt),
    "QzLT_QzEQ_": ("chain", "<=", arithmetic.num_le),
    "QzGT_QzEQ_": ("chain", ">=", arithmetic.num_ge),
    "vectorQzH_ref": ("template", "{0}[{1}]", scheme_pairs.vector_ref),
    "vectorQzH_setQzBANG_": (
        "template",
        "{0}.__setitem__({1},{2})",
        scheme_pairs.vector_set_bang,
    ),
}

assert frozenset(PRIMITIVES) == names.INTEGRATED_PRIMITIVES

_CELL_REF = re.compile(r"_Qzcell_\d+_\w+\[0\]\Z")


def _atom(form):
    """Python source for an operand that compiles to itself, else None."""

    if type(form) is str and (form.isidentifier() or _CELL_REF.match(form)):
        return form
    if type(form) is int or (
        type(form) is float and form == form and abs(form) != float("inf")
    ):
        return repr(form)
    return None


def _operand(form, env):
    atom = _atom(form)
    return atom if atom is not None else f"({compile_subform(form, env)})"


def _expression(kind, spelling, args, env):
    """Python source for the call, or None if it must call the procedure."""

    if kind == "template":
        if len(args) != spelling.count("{"):
            return None
        return spelling.format(*(_operand(arg, env) for arg in args))
    if kind == "fold":
        if len(args) == 1 and spelling == "-":
            return f"(-{_operand(args[0], env)})"
        if len(args) < 2:
            return None
        code = _operand(args[0], env)
        for arg in args[1:]:
            code = f"({code}{spelling}{_operand(arg, env)})"
        return code
    if len(args) < 2:
        return None
    if len(args) == 2:
        return f"({_operand(args[0], env)}{spelling}{_operand(args[1], env)})"
    # Python's chained comparison stops at the first false link, but Scheme
    # evaluates every argument, so only side-effect-free operands chain.
    atoms = [_atom(arg) for arg in args]
    if None in atoms:
        return None
    return "(" + spelling.join(atoms) + ")"


def _integrated(name):
    kind, spelling, procedure = PRIMITIVES[name]

    def primitive(*args):
        env = ENV.get()
        code = None
        if (
            env is not None
            and env.get(name) is procedure
            and not any(type(arg) is str and arg.startswith(":") for arg in args)
        ):
            code = _expression(kind, spelling, args, env)
        if code is None:
            # A parenthesized head is a raw Python fragment, so Hissp calls
            # the variable instead of expanding this macro again.
            return (f"({name})", *args)
        return code

    primitive.__name__ = name
    primitive.__qualname__ = f"_macro_.{name}"
    return primitive


_macro_ = SimpleNamespace(**{name: _integrated(name) for name in PRIMITIVES})

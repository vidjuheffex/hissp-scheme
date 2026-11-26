"""Compile two-argument arithmetic and comparisons to Python operators.

`(scheme base)` binds `+`, `<`, and friends to variadic procedures, and also
exports a macro under each name. The macro turns a two-argument call such as
`(+ a b)` into Python's `a + b` when that's what the call would compute:

- the module-level `+` at compile time is still base's (or the bootstrap's
  `operator.add`), so a module that defines its own `+` keeps calling it;
- a local variable named `+` lives in a cell (see `box_assigned_locals`), so
  local references compile to `cell[0]` and never reach this macro.

Exact rationals are `numeric_syntax.Rational`, whose operators already return
`int` for whole results, so plain Python operators give Scheme results.

Atomic operands compile to an inline infix fragment. Other operands go through
the matching `operator` function, bound in the importing module as
`_Qzprim_<name>`.
"""

from __future__ import annotations

import operator
import re
from types import SimpleNamespace

from hissp.compiler import ENV

from hissp_scheme import names
from hissp_scheme.runtime import base_runtime

# Munged Scheme name -> (infix operator, operator function, base procedure).
PRIMITIVES = {
    "QzPLUS_": ("+", operator.add, base_runtime.add),
    "QzH_": ("-", operator.sub, base_runtime.sub),
    "QzSTAR_": ("*", operator.mul, base_runtime.mul),
    "QzEQ_": ("==", operator.eq, base_runtime.num_eq),
    "QzLT_": ("<", operator.lt, base_runtime.num_lt),
    "QzGT_": (">", operator.gt, base_runtime.num_gt),
    "QzLT_QzEQ_": ("<=", operator.le, base_runtime.num_le),
    "QzGT_QzEQ_": (">=", operator.ge, base_runtime.num_ge),
}

assert frozenset(PRIMITIVES) == names.INTEGRATED_PRIMITIVES

_CELL_REF = re.compile(r"_Qzcell_\d+_\w+\[0\]\Z")


def helper_name(function):
    return f"_Qzprim_{function.__name__}"


def _inline_operand(form):
    """Python source for an operand that compiles to itself, else None."""

    if type(form) is str:
        if form.isidentifier() or _CELL_REF.match(form):
            return form
        return None
    if type(form) is int or (type(form) is float and form == form and abs(form) != float("inf")):
        return repr(form)
    return None


def _integrated(name):
    infix, function, procedure = PRIMITIVES[name]
    helper = helper_name(function)

    def primitive(*args):
        env = ENV.get()
        binding = env.get(name) if env is not None else None
        if (
            len(args) != 2
            or not (binding is procedure or binding is function)
            or any(type(arg) is str and arg.startswith(":") for arg in args)
        ):
            # A parenthesized head is a raw Python fragment, so Hissp calls
            # the variable instead of expanding this macro again.
            return (f"({name})", *args)
        left, right = (_inline_operand(arg) for arg in args)
        if left is not None and right is not None:
            return f"({left}{infix}{right})"
        if env.get(helper) is function:
            return (helper, *args)
        return (f"({name})", *args)

    primitive.__name__ = name
    primitive.__qualname__ = f"_macro_.{name}"
    return primitive


_macro_ = SimpleNamespace(**{name: _integrated(name) for name in PRIMITIVES})

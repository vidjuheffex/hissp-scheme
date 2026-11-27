"""Compile calls to arithmetic, comparison, and vector access to Python code.

`(scheme base)` binds `+`, `<`, `vector-ref`, and friends to procedures, and
also exports a macro under each name. The macro turns a call with the expected
number of arguments, such as `(+ a b)` or `(vector-ref v i)`, into the Python
expression it would compute (`a + b`, `v[i]`):

- the module-level binding at compile time is still base's (or the
  bootstrap's `operator.add`), so a module that defines its own `+` keeps
  calling it;
- a local variable named `+` lives in a cell (see `box_assigned_locals`), so
  local references compile to `cell[0]` and never reach this macro.

Exact rationals are `numeric_syntax.Rational`, whose operators already return
`int` for whole results, so plain Python operators give Scheme results.

The inline vector accessors skip the procedures' vector check, so they also
index other Python sequences, and negative indices count from the end.
"""

from __future__ import annotations

import operator
import re
from types import SimpleNamespace

from hissp.compiler import ENV

import scheme_pairs

from hissp_scheme import names
from hissp_scheme.macro.inline import compile_subform
from hissp_scheme.runtime import base_runtime

# Munged Scheme name -> (Python template, bindings the call may compile from).
PRIMITIVES = {
    "QzPLUS_": ("({0}+{1})", (operator.add, base_runtime.add)),
    "QzH_": ("({0}-{1})", (operator.sub, base_runtime.sub)),
    "QzSTAR_": ("({0}*{1})", (operator.mul, base_runtime.mul)),
    "QzEQ_": ("({0}=={1})", (operator.eq, base_runtime.num_eq)),
    "QzLT_": ("({0}<{1})", (operator.lt, base_runtime.num_lt)),
    "QzGT_": ("({0}>{1})", (operator.gt, base_runtime.num_gt)),
    "QzLT_QzEQ_": ("({0}<={1})", (operator.le, base_runtime.num_le)),
    "QzGT_QzEQ_": ("({0}>={1})", (operator.ge, base_runtime.num_ge)),
    "vectorQzH_ref": ("{0}[{1}]", (scheme_pairs.vector_ref,)),
    "vectorQzH_setQzBANG_": ("{0}.__setitem__({1},{2})", (scheme_pairs.vector_set_bang,)),
}

assert frozenset(PRIMITIVES) == names.INTEGRATED_PRIMITIVES

_CELL_REF = re.compile(r"_Qzcell_\d+_\w+\[0\]\Z")


def _operand(form, env):
    """Python source for an operand, parenthesized unless it's atomic."""

    if type(form) is str and (form.isidentifier() or _CELL_REF.match(form)):
        return form
    if type(form) is int or (type(form) is float and form == form and abs(form) != float("inf")):
        return repr(form)
    return f"({compile_subform(form, env)})"


def _integrated(name):
    template, bindings = PRIMITIVES[name]
    arity = template.count("{")

    def primitive(*args):
        env = ENV.get()
        binding = env.get(name) if env is not None else None
        if (
            len(args) != arity
            or not any(binding is allowed for allowed in bindings)
            or any(type(arg) is str and arg.startswith(":") for arg in args)
        ):
            # A parenthesized head is a raw Python fragment, so Hissp calls
            # the variable instead of expanding this macro again.
            return (f"({name})", *args)
        return template.format(*(_operand(arg, env) for arg in args))

    primitive.__name__ = name
    primitive.__qualname__ = f"_macro_.{name}"
    return primitive


_macro_ = SimpleNamespace(**{name: _integrated(name) for name in PRIMITIVES})

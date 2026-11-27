"""Compile `if` and `let` to plain Python expressions.

Hissp has no conditional or binding special forms. Its `if-else` passes the
branches as thunks to a lambda, and its `let` calls a lambda with the bindings
as default arguments, so both cost function objects and calls on every
evaluation. These forms sit on every hot path (`cond`, `and`, `or`, `when`,
`case`, and loop exits expand to them), so these macros compile their own
subforms and splice the Python code into an expression:

    (if test consequent alternate)
    -> ((consequent) if (test) is not False else (alternate))

    (let ((x init)) body ...)
    -> ((_Qzlet_7_x := (init)), (body), ...)[-1]

Only `#f` is false in Scheme, hence the `is not False` test. Each `let`
variable gets a fresh name, so the `:=` assignment can't clobber an outer
variable, and each procedure call has its own Python frame, so closures over a
`let` variable see the value from their own call.

Subforms compile in the current module's environment, so their macros expand
as they would in place.
"""

from __future__ import annotations

import ast
import itertools

from hissp.compiler import ENV, Compiler

_let_counter = itertools.count(1)


def compile_subform(form, env=None):
    """Python code for `form`, compiled in the current module's environment."""

    env = ENV.get() if env is None else env
    compiler = Compiler(
        qualname=env.get("__name__", "__main__"), env=env, evaluate=False
    )
    code = compiler.compile_form(form)
    if compiler.error is not None:
        raise compiler.error
    return code


def _literal_value(code):
    try:
        return True, ast.literal_eval(code)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False, None


def if_form(test, consequent, alternate):
    env = ENV.get()
    test_code = compile_subform(test, env)
    # A literal test, as in `(if 0 ...)`, selects its branch at compile time.
    # (Python also warns about `is` comparisons with literals.)
    is_literal, value = _literal_value(test_code)
    if is_literal:
        return compile_subform(consequent if value is not False else alternate, env)
    consequent_code = compile_subform(consequent, env)
    alternate_code = compile_subform(alternate, env)
    return (
        f"(({consequent_code})\n if ({test_code}) is not False\n"
        f" else ({alternate_code}))"
    )


def fresh_let_name(name):
    return f"_Qzlet_{next(_let_counter)}_{name}"


def sequence_form(assignments, body):
    """Python expression that runs `assignments`, then `body`, for its last value.

    `assignments` is a sequence of `(python_name, form)` pairs.
    """

    env = ENV.get()
    parts = [
        f"({name} := ({compile_subform(form, env)}))" for name, form in assignments
    ]
    parts.extend(f"({compile_subform(form, env)})" for form in body)
    if not body:
        parts.append("None")
    if len(parts) == 1:
        return parts[0]
    return "(" + ",\n ".join(parts) + ")[-1]"

"""Compile Scheme `if` to a Python conditional expression.

Hissp has no conditional special form. Its `if-else` macro passes the branches
as thunks to a lambda, which costs a few function objects and calls on every
evaluation. Scheme `if` sits on every hot path (`cond`, `and`, `when`, and
loop exits all expand to it), so it compiles its own subforms and splices them
into a Python conditional instead:

    (if test consequent alternate)
    -> ((consequent) if (test) is not False else (alternate))

Only `#f` is false in Scheme, hence the `is not False` test. The subforms are
compiled in the current module's environment, so their macros expand just as
they would in place.
"""

from __future__ import annotations

import ast

from hissp.compiler import ENV, Compiler


def _compile(form, env):
    compiler = Compiler(qualname=env.get("__name__", "__main__"), env=env, evaluate=False)
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
    test_code = _compile(test, env)
    # A literal test, as in `(if 0 ...)`, selects its branch at compile time.
    # (Python also warns about `is` comparisons with literals.)
    is_literal, value = _literal_value(test_code)
    if is_literal:
        return _compile(consequent if value is not False else alternate, env)
    consequent_code = _compile(consequent, env)
    alternate_code = _compile(alternate, env)
    return (
        f"(({consequent_code})\n if ({test_code}) is not False\n"
        f" else ({alternate_code}))"
    )

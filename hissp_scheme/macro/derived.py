"""Procedural transformers for derived `(scheme base)` syntax.

These build ordinary Scheme forms (`begin`, `define`, `lambda`, `let`) from
`define-record-type`, `define-values`, `let-values`, `let*-values`,
`cond-expand`, `include-ci`, and `syntax-error`.

Definition-producing forms expand to `(begin (define ...) ...)`. The body
expander in `syntax_rules` calls `definition_expansion` so those definitions
count as internal definitions when the forms appear in a body.
"""

from __future__ import annotations

import ast
import itertools

from hissp_scheme import names
from hissp_scheme.macro.quote import is_string_literal_form, symbol_form

_gensym_counter = itertools.count(1)

_CONTROL = "hissp_scheme.runtime.control_runtime.."
_RECORDS = "hissp_scheme.runtime.records.."
_LAMBDA = "schemeQzH_lambda"


def _gensym(stem):
    return f"_Qz{stem}_{next(_gensym_counter)}"


def _source(form):
    if isinstance(form, str):
        if is_string_literal_form(form):
            return form
        return names.demunge(form)
    if isinstance(form, tuple):
        return "(" + " ".join(_source(item) for item in form) + ")"
    return repr(form)


def _identifier(value, what, form_name):
    if not isinstance(value, str) or is_string_literal_form(value):
        raise SyntaxError(
            f"{form_name}: {what} must be an identifier, got {_source(value)}"
        )
    return value


# ---------------------------------------------------------------------------
# define-record-type
# ---------------------------------------------------------------------------


def define_record_type_form(type_name, constructor, predicate, *field_specs):
    form_name = "define-record-type"
    _identifier(type_name, "the type name", form_name)
    _identifier(predicate, "the predicate name", form_name)

    field_names = []
    accessors = []
    for spec in field_specs:
        if not (isinstance(spec, tuple) and 2 <= len(spec) <= 3):
            raise SyntaxError(
                f"{form_name}: field specs must be (field accessor [modifier]), "
                f"got {_source(spec)}"
            )
        field = _identifier(spec[0], "a field name", form_name)
        if field in field_names:
            raise SyntaxError(f"{form_name}: duplicate field {_source(field)}")
        field_names.append(field)
        accessors.append(
            (
                "define",
                _identifier(spec[1], "an accessor name", form_name),
                (
                    f"{_RECORDS}record_accessor",
                    type_name,
                    symbol_form(spec[1]),
                    symbol_form(field),
                ),
            )
        )
        if len(spec) == 3:
            accessors.append(
                (
                    "define",
                    _identifier(spec[2], "a modifier name", form_name),
                    (
                        f"{_RECORDS}record_modifier",
                        type_name,
                        symbol_form(spec[2]),
                        symbol_form(field),
                    ),
                )
            )

    definitions = [
        (
            "define",
            type_name,
            (
                f"{_RECORDS}make_record_type",
                symbol_form(type_name),
                ("scheme_pairs..scheme_list", *map(symbol_form, field_names)),
            ),
        )
    ]

    # `#f` means no constructor; a bare name takes every field in order.
    if constructor != "QzHASH_f":
        if isinstance(constructor, str):
            constructor_name, constructor_fields = constructor, tuple(field_names)
        elif isinstance(constructor, tuple) and constructor:
            constructor_name, *constructor_fields = constructor
        else:
            raise SyntaxError(
                f"{form_name}: constructor must be (name field ...), a name, or #f"
            )
        _identifier(constructor_name, "the constructor name", form_name)
        for field in constructor_fields:
            if field not in field_names:
                raise SyntaxError(
                    f"{form_name}: constructor field {_source(field)} is not a field"
                )
        definitions.append(
            (
                "define",
                constructor_name,
                (
                    f"{_RECORDS}record_constructor",
                    type_name,
                    symbol_form(constructor_name),
                    (
                        "scheme_pairs..scheme_list",
                        *map(symbol_form, constructor_fields),
                    ),
                ),
            )
        )

    definitions.append(
        (
            "define",
            predicate,
            (f"{_RECORDS}record_predicate", type_name, symbol_form(predicate)),
        )
    )
    definitions.extend(accessors)
    return ("begin", *definitions)


# ---------------------------------------------------------------------------
# Multiple-value binding forms
# ---------------------------------------------------------------------------


def _split_formals(formals, form_name):
    """Return (required names, rest name or None) for lambda-style formals."""

    if isinstance(formals, str) and not is_string_literal_form(formals):
        return (), formals
    if not isinstance(formals, tuple):
        raise SyntaxError(f"{form_name}: formals must be a list or an identifier")
    if "." in formals:
        if formals.index(".") != len(formals) - 2:
            raise SyntaxError(f"{form_name}: dotted formals must end with . rest")
        required, rest = formals[:-2], formals[-1]
    else:
        required, rest = formals, None
    for name in (*required, *(() if rest is None else (rest,))):
        _identifier(name, "a formal", form_name)
    return tuple(required), rest


def _temporary_formals(formals, form_name):
    """Fresh formals shaped like `formals`, plus (name, temporary) pairs."""

    required, rest = _split_formals(formals, form_name)
    temps = [_gensym("values") for _ in required]
    pairs = list(zip(required, temps))
    if rest is None:
        return tuple(temps), pairs
    rest_temp = _gensym("values")
    pairs.append((rest, rest_temp))
    if not required:
        return rest_temp, pairs
    return (*temps, ".", rest_temp), pairs


def _call_with_values(expression, formals, body):
    return (
        f"{_CONTROL}call_with_values",
        (_LAMBDA, (), expression),
        (_LAMBDA, formals, *body),
    )


def let_values_form(bindings, *body):
    form_name = "let-values"
    if not isinstance(bindings, tuple):
        raise SyntaxError(f"{form_name} bindings must be a list")
    renames = []
    stages = []
    for binding in bindings:
        if not (isinstance(binding, tuple) and len(binding) == 2):
            raise SyntaxError(
                f"{form_name} bindings must be (formals expression) pairs"
            )
        formals, expression = binding
        temp_formals, pairs = _temporary_formals(formals, form_name)
        names_seen = [name for name, _ in renames]
        for name, _ in pairs:
            if name in names_seen:
                raise SyntaxError(f"{form_name}: duplicate binding {_source(name)}")
            names_seen.append(name)
        renames.extend(pairs)
        stages.append((expression, temp_formals))

    result = ("let", tuple((name, temp) for name, temp in renames), *body)
    for expression, temp_formals in reversed(stages):
        result = _call_with_values(expression, temp_formals, (result,))
    return result


def let_star_values_form(bindings, *body):
    if not isinstance(bindings, tuple):
        raise SyntaxError("let*-values bindings must be a list")
    if not bindings:
        return ("let", (), *body)
    result = ("letQzH_values", (bindings[-1],), *body)
    for binding in reversed(bindings[:-1]):
        result = ("letQzH_values", (binding,), result)
    return result


def define_values_form(formals, expression):
    form_name = "define-values"
    required, rest = _split_formals(formals, form_name)
    temp = _gensym("define_values")
    definitions = [
        (
            "define",
            temp,
            (
                f"{_CONTROL}values_list",
                (_LAMBDA, (), expression),
                len(required),
                rest is not None,
            ),
        )
    ]
    for index, name in enumerate(required):
        definitions.append(("define", name, ("operator..getitem", temp, index)))
    if rest is not None:
        definitions.append(
            (
                "define",
                rest,
                (
                    "scheme_pairs..py_to_list",
                    (
                        "operator..getitem",
                        temp,
                        ("builtins..slice", len(required), None),
                    ),
                ),
            )
        )
    return ("begin", *definitions)


# ---------------------------------------------------------------------------
# cond-expand, include-ci, syntax-error
# ---------------------------------------------------------------------------


def _requirement_q(requirement):
    from hissp_scheme.runtime import features

    if isinstance(requirement, str) and not is_string_literal_form(requirement):
        return features.feature_q(names.demunge(requirement))
    if isinstance(requirement, tuple) and requirement:
        operator, *arguments = requirement
        operator = (
            names.restore_keyword(operator) if isinstance(operator, str) else operator
        )
        if operator == "and":
            return all(_requirement_q(item) for item in arguments)
        if operator == "or":
            return any(_requirement_q(item) for item in arguments)
        if operator == "not" and len(arguments) == 1:
            return not _requirement_q(arguments[0])
        if operator == "library" and len(arguments) == 1:
            return features.library_available_q(arguments[0])
    raise SyntaxError(
        f"cond-expand: invalid feature requirement {_source(requirement)}"
    )


def cond_expand_clause_body(clauses, form_name="cond-expand"):
    """Body of the first `cond-expand` clause whose requirement holds."""

    for clause in clauses:
        if not (isinstance(clause, tuple) and clause):
            raise SyntaxError(f"{form_name} clauses must be non-empty lists")
        requirement, *body = clause
        if requirement == "else" or _requirement_q(requirement):
            return tuple(body)
    return ()


def cond_expand_form(*clauses):
    return ("begin", *cond_expand_clause_body(clauses))


def include_ci_form(*paths):
    from hissp_scheme.runtime.scheme_bootstrap_runtime import scheme_include_forms

    if not paths:
        raise SyntaxError("include-ci requires at least one filename")
    return ("begin", *scheme_include_forms(paths, fold_case=True))


def _literal(form):
    if is_string_literal_form(form):
        return ast.literal_eval(form)
    return _source(form)


def syntax_error_form(message, *irritants):
    text = _literal(message)
    if irritants:
        text = f"{text} {' '.join(_source(item) for item in irritants)}"
    raise SyntaxError(text)


# ---------------------------------------------------------------------------
# Body expansion
# ---------------------------------------------------------------------------

_DEFINITION_FORMS = {
    "defineQzH_recordQzH_type": define_record_type_form,
    "defineQzH_values": define_values_form,
    "condQzH_expand": cond_expand_form,
    "includeQzH_ci": include_ci_form,
}


def definition_expansion(form):
    """`(begin ...)` for a form that may splice definitions into a body, else None."""

    if type(form) is not tuple or not form:
        return None
    head = form[0]
    if head == "include":
        from hissp_scheme.runtime.scheme_bootstrap_runtime import scheme_include_forms

        return ("begin", *scheme_include_forms(form[1:]))
    transformer = _DEFINITION_FORMS.get(head)
    if transformer is None:
        return None
    return transformer(*form[1:])

"""Macro-expander substrate for Scheme syntax forms.

This is ordinary Python on purpose. It implements the language substrate used
by `scheme_base.sld` for `define-syntax`, `syntax-rules`, local syntax
bindings, and the small procedural `syntax-case` hook.
"""

import builtins
import itertools


WILDCARD = "_"
_gensym_counter = itertools.count(1)


DEFAULT_STABLE_IDENTIFIERS = {
    # Special forms and Scheme macro names that should remain visible to the
    # target expansion environment.
    "quote",
    "if",
    "begin",
    "lambda",
    "schemeQzH_lambda",
    "let",
    "letQzSTAR_",
    "letrec",
    "letrecQzSTAR_",
    "do",
    "guard",
    "parameterize",
    "raise",
    "define",
    "defineQzH_syntax",
    "letQzH_syntax",
    "letrecQzH_syntax",
    "syntaxQzH_rules",
    "setQzBANG_",
    "import",
    "include",
    "and",
    "or",
    "when",
    "unless",
    "cond",
    "case",
    "caseQzH_dispatch",
    # Boolean constants installed by the base prelude.
    "QzHASH_t",
    "QzHASH_f",
    # Common operators.
    "QzPLUS_",
    "QzH_",
    "QzSTAR_",
    "QzSOL_",
    "QzEQ_",
    "QzLT_",
    "QzGT_",
    "QzLT_QzEQ_",
    "QzGT_QzEQ_",
    "opQzHASH_contains",
    # Core pair/list procedures. SRFI procedures are intentionally not listed
    # here: libraries must import the SRFIs they use, and SRFI-specific stable
    # identifiers should come from the macro definition site or explicit
    # syntax-rules literals.
    "cons",
    "list",
    "car",
    "cdr",
    "pairQzQUERY_",
    "nullQzQUERY_",
    "append",
    "reverse",
    "length",
}


class MatchFailure(Exception):
    # Internal control-flow exception used to backtrack between syntax-rules
    # clauses. User-facing errors are raised as SyntaxError by the public
    # transformer when no rule matches.
    pass


def cell(value=False):
    return [value]


def cell_ref(value):
    return value[0]


def cell_set(value, item):
    value[0] = item
    return item


def _is_symbol(value):
    # Hissp represents identifiers as strings after reading/munging. String
    # literals are also strings, but the reader represents them as strings that
    # look like Python string forms, e.g. \"('hello')\". They can still be bound
    # as pattern data, which is acceptable for macro matching.
    return isinstance(value, str)


def _is_ellipsis(value):
    # The Hissp reader turns source `...` into Python's Ellipsis singleton.
    return value is Ellipsis


def _is_literal_string_form(value):
    # Hissp represents string literals as strings containing a Python string
    # expression. These are data, not identifiers, so hygiene must never rename
    # them.
    return (
        isinstance(value, str)
        and len(value) >= 2
        and value[0] == "("
        and value[1] == chr(39)
    )


def _is_define_syntax_form(form):
    # Internal syntax definitions arrive here as ordinary reader data. The
    # spelling is already Hissp-munged because source `define-syntax` is not a
    # legal Python identifier.
    return isinstance(form, tuple) and len(form) == 3 and form[0] == "defineQzH_syntax"


def _is_define_form(form):
    return isinstance(form, tuple) and len(form) >= 3 and form[0] == "define"


def _definition_name(form):
    if not _is_define_form(form):
        return None
    head = form[1]
    if isinstance(head, str):
        if len(form) != 3:
            raise SyntaxError("value-style internal define requires exactly one value")
        return head
    if isinstance(head, tuple) and head and isinstance(head[0], str):
        return head[0]
    raise SyntaxError("internal define requires an identifier or function head")


def _definition_value_form(form):
    head = form[1]
    if isinstance(head, str):
        return form[2]
    return ("schemeQzH_lambda", tuple(head[1:]), *form[2:])


def _formal_names(formals):
    if isinstance(formals, str):
        return {formals}
    if not isinstance(formals, tuple):
        return set()
    names = set()
    for item in formals:
        if item == ".":
            continue
        if isinstance(item, str):
            names.add(item)
    return names


CELL_PREFIX = "_Qzcell_"


def _new_cell_name(name):
    return f"{CELL_PREFIX}{next(_gensym_counter)}_{name}"


def cell_ref_form(cell_name):
    # A raw Python fragment rather than a call: cell reads sit on hot paths such
    # as named-let loop variables.
    return f"{cell_name}[0]"


def cell_name_from_ref_form(form):
    # Inverse of `cell_ref_form`, used by `set!` when a macro passes an already
    # rewritten local reference as its target.
    if (
        isinstance(form, str)
        and form.startswith(CELL_PREFIX)
        and form.endswith("[0]")
    ):
        return form[:-3]
    return None


def _rewrite_internal_definition_symbol(symbol, cells):
    if symbol in cells:
        return cell_ref_form(cells[symbol])

    for name in sorted(cells, key=len, reverse=True):
        prefix = f"{name}."
        if not symbol.startswith(prefix):
            continue
        value = cell_ref_form(cells[name])
        for attribute in symbol[len(prefix) :].split("."):
            value = ("getattr", value, f"('{attribute}')")
        return value

    return symbol


def _without(mapping, names):
    if not names:
        return mapping
    return {name: value for name, value in mapping.items() if name not in names}


def _binding_pair_names(bindings):
    return [
        binding[0]
        for binding in bindings
        if isinstance(binding, tuple) and binding and isinstance(binding[0], str)
    ]


def _scoped_parts(form):
    """Describe the lexical scopes of a Scheme binding form.

    Returns a list of `(subform, shadowed_names)` pairs covering every subform
    that should be walked, or `None` when `form` isn't a binding form. Binding
    names themselves are left out so walkers never rewrite them.
    """

    operator = form[0]

    if operator in {"schemeQzH_lambda", "lambda"} and len(form) >= 3:
        shadowed = _formal_names(form[1])
        return [(item, shadowed) for item in form[2:]]

    if operator == "define" and len(form) >= 3 and isinstance(form[1], tuple):
        shadowed = _formal_names(form[1][1:])
        return [(item, shadowed) for item in form[2:]]

    if operator == "define" and len(form) == 3:
        return [(form[2], set())]

    if operator in {"let", "letQzSTAR_", "letrec", "letrecQzSTAR_"} and len(form) >= 3:
        named = operator == "let" and isinstance(form[1], str)
        bindings = form[2] if named else form[1]
        body = form[3:] if named else form[2:]
        if not isinstance(bindings, tuple):
            return None
        names = _binding_pair_names(bindings)
        all_names = set(names) | ({form[1]} if named else set())
        parts = []
        for index, binding in enumerate(bindings):
            if not (isinstance(binding, tuple) and len(binding) == 2):
                continue
            if operator in {"letrec", "letrecQzSTAR_"}:
                init_shadowed = set(names)
            elif operator == "letQzSTAR_":
                init_shadowed = set(names[:index])
            else:
                init_shadowed = set()
            parts.append((binding[1], init_shadowed))
        parts.extend((item, all_names) for item in body)
        return parts

    if operator == "do" and len(form) >= 3 and isinstance(form[1], tuple):
        specs = form[1]
        names = set(_binding_pair_names(specs))
        parts = []
        for spec in specs:
            if isinstance(spec, tuple) and len(spec) >= 2:
                parts.append((spec[1], set()))
                parts.extend((step, names) for step in spec[2:])
        parts.append((form[2], names))
        parts.extend((item, names) for item in form[3:])
        return parts

    return None


def _rebuild_scoped(form, rewrite):
    """Rebuild a binding form, applying `rewrite(subform, shadowed)` to parts."""

    operator = form[0]

    if operator in {"schemeQzH_lambda", "lambda"} or operator == "define":
        parts = _scoped_parts(form)
        head_length = len(form) - len(parts)
        return (*form[:head_length], *(rewrite(item, shadowed) for item, shadowed in parts))

    if operator in {"let", "letQzSTAR_", "letrec", "letrecQzSTAR_"}:
        named = operator == "let" and isinstance(form[1], str)
        bindings = form[2] if named else form[1]
        body = form[3:] if named else form[2:]
        names = _binding_pair_names(bindings)
        all_names = set(names) | ({form[1]} if named else set())
        new_bindings = []
        for index, binding in enumerate(bindings):
            if not (isinstance(binding, tuple) and len(binding) == 2):
                new_bindings.append(binding)
                continue
            if operator in {"letrec", "letrecQzSTAR_"}:
                init_shadowed = set(names)
            elif operator == "letQzSTAR_":
                init_shadowed = set(names[:index])
            else:
                init_shadowed = set()
            new_bindings.append((binding[0], rewrite(binding[1], init_shadowed)))
        head = (operator, form[1]) if named else (operator,)
        return (
            *head,
            tuple(new_bindings),
            *(rewrite(item, all_names) for item in body),
        )

    if operator == "do":
        specs = form[1]
        names = set(_binding_pair_names(specs))
        new_specs = []
        for spec in specs:
            if isinstance(spec, tuple) and len(spec) >= 2:
                new_specs.append(
                    (
                        spec[0],
                        rewrite(spec[1], set()),
                        *(rewrite(step, names) for step in spec[2:]),
                    )
                )
            else:
                new_specs.append(spec)
        return (
            operator,
            tuple(new_specs),
            rewrite(form[2], names),
            *(rewrite(item, names) for item in form[3:]),
        )

    raise AssertionError(f"not a binding form: {operator!r}")


def _rewrite_internal_definition_references(form, cells):
    if isinstance(form, str):
        return _rewrite_internal_definition_symbol(form, cells)

    if not isinstance(form, tuple) or not form:
        return form

    operator = form[0]
    if operator == "quote":
        return form

    if (
        operator in {"setQzBANG_", "set!"}
        and len(form) == 3
        and isinstance(form[1], str)
    ):
        if form[1] in cells:
            return (
                "hissp_scheme.macro.syntax_rules..cell_set",
                cells[form[1]],
                _rewrite_internal_definition_references(form[2], cells),
            )

    if _scoped_parts(form) is not None:
        return _rebuild_scoped(
            form,
            lambda item, shadowed: _rewrite_internal_definition_references(
                item, _without(cells, shadowed)
            ),
        )

    return tuple(_rewrite_internal_definition_references(item, cells) for item in form)


def _collect_assigned_names(form, candidates, found):
    if not candidates or not isinstance(form, tuple) or not form:
        return

    operator = form[0]
    if operator == "quote":
        return

    if (
        operator in {"setQzBANG_", "set!"}
        and len(form) == 3
        and isinstance(form[1], str)
        and form[1] in candidates
    ):
        found.add(form[1])

    parts = _scoped_parts(form)
    if parts is not None:
        for item, shadowed in parts:
            _collect_assigned_names(item, candidates - shadowed, found)
        return

    for item in form:
        _collect_assigned_names(item, candidates, found)


def box_assigned_locals(names, body):
    """Move locals that are targets of `set!` into mutable cells.

    Hissp lowers Scheme bodies to nested Python lambdas, which can't rebind an
    enclosing variable (there is no `nonlocal` in an expression). Each assigned
    name in `names` is copied into a cell at the top of `body`, and every
    reference and `set!` inside `body` goes through the cell instead.

    Only `set!` forms visible in the source are found; a macro that expands
    into `set!` of a caller's variable isn't detected.
    """

    body = tuple(body)
    found = set()
    for form in body:
        _collect_assigned_names(form, set(names), found)
    if not found:
        return body

    cells = {name: _new_cell_name(name) for name in sorted(found)}
    bindings = tuple(
        itertools.chain.from_iterable(
            (cell_name, ("hissp_scheme.macro.syntax_rules..cell", name))
            for name, cell_name in cells.items()
        )
    )
    rewritten = tuple(
        _rewrite_internal_definition_references(form, cells) for form in body
    )
    return (("hissp.macros.._macro_.let", bindings, *rewritten),)


def syntax_rules_stable_identifiers(extra=()):
    # Return the stable identifier set used for one transformer. Callers pass
    # this explicitly so future phases can provide a more precise lexical
    # context without rewriting the matcher/expander core.
    return set(DEFAULT_STABLE_IDENTIFIERS).union(extra)


def _is_stable_identifier(value, stable_identifiers):
    # Stable identifiers are left alone in templates. This is a pragmatic
    # stand-in for proper lexical-context tracking: known core names resolve in
    # the expansion environment, while local temporaries introduced by the macro
    # get generated names.
    if not isinstance(value, str):
        return False
    if value in stable_identifiers:
        return True
    if value.startswith(":"):
        return True
    if ".." in value:
        return True
    if _is_literal_string_form(value):
        return True
    return False


def _introduced_identifier(name, introduced):
    # Give each introduced identifier a stable generated spelling for one macro
    # expansion. Repeated occurrences of the same template identifier map to the
    # same generated name so local bindings and references still line up.
    if name not in introduced:
        introduced[name] = f"_Qzsyntax_rules_{next(_gensym_counter)}_{name}"
    return introduced[name]


def _pattern_variables(pattern, literals):
    # Return every pattern variable introduced by `pattern`. This is needed when
    # a repeated pattern matches zero times: variables inside the repeated
    # pattern must still be bound to an empty repetition list so template
    # expansion can use them safely.
    if isinstance(pattern, tuple):
        result = set()
        for item in pattern:
            if not _is_ellipsis(item):
                result.update(_pattern_variables(item, literals))
        return result
    if _is_symbol(pattern) and pattern != WILDCARD and pattern not in literals:
        return {pattern}
    return set()


def _bind_variable(bindings, name, value):
    # Bind one non-repeated pattern variable. Repeated variables are represented
    # as Python lists and are handled by `_append_repeated_bindings`.
    if name in bindings and bindings[name] != value:
        raise MatchFailure
    bindings[name] = value


def _append_repeated_bindings(bindings, repeated_vars, local_bindings):
    # Merge one repetition match into the outer binding table.
    for name in repeated_vars:
        bindings.setdefault(name, []).append(local_bindings[name])


def _match_atom(pattern, form, literals, bindings):
    # Match one non-list pattern atom.
    if _is_symbol(pattern):
        if pattern == WILDCARD:
            return
        if pattern in literals:
            if pattern != form:
                raise MatchFailure
            return
        _bind_variable(bindings, pattern, form)
        return

    if pattern != form:
        raise MatchFailure


def _match_sequence(pattern, form, literals, bindings):
    # Match tuple/list pattern structure. This supports one ellipsis marker per
    # tuple level:
    #
    #   (macro fixed repeated ... tail)
    #
    # Nested tuple levels may each have their own ellipsis, but the matched
    # binding shape must remain regular. Later template expansion validates that
    # repeated variables are only used under a compatible number of ellipses.
    if not isinstance(form, tuple):
        raise MatchFailure

    ellipsis_positions = [
        index for index, item in enumerate(pattern) if _is_ellipsis(item)
    ]
    if not ellipsis_positions:
        if len(pattern) != len(form):
            raise MatchFailure
        for pattern_item, form_item in builtins.zip(pattern, form):
            _match(pattern_item, form_item, literals, bindings)
        return

    if len(ellipsis_positions) > 1:
        raise SyntaxError("only one ellipsis per pattern level is supported")

    ellipsis_index = ellipsis_positions[0]
    if ellipsis_index == 0:
        raise SyntaxError("ellipsis must follow a repeat pattern")

    repeat_pattern = pattern[ellipsis_index - 1]
    prefix = pattern[: ellipsis_index - 1]
    suffix = pattern[ellipsis_index + 1 :]

    if len(form) < len(prefix) + len(suffix):
        raise MatchFailure

    for pattern_item, form_item in builtins.zip(prefix, form[: len(prefix)]):
        _match(pattern_item, form_item, literals, bindings)

    suffix_start = len(form) - len(suffix)
    for pattern_item, form_item in builtins.zip(suffix, form[suffix_start:]):
        _match(pattern_item, form_item, literals, bindings)

    repeated_forms = form[len(prefix) : suffix_start]
    repeated_vars = _pattern_variables(repeat_pattern, literals)
    for name in repeated_vars:
        bindings.setdefault(name, [])

    for repeated_form in repeated_forms:
        local_bindings = {}
        _match(repeat_pattern, repeated_form, literals, local_bindings)
        _append_repeated_bindings(bindings, repeated_vars, local_bindings)


def _match(pattern, form, literals, bindings):
    # Dispatch between atom and tuple matching.
    if isinstance(pattern, tuple):
        _match_sequence(pattern, form, literals, bindings)
    else:
        _match_atom(pattern, form, literals, bindings)


def _template_variables(template, bindings):
    # Find pattern variables referenced by a template fragment. This is used to
    # determine how many times an ellipsis template fragment should repeat.
    if isinstance(template, tuple):
        result = set()
        for item in template:
            if not _is_ellipsis(item):
                result.update(_template_variables(item, bindings))
        return result
    if _is_symbol(template) and template in bindings:
        return {template}
    return set()


def _template_repeated_variables(template, bindings):
    # Return only variables whose match value is a repetition list. Template
    # ellipses must be driven by at least one such variable.
    return {
        name
        for name in _template_variables(template, bindings)
        if isinstance(bindings[name], list)
    }


def _validate_template_ellipsis(template, bindings, depth=0):
    # Reject the easy-to-misread malformed ellipsis cases before producing a
    # partial expansion. This is intentionally conservative: if a template
    # fragment contains repeated variables, it must be followed by `...` at the
    # tuple level that consumes that repetition.
    if not isinstance(template, tuple):
        if (
            _is_symbol(template)
            and template in bindings
            and isinstance(bindings[template], list)
            and depth == 0
        ):
            raise SyntaxError(f"repeated variable {template!r} used outside ellipsis")
        return

    index = 0
    while index < len(template):
        item = template[index]
        if _is_ellipsis(item):
            raise SyntaxError("ellipsis must follow a template fragment")

        followed_by_ellipsis = index + 1 < len(template) and _is_ellipsis(
            template[index + 1]
        )
        repeated_vars = _template_repeated_variables(item, bindings)

        if (
            repeated_vars
            and not followed_by_ellipsis
            and depth == 0
            and not isinstance(item, tuple)
        ):
            names = ", ".join(sorted(repeated_vars))
            raise SyntaxError(f"repeated template variable outside ellipsis: {names}")

        _validate_template_ellipsis(
            item, bindings, depth + (1 if followed_by_ellipsis else 0)
        )
        index += 2 if followed_by_ellipsis else 1


def _binding_at_path(value, repeat_path):
    # Follow the active ellipsis indexes into a repeated binding. A flat
    # repetition has shape `[a, b, c]`; a nested repetition has shape
    # `[[a, b], [c, d]]`. The path `(1, 0)` selects `c`.
    for index in repeat_path:
        if not isinstance(value, list):
            raise SyntaxError("template has more ellipses than the pattern variable")
        value = value[index]
    return value


def _repetition_length(value, repeat_path):
    # Return the number of iterations for the next ellipsis at this path.
    value = _binding_at_path(value, repeat_path)
    if not isinstance(value, list):
        raise SyntaxError("template ellipsis has too many levels for pattern variable")
    return len(value)


def _repetition_count(template, bindings, repeat_path=()):
    # All repeated variables inside a template fragment must have the same
    # repetition count. This catches malformed templates early.
    counts = {
        _repetition_length(bindings[name], repeat_path)
        for name in _template_variables(template, bindings)
        if isinstance(bindings[name], list)
    }
    if not counts:
        raise SyntaxError("template ellipsis has no repeated pattern variable")
    if len(counts) != 1:
        raise SyntaxError(
            "template ellipsis variables have different repetition counts"
        )
    return counts.pop()


def _expand_atom(
    template,
    bindings,
    repeat_path,
    introduced,
    stable_identifiers,
    qualified_identifiers,
):
    # Replace a pattern variable with its matched form. Non-pattern symbols are
    # either stable global/core identifiers or introduced identifiers that must
    # be renamed to avoid accidental capture.
    if _is_symbol(template) and template in bindings:
        value = bindings[template]
        if isinstance(value, list):
            if not repeat_path:
                raise SyntaxError(
                    f"repeated variable {template!r} used outside ellipsis"
                )
            value = _binding_at_path(value, repeat_path)
            if isinstance(value, list):
                raise SyntaxError(
                    f"repeated variable {template!r} needs another ellipsis"
                )
            return value
        return value
    if _is_symbol(template) and template in qualified_identifiers:
        return qualified_identifiers[template]
    if _is_symbol(template) and not _is_stable_identifier(template, stable_identifiers):
        return _introduced_identifier(template, introduced)
    return template


def _expand_sequence(
    template,
    bindings,
    repeat_path,
    introduced,
    stable_identifiers,
    qualified_identifiers,
):
    # Expand one template tuple, splicing repeated template fragments into the
    # surrounding tuple when followed by `...`.
    output = []
    index = 0
    while index < len(template):
        item = template[index]
        if _is_ellipsis(item):
            raise SyntaxError("ellipsis must follow a template fragment")

        if index + 1 < len(template) and _is_ellipsis(template[index + 1]):
            count = _repetition_count(item, bindings, repeat_path)
            for repeated_index in range(count):
                output.append(
                    _expand(
                        item,
                        bindings,
                        repeat_path + (repeated_index,),
                        introduced,
                        stable_identifiers,
                        qualified_identifiers,
                    )
                )
            index += 2
            continue

        output.append(
            _expand(
                item,
                bindings,
                repeat_path,
                introduced,
                stable_identifiers,
                qualified_identifiers,
            )
        )
        index += 1

    return tuple(output)


def _expand(
    template,
    bindings,
    repeat_path=(),
    introduced=None,
    stable_identifiers=None,
    qualified_identifiers=None,
):
    # Dispatch between atom and tuple template expansion.
    if introduced is None:
        introduced = {}
    if stable_identifiers is None:
        stable_identifiers = syntax_rules_stable_identifiers()
    if qualified_identifiers is None:
        qualified_identifiers = {}
    if isinstance(template, tuple):
        if not repeat_path:
            _validate_template_ellipsis(template, bindings)
        return _expand_sequence(
            template,
            bindings,
            repeat_path,
            introduced,
            stable_identifiers,
            qualified_identifiers,
        )
    return _expand_atom(
        template,
        bindings,
        repeat_path,
        introduced,
        stable_identifiers,
        qualified_identifiers,
    )


def make_syntax_rules_transformer(
    name, literals, rules, stable_identifiers=None, qualified_identifiers=None
):
    # Build a Hissp macro function implementing one syntax-rules transformer.
    #
    # Hissp macro functions receive only the call arguments, not the operator
    # itself. Scheme syntax-rules patterns include the keyword in the first
    # position, so we reconstruct `(name . args)` before matching.
    if not isinstance(literals, tuple):
        raise SyntaxError("syntax-rules literals must be a list")

    stable_identifiers = syntax_rules_stable_identifiers(stable_identifiers or ())
    qualified_identifiers = qualified_identifiers or {}
    literal_set = set(literals)
    literal_set.add(name)

    if not rules:
        raise SyntaxError("syntax-rules requires at least one rule")

    for rule in rules:
        if not isinstance(rule, tuple) or len(rule) != 2:
            raise SyntaxError("each syntax-rules clause must be (pattern template)")

    def transformer(*args):
        form = (name, *args)
        for pattern, template in rules:
            bindings = {}
            try:
                _match(pattern, form, literal_set, bindings)
            except MatchFailure:
                continue
            return _expand(
                template,
                bindings,
                stable_identifiers=stable_identifiers,
                qualified_identifiers=qualified_identifiers,
            )
        raise SyntaxError(f"no syntax-rules pattern matched for {name}")

    transformer.__name__ = str(name)
    return transformer


def _syntax_rules_form_parts(transformer_form):
    # `syntax-rules` is represented as ordinary reader data. This helper
    # validates that shape and returns `(literals, rules)`.
    if (
        not isinstance(transformer_form, tuple)
        or not transformer_form
        or transformer_form[0] != "syntaxQzH_rules"
    ):
        raise SyntaxError("expected a syntax-rules transformer")
    if len(transformer_form) < 3:
        raise SyntaxError("syntax-rules requires literals and at least one rule")
    return transformer_form[1], transformer_form[2:]


def _syntax_case_transformer(name, transformer_form, env):
    # Minimal procedural transformer hook.
    #
    # This is intentionally much smaller than full R6RS/R7RS syntax-case. It is
    # the bridge for macros that cannot be expressed as syntax-rules because
    # they must compute target Hissp forms from identifiers, such as SRFI-177's
    # keyword-argument conversion.
    if len(transformer_form) != 2 or not isinstance(transformer_form[1], str):
        raise SyntaxError(
            "syntax-case currently expects one transformer procedure name"
        )
    if env is None:
        raise SyntaxError("syntax-case transformers require a definition environment")
    procedure_name = transformer_form[1]
    try:
        procedure = env[procedure_name]
    except KeyError:
        raise NameError(f"unbound syntax-case transformer: {procedure_name}") from None
    if not callable(procedure):
        raise TypeError(f"syntax-case transformer is not callable: {procedure_name}")

    def transformer(*args):
        return procedure(*args)

    transformer.__name__ = str(name)
    return transformer


def make_transformer_from_form(
    name, transformer_form, stable_identifiers=None, env=None
):
    # Shared constructor for `define-syntax` and `let-syntax`.
    if (
        isinstance(transformer_form, tuple)
        and transformer_form
        and transformer_form[0] == "syntaxQzH_case"
    ):
        return _syntax_case_transformer(name, transformer_form, env)

    qualified_identifiers = {}
    if env is not None:
        # Names already bound where the macro is defined should keep that
        # definition-site spelling in the expansion. This is the practical piece
        # of Scheme hygiene that lets a macro like SRFI-64 `test-group` expand
        # to its helper procedures (`test-begin`, `test-end`, etc.) without
        # treating them as caller-local identifiers to be gensymed.
        stable_identifiers = set(stable_identifiers or ()).union(env.keys())
        module_name = env.get("__name__")
        if isinstance(module_name, str) and module_name != "__main__":
            qualified_identifiers = {
                symbol: f"{module_name}..{symbol}"
                for symbol in env
                if (
                    isinstance(symbol, str)
                    and symbol not in DEFAULT_STABLE_IDENTIFIERS
                    and not symbol.startswith("__")
                    and symbol not in {"_macro_"}
                )
            }

    literals, rules = _syntax_rules_form_parts(transformer_form)
    return make_syntax_rules_transformer(
        name, literals, rules, stable_identifiers, qualified_identifiers
    )


def _expand_local_macros(form, local_macros):
    # Recursively expand local macro calls inside a `let-syntax` body. This is a
    # source-to-source expansion step; it does not mutate Hissp's global `_macro_`
    # table, so local macro names cannot leak outside the returned body.
    if not isinstance(form, tuple) or not form:
        return form

    operator = form[0]
    if operator == "quote":
        return form

    if isinstance(operator, str) and operator in local_macros:
        # A local transformer can expand into another local macro call. Because
        # recursive expansion uses the same completed `local_macros` table,
        # `letrec-syntax`-style mutual references work here.
        return _expand_local_macros(local_macros[operator](*form[1:]), local_macros)

    return tuple(_expand_local_macros(item, local_macros) for item in form)


def _local_macro_table(bindings, stable_identifiers, procedure):
    # Validate local syntax bindings and build a complete transformer table
    # before body expansion. The completed table is what gives
    # `letrec-syntax`-style transformers mutual visibility.
    if not isinstance(bindings, tuple):
        raise SyntaxError(f"{procedure} bindings must be a list")

    local_names = {
        binding[0]
        for binding in bindings
        if isinstance(binding, tuple)
        and len(binding) == 2
        and isinstance(binding[0], str)
    }
    stable_identifiers = syntax_rules_stable_identifiers(stable_identifiers).union(
        local_names
    )

    local_macros = {}
    for binding in bindings:
        if not isinstance(binding, tuple) or len(binding) != 2:
            raise SyntaxError(f"{procedure} bindings must be (name transformer) pairs")
        name, transformer_form = binding
        if not isinstance(name, str):
            raise SyntaxError(f"{procedure} binding names must be symbols")
        if name in local_macros:
            raise SyntaxError(f"duplicate {procedure} binding: {name}")
        local_macros[name] = make_transformer_from_form(
            name, transformer_form, stable_identifiers
        )
    return local_macros


def _expand_local_syntax(procedure, bindings, body, stable_identifiers=None):
    stable_identifiers = syntax_rules_stable_identifiers(stable_identifiers or ())
    local_macros = _local_macro_table(bindings, stable_identifiers, procedure)

    return (
        "hissp.macros.._macro_.progn",
        *(_expand_local_macros(form, local_macros) for form in body),
    )


def _internal_syntax_table(forms, stable_identifiers):
    # Build the macro table for a run of internal `define-syntax` forms.
    #
    # Internal syntax definitions are treated like a small `letrec-syntax`: all
    # names are known while constructing the transformers, and all are visible
    # while expanding the remaining body forms. This matches the practical
    # expectation for Scheme body-local macros without mutating Hissp's global
    # macro namespace.
    bindings = tuple((form[1], form[2]) for form in forms)
    return _local_macro_table(bindings, stable_identifiers, "internal define-syntax")


def _split_internal_syntax_definitions(body):
    # Scheme body syntax definitions must appear before expressions in this
    # implementation. Keeping that rule strict gives clear failure modes and
    # keeps expansion predictable while we do not yet implement the full R7RS
    # body-definition grammar.
    syntax_forms = []
    body_forms = []
    scanning_definitions = True

    for form in body:
        if scanning_definitions and _is_define_syntax_form(form):
            syntax_forms.append(form)
            continue

        scanning_definitions = False
        if _is_define_syntax_form(form):
            raise SyntaxError(
                "internal define-syntax must appear before body expressions"
            )
        body_forms.append(form)

    return tuple(syntax_forms), tuple(body_forms)


def _split_internal_runtime_definitions(body):
    definition_forms = []
    body_forms = []
    scanning_definitions = True

    for form in body:
        if scanning_definitions and _is_define_form(form):
            definition_forms.append(form)
            continue

        scanning_definitions = False
        if _is_define_form(form):
            raise SyntaxError("internal define must appear before body expressions")
        body_forms.append(form)

    return tuple(definition_forms), tuple(body_forms)


def _expand_internal_runtime_definitions(body):
    definition_forms, body_forms = _split_internal_runtime_definitions(body)
    if not definition_forms:
        return body

    names = tuple(_definition_name(form) for form in definition_forms)
    if len(set(names)) != len(names):
        raise SyntaxError("duplicate internal define name")

    cells = {name: _new_cell_name(name) for name in names}
    cell_names = tuple(cells.values())
    cell_values = tuple(
        ("hissp_scheme.macro.syntax_rules..cell", "QzHASH_f") for _ in cell_names
    )
    bindings = tuple(
        itertools.chain.from_iterable(builtins.zip(cell_names, cell_values))
    )
    initializers = tuple(
        (
            "hissp_scheme.macro.syntax_rules..cell_set",
            cells[name],
            _rewrite_internal_definition_references(
                _definition_value_form(form), cells
            ),
        )
        for name, form in builtins.zip(names, definition_forms)
    )
    rewritten_body = tuple(
        _rewrite_internal_definition_references(form, cells) for form in body_forms
    )
    return (("hissp.macros.._macro_.let", bindings, *initializers, *rewritten_body),)


def expand_body_definitions(body, stable_identifiers=None):
    # Expand the internal syntax-definition prefix of a body.
    #
    # Body-owning forms in `scheme_base.sld` call this before they lower to
    # Hissp. Runtime definitions remain ordinary body forms; only
    # `define-syntax` is consumed here because it is a compile-time binding.
    stable_identifiers = syntax_rules_stable_identifiers(stable_identifiers or ())
    syntax_forms, body_forms = _split_internal_syntax_definitions(tuple(body))

    if not syntax_forms:
        return _expand_internal_runtime_definitions(body_forms)

    local_macros = _internal_syntax_table(syntax_forms, stable_identifiers)
    expanded_body = tuple(
        _expand_local_macros(form, local_macros) for form in body_forms
    )
    return _expand_internal_runtime_definitions(expanded_body)


def expand_let_syntax(bindings, body, stable_identifiers=None):
    # Expand a Scheme `(let-syntax ((name transformer) ...) body ...)`.
    #
    # The expansion is lexical and non-leaking. For this subset, transformer
    # initializers are syntax-rules data, so there is no runtime initializer
    # scope distinction from `letrec-syntax`; body expansion gets the completed
    # local table.
    return _expand_local_syntax("let-syntax", bindings, body, stable_identifiers)


def expand_letrec_syntax(bindings, body, stable_identifiers=None):
    # Expand a Scheme `(letrec-syntax ((name transformer) ...) body ...)`.
    #
    # All local transformer names are mutually visible while expanding the body.
    # This is the R7RS distinction users care about for recursive/local macro
    # references. Full phase-aware transformer initialization is still outside
    # this subset.
    return _expand_local_syntax("letrec-syntax", bindings, body, stable_identifiers)

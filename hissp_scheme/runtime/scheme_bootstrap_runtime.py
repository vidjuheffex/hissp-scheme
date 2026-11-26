"""Runtime helpers for the minimal Scheme bootstrap macros.

`scheme_bootstrap.hissp` owns the macro surface. This module owns the ordinary
Python helper code those macros call: import-set planning, library export
metadata, source-level include resolution, and Scheme/Python name conversion.

Keeping this as a real Python module gives us normal editor support and avoids
large embedded Python strings inside the Hissp source.
"""

from __future__ import annotations

import ast
import builtins
import importlib
from pathlib import Path

import hissp

from hissp_scheme import names
from hissp_scheme.runtime.symbols import Symbol


current_source_file: str | None = None
currentQzH_sourceQzH_file: str | None = None


def _scheme_py_name(symbol):
    """Convert a Scheme/Hissp symbol spelling to a Python API spelling."""

    return names.demunge(symbol).replace("-", "_")


def _scheme_local_name(name):
    """Convert a Python export name into the local Scheme binding name."""

    return names.munge(name.replace("_", "-"))


def _scheme_public_names(module):
    """Return the public names a bare Python-style import should expose."""

    names = getattr(module, "__all__", None)
    if names is None:
        names = [name for name in dir(module) if not name.startswith("_")]
    return builtins.list(names)


def _scheme_module_name(symbol):
    """Convert a source module symbol to the Python importlib module name."""

    return names.demunge(symbol).replace("-", "_")


def _scheme_source_name(symbol):
    """Convert a reader symbol to the user-facing Scheme source spelling."""

    return names.demunge(symbol)


IMPORT_SET_OPERATORS = {"only", "except", "rename", "prefix"}


def _scheme_library_module_name(spec):
    """Resolve Scheme-shaped library names to generated Python module names."""

    if not isinstance(spec, tuple) or not spec:
        return None

    if names.restore_keyword(spec[0]) in IMPORT_SET_OPERATORS:
        return None

    if spec[0] == "srfi" and len(spec) == 2:
        return f"srfi{spec[1]}"

    if spec[0] == "scheme" and len(spec) >= 2:
        return "scheme_" + "_".join(_scheme_py_name(part) for part in spec[1:])

    return "_".join(_scheme_py_name(part) for part in spec)


def _scheme_export_tables(module):
    """Return value and macro export tables for a Scheme or Python module."""

    value_exports = getattr(module, "__scheme_exports__", None)
    macro_exports = getattr(module, "__scheme_macros__", None)
    if value_exports is None:
        value_exports = {
            _scheme_local_name(name): getattr(module, name)
            for name in _scheme_public_names(module)
        }
    else:
        value_exports = {
            names.munge(name): value for name, value in value_exports.items()
        }

    if macro_exports is None:
        macro_exports = {}
    else:
        macro_exports = {
            names.munge(name): getattr(module._macro_, macro_name)
            for name, macro_name in macro_exports.items()
        }

    return value_exports, macro_exports


def _scheme_import_tables(spec):
    """Return value/macro export tables for an import spec."""

    library_module_name = _scheme_library_module_name(spec)
    if library_module_name is not None:
        module = importlib.import_module(library_module_name)
        return _scheme_export_tables(module)

    module_name = _scheme_module_name(spec)
    module = importlib.import_module(module_name)
    return _scheme_export_tables(module)


def _scheme_import_plan(spec):
    """Return value/macro exports keyed by local Hissp binding names."""

    if isinstance(spec, str) or _scheme_library_module_name(spec) is not None:
        return _scheme_import_tables(spec)

    if not isinstance(spec, tuple) or not spec:
        raise SyntaxError("import spec must be a module name or import set")

    operator = names.restore_keyword(spec[0])
    if operator not in IMPORT_SET_OPERATORS:
        raise SyntaxError(
            f"unknown R7RS library name or import-set operator: "
            f"{names.demunge(operator)}"
        )
    if len(spec) < 2:
        raise SyntaxError(
            f"import set {names.demunge(operator)} requires a nested import set"
        )

    value_exports, macro_exports = _scheme_import_plan(spec[1])

    if operator == "only":
        selected = {names.munge(_scheme_source_name(name)) for name in spec[2:]}
        return (
            {name: value for name, value in value_exports.items() if name in selected},
            {name: value for name, value in macro_exports.items() if name in selected},
        )

    if operator == "except":
        excluded = {names.munge(_scheme_source_name(name)) for name in spec[2:]}
        return (
            {
                name: value
                for name, value in value_exports.items()
                if name not in excluded
            },
            {
                name: value
                for name, value in macro_exports.items()
                if name not in excluded
            },
        )

    if operator == "rename":
        renamed_values = {}
        renamed_macros = {}
        for clause in spec[2:]:
            if not isinstance(clause, tuple) or len(clause) != 2:
                raise SyntaxError("rename clauses must be (old new) pairs")
            old, new = clause
            old_name = names.munge(_scheme_source_name(old))
            new_name = names.munge(_scheme_source_name(new))
            if old_name in value_exports:
                renamed_values[new_name] = value_exports[old_name]
            if old_name in macro_exports:
                renamed_macros[new_name] = macro_exports[old_name]
        return renamed_values, renamed_macros

    if operator == "prefix":
        if len(spec) != 3:
            raise SyntaxError("prefix import set must be (prefix import-set prefix-id)")
        prefix = names.demunge(spec[2])
        return (
            {
                names.munge(prefix + names.demunge(name)): value
                for name, value in value_exports.items()
            },
            {
                names.munge(prefix + names.demunge(name)): value
                for name, value in macro_exports.items()
            },
        )

    raise AssertionError(f"unhandled import-set operator: {names.demunge(operator)}")


def install_import(env, spec):
    """Install an import spec directly into the caller's global environment."""

    value_exports, macro_exports = _scheme_import_plan(spec)
    for local_name, value in value_exports.items():
        env[local_name] = value

    macro_namespace = env.get("_macro_")
    if macro_exports and macro_namespace is None:
        raise SyntaxError("cannot import macros before a prelude creates _macro_")
    for local_name, value in macro_exports.items():
        setattr(macro_namespace, local_name, value)
    return None


def _scheme_export_spec(spec):
    """Return source spellings for one R7RS export spec."""

    spec = _scheme_sequence_to_tuple(spec)
    if isinstance(spec, str):
        source = _scheme_source_name(spec)
        return source, source
    if isinstance(spec, tuple) and len(spec) == 3 and spec[0] == "rename":
        return _scheme_source_name(spec[1]), _scheme_source_name(spec[2])
    raise SyntaxError("export specs must be identifiers or (rename internal external)")


def _scheme_sequence_to_tuple(value):
    """Convert Scheme Pair/list data to Python tuple data for metadata helpers."""

    if isinstance(value, Symbol):
        return names.rename_keyword(str(value))
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    if value == ():
        return ()
    if hasattr(value, "car") and hasattr(value, "cdr"):
        items = []
        while hasattr(value, "car") and hasattr(value, "cdr"):
            items.append(_scheme_sequence_to_tuple(value.car))
            value = value.cdr
        if value != ():
            raise SyntaxError("metadata lists must be proper lists")
        return tuple(items)
    return value


def install_library_exports(env, specs):
    """Register this generated Python module's Scheme library exports."""

    specs = _scheme_sequence_to_tuple(specs)
    value_exports = {}
    macro_exports = {}
    macro_namespace = env.get("_macro_")

    for spec in specs:
        internal_source, external_source = _scheme_export_spec(spec)
        internal_name = names.munge(internal_source)

        if macro_namespace is not None and hasattr(macro_namespace, internal_name):
            macro_exports[external_source] = internal_name
            continue

        if internal_name not in env:
            raise NameError(f"cannot export unbound identifier: {internal_source}")
        value_exports[external_source] = env[internal_name]

    env["__scheme_exports__"] = value_exports
    env["__scheme_macros__"] = macro_exports
    return None


def _scheme_literal_string(value):
    """Parse the reader representation of a Scheme string literal."""

    if not isinstance(value, str):
        raise SyntaxError("include filenames must be string literals")
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        raise SyntaxError("include filenames must be string literals") from None
    if not isinstance(parsed, str):
        raise SyntaxError("include filenames must be string literals")
    return parsed


def _scheme_current_source_dir():
    """Return the directory of the source file currently being compiled."""

    source = currentQzH_sourceQzH_file or current_source_file
    if not source:
        raise SyntaxError("cannot resolve include without a current source file")
    return Path(source).resolve().parent


def _scheme_include_forms(paths):
    """Read source-level include files as unevaluated Scheme forms."""

    from hissp_scheme.reader import read_scheme_source_forms

    forms = []
    base = _scheme_current_source_dir()
    for spec in paths:
        include_path = Path(_scheme_literal_string(spec))
        if not include_path.is_absolute():
            include_path = base / include_path
        forms.extend(read_scheme_source_forms(include_path))
    return forms


def library_form(env, name, clauses):
    """Build the expansion for `(define-library ...)`."""

    exports = []
    forms = []
    seen_exports = set()
    for clause in clauses:
        if not isinstance(clause, tuple) or not clause:
            raise SyntaxError("define-library clauses must be non-empty lists")
        operator, *body = clause
        if operator == "export":
            for export in body:
                internal_source, external_source = _scheme_export_spec(export)
                if external_source in seen_exports:
                    raise SyntaxError(
                        f"duplicate define-library export: {external_source}"
                    )
                seen_exports.add(external_source)
                exports.append(export)
        elif operator == "import":
            # A `define-library` expansion is compiled as one Hissp form. If we
            # only emitted `(import ...)` as the first child form, macros from
            # that import would not be visible while compiling later child
            # forms in the same expansion. Install imports into the active
            # compiler environment immediately, then also emit ordinary import
            # forms so evaluating the generated module has the same bindings.
            for spec in body:
                install_import(env, spec)
            forms.extend(("import", spec) for spec in body)
        elif operator == "begin":
            forms.extend(body)
        elif operator == "include":
            forms.extend(_scheme_include_forms(body))
        elif operator in {"include-ci", "include-library-declarations"}:
            raise SyntaxError(
                f"define-library clause {names.demunge(operator)} is not implemented yet"
            )
        elif operator == "cond-expand":
            raise SyntaxError("define-library cond-expand is not implemented yet")
        else:
            raise SyntaxError(
                f"unsupported define-library clause: {names.demunge(operator)}"
            )

    return (
        "hissp.macros.._macro_.progn",
        *forms,
        (
            "hissp_scheme.runtime.scheme_bootstrap_runtime..install_library_exports",
            ("builtins..globals",),
            ("quote", tuple(exports)),
        ),
    )


def _rest_parameter_name(rest):
    """Return the hidden Python `*args` parameter for a Scheme rest binding."""

    return f"_Qzscheme_rest_{rest}"


def _split_formals(formals):
    """Parse R7RS-style lambda formals.

    Hissp ultimately lowers functions to Python functions, so dotted or
    variadic Scheme formals must use a Python `*args` parameter internally.
    The user-visible rest binding is installed separately as a Scheme list.
    """

    if isinstance(formals, str):
        return (), formals

    if not isinstance(formals, tuple):
        raise SyntaxError("formals must be a list")
    if "." not in formals:
        return formals, None
    dot_index = formals.index(".")
    if dot_index != len(formals) - 2:
        raise SyntaxError("dotted formals must end with . rest")
    rest = formals[-1]
    if not isinstance(rest, str):
        raise SyntaxError("rest formal must be an identifier")
    return formals[:dot_index], rest


def scheme_formals(formals):
    """Convert Scheme formals to the Python/Hissp lambda parameter shape."""

    positional, rest = _split_formals(formals)
    if rest is None:
        return positional
    return (*positional, f"*{_rest_parameter_name(rest)}")


def scheme_body(formals, body):
    """Wrap a body so Scheme rest parameters are proper Pair lists.

    Python receives varargs as tuples. R7RS rest parameters are lists. This
    inserts one local binding at function entry, converting the hidden Python
    tuple into the public Scheme rest variable.
    """

    _, rest = _split_formals(formals)
    if rest is None:
        return body
    return (
        (
            "hissp.macros.._macro_.let",
            (rest, ("scheme_pairs..py_to_list", _rest_parameter_name(rest))),
            *body,
        ),
    )


def field_name(symbol):
    """Convert a Scheme field symbol to a Python attribute name."""

    if not isinstance(symbol, str):
        raise SyntaxError("field names must be symbols")
    return _scheme_py_name(symbol)


installQzH_import = install_import
installQzH_libraryQzH_exports = install_library_exports
libraryQzH_form = library_form
schemeQzH_includeQzH_forms = _scheme_include_forms
schemeQzH_formals = scheme_formals
schemeQzH_body = scheme_body
fieldQzH_name = field_name

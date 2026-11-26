"""Scheme reader extensions for this project.

The important boundary in this repo is:

    Lissp source text -> reader -> Hissp forms -> compiler -> Python

Most of the Scheme surface is implemented as normal Hissp macros in
`src/scheme_base.sld`. A macro can only see forms after the reader has already
parsed tokens, though. That means reader-level conflicts cannot be solved by
ordinary prelude bindings.

The concrete conflict that forced this file is SRFI-1's `list=` procedure.
Raw Hissp uses a trailing `=` token for keyword-argument syntax:

    (foo x= 1)  ; roughly foo(x=1)

So bare `(list= = xs ys)` is not read as "call the symbol `list=`"; the first
token becomes a `Kwarg(k='list', v='=')`. By the time macros run, the damage is
done. This wrapper keeps Hissp behavior everywhere except the one context where
Scheme needs a trailing-`=` symbol: operator position.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePath

from hissp.reader import Comment, Kwarg, Lexer, Lissp, Parser, _Unquote


SCHEME_PRELUDE_TAG = "scheme..prelude#:"
SCHEME_BOOTSTRAP_PRELUDE_TAG = "scheme_bootstrap..prelude#:"
SCHEME_PRELUDE_TAGS = (SCHEME_PRELUDE_TAG, SCHEME_BOOTSTRAP_PRELUDE_TAG)
SCHEME_SOURCE_SUFFIXES = {".scm", ".sld"}


def _uses_scheme_language(code: str, filename: str | None = None) -> bool:
    """Return true when source should use Scheme reader semantics."""

    return _is_scheme_source_filename(filename) or any(
        tag in code for tag in SCHEME_PRELUDE_TAGS
    )


def _is_scheme_source_filename(filename: str | None) -> bool:
    """Return true for ordinary Scheme source files."""

    return bool(filename and Path(filename).suffix in SCHEME_SOURCE_SUFFIXES)


def _needs_implicit_scheme_prelude(code: str, filename: str | None = None) -> bool:
    """Return true when a `.scm`/`.sld` file needs the reader prelude injected."""

    return _is_scheme_source_filename(filename) and not any(
        tag in code for tag in SCHEME_PRELUDE_TAGS
    )


def _set_current_source_file(path: Path) -> None:
    """Tell bootstrap macros which source file is currently compiling.

    Hissp macros run as Python functions in the module where they were defined,
    so the bootstrap runtime cannot infer the caller's source path from Python
    globals. `define-library` and top-level `include` need that path for R7RS
    include resolution relative to the containing source file.
    """

    try:
        from hissp_scheme.runtime import scheme_bootstrap_runtime
    except (ModuleNotFoundError, SyntaxError):
        # The bootstrap module itself is being generated; it does not use
        # `define-library`, so no include resolution is needed yet. SyntaxError
        # covers stale generated bootstrap modules from a previous bad compile.
        return

    scheme_bootstrap_runtime.currentQzH_sourceQzH_file = str(path)


def read_scheme_source_forms(path: Path | str) -> tuple:
    """Read a Scheme source fragment as forms without evaluating it."""

    path = Path(path).resolve(strict=True)
    reader = SchemeLissp(evaluate=False, filename=str(path))
    reader.scheme_quote_lists = True
    return tuple(reader.reads(re.sub(r"^#!.*\n", "", path.read_text("utf8"))))


def _quote_atom(form):
    """Return a runtime expression for one quoted Scheme atom."""

    if type(form) is Kwarg and form.v in {"QzQUERY_", "?"}:
        return ("quote", f"{form.k}QzEQ_QzQUERY_")
    if isinstance(form, str):
        return ("quote", form)
    return form


def _scheme_quote(form):
    """Lower quoted list-shaped reader data into core `Pair` constructors.

    Hissp quote turns quoted parenthesized forms into Python tuples. Scheme
    quote should instead produce Scheme list structure. This function converts:

        '(1 2 3)     -> (scheme_pairs.cons 1 (scheme_pairs.cons 2 ...))
        '(1 2 . 3)   -> (scheme_pairs.cons 1 (scheme_pairs.cons 2 3))
        'symbol      -> ordinary Hissp quoted symbol

    The empty list remains Python's empty tuple `()`, which is already the
    empty-list sentinel used by `src/scheme_pairs.sld`.
    """

    if not isinstance(form, tuple):
        return _quote_atom(form)

    if not form:
        return ()

    if len(form) >= 3 and form[-2] == ".":
        tail = _scheme_quote(form[-1])
        items = form[:-2]
    elif "." in form:
        raise SyntaxError("dot may only appear before the final tail in quoted lists")
    else:
        tail = ()
        items = form

    result = tail
    for item in reversed(items):
        result = ("scheme_pairs..cons", _scheme_quote(item), result)
    return result


def _scheme_list_expr(items, tail=()):
    """Build a `Pair` expression from already-lowered item expressions."""

    result = tail
    for item in reversed(items):
        result = ("scheme_pairs..cons", item, result)
    return result


def _scheme_quasiquote(form, *, in_list=False):
    """Lower Scheme quasiquote into runtime Pair construction.

    Hissp's reader already recognizes backtick, comma, and comma-at, but its
    default semantics are macro-template semantics. For Scheme source files
    we reinterpret the raw template payload as runtime list construction:

        `(1 ,x 3)    -> (cons 1 (cons x (cons 3 ())))
        `(1 ,@xs 4)  -> (append (list 1) xs (list 4))

    Splicing is only valid inside list context.
    """

    if type(form) is _Unquote:
        if form.target == ":?":
            return form.value
        if form.target == ":*":
            if in_list:
                return form
            raise SyntaxError("unquote-splicing not in list")
        raise SyntaxError(f"unsupported unquote target: {form.target}")

    if not isinstance(form, tuple):
        return _quote_atom(form)

    if not form:
        return ()

    if len(form) >= 3 and form[-2] == ".":
        tail = _scheme_quasiquote(form[-1])
        items = form[:-2]
    elif "." in form:
        raise SyntaxError(
            "dot may only appear before the final tail in quasiquoted lists"
        )
    else:
        tail = ()
        items = form

    segments = []
    normal_items = []
    saw_splice = False

    def flush_normal_items():
        if normal_items:
            segments.append(_scheme_list_expr(normal_items))
            normal_items.clear()

    for item in items:
        lowered = _scheme_quasiquote(item, in_list=True)
        if type(lowered) is _Unquote and lowered.target == ":*":
            saw_splice = True
            flush_normal_items()
            segments.append(lowered.value)
        else:
            normal_items.append(lowered)

    if not saw_splice:
        return _scheme_list_expr(normal_items, tail)

    flush_normal_items()
    if tail != ():
        segments.append(tail)
    if not segments:
        return ()
    if len(segments) == 1:
        return segments[0]
    return ("scheme_pairs..scheme_append", *segments)


def _scheme_form(form):
    """Rewrite parsed forms that need Scheme-level reader semantics."""

    if type(form) is Kwarg and form.v in {"QzQUERY_", "?"}:
        return f"{form.k}QzEQ_QzQUERY_"

    if (
        isinstance(form, tuple)
        and len(form) == 2
        and form[0] == "quote"
        and isinstance(form[1], tuple)
    ):
        return _scheme_quote(form[1])

    def rewrite_lambda_forms(value):
        # Only lambda needs recursive source rewriting. Do not recursively apply
        # quote lowering here: quasiquote already returns executable constructor
        # forms, and ordinary quoted data must stay data.
        if type(value) is Kwarg and value.v in {"QzQUERY_", "?"}:
            return f"{value.k}QzEQ_QzQUERY_"
        if type(value) is _Unquote or type(value) is Kwarg:
            return value
        if not isinstance(value, tuple):
            return value
        if value and value[0] == "quote":
            return value
        value = tuple(rewrite_lambda_forms(item) for item in value)
        value = _collapse_question_suffix_symbols(value)
        if value and value[0] == "lambda":
            return ("schemeQzH_lambda", *value[1:])
        return value

    return rewrite_lambda_forms(form)


def _collapse_question_suffix_symbols(items: tuple) -> tuple:
    """Recover `name=?`-style identifiers split by Hissp's kwarg reader."""

    result = []
    index = 0
    while index < len(items):
        item = items[index]
        if (
            index + 1 < len(items)
            and isinstance(item, str)
            and item.endswith("QzEQ_")
            and items[index + 1] == "QzQUERY_"
        ):
            result.append(f"{item}QzQUERY_")
            index += 2
        else:
            result.append(item)
            index += 1
    return tuple(result)


class SchemeParser(Parser):
    """Parser variant that recovers trailing-`=` symbols in call position.

    Hissp's parser represents `name=` as `Kwarg("name", next_form)`. That is
    correct for argument position, but wrong for Scheme procedure names such as
    `list=`.

    This override intentionally makes the smallest possible change:

    - If the first form inside parentheses is a `Kwarg`, treat it as a callable
      symbol ending in `=`.
    - Leave all other `Kwarg` forms untouched so ordinary Hissp keyword syntax
      still works outside operator position.

    Example:

        (list= = xs ys)

    Raw Hissp sees:

        (Kwarg(k="list", v="QzEQ_"), "xs", "ys")

    Scheme rewrites that to:

        ("listQzEQ_", "QzEQ_", "xs", "ys")

    That is the normal munged symbol for `list=`, followed by the comparator
    `=` and the list arguments.
    """

    def _open(self) -> tuple:
        # Delegate normal parenthesized-form parsing to Hissp first. This keeps
        # comments, nesting, quote/template behavior, reader tags, and ordinary
        # keyword forms exactly as Hissp defines them.
        form = super()._open()

        # Only repair operator position. `(foo x= 1)` still contains a Kwarg in
        # argument position and remains Hissp keyword syntax. `(list= = xs ys)`
        # has the Kwarg as the operator, so we reinterpret it as a Scheme
        # symbol name ending in `=`. Hissp also splits identifiers like
        # `string=?` as `string=` followed by `?`; in operator position that is
        # a single Scheme identifier, not a procedure plus an extra formal.
        if form and type(form[0]) is Kwarg:
            kwarg = form[0]
            if kwarg.v in {"QzQUERY_", "?"}:
                return (f"{kwarg.k}QzEQ_QzQUERY_", *form[1:])
            return (f"{kwarg.k}QzEQ_", kwarg.v, *form[1:])

        return form

    def _template(self, v: str):
        if not getattr(self.lissp, "scheme_quote_lists", False):
            return super()._template(v)
        with self.gensym_context():
            return _scheme_quasiquote(self._pull(v))

    def _parse(self):
        if not getattr(self.lissp, "scheme_quote_lists", False):
            yield from super()._parse()
            return

        for k, v, self._pos in self.tokens:
            if k == "whitespace":
                continue
            if k == "comment":
                form = Comment(v)
            elif k == "badspace":
                raise self._badspace(v)
            elif k == "open":
                form = self._open()
            elif k == "close":
                return self._close()
            elif k == "template":
                form = self._template(v)
            elif k == "unquote":
                form = self._unquote(v)
            elif k == "quote":
                form = "quote", self._pull(v)
            elif k == "inject":
                form = self._inject(v)
            elif k == "discard":
                self._pull(v)
                continue
            elif k == "gensym":
                form = self._gensym(self._pull(v))
            elif k == "tag":
                form = self._tag(self._pull(v), v)
            elif k == "unicode":
                form = self._unicode(v)
            elif k == "fragment":
                form = self._fragment(v)
            elif k == "continue":
                raise self._continue()
            elif k == "badfrag":
                raise SyntaxError("unpaired |", self.position())
            elif k == "control":
                form = self.escape(v)
            elif k == "bare":
                form = self.bare(v)
            elif k == "error":
                raise self._error(k)
            else:
                # Scheme has ordinary identifiers that end in `=`, such as
                # SRFI-1's `list=` and `lset=`. Hissp reserves trailing `=` for
                # Python keyword syntax. Scheme code uses SRFI-177 `call/kw`
                # instead, so inside Scheme files a trailing `=` token is a
                # symbol everywhere, not a Python keyword marker.
                form = self.bare(v)

            if getattr(self.lissp, "scheme_quote_lists", False):
                form = _scheme_form(form)
            yield form
        self._check_depth()


class SchemeLissp(Lissp):
    """A `Lissp` reader/compiler facade using `SchemeParser`.

    Hissp's public `Lissp` class already separates `reads` from `parse`, so we
    can swap only the parser class without monkeypatching the global Hissp
    package. Code that imports Hissp directly remains unchanged; only our
    launcher opts into this dialect.
    """

    def parse(self, tokens: Lexer) -> SchemeParser:
        return SchemeParser(self, tokens)

    def compile(self, code: str) -> str:
        previous = getattr(self, "scheme_quote_lists", False)
        self.scheme_quote_lists = _uses_scheme_language(code, self.filename)
        if self.filename:
            _set_current_source_file(Path(self.filename))
        if _needs_implicit_scheme_prelude(code, self.filename):
            code = f"{SCHEME_PRELUDE_TAG}\n{code}"
        try:
            return super().compile(code)
        finally:
            self.scheme_quote_lists = previous


def transpile_scheme_file(
    path: Path | str,
    package: str | None = None,
    output_dir: Path | str | None = None,
) -> Path:
    """Transpile one Scheme or Hissp-bridge source file with the Scheme reader.

    This mirrors `hissp.reader.transpile_file`, but uses `SchemeLissp`.
    Keeping a local copy matters because support modules need the same reader
    rules as the entrypoint. Otherwise `main.scm` could understand `list=`
    while `(scheme base)` or `terrain_app.sld` could not.

    Hissp compilation evaluates top-level forms because macros can affect later
    forms in the same file. This is normal for Hissp, but it also means modules
    should avoid top-level application side effects. `terrain_app.sld`
    therefore defines `(run)` instead of launching Ursina during transpilation.
    """

    # Resolve strictly so generated `.py` files always sit next to a real source
    # file, matching Hissp's own transpiler behavior.
    path = Path(path).resolve(strict=True)
    _set_current_source_file(path)

    # Hissp uses the module qualname during macro qualification and gensym
    # generation. For `src/foo.sld`, the default qualname is `foo`.
    qualname = f"{package or ''}{'.' if package else ''}{PurePath(path.name).stem}"

    # `evaluate=True` is required for files defining macros or reader tags:
    # later forms may depend on earlier macro definitions having run.
    reader = SchemeLissp(qualname=qualname, evaluate=True, filename=str(path))
    reader.env["__file__"] = str(path)

    # Preserve the standard shebang-stripping behavior from Hissp's transpiler.
    python = reader.compile(re.sub(r"^#!.*\n", "", path.read_text("utf8")))

    # The generated Python is an implementation artifact. `.gitignore` keeps it
    # out of source control for project-owned Lissp modules.
    if output_dir is None:
        py = path.with_suffix(".py")
    else:
        py = Path(output_dir).resolve()
        py.mkdir(parents=True, exist_ok=True)
        py = py / f"{path.stem}.py"
    py.write_text(python, "utf8")

    # Point generated modules at the generated Python path after compilation.
    # During compilation, `__file__` intentionally points at the source file so
    # macros such as `define-library` can resolve source-relative includes.
    reader.env["__file__"] = str(py)
    return py

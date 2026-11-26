# Hissp Scheme

This package is a Scheme-flavored language layer on top of
[Hissp](https://github.com/gilch/hissp). It provides the reader, bootstrap
runtime, R7RS-shaped core libraries, and implemented SRFIs used by consumer
apps.

Consumer projects depend on this Python package, but Scheme imports stay clean:

```scheme
(import (scheme base)
        (srfi 64))
```

There is no extra bundle namespace in Scheme source.

## Running Tests

```sh
uv run scheme-test
```

## REPL

```sh
uv run scheme-repl
```

The REPL builds the bundled libraries into `.scheme-build`, imports
`(scheme base)`, and evaluates Scheme forms interactively. Use `--no-base` to
start with only the bootstrap language, or `--show-python` to echo compiled
Python before each form is evaluated.

## Repository Layout

```text
hissp_scheme/
  reader.py          Scheme-aware Hissp reader/transpiler
  scheme/            bundled `(scheme ...)` source libraries
  srfi/              bundled `(srfi ...)` source libraries
  runtime/           Python runtime helpers used by Scheme libraries
  macro/             macro expander implementation helpers
  test.py            package test runner
tests/               Scheme/SRFI/compiler test suites
```

Consumer apps should call `hissp_scheme.core_library_files()` to get the core
libraries in dependency order, then transpile them into the app's own build
cache. Generated module names remain flat (`scheme_base`, `srfi64`, etc.) so
R7RS-style imports continue to resolve as `(scheme base)` and `(srfi 64)`.

## Language Stack

The language is intentionally layered:

```text
scheme_bootstrap
macro/syntax_rules
scheme_pairs
scheme
scheme_base
scheme/srfi library modules
consumer app/tests
```

`hissp_scheme/scheme/scheme_bootstrap.hissp` is the minimal Hissp bridge. It
defines only the bootstrap syntax needed to import libraries and compile
Scheme-shaped source.

`hissp_scheme/runtime/scheme_bootstrap_runtime.py` contains the ordinary Python
helpers used by the bootstrap macros: import-set planning, library export
metadata, include resolution, and Scheme/Python name conversion. It is kept as
normal Python for editor support and direct testing.

`hissp_scheme/macro/syntax_rules.py` implements the macro expander used by the
rest of the language: R7RS-style `syntax-rules` plus a small `syntax-case`
procedural transformer hook for macros that must compute target forms.

`hissp_scheme/macro/tail.py` builds Scheme procedures and marks tail
positions. `hissp_scheme/runtime/control_runtime.py` holds the matching
runtime: the tail-call trampoline, escape continuations, `dynamic-wind`, the
exception-handler stack, multiple values, and parameter objects.

`hissp_scheme/scheme/scheme_pairs.sld` owns the core `Pair` runtime,
fundamental list procedures, and the Python-list-backed vector substrate used
by `(scheme base)`.

`hissp_scheme/scheme/scheme.sld` is the public reader/prelude module injected
for `.sld` and `.scm` files. It does not install base.

`hissp_scheme/scheme/scheme_base.sld` is the explicit `(scheme base)` library.
It installs core syntax, the macro system, fundamental pair/list bindings, and
R7RS vector procedures.

`hissp_scheme/scheme/scheme_python.sld` is the explicit `(scheme python)`
interop library. It owns conversion helpers for Python-native dictionaries,
tuples, Python lists, and runtime attribute access. It is not a Python prelude
and it does not re-export SRFI libraries.

## Imports

`.sld` and `.scm` files are read as Scheme source automatically. The base
language, SRFIs, and optional libraries must be imported explicitly:

```scheme
(import (scheme base))
(import (srfi 1))
(import (srfi 18))
(import (srfi 28))
(import (srfi 64))
(import (srfi 69))
(import (srfi 177))
(import (scheme write))
(import (scheme read))
(import (scheme file))
(import (scheme string))
(import (scheme python))
```

The import macro also supports R7RS-style import sets for Scheme libraries and
Python modules:

```scheme
(import (only (srfi 64) test-begin test-end test-equal))
(import (rename (srfi 177) (call/kw call-with-keywords)))
(import (prefix json json-))
```

Scheme libraries declare their public surface with R7RS-shaped
`(define-library ...)` and `(export ...)` forms. The import layer installs both
value exports and macro exports into the caller, so SRFI macros live with their
SRFI modules instead of being hidden inside the base prelude.

Supported library clauses are `export`, `import`, `begin`, and `include`.
`include` splices source forms from files relative to the containing `.sld` or
`.scm` file before compilation. This is source composition, not module import;
use `import` when you want another compiled library/module.

`include-ci`, `include-library-declarations`, and `cond-expand` currently fail
with explicit errors instead of silently doing the wrong thing.

## SRFIs

Currently implemented:

`(srfi 1)` provides list-library extensions on top of the base `Pair` runtime.

`(srfi 18)` provides multithreading support: threads, mutexes, condition
variables, time objects, exception handlers, and SRFI-18 exception predicates.
The public API is Scheme source, backed by
`hissp_scheme/runtime/srfi18_runtime.py` because OS threads and synchronization
primitives must use CPython runtime facilities. Forced termination of another
already-running thread raises an explicit `NotImplementedError`; CPython cannot
safely kill arbitrary running threads.

`(srfi 28)` provides `format`.

`(srfi 64)` provides the test runner API and test macros such as `test-group`,
`test-equal`, and `test-error`. Its macros are written with `syntax-rules`.

`(srfi 69)` provides basic hash tables backed by Python dictionaries. Use it
for Scheme-level mutable maps instead of Hissp `%` literals or direct Python
`.get`/`.update` calls.

`(srfi 177)` provides keyword-call syntax: `call/kw`, `lambda/kw`, and
`define/kw`. Its macros are owned by the SRFI module and installed with
`define-syntax` using the `syntax-case` transformer hook.

The SRFI modules are written as Scheme libraries using a single
`(define-library ...)` form. Base dependencies are declared in the library's
own `(import (scheme base))` clause; no duplicate top-level base import is
required. Runtime procedures and macro surfaces are implemented in Scheme
source and exported from the owning SRFI module. Bootstrap, reader, Pair, and
macro-expander internals still use Python where they are implementing the
language substrate itself.

## R7RS Status

Implemented or usable:

- Library/import surface: `define-library`, `export`, `import`, `only`,
  `except`, `rename`, `prefix`, and source-level `include`.
- Explicit base import: `.sld` and `.scm` files enable the reader
  automatically, then use `(import (scheme base))` to opt into the base
  language.
- R7RS-style I/O split: `(scheme write)` provides `display`, `write`, and
  `newline`; `(scheme read)` provides `read-line`; `(scheme file)` provides
  R7RS file procedures such as `open-input-file`, `call-with-output-file`,
  `file-exists?`, and `delete-file`.
- `(scheme string)` provides immutable string procedures over Python `str`,
  with characters represented as one-character strings.
- `(scheme python)` provides Python interop helpers such as `dict->hash-table`,
  `hash-table->dict`, `tuple->list`, `list->tuple`, `dict-ref`, `dict-set!`,
  `attribute-ref`, and `attribute-set!`.
- Base syntax: `define`, `lambda`, `begin`, `if`, `let`, named `let`, `let*`,
  `letrec`, `letrec*`, `do`, `set!`, `and`, `or`, `when`, `unless`, `cond`,
  and `case`. `set!` on a local variable rebinds that local; internal
  `define` stays local to its body.
- Proper tail calls: a call in tail position of a procedure body (including
  the last form of `if`, `begin`, `let`-family bodies, `cond`, `case`, `and`,
  `or`, `when`, `unless`, and `do`) doesn't grow the Python stack. Self, mutual,
  and higher-order tail calls all run in constant stack space.
- Control: `call/cc` and `call-with-current-continuation` (escape-only, see
  below), `dynamic-wind`, `values`, `call-with-values`, `apply`, and
  `procedure?`.
- Exceptions: `raise`, `raise-continuable`, `with-exception-handler`, `guard`,
  `error`, `error-object?`, `error-object-message`, `error-object-irritants`,
  `file-error?`, and `read-error?`. Python exceptions raised by primitives
  (for example the `TypeError` from `(car 1)`) are delivered to Scheme handlers
  and `guard` clauses like any raised object.
- Parameters: `make-parameter` and `parameterize`.
- Macro system: `define-syntax`, `syntax-rules`, `let-syntax`,
  `letrec-syntax`, and the internal `syntax-case` hook used for procedural
  transformers.
- Data basics: booleans, quoted/quasiquoted Scheme lists, mutable pairs, core
  selectors/mutators, common list procedures, and mutable vectors.
- Rest parameters: dotted and variadic `define`/`lambda` forms bind Scheme
  `Pair` lists, not Python tuples.
- SRFI modules: `(srfi 1)`, `(srfi 18)`, `(srfi 28)`, `(srfi 64)`,
  `(srfi 69)`, and `(srfi 177)`.

Partial or intentionally explicit errors:

- `case` compares with the current Python/Scheme equality behavior, not a full
  R7RS numeric/character `eqv?` lattice.
- SRFI-18 maps to CPython threads. Joining, sleeping, mutexes, condition
  variables, timeouts, and thread-local specific fields are implemented; safe
  forced termination of another live running thread is not available on CPython
  and fails explicitly.
- `include-ci`, `include-library-declarations`, and `cond-expand` currently
  raise explicit errors.
- `call/cc` is escape-only. A continuation works while its `call/cc` is still
  running (early exit, breaking out of loops, non-local return). Invoking it
  after that `call/cc` has returned, or from another thread, raises
  `ContinuationError`. Generators and coroutines built on re-entering
  continuations aren't supported.
- The procedure passed to `call/cc` isn't called in tail position, because the
  frame that catches the escape has to stay live.
- Non-tail recursion still uses the Python stack, at a few Python frames per
  Scheme call. Importing the runtime raises Python's recursion limit to
  100,000, which allows non-tail recursion roughly 20,000 calls deep.
- Tail calls that pass Python keyword arguments (for example through SRFI-177
  `call/kw`) run as ordinary Python calls.
- Local `set!` is detected from `set!` forms written in the variable's scope.
  A macro that expands into `set!` of a caller's local variable isn't detected,
  and assigns a module-level variable instead.
- Scheme procedures are Python functions that run a small trampoline. Expect
  call-heavy non-tail code (such as naive `fib`) to run roughly 1.5x slower
  than plain Python lambdas would.
- Python keywords such as `return` can't be used as variable names.
- SRFI-18 `raise` keeps SRFI-18's behavior of returning the handler's value,
  but it shares the handler stack with `(scheme base)`, so either library's
  handlers see the other's raises.

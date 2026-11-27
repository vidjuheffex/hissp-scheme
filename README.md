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

`hissp_scheme/macro/derived.py` holds the procedural transformers for
`define-record-type`, `define-values`, `let-values`, `let*-values`,
`cond-expand`, `include-ci`, and `syntax-error`. The body expander also calls
it, so the definition forms define locals when they appear in a body.

`hissp_scheme/runtime/base_runtime.py` implements the `(scheme base)` numeric
tower, `eqv?`/`equal?`, and the R7RS list procedures. `runtime/ports.py` has
the port procedures, `runtime/bytevectors.py` the bytevector procedures,
`runtime/records.py` the record types, and `runtime/features.py` the
`features`/`cond-expand` feature list. `runtime/symbols.py` defines the
`Symbol` type, `runtime/printer.py` the `write`/`display` notation, and
`hissp_scheme/names.py` the spelling used for identifiers that are Python
keywords.

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
(import (srfi 132))
(import (srfi 177))
(import (scheme write))
(import (scheme inexact))
(import (scheme read))
(import (scheme file))
(import (scheme char))
(import (scheme cxr))
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

Supported library clauses are `export`, `import`, `begin`, `include`,
`include-ci`, `include-library-declarations`, and `cond-expand`. `include`
splices source forms from files relative to the containing `.sld` or `.scm`
file before compilation. This is source composition, not module import; use
`import` when you want another compiled library/module. `include-ci` folds
identifier case (not strings or characters) in the included forms.

`include`, `include-ci`, and `cond-expand` also work in programs, at top level
and in bodies. Feature requirements can test feature identifiers from
`(features)` (`r7rs`, `ratios`, `full-unicode`, `python`, `srfi-1`, the OS and
CPU, ...), `(library (srfi 1))`, and `and`/`or`/`not`.

## SRFIs

Currently implemented:

`(srfi 1)` provides the full SRFI-1 list library (`any`, `every`, `find`,
`fold-right`, `reduce`, `partition`, `delete-duplicates`, the `lset-*` set
operations, and the rest) on top of the base `Pair` runtime, backed by
`hissp_scheme/runtime/srfi1_runtime.py`. The procedures it shares with
`(scheme base)` and `(scheme cxr)` are re-exported from there. The
linear-update `!` procedures are the same as their pure versions, which SRFI-1
permits.

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

`(srfi 132)` provides the full sort library: `list-sort`, `vector-sort`,
`vector-sort!`, merging, neighbor-duplicate deletion, median finding, and
selection. Sorting is backed by Python's Timsort through
`hissp_scheme/runtime/srfi132_runtime.py`; Timsort is stable, so every sort is
stable and the `stable` variants are aliases. Note SRFI-132's argument order:
the comparator comes first, except for `vector-sort!` and `vector-stable-sort!`,
which take the vector first.

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
- Ports: ports are Python file objects. Base has the current ports
  (`current-input-port`, `current-output-port`, `current-error-port`, which are
  parameters defaulting to `sys.stdin`/`stdout`/`stderr`, so `parameterize`
  redirects output), port predicates, `close-port` and friends,
  `call-with-port`, `flush-output-port`, string ports (`open-input-string`,
  `open-output-string`, `get-output-string`), bytevector ports, `read-char`,
  `peek-char`, `read-line`, `read-string`, `char-ready?`, `write-char`,
  `write-string`, `newline`, the binary `read-u8`/`peek-u8`/`u8-ready?`/
  `read-bytevector`/`read-bytevector!`/`write-u8`/`write-bytevector`, and
  `eof-object`/`eof-object?`. `(scheme write)` provides `display` and `write`,
  defaulting to the current output port. `(scheme read)` provides `read`,
  which parses one datum from a port into the same values `quote` builds
  (including `#|...|#` and `#;` comments, `|symbols|`, datum labels, and
  `#!fold-case`), leaving the rest of the port unread; read errors satisfy
  `read-error?`. It also re-exports `read-line`; as an extension,
  `(read-line "prompt> ")` writes a prompt first. `(scheme file)` provides R7RS file procedures such as
  `open-input-file`, `call-with-output-file`, `file-exists?`, and
  `delete-file`.
- Bytevectors: `bytevector`, `bytevector?`, `make-bytevector`,
  `bytevector-u8-ref`/`-set!`, `bytevector-length`, `bytevector-copy`,
  `bytevector-copy!`, `bytevector-append`, `utf8->string`, and
  `string->utf8`. Bytevectors are Python `bytearray` and print as `#u8(...)`.
- Literals: vector literals `#(1 a "s")` and bytevector literals
  `#u8(1 2 255)`, including inside quoted data and quasiquote (`` `#(a ,x) ``).
- Records: `define-record-type`, at top level or in a body. Each record type
  is a Python class with one slot per field; instances print as
  `#<point x: 1 y: 2>`. The constructor may also be `#f` (none) or a bare name
  (all fields in order).
- Multiple-value bindings: `define-values`, `let-values`, and `let*-values`,
  with fixed, dotted, and identifier formals.
- `syntax-error` (raises a `SyntaxError` at expansion time), `features`, and
  `rationalize`.
- Strings and characters: `(scheme base)` has the R7RS string and character
  procedures (`string?`, `string-append`, `substring`, `string=?` and the
  other comparisons, `string->list`, `string-map`, `char?`, `char->integer`,
  and so on). `(scheme char)` has case conversion and character classes
  (`char-upcase`, `string-downcase`, `char-alphabetic?`, `string-ci=?`,
  `digit-value`, ...). Strings are immutable Python `str`, so `string-set!`,
  `string-copy!`, and `string-fill!` raise `TypeError`. Characters are
  one-character strings, written `#\a`, `#\space`, or `#\x41`.
- `(scheme python)` provides Python interop helpers such as `dict->hash-table`,
  `hash-table->dict`, `tuple->list`, `list->tuple`, `dict-ref`, `dict-set!`,
  `attribute-ref`, and `attribute-set!`.
- Base syntax: `define`, `lambda`, `begin`, `if`, `let`, named `let`, `let*`,
  `letrec`, `letrec*`, `do`, `set!`, `and`, `or`, `when`, `unless`, `cond`,
  and `case`. `set!` on a local variable rebinds that local; internal
  `define` stays local to its body. A top-level `begin` defines globals, and
  a `begin` directly in a body splices its definitions into that body.
- Booleans: only `#f` is false. `0`, `""`, and `'()` are true, as in R7RS.
  `not`, `boolean?`, and `boolean=?` are in base.
- Identifiers: Python keywords such as `return`, `class`, and `in` work as
  ordinary Scheme variable names.
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
  transformers. Quoted data in a `syntax-rules` template keeps its symbols as
  written (`'(tag x)` expands to the symbol `tag`, with `x` substituted).
- Data basics: booleans, quoted/quasiquoted Scheme lists, mutable pairs, core
  selectors/mutators, and mutable vectors. `(scheme base)` has the two-level
  accessors (`cadr`, `cddr`, ...); `(scheme cxr)` has the three- and
  four-level ones (`caddr`, `cadddr`, ...). Quoted data keeps string literals
  as strings, so `'("x" y)` is a list of a string and a symbol.
- Symbols: a distinct, interned `Symbol` type (a `str` subclass, for Python
  interop) with `symbol?`, `symbol->string`, `string->symbol`, and `symbol=?`.
  `string?` is false for symbols and `equal?` doesn't conflate them with
  strings.
- Equivalence: R7RS `eq?`, `eqv?` (exactness-aware for numbers), and
  `equal?` (structural over pairs, vectors, and strings). `case` uses `eqv?`.
- Numbers: exact integers and rationals (`fractions.Fraction`, reader syntax
  `1/2`), inexact floats and complex numbers, `+inf.0`/`-inf.0`/`+nan.0`, and
  `#x`/`#b`/`#o`/`#e`/`#i` prefixes. `/` of exact numbers stays exact.
  Arithmetic and comparisons are variadic. Base has the R7RS numeric
  procedures (`exact`, `inexact`, `quotient`, `floor/`, `exact-integer-sqrt`,
  `number->string`, `string->number`, and the rest); `(scheme inexact)` has
  `sqrt`, `exp`, `log`, the trigonometric functions, `nan?`, `infinite?`, and
  `finite?`.
- A list procedure given a non-list says so (`length` of a Python list
  suggests `vector-length`), rather than reporting a dotted tail.
- Lists: `map` and `for-each` (over several lists), `memq`/`memv`/`member`,
  `assq`/`assv`/`assoc`, `list?`, `make-list`, `list-tail`, `list-set!`,
  `list-copy`, `vector-map`, and `vector-for-each`.
- Printing: `write`, `display`, and the REPL use Scheme notation (`#t`,
  `"str"`, `1/2`, `#(1 2)`, `(a . b)`).
- Rest parameters: dotted and variadic `define`/`lambda` forms bind Scheme
  `Pair` lists, not Python tuples.
- SRFI modules: `(srfi 1)`, `(srfi 18)`, `(srfi 28)`, `(srfi 64)`,
  `(srfi 69)`, `(srfi 132)`, and `(srfi 177)`.

Partial or intentionally explicit errors:

- Numeric procedures stay generic over Python operators, so `(+ "a" "b")`
  concatenates and `=` compares any two values with `==` instead of raising
  for non-numbers.
- Characters are one-character strings, so `eqv?` can't tell `#\a` from
  `"a"`.
- SRFI-18 maps to CPython threads. Joining, sleeping, mutexes, condition
  variables, timeouts, and thread-local specific fields are implemented; safe
  forced termination of another live running thread is not available on CPython
  and fails explicitly.
- `peek-char` and `peek-u8` keep the peeked item in a per-port buffer that the
  Scheme reading procedures consume first. Reading the same port through
  Python methods directly skips that buffer.
- Characters are one-character strings, so `read` returns the same value for
  `#\a` and `"a"`, and `write` prints characters as strings.
- `call/cc` is escape-only. A continuation works while its `call/cc` is still
  running (early exit, breaking out of loops, non-local return). Invoking it
  after that `call/cc` has returned, or from another thread, raises
  `ContinuationError`. Generators and coroutines built on re-entering
  continuations aren't supported.
- The procedure passed to `call/cc` isn't called in tail position, because the
  frame that catches the escape has to stay live.
- Non-tail recursion still uses the Python stack. Importing the runtime
  raises Python's recursion limit to 100,000. A procedure that makes no tail
  calls uses one Python frame per call, so it can recurse about 95,000 calls
  deep; one that also makes tail calls uses two frames per call, so about
  half that.
- Tail calls that pass Python keyword arguments (for example through SRFI-177
  `call/kw`) run as ordinary Python calls.
- Local `set!` is detected from `set!` forms written in the variable's scope.
  A macro that expands into `set!` of a caller's local variable isn't detected,
  and assigns a module-level variable instead.
- Performance: naive `(fib 22)` takes about 1.5 ms, versus about 1.1 ms for
  the same function in plain Python. The compiler gets there by emitting
  plain Python where it can (see `hissp_scheme/macro/inline.py`,
  `primitives.py`, and `tail.py`):
  - `if` is a Python conditional expression, and `let` binds with `:=`
    (a `let` whose variables are `set!` uses a lambda and cells instead).
  - `+`, `-`, and `*` with two or more arguments (and `(- x)`) are Python
    operators, as are `=`, `<`, `>`, `<=`, and `>=` with two arguments, or
    more when every argument is a variable or number. `vector-ref` and
    `vector-set!` are Python indexing. None of this applies once the name is
    rebound. Inline vector access skips the vector type check, so
    it also indexes other Python sequences and accepts negative indices;
    passing `vector-ref` as a value gets the checked procedure.
  - A procedure whose body makes no tail calls skips the trampoline wrapper.
  - A tail call to a Python callable bound by a Scheme `import` (such as
    `cons` or `car`), or written as `module..name`, is a direct call. A
    Python callable can't continue a chain of Scheme tail calls, so this
    keeps tail calls proper. Bare Python builtins and Hissp prelude names
    still go through the trampoline, since a later Scheme definition may
    replace them.
- SRFI-18 `raise` keeps SRFI-18's behavior of returning the handler's value,
  but it shares the handler stack with `(scheme base)`, so either library's
  handlers see the other's raises.

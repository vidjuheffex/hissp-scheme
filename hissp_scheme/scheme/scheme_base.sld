scheme_bootstrap..prelude#:

;; Explicit `(scheme base)` library.
;;
;; This file is a sequence of top-level forms rather than a single
;; `define-library` form because it defines macros and then uses them later in
;; the same file. The final `install-library-exports` call registers the module
;; as `(scheme base)` for ordinary R7RS-shaped imports.

;; The core syntax (`define`, `lambda`, `set!`, `begin`, the `let` family, `do`,
;; `define-syntax`, `let-syntax`, `letrec-syntax`, and `case`) is implemented
;; in `hissp_scheme/macro/core.py`.
(import (only scheme_pairs install-core-list-bindings))
(import hissp_scheme.macro.core)

(install-core-list-bindings (builtins..globals))

(define-syntax and
  ;; R7RS `and`: short-circuit left to right and return the last true value.
  (syntax-rules ()
    ((and)
     #t)
    ((and test)
     test)
    ((and test rest ...)
     (if test
       (and rest ...)
       #f))))

(define-syntax or
  ;; R7RS `or`: short-circuit left to right and return the first true value.
  (syntax-rules ()
    ((or)
     #f)
    ((or test)
     test)
    ((or test rest ...)
     (let ((value test))
       (if value
         value
         (or rest ...))))))

(define-syntax when
  ;; R7RS `when`: run body only when the test is true.
  (syntax-rules ()
    ((when test body ...)
     (if test
       (begin body ...)
       #f))))

(define-syntax unless
  ;; R7RS `unless`: run body only when the test is false.
  (syntax-rules ()
    ((unless test body ...)
     (if test
       #f
       (begin body ...)))))

(define-syntax cond
  ;; R7RS `cond` subset with `else`, bare test clauses, normal body clauses,
  ;; and `=>` recipient clauses.
  (syntax-rules (else =>)
    ((cond)
     #f)
    ((cond (else result ...))
     (begin result ...))
    ((cond (test => recipient) clause ...)
     (let ((value test))
       (if value
         (recipient value)
         (cond clause ...))))
    ((cond (test) clause ...)
     (let ((value test))
       (if value
         value
         (cond clause ...))))
    ((cond (test result ...) clause ...)
     (if test
       (begin result ...)
       (cond clause ...)))))

;; ---------------------------------------------------------------------------
;; Control: continuations, multiple values, exceptions, parameters
;; ---------------------------------------------------------------------------
;; Implemented in `hissp_scheme/runtime/control_runtime.py`. `call/cc` is
;; escape-only: invoking a continuation after its `call/cc` returned raises
;; `ContinuationError`.

(define procedure? hissp_scheme.runtime.control_runtime..procedure_q)
(define apply hissp_scheme.runtime.control_runtime..apply)
(define call-with-current-continuation hissp_scheme.runtime.control_runtime..call_cc)
(define call/cc hissp_scheme.runtime.control_runtime..call_cc)
(define dynamic-wind hissp_scheme.runtime.control_runtime..dynamic_wind)
(define values hissp_scheme.runtime.control_runtime..values)
(define call-with-values hissp_scheme.runtime.control_runtime..call_with_values)
(define raise-continuable hissp_scheme.runtime.control_runtime..raise_continuable)
(define with-exception-handler hissp_scheme.runtime.control_runtime..with_exception_handler)
(define error hissp_scheme.runtime.control_runtime..error)
(define error-object? hissp_scheme.runtime.control_runtime..error_object_q)
(define error-object-message hissp_scheme.runtime.control_runtime..error_object_message)
(define error-object-irritants hissp_scheme.runtime.control_runtime..error_object_irritants)
(define file-error? hissp_scheme.runtime.control_runtime..file_error_q)
(define read-error? hissp_scheme.runtime.control_runtime..read_error_q)
(define make-parameter hissp_scheme.runtime.control_runtime..make_parameter)

;; ---------------------------------------------------------------------------
;; Booleans, equivalence, numbers, symbols, and lists
;; ---------------------------------------------------------------------------
;; Implemented in `hissp_scheme/runtime/base_runtime.py`. `not` comes from the
;; bootstrap prelude, since library code needs it before base is loaded.

(define boolean? hissp_scheme.runtime.booleans..boolean_q)
(define boolean=? hissp_scheme.runtime.booleans..boolean_eq_q)
(define eq? hissp_scheme.runtime.base_runtime..eq_q)
(define eqv? hissp_scheme.runtime.base_runtime..eqv_q)
(define equal? hissp_scheme.runtime.base_runtime..equal_q)

(define + hissp_scheme.runtime.arithmetic..add)
(define - hissp_scheme.runtime.arithmetic..sub)
(define * hissp_scheme.runtime.arithmetic..mul)
(define / hissp_scheme.runtime.arithmetic..div)
(define = hissp_scheme.runtime.arithmetic..num_eq)
(define < hissp_scheme.runtime.arithmetic..num_lt)
(define > hissp_scheme.runtime.arithmetic..num_gt)
(define <= hissp_scheme.runtime.arithmetic..num_le)
(define >= hissp_scheme.runtime.arithmetic..num_ge)

;; Calls of the procedures above, and of `vector-ref`/`vector-set!`, compile to
;; Python expressions; see `hissp_scheme/macro/primitives.py`. Each name is
;; exported as both the procedure and the macro. The import comes after the
;; definitions, since a `define` replaces a macro of the same name.
(import hissp_scheme.macro.primitives)
(define number? hissp_scheme.runtime.base_runtime..number_q)
(define complex? hissp_scheme.runtime.base_runtime..complex_q)
(define real? hissp_scheme.runtime.base_runtime..real_q)
(define rational? hissp_scheme.runtime.base_runtime..rational_q)
(define integer? hissp_scheme.runtime.base_runtime..integer_q)
(define exact? hissp_scheme.runtime.base_runtime..exact_q)
(define inexact? hissp_scheme.runtime.base_runtime..inexact_q)
(define exact-integer? hissp_scheme.runtime.base_runtime..exact_integer_q)
(define zero? hissp_scheme.runtime.base_runtime..zero_q)
(define positive? hissp_scheme.runtime.base_runtime..positive_q)
(define negative? hissp_scheme.runtime.base_runtime..negative_q)
(define odd? hissp_scheme.runtime.base_runtime..odd_q)
(define even? hissp_scheme.runtime.base_runtime..even_q)
(define max hissp_scheme.runtime.base_runtime..max_)
(define min hissp_scheme.runtime.base_runtime..min_)
(define abs hissp_scheme.runtime.base_runtime..abs_)
(define quotient hissp_scheme.runtime.base_runtime..truncate_quotient)
(define remainder hissp_scheme.runtime.base_runtime..truncate_remainder)
(define modulo hissp_scheme.runtime.base_runtime..floor_remainder)
(define floor/ hissp_scheme.runtime.base_runtime..floor_slash)
(define floor-quotient hissp_scheme.runtime.base_runtime..floor_quotient)
(define floor-remainder hissp_scheme.runtime.base_runtime..floor_remainder)
(define truncate/ hissp_scheme.runtime.base_runtime..truncate_slash)
(define truncate-quotient hissp_scheme.runtime.base_runtime..truncate_quotient)
(define truncate-remainder hissp_scheme.runtime.base_runtime..truncate_remainder)
(define gcd hissp_scheme.runtime.base_runtime..gcd)
(define lcm hissp_scheme.runtime.base_runtime..lcm)
(define numerator hissp_scheme.runtime.base_runtime..numerator)
(define denominator hissp_scheme.runtime.base_runtime..denominator)
(define floor hissp_scheme.runtime.base_runtime..floor)
(define ceiling hissp_scheme.runtime.base_runtime..ceiling)
(define truncate hissp_scheme.runtime.base_runtime..truncate)
(define round hissp_scheme.runtime.base_runtime..round_)
(define exact hissp_scheme.runtime.numeric_syntax..exact)
(define inexact hissp_scheme.runtime.base_runtime..inexact)
(define exact->inexact hissp_scheme.runtime.base_runtime..inexact)
(define inexact->exact hissp_scheme.runtime.numeric_syntax..exact)
(define rationalize hissp_scheme.runtime.base_runtime..rationalize)
(define features hissp_scheme.runtime.features..features)
(define square hissp_scheme.runtime.base_runtime..square)
(define exact-integer-sqrt hissp_scheme.runtime.base_runtime..exact_integer_sqrt)
(define expt hissp_scheme.runtime.base_runtime..expt)
(define number->string hissp_scheme.runtime.base_runtime..number_to_string)
(define string->number hissp_scheme.runtime.numeric_syntax..string_to_number)

(define symbol? hissp_scheme.runtime.symbols..symbol_q)
(define symbol->string hissp_scheme.runtime.symbols..symbol_to_string)
(define string->symbol hissp_scheme.runtime.symbols..string_to_symbol)
(define symbol=? hissp_scheme.runtime.symbols..symbol_eq_q)

(define list? hissp_scheme.runtime.base_runtime..list_q)
(define make-list hissp_scheme.runtime.base_runtime..make_list)
(define list-tail hissp_scheme.runtime.base_runtime..list_tail)
(define list-set! hissp_scheme.runtime.base_runtime..list_set_bang)
(define list-copy hissp_scheme.runtime.base_runtime..list_copy)
(define memq hissp_scheme.runtime.base_runtime..memq)
(define memv hissp_scheme.runtime.base_runtime..memv)
(define member hissp_scheme.runtime.base_runtime..member)
(define assq hissp_scheme.runtime.base_runtime..assq)
(define assv hissp_scheme.runtime.base_runtime..assv)
(define assoc hissp_scheme.runtime.base_runtime..assoc)
(define map hissp_scheme.runtime.base_runtime..map_)
(define for-each hissp_scheme.runtime.base_runtime..for_each)
(define vector-map hissp_scheme.runtime.base_runtime..vector_map)
(define vector-for-each hissp_scheme.runtime.base_runtime..vector_for_each)

;; ---------------------------------------------------------------------------
;; Strings and characters
;; ---------------------------------------------------------------------------
;; Implemented in `hissp_scheme/runtime/string_runtime.py`. Characters are
;; one-character strings.

(define string? hissp_scheme.runtime.string_runtime..string_q)
(define make-string hissp_scheme.runtime.string_runtime..make_string)
(define string hissp_scheme.runtime.string_runtime..string)
(define string-length hissp_scheme.runtime.string_runtime..string_length)
(define string-ref hissp_scheme.runtime.string_runtime..string_ref)
(define string-set! hissp_scheme.runtime.string_runtime..string_set_bang)
(define string=? hissp_scheme.runtime.string_runtime..string_eq_q)
(define string<? hissp_scheme.runtime.string_runtime..string_lt_q)
(define string>? hissp_scheme.runtime.string_runtime..string_gt_q)
(define string<=? hissp_scheme.runtime.string_runtime..string_le_q)
(define string>=? hissp_scheme.runtime.string_runtime..string_ge_q)
(define substring hissp_scheme.runtime.string_runtime..substring)
(define string-append hissp_scheme.runtime.string_runtime..string_append)
(define string->list hissp_scheme.runtime.string_runtime..string_to_list)
(define list->string hissp_scheme.runtime.string_runtime..list_to_string)
(define string-copy hissp_scheme.runtime.string_runtime..string_copy)
(define string-copy! hissp_scheme.runtime.string_runtime..string_copy_bang)
(define string-fill! hissp_scheme.runtime.string_runtime..string_fill_bang)
(define string->vector hissp_scheme.runtime.string_runtime..string_to_vector)
(define vector->string hissp_scheme.runtime.string_runtime..vector_to_string)
(define string-map hissp_scheme.runtime.string_runtime..string_map)
(define string-for-each hissp_scheme.runtime.string_runtime..string_for_each)
(define char? hissp_scheme.runtime.string_runtime..char_q)
(define char=? hissp_scheme.runtime.string_runtime..char_eq_q)
(define char<? hissp_scheme.runtime.string_runtime..char_lt_q)
(define char>? hissp_scheme.runtime.string_runtime..char_gt_q)
(define char<=? hissp_scheme.runtime.string_runtime..char_le_q)
(define char>=? hissp_scheme.runtime.string_runtime..char_ge_q)
(define char->integer hissp_scheme.runtime.string_runtime..char_to_integer)
(define integer->char hissp_scheme.runtime.string_runtime..integer_to_char)

;; ---------------------------------------------------------------------------
;; Bytevectors
;; ---------------------------------------------------------------------------
;; Implemented in `hissp_scheme/runtime/bytevectors.py`. Bytevectors are
;; Python `bytearray` objects.

(define bytevector hissp_scheme.runtime.bytevectors..bytevector)
(define bytevector? hissp_scheme.runtime.bytevectors..bytevector_q)
(define make-bytevector hissp_scheme.runtime.bytevectors..make_bytevector)
(define bytevector-length hissp_scheme.runtime.bytevectors..bytevector_length)
(define bytevector-u8-ref hissp_scheme.runtime.bytevectors..bytevector_u8_ref)
(define bytevector-u8-set! hissp_scheme.runtime.bytevectors..bytevector_u8_set_bang)
(define bytevector-copy hissp_scheme.runtime.bytevectors..bytevector_copy)
(define bytevector-copy! hissp_scheme.runtime.bytevectors..bytevector_copy_bang)
(define bytevector-append hissp_scheme.runtime.bytevectors..bytevector_append)
(define utf8->string hissp_scheme.runtime.bytevectors..utf8_to_string)
(define string->utf8 hissp_scheme.runtime.bytevectors..string_to_utf8)

;; ---------------------------------------------------------------------------
;; Ports and input/output
;; ---------------------------------------------------------------------------
;; Implemented in `hissp_scheme/runtime/ports.py`. Ports are Python file
;; objects; the current ports are parameters defaulting to `sys.stdin`,
;; `sys.stdout`, and `sys.stderr`.

(define current-input-port hissp_scheme.runtime.ports..current_input_port)
(define current-output-port hissp_scheme.runtime.ports..current_output_port)
(define current-error-port hissp_scheme.runtime.ports..current_error_port)
(define input-port? hissp_scheme.runtime.ports..input_port_q)
(define output-port? hissp_scheme.runtime.ports..output_port_q)
(define textual-port? hissp_scheme.runtime.ports..textual_port_q)
(define binary-port? hissp_scheme.runtime.ports..binary_port_q)
(define port? hissp_scheme.runtime.ports..port_q)
(define input-port-open? hissp_scheme.runtime.ports..input_port_open_q)
(define output-port-open? hissp_scheme.runtime.ports..output_port_open_q)
(define close-port hissp_scheme.runtime.ports..close_port)
(define close-input-port hissp_scheme.runtime.ports..close_input_port)
(define close-output-port hissp_scheme.runtime.ports..close_output_port)
(define call-with-port hissp_scheme.runtime.ports..call_with_port)
(define open-input-string hissp_scheme.runtime.ports..open_input_string)
(define open-output-string hissp_scheme.runtime.ports..open_output_string)
(define get-output-string hissp_scheme.runtime.ports..get_output_string)
(define open-input-bytevector hissp_scheme.runtime.ports..open_input_bytevector)
(define open-output-bytevector hissp_scheme.runtime.ports..open_output_bytevector)
(define get-output-bytevector hissp_scheme.runtime.ports..get_output_bytevector)
(define eof-object hissp_scheme.runtime.ports..eof_object)
(define eof-object? hissp_scheme.runtime.ports..eof_object_q)
(define read-char hissp_scheme.runtime.ports..read_char)
(define peek-char hissp_scheme.runtime.ports..peek_char)
(define read-line hissp_scheme.runtime.ports..read_line)
(define read-string hissp_scheme.runtime.ports..read_string)
(define char-ready? hissp_scheme.runtime.ports..char_ready_q)
(define read-u8 hissp_scheme.runtime.ports..read_u8)
(define peek-u8 hissp_scheme.runtime.ports..peek_u8)
(define u8-ready? hissp_scheme.runtime.ports..u8_ready_q)
(define read-bytevector hissp_scheme.runtime.ports..read_bytevector)
(define read-bytevector! hissp_scheme.runtime.ports..read_bytevector_bang)
(define newline hissp_scheme.runtime.ports..newline)
(define write-char hissp_scheme.runtime.ports..write_char)
(define write-string hissp_scheme.runtime.ports..write_string)
(define write-u8 hissp_scheme.runtime.ports..write_u8)
(define write-bytevector hissp_scheme.runtime.ports..write_bytevector)
(define flush-output-port hissp_scheme.runtime.ports..flush_output_port)

;; `raise` is a Python keyword, so it can't be an ordinary global binding.
(define raise-transformer hissp_scheme.macro.tail..raise_form)
(define-syntax raise
  (syntax-case raise-transformer))

(define guard-transformer hissp_scheme.macro.tail..guard_form)
(define-syntax guard
  ;; (guard (var clause ...) body ...) with `cond`-style clauses. When no
  ;; clause matches, the object is re-raised to the outer handlers.
  (syntax-case guard-transformer))

(define parameterize-transformer hissp_scheme.macro.tail..parameterize_form)
(define-syntax parameterize
  (syntax-case parameterize-transformer))

;; ---------------------------------------------------------------------------
;; Records, multiple-value bindings, and feature-conditional source
;; ---------------------------------------------------------------------------
;; Procedural transformers in `hissp_scheme/macro/derived.py`. The definition
;; forms are also expanded by the body expander, so they define locals when
;; they appear in a body.

(define define-record-type-transformer hissp_scheme.macro.derived..define_record_type_form)
(define-syntax define-record-type
  ;; (define-record-type <name> (constructor field ...) predicate
  ;;   (field accessor [modifier]) ...)
  ;; The constructor may also be #f (none) or a bare name (all fields).
  (syntax-case define-record-type-transformer))

(define define-values-transformer hissp_scheme.macro.derived..define_values_form)
(define-syntax define-values
  (syntax-case define-values-transformer))

(define let-values-transformer hissp_scheme.macro.derived..let_values_form)
(define-syntax let-values
  (syntax-case let-values-transformer))

(define let*-values-transformer hissp_scheme.macro.derived..let_star_values_form)
(define-syntax let*-values
  (syntax-case let*-values-transformer))

(define cond-expand-transformer hissp_scheme.macro.derived..cond_expand_form)
(define-syntax cond-expand
  (syntax-case cond-expand-transformer))

(define include-ci-transformer hissp_scheme.macro.derived..include_ci_form)
(define-syntax include-ci
  (syntax-case include-ci-transformer))

(define syntax-error-transformer hissp_scheme.macro.derived..syntax_error_form)
(define-syntax syntax-error
  ;; Raises a SyntaxError when expanded, typically from a syntax-rules template.
  (syntax-case syntax-error-transformer))

(hissp_scheme.runtime.scheme_bootstrap_runtime..install-library-exports
  (builtins..globals)
  '(+
    -
    *
    /
    =
    <
    >
    <=
    >=
    define
    (rename scheme-lambda lambda)
    scheme-lambda
    begin
    if
    let
    let*
    letrec
    letrec*
    do
    set!
    define-syntax
    let-syntax
    letrec-syntax
    and
    or
    when
    unless
    cond
    case
    procedure?
    apply
    call-with-current-continuation
    call/cc
    dynamic-wind
    values
    call-with-values
    raise
    raise-continuable
    with-exception-handler
    guard
    error
    error-object?
    error-object-message
    error-object-irritants
    file-error?
    read-error?
    make-parameter
    parameterize
    define-record-type
    define-values
    let-values
    let*-values
    cond-expand
    include
    include-ci
    syntax-error
    not
    boolean?
    boolean=?
    number?
    complex?
    real?
    rational?
    integer?
    exact?
    inexact?
    exact-integer?
    zero?
    positive?
    negative?
    odd?
    even?
    max
    min
    abs
    quotient
    remainder
    modulo
    floor/
    floor-quotient
    floor-remainder
    truncate/
    truncate-quotient
    truncate-remainder
    gcd
    lcm
    numerator
    denominator
    floor
    ceiling
    truncate
    round
    exact
    inexact
    exact->inexact
    inexact->exact
    rationalize
    features
    square
    exact-integer-sqrt
    expt
    number->string
    string->number
    symbol?
    symbol->string
    string->symbol
    symbol=?
    list?
    make-list
    list-tail
    list-set!
    list-copy
    memq
    memv
    member
    assq
    assv
    assoc
    map
    for-each
    string?
    make-string
    string
    string-length
    string-ref
    string-set!
    string=?
    string<?
    string>?
    string<=?
    string>=?
    substring
    string-append
    string->list
    list->string
    string-copy
    string-copy!
    string-fill!
    string-map
    string-for-each
    char?
    char=?
    char<?
    char>?
    char<=?
    char>=?
    char->integer
    integer->char
    vector-map
    vector-for-each
    bytevector
    bytevector?
    make-bytevector
    bytevector-length
    bytevector-u8-ref
    bytevector-u8-set!
    bytevector-copy
    bytevector-copy!
    bytevector-append
    utf8->string
    string->utf8
    current-input-port
    current-output-port
    current-error-port
    input-port?
    output-port?
    textual-port?
    binary-port?
    port?
    input-port-open?
    output-port-open?
    close-port
    close-input-port
    close-output-port
    call-with-port
    open-input-string
    open-output-string
    get-output-string
    open-input-bytevector
    open-output-bytevector
    get-output-bytevector
    eof-object
    eof-object?
    read-char
    peek-char
    read-line
    read-string
    char-ready?
    read-u8
    peek-u8
    u8-ready?
    read-bytevector
    read-bytevector!
    newline
    write-char
    write-string
    write-u8
    write-bytevector
    flush-output-port
    cons
    list
    eq?
    eqv?
    equal?
    pair?
    null?
    car
    cdr
    car+cdr
    list-ref
    length
    append
    reverse
    set-car!
    set-cdr!
    vector?
    make-vector
    vector
    vector-length
    vector-ref
    vector-set!
    vector->list
    list->vector
    vector->string
    string->vector
    vector-copy
    vector-copy!
    vector-append
    vector-fill!
    caar
    cadr
    cdar
    cddr))

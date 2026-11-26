scheme_bootstrap..prelude#:

;; Explicit `(scheme base)` library.
;;
;; This file is still bootstrap source rather than a single `define-library`
;; form because it defines macros and then uses those macros later in the same
;; file. Hissp makes that reliable for sequential top-level forms. The final
;; `install-library-exports` call registers the module as `(scheme base)` for
;; ordinary R7RS-shaped imports.

(import (only scheme_pairs install-core-list-bindings))
(import (only itertools chain))
(import (only hissp_scheme.macro.syntax_rules
              expand-body-definitions
              expand-sequence
              expand-let-syntax
              expand-letrec-syntax
              make-transformer-from-form
              syntax-rules-stable-identifiers))

(install-core-list-bindings (builtins..globals))

(defmacro define (head .#"*body")
  ;; Full Scheme `define`.
  ;;
  ;; Bootstrap provides basic value/function define. Base upgrades the
  ;; function case: bodies may start with internal `define-syntax` forms, and
  ;; the result is a tail-call-driving procedure (see `hissp_scheme.macro.tail`).
  (if-else (isinstance head tuple)
    (progn
      (unless head
        (throw (SyntaxError "function-style define requires a name")))
      (tuple
        (@ 'hissp.macros.._macro_.define
           (op#getitem head 0)
           (hissp_scheme.macro.tail..procedure_form
             (op#getitem head 0)
             (tuple (op#getitem head (slice 1 None)))
             body))))
    (progn
      (unless (= (len body) 1)
        (throw (SyntaxError "value-style define requires exactly one value")))
      (tuple (@ 'hissp.macros.._macro_.define head (op#getitem body 0))))))

(defmacro scheme-lambda (formals .#"*body")
  ;; Full Scheme lambda with internal syntax-definition expansion and proper
  ;; tail calls.
  ;;
  ;; The reader rewrites user source `(lambda ...)` to this non-keyword macro
  ;; name in files using `scheme base`, preventing
  ;; Python's own lambda syntax from bypassing the Scheme body expander.
  (hissp_scheme.macro.tail..procedure_form None formals body))

(defmacro set! (target value)
  ;; Scheme assignment. Locals that are `set!` somewhere in their scope live in
  ;; cells (see `box_assigned_locals`), and `set!` forms written directly in
  ;; that scope are rewritten before this macro runs. A macro can still hand
  ;; this form an already-rewritten cell reference as `target`, so handle that
  ;; here too. Everything else is a module-level variable.
  (hissp.macros.._macro_.let
    (cell (hissp_scheme.macro.syntax_rules..cell_name_from_ref_form target))
    (if-else cell
      (tuple (@ 'hissp_scheme.macro.syntax_rules..cell_set cell value))
      (tuple (@ 'hissp.macros.._macro_.setQzAT_ target value)))))

(defmacro begin (.#"*body")
  ;; Scheme sequencing with support for a syntax-definition prefix. Runtime
  ;; definitions stay in the surrounding scope, so a top-level `begin` defines
  ;; globals. (A `begin` directly in a body is spliced by the body expander.)
  (hissp.macros.._macro_.let
    (expanded (scheme_base..expandQzH_sequence
                body
                (scheme_base..syntaxQzH_rulesQzH_stableQzH_identifiers)))
    (tuple
      (chain
        (@ 'hissp.macros.._macro_.progn)
        expanded))))

(defmacro let (bindings .#"*body")
  ;; Scheme `let` and named `let`, with internal syntax-definition support.
  (if-else (isinstance bindings str)
    (progn
      (unless body
        (throw (SyntaxError "named let requires bindings")))
      (hissp_scheme.macro.tail..named_let_form
        bindings
        (op#getitem body 0)
        (op#getitem body (slice 1 None))))
    (tuple
      (chain
        (@ 'hissp.macros.._macro_.let
           (scheme_bootstrap..flattenQzH_letQzH_bindings bindings))
        (hissp_scheme.macro.tail..let_body bindings body)))))

(defmacro let* (bindings .#"*body")
  ;; Sequential `let`: each init sees the bindings before it.
  (hissp_scheme.macro.tail..let_star_form bindings body))

(defmacro letrec (bindings .#"*body")
  ;; Recursive bindings, implemented through internal `define`.
  (hissp_scheme.macro.tail..letrec_form bindings body "letrec"))

(defmacro letrec* (bindings .#"*body")
  ;; Like `letrec`, with inits evaluated left to right.
  (hissp_scheme.macro.tail..letrec_form bindings body "letrec*"))

(defmacro do (specs exit-clause .#"*commands")
  ;; R7RS `do` loop, expanded into a named `let`.
  (hissp_scheme.macro.tail..do_form specs exit-clause commands))

(defmacro define-syntax (name transformer)
  ;; Define a Scheme-style macro transformer.
  (unless (ands (isinstance transformer tuple)
                transformer
                (ors (= (op#getitem transformer 0) 'syntaxQzH_rules)
                     (= (op#getitem transformer 0) 'syntaxQzH_case)))
    (throw (SyntaxError "define-syntax supports syntax-rules and syntax-case transformers")))
  (tuple
    (@ 'builtins..setattr
       '_macro_
       (tuple (@ 'quote name))
       (tuple
         (@ 'scheme_base..makeQzH_transformerQzH_fromQzH_form
            (tuple (@ 'quote name))
            (tuple (@ 'quote transformer))
            (tuple (@ 'scheme_base..syntaxQzH_rulesQzH_stableQzH_identifiers))
            (tuple (@ 'builtins..globals)))))))

(defmacro let-syntax (bindings .#"*body")
  ;; Lexically scoped local syntax-rules transformers.
  (scheme_base..expandQzH_letQzH_syntax
    bindings
    body
    (scheme_base..syntaxQzH_rulesQzH_stableQzH_identifiers)))

(defmacro letrec-syntax (bindings .#"*body")
  ;; Mutually visible local syntax-rules transformers.
  (scheme_base..expandQzH_letrecQzH_syntax
    bindings
    body
    (scheme_base..syntaxQzH_rulesQzH_stableQzH_identifiers)))

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

(define (case-body-form body)
  (tuple
    (chain
      (@ 'begin)
      body)))

(define (case-datum-value-form datum)
  ;; Case labels are datums, so quote them as Scheme data.
  (tuple (@ 'hissp_scheme.macro.quote.._macro_.quote datum)))

(define (case-datum-list-form datums)
  (tuple
    (chain
      (@ 'QzAT_)
      (builtins..map case-datum-value-form datums))))

(define (case-dispatch-form key clauses)
  (if (null? clauses)
    #f
    (let ((clause (car clauses))
          (remaining (cdr clauses)))
      (unless (and (isinstance clause tuple)
                   (> (len clause) 0))
        (throw (SyntaxError "case clauses must be non-empty lists")))
      (let ((labels (op#getitem clause 0))
            (body (op#getitem clause (slice 1 None))))
        (if (= labels 'else)
          (case-body-form body)
          (begin
            (unless (isinstance labels tuple)
              (throw (SyntaxError "case datum labels must be a list")))
            (tuple
              (@ 'if
                 (tuple
                   (@ 'hissp_scheme.runtime.base_runtime..case_match_q
                      key
                      (case-datum-list-form labels)))
                 (case-body-form body)
                 (case-dispatch-form key remaining)))))))))

(define (case-transformer key . clauses)
  (let ((key-name (.format "_Qzcase_key_{}" (id clauses))))
    (tuple
      (@ 'let
         (tuple (@ (tuple (@ key-name key))))
         (case-dispatch-form key-name clauses)))))

(define-syntax case
  ;; R7RS-shaped `case`. This uses a procedural transformer because case labels
  ;; are datums, not expressions, and our syntax-rules layer intentionally keeps
  ;; quote handling conservative.
  (syntax-case case-transformer))

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

(define + hissp_scheme.runtime.base_runtime..add)
(define - hissp_scheme.runtime.base_runtime..sub)
(define * hissp_scheme.runtime.base_runtime..mul)
(define / hissp_scheme.runtime.base_runtime..div)
(define = hissp_scheme.runtime.base_runtime..num_eq)
(define < hissp_scheme.runtime.base_runtime..num_lt)
(define > hissp_scheme.runtime.base_runtime..num_gt)
(define <= hissp_scheme.runtime.base_runtime..num_le)
(define >= hissp_scheme.runtime.base_runtime..num_ge)
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
(define exact hissp_scheme.runtime.base_runtime..exact)
(define inexact hissp_scheme.runtime.base_runtime..inexact)
(define exact->inexact hissp_scheme.runtime.base_runtime..inexact)
(define inexact->exact hissp_scheme.runtime.base_runtime..exact)
(define square hissp_scheme.runtime.base_runtime..square)
(define exact-integer-sqrt hissp_scheme.runtime.base_runtime..exact_integer_sqrt)
(define expt hissp_scheme.runtime.base_runtime..expt)
(define number->string hissp_scheme.runtime.base_runtime..number_to_string)
(define string->number hissp_scheme.runtime.base_runtime..string_to_number)

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
    vector-map
    vector-for-each
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
    cddr
    caaar
    caadr
    cadar
    caddr
    cdaar
    cdadr
    cddar
    cdddr
    caaaar
    caaadr
    caadar
    caaddr
    cadaar
    cadadr
    caddar
    cadddr
    cdaaar
    cdaadr
    cdadar
    cdaddr
    cddaar
    cddadr
    cdddar
    cddddr))

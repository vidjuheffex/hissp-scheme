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
    (hissp_scheme.macro.tail..let_form bindings body)))

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

(define + hissp_scheme.runtime.arithmetic..add)
(define - hissp_scheme.runtime.arithmetic..sub)
(define * hissp_scheme.runtime.arithmetic..mul)
(define / hissp_scheme.runtime.arithmetic..div)
(define = hissp_scheme.runtime.arithmetic..num_eq)
(define < hissp_scheme.runtime.arithmetic..num_lt)
(define > hissp_scheme.runtime.arithmetic..num_gt)
(define <= hissp_scheme.runtime.arithmetic..num_le)
(define >= hissp_scheme.runtime.arithmetic..num_ge)

;; Two-argument calls of the procedures above, and `vector-ref`/`vector-set!`
;; calls, compile to Python expressions; see `hissp_scheme/macro/primitives.py`.
;; Each name is exported as both the procedure and the macro.
(builtins..setattr _macro_ 'QzPLUS_ hissp_scheme.macro.primitives.._macro_.QzPLUS_)
(builtins..setattr _macro_ 'QzH_ hissp_scheme.macro.primitives.._macro_.QzH_)
(builtins..setattr _macro_ 'QzSTAR_ hissp_scheme.macro.primitives.._macro_.QzSTAR_)
(builtins..setattr _macro_ 'QzEQ_ hissp_scheme.macro.primitives.._macro_.QzEQ_)
(builtins..setattr _macro_ 'QzLT_ hissp_scheme.macro.primitives.._macro_.QzLT_)
(builtins..setattr _macro_ 'QzGT_ hissp_scheme.macro.primitives.._macro_.QzGT_)
(builtins..setattr _macro_ 'QzLT_QzEQ_ hissp_scheme.macro.primitives.._macro_.QzLT_QzEQ_)
(builtins..setattr _macro_ 'QzGT_QzEQ_ hissp_scheme.macro.primitives.._macro_.QzGT_QzEQ_)
(builtins..setattr _macro_ 'vectorQzH_ref hissp_scheme.macro.primitives.._macro_.vectorQzH_ref)
(builtins..setattr _macro_ 'vectorQzH_setQzBANG_ hissp_scheme.macro.primitives.._macro_.vectorQzH_setQzBANG_)
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

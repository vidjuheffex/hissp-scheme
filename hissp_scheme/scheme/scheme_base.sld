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
              expand-let-syntax
              expand-letrec-syntax
              make-transformer-from-form
              syntax-rules-stable-identifiers))

(install-core-list-bindings (builtins..globals))

(defmacro define (head .#"*body")
  ;; Full Scheme `define`.
  ;;
  ;; Bootstrap provides basic value/function define. Base upgrades the
  ;; function-body case so libraries can start bodies with internal
  ;; `define-syntax` forms.
  (if-else (isinstance head tuple)
    (progn
      (unless head
        (throw (SyntaxError "function-style define requires a name")))
      (hissp.macros.._macro_.let
        (expanded (scheme_base..expandQzH_bodyQzH_definitions
                    body
                    (scheme_base..syntaxQzH_rulesQzH_stableQzH_identifiers)))
        (tuple
          (chain
            (@ 'hissp.macros.._macro_.defun
             (op#getitem head 0)
             (hissp_scheme.runtime.scheme_bootstrap_runtime..schemeQzH_formals
               (tuple (op#getitem head (slice 1 None)))))
            (hissp_scheme.runtime.scheme_bootstrap_runtime..schemeQzH_body
              (tuple (op#getitem head (slice 1 None)))
              expanded)))))
    (progn
      (unless (= (len body) 1)
        (throw (SyntaxError "value-style define requires exactly one value")))
      (tuple (@ 'hissp.macros.._macro_.define head (op#getitem body 0))))))

(defmacro scheme-lambda (formals .#"*body")
  ;; Full Scheme lambda with internal syntax-definition expansion.
  ;;
  ;; The reader rewrites user source `(lambda ...)` to this non-keyword macro
  ;; name in files using `scheme base`, preventing
  ;; Python's own lambda syntax from bypassing the Scheme body expander.
  (hissp.macros.._macro_.let
    (expanded (scheme_base..expandQzH_bodyQzH_definitions
                body
                (scheme_base..syntaxQzH_rulesQzH_stableQzH_identifiers)))
    (tuple
      (chain
        (@ 'hissp.macros.._macro_.fun
           'lambda
           (hissp_scheme.runtime.scheme_bootstrap_runtime..schemeQzH_formals formals))
        (hissp_scheme.runtime.scheme_bootstrap_runtime..schemeQzH_body formals expanded)))))

(defmacro begin (.#"*body")
  ;; Scheme sequencing with support for an internal syntax-definition prefix.
  (hissp.macros.._macro_.let
    (expanded (scheme_base..expandQzH_bodyQzH_definitions
                body
                (scheme_base..syntaxQzH_rulesQzH_stableQzH_identifiers)))
    (tuple
      (chain
        (@ 'hissp.macros.._macro_.progn)
        expanded))))

(defmacro let (bindings .#"*body")
  ;; Scheme-shaped local binding form with internal syntax-definition support.
  (hissp.macros.._macro_.let
    (expanded (scheme_base..expandQzH_bodyQzH_definitions
                body
                (scheme_base..syntaxQzH_rulesQzH_stableQzH_identifiers)))
    (tuple
      (chain
        (@ 'hissp.macros.._macro_.let
           (scheme_bootstrap..flattenQzH_letQzH_bindings bindings))
        expanded))))

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

(define (string-literal-form? value)
  (and (isinstance value str)
       (>= (len value) 2)
       (= (op#getitem value 0) "(")
       (= (op#getitem value 1) "'")))

(define (case-datum-value-form datum)
  ;; Case labels are datums. String literals already arrive as evaluable string
  ;; literal forms; bare symbols need an explicit quote to stay data.
  (if (and (isinstance datum str)
           (not (string-literal-form? datum)))
    (tuple (@ 'quote datum))
    datum))

(define (case-datum-list-form datums)
  (tuple
    (chain
      (@ 'QzAT_)
      (map case-datum-value-form datums))))

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
                   (@ 'operator..contains
                      (case-datum-list-form labels)
                      key))
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

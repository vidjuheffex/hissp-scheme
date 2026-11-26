(import (scheme base)
        (srfi 64))

(include "include_top_level.scm")

(test-group "scheme base"
  (define (my-func x)
    (+ x 10))

  (define inc
    (lambda (x)
      (+ x 1)))

  (define (collect first . rest)
    rest)

  (define when-value 0)
  (define case-key "beta")

  ;; Fundamental pairs/lists live in Scheme base, not SRFI-1.
  (define my-pair (cons 1 2))
  (define my-list (list 1 2 3))

  ;; R7RS vectors are represented as mutable Python lists at the interop
  ;; boundary, but they are distinct from Scheme Pair lists.
  (define my-vector (vector "a" "b" "c"))
  (define copy-target (vector 0 0 0 0))
  (define fill-target (vector 1 2 3 4))

  (define mutable-pair (cons "old" "tail"))

  (test-equal "define function" 15 (my-func 5))

  (test-equal "lambda" 5 (inc 4))

  (test-equal "function rest args are lists" (list 2 3) (collect 1 2 3))
  (test-assert "empty function rest arg is null" (null? (collect 1)))
  (test-equal "variadic lambda args are lists"
              (list "a" "b")
              ((lambda values values) "a" "b"))

  (test-equal "begin"
              5
              (begin
                (define begin-value 2)
                (+ begin-value 3)))
  (test-equal "internal function define captures let bindings"
              10
              (let ((offset 3))
                (define (add-offset value)
                  (+ value offset))
                (add-offset 7)))
  (test-equal "recursive internal function define"
              15
              (let ((base 5))
                (define (sum-to value)
                  (if (= value 0)
                    base
                    (+ value (sum-to (- value 1)))))
                (sum-to 4)))

  (test-equal "if consequent" "yes" (if (> 3 2) "yes" "no"))
  (test-equal "if alternate" "no" (if (< 3 2) "yes" "no"))

  (test-equal "let"
              7
              (let ((x 2)
                    (y 5))
                (+ x y)))

  (test-equal "top-level include value"
              123
              top-level-include-value)
  (test-equal "top-level include function"
              14
              (top-level-include-double 7))

  (test-equal "and empty" #t (and))
  (test-equal "and short-circuit" #f (and #t #f (throw (AssertionError "unreachable"))))
  (test-equal "and returns last true value" "last" (and #t "last"))
  (test-equal "or empty" #f (or))
  (test-equal "or short-circuit" "first" (or "first" (throw (AssertionError "unreachable"))))
  (test-equal "or returns last false value" #f (or #f))

  (when #t
    (set! when-value 5))
  (test-equal "when true" 5 when-value)
  (unless #t
    (set! when-value 99))
  (test-equal "unless skips true" 5 when-value)
  (unless #f
    (set! when-value 7))
  (test-equal "unless false" 7 when-value)

  (test-equal "cond normal clause"
              "middle"
              (cond
                ((< 3 2) "no")
                ((< 2 3) "middle")
                (else "fallback")))
  (test-equal "cond bare test returns value"
              "value"
              (cond
                (#f "no")
                ("value")
                (else "fallback")))
  (test-equal "cond arrow"
              12
              (cond
                ((+ 5 7) => (lambda (value) value))
                (else 0)))

  (test-equal "case normal clause"
              2
              (case case-key
                (("alpha") 1)
                (("beta" "gamma") 2)
                (else 3)))
  (test-equal "case else"
              "fallback"
              (case "z"
                (("x") "x")
                (else "fallback")))

  (test-equal "cons/car" 1 (car my-pair))
  (test-equal "cons/cdr" 2 (cdr my-pair))
  (test-equal "list/cadr" 2 (cadr my-list))
  (test-equal "list/cddr" '(3) (cddr my-list))
  (test-assert "pair?" (pair? my-list))
  (test-assert "null?" (null? (cdddr my-list)))
  (test-equal "length" 3 (length my-list))
  (test-equal "append" '(1 2 3 4) (append (list 1 2) (list 3 4)))
  (test-equal "reverse" '(3 2 1) (reverse my-list))

  (test-assert "vector?" (vector? my-vector))
  (test-equal "vector-length" 3 (vector-length my-vector))
  (test-equal "vector-ref" "b" (vector-ref my-vector 1))
  (vector-set! my-vector 1 "B")
  (test-equal "vector-set!" "B" (vector-ref my-vector 1))
  (test-equal "vector->list" (list "a" "B" "c") (vector->list my-vector))
  (test-equal "list->vector" (vector 1 2 3) (list->vector (list 1 2 3)))
  (test-equal "make-vector" (vector "x" "x" "x") (make-vector 3 "x"))
  (test-equal "vector-copy" (vector "B" "c") (vector-copy my-vector 1 3))
  (vector-copy! copy-target 1 (vector 7 8))
  (test-equal "vector-copy!" (vector 0 7 8 0) copy-target)
  (test-equal "vector-append" (vector 1 2 3 4) (vector-append (vector 1 2) (vector 3 4)))
  (vector-fill! fill-target 9 1 3)
  (test-equal "vector-fill!" (vector 1 9 9 4) fill-target)
  (test-equal "string->vector base" (vector "h" "i") (string->vector "hi"))
  (test-equal "vector->string base" "hi" (vector->string (vector "h" "i")))

  ;; SRFIs are not ambient base bindings. Each module must import the SRFI it
  ;; wants before using that SRFI's procedures or macros.
  (test-error "srfi-1 iota is not base" NameError
              (iota 3))
  (test-error "srfi-28 format is not base" ValueError
              (format "~a" "x"))
  (test-error "srfi-177 call/kw is not base" NameError
              (call/kw dict (name "terrain")))
  (test-error "scheme-python attribute-set! is not base" NameError
              (attribute-set! my-list 'field-name "value"))

  (set-car! mutable-pair "new")
  (test-equal "set-car!" (cons "new" "tail") mutable-pair))

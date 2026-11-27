(import (scheme base)
        (scheme write)
        (srfi 64))

(define-record-type <point>
  (make-point x y)
  point?
  (x point-x set-point-x!)
  (y point-y))

(define-record-type <partial>
  (make-partial b)
  partial?
  (a partial-a set-partial-a!)
  (b partial-b))

(define-record-type <all-fields> make-all-fields all-fields?
  (first all-fields-first)
  (second all-fields-second))

(define-record-type <no-constructor> #f no-constructor?
  (value no-constructor-value))

(test-group "define-record-type"
  (define p (make-point 1 2))
  (test-assert "predicate" (point? p))
  (test-equal "predicate other" #f (point? 5))
  (test-equal "predicate other record" #f (point? (make-partial 1)))
  (test-equal "accessor x" 1 (point-x p))
  (test-equal "accessor y" 2 (point-y p))
  (set-point-x! p 10)
  (test-equal "modifier" 10 (point-x p))
  (test-error "accessor type check" TypeError (point-x (make-partial 1)))
  (test-error "modifier type check" TypeError (set-point-x! 'nope 1))
  (test-error "constructor arity" TypeError (make-point 1))
  (test-equal "constructor subset" 7 (partial-b (make-partial 7)))
  (define partial (make-partial 7))
  (set-partial-a! partial 'set-later)
  (test-equal "field outside constructor" 'set-later (partial-a partial))
  (test-equal "bare constructor name takes all fields"
              '(1 2)
              (let ((r (make-all-fields 1 2)))
                (list (all-fields-first r) (all-fields-second r))))
  (test-equal "no constructor" #f (no-constructor? 1))
  (test-assert "type is bound" (procedure? make-point))
  (test-equal "write" "#<point x: 10 y: 2>"
              (let ((port (open-output-string)))
                (write p port)
                (get-output-string port)))
  (test-equal "records are not vectors" #f (vector? p))
  (test-equal "equal? is identity" #f (equal? (make-point 1 2) (make-point 1 2)))
  (test-assert "eqv? same record" (eqv? p p))

  (define (local-record)
    (define-record-type node (make-node value next) node?
      (value node-value)
      (next node-next))
    (node-value (node-next (make-node 1 (make-node 2 '())))))
  (test-equal "internal define-record-type" 2 (local-record)))

(define-values (dv-a dv-b) (values 1 2))
(define-values (dv-head . dv-tail) (values 1 2 3))
(define-values dv-all (values 4 5))
(define-values () (values))

(test-group "define-values"
  (test-equal "fixed" '(1 2) (list dv-a dv-b))
  (test-equal "rest" '(1 (2 3)) (list dv-head dv-tail))
  (test-equal "all" '(4 5) dv-all)
  (test-equal "single value" 9 (let () (define-values (x) 9) x))
  (define (internal)
    (define-values (q r) (floor/ 17 5))
    (define sum (+ q r))
    (list q r sum))
  (test-equal "internal" '(3 2 5) (internal))
  (test-error "too few values" TypeError
              (let () (define-values (x y) (values 1)) x))
  (test-error "too many values" TypeError
              (let () (define-values (x) (values 1 2)) x)))

(test-group "let-values"
  (test-equal "basic" '(1 2 3)
              (let-values (((a b) (values 1 2)) ((c) (values 3)))
                (list a b c)))
  (test-equal "rest and identifier formals" '(1 (2 3) (4 5))
              (let-values (((a . rest) (values 1 2 3)) (all (values 4 5)))
                (list a rest all)))
  (test-equal "no bindings" 'body (let-values () 'body))
  (test-equal "single value producer" 5 (let-values (((x) 5)) x))
  (define x 'outer)
  (test-equal "inits see outer scope" '(inner outer)
              (let-values (((x) (values 'inner)) ((y) (values x)))
                (list x y)))
  (test-equal "R7RS example" '(x y a b)
              (let ((a 'a) (b 'b) (x 'x) (y 'y))
                (let-values (((a b) (values x y))
                             ((x y) (values a b)))
                  (list a b x y))))
  (test-equal "body definitions" 3
              (let-values (((a) (values 1)))
                (define b 2)
                (+ a b)))
  (define (loop n)
    (let-values (((m) (values (- n 1))))
      (if (= m 0) 'done (loop m))))
  (test-equal "tail call in body" 'done (loop 100000)))

(test-group "let*-values"
  (define x 'outer)
  (test-equal "sequential" '(inner inner)
              (let*-values (((x) (values 'inner)) ((y) (values x)))
                (list x y)))
  (test-equal "R7RS example" '(x y x y)
              (let ((a 'a) (b 'b) (x 'x) (y 'y))
                (let*-values (((a b) (values x y))
                              ((x y) (values a b)))
                  (list a b x y))))
  (test-equal "no bindings" 'body (let*-values () 'body)))

(cond-expand
  ((and r7rs (not no-such-feature)) (define cond-expand-result 'matched))
  (else (define cond-expand-result 'else)))

(cond-expand
  (no-such-feature (define cond-expand-fallback 'wrong))
  (else (define cond-expand-fallback 'else)))

(test-group "cond-expand and features"
  (test-equal "and/not requirement" 'matched cond-expand-result)
  (test-equal "else" 'else cond-expand-fallback)
  (test-equal "or requirement" 'yes
              (cond-expand ((or no-such-feature r7rs) 'yes) (else 'no)))
  (test-equal "library available" 'yes
              (cond-expand ((library (srfi 1)) 'yes) (else 'no)))
  (test-equal "library missing" 'no
              (cond-expand ((library (srfi 99999)) 'yes) (else 'no)))
  (test-equal "srfi feature" 'yes
              (cond-expand (srfi-132 'yes) (else 'no)))
  (test-equal "internal definitions" 2
              (let ()
                (cond-expand (r7rs (define picked 2)) (else (define picked 3)))
                picked))
  (test-assert "features is a list of symbols"
               (and (list? (features)) (symbol? (car (features)))))
  (test-assert "features has r7rs" (memq 'r7rs (features))))

(include-ci "include_ci_value.scm")

(test-group "include and include-ci"
  (test-equal "include-ci folds identifiers" "hi!" (include-ci-shout "hi"))
  (test-equal "include-ci folds quoted symbols" 'hello include-ci-symbol)
  (test-equal "include-ci keeps strings" "Keep Case" include-ci-string)
  (define (with-include)
    (include "include_body_value.scm")
    (+ include-body-value 1))
  (test-equal "include in a body defines locals" 42 (with-include)))

(define-library (scheme test-cond-expand-library)
  (export picked-branch)
  (import (scheme base))
  (cond-expand
    (no-such-feature (begin (define picked-branch 'wrong)))
    ((library (scheme base)) (begin (define picked-branch 'right))))
  (include-library-declarations "include_declarations.scm"))

(test-group "define-library declarations"
  (test-equal "cond-expand" 'right picked-branch)
  (test-equal "include-library-declarations" 'declared declared-value))

(define-syntax checked-pair
  (syntax-rules ()
    ((_ (a . b)) 'ok)
    ((_ other) (syntax-error "checked-pair: expected a pair" other))))

(define-syntax quoted-template
  (syntax-rules ()
    ((_ x) '(tag x))))

(test-group "syntax-error and quoted templates"
  (test-equal "syntax-error not reached" 'ok (checked-pair (1 . 2)))
  (test-equal "quoted template symbols are not renamed" '(tag 5) (quoted-template 5)))

(test-group "rationalize"
  (test-equal "exact" 1/3 (rationalize 1/3 1/100))
  (test-equal "R7RS example exact" 1/3 (rationalize (exact .3) 1/10))
  (test-equal "R7RS example inexact" (/ 1. 3) (rationalize .3 1/10))
  (test-equal "integer in range" 1 (rationalize 3/4 1/4))
  (test-equal "zero in range" 0 (rationalize 1/10 1/5))
  (test-equal "negative" -1/3 (rationalize -1/3 1/100))
  (test-assert "inexact result" (inexact? (rationalize .3 1/10))))

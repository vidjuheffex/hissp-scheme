(import (scheme base)
        (srfi 64))

;; Top-level macros still need to be defined before later top-level forms use
;; them, but full `scheme` body forms now support internal `define-syntax`.

(test-begin "syntax-rules")

(define-syntax when
  (syntax-rules ()
    ((when test body ...)
     (if test
       (begin body ...)
       #f))))

(test-equal "syntax-rules when true" 7 (when #t (+ 3 4)))
(test-equal "syntax-rules when false" #f (when #f (+ 3 4)))

(define-syntax unless
  (syntax-rules ()
    ((unless test body ...)
     (if test
       #f
       (begin body ...)))))

(test-equal "syntax-rules unless" 5 (unless #f 5))

(define-syntax choose
  (syntax-rules (else)
    ((choose else value)
     value)
    ((choose test value)
     (if test value #f))))

(test-equal "syntax-rules literal matches" "fallback" (choose else "fallback"))
(test-equal "syntax-rules nonliteral rule true" "value" (choose #t "value"))
(test-equal "syntax-rules nonliteral rule false" #f (choose #f "value"))

(define-syntax ignore-first
  (syntax-rules ()
    ((ignore-first _ value)
     value)))

(test-equal "syntax-rules wildcard" 12 (ignore-first anything 12))

(define-syntax list-of
  (syntax-rules ()
    ((list-of item ...)
     (list item ...))))

(test-equal "syntax-rules template ellipsis" '(1 2 3) (list-of 1 2 3))
(test-equal "syntax-rules template ellipsis empty" '() (list-of))

(define-syntax with-temp
  (syntax-rules ()
    ((with-temp value body)
     (let ((tmp value))
       body))))

(test-equal "syntax-rules introduced binding does not capture caller"
            100
            (let ((tmp 100))
              (with-temp 1 tmp)))

(define-syntax double-with-temp
  (syntax-rules ()
    ((double-with-temp value)
     (let ((tmp value))
       (+ tmp tmp)))))

(test-equal "syntax-rules introduced references stay linked"
            8
            (let ((tmp 100))
              (double-with-temp 4)))

(test-equal "let-syntax local macro"
            42
            (let-syntax ((answer
                           (syntax-rules ()
                             ((answer)
                              42))))
              (answer)))

(test-equal "let-syntax shadows global macro locally"
            "local"
            (let-syntax ((choose
                           (syntax-rules ()
                             ((choose anything)
                              "local"))))
              (choose ignored)))

(test-equal "let-syntax does not leak"
            "global"
            (choose #t "global"))

(test-equal "letrec-syntax mutual local macros"
            5
            (letrec-syntax ((a
                              (syntax-rules ()
                                ((a x)
                                 (b x))))
                            (b
                              (syntax-rules ()
                                ((b x)
                                 (+ x 1)))))
              (a 4)))

(test-equal "letrec-syntax shadows global macro locally"
            "recursive local"
            (letrec-syntax ((choose
                              (syntax-rules ()
                                ((choose ignored)
                                 "recursive local"))))
              (choose #f)))

(test-equal "letrec-syntax does not leak"
            "global"
            (choose #t "global"))

(test-equal "internal define-syntax in let"
            42
            (let ()
              (define-syntax answer
                (syntax-rules ()
                  ((answer)
                   42)))
              (answer)))

(define (use-internal-syntax x)
  (define-syntax twice
    (syntax-rules ()
      ((twice value)
       (+ value value))))
  (twice x))

(test-equal "internal define-syntax in function body"
            8
            (use-internal-syntax 4))

(test-equal "internal define-syntax in lambda body"
            12
            ((lambda (x)
               (define-syntax triple
                 (syntax-rules ()
                   ((triple value)
                    (+ value (+ value value)))))
               (triple x))
             4))

(test-equal "internal define-syntax in begin"
            "begun"
            (begin
              (define-syntax begun
                (syntax-rules ()
                  ((begun)
                   "begun")))
              (begun)))

(test-group "syntax-rules body expansion in test-group"
  (let ()
    (define-syntax group-answer
      (syntax-rules ()
        ((group-answer)
         99)))
    (test-equal "internal define-syntax in test-group" 99 (group-answer))))

(define-syntax rows
  (syntax-rules ()
    ((rows (item ...) ...)
     (list (list item ...) ...))))

(test-equal "syntax-rules nested template ellipsis"
            '((1 2) (3 4))
            (rows (1 2) (3 4)))

(test-equal "syntax-rules nested template ellipsis with empty inner row"
            '(() (5))
            (rows () (5)))

(test-end "syntax-rules")

;; SRFI-1 list-library procedures.
;;
;; Core pair/list primitives live in `scheme`. This library adds SRFI-1
;; procedures in Scheme source and declares its public surface with
;; `(define-library ...)`. `make-list`, `map`, `member`, and `assoc` are the
;; `(scheme base)` procedures, which already have the SRFI-1 behavior.

(define-library (srfi 1)
  (export xcons
          cons*
          make-list
          iota
          proper-list?
          dotted-list?
          take
          drop
          map
          filter
          fold
          member
          assoc
          list=)
  (import (scheme base))
  (begin
    (define (optional args default)
      (if (null? args)
        default
        (car args)))

    (define (xcons tail head)
      (cons head tail))

    (define (cons* first . rest)
      (define (cons-star values)
        (if (null? (cdr values))
          (car values)
          (cons (car values)
                (cons-star (cdr values)))))
      (if (null? rest)
        first
        (cons first (cons-star rest))))

    (define (iota count . options)
      (let ((start (if (pair? options)
                     (car options)
                     0))
            (step (if (pair? options)
                    (if (pair? (cdr options))
                      (cadr options)
                      1)
                    1)))
        (define (loop index value)
          (if (= index count)
            '()
            (cons value (loop (+ index 1) (+ value step)))))
        (loop 0 start)))

    (define (proper-list? value)
      (if (null? value)
        #t
        (if (pair? value)
          (proper-list? (cdr value))
          #f)))

    (define (dotted-list? value)
      (if (null? value)
        #f
        (if (pair? value)
          (dotted-list? (cdr value))
          #t)))

    (define (take value count)
      (if (= count 0)
        '()
        (cons (car value) (take (cdr value) (- count 1)))))

    (define (drop value count)
      (if (= count 0)
        value
        (drop (cdr value) (- count 1))))

    (define (filter predicate value)
      (if (null? value)
        '()
        (let ((head (car value))
              (tail (filter predicate (cdr value))))
          (if (predicate head)
            (cons head tail)
            tail))))

    (define (fold procedure seed value)
      (if (null? value)
        seed
        (fold procedure
              (procedure (car value) seed)
              (cdr value))))

    (define (same-length? left right)
      (= (length left) (length right)))

    (define (list-pair= same? left right)
      (if (null? left)
        (null? right)
        (if (null? right)
          #f
          (if (same? (car left) (car right))
            (list-pair= same? (cdr left) (cdr right))
            #f))))

    (define (all-lists-equal? same? first rest)
      (if (null? rest)
        #t
        (let ((current (car rest)))
          (if (same-length? first current)
            (if (list-pair= same? first current)
              (all-lists-equal? same? current (cdr rest))
              #f)
            #f))))

    (define (list= same? first . rest)
      (all-lists-equal? same? first rest))))

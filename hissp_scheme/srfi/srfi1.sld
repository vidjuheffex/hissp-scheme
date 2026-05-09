;; SRFI-1 list-library procedures.
;;
;; Core pair/list primitives live in `scheme`. This library adds SRFI-1
;; procedures in Scheme source and declares its public surface with
;; `(define-library ...)`.

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

    (define (make-list count . maybe-fill)
      (let ((fill (optional maybe-fill #f)))
        (define (loop remaining)
          (if (= remaining 0)
            '()
            (cons fill (loop (- remaining 1)))))
        (loop count)))

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

    (define (map procedure value)
      (if (null? value)
        '()
        (cons (procedure (car value))
              (map procedure (cdr value)))))

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

    (define (member value values . maybe-equal)
      (let ((same? (optional maybe-equal equal?)))
        (if (null? values)
          #f
          (if (same? value (car values))
            values
            (member value (cdr values) same?)))))

    (define (assoc key alist . maybe-equal)
      (let ((same? (optional maybe-equal equal?)))
        (if (null? alist)
          #f
          (let ((entry (car alist)))
            (if (same? key (car entry))
              entry
              (assoc key (cdr alist) same?))))))

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

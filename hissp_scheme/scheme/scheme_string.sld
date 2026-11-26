;; R7RS-style `(scheme string)` library over Python `str`.
;;
;; Python has immutable strings and no separate character type. For now, a
;; Scheme character at this boundary is represented as a one-character Python
;; string. Procedures that would mutate a Scheme string raise explicit errors
;; rather than pretending Python strings are mutable.

(define-library (scheme string)
  (export list->string
          make-string
          string
          string->list
          string->vector
          string-append
          string-copy
          string-copy!
          string-fill!
          string-for-each
          string-length
          string-map
          string-ref
          string-set!
          substring
          string<=?
          string<?
          string=?
          string>=?
          string>?
          string?)
  (import (scheme base))
  (begin
    (define (string? value)
      ;; Symbols are a `str` subclass; see `hissp_scheme.runtime.symbols`.
      (eq? (type value) str))

    (define (check-string value procedure)
      (unless (string? value)
        (throw (TypeError (.format "{} expected a string" procedure))))
      value)

    (define (check-character value procedure)
      (unless (and (string? value) (= (len value) 1))
        (throw (TypeError (.format "{} expected a character" procedure))))
      value)

    (define (immutable-string-error procedure)
      (throw
        (TypeError
          (.format "{} cannot mutate Python-backed immutable strings"
                   procedure))))

    (define (make-string count . maybe-char)
      (let ((char (if (null? maybe-char)
                    "\x00"
                    (car maybe-char))))
        (check-character char "make-string")
        (* char count)))

    (define (string . chars)
      (define (loop remaining)
        (if (null? remaining)
          ""
          (+ (check-character (car remaining) "string")
             (loop (cdr remaining)))))
      (loop chars))

    (define (string-length value)
      (len (check-string value "string-length")))

    (define (string-ref value index)
      (op#getitem (check-string value "string-ref") index))

    (define (string-set! value index char)
      (immutable-string-error "string-set!"))

    (define (string=? left right)
      (= (check-string left "string=?")
         (check-string right "string=?")))

    (define (string<? left right)
      (< (check-string left "string<?")
         (check-string right "string<?")))

    (define (string>? left right)
      (> (check-string left "string>?")
         (check-string right "string>?")))

    (define (string<=? left right)
      (<= (check-string left "string<=?")
          (check-string right "string<=?")))

    (define (string>=? left right)
      (>= (check-string left "string>=?")
          (check-string right "string>=?")))

    (define (substring value start end)
      (op#getitem (check-string value "substring") (slice start end)))

    (define (string-append . strings)
      (define (loop remaining)
        (if (null? remaining)
          ""
          (+ (check-string (car remaining) "string-append")
             (loop (cdr remaining)))))
      (loop strings))

    (define (string->list value . options)
      (let ((start (if (pair? options) (car options) 0))
            (end (if (and (pair? options) (pair? (cdr options)))
                   (cadr options)
                   (len (check-string value "string->list")))))
        (define (loop index)
          (if (= index end)
            '()
            (cons (op#getitem value index) (loop (+ index 1)))))
        (loop start)))

    (define (list->string chars)
      (define (loop remaining)
        (if (null? remaining)
          ""
          (+ (check-character (car remaining) "list->string")
             (loop (cdr remaining)))))
      (loop chars))

    (define (string-copy value . options)
      (let ((start (if (pair? options) (car options) 0))
            (end (if (and (pair? options) (pair? (cdr options)))
                   (cadr options)
                   (len (check-string value "string-copy")))))
        (substring value start end)))

    (define (string-copy! to at source . options)
      (immutable-string-error "string-copy!"))

    (define (string-fill! value fill . options)
      (immutable-string-error "string-fill!"))

    (define (string-map proc value . more-values)
      (define (loop index)
        (if (= index (len value))
          ""
          (+ (proc (op#getitem value index))
             (loop (+ index 1)))))
      (when (not (null? more-values))
        (throw (NotImplementedError "string-map currently supports one string")))
      (check-string value "string-map")
      (loop 0))

    (define (string-for-each proc value . more-values)
      (define (loop index)
        (if (= index (len value))
          #f
          (begin
            (proc (op#getitem value index))
            (loop (+ index 1)))))
      (when (not (null? more-values))
        (throw (NotImplementedError "string-for-each currently supports one string")))
      (check-string value "string-for-each")
      (loop 0))

    (define (string->vector value . options)
      (let ((start (if (pair? options) (car options) 0))
            (end (if (and (pair? options) (pair? (cdr options)))
                   (cadr options)
                   (len (check-string value "string->vector")))))
        (list->vector (string->list value start end))))))

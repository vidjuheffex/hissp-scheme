;; SRFI-69: Basic hash tables.
;;
;; This library gives Scheme code a portable hash-table API while the runtime
;; storage uses Python dictionaries. The public optional-argument behavior and
;; names live here; `hissp_scheme.runtime.srfi69_runtime.py` owns the dict-backed implementation.

(define-library (srfi 69)
  (export make-hash-table
          hash-table?
          alist->hash-table
          hash-table-equivalence-function
          hash-table-hash-function
          hash-table-ref
          hash-table-ref/default
          hash-table-set!
          hash-table-delete!
          hash-table-exists?
          hash-table-update!
          hash-table-update!/default
          hash-table-size
          hash-table-keys
          hash-table-values
          hash-table-walk
          hash-table-fold
          hash-table->alist
          hash-table-copy
          hash-table-merge!
          hash
          string-hash
          string-ci-hash
          hash-by-identity)
  (import (scheme base)
          (prefix hissp_scheme.runtime.srfi69_runtime rt-))
  (begin
    (define (option-2 options default)
      (if (and (pair? options) (pair? (cdr options)))
        (cadr options)
        default))

    (define (make-hash-table . options)
      (if (null? options)
        (rt-make-hash-table equal? hash)
        (if (null? (cdr options))
          (rt-make-hash-table (car options) hash)
          (rt-make-hash-table (car options) (cadr options)))))

    (define (hash-table? obj)
      (rt-hash-table-q obj))

    (define (alist->hash-table alist . options)
      (if (null? options)
        (rt-alist-to-hash-table alist equal? hash)
        (if (null? (cdr options))
          (rt-alist-to-hash-table alist (car options) hash)
          (rt-alist-to-hash-table alist (car options) (cadr options)))))

    (define (hash-table-equivalence-function hash-table)
      (rt-hash-table-equivalence-function hash-table))

    (define (hash-table-hash-function hash-table)
      (rt-hash-table-hash-function hash-table))

    (define (hash-table-ref hash-table key . maybe-thunk)
      (if (null? maybe-thunk)
        (rt-hash-table-ref hash-table key)
        (rt-hash-table-ref hash-table key (car maybe-thunk))))

    (define (hash-table-ref/default hash-table key default)
      (rt-hash-table-ref-default hash-table key default))

    (define (hash-table-set! hash-table key value)
      (rt-hash-table-set-bang hash-table key value))

    (define (hash-table-delete! hash-table key)
      (rt-hash-table-delete-bang hash-table key))

    (define (hash-table-exists? hash-table key)
      (rt-hash-table-exists-q hash-table key))

    (define (hash-table-update! hash-table key function . maybe-thunk)
      (if (null? maybe-thunk)
        (rt-hash-table-update-bang hash-table key function)
        (rt-hash-table-update-bang hash-table key function (car maybe-thunk))))

    (define (hash-table-update!/default hash-table key function default)
      (rt-hash-table-update-bang-default hash-table key function default))

    (define (hash-table-size hash-table)
      (rt-hash-table-size hash-table))

    (define (hash-table-keys hash-table)
      (rt-hash-table-keys hash-table))

    (define (hash-table-values hash-table)
      (rt-hash-table-values hash-table))

    (define (hash-table-walk hash-table procedure)
      (rt-hash-table-walk hash-table procedure))

    (define (hash-table-fold hash-table function init-value)
      (rt-hash-table-fold hash-table function init-value))

    (define (hash-table->alist hash-table)
      (rt-hash-table-to-alist hash-table))

    (define (hash-table-copy hash-table)
      (rt-hash-table-copy hash-table))

    (define (hash-table-merge! hash-table1 hash-table2)
      (rt-hash-table-merge-bang hash-table1 hash-table2))

    (define (hash obj . maybe-bound)
      (if (null? maybe-bound)
        (rt-hash-value obj)
        (rt-hash-value obj (car maybe-bound))))

    (define (string-hash value . maybe-bound)
      (if (null? maybe-bound)
        (rt-string-hash value)
        (rt-string-hash value (car maybe-bound))))

    (define (string-ci-hash value . maybe-bound)
      (if (null? maybe-bound)
        (rt-string-ci-hash value)
        (rt-string-ci-hash value (car maybe-bound))))

    (define (hash-by-identity obj . maybe-bound)
      (if (null? maybe-bound)
        (rt-hash-by-identity obj)
        (rt-hash-by-identity obj (car maybe-bound))))))

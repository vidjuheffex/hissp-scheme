;; Python interop helpers.
;;
;; This is a boundary library, not a Python prelude. It converts between
;; Scheme-owned data structures and Python-native containers and provides
;; Scheme-shaped helpers for Python dictionaries, tuples, and object
;; attributes.

(define-library (scheme python)
  (export dict->hash-table
          hash-table->dict
          tuple->list
          list->tuple
          tuple->vector
          vector->tuple
          python-list->list
          list->python-list
          python-list->vector
          vector->python-list
          item-ref
          item-set!
          item-delete!
          dict?
          make-dict
          dict-ref
          dict-ref/default
          dict-set!
          dict-delete!
          dict-exists?
          dict-keys
          dict-values
          dict-items
          dict-copy
          dict-update!
          tuple?
          make-tuple
          tuple-ref
          tuple-length
          object?
          attribute-ref
          attribute-ref/default
          attribute-set!
          attribute-delete!
          attribute-exists?
          class?
          object-class
          class-name
          is-a?
          subclass?
          make-object
          method-ref
          call-method)
  (import (scheme base)
          (srfi 69)
          (prefix hissp_scheme.runtime.scheme_python_runtime rt-))
  (begin
    (define (dict->hash-table dictionary)
      (rt-dict-to-hash-table dictionary (make-hash-table)))

    (define hash-table->dict rt-hash-table-to-dict)

    (define tuple->list rt-tuple-to-list)

    (define list->tuple rt-list-to-tuple)

    (define tuple->vector rt-tuple-to-vector)

    (define vector->tuple rt-vector-to-tuple)

    (define python-list->list rt-python-list-to-list)

    (define list->python-list rt-list-to-python-list)

    (define python-list->vector rt-python-list-to-vector)

    (define vector->python-list rt-vector-to-python-list)

    (define item-ref rt-item-ref)

    (define item-set! rt-item-set-bang)

    (define item-delete! rt-item-delete-bang)

    (define dict? rt-dict-q)

    (define make-dict rt-make-dict)

    (define dict-ref rt-dict-ref)

    (define dict-ref/default rt-dict-ref-default)

    (define dict-set! rt-dict-set-bang)

    (define dict-delete! rt-dict-delete-bang)

    (define dict-exists? rt-dict-exists-q)

    (define dict-keys rt-dict-keys)

    (define dict-values rt-dict-values)

    (define dict-items rt-dict-items)

    (define dict-copy rt-dict-copy)

    (define dict-update! rt-dict-update-bang)

    (define tuple? rt-tuple-q)

    (define make-tuple rt-make-tuple)

    (define tuple-ref rt-tuple-ref)

    (define tuple-length rt-tuple-length)

    (define object? rt-object-q)

    (define attribute-ref rt-attribute-ref)

    (define attribute-ref/default rt-attribute-ref-default)

    (define attribute-set! rt-attribute-set-bang)

    (define attribute-delete! rt-attribute-delete-bang)

    (define attribute-exists? rt-attribute-exists-q)

    (define class? rt-class-q)

    (define object-class rt-object-class)

    (define class-name rt-class-name)

    (define is-a? rt-is-a-q)

    (define subclass? rt-subclass-q)

    (define make-object rt-make-object)

    (define method-ref rt-method-ref)

    (define call-method rt-call-method)))

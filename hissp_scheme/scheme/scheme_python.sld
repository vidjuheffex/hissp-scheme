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

    (define (hash-table->dict hash-table)
      (rt-hash-table-to-dict hash-table))

    (define (tuple->list value)
      (rt-tuple-to-list value))

    (define (list->tuple value)
      (rt-list-to-tuple value))

    (define (tuple->vector value)
      (rt-tuple-to-vector value))

    (define (vector->tuple vector)
      (rt-vector-to-tuple vector))

    (define (python-list->list value)
      (rt-python-list-to-list value))

    (define (list->python-list value)
      (rt-list-to-python-list value))

    (define (python-list->vector value)
      (rt-python-list-to-vector value))

    (define (vector->python-list value)
      (rt-vector-to-python-list value))

    (define (item-ref obj key)
      (rt-item-ref obj key))

    (define (item-set! obj key value)
      (rt-item-set-bang obj key value))

    (define (item-delete! obj key)
      (rt-item-delete-bang obj key))

    (define (dict? obj)
      (rt-dict-q obj))

    (define (make-dict . items)
      (rt-make-dict-from-list items))

    (define (dict-ref dictionary key)
      (rt-dict-ref dictionary key))

    (define (dict-ref/default dictionary key default)
      (rt-dict-ref-default dictionary key default))

    (define (dict-set! dictionary key value)
      (rt-dict-set-bang dictionary key value))

    (define (dict-delete! dictionary key)
      (rt-dict-delete-bang dictionary key))

    (define (dict-exists? dictionary key)
      (rt-dict-exists-q dictionary key))

    (define (dict-keys dictionary)
      (rt-dict-keys dictionary))

    (define (dict-values dictionary)
      (rt-dict-values dictionary))

    (define (dict-items dictionary)
      (rt-dict-items dictionary))

    (define (dict-copy dictionary)
      (rt-dict-copy dictionary))

    (define (dict-update! dictionary other)
      (rt-dict-update-bang dictionary other))

    (define (tuple? obj)
      (rt-tuple-q obj))

    (define (make-tuple . items)
      (rt-list-to-tuple items))

    (define (tuple-ref value index)
      (rt-tuple-ref value index))

    (define (tuple-length value)
      (rt-tuple-length value))

    (define (object? obj)
      (rt-object-q obj))

    (define (attribute-ref obj name)
      (rt-attribute-ref obj name))

    (define (attribute-ref/default obj name default)
      (rt-attribute-ref-default obj name default))

    (define (attribute-set! obj name value)
      (rt-attribute-set-bang obj name value))

    (define (attribute-delete! obj name)
      (rt-attribute-delete-bang obj name))

    (define (attribute-exists? obj name)
      (rt-attribute-exists-q obj name))

    (define (class? obj)
      (rt-class-q obj))

    (define (object-class obj)
      (rt-object-class obj))

    (define (class-name klass)
      (rt-class-name klass))

    (define (is-a? obj klass)
      (rt-is-a-q obj klass))

    (define (subclass? subclass superclass)
      (rt-subclass-q subclass superclass))

    (define (make-object klass . args)
      (rt-make-object-from-list klass args))

    (define (method-ref obj name)
      (rt-method-ref obj name))

    (define (call-method obj name . args)
      (rt-call-method-from-list obj name args))))

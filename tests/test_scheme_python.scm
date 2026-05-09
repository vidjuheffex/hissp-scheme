(import (scheme base)
        (scheme python)
        (srfi 64)
        (srfi 69)
        (only builtins bool int)
        (only types SimpleNamespace))

(test-group "scheme python"
  (define dictionary (make-dict "name" "terrain" "height" 120))
  (test-assert "dict?" (dict? dictionary))
  (test-equal "dict-ref" "terrain" (dict-ref dictionary "name"))
  (test-equal "dict-ref/default present"
              120
              (dict-ref/default dictionary "height" 0))
  (test-equal "dict-ref/default missing"
              "fallback"
              (dict-ref/default dictionary "missing" "fallback"))
  (dict-set! dictionary "active" #t)
  (test-assert "dict-set!" (dict-ref dictionary "active"))
  (test-assert "dict-exists?" (dict-exists? dictionary "name"))
  (dict-delete! dictionary "name")
  (test-equal "dict-delete!" #f (dict-exists? dictionary "name"))
  (test-equal "dict-keys" 2 (length (dict-keys dictionary)))
  (test-equal "dict-values" 2 (length (dict-values dictionary)))
  (test-equal "dict-items" 2 (length (dict-items dictionary)))

  (define copied-dictionary (dict-copy dictionary))
  (dict-set! copied-dictionary "copy-only" 1)
  (test-equal "dict-copy independent"
              #f
              (dict-exists? dictionary "copy-only"))
  (dict-update! dictionary (make-dict "updated" 99))
  (test-equal "dict-update!" 99 (dict-ref dictionary "updated"))

  (define hash-table (dict->hash-table dictionary))
  (test-assert "dict->hash-table" (hash-table? hash-table))
  (test-equal "dict->hash-table value"
              120
              (hash-table-ref hash-table "height"))
  (define round-tripped-dict (hash-table->dict hash-table))
  (test-assert "hash-table->dict" (dict? round-tripped-dict))
  (test-equal "hash-table->dict value"
              120
              (dict-ref round-tripped-dict "height"))

  (define tuple-value (make-tuple 1 2 3))
  (test-assert "tuple?" (tuple? tuple-value))
  (test-equal "tuple-length" 3 (tuple-length tuple-value))
  (test-equal "tuple-ref" 2 (tuple-ref tuple-value 1))
  (test-equal "tuple->list" (list 1 2 3) (tuple->list tuple-value))
  (test-equal "list->tuple" tuple-value (list->tuple (list 1 2 3)))
  (test-equal "tuple->vector" (vector 1 2 3) (tuple->vector tuple-value))
  (test-equal "vector->tuple" tuple-value (vector->tuple (vector 1 2 3)))

  (define python-list (list->python-list (list "a" "b")))
  (test-equal "python-list->list"
              (list "a" "b")
              (python-list->list python-list))
  (test-equal "python-list->vector"
              (vector "a" "b")
              (python-list->vector python-list))
  (test-equal "vector->python-list"
              python-list
              (vector->python-list (vector "a" "b")))

  (test-equal "item-ref tuple" 2 (item-ref tuple-value 1))
  (test-equal "item-ref dict" 120 (item-ref round-tripped-dict "height"))
  (item-set! round-tripped-dict "height" 121)
  (test-equal "item-set!" 121 (dict-ref round-tripped-dict "height"))
  (item-delete! round-tripped-dict "height")
  (test-equal "item-delete!" #f (dict-exists? round-tripped-dict "height"))

  (test-assert "object?" (object? dictionary))
  (test-assert "attribute-exists?" (attribute-exists? dictionary '__class__))
  (test-assert "attribute-ref" (attribute-ref dictionary '__class__))
  (test-equal "attribute-ref/default"
              "fallback"
              (attribute-ref/default dictionary 'missing-attribute "fallback"))

  (define attribute-target (SimpleNamespace))
  (attribute-set! attribute-target 'custom-attr "value")
  (test-equal "attribute-set!" "value" (attribute-ref attribute-target 'custom-attr))
  (attribute-delete! attribute-target 'custom-attr)
  (test-equal "attribute-delete!" #f (attribute-exists? attribute-target 'custom-attr))

  (test-assert "class?" (class? SimpleNamespace))
  (test-equal "object-class" SimpleNamespace (object-class attribute-target))
  (test-equal "class-name" "SimpleNamespace" (class-name SimpleNamespace))
  (test-assert "is-a?" (is-a? attribute-target SimpleNamespace))
  (test-assert "subclass?" (subclass? bool int))

  (define constructed (make-object SimpleNamespace))
  (attribute-set! constructed 'name "terrain")
  (test-equal "make-object" "terrain" (attribute-ref constructed 'name))

  (test-assert "method-ref" (method-ref "abc" 'upper))
  (test-equal "call-method no args" "ABC" (call-method "abc" 'upper))
  (test-equal "call-method args" "jello" (call-method "hello" 'replace "h" "j"))
  (test-error "method-ref rejects non-callable"
              TypeError
              (method-ref constructed 'name)))

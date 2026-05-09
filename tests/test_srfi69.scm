(import (scheme base)
        (srfi 1)
        (srfi 64)
        (srfi 69))

(test-group "srfi-69"
  (define table (make-hash-table))
  (test-assert "make-hash-table" (hash-table? table))
  (test-equal "empty size" 0 (hash-table-size table))

  (hash-table-set! table "name" "terrain")
  (hash-table-set! table "height" 120)
  (test-equal "hash-table-ref" "terrain" (hash-table-ref table "name"))
  (test-equal "hash-table-ref/default present"
              120
              (hash-table-ref/default table "height" 0))
  (test-equal "hash-table-ref/default missing"
              "missing"
              (hash-table-ref/default table "absent" "missing"))
  (test-equal "hash-table-ref thunk"
              "fallback"
              (hash-table-ref table "absent"
                              (lambda ()
                                (if #t "fallback" "unreachable"))))
  (test-error "hash-table-ref thunk must be callable"
              TypeError
              (hash-table-ref table "absent" "not-a-thunk"))
  (test-assert "hash-table-exists?"
               (hash-table-exists? table "name"))
  (test-equal "hash-table-size" 2 (hash-table-size table))

  (hash-table-update! table "height" (lambda (value) (+ value 1)))
  (test-equal "hash-table-update!" 121 (hash-table-ref table "height"))
  (hash-table-update!/default table "visits" (lambda (value) (+ value 1)) 0)
  (test-equal "hash-table-update!/default" 1 (hash-table-ref table "visits"))

  (hash-table-delete! table "name")
  (test-equal "hash-table-delete!" #f (hash-table-exists? table "name"))
  (test-error "hash-table-ref missing" KeyError (hash-table-ref table "name"))

  (define from-alist
    (alist->hash-table
      (list (cons "a" 1)
            (cons "b" 2)
            (cons "a" 99))))
  (test-equal "alist->hash-table keeps first duplicate"
              1
              (hash-table-ref from-alist "a"))
  (test-equal "hash-table->alist round-trip"
              2
              (length (hash-table->alist from-alist)))

  (define copied (hash-table-copy from-alist))
  (hash-table-set! copied "c" 3)
  (test-equal "hash-table-copy original unchanged"
              #f
              (hash-table-exists? from-alist "c"))

  (hash-table-merge! from-alist copied)
  (test-equal "hash-table-merge!" 3 (hash-table-ref from-alist "c"))

  (define key-total
    (hash-table-fold
      from-alist
      (lambda (key value total) (+ total value))
      0))
  (test-equal "hash-table-fold" 6 key-total)

  (define walked-total 0)
  (hash-table-walk
    from-alist
    (lambda (key value)
      (set! walked-total (+ walked-total value))))
  (test-equal "hash-table-walk" 6 walked-total)

  (test-equal "hash-table-keys length"
              3
              (length (hash-table-keys from-alist)))
  (test-equal "hash-table-values length"
              3
              (length (hash-table-values from-alist)))

  (test-assert "hash-table-equivalence-function"
               ((hash-table-equivalence-function from-alist) "x" "x"))
  (test-assert "hash-table-hash-function"
               (< ((hash-table-hash-function from-alist) "x" 10) 10))

  (test-assert "hash bound"
               (< (hash "abc" 10) 10))
  (test-assert "string-hash bound"
               (< (string-hash "abc" 10) 10))
  (test-equal "string-ci-hash ignores case"
              (string-ci-hash "ABC" 1000)
              (string-ci-hash "abc" 1000))
  (test-assert "hash-by-identity bound"
               (< (hash-by-identity table 10) 10)))

(import (scheme base)
        (srfi 64))

(test-group "strings"
  (define seen (vector))

  (test-assert "string?" (string? "abc"))
  (test-equal "string? rejects non-string" #f (string? 123))

  (test-equal "make-string" "xxx" (make-string 3 "x"))
  (test-equal "string" "abc" (string "a" "b" "c"))
  (test-error "string rejects non-character" TypeError (string "a" "bc"))

  (test-equal "string-length" 5 (string-length "hello"))
  (test-equal "string-ref" "e" (string-ref "hello" 1))

  (test-assert "string=?" (string=? "same" "same"))
  (test-assert "string<?" (string<? "abc" "abd"))
  (test-assert "string>?" (string>? "abd" "abc"))
  (test-assert "string<=? equal" (string<=? "abc" "abc"))
  (test-assert "string>=? equal" (string>=? "abc" "abc"))

  (test-equal "substring" "ell" (substring "hello" 1 4))
  (test-equal "string-append" "hello" (string-append "he" "ll" "o"))

  (test-equal "string->list" (list "a" "b" "c") (string->list "abc"))
  (test-equal "string->list slice" (list "b" "c") (string->list "abcd" 1 3))
  (test-equal "list->string" "abc" (list->string (list "a" "b" "c")))

  (test-equal "string-copy" "ell" (string-copy "hello" 1 4))
  (test-equal "string-map" "ABC" (string-map (lambda (ch) (.upper ch)) "abc"))

  (string-for-each
    (lambda (ch)
      (.append seen ch))
    "xyz")
  (test-equal "string-for-each" (vector "x" "y" "z") seen)

  (test-equal "string->vector" (vector "a" "b" "c") (string->vector "abc"))

  (test-error "string-set! immutable" TypeError (string-set! "abc" 1 "x"))
  (test-error "string-copy! immutable" TypeError (string-copy! "abc" 0 "z"))
  (test-error "string-fill! immutable" TypeError (string-fill! "abc" "z")))

(import (scheme base)
        (srfi 64))

(test-group "reader"
  (define quoted-list '(1 2 3))
  (test-equal "quote list" (list 1 2 3) quoted-list)
  (test-assert "quoted list is pair" (pair? quoted-list))
  (test-equal "quote nested" (list 1 (list 2 3)) '(1 (2 3)))
  (test-equal "quote dotted" (cons 1 2) '(1 . 2))

  (define quasiquote-value 9)
  (define quasiquote-splice (list 2 3))
  (test-equal "quasiquote unquote" '(1 9 3) `(1 ,quasiquote-value 3))
  (test-equal "quasiquote splice" '(1 2 3 4) `(1 ,@quasiquote-splice 4)))

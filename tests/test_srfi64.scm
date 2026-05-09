(import (scheme base)
        (srfi 64))

(test-group "srfi-64"
  (define (raise-value-error)
    (throw (ValueError "expected failure")))

  (test-approximate "test-approximate" 3.14 3.14159 0.01)
  (test-error "test-error" ValueError (raise-value-error))
  (test-group "nested group"
    (test-equal "test-group body" 3 (+ 1 2))))

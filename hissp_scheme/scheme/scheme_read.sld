;; R7RS-style `(scheme read)` library.

(define-library (scheme read)
  (export read-line)
  (import (scheme base))
  (begin
    (define (read-line . maybe-prompt)
      (input
        (if (null? maybe-prompt)
          ""
          (car maybe-prompt))))))

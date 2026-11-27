;; R7RS-style `(scheme write)` library.

(define-library (scheme write)
  (export display write)
  (import (scheme base))
  (begin
    (define (optional-output-port maybe-port)
      (if (null? maybe-port)
        (current-output-port)
        (car maybe-port)))

    (define (display value . maybe-port)
      (.write (optional-output-port maybe-port)
              (hissp_scheme.runtime.printer..display_string value))
      #f)

    (define (write value . maybe-port)
      (.write (optional-output-port maybe-port)
              (hissp_scheme.runtime.printer..write_string value))
      #f)))

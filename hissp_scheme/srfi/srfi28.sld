;; SRFI-28: Basic Format Strings.
;;
;; Implemented as Scheme source and exported with an R7RS-shaped library
;; declaration.

(define-library (srfi 28)
  (export format)
  (import (scheme base))
  (begin
    (define (format-display-string value)
      (if (isinstance value str)
        value
        (str value)))

    (define (format-write-string value)
      (repr value))

    (define (format-require-argument args arg-index directive)
      (if (< arg-index (length args))
        (list-ref args arg-index)
        (throw
          (ValueError
            (.format "not enough arguments for SRFI-28 directive ~{}"
                     directive)))))

    (define (format-loop template args index arg-index output)
      (if (>= index (len template))
        (if (= arg-index (length args))
          output
          (throw (ValueError "too many arguments for format string")))
        (let ((char (op#getitem template index)))
          (if (not (= char "~"))
            (format-loop template args (+ index 1) arg-index (+ output char))
            (format-directive template args (+ index 1) arg-index output)))))

    (define (format-directive template args directive-index arg-index output)
      (if (>= directive-index (len template))
        (throw (ValueError "format string ends after ~"))
        (let ((directive (op#getitem template directive-index)))
          (if (= directive "a")
            (format-loop template
                         args
                         (+ directive-index 1)
                         (+ arg-index 1)
                         (+ output
                            (format-display-string
                              (format-require-argument args arg-index directive))))
            (if (= directive "s")
              (format-loop template
                           args
                           (+ directive-index 1)
                           (+ arg-index 1)
                           (+ output
                              (format-write-string
                                (format-require-argument args arg-index directive))))
              (if (= directive "%")
                (format-loop template args (+ directive-index 1) arg-index (+ output "\n"))
                (if (= directive "~")
                  (format-loop template args (+ directive-index 1) arg-index (+ output "~"))
                  (throw
                    (ValueError
                      (.format "unsupported SRFI-28 format directive: ~{}"
                               directive))))))))))

    (define (format template . args)
      (format-loop template args 0 0 ""))))

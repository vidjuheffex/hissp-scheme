;; SRFI-28: Basic Format Strings.
;;
;; Implemented as Scheme source and exported with an R7RS-shaped library
;; declaration.

(define-library (srfi 28)
  (export format)
  (import (scheme base)
          (only hissp_scheme.runtime.printer display-string write-string))
  (begin
    (define (format-argument args arg-index directive)
      (if (< arg-index (length args))
        (list-ref args arg-index)
        (raise
          (ValueError
            (string-append "not enough arguments for SRFI-28 directive ~"
                           directive)))))

    (define (format-loop template args index arg-index output)
      (cond
        ((>= index (string-length template))
         (if (= arg-index (length args))
           output
           (raise (ValueError "too many arguments for format string"))))
        ((char=? (string-ref template index) #\~)
         (format-directive template args (+ index 1) arg-index output))
        (else
         (format-loop template args (+ index 1) arg-index
                      (string-append output (string (string-ref template index)))))))

    (define (format-directive template args index arg-index output)
      (if (>= index (string-length template))
        (raise (ValueError "format string ends after ~"))
        (let ((directive (string-ref template index)))
          (define (continue text next-arg-index)
            (format-loop template args (+ index 1) next-arg-index
                         (string-append output text)))
          (case directive
            ((#\a)
             (continue (display-string (format-argument args arg-index directive))
                       (+ arg-index 1)))
            ((#\s)
             (continue (write-string (format-argument args arg-index directive))
                       (+ arg-index 1)))
            ((#\%) (continue "\n" arg-index))
            ((#\~) (continue "~" arg-index))
            (else
             (raise
               (ValueError
                 (string-append "unsupported SRFI-28 format directive: ~"
                                (string directive)))))))))

    (define (format template . args)
      (format-loop template args 0 0 ""))))

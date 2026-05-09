;; R7RS-style `(scheme file)` library.
;;
;; This library is intentionally small and direct: Scheme source wraps Python's
;; ordinary file objects as ports. Text ports use Python's default text encoding;
;; binary ports use Python bytes mode.

(define-library (scheme file)
  (export call-with-input-file
          call-with-output-file
          delete-file
          file-exists?
          open-binary-input-file
          open-binary-output-file
          open-input-file
          open-output-file
          with-input-from-file
          with-output-to-file)
  (import (scheme base)
          (scheme python)
          (only builtins open)
          (only contextlib redirect-stdout)
          (only pathlib Path))
  (begin
    (define (open-input-file filename)
      (open filename "r"))

    (define (open-output-file filename)
      (open filename "w"))

    (define (open-binary-input-file filename)
      (open filename "rb"))

    (define (open-binary-output-file filename)
      (open filename "wb"))

    (define (call-with-input-file filename proc)
      (enter (open-input-file filename) proc))

    (define (call-with-output-file filename proc)
      (enter (open-output-file filename) proc))

    (define (with-input-from-file filename thunk)
      (call-with-input-file
        filename
        (lambda (port)
          (let ((previous sys..stdin))
            (attribute-set! sys. 'stdin port)
            (let ((result (thunk)))
              (attribute-set! sys. 'stdin previous)
              result)))))

    (define (with-output-to-file filename thunk)
      (call-with-output-file
        filename
        (lambda (port)
          (enter
            (redirect-stdout port)
            (lambda (ignored-port) (thunk))))))

    (define (file-exists? filename)
      (.exists (Path filename)))

    (define (delete-file filename)
      (.unlink (Path filename))
      #f)))

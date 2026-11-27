;; R7RS-style `(scheme read)` library.
;;
;; `read` parses one datum from an optional textual input port; it's
;; implemented in `hissp_scheme/runtime/datum_reader.py`.
;;
;; `read-line` is the `(scheme base)` procedure, re-exported so programs that
;; import it from here keep working. It reads from an optional port; as an
;; extension, a string argument is a prompt for the current input port.

(define-library (scheme read)
  (export read read-line)
  (import (scheme base))
  (begin
    (define read hissp_scheme.runtime.datum_reader..read)))

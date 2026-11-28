scheme_bootstrap..prelude#:

;; Reader/prelude entrypoint.
;;
;; This module intentionally does not install `(scheme base)`. `scheme_reader`
;; injects this prelude automatically for ordinary `.sld` and `.scm` files, so
;; user Scheme source can start directly with R7RS-shaped imports:
;;
;;   (import (scheme base))

(define prelude scheme_bootstrap..prelude)

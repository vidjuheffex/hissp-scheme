scheme_bootstrap..prelude#:

;; Reader/prelude entrypoint.
;;
;; This module intentionally does not install `(scheme base)`. `scheme_reader`
;; injects this prelude automatically for ordinary `.sld` and `.scm` files, so
;; user Scheme source can start directly with R7RS-shaped imports:
;;
;;   (import (scheme base))

(defmacro prelude (env)
  (tuple (@ 'scheme_bootstrap.._macro_.prelude env)))

(defun prelude (env)
  (tuple (@ 'scheme.._macro_.prelude env)))

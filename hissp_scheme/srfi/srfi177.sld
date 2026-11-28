;; SRFI-177-inspired keyword argument support.
;;
;;   (call/kw dumps payload (indent 2 sort-keys #t))
;;   (call/kw dumps payload (** options))
;;   (define/kw (describe name (color size)) ...)
;;
;; The transformers are in `hissp_scheme/macro/keywords.py`, since they build
;; Python keyword-argument calls and keyword-only formals.

(define-library (srfi 177)
  (export call/kw lambda/kw define/kw)
  (import (scheme base))
  (begin
    (define call/kw-transformer hissp_scheme.macro.keywords..call_kw_form)
    (define-syntax call/kw
      (syntax-case call/kw-transformer))

    (define lambda/kw-transformer hissp_scheme.macro.keywords..lambda_kw_form)
    (define-syntax lambda/kw
      (syntax-case lambda/kw-transformer))

    (define define/kw-transformer hissp_scheme.macro.keywords..define_kw_form)
    (define-syntax define/kw
      (syntax-case define/kw-transformer))))

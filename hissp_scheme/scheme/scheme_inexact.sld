;; R7RS `(scheme inexact)` library.

(define-library (scheme inexact)
  (export exp log sin cos tan asin acos atan sqrt finite? infinite? nan?)
  (import (scheme base))
  (begin
    (define exp hissp_scheme.runtime.base_runtime..exp)
    (define log hissp_scheme.runtime.base_runtime..log)
    (define sin hissp_scheme.runtime.base_runtime..sin)
    (define cos hissp_scheme.runtime.base_runtime..cos)
    (define tan hissp_scheme.runtime.base_runtime..tan)
    (define asin hissp_scheme.runtime.base_runtime..asin)
    (define acos hissp_scheme.runtime.base_runtime..acos)
    (define atan hissp_scheme.runtime.base_runtime..atan)
    (define sqrt hissp_scheme.runtime.base_runtime..sqrt)
    (define finite? hissp_scheme.runtime.base_runtime..finite_q)
    (define infinite? hissp_scheme.runtime.base_runtime..infinite_q)
    (define nan? hissp_scheme.runtime.base_runtime..nan_q)))

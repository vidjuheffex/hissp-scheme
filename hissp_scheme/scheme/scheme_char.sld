;; R7RS `(scheme char)` library. Characters are one-character strings.

(define-library (scheme char)
  (export char-alphabetic?
          char-numeric?
          char-whitespace?
          char-upper-case?
          char-lower-case?
          digit-value
          char-upcase
          char-downcase
          char-foldcase
          string-upcase
          string-downcase
          string-foldcase
          char-ci=?
          char-ci<?
          char-ci>?
          char-ci<=?
          char-ci>=?
          string-ci=?
          string-ci<?
          string-ci>?
          string-ci<=?
          string-ci>=?)
  (import (scheme base))
  (begin
    (define char-alphabetic? hissp_scheme.runtime.string_runtime..char_alphabetic_q)
    (define char-numeric? hissp_scheme.runtime.string_runtime..char_numeric_q)
    (define char-whitespace? hissp_scheme.runtime.string_runtime..char_whitespace_q)
    (define char-upper-case? hissp_scheme.runtime.string_runtime..char_upper_case_q)
    (define char-lower-case? hissp_scheme.runtime.string_runtime..char_lower_case_q)
    (define digit-value hissp_scheme.runtime.string_runtime..digit_value)
    (define char-upcase hissp_scheme.runtime.string_runtime..char_upcase)
    (define char-downcase hissp_scheme.runtime.string_runtime..char_downcase)
    (define char-foldcase hissp_scheme.runtime.string_runtime..char_foldcase)
    (define string-upcase hissp_scheme.runtime.string_runtime..string_upcase)
    (define string-downcase hissp_scheme.runtime.string_runtime..string_downcase)
    (define string-foldcase hissp_scheme.runtime.string_runtime..string_foldcase)
    (define char-ci=? hissp_scheme.runtime.string_runtime..char_ci_eq_q)
    (define char-ci<? hissp_scheme.runtime.string_runtime..char_ci_lt_q)
    (define char-ci>? hissp_scheme.runtime.string_runtime..char_ci_gt_q)
    (define char-ci<=? hissp_scheme.runtime.string_runtime..char_ci_le_q)
    (define char-ci>=? hissp_scheme.runtime.string_runtime..char_ci_ge_q)
    (define string-ci=? hissp_scheme.runtime.string_runtime..string_ci_eq_q)
    (define string-ci<? hissp_scheme.runtime.string_runtime..string_ci_lt_q)
    (define string-ci>? hissp_scheme.runtime.string_runtime..string_ci_gt_q)
    (define string-ci<=? hissp_scheme.runtime.string_runtime..string_ci_le_q)
    (define string-ci>=? hissp_scheme.runtime.string_runtime..string_ci_ge_q)))

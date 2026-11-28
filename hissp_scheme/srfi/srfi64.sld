;; SRFI-64: A Scheme API for test suites.
;;
;; The runner state and test forms are implemented in Scheme source. The
;; macros below wrap test expressions in thunks so failures can be recorded
;; without aborting the whole suite.

(define-library (srfi 64)
  (export test-begin
          test-end
          test-skip
          test-expect-fail
          test-runner-simple
          test-runner-current
          test-runner-current!
          test-runner-pass-count
          test-runner-fail-count
          test-runner-skip-count
          test-runner-xpass-count
          test-runner-xfail-count
          test-runner-group-path
          test-runner-test-name
          test-result-ref
          test-result-kind
          test-on-final-simple
          test-exit-code
          test-assert
          test-equal
          test-eqv
          test-eq
          test-approximate
          test-error
          test-group)
  (import (scheme base))
  (begin
    (define test-pass-count 0)
    (define test-fail-count 0)
    (define test-skip-count 0)
    (define test-xpass-count 0)
    (define test-xfail-count 0)
    (define test-total-count 0)
    (define test-group-depth 0)
    (define test-current-name "")
    (define test-current-kind "")

    (define (test-runner-simple)
      "default")

    (define (test-runner-current)
      "default")

    (define (test-runner-current! runner)
      runner)

    (define (test-runner-pass-count runner)
      test-pass-count)

    (define (test-runner-fail-count runner)
      test-fail-count)

    (define (test-runner-skip-count runner)
      test-skip-count)

    (define (test-runner-xpass-count runner)
      test-xpass-count)

    (define (test-runner-xfail-count runner)
      test-xfail-count)

    (define (test-runner-group-path runner)
      '())

    (define (test-runner-test-name runner)
      test-current-name)

    (define (test-result-ref runner key . maybe-default)
      (if (null? maybe-default)
        #f
        (car maybe-default)))

    (define (test-result-kind runner)
      test-current-kind)

    (define (test-skip specifier)
      ;; Skip filters are part of SRFI-64, but this minimal runner does not yet
      ;; maintain selector state. Keep the procedure present and inert.
      #f)

    (define (test-expect-fail specifier)
      ;; Expected-failure filters are present for API compatibility. The current
      ;; runner records ordinary failures.
      #f)

    (define (test-begin suite-name . maybe-count)
      (set! test-group-depth (+ test-group-depth 1))
      (print (.format "%%%% Starting test {}" suite-name))
      #f)

    (define (test-on-final-simple . maybe-runner)
      (print
        (.format "%%%% Summary: {} passed, {} failed, {} skipped, {} expected failed, {} unexpected passed"
                 test-pass-count
                 test-fail-count
                 test-skip-count
                 test-xfail-count
                 test-xpass-count))
      #f)

    (define (test-end . maybe-suite-name)
      (let ((suite-name (if (null? maybe-suite-name)
                          ""
                          (car maybe-suite-name))))
        (print (.format "%%%% Finished test {}" suite-name))
        (set! test-group-depth (- test-group-depth 1))
        (when (= test-group-depth 0)
          (test-on-final-simple))
        #f))

    (define (record-result name passed expected actual)
      (set! test-current-name (if name name ""))
      (set! test-total-count (+ test-total-count 1))
      (if passed
        (begin
          (set! test-current-kind "pass")
          (set! test-pass-count (+ test-pass-count 1))
          #t)
        (begin
          (set! test-current-kind "fail")
          (set! test-fail-count (+ test-fail-count 1))
          (print (.format "FAIL {}" test-current-name))
          (print (.format "  expected: {}" (hissp_scheme.runtime.printer..write_string expected)))
          (print (.format "  actual:   {}" (hissp_scheme.runtime.printer..write_string actual)))
          #f)))

    (define (_identity value)
      value)

    ;; Errors, Scheme or Python, are recorded as failures instead of ending the
    ;; suite.
    (define (test-assert-thunk name thunk source)
      (guard (error (#t (record-result name #f #t error)))
        (let ((actual (thunk)))
          (record-result name (not (eq? actual #f)) #t actual))))

    (define (test-compare-thunks name expected-thunk actual-thunk comparator source)
      (guard (error (#t (record-result name #f "no error" error)))
        (let ((expected (expected-thunk))
              (actual (actual-thunk)))
          (record-result name (comparator expected actual) expected actual))))

    (define (test-approximate-thunks name expected-thunk actual-thunk error-thunk source)
      (guard (error (#t (record-result name #f "no error" error)))
        (let ((expected (expected-thunk))
              (actual (actual-thunk))
              (tolerance (error-thunk)))
          (record-result name
                         (and (>= actual (- expected tolerance))
                              (<= actual (+ expected tolerance)))
                         expected
                         actual))))

    (define (error-matches? expected error)
      (if (eq? expected #t)
        #t
        (isinstance error expected)))

    (define (test-error-thunk name expected-error thunk source)
      ;; `record-result` runs outside the `guard` body, so a failure it raises
      ;; isn't mistaken for the expected error.
      (let ((outcome
             (guard (error (#t (list 'raised error)))
               (list 'returned (thunk)))))
        (if (eq? (car outcome) 'raised)
          (record-result name
                         (error-matches? expected-error (cadr outcome))
                         expected-error
                         (type (cadr outcome)))
          (record-result name #f expected-error (cadr outcome)))))

    (define (test-exit-code . maybe-runner)
      (if (> test-fail-count 0) 1 0))

    (define (same-object? left right)
      (eq? left right))

    (define (same-value? left right)
      (equal? left right))

    (define (same-number-or-object? left right)
      (eqv? left right))

    (define-syntax test-assert
      (syntax-rules ()
        ((_ name expression)
         (test-assert-thunk name
                            (lambda () (_identity expression))
                            'expression))
        ((_ expression)
         (test-assert-thunk #f
                            (lambda () (_identity expression))
                            'expression))))

    (define-syntax test-equal
      (syntax-rules ()
        ((_ name expected actual)
         (test-compare-thunks name
                              (lambda () (_identity expected))
                              (lambda () (_identity actual))
                              same-value?
                              'actual))
        ((_ expected actual)
         (test-compare-thunks #f
                              (lambda () (_identity expected))
                              (lambda () (_identity actual))
                              same-value?
                              'actual))))

    (define-syntax test-eqv
      (syntax-rules ()
        ((_ name expected actual)
         (test-compare-thunks name
                              (lambda () (_identity expected))
                              (lambda () (_identity actual))
                              same-number-or-object?
                              'actual))
        ((_ expected actual)
         (test-compare-thunks #f
                              (lambda () (_identity expected))
                              (lambda () (_identity actual))
                              same-number-or-object?
                              'actual))))

    (define-syntax test-eq
      (syntax-rules ()
        ((_ name expected actual)
         (test-compare-thunks name
                              (lambda () (_identity expected))
                              (lambda () (_identity actual))
                              same-object?
                              'actual))
        ((_ expected actual)
         (test-compare-thunks #f
                              (lambda () (_identity expected))
                              (lambda () (_identity actual))
                              same-object?
                              'actual))))

    (define-syntax test-approximate
      (syntax-rules ()
        ((_ name expected actual tolerance)
         (test-approximate-thunks name
                                  (lambda () (_identity expected))
                                  (lambda () (_identity actual))
                                  (lambda () (_identity tolerance))
                                  'actual))
        ((_ expected actual tolerance)
         (test-approximate-thunks #f
                                  (lambda () (_identity expected))
                                  (lambda () (_identity actual))
                                  (lambda () (_identity tolerance))
                                  'actual))))

    (define-syntax test-error
      (syntax-rules ()
        ((_ name expected-error expression)
         (test-error-thunk name
                           expected-error
                           (lambda () (_identity expression))
                           'expression))
        ((_ expected-error expression)
         (test-error-thunk #f
                           expected-error
                           (lambda () (_identity expression))
                           'expression))
        ((_ expression)
         (test-error-thunk #f
                           #t
                           (lambda () (_identity expression))
                           'expression))))

    (define-syntax test-group
      (syntax-rules ()
        ((_ suite-name body ...)
         (begin
           (test-begin suite-name)
           body ...
           (test-end suite-name)))))))

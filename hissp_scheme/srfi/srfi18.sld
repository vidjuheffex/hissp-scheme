;; SRFI-18: Multithreading support.
;;
;; The public API is an R7RS-shaped Scheme library. Actual threads, mutexes,
;; condition variables, time objects, and low-level exception records are backed
;; by `hissp_scheme.runtime.srfi18_runtime.py`, because those operations must use CPython runtime
;; facilities. This file keeps the Scheme spelling and optional-argument
;; behavior in Scheme source.

(define-library (srfi 18)
  (export current-thread
          thread?
          make-thread
          thread-name
          thread-specific
          thread-specific-set!
          thread-start!
          thread-yield!
          thread-sleep!
          thread-terminate!
          thread-join!
          mutex?
          make-mutex
          mutex-name
          mutex-specific
          mutex-specific-set!
          mutex-state
          mutex-lock!
          mutex-unlock!
          condition-variable?
          make-condition-variable
          condition-variable-name
          condition-variable-specific
          condition-variable-specific-set!
          condition-variable-signal!
          condition-variable-broadcast!
          current-time
          time?
          time->seconds
          seconds->time
          current-exception-handler
          with-exception-handler
          raise
          join-timeout-exception?
          abandoned-mutex-exception?
          terminated-thread-exception?
          uncaught-exception?
          uncaught-exception-reason)
  (import (scheme base)
          (prefix hissp_scheme.runtime.srfi18_runtime rt-))
  (begin
    (define (option-1 options default)
      (if (null? options)
        default
        (car options)))

    (define (option-2 options default)
      (if (and (pair? options) (pair? (cdr options)))
        (cadr options)
        default))

    (define (current-thread)
      (rt-current-thread))

    (define (thread? obj)
      (rt-thread-q obj))

    (define (make-thread thunk . maybe-name)
      (if (null? maybe-name)
        (rt-make-thread thunk)
        (rt-make-thread thunk (car maybe-name))))

    (define (thread-name thread)
      (rt-thread-name thread))

    (define (thread-specific thread)
      (rt-thread-specific thread))

    (define (thread-specific-set! thread obj)
      (rt-thread-specific-set-bang thread obj))

    (define (thread-start! thread)
      (rt-thread-start-bang thread))

    (define (thread-yield!)
      (rt-thread-yield-bang))

    (define (thread-sleep! timeout)
      (rt-thread-sleep-bang timeout))

    (define (thread-terminate! thread)
      (rt-thread-terminate-bang thread))

    (define (thread-join! thread . options)
      (if (null? options)
        (rt-thread-join-bang thread)
        (if (null? (cdr options))
          (rt-thread-join-bang thread (car options))
          (rt-thread-join-bang thread (car options) (cadr options)))))

    (define (mutex? obj)
      (rt-mutex-q obj))

    (define (make-mutex . maybe-name)
      (if (null? maybe-name)
        (rt-make-mutex)
        (rt-make-mutex (car maybe-name))))

    (define (mutex-name mutex)
      (rt-mutex-name mutex))

    (define (mutex-specific mutex)
      (rt-mutex-specific mutex))

    (define (mutex-specific-set! mutex obj)
      (rt-mutex-specific-set-bang mutex obj))

    (define (mutex-state mutex)
      (rt-mutex-state mutex))

    (define (mutex-lock! mutex . options)
      (if (null? options)
        (rt-mutex-lock-bang mutex)
        (if (null? (cdr options))
          (rt-mutex-lock-bang mutex (car options))
          (rt-mutex-lock-bang mutex (car options) (cadr options)))))

    (define (mutex-unlock! mutex . options)
      (if (null? options)
        (rt-mutex-unlock-bang mutex)
        (if (null? (cdr options))
          (rt-mutex-unlock-bang mutex (car options))
          (rt-mutex-unlock-bang mutex (car options) (cadr options)))))

    (define (condition-variable? obj)
      (rt-condition-variable-q obj))

    (define (make-condition-variable . maybe-name)
      (if (null? maybe-name)
        (rt-make-condition-variable)
        (rt-make-condition-variable (car maybe-name))))

    (define (condition-variable-name condition-variable)
      (rt-condition-variable-name condition-variable))

    (define (condition-variable-specific condition-variable)
      (rt-condition-variable-specific condition-variable))

    (define (condition-variable-specific-set! condition-variable obj)
      (rt-condition-variable-specific-set-bang condition-variable obj))

    (define (condition-variable-signal! condition-variable)
      (rt-condition-variable-signal-bang condition-variable))

    (define (condition-variable-broadcast! condition-variable)
      (rt-condition-variable-broadcast-bang condition-variable))

    (define (current-time)
      (rt-current-time))

    (define (time? obj)
      (rt-time-q obj))

    (define (time->seconds time)
      (rt-time-to-seconds time))

    (define (seconds->time seconds)
      (rt-seconds-to-time seconds))

    (define (current-exception-handler)
      (rt-current-exception-handler))

    (define (with-exception-handler handler thunk)
      (rt-with-exception-handler handler thunk))

    (define (scheme-raise obj)
      (rt-raise- obj))

    (define (raise-transformer obj)
      (tuple
        (@ 'srfi18..schemeQzH_raise obj)))

    (define-syntax raise
      (syntax-case raise-transformer))

    (define (join-timeout-exception? obj)
      (rt-join-timeout-exception-q obj))

    (define (abandoned-mutex-exception? obj)
      (rt-abandoned-mutex-exception-q obj))

    (define (terminated-thread-exception? obj)
      (rt-terminated-thread-exception-q obj))

    (define (uncaught-exception? obj)
      (rt-uncaught-exception-q obj))

    (define (uncaught-exception-reason exc)
      (rt-uncaught-exception-reason exc))))

(import (scheme base)
        (srfi 18)
        (srfi 64))

(test-group "srfi-18"
  (test-assert "current-thread is thread"
               (thread? (current-thread)))

  (define worker
    (make-thread
      (lambda ()
        (+ 20 22))
      "worker"))

  (test-assert "make-thread"
               (thread? worker))
  (test-equal "thread-name" "worker" (thread-name worker))

  (thread-specific-set! worker "specific-value")
  (test-equal "thread-specific" "specific-value" (thread-specific worker))

  (thread-start! worker)
  (test-equal "thread-join!" 42 (thread-join! worker))

  (define sleeper
    (thread-start!
      (make-thread
        (lambda ()
          (thread-sleep! 0.05)
          "awake"))))
  (test-equal "thread-join! timeout value"
              "timeout"
              (thread-join! sleeper 0 "timeout"))
  (test-equal "thread-sleep! and join"
              "awake"
              (thread-join! sleeper))

  (define uncaught-thread
    (thread-start!
      (make-thread
        (lambda ()
          (raise "boom")))))
  (define uncaught
    (engarde BaseException
      (lambda (error) error)
      (lambda ()
        (thread-join! uncaught-thread))))
  (test-assert "uncaught-exception?"
               (uncaught-exception? uncaught))
  (test-equal "uncaught-exception-reason"
              "boom"
              (uncaught-exception-reason uncaught))

  (test-equal "with-exception-handler"
              "handled"
              (with-exception-handler
                (lambda (obj)
                  (if #t "handled" "unreachable"))
                (lambda ()
                  (raise "ignored"))))

  (define timeout-thread
    (thread-start!
      (make-thread
        (lambda ()
          (thread-sleep! 0.05)))))
  (define timeout-error
    (engarde BaseException
      (lambda (error) error)
      (lambda ()
        (thread-join! timeout-thread 0))))
  (test-assert "join-timeout-exception?"
               (join-timeout-exception? timeout-error))
  (thread-join! timeout-thread)

  (define mutex (make-mutex "mutex"))
  (test-assert "mutex?" (mutex? mutex))
  (test-equal "mutex-name" "mutex" (mutex-name mutex))
  (mutex-specific-set! mutex "mutex-specific")
  (test-equal "mutex-specific" "mutex-specific" (mutex-specific mutex))
  (test-assert "mutex-lock!" (mutex-lock! mutex))
  (test-equal "mutex-state owned" (current-thread) (mutex-state mutex))
  (test-equal "mutex-lock! timeout" #f (mutex-lock! mutex 0 #f))
  (test-assert "mutex-unlock!" (mutex-unlock! mutex))
  (test-equal "mutex-state unlocked" 'not-abandoned (mutex-state mutex))

  (define condition-variable
    (make-condition-variable "condition-variable"))
  (test-assert "condition-variable?"
               (condition-variable? condition-variable))
  (test-equal "condition-variable-name"
              "condition-variable"
              (condition-variable-name condition-variable))
  (condition-variable-specific-set! condition-variable "cv-specific")
  (test-equal "condition-variable-specific"
              "cv-specific"
              (condition-variable-specific condition-variable))
  (condition-variable-signal! condition-variable)
  (condition-variable-broadcast! condition-variable)

  (define now (current-time))
  (test-assert "time?" (time? now))
  (test-assert "time->seconds"
               (> (time->seconds now) 0))
  (test-assert "seconds->time"
               (time? (seconds->time (+ 0.001 (time->seconds now)))))

  (define new-thread
    (make-thread
      (lambda ()
        "never-started")))
  (thread-terminate! new-thread)
  (define terminated-error
    (engarde BaseException
      (lambda (error) error)
      (lambda ()
        (thread-join! new-thread))))
  (test-assert "terminated-thread-exception?"
               (terminated-thread-exception? terminated-error))

  (thread-yield!))

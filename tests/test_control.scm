(import (scheme base)
        (srfi 64)
        (srfi 177)
        (only (srfi 18) current-exception-handler)
        (only hissp_scheme.runtime.control_runtime ContinuationError))

;; ---------------------------------------------------------------------------
;; Tail calls
;; ---------------------------------------------------------------------------

(define (tc-count-down n)
  (if (= n 0)
    'done
    (tc-count-down (- n 1))))

(define (tc-even? n)
  (if (= n 0) #t (tc-odd? (- n 1))))

(define (tc-odd? n)
  (if (= n 0) #f (tc-even? (- n 1))))

(define (tc-internal-even? n)
  (define (ev? n)
    (if (= n 0) #t (od? (- n 1))))
  (define (od? n)
    (if (= n 0) #f (ev? (- n 1))))
  (ev? n))

(define (tc-named-let-sum n)
  (let loop ((i 0) (acc 0))
    (if (= i n)
      acc
      (loop (+ i 1) (+ acc i)))))

(define (tc-cond-loop n)
  (cond
    ((= n 0) 'cond-done)
    (else (tc-cond-loop (- n 1)))))

(define (tc-cond-arrow-loop n)
  (cond
    ((= n 0) 'arrow-done)
    ((> n 0) => (lambda (ignored) (tc-cond-arrow-loop (- n 1))))))

(define (tc-case-loop n)
  (case (if (= n 0) "zero" "more")
    (("zero") 'case-done)
    (else (tc-case-loop (- n 1)))))

(define (tc-and-loop n)
  (if (= n 0) 'and-done (and #t (tc-and-loop (- n 1)))))

(define (tc-or-loop n)
  (if (= n 0) 'or-done (or #f (tc-or-loop (- n 1)))))

(define (tc-when-loop n)
  (if (= n 0) 'when-done (when #t (tc-when-loop (- n 1)))))

(define (tc-unless-loop n)
  (if (= n 0) 'unless-done (unless #f (tc-unless-loop (- n 1)))))

(define (tc-let-loop n)
  (if (= n 0)
    'let-done
    (let ((next (- n 1)))
      (tc-let-loop next))))

(define (tc-let*-loop n)
  (if (= n 0)
    'let*-done
    (let* ((a (- n 1))
           (b a))
      (tc-let*-loop b))))

(define (tc-do-sum n)
  (do ((i 0 (+ i 1))
       (acc 0 (+ acc i)))
      ((= i n) acc)))

(define (tc-apply-loop n)
  (if (= n 0)
    'apply-done
    (apply tc-apply-loop (list (- n 1)))))

(define (tc-lambda-loop n)
  ((lambda (m)
     (if (= m 0) 'lambda-done (tc-lambda-loop (- m 1))))
   n))

(test-group "tail calls"
  (test-equal "self tail call" 'done (tc-count-down 200000))
  (test-equal "named let 1,000,000 iterations"
              499999500000
              (tc-named-let-sum 1000000))
  (test-equal "mutual top-level tail calls" #t (tc-even? 100000))
  (test-equal "mutual top-level tail calls odd" #f (tc-odd? 100000))
  (test-equal "mutual internal-define tail calls" #t (tc-internal-even? 100000))
  (test-equal "cond tail" 'cond-done (tc-cond-loop 100000))
  (test-equal "cond => tail" 'arrow-done (tc-cond-arrow-loop 100000))
  (test-equal "case tail" 'case-done (tc-case-loop 100000))
  (test-equal "and tail" 'and-done (tc-and-loop 100000))
  (test-equal "or tail" 'or-done (tc-or-loop 100000))
  (test-equal "when tail" 'when-done (tc-when-loop 100000))
  (test-equal "unless tail" 'unless-done (tc-unless-loop 100000))
  (test-equal "let body tail" 'let-done (tc-let-loop 100000))
  (test-equal "let* body tail" 'let*-done (tc-let*-loop 100000))
  (test-equal "do loop" 4999950000 (tc-do-sum 100000))
  (test-equal "apply tail" 'apply-done (tc-apply-loop 100000))
  (test-equal "immediate lambda tail" 'lambda-done (tc-lambda-loop 100000)))

;; ---------------------------------------------------------------------------
;; Derived binding forms
;; ---------------------------------------------------------------------------

(test-group "binding forms"
  (test-equal "let*" 3 (let* ((a 1) (b (+ a 1))) (+ a b)))
  (test-equal "letrec"
              #t
              (letrec ((ev? (lambda (n) (if (= n 0) #t (od? (- n 1)))))
                       (od? (lambda (n) (if (= n 0) #f (ev? (- n 1))))))
                (ev? 10)))
  (test-equal "letrec*" 2 (letrec* ((a 1) (b (+ a 1))) b))
  (test-equal "named let" '(3 2 1)
              (let build ((n 1) (acc '()))
                (if (> n 3) acc (build (+ n 1) (cons n acc)))))
  (test-equal "do with body" '(2 1 0)
              (let ((acc '()))
                (do ((i 0 (+ i 1)))
                    ((= i 3) acc)
                  (set! acc (cons i acc))))))

;; ---------------------------------------------------------------------------
;; Escape continuations
;; ---------------------------------------------------------------------------

(define (tc-find-first pred lst)
  (call/cc
    (lambda (escape)
      (let loop ((rest lst))
        (unless (null? rest)
          (when (pred (car rest))
            (escape (car rest)))
          (loop (cdr rest))))
      #f)))

(define (tc-find-pair target rows)
  (call-with-current-continuation
    (lambda (escape)
      (let outer ((rows rows))
        (unless (null? rows)
          (let inner ((cols (car rows)))
            (unless (null? cols)
              (when (= (car cols) target)
                (escape (list 'found target)))
              (inner (cdr cols))))
          (outer (cdr rows))))
      'missing)))

(define tc-saved-k #f)

(test-group "escape continuations"
  (test-equal "call/cc normal return" 5 (call/cc (lambda (k) 5)))
  (test-equal "call/cc escape value" 7 (+ 1 (call/cc (lambda (k) (k 6) 100))))
  (test-equal "early exit from loop" 3 (tc-find-first (lambda (x) (> x 2)) '(1 2 3 4)))
  (test-equal "no exit" #f (tc-find-first (lambda (x) (> x 9)) '(1 2 3)))
  (test-equal "escape from nested loops" '(found 5) (tc-find-pair 5 '((1 2) (3 4) (5 6))))
  (test-equal "nested loops miss" 'missing (tc-find-pair 9 '((1 2) (3 4))))
  (test-equal "inner continuation escapes outer call/cc"
              'outer
              (call/cc
                (lambda (outer)
                  (call/cc
                    (lambda (inner)
                      (outer 'outer)))
                  'not-reached)))
  (test-equal "multiple values through continuation"
              '(1 2)
              (call-with-values
                (lambda () (call/cc (lambda (k) (k 1 2))))
                list))
  (test-error "re-entering an exited continuation"
              ContinuationError
              (begin
                (call/cc (lambda (k) (set! tc-saved-k k) 1))
                (tc-saved-k 2))))

;; ---------------------------------------------------------------------------
;; values
;; ---------------------------------------------------------------------------

(test-group "values"
  (test-equal "call-with-values" 3 (call-with-values (lambda () (values 1 2)) +))
  (test-equal "single value" 4 (values 4))
  (test-equal "zero values to consumer" '() (call-with-values (lambda () (values)) list)))

;; ---------------------------------------------------------------------------
;; dynamic-wind
;; ---------------------------------------------------------------------------

(define (tc-wind-normal)
  (let ((trace '()))
    (define (note! x) (set! trace (cons x trace)))
    (dynamic-wind
      (lambda () (note! 'before))
      (lambda () (note! 'during))
      (lambda () (note! 'after)))
    (reverse trace)))

(define (tc-wind-escape)
  (let ((trace '()))
    (define (note! x) (set! trace (cons x trace)))
    (call/cc
      (lambda (k)
        (dynamic-wind
          (lambda () (note! 'before))
          (lambda () (k 'escaped) (note! 'unreachable))
          (lambda () (note! 'after)))))
    (note! 'resumed)
    (reverse trace)))

(define (tc-wind-error)
  (let ((trace '()))
    (define (note! x) (set! trace (cons x trace)))
    (guard (e (#t (note! 'caught)))
      (dynamic-wind
        (lambda () (note! 'before))
        (lambda () (car 1))
        (lambda () (note! 'after))))
    (reverse trace)))

(test-group "dynamic-wind"
  (test-equal "dynamic-wind result" 'during
              (dynamic-wind (lambda () #f) (lambda () 'during) (lambda () #f)))
  (test-equal "normal order" '(before during after) (tc-wind-normal))
  (test-equal "escape runs after" '(before after resumed) (tc-wind-escape))
  (test-equal "python error runs after" '(before after caught) (tc-wind-error)))

;; ---------------------------------------------------------------------------
;; Exceptions
;; ---------------------------------------------------------------------------

(test-group "exceptions"
  (test-equal "guard catches raised symbol" 'boom (guard (e (#t e)) (raise 'boom)))
  (test-equal "guard clause test"
              '(caught boom)
              (guard (e ((= e 'other) 'wrong)
                        ((= e 'boom) (list 'caught e)))
                (raise 'boom)))
  (test-equal "guard else" 'fallback (guard (e ((= e 'other) 'wrong) (else 'fallback)) (raise 'boom)))
  (test-equal "guard => clause" 'boom (guard (e ((= e 'boom) => (lambda (ignored) e))) (raise 'boom)))
  (test-equal "guard body value" 3 (guard (e (#t 'raised)) (+ 1 2)))
  (test-equal "guard error object"
              (list "bad thing" '(1 2))
              (guard (e ((error-object? e)
                         (list (error-object-message e) (error-object-irritants e))))
                (error "bad thing" 1 2)))
  (test-equal "guard catches python TypeError"
              'type-error
              (guard (e ((isinstance e TypeError) 'type-error))
                (car 1)))
  (test-assert "python exceptions are error objects"
               (guard (e (#t (error-object? e))) (car 1)))
  (test-error "guard with no matching clause re-raises"
              #t
              (guard (e ((= e 'other) 'wrong)) (raise 'boom)))
  (test-equal "nested guard re-raise reaches outer"
              '(outer boom)
              (guard (outer-e (#t (list 'outer outer-e)))
                (guard (inner-e ((= inner-e 'other) 'wrong))
                  (raise 'boom))))
  (test-equal "with-exception-handler and raise-continuable"
              43
              (with-exception-handler
                (lambda (condition) 42)
                (lambda () (+ (raise-continuable 'oops) 1))))
  (test-equal "with-exception-handler escape through call/cc"
              '(handled bad)
              (call/cc
                (lambda (k)
                  (with-exception-handler
                    (lambda (e) (k (list 'handled e)))
                    (lambda () (raise 'bad))))))
  (test-equal "with-exception-handler sees python errors"
              'saw-type-error
              (call/cc
                (lambda (k)
                  (with-exception-handler
                    (lambda (e) (k (if (isinstance e TypeError) 'saw-type-error 'other)))
                    (lambda () (car 1))))))
  (test-equal "handler runs with outer handler installed"
              '(outer inner-value)
              (call/cc
                (lambda (k)
                  (with-exception-handler
                    (lambda (e) (k (list 'outer e)))
                    (lambda ()
                      (with-exception-handler
                        (lambda (e) (raise 'inner-value))
                        (lambda () (raise 'first))))))))
  (test-error "handler returning from raise is an error"
              #t
              (with-exception-handler
                (lambda (e) 'returned)
                (lambda () (raise 'non-continuable))))
  (test-assert "error-object? false for non-errors" (not (error-object? 'sym)))
  (test-assert "file-error?"
               (guard (e (#t (file-error? e)))
                 (open "/nonexistent/hissp-scheme/file.txt")))
  (test-error "uncaught error" #t (raise 'uncaught))
  (test-assert "srfi-18 shares the base handler stack"
               (let ((handler (lambda (e) e)))
                 (with-exception-handler
                   handler
                   (lambda () (eq? (current-exception-handler) handler))))))

;; ---------------------------------------------------------------------------
;; Parameters
;; ---------------------------------------------------------------------------

(define tc-param (make-parameter 10))
(define tc-doubled (make-parameter 5 (lambda (x) (* x 2))))

(test-group "parameterize"
  (test-equal "initial value" 10 (tc-param))
  (test-equal "parameterize binds" 20 (parameterize ((tc-param 20)) (tc-param)))
  (test-equal "restored after exit" 10 (tc-param))
  (test-equal "escape out of parameterize"
              'out
              (call/cc (lambda (k) (parameterize ((tc-param 30)) (k 'out)))))
  (test-equal "restored after escape" 10 (tc-param))
  (test-equal "converter on initial value" 10 (tc-doubled))
  (test-equal "converter on parameterize" 6 (parameterize ((tc-doubled 3)) (tc-doubled))))

;; ---------------------------------------------------------------------------
;; Local binding
;; ---------------------------------------------------------------------------

(define (tc-make-counter)
  (let ((tc-local-count 0))
    (lambda ()
      (set! tc-local-count (+ tc-local-count 1))
      tc-local-count)))

(define tc-counter (tc-make-counter))

(define (tc-bump-formal tc-formal-value)
  (set! tc-formal-value (+ tc-formal-value 1))
  tc-formal-value)

(define (tc-internal-helper-user)
  (define (tc-hidden-helper) 7)
  (tc-hidden-helper))

(test-group "local binding"
  (test-equal "closure counter first" 1 (tc-counter))
  (test-equal "closure counter second" 2 (tc-counter))
  (test-assert "local set! does not create a global"
               (not (operator..contains (builtins..globals) 'tc-local-count)))
  (test-equal "set! on a formal" 6 (tc-bump-formal 5))
  (test-assert "formal set! does not create a global"
               (not (operator..contains (builtins..globals) 'tc-formal-value)))
  (test-equal "internal define" 7 (tc-internal-helper-user))
  (test-assert "internal define does not leak"
               (not (operator..contains (builtins..globals) 'tc-hidden-helper))))

;; ---------------------------------------------------------------------------
;; Python interop
;; ---------------------------------------------------------------------------

(test-group "interop"
  (test-equal "scheme procedure as sorted key"
              (vector 3 2 1)
              (call/kw sorted (vector 1 3 2) (key (lambda (x) (- 0 x)))))
  (test-equal "python calling a tail-recursive procedure"
              (vector 'done)
              (builtins..list (builtins..map tc-count-down (vector 50000))))
  (test-assert "procedures are callable" (callable tc-count-down))
  (test-assert "procedure?" (procedure? tc-count-down))
  (test-equal "procedure name" "tc-count-down" (hissp..demunge (getattr tc-count-down "__name__"))))

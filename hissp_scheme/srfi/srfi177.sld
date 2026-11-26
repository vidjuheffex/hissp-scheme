;; SRFI-177-inspired keyword argument support.
;;
;; This file owns the keyword-call macro surface. It is Scheme source: the
;; public names are declared with `(define-library ...)`, and the macro helpers
;; are ordinary Scheme definitions evaluated at macro-expansion time.

(define-library (srfi 177)
  (export call/kw lambda/kw define/kw)
  (import (scheme base)
          (only hissp demunge)
          (only itertools chain))
  (begin
    (define (scheme-python-name symbol)
      (if (not (isinstance symbol str))
        (throw (SyntaxError "keyword names must be symbols"))
        (.replace (demunge symbol) "-" "_")))

    (define (keyword-string-form name)
      (.format "({!r})" name))

    (define (call-keyword-dict-form spec)
      (if (and (isinstance spec tuple)
               (= (len spec) 2)
               (= (op#getitem spec 0) 'QzSTAR_QzSTAR_))
        (op#getitem spec 1)
        (begin
          (define (loop index seen items)
            (if (>= index (len spec))
              (+ (tuple (@ 'QzPCENT_)) items)
              (let ((symbol (op#getitem spec index))
                    (value (op#getitem spec (+ index 1))))
                (let ((name (scheme-python-name symbol)))
                  (when (op#contains seen name)
                    (throw
                      (SyntaxError
                        (.format "duplicate call/kw keyword: {}"
                                 (demunge symbol)))))
                  (loop (+ index 2)
                        (+ seen (tuple (@ name)))
                        (+ items (tuple (@ (keyword-string-form name) value))))))))
          (unless (isinstance spec tuple)
            (throw (SyntaxError
                     "call/kw keyword arguments must be a final list: (name value ...) or (** mapping)")))
          (unless (= (op#mod (len spec) 2) 0)
            (throw (SyntaxError
                     "call/kw keyword argument list must contain name/value pairs")))
          (loop 0 () ()))))

    (define (lambda-keyword-default name)
      (.format "{}=False" name))

    (define (last-item values)
      (if (null? (cdr values))
        (car values)
        (last-item (cdr values))))

    (define (drop-last values)
      (if (null? (cdr values))
        '()
        (cons (car values) (drop-last (cdr values)))))

    (define (lambda-kw-params formals)
      (define positional formals)
      (define keywords ())
      (define (check-formal formal)
        (unless (isinstance formal str)
          (throw (SyntaxError "lambda/kw formals and keywords must be symbols"))))
      (unless (isinstance formals tuple)
        (throw (SyntaxError "lambda/kw formals must be a list")))
      (when (and (> (len formals) 0) (isinstance (op#getitem formals -1) tuple))
        (set! positional (op#getitem formals (slice 0 -1)))
        (set! keywords (op#getitem formals -1)))
      (tuple (builtins..map check-formal (+ positional keywords)))
      (if (> (len keywords) 0)
        (+ (+ positional (tuple (@ "*")))
           (tuple (builtins..map lambda-keyword-default keywords)))
        positional))

    (define (call/kw-transformer function . args)
      ;; Literal keywords:
      ;;
      ;;   (call/kw dumps payload (indent 2 sort-keys #t))
      ;;
      ;; Dynamic keyword mapping:
      ;;
      ;;   (call/kw dumps payload (** options))
      (unless (not (null? args))
        (throw (SyntaxError "call/kw requires a final keyword argument list")))
      (let ((positional (drop-last args))
            (keywords (call-keyword-dict-form (last-item args))))
        (tuple
          (chain
            (@ function)
            positional
            (@ ': ':** keywords)))))

    (define-syntax call/kw
      (syntax-case call/kw-transformer))

    (define (lambda/kw-transformer formals . body)
      (tuple
        (chain
          (@ 'hissp.macros.._macro_.fun
             'lambdaQzSOL_kw
             (tuple (lambda-kw-params formals)))
          body)))

    (define-syntax lambda/kw
      (syntax-case lambda/kw-transformer))

    (define (define/kw-transformer head . body)
      (unless (and (isinstance head tuple) head)
        (throw (SyntaxError "define/kw requires a function head")))
      (tuple
        (chain
          (@ 'hissp.macros.._macro_.defun
             (op#getitem head 0)
             (tuple (lambda-kw-params
                      (op#getitem head (slice 1 None)))))
          body)))

    (define-syntax define/kw
      (syntax-case define/kw-transformer))))

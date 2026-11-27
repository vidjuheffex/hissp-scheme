(import (scheme base)
        (scheme inexact)
        (srfi 64)
        (srfi 177)
        (scheme char)
        (scheme cxr)
        (only hissp_scheme.runtime.printer write-string display-string))

;; ---------------------------------------------------------------------------
;; Definitions used by the tests below
;; ---------------------------------------------------------------------------

(begin
  (define r7-top-x 1)
  (define r7-top-y 2))

(define (r7-body-begin)
  (begin
    (define r7-inner-a 10)
    (begin (define r7-inner-b 20)))
  (+ r7-inner-a r7-inner-b))

(define (r7-keyword-formals return class)
  (list return class))

(define def 5)

(define (r7-sum-with-for-each items)
  (let ((total 0))
    (for-each (lambda (x) (set! total (+ total x))) items)
    total))

(define r7-quoted '("x" y 1 #t (nested "z")))
(define r7-mutable (list 1 2 3))
(list-set! r7-mutable 1 'two)

(define (r7-values->list thunk)
  (call-with-values thunk list))

(define (r7-shadowed-plus + a b)
  (+ a b))

(define (r7-let-shadowed-less)
  (let ((< (lambda (a b) 'mine)))
    (< 1 2)))

(define (r7-inline-sum a b)
  (+ a b))

(define (r7-let-shadow x)
  (list (let ((x (* x 10))) x) x))

(define (r7-let-inits-see-outer x)
  (let ((x 1) (y x)) (list x y)))

(define (r7-let-closures n)
  ;; Each loop iteration is its own call, so each closure keeps its own `v`.
  (let loop ((i 0) (acc '()))
    (if (= i n)
      (map (lambda (thunk) (thunk)) acc)
      (let ((v (* i i)))
        (loop (+ i 1) (cons (lambda () v) acc))))))

(define (r7-let-set x)
  (let ((y x))
    (set! y (+ y 1))
    ((lambda () (set! y (* y 2))))
    y))

(define (r7-let-tail n)
  (let ((m (- n 1)))
    (if (= n 0) 'done (r7-let-tail m))))

(define r7-top-let (let ((secret 41)) (lambda () (+ secret 1))))

;; `list` is a parameter here, so the tail call through it must stay a proper
;; tail call even though the global `list` is a Python function.
(define (r7-param-shadows-global n list)
  (if (= n 0) 'done (list (- n 1) list)))

(define (r7-apply-loop n)
  (if (= n 0) 'done (apply r7-apply-loop (list (- n 1)))))

;; A local with the same name as a keyword must not rename the keyword.
(define (r7-kw-let triangles)
  (let ((triangles (+ triangles 1)))
    (call/kw dict (triangles triangles))))

(define (r7-kw-cell n)
  (let ((n n))
    (set! n (* n 2))
    (call/kw dict (n n))))

(define (r7-kw-internal-define)
  (define size 4)
  (call/kw dict (size size)))

(define (r7-kw-mapping)
  (let ((options (dict)))
    (op#setitem options "color" "red")
    (call/kw dict (** options))))

(define (r7-lambda-kw-shadow)
  (let ((scale 10))
    (list ((lambda/kw (x (scale)) (list x scale)) 1)
          (call/kw (lambda/kw (x (scale)) (list x scale)) 1 (scale 2))
          scale)))

;; `repeat` and `accumulate` start out as Hissp prelude (itertools) globals.
(define (repeat n)
  (if (= n 0) 'done (repeat (- n 1))))

(define (r7-ping n)
  (if (= n 0) 'done (accumulate (- n 1))))

(define (accumulate n)
  (r7-ping n))

(define (r7-tail-builtin n)
  (if (= n 0) '() (cons n (r7-tail-builtin (- n 1)))))

;; ---------------------------------------------------------------------------
;; Tests
;; ---------------------------------------------------------------------------

(test-group "r7rs truthiness"
  (test-equal 'yes (if 0 'yes 'no))
  (test-equal 'yes (if '() 'yes 'no))
  (test-equal 'yes (if "" 'yes 'no))
  (test-equal 'no (if #f 'yes 'no))
  (test-equal 0 (and 1 0))
  (test-equal 0 (or #f 0))
  (test-equal 'ran (when 0 'ran))
  (test-equal #f (unless 0 'ran))
  (test-equal 'zero (cond (0 'zero) (else 'other)))
  (test-equal 'empty (cond ((list) 'empty) (else 'other)))
  (test-equal #f (not 0))
  (test-equal #f (not '()))
  (test-equal #t (not #f))
  (test-equal #t (boolean? #f))
  (test-equal #f (boolean? 0))
  (test-equal #f (boolean? '()))
  (test-equal #t (boolean=? #t #t #t))
  (test-equal #f (boolean=? #t #f)))

(test-group "r7rs quoted data"
  (test-assert (string? (car r7-quoted)))
  (test-equal "x" (car r7-quoted))
  (test-assert (symbol? (cadr r7-quoted)))
  (test-equal 1 (caddr r7-quoted))
  (test-equal #t (cadddr r7-quoted))
  (test-equal "z" (cadr (car (cddddr r7-quoted))))
  (test-equal 'quote (car ''x))
  (test-equal (list 'quote 'x) ''x)
  (test-equal (list 'a 3 "s") `(a ,(+ 1 2) "s"))
  (test-equal (cons 'a 'b) '(a . b)))

(test-group "r7rs begin"
  (test-equal 3 (+ r7-top-x r7-top-y))
  (test-equal 30 (r7-body-begin))
  (test-assert (not (op#contains (builtins..globals) 'r7-inner-a))))

(test-group "r7rs keyword identifiers"
  (test-equal '(1 2) (r7-keyword-formals 1 2))
  (test-equal 6 (let ((in 1) (is 2) (pass 3)) (+ in is pass)))
  (test-equal 3 (let loop ((for 0)) (if (= for 3) for (loop (+ for 1)))))
  (test-equal 5 def)
  (test-equal "return" (symbol->string 'return))
  (test-assert (eq? 'return (string->symbol "return"))))

(test-group "r7rs symbols"
  (test-equal #t (symbol? 'abc))
  (test-equal #f (symbol? "abc"))
  (test-equal #f (string? 'abc))
  (test-equal "list->vector" (symbol->string 'list->vector))
  (test-assert (eq? 'abc (string->symbol "abc")))
  (test-equal "hello world" (symbol->string (string->symbol "hello world")))
  (test-equal #t (symbol=? 'a 'a 'a))
  (test-equal #f (symbol=? 'a 'b))
  (test-equal #f (equal? 'a "a"))
  (test-equal #t (eqv? 'a 'a))
  (test-equal 'yellow
              (case 'banana
                ((apple) 'red)
                ((banana cherry) 'yellow)
                (else 'unknown)))
  (test-equal 'inexact (case 2.0 ((2) 'exact) (else 'inexact))))

(test-group "r7rs equivalence"
  (test-equal #f (eqv? 2 2.0))
  (test-equal #t (eqv? 100000000000000000000 100000000000000000000))
  (test-equal #f (eqv? #t 1))
  (test-equal #t (eq? '() '()))
  (test-equal #t (equal? "abc" "abc"))
  (test-equal #t (equal? (list 1 (list 2 (vector 3 "x"))) (list 1 (list 2 (vector 3 "x")))))
  (test-equal #f (equal? (list 1 2) (list 1 2.0))))

(test-group "r7rs printer"
  (test-equal "(a \"b\" #t #f 1/2 #(1 2) 2.5 list->vector (1 . 2))"
              (write-string (list 'a "b" #t #f 1/2 (vector 1 2) 2.5 'list->vector (cons 1 2))))
  (test-equal "(a b)" (display-string (list "a" 'b)))
  (test-equal "\"line\\n\"" (write-string "line\n"))
  (test-equal "+inf.0" (write-string +inf.0)))

(test-group "r7rs arithmetic"
  (test-equal 1/2 (/ 1 2))
  (test-equal #t (exact? (/ 1 2)))
  (test-equal #t (exact-integer? (/ 6 3)))
  (test-equal 1/2 (/ 2))
  (test-equal 0.5 (/ 1.0 2))
  (test-equal +inf.0 (/ 1.0 0))
  (test-error ZeroDivisionError (/ 1 0))
  (test-equal #t (exact-integer? (+ 1/2 1/2)))
  (test-equal 2 (* 1/2 4))
  (test-equal -1/2 (- 1/2))
  (test-equal 0 (+))
  (test-equal 1 (*))
  (test-equal 10 (+ 1 2 3 4))
  (test-equal 7 (- 10 1 2))
  (test-equal #t (< 1 2 3))
  (test-equal #f (< 1 3 2))
  (test-equal #t (= 1 1.0 1))
  (test-equal #t (>= 3 3 2))
  (test-equal -3 (quotient -7 2))
  (test-equal -1 (remainder -7 2))
  (test-equal 1 (modulo -7 2))
  (test-equal -1 (modulo 7 -2))
  (test-equal '(-4 1) (r7-values->list (lambda () (floor/ -7 2))))
  (test-equal '(-3 -1) (r7-values->list (lambda () (truncate/ -7 2))))
  (test-equal '(4 1) (r7-values->list (lambda () (exact-integer-sqrt 17))))
  (test-equal 6 (gcd 12 18))
  (test-equal 0 (gcd))
  (test-equal 12 (lcm 4 6))
  (test-equal 2.0 (max 1 2.0))
  (test-equal 1 (min 1 2))
  (test-equal 1/2 (abs -1/2))
  (test-equal 3 (numerator 6/4))
  (test-equal 2 (denominator 6/4))
  (test-equal -4.0 (floor -3.5))
  (test-equal 1 (ceiling 1/2))
  (test-equal 2.0 (round 2.5))
  (test-equal 4 (round 7/2))
  (test-equal -2.0 (truncate -2.7))
  (test-equal 1024 (expt 2 10))
  (test-equal 1/4 (expt 2 -2))
  (test-equal 1/4 (square 1/2))
  (test-equal 4 (sqrt 16))
  (test-equal #t (exact-integer? (sqrt 16)))
  (test-equal 2/3 (sqrt 4/9))
  (test-equal #t (inexact? (sqrt 2)))
  (test-equal (builtins..complex 0 2) (sqrt -4)))

(test-group "r7rs numeric predicates and conversion"
  (test-equal #f (number? #t))
  (test-equal #t (number? 1/2))
  (test-equal #t (integer? 2.0))
  (test-equal #f (integer? 1/2))
  (test-equal #t (rational? 1/2))
  (test-equal #f (rational? +inf.0))
  (test-equal #t (real? 1.5))
  (test-equal #t (nan? +nan.0))
  (test-equal #t (infinite? -inf.0))
  (test-equal #t (finite? 1/2))
  (test-equal #t (exact? 1/2))
  (test-equal #t (inexact? 0.5))
  (test-equal #t (zero? 0.0))
  (test-equal #t (odd? -3))
  (test-equal 5/2 (exact 2.5))
  (test-equal #t (exact-integer? (exact 2.0)))
  (test-equal 0.25 (inexact 1/4))
  (test-equal 0.5 (exact->inexact 1/2))
  (test-equal 1/3 (string->number "1/3"))
  (test-equal 255 (string->number "#xff"))
  (test-equal 255 (string->number "ff" 16))
  (test-equal 3/2 (string->number "#e1.5"))
  (test-equal 100.0 (string->number "1e2"))
  (test-equal -inf.0 (string->number "-inf.0"))
  (test-equal #f (string->number "abc"))
  (test-equal "ff" (number->string 255 16))
  (test-equal "1/3" (number->string 1/3))
  (test-equal "2.5" (number->string 2.5))
  (test-equal "+inf.0" (number->string +inf.0))
  (test-equal 31 #x1F)
  (test-equal 3/2 #e1.5))

(test-group "r7rs integrated primitives"
  (test-equal '(1 2) (r7-shadowed-plus list 1 2))
  (test-equal 'mine (r7-let-shadowed-less))
  (test-equal 1 (r7-inline-sum 1/2 1/2))
  (test-equal #t (exact-integer? (r7-inline-sum 1/2 1/2)))
  (test-equal 1/2 (- 1 1/2))
  (test-equal #t (exact-integer? (* 2/3 3/2)))
  (test-equal 2.5 (r7-inline-sum 2 0.5))
  (test-equal "ab" (r7-inline-sum "a" "b"))
  (test-equal 6 (apply + '(1 2 3)))
  (test-equal #t (< 1 (+ 1 1) 3)))

(test-group "r7rs let"
  (test-equal '(20 2) (r7-let-shadow 2))
  (test-equal '(1 5) (r7-let-inits-see-outer 5))
  (test-equal '(4 1 0) (r7-let-closures 3))
  (test-equal 12 (r7-let-set 5))
  (test-equal 'done (r7-let-tail 50000))
  (test-equal 42 (r7-top-let))
  (test-equal 3 (let* ((a 1) (b (+ a 1))) (+ a b)))
  (test-equal 'b (or #f (let ((x 'b)) x)))
  (test-equal '(x "x") (let ((sym 'x) (str "x")) (list sym str))))

(test-group "r7rs tail calls"
  (test-equal 'done (r7-param-shadows-global 50000 r7-param-shadows-global))
  (test-equal 'done (r7-apply-loop 50000))
  (test-equal '(3 2 1) (r7-tail-builtin 3))
  (test-equal 'done (repeat 50000))
  (test-equal 'done (r7-ping 50000)))

(test-group "srfi-177 keywords next to local bindings"
  (test-equal (call/kw dict (triangles 4)) (r7-kw-let 3))
  (test-equal (call/kw dict (n 6)) (r7-kw-cell 3))
  (test-equal (call/kw dict (size 4)) (r7-kw-internal-define))
  (test-equal (call/kw dict (color "red")) (r7-kw-mapping))
  (test-equal '((1 #f) (1 2) 10) (r7-lambda-kw-shadow)))

(test-group "r7rs scheme char"
  (test-equal #\A (char-upcase #\a))
  (test-equal #\a (char-downcase #\A))
  (test-assert (char-alphabetic? #\a))
  (test-assert (char-numeric? #\7))
  (test-assert (char-whitespace? #\space))
  (test-equal 7 (digit-value #\7))
  (test-equal #f (digit-value #\a))
  (test-equal "HELLO" (string-upcase "hello"))
  (test-assert (string-ci=? "Hello" "hELLO" "HELLO"))
  (test-assert (char-ci=? #\a #\A)))

(test-group "r7rs long quoted list"
  (test-equal 300 (length '(0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 233 234 235 236 237 238 239 240 241 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257 258 259 260 261 262 263 264 265 266 267 268 269 270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 285 286 287 288 289 290 291 292 293 294 295 296 297 298 299)))
  (test-equal 299 (list-ref '(0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 233 234 235 236 237 238 239 240 241 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257 258 259 260 261 262 263 264 265 266 267 268 269 270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 285 286 287 288 289 290 291 292 293 294 295 296 297 298 299) 299)))

(test-group "r7rs lists"
  (test-equal '(11 22 33) (map + '(1 2 3) '(10 20 30)))
  (test-equal '(1 4 9) (map (lambda (x) (* x x)) '(1 2 3)))
  (test-equal '(2 4) (map + '(1 2) '(1 2 3)))
  (test-equal 6 (r7-sum-with-for-each '(1 2 3)))
  (test-equal '(c d) (memq 'c '(a b c d)))
  (test-equal #f (memq 'z '(a b)))
  (test-equal '(101 102) (memv 101 '(100 101 102)))
  (test-equal '("b") (member "b" (list "a" "b")))
  (test-equal '(2 3) (member 2.0 '(1 2 3) =))
  (test-equal '(b 2) (assq 'b '((a 1) (b 2))))
  (test-equal '(5 7) (assv 5 '((2 3) (5 7))))
  (test-equal '("b" 2) (assoc "b" (list (list "a" 1) (list "b" 2))))
  (test-equal '(2 4) (assoc 2.0 '((1 1) (2 4)) =))
  (test-equal #t (list? '(1 2)))
  (test-equal #t (list? '()))
  (test-equal #f (list? (cons 1 2)))
  (test-equal '(x x) (make-list 2 'x))
  (test-equal '(3 4) (list-tail '(1 2 3 4) 2))
  (test-equal '(1 two 3) r7-mutable)
  (test-equal '(1 2 3) (list-copy '(1 2 3)))
  (test-equal #f (let ((items (list 1 2))) (eq? items (list-copy items))))
  (test-equal (vector 11 22) (vector-map + (vector 1 2) (vector 10 20)))
  (test-equal 3 (let ((count 0))
                  (vector-for-each (lambda (x) (set! count (+ count x))) (vector 1 2))
                  count)))

(define (r7-vector-sum items)
  (let loop ((i 0) (total 0))
    (if (= i (vector-length items))
        total
        (loop (+ i 1) (+ total (vector-ref items i))))))

(define (r7-scale! items factor)
  (do ((i 0 (+ i 1)))
      ((= i (vector-length items)) items)
    (vector-set! items i (* (vector-ref items i) factor))))

(test-group "r7rs integrated vectors and operands"
  (test-equal 6 (r7-vector-sum (vector 1 2 3)))
  (test-equal (vector 2 4 6) (r7-scale! (vector 1 2 3) 2))
  (test-equal 20 (* (+ 1 (r7-vector-sum (vector 1 2 1))) (- 10 6)))
  (test-equal #t (< (car '(1)) (cadr '(1 2))))
  (test-equal '(a b) (map vector-ref (list (vector 'a) (vector 'x 'b)) '(0 1)))
  (test-equal 'mine (let ((vector-ref (lambda (v i) 'mine)))
                      (vector-ref (vector 1) 0)))
  (test-error "vector-ref index out of range" IndexError
              (vector-ref (vector 1) (+ 1 1))))

(test-group "r7rs newline and list errors"
  (test-equal "\n" (let ((port (io..StringIO)))
                     (newline port)
                     (.getvalue port)))
  (test-error "length of a Python list" TypeError
              (length (builtins..list (vector 1 2))))
  (test-equal "expected a list, got list [1, 2] (Python lists are Scheme vectors)"
              (guard (e (#t (builtins..str e)))
                (length (vector 1 2))))
  (test-equal "expected proper list, got dotted tail 2"
              (guard (e (#t (builtins..str e)))
                (length (cons 1 2)))))

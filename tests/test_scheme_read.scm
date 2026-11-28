(import (scheme base)
        (scheme file)
        (scheme read)
        (scheme write)
        (srfi 64)
        (only pathlib Path)
        (only tempfile TemporaryDirectory))

(test-group "scheme read"
  (define temp-root (TemporaryDirectory))
  (define temp-dir temp-root.name)
  (define text-path (str (.joinpath (Path temp-dir) "scheme-read.txt")))

  (call-with-output-file
    text-path
    (lambda (port)
      (.write port "alpha\nbeta")))

  (test-equal "read-line from current input"
              "alpha"
              (with-input-from-file text-path (lambda () (read-line))))

  (test-equal "read-line from a port"
              '("alpha" "beta")
              (call-with-input-file text-path
                (lambda (port)
                  (let ((first (read-line port)))
                    (list first (read-line port))))))

  (test-equal "read-line prompt extension"
              '("prompt> " "beta")
              (let ((out (open-output-string)))
                (parameterize ((current-output-port out)
                               (current-input-port (open-input-string "beta\n")))
                  (let ((line (read-line "prompt> ")))
                    (list (get-output-string out) line)))))

  (.cleanup temp-root))

(define (read-from text)
  (read (open-input-string text)))

(define (read-all text)
  (let ((port (open-input-string text)))
    (let loop ((acc '()))
      (let ((datum (read port)))
        (if (eof-object? datum)
          (reverse acc)
          (loop (cons datum acc)))))))

(define (read-error-from text)
  (guard (e ((read-error? e) 'read-error))
    (read-from text)))

(test-group "read"
  (test-equal "list" '(a b c) (read-from "(a b c)"))
  (test-equal "dotted list" '(a b . c) (read-from "(a b . c)"))
  (test-equal "nested lists" '(1 (2 (3)) ()) (read-from "(1 (2 (3)) ())"))
  (test-equal "numbers"
              '(42 -7 1.5 1/3 31 5 3/2 1e3)
              (read-all "42 -7 1.5 1/3 #x1F #b101 #e1.5 1e3"))
  (test-assert "exact rational" (exact? (read-from "1/3")))
  (test-assert "inexact float" (inexact? (read-from "#i3")))
  (test-equal "string escapes"
              "a\nb\tA\"\\|"
              (read-from "\"a\\nb\\t\\x41;\\\"\\\\\\|\""))
  (test-equal "string line continuation"
              "abcdef"
              (read-from "\"abc\\\n    def\""))
  (test-equal "characters"
              (list #\a #\space #\A #\( #\newline #\x)
              (read-all "#\\a #\\space #\\x41 #\\( #\\newline #\\x"))
  (test-equal "booleans" '(#t #f #t #f) (read-all "#t #f #true #false"))
  (test-equal "vector" #(1 (2) "s" #(x)) (read-from "#(1 (2) \"s\" #(x))"))
  (test-equal "bytevector" (bytevector 1 2 255) (read-from "#u8(1 2 255)"))
  (test-equal "quote abbreviations"
              '((quote x) (quasiquote (a (unquote b) (unquote-splicing c))))
              (read-all "'x `(a ,b ,@c)"))
  (test-equal "comments"
              '(a b c)
              (read-from "( a ; line comment\n #| block #| nested |# |# b #;(skipped datum) c)"))
  (test-equal "bar symbol" "hello world" (symbol->string (read-from "|hello world|")))
  (test-assert "symbols are interned"
               (eq? 'list->vector (read-from "list->vector")))
  (test-equal "python keyword names" '(if lambda define) (read-from "(if lambda define)"))
  (test-assert "symbol, not string" (symbol? (read-from "abc")))
  (test-assert "string, not symbol" (string? (read-from "\"abc\"")))
  (test-equal "peculiar identifiers" '(+ - ... ->x) (read-from "(+ - ... ->x)"))
  (test-assert "eof on empty input" (eof-object? (read-from "")))
  (test-assert "eof after only comments" (eof-object? (read-from "  ; nothing\n#| here |#")))
  (test-equal "sequential data" '(1 (2) "three" four) (read-all "1 (2) \"three\" four"))

  (test-equal "leaves the rest of the port"
              '(abc #\space "rest")
              (let* ((port (open-input-string "abc rest"))
                     (datum (read port))
                     (char (read-char port)))
                (list datum char (read-line port))))

  (test-equal "fold-case directive persists on the port"
              '(abc def Ghi)
              (read-all "#!fold-case ABC DEF #!no-fold-case Ghi"))

  (test-assert "datum labels build shared structure"
               (let ((x (read-from "#0=(a . #0#)")))
                 (eq? x (cdr x))))
  (test-equal "datum label reference"
              '((1 2) (1 2))
              (read-from "(#1=(1 2) #1#)"))

  (test-equal "reads from current input"
              '(x y)
              (parameterize ((current-input-port (open-input-string "(x y)")))
                (read)))

  (test-equal "round trip through write"
              '(1 "two" #\3 (4 . 5) #(6) sym)
              (let ((out (open-output-string)))
                (write '(1 "two" #\3 (4 . 5) #(6) sym) out)
                (read-from (get-output-string out))))

  (test-equal "unterminated list" 'read-error (read-error-from "(a b"))
  (test-equal "unexpected close" 'read-error (read-error-from ")"))
  (test-equal "bad dotted list" 'read-error (read-error-from "(a . b c)"))
  (test-equal "unterminated string" 'read-error (read-error-from "\"abc"))
  (test-equal "bad bytevector" 'read-error (read-error-from "#u8(256)"))
  (test-equal "unknown character" 'read-error (read-error-from "#\\bogus"))
  (test-equal "undefined label" 'read-error (read-error-from "#3#")))

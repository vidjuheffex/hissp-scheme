(import (scheme base)
        (scheme write)
        (scheme file)
        (srfi 64)
        (only pathlib Path)
        (only tempfile TemporaryDirectory))

(define (output-of thunk)
  (let ((port (open-output-string)))
    (parameterize ((current-output-port port))
      (thunk))
    (get-output-string port)))

(test-group "eof object"
  (test-assert "eof-object?" (eof-object? (eof-object)))
  (test-equal "eof-object? other" #f (eof-object? '()))
  (test-assert "eof-object is unique" (eq? (eof-object) (eof-object)))
  (test-equal "write eof" "#<eof>"
              (output-of (lambda () (write (eof-object))))))

(test-group "input string ports"
  (define in (open-input-string "ab\ncd\r\n\nlast"))
  (test-equal "peek-char" #\a (peek-char in))
  (test-equal "peek-char does not consume" #\a (peek-char in))
  (test-equal "read-char" #\a (read-char in))
  (test-equal "read-line rest of line" "b" (read-line in))
  (test-equal "read-line strips crlf" "cd" (read-line in))
  (test-equal "read-line empty line" "" (read-line in))
  (test-equal "read-string partial" "la" (read-string 2 in))
  (test-equal "read-string short" "st" (read-string 10 in))
  (test-assert "read-char at eof" (eof-object? (read-char in)))
  (test-assert "peek-char at eof" (eof-object? (peek-char in)))
  (test-assert "read-line at eof" (eof-object? (read-line in)))
  (test-assert "read-string at eof" (eof-object? (read-string 1 in)))
  (test-equal "read-string zero" "" (read-string 0 in))
  (test-assert "char-ready?" (char-ready? in))

  (define peeked (open-input-string "xy\nz"))
  (peek-char peeked)
  (test-equal "read-line after peek" "xy" (read-line peeked))
  (peek-char peeked)
  (test-equal "read-string after peek" "z" (read-string 5 peeked))

  (define (count-chars port)
    (let loop ((n 0))
      (if (eof-object? (read-char port))
        n
        (loop (+ n 1)))))
  (test-equal "read loop" 5 (count-chars (open-input-string "hello"))))

(test-group "output string ports"
  (define out (open-output-string))
  (write-string "hello" out)
  (write-char #\space out)
  (write-string "abcdef" out 2)
  (write-string "abcdef" out 0 1)
  (newline out)
  (write 'sym out)
  (display " " out)
  (display 42 out)
  (test-equal "get-output-string" "hello cdefa\nsym 42" (get-output-string out))
  (test-equal "get-output-string again" "hello cdefa\nsym 42" (get-output-string out))
  (test-error "write-char needs a character" TypeError (write-char "ab" out))
  (test-error "write-string range" IndexError (write-string "abc" out 2 9))
  (test-error "get-output-string needs a string port" TypeError
              (get-output-string (open-input-string "x"))))

(test-group "port predicates"
  (define in (open-input-string "x"))
  (define out (open-output-string))
  (test-assert "input-port?" (input-port? in))
  (test-equal "input-port? output" #f (input-port? out))
  (test-assert "output-port?" (output-port? out))
  (test-equal "output-port? input" #f (output-port? in))
  (test-assert "textual-port?" (textual-port? in))
  (test-equal "binary-port? textual" #f (binary-port? in))
  (test-assert "port?" (port? out))
  (test-equal "port? other" #f (port? 5))
  (test-equal "input-port? other" #f (input-port? "string"))
  (test-assert "input-port-open?" (input-port-open? in))
  (test-assert "output-port-open?" (output-port-open? out))
  (close-port in)
  (close-output-port out)
  (test-equal "input-port-open? after close" #f (input-port-open? in))
  (test-assert "closed input port is still an input port" (input-port? in))
  (test-equal "output-port-open? after close" #f (output-port-open? out))
  (test-error "close-input-port needs an input port" TypeError
              (close-input-port (open-output-string)))
  (test-error "close-output-port needs an output port" TypeError
              (close-output-port (open-input-string "")))
  (define in2 (open-input-string "y"))
  (close-input-port in2)
  (test-equal "close-input-port" #f (input-port-open? in2)))

(test-group "call-with-port"
  (define port (open-input-string "abc"))
  (test-equal "result" #\a (call-with-port port read-char))
  (test-equal "closes the port" #f (input-port-open? port)))

(test-group "current ports"
  (test-assert "current-output-port" (output-port? (current-output-port)))
  (test-assert "current-error-port" (output-port? (current-error-port)))
  (test-assert "current-input-port" (input-port? (current-input-port)))
  (test-equal "parameterize current-output-port"
              "inside\nmore 7 #t"
              (output-of
                (lambda ()
                  (display "inside")
                  (newline)
                  (write-string "more ")
                  (write 7)
                  (write-char #\space)
                  (write #t)
                  (flush-output-port))))
  (test-equal "parameterize current-input-port"
              '(#\q "rest")
              (parameterize ((current-input-port (open-input-string "qrest")))
                (list (read-char) (read-line))))
  (test-equal "with-output-to-file sees current port"
              "to file"
              (let* ((temp-root (TemporaryDirectory))
                     (path (str (op#truediv (Path temp-root.name) "out.txt"))))
                (with-output-to-file path
                  (lambda () (write-string "to file")))
                (let ((text (call-with-input-file path read-line)))
                  (.cleanup temp-root)
                  text))))

(test-group "file ports"
  (define temp-root (TemporaryDirectory))
  (define path (str (op#truediv (Path temp-root.name) "ports.txt")))
  (call-with-output-file path
    (lambda (port)
      (write-string "line one\nline two\n" port)
      (write-char #\! port)))
  (define port (open-input-file path))
  (test-assert "file input-port?" (input-port? port))
  (test-assert "file textual-port?" (textual-port? port))
  (test-equal "file read-line" "line one" (read-line port))
  (test-equal "file peek-char" #\l (peek-char port))
  (test-equal "file read-line after peek" "line two" (read-line port))
  (test-equal "file read-char" #\! (read-char port))
  (test-assert "file eof" (eof-object? (read-char port)))
  (close-input-port port)
  (test-equal "file closed" #f (input-port-open? port))
  (test-assert "closed file is still an input port" (input-port? port))
  (define binary (open-binary-input-file path))
  (test-assert "binary-port?" (binary-port? binary))
  (test-equal "binary read-u8" 108 (read-u8 binary))
  (close-port binary)
  (.cleanup temp-root))

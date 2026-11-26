(import (scheme base)
        (scheme write)
        (srfi 64)
        (only io StringIO))

(test-group "scheme write"
  (define display-port (StringIO))
  (display "hello" display-port)
  (display " " display-port)
  (write "world" display-port)
  (newline display-port)

  (test-equal "display/write/newline"
              "hello \"world\"\n"
              (.getvalue display-port)))

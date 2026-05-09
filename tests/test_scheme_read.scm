(import (scheme base)
        (scheme file)
        (scheme read)
        (srfi 64)
        (only pathlib Path)
        (only tempfile TemporaryDirectory))

(test-group "scheme read"
  (define temp-root (TemporaryDirectory))
  (define temp-dir temp-root.name)
  (define text-path (str (op#truediv (Path temp-dir) "scheme-read.txt")))

  (call-with-output-file
    text-path
    (lambda (port)
      (.write port "alpha\nbeta")))

  (test-equal "read-line from current input"
              "alpha"
              (with-input-from-file text-path (lambda () (read-line))))

  (.cleanup temp-root))

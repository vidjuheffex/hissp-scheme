(import (scheme base)
        (scheme file)
        (scheme write)
        (srfi 64)
        (only pathlib Path)
        (only tempfile TemporaryDirectory))

(test-group "scheme file"
  (define temp-root (TemporaryDirectory))
  (define temp-dir temp-root.name)
  (define text-path (str (.joinpath (Path temp-dir) "scheme-file.txt")))
  (define redirect-path (str (.joinpath (Path temp-dir) "redirect.txt")))
  (define binary-path (str (.joinpath (Path temp-dir) "scheme-file.bin")))

  (call-with-output-file
    text-path
    (lambda (port)
      (.write port "alpha\nbeta")))

  (test-assert "file-exists?" (file-exists? text-path))
  (test-equal "call-with-input-file"
              "alpha\nbeta"
              (call-with-input-file text-path (lambda (port) (.read port))))

  (with-output-to-file
    redirect-path
    (lambda ()
      (display "redirected")
      (newline)))
  (test-equal "with-output-to-file"
              "redirected\n"
              (call-with-input-file redirect-path (lambda (port) (.read port))))

  (let ((binary-output (open-binary-output-file binary-path)))
    (.write binary-output (bytes (vector 97 98 99)))
    (.close binary-output))
  (let ((binary-input (open-binary-input-file binary-path)))
    (test-equal "binary file ports" (bytes (vector 97 98 99)) (.read binary-input))
    (.close binary-input))

  (delete-file text-path)
  (test-equal "delete-file" #f (file-exists? text-path))

  (.cleanup temp-root))

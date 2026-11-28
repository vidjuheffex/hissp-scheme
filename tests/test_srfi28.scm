(import (scheme base)
        (srfi 64))
(import (srfi 28))

(test-group "srfi-28"
  (test-equal "format display/write"
              "name=terrain repr=\"terrain\"\n"
              (format "name=~a repr=~s~%" "terrain" "terrain"))
  (test-equal "format tilde"
              "~"
              (format "~~")))

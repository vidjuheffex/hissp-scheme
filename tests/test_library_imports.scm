(import (scheme base)
        (srfi 64))
(import (only math sqrt sin))
(import (except (only math cos tan) cos))
(import (rename (only math floor) (floor math-floor)))
(import (prefix (only math ceil) math-))
(import (rename (only json dumps) (dumps json-dumps)))

(define-library (scheme test-include-library)
  (export included-library-value included-library-add-one)
  (import (scheme base))
  (include "include_value.scm"))

(test-group "library/import"
  (test-equal "define-library include value"
              41
              included-library-value)

  (test-equal "define-library include function"
              42
              (included-library-add-one 41))

  (test-equal "nested import-set rename"
              "{\"x\": 1}"
              (json-dumps (% "x" 1)))

  (test-equal "only import-set"
              4.0
              (sqrt 16))

  (test-equal "except import-set keeps remaining names"
              0.0
              (sin 0))
  (test-equal "except import-set removes excluded names"
              0.0
              (tan 0))
  (test-error "except import-set excluded binding absent"
              NameError
              (cos 0))

  (test-equal "rename import-set"
              3
              (math-floor 3.9))

  (test-equal "prefix import-set"
              4
              (math-ceil 3.1)))

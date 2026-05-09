(import (scheme base)
        (srfi 64))
(import (srfi 177))
(import (only json dumps))
(import (rename (only json dumps) (dumps json-dumps)))

(test-group "srfi-177"
  (define payload
    (call/kw dict (name "terrain"
                   height 120
                   active #t)))

  (test-equal "call/kw dict"
              (call/kw dict (active #t height 120 name "terrain"))
              payload)

  (test-equal "python import + call/kw"
              "{\n  \"active\": true,\n  \"height\": 120,\n  \"name\": \"terrain\"\n}"
              (call/kw dumps payload (indent 2 sort-keys #t)))

  (test-equal "nested import-set rename"
              "{\"name\": \"terrain\", \"height\": 120, \"active\": true}"
              (json-dumps payload))

  (define json-options
    (call/kw dict (sort-keys #t)))

  (test-equal "python import + dynamic kwargs"
              "{\"active\": true, \"height\": 120, \"name\": \"terrain\"}"
              (call/kw dumps payload (** json-options)))

  (define/kw (describe terrain (color size))
    (@ terrain color size))

  (test-equal "define/kw defaults" (@ "terrain" #f #f) (describe "terrain"))
  (test-equal "define/kw call/kw"
              (@ "terrain" "azure" 18)
              (call/kw describe "terrain" (size 18 color "azure")))

  (define scale-by
    (lambda/kw (x (factor))
      (if factor
        (* x factor)
        x)))

  (test-equal "lambda/kw default" 8 (scale-by 8))
  (test-equal "lambda/kw keyword" 24 (call/kw scale-by 8 (factor 3))))

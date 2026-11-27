(import (scheme base)
        (srfi 64)
        (srfi 132))

(test-group "srfi-132"
  (test-assert "list-sorted? empty" (list-sorted? < '()))
  (test-assert "list-sorted? ascending" (list-sorted? < '(1 2 2 3)))
  (test-equal "list-sorted? unsorted" #f (list-sorted? < '(1 3 2)))
  (test-assert "vector-sorted?" (vector-sorted? < (vector 1 2 3)))
  (test-equal "vector-sorted? unsorted" #f (vector-sorted? < (vector 3 1 2)))
  (test-assert "vector-sorted? range"
               (vector-sorted? < (vector 9 1 2 3 0) 1 4))

  (test-equal "list-sort" '(1 2 3 4 5) (list-sort < '(3 1 4 5 2)))
  (test-equal "list-sort empty" '() (list-sort < '()))
  (test-equal "list-sort descending" '(5 4 3 1) (list-sort > '(3 1 4 5)))
  (test-equal "list-sort strings"
              '("apple" "fig" "pear")
              (list-sort string<? '("pear" "apple" "fig")))

  (define (car< a b) (< (car a) (car b)))
  (define records '((2 . a) (1 . b) (2 . c) (1 . d) (0 . e)))
  (test-equal "list-stable-sort keeps equal elements in order"
              '((0 . e) (1 . b) (1 . d) (2 . a) (2 . c))
              (list-stable-sort car< records))
  (test-equal "list-sort is stable too"
              '((0 . e) (1 . b) (1 . d) (2 . a) (2 . c))
              (list-sort car< records))

  (test-equal "comparator truth is Scheme truth"
              '(1 2 3)
              (list-sort (lambda (a b) (if (< a b) 0 #f)) '(3 1 2)))

  (define to-sort (list 3 1 2))
  (define sorted-in-place (list-sort! < to-sort))
  (test-equal "list-sort!" '(1 2 3) sorted-in-place)
  (test-equal "list-stable-sort!" '((1 . b) (2 . a))
              (list-stable-sort! car< (list '(2 . a) '(1 . b))))

  (define source (vector 5 3 1 4 2))
  (test-equal "vector-sort" (vector 1 2 3 4 5) (vector-sort < source))
  (test-equal "vector-sort leaves source alone" (vector 5 3 1 4 2) source)
  (test-equal "vector-sort range" (vector 1 3 4) (vector-sort < source 1 4))
  (test-equal "vector-sort start only" (vector 1 2 4) (vector-sort < source 2))
  (test-equal "vector-stable-sort"
              (vector '(1 . b) '(1 . d) '(2 . a))
              (vector-stable-sort car< (vector '(2 . a) '(1 . b) '(1 . d))))

  (define in-place (vector 5 3 1 4 2))
  (vector-sort! in-place <)
  (test-equal "vector-sort!" (vector 1 2 3 4 5) in-place)
  (define partial (vector 5 3 1 4 2))
  (vector-sort! partial < 1 4)
  (test-equal "vector-sort! range" (vector 5 1 3 4 2) partial)
  (define stable-in-place (vector 3 2 1))
  (vector-stable-sort! stable-in-place <)
  (test-equal "vector-stable-sort!" (vector 1 2 3) stable-in-place)

  (test-equal "list-merge" '(1 2 3 4 5 6) (list-merge < '(1 3 5) '(2 4 6)))
  (test-equal "list-merge empty" '(1 2) (list-merge < '() '(1 2)))
  (test-equal "list-merge stable: first list wins ties"
              '((1 . a) (1 . b) (2 . c))
              (list-merge car< '((1 . a) (2 . c)) '((1 . b))))
  (test-equal "list-merge!" '(1 2 3 4) (list-merge! < (list 1 4) (list 2 3)))
  (test-equal "list-merge! empty" '() (list-merge! < '() '()))

  (test-equal "vector-merge"
              (vector 1 2 3 4 5 6)
              (vector-merge < (vector 1 3 5) (vector 2 4 6)))
  (test-equal "vector-merge ranges"
              (vector 3 4 5)
              (vector-merge < (vector 1 3 5) (vector 2 4 6) 1 3 1 2))
  (define merge-target (make-vector 6 0))
  (vector-merge! < merge-target (vector 1 5) (vector 2 3))
  (test-equal "vector-merge!" (vector 1 2 3 5 0 0) merge-target)
  (define merge-offset (make-vector 5 0))
  (vector-merge! < merge-offset (vector 1 5) (vector 2) 2)
  (test-equal "vector-merge! at start" (vector 0 0 1 2 5) merge-offset)
  (test-error "vector-merge! overflow" IndexError
              (vector-merge! < (make-vector 2 0) (vector 1 2) (vector 3)))

  (test-equal "list-delete-neighbor-dups"
              '(1 2 7 0 -2)
              (list-delete-neighbor-dups = '(1 1 2 7 7 7 0 -2 -2)))
  (test-equal "list-delete-neighbor-dups empty"
              '()
              (list-delete-neighbor-dups = '()))
  (test-equal "list-delete-neighbor-dups!"
              '(1 2 7 0 -2)
              (list-delete-neighbor-dups! = (list 1 1 2 7 7 7 0 -2 -2)))
  (test-equal "vector-delete-neighbor-dups"
              (vector 1 2 7 0 -2)
              (vector-delete-neighbor-dups = (vector 1 1 2 7 7 7 0 -2 -2)))
  (test-equal "vector-delete-neighbor-dups range"
              (vector 2 7)
              (vector-delete-neighbor-dups = (vector 1 1 2 7 7 7 0) 2 6))
  (define dups (vector 1 1 2 7 7 7 0 -2 -2))
  (define dups-end (vector-delete-neighbor-dups! = dups))
  (test-equal "vector-delete-neighbor-dups! end" 5 dups-end)
  (test-equal "vector-delete-neighbor-dups! prefix"
              (vector 1 2 7 0 -2)
              (vector-copy dups 0 dups-end))
  (define dups-range (vector 9 9 3 3 4 9))
  (test-equal "vector-delete-neighbor-dups! range end"
              4
              (vector-delete-neighbor-dups! = dups-range 1 5))
  (test-equal "vector-delete-neighbor-dups! range prefix"
              (vector 9 9 3 4)
              (vector-copy dups-range 0 4))

  (test-equal "vector-find-median odd" 3 (vector-find-median < (vector 5 1 3) 0))
  (test-equal "vector-find-median even" 5/2
              (vector-find-median < (vector 4 1 3 2) 0))
  (test-equal "vector-find-median empty" 'none
              (vector-find-median < (vector) 'none))
  (test-equal "vector-find-median custom mean" 3
              (vector-find-median < (vector 4 1 3 2) 0 max))
  (define median-source (vector 4 1 3 2))
  (test-equal "vector-find-median!" 5/2
              (vector-find-median! < median-source 0))
  (test-equal "vector-find-median! sorts" (vector 1 2 3 4) median-source)

  (test-equal "vector-select! smallest" 1 (vector-select! < (vector 5 3 1 4 2) 0))
  (test-equal "vector-select! k" 4 (vector-select! < (vector 5 3 1 4 2) 3))
  (test-equal "vector-select! range" 4
              (vector-select! < (vector 0 5 3 4 0) 1 1 4))
  (test-error "vector-select! k out of range" IndexError
              (vector-select! < (vector 1 2) 2))

  (define separated (vector 5 3 1 4 2))
  (vector-separate! < separated 2)
  (test-equal "vector-separate! smallest k first"
              '(1 2)
              (list-sort < (vector->list separated 0 2)))
  (test-equal "vector-separate! keeps elements"
              '(1 2 3 4 5)
              (list-sort < (vector->list separated)))

  (test-error "list-sort requires a list" TypeError (list-sort < (vector 1 2)))
  (test-error "vector-sort requires a vector" TypeError (vector-sort < '(1 2)))
  (test-error "vector-sort bad range" IndexError (vector-sort < (vector 1 2) 1 5))
  (test-error "list-sort requires a procedure" TypeError (list-sort 1 '(1 2))))

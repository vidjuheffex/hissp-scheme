;; SRFI-132: Sort libraries.
;;
;; Sorting uses Python's stable Timsort, so the `stable` variants are the same
;; procedures as the plain ones. Optional start/end arguments are handled by
;; `hissp_scheme.runtime.srfi132_runtime`; this library owns the Scheme names and
;; the default `mean` for median finding, which must use Scheme arithmetic.

(define-library (srfi 132)
  (export list-sorted?
          vector-sorted?
          list-sort
          list-stable-sort
          list-sort!
          list-stable-sort!
          vector-sort
          vector-stable-sort
          vector-sort!
          vector-stable-sort!
          list-merge
          list-merge!
          vector-merge
          vector-merge!
          list-delete-neighbor-dups
          list-delete-neighbor-dups!
          vector-delete-neighbor-dups
          vector-delete-neighbor-dups!
          vector-find-median
          vector-find-median!
          vector-select!
          vector-separate!)
  (import (scheme base)
          (prefix hissp_scheme.runtime.srfi132_runtime rt-))
  (begin
    (define list-sorted? rt-list-sorted-q)

    (define vector-sorted? rt-vector-sorted-q)

    (define list-sort rt-list-sort)

    (define list-stable-sort rt-list-sort)

    (define list-sort! rt-list-sort-bang)

    (define list-stable-sort! rt-list-sort-bang)

    (define vector-sort rt-vector-sort)

    (define vector-stable-sort rt-vector-sort)

    (define vector-sort! rt-vector-sort-bang)

    (define vector-stable-sort! rt-vector-sort-bang)

    (define list-merge rt-list-merge)

    (define list-merge! rt-list-merge-bang)

    (define vector-merge rt-vector-merge)

    (define vector-merge! rt-vector-merge-bang)

    (define list-delete-neighbor-dups rt-list-delete-neighbor-dups)

    (define list-delete-neighbor-dups! rt-list-delete-neighbor-dups-bang)

    (define vector-delete-neighbor-dups rt-vector-delete-neighbor-dups)

    (define vector-delete-neighbor-dups! rt-vector-delete-neighbor-dups-bang)

    (define (default-mean a b)
      (/ (+ a b) 2))

    (define (vector-find-median less vector knil . maybe-mean)
      (rt-vector-find-median less vector knil
                             (if (null? maybe-mean) default-mean (car maybe-mean))))

    (define (vector-find-median! less vector knil . maybe-mean)
      (rt-vector-find-median-bang less vector knil
                                  (if (null? maybe-mean) default-mean (car maybe-mean))))

    (define vector-select! rt-vector-select-bang)

    (define vector-separate! rt-vector-separate-bang)))

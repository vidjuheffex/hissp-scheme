;; SRFI-1: List library.
;;
;; Core pair/list primitives live in `scheme`; the R7RS procedures that SRFI-1
;; shares with `(scheme base)` and `(scheme cxr)` (`cons`, `map`, `member`,
;; `assoc`, `caddr`, ...) are re-exported from there, since they already have
;; the SRFI-1 behavior. Everything else is implemented in
;; `hissp_scheme.runtime.srfi1_runtime`. The linear-update `!` procedures are
;; the same as their pure counterparts, which SRFI-1 permits.

(define-library (srfi 1)
  (export
    ;; Constructors
    cons list xcons cons* make-list list-tabulate list-copy circular-list iota
    ;; Predicates
    pair? null? proper-list? circular-list? dotted-list? not-pair? null-list?
    list=
    ;; Selectors
    car cdr
    caar cadr cdar cddr
    caaar caadr cadar caddr cdaar cdadr cddar cdddr
    caaaar caaadr caadar caaddr cadaar cadadr caddar cadddr
    cdaaar cdaadr cdadar cdaddr cddaar cddadr cdddar cddddr
    list-ref first second third fourth fifth sixth seventh eighth ninth tenth
    car+cdr take drop take-right drop-right take! drop-right! split-at
    split-at! last last-pair
    ;; Miscellaneous
    length length+ append concatenate reverse append! concatenate! reverse!
    append-reverse append-reverse! zip unzip1 unzip2 unzip3 unzip4 unzip5 count
    ;; Fold, unfold, and map
    fold unfold pair-fold reduce fold-right unfold-right pair-fold-right
    reduce-right append-map append-map! pair-for-each filter-map map-in-order
    map for-each map!
    ;; Filtering and partitioning
    filter partition remove filter! partition! remove!
    ;; Searching
    member memq memv find find-tail any every list-index take-while
    drop-while take-while! span break span! break!
    ;; Deletion
    delete delete-duplicates delete! delete-duplicates!
    ;; Association lists
    assoc assq assv alist-cons alist-copy alist-delete alist-delete!
    ;; Lists as sets
    lset<= lset= lset-adjoin lset-union lset-union! lset-intersection
    lset-intersection! lset-difference lset-difference! lset-xor lset-xor!
    lset-diff+intersection lset-diff+intersection!)
  (import (scheme base)
          (scheme cxr)
          (prefix hissp_scheme.runtime.srfi1_runtime rt-))
  (begin
    (define xcons rt-xcons)
    (define cons* rt-cons-star)
    (define list-tabulate rt-list-tabulate)
    (define circular-list rt-circular-list)
    (define iota rt-iota)

    (define proper-list? rt-proper-list-q)
    (define circular-list? rt-circular-list-q)
    (define dotted-list? rt-dotted-list-q)
    (define not-pair? rt-not-pair-q)
    (define null-list? rt-null-list-q)
    (define list= rt-list-eq)

    (define first rt-first)
    (define second rt-second)
    (define third rt-third)
    (define fourth rt-fourth)
    (define fifth rt-fifth)
    (define sixth rt-sixth)
    (define seventh rt-seventh)
    (define eighth rt-eighth)
    (define ninth rt-ninth)
    (define tenth rt-tenth)
    (define car+cdr rt-car-plus-cdr)
    (define take rt-take)
    (define drop rt-drop)
    (define take-right rt-take-right)
    (define drop-right rt-drop-right)
    (define take! rt-take)
    (define drop-right! rt-drop-right)
    (define split-at rt-split-at)
    (define split-at! rt-split-at)
    (define last rt-last)
    (define last-pair rt-last-pair)

    (define length+ rt-length-plus)
    (define concatenate rt-concatenate)
    (define append! append)
    (define concatenate! rt-concatenate)
    (define reverse! reverse)
    (define append-reverse rt-append-reverse)
    (define append-reverse! rt-append-reverse)
    (define zip rt-zip-lists)
    (define unzip1 rt-unzip1)
    (define unzip2 rt-unzip2)
    (define unzip3 rt-unzip3)
    (define unzip4 rt-unzip4)
    (define unzip5 rt-unzip5)
    (define count rt-count)

    (define fold rt-fold)
    (define unfold rt-unfold)
    (define pair-fold rt-pair-fold)
    (define reduce rt-reduce)
    (define fold-right rt-fold-right)
    (define unfold-right rt-unfold-right)
    (define pair-fold-right rt-pair-fold-right)
    (define reduce-right rt-reduce-right)
    (define append-map rt-append-map)
    (define append-map! rt-append-map)
    (define pair-for-each rt-pair-for-each)
    (define filter-map rt-filter-map)
    (define map-in-order map)
    (define map! map)

    (define filter rt-filter-list)
    (define partition rt-partition)
    (define remove rt-remove)
    (define filter! rt-filter-list)
    (define partition! rt-partition)
    (define remove! rt-remove)

    (define find rt-find)
    (define find-tail rt-find-tail)
    (define any rt-any-of)
    (define every rt-every)
    (define list-index rt-list-index)
    (define take-while rt-take-while)
    (define drop-while rt-drop-while)
    (define take-while! rt-take-while)
    (define span rt-span)
    (define break rt-break-span)
    (define span! rt-span)
    (define break! rt-break-span)

    (define delete rt-delete)
    (define delete-duplicates rt-delete-duplicates)
    (define delete! rt-delete)
    (define delete-duplicates! rt-delete-duplicates)

    (define alist-cons rt-alist-cons)
    (define alist-copy rt-alist-copy)
    (define alist-delete rt-alist-delete)
    (define alist-delete! rt-alist-delete)

    (define lset<= rt-lset-le)
    (define lset= rt-lset-eq)
    (define lset-adjoin rt-lset-adjoin)
    (define lset-union rt-lset-union)
    (define lset-union! rt-lset-union)
    (define lset-intersection rt-lset-intersection)
    (define lset-intersection! rt-lset-intersection)
    (define lset-difference rt-lset-difference)
    (define lset-difference! rt-lset-difference)
    (define lset-xor rt-lset-xor)
    (define lset-xor! rt-lset-xor)
    (define lset-diff+intersection rt-lset-diff-plus-intersection)
    (define lset-diff+intersection! rt-lset-diff-plus-intersection)))

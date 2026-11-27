;; R7RS `(scheme cxr)` library: the three- and four-level `car`/`cdr`
;; compositions. `(scheme base)` has only the two-level ones.

(define-library (scheme cxr)
  (export caaar
          caadr
          cadar
          caddr
          cdaar
          cdadr
          cddar
          cdddr
          caaaar
          caaadr
          caadar
          caaddr
          cadaar
          cadadr
          caddar
          cadddr
          cdaaar
          cdaadr
          cdadar
          cdaddr
          cddaar
          cddadr
          cdddar
          cddddr)
  (import (scheme base))
  (begin
    (define caaar scheme_base..caaar)
    (define caadr scheme_base..caadr)
    (define cadar scheme_base..cadar)
    (define caddr scheme_base..caddr)
    (define cdaar scheme_base..cdaar)
    (define cdadr scheme_base..cdadr)
    (define cddar scheme_base..cddar)
    (define cdddr scheme_base..cdddr)
    (define caaaar scheme_base..caaaar)
    (define caaadr scheme_base..caaadr)
    (define caadar scheme_base..caadar)
    (define caaddr scheme_base..caaddr)
    (define cadaar scheme_base..cadaar)
    (define cadadr scheme_base..cadadr)
    (define caddar scheme_base..caddar)
    (define cadddr scheme_base..cadddr)
    (define cdaaar scheme_base..cdaaar)
    (define cdaadr scheme_base..cdaadr)
    (define cdadar scheme_base..cdadar)
    (define cdaddr scheme_base..cdaddr)
    (define cddaar scheme_base..cddaar)
    (define cddadr scheme_base..cddadr)
    (define cdddar scheme_base..cdddar)
    (define cddddr scheme_base..cddddr)))

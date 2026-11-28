"""Runtime helpers used by bundled Scheme libraries."""

import sys

# Exact integers are unbounded in Scheme, but CPython refuses to convert ints
# of more than 4300 digits to or from decimal strings. That limit would break
# the reader, `number->string`, `string->number`, `write`, and `display`.
sys.set_int_max_str_digits(0)

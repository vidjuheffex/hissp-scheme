scheme_bootstrap..prelude#:

;; Core Scheme pair/list runtime.
;;
;; This module owns the data representation that the rest of Scheme shares:
;; mutable pairs, the empty-list sentinel, selectors, mutation, equality, and a
;; small set of base list procedures. SRFI-1 builds on this layer; it does not
;; define what pairs are.

.#"
import builtins
import itertools

import hissp


class Pair:
    # Mutable Scheme cons cell. The fields are intentionally public because the
    # primitive mutators `set-car!` and `set-cdr!` map directly to assignment.
    __slots__ = ('car', 'cdr')

    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def __iter__(self):
        value = self
        seen = set()
        while pair_q(value):
            if id(value) in seen:
                raise ValueError('cannot iterate circular list')
            seen.add(id(value))
            yield value.car
            value = value.cdr
        if not null_q(value):
            raise ValueError(f'improper list tail: {value!r}')

    def __repr__(self):
        parts = []
        value = self
        seen = set()
        while pair_q(value):
            if id(value) in seen:
                parts.append('...')
                return '(' + ' '.join(parts) + ')'
            seen.add(id(value))
            parts.append(repr(value.car))
            value = value.cdr
        if null_q(value):
            return '(' + ' '.join(parts) + ')'
        return '(' + ' '.join(parts) + ' . ' + repr(value) + ')'

    def __eq__(self, other):
        if not pair_q(other):
            return False
        try:
            left, left_tail = list_to_py(self, require_proper=False)
            right, right_tail = list_to_py(other, require_proper=False)
        except ValueError:
            return self is other
        return left == right and left_tail == right_tail


def cons(car, cdr):
    return Pair(car, cdr)


def pair_q(value):
    return isinstance(value, Pair)


def null_q(value):
    return value == ()


def _require_pair(value, procedure):
    if not pair_q(value):
        raise TypeError(f'{procedure} expected a pair, got {value!r}')
    return value


def car(pair):
    return _require_pair(pair, 'car').car


def cdr(pair):
    return _require_pair(pair, 'cdr').cdr


def set_car_bang(pair, value):
    _require_pair(pair, 'set-car!').car = value
    return None


def set_cdr_bang(pair, value):
    _require_pair(pair, 'set-cdr!').cdr = value
    return None


def scheme_list(*items):
    result = ()
    for item in reversed(items):
        result = cons(item, result)
    return result


def list_to_py(value, *, require_proper=True):
    result = []
    seen = set()
    while pair_q(value):
        if id(value) in seen:
            raise ValueError('circular list')
        seen.add(id(value))
        result.append(value.car)
        value = value.cdr
    if require_proper and not null_q(value):
        raise TypeError(f'expected proper list, got dotted tail {value!r}')
    return result, value


def py_to_list(items, tail=()):
    result = tail
    for item in reversed(builtins.list(items)):
        result = cons(item, result)
    return result


def scheme_length(value):
    return len(list_to_py(value)[0])


def list_ref(value, index):
    while index:
        value = cdr(value)
        index -= 1
    return car(value)


def car_plus_cdr(pair):
    pair = _require_pair(pair, 'car+cdr')
    return (pair.car, pair.cdr)


def scheme_append(*lists):
    if not lists:
        return ()
    result = lists[-1]
    for value in reversed(lists[:-1]):
        items, tail = list_to_py(value, require_proper=False)
        if not null_q(tail):
            raise TypeError('append arguments before the last must be proper lists')
        result = py_to_list(items, result)
    return result


def reverse(value):
    return py_to_list(reversed(list_to_py(value)[0]))


def vector_q(value):
    return isinstance(value, list)


def _require_vector(value, procedure):
    if not vector_q(value):
        raise TypeError(f'{procedure} expected a vector, got {value!r}')
    return value


def make_vector(count, fill=False):
    return [fill for _ in range(count)]


def scheme_vector(*items):
    return builtins.list(items)


def vector_length(value):
    return len(_require_vector(value, 'vector-length'))


def vector_ref(value, index):
    return _require_vector(value, 'vector-ref')[index]


def vector_set_bang(value, index, item):
    _require_vector(value, 'vector-set!')[index] = item
    return None


def vector_to_list(value, start=0, end=None):
    return py_to_list(_require_vector(value, 'vector->list')[start:end])


def list_to_vector(value):
    return builtins.list(list_to_py(value)[0])


def vector_to_string(value, start=0, end=None):
    return ''.join(_require_vector(value, 'vector->string')[start:end])


def string_to_vector(value, start=0, end=None):
    if not isinstance(value, str):
        raise TypeError(f'string->vector expected a string, got {value!r}')
    return builtins.list(value[start:end])


def vector_copy(value, start=0, end=None):
    return builtins.list(_require_vector(value, 'vector-copy')[start:end])


def vector_copy_bang(to, at, from_, start=0, end=None):
    target = _require_vector(to, 'vector-copy!')
    source = _require_vector(from_, 'vector-copy!')[start:end]
    target[at:at + len(source)] = source
    return None


def vector_append(*vectors):
    result = []
    for value in vectors:
        result.extend(_require_vector(value, 'vector-append'))
    return result


def vector_fill_bang(value, fill, start=0, end=None):
    vector = _require_vector(value, 'vector-fill!')
    stop = len(vector) if end is None else end
    for index in range(start, stop):
        vector[index] = fill
    return None


def _make_cxr(name, pattern):
    def cxr(value):
        for operation in reversed(pattern):
            value = car(value) if operation == 'a' else cdr(value)
        return value

    cxr.__name__ = name
    return cxr


def _cxxr_bindings():
    bindings = {}
    for size in range(2, 5):
        for pattern in itertools.product('ad', repeat=size):
            pattern = ''.join(pattern)
            name = f'c{pattern}r'
            bindings[name] = _make_cxr(name, pattern)
    return bindings


def install_core_list_bindings(env):
    bindings = {
        'Pair': Pair,
        'cons': cons,
        'list': scheme_list,
        'eq?': lambda a, b: a is b,
        'eqv?': lambda a, b: a == b,
        'equal?': lambda a, b: a == b,
        'pair?': pair_q,
        'null?': null_q,
        'car': car,
        'cdr': cdr,
        'car+cdr': car_plus_cdr,
        'list-ref': list_ref,
        'length': scheme_length,
        'append': scheme_append,
        'reverse': reverse,
        'set-car!': set_car_bang,
        'set-cdr!': set_cdr_bang,
        'vector?': vector_q,
        'make-vector': make_vector,
        'vector': scheme_vector,
        'vector-length': vector_length,
        'vector-ref': vector_ref,
        'vector-set!': vector_set_bang,
        'vector->list': vector_to_list,
        'list->vector': list_to_vector,
        'vector->string': vector_to_string,
        'string->vector': string_to_vector,
        'vector-copy': vector_copy,
        'vector-copy!': vector_copy_bang,
        'vector-append': vector_append,
        'vector-fill!': vector_fill_bang,
    }

    for index, name in enumerate(
        ('first', 'second', 'third', 'fourth', 'fifth',
         'sixth', 'seventh', 'eighth', 'ninth', 'tenth')
    ):
        bindings[name] = (lambda value, index=index: list_ref(value, index))

    for name, value in bindings.items():
        env[hissp.munge(name)] = value

    for name, value in _cxxr_bindings().items():
        env[name] = value
    return None
"

"""R7RS bytevectors, represented as Python `bytearray`."""

from __future__ import annotations


def _require_bytevector(value, procedure):
    if not isinstance(value, bytearray):
        raise TypeError(f"{procedure} expected a bytevector, got {value!r}")
    return value


def _require_byte(value, procedure):
    if not (
        isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 255
    ):
        raise TypeError(f"{procedure} expected a byte (0-255), got {value!r}")
    return value


def _require_index(bytevector, k, procedure):
    if not (isinstance(k, int) and 0 <= k < len(bytevector)):
        raise IndexError(
            f"{procedure}: index {k!r} out of range for bytevector of length "
            f"{len(bytevector)}"
        )
    return k


def _range(sequence, start, end, procedure):
    length = len(sequence)
    stop = length if end is None else end
    if not (
        isinstance(start, int)
        and isinstance(stop, int)
        and 0 <= start <= stop <= length
    ):
        raise IndexError(
            f"{procedure}: invalid range [{start}, {end}) for length {length}"
        )
    return start, stop


def bytevector(*items):
    for item in items:
        _require_byte(item, "bytevector")
    return bytearray(items)


def bytevector_q(obj):
    return isinstance(obj, bytearray)


def make_bytevector(k, byte=0):
    if not (isinstance(k, int) and k >= 0):
        raise TypeError(f"make-bytevector expected a non-negative length, got {k!r}")
    return bytearray((_require_byte(byte, "make-bytevector"),)) * k


def bytevector_length(bytevector):
    return len(_require_bytevector(bytevector, "bytevector-length"))


def bytevector_u8_ref(bytevector, k):
    bytevector = _require_bytevector(bytevector, "bytevector-u8-ref")
    return bytevector[_require_index(bytevector, k, "bytevector-u8-ref")]


def bytevector_u8_set_bang(bytevector, k, byte):
    bytevector = _require_bytevector(bytevector, "bytevector-u8-set!")
    bytevector[_require_index(bytevector, k, "bytevector-u8-set!")] = _require_byte(
        byte, "bytevector-u8-set!"
    )
    return False


def bytevector_copy(bytevector, start=0, end=None):
    bytevector = _require_bytevector(bytevector, "bytevector-copy")
    start, end = _range(bytevector, start, end, "bytevector-copy")
    return bytearray(bytevector[start:end])


def bytevector_copy_bang(to, at, source, start=0, end=None):
    to = _require_bytevector(to, "bytevector-copy!")
    source = _require_bytevector(source, "bytevector-copy!")
    start, end = _range(source, start, end, "bytevector-copy!")
    if not (isinstance(at, int) and 0 <= at and at + (end - start) <= len(to)):
        raise IndexError(
            f"bytevector-copy!: {end - start} bytes do not fit at index {at!r} "
            f"of a bytevector of length {len(to)}"
        )
    to[at : at + (end - start)] = source[start:end]
    return False


def bytevector_append(*bytevectors):
    result = bytearray()
    for item in bytevectors:
        result += _require_bytevector(item, "bytevector-append")
    return result


def utf8_to_string(bytevector, start=0, end=None):
    bytevector = _require_bytevector(bytevector, "utf8->string")
    start, end = _range(bytevector, start, end, "utf8->string")
    return bytes(bytevector[start:end]).decode("utf-8")


def string_to_utf8(string, start=0, end=None):
    if not isinstance(string, str):
        raise TypeError(f"string->utf8 expected a string, got {string!r}")
    start, end = _range(string, start, end, "string->utf8")
    return bytearray(string[start:end].encode("utf-8"))

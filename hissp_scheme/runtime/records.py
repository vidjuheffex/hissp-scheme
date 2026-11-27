"""Runtime support for R7RS `define-record-type`.

Each record type is a fresh Python class with one slot per field, so record
instances are ordinary Python objects that Python code can inspect. Field and
type names arrive as Scheme symbols; slot names are their munged spellings.
"""

from __future__ import annotations

from hissp_scheme.runtime.symbols import Symbol


class Record:
    """Base class of every record type created by `define-record-type`."""

    __slots__ = ()
    _scheme_fields: tuple = ()
    _scheme_name = "record"

    def __repr__(self):
        from hissp_scheme.runtime.printer import write_string

        fields = " ".join(
            f"{field.name}: {write_string(getattr(self, field, False))}"
            for field in self._scheme_fields
        )
        name = self._scheme_name.strip("<>")
        return f"#<{name} {fields}>" if fields else f"#<{name}>"


def _slot(field):
    return str(field)


def make_record_type(name, fields):
    fields = tuple(fields)
    if len(set(fields)) != len(fields):
        raise SyntaxError(f"define-record-type {name.name}: duplicate field name")
    record_type = type(
        str(name.name),
        (Record,),
        {
            "__slots__": tuple(_slot(field) for field in fields),
            "_scheme_fields": fields,
            "_scheme_name": name.name if isinstance(name, Symbol) else str(name),
        },
    )
    return record_type


def _require_field(record_type, field, procedure):
    if field not in record_type._scheme_fields:
        raise SyntaxError(
            f"{procedure}: {field.name} is not a field of {record_type._scheme_name}"
        )


def record_constructor(record_type, name, fields):
    fields = tuple(fields)
    for field in fields:
        _require_field(record_type, field, name.name)
    slots = tuple(_slot(field) for field in fields)
    unset = tuple(
        _slot(field) for field in record_type._scheme_fields if field not in fields
    )
    arity = len(slots)

    def constructor(*args):
        if len(args) != arity:
            raise TypeError(
                f"{name.name} expected {arity} argument{'s' * (arity != 1)}, "
                f"got {len(args)}"
            )
        record = record_type.__new__(record_type)
        for slot, value in zip(slots, args):
            setattr(record, slot, value)
        for slot in unset:
            setattr(record, slot, False)
        return record

    constructor.__name__ = constructor.__qualname__ = str(name)
    return constructor


def record_predicate(record_type, name):
    def predicate(obj):
        return isinstance(obj, record_type)

    predicate.__name__ = predicate.__qualname__ = str(name)
    return predicate


def _check(record_type, obj, procedure):
    if not isinstance(obj, record_type):
        raise TypeError(
            f"{procedure} expected a {record_type._scheme_name} record, got {obj!r}"
        )


def record_accessor(record_type, name, field):
    _require_field(record_type, field, name.name)
    slot = _slot(field)
    procedure = name.name

    def accessor(obj):
        _check(record_type, obj, procedure)
        return getattr(obj, slot)

    accessor.__name__ = accessor.__qualname__ = str(name)
    return accessor


def record_modifier(record_type, name, field):
    _require_field(record_type, field, name.name)
    slot = _slot(field)
    procedure = name.name

    def modifier(obj, value):
        _check(record_type, obj, procedure)
        setattr(obj, slot, value)
        return False

    modifier.__name__ = modifier.__qualname__ = str(name)
    return modifier

"""Control-flow runtime for `(scheme base)`.

Scheme procedures compile to ordinary Python functions, so this module supplies
the pieces Python lacks:

- Proper tail calls. A call in tail position compiles to a `TailCall` value
  instead of a Python call. Every Scheme procedure is wrapped by
  `make_procedure`, whose entry loop keeps running tail calls until a real
  value comes back, so tail calls never grow the Python stack.
- Escape-only continuations. `call_cc` catches a private exception raised when
  its continuation is invoked. Once `call_cc` returns, the continuation is
  dead and invoking it raises `ContinuationError`.
- R7RS dynamic state: `dynamic-wind`, the exception-handler stack, `guard`,
  error objects, multiple values, and parameter objects.

Wrappers are closures, not instances of a class with `__call__`: CPython calls
Python functions without consuming C stack, but every `__call__` dispatch does,
which would cap non-tail recursion depth near the C recursion limit.
"""

from __future__ import annotations

import sys
import threading

# Non-tail Scheme recursion still uses the Python stack (a few frames per
# Scheme call), so allow deeper recursion than CPython's default of 1000.
if sys.getrecursionlimit() < 100_000:
    sys.setrecursionlimit(100_000)


# ---------------------------------------------------------------------------
# Procedures and tail calls
# ---------------------------------------------------------------------------


class TailCall:
    """A pending call returned from tail position of a Scheme procedure."""

    __slots__ = ("procedure", "args")

    def __init__(self, procedure, *args):
        self.procedure = procedure
        self.args = args

    def __repr__(self):
        return f"TailCall({self.procedure!r}, *{self.args!r})"


def make_procedure(raw, name=None):
    """Wrap a compiled Scheme lambda body as a tail-call-driving procedure.

    `raw` may return a `TailCall`. The returned wrapper runs the trampoline, so
    Python callers always get a plain value.
    """

    def scheme_procedure(*args):
        result = raw(*args)
        while result.__class__ is TailCall:
            target = result.procedure
            if target.__class__ is _FunctionType and target.__code__ is _PROCEDURE_CODE:
                result = target._scheme_raw(*result.args)
            else:
                result = target(*result.args)
        return result

    scheme_procedure._scheme_raw = raw
    name = name or getattr(raw, "__name__", "lambda")
    scheme_procedure.__name__ = name
    scheme_procedure.__qualname__ = getattr(raw, "__qualname__", name)
    scheme_procedure.__doc__ = getattr(raw, "__doc__", None)
    return scheme_procedure


_FunctionType = type(make_procedure)
# Every wrapper shares this code object, which identifies Scheme procedures in
# the trampoline without an attribute lookup that can fail.
_PROCEDURE_CODE = make_procedure(lambda: None).__code__


# Name that compiled procedure bodies use for `TailCall` (see
# `hissp_scheme.macro.tail.procedure_form`).
TAIL_CALL_NAME = "_Qzscheme_tail_call"


def compiled_procedure(raw):
    """Procedure for a body compiled by `procedure_form`.

    A body that never makes a tail call can't return a `TailCall`, so it needs
    no trampoline and is used as is, saving a Python call per Scheme call.
    Python lists a closure variable in `co_freevars` only when the function
    or a function nested in it uses it.
    """

    if TAIL_CALL_NAME not in raw.__code__.co_freevars:
        raw._scheme_procedure = True
        return raw
    return make_procedure(raw)


def is_scheme_procedure(obj):
    """Whether `obj` is a procedure compiled from Scheme source."""

    return obj.__class__ is _FunctionType and (
        obj.__code__ is _PROCEDURE_CODE or getattr(obj, "_scheme_procedure", False)
    )


def procedure_q(obj):
    return callable(obj)


def _apply_raw(procedure, *args):
    if not args:
        return TailCall(procedure)
    *leading, rest = args
    return TailCall(procedure, *leading, *rest)


apply = make_procedure(_apply_raw, "apply")


# ---------------------------------------------------------------------------
# Multiple values
# ---------------------------------------------------------------------------


class Values:
    """Zero or several values in flight to a `call-with-values` consumer."""

    __slots__ = ("items",)

    def __init__(self, items):
        self.items = tuple(items)

    def __eq__(self, other):
        return isinstance(other, Values) and self.items == other.items

    def __repr__(self):
        return f"Values{self.items!r}"


def values(*items):
    if len(items) == 1:
        return items[0]
    return Values(items)


def _call_with_values_raw(producer, consumer):
    result = producer()
    if result.__class__ is Values:
        return TailCall(consumer, *result.items)
    return TailCall(consumer, result)


call_with_values = make_procedure(_call_with_values_raw, "call-with-values")


# ---------------------------------------------------------------------------
# Escape continuations
# ---------------------------------------------------------------------------


class ContinuationError(RuntimeError):
    """Raised when a continuation can't be resumed under escape-only semantics."""


class ContinuationInvoked(BaseException):
    """Unwinds the Python stack to the `call_cc` that owns `continuation`.

    This derives from `BaseException` so ordinary `except Exception` handlers in
    Python libraries don't swallow a Scheme escape.
    """

    def __init__(self, continuation, value):
        super().__init__()
        self.continuation = continuation
        self.value = value


class Continuation:
    """Escape-only continuation captured by `call/cc`."""

    __slots__ = ("active", "thread")

    __name__ = "continuation"

    def __init__(self):
        self.active = True
        self.thread = threading.get_ident()

    def __call__(self, *items):
        if not self.active:
            raise ContinuationError(
                "re-entrant continuations are not supported: "
                "this continuation's call/cc has already returned"
            )
        if self.thread != threading.get_ident():
            raise ContinuationError(
                "a continuation can only be invoked on the thread that captured it"
            )
        raise ContinuationInvoked(self, values(*items))

    def __repr__(self):
        state = "active" if self.active else "expired"
        return f"<continuation {state}>"


def call_cc(procedure):
    continuation = Continuation()
    try:
        return procedure(continuation)
    except ContinuationInvoked as signal:
        if signal.continuation is continuation:
            return signal.value
        raise
    finally:
        continuation.active = False


def dynamic_wind(before, thunk, after):
    before()
    try:
        return thunk()
    finally:
        after()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

_state = threading.local()

# Set on exceptions that already went through the handler stack, so enclosing
# `with-exception-handler` and `guard` frames don't deliver them a second time.
_DELIVERED = "_scheme_delivered"


class SchemeRaise(Exception):
    """Python carrier for a raised Scheme object that isn't an exception."""

    def __init__(self, payload):
        super().__init__(payload)
        self.payload = payload

    @property
    def reason(self):
        return self.payload


class SchemeError(Exception):
    """Error object created by Scheme `error`."""

    def __init__(self, message, irritants=()):
        super().__init__(message, irritants)
        self.message = message
        self.irritants = irritants

    def __str__(self):
        parts = [str(self.message), *(repr(item) for item in self.irritants)]
        return " ".join(parts)


def _scheme_list(items):
    import scheme_pairs

    return scheme_pairs.py_to_list(tuple(items))


def current_handlers():
    """Return the current thread's handler stack, innermost last."""

    return getattr(_state, "handlers", ())


def install_handlers(handlers):
    """Replace the current thread's handler stack (used when starting threads)."""

    _state.handlers = tuple(handlers)


def _payload(error):
    return error.payload if isinstance(error, SchemeRaise) else error


def _uncaught(obj):
    error = obj if isinstance(obj, BaseException) else SchemeRaise(obj)
    try:
        setattr(error, _DELIVERED, True)
    except (AttributeError, TypeError):
        pass
    return error


def _call_innermost_handler(obj):
    handlers = current_handlers()
    _state.handlers = handlers[:-1]
    try:
        return handlers[-1](obj)
    finally:
        _state.handlers = handlers


def _raise_secondary(obj):
    # A handler returned from a non-continuable raise. R7RS raises a secondary
    # exception in the handler's dynamic environment, i.e. with the outer
    # handlers installed.
    handlers = current_handlers()
    _state.handlers = handlers[:-1]
    try:
        raise_(
            SchemeError(
                "exception handler returned from non-continuable raise",
                _scheme_list((obj,)),
            )
        )
    finally:
        _state.handlers = handlers


def raise_(obj):
    if not current_handlers():
        raise _uncaught(obj)
    _call_innermost_handler(obj)
    _raise_secondary(obj)


def raise_continuable(obj):
    if not current_handlers():
        raise _uncaught(obj)
    return _call_innermost_handler(obj)


def _default_exception_handler(obj):
    raise _uncaught(obj)


def current_exception_handler():
    handlers = current_handlers()
    return handlers[-1] if handlers else _default_exception_handler


def with_exception_handler(handler, thunk):
    handlers = current_handlers()
    _state.handlers = (*handlers, handler)
    try:
        return thunk()
    except Exception as error:
        if getattr(error, _DELIVERED, False):
            raise
        # A Python-level error (for example a TypeError from a primitive) that
        # never went through `raise`. The stack has already unwound to here, so
        # deliver it as a non-continuable raise.
        _state.handlers = (*handlers, handler)
        _call_innermost_handler(error)
        _raise_secondary(error)
    finally:
        _state.handlers = handlers


class _GuardSignal(BaseException):
    def __init__(self, token, payload):
        super().__init__()
        self.token = token
        self.payload = payload


GUARD_NO_MATCH = object()


def guard_(handler, thunk):
    """Run `thunk`; on a raise, unwind here and call `handler` with the object.

    `handler` returns `GUARD_NO_MATCH` when none of the guard clauses applied, in
    which case the object is re-raised to the outer handlers.
    """

    token = object()

    def guard_handler(obj):
        raise _GuardSignal(token, obj)

    handlers = current_handlers()
    _state.handlers = (*handlers, guard_handler)
    try:
        return thunk()
    except _GuardSignal as signal:
        if signal.token is not token:
            raise
        payload = signal.payload
    except Exception as error:
        if getattr(error, _DELIVERED, False):
            raise
        payload = _payload(error)
    finally:
        _state.handlers = handlers

    result = handler(payload)
    if result is GUARD_NO_MATCH:
        return raise_continuable(payload)
    return result


def error(message, *irritants):
    raise_(SchemeError(message, _scheme_list(irritants)))


def error_object_q(obj):
    return isinstance(obj, Exception)


def error_object_message(obj):
    if isinstance(obj, SchemeError):
        return obj.message
    return str(obj)


def error_object_irritants(obj):
    if isinstance(obj, SchemeError):
        return obj.irritants
    args = getattr(obj, "args", ())
    if args and isinstance(args[0], str):
        args = args[1:]
    return _scheme_list(args)


def file_error_q(obj):
    return isinstance(obj, OSError)


def read_error_q(obj):
    return isinstance(obj, SyntaxError)


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


class Parameter:
    """R7RS parameter object with per-thread `parameterize` bindings."""

    __name__ = "parameter"

    def __init__(self, value, converter=None):
        self.converter = converter
        self.value = converter(value) if converter is not None else value
        self._local = threading.local()

    def _stack(self):
        stack = getattr(self._local, "stack", None)
        if stack is None:
            stack = self._local.stack = []
        return stack

    def __call__(self):
        stack = getattr(self._local, "stack", None)
        return stack[-1] if stack else self.value

    def __repr__(self):
        return f"<parameter {self()!r}>"


def make_parameter(value, converter=None):
    return Parameter(value, converter)


def parameterize_(thunk, *bindings):
    """Run `thunk` with each `(parameter, value)` pair in `bindings` bound."""

    converted = []
    for parameter, value in bindings:
        if not isinstance(parameter, Parameter):
            raise TypeError(f"parameterize expected a parameter object, got {parameter!r}")
        if parameter.converter is not None:
            value = parameter.converter(value)
        converted.append((parameter, value))
    pushed = []
    try:
        for parameter, value in converted:
            parameter._stack().append(value)
            pushed.append(parameter)
        return thunk()
    finally:
        for parameter in reversed(pushed):
            parameter._stack().pop()


def binding(parameter, value):
    return (parameter, value)

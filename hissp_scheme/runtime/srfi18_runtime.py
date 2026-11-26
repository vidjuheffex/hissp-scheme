"""Runtime substrate for the Scheme `(srfi 18)` library.

SRFI-18 describes a portable Scheme thread system. This module maps the parts
that can be represented honestly onto CPython's `threading` primitives. The
public Scheme library in `srfi18.sld` owns the Scheme names and optional
argument conventions; this file owns the actual OS-thread, mutex, condition,
time, and exception objects.
"""

from __future__ import annotations

import itertools
import threading
import time as _time
from dataclasses import dataclass
from typing import Any, Callable

import hissp

from hissp_scheme.runtime import control_runtime, symbols

_UNSPECIFIED = object()
_thread_ids = itertools.count(1)
_thread_local = threading.local()


class JoinTimeoutException(Exception):
    """Raised when `thread-join!` times out without a timeout value."""


class AbandonedMutexException(Exception):
    """Placeholder for SRFI-18 abandoned-mutex exceptions."""


class TerminatedThreadException(Exception):
    """Raised/stored when a thread is terminated explicitly."""


class UncaughtException(Exception):
    """Wrap an exception that escaped a child thread."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


# Raising a non-exception object with no handler installed produces this; it
# is the same carrier `(scheme base)` uses, so both libraries share one model.
SchemeRaised = control_runtime.SchemeRaise


@dataclass(frozen=True)
class SchemeTime:
    """Absolute time in seconds on Python's monotonic clock."""

    seconds: float


class SchemeThread:
    """SRFI-18 thread object backed by one Python `threading.Thread`."""

    def __init__(self, thunk: Callable[[], Any], name=_UNSPECIFIED):
        self.thunk = thunk
        self.name = name
        self.specific = _UNSPECIFIED
        self.result = None
        self.exception = None
        self.state = "new"
        self.identifier = next(_thread_ids)
        self._done = threading.Condition()
        self._handlers = control_runtime.current_handlers()
        self._thread = threading.Thread(
            target=self._run,
            name=None if name is _UNSPECIFIED else str(name),
            daemon=True,
        )

    def _run(self):
        _thread_local.current = self
        control_runtime.install_handlers(self._handlers)
        with self._done:
            self.state = "running"
            self._done.notify_all()
        try:
            self.result = self.thunk()
        except TerminatedThreadException as error:
            self.exception = error
        except SchemeRaised as error:
            self.exception = UncaughtException(error.reason)
        except BaseException as error:
            self.exception = UncaughtException(error)
        finally:
            with self._done:
                self.state = "terminated"
                self._done.notify_all()


class PrimordialThread:
    """Thread object for the initial Python thread running the program."""

    name = _UNSPECIFIED
    specific = _UNSPECIFIED
    result = None
    exception = None
    state = "running"
    identifier = 0


class SchemeMutex:
    """SRFI-18 mutex over a non-recursive Python lock."""

    def __init__(self, name=_UNSPECIFIED):
        self.name = name
        self.specific = _UNSPECIFIED
        self.owner = None
        self.locked_not_owned = False
        self.abandoned = False
        self._lock = threading.Lock()
        self._meta = threading.Lock()


class SchemeConditionVariable:
    """SRFI-18 condition variable over `threading.Condition`."""

    def __init__(self, name=_UNSPECIFIED):
        self.name = name
        self.specific = _UNSPECIFIED
        self._condition = threading.Condition()


_primordial_thread = PrimordialThread()
_thread_local.current = _primordial_thread


def _symbol(name: str) -> str:
    return symbols.string_to_symbol(name)


current_exception_handler = control_runtime.current_exception_handler
with_exception_handler = control_runtime.with_exception_handler

# SRFI-18 `raise` returns whatever the handler returns, which is R7RS
# `raise-continuable` behavior.
raise_ = control_runtime.raise_continuable


def current_thread():
    return getattr(_thread_local, "current", _primordial_thread)


def thread_q(obj):
    return isinstance(obj, (SchemeThread, PrimordialThread))


def make_thread(thunk, name=_UNSPECIFIED):
    return SchemeThread(thunk, name)


def thread_name(thread):
    return thread.name


def thread_specific(thread):
    return thread.specific


def thread_specific_set_bang(thread, obj):
    thread.specific = obj
    return None


def thread_start_bang(thread):
    if not isinstance(thread, SchemeThread):
        raise TypeError("thread-start! expected a thread created by make-thread")
    with thread._done:
        if thread.state != "new":
            raise RuntimeError("thread-start! expected a new thread")
        thread._thread.start()
    return thread


def thread_yield_bang():
    _time.sleep(0)
    return None


def _seconds_until(timeout):
    if isinstance(timeout, SchemeTime):
        return max(0.0, timeout.seconds - _time.monotonic())
    if timeout is False:
        return None
    if isinstance(timeout, (int, float)):
        return max(0.0, float(timeout))
    raise TypeError(f"invalid SRFI-18 timeout: {timeout!r}")


def thread_sleep_bang(timeout):
    if timeout is False:
        raise ValueError("thread-sleep! requires a timeout")
    _time.sleep(_seconds_until(timeout))
    return None


def thread_terminate_bang(thread):
    if thread is current_thread():
        raise TerminatedThreadException()
    if isinstance(thread, SchemeThread) and thread.state == "new":
        with thread._done:
            thread.exception = TerminatedThreadException()
            thread.state = "terminated"
            thread._done.notify_all()
        return None
    if isinstance(thread, SchemeThread) and thread.state == "terminated":
        return None
    raise NotImplementedError(
        "CPython cannot safely force-terminate a running non-current thread"
    )


def thread_join_bang(thread, timeout=False, timeout_val=_UNSPECIFIED):
    if not isinstance(thread, SchemeThread):
        if thread is current_thread():
            raise RuntimeError("thread-join! cannot join the current thread")
        raise TypeError("thread-join! expected a thread")

    seconds = _seconds_until(timeout)
    deadline = None if seconds is None else _time.monotonic() + seconds
    with thread._done:
        while thread.state != "terminated":
            if deadline is None:
                thread._done.wait()
                continue
            remaining = deadline - _time.monotonic()
            if remaining <= 0:
                if timeout_val is not _UNSPECIFIED:
                    return timeout_val
                raise JoinTimeoutException()
            thread._done.wait(remaining)

        if thread.exception is not None:
            raise thread.exception
        return thread.result


def mutex_q(obj):
    return isinstance(obj, SchemeMutex)


def make_mutex(name=_UNSPECIFIED):
    return SchemeMutex(name)


def mutex_name(mutex):
    return mutex.name


def mutex_specific(mutex):
    return mutex.specific


def mutex_specific_set_bang(mutex, obj):
    mutex.specific = obj
    return None


def mutex_state(mutex):
    with mutex._meta:
        if mutex.abandoned:
            return _symbol("abandoned")
        if mutex.owner is not None:
            return mutex.owner
        if mutex.locked_not_owned:
            return _symbol("not-owned")
        return _symbol("not-abandoned")


def mutex_lock_bang(mutex, timeout=False, owner=_UNSPECIFIED):
    seconds = _seconds_until(timeout)
    if seconds is None:
        acquired = mutex._lock.acquire()
    elif seconds == 0:
        acquired = mutex._lock.acquire(blocking=False)
    else:
        acquired = mutex._lock.acquire(timeout=seconds)
    if not acquired:
        return False

    with mutex._meta:
        was_abandoned = mutex.abandoned
        mutex.abandoned = False
        if owner is False:
            mutex.owner = None
            mutex.locked_not_owned = True
        else:
            mutex.owner = current_thread() if owner is _UNSPECIFIED else owner
            mutex.locked_not_owned = False
    if was_abandoned:
        raise AbandonedMutexException()
    return True


def _release_mutex_if_locked(mutex):
    with mutex._meta:
        mutex.owner = None
        mutex.locked_not_owned = False
        mutex.abandoned = False
    try:
        mutex._lock.release()
    except RuntimeError:
        pass


def mutex_unlock_bang(mutex, condition_variable=False, timeout=False):
    if condition_variable is False:
        _release_mutex_if_locked(mutex)
        return True

    if not isinstance(condition_variable, SchemeConditionVariable):
        raise TypeError("mutex-unlock! expected a condition variable or #f")

    seconds = _seconds_until(timeout)
    with condition_variable._condition:
        _release_mutex_if_locked(mutex)
        if seconds is None:
            condition_variable._condition.wait()
            return True
        return condition_variable._condition.wait(seconds)


def condition_variable_q(obj):
    return isinstance(obj, SchemeConditionVariable)


def make_condition_variable(name=_UNSPECIFIED):
    return SchemeConditionVariable(name)


def condition_variable_name(condition_variable):
    return condition_variable.name


def condition_variable_specific(condition_variable):
    return condition_variable.specific


def condition_variable_specific_set_bang(condition_variable, obj):
    condition_variable.specific = obj
    return None


def condition_variable_signal_bang(condition_variable):
    with condition_variable._condition:
        condition_variable._condition.notify(1)
    return None


def condition_variable_broadcast_bang(condition_variable):
    with condition_variable._condition:
        condition_variable._condition.notify_all()
    return None


def current_time():
    return SchemeTime(_time.monotonic())


def time_q(obj):
    return isinstance(obj, SchemeTime)


def time_to_seconds(value):
    return value.seconds


def seconds_to_time(value):
    return SchemeTime(float(value))


def join_timeout_exception_q(obj):
    return isinstance(obj, JoinTimeoutException)


def abandoned_mutex_exception_q(obj):
    return isinstance(obj, AbandonedMutexException)


def terminated_thread_exception_q(obj):
    return isinstance(obj, TerminatedThreadException)


def uncaught_exception_q(obj):
    return isinstance(obj, UncaughtException)


def uncaught_exception_reason(exc):
    return exc.reason


__all__ = [
    "current_exception_handler",
    "current_thread",
    "thread_q",
    "make_thread",
    "thread_name",
    "thread_specific",
    "thread_specific_set_bang",
    "thread_start_bang",
    "thread_yield_bang",
    "thread_sleep_bang",
    "thread_terminate_bang",
    "thread_join_bang",
    "mutex_q",
    "make_mutex",
    "mutex_name",
    "mutex_specific",
    "mutex_specific_set_bang",
    "mutex_state",
    "mutex_lock_bang",
    "mutex_unlock_bang",
    "condition_variable_q",
    "make_condition_variable",
    "condition_variable_name",
    "condition_variable_specific",
    "condition_variable_specific_set_bang",
    "condition_variable_signal_bang",
    "condition_variable_broadcast_bang",
    "current_time",
    "time_q",
    "time_to_seconds",
    "seconds_to_time",
    "with_exception_handler",
    "raise_",
    "join_timeout_exception_q",
    "abandoned_mutex_exception_q",
    "terminated_thread_exception_q",
    "uncaught_exception_q",
    "uncaught_exception_reason",
]

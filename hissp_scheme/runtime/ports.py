"""R7RS ports for `(scheme base)`.

Ports are Python file objects: `(scheme file)` opens them with `open`, string
ports are `io.StringIO`, and bytevector ports are `io.BytesIO`. Textual ports
read and write `str` (characters are one-character strings); binary ports read
and write bytes (bytevectors are `bytearray`).

Python text streams can't peek, so `peek-char` and `peek-u8` push the item
back into a per-port buffer that the Scheme reading procedures consume first.
Reading the same port through Python methods directly bypasses that buffer.

The current ports are parameter objects whose default is the matching `sys`
stream, looked up at call time, so `with-output-to-file` (which redirects
`sys.stdout`) and `parameterize` both change where output goes.
"""

from __future__ import annotations

import io
import select
import sys
import threading
import weakref

from hissp_scheme.runtime.control_runtime import Parameter


# ---------------------------------------------------------------------------
# End of file
# ---------------------------------------------------------------------------


class EofObject:
    __slots__ = ()

    def __repr__(self):
        return "#<eof>"


EOF = EofObject()


def eof_object():
    return EOF


def eof_object_q(obj):
    return obj is EOF


# ---------------------------------------------------------------------------
# Port classes and predicates
# ---------------------------------------------------------------------------


# Memory ports answer `readable()`/`writable()` even when closed: a closed
# input port is still an input port.


class _InputString(io.StringIO):
    def readable(self):
        return True

    def writable(self):
        return False

    def write(self, text):
        raise io.UnsupportedOperation("input string port is not writable")


class _OutputString(io.StringIO):
    def readable(self):
        return False

    def writable(self):
        return True

    def read(self, size=-1):
        raise io.UnsupportedOperation("output string port is not readable")


class _InputBytes(io.BytesIO):
    def readable(self):
        return True

    def writable(self):
        return False

    def write(self, data):
        raise io.UnsupportedOperation("input bytevector port is not writable")


class _OutputBytes(io.BytesIO):
    def readable(self):
        return False

    def writable(self):
        return True

    def read(self, size=-1):
        raise io.UnsupportedOperation("output bytevector port is not readable")


_MEMORY_PORTS = (io.StringIO, io.BytesIO)


def port_q(obj):
    if isinstance(obj, io.IOBase):
        return True
    return callable(getattr(obj, "read", None)) or callable(getattr(obj, "write", None))


def _direction(port, method, mode_letters):
    # `readable()`/`writable()` raise on closed files, so fall back to `mode`.
    check = getattr(port, method, None)
    if check is None:
        name = "read" if method == "readable" else "write"
        return callable(getattr(port, name, None))
    try:
        return bool(check())
    except ValueError:
        mode = getattr(port, "mode", "")
        return isinstance(mode, str) and any(letter in mode for letter in mode_letters)


def input_port_q(obj):
    return port_q(obj) and _direction(obj, "readable", "r+")


def output_port_q(obj):
    return port_q(obj) and _direction(obj, "writable", "wax+")


def binary_port_q(obj):
    return isinstance(obj, (io.BufferedIOBase, io.RawIOBase))


def textual_port_q(obj):
    return port_q(obj) and not binary_port_q(obj)


def _closed(port):
    return bool(getattr(port, "closed", False))


def input_port_open_q(port):
    return input_port_q(port) and not _closed(port)


def output_port_open_q(port):
    return output_port_q(port) and not _closed(port)


def _require_port(obj, procedure, check=port_q, kind="port"):
    if not check(obj):
        raise TypeError(f"{procedure} expected {kind}, got {obj!r}")
    return obj


def close_port(port):
    _require_port(port, "close-port").close()
    return False


def close_input_port(port):
    _require_port(port, "close-input-port", input_port_q, "an input port").close()
    return False


def close_output_port(port):
    _require_port(port, "close-output-port", output_port_q, "an output port").close()
    return False


def call_with_port(port, proc):
    _require_port(port, "call-with-port")
    result = proc(port)
    port.close()
    return result


# ---------------------------------------------------------------------------
# Current ports
# ---------------------------------------------------------------------------


class _StreamParameter(Parameter):
    """Parameter whose default is a `sys` stream, read on each call."""

    def __init__(self, stream_name):
        self.converter = None
        self.stream_name = stream_name
        self._local = threading.local()

    @property
    def value(self):
        return getattr(sys, self.stream_name)

    def __repr__(self):
        return f"<parameter current-{self.stream_name}-port>"


current_input_port = _StreamParameter("stdin")
current_output_port = _StreamParameter("stdout")
current_error_port = _StreamParameter("stderr")


def _input(port, procedure):
    if port is None:
        return current_input_port()
    return _require_port(port, procedure, input_port_q, "an input port")


def _output(port, procedure):
    if port is None:
        return current_output_port()
    return _require_port(port, procedure, output_port_q, "an output port")


def _binary(port):
    # The current ports are textual; binary I/O on them uses the byte buffer.
    if isinstance(port, io.TextIOBase) and hasattr(port, "buffer"):
        return port.buffer
    return port


# ---------------------------------------------------------------------------
# Pushback for peeking
# ---------------------------------------------------------------------------

_pending = weakref.WeakKeyDictionary()
_pending_unweakrefable = {}


def _take_pending(port, size=None):
    """Remove and return up to `size` pushed-back items (all if None)."""

    try:
        data = _pending.get(port)
        store = _pending
        key = port
    except TypeError:
        data = _pending_unweakrefable.get(id(port), (None, None))[1]
        store = _pending_unweakrefable
        key = id(port)
    if not data:
        return None
    if size is None or size >= len(data):
        del store[key]
        return data
    taken, rest = data[:size], data[size:]
    store[key] = rest if store is _pending else (port, rest)
    return taken


def _push_back(port, data):
    try:
        _pending[port] = data + _pending.get(port, data[:0])
    except TypeError:
        existing = _pending_unweakrefable.get(id(port), (port, data[:0]))[1]
        _pending_unweakrefable[id(port)] = (port, data + existing)


def _has_pending(port):
    try:
        return bool(_pending.get(port))
    except TypeError:
        return bool(_pending_unweakrefable.get(id(port), (None, None))[1])


def _read(port, size):
    """Read exactly up to `size` items, consuming pushed-back data first."""

    data = _take_pending(port, size)
    if data is None:
        return port.read(size)
    if len(data) < size:
        more = port.read(size - len(data))
        if more:
            data += more
    return data


def _ready(port):
    if _has_pending(port) or isinstance(port, _MEMORY_PORTS):
        return True
    try:
        readable, _, _ = select.select([port], [], [], 0)
    except (OSError, TypeError, ValueError, io.UnsupportedOperation):
        return True
    return bool(readable)


# ---------------------------------------------------------------------------
# Textual input
# ---------------------------------------------------------------------------


def read_char(port=None):
    port = _input(port, "read-char")
    char = _read(port, 1)
    return char if char else EOF


def peek_char(port=None):
    port = _input(port, "peek-char")
    char = _read(port, 1)
    if not char:
        return EOF
    _push_back(port, char)
    return char


def _strip_newline(line):
    if line.endswith("\n"):
        line = line[:-1]
        if line.endswith("\r"):
            line = line[:-1]
    return line


def read_line(port=None):
    """Read one line without its terminator, or the EOF object.

    As an extension, a string argument is a prompt written to the current
    output port before reading the current input port.
    """

    if isinstance(port, str):
        out = current_output_port()
        out.write(port)
        out.flush()
        port = None
    port = _input(port, "read-line")
    pending = _take_pending(port)
    if pending is not None:
        newline = pending.find("\n")
        if newline >= 0:
            _push_back(port, pending[newline + 1 :])
            return _strip_newline(pending[: newline + 1])
        line = pending + port.readline()
    elif (
        port is sys.stdin and callable(getattr(port, "isatty", None)) and port.isatty()
    ):
        try:
            return input()
        except EOFError:
            return EOF
    else:
        line = port.readline()
    if not line:
        return EOF
    return _strip_newline(line)


def read_string(k, port=None):
    port = _input(port, "read-string")
    if not (isinstance(k, int) and k >= 0):
        raise TypeError(f"read-string expected a non-negative count, got {k!r}")
    if k == 0:
        return ""
    text = _read(port, k)
    return text if text else EOF


def char_ready_q(port=None):
    return _ready(_input(port, "char-ready?"))


# ---------------------------------------------------------------------------
# Textual output
# ---------------------------------------------------------------------------


def _check_range(sequence, start, end, procedure):
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


def write_char(char, port=None):
    if not (isinstance(char, str) and len(char) == 1):
        raise TypeError(f"write-char expected a character, got {char!r}")
    _output(port, "write-char").write(char)
    return False


def write_string(string, port=None, start=0, end=None):
    if not isinstance(string, str):
        raise TypeError(f"write-string expected a string, got {string!r}")
    start, end = _check_range(string, start, end, "write-string")
    _output(port, "write-string").write(string[start:end])
    return False


def newline(port=None):
    _output(port, "newline").write("\n")
    return False


def flush_output_port(port=None):
    _output(port, "flush-output-port").flush()
    return False


# ---------------------------------------------------------------------------
# String and bytevector ports
# ---------------------------------------------------------------------------


def open_input_string(string):
    if not isinstance(string, str):
        raise TypeError(f"open-input-string expected a string, got {string!r}")
    return _InputString(string)


def open_output_string():
    return _OutputString()


def get_output_string(port):
    if not isinstance(port, _OutputString):
        raise TypeError(
            f"get-output-string expected an output string port, got {port!r}"
        )
    return port.getvalue()


def open_input_bytevector(bytevector):
    if not isinstance(bytevector, (bytes, bytearray)):
        raise TypeError(
            f"open-input-bytevector expected a bytevector, got {bytevector!r}"
        )
    return _InputBytes(bytes(bytevector))


def open_output_bytevector():
    return _OutputBytes()


def get_output_bytevector(port):
    if not isinstance(port, _OutputBytes):
        raise TypeError(
            f"get-output-bytevector expected an output bytevector port, got {port!r}"
        )
    return bytearray(port.getvalue())


# ---------------------------------------------------------------------------
# Binary input and output
# ---------------------------------------------------------------------------


def _binary_input(port, procedure):
    port = _binary(_input(port, procedure))
    if not binary_port_q(port):
        raise TypeError(f"{procedure} expected a binary input port, got {port!r}")
    return port


def _binary_output(port, procedure):
    port = _binary(_output(port, procedure))
    if not binary_port_q(port):
        raise TypeError(f"{procedure} expected a binary output port, got {port!r}")
    return port


def read_u8(port=None):
    data = _read(_binary_input(port, "read-u8"), 1)
    return data[0] if data else EOF


def peek_u8(port=None):
    port = _binary_input(port, "peek-u8")
    data = _read(port, 1)
    if not data:
        return EOF
    _push_back(port, bytes(data))
    return data[0]


def u8_ready_q(port=None):
    return _ready(_binary_input(port, "u8-ready?"))


def read_bytevector(k, port=None):
    port = _binary_input(port, "read-bytevector")
    if not (isinstance(k, int) and k >= 0):
        raise TypeError(f"read-bytevector expected a non-negative count, got {k!r}")
    if k == 0:
        return bytearray()
    data = _read(port, k)
    return bytearray(data) if data else EOF


def read_bytevector_bang(bytevector, port=None, start=0, end=None):
    if not isinstance(bytevector, bytearray):
        raise TypeError(f"read-bytevector! expected a bytevector, got {bytevector!r}")
    port = _binary_input(port, "read-bytevector!")
    start, end = _check_range(bytevector, start, end, "read-bytevector!")
    if start == end:
        return 0
    data = _read(port, end - start)
    if not data:
        return EOF
    bytevector[start : start + len(data)] = data
    return len(data)


def write_u8(byte, port=None):
    if not (isinstance(byte, int) and 0 <= byte <= 255):
        raise TypeError(f"write-u8 expected a byte, got {byte!r}")
    _binary_output(port, "write-u8").write(bytes((byte,)))
    return False


def write_bytevector(bytevector, port=None, start=0, end=None):
    if not isinstance(bytevector, (bytes, bytearray)):
        raise TypeError(f"write-bytevector expected a bytevector, got {bytevector!r}")
    start, end = _check_range(bytevector, start, end, "write-bytevector")
    _binary_output(port, "write-bytevector").write(bytes(bytevector[start:end]))
    return False

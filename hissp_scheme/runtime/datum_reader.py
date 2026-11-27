"""R7RS `read` for `(scheme read)`.

`read` parses one external representation from a textual input port and
returns the datum, leaving the rest of the port unread. It builds the same
values that `quote` produces for source data: lists are `Pair` chains,
symbols are interned `Symbol`s, vectors are Python lists, bytevectors are
`bytearray`, and characters are one-character strings.

The source reader (`hissp_scheme.reader`) can't be reused here: it parses a
whole text at once into Hissp code, while `read` has to stop right after one
datum. Lookahead uses the port pushback buffer from `ports`, so `read` mixes
freely with `read-char`, `peek-char`, and `read-line` on the same port.

Read errors raise `SyntaxError`, which satisfies `read-error?`. Supported
syntax beyond plain data: `'`, `` ` ``, `,`, and `,@` abbreviations, `;` and
nested `#| |#` comments, `#;` datum comments, `|...|` symbols, datum labels
(`#0=` and `#0#`), and the `#!fold-case`/`#!no-fold-case` directives, which
apply to the port for later reads.
"""

from __future__ import annotations

import weakref

import hissp
from scheme_pairs import Pair

from hissp_scheme.runtime.numeric_syntax import string_to_number
from hissp_scheme.runtime.ports import EOF, _input, _push_back, _read
from hissp_scheme.runtime.symbols import intern

_DELIMITERS = frozenset(' \t\n\r\f\v()";|')
_CHARACTER_NAMES = {
    "alarm": "\a",
    "backspace": "\b",
    "delete": "\x7f",
    "escape": "\x1b",
    "newline": "\n",
    "null": "\0",
    "return": "\r",
    "space": " ",
    "tab": "\t",
}
_STRING_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "t": "\t",
    "n": "\n",
    "r": "\r",
    '"': '"',
    "\\": "\\",
    "|": "|",
}
_ABBREVIATIONS = {
    "'": "quote",
    "`": "quasiquote",
    ",": "unquote",
    ",@": "unquote-splicing",
}

_fold_case_ports = weakref.WeakKeyDictionary()
_fold_case_unweakrefable = {}


def _fold_case_q(port):
    try:
        return _fold_case_ports.get(port, False)
    except TypeError:
        return _fold_case_unweakrefable.get(id(port), (None, False))[1]


def _set_fold_case(port, fold):
    try:
        _fold_case_ports[port] = fold
    except TypeError:
        _fold_case_unweakrefable[id(port)] = (port, fold)


def _symbol(name):
    return intern(hissp.munge(name))


class _Dot:
    pass


class _Close:
    pass


_DOT = _Dot()
_CLOSE = _Close()


class _Placeholder:
    __slots__ = ("label",)

    def __init__(self, label):
        self.label = label


class _DatumReader:
    def __init__(self, port):
        self.port = port
        self.fold_case = _fold_case_q(port)
        self.labels = {}

    # Characters -----------------------------------------------------------

    def next(self):
        return _read(self.port, 1)

    def peek(self):
        char = _read(self.port, 1)
        if char:
            _push_back(self.port, char)
        return char

    def expect(self, what):
        char = self.next()
        if not char:
            raise SyntaxError(f"read: end of file inside {what}")
        return char

    # Atmosphere -----------------------------------------------------------

    def skip_line_comment(self):
        while True:
            char = self.next()
            if not char or char == "\n":
                return

    def skip_block_comment(self):
        depth = 1
        previous = ""
        while depth:
            char = self.expect("#| comment")
            if previous == "|" and char == "#":
                depth -= 1
                char = ""
            elif previous == "#" and char == "|":
                depth += 1
                char = ""
            previous = char

    # Tokens ---------------------------------------------------------------

    def token(self, start=""):
        chars = [start]
        while True:
            char = self.next()
            if not char:
                break
            if char in _DELIMITERS:
                _push_back(self.port, char)
                break
            chars.append(char)
        return "".join(chars)

    def escaped_text(self, quote, what):
        chars = []
        while True:
            char = self.expect(what)
            if char == quote:
                return "".join(chars)
            if char != "\\":
                chars.append(char)
                continue
            char = self.expect(what)
            if char in _STRING_ESCAPES:
                chars.append(_STRING_ESCAPES[char])
            elif char in "xX":
                digits = []
                while (char := self.expect(what)) != ";":
                    digits.append(char)
                try:
                    chars.append(chr(int("".join(digits), 16)))
                except ValueError:
                    raise SyntaxError(
                        f"read: bad hex escape \\x{''.join(digits)}; in {what}"
                    ) from None
            elif char in " \t\n\r":
                self.line_continuation(char, what)
            else:
                raise SyntaxError(f"read: unknown escape \\{char} in {what}")

    def line_continuation(self, char, what):
        while char in " \t":
            char = self.expect(what)
        if char == "\r" and self.peek() == "\n":
            char = self.next()
        if char not in "\r\n":
            raise SyntaxError(f"read: backslash before non-newline in {what}")
        while (char := self.peek()) and char in " \t":
            self.next()

    # Data -----------------------------------------------------------------

    def datum(self):
        """Read the next datum; EOF at top level returns the EOF object."""

        item = self.item()
        if item is _CLOSE:
            raise SyntaxError("read: unexpected )")
        if item is _DOT:
            raise SyntaxError("read: unexpected .")
        return item

    def required_datum(self, what):
        item = self.datum()
        if item is EOF:
            raise SyntaxError(f"read: end of file inside {what}")
        return item

    def item(self):
        while True:
            char = self.next()
            if not char:
                return EOF
            if char in " \t\n\r\f\v":
                continue
            if char == ";":
                self.skip_line_comment()
                continue
            if char == "#":
                result = self.hash_syntax()
                if result is not None:
                    return result
                continue
            if char == "(":
                return self.list_tail()
            if char == ")":
                return _CLOSE
            if char == '"':
                return self.escaped_text('"', "string")
            if char == "|":
                return _symbol(self.escaped_text("|", "|symbol|"))
            if char in "'`,":
                if char == "," and self.peek() == "@":
                    self.next()
                    char = ",@"
                datum = self.required_datum(char)
                return Pair(_symbol(_ABBREVIATIONS[char]), Pair(datum, ()))
            return self.atom(self.token(char))

    def atom(self, token):
        if token == ".":
            return _DOT
        number = string_to_number(token)
        if number is not False:
            return number
        return _symbol(token.casefold() if self.fold_case else token)

    def list_tail(self):
        items = []
        tail = ()
        while True:
            item = self.item()
            if item is EOF:
                raise SyntaxError("read: end of file inside list")
            if item is _CLOSE:
                break
            if item is _DOT:
                if not items:
                    raise SyntaxError("read: . at the start of a list")
                tail = self.required_datum("dotted list")
                if self.item() is not _CLOSE:
                    raise SyntaxError("read: expected ) after dotted tail")
                break
            items.append(item)
        result = tail
        for item in reversed(items):
            result = Pair(item, result)
        return result

    def sequence(self, what):
        if self.next() != "(":
            raise SyntaxError(f"read: expected ( after {what}")
        items = []
        while True:
            item = self.item()
            if item is EOF:
                raise SyntaxError(f"read: end of file inside {what}(...)")
            if item is _CLOSE:
                return items
            if item is _DOT:
                raise SyntaxError(f"read: unexpected . in {what}(...)")
            items.append(item)

    def hash_syntax(self):
        """Datum after `#`, or None for comments and directives."""

        char = self.expect("# syntax")
        if char == "|":
            self.skip_block_comment()
            return None
        if char == ";":
            self.required_datum("#; comment")
            return None
        if char == "!":
            directive = self.token()
            if directive == "fold-case":
                self.fold_case = True
            elif directive == "no-fold-case":
                self.fold_case = False
            else:
                raise SyntaxError(f"read: unknown directive #!{directive}")
            _set_fold_case(self.port, self.fold_case)
            return None
        if char == "(":
            _push_back(self.port, char)
            return self.sequence("#")
        if char == "\\":
            return self.character()
        if char.isdigit():
            return self.label(char)
        token = self.token(char)
        lowered = token.lower()
        if lowered in ("t", "true"):
            return True
        if lowered in ("f", "false"):
            return False
        if lowered == "u8":
            items = self.sequence("#u8")
            if not all(type(item) is int and 0 <= item <= 255 for item in items):
                raise SyntaxError("read: #u8(...) elements must be bytes (0-255)")
            return bytearray(items)
        number = string_to_number("#" + token)
        if number is not False:
            return number
        raise SyntaxError(f"read: bad # syntax #{token}")

    def character(self):
        first = self.expect("character")
        if first in _DELIMITERS:
            return first
        name = self.token(first)
        if len(name) == 1:
            return name
        key = name.casefold() if self.fold_case else name
        if key in _CHARACTER_NAMES:
            return _CHARACTER_NAMES[key]
        if key[0] in "xX":
            try:
                return chr(int(key[1:], 16))
            except ValueError:
                pass
        raise SyntaxError(f"read: unknown character #\\{name}")

    def label(self, digit):
        digits = [digit]
        while (char := self.expect("datum label")).isdigit():
            digits.append(char)
        label = int("".join(digits))
        if char == "#":
            if label not in self.labels:
                raise SyntaxError(f"read: undefined datum label #{label}#")
            return self.labels[label]
        if char != "=":
            raise SyntaxError(f"read: bad datum label #{label}{char}")
        placeholder = _Placeholder(label)
        self.labels[label] = placeholder
        datum = self.required_datum(f"#{label}=")
        if datum is placeholder:
            raise SyntaxError(f"read: datum label #{label}= refers only to itself")
        self.labels[label] = datum
        _patch(datum, placeholder, datum)
        return datum


def _patch(datum, placeholder, value):
    """Replace `placeholder` with `value` throughout `datum`'s structure."""

    seen = set()
    stack = [datum]
    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        if node.__class__ is Pair:
            if node.car is placeholder:
                node.car = value
            else:
                stack.append(node.car)
            if node.cdr is placeholder:
                node.cdr = value
            else:
                stack.append(node.cdr)
        elif node.__class__ is list:
            for index, item in enumerate(node):
                if item is placeholder:
                    node[index] = value
                else:
                    stack.append(item)


def read(port=None):
    return _DatumReader(_input(port, "read")).datum()

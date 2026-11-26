"""Scheme booleans. Only `#f` (Python `False`) is false."""

from __future__ import annotations


def not_(value):
    return value is False


def boolean_q(value):
    return value is True or value is False


def boolean_eq_q(first, second, *rest):
    values = (first, second, *rest)
    if not all(boolean_q(value) for value in values):
        raise TypeError("boolean=? expects booleans")
    return all(value is first for value in values)

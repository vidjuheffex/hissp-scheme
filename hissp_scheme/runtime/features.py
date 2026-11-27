"""R7RS feature identifiers for `features` and `cond-expand`."""

from __future__ import annotations

import importlib.util
import os
import platform
import sys

_IMPLEMENTATION = (
    "r7rs",
    "exact-closed",
    "exact-complex",
    "ieee-float",
    "full-unicode",
    "ratios",
    "hissp-scheme",
    "python",
)

_SRFIS = ("srfi-1", "srfi-18", "srfi-28", "srfi-64", "srfi-69", "srfi-132", "srfi-177")


def _platform_features():
    found = ["posix" if os.name == "posix" else "windows"]
    system = platform.system().lower()
    if system == "darwin":
        found += ["darwin", "macosx", "unix"]
    elif system == "linux":
        found += ["linux", "unix"]
    elif system:
        found.append(system)
    machine = platform.machine().lower().replace("_", "-")
    if machine in {"amd64", "x86-64"}:
        machine = "x86-64"
    if machine:
        found.append(machine)
    found.append(f"{sys.byteorder}-endian")
    return found


FEATURES = tuple(dict.fromkeys((*_IMPLEMENTATION, *_SRFIS, *_platform_features())))


def feature_q(name):
    return name in FEATURES


def library_available_q(spec):
    from hissp_scheme.runtime.scheme_bootstrap_runtime import library_module_name

    module_name = library_module_name(spec)
    if module_name in sys.modules:
        return True
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def features():
    from scheme_pairs import py_to_list

    from hissp_scheme.runtime.symbols import string_to_symbol

    return py_to_list([string_to_symbol(name) for name in FEATURES])

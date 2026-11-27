"""Helpers for locating bundled Scheme libraries."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


CORE_LIBRARY_PATHS = (
    ("scheme", "scheme_bootstrap.hissp"),
    ("scheme", "scheme_pairs.sld"),
    ("scheme", "scheme.sld"),
    ("scheme", "scheme_base.sld"),
    ("scheme", "scheme_inexact.sld"),
    ("scheme", "scheme_cxr.sld"),
    ("scheme", "scheme_write.sld"),
    ("scheme", "scheme_read.sld"),
    ("scheme", "scheme_char.sld"),
    ("srfi", "srfi1.sld"),
    ("srfi", "srfi18.sld"),
    ("srfi", "srfi28.sld"),
    ("srfi", "srfi64.sld"),
    ("srfi", "srfi69.sld"),
    ("srfi", "srfi132.sld"),
    ("scheme", "scheme_python.sld"),
    ("scheme", "scheme_file.sld"),
    ("srfi", "srfi177.sld"),
)


def package_dir() -> Path:
    """Return the root package directory containing bundled sources."""

    return Path(str(resources.files(__name__)))


def scheme_source_dir() -> Path:
    """Return the directory containing bundled `(scheme ...)` sources."""

    return package_dir() / "scheme"


def srfi_source_dir() -> Path:
    """Return the directory containing bundled `(srfi ...)` sources."""

    return package_dir() / "srfi"


def core_library_files() -> tuple[Path, ...]:
    """Return core libraries in dependency order for transpilation."""

    base = package_dir()
    return tuple(base / folder / name for folder, name in CORE_LIBRARY_PATHS)

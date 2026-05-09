"""Build-cache helpers for bundled Scheme libraries."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from hissp_scheme import core_library_files, package_dir
from hissp_scheme.reader import transpile_scheme_file


PROJECT_ROOT = package_dir().parent
DEFAULT_BUILD_DIR = PROJECT_ROOT / ".scheme-build"


def ensure_build_path(build_dir: Path | str = DEFAULT_BUILD_DIR) -> Path:
    """Put the generated flat-module directory on `sys.path`."""

    build_path = Path(build_dir).resolve()
    path = str(build_path)
    if path not in sys.path:
        sys.path.insert(0, path)
    return build_path


def build_core_libraries(build_dir: Path | str = DEFAULT_BUILD_DIR) -> Path:
    """Transpile bundled Scheme libraries into `build_dir`."""

    build_path = ensure_build_path(build_dir)
    for module in core_library_files():
        transpile_scheme_file(module, output_dir=build_path)
    importlib.invalidate_caches()
    return build_path

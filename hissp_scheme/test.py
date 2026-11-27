"""Test runner for the bundled Scheme `.scm` SRFI-64 suites."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import hissp.repl

from hissp_scheme.build import DEFAULT_BUILD_DIR, build_core_libraries
from hissp_scheme.reader import SchemeLissp

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = PROJECT_ROOT / "tests"
BUILD_DIR = DEFAULT_BUILD_DIR

TEST_FILES = (
    TEST_DIR / "test_scheme_base.scm",
    TEST_DIR / "test_base_syntax.scm",
    TEST_DIR / "test_ports.scm",
    TEST_DIR / "test_bytevectors.scm",
    TEST_DIR / "test_scheme_write.scm",
    TEST_DIR / "test_scheme_read.scm",
    TEST_DIR / "test_scheme_file.scm",
    TEST_DIR / "test_strings.scm",
    TEST_DIR / "test_scheme_python.scm",
    TEST_DIR / "test_library_imports.scm",
    TEST_DIR / "test_srfi1.scm",
    TEST_DIR / "test_srfi18.scm",
    TEST_DIR / "test_srfi28.scm",
    TEST_DIR / "test_srfi64.scm",
    TEST_DIR / "test_srfi69.scm",
    TEST_DIR / "test_srfi132.scm",
    TEST_DIR / "test_srfi177.scm",
    TEST_DIR / "test_syntax_rules.scm",
    TEST_DIR / "test_reader.scm",
    TEST_DIR / "test_control.scm",
    TEST_DIR / "test_r7rs.scm",
)

COMPILE_ERROR_CASES = (
    (
        "define-library duplicate export",
        "(define-library (scheme test-duplicate-export)\n"
        "  (export value value)\n"
        "  (import (scheme base))\n"
        "  (begin (define value 1)))\n",
        SyntaxError,
        "duplicate define-library export",
    ),
    (
        "define-library unknown clause",
        "(define-library (scheme test-unknown-clause)\n"
        "  (export value)\n"
        "  (import (scheme base))\n"
        "  (frobnicate)\n"
        "  (begin (define value 1)))\n",
        SyntaxError,
        "unsupported define-library clause: frobnicate",
    ),
    (
        "syntax-error from a syntax-rules template",
        "(import (scheme base))\n"
        "(define-syntax test-rejects-everything\n"
        "  (syntax-rules ()\n"
        '    ((_ x) (syntax-error "test-rejects-everything: rejected" x))))\n'
        "(test-rejects-everything (a b))\n",
        SyntaxError,
        "test-rejects-everything: rejected (a b)",
    ),
    (
        "cond-expand invalid requirement",
        '(import (scheme base))\n(cond-expand (("not-a-feature") 1))\n',
        SyntaxError,
        "invalid feature requirement",
    ),
    (
        "bytevector literal out of range",
        "(import (scheme base))\n(define test-bad-bytes #u8(1 256))\n",
        SyntaxError,
        "#u8(...) elements must be bytes",
    ),
    (
        "define-record-type bad field spec",
        "(import (scheme base))\n"
        "(define-record-type <bad> (make-bad) bad? field-without-accessor)\n",
        SyntaxError,
        "field specs must be",
    ),
    (
        "import empty declaration",
        "(import)\n",
        SyntaxError,
        "import requires",
    ),
)

COMPILE_SUCCESS_CASES = (
    (
        "define-library import macro staging",
        "(define-library (scheme test-library-staging)\n"
        "  (export staged-value)\n"
        "  (import (scheme base))\n"
        "  (begin\n"
        "    (define staged-value (and #t 42))))\n",
        "stagedQzH_value",
        42,
    ),
)


def _record_result(name: str, passed: bool, expected, actual) -> None:
    _srfi64_attr("recordQzH_result")(name, passed, expected, actual)


def _srfi64_attr(name: str) -> Any:
    # `srfi64` is generated from Scheme source. Its Python attribute names are
    # Hissp-munged from Scheme exports, so static analyzers cannot know them
    # from the `.sld` file. Keep the dynamic boundary explicit here.
    return getattr(importlib.import_module("srfi64"), name)


def _compile(reader: SchemeLissp, code: str, filename: Path) -> None:
    reader.filename = str(filename)
    reader.env["__file__"] = str(filename)
    reader.compile(code)


def _record_compile_error_checks(reader: SchemeLissp) -> None:
    for name, code, expected_type, expected_message in COMPILE_ERROR_CASES:
        try:
            _compile(reader, code, TEST_DIR / f"<{name}>.scm")
        except expected_type as error:
            actual = str(error)
            passed = expected_message in actual
            _record_result(name, passed, expected_message, actual)
        except BaseException as error:
            _record_result(name, False, expected_type, type(error))
        else:
            _record_result(name, False, expected_type, "no error")


def _record_compile_success_checks(reader: SchemeLissp) -> None:
    for name, code, binding, expected in COMPILE_SUCCESS_CASES:
        try:
            _compile(reader, code, TEST_DIR / f"<{name}>.scm")
            actual = reader.env.get(binding)
            _record_result(name, actual == expected, expected, actual)
        except BaseException as error:
            _record_result(name, False, expected, type(error))


def _record_import_helper_error_checks() -> None:
    from hissp_scheme.runtime import scheme_bootstrap_runtime

    try:
        scheme_bootstrap_runtime.install_import({}, ("rename", "json", ("dumps",)))
    except SyntaxError as error:
        actual = str(error)
        _record_result(
            "import bad rename clause",
            "rename clauses must be" in actual,
            "rename clauses must be",
            actual,
        )
    except BaseException as error:
        _record_result("import bad rename clause", False, SyntaxError, type(error))
    else:
        _record_result("import bad rename clause", False, SyntaxError, "no error")


def main() -> int:
    build_core_libraries(BUILD_DIR)

    main_module = hissp.repl.force_main()
    env = main_module.__dict__
    env["__file__"] = str(TEST_DIR / "<scheme-tests>")

    reader = SchemeLissp(
        env=env, evaluate=True, filename=str(TEST_DIR / "<scheme-tests>")
    )
    _compile(
        reader,
        '(import (scheme base) (srfi 64))\n(test-begin "scheme")\n',
        TEST_DIR / "<begin>.scm",
    )

    for test_file in TEST_FILES:
        _compile(reader, test_file.read_text(encoding="utf8"), test_file)

    _record_compile_error_checks(reader)
    _record_compile_success_checks(reader)
    _record_import_helper_error_checks()

    _compile(reader, '(test-end "scheme")\n', TEST_DIR / "<end>.scm")

    return _srfi64_attr("testQzH_exitQzH_code")()


if __name__ == "__main__":
    raise SystemExit(main())

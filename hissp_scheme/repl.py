"""Interactive Scheme REPL for the bundled language layer."""

from __future__ import annotations

import argparse
import builtins
import sys
from code import InteractiveConsole
from contextlib import suppress
from pathlib import Path

import hissp.repl
from hissp.compiler import CompileError
from hissp.reader import Lissp, SoftSyntaxError

from hissp_scheme.build import DEFAULT_BUILD_DIR, build_core_libraries
from hissp_scheme.runtime.printer import write_string
from hissp_scheme.reader import (
    SCHEME_PRELUDE_TAG,
    SchemeLissp,
    _set_current_source_file,
)


PS1 = "scm> "
PS2 = "... "
DEFAULT_FILENAME = "<scheme-repl>.scm"


def _sys_ps1() -> str:
    return str(getattr(sys, "ps1", PS1))


def _sys_ps2() -> str:
    return str(getattr(sys, "ps2", PS2))


class SchemeFragmentLissp(SchemeLissp):
    """Compile interactive Scheme fragments without reinjecting the prelude."""

    def compile(self, code: str) -> str:
        previous = getattr(self, "scheme_quote_lists", False)
        previous_symbols = getattr(self, "scheme_symbols", False)
        self.scheme_quote_lists = True
        self.scheme_symbols = True
        if self.filename:
            _set_current_source_file(Path(self.filename))
        try:
            return Lissp.compile(self, code)
        finally:
            self.scheme_quote_lists = previous
            self.scheme_symbols = previous_symbols


class SchemeREPL(InteractiveConsole):
    """Read-evaluate-print loop backed by `SchemeLissp`."""

    def __init__(
        self,
        locals: dict[str, object] | None = None,
        filename: str = DEFAULT_FILENAME,
        *,
        show_python: bool = False,
    ) -> None:
        env = {} if locals is None else locals
        super().__init__(env, filename)
        self.lissp = SchemeFragmentLissp(
            env=env,
            evaluate=False,
            filename=filename,
            qualname=str(env.get("__name__", "__main__")),
        )
        self.locals = self.lissp.env
        self.show_python = show_python

    def runsource(
        self, source: str, filename: str = "<input>", symbol: str = "single"
    ) -> bool:
        try:
            self.lissp.filename = filename
            self.locals["__file__"] = filename
            python = self.lissp.compile(source)
        except SoftSyntaxError:
            return True
        except CompileError as error:
            print(f"{_sys_ps1()}# CompileError", file=sys.stderr)
            print(error, file=sys.stderr)
            return False
        except SyntaxError:
            self.showsyntaxerror()
            return False
        except BaseException:
            print(f"{_sys_ps1()}# Compilation failed!", file=sys.stderr)
            self.showtraceback()
            return False

        if self.show_python:
            print(
                _sys_ps1(),
                python.replace("\n", f"\n{_sys_ps2()}"),
                sep="",
                file=sys.stderr,
            )

        compiled_name = (
            f"<Compiled Scheme of {filename}:\n{self.lissp.compiler.linenos(python)}\n>"
        )
        previous_hook = sys.displayhook
        sys.displayhook = _scheme_displayhook
        try:
            return super().runsource(python, compiled_name, symbol)
        finally:
            sys.displayhook = previous_hook

    def raw_input(self, prompt: str = "") -> str:
        prompt = {sys.ps1: PS1, sys.ps2: PS2}.get(prompt, prompt)
        return super().raw_input(prompt)

    def interact(self, banner: str | None = None, exitmsg: str | None = None) -> None:
        with suppress(ImportError):
            import readline  # noqa: F401

        return super().interact(banner, exitmsg)


def _scheme_displayhook(value: object) -> None:
    """Echo REPL results in Scheme `write` notation."""

    if value is None:
        return
    builtins._ = value
    print(write_string(value))


def _exec_repl_python(source: str, env: dict[str, object], filename: str) -> None:
    exec(compile(source, filename, "exec"), env)


def _bootstrap_env(
    env: dict[str, object],
    filename: str,
    *,
    import_base: bool,
) -> None:
    env["__file__"] = filename

    prelude_reader = SchemeLissp(
        env=env,
        evaluate=False,
        filename=filename,
        qualname=str(env.get("__name__", "__main__")),
    )
    _exec_repl_python(
        prelude_reader.compile(SCHEME_PRELUDE_TAG),
        env,
        "<scheme-repl-prelude>",
    )

    if import_base:
        fragment_reader = SchemeFragmentLissp(
            env=env,
            evaluate=False,
            filename=filename,
            qualname=str(env.get("__name__", "__main__")),
        )
        _exec_repl_python(
            fragment_reader.compile("(import (scheme base))"),
            env,
            "<scheme-repl-imports>",
        )


def interact(
    locals: dict[str, object] | None = None,
    *,
    build_dir: Path | str = DEFAULT_BUILD_DIR,
    import_base: bool = True,
    show_python: bool = False,
) -> None:
    """Build bundled libraries and start the interactive Scheme REPL."""

    build_path = build_core_libraries(build_dir)
    if locals is None:
        main_module = hissp.repl.force_main()
        locals = main_module.__dict__

    _bootstrap_env(locals, DEFAULT_FILENAME, import_base=import_base)

    base_status = "(scheme base) imported" if import_base else "no libraries imported"
    banner = (
        f"Hissp Scheme REPL; {base_status}; build cache: {build_path}\nCtrl-D exits."
    )
    SchemeREPL(
        locals=locals,
        filename=DEFAULT_FILENAME,
        show_python=show_python,
    ).interact(banner=banner)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the Hissp Scheme REPL.")
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=DEFAULT_BUILD_DIR,
        help=f"generated library cache directory (default: {DEFAULT_BUILD_DIR})",
    )
    parser.add_argument(
        "--no-base",
        action="store_true",
        help="start without importing (scheme base)",
    )
    parser.add_argument(
        "--show-python",
        action="store_true",
        help="echo compiled Python before evaluating each input",
    )
    args = parser.parse_args(argv)

    interact(
        build_dir=args.build_dir,
        import_base=not args.no_base,
        show_python=args.show_python,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

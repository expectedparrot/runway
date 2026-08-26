"""Tests for what a built wheel actually contains.

Every other test in this suite runs against the source tree, where the
templates and the stylesheet are simply there. In a wheel they are there only
because the build backend was told to carry non-Python files, and the failure
mode if it wasn't is not subtle but it is late: the package imports, the tests
pass in the repo, and rendering raises ``TemplateNotFound`` on somebody else's
machine.

So these assert against the *imported* package rather than against repository
paths -- run the suite against an installed wheel and they check the wheel.

Runs under pytest, or directly: python tests/test_packaging.py
"""

from __future__ import annotations

import importlib
from pathlib import Path

import runway
from runway.renderer import STYLESHEET
from runway.templating import TEMPLATE_DIR

PACKAGE_DIR = Path(runway.__file__).resolve().parent

# Every template the package renders by name. Listed rather than globbed: a
# glob over whatever shipped would pass on a wheel that shipped nothing.
TEMPLATES = (
    "body.html",
    "comment.html",
    "page.html",
    "panel.html",
    "progress.html",
    "toolbar.html",
    "questions/background.html",
    "questions/checkbox.html",
    "questions/checkbox_with_other.html",
    "questions/choice.html",
    "questions/free_text.html",
    "questions/matrix.html",
    "questions/unsupported.html",
)


def test_every_template_ships():
    missing = [name for name in TEMPLATES if not (TEMPLATE_DIR / name).is_file()]
    assert not missing, f"templates absent from the installed package: {missing}"


def test_the_stylesheet_ships():
    """The bulk of a rendered page, and the only reason it looks like anything."""
    assert STYLESHEET.is_file(), f"no stylesheet at {STYLESHEET}"
    assert STYLESHEET.stat().st_size > 10_000, "stylesheet is implausibly small"


def test_the_package_data_sits_inside_the_package():
    """Not found by walking up out of it, which works in a checkout only."""
    for path in (TEMPLATE_DIR, STYLESHEET):
        assert PACKAGE_DIR in path.parents, f"{path} is outside {PACKAGE_DIR}"


def test_the_public_api_is_importable_and_complete():
    for name in runway.__all__:
        assert hasattr(runway, name), f"__all__ names {name}, which does not exist"


def test_the_console_script_target_resolves():
    """The `runway` entry point is `runway.cli:main`; this is the other half."""
    assert callable(importlib.import_module("runway.cli").main)


def _main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc or '(assertion failed)'}")
        else:
            print(f"ok   {name}")
    print("\n" + ("all passed" if not failures else f"{failures} failure(s)"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())

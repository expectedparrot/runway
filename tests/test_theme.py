"""Parity tests for the theme's CSS variables.

The colour utilities the components use more and more -- ``ring-ring``,
``border-ring`` -- name no colour; they read one from a CSS variable the
reference application declares on ``:root``. The recording holds this package's
copy of those declarations to the reference's own stylesheet, so a theme change
there fails here rather than leaving a preview with colours that resolve to
nothing.

Runs under pytest, or directly: python tests/test_theme.py
"""

from __future__ import annotations

import goldens
from runway.renderer import render_page, render_theme

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()


def test_the_theme_matches_the_reference():
    assert render_theme() == GOLDENS["theme_variables"]


def test_it_declares_the_ring_colour():
    # The one the focus rings read today, and the reason this exists.
    assert "--ring:" in render_theme()


QUESTION = {"question_name": "q", "question_type": "free_text", "question_text": "T"}


def test_every_page_carries_it_before_the_stylesheet():
    html = render_page(QUESTION)
    theme = html.index(render_theme())
    assert theme < html.index("<style>", theme + 1)


def test_a_surveys_own_css_comes_after_it():
    # So an author redefining --ring gets their colour, as on the live page.
    html = render_page(QUESTION, custom_css=":root{--ring:0 0% 0%}")
    assert html.index(render_theme()) < html.index(":root{--ring:0 0% 0%}")


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

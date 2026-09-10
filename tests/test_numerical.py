"""Parity tests for the numerical renderer.

The type has two formats and this package draws one. ``input`` is a single number
field, and it is what the reference renders when the humanize schema says nothing
about format -- so it is what nearly every numerical question previews as.
``slider`` is not transcribed, and the tests below are mostly about that boundary
being a stated decline rather than a quiet substitution.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and SPEC.md under "The goldens".

Runs under pytest, or directly: python tests/test_numerical.py
"""

from __future__ import annotations

import goldens
from runway import render_question, render_question_with_comment
from runway.question_types import DECLINES, RENDERERS, numerical

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

QUESTION = {
    "question_name": "visits",
    "question_type": "numerical",
    "question_text": "How many times have you visited?",
}
SLIDER = {"format": {"type": "slider", "min": 0, "max": 100, "step": 1}}


def test_numerical_input_matches_react():
    case = CASES["numerical_input"]
    assert (
        render_question(case["question"], case["humanize_schema"])
        == GOLDENS["numerical_input"]
    )


def test_numerical_is_registered_as_drawn():
    assert RENDERERS["numerical"] is numerical.render
    assert DECLINES["numerical"] is numerical.declines


def test_the_field_carries_an_empty_value():
    """A number input is a controlled field over there where a textarea is not,
    so React renders `value=""` on this one and nothing on the free-text box.
    The two are worth keeping apart: each is what its own component emits."""
    html = render_question(QUESTION)
    assert '<input type="number"' in html
    assert 'value=""/>' in html


def test_an_explicit_input_format_renders_the_same_field():
    """Saying `input` and saying nothing are the same request."""
    assert render_question(QUESTION, {"format": {"type": "input"}}) == render_question(
        QUESTION
    )


def test_a_slider_is_declined_rather_than_drawn_as_a_field():
    """The layout is not transcribed, so the page says so.

    Drawing the number field instead would show a control this respondent is
    never served, and a slider is also the one place the markup depends on the
    schema's *values* -- its bounds and step -- rather than only on its shape.
    """
    assert numerical.declines(QUESTION, SLIDER)
    html = render_question(QUESTION, SLIDER)
    assert '<input type="number"' not in html
    assert 'type="range"' not in html
    # The stand-in, which still shows the wording and the position in the survey.
    assert "How many times have you visited?" in html
    assert "No preview is available" in html


def test_the_field_carries_no_bounds_of_its_own():
    """The reference puts none on it, whatever the schema says elsewhere. A
    `min` or `max` here would be validation this package invented."""
    html = render_question(QUESTION, {"format": {"type": "input"}})
    for attribute in ('min="', 'max="', 'step="'):
        assert attribute not in html


def test_a_comment_still_attaches_to_it():
    html = render_question_with_comment(QUESTION, {"comment": {"label": "Why?"}})
    assert "edsl-numerical-question" in html
    assert "Why?" in html


def test_question_text_is_rendered_as_markdown():
    html = render_question({**QUESTION, "question_text": "How **many**?"})
    assert "<strong>many</strong>" in html


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

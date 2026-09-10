"""Tests for how a preview shows which control a respondent has chosen.

The reference hides the real input, draws the control as a span beside it, and
publishes which one is chosen as ``data-checked`` / ``data-unchecked``
attributes it rewrites on re-render. A preview has no re-render, so left alone
every control stays ``data-unchecked`` however many times it is clicked and a
click changes nothing on screen at all.

This used to be answered in CSS: three authored rules in ``base.css`` keyed off
``:checked`` on the input. They drew the right thing and one of them could not
be made to lose gracefully -- beating the variant utility that hides the dot
took more weight than a survey's own ``.edsl-radio-indicator`` rule had, so a
survey hiding an indicator was overruled in a preview and obeyed on the live
page. Author CSS is emitted last exactly so that cannot happen.

It is answered in the page script now: it rewrites the attribute, as the
reference does, and the component's own utilities do the drawing. What is
asserted here is that the stylesheet went back to being wholly generated, that
the utilities it must hand over to are still in it, and that the script reaches
every page that draws a control.

Runs under pytest, or directly: python tests/test_selected_state.py
"""

from __future__ import annotations

from pathlib import Path

from runway import render_question
from runway import renderer as runway_renderer

STYLESHEET = (Path(runway_renderer.__file__).parent / "assets/questions.css").read_text(
    encoding="utf-8"
)

TEMPLATES = Path(runway_renderer.__file__).parent / "templates"
BASE_CSS = (Path(runway_renderer.__file__).parent / "assets/base.css").read_text(
    encoding="utf-8"
)
SCRIPT = (TEMPLATES / "behaviour.html").read_text(encoding="utf-8")

# The utilities the component carries that now do all the drawing: one hides the
# indicator until the attribute says otherwise, the others colour the control
# once it does.
HIDDEN_UTILITY = r".data-\[unchecked\]\:hidden[data-unchecked]{display:none}"
CHECKED_UTILITIES = (
    r".data-\[checked\]\:border-sky-600[data-checked]",
    r".data-\[checked\]\:bg-sky-600[data-checked]",
)


def test_the_stylesheet_is_wholly_generated():
    """No authored rule keyed off `:checked` survives in either file.

    `base.css` is the build input and the shipped stylesheet is built from it,
    so both are checked: a rule left in the input would come back on the next
    rebuild, and one left in the output is what the package actually serves.
    """
    for source in (BASE_CSS, STYLESHEET):
        assert ".edsl-radio:checked" not in source
        assert ".edsl-checkbox:checked" not in source
        assert ":where(:has(.edsl-radio:checked))" not in source
        assert ":where(:has(.edsl-checkbox:checked))" not in source


def test_the_utilities_that_replaced_them_are_still_shipped():
    """What the script hands the drawing over to. Were any of these dropped
    from the build, a chosen control would go back to looking unchosen -- with
    nothing authored left to cover for it."""
    assert HIDDEN_UTILITY in STYLESHEET
    for utility in CHECKED_UTILITIES:
        assert utility in STYLESHEET, utility


def test_the_script_rewrites_the_attribute_the_reference_rewrites():
    """Both halves of the pair, on the control and on the indicator inside it --
    the reference marks both, and the utilities read one each."""
    assert "data-checked" in SCRIPT and "data-unchecked" in SCRIPT
    assert "-indicator" in SCRIPT


def test_a_survey_hiding_an_indicator_is_honoured():
    """The contract the old CSS broke, which is why it is gone.

    Nothing in the packaged stylesheet sets `display` on an indicator any more,
    so an author's rule meets only the variant utility -- exactly what it meets
    on the live page, where the attribute has flipped for the same reason.
    """
    assert "display:revert" not in STYLESHEET
    page = runway_renderer.render_page(
        {
            "question_name": "q",
            "question_type": "multiple_choice",
            "question_text": "T",
            "question_options": ["a", "b"],
        },
        custom_css=".edsl-radio-indicator{display:none}",
    )
    assert page.index(HIDDEN_UTILITY) < page.index(".edsl-radio-indicator{display:none}")


def test_the_script_reaches_every_page_that_draws_a_control():
    """The gate is "was a control drawn", read off the rendered body, so a type
    that starts drawing one is covered without anything here being told."""
    for question_type, extra in (
        ("multiple_choice", {"question_options": ["a", "b"]}),
        ("yes_no", {"question_options": ["Yes", "No"]}),
        ("checkbox", {"question_options": ["a", "b"]}),
        ("multiple_choice_with_other", {"question_options": ["a", "b"]}),
        ("matrix", {"question_items": ["row"], "question_options": ["a", "b"]}),
    ):
        page = runway_renderer.render_page(
            {
                "question_name": "q",
                "question_type": question_type,
                "question_text": "T",
                **extra,
            }
        )
        assert "syncControls" in page, question_type

    # And stops at a question that draws no control at all.
    text_only = runway_renderer.render_page(
        {"question_name": "q", "question_type": "free_text", "question_text": "T"}
    )
    assert "syncControls" not in text_only


def test_no_row_highlight_is_invented_anywhere():
    """The drawing reaches the control and stops there.

    An earlier version highlighted the whole option row for the stacked matrix
    and the carousel, because the reference drew those rows as cards whose
    classes it swapped. It draws them as plain rows now, like every other
    question's options, so a rule reaching `.edsl-option` would draw a
    highlight no live survey draws.
    """
    assert ".edsl-option:where(:has(:checked))" not in STYLESHEET


def test_the_controls_are_what_the_questions_actually_emit():
    """The script finds controls by class; these are the classes drawn."""
    choice = render_question(
        {
            "question_name": "q",
            "question_type": "multiple_choice",
            "question_text": "T",
            "question_options": ["a", "b"],
        }
    )
    assert "edsl-radio-control" in choice and "edsl-radio-indicator" in choice

    checkbox = render_question(
        {
            "question_name": "q",
            "question_type": "checkbox",
            "question_text": "T",
            "question_options": ["a", "b"],
        }
    )
    assert "edsl-checkbox-control" in checkbox and "edsl-checkbox-indicator" in checkbox

    # The matrix asks for the same control at a second size, in both the layouts
    # it draws -- the grid and the carousel. The carousel is checked explicitly
    # because it was once left out of a rule the stacked list had.
    matrix = {
        "question_name": "q",
        "question_type": "matrix",
        "question_text": "T",
        "question_items": ["row"],
        "question_options": ["a", "b"],
    }
    for schema in (None, {"format": {"type": "carousel"}}):
        html = render_question(matrix, schema)
        assert "edsl-radio-control" in html and "edsl-radio-indicator" in html


def test_a_surveys_own_css_is_still_emitted_last():
    """The contract the whole change is in service of."""
    page = runway_renderer.render_page(
        {
            "question_name": "q",
            "question_type": "multiple_choice",
            "question_text": "T",
            "question_options": ["a", "b"],
        },
        custom_css=".edsl-radio-control{border-color:red}",
    )
    assert page.index(HIDDEN_UTILITY) < page.index(
        ".edsl-radio-control{border-color:red}"
    )


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

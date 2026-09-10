"""Parity tests for the multiple-choice-with-other renderer.

A choice question with one more row, and the row is where the interesting claims
are: it is a radio in the same group as the options, so the two are exclusive of
each other with no rule anywhere, and the text field beneath it is named by the
label above rather than by a copy of the same words.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and SPEC.md under "The goldens".

Runs under pytest, or directly: python tests/test_multiple_choice_with_other.py
"""

from __future__ import annotations

import goldens
from runway import render_question, render_question_with_comment, renderer
from runway.question_types import RENDERERS, multiple_choice_with_other

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

# The behaviour script, identified as `test_checkbox.py` identifies it: the one
# line only it has.
SCRIPT = "closest('[data-exclusive]')"


def a_question(**overrides: object) -> dict:
    return {
        "question_name": "destination",
        "question_type": "multiple_choice_with_other",
        "question_text": "Where would you go?",
        "question_options": ["Beach", "Mountains", "City"],
        "other_option_text": "Somewhere else",
        **overrides,
    }


def test_multiple_choice_with_other_matches_react():
    case = CASES["multiple_choice_with_other"]
    assert (
        render_question(case["question"], case["humanize_schema"])
        == GOLDENS["multiple_choice_with_other"]
    )


def test_it_is_registered_as_drawn():
    assert (
        RENDERERS["multiple_choice_with_other"] is multiple_choice_with_other.render
    )


def test_the_other_row_shares_the_options_radio_group():
    """Which is what makes choosing it clear whichever option was picked, and
    the other way round, with no script and no rule."""
    html = render_question(a_question())
    assert html.count('name="destination"') == 4
    assert 'value="Somewhere else"' in html


def test_the_written_answer_is_one_field():
    """This type takes a single answer. The checkbox flavour takes several and
    draws a row apiece, with the buttons to add and remove them."""
    html = render_question(a_question())
    assert html.count('<input type="text"') == 1
    assert "edsl-other-add" not in html and "edsl-other-remove" not in html


def test_the_field_is_named_by_the_label_above_it():
    """`aria-labelledby` pointing at the visible label, not a copy of its words:
    the label is the author's and renders markdown, so a copy would drift."""
    html = render_question(a_question())
    assert 'id="destination-other-label"' in html
    assert 'aria-labelledby="destination-other-label"' in html
    assert "aria-label=" not in html


def test_the_other_label_is_the_authors_word():
    html = render_question(a_question(other_option_text="Anything else"))
    assert ">Anything else</span>" in html
    assert 'value="Anything else"' in html


def test_a_missing_other_label_renders_empty_rather_than_none():
    """React renders `undefined` as nothing. Emitting the string "None" would
    put a label on the page that no author wrote."""
    html = render_question(a_question(other_option_text=None))
    assert "None" not in html
    assert 'id="destination-other-label"' in html


def test_the_field_is_unanswered():
    """A preview shows the page as it opens: nothing chosen, nothing typed."""
    html = render_question(a_question())
    assert 'value=""/>' in html
    # Matched with the leading space, and `data-checked` spelled out: bare
    # `checked` appears inside both the `data-[checked]:` utilities every control
    # carries and the `data-unchecked` attribute saying none is chosen.
    assert ' checked=""' not in html
    assert ' data-checked=""' not in html
    # Two per control -- the control and its indicator -- across four radios.
    assert html.count('data-unchecked=""') == 8


def test_option_labels_are_rendered_as_markdown():
    html = render_question(a_question(question_options=["**Beach**", "City"]))
    assert "<strong>Beach</strong>" in html
    # The value stays the author's string, markers and all -- it is the answer,
    # not a label.
    assert 'value="**Beach**"' in html


def test_options_are_escaped_the_way_react_escapes_them():
    html = render_question(a_question(question_options=["Couldn't say"]))
    assert "&#x27;" in html and "&#39;" not in html


def test_piped_options_explain_themselves():
    """Options piped from a scenario cannot be enumerated outside a live run, so
    the reference substitutes a line saying so and this reproduces it."""
    html = render_question(a_question(question_options="{{ scenario.places }}"))
    assert "{{ scenario.places }}" in html
    assert "In a live survey" in html


def test_a_comment_still_attaches_to_it():
    html = render_question_with_comment(a_question(), {"comment": {"label": "Why?"}})
    assert "edsl-multiple-choice-with-other-question" in html
    assert "Why?" in html


# --------------------------------------------------------------------------
# The one rule the markup cannot carry
# --------------------------------------------------------------------------
#
# Choosing between a listed option and this one settles itself, the two being
# radios in a group. What does not is typing: the field sits below the row it
# belongs to, and nothing about entering text chooses it. So the page ships the
# behaviour script for that alone -- see `templates/behaviour.html`, where the
# checkbox flavour states the same rule for the same reason.


def test_the_script_ships_for_a_page_holding_one():
    """The bug this guards: the script's gate used to be "is there a checkbox
    here", so a page of nothing but this type shipped no script at all and a
    typed answer left the row above it unchosen."""
    assert SCRIPT in renderer.render_page(a_question())


def test_the_script_binds_this_type_by_name():
    """Shipping it is half the fix. The script walks a list of classes, and this
    type was not on it -- so even a page that happened to hold a checkbox too
    left this question unbound."""
    page = renderer.render_page(a_question())
    assert "setUpChoiceOther" in page
    assert "'.edsl-multiple-choice-with-other-question'" in page


def test_the_add_another_button_is_not_parked_for_it():
    """The script's gate and the template's are separate questions now. This
    type takes one written answer, so there is no row to add a second to, and
    parking the button would put markup on the page nothing could use."""
    page = renderer.render_page(a_question())
    assert 'id="preview-other-add"' not in page


def test_an_ordinary_choice_question_still_ships_nothing():
    """Widening the gate must not hand the script to every survey."""
    page = renderer.render_page(
        {
            "question_name": "destination",
            "question_type": "multiple_choice",
            "question_text": "Where would you go?",
            "question_options": ["Beach", "City"],
        }
    )
    assert SCRIPT not in page


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

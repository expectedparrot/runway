"""Tests for the questions a respondent is never shown.

Compute, image generation and thinking-wrapped questions are answered on the
server between pages and advanced straight past by the survey navigator. The
preview has to say so rather
than draw a control, and the case that matters most is the thinking wrapper: it
leaves the question's type alone, so nothing about ``multiple_choice`` says the
page is never served. Getting that wrong draws a plausible radio list for a
question no respondent will ever meet.

Uses examples/background_survey.json, which carries all three kinds alongside
questions of the same types that *are* shown.

Runs under pytest, or directly:
    python tests/test_background.py
"""

from __future__ import annotations

from pathlib import Path

from runway.question_types import background
from runway.renderer import render_bundle, render_question
from runway.survey import load

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "background_survey.json"

NOTICE = "Answered automatically"


def _questions() -> dict[str, dict]:
    questions, _ = load(EXAMPLE)
    return {question["question_name"]: question for question in questions}


def _render(question_name: str) -> str:
    return render_question(_questions()[question_name])


# --------------------------------------------------------------------------
# Which questions are background questions
# --------------------------------------------------------------------------


def test_the_three_kinds_are_recognized():
    questions = _questions()
    assert background.kind_of(questions["pet_category"]) == "thinking"
    assert background.kind_of(questions["pet_portrait"]) == "image_generation"
    assert background.kind_of(questions["pet_word_count"]) == "compute"


def test_questions_put_to_a_respondent_are_not():
    questions = _questions()
    for name in ("pet", "pet_attachment", "pet_story"):
        assert background.kind_of(questions[name]) is None, name


def test_the_wrapper_is_detected_by_its_model_not_its_prompt():
    # thinking_question() defaults the system prompt to "", so a question
    # wrapped without one would go undetected if that were the marker.
    wrapped = {"question_type": "free_text", "thinking_model": {"model": "test"}}
    assert background.is_background_question(wrapped)
    assert not background.is_background_question(
        {"question_type": "free_text", "thinking_system_prompt": ""}
    )


def test_the_type_decides_before_the_wrapper():
    # Matching the runner, which evaluates a compute question locally whatever
    # else is attached to it.
    both = {"question_type": "compute", "thinking_model": {"model": "test"}}
    assert background.kind_of(both) == "compute"


# --------------------------------------------------------------------------
# What the page says
# --------------------------------------------------------------------------


def test_a_thinking_question_is_not_drawn_as_the_type_it_wrapped():
    # The whole point: pet_category is a multiple_choice, and this package
    # draws multiple_choice. Drawing it here would show a control for a page
    # that is never served.
    html = _render("pet_category")
    assert 'type="radio"' not in html
    assert "Unusual" not in html
    assert NOTICE in html


def test_a_shown_question_of_the_same_type_is_still_drawn():
    # The counterpart, so the interception is known to be about the wrapper
    # rather than about multiple_choice.
    html = _render("pet")
    assert 'type="radio"' in html
    assert NOTICE not in html


def test_each_kind_says_why_it_is_answered_without_a_respondent():
    assert "computed on the server" in _render("pet_word_count")
    assert "An image model generates" in _render("pet_portrait")
    assert "using the model and system prompt" in _render("pet_category")


def test_the_notice_is_neither_the_note_nor_the_warning():
    # Three situations, three notices. "No preview yet" would be wrong (there
    # is nothing to preview) and so would "not supported in human surveys" (it
    # is supported, and it runs).
    for name in ("pet_category", "pet_portrait", "pet_word_count"):
        html = _render(name)
        assert "edsl-preview-background" in html, name
        assert "No preview is available" not in html, name
        assert "Not supported in human surveys" not in html, name


def test_a_background_questions_prompt_is_not_shown():
    # It is a prompt for a model or an expression for the server. Rendering it
    # in the usual question-text markup would imply a page the survey never
    # serves.
    html = _render("pet_portrait")
    assert "watercolour portrait" not in html
    assert "edsl-question-text" not in html


def test_an_undrawn_type_that_is_shown_still_gets_the_plain_note():
    # `list` has no control here yet, but it is put to a respondent, so it
    # keeps the "no preview yet" note and its question text. It stands in for
    # whatever is undrawn at the time: this was free_text until free_text was
    # drawn, which is the failure that says to move it on again.
    html = _render("pet_story")
    assert "No preview is available" in html
    assert "Tell us about them." in html
    assert NOTICE not in html


# --------------------------------------------------------------------------
# In a whole survey
# --------------------------------------------------------------------------


def test_the_toolbar_marks_the_pages_no_respondent_sees():
    # A thinking question keeps the type it wrapped, so the type alone cannot
    # tell the two multiple_choice entries apart.
    questions, humanize_schema = load(EXAMPLE)
    html = render_bundle(questions, humanize_schema)
    assert ">1. pet — Multiple Choice</option>" in html
    assert ">2. pet_category — Multiple Choice (automatic)</option>" in html
    assert ">3. pet_portrait — Image Generation (automatic)</option>" in html
    assert ">4. pet_word_count — Compute (automatic)</option>" in html
    assert ">5. pet_attachment — Linear Scale</option>" in html


def test_every_background_question_gets_its_own_panel():
    # They are survey items like any other: they count for progress and they
    # are worth looking at, they just have nothing to answer.
    questions, humanize_schema = load(EXAMPLE)
    html = render_bundle(questions, humanize_schema)
    assert html.count("edsl-preview-background") == 3
    assert html.count('class="preview-panel') == 6


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

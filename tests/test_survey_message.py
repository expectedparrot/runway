"""Parity tests for the survey-message renderer.

A message is a page a respondent reads and continues past: the question text,
no control, nothing a schema can change. That makes most of what is worth
testing here a question of what should *not* appear -- no input, no notice, no
schema-driven anything.

Two cases are recorded: a one-paragraph message, and a multi-block one -- a
heading, a paragraph and a list. The second is deliberately narrow. It records
nothing about the question-text div that the `markdown_text_*` cases do not
already record, because those render their text through the same component; what
it is the only case to do is put more than one markdown block through *this*
component, which is what would catch a message growing prose handling of its
own.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and SPEC.md under "The goldens".

Runs under pytest, or directly: python tests/test_survey_message.py
"""

from __future__ import annotations

import re

import goldens
from runway import render_question, render_question_with_comment
from runway.question_types import RENDERERS, survey_message, unsupported
from runway.renderer import pretty_type

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

QUESTION = CASES["survey_message"]["question"]

# The reference's own question-text opening tag, lifted out of a recording
# rather than written here.
QUESTION_TEXT_TAG = re.search(
    r'<div class="edsl-question-text[^"]*">', GOLDENS["survey_message"]
).group(0)


def test_it_matches_react():
    case = CASES["survey_message"]
    assert (
        render_question(case["question"], case["humanize_schema"])
        == GOLDENS["survey_message"]
    )


def test_a_multi_block_message_matches_react():
    """A heading, a paragraph and a list -- the shape a message is written in.

    The only recorded case putting more than one markdown block through this
    component, so it is what holds a message to rendering prose the way every
    other type does rather than growing handling of its own. The question-text
    div itself is already held by the `markdown_text_*` cases, which render the
    same markdown through a multiple choice.
    """
    case = CASES["survey_message_multi_block"]
    assert (
        render_question(case["question"], case["humanize_schema"])
        == GOLDENS["survey_message_multi_block"]
    )


def test_the_wrapper_names_the_type():
    """The type-specific hook a survey's custom_css reaches a message by, around
    the question-text markup every type shares."""
    html = render_question(QUESTION)
    assert html.startswith(
        '<div class="edsl-question edsl-survey-message-question mb-6">'
        + QUESTION_TEXT_TAG
    )
    assert html.endswith("</div></div>")


def test_it_is_registered_as_drawn():
    assert RENDERERS["survey_message"] is survey_message.render
    assert "survey_message" in unsupported.HUMANIZED_TYPES


def test_it_carries_no_control_at_all():
    """The whole of the type: text and nothing else. An input here would be a
    page the survey never serves -- a message takes no answer, which is why the
    reference component registers no form field for one."""
    html = render_question(QUESTION)
    for control in ("<input", "<textarea", "<select", "<button"):
        assert control not in html


def test_it_is_not_shown_as_missing_or_unsupported():
    """The empty page is the page. A message rendered through either stand-in
    would apologise for a control that is not meant to exist, or claim a survey
    needs fixing when it does not."""
    html = render_question(QUESTION)
    assert "No preview is available" not in html
    assert "Not supported in human surveys" not in html
    assert "Answered automatically" not in html


def test_it_is_not_treated_as_answered_on_the_server():
    """A message and a compute question are both drawn without a control and are
    opposites underneath: nobody is served a compute page, everybody is served
    this one."""
    from runway.question_types import background

    assert not background.is_background_question(QUESTION)


def test_question_text_is_rendered_as_markdown():
    html = render_question({**QUESTION, "question_text": "Welcome to **the study**."})
    assert "<strong>the study</strong>" in html


def test_question_text_is_escaped_the_way_react_escapes_it():
    assert "&#x27;" in render_question(QUESTION)
    assert "&#39;" not in render_question(QUESTION)


def test_markup_in_the_message_is_not_injectable():
    """react-markdown runs without rehype-raw, so a raw HTML block is escaped
    text. A message is the likeliest place for an author to try HTML, which
    makes this worth pinning here as well as in test_markdown."""
    html = render_question({**QUESTION, "question_text": "<script>alert(1)</script>"})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_the_schema_changes_nothing():
    """EDSL's humanize schema for this type is deliberately empty -- a message
    asks nothing, so there is no optionality, no comment field and no submitting
    indicator to configure. A schema that changed the markup would mean this
    template had grown a setting the live page does not honour."""
    plain = render_question(QUESTION)
    for schema in ({"format": {"type": "dropdown"}}, {"exclusive_options": ["a"]}, {}):
        assert render_question(QUESTION, schema) == plain


def test_a_schema_that_asks_for_a_comment_is_still_a_sibling():
    """The comment box is composed around every question rather than by any
    renderer, so it reaches this type too. Nothing in a valid schema can ask for
    one here -- the message schema has no comment field -- but the box is not
    the renderer's to refuse, and a message's own markup is unchanged by it."""
    html = render_question_with_comment(QUESTION, {"comment": {"label": "Why?"}})
    assert html.startswith(render_question(QUESTION))


def test_it_is_named_message_in_the_toolbar():
    """Following the reference, where the type is presented as Message. The
    automatic title-casing would give "Survey Message", which no author sees."""
    assert pretty_type("survey_message") == "Message"


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

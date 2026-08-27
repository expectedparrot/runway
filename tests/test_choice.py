"""Parity tests for the choice-family renderers and the comment box.

The family is multiple_choice, likert_five, yes_no and linear_scale: four
question types the reference implements as four components differing only in
the class on their outer div, so this package renders them from one template.
Each type is recorded separately all the same -- the point of a parity test is
to notice if that stops being true.

The markup to match is not written here. It is recorded from the reference
implementation's own React components -- ``renderToStaticMarkup`` on the ones
it exports -- into ``react_goldens.json``, from the case list in
``react_cases.json``. These tests read those two files and require
byte-for-byte equality.

Recording rather than transcribing is what makes this a contract rather than a
snapshot of somebody's best guess: when a reference component changes, the
re-recorded file lands here and the diff says exactly what to change. See
SPEC.md under "The goldens".

Runs under pytest, or directly: python tests/test_choice.py
"""

from __future__ import annotations

import goldens
from runway import (
    render_comment,
    render_question,
    render_question_with_comment,
)
from runway.question_types import RENDERERS, choice, get_renderer, unsupported

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

# Which kinds this file's sweep covers, and how each is rendered, both live in
# goldens.py -- so a new kind is taught to every parity test at once rather than
# to whichever one its author remembered.
RENDER_BY_KIND = goldens.RENDER_BY_KIND


def question_case(name: str) -> str:
    """This package's markup for a recorded question case."""
    return goldens.render_case(CASES[name])


# --------------------------------------------------------------------------
# The goldens themselves
# --------------------------------------------------------------------------


def test_every_case_has_a_golden():
    """The two recorded files are a matched pair.

    A case added to ``react_cases.json`` without a golden beside it would
    otherwise be silently skipped by every comparison below.
    """
    goldens.check_pairing()


def test_every_recorded_question_case_matches():
    """Every question case in the file, compared against its recording.

    The named tests below say what each interesting case is *for*; this one is
    the guarantee that no case can be recorded without also being checked.
    Without it a case added to ``react_cases.json`` gets a golden from
    a golden and no assertion -- recorded, green, and never compared -- which
    is how the markdown cases sat for a while.
    """
    drifted = []
    for name, case in sorted(CASES.items()):
        if case["kind"] not in RENDER_BY_KIND:
            continue
        if question_case(name) != GOLDENS[name]:
            drifted.append(name)
    assert not drifted, f"this package does not render {drifted} as recorded"


# --------------------------------------------------------------------------
# multiple_choice
# --------------------------------------------------------------------------


def test_radio_matches_react():
    assert question_case("multiple_choice_radio") == GOLDENS["multiple_choice_radio"]


def test_dropdown_matches_react():
    html = question_case("multiple_choice_dropdown")
    assert html == GOLDENS["multiple_choice_dropdown"]
    # Named separately from the byte comparison because it is the behaviour the
    # humanize schema selects: the dropdown replaces the radios, not joins them.
    assert 'type="radio"' not in html


def test_escaping_matches_react():
    # React's escaping is not MarkupSafe's: it emits &#x27; and &quot; where
    # MarkupSafe emits &#39; and &#34;, and it escapes quotes in text content as
    # well as in attributes. This case carries an apostrophe, a double quote and
    # angle brackets in both the question text and an option, in both a text
    # node and an attribute value.
    assert (
        question_case("multiple_choice_escaped") == GOLDENS["multiple_choice_escaped"]
    )


# --------------------------------------------------------------------------
# likert_five and yes_no
#
# The same template as multiple_choice, so what these tests are really for is
# the one thing that differs -- the wrapper class -- and the assurance that it
# stays the one thing.
# --------------------------------------------------------------------------


def test_likert_radio_matches_react():
    assert question_case("likert_five_radio") == GOLDENS["likert_five_radio"]


def test_likert_dropdown_matches_react():
    assert question_case("likert_five_dropdown") == GOLDENS["likert_five_dropdown"]


def test_yes_no_radio_matches_react():
    assert question_case("yes_no_radio") == GOLDENS["yes_no_radio"]


def test_yes_no_dropdown_matches_react():
    assert question_case("yes_no_dropdown") == GOLDENS["yes_no_dropdown"]


# --------------------------------------------------------------------------
# linear_scale
#
# The one member of the family whose options are not their own labels: it
# answers with a number and shows "3 - Couldn't be better".
# --------------------------------------------------------------------------


def test_linear_scale_radio_matches_react():
    assert question_case("linear_scale_radio") == GOLDENS["linear_scale_radio"]


def test_linear_scale_dropdown_matches_react():
    assert question_case("linear_scale_dropdown") == GOLDENS["linear_scale_dropdown"]


def test_linear_scale_unlabelled_matches_react():
    # option_labels null is a scale with no named ends -- every point shows its
    # own number. Recorded because null is the only empty form the reference
    # survives: `option in undefined` throws, so a question with no
    # option_labels at all cannot be served.
    assert (
        question_case("linear_scale_unlabelled") == GOLDENS["linear_scale_unlabelled"]
    )


def test_scale_answers_with_the_number_and_shows_the_label():
    # The distinction the whole family's value/label split exists for: what is
    # submitted is the scale point, what is read is the sentence.
    html = question_case("linear_scale_radio")
    assert 'value="1"/>' in html
    assert ">1 - Couldn&#x27;t be worse</span>" in html
    # ...and an unnamed point in the middle is just its number, in both places.
    assert 'value="3"/>' in html
    assert ">3</span>" in html


def test_scale_labels_are_found_however_their_keys_arrived():
    # A live EDSL question has integer keys; the same question through JSON has
    # strings. The reference cannot tell the difference -- JavaScript property
    # access stringifies the key -- so neither may this.
    question = {
        "question_name": "q",
        "question_type": "linear_scale",
        "question_text": "How is it?",
        "question_options": [1, 2],
    }
    from_json = render_question({**question, "option_labels": {"1": "Bad"}})
    from_edsl = render_question({**question, "option_labels": {1: "Bad"}})
    assert ">1 - Bad</span>" in from_json
    assert from_edsl == from_json


def test_a_missing_label_table_previews_as_a_bare_scale():
    # The reference would throw on this rather than render it, so there is no
    # golden to match; not drawing the question at all would say less about it
    # than drawing the scale does.
    html = render_question(
        {
            "question_name": "q",
            "question_type": "linear_scale",
            "question_text": "How is it?",
            "question_options": [1, 2],
        }
    )
    assert html.count('type="radio"') == 2
    assert " - " not in html


def test_whole_numbers_written_as_floats_keep_javascripts_spelling():
    # JavaScript has one number type, so a scale point serialized as 1.0 reads
    # as "1" over there. Python's str() would write "1.0" and every value and
    # label on the scale would silently disagree with the live page.
    html = render_question(
        {
            "question_name": "q",
            "question_type": "linear_scale",
            "question_text": "How is it?",
            "question_options": [1.0, 2.0],
            "option_labels": {1.0: "Bad"},
        }
    )
    assert 'value="1"/>' in html and 'value="2"/>' in html
    assert ">1 - Bad</span>" in html
    assert "1.0" not in html


def test_each_choice_type_keeps_its_own_wrapper_class():
    # The hook a stylesheet targets one of these types by. Sharing a template
    # must not mean sharing an identity: a survey styling
    # `.edsl-likert-question` has to reach the Likert questions and nothing else.
    for name, wrapper in (
        ("multiple_choice_radio", "edsl-multiple-choice-question"),
        ("likert_five_radio", "edsl-likert-question"),
        ("yes_no_radio", "edsl-yes-no-question"),
        ("linear_scale_radio", "edsl-linear-scale-question"),
    ):
        html = question_case(name)
        assert f'class="edsl-question {wrapper} mb-6"' in html, name


def test_the_family_renders_from_one_template():
    # Three registrations, one renderer: the reference shares an implementation
    # across these types, and this package's saving is the same one. A fourth
    # type registered here without being in TYPES would render with the multiple
    # choice wrapper and no test would say so, which is what this catches.
    assert {t for t, r in RENDERERS.items() if r is choice.render} == set(choice.TYPES)


def test_an_unknown_type_renders_as_a_multiple_choice():
    # Only reachable by calling the renderer directly -- an unregistered type
    # goes to the stand-in -- so the point is that the lookup cannot raise.
    html = choice.render(
        {
            "question_type": "not_a_type",
            "question_name": "q",
            "question_text": "Pick one",
            "question_options": ["A"],
        }
    )
    assert 'class="edsl-question edsl-multiple-choice-question mb-6"' in html


# --------------------------------------------------------------------------
# The comment box
# --------------------------------------------------------------------------


def test_question_block_with_comment_matches_react():
    assert (
        question_case("question_block_with_comment")
        == GOLDENS["question_block_with_comment"]
    )


def test_question_block_without_comment_matches_react():
    assert (
        question_case("question_block_without_comment")
        == GOLDENS["question_block_without_comment"]
    )


def test_a_configured_comment_is_the_only_difference():
    # The comment box is purely additive: with no comment configured the block
    # is the bare question, byte for byte. Recorded, not assumed -- the live
    # page reaches the question through a controlled wrapper, and this is what
    # says that wrapper contributes no markup of its own.
    assert GOLDENS["question_block_without_comment"] == GOLDENS["multiple_choice_radio"]
    with_comment = GOLDENS["question_block_with_comment"]
    assert with_comment.startswith(GOLDENS["question_block_without_comment"])


def test_comment_box_is_a_sibling_of_the_question():
    # Not nested inside it -- so it applies to every question type, including
    # the ones that fall back to the "no preview" notice.
    html = question_case("question_block_with_comment")
    assert html.index("</div>") < html.index("edsl-comment-field")
    assert 'class="edsl-comment-field mt-4"' in html


def test_comment_box_binds_to_the_questions_comment_field():
    html = question_case("question_block_with_comment")
    assert 'name="pref.comment"' in html
    assert 'id="pref-comment"' in html and 'for="pref-comment"' in html


def test_comment_label_is_escaped():
    # The label is author-supplied text, so it goes through the same escaping
    # as question text. This case's label carries an apostrophe.
    html = question_case("question_block_with_comment")
    assert "you&#x27;d like" in html
    assert "you'd like" not in html


def test_no_comment_configured_renders_nothing():
    question = CASES["multiple_choice_radio"]["question"]
    assert render_comment(question, None) == ""
    assert render_comment(question, {}) == ""
    assert render_comment(question, {"comment": None}) == ""


def test_an_empty_comment_config_still_renders_a_box():
    # absent/null mean "no comment"; an empty config means "a comment, with no
    # label", and the live page draws the same distinction.
    html = render_comment(CASES["multiple_choice_radio"]["question"], {"comment": {}})
    assert "edsl-comment-field" in html
    assert "<label" in html and "></label>" in html


def test_comment_applies_to_an_unsupported_question_type():
    # The box is composed outside the question renderers, so a type with no
    # preview still shows its comment box rather than losing it.
    html = render_question_with_comment(
        {"question_type": "rank", "question_name": "r", "question_text": "Rank these."},
        {"comment": {"label": "Anything else?"}},
    )
    assert "No preview is available" in html
    assert 'name="r.comment"' in html


def test_markup_is_not_injectable():
    html = question_case("multiple_choice_escaped")
    assert "<script>" not in html
    assert "<b>bye</b>" not in html


def test_piped_options_get_explanatory_message():
    html = render_question(
        {
            "question_name": "q",
            "question_type": "multiple_choice",
            "question_text": "Pick one",
            "question_options": "{{ scenario.choices }}",
        }
    )
    assert "will be shown as a separate option" in html


# --------------------------------------------------------------------------
# Fallback
# --------------------------------------------------------------------------


def test_unregistered_type_falls_back_to_notice():
    # rank is a type a human survey can be configured for, so the survey is fine
    # and only this package is behind: a note, not a warning.
    assert get_renderer("rank") is unsupported.render
    html = render_question(
        {"question_type": "rank", "question_name": "r", "question_text": "Rank these."}
    )
    assert "No preview is available" in html
    assert "<code>rank</code>" in html
    assert "Not supported in human surveys" not in html
    # The question text survives the fallback; only the control is missing.
    assert "Rank these." in html


def test_a_type_no_human_survey_can_run_is_warned_about_instead():
    # dict has no humanize configuration, so no preview could exist and the
    # survey itself is what needs changing. That has to read differently from a
    # type this package simply has not got to yet.
    assert "dict" not in unsupported.HUMANIZED_TYPES
    html = render_question(
        {
            "question_type": "dict",
            "question_name": "d",
            "question_text": "Break it down.",
        }
    )
    assert "Not supported in human surveys" in html
    assert "No preview is available" not in html
    assert "<code>dict</code>" in html
    # Still the louder of the two: solid amber rather than a dashed grey note.
    assert "border-amber-300" in html and "border-dashed" not in html
    assert "lucide-triangle-alert" in html
    # ...and the question text is still there, so the page says which question
    # is the problem.
    assert "Break it down." in html


def test_nothing_is_previewed_that_a_human_survey_cannot_run():
    # The two sets are about different things -- what this package draws, and
    # what a human survey can put to a respondent -- but one contains the other.
    # A renderer for a type outside it would be previewing something that can
    # never be taken.
    assert set(RENDERERS) <= unsupported.HUMANIZED_TYPES


def test_background_types_hide_their_question_text():
    # An interview's question_text is interviewer instruction, and compute /
    # image_generation never reach the respondent at all, so showing their text
    # would misrepresent what the survey displays.
    for question_type in sorted(unsupported.HIDDEN_TEXT_TYPES):
        html = render_question(
            {
                "question_type": question_type,
                "question_name": "q",
                "question_text": "INTERNAL PROMPT TEXT",
            }
        )
        assert "INTERNAL PROMPT TEXT" not in html, question_type
        assert "No preview is available" in html, question_type


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

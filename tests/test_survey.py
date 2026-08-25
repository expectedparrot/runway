"""Survey-level tests: bundling, splitting, and the mix of supported and
unsupported question types.

Uses examples/mixed_survey.json, which carries one of everything this package
can be asked for: the question types it draws, a type it does not draw yet
(``rank``), and a type no human survey can put to a respondent at all
(``dict``) -- so both fallback paths are exercised end to end alongside the
real ones.

Runs under pytest, or directly:
    python tests/test_survey.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import goldens
from runway.renderer import render_body, render_bundle
from runway.survey import load, render_survey

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "mixed_survey.json"

# Emitted once per inlined copy of the stylesheet.
STYLESHEET_MARKER = "tailwindcss v"


def _load() -> tuple[list[dict], dict]:
    return load(EXAMPLE)


def _write(**kwargs) -> list[tuple[Path, str]]:
    questions, humanize_schema = _load()
    with tempfile.TemporaryDirectory() as tmp:
        paths = render_survey(questions, humanize_schema, out_dir=Path(tmp), **kwargs)
        return [(p, p.read_text(encoding="utf-8")) for p in paths]


def _bundle() -> str:
    questions, humanize_schema = _load()
    return render_bundle(questions, humanize_schema)


def _split_page(question_name: str) -> str:
    """One split page, looked up by question name rather than position, so
    adding a question to the example does not renumber every assertion."""
    for path, html in _write(split=True):
        if path.stem.endswith(question_name):
            return html
    raise AssertionError(f"no page written for {question_name}")


# --------------------------------------------------------------------------
# The page shell around a question
# --------------------------------------------------------------------------


def test_shell_around_a_question_matches_react():
    """The layout container the survey page sits in, byte for byte.

    Its class list is not the concatenation of its two sources -- the reference
    implementation merges them through clsx + tailwind-merge, which drops pb-16
    for the later pb-8 and de-duplicates `flex flex-col` -- so this is recorded
    from the component rather than assembled by hand.
    """
    cases, recorded = goldens.load_cases(), goldens.load_goldens()
    # The shell is recorded around a marker; what goes inside it is a question,
    # covered by its own cases.
    before, after = recorded["survey_shell"].split(goldens.CONTENT_MARKER)
    body = render_body(cases["multiple_choice_radio"]["question"])
    assert body.startswith(before)
    assert body.endswith(after)


# --------------------------------------------------------------------------
# Bundling (the default)
# --------------------------------------------------------------------------


def test_bundle_is_a_single_index_file():
    written = _write()
    assert [p.name for p, _ in written] == ["index.html"]


def test_a_named_survey_is_written_under_its_own_name():
    # What lets several surveys share an output directory: the CLI passes the
    # survey file's name, so rendering a second one does not overwrite the
    # first.
    written = _write(name="mixed_survey")
    assert [p.name for p, _ in written] == ["mixed_survey.html"]


def test_bundle_inlines_the_stylesheet_only_once():
    # The whole point of bundling: N questions, one copy of the stylesheet.
    assert _bundle().count(STYLESHEET_MARKER) == 1


def test_bundle_holds_every_question():
    html = _bundle()
    assert 'data-question-name="commute_mode"' in html
    assert 'data-question-name="commute_breakdown"' in html
    assert "How do you usually get to work?" in html
    assert "commuting break down?" in html


def test_bundle_shows_exactly_one_panel_without_javascript():
    html = _bundle()
    assert html.count('class="preview-panel is-active"') == 1
    # ...and it is the first, so a no-JS viewer lands on question 1.
    first = html.index('data-question-name="commute_mode"')
    second = html.index('data-question-name="commute_breakdown"')
    assert first < second
    assert html.index('class="preview-panel is-active"') < second


def test_bundle_has_a_toolbar_entry_per_question():
    html = _bundle()
    assert '<option value="0">1. commute_mode — Multiple Choice</option>' in html
    assert '<option value="1">2. commute_time — Multiple Choice</option>' in html
    assert '<option value="2">3. commute_enjoyment — Likert Five</option>' in html
    assert '<option value="3">4. commute_satisfaction — Linear Scale</option>' in html
    assert '<option value="4">5. commute_switch — Yes/No</option>' in html
    assert '<option value="5">6. commute_barriers — Rank</option>' in html
    assert '<option value="6">7. commute_breakdown — Dict</option>' in html
    assert 'id="preview-prev"' in html and 'id="preview-next"' in html
    assert html.count('id="preview-counter"') == 1
    assert ">1 / 7<" in html


def test_bundle_keeps_each_questions_own_progress():
    html = _bundle()
    # Seven questions, so each panel's bar reads the share behind it: 0, 1/7,
    # 2/7 and so on, rounded to whole percents the way the live page rounds
    # them -- which is not Python's rounding, hence 29 rather than 28.
    for percent in (0, 14, 29, 43, 57, 71, 86):
        assert f'aria-valuenow="{percent}" aria-valuetext="{percent}%"' in html


def test_bundle_applies_the_surveys_progress_configuration():
    # The indicator is a survey-level setting, so it has to reach every panel.
    questions, _ = _load()
    html = render_bundle(questions, {"survey": {"progress": {"type": "hidden"}}})
    # Matched on the attribute, not the bare name: the inlined stylesheet
    # carries rules for these hooks whether or not the page uses them.
    assert 'class="edsl-progress' not in html
    # ...and the questions are still there: hiding the indicator is not hiding
    # the survey.
    assert html.count('class="edsl-question ') == 7


def test_bundle_draws_a_stepped_indicator_when_one_is_configured():
    questions, _ = _load()
    html = render_bundle(
        questions,
        {
            "survey": {
                "progress": {
                    "type": "steps",
                    "marker": "dot",
                    "steps": [
                        {"label": "Your commute", "complete_after": "commute_time"},
                        {"label": "Details", "complete_after": None},
                    ],
                }
            }
        },
    )
    assert 'class="edsl-progress edsl-progress-steps' in html
    assert 'class="edsl-progress edsl-progress-bar' not in html
    # One panel per question, each with its own reading of the same two steps:
    # the two questions up to the boundary sit on step one, the five after it
    # on step two.
    assert html.count("edsl-progress-step-current") == 7
    assert html.count("Step 1 of 2: Your commute, current step") == 2
    assert html.count("Step 2 of 2: Details, current step") == 5


def test_bundle_applies_per_question_humanize_schema():
    # commute_time is configured as a dropdown and commute_mode is not, so the
    # bundle has to route each question's schema to its own panel rather than
    # applying one setting to all of them.
    html = _bundle()
    assert '<select name="commute_time" class="edsl-select' in html
    assert '<select name="commute_mode"' not in html
    # The radio question keeps its radios; the dropdown question has none.
    assert 'value="Drive alone"/>' in html
    assert 'name="commute_time" class="edsl-radio' not in html


def test_comment_box_goes_only_to_the_question_that_configured_one():
    # commute_mode configures a comment and the other two do not, so the bundle
    # has to keep the box with its own question rather than adding it to each.
    html = _bundle()
    assert html.count('class="edsl-comment-field mt-4"') == 1
    assert 'name="commute_mode.comment"' in html
    assert "Anything you&#x27;d add about how you get there?" in html


def test_dropdown_question_lists_all_its_options():
    html = _bundle()
    for option in ("Under 10 minutes", "Over an hour", "It varies too much to say"):
        assert f">{option}</option>" in html
    # The placeholder carries selected="" because nothing is answered yet --
    # React marks the option matching the select's value. See react_goldens.
    assert '<option value="" selected="">Select...</option>' in html


def test_survey_custom_css_is_emitted_after_the_stylesheet():
    # The survey author's own stylesheet, applied as the live page applies it:
    # unescaped, and last, so it wins over the classes it is overriding.
    questions, _ = _load()
    css = ".edsl-question-text { font-size: 1.4rem; content: '>' }"
    html = render_bundle(questions, {"survey": {"custom_css": css}})
    assert f"<style>{css}</style>" in html
    assert html.index(STYLESHEET_MARKER) < html.index(css)


def test_toolbar_layout_is_reasserted_after_custom_css():
    # A survey stylesheet is previewed as-is, but must not be able to hide the
    # only means of navigating the preview.
    questions, _ = _load()
    html = render_bundle(
        questions,
        {"survey": {"custom_css": ".preview-toolbar { display: none }"}},
    )
    guard = html.index(".preview-toolbar{position:fixed")
    assert html.index(".preview-toolbar { display: none }") < guard


def test_single_question_bundle_has_no_toolbar():
    html = render_bundle([_load()[0][0]], {})
    assert "preview-toolbar" not in html
    assert "preview-panel" in html


# --------------------------------------------------------------------------
# Splitting
# --------------------------------------------------------------------------


def test_split_writes_one_page_per_question_in_order():
    written = _write(split=True)
    assert [p.name for p, _ in written] == [
        "01-commute_mode.html",
        "02-commute_time.html",
        "03-commute_enjoyment.html",
        "04-commute_satisfaction.html",
        "05-commute_switch.html",
        "06-commute_barriers.html",
        "07-commute_breakdown.html",
    ]


def test_split_pages_carry_the_survey_name_when_one_is_given():
    written = _write(split=True, name="mixed_survey")
    assert [p.name for p, _ in written][:2] == [
        "mixed_survey-01-commute_mode.html",
        "mixed_survey-02-commute_time.html",
    ]


def test_split_pages_are_complete_standalone_documents():
    for path, html in _write(split=True):
        assert html.startswith("<!doctype html>"), path.name
        assert html.rstrip().endswith("</html>"), path.name
        assert html.count(STYLESHEET_MARKER) == 1, path.name
        # No preview chrome on a single-question page.
        assert "preview-toolbar" not in html, path.name


def test_split_progress_advances_across_pages():
    pages = [html for _, html in _write(split=True)]
    for html, percent in zip(pages, (0, 14, 29, 43, 57, 71, 86), strict=True):
        assert f'aria-valuenow="{percent}"' in html
        assert f">{percent}%</span>" in html


# --------------------------------------------------------------------------
# Question content, independent of layout
# --------------------------------------------------------------------------


def test_supported_question_renders_its_control():
    html = _split_page("commute_mode")
    assert 'class="edsl-question edsl-multiple-choice-question mb-6"' in html
    assert html.count('type="radio"') == 5
    assert 'value="Public transit"' in html
    assert "No preview is available" not in html


def test_dropdown_question_renders_a_select_not_radios():
    html = _split_page("commute_time")
    assert '<select name="commute_time" class="edsl-select' in html
    assert 'type="radio"' not in html
    # Seven options plus the empty "Select..." placeholder.
    assert html.count("<option ") == 8


def test_the_rest_of_the_choice_family_renders_its_own_controls():
    # All three share multiple choice's template, so what a survey-level test
    # can add is that the type reaches the right wrapper through the registry
    # rather than falling back to the notice.
    likert = _split_page("commute_enjoyment")
    assert 'class="edsl-question edsl-likert-question mb-6"' in likert
    assert likert.count('type="radio"') == 5
    assert 'value="Strongly agree"' in likert

    yes_no = _split_page("commute_switch")
    assert 'class="edsl-question edsl-yes-no-question mb-6"' in yes_no
    assert yes_no.count('type="radio"') == 2

    scale = _split_page("commute_satisfaction")
    assert 'class="edsl-question edsl-linear-scale-question mb-6"' in scale
    assert scale.count('type="radio"') == 5
    # The scale answers with its number and shows its label.
    assert 'value="5"/>' in scale
    assert ">5 - Couldn&#x27;t be better</span>" in scale

    assert "No preview is available" not in likert + yes_no + scale


def test_a_type_awaiting_a_preview_renders_the_notice():
    # rank is a question a human survey can be configured for; this package has
    # just not transcribed its control yet.
    html = _split_page("commute_barriers")
    assert "No preview is available" in html
    assert "<code>rank</code>" in html
    assert "Not supported in human surveys" not in html
    # The fallback still gets the full page shell, not a bare fragment.
    assert "edsl-survey-container" in html
    assert 'type="submit">Next</button>' in html
    # ...but none of the multiple choice control.
    assert 'type="radio"' not in html


def test_a_type_no_human_survey_can_run_renders_the_warning():
    # dict has no humanize configuration at all, so the survey itself is what
    # needs changing -- a different message, and a louder one.
    html = _split_page("commute_breakdown")
    assert "Not supported in human surveys" in html
    assert "No preview is available" not in html
    assert "<code>dict</code>" in html
    assert "edsl-survey-container" in html


def test_unsupported_question_still_shows_its_question_text():
    # Without this the page cannot be told apart from any other unsupported
    # question, and the author cannot check their own wording.
    html = _split_page("commute_breakdown")
    assert "Roughly how does a typical week&#x27;s commuting break down?" in html
    assert 'class="edsl-question-text text-xl mb-3 whitespace-pre-wrap"' in html


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

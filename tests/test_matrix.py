"""Parity tests for the matrix renderer.

A matrix is the first type here that is not a list of options, and the first
whose reference implementation renders *two* layouts at once: a table above the
``md`` breakpoint and a stacked list of one-question-per-row below it. Both are
mounted and CSS picks one, so both are transcribed -- a preview that emitted
only the table would be a different page from the one served, and would lose the
property that turning a phone mid-question keeps the answer.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and SPEC.md under "The goldens".

One layout is deliberately *not* drawn: the carousel a humanize schema can ask
for. Rather than showing the default views for a question configured that way,
the renderer declines and the stand-in note is rendered -- and ``check`` says the
same thing, which is the property ``test_a_carousel_is_declined_by_both_halves``
holds.

Runs under pytest, or directly: python tests/test_matrix.py
"""

from __future__ import annotations

import re
from pathlib import Path

import goldens
from runway import inspection, render_question
from runway import renderer as runway_renderer
from runway.question_types import RENDERERS, matrix

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

CAROUSEL = {"format": {"type": "carousel"}}


def question_case(name: str) -> str:
    case = CASES[name]
    return render_question(case["question"], case["humanize_schema"])


def a_matrix(**overrides) -> dict:
    question = {
        "question_name": "visit",
        "question_type": "matrix",
        "question_text": "Rate each part of your visit.",
        "question_items": ["The food", "Value for money"],
        "question_options": ["Poor", "Good"],
    }
    question.update(overrides)
    return question


# --------------------------------------------------------------------------
# Parity
# --------------------------------------------------------------------------


def test_matrix_grid_matches_react():
    assert question_case("matrix_grid") == GOLDENS["matrix_grid"]


def test_matrix_labelled_matches_react():
    assert question_case("matrix_labelled") == GOLDENS["matrix_labelled"]


def test_matrix_is_registered_as_drawn():
    """The registry is what ``types`` and ``check`` read."""
    assert RENDERERS["matrix"] is matrix.render


# --------------------------------------------------------------------------
# Both views, and why they are held apart
# --------------------------------------------------------------------------


def test_both_views_are_emitted():
    """The reference mounts both and lets the breakpoint choose.

    Emitting one would be a smaller page and the wrong one: it is not the
    server that decides which layout a respondent gets.
    """
    html = render_question(a_matrix())
    assert 'class="edsl-matrix-stack-view md:hidden"' in html
    assert 'class="edsl-matrix-table-view hidden md:block"' in html


def test_the_two_views_never_share_a_radio_name():
    """The property the ``_stack`` scoping exists for.

    One name is one radio group. If both views named a row's group the same,
    the hidden view's radio would uncheck the visible one, and a respondent
    would lose an answer by rotating their phone.
    """
    html = render_question(a_matrix())
    names = set(re.findall(r'<input [^>]*name="([^"]+)"', html))
    stacked = {name for name in names if "_stack_" in name}
    assert stacked and stacked != names
    # Strip the scope and the two views ask for the same rows -- they answer the
    # same question, so anything else would mean they had drifted apart.
    assert {name.replace("_stack", "") for name in stacked} == names - stacked


def test_ids_are_built_from_indices_not_from_row_text():
    """A row piped from a file reads ``<see file dog>``, and an id may not
    contain whitespace -- so neither half of the grid may be spelled into one."""
    html = render_question(
        a_matrix(question_items=["The staff's attention", "Value for money"])
    )
    for identifier in re.findall(r'id="([^"]+)"', html):
        assert " " not in identifier and "'" not in identifier
    assert 'id="visit_0_0"' in html
    assert 'id="visit_stack_0_label"' in html


def test_an_apostrophe_is_escaped_the_way_react_escapes_it():
    """``&#x27;``, not MarkupSafe's ``&#39;`` -- on both axes."""
    html = render_question(
        a_matrix(
            question_items=["The staff's attention"],
            question_options=["Couldn't say"],
        )
    )
    assert "&#39;" not in html
    assert html.count("&#x27;") >= 2


# --------------------------------------------------------------------------
# Option labels: the two views spend them differently
# --------------------------------------------------------------------------


def test_a_label_is_stacked_in_the_grid_and_folded_into_the_list():
    """The one place the two views deliberately differ.

    A column heading has no width to spare, so the grid stacks the author's word
    above the number; a full-width row has nothing to save, so the stacked list
    writes ``1 - Strongly disagree`` the way a linear scale does.
    """
    html = render_question(
        a_matrix(
            question_options=[1, 5],
            option_labels={"1": "Strongly disagree", "5": "Strongly agree"},
        )
    )
    stack, table = html.split('<div class="edsl-matrix-table-view')
    assert "<span>1 - Strongly disagree</span>" in stack
    assert '<span class="break-words text-center">Strongly disagree</span>' in table
    # Each spelling belongs to one view. A heading that folded the label in, or
    # a list row that stacked it, would mean the two had stopped differing on
    # purpose and started differing by accident.
    assert "1 - Strongly disagree" not in table
    assert "break-words" not in stack


def test_an_unlabelled_column_shows_its_own_text_in_both_views():
    html = render_question(
        a_matrix(question_options=[1, 5], option_labels={"1": "Strongly disagree"})
    )
    assert "break-words" in html  # the labelled one
    assert html.count(">5<") >= 2  # the unlabelled one, in each view


def test_labels_are_found_however_their_keys_arrived():
    """Integer keys from a live question, string keys from JSON: the reference
    looks both up as property names, so both must resolve here."""
    integer_keys = render_question(a_matrix(question_options=[1], option_labels={1: "Low"}))
    string_keys = render_question(a_matrix(question_options=[1], option_labels={"1": "Low"}))
    assert integer_keys == string_keys
    assert "1 - Low" in integer_keys


def test_whole_numbers_written_as_floats_keep_javascripts_spelling():
    """``1.0`` reads as ``1`` over there, because JavaScript has one number
    type. Spelling it ``1.0`` would put every value and label off by a suffix."""
    html = render_question(a_matrix(question_options=[1.0, 2.0]))
    assert 'value="1"' in html and 'value="1.0"' not in html


# --------------------------------------------------------------------------
# The table's own shape
# --------------------------------------------------------------------------


def test_the_option_count_is_handed_to_the_table():
    """The one part of the grid a stylesheet cannot know.

    Both column widths come off this property, so custom CSS rebalances a grid
    by setting it and nothing else.
    """
    html = render_question(a_matrix(question_options=["a", "b", "c"]))
    assert "--edsl-matrix-option-count:3" in html


def test_a_column_is_declared_for_the_labels_and_one_per_option():
    html = render_question(a_matrix(question_options=["a", "b", "c"]))
    colgroup = html[html.index("<colgroup>") : html.index("</colgroup>")]
    # On the class, not on bare text: the option columns name the label column
    # too, since their width is what is left after it.
    assert colgroup.count('class="edsl-matrix-item-column') == 1
    assert colgroup.count('class="edsl-matrix-option-column') == 3


def test_the_label_column_has_no_heading():
    """Empty in the reference too: the space is what lets the option headings
    sit over their own columns."""
    html = render_question(a_matrix())
    header = html[html.index("edsl-matrix-header-row") :]
    assert 'dark:bg-gray-900"></th>' in header


# --------------------------------------------------------------------------
# The carousel, which is not drawn yet
# --------------------------------------------------------------------------


def test_a_carousel_matrix_is_declined_with_a_reason():
    assert matrix.declines(a_matrix(), CAROUSEL) == "the carousel format is not drawn yet"
    assert matrix.declines(a_matrix(), None) is None
    assert matrix.declines(a_matrix(), {"format": {"type": "dropdown"}}) is None


def test_a_carousel_is_declined_by_both_halves():
    """The property that keeps ``check`` from lying.

    Whatever the renderer does with a carousel-formatted matrix, the classifier
    must say the same -- a report promising a grid for a page that shows a note
    is worse than no report.
    """
    question = a_matrix()
    html = render_question(question, CAROUSEL)
    assert "edsl-preview-note" in html
    assert "edsl-matrix-table" not in html
    assert inspection.classify(question, CAROUSEL) == "note"
    assert inspection.classify(question, None) == "drawn"


def test_the_reason_reaches_the_report():
    entry = inspection.describe(a_matrix(), 1, CAROUSEL)
    assert entry["reason"] == "the carousel format is not drawn yet"
    # An ordinary matrix has nothing to explain away.
    assert "reason" not in inspection.describe(a_matrix(), 1, None)


# --------------------------------------------------------------------------
# Piping
# --------------------------------------------------------------------------


def test_a_piped_axis_gets_an_explanatory_row():
    """Rows and columns can both be piped, and neither can be enumerated
    outside a live run. The reference is handed a resolved grid by the server
    and would not survive being handed the template instead."""
    for key in ("question_items", "question_options"):
        html = render_question(a_matrix(**{key: "{{ scenario.rows }}"}))
        # The unresolved text is shown rather than hidden: it says what will be
        # there, and it points at the reference that has yet to resolve.
        assert "{{ scenario.rows }}" in html
        assert "In a live survey" in html
        assert "edsl-matrix-table" in html


def test_a_matrix_with_no_rows_still_renders_a_page():
    """Not a question, but a shape the server can send, and it must not take
    the page down with it."""
    html = render_question(a_matrix(question_items=[]))
    assert "edsl-matrix-table" in html
    assert "<tbody></tbody>" in html


# --------------------------------------------------------------------------
# The one hand-written stylesheet rule
# --------------------------------------------------------------------------
#
# Everything else in questions.css is generated from classes a component emits,
# so the parity tests cover it. This rule is authored, and its whole design is
# about how it loses -- to a survey's own CSS -- and how it wins -- over the
# utility it replaces. Neither is visible from the markup, so it is asserted
# here or nowhere.

STYLESHEET = (Path(runway_renderer.__file__).parent / "assets/questions.css").read_text(
    encoding="utf-8"
)
SELECTED_RULE = ":where(.edsl-matrix-stack) .edsl-option:where(:has(:checked)){"


def _without_where(selector: str) -> str:
    """Drop every ``:where(...)`` and its contents, nesting included.

    A regex cannot: ``:where(:has(:checked))`` nests, and one that stopped at
    the first closing paren would leave the second behind and quietly report
    the wrong weight.
    """
    out, index = [], 0
    while index < len(selector):
        if selector.startswith(":where(", index):
            depth, index = 1, index + len(":where(")
            while depth:
                depth += {"(": 1, ")": -1}.get(selector[index], 0)
                index += 1
            continue
        out.append(selector[index])
        index += 1
    return "".join(out)


def test_the_selected_state_rule_ships():
    assert SELECTED_RULE in STYLESHEET


def test_the_selected_rule_carries_one_class_of_weight():
    """`:where()` is load-bearing, not decoration.

    At one class this ties with the utility it overrides and wins on order --
    which is the cascade the live page has, where the selected classes simply
    replace the unselected ones. Spelled as a plain descendant selector it would
    be three classes and would outrank a survey's own `.edsl-option` rule, where
    the live page's styling never does.
    """
    # Everything outside :where() is what counts, and it is one class.
    assert _without_where(SELECTED_RULE.rstrip("{")).strip() == ".edsl-option"


def test_the_selected_rule_is_emitted_after_what_it_overrides():
    """Winning on order only works if the order is that way round."""
    at = STYLESHEET.index(SELECTED_RULE)
    for utility in (".border-gray-200{", ".bg-blue-50{"):
        assert STYLESHEET.index(utility) < at, utility


def test_the_selected_rule_is_scoped_to_the_stacked_list():
    """The choice family's options carry `.edsl-option` too and have no selected
    styling at all in the reference -- their radio alone shows the answer. An
    unscoped rule would draw a highlight the live survey never draws."""
    assert SELECTED_RULE.startswith(":where(.edsl-matrix-stack) ")
    choice = render_question(
        {
            "question_name": "q",
            "question_type": "multiple_choice",
            "question_text": "T",
            "question_options": ["a", "b"],
        }
    )
    assert "edsl-option" in choice and "edsl-matrix-stack" not in choice


def test_a_surveys_own_css_is_still_emitted_last():
    """What lets a matched-weight rule be overridden at all."""
    page = runway_renderer.render_page(
        a_matrix(), custom_css=".edsl-option{background:red}"
    )
    assert page.index(SELECTED_RULE) < page.index(".edsl-option{background:red}")


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

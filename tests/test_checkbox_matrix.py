"""Parity tests for the checkbox matrix renderer.

A checkbox matrix is matrix's default pair -- a table above ``md``, a stacked
list below it -- with a checkbox in every cell, so each row can check any
number of options. The rows and columns are prepared by matrix's own functions;
what these tests hold is what the type changes, and what it must not.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and SPEC.md under "The goldens".

Runs under pytest, or directly: python tests/test_checkbox_matrix.py
"""

from __future__ import annotations

import re

import goldens
from runway import inspection, render_question
from runway.question_types import RENDERERS, checkbox_matrix, unsupported

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()


def question_case(name: str) -> str:
    case = CASES[name]
    return render_question(case["question"], case["humanize_schema"])


def a_checkbox_matrix(**overrides) -> dict:
    question = {
        "question_name": "activities",
        "question_type": "checkbox_matrix",
        "question_text": "Which do you do on each day?",
        "question_items": ["Monday", "Saturday"],
        "question_options": ["Exercise", "Read"],
        "min_selections": 0,
        "max_selections": 2,
    }
    question.update(overrides)
    return question


# --------------------------------------------------------------------------
# Parity
# --------------------------------------------------------------------------


def test_checkbox_matrix_grid_matches_react():
    assert question_case("checkbox_matrix_grid") == GOLDENS["checkbox_matrix_grid"]


def test_checkbox_matrix_labelled_matches_react():
    assert (
        question_case("checkbox_matrix_labelled")
        == GOLDENS["checkbox_matrix_labelled"]
    )


def test_checkbox_matrix_item_blocks_matches_react():
    assert (
        question_case("checkbox_matrix_item_blocks")
        == GOLDENS["checkbox_matrix_item_blocks"]
    )


def test_checkbox_matrix_is_registered_as_drawn():
    """The registry is what ``types`` and ``check`` read."""
    assert RENDERERS["checkbox_matrix"] is checkbox_matrix.render
    assert "checkbox_matrix" in unsupported.HUMANIZED_TYPES


# --------------------------------------------------------------------------
# What the type changes
# --------------------------------------------------------------------------


def test_every_cell_is_a_checkbox_in_both_views():
    """Two rows by two options, in each of the two views: eight checkboxes and
    not one radio."""
    html = render_question(a_checkbox_matrix())
    assert html.count('type="checkbox"') == 8
    assert 'type="radio"' not in html


def test_a_stacked_row_is_a_group_not_a_radiogroup():
    html = render_question(a_checkbox_matrix())
    assert html.count('role="group"') == 2
    assert "radiogroup" not in html


def test_each_part_carries_both_names():
    """A survey's matrix CSS reaches this grid, and the second name styles it
    alone."""
    html = render_question(a_checkbox_matrix())
    for part in (
        "views",
        "stack-view",
        "stack",
        "stack-row",
        "stack-item",
        "table-view",
        "table",
        "item-column",
        "option-column",
        "header-row",
        "row",
        "label-cell",
        "cell",
    ):
        assert re.search(
            rf'class="edsl-matrix-{part} edsl-checkbox-matrix-{part}[ "]', html
        ), part
    assert 'class="edsl-question edsl-checkbox-matrix-question mb-6"' in html
    assert "edsl-matrix-question" not in html


def test_the_two_views_never_share_a_group_name():
    """As in a matrix: the stacked list scopes its names under ``_stack``, so
    the hidden view's boxes are never the same field as the visible ones."""
    html = render_question(a_checkbox_matrix())
    names = re.findall(r'name="([^"]+)"', html)
    assert sorted(set(names)) == [
        "activities_0",
        "activities_1",
        "activities_stack_0",
        "activities_stack_1",
    ]


def test_a_box_carries_its_option_as_its_value():
    html = render_question(a_checkbox_matrix(question_options=[1, 2]))
    assert 'value="1"' in html and 'value="2"' in html


def test_the_halo_is_square():
    html = render_question(a_checkbox_matrix())
    assert "inline-flex rounded-[3px] group-hover/bubble" in html
    assert "rounded-full" not in html


def test_a_carousel_format_is_not_read():
    """The reference has no carousel for this type, and the schema has no
    format to ask for one; a stray one draws the default pair regardless."""
    question = a_checkbox_matrix()
    assert render_question(question, {"format": {"type": "carousel"}}) == (
        render_question(question)
    )


def test_a_plain_checkbox_still_has_no_name_or_value():
    """The checkbox include gained a name and a value for this type only."""
    html = render_question(
        {
            "question_name": "pets",
            "question_type": "checkbox",
            "question_text": "Which pets?",
            "question_options": ["Cat", "Dog"],
        }
    )
    assert 'type="checkbox"' in html
    assert "name=" not in html.split('type="checkbox"', 1)[1].split("/>", 1)[0]


def test_a_piped_axis_gets_an_explanatory_row():
    html = render_question(a_checkbox_matrix(question_items="{{ scenario.rows }}"))
    assert "{{ scenario.rows }}" in html
    assert "In a live survey" in html


def test_it_is_reported_as_drawn():
    """What ``check`` reports: drawn, with no reason to give."""
    question = a_checkbox_matrix()
    assert inspection.classify(question) == "drawn"
    assert "reason" not in inspection.describe(question, 1)


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

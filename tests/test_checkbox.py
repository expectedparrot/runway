"""Parity tests for the checkbox renderer.

Two things here are invisible from the question dict, and both are what these
tests are for.

The **Select all** row is drawn by the wrapper the survey page mounts, whose
default is the opposite of the presentational component's — so it belongs on the
page even though nothing in the question asks for it. Recording the
presentational component would have dropped it from every golden while still
looking correct, which is why the cases render the wrapper.

**Exclusive options** are the only way a humanize schema changes this markup. An
option that clears the rest when ticked is not part of "all", so it does not
count towards the "more than one selectable option" that earns the row.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and the README under "The goldens".

Runs under pytest, or directly: python tests/test_checkbox.py
"""

from __future__ import annotations

import goldens
from runway import render_question, renderer
from runway.question_types import RENDERERS, checkbox

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

SELECT_ALL = "edsl-select-all"


def question_case(name: str) -> str:
    case = CASES[name]
    return render_question(case["question"], case["humanize_schema"])


def a_checkbox(**overrides) -> dict:
    question = {
        "question_name": "courses",
        "question_type": "checkbox",
        "question_text": "Which did you order?",
        "question_options": ["Starters", "Dessert"],
    }
    question.update(overrides)
    return question


# --------------------------------------------------------------------------
# Parity
# --------------------------------------------------------------------------


def test_checkbox_matches_react():
    assert question_case("checkbox") == GOLDENS["checkbox"]


def test_a_single_option_matches_react():
    assert question_case("checkbox_single_option") == GOLDENS["checkbox_single_option"]


def test_an_exclusive_option_matches_react():
    name = "checkbox_exclusive_leaves_one_selectable"
    assert question_case(name) == GOLDENS[name]


def test_checkbox_is_registered_as_drawn():
    assert RENDERERS["checkbox"] is checkbox.render


# --------------------------------------------------------------------------
# Select all
# --------------------------------------------------------------------------


def test_select_all_appears_without_the_question_asking_for_it():
    """The wrapper's default is `true` and the survey page does not override it,
    so the row is on the page for every ordinary checkbox question."""
    assert SELECT_ALL in render_question(a_checkbox())


def test_one_option_earns_no_select_all():
    """Nothing to say "all" about."""
    assert SELECT_ALL not in render_question(a_checkbox(question_options=["Only this"]))


def test_no_options_earns_no_select_all():
    assert SELECT_ALL not in render_question(a_checkbox(question_options=[]))


def test_an_exclusive_option_does_not_count_towards_all():
    """The one place a humanize schema reaches this markup.

    Two options with one exclusive leaves one that "all" could mean, so the row
    goes away -- where the same question without the schema keeps it.
    """
    question = a_checkbox(question_options=["A window seat", "None of the above"])
    schema = {"exclusive_options": ["None of the above"]}
    assert SELECT_ALL in render_question(question, None)
    assert SELECT_ALL not in render_question(question, schema)


def test_exclusive_options_survive_a_schema_that_names_none():
    for schema in (None, {}, {"exclusive_options": None}, {"exclusive_options": "x"}):
        assert checkbox.exclusive_options(schema) == []
    assert checkbox.exclusive_options({"exclusive_options": ["a"]}) == ["a"]


def test_the_select_all_box_is_named_for_its_question():
    html = render_question(a_checkbox())
    assert 'id="courses-select-all"' in html
    assert 'for="courses-select-all"' in html


# --------------------------------------------------------------------------
# The options themselves
# --------------------------------------------------------------------------


def test_options_are_identified_by_index_not_by_text():
    """An option piped from a file reads `<see file dog>`, and an id may not
    contain whitespace."""
    html = render_question(a_checkbox(question_options=["A window seat", "Two seats"]))
    assert 'id="courses-0"' in html and 'id="courses-1"' in html


def test_a_checkbox_group_has_no_name_attribute():
    """It is not a radio group, and the reference gives it none. A `name` here
    would look harmless and would group boxes that must stay independent."""
    assert "name=" not in render_question(a_checkbox())


def test_an_apostrophe_is_escaped_the_way_react_escapes_it():
    html = render_question(a_checkbox(question_options=["Couldn't say", "Other"]))
    assert "&#x27;" in html and "&#39;" not in html


def test_piped_options_get_the_explanatory_message():
    """The same line the choice family substitutes, so a piped question previews
    the same way whichever control it wears."""
    html = render_question(a_checkbox(question_options="{{ scenario.items }}"))
    assert "In a live survey" in html
    # One unenumerable option is not two, so there is no "all" to offer.
    assert SELECT_ALL not in html


# --------------------------------------------------------------------------
# The two rules the markup cannot carry
# --------------------------------------------------------------------------
#
# A preview's controls already respond to a click -- a radio group settles
# because the markup names it correctly, a checkbox ticks because that is what a
# checkbox does. Select all and "None of the above" are rules rather than markup,
# so they need a script, and this is the one place in the package that
# reimplements behaviour rather than transcribing markup. Kept to those two.


def test_exclusive_options_reach_the_page_as_positions():
    """Not as option text.

    An option label on the page is rendered markdown -- `**Never**` reaches the
    DOM as `Never` -- so a script matching the schema's strings against what it
    can read there would quietly stop recognising any option an author
    emphasised. The position is the same on both sides whatever the label says.
    """
    found = renderer.exclusive_options(
        [a_checkbox(question_options=["A", "**Never**", "C"])],
        {"questions": {"courses": {"exclusive_options": ["**Never**"]}}},
    )
    assert found == {"courses": [1]}


def test_only_checkbox_questions_get_an_entry():
    """No other type has the notion, and a key per question would invite a
    script that assumed otherwise."""
    questions = [a_checkbox(), {"question_name": "other", "question_type": "yes_no"}]
    assert set(renderer.exclusive_options(questions, {})) == {"courses"}


def test_piped_options_have_nothing_to_be_exclusive_of():
    found = renderer.exclusive_options(
        [a_checkbox(question_options="{{ scenario.items }}")],
        {"questions": {"courses": {"exclusive_options": ["A"]}}},
    )
    assert found == {"courses": []}


def test_the_script_ships_only_where_there_is_a_checkbox():
    """An ordinary survey carries no script it has no use for."""
    with_box = renderer.render_page(a_checkbox())
    without = renderer.render_page(
        {
            "question_name": "q",
            "question_type": "yes_no",
            "question_text": "T",
            "question_options": ["Yes", "No"],
        }
    )
    assert "var EXCLUSIVE" in with_box
    assert "var EXCLUSIVE" not in without


def test_the_script_reaches_a_split_page_too():
    """A single question is still a clickable page; the behaviour is not a
    property of being in a bundle."""
    assert "var EXCLUSIVE" in renderer.render_page(a_checkbox())


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

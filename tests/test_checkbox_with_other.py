"""Parity tests for the checkbox-with-other renderer.

The type is a checkbox question plus a row the respondent types into, and three
things about it are not guessable from the question dict — which is what most of
these tests are for.

**No Select all.** The wrapper the survey page mounts defaults `showSelectAll` to
*false* here and *true* on the plain checkbox's wrapper. Reasoning by analogy
from checkbox would put a row on the page that the live survey never draws, so
it is recorded rather than assumed.

**`exclusive_options` therefore changes nothing.** Its only effect on plain
checkbox markup is to take the Select all row away, and there is no row here. A
second recorded case holds the two to being byte-identical.

**One empty row, and no "Add another".** The question opens with a single blank
answer whose remove button is rendered but `invisible`, and the add button is
held back until something is typed — so an unanswered page, which is what a
preview shows, has neither an extra row nor a button.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and SPEC.md under "The goldens".

Runs under pytest, or directly: python tests/test_checkbox_with_other.py
"""

from __future__ import annotations

import re

import goldens
from runway import render_question, renderer
from runway.question_types import RENDERERS, checkbox_with_other

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()


def question_case(name: str) -> str:
    case = CASES[name]
    return render_question(case["question"], case["humanize_schema"])


def a_question(**overrides) -> dict:
    question = {
        "question_name": "allergies",
        "question_type": "checkbox_with_other",
        "question_text": "Any dietary requirements?",
        "question_options": ["Vegetarian", "Vegan"],
        "other_option_text": "Other",
    }
    question.update(overrides)
    return question


# --------------------------------------------------------------------------
# Parity
# --------------------------------------------------------------------------


def test_checkbox_with_other_matches_react():
    assert question_case("checkbox_with_other") == GOLDENS["checkbox_with_other"]


def test_an_exclusive_schema_matches_react():
    name = "checkbox_with_other_exclusive"
    assert question_case(name) == GOLDENS[name]


def test_it_is_registered_as_drawn():
    assert RENDERERS["checkbox_with_other"] is checkbox_with_other.render


# --------------------------------------------------------------------------
# The asymmetry with plain checkbox
# --------------------------------------------------------------------------


def test_there_is_no_select_all_row():
    """The wrapper's default is the opposite of the plain checkbox's, and the
    survey page overrides neither. Reasoning by analogy would put a row here
    that the live survey never draws."""
    assert "edsl-select-all" not in render_question(a_question())
    # Plenty of options, which is what would earn the row on a plain checkbox.
    many = a_question(question_options=["A", "B", "C", "D"])
    assert "edsl-select-all" not in render_question(many)


def test_the_schema_changes_nothing_at_all():
    """`exclusive_options` reaches plain checkbox markup only by removing the
    Select all row. With no row to remove, it has nowhere to land."""
    question = a_question(question_options=["Vegan", "None of the above"])
    plain = render_question(question, None)
    assert render_question(question, {"exclusive_options": ["None of the above"]}) == plain


def test_exclusive_options_reach_the_behaviour_script():
    """This type has no Select all row for them to remove, but they still mean
    something to a respondent: ticking one clears the others and the answers
    typed below. That is behaviour rather than markup, so it reaches the page
    script instead of the template."""
    found = renderer.exclusive_options(
        [a_question()], {"questions": {"allergies": {"exclusive_options": ["Vegan"]}}}
    )
    assert found == {"allergies": [1]}


def test_the_answered_state_renders_from_the_same_template():
    """The markup the page script has to produce, held to the reference.

    A second row, remove buttons that are visible rather than `invisible`, and
    the "Add another" button are all absent from an unanswered question. A
    script that built them would be writing markup no test could reach -- so the
    state is recorded, rendered from this package, and compared like any other.
    """
    assert (
        goldens.render_case(CASES["checkbox_with_other_answered"])
        == GOLDENS["checkbox_with_other_answered"]
    )


def test_the_button_the_script_clones_is_the_recorded_one():
    """The invariant the whole arrangement exists for.

    The page parks an "Add another" button in a `<template>` for the script to
    clone, because the button is absent from an unanswered question and a script
    that built one would be writing markup nothing had recorded. Both come from
    `questions/_other_add.html`, so what a respondent sees after typing is the
    reference's markup byte for byte -- and this is what says so.
    """
    page = renderer.render_page(a_question())
    parked = re.search(
        r'<template id="preview-other-add">(.*?)</template>', page, re.S
    ).group(1)
    recorded = GOLDENS["checkbox_with_other_answered"]
    start = recorded.index('<div class="flex pt-1">')
    end = recorded.index("</div>", recorded.index("</button>", start)) + len("</div>")
    assert parked == recorded[start:end]


def test_the_script_ships_with_this_type_too():
    """It has no Select all row, but it has rules all the same."""
    assert "var EXCLUSIVE" in renderer.render_page(a_question())


# --------------------------------------------------------------------------
# The other block
# --------------------------------------------------------------------------


def test_the_other_row_is_a_checkbox_like_any_other():
    """So the column of boxes runs unbroken: "other" is one of the things you
    can pick, not a separate mechanism bolted below them."""
    html = render_question(a_question())
    options = html[html.index("edsl-options") : html.index("edsl-other-option")]
    assert options.count('type="checkbox"') == 2
    assert 'id="allergies-other"' in html


def test_the_other_label_is_the_authors_word():
    html = render_question(a_question(other_option_text="Something else"))
    assert ">Something else</label>" in html
    # And it names the input for a screen reader, which is the same word again.
    assert 'aria-label="Something else, answer 1"' in html


def test_a_missing_other_label_renders_empty_rather_than_none():
    """React renders `undefined` as nothing. Emitting the word "None" -- or the
    string "None" from Python -- would put a label on the page that no author
    wrote."""
    html = render_question(a_question(other_option_text=None))
    assert ">None<" not in html
    assert 'aria-label=", answer 1"' in html


def test_the_page_opens_with_exactly_one_empty_answer():
    html = render_question(a_question())
    assert html.count('class="flex items-stretch gap-1"') == 1
    assert html.count('placeholder="Enter an item"') == 1


def test_the_only_rows_remove_button_is_rendered_but_unreachable():
    """Rendered rather than omitted, so the inputs do not resize as rows come
    and go; invisible and out of the tab order, since there is nothing a
    removal could leave behind."""
    html = render_question(a_question())
    assert "edsl-other-remove" in html
    assert 'tabindex="-1"' in html
    assert "invisible" in html


def test_there_is_no_add_another_button():
    """Held back until a row holds something, and a preview shows the page
    before anyone has typed."""
    assert "edsl-other-add" not in render_question(a_question())
    assert "Add another" not in render_question(a_question())


def test_the_remove_icon_is_the_lucide_one():
    html = render_question(a_question())
    assert 'class="lucide lucide-x w-4 h-4"' in html
    assert '<path d="M18 6 6 18"></path>' in html


# --------------------------------------------------------------------------
# The options themselves
# --------------------------------------------------------------------------


def test_an_apostrophe_is_escaped_the_way_react_escapes_it():
    html = render_question(a_question(question_options=["Couldn't say", "Other"]))
    assert "&#x27;" in html and "&#39;" not in html


def test_the_other_label_is_escaped_too():
    html = render_question(a_question(other_option_text="Something I'd rather type"))
    assert "&#x27;" in html and "&#39;" not in html


def test_piped_options_get_the_explanatory_message():
    html = render_question(a_question(question_options="{{ scenario.items }}"))
    assert "In a live survey" in html
    # The other block is not an option and survives regardless.
    assert "edsl-other-option" in html


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

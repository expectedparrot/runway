"""Parity tests for the numerical range renderer.

A From field and a To field, each numerical's number input under a label. The
markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and SPEC.md under "The goldens".

Runs under pytest, or directly: python tests/test_numerical_range.py
"""

from __future__ import annotations

import goldens
from runway import inspection, render_question, render_question_with_comment
from runway.question_types import RENDERERS, numerical_range

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

QUESTION = {
    "question_name": "budget",
    "question_type": "numerical_range",
    "question_text": "What would you spend?",
}


def question_case(name: str) -> str:
    case = CASES[name]
    return render_question(case["question"], case["humanize_schema"])


# --------------------------------------------------------------------------
# Parity
# --------------------------------------------------------------------------


def test_numerical_range_matches_react():
    assert question_case("numerical_range") == GOLDENS["numerical_range"]


def test_numerical_range_bounded_matches_react():
    assert question_case("numerical_range_bounded") == GOLDENS["numerical_range_bounded"]


def test_numerical_range_is_registered_as_drawn():
    """The registry is what ``types`` and ``check`` read."""
    assert RENDERERS["numerical_range"] is numerical_range.render
    question = dict(QUESTION)
    assert inspection.classify(question) == "drawn"
    assert "reason" not in inspection.describe(question, 1)


# --------------------------------------------------------------------------
# The two fields
# --------------------------------------------------------------------------


def test_each_label_points_at_its_field():
    html = render_question(QUESTION)
    for end, label in (("min", "From"), ("max", "To")):
        assert f'<label for="budget-{end}"' in html
        assert f'<input id="budget-{end}"' in html
        assert f">{label}</label>" in html
    assert html.index("budget-min") < html.index("budget-max")


def test_the_fields_carry_no_bounds_of_their_own():
    """The reference checks the question's bounds on submit, so a bounded range
    draws what an unbounded one does. A `min` or `max` here would be validation
    this package invented."""
    bounded = {**QUESTION, "min_value": 18, "max_value": 99}
    html = render_question(bounded)
    assert html == render_question(QUESTION)
    for attribute in ('min="', 'max="'):
        assert attribute not in html
    assert html.count('step="any"') == 2


def test_both_fields_are_numericals_input_with_a_range_hook():
    """Custom CSS for a numerical's field reaches these too."""
    html = render_question(QUESTION)
    assert html.count('class="edsl-input edsl-numerical-range-input w-full ') == 2


def test_a_comment_still_attaches_to_it():
    html = render_question_with_comment(QUESTION, {"comment": {"label": "Why?"}})
    assert "edsl-numerical-range-question" in html
    assert "Why?" in html


def test_question_text_is_rendered_as_markdown():
    html = render_question({**QUESTION, "question_text": "What would you **spend**?"})
    assert "<strong>spend</strong>" in html


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

"""Parity tests for the list renderer.

A question text, a fixed "one item per line" instruction and a textarea, with
nothing that varies and no configuration the reference passes through -- the
same shape as ``free_text`` with the instruction added.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and SPEC.md under "The goldens".

Runs under pytest, or directly: python tests/test_list.py
"""

from __future__ import annotations

import goldens
from runway import render_question, render_question_with_comment
from runway.question_types import RENDERERS
from runway.question_types import list as list_type

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

QUESTION = {
    "question_name": "packing",
    "question_type": "list",
    "question_text": "What's on your packing list?",
}


def test_list_matches_react():
    case = CASES["list"]
    assert render_question(case["question"], case["humanize_schema"]) == GOLDENS["list"]


def test_list_is_registered_as_drawn():
    assert RENDERERS["list"] is list_type.render


def test_it_tells_the_respondent_how_to_answer():
    assert "<p>Please enter one item per line.</p>" in render_question(QUESTION)


def test_the_textarea_is_empty_rather_than_valued():
    html = render_question(QUESTION)
    assert 'rows="4"></textarea>' in html
    assert "value=" not in html


def test_the_schema_changes_nothing():
    plain = render_question(QUESTION)
    for schema in ({"format": {"type": "dropdown"}}, {"exclusive_options": ["a"]}):
        assert render_question(QUESTION, schema) == plain


def test_a_comment_still_attaches_to_it():
    html = render_question_with_comment(QUESTION, {"comment": {"label": "Why?"}})
    assert "edsl-list-question" in html
    assert "Why?" in html


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

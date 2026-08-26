"""Parity tests for the free-text renderer.

The simplest type here: a question text and a textarea, with nothing that varies
and no configuration the reference passes through. That makes the useful tests
short and mostly about what should *not* appear — an empty textarea rather than
a `value` attribute, and no schema-driven anything, because the schema has
nothing to say to this control.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and the README under "The goldens".

Runs under pytest, or directly: python tests/test_free_text.py
"""

from __future__ import annotations

import goldens
from runway import render_question, render_question_with_comment
from runway.question_types import RENDERERS, free_text

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

QUESTION = {
    "question_name": "improve",
    "question_type": "free_text",
    "question_text": "What would you change about your visit?",
}


def test_free_text_matches_react():
    case = CASES["free_text"]
    assert (
        render_question(case["question"], case["humanize_schema"])
        == GOLDENS["free_text"]
    )


def test_free_text_is_registered_as_drawn():
    assert RENDERERS["free_text"] is free_text.render


def test_the_textarea_is_empty_rather_than_valued():
    """A preview shows the unanswered page, and React renders a controlled
    textarea with an empty value as empty content -- not as `value=""`. Emitting
    the attribute would be markup the reference never produces."""
    html = render_question(QUESTION)
    assert 'rows="4"></textarea>' in html
    assert "value=" not in html


def test_the_schema_changes_nothing():
    """The reference mounts this type without passing a schema, so there is
    nothing here for one to change. A schema that seemed to would mean this
    template had grown a setting the live page does not honour."""
    plain = render_question(QUESTION)
    for schema in ({"format": {"type": "dropdown"}}, {"exclusive_options": ["a"]}):
        assert render_question(QUESTION, schema) == plain


def test_a_comment_still_attaches_to_it():
    """The comment box is a sibling of the question rather than part of it, so
    it reaches every type including this one."""
    html = render_question_with_comment(QUESTION, {"comment": {"label": "Why?"}})
    assert "edsl-free-text-question" in html
    assert "Why?" in html


def test_question_text_is_rendered_as_markdown():
    html = render_question({**QUESTION, "question_text": "What would you **change**?"})
    assert "<strong>change</strong>" in html


def test_question_text_is_escaped_the_way_react_escapes_it():
    html = render_question({**QUESTION, "question_text": "What'd you change?"})
    assert "&#x27;" in html and "&#39;" not in html


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

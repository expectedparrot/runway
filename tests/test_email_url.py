"""Parity tests for the email and URL renderers.

Each is a question text and one input, with nothing that varies and no
configuration the reference passes through -- the single-line siblings of
``free_text``. The URL input is a text input with a URL keyboard rather than
``type="url"``, since the reference accepts a bare domain that a URL input
would refuse.

The markup to match is recorded from the reference component, not written here.
See ``test_choice.py`` and SPEC.md under "The goldens".

Runs under pytest, or directly: python tests/test_email_url.py
"""

from __future__ import annotations

import goldens
from runway import render_question, render_question_with_comment
from runway.question_types import RENDERERS, email, url

CASES = goldens.load_cases()
GOLDENS = goldens.load_goldens()

EMAIL = {
    "question_name": "contact_email",
    "question_type": "email",
    "question_text": "What's the best email to reach you at?",
}
URL = {
    "question_name": "homepage",
    "question_type": "url",
    "question_text": "What's your company's website?",
}


def test_email_matches_react():
    case = CASES["email"]
    assert render_question(case["question"], case["humanize_schema"]) == GOLDENS["email"]


def test_url_matches_react():
    case = CASES["url"]
    assert render_question(case["question"], case["humanize_schema"]) == GOLDENS["url"]


def test_both_are_registered_as_drawn():
    assert RENDERERS["email"] is email.render
    assert RENDERERS["url"] is url.render


def test_the_url_field_accepts_a_bare_domain():
    """A ``type="url"`` input would refuse ``example.com``, which the live
    survey accepts and stores with a scheme added."""
    html = render_question(URL)
    assert 'type="text" inputMode="url"' in html
    assert 'type="url"' not in html


def test_the_inputs_are_unanswered():
    for question in (EMAIL, URL):
        assert 'value=""/>' in render_question(question)


def test_the_schema_changes_nothing():
    """The reference mounts these types without passing a schema, so there is
    nothing here for one to change."""
    for question in (EMAIL, URL):
        plain = render_question(question)
        for schema in ({"format": {"type": "dropdown"}}, {"exclusive_options": ["a"]}):
            assert render_question(question, schema) == plain


def test_a_comment_still_attaches_to_them():
    html = render_question_with_comment(EMAIL, {"comment": {"label": "Why?"}})
    assert "edsl-email-question" in html
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

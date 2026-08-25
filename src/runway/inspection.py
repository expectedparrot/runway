"""What a question will render as, without rendering it.

`render_question` answers this implicitly by dispatching to one of four
renderers. This module answers it explicitly, so a survey can be checked
without writing ninety kilobytes of HTML and reading it -- which was the only
way to find out that a question falls through to the stand-in.

The four outcomes are the four renderers, and they are genuinely different
news:

``drawn``
    A control is transcribed for this type. The preview is the real thing.
``automatic``
    Nobody is ever asked it -- compute, image generation, or any type wrapped
    by ``thinking_question()``. Nothing is missing; there is no control because
    there is no respondent.
``note``
    A human survey can be configured for this type, but no control is
    transcribed here yet. The preview is behind; the survey is fine.
``warning``
    The type has no human-survey rendering anywhere, so no preview could
    exist. What needs changing is the survey, not this package.

The order below mirrors ``renderer.render_question`` exactly, and has to:
a thinking-wrapped ``multiple_choice`` is still ``multiple_choice``, so asking
the registry first would report a radio list for a page no respondent is served.
"""

from __future__ import annotations

from .question_types import RENDERERS, background, unsupported

# Ordered worst-news-last, which is also the order a summary reads best in.
STATUSES = ("drawn", "automatic", "note", "warning")

EXPLANATIONS = {
    "drawn": "previews with its real control",
    "automatic": "answered on the server; no respondent ever sees it",
    "note": "no preview built for this type yet",
    "warning": "cannot be shown to a respondent at all",
}


def classify(question: dict) -> str:
    """Which of :data:`STATUSES` this question will render as."""
    if background.is_background_question(question):
        return "automatic"
    question_type = question.get("question_type") or ""
    if question_type in RENDERERS:
        return "drawn"
    if question_type in unsupported.HUMANIZED_TYPES:
        return "note"
    return "warning"


def describe(question: dict, position: int) -> dict:
    """A question's classification as plain data, for reporting.

    ``position`` is its 1-based place in the survey's item list, which is what
    the progress indicator counts against -- not its index among the questions
    alone.
    """
    status = classify(question)
    entry = {
        "position": position,
        "name": question.get("question_name") or f"question-{position}",
        "type": question.get("question_type") or "unknown",
        "status": status,
        "explanation": EXPLANATIONS[status],
    }
    if status == "automatic":
        # Which of the three, since "automatic" alone does not say whether a
        # model was involved -- and a thinking wrapper is the surprising one.
        entry["kind"] = background.kind_of(question)
    return entry


def summarize(entries: list[dict]) -> dict[str, int]:
    """Count by status, including the zeroes so a report has a stable shape."""
    counts = dict.fromkeys(STATUSES, 0)
    for entry in entries:
        counts[entry["status"]] += 1
    return counts

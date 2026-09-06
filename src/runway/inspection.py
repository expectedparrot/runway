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
    Nothing a respondent could be served. Either the type has no human-survey
    rendering anywhere, or the survey pages by question group and this question
    is in none of them, so no page carries it. What needs changing is the
    survey, not this package.

The order below mirrors ``renderer.render_question`` exactly, and has to:
a thinking-wrapped ``multiple_choice`` is still ``multiple_choice``, so asking
the registry first would report a radio list for a page no respondent is served.

The one thing that cannot be read off the question is whether a page carries it
at all -- that is a fact about the survey's grouping, and the caller resolves the
pages and passes it in. It is asked first, ahead of even the background test: a
question no page holds is not run for its answer either.
"""

from __future__ import annotations

from .question_types import RENDERERS, background, declined, ungrouped, unsupported

# Ordered worst-news-last, which is also the order a summary reads best in.
STATUSES = ("drawn", "automatic", "note", "warning")

EXPLANATIONS = {
    "drawn": "previews with its real control",
    "automatic": "answered on the server; no respondent ever sees it",
    "note": "no preview built for this type yet",
    "warning": "cannot be shown to a respondent at all",
}


def classify(
    question: dict, humanize_schema: dict | None = None, unserved: bool = False
) -> str:
    """Which of :data:`STATUSES` this question will render as.

    The schema is part of the answer, not decoration: it can ask for a layout
    this package has not transcribed, and a renderer that declines the question
    on those grounds leaves it as undrawn as an unregistered type would.

    ``unserved`` says no page of this survey carries the question -- see
    :mod:`question_types.ungrouped`, and :func:`pages.resolve`, which works it
    out. A warning, because the survey is what needs changing: EDSL will not
    create a human survey from it as written.
    """
    if unserved:
        return "warning"
    if background.is_background_question(question):
        return "automatic"
    question_type = question.get("question_type") or ""
    if question_type in RENDERERS and not declined(question, humanize_schema):
        return "drawn"
    if question_type in unsupported.HUMANIZED_TYPES:
        return "note"
    return "warning"


def describe(
    question: dict,
    position: int,
    humanize_schema: dict | None = None,
    unserved: bool = False,
) -> dict:
    """A question's classification as plain data, for reporting.

    ``position`` is its 1-based place in the survey's item list, which is what
    the progress indicator counts against -- not its index among the questions
    alone.
    """
    status = classify(question, humanize_schema, unserved)
    entry = {
        "position": position,
        "name": question.get("question_name") or f"question-{position}",
        "type": question.get("question_type") or "unknown",
        "status": status,
        "explanation": EXPLANATIONS[status],
    }
    if unserved:
        # Said in the same words the page says it in, from the same constant:
        # a report and a preview describing one problem two ways is how an
        # author ends up thinking they are two problems.
        entry["reason"] = ungrouped.REASON
        return entry
    if status == "automatic":
        # Which of the three, since "automatic" alone does not say whether a
        # model was involved -- and a thinking wrapper is the surprising one.
        entry["kind"] = background.kind_of(question)
    reason = declined(question, humanize_schema)
    if reason:
        # A type this package draws, on a question it cannot: worth saying
        # exactly, because "no preview built for this type yet" would be a
        # puzzle next to the same type drawn two questions earlier.
        entry["reason"] = reason
    return entry


def summarize(entries: list[dict]) -> dict[str, int]:
    """Count by status, including the zeroes so a report has a stable shape."""
    counts = dict.fromkeys(STATUSES, 0)
    for entry in entries:
        counts[entry["status"]] += 1
    return counts

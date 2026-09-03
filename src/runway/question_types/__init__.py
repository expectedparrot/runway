"""Per-question-type renderers.

Adding a type is: write a module exposing ``render(question, humanize_schema)``
and register it below. Anything not registered falls through to the
"no preview available" notice, so an unregistered type is never an error.

A module can serve several types where the reference does -- ``choice`` covers
the three that share one implementation over there.

The registry answers "which control draws this type". It is deliberately not
asked whether the question is drawn at all: a question answered on the server is
never shown whatever its type is, and ``background`` handles that one level up
in ``renderer.render_question``.

``DECLINES`` is the third answer -- a type with a renderer that nonetheless
cannot draw *this* question, because the humanize schema asks for a layout not
transcribed yet. It is separate from the registry so that the gap is stated once
and read by both the renderer and the ``check`` classifier, which must agree.
"""

from __future__ import annotations

from collections.abc import Callable

from . import (
    background,
    checkbox,
    checkbox_with_other,
    choice,
    free_text,
    matrix,
    survey_message,
    unsupported,
)

Renderer = Callable[[dict, "dict | None"], str]

RENDERERS: dict[str, Renderer] = {
    "multiple_choice": choice.render,
    "likert_five": choice.render,
    "yes_no": choice.render,
    "linear_scale": choice.render,
    "matrix": matrix.render,
    "checkbox": checkbox.render,
    "checkbox_with_other": checkbox_with_other.render,
    "free_text": free_text.render,
    "survey_message": survey_message.render,
}

# Renderers that draw only some of what their type can be configured as. Each
# answers "why not this question", so that a partial transcription is a stated
# gap rather than a preview quietly showing a layout nobody is served -- and so
# that one answer serves both the renderer and `check`.
#
# Empty, and kept: `matrix` was the entry, for the carousel format it now draws.
# The mechanism is where the next partial renderer states its gap, and both
# callers already ask -- putting it back later should not mean re-threading it
# through `renderer.render_question` and `inspection.classify` again.
DECLINES: dict[str, Callable[[dict, dict | None], str | None]] = {}


def declined(question: dict, humanize_schema: dict | None = None) -> str | None:
    """Why this question gets no control despite its type having one, or None."""
    check = DECLINES.get(question.get("question_type") or "")
    return check(question, humanize_schema) if check else None


def get_renderer(question_type: str) -> Renderer:
    """Return the renderer for a question type, or the unsupported notice."""
    return RENDERERS.get(question_type, unsupported.render)


__all__ = ["DECLINES", "RENDERERS", "Renderer", "background", "declined", "get_renderer"]

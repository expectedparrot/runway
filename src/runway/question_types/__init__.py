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
"""

from __future__ import annotations

from collections.abc import Callable

from . import background, choice, unsupported

Renderer = Callable[[dict, "dict | None"], str]

RENDERERS: dict[str, Renderer] = {
    "multiple_choice": choice.render,
    "likert_five": choice.render,
    "yes_no": choice.render,
    "linear_scale": choice.render,
}


def get_renderer(question_type: str) -> Renderer:
    """Return the renderer for a question type, or the unsupported notice."""
    return RENDERERS.get(question_type, unsupported.render)


__all__ = ["RENDERERS", "Renderer", "background", "get_renderer"]

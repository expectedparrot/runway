"""Notice for the questions a respondent is never shown.

Some survey items are answered without anyone being asked. A ``compute``
question is evaluated on the server, an ``image_generation`` question is sent to
an image model, and a question of *any* type can be wrapped by EDSL's
``thinking_question()`` to be answered by its own model rather than by a person.
The survey navigator runs all three between pages and advances straight past
them -- it asks whether a question is thinking-wrapped or an instance of the
compute or image-generation types, which is the test this module mirrors -- so a
page for one is never served to anybody.

That makes them a third situation, not a variant of the two in ``unsupported``.
The note there means this package is behind; the warning there means the survey
needs changing. Here nothing is missing and nothing is wrong: there is no
control because there is no respondent, and saying so is more useful than
apologising for a control that will never exist.

Being a thinking question is a property of the *question*, not of its type: a
``multiple_choice`` wrapped by ``thinking_question()`` is still
``multiple_choice``, and left to the type registry it would be drawn with its
radio list -- a page the survey never serves. So this is dispatched on ahead of
the registry; see ``renderer.render_question``.

Markup lives in ``templates/questions/background.html``.
"""

from __future__ import annotations

from markupsafe import Markup

from .. import icons
from ..templating import render as render_template

TEMPLATE = "questions/background.html"
ICON_CLASS = "mt-0.5 size-4 shrink-0 text-blue-600"

# Question types that are always run in the background, whatever else they say.
BACKGROUND_TYPES = frozenset({"compute", "image_generation"})

# What ``thinking_question()`` leaves behind in ``to_dict()``. The system prompt
# is not a reliable marker -- it defaults to the empty string -- so the model is
# the one to test for.
THINKING_KEY = "thinking_model"

# Why this particular question never reaches a respondent. Keyed by the kind
# ``kind_of`` resolves, not by question type, since a thinking question keeps
# whatever type it wrapped.
REASONS = {
    "compute": "Its answer is computed on the server from the answers before it.",
    "image_generation": "An image model generates its answer on the server.",
    "thinking": (
        "A model answers it on the server, using the model and system prompt "
        "carried on the question rather than the survey's."
    ),
}


def kind_of(question: dict) -> str | None:
    """Which kind of background question this is, or None if it is not one.

    Type before wrapper, matching the order the runner dispatches in: a
    ``compute`` question that has also been wrapped is still evaluated locally,
    not sent to a model.
    """
    question_type = question.get("question_type") or ""
    if question_type in BACKGROUND_TYPES:
        return question_type
    if question.get(THINKING_KEY):
        return "thinking"
    return None


def is_background_question(question: dict) -> bool:
    """Whether this question is answered on the server rather than by a person."""
    return kind_of(question) is not None


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render the notice for a question the survey answers on its own."""
    kind = kind_of(question)
    return render_template(
        TEMPLATE,
        reason=REASONS[kind] if kind else "",
        # Already-built markup; Markup keeps it from being escaped.
        icon=Markup(icons.render("info", size=24, class_name=ICON_CLASS)),
    )

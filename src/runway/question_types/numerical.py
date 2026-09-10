"""Renderer for ``numerical``: a number a respondent types in.

The type has two formats, and this draws one of them. ``input`` is a single
number field, and it is what the reference renders when the humanize schema says
nothing about format -- so it is what nearly every numerical question previews
as.

``slider`` is the other, a range control carrying its own minimum, maximum and
step. It is not transcribed, and it is not guessed at either: a question
configured for a slider takes the stand-in through :data:`DECLINE`, because
drawing the number field there would show a control the respondent is never
served. A slider is also the one place a numerical question's markup depends on
the schema's values rather than only on its shape, so half-drawing it would be
worse than not drawing it.

The markup lives in ``templates/questions/numerical.html`` and is verified
byte-for-byte against the reference component's server-rendered output.
"""

from __future__ import annotations

from markupsafe import Markup

from ..blocks import prepared
from ..markdown import render_question_text
from ..templating import render as render_template

TEMPLATE = "questions/numerical.html"


def _format_type(humanize_schema: dict | None) -> str:
    """Which format the schema asks for; ``input`` when it says nothing."""
    if not humanize_schema:
        return "input"
    return (humanize_schema.get("format") or {}).get("type") or "input"


def declines(question: dict, humanize_schema: dict | None = None) -> str | None:
    """Why this question gets no control, or None if it gets one."""
    if _format_type(humanize_schema) == "slider":
        return "the slider format is not transcribed"
    return None


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a numerical question as static HTML.

    ``humanize_schema`` selects the format, and a slider never reaches here --
    :func:`declines` sends it to the stand-in one level up. Nothing else in the
    schema changes this markup: the field carries no bounds, since the reference
    puts none on it either.
    """
    return render_template(
        TEMPLATE,
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        question_text_blocks=prepared(question.get("question_text_blocks")),
    )

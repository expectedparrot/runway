"""Renderer for ``checkbox``: options a respondent may tick any number of.

Two things here are not visible from the type alone.

**Select all** is drawn by the wrapper the survey page mounts, whose default is
the opposite of the presentational component's -- so the row belongs on the page
even though nothing in the question asks for it. It appears only when more than
one option could be ticked by it.

**Exclusive options** are the schema reaching into that count. An option like
"None of the above" clears everything else when ticked, so it is not part of
"all"; a question of two options where one is exclusive has one selectable
option left and loses the Select all row entirely. That is the only way a
humanize schema changes this markup, and it is why the schema is read here
rather than ignored.

The markup lives in ``templates/questions/checkbox.html`` and is verified
byte-for-byte against the reference component's server-rendered output.
"""

from __future__ import annotations

from markupsafe import Markup

from ..markdown import render_option_text, render_question_text
from ..templating import render as render_template
from .values import as_text

TEMPLATE = "questions/checkbox.html"


def exclusive_options(humanize_schema: dict | None) -> list[str]:
    """Options that clear the rest when ticked, per the humanize schema."""
    if not humanize_schema:
        return []
    options = humanize_schema.get("exclusive_options")
    return list(options) if isinstance(options, list) else []


def _options(question: dict) -> list[dict[str, object]]:
    options = question.get("question_options") or []
    if isinstance(options, str):
        # Piped options: a template rather than a list, and nothing to
        # enumerate outside a live run. The choice family substitutes the same
        # explanatory line, and this reproduces it so a piped question previews
        # the same way whichever control it wears.
        options = [
            f"{options} — In a live survey, each item from {options} will be "
            "shown as a separate option."
        ]
    return [
        {"label_html": Markup(render_option_text(as_text(option)))}
        for option in options
    ]


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a checkbox question as static HTML."""
    options = question.get("question_options") or []
    if isinstance(options, str):
        options = [options]
    exclusive = exclusive_options(humanize_schema)
    selectable = [option for option in options if option not in exclusive]
    return render_template(
        TEMPLATE,
        question_name=question.get("question_name", ""),
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        options=_options(question),
        # One option has nothing to say "all" about, so the row is not drawn.
        show_select_all=len(selectable) > 1,
    )

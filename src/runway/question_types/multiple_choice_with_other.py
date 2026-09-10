"""Renderer for ``multiple_choice_with_other``: one choice, or one written in.

A choice question with an extra row on the end, and the row is an ordinary radio
in the same group as the options -- which is what makes the two exclusive of each
other without a rule anywhere. Below it sits the text field that row is for.

Two things are worth knowing before reading the template:

**The written answer is one field, not a list.** This type takes a single
answer, where the checkbox flavour takes several and draws a row each with the
buttons to add and remove them.

**The field is unanswered in a preview**, so it carries an empty value and the
radio above it is unchosen. Nothing in the humanize schema changes this markup:
the type's schema carries only optionality and the comment box, and the comment
box is a sibling of the question rather than part of it.

The markup lives in ``templates/questions/multiple_choice_with_other.html`` and
is verified byte-for-byte against the reference component's server-rendered
output; this module only prepares the context.
"""

from __future__ import annotations

from markupsafe import Markup

from ..blocks import prepared, prepared_option
from ..markdown import render_option_text, render_question_text
from ..templating import render as render_template
from .values import as_text

TEMPLATE = "questions/multiple_choice_with_other.html"


def _options(question: dict) -> list[dict[str, object]]:
    """The listed options, each with its markdown label and any file blocks.

    Piped options -- a template string rather than a list -- get the same
    explanatory line the choice family substitutes, so a piped question previews
    alike whichever control it wears.
    """
    options = question.get("question_options") or []
    if isinstance(options, str):
        options = [
            f"{options} — In a live survey, each item from {options} will be "
            "shown as a separate option."
        ]
    option_blocks = question.get("question_options_blocks")
    prepared_options = []
    for index, option in enumerate(options):
        text = as_text(option)
        blocks = (
            option_blocks[index]
            if isinstance(option_blocks, list) and index < len(option_blocks)
            else None
        )
        prepared_options.append(
            {
                "value": text,
                "label_html": Markup(render_option_text(text)),
                "blocks": prepared_option(blocks),
            }
        )
    return prepared_options


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a multiple-choice-with-other question as static HTML.

    ``humanize_schema`` is accepted and unused, for the reason in the module
    docstring: this type's schema holds nothing that reaches its markup.
    """
    return render_template(
        TEMPLATE,
        question_name=question.get("question_name", ""),
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        question_text_blocks=prepared(question.get("question_text_blocks")),
        options=_options(question),
        other_option_text=question.get("other_option_text") or "",
    )

"""Renderer for ``list``: a question text, an instruction and a textarea.

The respondent writes one item per line. Nothing about it varies -- the
reference passes no configuration through and the humanize schema has none to
give it -- so the template is the question text, the fixed instruction and an
empty textarea, like ``free_text`` with one line of guidance added.

The markup lives in ``templates/questions/list.html`` and is verified
byte-for-byte against the reference component's server-rendered output.
"""

from __future__ import annotations

from markupsafe import Markup

from ..blocks import prepared
from ..markdown import render_question_text
from ..templating import render as render_template

TEMPLATE = "questions/list.html"


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a list question as static HTML.

    ``humanize_schema`` is accepted and unused: the reference mounts this type
    without passing one, so there is nothing here for it to change.
    """
    return render_template(
        TEMPLATE,
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        question_text_blocks=prepared(question.get("question_text_blocks")),
    )

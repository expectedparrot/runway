"""Renderer for ``url``: a question text and a single web-address input.

Nothing about it varies -- the reference passes no configuration through and the
humanize schema has none to give it -- so the template is the question text and
a fixed input, like ``free_text``'s textarea.

The markup lives in ``templates/questions/url.html`` and is verified
byte-for-byte against the reference component's server-rendered output.
"""

from __future__ import annotations

from markupsafe import Markup

from ..blocks import prepared
from ..markdown import render_question_text
from ..templating import render as render_template

TEMPLATE = "questions/url.html"


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a url question as static HTML.

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

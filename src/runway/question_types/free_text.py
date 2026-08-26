"""Renderer for ``free_text``: a question text and a textarea.

The simplest type here, and the only one whose control has no options at all.
Nothing about it varies -- the reference passes no configuration through and the
humanize schema has none to give it -- so the template is the question text and
a fixed textarea, and the whole of what a preview can get wrong is the class
string on that textarea.

The markup lives in ``templates/questions/free_text.html`` and is verified
byte-for-byte against the reference component's server-rendered output.
"""

from __future__ import annotations

from markupsafe import Markup

from ..markdown import render_question_text
from ..templating import render as render_template

TEMPLATE = "questions/free_text.html"


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a free-text question as static HTML.

    ``humanize_schema`` is accepted and unused: the reference mounts this type
    without passing one, so there is nothing here for it to change. The comment
    box a schema can attach is a sibling of the question, not part of it, and is
    rendered by ``renderer.render_question_with_comment``.
    """
    return render_template(
        TEMPLATE,
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
    )

"""Renderer for ``numerical_range``: a range a respondent types as two numbers.

A From field and a To field, each numerical's number input under a label. The
type has one format, ``input``, so there is nothing to decline: every numerical
range draws the same pair.

The question's bounds (``min_value``, ``max_value``) are checked when the page
is submitted and draw nothing, so they are not read.

The markup lives in ``templates/questions/numerical_range.html`` and is verified
byte-for-byte against the reference component's server-rendered output.
"""

from __future__ import annotations

from markupsafe import Markup

from ..blocks import prepared
from ..markdown import render_question_text
from ..templating import render as render_template

TEMPLATE = "questions/numerical_range.html"


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a numerical range question as static HTML."""
    return render_template(
        TEMPLATE,
        question_name=question.get("question_name", ""),
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        question_text_blocks=prepared(question.get("question_text_blocks")),
    )

"""Renderer for ``checkbox_matrix``: a grid where each row can check any number.

Matrix's default pair -- the table above ``md``, the stacked list below it --
with a checkbox in every cell. The rows and columns are matrix's own, prepared
by the same functions, so a labelled option, a row from a scenario file and a
piped axis all come out as they do there. There is no carousel to recognise:
the reference has none for this type, because a row of checkboxes has no click
that finishes it.

The bounds on how many a row may check (``min_selections``, ``max_selections``)
are enforced when the page is submitted and draw nothing, so they are not read.

The markup lives in ``templates/questions/checkbox_matrix.html`` and is verified
byte-for-byte against the reference component's server-rendered output; this
module only prepares the context.
"""

from __future__ import annotations

from markupsafe import Markup

from ..blocks import prepared
from ..markdown import render_question_text
from ..templating import render as render_template
from .matrix import _items, _options

TEMPLATE = "questions/checkbox_matrix.html"


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a checkbox matrix question as static HTML: both views."""
    options = _options(question)
    return render_template(
        TEMPLATE,
        question_name=question.get("question_name", ""),
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        question_text_blocks=prepared(question.get("question_text_blocks")),
        items=_items(question),
        options=options,
        # As matrix's: the custom property the option columns divide by.
        option_count=len(options),
    )

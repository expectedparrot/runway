"""Warning for a question that no page of a grouped survey carries.

A survey presented by question group serves its groups and nothing else. A
question left out of every group is therefore never put to anybody: no page
holds it, and the response records it as skipped. EDSL's
``validate_humanize_schema`` refuses to create a human survey from that survey,
naming the questions it would drop -- so this is not a preview limitation but a
survey that cannot be run as written.

**This is a property of the page, not of the question**, which is what makes it
unlike everything else in this package's dispatch. A ``free_text`` question is
drawn or not drawn by what it *is*; this one is undrawn by where it sits, and the
same question in the same survey draws its real control the moment a group holds
it. So it is not in the renderer registry and is not asked about by
``render_question``: :func:`renderer.render_item` is handed the answer by the
page it is composing, which is the only place that knows.

The question's **text is still drawn**, the way it is for a question the survey
answers on its own -- the author needs to recognise which question this is, and
the wording is the thing they will recognise it by. Only the control is replaced,
because a control here would show a page that cannot exist.

Markup lives in ``templates/questions/ungrouped.html``.
"""

from __future__ import annotations

from markupsafe import Markup

from .. import icons
from ..blocks import prepared
from ..markdown import render_question_text
from ..templating import render as render_template

TEMPLATE = "questions/ungrouped.html"
ICON_CLASS = "mt-0.5 size-4 shrink-0 text-amber-600"

# What `check` says about such a question, and what the page says under it. Kept
# here so the report and the preview cannot describe the same problem two ways.
REASON = "in no question group, so a survey paging by group never serves it"


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render the warning for a question no group holds.

    ``humanize_schema`` is accepted and unused, so this has the signature every
    other stand-in has; nothing a schema can say changes a page that is not
    served.
    """
    text = question.get("question_text") or ""
    return render_template(
        TEMPLATE,
        has_question_text=bool(text),
        question_text_html=Markup(render_question_text(text)),
        question_text_blocks=prepared(question.get("question_text_blocks")),
        icon=Markup(icons.render("triangle-alert", size=24, class_name=ICON_CLASS)),
    )

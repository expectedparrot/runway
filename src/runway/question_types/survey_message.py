"""Renderer for ``survey_message``: text a respondent reads, and nothing else.

EDSL's ``SurveyMessage`` is a question in every structural sense -- it is a
``QuestionBase``, it takes a position in the survey, rules may jump to it -- and
in no behavioural one. Nobody answers it. The respondent reads it and presses
Next; the server records ``"continued"`` from the page it served, which is what
advances them past it.

**It is not a background question**, though both are drawn without a control. A
compute question is answered without a respondent, and its page carries a notice
saying so because there is a page nobody is served. A message has a page, and a
respondent is served it. Its emptiness is the design.

So the whole of the renderer is the question text in the same markup every other
type puts it in -- the reference reaches it through the same component -- and
the wrapper class that names the type. There is nothing for a humanize schema to
change: EDSL's schema for this type is deliberately empty, having no optionality
to configure, no comment field and no submitting indicator, so the parameter is
accepted and unused exactly as ``free_text``'s is.

The markup lives in ``templates/questions/survey_message.html``.
"""

from __future__ import annotations

from markupsafe import Markup

from ..markdown import render_question_text
from ..templating import render as render_template

TEMPLATE = "questions/survey_message.html"


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a survey message as static HTML.

    ``humanize_schema`` is accepted and unused: a message's humanize schema has
    no fields, so there is nothing in one for this to read.
    """
    return render_template(
        TEMPLATE,
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
    )

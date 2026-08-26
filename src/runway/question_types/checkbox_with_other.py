"""Renderer for ``checkbox_with_other``: options plus an "other" the respondent
types into.

A checkbox question with one extra row, and that row is most of the file. The
"other" entry is a checkbox like any other -- so the column runs unbroken -- and
below it a list of text inputs, one per answer, because "other" may be several
things rather than one.

Three things are not guessable from the type, and all three are recorded:

**No Select all.** The wrapper the survey page mounts defaults ``showSelectAll``
to *false* here, where the plain checkbox wrapper defaults it to *true*. The row
never appears, so ``exclusive_options`` -- whose only effect on the plain
checkbox is to take that row away -- changes nothing in this markup at all.

**One empty row, and it cannot be removed.** The question opens with a single
blank answer. Its remove button is rendered anyway rather than omitted, so the
inputs do not resize as rows come and go, but it is ``invisible`` and out of the
tab order.

**No "Add another" button.** It is held back until a row holds something, so on
an unanswered page -- which is what a preview shows -- there is nothing to add
another to.

The markup lives in ``templates/questions/checkbox_with_other.html`` and is
verified byte-for-byte against the reference component's server-rendered output.
"""

from __future__ import annotations

from markupsafe import Markup

from .. import icons
from ..markdown import render_option_text, render_question_text
from ..templating import render as render_template
from .values import as_text

TEMPLATE = "questions/checkbox_with_other.html"

# The reference sizes this one at 24 and then scales it with utilities, as it
# does every lucide icon.
REMOVE_ICON_CLASS = "w-4 h-4"
ADD_ICON_CLASS = "w-4 h-4"


def _rows(other_texts: list[str], other_option_text: str) -> list[dict[str, object]]:
    """The typed-answer rows, in the two states the reference gives them.

    A row can be removed only when it is not the only one -- there is nowhere
    for a removal to leave the respondent otherwise -- and the button says so
    twice over: out of the tab order, and `invisible` rather than absent, so the
    inputs do not resize as rows come and go.

    The label names the answer where there is one. An empty row is numbered
    instead, because "Remove" alone would not say which.
    """
    removable = len(other_texts) > 1
    rows = []
    for index, text in enumerate(other_texts):
        answer = text.strip()
        rows.append(
            {
                "value": text,
                "aria_label": f"{other_option_text}, answer {index + 1}",
                "remove_label": (
                    f"Remove {answer}" if answer else f"Remove empty answer {index + 1}"
                ),
                "removable": removable,
            }
        )
    return rows


def _options(question: dict, selected: list | None = None) -> list[dict[str, object]]:
    options = question.get("question_options") or []
    if isinstance(options, str):
        # Piped options: the same explanatory line the rest of the package
        # substitutes, so a piped question previews the same way whichever
        # control it wears.
        options = [
            f"{options} — In a live survey, each item from {options} will be "
            "shown as a separate option."
        ]
    ticked = set(selected or [])
    return [
        {
            "label_html": Markup(render_option_text(as_text(option))),
            "checked": option in ticked,
        }
        for option in options
    ]


def render(
    question: dict, humanize_schema: dict | None = None, answer: dict | None = None
) -> str:
    """Render a checkbox-with-other question as static HTML.

    ``humanize_schema`` is accepted and unused. That is not an oversight: the
    only setting that reaches the plain checkbox's markup is
    ``exclusive_options``, and it does so by removing a Select all row this type
    never draws. A recorded case holds the two to being identical.

    ``answer`` renders the question as though a respondent had begun filling it
    in -- ``{"options": [...], "other_texts": [...], "other_selected": bool}``.
    A preview never passes it: a page shows the unanswered state, and the
    registry calls this with two arguments. It exists because the *page script*
    has to produce that state in the browser, and markup no test can reach is
    markup nothing holds to the reference -- so the answered case is recorded
    too, and rendered from here to be compared against it.
    """
    answer = answer or {}
    selected = list(answer.get("options") or [])
    other_texts = list(answer.get("other_texts") or [""])
    other_option_text = question.get("other_option_text") or ""
    return render_template(
        TEMPLATE,
        question_name=question.get("question_name", ""),
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        options=_options(question, selected),
        # Plain text, not markdown: the reference interpolates it into the label
        # directly rather than passing it through the option renderer.
        other_option_text=other_option_text,
        other_selected=bool(answer.get("other_selected")),
        rows=_rows(other_texts, other_option_text),
        # Held back until a row holds something: on an untouched question it
        # would be a control for nothing.
        show_add=any(text.strip() for text in other_texts),
        remove_icon=Markup(icons.render("x", class_name=REMOVE_ICON_CLASS)),
        add_icon=Markup(icons.render("plus", class_name=ADD_ICON_CLASS)),
    )

"""Renderer for ``matrix``: a grid of rows answered against one shared scale.

The reference mounts *both* of its default views and lets a breakpoint choose
between them -- a table above ``md``, a stacked list of one-question-per-row
below it -- so this template emits both too. That is not a preview shortcut: it
is what the page serves, and it is why turning a phone sideways mid-question
does not lose an answer. The two views cannot share radio names for the same
reason, since one name is one group and the hidden view's radio would uncheck
the visible one; the stacked view scopes its names under ``_stack``.

An option carries an author's word for it -- ``option_labels``, the same field
the linear scale uses. The two views spend it differently: the table stacks the
label above the number in the column heading, where there is no width to spare,
and the stacked list folds it into the option text as ``1 - Strongly disagree``,
where there is. Both spellings are the reference's own, so both are built here
rather than in the template.

**The carousel format is not drawn yet.** A humanize schema can ask for one row
at a time instead of the two default views, which is a third and quite different
layout; until it is transcribed, a matrix configured that way renders the
stand-in note rather than a grid the respondent will never be shown. See
:func:`declines`.

The markup lives in ``templates/questions/matrix.html`` and is verified
byte-for-byte against the reference component's server-rendered output; this
module only prepares the context.
"""

from __future__ import annotations

from markupsafe import Markup

from ..markdown import render_option_text, render_question_text
from ..templating import render as render_template
from .values import as_text, option_labels

TEMPLATE = "questions/matrix.html"


def declines(question: dict, humanize_schema: dict | None = None) -> str | None:
    """Why this matrix gets no grid despite its type, or None.

    Asked before the renderer runs, so that what ``check`` reports and what the
    page shows cannot disagree: a preview that drew the default views for a
    question configured as a carousel would be showing a layout no respondent
    is served, which is worse than admitting the gap.
    """
    if not humanize_schema:
        return None
    if (humanize_schema.get("format") or {}).get("type") == "carousel":
        return "the carousel format is not drawn yet"
    return None


def _piped_axis_message(template: str) -> list[str]:
    """Fallback for an axis that is a piping template rather than a list.

    Rows and columns can both be piped from a scenario or an earlier answer, and
    outside a live run there is nothing to enumerate: the reference is handed a
    resolved grid by the server and would not survive being handed the template
    instead. One row (or column) carrying the unresolved text says what will be
    there without inventing a shape for it.
    """
    return [
        f"{template} — In a live survey, each item from {template} will be "
        "shown as a separate row or column."
    ]


def _axis(question: dict, key: str) -> list[object]:
    values = question.get(key) or []
    if isinstance(values, str):
        return list(_piped_axis_message(values))
    return list(values)


def _items(question: dict) -> list[dict[str, object]]:
    """The rows: a label each, and nothing else.

    A row's identity in the markup is its index, not its text. The reference
    builds every id and radio-group name that way on purpose -- a row piped from
    a file reads ``<see file dog>``, and an id may not contain whitespace.
    """
    return [
        {"label_html": Markup(render_option_text(as_text(item)))}
        for item in _axis(question, "question_items")
    ]


def _options(question: dict) -> list[dict[str, object]]:
    """The columns, in the three forms the two views need.

    ``header_label`` is the author's word on its own, which only the table uses;
    the stacked list has ``stack_label_html`` with the same word already folded
    in. An unlabelled column shows its own text in both, which is the usual
    case -- the ends of a scale are typically the only points named.
    """
    labels = option_labels(question)
    columns = []
    for option in _axis(question, "question_options"):
        text = as_text(option)
        label = labels.get(text)
        # The reference's own format, spaces included. It folds the label in
        # only when the option has no media to fold it into, and a preview never
        # resolves media, so this is the only branch reachable here.
        stacked = f"{text} - {label}" if label else text
        columns.append(
            {
                "value": text,
                "header_label": label,
                "label_html": Markup(render_option_text(text)),
                "stack_label_html": Markup(render_option_text(stacked)),
            }
        )
    return columns


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a matrix question as static HTML.

    Both default views, as the reference mounts them. A question this module
    :func:`declines` never reaches here -- ``renderer.render_question`` sends it
    to the stand-in instead.
    """
    options = _options(question)
    return render_template(
        TEMPLATE,
        question_name=question.get("question_name", ""),
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        items=_items(question),
        options=options,
        # The one part of the grid a stylesheet cannot know, handed to the table
        # as a custom property for the option columns to divide the leftover
        # width by. No fallback, deliberately: markup arriving without it leaves
        # the width invalid and the columns size themselves off their content,
        # where a fallback of 1 would have every column ask for the whole grid.
        option_count=len(options),
    )

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
and the full-width option rows fold it into the option text as
``1 - Strongly disagree``, where there is room. Both spellings are the
reference's own, so both are built here rather than in the template.

A humanize schema can ask for a **carousel** instead of the default pair --
``format: {"type": "carousel"}`` -- which is a third layout: one row at a time,
its options beneath it. :func:`is_carousel` is what recognises it, and the
markup is ``templates/questions/matrix_carousel.html``. Only the row the page
opens on carries options there, because that is all the reference renders; the
page script swaps in the rest, from the same include.

The markup lives in ``templates/questions/`` and is verified byte-for-byte
against the reference component's server-rendered output; this module only
prepares the context.
"""

from __future__ import annotations

from markupsafe import Markup

from .. import icons
from ..blocks import prepared, prepared_option
from ..markdown import render_option_text, render_question_text
from ..templating import render as render_template
from .values import as_text, option_labels

TEMPLATE = "questions/matrix.html"
CAROUSEL_TEMPLATE = "questions/matrix_carousel.html"
CAROUSEL_OPTIONS_TEMPLATE = "questions/_matrix_carousel_options.html"

# What the reference draws its two nav arrows at. Lucide's own default is 2, so
# this is passed rather than assumed -- see ``icons.render``.
_ARROW_STROKE_WIDTH = 1.5


def is_carousel(humanize_schema: dict | None = None) -> bool:
    """Whether this schema asks for one row at a time rather than the grid.

    A missing ``format`` and a null one both mean the default pair, which is
    every matrix that says nothing about layout.
    """
    if not humanize_schema:
        return False
    return (humanize_schema.get("format") or {}).get("type") == "carousel"


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


def _blocks_at(blocks: object, index: int) -> list[dict]:
    """One row's or column's blocks out of the positional list, if it has any."""
    if not isinstance(blocks, list) or index >= len(blocks):
        return []
    return prepared_option(blocks[index])


def _items(question: dict) -> list[dict[str, object]]:
    """The rows: a label each, and nothing else.

    A row's identity in the markup is its index, not its text. The reference
    builds every id and radio-group name that way on purpose -- a row piped from
    a file reads ``<see file dog>``, and an id may not contain whitespace.
    """
    item_blocks = question.get("question_items_blocks")
    return [
        {
            "label_html": Markup(render_option_text(as_text(item))),
            "blocks": _blocks_at(item_blocks, index),
        }
        for index, item in enumerate(_axis(question, "question_items"))
    ]


def _options(question: dict) -> list[dict[str, object]]:
    """The columns, in the three forms the two views need.

    ``header_label`` is the author's word on its own, which only the table uses;
    ``row_label_html`` has the same word already folded in, for the two layouts
    that draw an option as a full-width row -- the stacked list and the
    carousel, which are the same component over there. An unlabelled column
    shows its own text in every view, which is the usual case: the ends of a
    scale are typically the only points named.
    """
    labels = option_labels(question)
    option_blocks = question.get("question_options_blocks")
    columns = []
    for index, option in enumerate(_axis(question, "question_options")):
        text = as_text(option)
        label = labels.get(text)
        blocks = _blocks_at(option_blocks, index)
        # The reference's own format, spaces included -- but it folds the
        # author's word into the option text only when there is text to fold it
        # into. An option that resolved to an image has none, so there the word
        # *follows* the media instead of being dropped, as a bare text node
        # after the label. Both branches are reachable now that a scenario's
        # files are drawn.
        stacked = f"{text} - {label}" if label and not blocks else text
        columns.append(
            {
                "value": text,
                "header_label": label,
                "label_html": Markup(render_option_text(text)),
                "row_label_html": Markup(render_option_text(stacked)),
                # Escaped as text by the template, which is what the reference
                # does with it -- it is a string beside the label, not markup.
                "row_label_suffix": f" - {label}" if label and blocks else "",
                "blocks": blocks,
            }
        )
    return columns


def render_carousel_options(question: dict, row: int) -> str:
    """One row's option group, as the carousel draws it.

    The page script needs a group per row and may not build one itself, so the
    rows the reference does not render are rendered here instead and parked in
    a ``<template>``. This is the same include the carousel template uses for
    the row it opens on, which is what holds every group to the recorded one.
    """
    return render_template(
        CAROUSEL_OPTIONS_TEMPLATE,
        question_name=question.get("question_name", ""),
        row=row,
        options=_options(question),
    )


def advances_on_select(humanize_schema: dict | None = None) -> bool:
    """Whether answering a row moves the carousel on by itself.

    Absent means on, which is the reference's reading of the same field and the
    backend default behind it -- a config written before the field existed
    advances as it says it does.
    """
    fmt = (humanize_schema or {}).get("format") or {}
    return fmt.get("advance_on_select") is not False


def carousel_option_groups(question: dict) -> list[str]:
    """The option groups the page does not open with: rows 1 onwards.

    The reference renders only the row on screen, so those are the ones the
    page script has to be given rather than build. Row 0 is already on the page
    and is the one a golden covers.
    """
    return [
        render_carousel_options(question, row)
        for row in range(1, len(_items(question)))
    ]


def _render_carousel(question: dict) -> str:
    """One row at a time: the layout a humanize schema can ask for."""
    return render_template(
        CAROUSEL_TEMPLATE,
        question_name=question.get("question_name", ""),
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        question_text_blocks=prepared(question.get("question_text_blocks")),
        items=_items(question),
        options=_options(question),
        chevron_left=Markup(
            icons.render(
                "chevron-left", class_name="h-5 w-5", stroke_width=_ARROW_STROKE_WIDTH
            )
        ),
        chevron_right=Markup(
            icons.render(
                "chevron-right", class_name="h-5 w-5", stroke_width=_ARROW_STROKE_WIDTH
            )
        ),
    )


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a matrix question as static HTML.

    Both default views, as the reference mounts them -- unless the schema asks
    for the carousel, which replaces the pair rather than joining them.
    """
    if is_carousel(humanize_schema):
        return _render_carousel(question)
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
        # The one part of the grid a stylesheet cannot know, handed to the table
        # as a custom property for the option columns to divide the leftover
        # width by. No fallback, deliberately: markup arriving without it leaves
        # the width invalid and the columns size themselves off their content,
        # where a fallback of 1 would have every column ask for the whole grid.
        option_count=len(options),
    )

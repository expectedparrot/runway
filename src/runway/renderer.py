"""Page assembly: question markup -> a standalone HTML document.

Markup lives in ``templates/``; this module prepares context and composes the
fragments. The shell reproduces the **respondent-facing survey page** -- what
someone taking the survey sees -- rather than the authoring-side preview.

Two entry points:

``render_page``
    One question, one document. No preview chrome at all.
``render_bundle``
    A whole survey in one document: every question rendered into its own copy
    of the survey shell, one shown at a time, with a toolbar to jump between
    them. Preferred for anything longer than a single question -- the
    stylesheet is the bulk of a page's weight and a bundle pays for it once.
"""

from __future__ import annotations

import math
from pathlib import Path

from markupsafe import Markup

from . import icons
from . import progress as progress_module
from .question_types import (
    background,
    checkbox,
    declined,
    get_renderer,
    matrix,
    unsupported,
)
from .templating import render as render_template

ASSETS_DIR = Path(__file__).parent / "assets"
STYLESHEET = ASSETS_DIR / "questions.css"

# Marker styles the stepped indicator has a shape for.
MARKERS = ("number", "dot")

# The types whose rules the page script implements. Both carry options that a
# humanize schema can mark exclusive, and one of them draws a Select all row.
CHECKBOX_TYPES = ("checkbox", "checkbox_with_other")

# The web survey loads this font, and Tailwind's preflight sets it as the html
# font-family from theme.fontFamily.sans. Without it every metric shifts --
# line heights, wrapping, option-list heights -- so it matters more than any
# single class.
FONT_HREF = (
    "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:"
    "ital,wght@0,200..800;1,200..800&display=swap"
)

# Attributes the web survey's host page puts on <html>, <body> and the mount
# point. The dark: variants are inert here: no .dark ancestor is ever emitted,
# so previews render light.
HTML_CLASS = "h-full dark:bg-primary-dark-bg dark:text-primary-dark-text"
BODY_CLASS = "h-full"
ROOT_CLASS = "h-full"

# Display names for the toolbar. Anything absent is title-cased from its type.
PRETTY_TYPES = {
    "multiple_choice": "Multiple Choice",
    "multiple_choice_with_other": "Multiple Choice with Other",
    "checkbox_with_other": "Checkbox with Other",
    "free_text": "Free Text",
    "file_upload": "File Upload",
    "likert_five": "Likert Five",
    "linear_scale": "Linear Scale",
    "top_k": "Top K",
    "survey_message": "Message",
    "yes_no": "Yes/No",
    "dict": "Dict",
}


def pretty_type(question_type: str) -> str:
    """Human-readable label for a question type."""
    if question_type in PRETTY_TYPES:
        return PRETTY_TYPES[question_type]
    return question_type.replace("_", " ").title()


def _js_round(value: float) -> int:
    """Round half away from zero, as JavaScript's ``Math.round`` does.

    Python's ``round`` is banker's rounding -- ``round(12.5)`` is 12, where
    ``Math.round(12.5)`` is 13 -- so a survey with 8 questions would disagree
    with the live page on its second question. Progress is never negative here,
    so the simple form is enough.
    """
    return math.floor(value + 0.5)


def render_question(question: dict, humanize_schema: dict | None = None) -> str:
    """Render one question's own markup to an HTML fragment.

    Two things are asked before the type registry, because both are properties
    of the question rather than of its type. A question the survey answers on
    its own is never drawn -- a thinking-wrapped ``multiple_choice`` would
    otherwise get the radio list of a page no respondent is served. And a
    question whose renderer declines it, for a layout its humanize schema asks
    for that is not transcribed yet, gets the same stand-in an undrawn type
    would.
    """
    if background.is_background_question(question):
        return background.render(question, humanize_schema)
    # A type whose renderer draws only some of what it can be configured as: the
    # stand-in says the layout is not transcribed, which is true, where drawing
    # the transcribed one would show a page this respondent is not served.
    if declined(question, humanize_schema):
        return unsupported.render(question, humanize_schema)
    renderer = get_renderer(question.get("question_type", ""))
    return renderer(question, humanize_schema)


def render_comment(question: dict, humanize_schema: dict | None = None) -> str:
    """Render the comment box a humanize schema can attach to a question.

    Returns "" when the schema configures none, which is the common case. A
    schema carrying ``comment: {}`` does get a box, with no label -- absent and
    null mean "no comment", but an empty config means "a comment, unlabelled",
    and the live page draws that distinction the same way.
    """
    comment = (humanize_schema or {}).get("comment")
    if comment is None:
        return ""
    return render_template(
        "comment.html",
        question_name=question.get("question_name") or "",
        label=comment.get("label"),
    )


def render_question_with_comment(
    question: dict, humanize_schema: dict | None = None
) -> str:
    """A question and its comment box: what the survey page puts on the page.

    The comment box is a sibling of the question, not part of it, so it is
    composed here rather than by the question renderers -- which means every
    question type gets it, including those that fall back to the "no preview"
    notice.
    """
    return render_question(question, humanize_schema) + render_comment(
        question, humanize_schema
    )


def render_progress(payload: dict | None = None) -> str:
    """Render a progress payload -- see :mod:`progress` -- as HTML.

    ``None`` is the unconfigured survey: a bar at 0%, which is what a survey
    drew before the indicator was configurable. A ``hidden`` payload renders the
    empty string, which is what the reference component returns for it, and the
    reason this needs no separate "show progress" flag.

    Both readings are clamped and rounded to a whole percent *before* anything
    is drawn, exactly as the reference does, so ``aria-valuenow`` and the label
    beneath the bar can never disagree.
    """
    payload = payload or {}
    kind = payload.get("type", "bar")

    if kind == "hidden":
        return ""

    if kind == "steps":
        return render_template(
            "progress.html",
            kind="steps",
            # A marker style this package predates renders as a numbered step
            # rather than as a marker with no shape at all.
            marker=(
                payload.get("marker") if payload.get("marker") in MARKERS else "number"
            ),
            steps=[
                {
                    "label": step.get("label"),
                    # Same fallback the reference applies: a status from a newer
                    # server ("skipped", say) reads as upcoming.
                    "status": (
                        step.get("status")
                        if step.get("status") in progress_module.STEP_STATUSES
                        else "upcoming"
                    ),
                }
                for step in payload.get("steps") or []
            ],
        )

    fraction = payload.get("fraction") or 0.0
    percent = _js_round(max(0.0, min(1.0, fraction)) * 100)
    return render_template(
        "progress.html",
        kind="bar",
        percent=percent,
        # "loading" below 100% and "complete" at it, matching the progress
        # primitive the reference builds the bar from.
        state="complete" if percent >= 100 else "loading",
        show_label=payload.get("label", progress_module.PERCENT_LABEL) is not None,
    )


def render_body(
    question: dict,
    humanize_schema: dict | None = None,
    progress: dict | None = None,
) -> str:
    """Render the respond page's body markup around one question."""
    return render_template(
        "body.html",
        progress_html=Markup(render_progress(progress)),
        question_html=Markup(render_question_with_comment(question, humanize_schema)),
    )


def exclusive_positions(
    question: dict, humanize_schema: dict | None = None
) -> list[int] | None:
    """Which options clear the rest when ticked, or ``None`` for a non-checkbox.

    The one thing a checkbox's own markup cannot say. A preview's controls
    respond to a click because the browser makes them, but "Select all" and
    "None of the above" are rules rather than markup, and a rule needs to know
    which options it must leave alone. Read from the same schema the renderer
    reads, so the two cannot disagree about what is exclusive.

    **Positions, not option text.** An option label on the page is rendered
    markdown -- ``**Never**`` reaches the DOM as ``Never`` -- so a script
    matching the schema's strings against what it can read there would quietly
    stop recognising any option an author emphasised. The position is the same
    on both sides whatever the label says.

    **Per rendering, not per question name.** Options can be piped, and a piped
    list resolves per scenario -- so one question can be several different
    option lists with the exclusive option in a different place in each. Keyed
    by name, one of those renderings would get another's positions, and clicking
    an ordinary option would clear the rest while the exclusive one did nothing.

    The empty list and ``None`` are different answers: the first is a checkbox
    with nothing exclusive, which still needs the script; the second is a
    question that is not a checkbox at all. A question whose options are still a
    template string resolves to one explanatory line, which nothing can be
    exclusive of.
    """
    if question.get("question_type") not in CHECKBOX_TYPES:
        return None
    exclusive = checkbox.exclusive_options(humanize_schema)
    options = question.get("question_options") or []
    if isinstance(options, str):
        options = []
    return [index for index, option in enumerate(options) if option in exclusive]


def _positions_attribute(positions: list[int] | None) -> str | None:
    """:func:`exclusive_positions` as the attribute the page script reads."""
    if positions is None:
        return None
    return " ".join(str(position) for position in positions)


def has_checkbox(questions: list[dict]) -> bool:
    """Whether anything here needs the behaviour script at all.

    Asked on its own rather than read off the positions, which used to carry
    this too: an ordinary survey should ship no script it has no use for, and
    "there is a checkbox here" and "this checkbox's exclusive options are these"
    became two different questions once the second was answered per panel.
    """
    return any(
        question.get("question_type") in CHECKBOX_TYPES for question in questions
    )


def carousel_questions(
    questions: list[dict], humanize_schema: dict | None = None
) -> list[dict]:
    """Every carousel matrix on the page, with what the page script needs.

    A carousel shows one row at a time, and the reference renders only the row
    on screen -- so the option groups for every other row do not exist on a
    static page and the script cannot be allowed to build them. They are
    rendered here from the same include the drawn row uses and parked in a
    ``<template>``, which is the same arrangement ``checkbox_with_other`` uses
    for the states a preview does not open in.

    Empty for a survey with no carousel, which is the common case, and the page
    then carries neither the templates nor the script.
    """
    per_question = (humanize_schema or {}).get("questions") or {}
    found: list[dict] = []
    for question in questions:
        if question.get("question_type") != "matrix":
            continue
        name = question.get("question_name") or ""
        schema = per_question.get(name)
        if not matrix.is_carousel(schema):
            continue
        found.append(
            {
                "question_name": name,
                "advance": matrix.advances_on_select(schema),
                "groups": [
                    Markup(group) for group in matrix.carousel_option_groups(question)
                ],
            }
        )
    return found


def _document(
    *,
    title: str,
    body_html: str,
    custom_css: str | None,
    toolbar_html: str = "",
    carousels: list[dict] | None = None,
    checkbox_present: bool = False,
    root_exclusive: str | None = None,
) -> str:
    """Wrap composed body markup in the standalone document shell.

    ``root_exclusive`` is how a split page -- one question, no panel around it --
    carries what a bundle carries on the panel. The script looks for the nearest
    ancestor with the attribute, so it does not have to know which kind of page
    it is on.
    """
    custom = (custom_css or "").strip()
    return render_template(
        "page.html",
        title=title,
        html_class=HTML_CLASS,
        body_class=BODY_CLASS,
        root_class=ROOT_CLASS,
        font_href=FONT_HREF,
        stylesheet=Markup(STYLESHEET.read_text(encoding="utf-8")),
        custom_css=Markup(custom) if custom else "",
        toolbar_html=Markup(toolbar_html) if toolbar_html else "",
        # Emitted only when a carousel is on the page, so an ordinary survey
        # carries neither the parked option groups nor the script that moves
        # them.
        carousels=carousels or [],
        checkbox_present=checkbox_present,
        root_exclusive=root_exclusive,
        add_icon=Markup(icons.render("plus", class_name="w-4 h-4")),
        body_html=Markup(body_html),
    )


def _as_survey_schema(question: dict, humanize_schema: dict | None) -> dict:
    """One question's schema, in the survey-wide shape the page helpers read.

    ``render_page`` takes the schema for its single question; everything that
    assembles a page reads the survey's, keyed by question name. Wrapping it
    once here keeps the two callers from spelling the same nesting differently.
    """
    return {"questions": {question.get("question_name", ""): humanize_schema}}


def render_page(
    question: dict,
    humanize_schema: dict | None = None,
    custom_css: str | None = None,
    progress: dict | None = None,
) -> str:
    """Render a complete, standalone HTML document for one question.

    The stylesheet is inlined so the file stands on its own. ``custom_css``
    (the survey's ``humanize_schema["survey"]["custom_css"]``) is emitted last
    so it wins, exactly as the live survey applies it. It is the survey author's
    own stylesheet and goes into the page unescaped, as CSS must.

    ``progress`` is a payload from :mod:`progress`; omitting it draws the bar at
    0%, and ``progress.HIDDEN`` leaves the indicator off the page entirely.
    """
    positions = exclusive_positions(question, humanize_schema)
    return _document(
        title=question.get("question_name") or "Survey preview",
        body_html=render_body(question, humanize_schema, progress),
        custom_css=custom_css,
        carousels=carousel_questions(
            [question], _as_survey_schema(question, humanize_schema)
        ),
        checkbox_present=positions is not None,
        root_exclusive=_positions_attribute(positions),
    )


def render_bundle(
    questions: list[dict],
    humanize_schema: dict | None = None,
    title: str = "Survey preview",
    item_names: list[str] | None = None,
    variants: list[list[dict]] | None = None,
    scenarios: list[dict] | None = None,
) -> str:
    """Render a whole survey as one standalone document.

    Each question gets its own copy of the survey shell -- so its progress bar
    reads correctly -- wrapped in a panel that the toolbar shows one at a time.
    Repeating the shell costs ~1.5 KB per question against a stylesheet that is
    inlined once, which is why this is cheaper than a file per question.

    With JavaScript unavailable the first panel stays visible and the rest stay
    hidden, so the document degrades to "the first question" rather than to a
    wall of every question at once.

    ``item_names`` is the survey's full item order -- instructions included --
    used to place each question in the survey and to resolve the boundaries of a
    stepped indicator. It defaults to the questions given here, which is right
    for a survey that is only questions and understates the rest: a step ending
    on an instruction the caller did not name cannot resolve, and the indicator
    falls back to the bar.

    ``variants`` is the same questions bound to each scenario, one list per
    scenario and each parallel to ``questions`` -- what :mod:`scenarios` returns.
    ``scenarios`` describes them for the toolbar: ``{"index", "label"}`` per
    entry, indexed by the *scenario list's* own numbering rather than by
    position here, since that is the number the live survey identifies a
    scenario by.

    **Panels are deduplicated by what they render to.** A question that pipes
    nothing renders identically under every scenario and gets one panel, marked
    as serving all of them; only a question that actually varies is repeated. So
    a survey that pipes nothing collapses to exactly the panel list it has
    without scenarios, and a bundle grows only where the survey really differs.
    """
    humanize_schema = humanize_schema or {}
    per_question = humanize_schema.get("questions") or {}
    survey_schema = humanize_schema.get("survey") or {}
    custom_css = survey_schema.get("custom_css")
    progress_config = survey_schema.get("progress")

    names = [
        question.get("question_name") or f"question-{index + 1}"
        for index, question in enumerate(questions)
    ]
    item_names = item_names if item_names is not None else names
    position_of = {name: index for index, name in enumerate(item_names)}
    total = len(item_names)

    variants = variants if variants else [questions]
    bound = len(variants) > 1
    scenario_ids = (
        [entry["index"] for entry in scenarios]
        if scenarios
        else list(range(len(variants)))
    )

    panels: list[str] = []
    items: list[dict] = []

    for index, question in enumerate(questions):
        name = names[index]
        schema = per_question.get(name)
        progress = progress_module.resolve(
            progress_config,
            # Where this question sits among every item, which is what both
            # readings measure against. A question the caller did not list
            # falls back to its position among the questions.
            position_of.get(name, index),
            total,
            item_names,
        )
        # Grouped on everything the panel would carry, so two scenarios share a
        # panel only when there is genuinely nothing to tell them apart by.
        grouped: dict[tuple[str, str | None], list[int]] = {}
        for slot, variant in enumerate(variants):
            variant_question = variant[index]
            key = (
                render_body(variant_question, schema, progress=progress),
                _positions_attribute(exclusive_positions(variant_question, schema)),
            )
            grouped.setdefault(key, []).append(scenario_ids[slot])
        for (body, exclusive), serves in grouped.items():
            panels.append(
                render_template(
                    "panel.html",
                    body_html=Markup(body),
                    question_name=name,
                    # Both omitted without scenarios, so an ordinary bundle
                    # carries the markup it always has: the panels are then one
                    # per question and their order is the answer.
                    question_index=index if bound else None,
                    scenario_indices=(
                        " ".join(str(one) for one in serves) if bound else None
                    ),
                    exclusive=exclusive,
                    is_active=not panels,
                )
            )
        items.append(
            {
                "name": name,
                "pretty_type": pretty_type(question.get("question_type", "")),
                # Marked in the toolbar as well as on the page: a thinking
                # question keeps the type it wrapped, so "Multiple Choice"
                # alone would not distinguish the page nobody is served from
                # the one before it.
                "is_background": background.is_background_question(question),
            }
        )

    # The toolbar counts questions, not panels: it is preview chrome for moving
    # between the questions in this document, and a question bound to four
    # scenarios is still one question.
    toolbar = (
        render_template(
            "toolbar.html",
            items=items,
            count=len(items),
            scenarios=scenarios if bound else None,
        )
        if len(items) > 1
        else ""
    )

    return _document(
        title=title,
        body_html="".join(panels),
        custom_css=custom_css,
        toolbar_html=toolbar,
        carousels=carousel_questions(questions, humanize_schema),
        checkbox_present=has_checkbox(questions),
    )

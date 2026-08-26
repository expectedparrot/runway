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

from . import progress as progress_module
from .question_types import background, declined, get_renderer, unsupported
from .templating import render as render_template

ASSETS_DIR = Path(__file__).parent / "assets"
STYLESHEET = ASSETS_DIR / "questions.css"

# Marker styles the stepped indicator has a shape for.
MARKERS = ("number", "dot")

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
            marker=payload.get("marker")
            if payload.get("marker") in MARKERS
            else "number",
            steps=[
                {
                    "label": step.get("label"),
                    # Same fallback the reference applies: a status from a newer
                    # server ("skipped", say) reads as upcoming.
                    "status": step.get("status")
                    if step.get("status") in progress_module.STEP_STATUSES
                    else "upcoming",
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


def _document(
    *,
    title: str,
    body_html: str,
    custom_css: str | None,
    toolbar_html: str = "",
) -> str:
    """Wrap composed body markup in the standalone document shell."""
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
        body_html=Markup(body_html),
    )


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
    return _document(
        title=question.get("question_name") or "Survey preview",
        body_html=render_body(question, humanize_schema, progress),
        custom_css=custom_css,
    )


def render_bundle(
    questions: list[dict],
    humanize_schema: dict | None = None,
    title: str = "Survey preview",
    item_names: list[str] | None = None,
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

    panels: list[str] = []
    items: list[dict] = []

    for index, question in enumerate(questions):
        name = names[index]
        body = render_body(
            question,
            per_question.get(name),
            progress=progress_module.resolve(
                progress_config,
                # Where this question sits among every item, which is what both
                # readings measure against. A question the caller did not list
                # falls back to its position among the questions.
                position_of.get(name, index),
                total,
                item_names,
            ),
        )
        panels.append(
            render_template(
                "panel.html",
                body_html=Markup(body),
                question_name=name,
                is_active=index == 0,
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

    # The toolbar counts panels, not survey items: it is preview chrome for
    # moving between the questions in this document.
    toolbar = (
        render_template("toolbar.html", items=items, count=len(items))
        if len(items) > 1
        else ""
    )

    return _document(
        title=title,
        body_html="".join(panels),
        custom_css=custom_css,
        toolbar_html=toolbar,
    )

"""Page assembly: question markup -> a standalone HTML document.

Markup lives in ``templates/``; this module prepares context and composes the
fragments. The shell reproduces the **respondent-facing survey page** -- what
someone taking the survey sees -- rather than the authoring-side preview.

Three entry points:

``render_page``
    One question, one document. No preview chrome at all.
``render_page_of``
    The same, for a page holding several questions -- a survey that pages by
    question group. ``render_page`` is this with a single item.
``render_bundle``
    A whole survey in one document: every page rendered into its own copy of
    the survey shell, one shown at a time, with a toolbar to jump between them.
    Preferred for anything longer than a single question -- the stylesheet is
    the bulk of a page's weight and a bundle pays for it once.
"""

from __future__ import annotations

import math
from pathlib import Path

from markupsafe import Markup

from . import icons
from . import pages as pages_module
from . import progress as progress_module
from .question_types import (
    background,
    checkbox,
    declined,
    get_renderer,
    matrix,
    ungrouped,
    unsupported,
)
from .templating import render as render_template

ASSETS_DIR = Path(__file__).parent / "assets"
STYLESHEET = ASSETS_DIR / "questions.css"

# Marker styles the stepped indicator has a shape for.
MARKERS = ("number", "dot")

# The types whose checkbox rules the page script implements. Both carry options
# that a humanize schema can mark exclusive, and one of them draws a Select all
# row. This is also what decides whether the "Add another" button is parked for
# cloning, which is why `multiple_choice_with_other` is not one of them: its
# written answer is a single field with nothing to add a row to.
CHECKBOX_TYPES = ("checkbox", "checkbox_with_other")

# What the page script publishes state for, found in the rendered body rather
# than guessed from a list of types. Every question drawing a radio or a
# checkbox needs it -- that is most of them, and the set grows whenever a new
# type reaches for the shared control include -- so a list here would be a list
# to forget to add to, and forgetting would look like a control that does not
# respond to a click.
CONTROL_CLASSES = ("edsl-radio-control", "edsl-checkbox-control")

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


def render_item(
    question: dict,
    humanize_schema: dict | None = None,
    exclusive: str | None = None,
    unserved: bool = False,
) -> str:
    """One item's block on the page: the question, its comment, its wrapper.

    The reference wraps every item of a page in an ``edsl-survey-item`` div,
    whether the page holds one question or a whole group, so this is not
    something only a group page grows.

    ``unserved`` is the one thing about a question that its own dict cannot say:
    that no page of this survey carries it, because it is in no question group
    -- see :mod:`question_types.ungrouped`. The page composing this knows, and
    hands the answer down; the control is then replaced by a warning, since
    drawing one would show a page that cannot exist. No comment box either: a
    comment on an answer nobody gives is furniture from a page nobody is served.
    """
    body = (
        ungrouped.render(question, humanize_schema)
        if unserved
        else render_question_with_comment(question, humanize_schema)
    )
    return render_template(
        "survey_item.html",
        item_html=Markup(body),
        exclusive=exclusive,
    )


def render_page_body(
    items: list[tuple[dict, dict | None]],
    progress: dict | None = None,
    unserved: bool = False,
) -> str:
    """Render the respond page's body markup around a page's items.

    ``items`` is ``(question, its humanize schema)`` per question on the page:
    one of them for an ordinary survey, a whole question group's worth for a
    survey that pages by group.

    Where a page holds several questions, each checkbox among them carries its
    own exclusive positions -- see ``survey_item.html``. On a page holding one,
    nothing is emitted here and the panel (or ``#root``) carries them, which is
    where they have always been.

    ``unserved`` says this whole page is one nobody is shown -- a question in no
    question group, in a survey paged by them. It is a property of the page
    rather than of any question on it, which is why it arrives here and not in
    the question dicts; such a page is always one question, since a group is
    what puts two of them together.
    """
    several = len(items) > 1
    return render_template(
        "body.html",
        progress_html=Markup(render_progress(progress)),
        items_html=Markup(
            "".join(
                render_item(
                    question,
                    schema,
                    exclusive=(
                        _positions_attribute(exclusive_positions(question, schema))
                        if several
                        else None
                    ),
                    unserved=unserved,
                )
                for question, schema in items
            )
        ),
    )


def render_body(
    question: dict,
    humanize_schema: dict | None = None,
    progress: dict | None = None,
) -> str:
    """Render the respond page's body markup around one question."""
    return render_page_body([(question, humanize_schema)], progress)


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


def page_exclusive(items: list[tuple[dict, dict | None]]) -> str | None:
    """What the container around a page carries, or ``None`` if it carries none.

    A page of one question puts its exclusive positions on the panel in a bundle
    and on ``#root`` on a split page, which is where the behaviour script has
    always found them. A page of several cannot: the attribute would speak for
    one question and be read by all of them, so each item carries its own
    instead and the container carries nothing.
    """
    if len(items) != 1:
        return None
    question, schema = items[0]
    return _positions_attribute(exclusive_positions(question, schema))


def has_checkbox(questions: list[dict]) -> bool:
    """Whether the "Add another" button has to be parked for cloning.

    Asked on its own rather than read off the positions, which used to carry
    this too: an ordinary survey should ship no script it has no use for, and
    "there is a checkbox here" and "this checkbox's exclusive options are these"
    became two different questions once the second was answered per panel.
    """
    return any(
        question.get("question_type") in CHECKBOX_TYPES for question in questions
    )


def has_behaviour(body_html: str) -> bool:
    """Whether anything on this page needs the behaviour script at all.

    Asked of the rendered body, not the questions: what the script publishes is
    the chosen state of a control, so the question is literally whether one was
    drawn. A page that draws a warning instead of its control answers no on its
    own, with nothing here having to remember to ask.

    A wider question than :func:`has_checkbox`, which stayed behind on the
    types that park an "Add another" button. The two were one flag until a page
    of nothing but `multiple_choice_with_other` got neither and left a typed
    answer beside a row nothing had chosen.
    """
    return any(name in body_html for name in CONTROL_CLASSES)


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
    found = [carousel_entry(question, per_question) for question in questions]
    return [entry for entry in found if entry is not None]


def carousel_entry(
    question: dict, per_question: dict, scenario_indices: str | None = None
) -> dict | None:
    """One carousel's parked rows, or ``None`` if this question is not one.

    ``scenario_indices`` names the panel these belong to, and is what keeps a
    scenario-bound page honest. **The rows must be built from the same rendering
    of the question the visible row was built from** -- these are the rest of
    that question, and a set built from the unbound question would put an
    unpiped row behind a piped one. It is also what makes them unique: the
    script finds them by question name, and a question drawn once per scenario
    is several panels answering to the same name.
    """
    if question.get("question_type") != "matrix":
        return None
    name = question.get("question_name") or ""
    schema = per_question.get(name)
    if not matrix.is_carousel(schema):
        return None
    return {
        "question_name": name,
        "scenario_indices": scenario_indices,
        "advance": matrix.advances_on_select(schema),
        "groups": [Markup(group) for group in matrix.carousel_option_groups(question)],
    }


def _document(
    *,
    title: str,
    body_html: str,
    custom_css: str | None,
    toolbar_html: str = "",
    carousels: list[dict] | None = None,
    checkbox_present: bool = False,
    behaviour_present: bool = False,
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
        behaviour_present=behaviour_present,
        root_exclusive=root_exclusive,
        add_icon=Markup(icons.render("plus", class_name="w-4 h-4")),
        body_html=Markup(body_html),
    )


def _as_survey_schema(items: list[tuple[dict, dict | None]]) -> dict:
    """A page's schemas, in the survey-wide shape the page helpers read.

    A page is given the schema for each question on it; everything that
    assembles a page reads the survey's, keyed by question name. Wrapping them
    once here keeps the two callers from spelling the same nesting differently.
    """
    return {
        "questions": {
            question.get("question_name", ""): schema for question, schema in items
        }
    }


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
    return render_page_of(
        [(question, humanize_schema)], custom_css=custom_css, progress=progress
    )


def render_page_of(
    items: list[tuple[dict, dict | None]],
    custom_css: str | None = None,
    progress: dict | None = None,
    title: str | None = None,
    unserved: bool = False,
) -> str:
    """Render one page of a survey -- its whole run of items -- as a document.

    A page is one question unless the survey pages by question group, in which
    case it is the group; ``items`` is ``(question, its humanize schema)`` for
    each question on it. :func:`render_page` is this with a single item, and
    that page's markup is unchanged by the existence of this one.

    ``title`` defaults to the page's own name -- the group's, where a caller
    knows it, and otherwise the first question's. ``unserved`` marks a page no
    respondent is shown; see :func:`render_page_body`.
    """
    questions = [question for question, _ in items]
    first = questions[0] if questions else {}
    body_html = render_page_body(items, progress, unserved=unserved)
    return _document(
        title=title or first.get("question_name") or "Survey preview",
        body_html=body_html,
        custom_css=custom_css,
        # Neither applies to a page that draws a warning instead of its control:
        # there is no carousel to move and no checkbox to tick.
        carousels=(
            [] if unserved else carousel_questions(questions, _as_survey_schema(items))
        ),
        checkbox_present=not unserved and has_checkbox(questions),
        # No `unserved` guard: such a page draws a warning where its control
        # would be, so there is no control in the body to find.
        behaviour_present=has_behaviour(body_html),
        root_exclusive=None if unserved else page_exclusive(items),
    )


def render_bundle(
    questions: list[dict],
    humanize_schema: dict | None = None,
    title: str = "Survey preview",
    item_names: list[str] | None = None,
    variants: list[list[dict]] | None = None,
    scenarios: list[dict] | None = None,
    pages: list[pages_module.Page] | None = None,
) -> str:
    """Render a whole survey as one standalone document.

    Each page gets its own copy of the survey shell -- so its progress bar
    reads correctly -- wrapped in a panel that the toolbar shows one at a time.
    Repeating the shell costs ~1.5 KB per page against a stylesheet that is
    inlined once, which is why this is cheaper than a file per page.

    With JavaScript unavailable the first panel stays visible and the rest stay
    hidden, so the document degrades to "the first page" rather than to a wall
    of every question at once.

    ``pages`` says which questions land on a page together -- see :mod:`pages`,
    whose ``Page.positions`` index into ``questions``. Given none, a page is one
    question, which is what a survey without question groups is served as.

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

    **Panels are deduplicated by what they render to.** A page that pipes
    nothing renders identically under every scenario and gets one panel, marked
    as serving all of them; only a page that actually varies is repeated. So a
    survey that pipes nothing collapses to exactly the panel list it has without
    scenarios, and a bundle grows only where the survey really differs.
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

    # A page per question, for a caller that has not resolved any. Built here
    # rather than by `pages.resolve`, which walks a survey's *items*: what
    # reaches this function is the previewable questions, and where each of them
    # sits among the items is what `item_names` was given for.
    if pages is None:
        pages = [
            pages_module.Page(
                positions=(index,),
                index=position_of.get(names[index], index),
                group=None,
                name=names[index],
            )
            for index in range(len(questions))
        ]

    panels: list[str] = []
    items: list[dict] = []
    carousels: list[dict] = []

    for number, page in enumerate(pages):
        schemas = [per_question.get(names[position]) for position in page.positions]
        progress = progress_module.resolve(
            progress_config,
            # Where this page begins among every item, which is what both
            # readings measure against: a respondent on it has everything before
            # it behind them, and a step it crosses is the step they are on.
            page.index,
            total,
            item_names,
        )
        # Grouped on everything the panel would carry, so two scenarios share a
        # panel only when there is genuinely nothing to tell them apart by.
        grouped: dict[tuple[str, str | None], list[int]] = {}
        # The rendering each group was formed from, so the carousel rows parked
        # for a panel come from the same binding as the row on it.
        formed_by: dict[tuple[str, str | None], list[dict]] = {}
        for slot, variant in enumerate(variants):
            bound_items = [
                (variant[position], schema)
                for position, schema in zip(page.positions, schemas, strict=True)
            ]
            key = (
                render_page_body(
                    bound_items, progress=progress, unserved=page.unserved
                ),
                None if page.unserved else page_exclusive(bound_items),
            )
            grouped.setdefault(key, []).append(scenario_ids[slot])
            formed_by.setdefault(key, [question for question, _ in bound_items])
        for (body, exclusive), serves in grouped.items():
            serving = " ".join(str(one) for one in serves) if bound else None
            # Nothing to park for a page drawing a warning in place of its
            # control: the carousel it would have had is not on the page.
            for question in [] if page.unserved else formed_by[(body, exclusive)]:
                entry = carousel_entry(question, per_question, serving)
                if entry is not None:
                    carousels.append(entry)
            panels.append(
                render_template(
                    "panel.html",
                    body_html=Markup(body),
                    question_name=page.name,
                    # Both omitted without scenarios, so an ordinary bundle
                    # carries the markup it always has: the panels are then one
                    # per page and their order is the answer.
                    question_index=number if bound else None,
                    scenario_indices=serving,
                    exclusive=exclusive,
                    is_active=not panels,
                )
            )
        on_page = [questions[position] for position in page.positions]
        items.append(
            {
                "name": page.name,
                # A page of one question is named by its type, as it always has
                # been. A group is named by how much is on it: listing four
                # types in a dropdown entry says less than the count does.
                "pretty_type": (
                    pretty_type(on_page[0].get("question_type", ""))
                    if len(on_page) == 1
                    else f"{len(on_page)} questions"
                ),
                # Marked in the toolbar as well as on the page: a thinking
                # question keeps the type it wrapped, so "Multiple Choice"
                # alone would not distinguish the page nobody is served from
                # the one before it. A group counts as automatic only when
                # every question on it is -- a group holding one human question
                # is a page a respondent is served.
                "is_background": all(
                    background.is_background_question(question)
                    for question in on_page
                ),
                # Marked apart from the above, and ahead of it in the template:
                # a question in no group is not served whoever would have
                # answered it, and that is the news an author has to act on.
                "is_unserved": page.unserved,
            }
        )

    # The toolbar counts pages, not panels: it is preview chrome for moving
    # between the pages in this document, and a page bound to four scenarios is
    # still one page.
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

    body_html = "".join(panels)
    return _document(
        title=title,
        body_html=body_html,
        custom_css=custom_css,
        toolbar_html=toolbar,
        carousels=carousels,
        checkbox_present=has_checkbox(questions),
        behaviour_present=has_behaviour(body_html),
    )

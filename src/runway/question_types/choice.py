"""Renderer for the choice family: ``multiple_choice``, ``likert_five``,
``yes_no`` and ``linear_scale``.

One module and one template for four types, because the reference implements
them that way: four components whose bodies differ only in the class on the
outer div, all four handing their options to the same radio-list and dropdown
renderers. Transcribing that as four near-identical templates would invite the
drift this package exists to catch -- four copies to keep in step by hand,
where the reference has one.

An option is a value and a label, which for three of the four are the same
string. ``linear_scale`` is why they are separate fields: it answers with a
number and shows ``3 - Neutral``, and its option labels are built here rather
than in the template because the reference builds them outside its component
too.

The markup lives in ``templates/questions/choice.html`` and is verified
byte-for-byte against each component's server-rendered output; this module only
prepares the context.
"""

from __future__ import annotations

from markupsafe import Markup

from ..markdown import render_option_text, render_question_text
from ..templating import render as render_template

TEMPLATE = "questions/choice.html"

# The types this renders, which are also the keys of the template's wrapper
# class lookup. A question arriving with anything else is rendered as a plain
# multiple choice -- see render().
TYPES = ("multiple_choice", "likert_five", "yes_no", "linear_scale")


def _as_text(value: object) -> str:
    """A question option as text, the way JavaScript would write it.

    Linear scale options are numbers, and the reference turns them into strings
    by interpolating them. JavaScript has one number type, so a scale point that
    arrives as ``1.0`` -- from a survey serialized by a tool that writes whole
    numbers as floats -- reads there as ``1`` and would read here as ``1.0``:
    every option value and label off by a suffix, with nothing to notice it.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _option(value: object, label: str | None = None) -> dict[str, str]:
    """One option's three forms.

    ``value`` and ``label`` are the plain strings; ``label_html`` is the label
    rendered as markdown, which is what a drawn option shows. A dropdown uses
    ``label`` instead -- the reference passes option strings to its ``<select>``
    untouched, markers and all, rather than quietly rendering markup a
    ``<select>`` cannot hold.
    """
    text = _as_text(value)
    label = text if label is None else label
    return {
        "value": text,
        "label": label,
        "label_html": Markup(render_option_text(label)),
    }


def _piped_options_message(template: str) -> list[dict[str, str]]:
    """Fallback text for options that are an unresolved piping template.

    When ``question_options`` is a Jinja template rather than a list -- options
    piped from a scenario or an earlier answer -- there is nothing to enumerate
    outside a live run. The web preview substitutes an explanatory line instead;
    this reproduces it so a piped question previews the same way in both.
    """
    return [
        _option(
            f"{template} — In a live survey, each item from {template} will be "
            "shown as a separate option."
        )
    ]


def _scale_labels(question: dict) -> dict[str, str]:
    """``option_labels`` keyed the way an option will be looked up.

    The reference reads this with ``option in labels``, and JavaScript property
    access turns the number into its text form -- so a live question's integer
    keys and a JSON round-tripped question's string keys behave identically over
    there. Normalizing to text is how that holds here too.

    A missing table means an unlabelled scale, as does an explicit null. The
    reference only tolerates the null: reading ``option in undefined`` throws,
    so a question with no ``option_labels`` at all cannot be served to a
    respondent. Previewing it as a bare scale says more about the question than
    failing to draw it would.
    """
    labels = question.get("option_labels") or {}
    if not isinstance(labels, dict):
        return {}
    return {_as_text(key): str(value) for key, value in labels.items()}


def _options(question: dict) -> list[dict[str, str]]:
    options = question.get("question_options") or []
    if isinstance(options, str):
        return _piped_options_message(options)

    if question.get("question_type") != "linear_scale":
        return [_option(option) for option in options]

    labels = _scale_labels(question)
    scale = []
    for option in options:
        text = _as_text(option)
        # The reference's own format, spaces included. An unlabelled point on a
        # labelled scale shows its number alone -- the ends of a scale are
        # usually the only points named.
        label = f"{text} - {labels[text]}" if text in labels else None
        scale.append(_option(option, label))
    return scale


def _is_dropdown(humanize_schema: dict | None) -> bool:
    if not humanize_schema:
        return False
    return (humanize_schema.get("format") or {}).get("type") == "dropdown"


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render a choice question as static HTML.

    Every type in :data:`TYPES` routes here, and the type selects the wrapper
    class. An unregistered type never reaches this function -- it falls through
    to the stand-in -- but calling it directly with one is not an error either:
    it renders as a multiple choice, which is what the family shares.
    """
    question_type = question.get("question_type")
    return render_template(
        TEMPLATE,
        question_type=question_type if question_type in TYPES else "multiple_choice",
        question_name=question.get("question_name", ""),
        question_text_html=Markup(
            render_question_text(question.get("question_text", ""))
        ),
        options=_options(question),
        is_dropdown=_is_dropdown(humanize_schema),
    )

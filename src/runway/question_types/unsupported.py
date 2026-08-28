"""Stand-in for question types this package does not draw a control for.

Two different things end up here, and they are not the same news:

*This package has not transcribed the type yet.* The survey runs fine with
people; the preview is simply behind. That reads as a note.

*The survey cannot be run with people at all.* The question type has no
human-survey rendering anywhere, so no preview could exist. That reads as a
warning, because it is about the survey rather than about this tool.

Markup lives in ``templates/questions/unsupported.html``.
"""

from __future__ import annotations

from markupsafe import Markup

from .. import icons
from ..markdown import render_question_text
from ..templating import render as render_template

TEMPLATE = "questions/unsupported.html"
NOTE_ICON_CLASS = "mt-0.5 size-4 shrink-0 text-gray-500"
WARNING_ICON_CLASS = "mt-0.5 size-4 shrink-0 text-amber-600"

# The question types a human survey can be configured for -- the ones the
# humanize schema carries a configuration for. Transcribed from that schema's
# own registry of type to configuration, and the whole of it: a type outside
# this set has nothing to render to a respondent, which is why it is worth
# saying differently.
#
# Being in here is not a promise that this package previews the type. It is the
# other axis: whether a preview could exist at all. What this package does draw
# is the renderer registry in ``question_types/__init__.py``.
HUMANIZED_TYPES = frozenset(
    {
        "budget",
        "checkbox",
        "checkbox_with_other",
        "compute",
        "file_upload",
        "free_text",
        "image_generation",
        "interview",
        "likert_five",
        "linear_scale",
        "list",
        "matrix",
        "multiple_choice",
        "multiple_choice_with_other",
        "numerical",
        "rank",
        "survey_message",
        "top_k",
        "yes_no",
    }
)

# Types whose ``question_text`` a respondent never sees, so showing it here
# would suggest the survey displays something it does not. Interview questions
# use it as internal instruction for the interviewer: the question *is* put to a
# respondent, just not in those words. The other questions whose text nobody
# reads -- compute, image generation, thinking -- are not put to a respondent at
# all, and never reach this module; see ``background``.
HIDDEN_TEXT_TYPES = frozenset({"interview"})


def render(question: dict, humanize_schema: dict | None = None) -> str:
    """Render the stand-in for a question type with no control here.

    The question text is included so the page still shows what is being asked
    and pages remain distinguishable; only the input control is absent.
    """
    question_type = question.get("question_type") or "unknown"
    humanized = question_type in HUMANIZED_TYPES
    show_text = question_type not in HIDDEN_TEXT_TYPES
    return render_template(
        TEMPLATE,
        question_type=question_type,
        # Markdown, exactly as a drawn question's text is: an author checking
        # the wording of a type this package has yet to draw should see it
        # rendered the way the survey will render it, not with the markers
        # showing.
        question_text_html=Markup(
            render_question_text(question.get("question_text", "")) if show_text else ""
        ),
        humanized=humanized,
        # Already-built markup; Markup keeps it from being escaped.
        icon=Markup(
            icons.render("info", size=24, class_name=NOTE_ICON_CLASS)
            if humanized
            else icons.render("triangle-alert", size=24, class_name=WARNING_ICON_CLASS)
        ),
    )

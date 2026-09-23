"""A survey with a logo in a banner above every page.

The schema names the logo by the uuid of an asset in the author's library on
Coop -- upload one with ``coop.upload_human_survey_asset("logo.png")`` or
``ep humanize assets upload logo.png`` -- and never carries the image itself.
The uuid below is illustrative and names no real asset, so this example always
previews the way a logo does when it has not been fetched: a placeholder in the
logo's place, at the position and with the alt text the schema gives. Swap in
the uuid of an asset of your own and render with ``--fetch-assets`` to see the
real one.

The stylesheet is what makes the banner a band: the page draws the logo on the
survey's own background, and ``.edsl-survey-banner`` is the hook for putting a
colour behind it -- which is what a white logo needs. ``.edsl-logo`` sizes it;
the page's default is 40px tall, with the width following the image.
"""

from edsl.questions import (
    QuestionFreeText,
    QuestionLinearScale,
    QuestionMultipleChoice,
)
from edsl.surveys import Survey

# Illustrative: an asset uuid is what the schema holds, and this one names none.
LOGO_ASSET = "00000000-0000-4000-8000-000000000000"

CUSTOM_CSS = """.edsl-survey-banner {
    background: #1f3a5f;
}
.edsl-logo {
    height: 48px;
}
.edsl-progress-fill { background: #1f3a5f }
"""

survey = Survey(
    [
        QuestionMultipleChoice(
            question_name="role",
            question_text="Which best describes your role?",
            question_options=[
                "Hiring manager",
                "Recruiter",
                "Team member who interviews",
                "None of these",
            ],
        ),
        QuestionLinearScale(
            question_name="confidence",
            question_text="How confident are you in judging a candidate from a resume?",
            question_options=[1, 2, 3, 4, 5],
            option_labels={1: "Not at all", 5: "Completely"},
        ),
        QuestionFreeText(
            question_name="signals",
            question_text="What on a resume do you look at first, and why?",
        ),
    ]
)

humanize_schema = {
    "survey": {
        "custom_css": CUSTOM_CSS,
        "branding": {
            "logo": {
                "source": {"type": "asset", "asset_uuid": LOGO_ASSET},
                "alt": "Decision Research Lab",
                "position": "left",
            }
        },
    },
}

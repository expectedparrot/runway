"""A survey served a question group at a time, rather than a question at a time.

Two things have to agree for this to happen, and they arrive from different
places. The **survey** defines its question groups -- ``add_question_group``
takes the first and last question of a page, inclusive, and names it -- and the
**humanize schema** asks for them with ``presentation: "group"``. Either alone
changes nothing: a survey with groups whose schema says nothing is served a
question at a time, which is exactly what it was served before it had them.

Three pages here, and each is a different thing worth seeing:

``background``
    Three ordinary questions on one page, which is the whole feature.
``about_choices``
    Three items again, the first of which is a ``survey_message`` -- text a
    respondent reads with nothing to answer. It is a *question* as far as the
    groups are concerned: it takes an index of its own, so the group after it
    starts at 6 rather than 5, and it has to be inside a group like anything
    else. A survey paging by group serves no question that is in none, a message
    included, so one left out would simply never be read.
``wrap_up``
    A page with one question on it. A group of one is still a group, and the
    page is named after it rather than after the question.

``commute_days`` is in **no group at all**, and is the one thing here that is
deliberately wrong. A survey paging by group serves its groups and nothing else,
so a question outside them is never asked and the response records it as skipped
-- EDSL's ``validate_humanize_schema`` refuses to create a human survey from
this survey for exactly that reason. It is in the example because the mistake is
silent everywhere else: the preview draws the question's text with a warning in
place of its control, marks the page ``(no group)`` in the toolbar, and ``check``
reports it as a warning and exits non-zero. Delete the question or add it to a
group and the survey is a valid one; nothing else here depends on it.

``improvements`` is the reason the checkbox is here rather than anywhere else:
"None of the above" clears the rest when ticked, and a page holding several
questions cannot say which of them that rule belongs to from the panel around
them all -- so each item on such a page carries its own. It is the one part of
grouped pages that is behaviour rather than markup.

The stepped progress indicator is configured to change on the same boundaries
the pages do: each step's ``complete_after`` names the last question of a group,
so a marker fills exactly when a page is submitted. That is worth doing
deliberately -- steps and groups are two separate lists, and nothing makes them
agree except naming the right questions.

``custom_css`` styles ``.edsl-survey-item``, which is the hook the live survey
puts around every item of a page for exactly this: how the questions on a group
page are separated is the author's decision, not one the survey makes for them.
A survey that pages per question has the hook too, around its single question,
and the rule below is written so that it only draws a line between items rather
than above the first.
"""

from edsl.questions import (
    QuestionCheckBox,
    QuestionFreeText,
    QuestionLikertFive,
    QuestionLinearScale,
    QuestionMultipleChoice,
    SurveyMessage,
)
from edsl.surveys import Survey

CUSTOM_CSS = """.edsl-survey-item + .edsl-survey-item {
    border-top: 1px solid #e5e7eb;
    padding-top: 1.5rem;
}
"""

survey = Survey(
    [
        QuestionMultipleChoice(
            question_name="work_location",
            question_text="Where do you usually work?",
            question_options=["At home", "In an office", "A mix of both"],
        ),
        QuestionFreeText(
            question_name="role",
            question_text="What is your role?",
        ),
        QuestionLinearScale(
            question_name="years_experience",
            question_text="How many years have you been doing it?",
            question_options=[0, 1, 2, 3, 4, 5],
            option_labels={0: "Under a year", 5: "Five or more"},
        ),
        SurveyMessage(
            question_name="about_this_page",
            question_text=(
                "These questions ask about your working arrangement today. "
                "Answer for your own situation."
            ),
        ),
        QuestionLikertFive(
            question_name="satisfaction",
            question_text="I am satisfied with how I work today.",
        ),
        QuestionCheckBox(
            question_name="improvements",
            question_text="What would improve it? Select all that apply.",
            question_options=[
                "More days at home",
                "A quieter place to work",
                "Better equipment",
                "Fewer meetings",
                "None of the above",
            ],
        ),
        QuestionMultipleChoice(
            question_name="commute_days",
            question_text="How many days a week do you travel to an office?",
            question_options=["None", "One or two", "Three or four", "Five"],
        ),
        QuestionFreeText(
            question_name="anything_else",
            question_text="Anything else you would like to tell us?",
        ),
    ]
)

# First question, last question (inclusive), group name.
survey.add_question_group("work_location", "years_experience", "background")
survey.add_question_group("about_this_page", "improvements", "about_choices")
survey.add_question_group("anything_else", "anything_else", "wrap_up")

humanize_schema = {
    "survey": {
        "presentation": "group",
        "custom_css": CUSTOM_CSS,
        "progress": {
            "type": "steps",
            "marker": "number",
            "steps": [
                {"label": "About you", "complete_after": "years_experience"},
                {"label": "Your setup", "complete_after": "improvements"},
                {"label": "Anything else"},
            ],
        },
    },
    "questions": {
        "improvements": {"exclusive_options": ["None of the above"]},
    },
}

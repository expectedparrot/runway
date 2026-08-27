"""Checkboxes, the Select all row, and answers a respondent types themselves.

The **Select all** row is drawn by the wrapper the survey page mounts rather
than by anything in the question, and it appears only when more than one option
could be ticked by it -- so `newsletter`, with one option, has none.

`reasons` shows the other half of that rule: an option marked exclusive clears
the rest when ticked, so it is not part of "all". With five options and one
exclusive there are still four selectable, and the row stays.

`other_modes` is the with-other variant, whose wrapper defaults the same setting
the *opposite* way: it never draws the row, however many options it has.
"""

from edsl.questions import (
    QuestionCheckBox,
    QuestionCheckBoxWithOther,
    QuestionFreeText,
)
from edsl.surveys import Survey

survey = Survey(
    [
        QuestionCheckBox(
            question_name="modes_used",
            question_text=(
                "Which of these have you used to get to work in the past month?"
            ),
            question_options=[
                "Drive alone",
                "Carpool",
                "Public transit",
                "Walk or cycle",
                "Something else",
            ],
        ),
        QuestionCheckBox(
            question_name="reasons",
            question_text="Why that one most often? Select all that apply.",
            question_options=[
                "It's the fastest",
                "It's the cheapest",
                "It's the only option I have",
                "I enjoy it",
                "None of the above",
            ],
        ),
        QuestionCheckBox(
            question_name="newsletter",
            question_text="Anything else?",
            question_options=["Send me the results when they're published"],
        ),
        QuestionCheckBoxWithOther(
            question_name="other_modes",
            question_text="Any other way you get to work that we missed?",
            question_options=["Motorbike", "Taxi or rideshare"],
            other_option_text="Something else",
        ),
        QuestionFreeText(
            question_name="comment",
            question_text="Anything else about your commute we should know?",
        ),
    ]
)

humanize_schema = {
    "survey": {"progress": {"style": "bar", "show_label": True}},
    "questions": {
        "reasons": {"exclusive_options": ["None of the above"]},
        "comment": {"comment": {"label": "Optional"}},
    },
}

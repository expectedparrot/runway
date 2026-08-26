"""The smallest thing runway will render: one question, no configuration.

Useful as the boundary case -- a bundle of one draws no toolbar, so this is what
a preview looks like with no chrome at all.
"""

from edsl import Survey
from edsl.questions import QuestionMultipleChoice

survey = Survey(
    [
        QuestionMultipleChoice(
            question_name="commute_mode",
            question_text="How do you usually get to work?",
            question_options=[
                "Drive alone",
                "Carpool",
                "Public transit",
                "Walk or cycle",
                "I work from home",
            ],
        )
    ]
)

humanize_schema: dict = {}

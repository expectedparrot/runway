"""A survey with its own stylesheet.

`custom_css` is emitted last in the page so it wins, exactly as the live survey
applies it. Everything it reaches for here is an `edsl-` hook the transcribed
markup carries for this purpose -- no Tailwind utility is targeted, since those
are an implementation detail of how the page is built rather than a promise to
authors.
"""

from edsl.questions import (
    QuestionLikertFive,
    QuestionLinearScale,
    QuestionMultipleChoice,
)
from edsl.surveys import Survey

CUSTOM_CSS = """.edsl-survey-container {
    background: #fbf7f0;
    font-family: Georgia, 'Times New Roman', serif;
}
.edsl-question-text {
    color: #7c2d12;
    font-size: 1.35rem;
    letter-spacing: -0.01em;
}
.edsl-option {
    border: 1px solid #e7d9c4;
    border-radius: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #fffdf9;
}
.edsl-option:hover { border-color: #c2410c }
.edsl-radio { accent-color: #c2410c }
.edsl-progress-fill { background: #c2410c }
.edsl-comment-field {
    border-color: #e7d9c4;
    background: #fffdf9;
}
"""

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
        ),
        QuestionLikertFive(
            question_name="commute_enjoyment",
            question_text="My commute is a good use of my time.",
        ),
        QuestionLinearScale(
            question_name="commute_satisfaction",
            question_text="How is your commute, all things considered?",
            question_options=[1, 2, 3, 4, 5],
            option_labels={1: "Couldn't be worse", 5: "Couldn't be better"},
        ),
    ]
)

humanize_schema = {
    "questions": {
        "commute_satisfaction": {"comment": {"label": "Anything you'd add?"}},
    },
    "survey": {"custom_css": CUSTOM_CSS},
}

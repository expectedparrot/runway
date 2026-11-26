"""Numerical range questions: a From and a To.

Each is two of numerical's number fields under a label, side by side from the
`sm` breakpoint up and stacked below it. Narrow the window to see them stack.

`meal_budget` sets no bounds. `study_ages` sets `min_value` and `max_value`,
which draw nothing: they are checked when the page is submitted, as a
numerical question's are, so the two questions look the same here.
"""

from edsl.questions import QuestionNumericalRange
from edsl.surveys import Survey

survey = Survey(
    [
        QuestionNumericalRange(
            question_name="meal_budget",
            question_text="What's the least and the most you'd spend on a meal out?",
        ),
        QuestionNumericalRange(
            question_name="study_ages",
            question_text="Which ages should the study include?",
            min_value=18,
            max_value=99,
        ),
    ]
)

"""Checkbox matrix questions: a grid where each row can check any number.

The same two layouts as a matrix -- a table above the `md` breakpoint and a
stacked list of one checkbox question per row below it -- with a checkbox in
every cell. Narrow the window to swap between them.

`weekly_activities` is the plain grid. `acceptable_scores` carries
`option_labels`, which the two views spend as a matrix does: the grid stacks the
author's word above the number, the stacked list folds it in as `1 - Poor`. Its
bounds of one to three per row draw nothing; they are checked when the page is
submitted. `channels` is the width stress case, where the stacked list earns
its place.

There is no carousel for this type: a row of checkboxes has no click that
finishes it to move on from.
"""

from edsl.questions import QuestionCheckboxMatrix
from edsl.surveys import Survey

survey = Survey(
    [
        QuestionCheckboxMatrix(
            question_name="weekly_activities",
            question_text="Which of these do you usually do on each day?",
            question_items=["Monday", "Wednesday", "Saturday"],
            question_options=["Exercise", "Cook dinner", "Read", "Couldn't say"],
        ),
        QuestionCheckboxMatrix(
            question_name="acceptable_scores",
            question_text="Which scores would you be happy to give each of these?",
            question_items=[
                "The food",
                "The staff's attention",
                "Value for money",
            ],
            question_options=[1, 2, 3, 4, 5],
            option_labels={1: "Poor", 5: "Excellent"},
            min_selections=1,
            max_selections=3,
        ),
        QuestionCheckboxMatrix(
            question_name="channels",
            question_text=(
                "Where have you heard about each of these products in the last "
                "month? Check every place that applies."
            ),
            question_items=[
                "The new phone plan",
                "The home broadband bundle",
                "The streaming add-on",
            ],
            question_options=[
                "TV",
                "Radio",
                "Podcast",
                "Social media",
                "A search ad",
                "A friend or colleague",
                "In a shop",
                "I haven't heard of it",
            ],
        ),
    ]
)

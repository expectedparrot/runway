"""Matrix questions: the grid, its labels, and the carousel.

A matrix is the first type here that is not a list of options, and the first
whose reference renders *two* layouts at once -- a table above the `md`
breakpoint and a stacked list of one question per row below it. Both are in
every preview; narrow the window to swap between them.

`agreement` is the labelled case, where the two views spend `option_labels`
differently: the grid stacks the author's word above the number, the stacked
list folds it in as `1 - Strongly disagree`.

`one_at_a_time` and `spirits` ask for the third layout, the carousel: one row
at a time, with the options beneath it, which replaces the default pair rather
than joining them. They differ in the one setting the format has. `one_at_a_time`
takes the default, where answering a row moves you on by itself; `spirits` sets
`advance_on_select: false`, where it does not and the arrows are the only way
through. `spirits` also carries `option_labels`, which the carousel folds into
the option text the way the stacked list does.

Dragging a carousel does nothing in a preview -- see README under Known gaps --
so use the arrows here, and try a real one on a phone before sending a survey
out.

`likelihood_10pt` is the width stress case: eleven columns is where a table
stops being readable and the stacked list earns its place.
"""

from edsl.questions import QuestionMatrix, QuestionYesNo
from edsl.surveys import Survey

survey = Survey(
    [
        QuestionMatrix(
            question_name="service_ratings",
            question_text="Rate each part of your visit.",
            question_items=[
                "The food",
                "The staff's attention",
                "Value for money",
                "How long you waited",
            ],
            question_options=["Poor", "Fair", "Good", "Excellent", "Couldn't say"],
        ),
        QuestionMatrix(
            question_name="agreement",
            question_text="How much do you agree with each statement?",
            question_items=[
                "It was easy to book a table",
                "The menu described the dishes well",
                "I'd come again",
            ],
            question_options=[1, 2, 3, 4, 5],
            option_labels={1: "Strongly disagree", 5: "Strongly agree"},
        ),
        QuestionMatrix(
            question_name="one_at_a_time",
            question_text="How often do you order each of these?",
            question_items=["Starters", "Dessert", "Wine"],
            question_options=["Never", "Sometimes", "Usually"],
        ),
        QuestionMatrix(
            question_name="spirits",
            question_text="How would you rate each of these?",
            question_items=[
                "The house red",
                "The cocktail list",
                "The alcohol-free options",
            ],
            question_options=[1, 2, 3, 4, 5],
            option_labels={1: "Poor", 5: "Excellent"},
        ),
        QuestionMatrix(
            question_name="likelihood_10pt",
            question_text=(
                "On a scale from 1 to 10, where 1 is 'not at all likely' and 10 "
                "is 'extremely likely', how likely are you to do each of the "
                "following in the next year? Choose 'I don't know / prefer not "
                "to answer' if you would rather not say."
            ),
            question_items=[
                "Recommend this company as a place to work",
                "Apply for an internal transfer",
                "Take on a leadership role",
                "Still be working here twelve months from now",
            ],
            question_options=[str(n) for n in range(1, 11)]
            + ["I don't know / prefer not to answer"],
        ),
        QuestionYesNo(
            question_name="recommend",
            question_text="Would you recommend us to a friend?",
        ),
    ]
)

humanize_schema = {
    "survey": {"progress": {"style": "bar", "show_label": True}},
    "questions": {
        "agreement": {"comment": {"label": "Anything you'd add?"}},
        # The carousel, in its two settings. Absent means on, which is the
        # reference's own reading of the field, so the first of these is what a
        # schema written before the field existed gets.
        "one_at_a_time": {"format": {"type": "carousel"}},
        "spirits": {"format": {"type": "carousel", "advance_on_select": False}},
    },
}

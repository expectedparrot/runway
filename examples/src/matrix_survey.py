"""Matrix questions: the grid, its labels, and the layout that is not drawn yet.

A matrix is the first type here that is not a list of options, and the first
whose reference renders *two* layouts at once -- a table above the `md`
breakpoint and a stacked list of one question per row below it. Both are in
every preview; narrow the window to swap between them.

`agreement` is the labelled case, where the two views spend `option_labels`
differently: the grid stacks the author's word above the number, the stacked
list folds it in as `1 - Strongly disagree`.

`one_at_a_time` asks for the carousel format, which is not transcribed yet, so
it previews as a note naming the reason rather than as a grid no respondent
would be shown. `likelihood_10pt` is the width stress case: eleven columns is
where a table stops being readable and the stacked list earns its place.
"""

from edsl import Survey
from edsl.questions import QuestionMatrix, QuestionYesNo

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
        # Not transcribed yet, so this one previews as a note. Kept in the
        # example precisely so the gap is visible rather than discovered.
        "one_at_a_time": {"format": {"type": "carousel"}},
    },
}

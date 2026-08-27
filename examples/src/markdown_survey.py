"""Markdown, everywhere a survey can carry it.

Question text and option labels are both rendered as markdown, and this survey
walks the cases that are easy to get subtly wrong: inline emphasis, links with
query strings, block content in a question, a GFM table, code spans that must
*not* be treated as emphasis, and text with characters React and MarkupSafe
escape differently.

Two of them are about restraint rather than support. `md_not_markdown` is text
an author did not mean as markdown -- `snake_case_names` and `3 * 4` -- which
must survive untouched. `md_footnote_gap` uses a footnote, which this preview
does not render; the example is here so the gap is visible rather than
discovered.

`md_dropdown` is configured as a dropdown, where option markers stay literal:
a `<select>` holds text and nothing else, and quietly rendering markup it cannot
show would hide that the two settings do not combine.
"""

from edsl.questions import (
    QuestionLikertFive,
    QuestionLinearScale,
    QuestionMultipleChoice,
    QuestionRank,
    QuestionYesNo,
)
from edsl.surveys import Survey

survey = Survey(
    [
        QuestionMultipleChoice(
            question_name="md_text",
            question_text=(
                "How do you **usually** get to work?\n\n"
                "If you travel more than one way, pick the one you use _most "
                "often_. See [our travel policy](https://example.com/policy?a=1&b=2) "
                "if you are unsure."
            ),
            question_options=["Drive alone", "Carpool", "Public transit"],
        ),
        QuestionLikertFive(
            question_name="md_options",
            question_text="My commute is a good use of my time.",
            question_options=[
                "**Strongly** disagree",
                "_Mildly_ disagree",
                "Neither ~~here~~ nor there",
                "_Mildly_ agree",
                "**Strongly** agree",
            ],
        ),
        QuestionMultipleChoice(
            question_name="md_option_link",
            question_text="Which scheme are you enrolled in?",
            question_options=[
                "The [cycle scheme](https://example.com/cycle)",
                "The `TRAVEL-2` season ticket loan",
                "Neither",
            ],
        ),
        QuestionMultipleChoice(
            question_name="md_dropdown",
            question_text="How long is your commute, **door to door**?",
            question_options=[
                "**Under** 20 minutes",
                "20 to 45 minutes",
                "**Over** 45 minutes",
            ],
        ),
        QuestionYesNo(
            question_name="md_blocks",
            question_text=(
                "## Before you answer\n\n"
                "We define a commute as:\n\n"
                "- travel from home to a workplace\n"
                "- on a day you were expected there\n\n"
                "> Trips made entirely for personal reasons do not count.\n\n"
                "With that in mind — did you commute last week?"
            ),
            question_options=["Yes", "No"],
        ),
        QuestionMultipleChoice(
            question_name="md_table",
            question_text=(
                "Here is what each option costs on an average weekday:\n\n"
                "| Mode | Typical time | Cost each way |\n"
                "| :- | -: | -: |\n"
                "| Train | 35 min | 4.80 |\n"
                "| Bus | 50 min | 2.10 |\n"
                "| Cycle | 40 min | 0.00 |\n\n"
                "Which would you pick **tomorrow**?"
            ),
            question_options=["Train", "Bus", "Cycle"],
        ),
        QuestionLinearScale(
            question_name="md_scale_labels",
            question_text="How is your commute, all things considered?",
            question_options=[1, 2, 3, 4, 5],
            option_labels={1: "Couldn't be **worse**", 5: "Couldn't be **better**"},
        ),
        QuestionMultipleChoice(
            question_name="md_not_markdown",
            question_text=(
                "Which cost code applies? Enter it as `dept_code * 2` — note "
                "that snake_case_names and 3 * 4 are literal."
            ),
            question_options=["snake_case_one", "2 * 3 = 6", 'Don\'t "know" & <unsure>'],
        ),
        QuestionRank(
            question_name="md_undrawn_type",
            question_text=(
                "Rank these from **most** to _least_ annoying.\n\n"
                "There is no control for `rank` here yet, but the wording still "
                "renders as the survey will show it."
            ),
            question_options=["Traffic", "Cost", "Crowding"],
            num_selections=3,
        ),
        QuestionMultipleChoice(
            question_name="md_footnote_gap",
            question_text=(
                "Do you claim mileage?[^1]\n\n"
                "[^1]: Footnotes are the one thing this preview does not render "
                "— see README."
            ),
            question_options=["Yes", "No"],
        ),
    ]
)

humanize_schema = {
    "questions": {
        "md_dropdown": {"format": {"type": "dropdown"}},
        "md_text": {
            "comment": {"label": "Anything to add about **how** you travel?"}
        },
    },
}

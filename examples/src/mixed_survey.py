"""One of everything runway can be asked for.

Types it draws, a type it does not draw yet (`rank`), and a type no human survey
can put to a respondent at all (`dict`) -- so both fallback paths are exercised
alongside the real ones. Most of the survey-level tests read this file, which is
why its shape is worth leaving alone: several of them assert progress values
that follow from there being seven items.
"""

from edsl.questions import (
    QuestionDict,
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
        QuestionMultipleChoice(
            question_name="commute_time",
            question_text="How long is your commute, door to door, one way?",
            question_options=[
                "Under 10 minutes",
                "10 to 20 minutes",
                "20 to 30 minutes",
                "30 to 45 minutes",
                "45 to 60 minutes",
                "Over an hour",
                "It varies too much to say",
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
        QuestionYesNo(
            question_name="commute_switch",
            question_text="Would you switch if a better option existed?",
        ),
        # No control transcribed for this type yet, so it previews as a note.
        # The survey is fine; the package is behind.
        QuestionRank(
            question_name="commute_barriers",
            question_text="Rank these from most to least annoying.",
            question_options=["Traffic", "Cost", "Crowding", "Unreliable timing"],
            num_selections=4,
        ),
        # No human-survey rendering anywhere, so no preview could exist: this one
        # previews as a warning, which is about the survey rather than the tool.
        QuestionDict(
            question_name="commute_breakdown",
            question_text="Roughly how does a typical week's commuting break down?",
            answer_keys=["days_in_office", "minutes_each_way", "usual_departure"],
            value_types=["int", "int", "str"],
            value_descriptions=[
                "Days per week you travel to a workplace",
                "Door-to-door minutes, one way",
                "The time you normally leave home",
            ],
        ),
    ]
)

humanize_schema = {
    "questions": {
        "commute_mode": {
            "comment": {"label": "Anything you'd add about how you get there?"}
        },
        "commute_time": {"format": {"type": "dropdown"}},
    },
}

"""A survey bound to a scenario list, which is three surveys wearing one name.

A humanized survey can be attached to a scenario list, and a respondent is
assigned one scenario for the whole of their response. So a scenario is not
decoration -- it is *which* survey that respondent is given, and previewing one
scenario is previewing a page somebody is actually served.

Three things here are worth pointing at.

**`familiar` and `modes` pipe; `anything` does not.** So `anything` renders the
same under every scenario and the bundle carries it once, marked as serving all
three, while the other two are repeated. That is the whole reason a bundle bound
to a scenario list is not simply questions times scenarios in size.

**`modes` pipes its whole option list**, not a word inside a sentence, and the
three lists are different lengths. Its schema marks "None of these" exclusive --
ticking it clears the rest -- and that option lands at position 3, 1 and 4 in
the three renderings. There is one question name and three right answers, which
is why the preview carries the exclusive positions on each panel rather than in
one table keyed by question.

**Nothing here references an agent or an earlier answer**, which keeps the
example about scenarios. Those render as written wherever they appear; see the
README's Known gaps for why, and for the one case -- a *filter* applied to one --
where a question stops piping altogether.
"""

from edsl.questions import (
    QuestionCheckBox,
    QuestionFreeText,
    QuestionMultipleChoice,
)
from edsl.scenarios import Scenario, ScenarioList
from edsl.surveys import Survey

survey = Survey(
    [
        QuestionMultipleChoice(
            question_name="familiar",
            question_text="How well do you know **{{ city }}**?",
            question_options=[
                "I have never been",
                "I have visited",
                "I have lived there",
            ],
        ),
        QuestionCheckBox(
            question_name="modes",
            question_text=(
                "Which of these have you used to get around {{ scenario.city }}?"
            ),
            question_options="{{ transport }}",
        ),
        QuestionFreeText(
            question_name="anything",
            question_text="Anything else we should know about getting around?",
        ),
    ]
)

humanize_schema = {
    "questions": {"modes": {"exclusive_options": ["None of these"]}},
}

# Both spellings of a scenario key are in use above -- `{{ city }}` bare and
# `{{ scenario.city }}` namespaced -- because the live page exposes every key
# both ways and a preview that only handled one would look right until it met a
# survey written the other.
scenarios = ScenarioList(
    [
        Scenario(
            {
                "city": "Boston",
                "transport": [
                    "The T",
                    "Commuter rail",
                    "Bike share",
                    "None of these",
                ],
            }
        ),
        Scenario({"city": "Austin", "transport": ["The bus", "None of these"]}),
        Scenario(
            {
                "city": "Chicago",
                "transport": [
                    "The L",
                    "Metra",
                    "The bus",
                    "Divvy",
                    "None of these",
                ],
            }
        ),
    ]
)

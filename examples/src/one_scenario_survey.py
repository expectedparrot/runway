"""A survey bound to a scenario list with exactly one scenario in it.

The degenerate case, and it is here because it is not merely a smaller version
of the multi-scenario one -- two things about a bundle change when the list has
a single entry, and both are easy to regress without an example holding them.

**The files are named the way an unbound survey's are.** `--split` writes
`one_scenario_survey-01-visited.html`, with no `-s00-` segment in it. A segment
saying "scenario 0" where there is no scenario 1 is noise, and adding one would
rename every file belonging to anyone who binds a single-scenario list -- so the
naming is keyed on there being a choice to record, not on a scenario existing.

**Every question still pipes.** Nothing about a one-scenario list makes the
substitution optional; `{{ venue }}` resolves here exactly as it does under
three. What disappears is the *choosing*, not the binding.

This is the shape a real survey takes more often than the multi-scenario one
suggests: a study personalized to a single client, site or product, where the
scenario exists to keep the wording in data rather than in the question text.
Both spellings appear again, bare and namespaced, for the same reason they do
in `scenario_survey` -- a preview that handled only one would look right until
it met a survey written the other way.

No humanize schema: nothing here needs a control it would not get by default,
and an example that carried a schema for the sake of having one would suggest a
scenario list requires it.
"""

from edsl.questions import QuestionFreeText, QuestionMultipleChoice
from edsl.scenarios import Scenario, ScenarioList
from edsl.surveys import Survey

survey = Survey(
    [
        QuestionMultipleChoice(
            question_name="visited",
            question_text="Have you been to the **{{ venue }}** in the past year?",
            question_options=[
                "Yes, more than once",
                "Yes, once",
                "No",
                "I did not know it was there",
            ],
        ),
        QuestionFreeText(
            question_name="improve",
            question_text="What would make {{ scenario.venue }} better?",
        ),
    ]
)

scenarios = ScenarioList([Scenario({"venue": "Boston Public Library"})])

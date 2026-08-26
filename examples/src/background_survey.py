"""Questions the survey answers on its own, next to questions it asks.

Three kinds of question are never put to a respondent -- `compute`, which the
server evaluates; `image_generation`, which goes to an image model between
pages; and a question of *any* type wrapped by `thinking_question`, which a
model answers with its own prompt. Their pages carry a third notice saying so,
neither "no preview yet" nor "not supported", because nothing is missing and
nothing is wrong.

The thinking wrapper is the one to watch, and why this example exists: it leaves
the question's type alone, so `pet_category` is still a `multiple_choice` and a
preview asking the type registry first would draw it a radio list for a page no
respondent is served. `pet` is an ordinary `multiple_choice` two lines above it,
so the two are indistinguishable by type.

`pet_story` is here for the other axis: a type that *is* asked but has no
control transcribed yet, so it gets the plain note. It stands in for whatever is
undrawn at the time -- it was `free_text` until free_text was drawn.
"""

from edsl import Survey
from edsl.language_models import Model
from edsl.questions import (
    QuestionCompute,
    QuestionImageGeneration,
    QuestionLinearScale,
    QuestionList,
    QuestionMultipleChoice,
    thinking_question,
)

survey = Survey(
    [
        QuestionMultipleChoice(
            question_name="pet",
            question_text="Which pet do you have at home?",
            question_options=["A dog", "A cat", "Something else", "None"],
        ),
        thinking_question(
            QuestionMultipleChoice(
                question_name="pet_category",
                question_text=(
                    "The respondent said: {{ pet.answer }}. "
                    "Which category does that fall into?"
                ),
                question_options=["Common", "Unusual", "No pet"],
            ),
            model=Model("test"),
            system_prompt="Classify tersely. Answer with the option only.",
        ),
        QuestionImageGeneration(
            question_name="pet_portrait",
            question_text=(
                "A warm watercolour portrait of {{ pet.answer }}, "
                "on a plain background."
            ),
            model="test-image",
            service_name="test",
        ),
        QuestionCompute(
            question_name="pet_word_count",
            question_text="{{ pet.answer | length }}",
        ),
        QuestionLinearScale(
            question_name="pet_attachment",
            question_text="How attached are you to your pet?",
            question_options=[1, 2, 3, 4, 5],
            option_labels={1: "Not at all", 5: "Completely"},
        ),
        QuestionList(
            question_name="pet_story",
            question_text="Tell us about them.",
        ),
    ]
)

humanize_schema: dict = {}

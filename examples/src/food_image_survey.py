"""A survey whose options are pictures, and whose pictures are somewhere else.

The example the other scenario ones build up to. Four things meet here that the
smaller examples hold one at a time:

**Images inside option labels.** `food_category` writes `{{ scenario.baked_img }}`
into each of its options, so the choice a respondent makes is a picture rather
than a word. Option labels are split into blocks the way question text is, and
the schema's custom CSS turns the four of them into a card grid -- which is what
an image option is usually for, and why the CSS is part of the example rather
than a note about it.

**A scenario list with no bytes in it.** Every file here is *offloaded*: its
`base64_string` is the literal word, and the image itself lives wherever the
platform put it. That is what a scenario list exported after an upload looks
like, and it is worth an example precisely because a preview cannot resolve it.
Each option draws `(image unavailable)` -- the same thing the live page draws
for a file it cannot show -- rather than a broken picture. Point the same survey
at a list whose files are inline and the pictures appear with nothing else
changed.

**Questions nobody is asked.** The three `image_generation` questions are the
survey's subject and are never shown to a respondent: they run between pages and
their answers are what `ratings` and `favorite` then ask about. `check` calls
them `automatic`, which is the outcome that means *nothing is missing*.

**Answers piped into a later question's options.** `ratings` and `favorite`
reference `{{ img_watercolor.answer }}` and its siblings. A preview has no
answers, so those stay as written -- the same rendering they get when a scenario
is bound but a prior answer is not. `dish` shows the sharper edge of that: it
*filters* a prior answer (`| trim` over a `.split(...)`), and a filter applied to
a name standing in for something absent takes the whole question's render down
with it, so `dish` previews entirely unpiped. That is the documented trade -- a
visible untouched template rather than a plausible wrong number.

The schema also asks for a stepped progress indicator and a carousel-formatted
matrix, so the example covers both alongside the media.

Nothing here needs a file on disk. The scenario list is built from the offloaded
form directly, which keeps the example a few hundred bytes instead of a few
hundred kilobytes of base64 -- and keeps it honest about the case it is showing.
"""

from __future__ import annotations

from edsl.questions import (
    QuestionFreeText,
    QuestionImageGeneration,
    QuestionMatrix,
    QuestionMultipleChoice,
)
from edsl.scenarios import FileStore, Scenario, ScenarioList
from edsl.surveys import Survey

# The three renderings the survey generates and then asks about. Named once so
# the questions that make them and the questions that ask about them cannot
# drift apart.
STYLES = {
    "img_watercolor": ("Watercolor", "A loose watercolor painting"),
    "img_photo": ("Photo", "A photorealistic overhead studio photograph"),
    "img_cartoon": ("Cartoon", "A bold flat-color cartoon illustration"),
}

# Each generated image, referenced as an option: the caption a respondent reads,
# then the answer that resolves to the picture itself.
GENERATED_OPTIONS = [
    f"{caption} {{{{ {name}.answer }}}}" for name, (caption, _) in STYLES.items()
]


# The four images as the platform recorded them after upload: the id it stored
# each under, and the digest it took of the bytes. Real ids, kept rather than
# invented, because they are how the file is fetched back -- an example carrying
# made-up ones would describe the shape and none of the substance.
UPLOADS = {
    "baked": ("3d316073-83c4-41d9-ae73-11c234f24081", "773fcf75bc3a30f7ed3d7d5e2022dfa6"),
    "grilled": ("4774a835-b96f-4503-907c-5aae1f2173f6", "af9eb3d31b96a9fb46a3342493a55595"),
    "noodles": ("c603f0fd-9f1b-49a3-8349-2c5a5cc423e7", "4fc1379d28eff0dd57cc448f74418e0b"),
    "dessert": ("a4fc7702-1a50-4060-9838-c82e04daeeb2", "0f146108a3f88eb99ed94542852efdfa"),
}


def offloaded(name: str) -> FileStore:
    """A scenario file whose bytes live somewhere a preview cannot reach.

    The shape a scenario list has after its media has been uploaded: the file is
    described -- what kind it is, the id it was stored under, a digest of the
    bytes -- and ``base64_string`` says ``offloaded`` rather than carrying the
    image. Assembled here rather than read from disk because there is no disk
    copy to read: this example is *about* the offloaded case, and a file inlined
    into it would be a different one.

    ``path`` keeps the file's name and not the directory it was uploaded from,
    which was one machine's layout and is nobody else's business. Everything a
    later pass needs to find the file again -- the id, the digest -- is here.
    """
    file_uuid, content_hash = UPLOADS[name]
    return FileStore.from_dict(
        {
            "path": f"{name}.jpg",
            "base64_string": "offloaded",
            "binary": True,
            "suffix": "jpg",
            "mime_type": "image/jpeg",
            "external_locations": {
                "gcs": {
                    "file_uuid": file_uuid,
                    "uploaded": True,
                    "offloaded": True,
                    "content_hash": content_hash,
                    "token_estimate": 516,
                }
            },
            "extracted_text": None,
        }
    )


survey = Survey(
    [
        QuestionMultipleChoice(
            question_name="food_category",
            question_text="Pick one.",
            question_options=[
                "Baked goods {{ scenario.baked_img }}",
                "Grilled {{ scenario.grilled_img }}",
                "Noodles {{ scenario.noodles_img }}",
                "Dessert {{ scenario.dessert_img }}",
            ],
        ),
        QuestionFreeText(
            question_name="dish",
            # Splits the marker back off the chosen option to recover the words
            # a respondent saw. A filter over a prior answer, so this previews
            # unpiped -- see the module docstring.
            question_text=(
                "You picked {{ food_category.answer.split('<see file')[0] | trim }}. "
                "Name one dish in that category."
            ),
        ),
        *[
            QuestionImageGeneration(
                question_name=name,
                question_text=f"{prompt} of {{{{ dish.answer }}}}, on a plain background.",
                model="gemini-3.1-flash-image",
                service_name="google",
            )
            for name, (_, prompt) in STYLES.items()
        ],
        QuestionMatrix(
            question_name="ratings",
            question_text="Rate each image.",
            question_items=GENERATED_OPTIONS,
            question_options=[1, 2, 3, 4, 5],
            option_labels={1: "Terrible", 3: "Fine", 5: "Delicious"},
        ),
        QuestionMultipleChoice(
            question_name="favorite",
            question_text="Which would you actually want to eat?",
            question_options=GENERATED_OPTIONS,
        ),
    ],
    # Both picture questions are shuffled, which is why an option's blocks are
    # matched to it by position against the order actually served rather than
    # derived once from the authored list.
    questions_to_randomize=["food_category", "favorite"],
)

scenarios = ScenarioList(
    [
        Scenario(
            {
                "baked_img": offloaded("baked"),
                "grilled_img": offloaded("grilled"),
                "noodles_img": offloaded("noodles"),
                "dessert_img": offloaded("dessert"),
            }
        )
    ]
)

humanize_schema = {
    "questions": {
        "dish": {
            "submitting_indicator": {
                "type": "callout",
                "title": "Generating 3 images of your dish...",
            }
        },
        "ratings": {
            "format": {"type": "carousel"},
            "comment": {"label": "Anything to add about these?"},
        },
    },
    "survey": {
        "custom_css": """
/* ---- Image options as a card grid ---- */
.edsl-multiple-choice-question .edsl-options {
    display: grid;
    grid-template-columns: 1fr;      /* single column on phones */
    gap: 1rem;
}

/* The options container also carries a vertical-rhythm rule that puts a
    margin-top on every option after the first. Harmless in a column, stray gaps
    in a grid. This selector matches its specificity, so it wins. */
.edsl-multiple-choice-question .edsl-options > :not([hidden]) ~ :not([hidden]) {
    margin-top: 0;
}

@media (min-width: 640px) {
    .edsl-multiple-choice-question .edsl-options {
        grid-template-columns: repeat(2, 1fr);   /* 2x2 for the four categories */
    }

    /* Exactly three options -- the favourite question -- would otherwise sit
        2 + 1 with an orphan on its own row. One row of three instead. */
    .edsl-multiple-choice-question
        .edsl-options:has(> .edsl-option:nth-child(3):last-child) {
        grid-template-columns: repeat(3, 1fr);
    }
}

.edsl-multiple-choice-question .edsl-option {
    flex-direction: column-reverse;   /* picture on top, radio beneath it */
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem;
    border: 1px solid rgb(148 163 184 / 0.35);
    border-radius: 0.75rem;
    cursor: pointer;
}

.edsl-multiple-choice-question .edsl-option:hover {
    border-color: rgb(22 163 74 / 0.5);
}

.edsl-multiple-choice-question .edsl-option:has(.edsl-radio:checked) {
    border-color: rgb(22 163 74);
    background: rgb(22 163 74 / 0.1);
}

.edsl-multiple-choice-question .edsl-option-label {
    margin-left: 0;
    text-align: center;
}

.edsl-multiple-choice-question .edsl-option-content {
    align-items: center;
}

.edsl-multiple-choice-question .edsl-option-image {
    max-height: none;
    width: 100%;
    aspect-ratio: 1 / 1;
    object-fit: cover;
    border-radius: 0.5rem;
}

/* ---- Matrix rows, one slide each: caption above a large thumbnail ---- */
/* The row label owns the full width of the slide now, so the picture finally
    gets the size the sticky label column never had room for. */
.edsl-matrix-question .edsl-matrix-carousel-item {
    text-align: center;
}

.edsl-matrix-question .edsl-matrix-carousel-item .edsl-option-content {
    flex-direction: column;      /* caption on top, image beneath */
    align-items: center;
    gap: 0.5rem;
    width: 100%;
}

.edsl-matrix-question .edsl-matrix-carousel-item .edsl-option-text {
    font-weight: 600;
}

.edsl-matrix-question .edsl-matrix-carousel-item .edsl-option-image {
    max-height: none;
    width: 100%;
    max-width: 14rem;
    aspect-ratio: 1 / 1;
    object-fit: cover;
    border-radius: 0.5rem;
    margin-inline: auto;
}

/* The rating options are full-width rows here, not radios in a column of a
    grid -- so give them the same green "chosen" state as the picture cards. */
.edsl-matrix-question .edsl-option:hover {
    border-color: rgb(22 163 74 / 0.5);
}

.edsl-matrix-question .edsl-option:has(.edsl-radio:checked) {
    border-color: rgb(22 163 74);
    background: rgb(22 163 74 / 0.1);
}

/* The dots are the overview the grid gave away: a filled one is a row already
    rated. Same green, so the survey has one meaning for "done". */
.edsl-matrix-question .edsl-matrix-carousel-dot-answered > span {
    background: rgb(22 163 74);
}

.edsl-matrix-question .edsl-matrix-carousel-dot-current > span {
    box-shadow: 0 0 0 2px #fff, 0 0 0 4px rgb(22 163 74);
}
""",
        "progress": {
            "type": "steps",
            "marker": "number",
            "steps": [
                {"label": "Category", "complete_after": "food_category"},
                {"label": "Your dish", "complete_after": "dish"},
                {"label": "Rate", "complete_after": "ratings"},
                {"label": "Favorite"},
            ],
        },
    },
}

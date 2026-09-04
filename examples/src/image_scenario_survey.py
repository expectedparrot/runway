"""A scenario list whose keys hold images, drawn into the question they belong to.

A scenario value may be a `FileStore` -- an image, a PDF, an audio clip -- and it
is not decoration on the question. A question whose text names one is split
around it into blocks, and the image is drawn between the words: text, picture,
text, in the order they were written. That is the page a respondent is served,
so it is the page a preview has to show.

Where the live survey has a link to a file it has fetched, a preview has the
bytes: a `FileStore` carries its file base64-encoded inside the scenario list,
so the image is inlined into the page as a `data:` URI. Same markup, same
splitting, same order -- only the source of the bytes differs, and it has to,
because a preview is one file with nothing behind it.

The survey asks for all four combinations, because a file key and a plain key
are built into the replacement dictionary differently and only an example pins
what actually reaches the page:

| reference               | renders as          |
| ----------------------- | ------------------- |
| `{{ colour }}`          | `Ember Red`         |
| `{{ scenario.colour }}` | `Ember Red`         |
| `{{ swatch }}`          | the swatch, drawn   |
| `{{ scenario.swatch }}` | the swatch, drawn   |

**The last row is the one worth having an example for, because it is not what
the replacement dictionary appears to say.** `scenarios.replacements` puts a
file key in bare and deliberately leaves it out of the `scenario` namespace --
and rendering the two templates against that dictionary directly does give
`<see file swatch>` and `''`.

But the dictionary is not what resolves the template. It is handed to
`QuestionBase.render`, which discards the namespace it was given and rebuilds
`scenario` as a shallow copy of every *other* key ("allows both
{{ scenario.x }} and {{ scenario }} to work"). The bare marker is one of those
keys, so it is put back under the namespace on the way through, and both
spellings resolve to the same file. The live survey renders through that same
call, so this is what a respondent is served, not an artefact of previewing.

Worth an example precisely because a unit test on the replacement dictionary
cannot see it: that dictionary is one half of an arrangement edsl completes,
and it reads correct either way. Only a rendered question shows what is served.

`<see file swatch>` is still what the *text* renders to -- it is the marker the
split is performed on, and a survey naming a key that holds no file stops there
and draws as "Unsupported file type". It is an intermediate now, not the output.

The swatches are 480x320 solid-colour PNGs, 939 bytes each, under
`examples/media`. Big enough to see -- an image is drawn at its natural size,
so a 16x16 file previews as a speck -- and still nearly free, because a solid
colour compresses to almost nothing. That matters here: a `FileStore` base64s
the file into the scenario list, and the scenario list is generated but
**committed**, so a photograph would be a megabyte of churn in every diff that
touched it.

Each swatch is referenced by a **repo-relative** path and loaded from an
absolute one. A `FileStore` records the path it was handed verbatim, so building
one from an absolute path would write this machine's directory layout into a
committed file and `build.py --check` would call the example stale on every
other machine. Reading the bytes here rather than letting the FileStore open the
file is what lets those two paths differ.

It is also what makes the bytes right. `FileStore`'s own encoder opens a file in
**text mode first** and only falls back to binary when that raises -- and under a
single-byte platform codec, reading a PNG as text usually does not raise. It
"succeeds", re-encodes as UTF-8, and the file silently grows a few hundred bytes
that are not the file. Whether an image survives being put in a scenario list
comes down to whether its bytes happen to include one the codec rejects, which
is why two of these three swatches used to round-trip and the third did not.
Building the entry from bytes read here skips that encoder entirely.
"""

from __future__ import annotations

import base64
from pathlib import Path

from edsl.questions import QuestionFreeText, QuestionMultipleChoice
from edsl.scenarios import FileStore, Scenario, ScenarioList
from edsl.surveys import Survey

REPO = Path(__file__).resolve().parents[2]
MEDIA = "examples/media"


def swatch(name: str) -> FileStore:
    """The PNG at ``examples/media/<name>.png``, as a scenario file value.

    Assembled rather than opened, for the two reasons in the module docstring:
    the recorded path stays relative while the read is absolute, and the bytes
    are the file's own.
    """
    relative = f"{MEDIA}/{name}.png"
    data = (REPO / relative).read_bytes()
    return FileStore.from_dict(
        {
            "path": relative,
            "base64_string": base64.b64encode(data).decode("ascii"),
            "binary": True,
            "suffix": "png",
            "mime_type": "image/png",
            "external_locations": {},
            "extracted_text": None,
        }
    )


survey = Survey(
    [
        QuestionMultipleChoice(
            question_name="reaction",
            question_text=(
                "Here is **{{ colour }}**.\n\n"
                "{{ swatch }}\n\n"
                "How does it strike you?"
            ),
            question_options=[
                "I would live with it",
                "Only as an accent",
                "Not for me",
            ],
        ),
        QuestionFreeText(
            question_name="room",
            question_text="Which room would you put {{ scenario.colour }} in?",
        ),
        QuestionFreeText(
            question_name="namespaced",
            question_text=(
                "The swatch again, through the namespace: "
                "{{ scenario.swatch }} -- the same image, because the "
                "render rebuilds the namespace from the keys around it."
            ),
        ),
    ]
)

scenarios = ScenarioList(
    [
        Scenario({"colour": "Ember Red", "swatch": swatch("ember-red")}),
        Scenario({"colour": "Harbour Blue", "swatch": swatch("harbour-blue")}),
        Scenario({"colour": "Fern Green", "swatch": swatch("fern-green")}),
    ]
)

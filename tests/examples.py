"""The example surveys, and the schemas that sit beside them.

An example is two files, because that is what an author has: the survey is
``Survey.to_dict()`` verbatim, which carries no humanize schema because a schema
is not part of an EDSL survey, and the schema — where the survey needs one —
lives under ``examples/schemas`` with the same name.

Tests read them through here rather than calling ``load`` directly, so that a
test cannot quietly stop applying a schema. Several of the interesting cases
only exist because of one: a matrix is a carousel rather than a grid, a
question is a dropdown rather than radios, an option is exclusive. Dropping the
schema would leave those paths green and unexercised.
"""

from __future__ import annotations

from pathlib import Path

from runway.survey import load, load_schema

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
SCHEMAS = EXAMPLES / "schemas"


def paths() -> list[Path]:
    """Every example survey, in a stable order."""
    return sorted(EXAMPLES.glob("*.json"))


def schema_path(survey: Path) -> Path:
    """Where a survey's schema would be, whether or not it has one."""
    return SCHEMAS / survey.name


def load_example(survey: Path) -> tuple[list[dict], dict]:
    """A survey's questions and its schema, from the two files."""
    questions = load(survey)
    sidecar = schema_path(survey)
    return questions, load_schema(sidecar) if sidecar.is_file() else {}

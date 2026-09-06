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
SCENARIOS = EXAMPLES / "scenarios"


def paths() -> list[Path]:
    """Every example survey, in a stable order."""
    return sorted(EXAMPLES.glob("*.json"))


def schema_path(survey: Path) -> Path:
    """Where a survey's schema would be, whether or not it has one."""
    return SCHEMAS / survey.name


def scenarios_path(survey: Path) -> Path:
    """Where a survey's scenario list would be, whether or not it has one.

    A third file for the same reason there is a second: a scenario list is
    bound to a survey rather than stored in one, so it arrives on its own.
    """
    return SCENARIOS / survey.name


def load_example(survey: Path) -> tuple[list[dict], dict]:
    """A survey's questions and its schema, from the two files."""
    return load(survey).get("questions") or [], load_example_schema(survey)


def load_example_schema(survey: Path) -> dict:
    """A survey's schema, or ``{}`` where it needs none."""
    sidecar = schema_path(survey)
    return load_schema(sidecar) if sidecar.is_file() else {}


def load_grouped_example(survey: Path) -> tuple[list[dict], dict, dict]:
    """The same, plus the survey's own question groups.

    A third thing an example is made of, and unlike the schema it *is* in the
    survey file -- so it comes out of the same read rather than from a sidecar.
    Empty for the surveys that define none, which is all but one of them.
    """
    document = load(survey)
    return (
        document.get("questions") or [],
        load_example_schema(survey),
        document.get("question_groups"),
    )

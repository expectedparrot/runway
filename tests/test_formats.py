"""The formats a survey arrives in, and that they all say the same thing.

`Survey.save()` writes a `.ep` package by default -- a git repository in a zip,
one JSON file per question -- and `.json.gz` or `.json` on request. All three go
through `Survey.load()`, which is edsl's business rather than this package's, so
what is worth pinning is not how they are opened but that opening them lands in
the same place: **the same survey renders byte for byte the same page whichever
file it came out of.** Reading them all the same way is what buys that. A JSON
survey read by a lookalike reader here would drift -- integer `option_labels`
keys come back from JSON as strings, and that is only the difference anyone has
noticed -- and the result would be a preview that lied about a survey nobody had
changed.

A humanize schema is not part of any of them. edsl neither writes one nor reads
one, so it is not something a survey file has to give, whatever its format:
`--schema` is the only route, and a `humanize_schema` key written into a survey
document is ignored rather than honoured. That is pinned here, because "ignored"
is a claim about behaviour and not just an absence.

The fixtures are built here rather than committed, because a `.ep` is a zip of
a git repository and so is different every time it is written: committing one
would be a binary that never matched itself. Building one needs the `git`
executable, which nothing else in this package does, so those skip without it.

Runs under pytest, or directly: python tests/test_formats.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import examples
from runway.cli import main
from runway.survey import SurveyLoadError, load, name_for

EXAMPLE = examples.EXAMPLES / "mixed_survey.json"
SCHEMA = examples.SCHEMAS / "mixed_survey.json"

needs_git = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="a .ep package is a git repository, so writing one needs git",
)


def _saved_as(tmp_path: Path, name: str) -> Path:
    """The example survey, resaved by edsl under ``name``.

    ``save()`` picks its format from the file name, the same way ``load()``
    picks how to open one -- so naming the file is all it takes to get a
    package rather than a dump.
    """
    from edsl.surveys import Survey

    path = tmp_path / name
    Survey.load(str(EXAMPLE)).save(str(path))
    assert path.is_file(), f"edsl did not write {path}"
    return path


def _render(survey: Path, out: Path) -> str:
    assert main(["render", str(survey), "--schema", str(SCHEMA), "-o", str(out)]) == 0
    written = list(out.glob("*.html"))
    assert len(written) == 1, written
    return written[0].read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# The same survey, whichever file it came out of
# --------------------------------------------------------------------------


@needs_git
def test_a_package_renders_the_same_page_as_its_json(tmp_path):
    """The whole point of reading `.ep` at all: it is the same survey."""
    package = _saved_as(tmp_path, "mixed_survey.ep")
    assert _render(package, tmp_path / "from_ep") == _render(
        EXAMPLE, tmp_path / "from_json"
    )


def test_a_compressed_dump_renders_the_same_page_as_its_json(tmp_path):
    assert _render(
        _saved_as(tmp_path, "mixed_survey.json.gz"), tmp_path / "from_gz"
    ) == _render(EXAMPLE, tmp_path / "from_json")


@needs_git
def test_loading_a_package_yields_questions_and_nothing_else(tmp_path):
    """A survey file has questions in it; a schema is not a survey's to carry."""
    assert load(_saved_as(tmp_path, "mixed_survey.ep"))


# --------------------------------------------------------------------------
# What the output is called
# --------------------------------------------------------------------------


def test_output_is_named_for_the_survey_not_the_file(tmp_path):
    """`.json.gz` is two suffixes, so `Path.stem` would leave one behind and
    write `mixed_survey.json.html`."""
    out = tmp_path / "out"
    _render(_saved_as(tmp_path, "mixed_survey.json.gz"), out)
    assert (out / "mixed_survey.html").is_file()


def test_name_for_strips_every_format_suffix():
    assert name_for(Path("a/mixed_survey.ep")) == "mixed_survey"
    assert name_for(Path("a/mixed_survey.json")) == "mixed_survey"
    assert name_for(Path("a/mixed_survey.json.gz")) == "mixed_survey"
    # Not a format this reads, so the file's own stem is the best guess.
    assert name_for(Path("a/mixed_survey.txt")) == "mixed_survey"


# --------------------------------------------------------------------------
# The humanize schema, which is not part of a survey at all
# --------------------------------------------------------------------------


DROPDOWN = {"questions": {"commute_time": {"format": {"type": "dropdown"}}}}


def test_a_schema_written_into_a_survey_document_is_ignored(tmp_path):
    """`humanize_schema` is not an EDSL survey key. edsl drops it on the way in,
    and so does this -- the file previews as though it were not there, which is
    what makes `--schema` the one route rather than the usual one."""
    document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    document["humanize_schema"] = DROPDOWN
    inline = tmp_path / "mixed_survey.json"
    inline.write_text(json.dumps(document), encoding="utf-8")

    assert load(inline) == load(EXAMPLE)

    out, plain = tmp_path / "inline", tmp_path / "plain"
    assert main(["render", str(inline), "-o", str(out)]) == 0
    assert main(["render", str(EXAMPLE), "-o", str(plain)]) == 0
    assert (out / "mixed_survey.html").read_text(encoding="utf-8") == (
        plain / "mixed_survey.html"
    ).read_text(encoding="utf-8")


def test_a_schema_reaches_a_survey_of_any_format_through_the_flag(tmp_path):
    """The route that does work, and that it works the same for a package as
    for the JSON it was saved from."""
    sidecar = tmp_path / "sidecar.json"
    sidecar.write_text(json.dumps(DROPDOWN), encoding="utf-8")

    def styled(survey: Path, out: Path) -> str:
        assert main(["render", str(survey), "--schema", str(sidecar), "-o", str(out)]) == 0
        return (out / "mixed_survey.html").read_text(encoding="utf-8")

    from_json = styled(EXAMPLE, tmp_path / "json_out")
    # The schema asked for a dropdown, so it has to have changed something.
    assert from_json != _render(EXAMPLE, tmp_path / "unstyled")
    if shutil.which("git"):
        assert styled(_saved_as(tmp_path, "mixed_survey.ep"), tmp_path / "ep_out") == from_json


# --------------------------------------------------------------------------
# Failure
# --------------------------------------------------------------------------


def test_a_bare_list_is_refused_with_a_way_forward(tmp_path):
    """It used to be accepted, and edsl cannot build a `Survey` from one. What
    matters is that it fails as itself: edsl's own error is a `ValueError`
    about sequence lengths, which tells nobody what to do next."""
    bare = tmp_path / "bare.json"
    bare.write_text(
        json.dumps(
            [
                {
                    "question_name": "modes",
                    "question_type": "checkbox",
                    "question_text": "Which?",
                    "question_options": ["Bus", "Train"],
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(SurveyLoadError) as caught:
        load(bare)
    assert "questions" in str(caught.value)
    assert main(["check", str(bare)]) == 1


def test_a_stubbed_survey_document_says_what_is_missing(tmp_path):
    """The cost of loading through edsl, so it should read like one. edsl's own
    message is a bare `KeyError: 'data'`, which names neither the problem nor
    the fix."""
    stub = tmp_path / "stub.json"
    stub.write_text(
        json.dumps(
            {
                "questions": [
                    {
                        "question_name": "q",
                        "question_type": "free_text",
                        "question_text": "Hi",
                    }
                ],
                "memory_plan": {},
                "rule_collection": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SurveyLoadError) as caught:
        load(stub)
    assert "memory_plan" in str(caught.value)
    assert main(["check", str(stub)]) == 1


def test_a_missing_file_fails_as_a_load_error_in_every_format(tmp_path):
    """`load` promises one exception; a file that is not there must not slip
    out as an OSError from whichever reader happened to open it."""
    for name in ("nope.json", "nope.json.gz", "nope.ep"):
        with pytest.raises(SurveyLoadError):
            load(tmp_path / name)


def test_an_unopenable_package_is_reported_rather_than_raised(tmp_path):
    """A `.ep` fails in more ways than JSON does -- a missing `git`, a zip that
    is not a package -- and none of them should reach a user as a traceback."""
    bad = tmp_path / "bad.ep"
    bad.write_bytes(b"not a zip")
    with pytest.raises(SurveyLoadError):
        load(bad)
    assert main(["check", str(bad)]) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

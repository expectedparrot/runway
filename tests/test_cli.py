"""Tests for the command line and the classification behind `check`.

Two things are worth pinning here. The first is that `check` agrees with what
rendering actually does -- it exists to save you from rendering, so a report
that disagreed with the page would be worse than no report. That is
`test_check_agrees_with_what_render_produces`, which renders every example and
confirms the claimed status matches the markup.

The second is the shape of the CLI: a verb is always required, and the old bare
form is gone rather than quietly aliased.

Runs under pytest, or directly: python tests/test_cli.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from runway import inspection
from runway.cli import main
from runway.renderer import render_question
from runway.survey import iter_questions, load

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
MIXED = EXAMPLES / "mixed_survey.json"
BACKGROUND = EXAMPLES / "background_survey.json"

# The class each stand-in puts on the page. The templates carry one per case
# already, which makes them exactly the right hook: a template that stopped
# emitting its class would fail here rather than silently make `check` a liar.
MARKERS = {
    "note": "edsl-preview-note",
    "warning": "edsl-preview-warning",
    "automatic": "edsl-preview-background",
}


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------


def test_check_agrees_with_what_render_produces():
    """The point of `check`: its verdict is the page's verdict.

    Rendering is the ground truth -- `check` is only useful because it saves
    you from doing it, so the two must not be able to disagree.
    """
    for example in sorted(EXAMPLES.glob("*.json")):
        questions, _ = load(example)
        for position, question in iter_questions(questions):
            status = inspection.classify(question)
            html = render_question(question)
            if status == "drawn":
                assert not any(m in html for m in MARKERS.values()), (
                    example.name,
                    position,
                )
            else:
                # The claimed status, and only it: a note that also carried the
                # warning class would mean the two had stopped being distinct.
                for other, marker in MARKERS.items():
                    present = marker in html
                    assert present == (other == status), (
                        example.name,
                        position,
                        status,
                        other,
                    )


def test_a_thinking_wrapper_beats_its_type():
    """The case the whole design turns on.

    A thinking-wrapped multiple_choice is still multiple_choice, so a
    classifier that asked the type registry first would call it `drawn` and
    promise a radio list for a page nobody is served.
    """
    wrapped = {
        "question_type": "multiple_choice",
        "question_name": "q",
        "question_options": ["a", "b"],
        "thinking_model": "some-model",
    }
    assert inspection.classify(wrapped) == "automatic"
    del wrapped["thinking_model"]
    assert inspection.classify(wrapped) == "drawn"


def test_an_unrenderable_type_is_a_warning_not_a_note():
    assert inspection.classify({"question_type": "dict", "question_name": "q"}) == "warning"
    assert inspection.classify({"question_type": "rank", "question_name": "q"}) == "note"


def test_summarize_reports_every_status_even_at_zero():
    counts = inspection.summarize([{"status": "drawn"}])
    assert set(counts) == set(inspection.STATUSES)
    assert counts["drawn"] == 1 and counts["warning"] == 0


def test_describe_names_which_kind_of_automatic():
    entry = inspection.describe({"question_type": "compute", "question_name": "q"}, 1)
    assert entry["kind"] == "compute"
    # Only the automatic branch carries it; the others have nothing to say.
    assert "kind" not in inspection.describe(
        {"question_type": "yes_no", "question_name": "q"}, 1
    )


# --------------------------------------------------------------------------
# the command line
# --------------------------------------------------------------------------


def test_a_verb_is_required():
    """The bare form is gone, not aliased to render.

    argparse exits rather than returning for an unrecognized subcommand, so a
    survey path in the verb position is a SystemExit -- with the five valid
    choices named in the message.
    """
    assert main([]) == 2
    try:
        main([str(MIXED)])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("a bare survey path was accepted as a command")


def test_check_writes_nothing(tmp_path):
    before = set(tmp_path.iterdir())
    main(["check", str(MIXED)])
    assert set(tmp_path.iterdir()) == before


def test_check_fails_only_on_an_unshowable_question():
    # mixed_survey carries a `dict`, which no survey can put to a person.
    assert main(["check", str(MIXED)]) == 1
    # background_survey's undrawn types are this package being behind, which is
    # not the survey's problem and must not fail a build.
    assert main(["check", str(BACKGROUND)]) == 0


def test_check_json_is_parseable_and_complete(capsys):
    main(["check", "--json", str(MIXED)])
    report = json.loads(capsys.readouterr().out)["surveys"][0]
    assert report["items"] == 7
    assert sum(report["summary"].values()) == len(report["questions"])
    assert {q["status"] for q in report["questions"]} <= set(inspection.STATUSES)


def test_types_json_covers_every_humanized_type(capsys):
    from runway.question_types import unsupported

    main(["types", "--json"])
    rows = json.loads(capsys.readouterr().out)["types"]
    assert {row["type"] for row in rows} == set(unsupported.HUMANIZED_TYPES)


def test_types_marks_the_automatic_ones_as_handled(capsys):
    """compute and image_generation have no control and need none."""
    main(["types", "--json"])
    rows = {row["type"]: row["status"] for row in json.loads(capsys.readouterr().out)["types"]}
    assert rows["compute"] == "automatic"
    assert rows["image_generation"] == "automatic"
    assert rows["multiple_choice"] == "drawn"
    assert rows["rank"] == "note"


def test_version_reports_what_it_draws(capsys):
    from runway import __version__
    from runway.question_types import RENDERERS

    main(["version", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["version"] == __version__
    assert data["drawn_types"] == sorted(RENDERERS)


def test_guide_mentions_each_command(capsys):
    main(["guide"])
    out = capsys.readouterr().out
    for command in ("check", "render", "types"):
        assert command in out


def test_render_writes_a_bundle(tmp_path):
    assert main(["render", str(MIXED), "-o", str(tmp_path)]) == 0
    assert [p.name for p in tmp_path.iterdir()] == ["mixed_survey.html"]


def test_a_missing_file_is_an_error_not_a_traceback(tmp_path):
    assert main(["render", str(tmp_path / "nope.json"), "-o", str(tmp_path)]) == 1
    assert main(["check", str(tmp_path / "nope.json")]) == 1


def test_malformed_json_is_reported_rather_than_raised(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main(["check", str(bad)]) == 1


def test_nothing_is_written_when_one_of_several_surveys_is_bad(tmp_path):
    """Read everything first, so a bad path leaves the directory as it was."""
    out = tmp_path / "out"
    assert main(["render", str(MIXED), str(tmp_path / "nope.json"), "-o", str(out)]) == 1
    assert not out.exists()


def _main() -> int:
    """Standalone runner. Skips the tests that need pytest fixtures."""
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, fn in sorted(globals().items()):
            if not name.startswith("test_") or not callable(fn):
                continue
            code = fn.__code__
            kwargs = {}
            if "tmp_path" in code.co_varnames[: code.co_argcount]:
                kwargs["tmp_path"] = Path(tmp) / name
                kwargs["tmp_path"].mkdir(parents=True, exist_ok=True)
            elif "capsys" in code.co_varnames[: code.co_argcount]:
                print(f"skip {name}: needs pytest's capsys")
                continue
            try:
                fn(**kwargs)
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc or '(assertion failed)'}")
            else:
                print(f"ok   {name}")
    print("\n" + ("all passed" if not failures else f"{failures} failure(s)"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
